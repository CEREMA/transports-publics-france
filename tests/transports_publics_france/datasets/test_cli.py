from transports_publics_france.datasets.cli import create_parser, main
import argparse
import pytest


def test_create_parser():

    parser = create_parser()

    assert isinstance(parser, argparse.ArgumentParser)

    input_args = parser.parse_args(["demo", "--verbose", "--dry-publish"])

    assert input_args.dataset == "demo"
    assert input_args.verbose
    assert not input_args.publish
    assert input_args.dry_publish


@pytest.fixture
def mock_command_line(mocker):
    parser = create_parser()

    def _mock_command_line(args):
        mocker.patch(
            "argparse.ArgumentParser.parse_args", return_value=parser.parse_args(args)
        )

    return _mock_command_line


def test_main_publish_conflict(mock_command_line):
    mock_command_line(["demo", "--publish", "API_KEY", "--dry-publish"])

    with pytest.raises(ValueError):
        main()


def test_main_publish(mock_command_line, mocker):
    mock_command_line(["demo", "--publish", "API_KEY"])

    mock = mocker.patch(
        "transports_publics_france.datasets.cli.DatasetManager.update_datagouv_dataset"
    )

    main()

    mock.assert_called_with(dry=False)


def test_main_dry_publish(mock_command_line, mocker):
    mock_command_line(["demo", "--dry-publish"])

    mock = mocker.patch(
        "transports_publics_france.datasets.cli.DatasetManager.update_datagouv_dataset"
    )

    main()

    mock.assert_called_with(dry=True)
