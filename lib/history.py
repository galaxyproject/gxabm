import os
import sys
import yaml

# import common
from .common import connect, parse_profile, GALAXY_SERVER
from pprint import pprint

#
# History related functions
#

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
    id_width = len(histories[0]['id'])
    name_width = longest_name(histories)

    print(f"{'ID':<{id_width}} {'Name':<{name_width}} Deleted Public  Tags" )
    for history in histories:
        print(f"{history['id']:<{id_width}} {history['name']:<{name_width}} {pad(history['deleted'])} {pad(history['published'])} {', '.join(history['tags'])}")


def list(args: list):
    gi = connect()
    print_histories(gi.histories.get_histories())

    if len(args) > 0:
        if args[0] in [ 'all', '-a', '--all' ]:
            print('Histories Published by all users')
            print_histories(gi.histories.get_published_histories())


def show(args: list):
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
    gi = connect()
    history = gi.histories.show_history(args[0], contents=contents)
    pprint(history)


def find(args: list):
    if len(args) == 0:
        print("ERROR: No history ID provided")
        return
    gi = connect()
    for history in gi.histories.get_histories(name=args[0]):
        print(f"{history['id']}\t{history['name']}")


def clean(args: list):
    gi = connect()
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


def download(args: list):
    print('history download not implemented')


def upload(args: list):
    print('history upload not implemented')


def test(args: list):
    gi = connect()
    gi.datasets.publish_dataset('bbd44e69cb8906b5a5560acb9ce77faa', published=True)


def export(args: list):
    wait = True
    if '--no-wait' in args:
        wait = False
        args.remove('--no-wait')
    if  '-n' in args:
        wait = False
        args.remove('-w')
    if len(args) == 0:
        print("ERROR: no history ID specified")
        return
    hid = args[0]
    gi = connect()
    jeha_id = gi.histories.export_history(hid, gzip=True, wait=wait)
    # global GALAXY_SERVER
    export_url = "unknown"
    if wait:
        export_url = f"{GALAXY_SERVER}/history/export_archive?id={args[0]}&jeha_id={jeha_id}"
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


def publish(args: list):
    if len(args) == 0:
        print("ERROR: No history ID provided.")
        return
    gi = connect()
    result = gi.histories.update_history(args[0], published=True)
    print(f"Published: {result['published']}")


def rename(args: list):
    if len(args) != 2:
        print("ERROR: Invalid command")
        print("USAGE: rename ID 'new history name'")
        return
    gi = connect()
    result = gi.histories.update_history(args[0], name=args[1])
    print(f"History renamed to {result['name']}")


def _import(args: list):
    gi = connect()
    result = gi.histories.import_history(url=args[0])
    pprint(result)


def himport(args: list):
    def error_message(msg = 'Invalid command'):
        print(f"ERROR: {msg}")
        print(f"USAGE: {sys.argv[0]} history import SERVER HISTORY_ID JEHA_ID")
        print(f"       {sys.argv[0]} history import http://GALAXY_SERVER_URL")

    if len(args) == 1:
        if 'http' in args[0]:
            url = args[0]
        else:
            config = f'{os.path.dirname(__file__)}/histories.yml'
            if not os.path.exists(config):
                error_message('The histories config file was not found.')
                return
            with open(config, 'r') as f:
                datasets = yaml.load(f)
            if not args[0] in datasets:
                error_message('Please specify a URL or name of the history to import')
                return
            url = datasets[args[0]]
    elif len(args) == 3:
        server, key = parse_profile(args[0])
        if server is None:
            error_message(f"Invalid server profile name: {args[0]}")
            return
        url = f"{server}history/export_archive?id={args[1]}&jeha_id={args[2]}"
    else:
        error_message()
        return

    gi = connect()
    print(f"Importing history from {url}")
    result = gi.histories.import_history(url=url)
    pprint(result)


def delete(args:list):
    if len(args) != 1:
        print('ERROR: please provide the history ID')
        return
    gi = connect()
    gi.histories.delete_history(args[0], True)
    print(f"Deleted history {args[0]}")


def purge(args:list):
    if len(args) != 1:
        print("ERROR: Please pass a string used to filter histories to be deleted.")
        print("Use 'abm <cloud> history purge *' to remove ALL histories.")
        return
    all = args[0] == '0'
    gi = connect()
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


def tag(args: list):
    replace = False
    if '--replace' in args:
        replace = True
        args.remove('--replace')
    if '-r' in args:
        replace = True
        args.remove('-r')
    if len(args) < 2:
        print("ERROR: Invalid command. Please provide the history ID and one or more tags.")
        return

    gi = connect()
    hid = args.pop(0)
    if not replace:
        history = gi.histories.show_history(hid, contents=False)
        args += history['tags']
    gi.histories.update_history(hid, tags=args)
    print(f"Set history tags to: {', '.join(args)}")