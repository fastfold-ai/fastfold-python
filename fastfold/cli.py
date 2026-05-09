import argparse
import json
import os
import sys
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .client import Client
from .errors import AuthenticationError, FastFoldError

def _print_err(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _positive_exit(code: int = 0) -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    raise SystemExit(code)


def _emit_json(data: Any) -> None:
    print(json.dumps(data, indent=2))


def _add_client_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", required=False, help="API Key (overrides FASTFOLD_API_KEY)")
    parser.add_argument("--base-url", required=False, help="API base URL (default https://api.fastfold.ai)")
    parser.add_argument("--timeout", required=False, type=float, default=30.0, help="HTTP timeout in seconds")


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Print full JSON response.")


def _add_visibility_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--public", dest="is_public", action="store_true", help="Make the resource public.")
    parser.add_argument("--private", dest="is_public", action="store_false", help="Make the resource private.")
    parser.set_defaults(is_public=None)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fastfold-cli", description="Fastfold CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fold_parser = subparsers.add_parser("fold", help="Create a folding job")
    fold_parser.add_argument("--sequence", required=True, help="Protein sequence (single letter amino acids)")
    fold_parser.add_argument("--model", required=True, help="Model name (e.g., boltz-2, openfold3, chai1)")
    fold_parser.add_argument("--name", required=False, help="Optional job name")
    fold_parser.add_argument("--from-id", required=False, dest="from_id", help="Optional library item ID to associate")
    fold_parser.add_argument("--params", required=False, help="JSON or YAML string for advanced params payload")
    fold_parser.add_argument("--constraints", required=False, help="JSON or YAML string for constraints payload")
    _add_client_args(fold_parser)
    _add_json_flag(fold_parser)

    jobs_parser = subparsers.add_parser("jobs", help="Work with fold jobs")
    jobs_subparsers = jobs_parser.add_subparsers(dest="jobs_command", required=True)

    jobs_create = jobs_subparsers.add_parser("create", help="Create a job from a full payload")
    jobs_create.add_argument("--payload", help="Inline JSON or YAML payload.")
    jobs_create.add_argument("--payload-file", help="Payload file path or '-' for stdin.")
    jobs_create.add_argument("--format", choices=["auto", "json", "yaml"], default="auto", help="Payload format.")
    jobs_create.add_argument("--from-id", dest="from_id", help="Optional library item ID to associate.")
    _add_client_args(jobs_create)
    _add_json_flag(jobs_create)

    jobs_from_yaml = jobs_subparsers.add_parser("from-yaml", help="Create a Boltz-style job from YAML input")
    jobs_from_yaml.add_argument("--file", required=True, help="YAML file path or '-' for stdin.")
    jobs_from_yaml.add_argument("--model", required=True, help="Model name passed to params.modelName.")
    jobs_from_yaml.add_argument("--name", help="Optional job name override.")
    jobs_from_yaml.add_argument("--from-id", dest="from_id", help="Optional library item ID to associate.")
    jobs_from_yaml.add_argument("--public", action="store_true", help="Make the job public.")
    jobs_from_yaml.add_argument("--draft", action="store_true", help="Create the job without dispatching immediately.")
    jobs_from_yaml.add_argument("--chat-id", help="Optional chat ID.")
    _add_client_args(jobs_from_yaml)
    _add_json_flag(jobs_from_yaml)

    jobs_results = jobs_subparsers.add_parser("results", help="Fetch job results")
    jobs_results.add_argument("job_id", help="Job ID")
    _add_client_args(jobs_results)
    _add_json_flag(jobs_results)

    jobs_wait = jobs_subparsers.add_parser("wait", help="Wait for job completion")
    jobs_wait.add_argument("job_id", help="Job ID")
    jobs_wait.add_argument("--poll-interval", type=float, default=5.0, help="Polling interval in seconds.")
    jobs_wait.add_argument("--wait-timeout", dest="wait_timeout", type=float, default=None, help="Timeout in seconds.")
    jobs_wait.add_argument("--no-log", action="store_true", help="Disable progress logging.")
    _add_client_args(jobs_wait)
    _add_json_flag(jobs_wait)

    jobs_public = jobs_subparsers.add_parser("set-public", help="Toggle job visibility")
    jobs_public.add_argument("job_id", help="Job ID")
    _add_visibility_flags(jobs_public)
    _add_client_args(jobs_public)
    _add_json_flag(jobs_public)

    jobs_yaml = jobs_subparsers.add_parser("render-yaml", help="Render a job payload to YAML")
    jobs_yaml.add_argument("--payload", help="Inline JSON or YAML payload.")
    jobs_yaml.add_argument("--payload-file", help="Payload file path or '-' for stdin.")
    jobs_yaml.add_argument("--format", choices=["auto", "json", "yaml"], default="auto", help="Payload format.")
    _add_client_args(jobs_yaml)

    jobs_json = jobs_subparsers.add_parser("render-json", help="Render a job payload to model-specific JSON")
    jobs_json.add_argument("--payload", help="Inline JSON or YAML payload.")
    jobs_json.add_argument("--payload-file", help="Payload file path or '-' for stdin.")
    jobs_json.add_argument("--format", choices=["auto", "json", "yaml"], default="auto", help="Payload format.")
    _add_client_args(jobs_json)
    _add_json_flag(jobs_json)

    library_parser = subparsers.add_parser("library", help="Work with library items and files")
    library_subparsers = library_parser.add_subparsers(dest="library_command", required=True)

    library_create = library_subparsers.add_parser("create", help="Create a library item")
    library_create.add_argument("--name", required=True, help="Item name.")
    library_create.add_argument("--type", required=True, choices=["file", "folder"], help="Item type.")
    library_create.add_argument("--parent-id", help="Parent folder ID.")
    library_create.add_argument("--file-type", help="File type, e.g. protein/json/yml/ligand.")
    library_create.add_argument("--origin", help="Origin, e.g. USER_UPLOAD.")
    library_create.add_argument("--metadata", help="Inline JSON or YAML metadata object.")
    _add_client_args(library_create)
    _add_json_flag(library_create)

    library_get = library_subparsers.add_parser("get", help="Get a library item")
    library_get.add_argument("item_id", help="Library item ID")
    _add_client_args(library_get)
    _add_json_flag(library_get)

    library_upload = library_subparsers.add_parser("upload", help="Upload files to a library item")
    library_upload.add_argument("item_id", help="Library item ID")
    library_upload.add_argument("files", nargs="+", help="Local file paths to upload.")
    _add_client_args(library_upload)
    _add_json_flag(library_upload)

    workflows_parser = subparsers.add_parser("workflows", help="Work with workflows")
    workflows_subparsers = workflows_parser.add_subparsers(dest="workflows_command", required=True)

    workflows_create = workflows_subparsers.add_parser("create", help="Create a workflow from JSON/YAML payload")
    workflows_create.add_argument("--payload", help="Inline JSON or YAML workflow payload.")
    workflows_create.add_argument("--payload-file", help="Workflow payload file path or '-' for stdin.")
    workflows_create.add_argument("--format", choices=["auto", "json", "yaml"], default="auto", help="Payload format.")
    _add_client_args(workflows_create)
    _add_json_flag(workflows_create)

    workflows_get = workflows_subparsers.add_parser("get", help="Fetch a workflow")
    workflows_get.add_argument("workflow_id", help="Workflow ID")
    workflows_get.add_argument("--public", action="store_true", help="Use the public workflow endpoint.")
    _add_client_args(workflows_get)
    _add_json_flag(workflows_get)

    workflows_status = workflows_subparsers.add_parser("status", help="Fetch workflow status")
    workflows_status.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(workflows_status)
    _add_json_flag(workflows_status)

    workflows_results = workflows_subparsers.add_parser("task-results", help="Fetch workflow task results")
    workflows_results.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(workflows_results)
    _add_json_flag(workflows_results)

    workflows_execute = workflows_subparsers.add_parser("execute", help="Execute a workflow")
    workflows_execute.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(workflows_execute)
    _add_json_flag(workflows_execute)

    workflows_public = workflows_subparsers.add_parser("set-public", help="Toggle workflow visibility")
    workflows_public.add_argument("workflow_id", help="Workflow ID")
    _add_visibility_flags(workflows_public)
    _add_client_args(workflows_public)
    _add_json_flag(workflows_public)

    workflows_graph = workflows_subparsers.add_parser("create-graph", help="Create a draft graph workflow shell")
    workflows_graph.add_argument("--workflow-name", required=True, help="Workflow name, e.g. boltzgen_v1.")
    workflows_graph.add_argument("--name", default="", help="Workflow display name.")
    workflows_graph.add_argument("--create-mode", default="", help="Optional create mode.")
    _add_client_args(workflows_graph)
    _add_json_flag(workflows_graph)

    workflows_get_yml = workflows_subparsers.add_parser("get-yml", help="Fetch workflow YAML")
    workflows_get_yml.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(workflows_get_yml)

    workflows_set_yml = workflows_subparsers.add_parser("set-yml", help="Replace workflow YAML")
    workflows_set_yml.add_argument("workflow_id", help="Workflow ID")
    workflows_set_yml.add_argument("--file", required=True, help="Path to workflow.yml or '-' for stdin.")
    _add_client_args(workflows_set_yml)
    _add_json_flag(workflows_set_yml)

    workflows_from_yml = workflows_subparsers.add_parser("create-from-yml", help="Create a workflow from workflow.yml")
    workflows_from_yml.add_argument("--workflow-name", required=True, help="Workflow name, e.g. boltzgen_v1.")
    workflows_from_yml.add_argument("--file", required=True, help="Path to workflow.yml or '-' for stdin.")
    workflows_from_yml.add_argument("--name", default="", help="Workflow display name.")
    workflows_from_yml.add_argument("--create-mode", default="", help="Optional create mode.")
    workflows_from_yml.add_argument("--execute", action="store_true", help="Execute immediately after creation.")
    _add_client_args(workflows_from_yml)
    _add_json_flag(workflows_from_yml)

    openmm_parser = workflows_subparsers.add_parser("openmm", help="OpenMM convenience commands")
    openmm_subparsers = openmm_parser.add_subparsers(dest="openmm_command", required=True)

    openmm_from_fold = openmm_subparsers.add_parser("from-fold-job", help="Submit OpenMM from a fold job")
    openmm_from_fold.add_argument("job_id", help="Fold job ID")
    openmm_from_fold.add_argument("--name", help="Workflow display name.")
    openmm_from_fold.add_argument("--simulation-name", help="workflow_input.name")
    openmm_from_fold.add_argument("--job-run-id", help="Source job run ID.")
    openmm_from_fold.add_argument("--sequence-id", help="Source sequence ID.")
    openmm_from_fold.add_argument("--preset", default="single_af_go", help="OpenMM preset.")
    openmm_from_fold.add_argument("--force-field", default="calvados3", help="workflow_input.residue_profile")
    openmm_from_fold.add_argument("--temperature", type=float, default=293.15, help="Temperature in K.")
    openmm_from_fold.add_argument("--ionic", type=float, default=0.15, help="Ionic strength.")
    openmm_from_fold.add_argument("--ph", type=float, default=7.5, help="pH.")
    openmm_from_fold.add_argument("--step-size-ns", type=float, default=0.01, help="Step size in ns.")
    openmm_from_fold.add_argument("--sim-length-ns", type=float, default=0.2, help="Simulation length in ns.")
    openmm_from_fold.add_argument("--box-length", type=float, default=20.0, help="Box length.")
    openmm_from_fold.add_argument("--public", action="store_true", help="Make the workflow public.")
    _add_client_args(openmm_from_fold)
    _add_json_flag(openmm_from_fold)

    openmm_manual = openmm_subparsers.add_parser("from-manual-files", help="Submit OpenMM from local PDB + PAE files")
    openmm_manual.add_argument("--pdb", required=True, help="Structure PDB/CIF path.")
    openmm_manual.add_argument("--pae", required=True, help="PAE JSON path.")
    openmm_manual.add_argument("--name", help="Workflow display name.")
    openmm_manual.add_argument("--simulation-name", help="workflow_input.name")
    openmm_manual.add_argument("--force-field", default="calvados3", help="workflow_input.residue_profile")
    openmm_manual.add_argument("--temperature", type=float, default=293.15, help="Temperature in K.")
    openmm_manual.add_argument("--ionic", type=float, default=0.15, help="Ionic strength.")
    openmm_manual.add_argument("--ph", type=float, default=7.5, help="pH.")
    openmm_manual.add_argument("--step-size-ns", type=float, default=0.01, help="Step size in ns.")
    openmm_manual.add_argument("--sim-length-ns", type=float, default=0.2, help="Simulation length in ns.")
    openmm_manual.add_argument("--box-length", type=float, default=20.0, help="Box length.")
    openmm_manual.add_argument("--public", action="store_true", help="Make the workflow public.")
    _add_client_args(openmm_manual)
    _add_json_flag(openmm_manual)

    openmm_from_workflow = openmm_subparsers.add_parser("from-workflow", help="Submit OpenMM from an existing workflow")
    openmm_from_workflow.add_argument("workflow_id", help="Source workflow ID")
    openmm_from_workflow.add_argument("--name", help="Workflow display name.")
    openmm_from_workflow.add_argument("--simulation-name", help="workflow_input.name")
    openmm_from_workflow.add_argument("--public", action="store_true", help="Make the new workflow public.")
    openmm_from_workflow.add_argument("--private", action="store_true", help="Make the new workflow private.")
    openmm_from_workflow.add_argument("--input-json", help="Optional JSON or YAML object merged into workflow_input.")
    _add_client_args(openmm_from_workflow)
    _add_json_flag(openmm_from_workflow)

    openmm_extract = openmm_subparsers.add_parser("extract-frame", help="Extract an OpenMM frame")
    openmm_extract.add_argument("workflow_id", help="Workflow ID")
    openmm_extract.add_argument("--time-ns", type=float, required=True, help="Time in ns.")
    openmm_extract.add_argument("--selection", default="protein or resname LIG", help="MDAnalysis selection.")
    openmm_extract.add_argument("--output-filename", default="extracted_frame.pdb", help="Output file name.")
    openmm_extract.add_argument("--dt-in-ps", type=float, default=0.0, help="Timestep override in ps.")
    _add_client_args(openmm_extract)
    _add_json_flag(openmm_extract)

    openmmdl_parser = workflows_subparsers.add_parser("openmmdl", help="OpenMMDL convenience commands")
    openmmdl_subparsers = openmmdl_parser.add_subparsers(dest="openmmdl_command", required=True)

    openmmdl_prepare = openmmdl_subparsers.add_parser("prepare-script", help="Prepare an OpenMMDL script")
    openmmdl_prepare.add_argument("--input-json", required=True, help="JSON or YAML object file for workflow_input.")
    _add_client_args(openmmdl_prepare)
    _add_json_flag(openmmdl_prepare)

    openmmdl_local = openmmdl_subparsers.add_parser("from-local-files", help="Submit OpenMMDL from local files")
    openmmdl_local.add_argument("--topology", required=True, help="Path to topology file.")
    openmmdl_local.add_argument("--ligand", action="append", default=[], help="Path to ligand file (repeatable).")
    openmmdl_local.add_argument("--name", help="Workflow display name.")
    openmmdl_local.add_argument("--simulation-name", help="workflow_input.name")
    openmmdl_local.add_argument("--run-analysis", action=argparse.BooleanOptionalAction, default=None, help="Set run_analysis.")
    openmmdl_local.add_argument("--sim-length-ns", type=float, default=None, help="workflow_input.sim_length_ns")
    openmmdl_local.add_argument("--step-time-ps", type=float, default=None, help="workflow_input.step_time_ps")
    openmmdl_local.add_argument("--analysis-cpus", type=int, default=None, help="workflow_input.analysis_cpus")
    openmmdl_local.add_argument("--failure-retries", type=int, default=None, help="workflow_input.failure_retries")
    openmmdl_local.add_argument("--ligand-selection", default=None, help="workflow_input.ligand_selection")
    openmmdl_local.add_argument("--input-json", help="Optional JSON or YAML object merged into workflow_input.")
    openmmdl_local.add_argument("--skip-prepare", action="store_true", help="Skip /prepare-script.")
    openmmdl_local.add_argument("--draft-script", action="store_true", help="Create in DRAFT mode.")
    openmmdl_local.add_argument("--public", action="store_true", help="Make the workflow public.")
    _add_client_args(openmmdl_local)
    _add_json_flag(openmmdl_local)

    openmmdl_from_workflow = openmmdl_subparsers.add_parser("from-workflow", help="Submit OpenMMDL from an existing workflow")
    openmmdl_from_workflow.add_argument("workflow_id", help="Source workflow ID")
    openmmdl_from_workflow.add_argument("--name", help="Workflow display name.")
    openmmdl_from_workflow.add_argument("--simulation-name", help="workflow_input.name")
    openmmdl_from_workflow.add_argument("--input-json", help="Optional JSON or YAML object merged into workflow_input.")
    openmmdl_from_workflow.add_argument("--prepare", action="store_true", help="Run prepare-script before submit.")
    _add_client_args(openmmdl_from_workflow)
    _add_json_flag(openmmdl_from_workflow)

    openmmdl_execute = openmmdl_subparsers.add_parser("execute-draft", help="Execute a DRAFT OpenMMDL workflow")
    openmmdl_execute.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(openmmdl_execute)
    _add_json_flag(openmmdl_execute)

    openmmdl_extract = openmmdl_subparsers.add_parser("extract-frame", help="Extract an OpenMMDL frame")
    openmmdl_extract.add_argument("workflow_id", help="Workflow ID")
    openmmdl_extract.add_argument("--time-ns", type=float, required=True, help="Time in ns.")
    openmmdl_extract.add_argument("--selection", default="protein or resname LIG", help="MDAnalysis selection.")
    openmmdl_extract.add_argument("--output-filename", default="extracted_frame.pdb", help="Output file name.")
    openmmdl_extract.add_argument("--dt-in-ps", type=float, default=0.0, help="Timestep override in ps.")
    _add_client_args(openmmdl_extract)
    _add_json_flag(openmmdl_extract)

    evolla_parser = workflows_subparsers.add_parser("evolla", help="Evolla convenience commands")
    evolla_subparsers = evolla_parser.add_subparsers(dest="evolla_command", required=True)

    evolla_from_fold = evolla_subparsers.add_parser("from-fold-job", help="Create evolla_v1 from a completed fold job")
    evolla_from_fold.add_argument("job_id", help="Fold job ID")
    evolla_from_fold.add_argument("--question", required=True, help="Natural-language question about the structure.")
    evolla_from_fold.add_argument("--name", help="Workflow display name.")
    evolla_from_fold.add_argument("--job-run-id", help="Source job run ID (default: latest from job results).")
    evolla_from_fold.add_argument("--sequence-id", help="Source sequence ID (default: first protein sequence).")
    evolla_from_fold.add_argument(
        "--source-user-id",
        help="Artifact owner id for Evolla resolution (or set FASTFOLD_EVOLLA_SOURCE_USER_ID).",
    )
    evolla_from_fold.add_argument("--public", action="store_true", help="Make the workflow public.")
    _add_client_args(evolla_from_fold)
    _add_json_flag(evolla_from_fold)

    evolla_from_local = evolla_subparsers.add_parser(
        "from-file",
        help="Upload a structure file and create evolla_v1 (library upload + question)",
    )
    evolla_from_local.add_argument("file_path", help="Local structure path (.cif, .mmcif, .pdb, …).")
    evolla_from_local.add_argument("--question", required=True, help="Natural-language question about the structure.")
    evolla_from_local.add_argument("--name", help="Workflow display name.")
    evolla_from_local.add_argument("--file-type", default="protein", help="Library file type (default protein).")
    evolla_from_local.add_argument("--item-name", help="Library item name (default derived from file name).")
    evolla_from_local.add_argument("--parent-id", help="Optional parent folder library id.")
    evolla_from_local.add_argument("--model-type", default="evolla-10b", help="workflow_input.modelType.")
    evolla_from_local.add_argument("--public", action="store_true", help="Make the workflow public.")
    _add_client_args(evolla_from_local)
    _add_json_flag(evolla_from_local)

    evolla_from_input = evolla_subparsers.add_parser(
        "from-input",
        help="Create evolla_v1 from a workflow_input JSON/YAML file (see docs for targetSource shapes)",
    )
    evolla_from_input.add_argument("--file", required=True, help="Path to workflow_input or '-' for stdin.")
    evolla_from_input.add_argument("--format", choices=["auto", "json", "yaml"], default="auto")
    evolla_from_input.add_argument("--name", default="", help="Workflow display name.")
    evolla_from_input.add_argument("--create-mode", default="", help="Optional create mode.")
    _add_client_args(evolla_from_input)
    _add_json_flag(evolla_from_input)

    boltzgen_parser = workflows_subparsers.add_parser("boltzgen", help="BoltzGen convenience commands")
    boltzgen_subparsers = boltzgen_parser.add_subparsers(dest="boltzgen_command", required=True)

    boltzgen_draft = boltzgen_subparsers.add_parser("create-draft", help="Create a BoltzGen draft workflow")
    boltzgen_draft.add_argument("--name", default="", help="Workflow display name.")
    boltzgen_draft.add_argument("--create-mode", default="api", help="Create mode.")
    _add_client_args(boltzgen_draft)
    _add_json_flag(boltzgen_draft)

    boltzgen_from_yml = boltzgen_subparsers.add_parser("create-from-yml", help="Create a BoltzGen workflow from workflow.yml")
    boltzgen_from_yml.add_argument("--file", required=True, help="Path to workflow.yml or '-' for stdin.")
    boltzgen_from_yml.add_argument("--name", default="", help="Workflow display name.")
    boltzgen_from_yml.add_argument("--create-mode", default="api", help="Create mode.")
    boltzgen_from_yml.add_argument("--execute", action="store_true", help="Execute immediately.")
    _add_client_args(boltzgen_from_yml)
    _add_json_flag(boltzgen_from_yml)

    boltzgen_get_yml = boltzgen_subparsers.add_parser("get-yml", help="Fetch BoltzGen workflow.yml")
    boltzgen_get_yml.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(boltzgen_get_yml)

    boltzgen_set_yml = boltzgen_subparsers.add_parser("set-yml", help="Replace BoltzGen workflow.yml")
    boltzgen_set_yml.add_argument("workflow_id", help="Workflow ID")
    boltzgen_set_yml.add_argument("--file", required=True, help="Path to workflow.yml or '-' for stdin.")
    _add_client_args(boltzgen_set_yml)
    _add_json_flag(boltzgen_set_yml)

    boltzgen_execute = boltzgen_subparsers.add_parser("execute", help="Execute a BoltzGen workflow")
    boltzgen_execute.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(boltzgen_execute)
    _add_json_flag(boltzgen_execute)

    boltzgen_logs = boltzgen_subparsers.add_parser("logs", help="Fetch BoltzGen workflow logs")
    boltzgen_logs.add_argument("workflow_id", help="Workflow ID")
    _add_client_args(boltzgen_logs)
    _add_json_flag(boltzgen_logs)

    boltzgen_examples = boltzgen_subparsers.add_parser("example-files", help="List packaged example files")
    boltzgen_examples.add_argument("--list", action="store_true", help="List packaged examples.")
    _add_client_args(boltzgen_examples)
    _add_json_flag(boltzgen_examples)

    boltzgen_build = boltzgen_subparsers.add_parser("build-spec", help="Build workflow.yml from a template plus replacements")
    boltzgen_build.add_argument("--template-file", required=True, help="Path to a template workflow.yml.")
    boltzgen_build.add_argument("--replacements-file", required=False, help="JSON or YAML mapping file.")
    boltzgen_build.add_argument("--output", required=True, help="Output file path.")
    _add_client_args(boltzgen_build)

    reports_parser = subparsers.add_parser("reports", help="Reporting helpers")
    reports_subparsers = reports_parser.add_subparsers(dest="reports_command", required=True)

    reports_slack = reports_subparsers.add_parser("slack", help="Send a markdown report to Slack")
    reports_slack.add_argument("--markdown", help="Inline markdown content.")
    reports_slack.add_argument("--markdown-file", help="Markdown file path or '-' for stdin.")
    reports_slack.add_argument("--report-name", help="Optional report name.")
    reports_slack.add_argument("--no-save-to-library", action="store_true", help="Do not save the report to the library.")
    _add_client_args(reports_slack)
    _add_json_flag(reports_slack)

    return parser


def _parse_mapping(value: Optional[str], label: str) -> Optional[Dict[str, Any]]:
    if not value:
        return None
    try:
        data = json.loads(value)
    except Exception:
        try:
            data = yaml.safe_load(value)
        except Exception as ex:
            raise ValueError(f"Invalid JSON/YAML for {label}: {ex}") from ex
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be an object")
    return data


def _detect_format(path: Optional[str], explicit_format: str) -> str:
    if explicit_format != "auto":
        return explicit_format
    if not path or path == "-":
        return "json"
    suffix = Path(path).suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    return "json"


def _load_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).expanduser().read_text(encoding="utf-8")


