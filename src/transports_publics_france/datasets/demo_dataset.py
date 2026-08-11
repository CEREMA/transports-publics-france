"""
Dataset update class demonstration.
"""

from transports_publics_france.datasets.utils import DatasetManager


class DemoDataset(DatasetManager):
    """
    Demonstration class that pushes LICENSE.txt to a demo dataset.
    """

    def __init__(self, authenticate=True, verbose=False, dry=False):
        super().__init__(
            environment="demo", authenticate=authenticate, verbose=verbose, dry=dry
        )

    @classmethod
    def dataset_id(cls):
        return "6a75b2fe90f2b13aa640af68"

    def _resources(self) -> list[dict]:
        return [
            {
                "id": "c1d3d857-cb33-45a8-ab13-e9d72218486b",
                "payload": {},
                "file": "LICENSE.txt",
            }
        ]

    def generate_dataset_ressources(self):
        # nothing to do, LICENSE.txt already exists
        pass
