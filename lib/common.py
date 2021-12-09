import os
import sys
import yaml
import subprocess
import bioblend.galaxy
# from lib import GALAXY_SERVER, API_KEY, KUBECONFIG
import lib

# global GALAXY_SERVER, API_KEY, KUBECONFIG

PROFILE_SEARCH_PATH = ['~/.abm/profile.yml', '.abm-profile.yml']

datasets = {
    "dna": [
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR013/ERR013101/ERR013101_1.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR015/ERR015526/ERR015526_2.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR592/SRR592109/SRR592109_2.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR233/SRR233167/SRR233167_2.fastq.gz",
        "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR047/ERR047678/ERR047678_1.fastq.gz",
        "ftp://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/data/AshkenazimTrio/HG003_NA24149_father/NIST_Illumina_2x250bps/reads/D2_S1_L002_R1_002.fastq.gz"
    ],
    "rna": []
}

# def init():
#     # TODO: These should be encapsultated into a proper *context* type object.
#     GALAXY_SERVER = None
#     API_KEY = None
#     KUBECONFIG = None


def connect():
    """
    Create a connection to the Galaxy instance

    :return: a GalaxyInstance object
    """
    if lib.GALAXY_SERVER is None:
        print('ERROR: The Galaxy server URL has not been set.  Please check your')
        print('       configuration in ~/.abm/profile.yml and try again.')
        sys.exit(1)
    if lib.API_KEY is None:
        print('ERROR: The Galaxy API key has not been set.  Please check your')
        print('       configuration in ~/.abm/profile.yml and try again.')
        sys.exit(1)
    return bioblend.galaxy.GalaxyInstance(url=lib.GALAXY_SERVER, key=lib.API_KEY)


def set_active_profile(profile_name: str):
    lib.GALAXY_SERVER, lib.API_KEY, lib.KUBECONFIG = parse_profile(profile_name)
    return lib.GALAXY_SERVER != None


def load_profiles():
    '''
    Load the profile configuration file.

    :return: a dictionary containing the YAML content of the configuration.
    '''
    profiles = None
    for profile_path in PROFILE_SEARCH_PATH:
        profile_path = os.path.expanduser(profile_path)
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                # print(f'Loading profile from {profile_path}')
                profiles = yaml.safe_load(f)
            break
    return profiles

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
        quoted_keys = ', '.join([f"'{k}'" for k in keys[0:-2]]) + f", and '{keys[-1]}'"
        print(f'The defined profile names are: {quoted_keys}')
        return None, None, None
    profile = profiles[profile_name]
    if 'kube' in profile:
        return (profile['url'], profile['key'], os.path.expanduser(profile['kube']))
    return (profile['url'], profile['key'], None)


def run(command, env:dict=None):
    if env is not None:
        for name,value in env.items():
            os.environ[name] = value
    if lib.KUBECONFIG is not None:
        os.environ['KUBECONFIG'] = lib.KUBECONFIG
    result = subprocess.run(command.split(), capture_output=True, env=os.environ)
    if result.returncode == 0:
        raise RuntimeError(result.stdout.decode('utf-8').strip())


def find_executable(name):
    return run(f"which {name}")


