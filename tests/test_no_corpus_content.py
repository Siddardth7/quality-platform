"""Repo-wide guard: no corpus artefact and no licensed corpus text is committed (M4-5, #286).

This lives at repo root rather than under ``apps/quality_database/tests/`` for the same
reason ``tests/test_cross_app_import_boundary.py`` does: it is an assertion about the
whole repository — every tracked file, not one app's package.

Two independent guards:

1. **Artefact guard** (always runs, needs no corpus) — ``apps/quality_database/.corpus_out/``
   is gitignored *and* nothing under it is tracked right now. This is the machine-checkable
   form of the M4-1 policy ("the corpus is private; only our derivations are public").
2. **Text guard** (gated on the corpus being present locally — CI never holds it, so the
   skip is the permanent, expected CI outcome) — no tracked text file contains a signature
   substring of any non-``serve`` corpus record, i.e. of anything the ledger classifies as
   ``quote`` / ``paraphrase-and-point`` / ``never-ship``. ``serve`` records are this
   project's own derivations, freely reproducible by definition, so they are out of scope.

Both guards carry a scratch-repo **negative control** in the test body: a throwaway
``git init`` repo where the offence is planted deliberately, proving the mechanism fails
when it should instead of merely reporting "found nothing". No control touches the real
repo's git index.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

_CORPUS_OUT = "apps/quality_database/.corpus_out"

# Extensions worth scanning; anything else (.npy, images, fonts) cannot carry readable
# prose and would only add decode noise — the same "only parse what you expect to parse"
# discipline as _referenced_modules() in test_cross_app_import_boundary.py.
_TEXT_SUFFIXES = frozenset({".py", ".md", ".tsv", ".json", ".toml", ".yml", ".yaml", ".txt"})

# Deliberately-public metadata, verified (spec #286, "Context & research") to hold
# locators or separately-reviewed short quotes, never corpus.json's segmented full text:
#   - the ledger itself is Tier 3 bibliographic metadata (docs/CORPUS_LEDGER.md, "What is public");
#   - the M4-4 gold set stores expected_chunk_id / clause / page, with every
#     `expected_excerpt` null (all 13 items checked by direct inspection);
#   - apps/*/docs/CITATIONS.tsv is the pre-existing MSA-precedent quote manifest, governed
#     by its own review + apps/msa/tests/test_citations.py.
# Excluding these is a recorded decision, not a blind skip.
_ALLOWLIST = frozenset(
    {
        "docs/CORPUS_LEDGER.md",
        "docs/CORPUS_LEDGER.tsv",
        "apps/quality_database/docs/eval/gold_set.json",
    }
)
_ALLOWLIST_GLOB = "apps/*/docs/CITATIONS.tsv"

# A signature is the first _SIGNATURE_CHARS of a record's whitespace-normalized text, and
# records shorter than _MIN_RECORD_CHARS are skipped: a very short record is typically a
# bare clause heading ("Severity", "4.2 Scope") that would match innocuous prose anywhere
# in the repo. 80 characters of contiguous handbook text is not a coincidence.
_SIGNATURE_CHARS = 80
_MIN_RECORD_CHARS = 40

_SERVE = "serve"


def _git(args: list[str], cwd: Path) -> str:
    """Run a git plumbing command and return stdout, failing loudly on a git error."""
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"git {' '.join(args)} failed in {cwd}: {result.stderr}"
    return result.stdout


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _is_allowlisted(relpath: str) -> bool:
    return relpath in _ALLOWLIST or Path(relpath).match(_ALLOWLIST_GLOB)


def _signatures() -> set[str]:
    """Signature substrings of every non-``serve`` record in the local corpus."""
    from quality_database_app.pipeline import DEFAULT_OUT_PATH, load_records

    signatures: set[str] = set()
    for record in load_records(DEFAULT_OUT_PATH).records:
        if record.serving_flag == _SERVE:
            continue
        normalized = _normalize(record.text)
        if len(normalized) >= _MIN_RECORD_CHARS:
            signatures.add(normalized[:_SIGNATURE_CHARS])
    return signatures


def _scan(repo_root: Path, signatures: set[str]) -> set[tuple[str, str]]:
    """Every ``(tracked file, signature it leaks)`` pair in ``repo_root``."""
    found: set[tuple[str, str]] = set()
    for relpath in _git(["ls-files"], cwd=repo_root).splitlines():
        if _is_allowlisted(relpath):
            continue
        path = repo_root / relpath
        if path.suffix not in _TEXT_SUFFIXES or not path.is_file():
            continue
        haystack = _normalize(path.read_text(encoding="utf-8", errors="ignore"))
        found.update((relpath, sig) for sig in signatures if sig in haystack)
    return found


def _scratch_repo(directory: str) -> Path:
    """A throwaway git repo, so no control ever touches the real repo's index."""
    root = Path(directory)
    _git(["init", "-q"], cwd=root)
    return root


