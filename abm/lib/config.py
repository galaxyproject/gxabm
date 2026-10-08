import argparse
import os
import re
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


def _process_terra_workspaces(gi, terra_workspaces):
    """Process Terra workspace configurations and import datasets."""
    if not TERRA_AVAILABLE:
        print(
            "ERROR: Terra workspace support not available. Install fs.anvilfs package."
        )
        return

    for workspace_config in terra_workspaces:
        namespace = workspace_config.get('namespace')
        workspace_name = workspace_config.get('workspace')

        if not namespace or not workspace_name:
            print(
                f"ERROR: Terra workspace config missing 'namespace' or 'workspace': {workspace_config}"
            )
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
                            print(
                                f"    ERROR: pattern config missing 'pattern' field: {pattern_config}"
                            )
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
                                    full_path = f"{scan_dir.rstrip('/')}/{file_info.name}".replace(
                                        "//", "/"
                                    )
                                    all_files.append(
                                        {
                                            "path": full_path,
                                            "name": file_info.name,
                                            "size": (
                                                file_info.size
                                                if hasattr(file_info, 'size')
                                                else 0
                                            ),
                                        }
                                    )
                        except Exception as e:
                            print(f"      ERROR scanning directory {scan_dir}: {e}")
                            continue

                        # Filter files by filename pattern
                        matching_files = _filter_files_by_pattern(
                            all_files, filename_pattern
                        )
                        print(f"    Found {len(matching_files)} matching files")

                        # Import each matching file
                        for file_info in matching_files:
                            file_path = file_info["path"]
                            file_name = file_info["name"]

                            # Detect datatype
                            datatype = (
                                custom_datatype
                                or _detect_datatype_from_extension(file_name)
                            )

                            try:
                                # Generate signed URL for the file
                                # Note: This may need adjustment based on fs.anvilfs API
                                with anvil_fs.open(file_path, 'rb') as f:
                                    # For now, we'll use the file path directly
                                    # In a real implementation, we'd need to generate signed URLs
                                    file_url = f"anvil://{namespace}/{workspace_name}/{file_path}"

                                # Import dataset using Galaxy's URL import mechanism
                                # This will need to be adapted to work with AnVIL URLs
                                print(
                                    f"      Importing: {file_name} (type: {datatype})"
                                )
                                dataset._import_from_url(
                                    gi,
                                    dataset_history,
                                    file_url,
                                    file_name=file_name,
                                    file_type=datatype,
                                )

                            except Exception as e:
                                print(f"      ERROR importing {file_name}: {e}")

                    except Exception as e:
                        print(f"    ERROR processing pattern {pattern}: {e}")

        except Exception as e:
            print(
                f"ERROR connecting to Terra workspace {namespace}/{workspace_name}: {e}"
            )
            # Provide helpful guidance on authentication
            if 'credentials' in str(e).lower() or 'authentication' in str(e).lower():
                print(f"  Set up Terra authentication with:")
                print(
                    f"    export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'"
                )
                print(
                    f"    export TERRA_NOTEBOOK_GOOGLE_ACCESS_TOKEN=\"$(gcloud auth print-access-token)\""
                )
            continue


def _import_dataset_with_metadata(gi, history_id, dataset_config, default_name=None):
    """Import a dataset with optional name and datatype metadata.

    ``dataset_config`` is a URL string or a ``{url, name?, datatype?}`` dict.
    When the config carries no ``name`` the dataset is named ``default_name``
    if given, otherwise the filename portion of the URL.

    Returns the id of the new dataset (``outputs[0]['id']`` from ``put_url``)
    so callers can build collections from it (issue #364), or ``None`` if the
    config was invalid.
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


def _process_datasets(gi, datasets):
    """Import datasets from any supported bootstrap format (version-agnostic).

    Replaces the former version-specific ``_process_datasets_v0``/``_v1``
    handlers with a single implementation that accepts every previously
    supported shape (issue #349).
    """
    mapping = _normalize_datasets_config(datasets)
    for history_name, items in mapping.items():
        print(f"Importing {len(items)} datasets into history '{history_name}'...")
        history_id = _get_or_create_history(gi, history_name)
        for item in items:
            # An item with a 'collection' key defines a dataset collection
            # whose member datasets are uploaded inline (issue #364).
            if isinstance(item, dict) and 'collection' in item:
                _import_collection(gi, history_id, item)
                continue
            try:
                _import_dataset_with_metadata(gi, history_id, item)
            except Exception as e:
                print(f"ERROR: failed to import dataset {item}: {e}")


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
        for entry in histories:
            # v1 entries may be a plain URL string or a {url, name} dict; pass
            # only the URL string to the importer (issue #346).
            url, name = _normalize_history_entry(entry)
            if not url:
                print(f"ERROR: history entry missing 'url': {entry}")
                continue
            try:
                # Call existing history import function
                history._import(context, [url], name=name)
            except Exception as e:
                print(f"ERROR: failed to import history from {url}: {e}")

    # The bootstrap config format is version-agnostic; the 'version' attribute
    # is ignored if present (issue #349). _process_datasets handles every
    # supported dataset shape with full backwards compatibility.
    if 'datasets' in config:
        gi = connect(context)
        _process_datasets(gi, config['datasets'])

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
