import json
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Where the workflow invocation data returned by Galaxy will be saved.
INVOCATIONS_DIR = "invocations"
#  Where workflow runtime metrics will be saved.
METRICS_DIR = "metrics"

# Global instance of a YAML parser so we can reuse it if needed.
parser = None


# Keys used in various dictionaries.
class Keys:
    NAME = 'name'
    RUNS = 'runs'
    INPUTS = 'inputs'
    REFERENCE_DATA = 'reference_data'
    WORKFLOW_ID = 'workflow_id'
    DATASET_ID = 'dataset_id'
    COLLECTION = 'collection'
    HISTORY_BASE_NAME = 'output_history_base_name'
    HISTORY_NAME = 'history_name'


# def get_master_api_key():
#     '''
#     Get the master API key from the environment or configuration file.
#     '''
#     if 'GALAXY_MASTER_API_KEY' in os.environ:
#         return os.environ['GALAXY_MASTER_API_KEY']
#     config_path = os.path.expanduser("~/.abm/config.yml")
#     if not os.path.exists(config_path):
#         raise RuntimeError(f"ERROR: Configuration file not found: {config_path}")
#     with open(config_path, 'r') as f:
#         config = yaml.safe_load(f)
#     key = config.get('GALAXY_MASTER_API_KEY', None)
#     if key == None:
#         raise RuntimeError("ERROR: GALAXY_MASTER_API_KEY not found in config.yml")
#     return key
