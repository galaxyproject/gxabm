import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# TODO: These should be encapsultated into a proper *context* type object.
global GALAXY_SERVER, API_KEY, KUBECONFIG
GALAXY_SERVER = API_KEY = KUBECONFIG = None
INVOCATIONS_DIR = "invocations"
METRICS_DIR = "metrics"


class Keys:
    NAME = 'name'
    RUNS = 'runs'
    INPUTS = 'inputs'
    REFERENCE_DATA = 'reference_data'
    WORKFLOW_ID = 'workflow_id'
    DATASET_ID = 'dataset_id'
    HISTORY_BASE_NAME = 'output_history_base_name'
    HISTORY_NAME = 'history_name'


