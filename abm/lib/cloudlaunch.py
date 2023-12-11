import configparser
import json
import os
import traceback

import arrow
import requests
from cloudlaunch_cli.main import create_api_client
from common import Context

BOLD = '\033[1m'
CLEAR = '\033[0m'


def h1(text):
    return f"{BOLD}{text}{CLEAR}"


list_help = f'''
{h1('NAME')}
    list
    
{h1('DESCRIPTION')}
    Lists deployments
    
{h1('SYNOPSIS')}
    abm cloudlaunch list [OPTIONS]
    
{h1('OPTIONS')}
    -a, --archived  list deployments that have been archived
    -r, --running   list running deployments
    -d, --deleted   list deleted deployments
    -l, --launch    list deploymentes that are launching or have launched
    -n, --limit     limit output to N lines
    -h, --help      print this help message
    
{h1('NOTES')}
    The --archived, --running, and --deleted options are mutually exclusive.
    
'''


def list(context: Context, args: list):
    archived = False
    filter = None
    status = lambda t: t.instance_status if t.instance_status else t.status
    n = None
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['-a', '--archived', 'archived']:
            archived = True
        elif arg in ['-r', '--running', 'running']:
            filter = lambda d: 'running' in status(d.latest_task) or (
                'LAUNCH' == d.latest_task.action and 'SUCCESS' == status(d.latest_task)
            )
        elif arg in ['-d', '--deleted', 'deleted']:
            filter = lambda d: 'DELETE' in d.latest_task.action
        elif arg in ['-l', '--launch', 'launch']:
            filter = lambda d: 'LAUNCH' in d.latest_task.action
        elif arg in ['-n', '--limit', 'limit']:
            n = int(args.pop(0))
        elif arg in ['-h', '--help', 'help']:
            print(list_help)
            return
        else:
            print(f"Invalid parameter: {arg}")
            return
    deployments = create_api_client().deployments.list(archived=archived)

    if filter is not None:
        deployments = [d for d in deployments if filter(d)]

    if n is not None and len(deployments) > n:
        deployments = deployments[:n]
    _print_deployments(deployments)


def create(context: Context, args: list):
    cloud = None
    region = None
    params = {'application': 'cloudman-20', 'application_version': 'dev'}
    config = {
        "config_cloudlaunch": {
            "rootStorageType": "volume",
            "rootStorageSize": 42,
            "keyPair": "",
        },
        "config_cloudman2": {"clusterPassword": "gvl_letmein"},
    }
    targets = {'aws': 11, 'gcp': 16}
    regions = {
        'aws': {
            'us-east-1': 11,
            'us-east-2': 12,
            'us-west-1': 13,
            'us-west-2': 14,
            'us-east-1b': 36,
        },
        'gcp': {'us-central1': 16},
    }
    while len(args) > 0:
        arg = args.pop(0)
        if arg in ['aws', 'gcp']:
            if cloud is not None:
                print(f"ERROR: the cloud provider has already been specified: {cloud}")
                return
            cloud = arg
            # params['deployment_target_id'] = targets[cloud]
        elif arg in ['-c', '--config']:
            filepath = args.pop(0)
            with open(filepath, 'r') as f:
                params['config_app'] = json.load(f)
        elif arg in ['-t', '--type']:
            config['config_cloudlaunch']['vmType'] = args.pop(0)
        elif arg in ['-k', '--kp', '--keypair']:
            config['config_cloudlaunch']['keyPair'] = args.pop(0)
        elif arg in ['-p', '--password']:
            config['config_cloudman2']['clusterPassword'] = args.pop(0)
        elif arg in ['-r', '--region']:
            region = args.pop(0)
        elif 'name' in params:
            print(
                f"ERROR: the cluster name has already been specified: {params['name']}"
            )
            return
        else:
            params['name'] = arg

    params['config_app'] = config
    if 'name' not in params:
        print("ERROR: cluster name not specifed")
        return
    if cloud is None:
        print("ERROR: cloud provider not specied. Must be one of 'aws' or 'gcp'")
        return
    if region is not None:
        if cloud not in regions:
            print("ERROR: No regions have been defined for cloud provider {cloud")
            return
        if region not in regions[cloud]:
            print(f"ERROR: Region {region} has not been defined for {cloud}")
            return
        params['deployment_target_id'] = regions[cloud][region]

    # If the deployment target (region) has not been specified on the command
    # line use the default for that provider.
    if 'deployment_target_id' not in params:
        params['deployment_target_id'] = targets[cloud]

    if 'vmType' not in config['config_cloudlaunch']:
        print("ERROR: please specify a VM type.")
        return
    print(f"Deployment target id {params['deployment_target_id']}")
    cloudlaunch_client = create_api_client(cloud)
    try:
        new_deployment = cloudlaunch_client.deployments.create(**params)
        _print_deployments([new_deployment])
    except Exception as e:
        print("Unable to launch the cluster")
        # traceback.print_tb(e.__traceback__)
        print(e)


def delete(context: Context, args: list):
    if len(args) == 0:
        print("ERROR: Invalid parameters.")
        return
    # if args[0] not in ['aws', 'gcp']:
    #     print(f"ERROR: Invalid cloud specified: '{args[0]}'. Must be one of 'aws' or 'gcp'.")
    #     return
    # id = args[0]
    configfile = os.path.expanduser("~/.cloudlaunch")
    if not os.path.exists(configfile):
        print("ERROR: Cloudlaunch has not been configured.")
        return

    config = configparser.ConfigParser()
    config.read(configfile)

    # cloudlaunch_client = create_api_client(args[0])
    # cloudlaunch_client.deployments.delete(args[1])
    url = config['cloudlaunch-cli']['url']
    token = config['cloudlaunch-cli']['token']
    headers = {
        'Accept': 'application/json',
        'Content-type': 'application/json',
        'Authorization': f"Token {token}",
    }

    data = dict(action='DELETE')
    for id in args:
        print(f"URL is: {url}/deployments/{id}/tasks/")
        response = requests.post(
            f"{url}/deployments/{id}/tasks/", json=data, headers=headers
        )
        if response.status_code < 300:
            print(f"Deleted deployment {id}")
        else:
            print(f"{response.status_code} - {response.reason}")
            print(response.text)
        print()


def _print_deployments(deployments):
    if len(deployments) > 0:
        print(
            "{:6s}  {:24s}  {:6s}  {:15s}  {:15s} {:s}".format(
                "ID", "Name", "Cloud", "Created", "Address", "Status"
            )
        )
    else:
        print("No deployments.")
    for deployment in deployments:
        created_date = arrow.get(deployment.added)
        latest_task = deployment.latest_task
        latest_task_status = (
            latest_task.instance_status
            if latest_task.instance_status
            else latest_task.status
        )
        latest_task_display = "{action}:{latest_task_status}".format(
            action=latest_task.action, latest_task_status=latest_task_status
        )
        ip_address = deployment.public_ip if deployment.public_ip else 'N/A'
        cloud = deployment._data['deployment_target']['target_zone']['cloud']['id']
        print(
            "{identifier:6d}  {name:24.24s}  {cloud:6.6s}  {created_date:15.15s}  "
            "{ip_address:15.15s} {latest_task_display}".format(
                identifier=deployment._id,
                cloud=cloud,
                created_date=created_date.humanize(),
                latest_task_display=latest_task_display,
                ip_address=ip_address,
                **deployment._data,
            )
        )
        # pprint(deployment._data)
        # print()
