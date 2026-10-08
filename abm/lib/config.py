import argparse
import os
import re
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from bioblend.galaxy import dataset_collections
from common import (
    Context,
    _make_dataset_element,
    _make_paired_element,
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

# Terra workspace integration.
#
# terra_compat MUST be imported before anvilfs. It monkey-patches
# configparser.SafeConfigParser (removed in Python 3.12) back into place, and
# importing anvilfs eagerly imports firecloud, which calls SafeConfigParser()
# at import time. The `isort: off`/`on` guards preserve this order -- anvilfs
# is third-party and isort would otherwise sort it ahead of the first-party
# terra_compat import. A broad except ensures a broken or absent Terra stack
# disables the feature instead of crashing the whole CLI.
try:
    # isort: off
    from . import terra_compat  # noqa: F401
    from anvilfs.anvilfs import AnVILFS

    # isort: on

    TERRA_AVAILABLE = True
except Exception:
    TERRA_AVAILABLE = False


def do_list(context: Context, args: list):
    profiles = load_profiles()
    print(f"Loaded {len(profiles)} profiles")
    for profile in profiles:
        print(f"{profile}\t{profiles[profile]['url']}")


def create(context: Context, argv: list):
    parser = argparse.ArgumentParser(prog='abm config create')
    parser.add_argument('profile_name', help='name of the profile to create')
    parser.add_argument(
        'kube_path', nargs='?', help='path to kubeconfig file (backwards compatibility)'
    )
    parser.add_argument('--url', help='Galaxy server URL')
    parser.add_argument('--key', help='Galaxy API key')
    parser.add_argument('--kube', help='path to kubeconfig file')
    parser.add_argument('--master', help='Galaxy master (bootstrap) API key')

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
    # Only store the master key when provided; a profile with no 'master' field
    # falls back to the regular API key (see parse_profile in common.py).
    if args.master:
        profile["master"] = args.master

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


def master(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config master <cloud> <bootstrap_api_key>")
        return
    profile_name = args[0]
    master_key = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile["master"] = master_key
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
        '.xml': 'xml',
    }

    filename_lower = filename.lower()
    for ext, datatype in extension_map.items():
        if filename_lower.endswith(ext):
            return datatype
    return None


def _filter_files_by_pattern(
    files: List[Dict[str, Any]], pattern: str
) -> List[Dict[str, Any]]:
    """Filter files by glob-style pattern against filename."""
    # Convert glob pattern to regex
    regex_pattern = pattern.replace("*", ".*").replace("?", ".")
    regex = re.compile(f"^{regex_pattern}$")

    # Match against filename (name field) rather than full path
    return [f for f in files if regex.match(f.get("name", ""))]


class BootstrapResult:
    """Counts the imports attempted by ``bootstrap`` (see ``failOnImport``)."""

    def __init__(self):
        self.imported = 0
        self.failed = 0

    def ok(self):
        self.imported += 1

    def fail(self):
        self.failed += 1


# The Galaxy file source configured for the workspace an AnVIL instance was
# launched from, and where fs.anvilfs mounts the workspace bucket inside it.
DEFAULT_TERRA_FILE_SOURCE = "terra-launch-workspace"
TERRA_BUCKET_ROOT = "Other Data/Files"

HISTORY_ARCHIVE_EXTENSIONS = ('.rocrate.zip', '.tar.gz', '.tgz', '.tar')


def _classify_bootstrap_file(name: str) -> Optional[str]:
    """Return 'workflow', 'history', or None for a file in a bootstrap folder."""
    lower = name.lower()
    if lower.endswith('.ga'):
        return 'workflow'
    if lower.endswith(HISTORY_ARCHIVE_EXTENSIONS):
        return 'history'
    return None


def _bootstrap_folder_candidates(folder: str) -> List[str]:
    """Paths, within the file source, to try for a ``bootstrap`` folder.

    A bare folder name is what a user sees in the Terra UI, so it is looked up
    in the workspace bucket first and then as a literal path.
    """
    path = folder.strip('/')
    if '/' in path:
        return [path]
    return [f"{TERRA_BUCKET_ROOT}/{path}", path]


class RemoteListingError(Exception):
    """A Galaxy file source directory could not be listed.

    Raised for anything other than success or a confirmed missing directory,
    e.g. an HTTP 500, an authentication failure, or a network timeout, so the
    caller can report a failure instead of treating it as "no such folder".
    """


# Fragments of Galaxy's error message when a remote path or its file source
# does not exist. A missing directory in a PyFilesystem-backed file source
# (the AnVIL source is one) is reported as a generic MessageException, which
# is an HTTP 400 rather than a 404, so the status code alone is not enough.
_NOT_FOUND_FRAGMENTS = ('not found', 'could not find handler', 'does not exist')


def _error_message(response) -> str:
    """Best-effort error text from a Galaxy API error response."""
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get('err_msg') or body)
        return str(body)
    except Exception:
        return getattr(response, 'text', '') or ''


