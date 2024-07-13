import argparse

from common import (Context, connect, get_float_key, get_str_key, print_json,
                    print_markdown_table, print_table_header, print_yaml,
                    summarize_metrics)


def doList(context: Context, args: list):
    wid = None
    hid = None
    while len(args) > 0:
        arg = args.pop(0)
        if args in ['-h', '--history']:
            hid = args.pop(0)
        elif arg in ['-w', '--workflow']:
            wid = args.pop(0)
        else:
            print(f'Invalid parameter: {arg}')
            return
    gi = connect(context)
    invocations = gi.invocations.get_invocations(workflow_id=wid, history_id=hid)
    print('ID\tState\tWorkflow\tHistory')
    for invocation in invocations:
        id = invocation['id']
        state = invocation['state']
        workflow = invocation['workflow_id']
        history = invocation['history_id']
        print(f'{id}\t{state}\t{workflow}\t{history}')


def show(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no invocation ID was provided")
        return
    gi = connect(context)
    invocation = gi.invocations.show_invocation(args[0])
    print_yaml(invocation)


def summarize(context: Context, args: list):
    parser = argparse.ArgumentParser()
    parser.add_argument('id', nargs=1)
    parser.add_argument('--markdown', action='store_true')
    parser.add_argument('-s', '--sort-by', choices=['runtime', 'memory', 'tool'])
    argv = parser.parse_args(args)
    gi = connect(context)
    id = argv.id[0]
    all_jobs = []
    jobs = gi.jobs.get_jobs(invocation_id=id)
    for job in jobs:
        job['invocation_id'] = id
        job['workflow_id'] = ''
        all_jobs.append(job)
    table = summarize_metrics(gi, all_jobs)
    if argv.sort_by:
        reverse = True
        get_key = None
        if argv.sort_by == 'runtime':
            get_key = get_float_key(15)
        elif argv.sort_by == 'memory':
            get_key = get_float_key(11)
        elif argv.sort_by == 'tool':
            get_key = get_str_key(4)
            reverse = False
        table.sort(key=get_key, reverse=reverse)
    if argv.markdown:
        print_markdown_table(table)
    else:
        print_table_header()
        for row in table:
            print(','.join(row))