def _load_mapping_from_args(
    payload: Optional[str],
    payload_file: Optional[str],
    *,
    format: str = "auto",
    label: str = "payload",
) -> Dict[str, Any]:
    if payload:
        data = _parse_mapping(payload, label)
        if data is None:
            raise ValueError(f"{label} must not be empty.")
        return data
    if payload_file:
        text = _load_text(payload_file)
        resolved_format = _detect_format(payload_file, format)
        data = yaml.safe_load(text) if resolved_format == "yaml" else json.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"{label} file must contain an object.")
        return data
    raise ValueError(f"Provide --payload or --payload-file for {label}.")


def _build_client(args: argparse.Namespace) -> Client:
    api_key = args.api_key or os.getenv("FASTFOLD_API_KEY")
    if not api_key:
        raise AuthenticationError("FASTFOLD_API_KEY is not set and --api-key was not provided.")
    return Client(api_key=api_key, base_url=args.base_url, timeout=getattr(args, "timeout", 30.0))


def _workflow_from_payload(client: Client, payload: Dict[str, Any]):
    workflow_name = str(payload.get("workflow_name") or payload.get("workflowName") or "").strip()
    if not workflow_name:
        raise ValueError("Workflow payload must include workflow_name.")
    workflow_input = payload.get("workflow_input") or payload.get("workflowInput") or {}
    if workflow_input is None:
        workflow_input = {}
    if not isinstance(workflow_input, dict):
        raise ValueError("workflow_input must be an object.")
    return client.workflows.create(
        workflow_name,
        workflow_input,
        name=str(payload.get("name") or ""),
        create_mode=str(payload.get("create_mode") or payload.get("createMode") or ""),
    )


