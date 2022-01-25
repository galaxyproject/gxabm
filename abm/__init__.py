import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

#__version__="2.0.0-dev6"

def getVersion():
    dir = os.path.dirname(os.path.realpath(__file__))
    version_file = os.path.join(dir, 'VERSION')
    with open(version_file, 'r') as f:
        version = f.read().strip()
    return version
