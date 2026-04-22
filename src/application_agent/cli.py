from __future__ import annotations

import argparse
import json
from pathlib import Path

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.analyze_vacancy import AnalyzeVacancyRequest
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest
from application_agent.workflows.intake_adoptions import IntakeAdoptionsRequest
from application_agent.workflows.prepare_screening import PrepareScreeningRequest
from application_agent.workflows.registry import build_default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="application-agent")
    parser.add_argument("--root", default=".", help="Path to the private workspace root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Create the expected workspace and runtime memory layout.")
    subparsers.add_parser("list-workflows", help="Show registered workflows.")
    subparsers.add_parser("show-memory", help="Print current runtime memory as JSON.")

    ingest = subparsers.add_parser("ingest-vacancy", help="Create a vacancy scaffold and remember it.")
    ingest.add_argument("--company", default="")
    ingest.add_argument("--position", default="")
    ingest.add_argument("--source-url", default="")
    ingest.add_argument("--source-channel", default="")
    ingest.add_argument("--source-type", default="")
    ingest.add_argument("--source-text", default="")
    ingest.add_argument("--input-file", default="")
    ingest.add_argument("--language", default="")
    ingest.add_argument("--country", default="")
    ingest.add_argument("--work-mode", default="")
    ingest.add_argument("--target-mode", default="balanced")
    ingest.add_argument("--include-employer-channels", action="store_true")

    analyze = subparsers.add_parser("analyze-vacancy", help="Create the first-pass fit analysis for a vacancy.")
    analyze.add_argument("--vacancy-id", default="")
    analyze.add_argument("--company", default="")
    analyze.add_argument("--position", default="")
    analyze.add_argument("--source-url", default="")
    analyze.add_argument("--source-channel", default="Manual")
    analyze.add_argument("--source-type", default="")
    analyze.add_argument("--source-text", default="")
    analyze.add_argument("--input-file", default="")
    analyze.add_argument("--language", default="")
    analyze.add_argument("--country", default="")
    analyze.add_argument("--work-mode", default="")
    analyze.add_argument("--target-mode", default="")
    analyze.add_argument("--selected-resume", default="")
    analyze.add_argument("--include-employer-channels", action="store_true")

    prepare = subparsers.add_parser(
        "prepare-screening",
        help="Build screening.md for an already ingested and analyzed vacancy.",
    )
    prepare.add_argument("--vacancy-id", default="")
    prepare.add_argument("--selected-resume", default="")
    prepare.add_argument("--output-language", default="")
    prepare.add_argument("--preparation-depth", default="")

    intake = subparsers.add_parser(
        "intake-adoptions",
        help="Normalize vacancy adoptions into root inbox and pending questions.",
    )
    intake.add_argument("--vacancy-id", default="")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    layout = WorkspaceLayout(Path(args.root).resolve())
    created_dirs = layout.bootstrap()
    store = JsonMemoryStore(layout)
    store.bootstrap()

    if args.command == "bootstrap":
        print(json.dumps({"created_directories": [str(path) for path in created_dirs]}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "list-workflows":
        registry = build_default_registry()
        payload = [{"name": name, "description": getattr(workflow, "description", "")} for name, workflow in registry.items()]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "show-memory":
        print(json.dumps(store.snapshot(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "ingest-vacancy":
        source_text = args.source_text
        if args.input_file:
            source_text = Path(args.input_file).read_text(encoding="utf-8")
        request = IngestVacancyRequest(
            company=args.company,
            position=args.position,
            source_text=source_text,
            source_url=args.source_url,
            source_channel=args.source_channel,
            source_type=args.source_type,
            language=args.language,
            country=args.country,
            work_mode=args.work_mode,
            target_mode=args.target_mode,
            include_employer_channels=args.include_employer_channels,
        )
        workflow = build_default_registry().get("ingest-vacancy")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.command == "analyze-vacancy":
        source_text = args.source_text
        if args.input_file:
            source_text = Path(args.input_file).read_text(encoding="utf-8")
        request = AnalyzeVacancyRequest(
            vacancy_id=args.vacancy_id or None,
            company=args.company,
            position=args.position,
            source_text=source_text,
            source_url=args.source_url,
            source_channel=args.source_channel,
            source_type=args.source_type,
            language=args.language,
            country=args.country,
            work_mode=args.work_mode,
            target_mode=args.target_mode,
            selected_resume=args.selected_resume,
            include_employer_channels=args.include_employer_channels,
        )
        workflow = build_default_registry().get("analyze-vacancy")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.command == "prepare-screening":
        request = PrepareScreeningRequest(
            vacancy_id=args.vacancy_id,
            selected_resume=args.selected_resume,
            output_language=args.output_language,
            preparation_depth=args.preparation_depth,
        )
        workflow = build_default_registry().get("prepare-screening")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.command == "intake-adoptions":
        request = IntakeAdoptionsRequest(vacancy_id=args.vacancy_id)
        workflow = build_default_registry().get("intake-adoptions")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
