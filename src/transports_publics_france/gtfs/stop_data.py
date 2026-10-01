"""
Construction de la table des arrêts × lignes pour un dataset GTFS.
"""

import logging
import traceback
from datetime import date
import polars as pl

from transports_publics_france.gtfs.clean_stopnames import reduce_stop_name
from transports_publics_france.gtfs.gtfs_processing import (
    get_active_services, get_parent_station, map_route_type
)

from transports_publics_france.config import MODE_PRIORITY


log = logging.getLogger(__name__)

# Statuts retournés (repris tels quels dans result_extract)
STATUS_SUCCESS = "success"
STATUS_NO_STOPS = "no stops"
STATUS_NO_SERVICES = "no services"
STATUS_ERROR = "processing error"


def get_stop_data(
    tables: dict[str, pl.DataFrame],
    dataset_id: str,
    run_date: date,
    day_run_date: str,
) -> tuple[pl.DataFrame | None, str]:
    """
    Create the parent_station × route table of a GTFS dataset.

    Parameters
    ----------
    tables : dict[str, pl.DataFrame]
        Already read and validated GTFS tables. The ids are prefixed
        (stops, routes, trips, stop_times, agency, calendar, calendar_dates).
    dataset_id : str
        ID of the dataset (a column in the final report).
    run_date : date
        Date of the execution (active services + `date_extraction` column).
    day_run_date : str
        Day of the week of `run_date` (format expected by `get_active_services`).

    Returns
    -------
    (df, status)
        df : treated dataFrame, or None if nothing to return.
        status : "success", "no stops", "no services" or "processing error".
    """
    try:
        stops_df = tables["stops"].filter(pl.col("stop_id").is_not_null()).unique()
        routes_df = tables["routes"].filter(pl.col("route_id").is_not_null()).unique()
        trips_df = tables["trips"].filter(
            pl.col("trip_id").is_not_null() | pl.col("route_id").is_not_null()
        ).unique()
        stop_times_df = tables["stop_times"].filter(pl.col("trip_id").is_not_null()).unique()

        if len(stops_df) == 0:
            log.warning("Dataset %s : no stops, pass.", dataset_id)
            return None, STATUS_NO_STOPS

        active_services = get_active_services(
            tables.get("calendar"), tables.get("calendar_dates"), run_date, day_run_date
        )
        if len(active_services) == 0:
            log.warning("Dataset %s : no active services today, pass.", dataset_id)
            return None, STATUS_NO_SERVICES

        # Only active services
        trips_df = trips_df.filter(pl.col("service_id").is_in(active_services.to_list()))
        routes_df = routes_df.filter(pl.col("route_id").is_in(trips_df["route_id"].to_list()))

        # Missing columns / default values
        stops_df = _fix_stops(stops_df)
        routes_df = _fix_routes(routes_df)
        stop_times_df = _fix_stop_times(stop_times_df)
        agency_df = _fix_agency(tables.get("agency", pl.DataFrame()))
        if "agency_id" not in routes_df.columns:
            routes_df = routes_df.with_columns(pl.lit(agency_df["agency_id"][0]).alias("agency_id"))

        # Join
        stops_full = _build_stops_full(stops_df)
        joined = _join_all(stops_full, stop_times_df, trips_df, routes_df, agency_df)
        joined = _flag_on_demand(joined)

        # 1 row per parent_station × route
        arret_route = (
            joined.filter(pl.col("trip_id").is_not_null())
            .group_by(["parent_station", "route_id"])
            .first()
        )

        arret_route = _add_peak_frequency(arret_route, joined)
        arret_route = _add_route_type_and_priority(arret_route)
        arret_route = _add_reduced_stop_name(arret_route)

        stations_routes = _select_principal_lines(arret_route)
        processed = _format_output(stations_routes, dataset_id, run_date)

        return processed, STATUS_SUCCESS

    except Exception as e:
        log.warning("Dataset %s : erreur de traitement (%s), on passe.", dataset_id, e)
        log.warning(traceback.format_exc())
        return None, STATUS_ERROR


# ─────────────────────────────────────────────
# Missing columns correction
# ─────────────────────────────────────────────
def _fix_stops(stops_df: pl.DataFrame) -> pl.DataFrame:
    if "location_type" not in stops_df.columns:
        stops_df = stops_df.with_columns(pl.lit("0").alias("location_type"))
    stops_df = stops_df.with_columns(
        pl.when(pl.col("location_type") == "").then(pl.lit("0"))
        .otherwise(pl.col("location_type")).alias("location_type")
    )
    if "parent_station" not in stops_df.columns:
        stops_df = stops_df.with_columns(pl.lit("").alias("parent_station"))
    return stops_df


