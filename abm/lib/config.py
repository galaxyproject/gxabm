import argparse
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import timedelta

import yaml
from common import (
    Context,
    connect,
    find_config,
    get_yaml_parser,
    load_profiles,
    print_json,
    print_yaml,
    save_config,
    save_profiles,
)

# Import functions for bootstrap functionality
from . import dataset, history, workflow

# Terra workspace integration
try:
    # Import our Python 3.12 compatibility patch first
    from . import terra_compat
    from anvilfs.anvilfs import AnVILFS
    TERRA_AVAILABLE = True
except ImportError:
    TERRA_AVAILABLE = False


def do_list(context: Context, args: list):
    profiles = load_profiles()
    print(f"Loaded {len(profiles)} profiles")
    for profile in profiles:
        print(f"{profile}\t{profiles[profile]['url']}")


def create(context: Context, argv: list):
    parser = argparse.ArgumentParser(prog='abm config create')
    parser.add_argument('profile_name', help='name of the profile to create')
    parser.add_argument('kube_path', nargs='?', help='path to kubeconfig file (backwards compatibility)')
    parser.add_argument('--url', help='Galaxy server URL')
    parser.add_argument('--key', help='Galaxy API key')
    parser.add_argument('--kube', help='path to kubeconfig file')

    args = parser.parse_args(argv)

    profiles = load_profiles()
    if args.profile_name in profiles:
        print("ERROR: a cloud configuration with that name already exists.")
        return

    # Handle backwards compatibility: if kube_path is provided as positional argument, use it
    kube_value = ""
    if args.kube_path:
        kube_value = args.kube_path
    elif args.kube:
        kube_value = args.kube

    profile = {"url": args.url or "", "key": args.key or "", "kube": kube_value}

    profiles[args.profile_name] = profile
    save_profiles(profiles)
    print_json(profile)


def remove(context: Context, args: list):
    if len(args) == 0:
        print("USAGE: abm config remove <cloud> [<cloud>...]")
        return
    profiles = load_profiles()
    for profile_name in args:
        if profile_name in profiles:
            del profiles[profile_name]
        else:
            print("ERROR: now cloud configuration with that name.")
    save_profiles(profiles)
    print_yaml(profiles)


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
    profile["key"] = key
    save_profiles(profiles)
    print_json(profile)


