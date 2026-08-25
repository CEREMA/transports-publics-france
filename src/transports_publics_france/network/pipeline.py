"""
Creation of the network report (gtfs_datasets_info)
from raw data persisted by gtfs/pipeline.py.

To link an individual GTFS to the regional aggregate it belongs to,
we rely on the "offers" from the transport.data.gouv.fr API.

Requires running gtfs/pipeline.py first, for the given run_date (see config.py),
the following files must exist :
    - {date}_networks_raw.parquet
    - {date}_gtfs_datasets_raw.parquet

# TODO : certainement qu'écrire des fichiers en dur n'est pas très package-compatible
"""

import logging
import polars as pl
from transports_publics_france.config import RUN_DATE, DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATE_STR = str(RUN_DATE).replace("-", "")
out_dir = DATA_DIR / "transport.data.gouv.fr"

networks_path = out_dir / f"{DATE_STR}_networks_raw.parquet"
gtfs_datasets_path = out_dir / f"{DATE_STR}_gtfs_datasets_raw.parquet"

if not networks_path.exists():
    raise FileNotFoundError(
        f"{networks_path} not found : run gtfs/pipeline.py first for {RUN_DATE}."
    )

networks_df = pl.read_parquet(networks_path)
log.info("networks_df loaded (%d rows).", len(networks_df))

if gtfs_datasets_path.exists():
    gtfs_datasets = pl.read_parquet(gtfs_datasets_path)
    log.info("gtfs_datasets loaded (%d rows).", len(gtfs_datasets))
else:
    log.warning("%s not found, report limited to observed data.", gtfs_datasets_path)
    gtfs_datasets = pl.DataFrame()

if len(gtfs_datasets) > 0 and "resources_id" in gtfs_datasets.columns:
    gtfs_datasets_info = gtfs_datasets.join(networks_df, on="resources_id", how="left")
else:
    gtfs_datasets_info = networks_df


# Connection individual GTFS <-> regional aggregate

# Geographic rank : a GTFS can't have a geographic coverage larger than the aggregate
GEO_RANK = {"commune": 0, "epci": 1, "departement": 2, "region": 3, "pays": 4}


def _offer_id_set(offer_ids: list[int] | None) -> set[int]:
    return set(offer_ids) if offer_ids else set()


if "is_agregat" in gtfs_datasets_info.columns and "offer_ids" in gtfs_datasets_info.columns:
    agregats_info = [
        {
            "resources_id": row["resources_id"],
            "page_url": row.get("page_url"),
            "offer_ids": _offer_id_set(row["offer_ids"]),
            "geo_rank": GEO_RANK.get(row.get("categorie_geo"), 99),
        }
        for row in gtfs_datasets_info.filter(pl.col("is_agregat")).iter_rows(named=True)
        if _offer_id_set(row["offer_ids"])
    ]
    log.info(
        "%d regional aggregate(s) identified for matching (via offers API).",
        len(agregats_info),
    )


    def _find_agregat(
            is_agregat: bool | None, offer_ids: list[int] | None, categorie_geo: str | None
    ) -> tuple[int | None, str | None]:
        """
        Returns (resources_id, page_url) of the aggregate, or (None, None).
        """
        if is_agregat:
            return (None, None)  # an aggregate cannot be linked to itself

        offers = _offer_id_set(offer_ids)
        if not offers:
            return (None, None)

        geo_rank = GEO_RANK.get(categorie_geo, 99)

        for ag in agregats_info:
            # the GTFS cannot have a geographic coverage larger than the aggregate
            if geo_rank > ag["geo_rank"]:
                continue

            if offers & ag["offer_ids"]:
                return (ag["resources_id"], ag["page_url"])

        return (None, None)


    matches = [
        _find_agregat(is_ag, offer_ids, categorie_geo)
        for is_ag, offer_ids, categorie_geo in zip(
            gtfs_datasets_info["is_agregat"].to_list(),
            gtfs_datasets_info["offer_ids"].to_list(),
            gtfs_datasets_info["categorie_geo"].to_list(),
        )
    ]
    gtfs_datasets_info = gtfs_datasets_info.with_columns([
        pl.Series("agregat_resources_id", [m[0] for m in matches]),
    ])
    nb_matches = sum(1 for m in matches if m[0] is not None)
    log.info("%d individual GTFS(s) connected to a regional aggregate.", nb_matches)
