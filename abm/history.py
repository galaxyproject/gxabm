import os
import sys
import yaml

import common
from common import connect, parse_profile
from pprint import pprint

#
# History related functions
#
def list(args: list):
    gi = connect()
    print('Listing histories')
    for history in gi.histories.get_histories():
        print(f"{history['id']}\t{history['name']}\t{history['deleted']}\t{history['published']}")

    if len(args) > 0:
        if args[0] in [ 'all', '-a', '--all' ]:
            print('Histories Published by all users')
            for history in gi.histories.get_published_histories():
                print(f"{history['id']}\t{history['name']}\t{history['deleted']}\t{history['published']}")


def show(args: list):
    gi = connect()
    history = gi.histories.show_history(args[0])
    pprint(history)


def find(args: list):
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
    # global GALAXY_SERVER
    print(f"The history can be imported from {common.GALAXY_SERVER}/history/export_archive?id=9198b7907edea3fa&jeha_id=97cf03bfbaeeac26")


def export(args: list):
    if len(args) == 0:
        print("ERROR: no history ID specified")
        return
    gi = connect()
    jeha_id = gi.histories.export_history(args[0], gzip=True, wait=True)
    global GALAXY_SERVER
    print(f"The history can be imported from {GALAXY_SERVER}/history/export_archive?id={args[0]}&jeha_id={jeha_id}")


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
                error_message()
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


