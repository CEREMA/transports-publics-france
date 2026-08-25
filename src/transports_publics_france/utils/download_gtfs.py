"""
Utils for downloading GTFS resources from transport.data.gouv.fr
- download_resource(slug, resources_id, resources_url, base_dir, redownload)
- download_resources(gtfs_datasets, redownload, timeout)
"""

import logging
import socket
from pathlib import Path
import polars as pl
import requests

from transports_publics_france.config import BASE_DIR
from transports_publics_france.utils.io import make_local_resource_path

log = logging.getLogger(__name__)


def download_resource(
    slug: str,
    resources_id: str | int,
    resources_url: str,
    base_dir: Path,
    redownload: bool = False,
) -> Path:
    """Replicates territoRy::download_resource().

    Download zip file to base_dir/resources_id/gtfs.zip.
    Raises an exception in case of failure (to allow retry in download_resources).
    """
    destfile = make_local_resource_path(base_dir, resources_id) / "gtfs.zip"
    destfile.parent.mkdir(parents=True, exist_ok=True)

    if destfile.exists() and not redownload:
        log.info("File %s already present, skipping.", slug)
        return destfile

    log.info("Downloading %s from %s", slug, resources_url)
    r = requests.get(resources_url, timeout=15, stream=True)
    r.raise_for_status()
    with open(destfile, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return destfile


def download_resources(
    gtfs_datasets: pl.DataFrame,
    redownload: bool = False,
    timeout: int = 10,
) -> pl.DataFrame:
    """Replicates territoRy::download_resources().

    Iterates over gtfs_datasets, tries resources_url then resources_original_url in case of failure.
    Returns a DataFrame with columns : slug, destfile, downloaded.
    """
    socket.setdefaulttimeout(timeout)
    log.info("=== Downloading resources ===")
    results = []

    for row in gtfs_datasets.iter_rows(named=True):
        slug = row.get("slug", "")
        rid = row.get("resources_id")
        url = row.get("resources_url")
        original_url = row.get("resources_original_url")

        try:
            destfile = download_resource(slug, rid, url, BASE_DIR, redownload)
            results.append({"slug": slug, "destfile": str(destfile), "downloaded": True})
        except Exception:
            log.warning(
                "Failed to download %s from %s. Retrying with original_url...", slug, url
            )
            try:
                destfile = download_resource(slug, rid, original_url, BASE_DIR, redownload)
                results.append({"slug": slug, "destfile": str(destfile), "downloaded": True})
            except Exception as e2:
                log.warning("Definitive failure for %s : %s", slug, e2)
                results.append({"slug": slug, "destfile": None, "downloaded": False})

    dl_df = pl.DataFrame(results)
    failed = dl_df.filter(~pl.col("downloaded"))
    if len(failed) > 0:
        log.warning("Resources not downloaded : %s", ", ".join(failed["slug"].to_list()))
    return dl_df
