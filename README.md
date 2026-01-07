# FastFold Python SDK and CLI

Python client and CLI for the FastFold Jobs API.

## Installation

From the project root:

```bash
pip install .
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

```python
from fastfold import Client

client = Client()  # Reads FASTFOLD_API_KEY from env by default

myJob = client.fold.create(
    sequence="LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    model="boltz-2",
    is_public=True,
)
print("Job ID:", myJob.id)

# Wait for completion, then fetch CIF URL (boltz-2 complex)
results = client.jobs.wait_for_completion(myJob.id, poll_interval=5.0, timeout=900.0)
print("Status:", results.job.status)
print("CIF URL:", results.cif_url())
print("Mean PLDDT:", results.metrics().mean_PLDDT)
```

Advanced usage for Boltz-2 with Affinity prediction and pockets:

```python
myJob = client.fold.create(
    name="Streptococcal protein G with Pocket",
    model="boltz-2",
    sequences=[
        {
            "proteinChain": {
                "sequence": "MTYKLILNGKTLKGETTTEAVDAATAEKVFKQYANDNGVDGEWTYDDATKTFTVTE",
                "count": 1,
                "chain_id": "A",
                "label": "mobile-purple",
            }
        },
        {
            "ligandSequence": {
                "sequence": "ATP",
                "count": 1,
                "chain_id": "B",
                "label": "constitutional-brown",
                "is_ccd": True,
                "property_type": "affinity",
            }
        },
    ],
    params={
        "modelName": "boltz-2",
        "weightSet": "Boltz-2",
        "relaxPrediction": True,
        "method": "Boltz-2",
        "recyclingSteps": 3,
        "samplingSteps": 200,
        "diffusionSample": 1,
        "stepScale": 1.638,
        "affinityMwCorrection": False,
        "samplingStepsAffinity": 200,
        "diffusionSamplesAffinity": 5,
    },
    constraints={
        "pocket": [
            {
                "binder": {"chain_id": "B"},
                "contacts": [
                    {"chain_id": "A", "res_idx": 12},
                    {"chain_id": "A", "res_idx": 15},
                    {"chain_id": "A", "res_idx": 18},
                ],
            }
        ]
    },
)

# Wait for completion and fetch CIF URL (boltz-2 complex)
results = client.jobs.wait_for_completion(myJob.id, poll_interval=5.0, timeout=900.0)
print("Completed CIF URL:", results.cif_url())
metrics = results.metrics()
print("Mean PLDDT:", metrics.mean_PLDDT)
print("ptm_score:", metrics.ptm_score)
print("iptm_score:", metrics.iptm_score)
# Boltz-2 affinity metrics (present only if provided by API)
print("affinity_pred_value:", metrics.affinity_pred_value)
print("affinity_probability_binary:", metrics.affinity_probability_binary)
print("affinity_pred_value1:", metrics.affinity_pred_value1)
print("affinity_probability_binary1:", metrics.affinity_probability_binary1)
print("affinity_pred_value2:", metrics.affinity_pred_value2)
print("affinity_probability_binary2:", metrics.affinity_probability_binary2)
```

### Non-complex multi-sequence artifacts (indexing)

```python
# Create a non-complex job with two protein chains and fetch per-sequence artifacts by index
myJob = client.fold.create(
    name="My Protein List",
    model="simplefold_100M",
    sequences=[
        {
            "proteinChain": {
                "sequence": "MCNTNMSVSTEGAASTSQIPASEQETLVRPKPLLLKLLKSVGAQNDTYTMKEIIFYIGQYIMTKRLYDEKQQHIVYCSNDLLGDVFGVPSFSVKEHRKIYAMIYRNLVAV",
                "count": 1,
                "chain_id": "A",
                "label": "specific-white",
            }
        },
        {
            "proteinChain": {
                "sequence": "SQETFSGLWKLLPPE",
                "count": 1,
                "chain_id": "B",
                "label": "wily-amethyst",
            }
        },
    ],
    params={
        "modelName": "simplefold_100M",
        "weightSet": "SimpleFold",
        "method": "SimpleFold",
    },
)

