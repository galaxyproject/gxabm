from common import load_profiles
from pprint import pprint


def list(args: list):
    profiles = load_profiles()
    print(f"Loaded {len(profiles)} profiles")
    for profile in profiles:
        print(f"{profile}\t{profiles[profile]['url']}")

