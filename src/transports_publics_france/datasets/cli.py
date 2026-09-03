"""
Command line interface for generating transports-publics-france datasets and optionally publishing them to data.gouv.fr.

Exposed with uv as `uv run generate-dataset DATASET_KEY`
"""

import argparse
from transports_publics_france.datasets import DatasetManager, DATASET_KEY_MAPPER


def create_parser():
    parser = argparse.ArgumentParser(
        description="Generate resources of the transports-publics-france datasets",
    )

    parser.add_argument(
        "dataset",
        help="dataset key, in '{key}_dataset.py' ",
        metavar="DATASET_KEY",
        choices=["demo"],
        type=str,
        action="store",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="detailed logging if true",
        action="store_true",
    )

    parser.add_argument(
        "--publish",
        help="publish the generated dataset to data.gouv.fr with the given token, or using the DATAGOUV_API_KEY env variable",
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

    # check publish args
    if input_args.publish and input_args.dry_publish:
        raise ValueError("Cannot publish and dry publish at the same time")

    # get dataset generation class
    try:
        dataset_class = DATASET_KEY_MAPPER[input_args.dataset]
        dataset_manager: DatasetManager = dataset_class(verbose=input_args.verbose)
    except KeyError:
        raise ValueError(f"Dataset key {input_args.dataset} was not found")

    # generate datasets resources
    dataset_manager.generate_dataset_resources()

    # publish or dry publish if asked
    if input_args.publish:
        dataset_manager.authenticate(input_args.publish)
        dataset_manager.update_datagouv_dataset(dry=False)
    elif input_args.dry_publish:
        dataset_manager.update_datagouv_dataset(dry=True)
    else:
        print("No action provided. Use --publish API_KEY or --dry-publish")
