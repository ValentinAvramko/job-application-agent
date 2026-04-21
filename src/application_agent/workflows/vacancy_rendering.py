from __future__ import annotations


def render_meta(request: object, vacancy_id: str, timestamp: str, infer_source_channel: object, *, excel_row: int | None = None) -> str:
    request_country = getattr(request, "country").strip() or "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e"
    request_work_mode = getattr(request, "work_mode").strip() or "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e"
    source_channel = getattr(request, "source_channel").strip() or infer_source_channel(
        getattr(request, "source_url"),
        getattr(request, "source_text"),
    )
    return "\n".join(
        [
            f"vacancy_id: {vacancy_id}",
            f"source_type: {request.normalized_source_type()}",
            f"source_url: {getattr(request, 'source_url') or 'null'}",
            f"source_channel: {source_channel}",
            f"company: {getattr(request, 'company')}",
            f"position: {getattr(request, 'position')}",
            f"language: {getattr(request, 'language')}",
            f"country: {request_country}",
            f"work_mode: {request_work_mode}",
            'is_active: "\u0414\u0430"',
            f"ingested_at: {timestamp}",
            "selected_resume: undecided",
            f"target_mode: {getattr(request, 'target_mode')}",
            f"include_employer_channels: {str(getattr(request, 'include_employer_channels')).lower()}",
            f"excel_row: {excel_row if excel_row is not None else 'null'}",
            "status: ingested",
            'notes: ""',
            "",
        ]
    )


def render_source(request: object, vacancy_id: str, infer_source_channel: object, is_unspecified: object) -> str:
    def display_value(value: str) -> str:
        cleaned = value.strip()
        return "\u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445" if is_unspecified(cleaned) else cleaned

    source_channel = getattr(request, "source_channel") or infer_source_channel(
        getattr(request, "source_url"),
        getattr(request, "source_text"),
    )
    lines = [
        "# \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
        "",
        "## \u041f\u0430\u0441\u043f\u043e\u0440\u0442",
        "",
        f"- \u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f: {display_value(getattr(request, 'company'))}",
        f"- \u041f\u043e\u0437\u0438\u0446\u0438\u044f: {display_value(getattr(request, 'position'))}",
        f"- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: {vacancy_id}",
        f"- \u0418\u0441\u0445\u043e\u0434\u043d\u0430\u044f \u0441\u0441\u044b\u043b\u043a\u0430: {display_value(getattr(request, 'source_url'))}",
        f"- \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: {display_value(source_channel)}",
        "",
        "## \u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
        "",
    ]

    params = [
        ("\u0421\u0442\u0440\u0430\u043d\u0430", getattr(request, "country")),
        ("\u0413\u043e\u0440\u043e\u0434", getattr(request, "city")),
        ("\u0417\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c", getattr(request, "employment_type")),
        ("\u0413\u0440\u0430\u0444\u0438\u043a", getattr(request, "work_schedule")),
        ("\u0424\u043e\u0440\u043c\u0430\u0442 \u0440\u0430\u0431\u043e\u0442\u044b", getattr(request, "work_mode")),
    ]
    lines.extend([f"- {label}: {display_value(value)}" for label, value in params])

    lines.extend(["", "## \u0418\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442", ""])
    if getattr(request, "source_markdown").strip():
        lines.append(getattr(request, "source_markdown").strip())
    elif getattr(request, "source_text").strip():
        lines.append(getattr(request, "source_text").strip())
    else:
        lines.append("<!-- \u0412\u0441\u0442\u0430\u0432\u044c \u0441\u044e\u0434\u0430 \u0438\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 \u0431\u0435\u0437 \u0438\u043d\u0442\u0435\u0440\u043f\u0440\u0435\u0442\u0430\u0446\u0438\u0438. -->")
    lines.append("")
    return "\n".join(lines)


def render_target_mode(target_mode: str) -> str:
    mapping = {
        "conservative": "\u043a\u043e\u043d\u0441\u0435\u0440\u0432\u0430\u0442\u0438\u0432\u043d\u044b\u0439",
        "balanced": "\u0441\u0431\u0430\u043b\u0430\u043d\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439",
        "aggressive": "\u0430\u0433\u0440\u0435\u0441\u0441\u0438\u0432\u043d\u044b\u0439",
    }
    return mapping.get(target_mode, target_mode)


