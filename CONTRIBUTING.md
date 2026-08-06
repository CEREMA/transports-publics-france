# Contributing guidelines for `transports-publics-france`

## Introduction

Thank you for considering contributing to `transports-publics-france` !

## Getting started

#### If you find a security vulnerability:

  - do NOT open an issue. Contact us directly instead

#### If you've found a bug:

  - search through the [project issues](https://github.com/CEREMA/transports-publics-france/issues)
  - if you don't find your bug in the listed issues, open a new one

#### If you have a feature proposal or want to contribute:

  - post your proposal on the [issue tracker](https://github.com/CEREMA/transports-publics-france/issues) so we can review it together
  - fork the repo, make your change, test it, and submit a PR

## Coding style and commit messages
    
### Coding style

The coding style imposed on `transports-publics-france` includes:

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

We use Black for formatting the codebase.

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

Run tests from the root of the project using pytest. Use the -v option for verbose output.

```bash
pytest [-v]
```

### Auto-run on PRs

Tests are automatically run when making a PR on gitHub
