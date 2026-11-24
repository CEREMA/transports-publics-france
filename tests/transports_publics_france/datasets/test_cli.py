from transports_publics_france.datasets.cli import create_parser, main
import argparse
import pytest


def test_create_parser():

    parser = create_parser()

    assert isinstance(parser, argparse.ArgumentParser)

    input_args = parser.parse_args(["demo", "--dry-publish", "--log-level", "ERROR"])

    assert input_args.dataset == "demo"
    assert input_args.log_level == "ERROR"
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


@pytest.fixture
def mock_logger_enable(mocker):
    mocker.patch("transports_publics_france.datasets.cli.enable_logs")


def test_main_publish_conflict(mock_command_line, mock_logger_enable):
    mock_command_line(["demo", "--publish", "API_KEY", "--dry-publish"])

    with pytest.raises(ValueError):
        main()


def test_main_publish(mock_command_line, mocker, mock_logger_enable):
    mock_command_line(["demo", "--publish", "API_KEY"])

    mock = mocker.patch(
        "transports_publics_france.datasets.cli.DatasetManager.update_datagouv_dataset"
    )

    main()

    mock.assert_called_with(dry=False)


def test_main_dry_publish(mock_command_line, mocker, mock_logger_enable):
    mock_command_line(["demo", "--dry-publish"])

    mock = mocker.patch(
        "transports_publics_france.datasets.cli.DatasetManager.update_datagouv_dataset"
    )

    main()

    mock.assert_called_with(dry=True)


def test_main_clean(mock_command_line, mocker):
    mock_command_line(["demo", "--clean"])

    mock = mocker.patch(
        "transports_publics_france.datasets.cli.DatasetManager.delete_folder"
    )

    main()

    mock.assert_called_once()