# Wait for completion then access per-sequence artifacts by index
results = client.jobs.wait_for_completion(myJob.id, poll_interval=5.0, timeout=900.0)
# Access per-sequence artifacts by index
cif_url_chain_a = results[0].cif_url()
cif_url_chain_b = results[1].cif_url()

print("Chain A CIF:", cif_url_chain_a)
print("Chain B CIF:", cif_url_chain_b)

m0 = results[0].metrics()
m1 = results[1].metrics()
print("Chain A mean PLDDT:", m0.mean_PLDDT)
print("Chain B mean PLDDT:", m1.mean_PLDDT)
```

### Create with library source (from_id) and additional params

```python
myJob = client.fold.create(
    model="boltz-2",
    sequence="LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    from_id="770e8400-e29b-41d4-a716-446655440002",
    params={"relaxPrediction": True, "recyclingSteps": 2},
)

# Wait for completion
results = client.jobs.wait_for_completion(myJob.id, poll_interval=5.0, timeout=900.0)
print("Completed:", results.job.status)
```

### Fetch results and status

```python
# Prefer waiting for completion in scripts/notebooks
results = client.jobs.wait_for_completion(myJob.id, poll_interval=5.0, timeout=900.0)
status = results.job.status
print("Status:", status)
```

Status could be:

- PENDING: Job queued but not yet initialized
- INITIALIZED: Job created and ready to run
- RUNNING: Job is processing
- COMPLETED: Job finished successfully
- FAILED: Job encountered an error
- STOPPED: Job was stopped before completion

### Update visibility

```python
client.jobs.set_public(myJob.id, True)  # make job publicly accessible
```

### Get artifact URLs

```python
# Ensure we have completed results
results = client.jobs.wait_for_completion(myJob.id, poll_interval=5.0, timeout=900.0)

# Complex jobs (shared artifacts at top level)
if results.job.is_complex:
    cif_url = results.cif_url()
    pdb_url = results.pdb_url()
    pae_url = results.pae_plot_url()
    plddt_url = results.plddt_plot_url()
else:
    # Non-complex: per-sequence artifacts via indexing
    cif_url = results[0].cif_url()
    pdb_url = results[0].pdb_url()
```

### Get metrics

```python
# Ensure the job has completed
results = client.jobs.wait_for_completion(myJob.id, poll_interval=5.0, timeout=900.0)

# Complex (boltz-2) jobs: top-level metrics
if results.job.is_complex:
    metrics = results.metrics()
    print("mean_PLDDT:", metrics.mean_PLDDT)
    print("ptm_score:", metrics.ptm_score)
    print("iptm_score:", metrics.iptm_score)
    print("max_pae_score:", metrics.max_pae_score)
    # Boltz-2 affinity metrics (present only if provided by API)
    print("affinity_pred_value:", metrics.affinity_pred_value)
    print("affinity_probability_binary:", metrics.affinity_probability_binary)
    print("affinity_pred_value1:", metrics.affinity_pred_value1)
    print("affinity_probability_binary1:", metrics.affinity_probability_binary1)
    print("affinity_pred_value2:", metrics.affinity_pred_value2)
    print("affinity_probability_binary2:", metrics.affinity_probability_binary2)
else:
    # Non-complex: per-sequence metrics via indexing
    m0 = results[0].metrics()
    print("Chain A mean_PLDDT:", m0.mean_PLDDT)
    m1 = results[1].metrics()
    print("Chain B mean_PLDDT:", m1.mean_PLDDT)
```

## CLI Usage

Submit a folding job:

```bash
fastfold fold --sequence "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES" --model boltz-2
```

Optional flags:

```bash
fastfold fold \
  --sequence "..." \
  --model boltz-2 \
  --name "My Job" \
  --api-key "sk-..." \
  --base-url "https://api.fastfold.ai"
```

On success the CLI prints the created job ID to stdout.
