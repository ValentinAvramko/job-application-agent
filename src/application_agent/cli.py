from __future__ import annotations

import argparse
import json
from pathlib import Path

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest
from application_agent.workflows.registry import build_default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="application-agent")
    parser.add_argument("--root", default=".", help="Path to the private workspace root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Create the expected workspace and runtime memory layout.")
    subparsers.add_parser("list-workflows", help="Show registered workflows.")
    subparsers.add_parser("show-memory", help="Print current runtime memory as JSON.")

    ingest = subparsers.add_parser("ingest-vacancy", help="Create a vacancy scaffold and remember it.")
    ingest.add_argument("--company", required=True)
    ingest.add_argument("--position", required=True)
    ingest.add_argument("--source-url", default="")
    ingest.add_argument("--source-channel", default="Manual")
    ingest.add_argument("--source-type", default="")
    ingest.add_argument("--source-text", default="")
    ingest.add_argument("--input-file", default="")
    ingest.add_argument("--language", default="ru")
    ingest.add_argument("--country", default="Не указано")
    ingest.add_argument("--work-mode", default="Не указано")
    ingest.add_argument("--target-mode", default="balanced")
    ingest.add_argument("--include-employer-channels", action="store_true")
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

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

