"""Markdown report body builder for the report node."""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Any

from state.transcript_analysis_schema import REASON_TO_CATEGORY

OUTCOME_KPI_LABELS: dict[str, str] = {
    "total_transcripts": "Transcripts analyzed in this batch",
    "resolved_total": "Successfully resolved conversations",
    "overall_resolution_rate_pct": "Overall resolution success rate",
    "chatbot_resolved_count": "Fully resolved by the chatbot",
    "human_resolved_count": "Fully resolved by a human agent",
    "unresolved_count": "Still unresolved at conversation end",
    "user_abandoned_count": "Users who abandoned the conversation",
    "escalated_no_resolution_count": "Escalated but left unresolved",
    "transferred_only_count": "Transferred only with no resolution",
    "partial_resolution_count": "Partially resolved outcomes",
    "unknown_stage_count": "Unknown or missing outcome stage",
    "chatbot_resolved_rate_pct": "Share of volume resolved by chatbot",
    "human_resolved_rate_pct": "Share of volume resolved by humans",
}


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").title()


def _ops(state: dict) -> dict[str, Any]:
    raw = state.get("operations_metrics") or {}
    return raw if isinstance(raw, dict) else {}


def _failure(state: dict) -> dict[str, Any]:
    raw = state.get("failure_metrics") or {}
    return raw if isinstance(raw, dict) else {}


def _mermaid_safe_label(s: str, max_len: int = 40) -> str:
    t = _humanize_key(s)
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return t.replace('"', "'")


def _mermaid_pie_from_counts(title: str, counts: dict[str, int]) -> str:
    lines = ["```mermaid", "pie showData", f"    title {title}"]
    for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        if v <= 0:
            continue
        label = _mermaid_safe_label(k)
        lines.append(f'    "{label}" : {v}')
    if len(lines) == 3:
        lines.append('    "No data" : 1')
    lines.append("```")
    return "\n".join(lines)


def _md_table_rows(rows: list[tuple[str, str]]) -> str:
    out = ["| Metric | Value |", "| --- | --- |"]
    for k, v in rows:
        out.append(f"| {k} | {v} |")
    return "\n".join(out)


def _md_table_metric_value_note(rows: list[tuple[str, str, str]]) -> str:
    out = ["| Metric | Value | Note |", "| --- | --- | --- |"]
    for metric, value, note in rows:
        out.append(f"| {metric} | {value} | {note} |")
    return "\n".join(out)


