# Automated Benchmarking in Galaxy
An opinionated Python Bioblend script for automating benchmarking tasks in Galaxy.

## Installation

It is recommended to install `abm` into its own virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install gxabm
```


### From Source

1. Clone the GitHub repository.
   ```bash
   git clone https://github.com/galaxyproject/gxabm.git
   cd gxabm
   ```
1. Create a virtual env and install the required libraries
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

> :bulb: The included `setup.sh` file can be *sourced* to both activate the virtual environment and create an alias so you do not need to type `python3 abm.py` or `python3 -m abm` all the time.  The remainder of this document assumes that the `setup.sh` file has been *sourced* or `abm` has been installed from PyPI.

```bash
source setup.sh
abm workflow help
```

## Setup

### Prerequisites

To make full use of the `abm` program users will need to install:

1. [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) (optional)
1. [helm](https://helm.sh/docs/intro/install/)

The `kubectl` program is only required when bootstrapping a new Galaxy instance, in particular to obtain the Galaxy URL from the Kubernetes cluster (`abm <cloud> kube url`). Helm is used to update Galaxy's job configuration settings and is **required** to run any experiments.

### Credentials

You will need an [API key](https://training.galaxyproject.org/training-material/faqs/galaxy/preferences_admin_api_key.html) for every Galaxy instance you would like to interact with. You will also need the *kubeconfig* file for each Kubernetes cluster.  The `abm` script loads the Galaxy server URLs, API keys, and the location of the *kubeconfig* files from a YAML configuration file. The profile is searched for in the following order:

1. `.abm/profile.yml` (current directory)
2. `~/.abm/profile.yml` (home directory)
3. `.abm-profile.yml` (current directory)

You can use the `samples/profile.yml` file as a starting point.

By default `kubectl` expects that all *kubeconfig*s are stored in a single configuration file located at `$HOME/.kube/config`. However, this is a system-wide configuration making it difficult for two processes to operate on different Kubernetes clusters at the same time.  Therefore `abm` expects each cluster to store its configuration in its own *kubeconfig* file in a directory named `$HOME/.kube/configs`.

:bulb: It is also possible to create Galaxy users and their API keys directly with `abm`.

```bash
abm <cloud> user create username email@example.org password
abm <cloud> user key email@example.org
```

> :warning: Creating users and their API keys requires that a *master api key* has been configured for Galaxy.

## Usage

To get general usage information run the command:

```bash
abm help
```

You can get information about a specific `abm` command with:

```bash
abm workflow help
```

When running a command (i.e. not just printing help) you will need to specify the Galaxy instance to target as the first parameter:

```bash
abm aws workflow list
abm aws benchmark run benchmarks/paired-dna.yml
```

You can set the log level for debugging with the `--log` flag:

```bash
abm --log DEBUG aws workflow list
```

Valid log levels are: `DEBUG`, `INFO`, `WARN`, `WARNING`, `ERROR`, `FATAL`, `CRITICAL`.

### Terms and Definitions

**workflow**<br/>
A [Galaxy workflow](https://galaxyproject.org/learn/advanced-workflow/). Workflows in `abm` are managed with the `workflow` sub-command. Workflows can **not** be run directly via the `abm` command, but are run through the *benchmark* or *experiment* commands.

**benchmark**<br/>
A *benchmark* consists of one or more *workflows* with their inputs and outputs defined in a YAML configuration file. See the [Benchmark Configuration](#benchmark-configuration) section for instructions on defining a *benchmark*.

**experiment**<br/>
An *experiment* consists of one or more benchmarks to be run on one or more cloud providers. Experiments run benchmarks across clouds in parallel using threads. Each experiment definition consists of:
1. The number of *runs* to be executed. Each *benchmark* will be executed this number of times.
1. The *benchmarks* to be executed
1. The cloud providers the *benchmarks* should be executed on
1. The job rule configurations to be used. The job rule configurations define the number of CPUs and amount of memory to be allocated to the tools being benchmarked.

See the [Experiment Configuration](#experiment-configuration) section for instructions on defining an *experiment*.


## Instance Configuration

Before ABM can interact with a Galaxy cluster an entry for that cluster needs to be created in ABM's `~/.abm/profile.yml` configuration file.  Since the profile is just a YAML file it can be edited in any text editor to add the entry with the URL, API key, and kubeconfig location. Or you can use `abm` commands to create the entry:

1. Create a new entry for *cloud* in the profile. The name can be anything you want, as long as that name has not already been used. The *kubeconfig* will have been generated when the cluster was provisioned; how it is obtained depends on the cloud provider.
   ```bash
   abm config create cloud /path/to/kubeconfig
   ```

2. Set the Galaxy URL. The `abm cloud kube url` command can be used to determine Galaxy's URL, but see the [Caveats](#caveats-and-known-problems) section for known problems. If that does not work you can also use `kubectl get svc -n galaxy` to find the ingress service name and `kubectl describe svc -n galaxy service-name` to find the ingress URL.
   ```bash
   abm config url cloud https://galaxy.url
   ```

3. Create a new user in the Galaxy instance. The email address should be specified in the Galaxy `admin_users` section of the `values.yml` file used when installing Galaxy to the cluster. If the user is not an admin user then installing tools will fail.
   ```bash
   abm cloud user create username user_email@example.org userpassword
   ```

4. Fetch the user's API key and save it to the profile.
   ```bash
   key=$(abm cloud user apikey user_email@example.org)
   abm config key cloud $key
   ```

5. Verify the configuration.
   ```bash
   abm config show cloud
   ```


## Benchmark Configuration

The runtime parameters for benchmarking runs are specified in a YAML configuration file.  The configuration file can contain more than one runtime configuration specified as a YAML list. This file can be stored anywhere; several examples are included in the `samples/benchmarks` directory.

The YAML configuration for a single workflow looks like:

```yaml
- workflow_id: Variant analysis on WGS PE data
  output_history_base_name: Variant-Calling
  reference_data:
    - name: Reference Transcript (FASTA)
      dataset_id: 50a269b7a99356aa
  runs:
    - history_name: 2GB
      inputs:
      - name: Paired Collection
        collection: SRR24043307-2GB
      - name: GenBank genome
        dataset_id: GRCh38.p14.gbff.gz
      - name: Name for genome database
        value: h38
    - history_name: 4GB
      inputs:
      - name: FASTQ RNA Dataset
        dataset_id: 1faa2d3b2ed5c436
