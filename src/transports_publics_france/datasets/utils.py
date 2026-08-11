"""
Utils for data.gouv.fr interaction and dataset management.
"""

from abc import ABC, abstractmethod
from datagouv import Client, Organization, Dataset
import os
from transports_publics_france.utils import get_package_version

CEREMA_ORGANIZATION_ID = "5c812a16634f416583ed1876"


class DatasetManager(ABC):
    """
    Generate and manage resources for a specific dataset.

    Subclasses should identify the dataset and its resources,
    and provide ways to generate and update them.
    """

    def __init__(self, environment="www", authenticate=True, verbose=False, dry=False):
        """
        Create a DatasetManager instance.

        :param environment: url prefix, see Client class
        :param authenticate: wether to authenticate using an API key or not
        :param verbose: manager and client verbosity
        :param dry: if True, don't actually update remote objects. For testing the pipeline
        """
        self.verbose: bool = verbose
        self.dry: bool = dry
        self.client: Client = get_datagouv_client(environment, authenticate, verbose)
        self._dataset = None

    @property
    def dataset(self) -> Dataset:
        """
        Instance of datagouv.Dataset for the managed dataset.
        """
        if self._dataset is None:
            self._dataset = self.client.dataset(self.dataset_id())
        return self._dataset

    # resource update

    def update_resources(self):
        """
        Browse the dataset resources and update them.
        """
        for resource_data in self._resources():
            resource_id = resource_data["id"]
            resource_file = resource_data["file"]

            # get resource info and add additional fields
            resource_payload = self.get_full_resource_payload(
                resource_data.get("payload", dict())
            )

            # update resource
            self._update_resource(resource_id, resource_payload, resource_file)

    def _update_resource(self, resource_id, payload, file):
        """
        Update the resource with the given payload and file.

        If dry, just check that the resource file exists.
        """
        message = f"Updated resource {resource_id} with file: {file}"
        if self.dry:
            message = message.replace("Updated", "Dry updated")
            if not os.path.exists(file):
                raise FileNotFoundError(f"Resource file not found: {file}")
        else:
            self.client.resource(resource_id).update(payload, file)
        self.log(message)

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

    # dataset specific methods to override

    @classmethod
    @abstractmethod
    def dataset_id(cls) -> str:
        """
        Dataset id as a string.

        :return: dataset id as a string
        """
        pass

    @abstractmethod
    def generate_dataset_ressources(self):
        """
        Generate files that will be used to update the dataset resources.
        """
        pass

    @abstractmethod
    def _resources(self) -> list[dict]:
        """
        List the resources of the dataset.

        Each list item is a dict containing the following keys:
            - id: resource id
            - file: path to resource file
            - payload: dict containing resource information

        :return: list of {id, file, payload} items
        """
        pass

    # utils

    def log(self, message):
        """
        Log a message if verbose.

        :param message: message to log
        """
        if self.verbose:
            print(message)


def get_datagouv_client(
    environment: str = "www", authenticate: bool = True, verbose=False
) -> Client:
    """
    Create a datagouv.Client instance.

    If authenticate, get the API key from the DATAGOUV_API_KEY environment variable.

    :param environment: url prefix, see Client class
    :param authenticate: wether to authenticate using an API key or not
    :param verbose: client verbosity

    :return: datagouv.Client instance
    """
    if authenticate:
        try:
            api_key = os.environ["DATAGOUV_API_KEY"]
        except KeyError:
            raise EnvironmentError("Missing environment variable DATAGOUV_API_KEY")
    else:
        api_key = None

    return Client(environment=environment, api_key=api_key, verbose=verbose)


def get_cerema_organization(client: Client | None = None) -> Organization:
    """
    Get a datagouv.Organization instance for the Cerema organisation.

    :param client: optionally provide client

    :return: datagouv.Organization instance of Cerema
    """
    client = client or get_datagouv_client(authenticate=False)
    return client.organization(CEREMA_ORGANIZATION_ID)