def _list_remote_files(gi, uri: str) -> Optional[List[Dict[str, Any]]]:
    """Recursively list a Galaxy file source directory.

    Returns the entries, or None if the directory (or the file source) does
    not exist. Any other problem raises ``RemoteListingError``.
    """
    try:
        response = gi.make_get_request(
            f"{gi.url}/remote_files",
            params={'target': uri, 'format': 'uri', 'recursive': 'true'},
        )
    except Exception as e:
        raise RemoteListingError(f"failed to list {uri}: {e}") from e
    if response.status_code == 200:
        return response.json()
    message = _error_message(response)
    if response.status_code == 404:
        return None
    if response.status_code == 400 and any(
        fragment in message.lower() for fragment in _NOT_FOUND_FRAGMENTS
    ):
        return None
    raise RemoteListingError(
        f"failed to list {uri}: HTTP {response.status_code} {message}".rstrip()
    )


def _import_workflow_from_uri(gi, uri: str):
    """Have Galaxy import and publish the workflow at ``uri``, then install its tools.

    A tool that fails to install is reported but does not fail the import.
    """
    print(f"Importing workflow from {uri}")
    imported = gi.workflows._post(payload={'archive_source': uri})
    workflow_id = imported['id']
    gi.workflows.update_workflow(workflow_id, published=True)
    workflow.install_tools_for_workflow(gi, workflow_id)
    return workflow_id


def _process_terra_bootstrap(gi, workspace_config, result):
    """Import every history archive and workflow found in a workspace folder.

    Galaxy reads the files itself through its Terra file source, so the folder
    is listed with the remote files API and imported by ``gxfiles://`` URI.
    """
    folder = workspace_config['bootstrap']
    file_source = workspace_config.get('file_source', DEFAULT_TERRA_FILE_SOURCE)

    entries = None
    for path in _bootstrap_folder_candidates(folder):
        uri = f"gxfiles://{file_source}/{path}"
        try:
            entries = _list_remote_files(gi, uri)
        except RemoteListingError as e:
            # Not a missing folder: the listing itself failed, so count it as
            # a failure rather than silently skipping the folder.
            print(f"  ERROR: {e}")
            result.fail()
            return
        if entries is not None:
            break
    if entries is None:
        # Most workspaces will not have a bootstrap folder.
        print(
            f"  No bootstrap folder '{folder}' found in file source '{file_source}', skipping"
        )
        return

    files = [e for e in entries if e.get('class') == 'File']
    print(f"  Found {len(files)} files in {uri}")
    for entry in files:
        kind = _classify_bootstrap_file(entry['name'])
        if kind is None:
            print(f"  Skipping {entry['name']}: not a workflow or history archive")
            continue
        try:
            if kind == 'workflow':
                imported = _import_workflow_from_uri(gi, entry['uri'])
            else:
                imported = history._do_import(gi, entry['uri'], wait=True)
        except Exception as e:
            print(f"  ERROR: failed to import {entry['name']}: {e}")
            imported = None
        if imported:
            result.ok()
        else:
            print(f"  ERROR: {kind} {entry['name']} was not imported")
            result.fail()


