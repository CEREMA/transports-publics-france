"""
Validation of the GTFS tables read from a dataset :
- validate_gtfs_tables(tables, dataset_id)
"""

import polars as pl
from loguru import logger
from transports_publics_france.config import REQUIRED_FILES, REQUIRED_COLS


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
        logger.warning(
            f"Dataset {dataset_id} : files missing ({", ".join(missing)}), pass."
        )
        return f"missing {','.join(missing)}"

    for tbl, cols in REQUIRED_COLS.items():
        missing_cols = [c for c in cols if c not in tables[tbl].columns]
        if missing_cols:
            logger.warning(
                f"Dataset {dataset_id} : required columns missing in {tbl} → {", ".join(missing_cols)}"
            )
            return "invalid schema"

    return None
