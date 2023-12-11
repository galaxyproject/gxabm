import json
import os
import sys

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# from common import parse_profile

INVOCATIONS_DIR = "invocations"
METRICS_DIR = "metrics"

parser = None


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
