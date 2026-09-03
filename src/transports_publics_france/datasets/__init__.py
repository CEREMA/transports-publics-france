from transports_publics_france.datasets.dataset_manager import DatasetManager
from transports_publics_france.datasets.demo_dataset import DemoDataset

# { dataset_key: dataset_class } mapper
DATASET_KEY_MAPPER = {
    dataset_class.dataset_key(): dataset_class for dataset_class in [
        DemoDataset
    ]
}