def _process_terra_workspaces(gi, terra_workspaces, result=None):
    """Process Terra workspace configurations: dataset patterns and bootstrap folders."""
    if result is None:
        result = BootstrapResult()
    if isinstance(terra_workspaces, dict):
        terra_workspaces = [terra_workspaces]

    for workspace_config in terra_workspaces:
        if 'datasets' in workspace_config:
            _process_terra_datasets(gi, workspace_config, result)
        if workspace_config.get('bootstrap'):
            _process_terra_bootstrap(gi, workspace_config, result)


def _process_terra_datasets(gi, workspace_config, result):
    """Import the datasets matching a Terra workspace's file patterns."""
    namespace = workspace_config.get('namespace')
    workspace_name = workspace_config.get('workspace')

    if not namespace or not workspace_name:
        print(
            f"ERROR: Terra workspace config missing 'namespace' or 'workspace': {workspace_config}"
        )
        result.fail()
        return

    if not TERRA_AVAILABLE:
        print(
            "ERROR: Terra workspace support not available. Install fs.anvilfs package."
        )
        result.fail()
        return

    print(f"Processing Terra workspace: {namespace}/{workspace_name}")

    try:
        # Connect to Terra workspace via fs.anvilfs
        anvil_fs = AnVILFS(namespace, workspace_name)
    except Exception as e:
        print(f"ERROR connecting to Terra workspace {namespace}/{workspace_name}: {e}")
        # Provide helpful guidance on authentication
        if 'credentials' in str(e).lower() or 'authentication' in str(e).lower():
            print(f"  Set up Terra authentication with:")
            print(
                f"    export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'"
            )
            print(
                f"    export TERRA_NOTEBOOK_GOOGLE_ACCESS_TOKEN=\"$(gcloud auth print-access-token)\""
            )
        result.fail()
        return

    for history_name, dataset_patterns in workspace_config['datasets'].items():
        print(f"  Processing history: {history_name}")
        try:
            dataset_history = _get_or_create_history(gi, history_name)
        except Exception as e:
            print(f"  ERROR: unable to get or create history {history_name}: {e}")
            result.fail()
            continue

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
                    print(
                        f"    ERROR: pattern config missing 'pattern' field: {pattern_config}"
                    )
                    result.fail()
                    continue
            else:
                print(f"    ERROR: invalid pattern config: {pattern_config}")
                result.fail()
                continue

            print(f"    Looking for files matching: {pattern}")

            # Split the pattern into a directory to scan and a filename pattern,
            # e.g. "Tables/sample/*.fastq". A bare "*.fastq" scans the root.
            pattern_path = Path(pattern)
            if pattern_path.parent != Path("."):
                scan_dir = str(pattern_path.parent)
                filename_pattern = pattern_path.name
            else:
                scan_dir = "/"
                filename_pattern = pattern

            print(f"      Scanning directory: {scan_dir}")
            print(f"      Filename pattern: {filename_pattern}")

            try:
                all_files = [
                    {
                        "path": f"{scan_dir.rstrip('/')}/{f.name}".replace("//", "/"),
                        "name": f.name,
                    }
                    for f in anvil_fs.scandir(scan_dir)
                    if f.is_file
                ]
            except Exception as e:
                print(f"      ERROR scanning directory {scan_dir}: {e}")
                result.fail()
                continue

            matching_files = _filter_files_by_pattern(all_files, filename_pattern)
            print(f"    Found {len(matching_files)} matching files")

            for file_info in matching_files:
                file_name = file_info["name"]
                datatype = custom_datatype or _detect_datatype_from_extension(file_name)
                file_url = f"anvil://{namespace}/{workspace_name}/{file_info['path']}"
                print(f"      Importing: {file_name} (type: {datatype})")
                try:
                    dataset._import_from_url(
                        gi,
                        dataset_history,
                        file_url,
                        file_name=file_name,
                        file_type=datatype,
                    )
                    result.ok()
                except Exception as e:
                    print(f"      ERROR importing {file_name}: {e}")
                    result.fail()


