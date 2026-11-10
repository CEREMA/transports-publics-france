from transports_publics_france.utils import get_package_version


def test_get_package_version():
    version = get_package_version()

    split = version.split(".")

    assert len(split) == 3
    for part in split:
        assert part.isdigit()
