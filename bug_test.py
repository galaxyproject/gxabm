import bioblend.galaxy
from pprint import pprint
import os
import sys

# ID="1faa2d3b2ed5c436"
# ID="ab2feef9fbed6ebd"
# ID="28fa757e56346a34"

def bug():
    ID = "2a389383c5e81a6c"
    URL = os.environ.get('GALAXY_SERVER')
    KEY = os.environ.get('API_KEY')
    gi = bioblend.galaxy.GalaxyInstance(url=URL, key=KEY)
    dataset = gi.datasets.show_dataset(ID)
    assert ID == dataset['id'], f"The IDs should match, found {dataset['id']}"
    datasets = gi.datasets.get_datasets(name=dataset['name'])
    assert len(datasets) > 0, f"We should be able to find ourselves by name: \"{dataset['name']}\""
    print(f"Found dataset {dataset['name']}")

def find_by_name():
    ID = "2a389383c5e81a6c"
    URL = os.environ.get('GALAXY_SERVER')
    KEY = os.environ.get('API_KEY')
    gi = bioblend.galaxy.GalaxyInstance(url=URL, key=KEY)
    count  = 0
    datasets = gi.datasets.get_datasets(limit=10000)
    assert len(datasets) > 0, "We need at least one dataset to test"
    print(f"searching {len(datasets)} datasets")
    for dataset in datasets:
        id = dataset['id']
        assert id != ID, f"Found {id} at index {count}"
        count += 1
        # print(f"Checking {id}")
        # ds2 = gi.datasets.show_dataset(id)
        # assert ds2['id'] == id, 'The ID values should match.'
        # datasets  = gi.datasets.get_datasets(name=dataset['name'], limit=1000)
        # assert len(datasets) > 0, f"We should be able to find {id} {dataset['name']}"


def main():
    ID = "2a389383c5e81a6c"
    URL = os.environ.get('GALAXY_SERVER')
    KEY = os.environ.get('API_KEY')
    gi = bioblend.galaxy.GalaxyInstance(url=URL, key=KEY)
    print(f"Show ID  {ID}")
    dataset = gi.datasets.show_dataset(ID)
    name = dataset['name']
    print(f"{dataset['id']} {dataset['name']}")

    print(f"Filter by name {name}")
    datasets  = gi.datasets.get_datasets(name=name, limit=1000)
    if len(datasets) == 0:
        print('No such dataset')
    else:
        print(f"Found {len(datasets)} datasets")
        for dataset in datasets:
            print(f"{dataset['id']} {dataset['name']}")

    print(f"Show dataset['id'] {dataset['id']}")
    dataset = gi.datasets.show_dataset(dataset['id'])
    #pprint(dataset)
    if dataset is None:
        print("Can not find the dataset")
    else:
        print(f"{dataset['id']} {dataset['name']}")

def count():
    URL = KEY = None
    gi = bioblend.galaxy.GalaxyInstance(url=URL, key=KEY)
    datasets = gi.datasets.get_datasets(limit=10000)
    print(f"There are {len(datasets)} datasets")

if __name__ == '__main__':
    bug()