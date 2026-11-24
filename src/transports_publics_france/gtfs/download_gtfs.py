"""
Utils for downloading GTFS resources from transport.data.gouv.fr
- download_resource(slug, resources_id, resources_url, base_dir)
- download_resources(base_dir, gtfs_datasets, timeout)
"""

from loguru import logger
import socket
from pathlib import Path
import polars as pl
import requests


def download_resource(
    slug: str,
    resources_id: str | int,
    resources_url: str,
    base_dir: Path,
) -> Path:
    """Replicates territoRy::download_resource().

    Download zip file to base_dir/resources_id/gtfs.zip.
    Raises an exception in case of failure (to allow retry in download_resources).
    """
    destfile = base_dir / str(resources_id) / "gtfs.zip"
    destfile.parent.mkdir(parents=True, exist_ok=True)

    if destfile.exists():
        logger.debug(f"File {slug} already present, skipping.")
        return destfile

    logger.info(f"Downloading {slug} from {resources_url}")
    r = requests.get(resources_url, timeout=15, stream=True)
    r.raise_for_status()
    with open(destfile, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return destfile


def download_resources(
    base_dir: Path,
    gtfs_datasets: pl.DataFrame,
    timeout: int = 10,
) -> pl.DataFrame:
    """Replicates territoRy::download_resources().

    Iterates over gtfs_datasets, tries resources_url then resources_original_url in case of failure.
    Returns a DataFrame with columns : slug, destfile, downloaded.
    """
    socket.setdefaulttimeout(timeout)
    logger.info("=== Downloading resources ===")
    results = []

    for row in gtfs_datasets.iter_rows(named=True):
        slug = row.get("slug", "")
        rid = row.get("resources_id")
        url = row.get("resources_url")
        original_url = row.get("resources_original_url")

        try:
            destfile = download_resource(slug, rid, url, base_dir)
            results.append(
                {"slug": slug, "destfile": str(destfile), "downloaded": True}
            )
        except Exception:
            logger.debug(
                f"Failed to download {slug} from {url}. Retrying with original_url..."
            )
            try:
                destfile = download_resource(slug, rid, original_url, base_dir)
                results.append(
                    {"slug": slug, "destfile": str(destfile), "downloaded": True}
                )
            except Exception as e2:
                logger.warning(f"Definitive failure for {slug} : {e2}")
                results.append({"slug": slug, "destfile": None, "downloaded": False})

    dl_df = pl.DataFrame(results)
    failed = dl_df.filter(~pl.col("downloaded"))
    if len(failed) > 0:
        logger.warning(
            "Resources not downloaded : {resource_list}",
            resource_list=", ".join(failed["slug"].to_list()),
        )
    return dl_df