def handle_fold(args: argparse.Namespace) -> int:
    try:
        client = _build_client(args)
        job = client.fold.create(
            sequence=args.sequence,
            model=args.model,
            name=args.name,
            from_id=args.from_id,
            params=_parse_mapping(args.params, "params"),
            constraints=_parse_mapping(args.constraints, "constraints"),
        )
        _emit_json(job.raw) if args.json else print(job.id)
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


def handle_jobs(args: argparse.Namespace) -> int:
    try:
        client = _build_client(args)
        if args.jobs_command == "create":
            payload = _load_mapping_from_args(args.payload, args.payload_file, format=args.format, label="job payload")
            job = client.jobs.create(payload, from_id=args.from_id)
            _emit_json(job.raw) if args.json else print(job.id)
        elif args.jobs_command == "from-yaml":
            yaml_text = _load_text(args.file)
            job = client.jobs.create_from_yaml(
                yaml_text,
                model_name=args.model,
                name=args.name,
                from_id=args.from_id,
                is_public=args.public,
                run_now=not args.draft,
                chat_id=args.chat_id,
            )
            _emit_json(job.raw) if args.json else print(job.id)
        elif args.jobs_command == "results":
            results = client.jobs.get_results(args.job_id)
            _emit_json(results.raw) if args.json else print(results.job.status)
        elif args.jobs_command == "wait":
            results = client.jobs.wait_for_completion(
                args.job_id,
                poll_interval=args.poll_interval,
                timeout=args.wait_timeout,
                log=not args.no_log,
            )
            _emit_json(results.raw) if args.json else print(results.job.status)
        elif args.jobs_command == "set-public":
            if args.is_public is None:
                raise ValueError("Provide either --public or --private.")
            response = client.jobs.set_public(args.job_id, args.is_public)
            payload = {"jobId": response.job_id, "isPublic": response.is_public}
            _emit_json(payload) if args.json else print(response.job_id)
        elif args.jobs_command == "render-yaml":
            payload = _load_mapping_from_args(args.payload, args.payload_file, format=args.format, label="job payload")
            print(client.jobs.render_yaml(payload))
        elif args.jobs_command == "render-json":
            payload = _load_mapping_from_args(args.payload, args.payload_file, format=args.format, label="job payload")
            _emit_json(client.jobs.render_json(payload))
        else:
            raise ValueError(f"Unsupported jobs command: {args.jobs_command}")
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


