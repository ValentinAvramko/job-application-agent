from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.analyze_vacancy import AnalyzeVacancyRequest
from application_agent.workflows.build_linkedin import BuildLinkedInRequest
from application_agent.workflows.export_resume_pdf import ExportResumePdfRequest
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest
from application_agent.workflows.intake_adoptions import IntakeAdoptionsRequest
from application_agent.workflows.prepare_screening import PrepareScreeningRequest
from application_agent.workflows.rebuild_master import RebuildMasterRequest
from application_agent.workflows.rebuild_role_resume import RebuildRoleResumeRequest
from application_agent.workflows.registry import build_default_registry

DEFAULT_CONFIG_RELATIVE_PATH = Path("agent_memory") / "config" / "application-agent.json"
DEFAULT_SECRETS_RELATIVE_PATH = Path("agent_memory") / "config" / "secrets.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-application-agent")
    parser.add_argument("--root", default=".", help="Path to the private workspace root.")
    parser.add_argument(
        "--config",
        default="",
        help=(
            "Optional JSON config with workflow defaults. "
            "Defaults to <root>/agent_memory/config/application-agent.json when that file exists."
        ),
    )
    parser.add_argument(
        "--secrets",
        default="",
        help=(
            "Optional JSON secrets config. "
            "Defaults to <root>/agent_memory/config/secrets.json when that file exists."
        ),
    )
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

    analyze = subparsers.add_parser("analyze-vacancy", help="Create the deep fit analysis package for a vacancy.")
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
    analyze.add_argument("--target-mode", default=None)
    analyze.add_argument("--selected-resume", default=None)
    analyze.add_argument("--llm-provider", default=None)
    analyze.add_argument("--llm-model", default=None)
    analyze.add_argument("--llm-temperature", default=None, type=float)
    analyze.add_argument("--llm-reasoning-effort", default=None)
    analyze.add_argument("--llm-reasoning-summary", default=None)
    analyze.add_argument("--llm-text-verbosity", default=None)
    analyze.add_argument("--russian-text-skill-path", default=None)
    analyze.add_argument("--include-employer-channels", action="store_true", default=None)

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

    subparsers.add_parser(
        "rebuild-master",
        help="Rebuild the MASTER resume managed approved-signals section and runtime report.",
    )
    rebuild_role = subparsers.add_parser(
        "rebuild-role-resume",
        help="Rebuild the managed canonical block for a selected role resume.",
    )
    rebuild_role.add_argument("--target-role", default="")
    build_linkedin = subparsers.add_parser(
        "build-linkedin",
        help="Build a deterministic LinkedIn draft pack for a selected role resume.",
    )
    build_linkedin.add_argument("--target-role", default="")
    export_resume_pdf = subparsers.add_parser(
        "export-resume-pdf",
        help="Render a PDF artifact and verification trail for a selected resume source.",
    )
    export_resume_pdf.add_argument("--target-resume", default="")
    export_resume_pdf.add_argument("--output-language", default="")
    export_resume_pdf.add_argument("--contact-region", default="")
    export_resume_pdf.add_argument("--template-id", default="")
    return parser


def load_cli_config(*, root: Path, config_path: str) -> dict[str, Any]:
    path = resolve_config_path(root=root, config_path=config_path)
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid config at {path}: top-level JSON value must be an object.")
    return payload


def load_secret_config(*, root: Path, secrets_path: str) -> dict[str, Any]:
    path = resolve_secrets_path(root=root, secrets_path=secrets_path)
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON secrets config at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid secrets config at {path}: top-level JSON value must be an object.")
    return payload


def resolve_config_path(*, root: Path, config_path: str) -> Path | None:
    if config_path.strip():
        path = Path(config_path).expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()
    return root / DEFAULT_CONFIG_RELATIVE_PATH


def resolve_secrets_path(*, root: Path, secrets_path: str) -> Path | None:
    if secrets_path.strip():
        path = Path(secrets_path).expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()
    return root / DEFAULT_SECRETS_RELATIVE_PATH


def workflow_config(config: dict[str, Any], workflow_name: str) -> dict[str, Any]:
    raw = config.get(workflow_name, {})
    if raw == {} and isinstance(config.get("workflows"), dict):
        raw = config["workflows"].get(workflow_name, {})
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid config for workflow '{workflow_name}': expected object.")
    return raw


def config_value(
    args: argparse.Namespace,
    config: dict[str, Any],
    attr: str,
    *,
    config_key: str | None = None,
    default: Any = "",
) -> Any:
    value = getattr(args, attr)
    if value is not None:
        return value
    return config.get(config_key or attr, default)


def optional_float_config_value(args: argparse.Namespace, config: dict[str, Any], attr: str) -> float | None:
    value = config_value(args, config, attr, default=None)
    if value in {None, ""}:
        return None
    return float(value)


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
        config = load_cli_config(root=layout.root, config_path=args.config)
        secrets = load_secret_config(root=layout.root, secrets_path=args.secrets)
        analyze_config = workflow_config(config, "analyze-vacancy")
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
            target_mode=config_value(args, analyze_config, "target_mode", default=""),
            selected_resume=config_value(args, analyze_config, "selected_resume", default=""),
            llm_provider=config_value(args, analyze_config, "llm_provider", default="openai"),
            llm_model=config_value(args, analyze_config, "llm_model", default=""),
            llm_temperature=optional_float_config_value(args, analyze_config, "llm_temperature"),
            llm_reasoning_effort=config_value(args, analyze_config, "llm_reasoning_effort", default=""),
            llm_reasoning_summary=config_value(args, analyze_config, "llm_reasoning_summary", default=""),
            llm_text_verbosity=config_value(args, analyze_config, "llm_text_verbosity", default=""),
            llm_api_key=str(secrets.get("OPENAI_API_KEY", "")).strip(),
            llm_base_url=str(secrets.get("OPENAI_BASE_URL", "")).strip(),
            russian_text_skill_path=config_value(args, analyze_config, "russian_text_skill_path", default=""),
            include_employer_channels=bool(
                config_value(args, analyze_config, "include_employer_channels", default=False)
            ),
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

    if args.command == "rebuild-master":
        request = RebuildMasterRequest()
        workflow = build_default_registry().get("rebuild-master")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.command == "rebuild-role-resume":
        request = RebuildRoleResumeRequest(target_role=args.target_role)
        workflow = build_default_registry().get("rebuild-role-resume")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.command == "build-linkedin":
        request = BuildLinkedInRequest(target_role=args.target_role)
        workflow = build_default_registry().get("build-linkedin")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-resume-pdf":
        request = ExportResumePdfRequest(
            target_resume=args.target_resume,
            output_language=args.output_language,
            contact_region=args.contact_region,
            template_id=args.template_id,
        )
        workflow = build_default_registry().get("export-resume-pdf")
        result = workflow.run(layout=layout, store=store, request=request)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
