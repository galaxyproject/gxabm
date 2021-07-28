# Benchmarking Scripts
Python Bioblend scripts for automating tasks in Galaxy

## Prerequisites

The only Python requirement (so far) is the Bioblend library.

Create a Python virtual environment and install the bioblend library:

```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install bioblend
```

**NOTE:** On Linux and MacOS system you can set the executable bit on the `workflow.py`
file so you do not need to explicitly run the script with Python.

```
chmod +x workflow.py
./workflow.py help
```

## Commands

**histories**<br/>
Prints all public histories from all users on the server.  Don't do this on Main or EU!

**workflows**<br/>
Prints all published workflows and their expected inputs.

**run**<br/>
Run a workflow.  Currently this is hard coded to simply run the `RNA Workflow Test`.

## Runtime Configuration

A future version of the `workflow.py` script will load runtime configuration from
YAML configuration files.

## Obtaining Results

In the future the results of a workflow invocation will be scraped from the server and
output in a format suitable for importing into a spreadsheet or database.

