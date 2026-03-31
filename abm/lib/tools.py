import argparse
import json
import re

import yaml
from common import Context, connect, find_history


def _get_panel_tool_ids(gi):
    """Return the set of tool IDs shown in the tool panel (latest versions)."""
    panel_ids = set()
    for section in gi.tools.get_tool_panel():
        for elem in section.get('elems', []):
            tool_id = elem.get('id')
            if tool_id:
                panel_ids.add(tool_id)
        # Top-level tools (not in a section)
        tool_id = section.get('id')
        model = section.get('model_class', '')
        if tool_id and model == 'Tool':
            panel_ids.add(tool_id)
    return panel_ids


def do_list(context: Context, argv: list):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-n', '--name', help='only show tools whose name matches this regex'
    )
    parser.add_argument(
        '-s',
        '--section',
        help='only show tools in this panel section (regex match)',
    )
    parser.add_argument(
        '-id', '--id', dest='tool_id', help='filter tools by tool ID (regex match)'
    )
    parser.add_argument(
        '-l',
        '--latest',
        action='store_true',
        help='only show the latest version of each tool',
    )
    args = parser.parse_args(argv)

    gi = connect(context)
    if args.latest:
        panel_ids = _get_panel_tool_ids(gi)
    tools = gi.tools.get_tools()
    if args.latest:
        tools = [t for t in tools if t.get('id') in panel_ids]
    if args.name:
        pattern = re.compile(args.name, re.IGNORECASE)
        tools = [t for t in tools if pattern.search(t.get('name', ''))]
    if args.tool_id:
        pattern = re.compile(args.tool_id, re.IGNORECASE)
        tools = [t for t in tools if pattern.search(t.get('id', ''))]
    if args.section:
        pattern = re.compile(args.section, re.IGNORECASE)
        tools = [
            t for t in tools if pattern.search(t.get('panel_section_name', '') or '')
        ]
    if len(tools) == 0:
        print('No tools found')
        return
    print(f'Found {len(tools)} tools')
    print('ID\tVersion\tSection\tName')
    for tool in sorted(tools, key=lambda t: t.get('name', '')):
        section = tool.get('panel_section_name', '') or ''
        print(f"{tool['id']}\t{tool.get('version', '')}\t{section}\t{tool['name']}")


