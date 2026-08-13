# Datasets

`transports-publics-france` contains code to generate several datasets available on the Cerema organisation of [data.gouv.fr](https://www.data.gouv.fr/organizations/cerema/datasets).

Each `{key}_dataset.py` is related to a specific dataset 
and contains instructions to generate its resources.

## List of datasets and their generating scripts

### [Jeu de données test](https://demo.data.gouv.fr/datasets/6a75b2fe90f2b13aa640af68/) ([demo_dataset.py](demo_dataset.py)) 

Dataset for demonstrating how to use dataset generation classes.

Publishes the package license to [demo.data.gouv.fr](https://demo.data.gouv.fr).

#### Resources

- license.txt: the package license

## Run the generation of dataset resources

Run this command to generate resources for the dataset corresponding to the key

```bash
# DATASET_KEY is the prefix in `{key}_dataset.py`
uv run generate-dataset DATASET_KEY
```

Publication to [demo.data.gouv.fr](https://demo.data.gouv.fr) can be simulated with the following command

```bash
uv run generate-dataset DATASET_KEY --dry-publish
```

## Updating the datasets on data.gouv.fr

_This action is only available for the repository maintainers and owners of an authorized account on the Cerema organization._

### GitHub action

Prefer using the `TODO` GitHub action.
If you are authorized, you can trigger it from the `Actions` tab of GitHub.

### Running the update locally

You will need an authorized API key. Then, run 

```bash
uv run generate-dataset DATASET_KEY --publish DATAGOUV_API_KEY
```

## Adding new datasets to `transports-publics-france`

On how to implement new dataset file generation, see [CONTRIBUTING.md](../../../CONTRIBUTING.md).