def _import_dataset_with_metadata(gi, history_id, dataset_config, default_name=None):
    """Import a dataset with optional name and datatype metadata.

    ``dataset_config`` is a URL string or a ``{url, name?, datatype?}`` dict.
    When the config carries no ``name`` the dataset is named ``default_name``
    if given, otherwise the filename portion of the URL.

    Returns the id of the new dataset (``outputs[0]['id']`` from ``put_url``)
    so callers can build collections from it (issue #364), or ``None`` if the
    config was invalid. The result is truthy on success so callers can also
    use it to count imports for ``failOnImport``.
    """
    if isinstance(dataset_config, str):
        # Simple URL format
        url = dataset_config
        kwargs = {'file_name': default_name or _extract_filename_from_url(url)}
    elif isinstance(dataset_config, dict):
        # Dictionary format with optional name and datatype
        url = dataset_config.get('url')
        if not url:
            print(
                f"ERROR: dataset config missing required 'url' field: {dataset_config}"
            )
            return None

        # Extract optional parameters
        file_name = dataset_config.get('name') or default_name
        if not file_name:
            file_name = _extract_filename_from_url(url)

        file_type = dataset_config.get('datatype')

        # Build kwargs for import
        kwargs = {'file_name': file_name}
        if file_type:
            kwargs['file_type'] = file_type
    else:
        print(f"ERROR: dataset config must be URL string or dict: {dataset_config}")
        return None

    response = dataset._import_from_url(gi, history_id, url, **kwargs)
    return _dataset_id_from_upload(response)


def _dataset_id_from_upload(response):
    """Extract the new dataset id from a ``put_url``/upload tool response."""
    try:
        return response['outputs'][0]['id']
    except (KeyError, IndexError, TypeError):
        return None


COLLECTION_TYPES = ('list', 'list:paired')
PAIRED_ROLES = ('forward', 'reverse')


def _is_valid_leaf(leaf):
    """True if ``leaf`` is a URL string or a dict with a ``url`` key."""
    if isinstance(leaf, str):
        return bool(leaf)
    return isinstance(leaf, dict) and bool(leaf.get('url'))


def _validate_collection_config(item):
    """Validate a bootstrap collection item.

    Returns ``None`` when the definition is valid, otherwise an error message.
    The whole definition is checked before any upload starts so an invalid
    collection never leaves half of its datasets behind.
    """
    name = item.get('collection')
    if not name or not isinstance(name, str):
        return f"collection item missing a 'collection' name: {item}"
    ctype = item.get('type', 'list')
    if ctype not in COLLECTION_TYPES:
        return (
            f"collection '{name}' has unknown type '{ctype}' "
            f"(expected one of {', '.join(COLLECTION_TYPES)})"
        )
    elements = item.get('elements')
    if not isinstance(elements, dict) or not elements:
        return f"collection '{name}' requires a non-empty 'elements' mapping"
    for element_id, value in elements.items():
        if ctype == 'list:paired':
            if not isinstance(value, dict):
                return (
                    f"collection '{name}' element '{element_id}' must be a mapping "
                    f"with 'forward' and 'reverse' datasets"
                )
            for role in PAIRED_ROLES:
                if role not in value:
                    return (
                        f"collection '{name}' element '{element_id}' "
                        f"is missing '{role}'"
                    )
                if not _is_valid_leaf(value[role]):
                    return (
                        f"collection '{name}' element '{element_id}' "
                        f"'{role}' must be a URL or a dict with a 'url'"
                    )
        elif not _is_valid_leaf(value):
            return (
                f"collection '{name}' element '{element_id}' "
                f"must be a URL or a dict with a 'url'"
            )
    return None


