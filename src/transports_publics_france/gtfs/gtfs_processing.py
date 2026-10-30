"""
Business logic functions for GTFS data processing :
- get_active_services(calendar, calendar_dates, run_date, day_run_date)
- get_parent_station()
- map_route_type(route_type)
- prefix_ids(tables, dataset_id)
- summarize_network(tables, dataset_id, run_date)
"""

import logging
from datetime import date
import polars as pl

from transports_publics_france.config import ROUTE_TYPE_MAP, ID_COLS

log = logging.getLogger(__name__)


def get_active_services(
    calendar: pl.DataFrame | None,
    calendar_dates: pl.DataFrame | None,
    run_date: date,
    day_run_date: str,
) -> pl.Series:
    """Return the active service_id for a given date."""
    active = pl.Series("service_id", [], dtype=pl.Utf8)
    date_str = str(run_date).replace("-", "")

    if calendar is not None and len(calendar) > 0:
        if day_run_date in calendar.columns:
            mask = (
                (calendar["start_date"] <= date_str)
                & (calendar["end_date"] >= date_str)
                & (calendar[day_run_date] == "1")
            )
            active = calendar.filter(mask)["service_id"]

    if calendar_dates is not None and len(calendar_dates) > 0:
        today_cd = calendar_dates.filter(pl.col("date") == date_str)
        if len(today_cd) > 0:
            added = today_cd.filter(pl.col("exception_type") == "1")["service_id"]
            removed = today_cd.filter(pl.col("exception_type") == "2")["service_id"]
            active = pl.concat([active, added]).unique()
            active = active.filter(~active.is_in(removed.to_list()))

    return active.unique()


def get_parent_station(stops: pl.DataFrame) -> pl.DataFrame:
    """Associate each stop_id with its parent_station (or itself if none).

    Replicates territoRy / gtfstools::get_parent_station() (one level).
    """
    if "parent_station" not in stops.columns:
        return stops.with_columns(pl.col("stop_id").alias("parent_station"))
    return stops.with_columns(
        pl.when(pl.col("parent_station").is_null() | (pl.col("parent_station") == ""))
        .then(pl.col("stop_id"))
        .otherwise(pl.col("parent_station"))
        .alias("parent_station")
    )


def map_route_type(rt: str | None) -> str:
    """Map a GTFS route_type to a category (bus, tramway, metro, train, others)."""
    if rt is None:
        return "non renseigné"
    return ROUTE_TYPE_MAP.get(str(rt).strip(), "non renseigné")


def prefix_ids(
    tables: dict[str, pl.DataFrame], dataset_id: str
) -> dict[str, pl.DataFrame]:
    """Prefix the id columns with the dataset_id, so that ids are unique across datasets.

    Returns a new dict, the input dict is left untouched.
    """
    prefixed = dict(tables)

    for tbl, cols in ID_COLS.items():
        if tbl not in prefixed:
            continue
        exprs = [
            (pl.lit(dataset_id + "_") + pl.col(col)).alias(col)
            for col in cols
            if col in prefixed[tbl].columns
        ]
        if exprs:
            prefixed[tbl] = prefixed[tbl].with_columns(exprs)

    if "stops" in prefixed and "parent_station" in prefixed["stops"].columns:
        prefixed["stops"] = prefixed["stops"].with_columns(
            pl.when(
                pl.col("parent_station").is_not_null()
                & (pl.col("parent_station") != "")
            )
            .then(pl.lit(dataset_id + "_") + pl.col("parent_station"))
            .otherwise(pl.col("parent_station"))
            .alias("parent_station")
        )

    return prefixed


def _is_out_of_period(d: date, dmin, dmax) -> bool:
    """True if d is outside [dmin, dmax] (or if the period is unknown)."""
    if dmin is None or dmax is None:
        return True
    try:
        return str(d).replace("-", "") < str(dmin) or str(d).replace("-", "") > str(
            dmax
        )
    except Exception:
        return True


def summarize_network(
    tables: dict[str, pl.DataFrame],
    dataset_id: str,
    run_date: date,
) -> dict:
    """Summary of a GTFS dataset : agencies, observed dates, out-of-period flag."""
    agency_names = None
    if "agency" in tables and "agency_name" in tables["agency"].columns:
        agency_names = ", ".join(
            tables["agency"]["agency_name"].drop_nulls().unique().to_list()
        )

    cal_dates_series: list[str] = []
    if "calendar_dates" in tables and "date" in tables["calendar_dates"].columns:
        cal_dates_series = tables["calendar_dates"]["date"].drop_nulls().to_list()

    date_min = date_max = None
    if "calendar" in tables:
        cal = tables["calendar"]
        all_dates = (
            list(
                cal.get_column("start_date").drop_nulls().to_list()
                if "start_date" in cal.columns
                else []
            )
            + list(
                cal.get_column("end_date").drop_nulls().to_list()
                if "end_date" in cal.columns
                else []
            )
            + cal_dates_series
        )
        if all_dates:
            date_min = min(all_dates)
            date_max = max(all_dates)
    elif cal_dates_series:
        date_min = min(cal_dates_series)
        date_max = max(cal_dates_series)

    return {
        "resources_id": int(dataset_id) if dataset_id.isdigit() else dataset_id,
        "agency_name": agency_names,
        "date_min_observed": date_min,
        "date_max_observed": date_max,
        "hors_periode": _is_out_of_period(run_date, date_min, date_max),
    }
