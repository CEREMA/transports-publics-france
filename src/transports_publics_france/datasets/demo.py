"""
Dataset update class demonstration.
"""

from transports_publics_france.datasets.dataset_manager import DatasetManager
import shutil
import datetime


class Demo(DatasetManager):
    """
    Demonstration class that pushes the package license to a demo dataset.
    """

    LICENSE_RESOURCE_FILENAME = "LICENSE_RESOURCE.txt"

    # ignore the __init__ if using this class as an example
    def __init__(self, verbose=False):
        super().__init__(environment="demo", verbose=verbose)

    @classmethod
    def dataset_id(cls):
        return "6a75b2fe90f2b13aa640af68"

    def _generate_dataset_resources(self):
        # copy LICENSE.txt to dataset folder
        dest = self.folder + self.LICENSE_RESOURCE_FILENAME
        self.log(f"Copy license file to: {dest}")
        shutil.copyfile("LICENSE.txt", dest)

    def _update_datagouv_dataset(self):
        # force dry dataset update since this is a demo dataset
        self._dry_update_datagouv = True

        # replace the file of the relevant resource
        self._replace_resource_file(
            "c1d3d857-cb33-45a8-ab13-e9d72218486b",
            self.LICENSE_RESOURCE_FILENAME,
            payload={
                "description": f"License file at {datetime.datetime.now().isoformat()}"
            },
        )
