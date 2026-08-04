import argparse
import json
import os
import sys
import time
from pathlib import Path
from pprint import pprint

import yaml
from bioblend.galaxy.objects import GalaxyInstance
from lib.common import (
    Context,
    connect,
    find_config,
    find_history,
    get_float_key,
    get_str_key,
    parse_profile,
    print_json,
    print_markdown_table,
    print_table_header,
    summarize_metrics,
    try_for,
)

#
# History related functions
#

# The number of times a failed job will be restarted.
RESTART_MAX = 3


def longest_name(histories: list):
    longest = 0
    for history in histories:
        if len(history['name']) > longest:
            longest = len(history['name'])
    return longest


def pad(value: bool):
    if value:
        return 'True   '
    return 'False  '


def print_histories(histories: list):
    if len(histories) == 0:
        print("There are no available histories.")
        return

    id_width = len(histories[0]['id'])
    name_width = longest_name(histories)

    print(f"{'ID':<{id_width}} {'Name':<{name_width}} Deleted Public  Tags")
    for history in histories:
        print(
            f"{history['id']:<{id_width}} {history['name']:<{name_width}} {pad(history['deleted'])} {pad(history['published'])} {', '.join(history['tags'])}"
        )


def _list(context: Context, args: list):
    gi = connect(context)
    print_histories(gi.histories.get_histories())

    if len(args) > 0:
        if args[0] in ['all', '-a', '--all']:
            print('Histories Published by all users')
            print_histories(gi.histories.get_published_histories())


def show(context: Context, args: list):
    contents = False
    if '-c' in args:
        contents = True
        args.remove('-c')
    if '--contents' in args:
        contents = True
        args.remove('--contents')
    if len(args) == 0:
        print("ERROR: No history ID provided.")
        return
    gi = connect(context)
    hid = find_history(gi, args[0])
    if hid is None:
        print(f"ERROR: No such history {args[0]}")
        return
    history = gi.histories.show_history(hid, contents=contents)
    print(json.dumps(history, indent=4))


