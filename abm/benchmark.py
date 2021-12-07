import io
import os
import sys
import time

import yaml
import json
import helm
import common
from common import connect, parse_profile, load_profiles
#from workflow import parse_workflow, find_workflow_id, find_dataset_id, Keys
import workflow

INVOCATIONS_DIR = "invocations"
METRICS_DIR = "metrics"

def run(args: list):
    """
    Runs a single benchmark defined by *args[0]*

    :param args: a list that contains a single element, the path to a benchmark
      configuration file.

    :return: True if the benchmarks completed sucessfully. False otherwise.
    """

    if len(args) == 0:
        print("ERROR: No benchmarking configuration provided.")
        return False

    benchmark_path = args[0]
    if not os.path.exists(benchmark_path):
        print(f"ERROR: Benchmarking configuration not found {benchmark_path}")
        return False

    with open(benchmark_path, 'r') as f:
        config = yaml.load(f)

    profiles = load_profiles()
    num_runs = config['runs']
    for n in range(num_runs):
        print("------------------------")
        print(f"Benchmarking run #{n+1}")
        for cloud in config['cloud']:
            if cloud not in profiles:
                print(f"WARNING: no profile for instance {cloud}")
                continue
            common.GALAXY_SERVER, common.API_KEY, common.KUBECONFIG = parse_profile(cloud)
            if common.KUBECONFIG is None:
                print(f"WARNGING: no kubeconfig for instance {cloud}")
                continue
            for job_conf in config['job_configs']:
                job_conf_path = f"rules/{job_conf}.yml"
                if not helm.update([job_conf_path]):
                    print(f"WARNING: job conf not found {job_conf}")
                    continue
                history_name_prefix = f"Run {n} {job_conf}"
                for workflow_conf in config['workflow_conf']:
                    workflow.run([workflow_conf, history_name_prefix])


    
# def run_single(args: list):
#     """ Runs a single benchmark defined by *args[0]*
#
#     :param args: a list that contains a single element, the path to a benchmark
#       configuration file.
#
#     :return: True if the benchmarks completed sucessfully. False otherwise.
#     """
#     if len(args) == 0:
#         print('ERROR: no workflow configuration specified')
#         return
#     workflow_path = args[0]
#     if not os.path.exists(workflow_path):
#         print(f'ERROR: can not find workflow configuration {workflow_path}')
#         return
#
#     if os.path.exists(INVOCATIONS_DIR):
#         if not os.path.isdir(INVOCATIONS_DIR):
#             print('ERROR: Can not save invocation status, directory name in use.')
#             sys.exit(1)
#     else:
#         os.mkdir(INVOCATIONS_DIR)
#
#     if os.path.exists(METRICS_DIR):
#         if not os.path.isdir(METRICS_DIR):
#             print('ERROR: Can not save metrics, directory name in use.')
#             #sys.exit(1)
#             return False
#     else:
#         os.mkdir(METRICS_DIR)
#
#     gi = connect()
#     workflows = parse_workflow(workflow_path)
#
#     print(f"Found {len(workflows)} workflow definitions")
#     for workflow in workflows:
#         wf_name = workflow[Keys.WORKFLOW_ID]
#         wfid = find_workflow_id(gi, wf_name)
#         if wfid is None:
#             print(f"Unable to load the workflow ID for {workflow[Keys.WORKFLOW_ID]}")
#             return False
#         else:
#             print(f"Found workflow id {wfid}")
#         inputs = {}
#         history_base_name = wfid
#         if Keys.HISTORY_BASE_NAME in workflow:
#             history_base_name = workflow[Keys.HISTORY_BASE_NAME]
#
#         if Keys.REFERENCE_DATA in workflow:
#             for spec in workflow[Keys.REFERENCE_DATA]:
#                 input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
#                 if input is None or len(input) == 0:
#                     print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
#                     return False
#                 dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
#                 print(f"Reference input dataset {dsid}")
#                 inputs[input[0]] = {'id': dsid, 'src': 'hda'}
#
#         count = 0
#         for run in workflow[Keys.RUNS]:
#             count += 1
#             if Keys.HISTORY_NAME in run:
#                 output_history_name = f"{history_base_name} {run[Keys.HISTORY_NAME]}"
#             else:
#                 output_history_name = f"{history_base_name} run {count}"
#             for spec in run[Keys.INPUTS]:
#                 input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
#                 if input is None or len(input) == 0:
#                     print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
#                     return False
#                 dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
#                 print(f"Input dataset ID: {dsid}")
#                 inputs[input[0]] = {'id': dsid, 'src': 'hda'}
#
#             print(f"Running workflow {wfid}")
#             invocation = gi.workflows.invoke_workflow(wfid, inputs=inputs, history_name=output_history_name)
#             id = invocation['id']
#             output_path = os.path.join(INVOCATIONS_DIR, id + '.json')
#             with open(output_path, 'w') as f:
#                 json.dump(invocation, f, indent=4)
#                 print(f"Wrote invocation data to {output_path}")
#             invocations = gi.invocations.wait_for_invocation(id, 86400, 10, False)
#             print("Waiting for jobs")
#             wait_for_jobs(gi, invocations)
#     print("Benchmarking run complete")
#     return True


def test(args: list):
    print(common.GALAXY_SERVER)


def summarize(args: list):
    """
    Parses all the files in the **METRICS_DIR** directory and prints metrics
    as CSV to stdout

    :param args: Ignored
    :return: None
    """
    row = [''] * 12
    for file in os.listdir(METRICS_DIR):
        input_path = os.path.join(METRICS_DIR, file)
        with open(input_path, 'r') as f:
            data = json.load(f)
        row[0] = data['workflow_id']
        row[1] = data['history_id']
        row[2] = data['server'] if data['server'] is not None else 'https://iu1.usegvl.org/galaxy'
        row[3] = data['metrics']['tool_id']
        row[4] = data['metrics']['state']
        add_metrics_to_row(data['metrics']['job_metrics'], row)
        print(','.join(row))


def add_metrics_to_row(metrics_list: list, row: list):
    accept_metrics = ['galaxy_slots', 'galaxy_memory_mb', 'runtime_seconds', 'cpuacct.usage','memory.limit_in_bytes', 'memory.max_usage_in_bytes','memory.soft_limit_in_bytes']
    for job_metrics in metrics_list:
        if job_metrics['name'] in accept_metrics:
            index = accept_metrics.index(job_metrics['name'])
            row[index + 5] = job_metrics['raw_value']




