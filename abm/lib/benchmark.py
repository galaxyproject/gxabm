import os
import sys
import json
import yaml
import logging
import argparse
from lib import Keys, INVOCATIONS_DIR, METRICS_DIR
from lib.common import connect, Context
from bioblend.galaxy import GalaxyInstance

log = logging.getLogger('abm')

def run_cli(context: Context, args: list):
    """
    Runs a single workflow defined by *args[0]*

    :param args: a list that contains:
    args[0] - the path to the benchmark configuration file
    args[1] - the prefix to use when creating the new history in Galaxy
    args[2] - the name of the experiment, if part of one. This is used to
              generate output folder names.

    :return: True if the workflows completed sucessfully. False otherwise.
    """
    if len(args) == 0:
        print('ERROR: no workflow configuration specified')
        return

    parser = argparse.ArgumentParser()
    parser.add_argument('workflow_path')
    parser.add_argument('-p', '--prefix')
    parser.add_argument('-e', '--experiment')
    a = parser.parse_args(args)
    #workflow_path = args[0]
    if not os.path.exists(a.workflow_path):
        print(f'ERROR: can not find workflow configuration {a.workflow_path}')
        return
    run(context, a.workflow_path, a.prefix, a.experiment)


def run(context: Context, workflow_path, history_prefix: str, experiment: str):
    # if len(args) > 1:
    #     history_prefix = args[1]
    #     if len(args) > 2:
    #         experiment = args[2].replace(' ', '_').lower()


    if os.path.exists(INVOCATIONS_DIR):
        if not os.path.isdir(INVOCATIONS_DIR):
            print('ERROR: Can not save invocation status, directory name in use.')
            sys.exit(1)
    else:
        os.mkdir(INVOCATIONS_DIR)


    if os.path.exists(METRICS_DIR):
        if not os.path.isdir(METRICS_DIR):
            print('ERROR: Can not save metrics, directory name in use.')
            #sys.exit(1)
            return False
    else:
        os.mkdir(METRICS_DIR)

    invocations_dir = INVOCATIONS_DIR
    metrics_dir = METRICS_DIR
    if experiment is not None:
        invocations_dir = os.path.join(INVOCATIONS_DIR, experiment)
        if not os.path.exists(invocations_dir):
            os.makedirs(invocations_dir, exist_ok=True)
        metrics_dir = os.path.join(METRICS_DIR, experiment)
        if not os.path.exists(metrics_dir):
            os.makedirs(metrics_dir, exist_ok=True)

    gi = connect(context)
    workflows = parse_workflow(workflow_path)

    print(f"Found {len(workflows)} workflow definitions")
    for workflow in workflows:
        wf_name = workflow[Keys.WORKFLOW_ID]
        wfid = find_workflow_id(gi, wf_name)
        if wfid is None:
            print(f"Unable to load the workflow ID for {workflow[Keys.WORKFLOW_ID]}")
            return False
        else:
            print(f"Found workflow id {wfid}")
        inputs = {}
        input_names = []
        history_base_name = wfid
        if Keys.HISTORY_BASE_NAME in workflow:
            history_base_name = workflow[Keys.HISTORY_BASE_NAME]

        if Keys.REFERENCE_DATA in workflow:
            for spec in workflow[Keys.REFERENCE_DATA]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    return False
                dsname = spec[Keys.NAME]
                dsid = find_dataset_id(gi, dsname)
                print(f"Reference input dataset {dsid}")
                inputs[input[0]] = {'id': dsid, 'src': 'hda'}
                input_names.append(dsname)

        count = 0
        for run in workflow[Keys.RUNS]:
            count += 1
            if Keys.HISTORY_NAME in run:
                output_history_name = f"{history_base_name} {run[Keys.HISTORY_NAME]}"
            else:
                output_history_name = f"{history_base_name} run {count}"
            #inputs = []
            for spec in run[Keys.INPUTS]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    return False

                dsname = spec[Keys.DATASET_ID]
                input_names.append(dsname)
                #inputs.append(dsname)
                dsid = find_dataset_id(gi, dsname)
                print(f"Input dataset ID: {dsname} [{dsid}]")
                inputs[input[0]] = {'id': dsid, 'src': 'hda'}

            print(f"Running workflow {wfid}")
            new_history_name = output_history_name
            if history_prefix is not None:
                new_history_name = f"{history_prefix} {output_history_name}"
            invocation = gi.workflows.invoke_workflow(wfid, inputs=inputs, history_name=new_history_name)
            id = invocation['id']
            invocations = gi.invocations.wait_for_invocation(id, 86400, 10, False)
            print("Waiting for jobs")
            if history_prefix is not None:
                parts = history_prefix.split()
                invocations['run'] = parts[0]
                invocations['cloud'] = parts[1]
                invocations['job_conf'] = parts[2]
                invocations['output_dir'] = metrics_dir
            invocations['inputs'] = ' '.join(input_names)
            #TODO Change this output path. (Change it to what? KS)
            output_path = os.path.join(invocations_dir, id + '.json')
            with open(output_path, 'w') as f:
                json.dump(invocations, f, indent=4)
                print(f"Wrote invocation data to {output_path}")
            wait_for_jobs(context, gi, invocations)
    print("Benchmarking run complete")
    return True



