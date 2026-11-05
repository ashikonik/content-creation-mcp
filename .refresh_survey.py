#!/usr/bin/env python3
"""Recompute the survey summary header and Markdown report in place.

The raw sweep output that `.build_survey.py` consumes no longer exists, but
the published JSONL does. This script reads the JSONL back, recomputes the
counts, and rewrites both artifacts so they stay consistent with the records
they describe.

Usage:
    python3 .refresh_survey.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# `.build_survey.py` is dot-prefixed, so it cannot be imported by name.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "build_survey", Path(__file__).resolve().parent / ".build_survey.py"
)
assert _spec and _spec.loader
build_survey = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_survey)

render_report = build_survey.render_report
star_histogram = build_survey.star_histogram

# `render_report` recomputes the modality split with the keyword classifier
# in `.build_survey.py`. That classifier was only ever a fallback for records
# that arrived without a modality — the published JSONL carries the curated
# value. Replacing it here keeps the Markdown and the JSONL summary header
# in agreement.
build_survey.classify_modality = lambda record: record.get("modality") or "other"

ROOT = Path(__file__).resolve().parent
SURVEYS = ROOT / "surveys"
JSONL = SURVEYS / "content_creation_github.jsonl"
MD = SURVEYS / "content_creation_github.md"

LIST_A = "agent/skill repos"
LIST_B = "tool repos"


def load() -> tuple[dict, list[dict]]:
    """Return (summary, records) from the published JSONL.

    A handful of records in the published file carry a description with a
    literal newline, so the record spills across two physical lines. Records
    are re-joined here before parsing, and the repaired file is written back
    by `main`.
    """
    records: list[dict] = []
    buffer: str | None = None
    for line in JSONL.read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith('{"_summary"'):
            continue
        if line.startswith('{"full_name"'):
            if buffer is not None:
                records.append(json.loads(buffer))
            buffer = line
        else:
            buffer = f"{buffer} {line}" if buffer else line
    if buffer is not None:
        records.append(json.loads(buffer))

    # The survey uses `avpipe` as the modality key. Repositories added to
    # the file after the original sweep used `av_pipeline`; normalise them
    # so the modality split has one bucket rather than two.
    for record in records:
        if record.get("modality") == "av_pipeline":
            record["modality"] = "avpipe"

    return {}, records


def as_list(record: dict) -> list[str]:
    value = record.get("list")
    if isinstance(value, list):
        return value
    return [value] if value else []


def build_summary(records: list[dict]) -> dict:
    list_a = [r for r in records if LIST_A in as_list(r)]
    list_b = [r for r in records if LIST_B in as_list(r)]

    def split(recs: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in recs:
            modality = r.get("modality") or "other"
            counts[modality] = counts.get(modality, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    return {
        "counts": {
            "total": len(records),
            "agent_skill_repos": len(list_a),
            "tool_repos": len(list_b),
        },
        "star_histogram": {
            "agent_skill_repos": star_histogram(list_a),
            "tool_repos": star_histogram(list_b),
        },
        "modality_split": {
            "agent_skill_repos": split(list_a),
            "tool_repos": split(list_b),
        },
    }


def to_report_shape(record: dict) -> dict:
    """Map a published record back onto the shape `render_report` expects."""
    return {
        "full_name": record.get("full_name"),
        "stars": record.get("stars"),
        "url": record.get("url"),
        "desc": record.get("description"),
        "lang": record.get("language"),
        "license": record.get("license"),
        "modality": record.get("modality"),
        "skill_hit": record.get("has_skill_defs"),
        "is_agent": record.get("is_agent"),
        "fork": record.get("fork"),
        "updated": record.get("updated"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the artifacts on disk are already up to date.",
    )
    args = parser.parse_args()

    _, records = load()
    summary = build_summary(records)

    list_a = sorted(
        (to_report_shape(r) for r in records if LIST_A in as_list(r)),
        key=lambda r: -(r.get("stars") or 0),
    )
    list_b = sorted(
        (to_report_shape(r) for r in records if LIST_B in as_list(r)),
        key=lambda r: -(r.get("stars") or 0),
    )

    # The JSONL is rewritten with the summary as line 1 and the records sorted
    # by stars descending, matching the builder's output layout.
    ordered = sorted(records, key=lambda r: -(r.get("stars") or 0))
    jsonl_text = (
        json.dumps({"_summary": summary}, ensure_ascii=False)
        + "\n"
        + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ordered)
    )

    md_text = render_report(list_a, list_b, len(ordered))

    if args.check:
        current_jsonl = JSONL.read_text(encoding="utf-8")
        current_md = MD.read_text(encoding="utf-8")
        if current_jsonl == jsonl_text and current_md == md_text:
            print("survey artifacts are up to date")
            return 0
        print("survey artifacts are STALE", file=sys.stderr)
        return 1

    JSONL.write_text(jsonl_text, encoding="utf-8")
    MD.write_text(md_text, encoding="utf-8")

    print(f"refreshed {JSONL.name} ({len(ordered)} repositories)")
    print(f"refreshed {MD.name}")
    print(
        "  counts: "
        + json.dumps(summary["counts"], ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
