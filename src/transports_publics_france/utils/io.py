"""
Input/Output utilities for the transports-publics-france package :
- make_local_resource_path(base_dir, resources_id)
- extract_gtfs_zip(gtfs_zip_file, files)
- read_gtfs_dataset(gtfs_dir, files_to_keep)
"""

import logging
import re
import unicodedata
import zipfile
from pathlib import Path
from io import StringIO
import polars as pl

log = logging.getLogger(__name__)

def make_local_resource_path(base_dir: Path, resources_id: str | int) -> Path:
    """Replicates territoRy::make_local_resource_path() : base_dir / resources_id."""
    return base_dir / str(resources_id)


def extract_gtfs_zip(gtfs_zip_file: Path, files: list[str] | None = None) -> dict:
    """Extract the *.txt files from a GTFS zip file into its parent directory.

    Replicates territoRy::extract_gtfs_zip() :
    - Lists the files in the zip
    - Matches the requested names via pmatch (basename)
    - Extracts with junkpaths=True (flatten subdirectories)
    - Returns {"files": "a.txt, b.txt, ...", "extracted": bool}
    """
    destdir = gtfs_zip_file.parent

    try:
        with zipfile.ZipFile(gtfs_zip_file) as zf:
            archive_names = zf.namelist()
    except Exception as e:
        log.debug("Impossible to open %s : %s", gtfs_zip_file, e)
        return {"files": None, "extracted": False}

    # pmatch : pour chaque nom demandé, trouve le fichier dans l'archive par basename
    if files is not None:
        matched = []
        for wanted in files:
            wanted_base = Path(wanted).name
            candidates = [n for n in archive_names if Path(n).name == wanted_base]
            if candidates:
                matched.append(candidates[0])
        files_to_extract = matched if matched else []
    else:
        files_to_extract = archive_names

    if not files_to_extract:
        return {"files": "", "extracted": False}

    # Extraction avec flatten (junkpaths) : tous les .txt à la racine de destdir
    extracted_names = []
    try:
        with zipfile.ZipFile(gtfs_zip_file) as zf:
            for member in files_to_extract:
                basename = Path(member).name
                dest_path = destdir / basename
                with zf.open(member) as src, open(dest_path, "wb") as dst:
                    dst.write(src.read())
                extracted_names.append(basename)
    except Exception as e:
        log.debug("Extracting error %s : %s", gtfs_zip_file, e)
        return {"files": "", "extracted": False}

    return {
        "files": ", ".join(extracted_names),
        "extracted": len(extracted_names) > 0,
    }


def _clean_column_name(name: str) -> str:
    """Equivalent of janitor::clean_names() : snake_case, without special characters."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name or "col"


def read_gtfs_dataset(
    gtfs_dir: Path,
    files_to_keep: list[str] | None = None,
) -> dict[str, pl.DataFrame]:
    """Reads all .txt files from a GTFS directory into Polars DataFrames.

    Replicates territoRy::read_gtfs_dataset() :
    - Reads all *.txt files from the directory (or only files_to_keep)
    - All columns as strings (colClasses = "character")
    - Column names cleaned (janitor::clean_names → snake_case)
    - Removes unnamed columns (starting with "...")
    - Removes residual quotation marks (str_remove_all(x, '"'))
    """
    gtfs_files = sorted(gtfs_dir.glob("*.txt"))

    if files_to_keep is not None:
        gtfs_files = [f for f in gtfs_files if f.stem in files_to_keep]

    result: dict[str, pl.DataFrame] = {}
    for f in gtfs_files:
        try:
            raw = f.read_bytes().decode("utf-8-sig", errors="replace")
            df = pl.read_csv(
                StringIO(raw),
                infer_schema_length=0,
                ignore_errors=True,
                truncate_ragged_lines=True,
            )
            df = df.rename({c: _clean_column_name(c) for c in df.columns})
            df = df.select([c for c in df.columns if not c.startswith("...")])
            df = df.with_columns(
                [pl.col(c).str.replace_all('"', "") for c in df.columns]
            )
            result[f.stem] = df
        except Exception as e:
            log.debug("Impossible to read %s : %s", f.name, e)

    return result
