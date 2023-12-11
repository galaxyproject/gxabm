import json
import os
import subprocess
import sys

import bioblend.galaxy
import lib
from bioblend.galaxy import dataset_collections
from ruamel.yaml import YAML

PROFILE_SEARCH_PATH = ['~/.abm/profile.yml', '.abm-profile.yml']

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


class Context:
    def __init__(self, *args):
        if len(args) == 1:
            arg = args[0]
            if type(arg) == str:
                self.GALAXY_SERVER, self.API_KEY, self.KUBECONFIG = parse_profile(arg)
            elif type(arg) == dict:
                self.GALAXY_SERVER = arg['GALAXY_SERVER']
                self.API_KEY = arg['API_KEY']
                self.KUBECONFIG = arg['KUBECONFIG']
            else:
                raise Exception(f'Invalid arg for Context: {type(arg)}')
        elif len(args) == 3:
            self.GALAXY_SERVER = args[0]
            self.API_KEY = args[1]
            self.KUBECONFIG = args[2]
        else:
            raise Exception(
                f'Invalid args for Context. Expected one or three, found {len(args)}'
            )


def print_json(obj, indent=2):
    print(json.dumps(obj, indent=indent))


def print_yaml(obj):
    get_yaml_parser().dump(obj, sys.stdout)


def connect(context: Context):
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
    gi = bioblend.galaxy.GalaxyInstance(url=context.GALAXY_SERVER, key=context.API_KEY)
    gi.max_get_attempts = 3
    gi.get_retry_delay = 1
    return gi


def _set_active_profile(profile_name: str):
    # print(f"Parsing profile for {profile_name}")
    lib.GALAXY_SERVER, lib.API_KEY, lib.KUBECONFIG = parse_profile(profile_name)
    return lib.GALAXY_SERVER != None


def get_context(profile_name: str):
    return Context(profile_name)


def get_yaml_parser():
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
    profiles = load_profiles()
    if profiles is None:
        print(f'ERROR: Could not locate an abm profile file in {PROFILE_SEARCH_PATH}')
        return None, None, None
    if profile_name not in profiles:
        print(f'ERROR: {profile_name} is not the name of a valid profile.')
        keys = list(profiles.keys())
        if len(keys) > 0:
            quoted_keys = (
                ', '.join([f"'{k}'" for k in keys[0:-2]]) + f", and '{keys[-1]}'"
            )
            print(f'The defined profile names are: {quoted_keys}')
        return None, None, None
    profile = profiles[profile_name]
    if 'kube' in profile:
        return (profile['url'], profile['key'], os.path.expanduser(profile['kube']))
    return (profile['url'], profile['key'], None)


def run(command, env: dict = None):
    if env is None:
        env = os.environ
    # if env is not None:
    #     for name,value in env.items():
    #         os.environ[name] = value
    # if lib.KUBECONFIG is not None:
    #     os.environ['KUBECONFIG'] = lib.KUBECONFIG
    # local_env = os.environ.copy()
    # local_env.update(env)
    result = subprocess.run(command.split(), capture_output=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode('utf-8').strip())
    return result.stdout.decode('utf-8').strip()


def get_env(context: Context):
    copy = os.environ.copy()
    for key, value in context.__dict__.items():
        if value is not None:
            copy[key] = value
    return copy


def find_executable(name):
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


def summarize_metrics(gi, jobs: list):
    header = [
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
        "memory.max_usage_in_bytes",
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

    print(','.join(header))
    for job in jobs:
        job_metrics = gi.jobs.get_metrics(job['id'])
        row = []
        metrics = metrics_to_dict(job_metrics, header)
        metrics['id'] = job.get('id', 'unknown')
        metrics['history_id'] = job.get('history_id', 'unknown')
        metrics['history_name'] = job.get('history_name', 'unknown')
        metrics['state'] = job.get('state', 'unknown')
        metrics['tool_id'] = job.get('tool_id', 'unknown')
        metrics['invocation_id'] = job.get('invocation_id', 'unknown')
        for key in header:
            if key in metrics:
                row.append(metrics[key])
            else:
                row.append('')
        print(','.join(row), end='\n')


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


def _get_dataset_data(gi, name_or_id):
    def make_result(data):
        return {
            'id': data['id'],
            'size': data['file_size'],
            'history': data['history_id'],
        }

    try:
        ds = gi.datasets.show_dataset(name_or_id)
        return make_result(ds)
    except Exception as e:
        pass

    try:
        datasets = gi.datasets.get_datasets(
            name=name_or_id
        )  # , deleted=True, purged=True)
        for ds in datasets:
            # print_json(ds)
            state = True
            if 'state' in ds:
                state = ds['state'] == 'ok'
            if state and not ds['deleted'] and ds['visible']:
                # The dict returned by get_datasets does not include the input
                # file sizes so we need to make another call to show_datasets
                return make_result(gi.datasets.show_dataset(ds['id']))
    except Exception as e:
        pass

    return None


def _make_dataset_element(name, value):
    # print(f"Making dataset element for {name} = {value}({type(value)})")
    return dataset_collections.HistoryDatasetElement(name=name, id=value)
