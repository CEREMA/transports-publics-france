"""
Pipeline for downloading and processing the GTFS data

# TODO For now it is a full script but it has to be refactored
# TODO : We need to mark whether a function is public or private
"""

import gc
import traceback
import logging
from datetime import date
import polars as pl

# TODO config must be removed to be package-compatible : must become parameters
from transports_publics_france.config import (
    DATA_DIR, BASE_DIR, RAW_DIR, REDOWNLOAD, RUN_DATE,
    DAY_RUN_DATE, CONSOLIDATED_DIR, REQUIRED_FILES,
    REQUIRED_COLS, ID_COLS, TABLES_GTFS, GTFS_FILES_WANTED
)

from transports_publics_france.gtfs.io import extract_gtfs_zip, read_gtfs_dataset
from transports_publics_france.gtfs.api import get_gtfs_datasets_info
from transports_publics_france.gtfs.download_gtfs import download_resources
from transports_publics_france.gtfs.stop_data import get_stop_data
from transports_publics_france.utils import _flatten_nested_columns

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Metadata recuperation
# ─────────────────────────────────────────────
log.info("=== GTFS metadata recuperation ===")

try:
    gtfs_datasets = get_gtfs_datasets_info()
    gtfs_datasets = gtfs_datasets.with_columns(
        pl.lit(str(RUN_DATE)).alias("resources_extract_date")
    )
    log.info("%d available GTFS datasets on the API.", len(gtfs_datasets))
except Exception as e:
    log.error("Impossible to get the metadata : %s", e)
    gtfs_datasets = pl.DataFrame()


# ─────────────────────────────────────────────
# Download and/or detection of the GTFS
# ─────────────────────────────────────────────
log.info("=== Download / detection of the already downloaded GTFS ===")

if REDOWNLOAD and len(gtfs_datasets) > 0:
    download_resources(gtfs_datasets, redownload=REDOWNLOAD, timeout=15)

all_dirs = [d for d in BASE_DIR.iterdir() if d.is_dir()] if BASE_DIR.exists() else []
gtfs_dirs = [d for d in all_dirs if (d / "gtfs.zip").exists()]
gtfs_dirs.sort()
log.info("%d GTFS to process", len(gtfs_dirs))


# ─────────────────────────────────────────────
# Read and compilation
# ─────────────────────────────────────────────
log.info("=== Read and compilation of GTFS ===")

all_stops_data: list[pl.DataFrame] = []
result_extract: list[dict] = []
networks_list: list[dict] = []
n_datasets = len(gtfs_dirs)

for i, dataset_path in enumerate(gtfs_dirs, 1):
    dataset_id = dataset_path.name
    zip_path = dataset_path / "gtfs.zip"

    if not zip_path.exists():
        log.warning("Dataset %s not found, pass.", dataset_id)
        result_extract.append({"dataset_id": dataset_id, "result": "not found"})
        continue

    # Extraction of the *.txt in the zip
    extraction_res = extract_gtfs_zip(zip_path, files=GTFS_FILES_WANTED)

    if not extraction_res["extracted"]:
        log.warning("Dataset %s : failed extraction, pass.", dataset_id)
        result_extract.append({"dataset_id": dataset_id, "result": "failed extract"})
        continue

    # Read the extracted *.txt files
    tables: dict[str, pl.DataFrame] = read_gtfs_dataset(
        dataset_path,
        files_to_keep=[
            "stop_times", "stops", "routes", "trips",
            "agency", "calendar", "calendars", "calendar_dates"
        ],
    )

    # Delete the temporary *.txt files after reading
    for txt_file in dataset_path.glob("*.txt"):
        try:
            txt_file.unlink()
        except Exception:
            pass

    # Alias "calendars" → "calendar"
    if "calendars" in tables and "calendar" not in tables:
        tables["calendar"] = tables.pop("calendars")

    # Verification of the required files
    missing = [f for f in REQUIRED_FILES if f not in tables]
    if missing:
        log.warning(
            "Dataset %s : files missing (%s), pass.", dataset_id, ", ".join(missing)
        )
        result_extract.append({"dataset_id": dataset_id, "result": f"missing {','.join(missing)}"})
        continue

    # Verification of required columns
    invalid = False
    for tbl, cols in REQUIRED_COLS.items():
        missing_cols = [c for c in cols if c not in tables[tbl].columns]
        if missing_cols:
            log.warning(
                "Dataset %s : required columns missing in %s → %s",
                dataset_id, tbl, ", ".join(missing_cols)
            )
            invalid = True
            break
    if invalid:
        result_extract.append({"dataset_id": dataset_id, "result": "invalid schema"})
        continue

    # Id prefixing
    for tbl, cols in ID_COLS.items():
        if tbl not in tables:
            continue
        exprs = []
        for col in cols:
            if col in tables[tbl].columns:
                exprs.append(
                    (pl.lit(dataset_id + "_") + pl.col(col)).alias(col)
                )
        if exprs:
            tables[tbl] = tables[tbl].with_columns(exprs)

    if "stops" in tables and "parent_station" in tables["stops"].columns:
        tables["stops"] = tables["stops"].with_columns(
            pl.when(
                pl.col("parent_station").is_not_null() & (pl.col("parent_station") != "")
            )
            .then(pl.lit(dataset_id + "_") + pl.col("parent_station"))
            .otherwise(pl.col("parent_station"))
            .alias("parent_station")
        )

    # Save the raw tables ──
    for tbl, df in tables.items():
        df_out = df.with_columns([
            pl.lit(dataset_id).alias("dataset_id"),
            pl.lit(str(RUN_DATE)).alias("date_extraction"),
        ])
        out_dir = RAW_DIR / tbl
        out_dir.mkdir(parents=True, exist_ok=True)
        df_out.write_parquet(out_dir / f"{dataset_id}.parquet")

    # Summary of the network
    agency_names = None
    if "agency" in tables and "agency_name" in tables["agency"].columns:
        agency_names = ", ".join(tables["agency"]["agency_name"].drop_nulls().unique().to_list())

    cal_dates_series: list[str] = []
    if "calendar_dates" in tables and "date" in tables["calendar_dates"].columns:
        cal_dates_series = tables["calendar_dates"]["date"].drop_nulls().to_list()

    date_min = date_max = None
    if "calendar" in tables:
        cal = tables["calendar"]
        all_dates = (
            list(
                cal.get_column("start_date").drop_nulls().to_list()
                if "start_date" in cal.columns else []
            )
            + list(
                cal.get_column("end_date").drop_nulls().to_list()
                if "end_date" in cal.columns else []
            )
            + cal_dates_series
        )
        if all_dates:
            date_min = min(all_dates)
            date_max = max(all_dates)
    elif cal_dates_series:
        date_min = min(cal_dates_series)
        date_max = max(cal_dates_series)

    def _in_period(d: date, dmin, dmax) -> bool:
        if dmin is None or dmax is None:
            return True
        try:
            return str(d).replace("-", "") < str(dmin) or str(d).replace("-", "") > str(dmax)
        except Exception:
            return True

    networks_list.append({
        "resources_id": int(dataset_id) if dataset_id.isdigit() else dataset_id,
        "agency_name": agency_names,
        "date_min_observed": date_min,
        "date_max_observed": date_max,
        "hors_periode": _in_period(RUN_DATE, date_min, date_max),
    })

    # Stops × routes table of the dataset
    processed, status = get_stop_data(tables, dataset_id, RUN_DATE, DAY_RUN_DATE)
    result_extract.append({"dataset_id": dataset_id, "result": status})

    if processed is not None:
        all_stops_data.append(processed)
        log.info(
            "Dataset %s (%d/%d) : %d arrêts traités.", dataset_id, i, n_datasets, len(processed)
        )

    del tables
    gc.collect()