def url(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config url <cloud> <url>")
        return
    profile_name = args[0]
    url = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile["url"] = url
    save_profiles(profiles)
    print_json(profile)


def kube(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config kube <cloud> <kube_path>")
        return
    profile_name = args[0]
    kube_path = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile["kube"] = kube_path
    save_profiles(profiles)
    print_json(profile)


def show(context: Context, args: list):
    if len(args) != 1:
        print("USAGE: abm config show <cloud>")
        return
    profiles = load_profiles()
    if args[0] not in profiles:
        print(f"ERROR: No such cloud {args[0]}")
        return
    print_json(profiles[args[0]])


def workflows(context: Context, args: list):
    # userfile = os.path.join(Path.home(), ".abm", "workflows.yml")
    userfile = find_config("workflows.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import workflows.")
        return
    workflows = _load_config(userfile)
    if workflows is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Workflows defined in {userfile}")
        for key, url in workflows.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        if len(args) != 2:
            print("USAGE: abm config workflows delete <workflow>")
            return
        id = args[1]
        if id not in workflows:
            print(f"ERROR: No such workflow {id}")
            return
        url = workflows[id]
        del workflows[id]
        print(f"Removed workflow {id} -> {url}.")
        save = True
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config workflows add <workflow> <url>")
            return
        id = args[1]
        if id in workflows:
            print(f"ERROR: Workflow {id} already exists.")
            return
        url = args[2]
        workflows[id] = url
        print(f"Added workflow {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, workflows)


def datasets(context: Context, args: list):
    # userfile = os.path.join(Path.home(), ".abm", "datasets.yml")
    userfile = find_config("datasets.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import datasets.")
        return
    datasets = _load_config(userfile)
    if datasets is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Datasets defined in {userfile}")
        for key, url in datasets.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        id = args[1]
        if id not in datasets:
            print(f"ERROR: No such dataset {id}")
            return
        url = datasets[id]
        del datasets[id]
        print(f"Removed dataset {id} -> {url}.")
        save = True
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config datasets add <dataset> <url>")
            return
        id = args[1]
        if id in datasets:
            print(f"ERROR: Dataset {id} already exists.")
            return
        url = args[2]
        datasets[id] = url
        print(f"Added dataset {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, datasets)


def histories(context: Context, args: list):
    userfile = find_config("histories.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import histories.")
        return
    histories = _load_config(userfile)
    if histories is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Datasets defined in {userfile}")
        for key, url in histories.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        if len(args) != 2:
            print("USAGE: abm config histories delete <history>")
            return
        id = args[1]
        if id not in histories:
            print(f"ERROR: No such history {id}")
            return
        url = histories[id]
        del histories[id]
        save = True
        print(f"Removed history {id} -> {url}.")
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config histories add <history> <url>")
            return
        id = args[1]
        if id in histories:
            print(f"ERROR: History {id} already exists.")
            return
        url = args[2]
        histories[id] = url
        print(f"Added history {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, histories)


def _load_config(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: configuration file not found: {filepath}")
        return None
    with open(filepath, "r") as f:
        return yaml.safe_load(f)


def _extract_filename_from_url(url: str) -> str:
    """Extract filename from URL for dataset naming."""
    return Path(url).name


def _detect_datatype_from_extension(filename: str) -> Optional[str]:
    """Detect Galaxy datatype from file extension."""
    extension_map = {
        '.fastq.gz': 'fastqsanger.gz',
        '.fastq': 'fastqsanger',
        '.fq.gz': 'fastqsanger.gz',
        '.fq': 'fastqsanger',
        '.bam': 'bam',
        '.sam': 'sam',
        '.tsv': 'tabular',
        '.csv': 'csv',
        '.html': 'html',
        '.txt': 'txt',
        '.bed': 'bed',
        '.gtf': 'gtf',
        '.gff': 'gff',
        '.vcf': 'vcf',
        '.bcf': 'bcf',
        '.h5': 'h5',
        '.hdf5': 'h5',
        '.json': 'json',
        '.xml': 'xml'
    }

    filename_lower = filename.lower()
    for ext, datatype in extension_map.items():
        if filename_lower.endswith(ext):
            return datatype
    return None


def _filter_files_by_pattern(files: List[Dict[str, Any]], pattern: str) -> List[Dict[str, Any]]:
    """Filter files by glob-style pattern against filename."""
    # Convert glob pattern to regex
    regex_pattern = pattern.replace("*", ".*").replace("?", ".")
    regex = re.compile(f"^{regex_pattern}$")

    # Match against filename (name field) rather than full path
    return [f for f in files if regex.match(f.get("name", ""))]


def _process_terra_workspaces(gi, terra_workspaces):
    """Process Terra workspace configurations and import datasets."""
    if not TERRA_AVAILABLE:
        print("ERROR: Terra workspace support not available. Install fs.anvilfs package.")
        return

    for workspace_config in terra_workspaces:
        namespace = workspace_config.get('namespace')
        workspace_name = workspace_config.get('workspace')

        if not namespace or not workspace_name:
            print(f"ERROR: Terra workspace config missing 'namespace' or 'workspace': {workspace_config}")
            continue

        print(f"Processing Terra workspace: {namespace}/{workspace_name}")

        try:
            # Connect to Terra workspace via fs.anvilfs
            anvil_fs = AnVILFS(namespace, workspace_name)

            # Process dataset import configurations
            datasets_config = workspace_config.get('datasets', {})
            for history_name, dataset_patterns in datasets_config.items():
                print(f"  Processing history: {history_name}")

                # Get or create the named history
                histories = gi.histories.get_histories(name=history_name)
                if histories:
                    dataset_history = histories[0]['id']
                    print(f"    Using existing history: {history_name}")
                else:
                    new_history = gi.histories.create_history(name=history_name)
                    dataset_history = new_history['id']
                    print(f"    Created new history: {history_name}")

                # Process each dataset pattern
                for pattern_config in dataset_patterns:
                    if isinstance(pattern_config, str):
                        # Simple pattern string
                        pattern = pattern_config
                        custom_datatype = None
                    elif isinstance(pattern_config, dict):
                        # Dictionary with pattern and optional datatype
                        pattern = pattern_config.get('pattern')
                        custom_datatype = pattern_config.get('datatype')
                        if not pattern:
                            print(f"    ERROR: pattern config missing 'pattern' field: {pattern_config}")
                            continue
                    else:
                        print(f"    ERROR: invalid pattern config: {pattern_config}")
                        continue

                    print(f"    Looking for files matching: {pattern}")

                    try:
                        # Parse pattern to extract directory path and filename pattern
                        pattern_path = Path(pattern)
                        if pattern_path.parent != Path("."):
                            # Pattern has directory path (e.g., "Tables/sample/*.fastq")
                            scan_dir = str(pattern_path.parent)
                            filename_pattern = pattern_path.name
                        else:
                            # Pattern is just filename (e.g., "*.fastq")
                            scan_dir = "/"
                            filename_pattern = pattern

                        print(f"      Scanning directory: {scan_dir}")
                        print(f"      Filename pattern: {filename_pattern}")

                        # List files in the specific directory
                        all_files = []
                        try:
                            for file_info in anvil_fs.scandir(scan_dir):
                                if file_info.is_file:
                                    full_path = f"{scan_dir.rstrip('/')}/{file_info.name}".replace("//", "/")
                                    all_files.append({
                                        "path": full_path,
                                        "name": file_info.name,
                                        "size": file_info.size if hasattr(file_info, 'size') else 0
                                    })
                        except Exception as e:
                            print(f"      ERROR scanning directory {scan_dir}: {e}")
                            continue

                        # Filter files by filename pattern
                        matching_files = _filter_files_by_pattern(all_files, filename_pattern)
                        print(f"    Found {len(matching_files)} matching files")

                        # Import each matching file
                        for file_info in matching_files:
                            file_path = file_info["path"]
                            file_name = file_info["name"]

                            # Detect datatype
                            datatype = custom_datatype or _detect_datatype_from_extension(file_name)

                            try:
                                # Generate signed URL for the file
                                # Note: This may need adjustment based on fs.anvilfs API
                                with anvil_fs.open(file_path, 'rb') as f:
                                    # For now, we'll use the file path directly
                                    # In a real implementation, we'd need to generate signed URLs
                                    file_url = f"anvil://{namespace}/{workspace_name}/{file_path}"

                                # Import dataset using Galaxy's URL import mechanism
                                # This will need to be adapted to work with AnVIL URLs
                                print(f"      Importing: {file_name} (type: {datatype})")
                                dataset._import_from_url(gi, dataset_history, file_url, file_name=file_name, file_type=datatype)

                            except Exception as e:
                                print(f"      ERROR importing {file_name}: {e}")

                    except Exception as e:
                        print(f"    ERROR processing pattern {pattern}: {e}")

        except Exception as e:
            print(f"ERROR connecting to Terra workspace {namespace}/{workspace_name}: {e}")
            # Provide helpful guidance on authentication
            if 'credentials' in str(e).lower() or 'authentication' in str(e).lower():
                print(f"  Set up Terra authentication with:")
                print(f"    export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'")
                print(f"    export TERRA_NOTEBOOK_GOOGLE_ACCESS_TOKEN=\"$(gcloud auth print-access-token)\"")
            continue


def _import_dataset_with_metadata(gi, history_id, dataset_config):
    """Import a dataset with optional name and datatype metadata."""
    if isinstance(dataset_config, str):
        # Simple URL format
        url = dataset_config
        file_name = _extract_filename_from_url(url)
        dataset._import_from_url(gi, history_id, url, file_name=file_name)
    elif isinstance(dataset_config, dict):
        # Dictionary format with optional name and datatype
        url = dataset_config.get('url')
        if not url:
            print(f"ERROR: dataset config missing required 'url' field: {dataset_config}")
            return

        # Extract optional parameters
        file_name = dataset_config.get('name')
        if not file_name:
            file_name = _extract_filename_from_url(url)

        file_type = dataset_config.get('datatype')

        # Build kwargs for import
        kwargs = {'file_name': file_name}
        if file_type:
            kwargs['file_type'] = file_type

        dataset._import_from_url(gi, history_id, url, **kwargs)
    else:
        print(f"ERROR: dataset config must be URL string or dict: {dataset_config}")


def _process_datasets_v1(gi, datasets):
    """Process datasets in version 1 format with enhanced metadata support."""
    # Check if datasets is a simple list or dictionary
    if isinstance(datasets, list):
        # Simple list format - create default history
        print(f"Importing {len(datasets)} datasets into default history...")
        new_history = gi.histories.create_history(name="Configured Datasets")
        dataset_history = new_history['id']

        for dataset_config in datasets:
            try:
                _import_dataset_with_metadata(gi, dataset_history, dataset_config)
            except Exception as e:
                print(f"ERROR: failed to import dataset {dataset_config}: {e}")

    elif isinstance(datasets, dict):
        # Dictionary format - group by history name
        for history_name, dataset_list in datasets.items():
            print(
                f"Importing {len(dataset_list)} datasets into history '{history_name}'..."
            )

            # Get or create the named history
            histories = gi.histories.get_histories(name=history_name)
            if histories:
                dataset_history = histories[0]['id']
            else:
                new_history = gi.histories.create_history(name=history_name)
                dataset_history = new_history['id']

            for dataset_config in dataset_list:
                try:
                    _import_dataset_with_metadata(gi, dataset_history, dataset_config)
                except Exception as e:
                    print(f"ERROR: failed to import dataset {dataset_config}: {e}")
    else:
        print("ERROR: datasets section must be either a list or dictionary")


def _process_datasets_v0(gi, datasets):
    """Process datasets in legacy version 0 format (backward compatibility)."""
    # Check if datasets is a simple list or dictionary
    if isinstance(datasets, list):
        # Simple list format - create default history
        print(f"Importing {len(datasets)} datasets into default history...")
        new_history = gi.histories.create_history(name="Configured Datasets")
        dataset_history = new_history['id']

        for url in datasets:
            try:
                dataset._import_from_url(gi, dataset_history, url)
            except Exception as e:
                print(f"ERROR: failed to import dataset from {url}: {e}")

    elif isinstance(datasets, dict):
        # Dictionary format - group by history name
        for history_name, urls in datasets.items():
            print(
                f"Importing {len(urls)} datasets into history '{history_name}'..."
            )

            # Get or create the named history
            histories = gi.histories.get_histories(name=history_name)
            if histories:
                dataset_history = histories[0]['id']
            else:
                new_history = gi.histories.create_history(name=history_name)
                dataset_history = new_history['id']

            for url in urls:
                try:
                    dataset._import_from_url(gi, dataset_history, url)
                except Exception as e:
                    print(f"ERROR: failed to import dataset from {url}: {e}")
    else:
        print("ERROR: datasets section must be either a list or dictionary")


def bootstrap(context: Context, args: list):
    """Configure a Galaxy instance by uploading datasets, histories, and workflows from a YAML configuration file."""
    if len(args) < 2:
        print("USAGE: abm config bootstrap <server> <config_file>")
        return

    server = args[0]
    config_file = args[1]

    # Create context for the specified server
    context = Context(server)

    if not os.path.exists(config_file):
        print(f"ERROR: configuration file not found: {config_file}")
        return

    # Load configuration file
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: failed to parse configuration file: {e}")
        return

    if config is None:
        print("ERROR: configuration file is empty")
        return

    # Process histories
    if 'histories' in config:
        histories = config['histories']
        print(f"Importing {len(histories)} histories...")
        for url in histories:
            try:
                # Call existing history import function
                history._import(context, [url])
            except Exception as e:
                print(f"ERROR: failed to import history from {url}: {e}")

    # Determine configuration version (default to 0 for backward compatibility)
    config_version = config.get('version', 0)
    print(f"Processing bootstrap configuration version {config_version}")

    # Process datasets using version-appropriate handler
    if 'datasets' in config:
        datasets = config['datasets']
        gi = connect(context)

        if config_version == 0:
            # Legacy format for backward compatibility
            _process_datasets_v0(gi, datasets)
        elif config_version == 1:
            # Enhanced format with name and datatype support
            _process_datasets_v1(gi, datasets)
        else:
            print(f"ERROR: unsupported configuration version: {config_version}")

    # Process workflows (with tool installation)
    if 'workflows' in config:
        workflows = config['workflows']
        print(f"Importing {len(workflows)} workflows (with tools)...")
        for url in workflows:
            try:
                # Call existing workflow import function with tools
                workflow.import_from_url(context, [url])
            except Exception as e:
                print(f"ERROR: failed to import workflow from {url}: {e}")

    # Process workflows (without tool installation)
    if 'workflows-no-tools' in config:
        workflows_no_tools = config['workflows-no-tools']
        print(f"Importing {len(workflows_no_tools)} workflows (without tools)...")
        for url in workflows_no_tools:
            try:
                # Call existing workflow import function without tools
                workflow.import_from_url(context, [url, '--no-tools'])
            except Exception as e:
                print(f"ERROR: failed to import workflow from {url}: {e}")

    # Process Terra workspaces
    if 'terra' in config:
        terra_workspaces = config['terra']
        print(f"Processing {len(terra_workspaces)} Terra workspaces...")
        gi = connect(context)
        _process_terra_workspaces(gi, terra_workspaces)

    print("Instance configuration complete!")
