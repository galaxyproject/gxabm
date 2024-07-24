import argparse
import json
import logging
import os
import threading
import traceback
from datetime import timedelta
from pprint import pprint
from time import perf_counter

import benchmark
import helm
import yaml
from common import (Context, get_float_key, get_str_key, load_profiles,
                    print_markdown_table)

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
    parser = argparse.ArgumentParser()
    parser.add_argument('benchmark_path')
    parser.add_argument('-r', '--run-number', default=-1)
    argv = parser.parse_args(args)

    benchmark_path = argv.benchmark_path

    if not os.path.exists(benchmark_path):
        print(f"ERROR: Benchmarking configuration not found {benchmark_path}")
        return False

    with open(benchmark_path, 'r') as f:
        config = yaml.safe_load(f)
    config['start_at'] = argv.run_number
    print(f"Starting with run number {argv.run_number}")

    profiles = load_profiles()
    threads = []
    start = perf_counter()
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

    end = perf_counter()
    print('All threads have terminated.')
    print(f"Execution time {timedelta(seconds=end - start)}")


def run_on_cloud(cloud: str, config: dict):
    print("------------------------")
    print(f"Benchmarking: {cloud}")
    context = Context(cloud)
    namespace = 'galaxy'
    chart = 'anvil/galaxykubeman'
    start = int(config['start_at'])
    print(f"Staring run number {start}")
    if start < 0:
        start = 1
    print(f"Staring run number {start}")
    end = start + config['runs']
    if 'galaxy' in config:
        namespace = config['galaxy']['namespace']
        chart = config['galaxy']['chart']
    if 'job_configs' in config and len(config['job_configs']) > 0:
        for conf in config['job_configs']:
            rules_file = f"rules/{conf}.yml"
            print(f"Applying {rules_file} namespace:{namespace} chart:{chart}")
            if not helm.update(context, [f"rules/{conf}.yml", namespace, chart]):
                log.warning(f"job configuration not found: rules/{conf}.yml")
                continue
            for workflow_conf in config['benchmark_confs']:
                for n in range(start, end):
                    history_name_prefix = f"{n} {cloud} {conf}"
                    benchmark.run(
                        context, workflow_conf, history_name_prefix, config['name']
                    )
    else:
        for workflow_conf in config['benchmark_confs']:
            for n in range(start, end):
                history_name_prefix = f"{n} {cloud}"
                benchmark.run(
                    context, workflow_conf, history_name_prefix, config['name']
                )


def test(context: Context, args: list):
    print(context.GALAXY_SERVER)
    if os.path.exists(args[0]):
        with open(args[0]) as f:
            data = yaml.safe_load(f)
        print(data)


def parse_toolid(id: str) -> str:
    parts = id.split('/')
    if len(parts) < 2:
        return f"{id},unknown"
    return f"{parts[-2]},{parts[-1]}"


