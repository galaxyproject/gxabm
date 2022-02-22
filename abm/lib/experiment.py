import os
import threading
import traceback

import yaml
import json
import helm
import benchmark
import logging
from common import load_profiles, Context

INVOCATIONS_DIR = "invocations"
METRICS_DIR = "metrics"

log = logging.getLogger('abm')

def run(context: Context, args: list):
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
    # latch = CountdownLatch(len(config['cloud']))
    threads = []
    for cloud in config['cloud']:
        if cloud not in profiles:
            print(f"WARNING: No profile found for {cloud}")
            continue
        t = threading.Thread(target=run_on_cloud, args=(cloud, config))
        threads.append(t)
        print(f"Starting thread for {cloud}")
        t.start()
    print('Waiting for threads')
    for t in threads:
        t.join()
    print('All threads have terminated.')

        # if not set_active_profile(cloud):
        #     print(f"ERROR: Unable to set the profile for {cloud}")
        #     continue
        # if lib.KUBECONFIG is None:
        #     print(f"ERROR: No kubeconfig set for {cloud}")
        #     continue
        # print("------------------------")
        # print(f"Benchmarking: {cloud}")
        # for conf in config['job_configs']:
        #     job_conf_path = f"rules/{conf}.yml"
        #     if not helm.update([job_conf_path]):
        #         print(f"WARNING: job conf not found {conf}")
        #         continue
        #     for n in range(num_runs):
        #         history_name_prefix = f"{n} {cloud} {conf}"
        #         for workflow_conf in config['benchmark_confs']:
        #             benchmark.run([workflow_conf, history_name_prefix])

    # for n in range(num_runs):
    #     print("------------------------")
    #     print(f"Benchmarking run #{n+1}")
    #     for cloud in config['cloud']:
    #         if cloud not in profiles:
    #             print(f"WARNING: no profile for instance {cloud}")
    #             continue
    #         if not set_active_profile(cloud):
    #             print(f"WARNING: unable to set {cloud} as the active profile")
    #         if lib.KUBECONFIG is None:
    #             print(f"WARNGING: no kubeconfig for instance {cloud}")
    #             continue
    #         for job_conf in config['job_configs']:
    #             job_conf_path = f"rules/{job_conf}.yml"
    #             if not helm.update([job_conf_path]):
    #                 print(f"WARNING: job conf not found {job_conf}")
    #                 continue
    #             history_name_prefix = f"Run {n} {job_conf}"
    #             for workflow_conf in config['workflow_conf']:
    #                 workflow.run([workflow_conf, history_name_prefix])


def run_on_cloud(cloud: str, config: dict):
    print("------------------------")
    print(f"Benchmarking: {cloud}")
    context = Context(cloud)
    namespace = 'galaxy'
    chart = 'anvil/galaxykubeman'
    if 'galaxy' in config:
        namespace = config['galaxy']['namespace']
        chart = config['galaxy']['chart']
    for conf in config['job_configs']:
        if not helm.update(context, [f"rules/{conf}.yml", namespace, chart]):
            log.warning(f"job configuration not found: rules/{conf}.yml")
            continue
        for n in range(config['runs']):
            history_name_prefix = f"{n} {cloud} {conf}"
            for workflow_conf in config['benchmark_confs']:
                benchmark.run(context, workflow_conf, history_name_prefix, config['name'])


def test(context: Context, args: list):
    print(context.GALAXY_SERVER)
    if os.path.exists(args[0]):
        with open(args[0]) as f:
            data = yaml.safe_load(f)
        print(data)


def parse_toolid(id:str) -> str:
    parts = id.split('/')
    return f"{parts[-2]},{parts[-1]}"


def summarize(context: Context, args: list):
    """
    Parses all the files in the specified directory and prints metrics
    as CSV to stdout

    :param args[0]: The path to the directory containing metrics filees
    :return: None
    """
    separator = None
    input_dir = None
    for arg in args:
        if arg in ['-t', '--tsv']:
            separator = '\t'
        elif arg in ['-c', '--csv']:
            separator = ','
        else:
            input_dir = arg

    if input_dir is None:
        input_dir = 'metrics'

    if separator is None:
        separator = ','

    row = [''] * 14
    #print("Run,Cloud,Job Conf,Workflow,History,Inputs,Server,Tool,Tool Version,State,Slots,Memory,Runtime (Sec),CPU,Memory Limit (Bytes),Memory Max usage (Bytes),Memory Soft Limit")
    print("Run,Cloud,Job Conf,Workflow,History,Inputs,Tool,Tool Version,State,Slots,Memory,Runtime (Sec),CPU,Memory Limit (Bytes),Memory Max usage (Bytes)")
    for file in os.listdir(input_dir):
        input_path = os.path.join(input_dir, file)
        if not os.path.isfile(input_path) or not input_path.endswith('.json'):
            continue
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)
            row[0] = data['run']
            row[1] = data['cloud']
            row[2] = data['job_conf']
            row[3] = data['workflow_id']
            row[4] = data['history_id']
            row[5] = data['inputs']
            #row[6] = data['server'] if data['server'] is not None else 'https://iu1.usegvl.org/galaxy'
            row[6] = parse_toolid(data['metrics']['tool_id'])
            row[7] = data['metrics']['state']
            add_metrics_to_row(data['metrics']['job_metrics'], row)
            print(separator.join(row))
        except Exception as e:
            # Silently fail to allow the remainder of the table to be generated.
            pass


def add_metrics_to_row(metrics_list: list, row: list):
    accept_metrics = ['galaxy_slots', 'galaxy_memory_mb', 'runtime_seconds', 'cpuacct.usage','memory.limit_in_bytes', 'memory.max_usage_in_bytes']  #,'memory.soft_limit_in_bytes']
    for job_metrics in metrics_list:
        if job_metrics['name'] in accept_metrics:
            index = accept_metrics.index(job_metrics['name'])
            row[index + 8] = job_metrics['raw_value']
            # row.append(job_metrics['raw_value'])




