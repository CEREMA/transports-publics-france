"""
Utility functions useful everywhere
"""

import importlib.metadata
import polars as pl


def _flatten_nested_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Convert List / Struct cols to String for CSV export."""
    for col, dtype in df.schema.items():
        if isinstance(dtype, pl.List):
            if isinstance(dtype.inner, pl.Struct):
                # List[Struct] -> JSON of each element, separated by ","
                expr = (
                    pl.col(col)
                    .list.eval(pl.element().struct.json_encode())
                    .list.join(",")
                )
            else:
                # List[scalaire] -> String, separated by ","
                expr = (
                    pl.col(col).list.eval(pl.element().cast(pl.String)).list.join(",")
                )
            df = df.with_columns(expr.alias(col))
        elif isinstance(dtype, pl.Struct):
            # Struct -> JSON
            df = df.with_columns(pl.col(col).struct.json_encode().alias(col))
    return df


def get_package_version() -> str:
    """
    Get the version of transports-publics-france.
    :return: Version in SemVer format (major.minor.patch)
    """
    return importlib.metadata.version("transports-publics-france")