def translate(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no workflow configuration specified')
        return
    workflow_path = args[0]
    if not os.path.exists(workflow_path):
        print(f'ERROR: can not find workflow configuration {workflow_path}')
        return

    gi = connect(context)
    # wf_index,ds_index = create_rev_index(gi)
    workflows = parse_workflow(args[0])
    for workflow in workflows:
        wfid = workflow[Keys.WORKFLOW_ID]
        wfinfo = gi.workflows.show_workflow(wfid)
        if wfinfo is None or 'name' not in wfinfo:
            print(f"Warning: unable to translate workflow ID {wfid}")
        else:
            workflow[Keys.WORKFLOW_ID] = wfinfo['name']
        # if workflow[Keys.WORKFLOW_ID] in wf_index:
        #     workflow[Keys.WORKFLOW_ID] = wf_index[workflow[Keys.WORKFLOW_ID]]
        # else:
        #     print(f"Warning: no workflow id for {workflow[Keys.WORKFLOW_ID]}")
        if Keys.REFERENCE_DATA in workflow:
            for ref in workflow[Keys.REFERENCE_DATA]:
                dsid = ref[Keys.DATASET_ID]
                dataset = gi.datasets.show_dataset(dsid)
                if dataset is None:
                    print(f"Warning: could not translate dataset ID {dsid}")
                else:
                    ref[Keys.DATASET_ID] = dataset['name']
        for run in workflow[Keys.RUNS]:
            for input in run[Keys.INPUTS]:
                dsid = input[Keys.DATASET_ID]
                dataset = gi.datasets.show_dataset(dsid)
                if dataset is None:
                    print(f"Warning: could not translate dataset ID {dsid}")
                else:
                    input[Keys.DATASET_ID] = dataset['name']
    print(yaml.dump(workflows))


def validate(context: Context, args: list):
    if len(args) == 0:
        print('ERROR: no workflow configuration specified')
        return

    workflow_path = args[0]
    if not os.path.exists(workflow_path):
        print(f'ERROR: can not find workflow configuration {workflow_path}')
        return
    print(f"Validating workflow on {context.GALAXY_SERVER}")
    workflows = parse_workflow(workflow_path)
    gi = connect(context)
    total_errors = 0
    for workflow in workflows:
        wfid = workflow[Keys.WORKFLOW_ID]
        try:
            wfid = find_workflow_id(gi, wfid)
        except:
            wfid = None

        if wfid is None:
            print(f"The workflow '{workflow[Keys.WORKFLOW_ID]}' does not exist on this server.")
            return
        else:
            print(f"Workflow: {workflow[Keys.WORKFLOW_ID]} -> {wfid}")
        inputs = {}
        errors = 0
        history_base_name = wfid
        if Keys.HISTORY_BASE_NAME in workflow:
            history_base_name = workflow[Keys.HISTORY_BASE_NAME]

        if Keys.REFERENCE_DATA in workflow:
            for spec in workflow[Keys.REFERENCE_DATA]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    errors += 1
                    #sys.exit(1)
                else:
                    dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
                    if dsid is None:
                        print(f"ERROR: Reference dataset not found {spec[Keys.DATASET_ID]}")
                        errors += 1
                    else:
                        print(f"Reference input dataset {spec[Keys.DATASET_ID]} -> {dsid}")
                        inputs[input[0]] = {'id': dsid, 'src': 'hda'}

        count = 0
        for run in workflow[Keys.RUNS]:
            count += 1
            for spec in run[Keys.INPUTS]:
                input = gi.workflows.get_workflow_inputs(wfid, spec[Keys.NAME])
                if input is None or len(input) == 0:
                    print(f'ERROR: Invalid input specification for {spec[Keys.NAME]}')
                    errors += 1
                else:
                    dsid = find_dataset_id(gi, spec[Keys.DATASET_ID])
                    if dsid is None:
                        print(f"ERROR: Dataset not found {spec[Keys.DATASET_ID]}")
                        errors += 1
                    else:
                        print(f"Input dataset: {spec[Keys.DATASET_ID]} -> {dsid}")
                        inputs[input[0]] = {'id': dsid, 'src': 'hda'}

        if errors == 0:
            print("This workflow configuration is valid and can be executed on this server.")
        else:
            print("---------------------------------")
            print("WARNING")
            print("The above problems need to be corrected before this workflow configuration can be used.")
            print("---------------------------------")
        total_errors += errors

    return total_errors == 0


def wait_for_jobs(context, gi: GalaxyInstance, invocations: dict):
    """ Blocks until all jobs defined in the *invocations* to complete.

    :param gi: The *GalaxyInstance** running the jobs
    :param invocations:
    :return:
    """
    wfid = invocations['workflow_id']
    hid = invocations['history_id']
    run = invocations['run']
    cloud = invocations['cloud']
    conf = invocations['job_conf']
    inputs = invocations['inputs']
    output_dir = invocations['output_dir']
    for step in invocations['steps']:
        job_id = step['job_id']
        if job_id is not None:
            retries = 3
            done = False
            while not done and retries >= 0:
                print(f"Waiting for job {job_id} on {context.GALAXY_SERVER}")
                try:
                    # TDOD Should retry if anything throws an exception.
                    status = gi.jobs.wait_for_job(job_id, 86400, 10, False)
                    data = gi.jobs.show_job(job_id, full_details=True)
                    metrics = {
                        'run': run,
                        'cloud': cloud,
                        'job_conf': conf,
                        'workflow_id': wfid,
                        'history_id': hid,
                        'inputs': inputs,
                        'metrics': data,
                        'status': status,
                        'server': context.GALAXY_SERVER
                    }
                    output_path = os.path.join(output_dir, f"{job_id}.json")
                    with open(output_path, "w") as f:
                        json.dump(metrics, f, indent=4)
                        print(f"Wrote metrics to {output_path}")
                    done = True
                except ConnectionError as e:
                    print(f"ERROR: connection dropped while waiting for {job_id}")
                    retries -= 1
                except Exception as e:
                    print(f"ERROR: {e}")
                    retries -= 1


def parse_workflow(workflow_path: str):
    if not os.path.exists(workflow_path):
        print(f'ERROR: could not find workflow file {workflow_path}')
        return None

    with open(workflow_path, 'r') as stream:
        config = yaml.safe_load(stream)
        # try:
        #     config = yaml.safe_load(stream)
        #     # print(f"Loaded {name}")
        # except yaml.YAMLError as exc:
        #     print('Error encountered parsing the YAML input file')
        #     print(exc)
        #     #TODO Don't do this...
        #     sys.exit(1)
    return config


def find_workflow_id(gi, name_or_id):
    try:
        wf = gi.workflows.show_workflow(name_or_id)
        return wf['id']
    except:
        pass

    try:
        wf = gi.workflows.get_workflows(name=name_or_id, published=True)
        return wf[0]['id']
    except:
        pass
    #print(f"Warning: unable to find workflow {name_or_id}")
    return None


def find_dataset_id(gi, name_or_id):
    # print(f"Finding dataset {name_or_id}")
    try:
        ds = gi.datasets.show_dataset(name_or_id)
        return ds['id']
    except:
        pass

    try:
        # print('Trying by name')
        ds = gi.datasets.get_datasets(name=name_or_id)  # , deleted=True, purged=True)
        if len(ds) > 0:
            return ds[0]['id']
    except:
        print('Caught an exception')
        print(sys.exc_info())
    #print(f"Warning: unable to find dataset {name_or_id}")
    return None



