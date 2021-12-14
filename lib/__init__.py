import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# TODO: These should be encapsultated into a proper *context* type object.
global GALAXY_SERVER, API_KEY, KUBECONFIG
GALAXY_SERVER = API_KEY = KUBECONFIG = None