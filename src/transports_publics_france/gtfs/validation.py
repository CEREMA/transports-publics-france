"""
Validation of the GTFS tables read from a dataset :
- validate_gtfs_tables(tables, dataset_id)
"""

import logging
import polars as pl

from transports_publics_france.config import REQUIRED_FILES, REQUIRED_COLS

log = logging.getLogger(__name__)


def validate_gtfs_tables(
    tables: dict[str, pl.DataFrame],
    dataset_id: str = "",
) -> str | None:
    """Check that the required GTFS files and columns are present.

    Returns None if the tables are valid, otherwise the status describing
    the problem ("missing stops,trips" or "invalid schema").
    `dataset_id` is only used to make the log messages explicit.
    """
    missing = [f for f in REQUIRED_FILES if f not in tables]
    if missing:
        log.warning(
            "Dataset %s : files missing (%s), pass.", dataset_id, ", ".join(missing)
        )
        return f"missing {','.join(missing)}"

    for tbl, cols in REQUIRED_COLS.items():
        missing_cols = [c for c in cols if c not in tables[tbl].columns]
        if missing_cols:
            log.warning(
                "Dataset %s : required columns missing in %s → %s",
                dataset_id, tbl, ", ".join(missing_cols)
            )
            return "invalid schema"

    return None
