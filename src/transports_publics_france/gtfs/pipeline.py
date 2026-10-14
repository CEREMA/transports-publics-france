"""
Pipeline for downloading and processing the GTFS data

Public function : run_gtfs_pipeline()
Can also be run as a script : python -m transports_publics_france.gtfs.pipeline

# TODO config must be removed to be package-compatible : must become parameters
"""

import gc
import logging
from pathlib import Path
import polars as pl

from transports_publics_france.config import (
    DATA_DIR, BASE_DIR, RAW_DIR, REDOWNLOAD, RUN_DATE,
    DAY_RUN_DATE, UNIFIED_DIR, TABLES_GTFS, GTFS_FILES_WANTED
)

from transports_publics_france.gtfs.io import load_gtfs_tables
from transports_publics_france.gtfs.api import get_gtfs_datasets_info
from transports_publics_france.gtfs.download_gtfs import download_resources
from transports_publics_france.gtfs.stop_data import get_stop_data
from transports_publics_france.gtfs.validation import validate_gtfs_tables
from transports_publics_france.gtfs.gtfs_processing import prefix_ids, summarize_network
from transports_publics_france.gtfs.unify import compile_all_stops, unify_gtfs_tables
from transports_publics_france.utils import _flatten_nested_columns

log = logging.getLogger(__name__)

# Tables read from each GTFS ("calendars" is a frequent typo for "calendar")
TABLES_TO_READ = [*TABLES_GTFS, "calendars"]


def run_gtfs_pipeline() -> None:
    """Download (optional), read, consolidate and compile the GTFS of France."""
    gtfs_datasets = _fetch_metadata()
    gtfs_dirs = _download_and_list_gtfs(gtfs_datasets)

    log.info("=== Read and compilation of GTFS ===")
    result_extract, networks_list, all_stops_data = _process_all_datasets(gtfs_dirs)

    unify_gtfs_tables(RAW_DIR, UNIFIED_DIR)

    _persist_report_data(networks_list, gtfs_datasets)
    _save_results(result_extract)

    all_stops = compile_all_stops(all_stops_data)
    if len(all_stops) > 0:
        date_str = str(RUN_DATE).replace("-", "")
        out_path = DATA_DIR / f"all_stops_data_{date_str}.parquet"
        all_stops.write_parquet(out_path)

        nb_success = sum(1 for r in result_extract if r["result"] == "success")
        log.info("Completed ! %d stops compiled.", len(all_stops))
        log.info("File saved : %s", out_path)
        log.info(
            "Extraction report : %d/%d datasets processed successfully.",
            nb_success, len(result_extract)
        )


# ─────────────────────────────────────────────
# Metadata recuperation, download
# ─────────────────────────────────────────────
def _fetch_metadata() -> pl.DataFrame:
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

    return gtfs_datasets


def _download_and_list_gtfs(gtfs_datasets: pl.DataFrame) -> list[Path]:
    log.info("=== Download / detection of the already downloaded GTFS ===")

    if REDOWNLOAD and len(gtfs_datasets) > 0:
        download_resources(gtfs_datasets, redownload=REDOWNLOAD, timeout=15)

    all_dirs = [d for d in BASE_DIR.iterdir() if d.is_dir()] if BASE_DIR.exists() else []
    gtfs_dirs = [d for d in all_dirs if (d / "gtfs.zip").exists()]
    gtfs_dirs.sort()
    log.info("%d GTFS to process", len(gtfs_dirs))
    return gtfs_dirs


# ─────────────────────────────────────────────
# Read and compilation
# ─────────────────────────────────────────────
def _process_all_datasets(gtfs_dirs: list[Path]) -> (
        tuple[list[dict], list[dict], list[pl.DataFrame]]
    ):
    """Returns (result_extract, networks_list, all_stops_data)."""
    result_extract: list[dict] = []
    networks_list: list[dict] = []
    all_stops_data: list[pl.DataFrame] = []
    n_datasets = len(gtfs_dirs)

    for i, dataset_path in enumerate(gtfs_dirs, 1):
        status, stops, network = _process_dataset(dataset_path)

        result_extract.append({"dataset_id": dataset_path.name, "result": status})
        if network:
            networks_list.append(network)
        if stops is not None:
            all_stops_data.append(stops)
            log.info(
                "Dataset %s (%d/%d) : %d arrêts traités.",
                dataset_path.name, i, n_datasets, len(stops)
            )
        gc.collect()

    return result_extract, networks_list, all_stops_data


def _process_dataset(dataset_path: Path) -> tuple[str, pl.DataFrame | None, dict | None]:
    """Read, validate and process the GTFS of one dataset directory.

    Returns (status, stops, network) : stops and network are None when
    the dataset could not be processed that far.
    """
    dataset_id = dataset_path.name

    tables = load_gtfs_tables(
        dataset_path, files_wanted=GTFS_FILES_WANTED, files_to_keep=TABLES_TO_READ
    )
    if tables is None:
        log.warning("Dataset %s : failed extraction, pass.", dataset_id)
        return "failed extract", None, None

    error = validate_gtfs_tables(tables, dataset_id)
    if error:
        return error, None, None

    tables = prefix_ids(tables, dataset_id)
    _save_raw_tables(tables, dataset_id)
    network = summarize_network(tables, dataset_id, RUN_DATE)

    # Stops × routes table of the dataset
    stops, status = get_stop_data(tables, dataset_id, RUN_DATE, DAY_RUN_DATE)
    return status, stops, network


def _save_raw_tables(tables: dict[str, pl.DataFrame], dataset_id: str) -> None:
    for tbl, df in tables.items():
        df_out = df.with_columns([
            pl.lit(dataset_id).alias("dataset_id"),
            pl.lit(str(RUN_DATE)).alias("date_extraction"),
        ])
        out_dir = RAW_DIR / tbl
        out_dir.mkdir(parents=True, exist_ok=True)
        df_out.write_parquet(out_dir / f"{dataset_id}.parquet")


# ─────────────────────────────────────────────
# Persisting raw data for the report, saving results
# ─────────────────────────────────────────────
def _persist_report_data(networks_list: list[dict], gtfs_datasets: pl.DataFrame) -> None:
    log.info("=== Persisting raw data for the network report ===")

    date_str = str(RUN_DATE).replace("-", "")

    if networks_list:
        networks_df = pl.DataFrame(networks_list)
        networks_df = _flatten_nested_columns(networks_df)
        networks_df.write_csv(DATA_DIR / f"{date_str}_networks_raw.csv")
        log.info("networks_df persistated (%d rows).", len(networks_df))
    else:
        log.warning("networks_list is empty, nothing to persist for the report.")

    if len(gtfs_datasets) > 0:
        gtfs_datasets = _flatten_nested_columns(gtfs_datasets)
        gtfs_datasets.write_csv(DATA_DIR / f"{date_str}_gtfs_datasets_raw.csv")
        log.info("gtfs_datasets persistated (%d rows).", len(gtfs_datasets))
    else:
        log.warning("gtfs_datasets is empty, nothing to persist for the report.")


def _save_results(result_extract: list[dict]) -> None:
    log.info("=== Saving results ===")

    result_df = (
        pl.DataFrame(result_extract) if result_extract
        else pl.DataFrame({"dataset_id": [], "result": []})
    )
    date_str = str(RUN_DATE).replace("-", "")
    result_df.write_csv(DATA_DIR / f"{date_str}_resultats_extraction.csv")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run_gtfs_pipeline()