def find(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: No history ID provided")
        return
    return_json = False
    history_name = None
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['-j', '--json']:
            return_json = True
        else:
            history_name = arg
    if history_name is None:
        print("ERROR: no history name provided")
        return
    gi = connect(context)
    histories = gi.histories.get_histories(name=history_name)
    if return_json:
        print_json(histories)
    else:
        for history in histories:
            print(f"{history['id']}\t{history['name']}")


def clean(context: Context, args: list):
    gi = connect(context)
    print("Empty histories")
    for history in gi.histories.get_histories():
        info = gi.histories.show_history(history['id'])
        if 'empty' in info:
            if info['empty']:
                print(f"{history['id']}\t{history['name']}")
            else:
                pprint(info)
        else:
            pprint(info)
            return


def download(context: Context, args: list):
    parser = argparse.ArgumentParser()
    parser.add_argument('history', help='History name or ID to download')
    parser.add_argument(
        '-o',
        '--output',
        help='Output file path (default: HISTORY_NAME.tar.gz)',
        default=None,
    )
    argv = parser.parse_args(args)

    gi = connect(context)
    hid = find_history(gi, argv.history)
    if hid is None:
        print(f'ERROR: No such history {argv.history}')
        return

    url = f'{gi.histories._make_url(hid)}/exports'
    response = gi.make_get_request(url)
    if response.status_code != 200:
        print('ERROR: Could not check export status.')
        return

    exports = response.json()
    ready = [e for e in exports if e.get('ready')]
    if not ready:
        print('ERROR: History has not been exported yet.')
        print('Run "abm CLOUD history export HISTORY" first.')
        return

    latest = ready[-1]
    jeha_id = latest['download_url'].rsplit('/', 1)[-1]

    history = gi.histories.show_history(hid, contents=False)
    default_name = history['name'].replace(' ', '_').replace('/', '_') + '.tar.gz'

    if argv.output and os.path.isdir(argv.output):
        outpath = os.path.join(argv.output, default_name)
    elif argv.output:
        outpath = argv.output
    else:
        outpath = default_name

    print(f'Downloading history to {outpath}...')
    with open(outpath, 'wb') as outf:
        gi.histories.download_history(hid, jeha_id, outf)
    file_size = os.path.getsize(outpath)
    print(f'Downloaded {outpath} ({file_size:,} bytes)')


def upload(context: Context, args: list):
    print('history upload not implemented')


def test(context: Context, args: list):
    gi = connect(context)
    gi.datasets.publish_dataset('bbd44e69cb8906b5a5560acb9ce77faa', published=True)


def export(context: Context, args: list):
    wait = True
    if '--no-wait' in args:
        wait = False
        args.remove('--no-wait')
    if '-n' in args:
        wait = False
        args.remove('-w')
    if len(args) == 0:
        print("ERROR: no history ID specified")
        return
    gi = connect(context)
    hid = find_history(gi, args[0])
    jeha_id = gi.histories.export_history(hid, gzip=True, wait=wait)
    # global GALAXY_SERVER
    export_url = "unknown"
    if wait:
        export_url = f"{context.GALAXY_SERVER}/history/export_archive?id={args[0]}&jeha_id={jeha_id}"
        print(f"The history can be imported from {export_url}")
        history = gi.histories.show_history(hid, contents=False)
        tags = history['tags']
        if 'exported' not in tags:
            tags.append('exported')
            gi.histories.update_history(hid, tags=tags)
            print(f"History tagged with: {tags}")

    else:
        print("Please run the following command to obtain the ID of the export job:")
        print("python abm <cloud> job list | grep EXPORT")
        print()
    return export_url


def publish(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: No history ID provided.")
        return
    gi = connect(context)
    result = gi.histories.update_history(find_history(gi, args[0]), published=True)
    print(f"Published: {result['published']}")


def rename(context: Context, args: list):
    if len(args) != 2:
        print("ERROR: Invalid command")
        print("USAGE: rename ID 'new history name'")
        return
    gi = connect(context)
    result = gi.histories.update_history(find_history(gi, args[0]), name=args[1])
    print(f"History renamed to {result['name']}")


def _do_import(gi, url: str, wait: bool = True, name: str = None):
    """Import a single history archive from ``url``.

    Returns the new history id on success, or None on failure. When ``wait`` is
    False the import job is not awaited and the raw job dict is returned instead
    (there is no new history to rename yet).
    """
    print(f"Importing history from {url}")
    # import_history returns the import *job*, not the new history, and Galaxy
    # names the imported history after the archive contents rather than the
    # URL, so identify the created history by diffing the history list.
    before = {h['id'] for h in gi.histories.get_histories()}
    job = gi.histories.import_history(url=url)
    if not wait:
        print(json.dumps(job, indent=4))
        return job

    print(f"Waiting for job {job['id']}")
    try:
        gi.jobs.wait_for_job(job['id'], 86400, 10, False)
        print('Done')
    except:
        return None

    new = [h for h in gi.histories.get_histories() if h['id'] not in before]
    if len(new) != 1:
        print(
            f"WARNING: expected 1 new history after import, found {len(new)}: "
            f"{[h['name'] for h in new]}"
        )
    if not new:
        return None
    history_id = new[0]['id']

    if name:
        gi.histories.update_history(history_id, name=name)
        print(f"Imported history {history_id} renamed to '{name}'")

    return history_id


def _import(context: Context, args: list, name: str = None):
    gi = connect(context)
    return _do_import(gi, args[0], wait=True, name=name)


def _resolve_history_ref(identifier: str, histories: dict):
    """Resolve a history identifier to an archive URL.

    A URL is returned unchanged; any other value is treated as an alias and
    looked up in the ``histories`` mapping loaded from histories.yml. Returns
    None (after printing an error) when the alias is unknown.
    """
    if identifier.startswith('http'):
        return identifier
    if not histories or identifier not in histories:
        print(f"ERROR: No such history {identifier}")
        return None
    return histories[identifier]


def himport(context: Context, args: list):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-n',
        '--no-wait',
        action='store_true',
        help='Do not wait for the import to complete',
        default=False,
    )
    parser.add_argument(
        '-f',
        '--file',
        help='Use the specified histories.yml file',
        required=False,
        default=None,
    )
    parser.add_argument(
        '-r',
        '--name',
        help='Rename the imported history to this name',
        required=False,
        default=None,
    )
    parser.add_argument(
        'identifiers',
        nargs='+',
        help='One or more history aliases or URLs to import',
    )
    argv = parser.parse_args(args)

    wait = not argv.no_wait
    # Renaming targets a single imported history, so it cannot be combined with
    # multiple identifiers, and it needs the import to complete first.
    if argv.name and len(argv.identifiers) > 1:
        print("ERROR: --name can only be used when importing a single history")
        return False
    if argv.name and not wait:
        print(
            "ERROR: --name requires waiting for the import to complete (remove --no-wait)"
        )
        return False

    # Load the histories.yml config once, only if an alias needs resolving.
    histories = None
    if any(not ident.startswith('http') for ident in argv.identifiers):
        config = argv.file if argv.file is not None else find_config("histories.yml")
        if config is None:
            print("ERROR: No histories.yml file found.")
            return False
        with open(config, 'r') as f:
            histories = yaml.safe_load(f)

    gi = connect(context)
    all_ok = True
    for identifier in argv.identifiers:
        url = _resolve_history_ref(identifier, histories)
        if url is None:
            all_ok = False
            continue
        try:
            result = _do_import(gi, url, wait=wait, name=argv.name)
        except Exception as e:
            print(f"ERROR: failed to import history from {url}: {e}")
            all_ok = False
            continue
        if wait and result is None:
            all_ok = False
    return all_ok


def create(context: Context, args: list):
    if len(args) != 1:
        print("ERROR: Please provide a history name")
        return
    gi = connect(context)
    id = gi.histories.create_history(args[0])
    print(json.dumps(id, indent=4))


def delete(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: please provide one or more history IDs or names')
        return
    gi = connect(context)
    for identifier in args:
        history = find_history(gi, identifier)
        if history is None:
            print(f"ERROR: No such history {identifier}")
            continue
        gi.histories.delete_history(history, True)
        print(f"Deleted history {identifier}")


def copy(context: Context, args: list):
    if len(args) != 2:
        print("ERROR: Invalid parameters. Provide a history ID and new history name.")
        return
    id = find_history(args[0])
    name = args[1]

    gi = connect(context)
    new_history = gi.histories.create_history(name)
    datasets = gi.datasets.get_datasets(history_id=id)
    for dataset in datasets:
        gi.histories.copy_dataset(new_history['id'], dataset['id'])
    print(json.dumps(new_history, indent=4))


def purge(context: Context, args: list):
    if len(args) != 1:
        print("ERROR: Please pass a string used to filter histories to be deleted.")
        print("Use 'abm <cloud> history purge *' to remove ALL histories.")
        return
    all = args[0] == '0'
    gi = connect(context)
    print('Purging histories')
    count = 0
    for history in gi.histories.get_histories():
        if all or args[0] in history['name']:
            gi.histories.delete_history(history['id'], True)
            print(f"Deleted user history {history['id']}")
            count += 1
    for history in gi.histories.get_published_histories():
        if all or args[0] in history['name']:
            gi.histories.delete_history(history['id'], True)
            print(f"Deleted published history {history['id']}")
            count += 1
    print(f'Purged {count} histories')


def tag(context: Context, args: list):
    replace = False
    if '--replace' in args:
        replace = True
        args.remove('--replace')
    if '-r' in args:
        replace = True
        args.remove('-r')
    if len(args) < 2:
        print(
            "ERROR: Invalid command. Please provide the history ID and one or more tags."
        )
        return

    gi = connect(context)
    hid = find_history(gi, args.pop(0))
    if not replace:
        history = gi.histories.show_history(hid, contents=False)
        args += history['tags']
    gi.histories.update_history(hid, tags=args)
    print(f"Set history tags to: {', '.join(args)}")


def summarize(context: Context, args: list):
    parser = argparse.ArgumentParser()
    parser.add_argument('id_list', nargs='+')
    parser.add_argument('--markdown', action='store_true')
    parser.add_argument('-s', '--sort-by', choices=['runtime', 'memory', 'tool'])
    argv = parser.parse_args(args)

    if len(argv.id_list) == 0:
        print("ERROR: Provide one or more history ID values.")
        return
    gi = connect(context)
    all_jobs = []
    id_list = argv.id_list
    while len(id_list) > 0:
        hid = find_history(gi, id_list.pop(0))
        history = gi.histories.show_history(history_id=hid)
        jobs = gi.jobs.get_jobs(history_id=hid)
        for job in jobs:
            job['invocation_id'] = ''
            job['history_id'] = hid
            job['history_name'] = history['name']
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


def wait(context: Context, args: list):
    state = ''
    if len(args) == 0:
        print("ERROR: No history ID provided")
        return

    gi = connect(context)
    history_id = find_history(gi, args[0])
    if history_id is None:
        print("ERROR: No such history")
        return
    wait_for(gi, history_id)


def kill_all_jobs(gi: GalaxyInstance, job_list: list):
    cancel_states = ['new', 'running', 'paused']
    for job in job_list:
        if job['state'] in cancel_states:
            print(f"Cancelling job {job['tool_id']}")
            gi.jobs.cancel_job(job['id'])
        else:
            print(
                f"Job {job['id']} for tool {job['tool_id']} is in state {job['state']}"
            )


def wait_for(gi: GalaxyInstance, history_id: str):
    errored = []
    waiting = True
    job_states = JobStates()
    restart_counts = dict()
    while waiting:
        restart = []
        status_counts = dict()
        terminal = 0
        job_list = try_for(lambda: gi.jobs.get_jobs(history_id=history_id))
        for job in job_list:
            job_states.update(job)
            state = job['state']
            id = job['id']
            # Count how many jobs are in each state.
            if state not in status_counts:
                status_counts[state] = 1
            else:
                status_counts[state] += 1
            # Count jobs in a terminal state and mark failed jobs for a restart
            if state == 'ok':
                terminal += 1
            elif state == 'error':
                terminal += 1
                if id not in errored:
                    tool = job['tool_id']
                    if tool in restart_counts:
                        restart_counts[tool] += 1
                    else:
                        restart_counts[tool] = 1
                    if restart_counts[tool] < RESTART_MAX:
                        restart.append(id)
                    else:
                        kill_all_jobs(gi, job_list)
                        waiting = False
                    errored.append(id)
        if len(restart) > 0 and waiting:
            for job in restart:
                print(f"Restaring job {job}")
                try:
                    gi.jobs.rerun_job(job, remap=True)
                except:
                    try:
                        gi.jobs.rerun_job(job, remap=False)
                    except:
                        print(f"Failed to restart job {job}")
                        waiting = False
        elif len(job_list) == terminal:
            print("All jobs are in a terminal state")
            waiting = False
        if waiting:
            time.sleep(30)


class JobStates:
    def __init__(self):
        self._jobs = dict()

    def update(self, job):
        id = job['id']
        state = job['state']
        tool = job['tool_id']
        if '/' in tool:
            tool = tool.split('/')[-2]
        if id not in self._jobs:
            print(f"Job {id} {tool} state {state}")
        elif state != self._jobs[id]:
            print(f"Job {id} {tool} {self._jobs[id]} -> {state}")
        self._jobs[id] = state
