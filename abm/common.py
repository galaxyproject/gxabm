import sys
import bioblend.galaxy

GALAXY_SERVER = None
API_KEY = None

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
        print('ERROR: The Galaxy server URL has not been set.  You must either:')
        print('  1. Configure a profile and put it in ~/.abm/profile.yml')
        print('  2. Set the environment variable GALAXY_SERVER, or')
        print('  3. Pass the server URL with the -s|--server option')
        sys.exit(1)
    if API_KEY is None:
        print('ERROR: The Galaxy API key has not been set.  You must either:')
        print('  1. Configure a profile and put it in ~/.abm/profile.yml')
        print('  2. Set the environment variable API_KEY, or')
        print('  3. Pass the APi key with the -k|--key option')
        sys.exit(1)
    return bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
