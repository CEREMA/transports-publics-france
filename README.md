# transports-publics-france

This repository contains code related to the processing and analysis of data related to french public transports.

TODO (mention the division between the python package and the dataset generation scripts)


## Usage

`transports-publics-france` can be used as a Python package or as a script to generate datasets.

### Using as a package

The `transports-publics-france` package will soon be available on PyPi and can be installed with

```bash
# using uv
uv add transports-publics-france

# using pip
pip install transports-publics-france
```

### Generate dataset resources

`transports-publics-france` contains the source code used to generate the resources
of [several opendata datasets](src/transports_publics_france/datasets/README.md).

You can reproduce this generation process by running the following command

```bash
# DATASET_KEY is the prefix in `{key}_dataset.py`
uv run generate-dataset DATASET_KEY
```

For detailed help on the command arguments, run

```bash
uv run generate-dataset -h
```
