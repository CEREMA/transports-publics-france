# Datasets

`transports-publics-france` contains code to generate and update several datasets available on the Cerema organisation of [data.gouv.fr]([https://data.gouv.fr](https://www.data.gouv.fr/organizations/cerema/datasets)).

Each `{key}_dataset.py` is related to a specific dataset 
and contains instructions to generate and update its files.

## List of datasets and their generating scripts

### [Jeu de données test](https://demo.data.gouv.fr/datasets/6a75b2fe90f2b13aa640af68/) ([demo_dataset.py](demo_dataset.py)) 

Dataset for demonstrating how to use dataset publication classes.

Publishes the package license to [demo.data.gouv.fr](https://demo.data.gouv.fr).

#### Resources

- license.txt: the package license

## Run the generation of dataset resources

Run this command to generate resources' files without updating the remote dataset

```bash
# TODO
```

### Updating the datasets on data.gouv.fr

_This action is only available for the repository maintainers._

#### GitHub action

Prefer using the `TODO` GitHub action.
If you are authorized, you can trigger it from the `Actions` tab of GitHub.

#### Running the update locally

You will need an authorized API key stored in the `DATAGOUV_API_KEY` environment variable.
Then, run 

```bash
# TODO
```