def _import_collection(gi, history_id, item):
    """Upload the datasets of a bootstrap collection item and create the collection.

    The item has the shape::

        collection: <name>
        type: list | list:paired     (default list)
        hide_elements: true|false    (default false)
        elements:
          <element id>: <dataset>                       # list
          <element id>: {forward: <dataset>, reverse: <dataset>}   # list:paired

    where ``<dataset>`` is a URL string or a ``{url, name?, datatype?}`` dict.
    Datasets without a ``name`` are named after their element identifier
    (``pair1_forward`` for paired elements). Returns True when the collection
    was created, False when it was skipped because of an invalid definition or
    a failed upload. Failures are reported and never raised, so one bad
    collection does not abort the rest of the bootstrap.
    """
    error = _validate_collection_config(item)
    if error:
        print(f"ERROR: {error}")
        return False

    name = item['collection']
    ctype = item.get('type', 'list')
    print(f"Creating {ctype} collection '{name}'...")

    def _upload(leaf, default_name):
        try:
            dataset_id = _import_dataset_with_metadata(
                gi, history_id, leaf, default_name=default_name
            )
        except Exception as e:
            print(f"ERROR: failed to import dataset {leaf}: {e}")
            return None
        if dataset_id is None:
            print(f"ERROR: no dataset id returned for {leaf}")
        return dataset_id

    elements = []
    dataset_ids = []
    for element_id, value in item['elements'].items():
        if ctype == 'list:paired':
            ids = {}
            for role in PAIRED_ROLES:
                ids[role] = _upload(value[role], f"{element_id}_{role}")
                if ids[role] is None:
                    print(f"ERROR: skipping collection '{name}'")
                    return False
            dataset_ids.extend(ids.values())
            elements.append(
                _make_paired_element(element_id, ids['forward'], ids['reverse'])
            )
        else:
            dataset_id = _upload(value, element_id)
            if dataset_id is None:
                print(f"ERROR: skipping collection '{name}'")
                return False
            dataset_ids.append(dataset_id)
            elements.append(_make_dataset_element(element_id, dataset_id))

    try:
        result = gi.histories.create_dataset_collection(
            history_id=history_id,
            collection_description=dataset_collections.CollectionDescription(
                name=name, type=ctype, elements=elements
            ),
        )
    except Exception as e:
        print(f"ERROR: failed to create collection '{name}': {e}")
        return False
    print(f"Created collection '{name}' ({result.get('id', '?')})")

    if item.get('hide_elements'):
        for dataset_id in dataset_ids:
            try:
                gi.histories.update_dataset(history_id, dataset_id, visible=False)
            except Exception as e:
                print(f"WARNING: failed to hide dataset {dataset_id}: {e}")
    return True


DEFAULT_DATASET_HISTORY = "Configured Datasets"


def _normalize_datasets_config(datasets):
    """Normalize any accepted 'datasets' shape into ``{history_name: [item, ...]}``.

    The bootstrap config format is version-agnostic (issue #349). Accepts:

      * a list of items                    -> imported into the default history
      * a single URL string                -> default history, one item
      * a single ``{url, ...}`` dataset dict -> default history, one item
      * a dict of ``history_name -> list``   -> passthrough
      * a dict of ``history_name -> scalar`` -> the scalar wrapped in a list

    Each item is a URL string or a ``{url, name?, datatype?}`` dict; per-item
    validation is left to ``_import_dataset_with_metadata``. Returns an empty
    mapping (after printing an error) for any unsupported top-level type.
    """
    if isinstance(datasets, str):
        return {DEFAULT_DATASET_HISTORY: [datasets]}
    if isinstance(datasets, list):
        return {DEFAULT_DATASET_HISTORY: datasets}
    if isinstance(datasets, dict):
        # A single dataset config (identified by a 'url' key) rather than a
        # history map.
        if 'url' in datasets:
            return {DEFAULT_DATASET_HISTORY: [datasets]}
        normalized = {}
        for history_name, value in datasets.items():
            normalized[history_name] = value if isinstance(value, list) else [value]
        return normalized
    print(f"ERROR: datasets section must be a list, dict, or URL string: {datasets!r}")
    return {}


def _get_or_create_history(gi, name):
    """Return the id of the history named ``name``, creating it if necessary."""
    histories = gi.histories.get_histories(name=name)
    if histories:
        return histories[0]['id']
    return gi.histories.create_history(name=name)['id']


