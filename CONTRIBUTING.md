# Contributing guidelines for `transports-publics-france`

## Introduction

Thank you for considering contributing to `transports-publics-france` !

### If you find a security vulnerability:

  - do NOT open an issue. Contact us directly instead

### If you've found a bug:

  - search through the [project issues](https://github.com/CEREMA/transports-publics-france/issues)
  - if you don't find your bug in the listed issues, open a new one

### If you have a feature proposal or want to contribute:

  - post your proposal on the [issue tracker](https://github.com/CEREMA/transports-publics-france/issues) so we can review it together
  - fork the repo, make your change, test it, and submit a PR

## Getting started

Make sure to install all the project dependencies by running

```bash
uv sync --all-extras
```

## Coding style and commit messages
    
### Coding style

The coding style on `transports-publics-france` includes:

  - respect [PEP8 style guide](https://peps.python.org/pep-0008/) as much as possible
  - write code in english
  - use [Python typing](https://docs.python.org/3/library/typing.html) when possible
  - document your code as much as possible, ideally in reST docstring style. Example: 

```python
def function(param1: str, param2: int):
    """
    This is a reST style.
    
    :param param1: this is a first param
    :param param2: this is a second param
    :returns: this is a description of what is returned
    :raises keyError: raises an exception
    """
    return param1, param2
```

### Black formatting

We use [Black](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html) for formatting the codebase.

**Don't try to fit Black's style yourself !** A code formatter is meant to be run after
you've finished coding to ensure uniform style.

Formatting is done by installing and running Black at the project root. 

```bash
black .

# black will list every file modified during the process
```

Black style formatting is automatically checked when making a PR on GitHub.


### Commit message convention

Commits on branch `main` must use the [conventional commit convention](https://www.conventionalcommits.org/en/v1.0.0/)
in order to generate a [changelog from the commits](https://github.com/conventional-changelog/standard-version)

## Testing

### Run tests locally

Run tests from the root of the project using [pytest](https://docs.pytest.org/en/stable/). Use the -v option for verbose output.

```bash
pytest [-v]
```

### Auto-run on PRs

Tests are automatically run when making a PR on gitHub

## Adding a new dataset to `transports-publics-france`

Here are the step to follow if you want to add a new dataset to the list of datasets
managed using `transports-publics-france`:

1. Create your dataset and resources in [data.gouv.fr](https://www.data.gouv.fr) using the Cerema organization
2. Create a new python module in `src/transports_publics_france/datasets/`. The module name (without ".py") will be refered as the `dataset_key` and used as identifier in the package.
3. In this file, define a class that inherits `transports_publics_france.datasets.DatasetManager`. It must implement all the abstract methods of `DatasetManager` (see example in [demo_dataset.py](demo_dataset.py)):
   2. `dataset_id`: returns the *data.gouv.fr* id of the dataset you want to update. Add the `@classmethod` decorator on top of the signature.
   3. `_generate_dataset_resources`: **actual code that generates the resources' files**
   4. `_update_datagouv_dataset`: **code that updates the datagouv dataset**. Use the methods of the parent class to update the dataset:
```python
import datetime

def _update_datagouv_dataset(self):
    # define what to do with the generated files
    # (they must be in the dataset folder)
   
    # add a new resource to the dataset
    self._add_resource_file(
        filename="MY_FILE.txt", 
        title="My resource title", 
        payload={"description": "My resource description"}
    )
   
    # replace the file of an existing resource
    self._replace_resource_file(
        resource_id="c1d3d857-cb33-45a8-ab13-e9d72218486b",
        filename="MY_FILE.txt",
        payload={
            "description": f"Updated the {datetime.datetime.now().isoformat()}"
        },
  )
```

4. Run `uv run generate-dataset MY_DATASET_KEY --dry-publish -v` to test your class without updating the remote dataset. Check that the files generated in the dataset folder fit your expectations
5. Update this README with your dataset information