# ─────────────────────────────────────────────
# Consolidation of the raw tables
# ─────────────────────────────────────────────
log.info("=== Consolidation of the raw GTFS tables ===")

for tbl in TABLES_GTFS:
    tbl_dir = RAW_DIR / tbl
    fichiers = list(tbl_dir.glob("*.parquet")) if tbl_dir.exists() else []
    if not fichiers:
        log.warning("Table %s : aucun fichier trouvé, on passe.", tbl)
        continue

    out_path = CONSOLIDATED_DIR / f"{tbl}.parquet"
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

        log.info("Table %s consolidated (%d datasets).", tbl, len(fichiers))
        gc.collect()
    except Exception as e:
        log.error("Table %s : failed to consolidate (%s).", tbl, e)
        log.error(traceback.format_exc())


# ─────────────────────────────────────────────
# Persistating raw data for the report
# ─────────────────────────────────────────────
log.info("=== Persisting raw data for the network report ===")

date_str = str(RUN_DATE).replace("-", "")
rapport_dir = DATA_DIR / "transport.data.gouv.fr"

if networks_list:
    networks_df = pl.DataFrame(networks_list)
    networks_df = _flatten_nested_columns(networks_df)
    networks_df.write_csv(rapport_dir / f"{date_str}_networks_raw.csv")
    log.info("networks_df persistated (%d rows).", len(networks_df))
else:
    log.warning("networks_list is empty, nothing to persist for the report.")

if len(gtfs_datasets) > 0:
    gtfs_datasets = _flatten_nested_columns(gtfs_datasets)
    gtfs_datasets.write_csv(rapport_dir / f"{date_str}_gtfs_datasets_raw.csv")
    log.info("gtfs_datasets persistated (%d rows).", len(gtfs_datasets))
else:
    log.warning("gtfs_datasets is empty, nothing to persist for the report.")


# ─────────────────────────────────────────────
# Saving results
# ─────────────────────────────────────────────
log.info("=== Saving results ===")

result_df = (
    pl.DataFrame(result_extract) if result_extract
    else pl.DataFrame({"dataset_id": [], "result": []})
)
date_str = str(RUN_DATE).replace("-", "")
result_df.write_csv(
    DATA_DIR / "transport.data.gouv.fr" / f"{date_str}_resultats_extraction.csv"
)


# All stops compilation
# TODO : get this section in its own .py file

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
    all_stops = all_stops.filter(pl.col("latitude").is_not_null() | pl.col("route_id").is_null())

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

    out_path = DATA_DIR / f"all_stops_data_{date_str}.parquet"
    all_stops.write_parquet(out_path)

    nb_success = sum(1 for r in result_extract if r["result"] == "success")
    log.info("Completed ! %d stops compiled.", len(all_stops))
    log.info("File saved : %s", out_path)
    log.info(
        "Extraction report : %d/%d datasets processed successfully.",
        nb_success, len(result_extract)
    )