def _fix_routes(routes_df: pl.DataFrame) -> pl.DataFrame:
    if "route_short_name" not in routes_df.columns:
        routes_df = routes_df.with_columns(pl.col("route_long_name").alias("route_short_name"))
    elif "route_long_name" not in routes_df.columns:
        routes_df = routes_df.with_columns(pl.col("route_short_name").alias("route_long_name"))
    # Si route_short_name est vide, on prend route_long_name
    return routes_df.with_columns(
        pl.coalesce(["route_short_name", "route_long_name"]).alias("route_short_name")
    )


def _fix_stop_times(stop_times_df: pl.DataFrame) -> pl.DataFrame:
    for col in ("pickup_type", "drop_off_type"):
        if col not in stop_times_df.columns:
            stop_times_df = stop_times_df.with_columns(pl.lit("0").alias(col))
    return stop_times_df


def _fix_agency(agency_df: pl.DataFrame) -> pl.DataFrame:
    if len(agency_df) == 0:
        return pl.DataFrame({"agency_id": [""], "agency_name": [None], "agency_lang": [None]})
    if "agency_id" not in agency_df.columns:
        agency_df = agency_df.with_columns(pl.lit("").alias("agency_id"))
    if "agency_lang" not in agency_df.columns:
        agency_df = agency_df.with_columns(pl.lit(None).cast(pl.Utf8).alias("agency_lang"))
    return agency_df


# ─────────────────────────────────────────────
# Joins
# ─────────────────────────────────────────────
def _build_stops_full(stops_df: pl.DataFrame) -> pl.DataFrame:
    """Associe chaque arrêt à sa station parent (nom + coordonnées de la parent si dispo)."""
    stations_df = get_parent_station(stops_df).select(["stop_id", "parent_station"])
    stops_coords = stops_df.select(["stop_id", "stop_name", "stop_lat", "stop_lon"])
    stops_full = stations_df.join(
        stops_coords.rename({"stop_id": "parent_station"}),
        on="parent_station",
        how="left",
    )
    for col in ["stop_name", "stop_lat", "stop_lon"]:
        if f"{col}_parent" in stops_full.columns:
            stops_full = stops_full.with_columns(
                pl.coalesce([f"{col}_parent", col]).alias(col)
            ).drop(f"{col}_parent")
    return stops_full


def _join_all(
    stops_full: pl.DataFrame,
    stop_times_df: pl.DataFrame,
    trips_df: pl.DataFrame,
    routes_df: pl.DataFrame,
    agency_df: pl.DataFrame,
) -> pl.DataFrame:
    """stops × stop_times × trips × routes × agency."""
    routes_sel = routes_df.select(
        [c for c in ["route_id", "route_type", "route_short_name",
                     "route_long_name", "agency_id"] if c in routes_df.columns]
    ).unique()
    routes_sel = routes_sel.with_columns(
        pl.when(pl.col("route_short_name") == "")
        .then(pl.col("route_long_name"))
        .otherwise(pl.col("route_short_name"))
        .alias("route_short_name")
    )

    trips_sel = trips_df.select(["route_id", "trip_id"]).unique()

    st_sel = stop_times_df.select(
        [c for c in ["trip_id", "stop_id", "stop_sequence",
                     "arrival_time", "pickup_type", "drop_off_type"]
         if c in stop_times_df.columns]
    ).unique()
    st_sel = st_sel.with_columns([
        pl.col("pickup_type").fill_null("0"),
        pl.col("drop_off_type").fill_null("0"),
    ])

    agency_sel = agency_df.select(
        [c for c in ["agency_id", "agency_name", "agency_lang"] if c in agency_df.columns]
    ).unique()

    j1 = stops_full.join(st_sel, on="stop_id", how="inner")
    j2 = j1.join(trips_sel, on="trip_id", how="inner")
    return (
        routes_sel.join(agency_sel, on="agency_id", how="left")
        .join(j2, on="route_id", how="inner")
    )


# ─────────────────────────────────────────────
# More information added
# ─────────────────────────────────────────────
def _flag_on_demand(joined: pl.DataFrame) -> pl.DataFrame:
    """Transport à la demande : ligne_ad (totale) / ligne_ad_partiel."""
    tad = joined.group_by("route_id").agg([
        (pl.col("drop_off_type") == "2").all().alias("ligne_ad"),
        (pl.col("drop_off_type") == "2").any().alias("ligne_ad_partiel"),
    ])
    joined = joined.join(tad, on="route_id", how="left")
    return joined.with_columns(
        pl.when(pl.col("ligne_ad")).then(pl.lit(False))
        .otherwise(pl.col("ligne_ad_partiel")).alias("ligne_ad_partiel")
    )


def _extract_hour(s: pl.Series) -> pl.Series:
    """Extrait l'heure d'une colonne arrival_time (HH:MM:SS) sous forme d'Int32."""
    return s.str.split(":").list.get(0).cast(pl.Int32, strict=False)


