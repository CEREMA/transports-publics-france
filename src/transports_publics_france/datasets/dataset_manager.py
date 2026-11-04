"""
This module contains utils dataset management.

This module does not correspond to a dataset released and managed by `transports-publics-france`.
"""

from abc import ABC, abstractmethod
import datagouv
import os
from transports_publics_france.utils import get_package_version

CEREMA_ORGANIZATION_ID = "5c812a16634f416583ed1876"

DATASET_FOLDER = "generated_datasets/"


class DatasetManager(ABC):
    """
    Generate and manage resources for a specific dataset.

    Subclasses should identify the dataset and implement how its resources are generated and updated.
    """

    def __init__(self, environment="www", verbose=False):
        """
        Create a DatasetManager instance.

        :param environment: url prefix, see Client class
        :param verbose: manager and client verbosity
        """
        # process verbosity
        self.verbose: bool = verbose

        # datagouv.Dataset instance cache
        self._dataset = None

        # if True, don't actually update datagouv datasets
        self._dry_update_datagouv: bool = False

        # client attributes
        self._client_environment: str = environment
        self.datagouv_client: datagouv.Client
        self.authenticate(None)  # init unauthenticated client

    # dataset key for transports-publics-france identification

    @classmethod
    def dataset_key(cls) -> str:
        """
        Dataset key (used as identifier in the package).

        This corresponds to the name of the module in which
        the dataset class is defined.

        :return: dataset key string
        """
        return cls.__module__.split(".")[-1]

    # datagouv objects

    @property
    def dataset(self) -> datagouv.Dataset:
        """
        Instance of datagouv.Dataset for the managed dataset.
        """
        if self._dataset is None:
            self._dataset = self.datagouv_client.dataset(self.dataset_id())
        return self._dataset

    @classmethod
    @abstractmethod
    def dataset_id(cls) -> str:
        """
        Dataset id as a string.

        :return: dataset id as a string
        """

    # dataset folder where resources are generated

    @property
    def folder(self) -> str:
        """
        Dataset folder where intermediate files and results are generated.
        """
        return os.path.join(DATASET_FOLDER, self.dataset_key(), "")

    # resource generation

    def generate_dataset_resources(self):
        """
        Prepare resource generation and call the _generate_dataset_resources method.
        """
        # create target folder
        self.create_folder()

        # call resource generation method
        self.log(f"Start generating resources for '{self.dataset_key()}' dataset")
        self._generate_dataset_resources()

    @abstractmethod
    def _generate_dataset_resources(self):
        """
        Generate files that will be used to update the dataset resources.

        Resources should be generated in the dataset folder (self.folder).
        """

    # dataset update

    def authenticate(self, api_key: str | None):
        """
        Create and store an authenticated datagouv.Client instance.

        Sets the self.datagouv_client attribute.

        :param api_key: API key used to authenticate to datagouv.fr
        """
        self.datagouv_client = datagouv.Client(
            environment=self._client_environment, api_key=api_key, verbose=self.verbose
        )

    def update_datagouv_dataset(self, dry: bool):
        """
        Prepare resource generation and call the _generate_dataset_resources method.

        :param dry: if dry, don't actually perform the dataset update
        """
        # store dry value
        self._dry_update_datagouv = dry

        self.log(
            f"Start updating '{self.dataset_key()}' dataset on datagouv.fr (datagouv id: {self.dataset_id()})"
        )
        self._update_datagouv_dataset()
        self.log(
            f"'{self.dataset_key()}' dataset has been successfully updated (datagouv id: {self.dataset_id()})"
        )

    @abstractmethod
    def _update_datagouv_dataset(self):
        """
        Update the datagouv dataset with generated dataset files.

        Datasets can be updated in two ways:
          - Adding new resources: call the _add_resource_file method
          - Replacing a resource file: call the _replace_resource_file method

        Resource files should be in the dataset folder (self.folder).
        """
        pass

    # resource update

    def _add_resource_file(
        self, filename: str, title: str, payload: dict | None = None
    ) -> str:
        """
        Add a new resource file to the dataset.

        Resource attributes that can be included in payload (see datagouv API):
          - description
          - type
          - ...

        :param filename: name of the resource file (must be in the resource folder)
        :param title: resource title
        :param payload: other resource attributes

        :return: generated resource id
        """
        # build resource payload
        payload = payload or dict()
        payload["title"] = title

        # perform checks and data preparation
        filepath, full_payload = self._prepare_resource_update(filename, payload)

        resource_id = "#"
        if not self._dry_update_datagouv:
            # attach new resource to dataset
            resource_id = self.dataset.create_static(filepath, full_payload).id

        # log success
        self.log(
            f"{"[Dry] " if self._dry_update_datagouv else ""}Created resource '{title}' ({resource_id}) from file: {filepath}"
        )
        return resource_id

    def _replace_resource_file(
        self, resource_id: str, filename: str, payload: dict | None = None
    ):
        """
        Update the resource with the given payload and file.

        The file must be in the dataset folder.

        :param resource_id: datagouv resource id
        :param filename: name of the resource file (must be in the resource folder)
        :param payload: resource info payload
        """
        # perform checks and data preparation
        filepath, full_payload = self._prepare_resource_update(
            filename, payload or dict()
        )

        if not self._dry_update_datagouv:
            # update resource file
            self.datagouv_client.resource(resource_id).update(full_payload, filepath)

        # log success
        self.log(
            f"{"[Dry] " if self._dry_update_datagouv else ""}Updated resource {resource_id} with file: {filepath}"
        )

        return resource_id

    def _prepare_resource_update(self, filename: str, payload: dict):
        """
        Perform checks and processing on the resource file and payload.

        Resource files are supposed to be in the dataset folder.

        :param filename: name of the resource file (must be in dataset folder)
        :param payload: resource information payload

        :return: resource_filepath, resource_payload
        """
        # check file existence
        filepath = os.path.join(self.folder, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Resource file not found: {filepath}")

        full_payload = self.get_full_resource_payload(payload)

        return filepath, full_payload

    def get_full_resource_payload(self, payload: dict) -> dict:
        """
        Fill the resource payload with additional information.

        :param payload: original resource payload

        :return: updated resource payload
        """
        extras = payload.get("extras", dict())

        # store package version in resource extras
        extras["transports-publics-france-version"] = get_package_version()

        payload["extras"] = extras
        return payload

    # utils

    def log(self, message):
        """
        Log a message if verbose.

        :param message: message to log
        """
        if self.verbose:
            print(message)

    def create_folder(self):
        """
        Create the dataset folder if it doesn't already exist.
        """
        os.makedirs(self.folder, exist_ok=True)


def get_cerema_organization(api_key: str | None = None) -> datagouv.Organization:
    """
    Get the datagouv.Organization instance of the Cerema organisation.

    :param api_key: API key used to authenticate to datagouv.fr

    :return: datagouv.Organization instance of Cerema
    """
    client = datagouv.Client(api_key=api_key)
    return client.organization(CEREMA_ORGANIZATION_ID)


# def get_datagouv_client(
#     environment: str = "www", authenticate: bool = True, verbose=False
# ) -> datagouv.Client:
#     """
#     Create a datagouv.Client instance.
#
#     If authenticate, get the API key from the DATAGOUV_API_KEY environment variable.
#
#     :param environment: url prefix, see Client class
#     :param authenticate: wether to authenticate using an API key or not
#     :param verbose: client verbosity
#
#     :return: datagouv.Client instance
#     """
#     if authenticate:
#         try:
#             api_key = os.environ["DATAGOUV_API_KEY"]
#         except KeyError:
#             raise EnvironmentError("Missing environment variable DATAGOUV_API_KEY")
#     else:
#         api_key = None
#
#     return datagouv.Client(environment=environment, api_key=api_key, verbose=verbose)