def _process_datasets(gi, datasets, result=None):
    """Import datasets from any supported bootstrap format (version-agnostic).

    Replaces the former version-specific ``_process_datasets_v0``/``_v1``
    handlers with a single implementation that accepts every previously
    supported shape (issue #349).
    """
    if result is None:
        result = BootstrapResult()
    mapping = _normalize_datasets_config(datasets)
    if datasets and not mapping:
        result.fail()
    for history_name, items in mapping.items():
        print(f"Importing {len(items)} datasets into history '{history_name}'...")
        history_id = _get_or_create_history(gi, history_name)
        for item in items:
            # An item with a 'collection' key defines a dataset collection
            # whose member datasets are uploaded inline (issue #364).
            if isinstance(item, dict) and 'collection' in item:
                if _import_collection(gi, history_id, item):
                    result.ok()
                else:
                    result.fail()
                continue
            try:
                imported = _import_dataset_with_metadata(gi, history_id, item)
            except Exception as e:
                print(f"ERROR: failed to import dataset {item}: {e}")
                imported = False
            if imported:
                result.ok()
            else:
                result.fail()


def _normalize_history_entry(entry):
    """Normalize a bootstrap 'histories' entry into a ``(url, name)`` tuple.

    An entry may be either a plain URL string or a dict with a required ``url``
    field and an optional ``name`` field (v1 config format). For a plain URL
    string the name defaults to the filename portion of the URL. Returns
    ``(None, name)`` when a dict is missing its ``url`` so the caller can report
    the error rather than passing the whole dict to Galaxy as the archive
    source (see issue #346).
    """
    if isinstance(entry, dict):
        return entry.get('url'), entry.get('name')
    return entry, _extract_filename_from_url(entry)


def _bootstrap_workflow(context, args, result):
    """Import one workflow through ``workflow.import_from_url`` and record the outcome."""
    try:
        imported = workflow.import_from_url(context, args)
    except Exception as e:
        print(f"ERROR: failed to import workflow from {args[0]}: {e}")
        imported = False
    # import_from_url returns False when the workflow could not be imported.
    if imported is False:
        result.fail()
    else:
        result.ok()


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

    # Failed imports are only logged unless failOnImport is true, in which
    # case any failed import makes the command exit with a non-zero status.
    fail_on_import = bool(config.get('failOnImport', False))
    result = BootstrapResult()

    # Process histories
    if 'histories' in config:
        histories = config['histories']
        print(f"Importing {len(histories)} histories...")
        for entry in histories:
            # v1 entries may be a plain URL string or a {url, name} dict; pass
            # only the URL string to the importer (issue #346).
            url, name = _normalize_history_entry(entry)
            if not url:
                print(f"ERROR: history entry missing 'url': {entry}")
                result.fail()
                continue
            try:
                # Call existing history import function; None means it failed.
                imported = history._import(context, [url], name=name)
            except Exception as e:
                print(f"ERROR: failed to import history from {url}: {e}")
                imported = None
            if imported:
                result.ok()
            else:
                result.fail()

    # The bootstrap config format is version-agnostic; the 'version' attribute
    # is ignored if present (issue #349). _process_datasets handles every
    # supported dataset shape with full backwards compatibility.
    if 'datasets' in config:
        gi = connect(context)
        _process_datasets(gi, config['datasets'], result)

    # Process workflows (with tool installation)
    if 'workflows' in config:
        workflows = config['workflows']
        print(f"Importing {len(workflows)} workflows (with tools)...")
        for url in workflows:
            _bootstrap_workflow(context, [url], result)

    # Process workflows (without tool installation)
    if 'workflows-no-tools' in config:
        workflows_no_tools = config['workflows-no-tools']
        print(f"Importing {len(workflows_no_tools)} workflows (without tools)...")
        for url in workflows_no_tools:
            _bootstrap_workflow(context, [url, '--no-tools'], result)

    # Process Terra workspaces
    if 'terra' in config:
        terra_workspaces = config['terra']
        if isinstance(terra_workspaces, dict):
            terra_workspaces = [terra_workspaces]
        print(f"Processing {len(terra_workspaces)} Terra workspaces...")
        gi = connect(context)
        _process_terra_workspaces(gi, terra_workspaces, result)

    print(f"Imported {result.imported}, failed {result.failed}")
    print("Instance configuration complete!")
    if fail_on_import and result.failed > 0:
        sys.exit(1)
