"""
Business logic functions for GTFS data processing :
- get_active_services(calendar, calendar_dates, run_date, day_run_date)
- get_parent_station()
- map_route_type(route_type)
"""

import logging
from datetime import date
import polars as pl

from transports_publics_france.config import ROUTE_TYPE_MAP

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
        pl.when(
            pl.col("parent_station").is_null() | (pl.col("parent_station") == "")
        )
        .then(pl.col("stop_id"))
        .otherwise(pl.col("parent_station"))
        .alias("parent_station")
    )


def map_route_type(rt: str | None) -> str:
    """Map a GTFS route_type to a category (bus, tramway, metro, train, others)."""
    if rt is None:
        return "non renseigné"
    return ROUTE_TYPE_MAP.get(str(rt).strip(), "non renseigné")
