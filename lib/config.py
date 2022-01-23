from common import load_profiles, Context

import kubectl
import users

def list(context: Context, args: list):
    profiles = load_profiles()
    print(f"Loaded {len(profiles)} profiles")
    for profile in profiles:
        print(f"{profile}\t{profiles[profile]['url']}")


def update(context: Context, args: list):
    create = False
    if '-c' in args:
        create = True
        args.remove('-c')
    if '--create' in args:
        create = True
        args.remove('--create')
    if len(args) == 0:
        print("ERROR: no user specified")
        return

    context.GALAXY_SERVER = kubectl.get_url(context, [])
    context.API_KEY = users.get_api_key(context, args)
