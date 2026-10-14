"""
Compilation of the stops of all the GTFS datasets into a single table :
- compile_all_stops(all_stops_data)
"""

import gc
from pathlib import Path
import logging
import traceback
import polars as pl

from transports_publics_france.config import TABLES_GTFS

log = logging.getLogger(__name__)


def compile_all_stops(all_stops_data: list[pl.DataFrame]) -> pl.DataFrame:
    """Concatenate the stops tables of the datasets, then clean and deduplicate them.

    Returns an empty DataFrame if there is nothing to compile.
    """
    if all_stops_data:
        all_stops_data = [
            df.with_columns(pl.col("freq_ppm_max").cast(pl.Int64))
            if "freq_ppm_max" in df.columns else df
            for df in all_stops_data
        ]
        all_stops = pl.concat(all_stops_data, how="diagonal")
    else:
        all_stops = pl.DataFrame()
        log.warning("No stops compiled.")

    if len(all_stops) > 0:
        # Final cleanups
        all_stops = all_stops.filter(
            pl.col("latitude").is_not_null() | pl.col("route_id").is_null()
        )

        if "agency_lang" in all_stops.columns:
            all_stops = all_stops.with_columns(
                pl.col("agency_lang").str.to_uppercase()
                .str.replace("^$", None)
                .str.replace("FR-FR", "FR")
                .alias("agency_lang")
            )

        if "freq_ppm_max" in all_stops.columns:
            all_stops = all_stops.with_columns(pl.col("freq_ppm_max").fill_null(0))
        all_stops = all_stops.unique()

        # Final verification of route_type "non renseigné"
        if "route_type" in all_stops.columns:
            nb_nr = all_stops.filter(pl.col("route_type") == "non renseigné").height
            if nb_nr < len(all_stops) * 0.001:
                all_stops = all_stops.with_columns(
                    pl.when(pl.col("route_type") == "non renseigné")
                    .then(pl.lit("autres"))
                    .otherwise(pl.col("route_type"))
                    .alias("route_type")
                )

        # Final deduplication
        sort_col = "freq_ppm_max" if "freq_ppm_max" in all_stops.columns else all_stops.columns[0]

        for group_cols in [
            ["stop_name_red", "route_short_name", "route_type", "latitude", "longitude"],
            ["stop_id", "stop_name_red", "route_id", "agency_id"],
        ]:
            valid_group = [c for c in group_cols if c in all_stops.columns]
            if valid_group and sort_col in all_stops.columns:
                all_stops = (
                    all_stops.sort(sort_col, descending=True)
                    .group_by(valid_group)
                    .first()
                )

        # Final deduplication by rounded coordinates
        if "latitude" in all_stops.columns and "longitude" in all_stops.columns:
            all_stops = all_stops.with_columns([
                pl.col("latitude").round(3).alias("arrond_lat"),
                pl.col("longitude").round(3).alias("arrond_lon"),
            ])
            group_rnd = [
                c for c in ["stop_name_red", "route_short_name",
                            "route_type", "arrond_lat", "arrond_lon"]
                if c in all_stops.columns]
            if group_rnd and sort_col in all_stops.columns:
                all_stops = (
                    all_stops.sort(sort_col, descending=True)
                    .group_by(group_rnd)
                    .first()
                    .drop(["arrond_lat", "arrond_lon"])
                )

    return all_stops


def unify_gtfs_tables(raw_dir: Path, out_dir: Path) -> None:
    """Stack the tables of all datasets (raw_dir/<table>/<dataset_id>.parquet)
    into one parquet per table in out_dir."""
    log.info("=== Unification of the raw GTFS tables ===")

    for tbl in TABLES_GTFS:
        tbl_dir = raw_dir / tbl
        fichiers = list(tbl_dir.glob("*.parquet")) if tbl_dir.exists() else []
        if not fichiers:
            log.warning("Table %s : no file was found, pass.", tbl)
            continue

        out_path = out_dir / f"{tbl}.parquet"
        try:
            if tbl == "stop_times":
                lfs = [pl.scan_parquet(str(f)) for f in fichiers]
                lf = pl.concat(lfs, how="diagonal_relaxed")
                lf.sink_parquet(out_path)
            else:
                dfs = [pl.read_parquet(f) for f in fichiers]
                consolidated = pl.concat(dfs, how="diagonal")
                consolidated.write_parquet(out_path)
                del dfs, consolidated

            log.info("Table %s unified (%d datasets).", tbl, len(fichiers))
            gc.collect()
        except Exception as e:
            log.error("Table %s : failed to unify (%s).", tbl, e)
            log.error(traceback.format_exc())
