import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional

from .client import Client
from .errors import FastFoldError, AuthenticationError

_AGENT_PKG = "fastfold-agent-cli"
_AGENT_CMD = "fastfold"


def _print_err(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _positive_exit(code: int = 0) -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    raise SystemExit(code)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fastfold-cli", description="FastFold CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fastfold-cli fold ...
    fold_parser = subparsers.add_parser("fold", help="Create a folding job")
    fold_parser.add_argument("--sequence", required=True, help="Protein sequence (single letter amino acids)")
    fold_parser.add_argument("--model", required=True, help="Model name (e.g., boltz-2, monomer, multimer, esm1b, boltz)")
    fold_parser.add_argument("--name", required=False, help="Optional job name")
    fold_parser.add_argument("--from-id", required=False, dest="from_id", help="Optional library item ID to associate")
    fold_parser.add_argument("--params", required=False, help="JSON string for advanced params payload")
    fold_parser.add_argument("--constraints", required=False, help="JSON string for constraints payload")
    fold_parser.add_argument("--api-key", required=False, help="API Key (overrides FASTFOLD_API_KEY)")
    fold_parser.add_argument("--base-url", required=False, help="API base URL (default https://api.fastfold.ai)")
    fold_parser.add_argument("--timeout", required=False, type=float, default=30.0, help="HTTP timeout in seconds")

    # fastfold-cli agent ...
    agent_parser = subparsers.add_parser(
        "agent",
        help="Run the FastFold AI research agent (installs fastfold-agent-cli if needed)",
        add_help=False,
    )
    agent_parser.add_argument("args", nargs=argparse.REMAINDER, help="Query or flags passed to the agent")

    return parser


def _parse_json(value: Optional[str], label: str) -> Optional[Dict[str, Any]]:
    if not value:
        return None
    try:
        data = json.loads(value)
        if not isinstance(data, dict):
            raise ValueError(f"{label} must be a JSON object")
        return data
    except Exception as ex:
        raise ValueError(f"Invalid JSON for {label}: {ex}") from ex


def handle_fold(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.getenv("FASTFOLD_API_KEY")
    if not api_key:
        _print_err("Error: FASTFOLD_API_KEY is not set and --api-key was not provided.")
        return 2
    try:
        client = Client(api_key=api_key, base_url=args.base_url, timeout=args.timeout)
        job = client.fold.create(
            sequence=args.sequence,
            model=args.model,
            name=args.name,
            from_id=args.from_id,
            params=_parse_json(args.params, "params"),
            constraints=_parse_json(args.constraints, "constraints"),
        )
        # Print only the job ID to stdout for easy scripting
        print(job.id)
        return 0
    except AuthenticationError as e:
        _print_err(f"Authentication failed: {e}")
        return 2
    except FastFoldError as e:
        _print_err(f"Request failed: {e}")
        return 1
    except Exception as e:
        _print_err(f"Unexpected error: {e}")
        return 1


def _agent_is_installed() -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", _AGENT_PKG],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def handle_agent(args: argparse.Namespace) -> int:
    if not _agent_is_installed():
        sys.stderr.write(f"Installing {_AGENT_PKG} from PyPI...\n")
        sys.stderr.flush()
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", _AGENT_PKG],
        )
        if result.returncode != 0:
            _print_err(f"Failed to install {_AGENT_PKG}.")
            return 1
        sys.stderr.write(f"{_AGENT_PKG} installed.\n")

    agent_args = args.args or []
    # Strip leading '--' separator that argparse may leave
    if agent_args and agent_args[0] == "--":
        agent_args = agent_args[1:]

    result = subprocess.run([_AGENT_CMD, *agent_args])
    return result.returncode


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "fold":
        code = handle_fold(args)
        _positive_exit(code)
    elif args.command == "agent":
        code = handle_agent(args)
        _positive_exit(code)
    else:
        parser.print_help()
        _positive_exit(1)




