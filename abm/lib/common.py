import json
import os
import subprocess
import sys
from math import ceil
from pathlib import Path

import bioblend.galaxy
import lib
from bioblend.galaxy import dataset_collections
from ruamel.yaml import YAML

# Where we will look for our configuration file.
PROFILE_SEARCH_PATH = ['.abm/profile.yml', '~/.abm/profile.yml', '.abm-profile.yml']

# Deprecated. Do not use.
datasets = {
    "dna": [
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR013/ERR013101/ERR013101_1.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR015/ERR015526/ERR015526_2.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR592/SRR592109/SRR592109_2.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR233/SRR233167/SRR233167_2.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR047/ERR047678/ERR047678_1.fastq.gz",
        "ftp://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/data/AshkenazimTrio/HG003_NA24149_father/NIST_Illumina_2x250bps/reads/D2_S1_L002_R1_002.fastq.gz",
    ],
    "rna": [],
}


def try_for(f, limit=3):
    """
    Tries to invoke the function f. If the function f fails it will be retried
    *limit* number of times.

    :param f: the function to invoke
    :param limit: how many times the function will be retried
    :return: the result of calling f()
    """
    count = 0
    running = True
    result = None
    while running:
        try:
            count += 1
            result = f()
            running = False
        except Exception as e:
            if count >= limit:
                raise e
    return result


class Context:
    """
    The context object that contains information to connect to a Galaxy instance.

    GALAXY_SERVER: the URL of the Galaxy server to connect to
    API_KEY      : a user's API key to make API calls on the Galaxy instance
    KUBECONFIG:  : the kubeconfig file needed to make changes via Helm
    """

    def __init__(self, *args):
        if len(args) == 1:
            arg = args[0]
            if type(arg) == str:
                (
                    self.GALAXY_SERVER,
                    self.API_KEY,
                    self.KUBECONFIG,
                    self.MASTER_KEY,
                ) = parse_profile(arg)
            elif type(arg) == dict:
                self.GALAXY_SERVER = arg['GALAXY_SERVER']
                self.API_KEY = arg['API_KEY']
                self.KUBECONFIG = arg['KUBECONFIG']
                if 'MASTER_KEY' in arg:
                    self.MASTER_KEY = arg['MASTER_KEY']
                else:
                    self.MASTER_KEY = None
            else:
                raise Exception(f'Invalid arg for Context: {type(arg)}')
        elif len(args) == 3 or len(args) == 4:
            self.GALAXY_SERVER = args[0]
            self.API_KEY = args[1]
            self.KUBECONFIG = args[2]
            if len(args) == 4:
                self.MASTER_KEY = args[3]
        else:
            raise Exception(
                f'Invalid args for Context. Expected one or four, found {len(args)}'
            )


def print_json(obj, indent=2):
    print(json.dumps(obj, indent=indent))


def print_yaml(obj):
    get_yaml_parser().dump(obj, sys.stdout)


def connect(context: Context, use_master_key=False):
    """
    Create a connection to the Galaxy instance

    :return: a GalaxyInstance object
    """
    if context.GALAXY_SERVER is None:
        print('ERROR: The Galaxy server URL has not been set.  Please check your')
        print('       configuration in ~/.abm/profile.yml and try again.')
        sys.exit(1)
    if context.API_KEY is None:
        print('ERROR: The Galaxy API key has not been set.  Please check your')
        print('       configuration in ~/.abm/profile.yml and try again.')
        sys.exit(1)
    key = context.API_KEY
    if use_master_key:
        if context.MASTER_KEY is None:
            print('ERROR: The Galaxy master key has not been set.  Please check your')
            print('       configuration in ~/.abm/profile.yml and try again.')
            sys.exit(1)
        key = context.MASTER_KEY
    gi = bioblend.galaxy.GalaxyInstance(url=context.GALAXY_SERVER, key=key)
    gi.max_get_attempts = 3
    gi.get_retry_delay = 1
    return gi


def _set_active_profile(profile_name: str):
    """
    Unused.

    :param profile_name:
    :return:
    """
    lib.GALAXY_SERVER, lib.API_KEY, lib.KUBECONFIG, lib.MASTER_KEY = parse_profile(
        profile_name
    )
    return lib.GALAXY_SERVER != None


def get_context(profile_name: str):
    return Context(profile_name)


def get_yaml_parser():
    """
    Returns a singleton instance of a YAML parser.

    :return: a YAML parser.
    """
    if lib.parser is None:
        lib.parser = YAML()
    return lib.parser


def load_profiles():
    '''
    Load the profile configuration file.

    :return: a dictionary containing the YAML content of the configuration.
    '''
    yaml = get_yaml_parser()
    profiles = {}
    for profile_path in PROFILE_SEARCH_PATH:
        profile_path = os.path.expanduser(profile_path)
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                # print(f'Loading profile from {profile_path}')
                profiles = yaml.load(f)
            break
    return profiles


