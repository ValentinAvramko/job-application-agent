from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.analyze_vacancy import AnalyzeVacancyRequest
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest
from application_agent.workflows.registry import build_default_registry


def extract_vacancy_id_from_artifacts(artifacts: list[str]) -> str:
    for artifact in artifacts:
        path = Path(artifact)
        if path.name in {"meta.yml", "source.md", "analysis.md", "adoptions.md"}:
            return path.parent.name
    raise ValueError("Unable to determine vacancy_id from workflow artifacts.")


def build_ingest_commit_message(vacancy_id: str) -> str:
    return f"Ingest vacancy {vacancy_id}"


def run_git_command(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def autopush_ingest_artifacts(repo_root: Path, artifacts: list[str]) -> str:
    tracked_artifacts = [
        str(Path(artifact).resolve().relative_to(repo_root))
        for artifact in artifacts
        if Path(artifact).resolve().is_relative_to(repo_root)
    ]
    if not tracked_artifacts:
        raise ValueError("No ingest artifacts are located inside the workspace repository.")

    vacancy_id = extract_vacancy_id_from_artifacts(artifacts)
    add_result = run_git_command(repo_root, ["add", "--", *tracked_artifacts])
    if add_result.returncode != 0:
        raise RuntimeError(f"Failed to stage ingest artifacts: {add_result.stderr.strip() or add_result.stdout.strip()}")

    commit_message = build_ingest_commit_message(vacancy_id)
    commit_result = run_git_command(repo_root, ["commit", "-m", commit_message])
    if commit_result.returncode != 0:
        output = commit_result.stderr.strip() or commit_result.stdout.strip()
        if "nothing to commit" not in output.lower():
            raise RuntimeError(f"Failed to commit ingest artifacts: {output}")

    branch_result = run_git_command(repo_root, ["branch", "--show-current"])
    if branch_result.returncode != 0:
        raise RuntimeError(f"Failed to detect current git branch: {branch_result.stderr.strip() or branch_result.stdout.strip()}")
    branch = branch_result.stdout.strip() or "main"

    push_result = run_git_command(repo_root, ["push", "origin", branch])
    if push_result.returncode != 0:
        raise RuntimeError(f"Failed to push ingest artifacts: {push_result.stderr.strip() or push_result.stdout.strip()}")

    return commit_message


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
        commit_message = autopush_ingest_artifacts(layout.root, result.artifacts)
        result.summary = f"{result.summary} Выполнены git commit и push: {commit_message}."
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

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