```

- **workflow_id**<br/>
  The name or ID of the workflow to run. Both human-readable workflow names (e.g., `Variant analysis on WGS PE data`) and Galaxy hex IDs (e.g., `d6d3c2119c4849e4`) are supported.

- **output_history_base_name**  (optional)<br/>
  Name to use as the basis for histories created.  If the *output_history_base_name* is not specified then the  *workflow_id* is used.

- **reference_data** (optional)<br/>
  Input data that is the same for all benchmarking runs and only needs to be set once.  See the section on *inputs* below for a description of the fields

- **runs**<br/>
  Input definitions for a benchmarking run.  Each run definition should contain:

  - **history_name** (optional) <br/>
    The name of the history created for the output.  The final output history name is generated by concatenating the *output_history_base_name* from above and the *history_name*.  If the *history_name* is not specified an incrementing integer counter is used.
  - **inputs**<br/>
    The one or more inputs to the workflow.  Each input specification requires a **name** (the input name as specified in the workflow editor) and one of the following:
    1. **dataset_id** — a dataset name or History API ID for single dataset inputs (`hda`).
    2. **collection** — the name of an existing dataset collection (`hdca`).
    3. **value** — a plain text parameter value (e.g., a database name or string argument).
    4. **paired** — defines a paired dataset collection to be created on the fly from individual datasets.

## Experiment Configuration

Each *experiment* is defined by a YAML configuration file. See `samples/experiment.yaml` for an example.

```yaml
name: Benchmarking DNA
runs: 3
benchmark_confs:
  - benchmarks/dna-named.yml
cloud:
  - tacc1
  - tacc2
job_configs:
  - 4x8
  - 8x16
