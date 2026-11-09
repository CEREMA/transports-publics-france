"""
Network report dataset (gtfs_datasets_info).

Generates the report with the GTFS pipeline + `build_network_report`,
then publishes it as a resource of the dataset on data.gouv.fr.

Fields documentation: gtfs_datasets_info.md
"""

import datetime
from pathlib import Path

from transports_publics_france.datasets.dataset_manager import DatasetManager
from transports_publics_france import run_gtfs_pipeline, build_network_report


class GtfsDatasetsInfo(DatasetManager):
    """
    Generate and publish the network report: one row per GTFS resource
    referenced on transport.data.gouv.fr.
    """

    # subfolder of the dataset folder for the (heavy) intermediate files
    WORK_SUBFOLDER = "data"

    def __init__(self, verbose=False, run_date: datetime.date | None = None):
        super().__init__(verbose=verbose)
        self.run_date: datetime.date = run_date or datetime.date.today()

    @property
    def report_filename(self) -> str:
        """Return the filename of the report."""
        return f"{self.run_date.strftime('%Y%m%d')}_gtfs_datasets_info.csv"

    @classmethod
    def dataset_id(cls) -> str:
        return "6a97e28ffcf92f8247d2ef0b"

    def _generate_dataset_resources(self):
        # intermediate files (downloaded GTFS, raw tables...) subfolder
        work_dir = Path(self.folder) / self.WORK_SUBFOLDER
        work_dir.mkdir(parents=True, exist_ok=True)

        run_gtfs_pipeline(out_dir=work_dir, run_date=self.run_date, redownload=True)
        build_network_report(self.run_date, work_dir)

    def _update_datagouv_dataset(self):
        self._add_resource_file(
            filename=f"{self.WORK_SUBFOLDER}/{self.report_filename}",
            title=f"Rapport par réseau - {self.run_date.isoformat()}",
            payload={
                "description": (
                    "Une ligne par ressource GTFS référencée sur transport.data.gouv.fr. "
                    f"Extraction du {self.run_date.isoformat()}."
                ),
            },
        )
