
## List of datasets and their generating scripts

### [Jeu de données test](https://demo.data.gouv.fr/datasets/6a75b2fe90f2b13aa640af68/) ([demo_dataset.py](demo_dataset.py)) 

Dataset for demonstrating how to use dataset publication classes.

Publishes the package license to [demo.data.gouv.fr](https://demo.data.gouv.fr).

#### Resources

- license.txt: the package license


## How to add a new dataset to `transports-publics-france`

1. Create your dataset and resources in [data.gouv.fr](https://www.data.gouv.fr) using the Cerema organization
2. Create a new `{key}_dataset.py` file, with `{key}` being your dataset key *in the package*
3. In this file, define a class that inherits `datasets_publication.utils.DatasetManager`. It must implement all the abstract methods of `DatasetManager` (see example in [demo_dataset.py](demo_dataset.py)):
   1. `_dataset_id`: returns the *data.gouv.fr* id of the dataset you want to update
   2. `generate_dataset_ressources`: actual code that generates the resources' files
   3. `_resources`: returns a list of resource information
         1. `id`: resource id *in data.gouv.fr*
         2. `file`: path to resource file
         3. `payload`: dict containing resource information (see [API doc](https://guides.data.gouv.fr/api-de-data.gouv.fr/reference/datasets?select=par-api#put-datasets-dataset-resources-rid) for available fields)
4. Run `TODO` to test your class without updating the remote dataset. Check that the files generated in the dataset folder fit your expectations
5. Update this README with your dataset information