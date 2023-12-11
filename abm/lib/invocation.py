from common import Context, connect, print_json, summarize_metrics


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


def summarize(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: Provide one or more invocation ID values.")
        return
    gi = connect(context)
    id = args[0]
    all_jobs = []
    jobs = gi.jobs.get_jobs(invocation_id=id)
    for job in jobs:
        job['invocation_id'] = id
        job['workflow_id'] = ''
        all_jobs.append(job)
    summarize_metrics(gi, all_jobs)
