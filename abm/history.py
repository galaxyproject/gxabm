from common import connect
from pprint import pprint

#
# History related functions
#
def list(args: list):
    gi = connect()
    print('Listing histories')
    for history in gi.histories.get_histories():
        print(f"{history['id']}\t{history['name']}\t{history['deleted']}\t{history['published']}")

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
    if len(args) != 3:
        print("ERROR: Invalid command")
        print(f"USAGE: {sys.argv[0]} history import SERVER HISTORY_ID JEHA_ID")
        return

    server, key = parse_profile(args[0])
    if server is None:
        return
    url = f"{server}history/export_archive?id={args[1]}&jeha_id={args[2]}"
    gi = connect()
    print(f"Importing history from {url}")
    result = gi.histories.import_history(url=url)
    pprint(result)



