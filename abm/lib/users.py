import json

from pprint import pprint
from common import Context, connect


def list(context: Context, args: list):
    # TODO the master API key needs to be parameterized or specified in a config file.
    context.API_KEY = "galaxypassword"
    gi = connect(context)
    user_list = gi.users.get_users()
    pprint(user_list)


def api_key(context: Context, args: list):
    print(get_api_key(context, args))


def get_api_key(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: no user email given")
        return

    # TODO the master API key needs to be parameterized or specified in a config file.
    context.API_KEY = "galaxypassword"
    gi = connect(context)
    user_list = gi.users.get_users(f_email=args[0])
    if user_list is None or len(user_list) == 0:
        print("WARNING: no such user")
        return
    if len(user_list) > 1:
        print("WARNING: more than one user with that email address")
        return
    id = user_list[0]['id']
    key = gi.users.get_user_apikey(id)
    if key is None or key == 'Not available.':
        # print(f"Creating API key for {args[0]}")
        key = gi.users.create_user_apikey(id)
    return key


def create(context: Context, args:list):
    if len(args) != 3:
        print("ERROR: Please specify the username, email, and password")
        return

    name = args[0]
    email: str = args[1]
    password = args[2]
    if not '@' in email:
        print(f"ERROR: {email} does not look like a valid email address")
        return

    # TODO the master API key needs to be parameterized or specified in a config file.
    context.API_KEY = "galaxypassword"
    gi = connect(context)
    user_record = gi.users.create_local_user(name, email, password)
    id = user_record['id']
    key = gi.users.create_user_apikey(id)
    print(f"Created user {name} with API key {key}")
