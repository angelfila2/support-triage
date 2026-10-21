"""Regression coverage for reorganized packages and module entry points."""

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from backend.config import BASE_DIR, REPO_ROOT


@pytest.mark.parametrize("module", [
    "backend.api",
    "backend.storage",
    "backend.agent.triage",
    "backend.agent.classifier",
    "backend.agent.responder",
    "backend.agent.router",
    "backend.agent.safety",
    "backend.agent.structured_output",
    "backend.rag.kb",
    "backend.rag.vector",
    "backend.rag.retriever",
    "backend.evaluation.run_batch",
    "backend.evaluation.evaluate",
])
def test_reorganized_modules_import_without_running_models(module):
    importlib.import_module(module)


def test_relative_paths_do_not_depend_on_working_directory(tmp_path):
    environment = os.environ.copy()
    environment.update(
        PYTHONPATH=str(REPO_ROOT),
        OUTPUT_DIR=str(tmp_path / "output"),
        DATA_DIR="data",
        SAMPLE_TICKETS_FILE="data/fixture.csv",
        KNOWLEDGE_BASE_DIR="knowledgebase",
    )
    code = (
        "import json; from backend import config; "
        "print(json.dumps([str(config.DATA_DIR), "
        "str(config.SAMPLE_TICKETS_FILE), str(config.KNOWLEDGE_BASE_DIR)]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=30, check=True,
    )
    assert json.loads(result.stdout) == [
        str(BASE_DIR / "data"),
        str(BASE_DIR / "data" / "fixture.csv"),
        str(BASE_DIR / "knowledgebase"),
    ]


@pytest.mark.parametrize(("module", "setting", "message"), [
    ("backend.evaluation.run_batch", "SAMPLE_TICKETS_FILE", "Sample tickets file not found"),
    ("backend.evaluation.evaluate", "TRIAGE_RESULTS_FILE", "Results file not found"),
])
def test_evaluation_commands_report_missing_input_instead_of_import_errors(
    tmp_path, module, setting, message
):
    environment = os.environ.copy()
    environment["OUTPUT_DIR"] = str(tmp_path / "output")
    environment[setting] = str(tmp_path / "missing.csv")
    result = subprocess.run(
        [sys.executable, "-m", module], cwd=REPO_ROOT, env=environment,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert message in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
