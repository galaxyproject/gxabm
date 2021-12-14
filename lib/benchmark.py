import io
import os
import sys
import time

import yaml
import json
import lib
import helm
import common
from common import connect, parse_profile, load_profiles, set_active_profile
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
        config = yaml.safe_load(f)

    profiles = load_profiles()
    num_runs = config['runs']
    for n in range(num_runs):
        print("------------------------")
        print(f"Benchmarking run #{n+1}")
        for cloud in config['cloud']:
            if cloud not in profiles:
                print(f"WARNING: no profile for instance {cloud}")
                continue
            if not set_active_profile(cloud):
                print(f"WARNING: unable to set {cloud} as the active profile")
            if lib.KUBECONFIG is None:
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