def _add_peak_frequency(arret_route: pl.DataFrame, joined: pl.DataFrame) -> pl.DataFrame:
    """Fréquence maximale en heure de pointe du matin (7h-9h) -> freq_ppm_max."""
    if "arrival_time" not in joined.columns:
        return arret_route.with_columns(pl.lit(0).alias("freq_ppm_max"))

    ppm_df = joined.filter(
        (pl.col("pickup_type") == "0") | (pl.col("drop_off_type") == "0")
    )
    ppm_df = ppm_df.with_columns(
        _extract_hour(pl.col("arrival_time")).alias("_hour")
    ).filter(pl.col("_hour").is_between(7, 8))

    if len(ppm_df) == 0:
        return arret_route.with_columns(pl.lit(0).alias("freq_ppm_max"))

    freq_ppm = (
        ppm_df.group_by(
            ["stop_id", "parent_station", "route_id", "route_type", "stop_sequence"]
        )
        .agg(pl.len().alias("N"))
        .sort("N", descending=True)
        .group_by(["parent_station", "route_id", "route_type"])
        .first()
        .select(["parent_station", "route_id", "route_type", "N"])
        .rename({"N": "freq_ppm_max"})
    )
    return arret_route.join(
        freq_ppm, on=["parent_station", "route_id", "route_type"], how="left"
    )


def _add_route_type_and_priority(arret_route: pl.DataFrame) -> pl.DataFrame:
    """Libellé du mode (+ suffixe TAD) et rang de priorité des modes."""
    arret_route = arret_route.with_columns(
        pl.col("route_type").map_elements(map_route_type, return_dtype=pl.Utf8)
        .alias("route_type")
    )
    arret_route = arret_route.with_columns(
        pl.when(pl.col("ligne_ad"))
        .then(pl.col("route_type") + pl.lit(" TAD"))
        .otherwise(pl.col("route_type"))
        .alias("route_type")
    )
    return arret_route.with_columns(
        pl.col("route_type").replace_strict(MODE_PRIORITY, default=999).alias("rang_route_type")
    )


def _add_reduced_stop_name(arret_route: pl.DataFrame) -> pl.DataFrame:
    return arret_route.with_columns(
        pl.col("stop_name").map_elements(
            lambda x: reduce_stop_name(x) if x else x, return_dtype=pl.Utf8
        ).alias("stop_name_red")
    )


def _select_principal_lines(arret_route: pl.DataFrame) -> pl.DataFrame:
    """Ne garde que le mode prioritaire de chaque ligne (ligne_princ == 1)."""
    arret_route = arret_route.sort("rang_route_type")
    ligne_princ = (
        arret_route.select(["route_short_name", "rang_route_type"])
        .unique()
        .with_columns(
            pl.col("rang_route_type").rank(method="dense")
            .over(["route_short_name"]).alias("ligne_princ")
        )
    )
    arret_route = arret_route.join(
        ligne_princ, on=["route_short_name", "rang_route_type"], how="left"
    )
    arret_route_nom_red = (
        arret_route.filter(pl.col("ligne_princ") == 1)
        .group_by(["route_short_name", "stop_name_red", "parent_station"])
        .first()
    )

    keep_cols = [c for c in [
        "parent_station", "stop_id", "stop_name", "stop_name_red",
        "stop_lat", "stop_lon", "route_id", "route_type",
        "route_short_name", "route_long_name",
        "agency_id", "agency_name", "agency_lang",
        "freq_ppm_max", "ligne_ad", "ligne_ad_partiel",
    ] if c in arret_route_nom_red.columns]

    return (
        arret_route_nom_red.select(keep_cols)
        .drop("stop_id").rename({"parent_station": "stop_id"})
    )


# ─────────────────────────────────────────────
# Final format
# ─────────────────────────────────────────────
def _format_output(
    stations_routes: pl.DataFrame, dataset_id: str, run_date: date
) -> pl.DataFrame:
    processed = stations_routes.with_columns([
        pl.lit(str(run_date)).alias("date_extraction"),
        pl.lit(dataset_id).alias("dataset_id"),
        pl.col("stop_lat").cast(pl.Float64, strict=False).alias("latitude"),
        pl.col("stop_lon").cast(pl.Float64, strict=False).alias("longitude"),
    ])
    if "stop_lat" in processed.columns:
        processed = processed.drop(["stop_lat", "stop_lon"])

    # stop_id_red et route_id_red
    processed = processed.with_columns([
        pl.col("stop_id").str.extract(r"(\w+)$")
        .fill_null(pl.col("stop_name_red")).alias("stop_id_red"),
        pl.col("route_id").str.extract(r"(\w+)$")
        .fill_null(pl.col("route_short_name")).alias("route_id_red"),
    ])

    # Titlecase
    for col in ["stop_name", "route_long_name"]:
        if col in processed.columns:
            processed = processed.with_columns(
                pl.col(col).str.to_titlecase().str.strip_chars().alias(col)
            )

    processed = processed.filter(
        pl.col("latitude").is_not_null() | pl.col("route_id").is_not_null()
    )
    if "freq_ppm_max" in processed.columns:
        processed = processed.with_columns(pl.col("freq_ppm_max").fill_null(0))

    return processed