def save_profiles(profiles: dict):
    """
    Write the ABM configuration file.

    :param profiles: the configuration to be saved.
    :return: None
    """
    yaml = get_yaml_parser()
    for profile_path in PROFILE_SEARCH_PATH:
        path = os.path.expanduser(profile_path)
        if os.path.exists(path):
            with open(path, 'w') as f:
                yaml.dump(profiles, f)
            print(f"Saved profiles to {path}")
            return


def parse_profile(profile_name: str):
    '''
    Parse the profile containing Galaxy URLs and API keys.

    :param profile_name: path to the profile to parse
    :return: a tuple containing the Galaxy URL, API key, and path to the kubeconfig
    '''
    nones = (None, None, None, None)
    profiles = load_profiles()
    if profiles is None:
        print(f'ERROR: Could not locate an abm profile file in {PROFILE_SEARCH_PATH}')
        return nones
    if profile_name not in profiles:
        print(f'ERROR: {profile_name} is not the name of a valid profile.')
        keys = list(profiles.keys())
        if len(keys) > 0:
            quoted_keys = (
                ', '.join([f"'{k}'" for k in keys[0:-2]]) + f", and '{keys[-1]}'"
            )
            print(f'The defined profile names are: {quoted_keys}')
        return nones
    profile = profiles[profile_name]
    kube = None
    master = 'galaxypassword'
    if 'kube' in profile:
        kube = os.path.expanduser(profile['kube'])
    if 'master' in profile:
        master = profile['master']
    return (profile['url'], profile['key'], kube, master)


def run(command, env: dict = None):
    """
    Runs a command on the local machine.  Used to invoke the helm and kubectl
    executables.

    :param command: the command to be invoked
    :param env: environment variables for the command.
    :return:
    """
    if env is None:
        env = os.environ
    result = subprocess.run(command.split(), capture_output=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode('utf-8').strip())
    return result.stdout.decode('utf-8').strip()


def get_env(context: Context):
    """
    Creates a copy of the environment variables as returned by os.environ.
    :param context: Ignored
    :return: a dictionary of the environment variables
    """
    copy = os.environ.copy()
    for key, value in context.__dict__.items():
        if value is not None:
            copy[key] = value
    return copy


def find_executable(name):
    """
    Used the which command on the local machine to find the full path to an
    executable.

    :param name: the name of a command line executable or script.
    :return: the full path to the executable or an empty string if the executable is not found.
    """
    return run(f"which {name}")


# This is all the job metrics returned by Galaxy
#    "cpuacct.usage",
#     "end_epoch",
#     "galaxy_memory_mb",
#     "galaxy_slots",
#     "memory.failcnt",
#     "memory.limit_in_bytes",
#     "memory.max_usage_in_bytes",
#     "memory.memsw.limit_in_bytes",
#     "memory.memsw.max_usage_in_bytes",
#     "memory.oom_control.oom_kill_disable",
#     "memory.oom_control.under_oom",
#     "memory.soft_limit_in_bytes",
#     "memtotal",
#     "processor_count",
#     "runtime_seconds",
#     "start_epoch",
#     "swaptotal",
#     "uname"

# Columns to be defined when generating CSV files.
table_header = [
    "id",
    "history_id",
    "history_name",
    "state",
    "tool_id",
    "invocation_id",
    "workflow_id",
    "cpuacct.usage",
    # "end_epoch",
    "galaxy_memory_mb",
    "galaxy_slots",
    # "memory.failcnt",
    "memory.limit_in_bytes",
    "memory.peak",
    # "memory.max_usage_in_bytes",
    # "memory.memsw.limit_in_bytes",
    # "memory.memsw.max_usage_in_bytes",
    # "memory.oom_control.oom_kill_disable",
    # "memory.oom_control.under_oom",
    "memory.soft_limit_in_bytes",
    "memtotal",
    "processor_count",
    "runtime_seconds",
    # "start_epoch",
    # "swaptotal",
    # "uname"
]


def print_table_header():
    """
    Prints the table header suitable for inclusion in CSV files.

    :return: None. The table header is printed to stdout.
    """
    print(','.join(table_header))


history_name_cache = dict()


def get_history_name(gi, hid: str) -> str:
    if hid in history_name_cache:
        return history_name_cache[hid]
    history = gi.histories.show_history(hid)
    if history is None:
        return 'unknown'
    name = history['name']
    history_name_cache[hid] = name
    return name


