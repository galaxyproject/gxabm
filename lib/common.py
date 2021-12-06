import os
import sys
import yaml
import bioblend.galaxy

GALAXY_SERVER = None
API_KEY = None
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


def connect():
    """
    Create a connection to the Galaxy instance

    :return: a GalaxyInstance object
    """
    if GALAXY_SERVER is None:
        print('ERROR: The Galaxy server URL has not been set.  Please check your')
        print('       configuration in ~/.abm/profile.yml and try again.')
        sys.exit(1)
    if API_KEY is None:
        print('ERROR: The Galaxy API key has not been set.  Please check your')
        print('       configuration in ~/.abm/profile.yml and try again.')
        sys.exit(1)
    return bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)


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
    :return: a tuple containing the Galaxy URL and API key
    '''
    profiles = load_profiles()
    if profiles is None:
        print(f'ERROR: Could not locate an abm profile file in {PROFILE_SEARCH_PATH}')
        return None, None
    if profile_name not in profiles:
        print(f'ERROR: {profile_name} is not the name of a valid profile.')
        keys = list(profiles.keys())
        quoted_keys = ', '.join([f"'{k}'" for k in keys[0:-2]]) + f", and '{keys[-1]}'"
        print(f'The defined profile names are: {quoted_keys}')
        return None, None
    profile = profiles[profile_name]
    return (profile['url'], profile['key'])