def show(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no tool ID provided')
        return
    gi = connect(context)
    tool = gi.tools.show_tool(args[0], io_details=True)
    print(json.dumps(tool, indent=4))


def inputs(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no tool ID provided')
        return
    gi = connect(context)
    tool = gi.tools.show_tool(args[0], io_details=True)
    tool_inputs = tool.get('inputs', [])
    if len(tool_inputs) == 0:
        print('No inputs found')
        return
    print(f'Inputs for {tool["name"]} ({tool["id"]}):')
    for inp in tool_inputs:
        label = inp.get('label', '') or ''
        required = ' (required)' if inp.get('optional') is False else ''
        print(f"  {inp['name']}: {inp.get('type', 'unknown')}{required}")
        if label:
            print(f"    {label}")


def search(context: Context, argv: list):
    if len(argv) == 0:
        print('ERROR: no search query provided')
        return
    gi = connect(context)
    query = ' '.join(argv)
    pattern = re.compile(query, re.IGNORECASE)
    tools = gi.tools.get_tools()
    results = [
        t
        for t in tools
        if pattern.search(t.get('name', ''))
        or pattern.search(t.get('id', ''))
        or pattern.search(t.get('description', '') or '')
    ]
    if len(results) == 0:
        print('No tools found')
        return
    print(f'Found {len(results)} tools')
    print('ID\tVersion\tName')
    for tool in sorted(results, key=lambda t: t.get('name', '')):
        print(f"{tool['id']}\t{tool.get('version', '')}\t{tool['name']}")


# ---------------------------------------------------------------------------
# scaffold: generate a YAML input template for a tool
# ---------------------------------------------------------------------------


def _scaffold_inputs(inputs, indent=0):
    """Recursively generate YAML scaffold lines from tool input definitions."""
    lines = []
    prefix = '  ' * indent
    for inp in inputs:
        itype = inp.get('type', 'unknown')
        name = inp.get('name', '?')
        label = inp.get('label', '') or ''
        help_text = inp.get('help', '') or ''
        # Truncate long help text
        if len(help_text) > 80:
            help_text = help_text[:77] + '...'

        if itype == 'conditional':
            test_param = inp.get('test_param', {})
            selector_name = test_param.get('name', 'selector')
            default_value = test_param.get('value', '')
            cases = inp.get('cases', [])
            case_values = [c['value'] for c in cases]

            lines.append(f'{prefix}# {label}' if label else f'{prefix}# {name}')
            lines.append(
                f'{prefix}# Options: {", ".join(repr(v) for v in case_values)}'
            )
            lines.append(f'{prefix}{selector_name}: {repr(default_value)}')

            # Scaffold the default case (or first case)
            default_case = None
            for case in cases:
                if case['value'] == default_value:
                    default_case = case
                    break
            if default_case is None and cases:
                default_case = cases[0]
            if default_case:
                case_inputs = default_case.get('inputs', [])
                if case_inputs:
                    lines.extend(_scaffold_inputs(case_inputs, indent))

            # Show other cases as comments
            for case in cases:
                if case is default_case:
                    continue
                case_inputs = case.get('inputs', [])
                if case_inputs:
                    lines.append(
                        f'{prefix}# --- inputs when {selector_name} = {repr(case["value"])} ---'
                    )
                    for line in _scaffold_inputs(case_inputs, indent):
                        lines.append(f'{prefix}# {line.lstrip()}')

        elif itype == 'section':
            lines.append(f'{prefix}# {inp.get("title", name)}')
            lines.append(f'{prefix}{name}:')
            lines.extend(_scaffold_inputs(inp.get('inputs', []), indent + 1))

        elif itype == 'repeat':
            min_val = inp.get('min', 0)
            lines.append(f'{prefix}# {inp.get("title", name)} (repeat, min={min_val})')
            lines.append(f'{prefix}{name}:')
            lines.append(f'{prefix}  - # entry 1')
            lines.extend(_scaffold_inputs(inp.get('inputs', []), indent + 2))

        elif itype in ('data', 'data_collection'):
            src = 'hdca' if itype == 'data_collection' else 'hda'
            extensions = inp.get('extensions', [])
            ext_str = ', '.join(extensions[:5])
            if len(extensions) > 5:
                ext_str += ', ...'
            required = ' (required)' if not inp.get('optional', True) else ''
            comment = f'{label}{required}' if label else f'{name}{required}'
            if ext_str:
                comment += f' [{ext_str}]'
            lines.append(f'{prefix}# {comment}')
            lines.append(f'{prefix}{name}: {src}:DATASET_ID')

        elif itype == 'boolean':
            default = inp.get('value', False)
            if isinstance(default, str):
                default = default.lower() == 'true'
            comment = label if label else name
            lines.append(f'{prefix}# {comment}')
            lines.append(f'{prefix}{name}: {str(default).lower()}')

        elif itype == 'select':
            options = inp.get('options', [])
            default = inp.get('value', '')
            option_values = [o[1] for o in options] if options else []
            comment = label if label else name
            if option_values:
                comment += (
                    f' (options: {", ".join(repr(v) for v in option_values[:8])})'
                )
            lines.append(f'{prefix}# {comment}')
            lines.append(f'{prefix}{name}: {repr(default)}')

        elif itype in ('integer', 'float'):
            default = inp.get('value', '')
            if default is None:
                default = ''
            comment = label if label else name
            if help_text:
                comment += f' - {help_text}'
            lines.append(f'{prefix}# {comment}')
            lines.append(f'{prefix}{name}: {default}')

        elif itype == 'text':
            default = inp.get('value', '') or ''
            comment = label if label else name
            lines.append(f'{prefix}# {comment}')
            lines.append(f'{prefix}{name}: {repr(default)}')

        elif itype == 'color':
            default = inp.get('value', '#000000')
            lines.append(f'{prefix}# {label or name}')
            lines.append(f'{prefix}{name}: {repr(default)}')

        elif itype == 'hidden':
            # Skip hidden params
            continue

        else:
            default = inp.get('value', '')
            comment = f'{label} (type: {itype})' if label else f'{name} (type: {itype})'
            lines.append(f'{prefix}# {comment}')
            lines.append(f'{prefix}{name}: {repr(default)}')

    return lines


def scaffold(context: Context, argv: list):
    if len(argv) == 0:
        print('ERROR: no tool ID provided')
        return
    gi = connect(context)
    tool = gi.tools.show_tool(argv[0], io_details=True)
    tool_inputs = tool.get('inputs', [])

    lines = [
        f'# Input template for: {tool["name"]}',
        f'# Tool ID: {tool["id"]}',
        f'# Version: {tool.get("version", "unknown")}',
        f'#',
        f'# Dataset references use the format: hda:DATASET_ID or hdca:COLLECTION_ID',
        f'# Edit the values below and pass this file to: abm CLOUD tools run {tool["id"]} -f THIS_FILE',
        f'#',
    ]
    lines.extend(_scaffold_inputs(tool_inputs))
    print('\n'.join(lines))


# ---------------------------------------------------------------------------
# run: execute a tool
# ---------------------------------------------------------------------------


def _parse_value(value):
    """Parse a string value into its appropriate type.

    Handles dataset references (hda:ID, hdca:ID), booleans, numbers,
    and falls through to plain strings.
    """
    # Dataset reference shorthand
    if ':' in value:
        parts = value.split(':', 1)
        if parts[0] in ('hda', 'hdca', 'ldda'):
            return {'src': parts[0], 'id': parts[1]}

    # Booleans
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False

    # Numbers
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass

    return value


def _resolve_values(obj):
    """Recursively resolve dataset reference strings in a loaded YAML dict."""
    if isinstance(obj, dict):
        return {k: _resolve_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_values(item) for item in obj]
    if isinstance(obj, str):
        return _parse_value(obj)
    return obj


def _flatten_inputs(data, prefix=''):
    """Flatten a nested dict into pipe-delimited keys for BioBlend legacy format."""
    flat = {}
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f'{prefix}|{key}' if prefix else key
            if isinstance(value, dict):
                # Check if it's a dataset reference
                if 'src' in value and 'id' in value and len(value) == 2:
                    flat[full_key] = value
                else:
                    flat.update(_flatten_inputs(value, full_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    flat.update(_flatten_inputs(item, f'{full_key}_{i}'))
            else:
                flat[full_key] = value
    return flat


def run(context: Context, argv: list):
    parser = argparse.ArgumentParser()
    parser.add_argument('tool_id', help='tool ID to run')
    parser.add_argument(
        '--history', required=True, help='history name or ID to run the tool in'
    )
    parser.add_argument(
        '-f', '--file', dest='input_file', help='YAML/JSON file with tool inputs'
    )
    parser.add_argument(
        '-w', '--wait', action='store_true', help='wait for the job to complete'
    )
    args, remaining = parser.parse_known_args(argv)

    gi = connect(context)

    # Resolve history
    history_id = find_history(gi, args.history)
    if history_id is None:
        print(f'ERROR: history not found: {args.history}')
        return

    # Build inputs from file
    tool_inputs = {}
    if args.input_file:
        with open(args.input_file) as f:
            if args.input_file.endswith('.json'):
                raw = json.load(f)
            else:
                raw = yaml.safe_load(f) or {}
        tool_inputs = _resolve_values(raw)

    # Merge CLI key=value overrides
    for arg in remaining:
        if '=' not in arg:
            print(f'ERROR: invalid input parameter (expected key=value): {arg}')
            return
        key, value = arg.split('=', 1)
        tool_inputs[key] = _parse_value(value)

    if not tool_inputs:
        print('ERROR: no inputs provided. Use -f FILE and/or key=value arguments.')
        return

    # Flatten nested dict to pipe-delimited keys for legacy format
    flat_inputs = _flatten_inputs(tool_inputs)

    print(f'Running tool {args.tool_id} in history {history_id}')
    result = gi.tools.run_tool(history_id, args.tool_id, flat_inputs)

    # Print job info
    jobs = result.get('jobs', [])
    outputs = result.get('outputs', [])
    if jobs:
        for job_info in jobs:
            print(f"Job {job_info['id']}: {job_info['state']}")
    if outputs:
        print(f'{len(outputs)} output(s):')
        for out in outputs:
            print(f"  {out['id']}\t{out.get('name', '')}")

    if args.wait and jobs:
        import time

        job_id = jobs[0]['id']
        print(f'Waiting for job {job_id}...')
        while True:
            job_details = gi.jobs.show_job(job_id)
            state = job_details['state']
            if state in ('ok', 'error', 'deleted', 'paused'):
                print(f'Job {job_id}: {state}')
                break
            time.sleep(5)
