# Benchmarking Scripts
Python Bioblend scripts for automating tasks in Galaxy

## Prerequisites

The only Python requirement (so far) is the Bioblend library.

Create a Python virtual environment and install the *bioblend* and *pyyaml* libraries:

```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install bioblend
pip install pyyaml
```

**NOTE:** On Linux and MacOS system you can set the executable bit on the `workflow.py`
file so you do not need to explicitly run the script with Python.

```
chmod +x workflow.py
./workflow.py help
```

### SYNOPSIS
    Run workflows on remote Galaxy instances.

### USAGE
./workflow.py [-k KEY] [-s SERVER] [COMMAND...]

### OPTIONS
-k|--key GALAXY_API_KEY
    Specify the Galaxy API for the remote server
-s|--server
    The URL for the remote Galaxy server

### COMMANDS
wf|workflows
    List all public workflows and their inputs
hist|histories
    List all public histories and their datasets
st|status <invocation_id>
    If the invocation_id is specified then the invocation report for that workflow
    invocation is returned.  Otherwise lists all the workflow invocations on
    the server
run <configuration.yml>
    Run the workflow specified in the configuration.yml file.
help|-h|--help
    Prints this help screen

When a workflow is run with the `run` command the invocation details will be saved to a JSON file with the invocation ID as the file name with a *.json* extension.  Use the invocation ID with the `st` (`status`) command to get detailed information about that invocation.

### EXAMPLES

    ./workflow.py run configs/paired-dna.yml
    ./workflow.py st da4e6f496166d13f

## Runtime Configuration

The runtime parameters for a benchmarking run are specified in a YAML file.  This file can be stored anywhere, but several examples are included in the `config` directory. The configuration YAML must include:

- **workflow_id**
  The ID of the workflow to run.
- **inputs**
  A list of dictionaries that specify:
  1. **name** the name of the input as specifed in the the workflow editor.
  2. **dataset_id**: the ID of the dataset to be used as input.  This dataset can be located in any publicy accessible history.
- **output_history_name**
  A new history with this name will be created and all processed datasets will be stored into this history.

#### Example

```
workflow_id: b94314cb9cb46380
inputs:
  - name: FASTQ Dataset
    dataset_id: e49d4a2f705b9571
output_history_name: Example Paired DNA Test
```



## Obtaining Results

TBD. 

Scrape the results of a workflow invocation and output in a format suitable for importing into a spreadsheet or database. See issue [#3](../../issues/3). 

### Contributing

Fork this repository and then create a working branch for yourself base off the `dev` branch. All pull requests should target  `dev` and not the `master` branch.

```bash
git clone https://github.com/ksuderman/bioblend-scripts.git
cd bioblend-scripts
git checkout -b my-branch
```

If you decide to work on one of the [issues](bioblend-scripts/issues) be sure to assign yourself to that issue to let others know the issue is taken.