def render_analysis(vacancy_id: str, request: object) -> str:
    return "\n".join(
        [
            "# \u0410\u043d\u0430\u043b\u0438\u0437 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
            "",
            "## \u0421\u0432\u043e\u0434\u043a\u0430",
            "",
            f"- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: {vacancy_id}",
            "- \u0412\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0435 \u0440\u0435\u0437\u044e\u043c\u0435: undecided",
            f"- \u0420\u0435\u0436\u0438\u043c \u0430\u0434\u0430\u043f\u0442\u0430\u0446\u0438\u0438: {render_target_mode(getattr(request, 'target_mode'))}",
            f"- \u042f\u0437\u044b\u043a: {getattr(request, 'language')}",
            f"- \u041a\u0430\u043d\u0430\u043b\u044b \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044f: {'\u0434\u0430' if getattr(request, 'include_employer_channels') else '\u043d\u0435\u0442'}",
            "",
            "## \u0410\u043d\u0430\u043b\u0438\u0437 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f: \u0442\u0435\u043a\u0443\u0449\u0435\u0435 \u0440\u0435\u0437\u044e\u043c\u0435",
            "",
            "- \u041e\u0431\u0449\u0435\u0435 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u0435:",
            "- \u041a\u0440\u0430\u0442\u043a\u0438\u0439 \u0432\u044b\u0432\u043e\u0434:",
            "",
            "## \u0410\u043d\u0430\u043b\u0438\u0437 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f: \u043f\u043e\u0441\u043b\u0435 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u043d\u044b\u0445 \u043f\u0440\u0430\u0432\u043e\u043a",
            "",
            "- \u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f:",
            "- \u041f\u0440\u0438\u0440\u043e\u0441\u0442:",
            "- \u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439:",
            "",
            "## \u041c\u0430\u0442\u0440\u0438\u0446\u0430 \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u0439",
            "",
            "| \u0422\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u0435 | \u041f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442 | \u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 | \u041f\u043e\u043a\u0440\u044b\u0442\u0438\u0435 | \u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439 |",
            "| --- | --- | --- | --- | --- |",
            "",
            "## \u0421\u0438\u043b\u044c\u043d\u044b\u0435 \u0441\u0442\u043e\u0440\u043e\u043d\u044b",
            "",
            "- ",
            "",
            "## \u041f\u0440\u043e\u0431\u0435\u043b\u044b",
            "",
            "- ",
            "",
            "## \u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u0434\u043b\u044f \u0441\u043e\u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e \u043f\u0438\u0441\u044c\u043c\u0430",
            "",
            "- ",
            "",
            "## \u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u043f\u043e \u043f\u0440\u0430\u0432\u043a\u0430\u043c \u0440\u0435\u0437\u044e\u043c\u0435",
            "",
            "- ",
            "",
            "## \u041a\u0430\u043d\u0430\u043b\u044b \u0441\u0432\u044f\u0437\u0438 \u0441 \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u0435\u043c",
            "",
            "- ",
            "",
            "## \u0412\u043e\u043f\u0440\u043e\u0441\u044b \u043d\u0430 \u0443\u0442\u043e\u0447\u043d\u0435\u043d\u0438\u0435",
            "",
            "- ",
            "",
        ]
    )


def render_adoptions(vacancy_id: str) -> str:
    return "\n".join(
        [
            "# \u0410\u0434\u0430\u043f\u0442\u0430\u0446\u0438\u0438 \u043f\u043e \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
            "",
            f"- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: {vacancy_id}",
            "",
            "## \u0412\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0435 \u0441\u0438\u0433\u043d\u0430\u043b\u044b",
            "",
            "- ",
            "",
            "## \u041a\u0430\u043d\u0434\u0438\u0434\u0430\u0442\u044b \u0432 \u043f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0435 \u0441\u0438\u0433\u043d\u0430\u043b\u044b",
            "",
            "- ",
            "",
            "## \u041e\u0442\u043a\u0440\u044b\u0442\u044b\u0435 \u0432\u043e\u043f\u0440\u043e\u0441\u044b",
            "",
            "- ",
            "",
            "## \u041e\u0431\u0449\u0438\u0435 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438 \u043f\u043e \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0438\u044e \u0438\u0437 MASTER \u0432 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0440\u043e\u043b\u0435\u0432\u0443\u044e \u0432\u0435\u0440\u0441\u0438\u044e",
            "",
            "- ",
            "",
            "## \u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 `\u041e \u0441\u0435\u0431\u0435 (\u043f\u0440\u043e\u0444\u0438\u043b\u044c)`",
            "",
            "- ",
            "",
            "## \u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 `\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043a\u043e\u043c\u043f\u0435\u0442\u0435\u043d\u0446\u0438\u0438`",
            "",
            "- ",
            "",
            "## \u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 `\u041e\u043f\u044b\u0442 \u0440\u0430\u0431\u043e\u0442\u044b`",
            "",
            "- ",
            "",
        ]
    )
