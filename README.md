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

response = client.fold.create(
    sequence="LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES",
    model="boltz-2",
)

print(response.id)  # jobId
```

Advanced options:

```python
job = client.fold.create(
    sequence="...",
    model="boltz-2",
    name="My Job",
    from_id=None,  # maps to ?from=<uuid>
    params={"recyclingSteps": 3},  # merged into params
    constraints={
        "pocket": [
            {
                "binder": {"chain_id": "A"},
                "contacts": [{"chain_id": "B", "res_idx": 10}],
            }
        ]
    },
)
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

## Python API Reference (minimal)

- `Client(api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 30.0)`
  - Reads `FASTFOLD_API_KEY` if `api_key` is not provided.
- `Client.fold.create(sequence: str, model: str, name: Optional[str] = None, from_id: Optional[str] = None, params: Optional[dict] = None, constraints: Optional[dict] = None) -> Job`
  - Returns a `Job` object with `id`, `run_id`, `name`, `status`, `sequence_ids`, and `raw`.


