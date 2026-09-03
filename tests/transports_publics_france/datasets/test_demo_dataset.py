from transports_publics_france.datasets import DemoDataset
import pytest


class TestDemoDataset:

    @pytest.fixture
    def example_instance(self) -> DemoDataset:
        return DemoDataset()

    def test_init(self, example_instance):
        assert example_instance._client_environment == "demo"

    def test_dataset_id(self):
        assert DemoDataset.dataset_id() == "6a75b2fe90f2b13aa640af68"

    def test__generate_dataset_resources(self, example_instance, mocker):
        mock = mocker.patch(
            "transports_publics_france.datasets.demo_dataset.shutil.copyfile"
        )

        example_instance._generate_dataset_resources()

        mock.assert_called_with(
            "LICENSE.txt",
            example_instance.folder + example_instance.LICENSE_RESOURCE_FILENAME,
        )

    def test__update_datagouv_dataset(self, example_instance, mocker):
        mock = mocker.patch(
            "transports_publics_france.datasets.demo_dataset.DemoDataset._replace_resource_file"
        )

        example_instance._update_datagouv_dataset()

        mock.assert_called_once()