else:
    log.warning("Columns is_agregat/offer_ids missing, regional aggregate matching ignored.")


# Save

# 1) delete columns
cols_a_suppr = [
    "slug", "id", "resources_type", "resources_updated", "start_date", "end_date"
]
gtfs_datasets_info = gtfs_datasets_info.drop(cols_a_suppr, strict=False)

# 2) rename columns
RENAME_MAP = {
    c: "resource_" + c.removeprefix("resources_")
    for c in gtfs_datasets_info.columns
    if c.startswith("resources_")
}
RENAME_MAP.update({
    "datagouv_id": "dataset_id",
    "resources_id": "resource_transport_id",
    "title": "dataset_title",
    "date_min_observed": "start_date",
    "date_max_observed": "end_date",
})
RENAME_MAP = {k: v for k, v in RENAME_MAP.items() if k in gtfs_datasets_info.columns}
gtfs_datasets_info = gtfs_datasets_info.rename(RENAME_MAP)

if "hors_periode" in gtfs_datasets_info.columns:
    gtfs_datasets_info = gtfs_datasets_info.with_columns(
        pl.col("hors_periode").not_().alias("service_dates_valid")
    ).drop("hors_periode")

# reformat dates (YYYYMMDD -> JJ/MM/YYYY)
for c in ("start_date", "end_date"):
    gtfs_datasets_info = gtfs_datasets_info.with_columns(
        pl.col(c).str.strptime(pl.Date, "%Y%m%d", strict=False).dt.strftime("%d/%m/%Y").alias(c)
    )

# 3) reorganization : ids, then titles, then urls, for the first columns
COLS_ID = ["dataset_id", "resource_transport_id", "resource_datagouv_id"]
COLS_TITLE = ["dataset_title", "resource_title"]
COLS_URL = ["page_url", "resource_url", "resource_original_url", "resource_page_url"]

first_cols = [
    c for c in COLS_ID + COLS_TITLE + COLS_URL if c in gtfs_datasets_info.columns
]
other_cols = [c for c in gtfs_datasets_info.columns if c not in first_cols]
gtfs_datasets_info = gtfs_datasets_info.select(first_cols + other_cols)

# TODO : normalement tout cela devrait être fait avant dans le pipeline

# Effective save
out_path = out_dir / f"{DATE_STR}_gtfs_datasets_info.parquet"
gtfs_datasets_info.write_parquet(out_path)
log.info("Network report written : %s (%d rows).", out_path, len(gtfs_datasets_info))
log.info("Columns in the report : %s", gtfs_datasets_info.columns)


# Conversion of the nested columns for CSV export
for col, dtype in zip(gtfs_datasets_info.columns, gtfs_datasets_info.dtypes):
    if isinstance(dtype, pl.List):
        inner_dtype = dtype.inner

        if isinstance(inner_dtype, pl.Struct):
            # List -> JSON
            gtfs_datasets_info = gtfs_datasets_info.with_columns(
                pl.col(col)
                .list.eval(pl.element().struct.json_encode())
                .list.join(",")
                .alias(col)
            )
        else:
            # List -> String then concatenate
            gtfs_datasets_info = gtfs_datasets_info.with_columns(
                pl.col(col)
                .list.eval(pl.element().cast(pl.String))
                .list.join(",")
                .alias(col)
            )

    elif isinstance(dtype, pl.Struct):
        # Simple structure -> JSON
        gtfs_datasets_info = gtfs_datasets_info.with_columns(
            pl.col(col).struct.json_encode().alias(col)
        )

csv_path = out_dir / f"{DATE_STR}_gtfs_datasets_info.csv"
gtfs_datasets_info.write_csv(csv_path)
log.info("Network report (CSV) written : %s.", csv_path)