def summarize_metrics(gi, jobs: list):
    table = []
    # table.append(header)
    # print(','.join(header))
    for job in jobs:
        job_metrics = gi.jobs.get_metrics(job['id'])
        row = []
        toolid = job.get('tool_id', 'unknown')
        if '/' in toolid:
            parts = toolid.split('/')
            toolid = f'{parts[-2]}/{parts[-1]}'
        metrics = metrics_to_dict(job_metrics, table_header)
        metrics['id'] = job.get('id', 'unknown')
        hid = job.get('history_id', 'unknown')
        metrics['history_id'] = hid
        metrics['history_name'] = get_history_name(gi, hid)
        metrics['state'] = job.get('state', 'unknown')
        metrics['tool_id'] = toolid
        metrics['invocation_id'] = job.get('invocation_id', 'unknown')
        for key in table_header:
            if key in metrics:
                row.append(metrics[key])
            else:
                row.append('')
        # print(','.join(row), end='\n')
        table.append(row)
    return table


def print_markdown_table(table: list) -> None:
    print('| Tool ID | History | State | Memory (GB) | Runtime (sec)|')
    print('|---|---|---:|---:|---:|')
    GB = 1024 * 1024 * 1024
    for row in table[1:]:
        # memory = ''
        # if row[11] != '':
        #     memory = float(row[11]) / GB
        #     if memory < 0.1:
        #         memory = 0.1
        #     memory = f"{memory:3.1f}"
        history = row[2]
        state = row[3]
        tool_id = row[4]
        # cpu = '' if row[7] == '' else float(row[7]) / 10**9
        memory = '' if row[11] == '' else f"{max(0.1, float(row[11]) / GB):3.1f}"
        runtime = '' if row[15] == '' else f"{max(1, float(row[15])):5.0f}"
        print(f'| {tool_id} | {history} | {state} | {memory} | {runtime} |')


def metrics_to_dict(metrics: list, accept: list):
    result = dict()
    for m in metrics:
        key = m['name']
        if key in accept:
            result[key] = m['raw_value']
    return result


def get_keys(d: dict):
    result = []
    for key in d.keys():
        result.append(key)
    result.sort()
    return result


def find_history(gi, name_or_id):
    history = None
    try:
        history = gi.histories.show_history(name_or_id)
    except:
        pass

    if history is not None:
        return history['id']
    history = gi.histories.get_histories(name=name_or_id)
    if history is None:
        return name_or_id
    if len(history) == 0:
        return None
    return history[0]['id']


def find_dataset(gi, history_id, name_or_id):
    try:
        dataset = gi.datasets.show_dataset(name=name_or_id)
        return dataset['id']
    except:
        pass

    try:
        dataset = gi.datasets.show_dataset(name_or_id)
        return dataset['id']
    except:
        pass
    return None
    # print("Calling get_datasets")
    # datasets = gi.datasets.get_datasets(history_id=history_id, name=name_or_id)
    # if datasets is None:
    #     print("Not found")
    #     return None
    # if len(datasets) == 0:
    #     print("No datasets found (len == 0)")
    #     return None
    # return datasets[0]['id']


def find_config(name: str) -> str:
    if os.path.exists(".abm"):
        if os.path.exists(f".abm/{name}"):
            return f".abm/{name}"
    config = os.path.join(Path.home(), ".abm", name)
    if os.path.exists(config):
        return config
    return None


def _get_dataset_data(gi, name_or_id):
    print(f"Getting dataset data for {name_or_id}")

    def make_result(data):
        return {
            'id': data['id'],
            'size': data['file_size'],
            'history': data['history_id'],
        }

    try:
        ds = gi.datasets.show_dataset(name_or_id)
        print(f"Got dataset data for {name_or_id} {ds['id']}")
        return make_result(ds)
    except Exception as e:
        print(f"Failed to get dataset data for {name_or_id}")
        pass

    try:
        print("Getting all datasets")
        datasets = gi.datasets.get_datasets(
            name=name_or_id
        )  # , deleted=True, purged=True)
        print(f"List of datasets for {name_or_id} is {len(datasets)}")
        for ds in datasets:
            # print_json(ds)
            state = True
            if 'state' in ds:
                state = ds['state'] == 'ok'
            if state and not ds['deleted'] and ds['visible']:
                # The dict returned by get_datasets does not include the input
                # file sizes so we need to make another call to show_datasets
                print(f"Getting dataset data for {ds['id']}")
                return make_result(gi.datasets.show_dataset(ds['id']))
            else:
                print(f"Skipping dataset {ds['id']}")
                print_json(ds)
    except Exception as e:
        pass

    return None


def _make_dataset_element(name, value):
    # print(f"Making dataset element for {name} = {value}({type(value)})")
    return dataset_collections.HistoryDatasetElement(name=name, id=value)


def get_float_key(column: int):
    def get_key(row: list):
        if row[column] == '':
            return -1
        return float(row[column])

    return get_key


def get_str_key(column: int):
    # print(f"Getting string key for column {column}")
    def get_key(row: list):
        # print(f"Sorting by column {column} key {row[column]}")
        return row[column]

    return get_key
