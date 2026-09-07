from transports_publics_france.datasets.demo import Demo
from transports_publics_france.datasets.dataset_manager import (
    get_cerema_organization,
    CEREMA_ORGANIZATION_ID,
    DatasetManager,
)
import datagouv
import pytest


class TestDataSetManager:

    @pytest.fixture
    def example_instance(self) -> Demo:
        return Demo()

    def test_init(self):
        instance = Demo(verbose=True)

        assert instance.verbose
        assert isinstance(instance.datagouv_client, datagouv.Client)

    def test_dataset_key(self):
        assert DatasetManager.dataset_key() == "dataset_manager"
        assert Demo.dataset_key() == "demo"

    def test_folder(self, example_instance):

        assert example_instance.dataset_key() in example_instance.folder

    def test_generate_dataset_resources(self, example_instance, mocker):

        mock1 = mocker.patch(
            "transports_publics_france.datasets.dataset_manager.DatasetManager.create_folder"
        )
        mock2 = mocker.patch(
            "transports_publics_france.datasets.demo.Demo._generate_dataset_resources"
        )

        example_instance.generate_dataset_resources()

        mock1.assert_called_once()
        mock2.assert_called_once()

    def test_authenticate(self, example_instance):

        example_instance.authenticate("FAKE_API_KEY")

        assert isinstance(example_instance.datagouv_client, datagouv.Client)

    def test_update_datagouv_dataset(self, example_instance, mocker):

        mock = mocker.patch(
            "transports_publics_france.datasets.demo.Demo._update_datagouv_dataset"
        )

        example_instance.update_datagouv_dataset(dry=True)

        assert example_instance._dry_update_datagouv
        mock.assert_called_once()

    def test_add_resource_file(self, example_instance, mocker):
        example_instance._dry_update_datagouv = False
        resource = datagouv.Resource("RESOURCE_ID", dataset_id="...", fetch=False)
        fake_full_payload = {"fake": "payload"}
        mock_prepare_payload = mocker.patch(
            "transports_publics_france.datasets.dataset_manager.DatasetManager._prepare_resource_update",
            return_value=("filepath", fake_full_payload),
        )
        mock_create_static = mocker.patch(
            "transports_publics_france.datasets.dataset_manager.datagouv.Dataset.create_static",
            return_value=resource,
        )

        resource_id = example_instance._add_resource_file(
            "FILE.txt", "My resource", {"description": "My resource description"}
        )

        mock_prepare_payload.assert_called_with(
            "FILE.txt",
            {"title": "My resource", "description": "My resource description"},
        )
        assert resource_id == "RESOURCE_ID"
        mock_create_static.assert_called_with("filepath", fake_full_payload)

    def test_replace_resource_file(self, example_instance, mocker):
        example_instance._dry_update_datagouv = False
        fake_resource_id = "RESOURCE_ID"
        fake_payload = {"fake": "payload"}
        fake_full_payload = {"fake": "full_payload"}
        mock_prepare_payload = mocker.patch(
            "transports_publics_france.datasets.dataset_manager.DatasetManager._prepare_resource_update",
            return_value=("filepath", fake_full_payload),
        )
        mock_resource = mocker.patch(
            "transports_publics_france.datasets.dataset_manager.datagouv.Client.resource",
            return_value=datagouv.Resource(
                fake_resource_id, dataset_id="...", fetch=False
            ),
        )
        mock_resource_update = mocker.patch(
            "transports_publics_france.datasets.dataset_manager.datagouv.Resource.update"
        )

        resource_id = example_instance._replace_resource_file(
            fake_resource_id, "FILE.txt", payload=fake_payload
        )

        assert resource_id == fake_resource_id
        mock_prepare_payload.assert_called_with("FILE.txt", fake_payload)
        mock_resource.assert_called_with(resource_id)
        mock_resource_update.assert_called_with(fake_full_payload, "filepath")

    def test_get_full_resource_payload(self, example_instance, mocker):
        fake_version = "X.Y.Z"
        mocker.patch(
            "transports_publics_france.datasets.dataset_manager.get_package_version",
            return_value=fake_version,
        )
        original_payload = {"key": "val", "extras": {"k": "v"}}

        full_payload = example_instance.get_full_resource_payload(original_payload)

        assert full_payload == {
            "key": "val",
            "extras": {
                "k": "v",
                "transports-publics-france-version": fake_version,
            },
        }

    def test_log(self, example_instance, mocker):
        mock = mocker.patch("transports_publics_france.datasets.dataset_manager.print")
        example_instance.verbose = True

        example_instance.log("TEST_0")

        mock.assert_called_with("TEST_0")
        assert len(mock.mock_calls) == 1

        example_instance.verbose = False
        example_instance.log("TEST_1")

        assert len(mock.mock_calls) == 1

    def test_create_folder(self, example_instance, mocker):
        mock = mocker.patch(
            "transports_publics_france.datasets.dataset_manager.os.makedirs"
        )

        example_instance.create_folder()

        mock.assert_called_with(example_instance.folder, exist_ok=True)


def test_get_cerema_organization(mocker):
    mock = mocker.patch(
        "transports_publics_france.datasets.dataset_manager.datagouv.Client.organization",
        return_value=datagouv.Organization(CEREMA_ORGANIZATION_ID, fetch=False),
    )

    organisation = get_cerema_organization()

    mock.assert_called_with(CEREMA_ORGANIZATION_ID)
    assert isinstance(organisation, datagouv.Organization)
