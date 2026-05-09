# Fastfold SDK

Python SDK and CLI for Fastfold jobs, workflows, library operations, and reports.

<a href="https://colab.research.google.com/drive/1gW6p82UkzvSSzZTHgcITkzoAihuotkZm?usp=sharing" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## Installation

Install from PyPI:

```bash
pip install fastfold-ai
```

Or for development:

```bash
pip install -e .
```

Requires Python 3.8+.

## Authentication

Set your API key in the environment:

```bash
export FASTFOLD_API_KEY="sk-...your-api-key"
```

You can also pass an API key when creating the client or via the CLI flag `--api-key`.

## SDK Usage

The SDK exposes both typed helpers and capability-oriented services:

- `client.fold` for the simplest fold-job flow
- `client.jobs` for raw payloads, YAML submission, polling, and rendering helpers
- `client.workflows` for generic workflow create/get/status/task-results/execute/YAML APIs
- `client.library` for library item creation and file uploads
- `client.openmm`, `client.openmmdl`, `client.evolla`, and `client.boltzgen` for the most common multi-step workflow flows
- `client.reports` for Slack markdown report submission

For end-to-end walkthroughs, downloadable input files, and additional variants, see:

- [Fold](https://docs.fastfold.ai/sdk/fold)
- [OpenMM](https://docs.fastfold.ai/sdk/openmm)
- [OpenMMDL](https://docs.fastfold.ai/sdk/openmmdl)
- [Evolla](https://docs.fastfold.ai/sdk/evolla)
- [BoltzGen](https://docs.fastfold.ai/sdk/boltzgen)
- [CLI](https://docs.fastfold.ai/sdk/cli)
- [SDK overview](https://docs.fastfold.ai/sdk)

### Fold job

Create a fold job, wait for completion, then inspect the returned artifacts:

```python
from fastfold import Client

client = Client()

job = client.fold.create(
    sequence="LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    model="boltz-2",
    is_public=True,
)

results = client.jobs.wait_for_completion(job.id, poll_interval=5.0, timeout=900.0)
print(results.job.status)
print(results.cif_url())
print(results.metrics().mean_PLDDT)
print(results.get_viewer_link())
```

### OpenMM first run from local files

Submit an OpenMM workflow from a local structure file and its matching PAE JSON:

```python
from fastfold import Client

client = Client()
workflow = client.openmm.submit_from_manual_files(
    pdb_path="./protein.pdb",
    pae_path="./pae.json",
    simulation_name="AF-P00698",
    residue_profile="calvados3",
    temp=293.15,
    ionic=0.15,
    ph=7.5,
    step_size_ns=0.01,
    sim_length_ns=10.0,
    box_length=50,
)
print(workflow.workflow_id)
```

### OpenMMDL from local files

Submit an OpenMMDL workflow from local topology and ligand files:

```python
from fastfold import Client

client = Client()
workflow = client.openmmdl.submit_from_local_files(
    topology_path="./KEAP1kd.pdb",
    ligand_paths=["./IQK.sdf"],
    simulation_name="KEAP1 + IQK",
    input_json={
        "smallMoleculeMode": "single",
        "equilibration": "only_minimization",
        "sim_length_ns": 0.05,
        "step_time_ps": 0.002,
        "failure_retries": 0,
        "addWater": False,
        "addMembrane": False,
        "boxType": "geometry",
        "geomPadding": 1.0,
        "geometryDropdown": "cube",
        "membranePadding": 2.0,
        "writeDCD": True,
        "dcdFrames": 5,
        "pdbInterval_ns": 0.05,
        "writeData": False,
        "writeCheckpoint": False,
    },
)
print(workflow.workflow_id)
```

### Evolla from a local structure file

Upload a **.cif** / **.mmcif** / **.pdb** to your library and start Evolla in one call:

```python
from fastfold import Client

client = Client()
workflow = client.evolla.submit_from_local_file(
    "./structure.cif",
    "What is the likely function of this domain?",
)
print(workflow.workflow_id)
```

### Evolla from a completed fold job

Ask a natural-language question about a structure from an existing fold (uses the same `workflow_input` shape as the web app: `sourceType` / `targetSource` `sequence`, artifact URL, and ids):

```python
from fastfold import Client

client = Client()
workflow = client.evolla.submit_from_fold_job(
    "YOUR_JOB_ID",
    "What is the likely function of this domain?",
)
print(workflow.workflow_id)
```

If the CIF URL in job results is not a signed path that embeds your user id, pass `source_user_id="..."` or set `FASTFOLD_EVOLLA_SOURCE_USER_ID`. See [Evolla](https://docs.fastfold.ai/sdk/evolla).

### BoltzGen minimal workflow

Create a draft BoltzGen workflow, upload a minimal `workflow.yml`, and execute it:

```python
from pathlib import Path

from fastfold import Client

client = Client()
draft = client.boltzgen.create_draft(name="boltzgen_demo")
client.boltzgen.upsert_workflow_yml(
    draft.workflow_id,
    Path("fastfold/examples/boltzgen/minimal.workflow.yml").read_text(),
)
client.boltzgen.execute(draft.workflow_id)
print(draft.workflow_id)
```

For preset bundles, downloadable design-spec files, and multi-spec examples, see
[BoltzGen](https://docs.fastfold.ai/sdk/boltzgen).

### Slack report sharing

Send a markdown report and optionally persist it as a library item:

```python
from fastfold import Client

client = Client()
result = client.reports.send_agent_cli_report(
    "## Demo Report\n\n- Workflow completed.\n- Artifacts are ready.",
    report_name="demo_report",
)
print(result.ok, result.library_item_id)
```

## CLI Usage

The CLI keeps `fastfold-cli fold` working, but it now also exposes resource-oriented subcommands.
For the complete command matrix, see [CLI](https://docs.fastfold.ai/sdk/cli).

```bash
# Fold job
fastfold-cli fold --sequence "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES" --model boltz-2

# OpenMM first run from local files
fastfold-cli workflows openmm from-manual-files \
  --pdb ./protein.pdb \
  --pae ./pae.json \
  --simulation-name AF-P00698 \
  --force-field calvados3 \
  --temperature 293.15 \
  --ionic 0.15 \
  --ph 7.5 \
  --step-size-ns 0.01 \
  --sim-length-ns 10 \
  --box-length 50

# OpenMMDL from local files
fastfold-cli workflows openmmdl from-local-files \
  --topology ./KEAP1kd.pdb \
  --ligand ./IQK.sdf \
  --simulation-name "KEAP1 + IQK" \
  --input-json fastfold/examples/openmmdl/workflow_input.json

# Evolla from a local structure
fastfold-cli workflows evolla from-file ./structure.cif --question "What is the function of this protein?"

# Evolla from fold results
fastfold-cli workflows evolla from-fold-job YOUR_JOB_ID --question "What is the function of this protein?"

# BoltzGen draft
fastfold-cli workflows boltzgen create-draft --name demo

# Report sharing
fastfold-cli reports slack --markdown-file fastfold/examples/reports/sample_report.md
```

Most create and inspection commands are script-friendly: they print IDs by default, or full JSON with `--json`.

## Packaged Examples

Small, reusable text assets ship under `fastfold/examples/`:

- `fastfold/examples/fold/job_payload.json`
- `fastfold/examples/openmm/from_manual_files.json`
- `fastfold/examples/openmm/from_fold_job.json`
- `fastfold/examples/openmmdl/workflow_input.json`
- `fastfold/examples/openmmdl/from_local_files.json`
- `fastfold/examples/openmmdl/quick_water_box.workflow_input.json`
- `fastfold/examples/openmmdl/quick_membrane.workflow_input.json`
- `fastfold/examples/evolla/from_fold_job.template.json`
- `fastfold/examples/boltzgen/minimal.workflow.yml`
- `fastfold/examples/boltzgen/design_spec.example.yaml`
- `fastfold/examples/boltzgen/replacements.example.json`
- `fastfold/examples/fold/boltz2_affinity_input.yaml`
- `fastfold/examples/reports/sample_report.md`

Larger reference bundles and downloadable preset files live in the docs:

- [SDK overview](https://docs.fastfold.ai/sdk)
- [OpenMM](https://docs.fastfold.ai/sdk/openmm)
- [OpenMMDL](https://docs.fastfold.ai/sdk/openmmdl)
- [Evolla](https://docs.fastfold.ai/sdk/evolla)
- [BoltzGen](https://docs.fastfold.ai/sdk/boltzgen)
