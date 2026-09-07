from transports_publics_france.datasets import Demo
import pytest


class TestDemo:

    @pytest.fixture
    def example_instance(self) -> Demo:
        return Demo()

    def test_init(self, example_instance):
        assert example_instance._client_environment == "demo"

    def test_dataset_id(self):
        assert Demo.dataset_id() == "6a75b2fe90f2b13aa640af68"

    def test__generate_dataset_resources(self, example_instance, mocker):
        mock = mocker.patch(
            "transports_publics_france.datasets.demo.shutil.copyfile"
        )

        example_instance._generate_dataset_resources()

        mock.assert_called_with(
            "LICENSE.txt",
            example_instance.folder + example_instance.LICENSE_RESOURCE_FILENAME,
        )

    def test__update_datagouv_dataset(self, example_instance, mocker):
        mock = mocker.patch(
            "transports_publics_france.datasets.demo.Demo._replace_resource_file"
        )

        example_instance._update_datagouv_dataset()

        assert example_instance._dry_update_datagouv
        mock.assert_called_once()