def summarize(context: Context, args: list):
    """
    Parses all the files in the specified directory and prints metrics
    as CSV to stdout

    :param args[0]: The path to the directory containing metrics filees
    :return: None
    """
    markdown = False
    separator = None
    make_row = make_table_row
    header_row = "Run,Cloud,Job Conf,Workflow,History,Inputs,Tool,Tool Version,State,Slots,Memory,Runtime (Sec),CPU,Memory Limit (Bytes),Memory Max usage (Bytes)"

    parser = argparse.ArgumentParser()
    parser.add_argument('dirs', nargs='*')
    parser.add_argument('-c', '--csv', action='store_true')
    parser.add_argument('-t', '--tsv', action='store_true')
    parser.add_argument('-m', '--model', action='store_true')
    parser.add_argument('--markdown', action='store_true')
    parser.add_argument('-s', '--sort-by', choices=['runtime', 'memory', 'tool'])
    argv = parser.parse_args(args)

    count = 0
    if argv.csv:
        separator = ','
        count += 1
    if argv.tsv:
        separator = '\t'
        count += 1
    if argv.model:
        separator = ','
        make_row = make_model_row
        count += 1
    if argv.markdown:
        markdown = True
        count += 1

    if count == 0:
        print("ERROR: no output format selected")
        return
    if count > 1:
        print("ERROR: multiple output formats selected")
        return

    input_dirs = argv.dirs

    if len(input_dirs) == 0:
        input_dirs.append('metrics')

    if separator is None:
        separator = ','

    if markdown:
        print("|Run|Inputs|Job Conf|Tool|State|Runtime (Sec)|Max Memory (GB)|")
        print("|---|---|---|---|---|---:|---:|")
    else:
        print(header_row)

    table = list()
    GB = float(1073741824)
    for input_dir in input_dirs:
        for file in os.listdir(input_dir):
            input_path = os.path.join(input_dir, file)
            if not os.path.isfile(input_path) or not input_path.endswith('.json'):
                continue
            try:
                with open(input_path, 'r') as f:
                    data = json.load(f)
                if data['metrics']['tool_id'] == 'upload1':
                    # print('Ignoring upload tool')
                    continue
                row = make_row(data)
                table.append(row)
            except Exception as e:
                print(f"Unable to process {input_path}")
                print(e)
                traceback.print_exc()
                # Silently fail to allow the remainder of the table to be generated.
                # pass

    reverse = True
    if argv.sort_by:
        comp = get_str_key(6)
        if argv.sort_by == 'runtime':
            # key = 10
            comp = get_float_key(10)
        # elif argv.sort_by == 'cpu':
        #     comp = get_float_comparator(11)
        #     #key = 11
        elif argv.sort_by == 'memory':
            comp = get_float_key(13)
            # key = 13
        elif argv.sort_by == 'tool':
            # print('Getting string key accessor.')
            comp = get_str_key(6)
            reverse = False
        # table.sort(key=lambda row: -1 if row[key] == '' else float(row[key]), reverse=True)
        table.sort(key=comp, reverse=reverse)

    if markdown:
        for row in table:
            runtime = '' if len(row[10]) == 0 else f"{float(row[10]):4.1f}"
            # cpu = '' if len(row[11]) == 0 else f"{float(row[11])/10**9:4.1f}"
            memory = '' if len(row[13]) == 0 else f"{float(row[13])/GB:4.3f}"
            # memory = float(row[13]) / GB
            print(
                f"| {row[0]} | {row[5].split(' ')[0]} |{row[2]} | {row[6]} | {row[7]} | {runtime}  | {memory} |"
            )
    else:
        for row in table:
            print(separator.join([str(x) for x in row]))


accept_metrics = [
    'galaxy_slots',
    'galaxy_memory_mb',
    'runtime_seconds',
    'cpuacct.usage',
    'memory.limit_in_bytes',
    'memory.peak',
    #'memory.max_usage_in_bytes',
]  # ,'memory.soft_limit_in_bytes']


def make_table_row(data: dict):
    row = [
        str(data[key])
        for key in ['run', 'cloud', 'job_conf', 'workflow_id', 'history_id', 'inputs']
    ]
    row.append(parse_toolid(data['metrics']['tool_id']))
    row.append(data['metrics']['state'])
    for e in _get_metrics(data['metrics']['job_metrics']):
        row.append(e)
    return row


def make_model_row(data: dict):
    metrics = data['metrics']
    row = []
    row.append(metrics['id'])
    tool_id = metrics['tool_id']
    row.append(tool_id)
    row.append(tool_id.split('/')[-1])
    row.append(metrics['state'])
    job_metrics = parse_job_metrics(metrics['job_metrics'])
    row.append(job_metrics.get('memory.max_usage_in_bytes', 0))
    row.append(job_metrics.get('cpuacct.usage', 0))
    row.append(job_metrics.get('processor_count', 0))
    row.append(job_metrics.get('galaxy_slots', 0))
    row.append(job_metrics.get('runtime_seconds', 0))
    if len(data['ref_data_size']) == 0:
        row.append('0')
    else:
        row.append(data['ref_data_size'][0])
    for size in data['input_data_size']:
        row.append(size)
    return row


def _get_metrics(metrics: list):
    row = [''] * len(accept_metrics)
    for job_metrics in metrics:
        if job_metrics['name'] in accept_metrics:
            index = accept_metrics.index(job_metrics['name'])
            try:
                row[index] = job_metrics['raw_value']
            except:
                pass
    return row


def add_metrics_to_row(metrics_list: list, row: list):
    for job_metrics in metrics_list:
        if job_metrics['name'] in accept_metrics:
            index = accept_metrics.index(job_metrics['name'])
            try:
                row[index + 8] = job_metrics['raw_value']
            except:
                pass


def parse_job_metrics(metrics_list: list):
    metrics = {}
    for job_metrics in metrics_list:
        metrics[job_metrics['name']] = job_metrics['raw_value']
    return metrics