def handle_library(args: argparse.Namespace) -> int:
    try:
        client = _build_client(args)
        if args.library_command == "create":
            metadata = _parse_mapping(args.metadata, "metadata")
            item = client.library.create_item(
                name=args.name,
                type=args.type,
                parent_id=args.parent_id,
                file_type=args.file_type,
                origin=args.origin,
                metadata=metadata,
            )
            _emit_json(item.raw) if args.json else print(item.id)
        elif args.library_command == "get":
            item = client.library.get_item(args.item_id)
            _emit_json(item.raw) if args.json else print(item.id)
        elif args.library_command == "upload":
            item = client.library.upload_files(args.item_id, *args.files)
            _emit_json(item.raw) if args.json else print(item.id)
        else:
            raise ValueError(f"Unsupported library command: {args.library_command}")
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


def handle_openmm(args: argparse.Namespace, client: Client) -> int:
    if args.openmm_command == "from-fold-job":
        workflow = client.openmm.submit_from_fold_job(
            args.job_id,
            name=args.name,
            simulation_name=args.simulation_name,
            source_job_run_id=args.job_run_id,
            source_sequence_id=args.sequence_id,
            preset=args.preset,
            residue_profile=args.force_field,
            temp=args.temperature,
            ionic=args.ionic,
            ph=args.ph,
            step_size_ns=args.step_size_ns,
            sim_length_ns=args.sim_length_ns,
            box_length=args.box_length,
            is_public=args.public,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.openmm_command == "from-manual-files":
        workflow = client.openmm.submit_from_manual_files(
            pdb_path=args.pdb,
            pae_path=args.pae,
            name=args.name,
            simulation_name=args.simulation_name,
            residue_profile=args.force_field,
            temp=args.temperature,
            ionic=args.ionic,
            ph=args.ph,
            step_size_ns=args.step_size_ns,
            sim_length_ns=args.sim_length_ns,
            box_length=args.box_length,
            is_public=args.public,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.openmm_command == "from-workflow":
        overrides = (
            _load_mapping_from_args(None, args.input_json, format="auto", label="workflow_input overrides")
            if args.input_json
            else {}
        )
        is_public = True if args.public else False if args.private else None
        workflow = client.openmm.submit_from_workflow(
            args.workflow_id,
            name=args.name,
            simulation_name=args.simulation_name,
            is_public=is_public,
            **overrides,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.openmm_command == "extract-frame":
        result = client.openmm.extract_frame(
            args.workflow_id,
            time_ns=args.time_ns,
            selection=args.selection,
            output_filename=args.output_filename,
            dt_in_ps=args.dt_in_ps,
        )
        _emit_json(result.raw) if args.json else print(result.pdb_url or "")
    else:
        raise ValueError(f"Unsupported OpenMM command: {args.openmm_command}")
    return 0


def handle_openmmdl(args: argparse.Namespace, client: Client) -> int:
    if args.openmmdl_command == "prepare-script":
        workflow_input = _load_mapping_from_args(None, args.input_json, format="auto", label="workflow_input")
        prepared = client.openmmdl.prepare_script(workflow_input)
        _emit_json(prepared.raw) if args.json else _emit_json(prepared.workflow_input or {})
    elif args.openmmdl_command == "from-local-files":
        input_json = (
            _load_mapping_from_args(None, args.input_json, format="auto", label="workflow_input overrides")
            if args.input_json
            else None
        )
        workflow = client.openmmdl.submit_from_local_files(
            topology_path=args.topology,
            ligand_paths=args.ligand,
            name=args.name,
            simulation_name=args.simulation_name,
            run_analysis=args.run_analysis,
            sim_length_ns=args.sim_length_ns,
            step_time_ps=args.step_time_ps,
            analysis_cpus=args.analysis_cpus,
            failure_retries=args.failure_retries,
            ligand_selection=args.ligand_selection,
            input_json=input_json,
            skip_prepare=args.skip_prepare,
            draft_script=args.draft_script,
            is_public=args.public,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.openmmdl_command == "from-workflow":
        input_json = (
            _load_mapping_from_args(None, args.input_json, format="auto", label="workflow_input overrides")
            if args.input_json
            else None
        )
        workflow = client.openmmdl.submit_from_workflow(
            args.workflow_id,
            name=args.name,
            simulation_name=args.simulation_name,
            input_json=input_json,
            prepare=args.prepare,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.openmmdl_command == "execute-draft":
        data = client.openmmdl.execute_draft(args.workflow_id)
        _emit_json(data) if args.json else print(args.workflow_id)
    elif args.openmmdl_command == "extract-frame":
        result = client.openmmdl.extract_frame(
            args.workflow_id,
            time_ns=args.time_ns,
            selection=args.selection,
            output_filename=args.output_filename,
            dt_in_ps=args.dt_in_ps,
        )
        _emit_json(result.raw) if args.json else print(result.pdb_url or "")
    else:
        raise ValueError(f"Unsupported OpenMMDL command: {args.openmmdl_command}")
    return 0


def _package_example_files() -> Dict[str, str]:
    root = resources.files("fastfold").joinpath("examples")
    return {
        "fold_job_json": str(root.joinpath("fold", "job_payload.json")),
        "fold_boltz2_yaml": str(root.joinpath("fold", "boltz2_affinity_input.yaml")),
        "openmm_from_fold_job_json": str(root.joinpath("openmm", "from_fold_job.json")),
        "openmm_from_manual_files_json": str(root.joinpath("openmm", "from_manual_files.json")),
        "openmmdl_input_json": str(root.joinpath("openmmdl", "workflow_input.json")),
        "openmmdl_from_local_files_json": str(root.joinpath("openmmdl", "from_local_files.json")),
        "openmmdl_quick_water_box_input_json": str(root.joinpath("openmmdl", "quick_water_box.workflow_input.json")),
        "openmmdl_quick_membrane_input_json": str(root.joinpath("openmmdl", "quick_membrane.workflow_input.json")),
        "evolla_from_fold_job_template_json": str(root.joinpath("evolla", "from_fold_job.template.json")),
        "boltzgen_workflow_yml": str(root.joinpath("boltzgen", "minimal.workflow.yml")),
        "boltzgen_design_spec_yaml": str(root.joinpath("boltzgen", "design_spec.example.yaml")),
        "boltzgen_replacements_json": str(root.joinpath("boltzgen", "replacements.example.json")),
        "slack_report_md": str(root.joinpath("reports", "sample_report.md")),
    }


def handle_evolla(args: argparse.Namespace, client: Client) -> int:
    if args.evolla_command == "from-fold-job":
        workflow = client.evolla.submit_from_fold_job(
            args.job_id,
            args.question,
            name=args.name,
            source_job_run_id=args.job_run_id,
            source_sequence_id=args.sequence_id,
            source_user_id=args.source_user_id,
            is_public=args.public,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.evolla_command == "from-file":
        workflow = client.evolla.submit_from_local_file(
            args.file_path,
            args.question,
            name=args.name,
            file_type=args.file_type,
            item_name=args.item_name,
            parent_id=args.parent_id,
            model_type=args.model_type,
            is_public=args.public,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.evolla_command == "from-input":
        workflow = client.evolla.submit_from_input_file(
            args.file,
            name=args.name,
            create_mode=args.create_mode,
            format=args.format,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    else:
        raise ValueError(f"Unsupported Evolla command: {args.evolla_command}")
    return 0


def handle_boltzgen(args: argparse.Namespace, client: Client) -> int:
    if args.boltzgen_command == "create-draft":
        workflow = client.boltzgen.create_draft(name=args.name, create_mode=args.create_mode)
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.boltzgen_command == "create-from-yml":
        workflow_yml = _load_text(args.file)
        workflow = client.boltzgen.create_from_workflow_yml(
            workflow_yml,
            name=args.name,
            create_mode=args.create_mode,
            execute=args.execute,
        )
        _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
    elif args.boltzgen_command == "get-yml":
        print(client.boltzgen.get_workflow_yml(args.workflow_id))
    elif args.boltzgen_command == "set-yml":
        workflow_yml = _load_text(args.file)
        data = client.boltzgen.upsert_workflow_yml(args.workflow_id, workflow_yml)
        _emit_json(data) if args.json else print(args.workflow_id)
    elif args.boltzgen_command == "execute":
        data = client.boltzgen.execute(args.workflow_id)
        _emit_json(data) if args.json else print(args.workflow_id)
    elif args.boltzgen_command == "logs":
        data = client.boltzgen.get_logs(args.workflow_id)
        _emit_json(data)
    elif args.boltzgen_command == "example-files":
        _emit_json(_package_example_files())
    elif args.boltzgen_command == "build-spec":
        template_text = _load_text(args.template_file)
        replacements = (
            _load_mapping_from_args(None, args.replacements_file, format="auto", label="replacements")
            if args.replacements_file
            else {}
        )
        for key, value in replacements.items():
            template_text = template_text.replace("{{" + str(key) + "}}", str(value))
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template_text, encoding="utf-8")
        print(str(output_path))
    else:
        raise ValueError(f"Unsupported BoltzGen command: {args.boltzgen_command}")
    return 0


def handle_workflows(args: argparse.Namespace) -> int:
    try:
        client = _build_client(args)
        command = args.workflows_command
        if command == "create":
            payload = _load_mapping_from_args(args.payload, args.payload_file, format=args.format, label="workflow payload")
            workflow = _workflow_from_payload(client, payload)
            _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
        elif command == "get":
            workflow = client.workflows.get_public(args.workflow_id) if args.public else client.workflows.get(args.workflow_id)
            _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
        elif command == "status":
            status = client.workflows.status(args.workflow_id)
            _emit_json(status.raw) if args.json else print(status.status)
        elif command == "task-results":
            results = client.workflows.task_results(args.workflow_id)
            _emit_json(results.raw) if args.json else print(args.workflow_id)
        elif command == "execute":
            data = client.workflows.execute(args.workflow_id)
            _emit_json(data) if args.json else print(args.workflow_id)
        elif command == "set-public":
            if args.is_public is None:
                raise ValueError("Provide either --public or --private.")
            response = client.workflows.set_public(args.workflow_id, args.is_public)
            _emit_json(response.raw) if args.json else print(response.workflow_id)
        elif command == "create-graph":
            workflow = client.workflows.create_graph(args.workflow_name, name=args.name, create_mode=args.create_mode)
            _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
        elif command == "get-yml":
            print(client.workflows.get_workflow_yml(args.workflow_id))
        elif command == "set-yml":
            workflow_yml = _load_text(args.file)
            data = client.workflows.set_workflow_yml(args.workflow_id, workflow_yml)
            _emit_json(data) if args.json else print(args.workflow_id)
        elif command == "create-from-yml":
            workflow_yml = _load_text(args.file)
            workflow = client.workflows.create_from_workflow_yml(
                workflow_name=args.workflow_name,
                workflow_yml=workflow_yml,
                name=args.name,
                create_mode=args.create_mode,
                execute=args.execute,
            )
            _emit_json(workflow.raw) if args.json else print(workflow.workflow_id)
        elif command == "openmm":
            return handle_openmm(args, client)
        elif command == "openmmdl":
            return handle_openmmdl(args, client)
        elif command == "evolla":
            return handle_evolla(args, client)
        elif command == "boltzgen":
            return handle_boltzgen(args, client)
        else:
            raise ValueError(f"Unsupported workflows command: {command}")
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


def handle_reports(args: argparse.Namespace) -> int:
    try:
        client = _build_client(args)
        if args.reports_command != "slack":
            raise ValueError(f"Unsupported reports command: {args.reports_command}")
        markdown = args.markdown or (_load_text(args.markdown_file) if args.markdown_file else "")
        if not markdown:
            raise ValueError("Provide --markdown or --markdown-file.")
        result = client.reports.send_agent_cli_report(
            markdown,
            report_name=args.report_name,
            save_to_library=not args.no_save_to_library,
        )
        _emit_json(result.raw) if args.json else print(result.library_item_id or "")
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


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "fold":
        code = handle_fold(args)
    elif args.command == "jobs":
        code = handle_jobs(args)
    elif args.command == "library":
        code = handle_library(args)
    elif args.command == "workflows":
        code = handle_workflows(args)
    elif args.command == "reports":
        code = handle_reports(args)
    else:
        parser.print_help()
        _positive_exit(1)
    _positive_exit(code)
