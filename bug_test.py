import bioblend.galaxy
from pprint import pprint

URL="https://benchmarking.usegvl.org/initial/galaxy/"
KEY="43f747baa4efe808fc090938dd5e74c7"
ID="1faa2d3b2ed5c436"
# ID="ab2feef9fbed6ebd"
# ID="28fa757e56346a34"
def main():
    gi = bioblend.galaxy.GalaxyInstance(url=URL, key=KEY)
    dataset = gi.datasets.show_dataset(ID)
    name = dataset['name']
    print(f"{dataset['id']} {dataset['name']}")
    datasets  = gi.datasets.get_datasets(name=name, limit=1000)
    if len(datasets) == 0:
        print('No such dataset')
    else:
        for dataset in datasets:
            print(f"{dataset['id']} {dataset['name']}")

    dataset = gi.datasets.show_dataset(dataset['id'])
    #pprint(dataset)
    if dataset is None:
        print("Can not find the dataset")
    else:
        print(f"{dataset['id']} {dataset['name']}")

def count():
    gi = bioblend.galaxy.GalaxyInstance(url=URL, key=KEY)
    datasets = gi.datasets.get_datasets(limit=10000)
    print(f"There are {len(datasets)} datasets")

if __name__ == '__main__':
    main()