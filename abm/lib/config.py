from common import load_profiles, save_profiles, get_yaml_parser, Context
from ruamel.yaml import YAML
from pprint import pprint

import kubectl
import users
import sys

def list(context: Context, args: list):
    profiles = load_profiles()
    print(f"Loaded {len(profiles)} profiles")
    for profile in profiles:
        print(f"{profile}\t{profiles[profile]['url']}")


def create(context: Context, args: list):
    if len(args) != 2:
        print("USAGE: abm config create <cloud> /path/to/kube.config")
        return
    profile_name = args[0]
    profiles = load_profiles()
    if profile_name in profiles:
        print("ERROR: a cloud configuration with that name already exists.")
        return
    profiles[profile_name] = { 'url': "", 'key': '', 'kube': args[1]}
    print(get_yaml_parser().dump(profiles, sys.stdout))


def key(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config key <cloud> <key>")
        return
    profile_name = args[0]
    key = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile['key'] = key
    save_profiles(profiles)


def url(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config key <cloud> <url>")
        return
    profile_name = args[0]
    url = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile['url'] = url
    save_profiles(profiles)
