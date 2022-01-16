import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from common import parse_profile

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
            raise Exception(f'Invalid args for Context. Expected one or three, found {len(args)}')



