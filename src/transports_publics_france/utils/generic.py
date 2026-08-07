import importlib.metadata


def get_package_version() -> str:
    """
    Get the version of transports-publics-france.

    :return: Version in SemVer format (major.minor.patch)
    """

    return importlib.metadata.version("transports-publics-france")