```
- **name**<br/>
The name of the experiment.  This value is not currently used.
- **runs**<br/>
The number of times each *benchmark* will be executed.  **Note** a *benchmark* configuration may itself define more than one *workflow* execution.
- **benchmark_confs**<br/>
The *benchmark* configurations to be executed during the *experiment*. These paths are expected to be relative to the current working directory.
- **cloud**<br/>
The cloud providers, as defined in the `profile.yml` file, where the experiments will be run.  The cloud provider instances must already have the *workflows* and history datasets uploaded and available for use.
- **job_configs**<br/>
The `jobs.rules.container_mapper_rules` files that define the CPU and memory resources allocated to tools.  These are resolved as `rules/<name>.yml` relative to the current working directory. See `samples/benchmarks/rules/` for examples.

## Transferring Data Between Instances

### Moving Workflows

Use the `workflow download` and `workflow upload` commands to transfer Galaxy *workflows* between Galaxy instances.

```bash
abm cloud1 workflow download <workflow ID> /path/to/save/workflow.ga
abm cloud2 workflow upload /path/to/save/workflow.ga
```

**NOTE** the name of the saved file (workflow.ga in the above example) is unrelated to the name of the workflow as it will appear in the Galaxy user interface or when listed with the `workflow list` command.

### Moving Benchmarks

The `benchmark translate` and `benchmark validate` commands can be used when moving workflows and datasets between Galaxy instances.  The `benchmark translate` command takes the path to a *benchmark* configuration file, translates the workflow and dataset ID values to their name as they appear in the Galaxy user interface, and writes the configuration to stdout.  To save the translated workflow configuration, redirect the output to a file:

```bash
abm aws benchmark translate config/rna-seq.yml > benchmarks/rna-seq-named.yml
```

Then use the `benchmark validate` command to ensure that the other Galaxy instance has the same workflow and datasets installed:

```bash
abm gcp benchmark validate config/rna-seq-named.yml
```

### Moving Histories

#### Exporting Histories

1. Ensure the history is publicly available (i.e. published) on the Galaxy instance.  You can do this through the Galaxy user interface or via the `history publish` command:
   ```bash
   abm cloud history publish <history id>
   ```
   If you do not know the `<history id>` you can find it with `abm cloud history list`.

2. Export the history:
   ```bash
   abm cloud history export <history id>
   ```
   Make note of the URL that is returned from the `history export` command as this is the URL to use to import the history to another Galaxy instance. Depending on the size of the datasets in the history it may take several hours for the history to be exported, during which time your computer terminal will be blocked.  Use the `--no-wait` option if you do not want `history export` to block until the export is complete.
   ```bash
   abm cloud history export <history id> --no-wait
   ```
   The `history export` command will return immediately and print the job ID for the export job.  Use this job ID to obtain the status of the job and determine when it has completed.
   ```bash
   abm cloud job show <job id>
   ```
   Once a history has been exported the first time, and as long as it has not changed, running `history export` again will simply print the URL and exit without re-exporting the history.  This is useful when the `--no-wait` option was specified and you need to determine the URL to use for importing.

> :bulb: A history should only be exported once and the URL re-used on new benchmarking instances as they are created. Use the `~/.abm/histories.yml` file to record the URLs so they can be easily reused with the `history import` command.

#### Importing Histories

To import a history use the URL returned from the `history export` command:

```bash
abm dest history import URL

# For example
abm dest history import https://usegalaxy.org/history/export_archive?id=9198b7907edea3fa&jeha_id=02700395dbc14520
```

You can also import histories defined in `~/.abm/histories.yml` by specifying the YAML dictionary key name:

```bash
abm dest history import rna
```

## Contributing

Fork this repository and then create a working branch for yourself from the `dev` branch. All pull requests should target `dev` and not the `master` branch.

```bash
git clone https://github.com/galaxyproject/gxabm.git
cd gxabm
git checkout -b my-branch
```

If you decide to work on one of the [issues](https://github.com/galaxyproject/gxabm/issues) be sure to assign yourself to that issue to let others know the issue is taken.

## Versioning

Use the `bin/bump.sh` script to update the version number in `abm/VERSION`:

```bash
bin/bump.sh major
bin/bump.sh minor
bin/bump.sh patch
bin/bump.sh release
```

The `patch` command is only valid for *development* versions, that is, a version number followed by a dash, followed by some characters, followed by some digits. For example `2.0.0-rc1` or `2.1.0-dev.8`.  Use `bin/bump.sh release` to move from a *development* build to a *release* build.

## Building and Deploying

```bash
make clean
make dist
make test-deploy
make deploy
```

The `make test-deploy` deploys artifacts to TestPyPI server and is intended for deploying and testing *development* builds.  Development build **should not** be deployed to PyPI.

## Caveats and Known Problems

ABM relies on the names of things (datasets, histories, etc.) to find them on the Galaxy instance. This can cause problems as nothing in Galaxy forces names to be unique.  For example, if the Galaxy instance contains more than one dataset named `SRR35689022.fastq` ABM will select the first one returned by Galaxy, which may or may not be the one you intended.  It is up to the user to ensure important items have sensible, unique names.

ABM is intended to run on a dedicated Galaxy instance with no other users.  It can be used on multi-user systems, but ABM does not play nicely with others and some commands may cause ABM to restart the server. Care must also be taken when performing destructive commands such as deleting datasets or histories.  

The `abm kube url` command is intended to retrieve the URL needed to access the Galaxy instance on the Kubernetes cluster.  However, there are a few issues that make this not so straight-forward:

- The name of the ingress controller is not consistent.  Sometimes it is `ingress-nginx-controller` (AWS) and sometimes it is simply `ingress-nginx` (GCP).
- Sometimes the instance is accessed via the `hostname` field (AWS) and sometimes the `ip` field.
- The URL for the Galaxy instance may have an arbitrary path included, e.g. `https://hostname` or `https://hostname/galaxy` or `https://hostname/something/galaxy`.