def _outcome_kpis_table_rows(om: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for k in sorted(om.keys()):
        label = OUTCOME_KPI_LABELS.get(k, _humanize_key(k))
        rows.append((label, str(om[k])))
    return rows


def _summary_kpis_and_stages(
    ops: dict[str, Any], fail: dict[str, Any]
) -> tuple[list[tuple[str, str, str]], dict[str, int], str | None]:
    if "error" in ops:
        err = str(ops.get("error", "Unknown error"))
        return [("Operations metrics", "—", err)], {}, None

    kpis = ops.get("outcome_kpis") or {}
    if not isinstance(kpis, dict):
        kpis = {}

    total = int(kpis.get("total_transcripts") or 0)
    resolved = int(kpis.get("resolved_total") or 0)
    not_resolved = max(0, total - resolved)
    rate = kpis.get("overall_resolution_rate_pct")
    rate_s = f"{rate}%" if rate is not None else "—"
    not_pct = round(100.0 * not_resolved / total, 1) if total else 0.0

    by_cat = fail.get("failure_reason_mentions_by_category") or {}
    if not isinstance(by_cat, dict):
        by_cat = {}
    comm = int(by_cat.get("agent_communication", 0) or 0) + int(
        by_cat.get("chatbot_communication", 0) or 0
    )
    policy_n = int(by_cat.get("policy", 0) or 0)
    with_fail = int(fail.get("transcripts_with_failure_reasons") or 0)

    cards: list[tuple[str, str, str]] = [
        ("Total transcripts", f"{total:,}", "Analyzed in this run"),
        ("Resolved", f"{resolved:,}", f"{rate_s} overall resolution rate"),
        ("Failure to resolve", f"{not_resolved:,}", f"{not_pct}% of volume" if total else "—"),
        ("Communication issues", f"{comm:,}", "Mentions (agent + chatbot)"),
        ("User abandoned", f"{int(kpis.get('user_abandoned_count') or 0):,}", "By resolution stage"),
        (
            "Escalated, no resolution",
            f"{int(kpis.get('escalated_no_resolution_count') or 0):,}",
            "By resolution stage",
        ),
        ("With failure reasons", f"{with_fail:,}", "Transcripts flagged"),
        ("Policy-related", f"{policy_n:,}", "Failure mention count"),
    ]

    stage_counts: dict[str, int] = {}
    for row in ops.get("resolution_stage_breakdown") or []:
        if isinstance(row, dict):
            st = str(row.get("resolution_stage") or "")
            c = int(row.get("count") or 0)
            if st:
                stage_counts[st] = c

    return cards, stage_counts, None


def _executive_summary_md(
    kpi_cards: list[tuple[str, str, str]],
    stage_counts: dict[str, int],
) -> str:
    lines = [
        "### Executive summary",
        "",
        _md_table_metric_value_note(kpi_cards),
        "",
        "### Resolution mix",
        "",
    ]
    total = sum(stage_counts.values())
    if total <= 0:
        lines.append("*No resolution mix data.*")
    else:
        lines.append(_mermaid_pie_from_counts("Resolution mix", stage_counts))
    return "\n".join(lines)


def _group_reasons_by_category(
    by_reason: dict[str, int],
) -> dict[str, list[tuple[str, int]]]:
    g: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for reason, cnt in by_reason.items():
        r = str(reason)
        cat = REASON_TO_CATEGORY.get(r, "other")
        g[cat].append((r, int(cnt)))
    for cat in g:
        g[cat].sort(key=lambda x: (-x[1], x[0]))
    return dict(g)


_MENTION_COL_STYLE = (
    "text-align:right;width:5.5em;min-width:5.5em;"
    "font-variant-numeric:tabular-nums;padding-left:1em;"
)


def _failure_reasons_by_category_html(fail: dict[str, Any]) -> str:
    raw_reason = fail.get("failure_reason_mentions_by_reason")
    if not isinstance(raw_reason, dict) or not raw_reason:
        return "*No per-reason failure data.*\n"

    by_reason = {str(k): int(v) for k, v in raw_reason.items()}
    grouped = _group_reasons_by_category(by_reason)
    cat_totals = {c: sum(n for _, n in pairs) for c, pairs in grouped.items()}
    cat_order = sorted(cat_totals.keys(), key=lambda c: (-cat_totals[c], c))

    body_rows: list[str] = []
    th_mentions = f'<th style="{_MENTION_COL_STYLE}">Mentions</th>'

    for cat in cat_order:
        reasons = grouped.get(cat, [])
        if not reasons:
            continue
        total = cat_totals[cat]
        title = html.escape(_humanize_key(str(cat)))
        n_rows = len(reasons)
        for i, (r, n) in enumerate(reasons):
            reason_td = f"<td>{html.escape(_humanize_key(r))}</td>"
            mention_td = f'<td style="{_MENTION_COL_STYLE}">{n}</td>'
            if i == 0:
                cat_td = (
                    f'<td rowspan="{n_rows}" style="vertical-align:top;">'
                    f"<strong>{title}</strong><br/>"
                    f"<small>Total mentions: {total}</small></td>"
                )
                body_rows.append(f"<tr>{cat_td}{reason_td}{mention_td}</tr>")
            else:
                body_rows.append(f"<tr>{reason_td}{mention_td}</tr>")

    return (
        '<table border="1" cellpadding="8" cellspacing="0" '
        'style="width:100%;border-collapse:collapse;">'
        f"<thead><tr><th>Category</th><th>Reason</th>{th_mentions}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>\n"
    )


_FAILURE_BAR_PALETTE: tuple[str, ...] = (
    "#2563eb",
    "#16a34a",
    "#d97706",
    "#dc2626",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#ea580c",
    "#4f46e5",
    "#0d9488",
)


def _failure_category_bars_html(
    title: str,
    categories: list[str],
    values: list[int],
) -> str:
    if not categories or not values:
        return "*No failure category data.*"
    n = len(categories)
    colors = [_FAILURE_BAR_PALETTE[i % len(_FAILURE_BAR_PALETTE)] for i in range(n)]
    vmax = max(max(values), 1)

    parts: list[str] = [
        f'<p style="font-weight:600;margin:0 0 12px 0;">{html.escape(title)}</p>',
        '<div style="max-width:720px;font-family:system-ui,Segoe UI,sans-serif;font-size:0.9rem;">',
    ]
    for i, (cat, v) in enumerate(zip(categories, values)):
        c = colors[i]
        pct = min(100.0, 100.0 * float(v) / float(vmax))
        label = html.escape(_humanize_key(str(cat)))
        ce = html.escape(c)
        parts.append(
            '<div style="display:flex;align-items:center;gap:10px;margin:10px 0;">'
            f'<span style="flex:0 0 14px;height:14px;background:{ce};border-radius:2px;"></span>'
            f'<span style="flex:0 1 11rem;min-width:0;line-height:1.25;">{label}</span>'
            '<div style="flex:1;height:24px;background:#eef2f7;border-radius:4px;'
            'overflow:hidden;min-width:72px;">'
            f'<div style="height:100%;width:{pct:.1f}%;background:{ce};min-width:2px;"></div>'
            "</div>"
            f'<span style="flex:0 0 2.75em;text-align:right;'
            f'font-variant-numeric:tabular-nums;">{v}</span>'
            "</div>"
        )
    parts.append("</div>")
    return "\n".join(parts)


def generate_report_body(state: dict) -> str:
    ops = _ops(state)
    fail = _failure(state)

    sections: list[str] = [
        "# Customer Support Analysis Report",
        "",
        "> Snapshot of performance, failure patterns, and improvement opportunities.",
        "",
        "---",
        "",
    ]

    kpi_cards, stage_counts, _ = _summary_kpis_and_stages(ops, fail)

    sections.append("## Summary")
    sections.append("")
    sections.append("> High-level view of system performance and outcomes.")
    sections.append("")
    sections.append(_executive_summary_md(kpi_cards, stage_counts))
    sections.append("")
    sections.append("---")
    sections.append("")

    if "error" not in ops:
        sections.append("## Operational Metrics")
        sections.append("")
        sections.append("> Core KPIs for this analysis run.")
        sections.append("")
        om = ops.get("outcome_kpis")
        if isinstance(om, dict) and om:
            sections.append("### Outcome KPIs")
            sections.append("")
            sections.append(_md_table_rows(_outcome_kpis_table_rows(om)))
            sections.append("")

    sections.append("---")
    sections.append("")

    sections.append("## Failure Analysis")
    sections.append("")
    sections.append("> Where and why conversations fail.")
    sections.append("")

    if "error" in fail:
        sections.append(f"*Error loading failure metrics: {fail['error']}*")
        sections.append("")
    else:
        tt = fail.get("total_transcripts")
        tw = fail.get("transcripts_with_failure_reasons")
        if tt is not None or tw is not None:
            sections.append(
                f"- Transcripts in scope: {tt if tt is not None else '—'}"
            )
            sections.append(
                f"- With failure reasons recorded: {tw if tw is not None else '—'}"
            )
            sections.append("")

        sections.append("### Failure reasons by category")
        sections.append("")
        sections.append(_failure_reasons_by_category_html(fail))

        fc: dict[str, int] = {}
        raw_fc = fail.get("failure_reason_mentions_by_category")
        if isinstance(raw_fc, dict):
            fc = {str(k): int(v) for k, v in raw_fc.items() if int(v or 0) > 0}

        sections.append("### Mentions by category (chart)")
        sections.append("")
        if fc:
            top = sorted(fc.items(), key=lambda x: (-x[1], x[0]))[:10]
            labels = [t[0] for t in top]
            vals = [t[1] for t in top]
            sections.append(
                _failure_category_bars_html(
                    "Failure mentions by category", labels, vals
                )
            )
        else:
            sections.append("*No failure category data.*")
        sections.append("")

    sections.append("---")
    sections.append("")
    sections.append("_Generated automatically by the support analysis system._")
    return "\n".join(sections)
