from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.linkedin_builder import apply_build_linkedin_projection
from application_agent.workspace import WorkspaceLayout


class BuildLinkedInHelpersTests(unittest.TestCase):
    def test_projection_builds_artifact_with_metadata_precedence_and_is_idempotent(self) -> None:
        workspace_dir, layout = build_workspace("build-linkedin-idempotent")
        master_path = layout.resumes_dir / "MASTER.md"
        role_resume_path = layout.resumes_dir / "CTO.md"
        metadata_path = layout.profile_dir / "contact-regions.yml"
        output_path = layout.profile_dir / "linkedin" / "CTO.md"

        metadata_path.write_text(
            "\n".join(
                [
                    "public_name:",
                    '  ru: "Валентин Аврамко"',
                    '  eu: "Valentin Avramko"',
                    "public_location:",
                    '  ru: "Краснодар"',
                    '  eu: "Bilbao, Spain"',
                    "links:",
                    '  linkedin: "https://linkedin.com/in/valentin-avramko"',
                    "contacts:",
                    '  email: "public@example.com"',
                    '  phone: "+34 600 11 22 33"',
                    "",
                ]
            ),
            encoding="utf-8",
            newline="\n",
        )

        first = apply_build_linkedin_projection(
            target_role="CTO",
            master_path=master_path,
            role_resume_path=role_resume_path,
            profile_metadata_path=metadata_path,
            output_path=output_path,
        )
        second = apply_build_linkedin_projection(
            target_role="CTO",
            master_path=master_path,
            role_resume_path=role_resume_path,
            profile_metadata_path=metadata_path,
            output_path=output_path,
        )

        artifact = output_path.read_text(encoding="utf-8")
        public_part, _, guide_part = artifact.partition("## Field-by-Field Filling Guide")

        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertIn("## Executive Summary", artifact)
        self.assertIn("## Ready-to-Paste RU Pack", artifact)
        self.assertIn("## Ready-to-Paste EN Pack", artifact)
        self.assertIn("- Name: Валентин Аврамко", artifact)
        self.assertIn("- Name: Valentin Avramko", artifact)
        self.assertIn("- Location: Bilbao, Spain", artifact)
        self.assertIn("https://linkedin.com/in/valentin-avramko", artifact)
        self.assertIn("Технический директор с опытом управления инженерными командами", artifact)
        self.assertNotIn("public@example.com", public_part)
        self.assertNotIn("+34 600 11 22 33", public_part)
        self.assertIn("OPTIONAL: public@example.com", guide_part)
        self.assertIn("OPTIONAL: +34 600 11 22 33", guide_part)

    def test_projection_marks_missing_metadata_and_translation_gaps_without_inventing_public_values(self) -> None:
        workspace_dir, layout = build_workspace("build-linkedin-gaps")
        master_path = layout.resumes_dir / "MASTER.md"
        role_resume_path = layout.resumes_dir / "EM.md"
        output_path = layout.profile_dir / "linkedin" / "EM.md"
        write_minimal_master_resume(master_path)

        result = apply_build_linkedin_projection(
            target_role="Engineering Manager",
            master_path=master_path,
            role_resume_path=role_resume_path,
            profile_metadata_path=layout.profile_dir / "contact-regions.yml",
            output_path=output_path,
        )

        artifact = output_path.read_text(encoding="utf-8")
        public_part, _, guide_part = artifact.partition("## Field-by-Field Filling Guide")

        self.assertTrue(result.changed)
        self.assertIn(
            "CHECK: profile/contact-regions.yml is missing; public profile surface falls back to resume inputs only.",
            artifact,
        )
        self.assertIn("CHECK: English public name variant is missing in the current inputs.", artifact)
        self.assertIn("CHECK: English location variant is missing in the current inputs.", artifact)
        self.assertIn("CHECK: Prepare English About from the approved RU source below without adding new facts.", artifact)
        self.assertIn("GAP: no factual experience bullets were found in MASTER or the role resume.", artifact)
        self.assertIn("OPTIONAL: add the public LinkedIn URL after the profile is created.", artifact)
        self.assertNotIn("private@example.com", public_part)
        self.assertIn("OPTIONAL: private@example.com", guide_part)


def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f"{prefix}-{uuid.uuid4().hex}"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_master_resume(layout.resumes_dir / "MASTER.md")
    write_cto_resume(layout.resumes_dir / "CTO.md")
    write_em_resume(layout.resumes_dir / "EM.md")
    return workspace_dir, layout


def write_master_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "full_name:",
                '  ru: "Валентин Аврамко"',
                '  eu: "Valentin Avramko"',
                "location:",
                '  ru: "Краснодар, Россия"',
                '  eu: "Bilbao, Spain"',
                "contacts:",
                '  email: "private@example.com"',
                '  phone: "+34 699 00 11 22"',
                '  telegram: "@ValentinAvramko"',
                "links:",
                '  linkedin: "https://linkedin.com/in/Avramko"',
                "---",
                "",
                "# Валентин Аврамко — Executive Profile",
                "",
                "## О себе",
                "",
                "Руковожу архитектурой, delivery и инженерными командами в продуктовых и корпоративных системах.",
                "",
                "## Ключевые достижения",
                "",
                "- Built internal RAG prototype with pgvector",
                "- Improved delivery metrics through CI/CD discipline",
                "",
                "## Опыт работы",
                "",
                "### Free2Trip",
                "",
                "**CTO**",
                "",
                "- Led architecture and product delivery.",
                "",
                "## Рекомендации",
                "",
                "References available on request.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def write_minimal_master_resume(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "---",
                "full_name:",
                '  ru: "Валентин Аврамко"',
                "location:",
                '  ru: "Краснодар, Россия"',
                "contacts:",
                '  email: "private@example.com"',
                "---",
                "",
                "# Валентин Аврамко — Executive Profile",
                "",
                "## О себе",
                "",
                "Руковожу инженерной командой и улучшаю процессы поставки изменений.",
                "",
                "## Рекомендации",
                "",
                "References available on request.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def write_cto_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Валентин Аврамко — Технический директор",
                "",
                "## О себе",
                "",
                "Технический директор с опытом управления инженерными командами, delivery и архитектурой корпоративных платформ.",
                "",
                "## Ключевые акценты",
                "",
                "- Platform engineering and delivery systems",
                "- Executive stakeholder management",
                "",
                "## Технологии и инструменты",
                "",
                "- OpenAI",
                "- PostgreSQL",
                "",
                "## Опыт работы",
                "",
                "### Free2Trip",
                "",
                "**CTO**",
                "",
                "- Own product architecture and delivery.",
                "",
                "## Рекомендации",
                "",
                "References available on request.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def write_em_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Валентин Аврамко — Engineering Manager",
                "",
                "## О себе",
                "",
                "Руковожу инженерной командой и улучшаю процессы поставки изменений.",
                "",
                "## Рекомендации",
                "",
                "References available on request.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    unittest.main()
