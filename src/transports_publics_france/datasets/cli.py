"""
Command line interface for generating transports-publics-france datasets and optionally publishing them to data.gouv.fr.

Exposed as `generate-dataset DATASET_KEY` using uv.

This module does not correspond to a dataset released and managed by `transports-publics-france`.
"""

import argparse
from loguru import logger
from transports_publics_france.utils import enable_logs
from transports_publics_france.datasets import DatasetManager, DATASET_KEY_MAPPER


def create_parser():
    parser = argparse.ArgumentParser(
        description="Generate resources of the transports-publics-france datasets",
    )

    parser.add_argument(
        "dataset",
        help=f"dataset key, among {list(DATASET_KEY_MAPPER.keys())}",
        metavar="DATASET_KEY",
        choices=list(DATASET_KEY_MAPPER.keys()),
        type=str,
        action="store",
    )

    parser.add_argument(
        "-l",
        "--log-level",
        help="Set logging level. Logging is managed using the loguru library",
        type=str,
        choices=["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    )

    parser.add_argument(
        "--publish",
        help="publish the generated dataset resources to data.gouv.fr with the given token",
        metavar="DATAGOUV_API_KEY",
        action="store",
    )

    parser.add_argument(
        "--dry-publish",
        help="run the publication pipeline without actually updating the datasets on data.gouv.fr",
        action="store_true",
    )

    return parser


def main():
    # get command line parser
    parser = create_parser()

    # read command line arguments and parse them
    input_args = parser.parse_args()

    # setup logging
    enable_logs(input_args.log_level)

    # check publish args
    if input_args.publish and input_args.dry_publish:
        raise ValueError("Cannot publish and dry publish at the same time")

    # get dataset generation class
    try:
        dataset_class = DATASET_KEY_MAPPER[input_args.dataset]
        dataset_manager: DatasetManager = dataset_class()
    except KeyError:  # pragma: no cover
        raise ValueError(f"Dataset key {input_args.dataset} was not found")

    logger.info(f"Start dataset generation pipeline for '{input_args.dataset}' dataset ")

    # generate datasets resources
    dataset_manager.generate_dataset_resources()

    # publish or dry publish if asked
    if input_args.publish:
        dataset_manager.authenticate(input_args.publish)
        dataset_manager.update_datagouv_dataset(dry=False)
    elif input_args.dry_publish:
        dataset_manager.update_datagouv_dataset(dry=True)