def test_corpus_artifacts_are_gitignored_and_untracked() -> None:
    """``.corpus_out/`` is ignored, and nothing under it is tracked in this repo.

    The negative control below is what makes the ``ls-files`` half non-vacuous: an empty
    result proves nothing unless the same command is shown to be non-empty when a corpus
    file really has been force-added past the gitignore.
    """
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", f"{_CORPUS_OUT}/corpus.json"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ignored.returncode == 0, (
        f"{_CORPUS_OUT}/ is not gitignored — corpus-derived text would be committable. "
        f"See .gitignore and docs/CORPUS_LEDGER.md."
    )

    tracked = _git(["ls-files", "--", _CORPUS_OUT], cwd=_REPO_ROOT).split()
    assert not tracked, f"corpus artefacts are tracked in git: {tracked}"

    # Negative control: force-add a synthetic corpus file in a scratch repo carrying this
    # repo's real .gitignore, and assert the same ls-files check catches it.
    with tempfile.TemporaryDirectory() as directory:
        scratch = _scratch_repo(directory)
        (scratch / ".gitignore").write_text(
            (_REPO_ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8"
        )
        planted = scratch / _CORPUS_OUT / "corpus.json"
        planted.parent.mkdir(parents=True)
        planted.write_text('{"records": []}\n', encoding="utf-8")

        _git(["add", "-f", "--", _CORPUS_OUT], cwd=scratch)
        control = _git(["ls-files", "--", _CORPUS_OUT], cwd=scratch).split()

    assert control, (
        "negative control failed: a force-added corpus file was not reported by "
        "`git ls-files`, so the assertion above proves nothing."
    )


def test_no_verbatim_corpus_text_in_tracked_files() -> None:
    """No tracked file carries licensed corpus text.

    Skipped when the local corpus file is absent — which is always the case on CI, by
    design: the licensed manuals are never on CI (same posture as
    ``tests/test_corpus_ledger.py::test_on_machine_paths_are_consistent_with_reality``).
    A permanently-skipped run on CI is the expected outcome, not a broken test.
    """
    from quality_database_app.pipeline import DEFAULT_OUT_PATH

    if not DEFAULT_OUT_PATH.exists():
        pytest.skip(
            f"{DEFAULT_OUT_PATH} not present — the corpus is private and is never on CI. "
            f"Build it locally (quality_database_app.pipeline.run(), $CORPUS_ROOT) to run "
            f"this scan."
        )

    signatures = _signatures()
    # An empty-but-present corpus is a legitimate state: nothing to check, and the scan
    # passes — deliberately distinct from the skip above (file absent).
    leaks = sorted(_scan(_REPO_ROOT, signatures))
    assert not leaks, (
        "licensed corpus text is committed in tracked file(s) — the M4-1 policy forbids "
        "verbatim non-`serve` corpus text in the repo:\n  "
        + "\n  ".join(f"{path}: {sig[:40]}..." for path, sig in leaks)
    )

    if not signatures:  # pragma: no cover - only on an empty local corpus
        pytest.skip("local corpus holds no non-`serve` record long enough to sign.")

    # Negative control: plant one real signature in a tracked file of a scratch repo and
    # assert the same scan flags it.
    with tempfile.TemporaryDirectory() as directory:
        scratch = _scratch_repo(directory)
        planted_signature = sorted(signatures)[0]
        (scratch / "leaked.md").write_text(f"# notes\n\n{planted_signature}\n", encoding="utf-8")
        _git(["add", "--", "leaked.md"], cwd=scratch)
        control = _scan(scratch, signatures)

    assert ("leaked.md", planted_signature) in control, (
        "negative control failed: the scan did not flag a planted corpus signature, so "
        "the assertion above proves nothing."
    )
