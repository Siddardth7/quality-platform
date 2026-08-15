"""
quality_core/project/io.py
Load / write boundary for a Quality Platform project directory (#276).

:class:`ProjectPaths` is the single source of truth for the on-disk file graph
(see `docs/PROJECT_FILE_CONTRACT.md`); every M3 arrow issue reads and writes
through it instead of hard-coding a filename. The rest is one generic pair —
:func:`load_artifact` / :func:`write_artifact` — over the models in
:mod:`quality_core.project.schema`, plus :func:`load_optional_artifact` for the
arrow-hasn't-run-yet case (no file is not an error; a *malformed* file is).

Every user-facing failure is a :class:`ProjectError`, a subclass of
:class:`~quality_core.io.IngestError` (itself a ``ValueError``) — same discipline
as the CSV/Excel ingest boundary, so a caller that already handles `IngestError`
needs no third exception type, and the message is safe to show as-is.

Paths are pure arithmetic: :func:`discover_project` never touches the filesystem,
so it works on a project that does not exist yet. Writers create their parent
directory on demand, which is what makes a fresh project materialise file by file
as each arrow runs.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import pydantic
import yaml

from quality_core.io.validate import IngestError, clean_pydantic_message
from quality_core.project.schema import SCHEMA_VERSION, ProjectMeta

_T = TypeVar("_T", bound=pydantic.BaseModel)

#: Relative layout of a project directory. Kept as module constants so a reader
#: (and a test) can see the whole graph in one place.
PROJECT_YAML = "project.yaml"
FMEA_JSON = ("fmea", "fmea.json")
CONTROL_PLAN_JSON = ("control-plan", "plan.json")
SPC_CONFIG_JSON = ("spc", "config.json")
#: Lives under `spc/` because it annotates the SPC monitoring selection — it is
#: not a second MSA file (M3-5, #280).
MSA_GATE_JSON = ("spc", "msa-gate.json")
SPC_RESULTS_DIR = ("spc", "results")
GAGE_RR_JSON = ("msa", "gage-rr.json")
FEEDBACK_JSON = ("feedback", "spc-to-fmea.json")


class ProjectError(IngestError):
    """A user-facing project-file failure with a message safe to show as-is."""


@dataclass(frozen=True)
class ProjectPaths:
    """The canonical paths inside one project directory."""

    root: Path
    project_yaml: Path
    fmea_json: Path
    control_plan_json: Path
    spc_config_json: Path
    msa_gate_json: Path
    spc_results_dir: Path
    gage_rr_json: Path
    feedback_json: Path


def discover_project(root: str | os.PathLike[str]) -> ProjectPaths:
    """Return the canonical file graph for the project rooted at ``root``.

    Pure path arithmetic — the directory need not exist yet, and nothing is read
    or created here. Use :func:`load_optional_artifact` to ask whether a given
    artifact has been produced.
    """
    base = Path(root)
    return ProjectPaths(
        root=base,
        project_yaml=base / PROJECT_YAML,
        fmea_json=base.joinpath(*FMEA_JSON),
        control_plan_json=base.joinpath(*CONTROL_PLAN_JSON),
        spc_config_json=base.joinpath(*SPC_CONFIG_JSON),
        msa_gate_json=base.joinpath(*MSA_GATE_JSON),
        spc_results_dir=base.joinpath(*SPC_RESULTS_DIR),
        gage_rr_json=base.joinpath(*GAGE_RR_JSON),
        feedback_json=base.joinpath(*FEEDBACK_JSON),
    )


def spc_result_path(paths: ProjectPaths, characteristic: str) -> Path:
    """Path of the SPC result file for ``characteristic`` — one file per characteristic.

    The name is the characteristic slugified (lowercase, runs of non-alphanumerics
    collapsed to ``-``), so a re-run of the same characteristic overwrites its own
    file rather than accumulating per-run files (git is the history, #276).
    """
    slug = re.sub(r"[^a-z0-9]+", "-", characteristic.lower()).strip("-")
    if not slug:
        raise ProjectError(
            f"Characteristic {characteristic!r} has no letters or digits, so it has no "
            "file name. Rename the characteristic."
        )
    return paths.spc_results_dir / f"{slug}.json"


def spc_result_paths(paths: ProjectPaths) -> list[Path]:
    """Every SPC result file present, sorted by name; empty when none have been written."""
    if not paths.spc_results_dir.is_dir():
        return []
    return sorted(paths.spc_results_dir.glob("*.json"))


# ===========================================================================
# Reading
# ===========================================================================


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectError(
            f"Could not read '{path}'. The file may be missing, unreadable, or a directory."
        ) from exc


def _validate(payload: object, model: type[_T], path: Path) -> _T:
    """Version-check a parsed mapping, then validate it into ``model``."""
    if not isinstance(payload, dict):
        raise ProjectError(f"'{path}' must hold a single object at the top level.")
    found = payload.get("schema_version")
    if found != SCHEMA_VERSION:
        raise ProjectError(
            f"'{path}' declares schema_version {found!r}, but this version of the "
            f"platform reads schema_version {SCHEMA_VERSION}. Re-generate the file "
            "with a matching tool version."
        )
    try:
        return model.model_validate(payload)
    except pydantic.ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first.get("loc", ()))
        field = f" at '{where}'" if where else ""
        message = clean_pydantic_message(first.get("msg", "invalid value"))
        raise ProjectError(f"'{path}' is not a valid {model.__name__}{field}: {message}.") from exc


def load_artifact(path: Path, model: type[_T]) -> _T:
    """Load one JSON artifact file and validate it against ``model``.

    Raises
    ------
    ProjectError
        On a missing/unreadable file, invalid JSON, an unrecognised
        ``schema_version``, or a field that fails validation — each with a
        message naming the file and the problem.
    """
    text = _read_text(path)
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise ProjectError(f"'{path}' is not valid JSON: {exc}.") from exc
    return _validate(payload, model, path)


def load_optional_artifact(path: Path, model: type[_T]) -> _T | None:
    """Same as :func:`load_artifact`, but return ``None`` when the file is absent.

    An arrow that has not run yet legitimately has no output file (e.g. no
    out-of-control signal means no ``feedback/spc-to-fmea.json``). A file that
    *does* exist and is malformed still raises :class:`ProjectError`.
    """
    if not path.exists():
        return None
    return load_artifact(path, model)


def load_project_meta(paths: ProjectPaths) -> ProjectMeta:
    """Load and validate ``project.yaml``."""
    text = _read_text(paths.project_yaml)
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ProjectError(f"'{paths.project_yaml}' is not valid YAML: {exc}.") from exc
    return _validate(payload, ProjectMeta, paths.project_yaml)


# ===========================================================================
# Writing — a re-run overwrites its own file in place (git is the history)
# ===========================================================================


def write_artifact(path: Path, artifact: pydantic.BaseModel) -> None:
    """Write one artifact as pretty-printed JSON, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact.model_dump(mode="json"), indent=2, ensure_ascii=False)
    path.write_text(payload + "\n", encoding="utf-8")


def write_project_meta(paths: ProjectPaths, meta: ProjectMeta) -> None:
    """Write ``project.yaml``, keeping field order so the file stays hand-readable."""
    paths.project_yaml.parent.mkdir(parents=True, exist_ok=True)
    paths.project_yaml.write_text(
        yaml.safe_dump(meta.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
