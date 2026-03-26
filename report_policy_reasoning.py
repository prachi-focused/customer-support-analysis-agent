"""LLM agent with optional policy retrieval tool for grounded recommendations."""

from __future__ import annotations

import json
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from node_2_policy_update import search_policy_context

load_dotenv()

_DEFAULT_MODEL = "gpt-4o-mini"
_MAX_TOOL_ROUNDS = 10

_POLICY_REASONING_SYSTEM = """You are an internal support operations analyst for a movie theater chain.
You receive quantitative metrics from a transcript analysis run (JSON below). Your job is to produce policy-grounded recommendations as Markdown.

## Tool: search_policy_chunks

You have access to **search_policy_chunks**, which searches the organization's **ingested policy documents** in the vector store (semantic search).

**When to use it**
- Call it when you need **actual policy text** to ground recommendations, cite rules, or verify what is officially allowed (refunds, escalations, chatbot vs human scope, etc.).
- You may call it **zero times** if metrics alone are enough for a short summary—but for "policy-grounded" reasoning you should usually retrieve at least one relevant query.
- You may call it **multiple times** with **different queries** if the first results are insufficient or you need another topic (e.g. one query for refunds, another for escalation).

**How to use it**
- **query** (required): A short natural-language search string. Be specific (e.g. "customer refund before showtime", "when to escalate to supervisor", "chatbot limitations").
- **k** (optional, default 8): Number of chunks to return (roughly 4–12 is reasonable).

**After each tool result**
- Read the returned excerpts. Use them to support or qualify your recommendations. Cite document name and section when you reference policy.
- If excerpts are empty or irrelevant, try a **different query** or state clearly that policy was not found for that topic.

## Output rules

1. Tie main issues in the metrics to patterns (resolution stages, failure categories, top failure reasons).
2. Propose concrete improvements **grounded in retrieved policy** when excerpts support them; label general advice as non-policy when policy does not cover it.
3. Output valid **Markdown**: ### subsections, bullets, **bold**. Aim for roughly 400–800 words unless data is very sparse.
4. Do **not** invent exact policy quotes; only paraphrase or quote what appears in tool results.
5. When you are done retrieving policy (or choosing not to), write your **final Markdown answer** in the assistant message **without** further tool calls."""


def _metrics_payload(ops: dict[str, Any], fail: dict[str, Any]) -> dict[str, Any]:
    """Stable JSON-serializable snapshot for the prompt."""
    out: dict[str, Any] = {}
    if isinstance(ops, dict) and "error" not in ops:
        out["operations_metrics"] = {k: v for k, v in ops.items() if k != "error"}
    elif isinstance(ops, dict) and ops.get("error"):
        out["operations_metrics_error"] = str(ops.get("error"))
    if isinstance(fail, dict) and "error" not in fail:
        out["failure_metrics"] = {k: v for k, v in fail.items() if k != "error"}
    elif isinstance(fail, dict) and fail.get("error"):
        out["failure_metrics_error"] = str(fail.get("error"))
    return out


def _format_chunks_for_prompt(chunks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        doc = ch.get("document_name") or "unknown"
        sec = ch.get("section_heading") or ""
        content = (ch.get("content") or "").strip()
        head = f"### Excerpt {i}: {doc}"
        if sec:
            head += f" — {sec}"
        lines.append(head)
        lines.append(content)
        lines.append("")
    return "\n".join(lines).strip()


def _make_search_policy_tool(default_k: int):
    """Build tool so default chunk count matches caller's ``k_chunks``."""

    @tool
    def search_policy_chunks(query: str, k: int = default_k) -> str:
        """Search ingested policy documents (vector store) for excerpts relevant to your question.

        Use a focused natural-language query. Returns top matching chunks with document name,
        section heading, and text. Call again with a different query if results are empty or off-topic.
        """
        if not (query or "").strip():
            return "Error: query must be a non-empty string."
        k_eff = max(1, min(int(k), 24))
        try:
            chunks = search_policy_context(query.strip(), k=k_eff)
        except Exception as e:
            return (
                f"Policy search failed: {e}. "
                "Ensure Postgres is running, policy_chunks is populated, and policies were ingested."
            )
        if not chunks:
            return (
                "No policy chunks matched this query. Try different keywords, or confirm policies "
                "were ingested (policy update node / assets/policies/*.txt)."
            )
        return _format_chunks_for_prompt(chunks)

    return search_policy_chunks


def _tool_map(tool_obj: Any) -> dict[str, Any]:
    return {tool_obj.name: tool_obj}


def _run_tool_calls(ai: AIMessage, tools_by_name: dict[str, Any]) -> list[ToolMessage]:
    out: list[ToolMessage] = []
    for tc in ai.tool_calls or []:
        name = tc["name"]
        tid = tc["id"]
        args = tc.get("args") or {}
        tool_fn = tools_by_name.get(name)
        if tool_fn is None:
            body = f"Unknown tool: {name}"
        else:
            try:
                body = tool_fn.invoke(args)
            except Exception as e:
                body = f"Tool error: {e}"
        if not isinstance(body, str):
            body = json.dumps(body, default=str)
        out.append(ToolMessage(content=body, tool_call_id=tid))
    return out


def _final_text(msg: AIMessage) -> str:
    c = msg.content
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        parts: list[str] = []
        for block in c:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(parts).strip()
    return str(c or "").strip()


def generate_policy_reasoning_markdown(
    ops: dict[str, Any],
    fail: dict[str, Any],
    *,
    k_chunks: int = 8,
    model_name: str | None = None,
) -> str:
    """
    Agent with search_policy_chunks tool: model decides when/how to retrieve policy, then writes Markdown.
    ``k_chunks`` is the default ``k`` in the tool schema; the model may pass a different ``k`` per call.
    """
    payload = _metrics_payload(ops, fail)
    if not payload:
        return "*No operations or failure metrics available for policy-grounded analysis.*\n"

    metrics_json = json.dumps(payload, indent=2, default=str)
    search_tool = _make_search_policy_tool(k_chunks)
    tools = [search_tool]
    tools_by_name = _tool_map(search_tool)

    model = ChatOpenAI(
        model=model_name or _DEFAULT_MODEL,
        temperature=0,
    ).bind_tools(tools)
    # creating an Agent will loop and reason more.

    messages: list[BaseMessage] = [
        SystemMessage(content=_POLICY_REASONING_SYSTEM),
        HumanMessage(
            content=(
                "## Metrics (JSON)\n\n"
                f"```json\n{metrics_json}\n```\n\n"
                "Use the search_policy_chunks tool as needed, then respond with your final "
                "Markdown analysis and recommendations only in your last assistant message "
                "(after you finish tool use)."
            )
        ),
    ]

    try:
        for _ in range(_MAX_TOOL_ROUNDS):
            ai = model.invoke(messages)
            if not isinstance(ai, AIMessage):
                return "*Unexpected response type from the model.*\n"
            messages.append(ai)

            if not ai.tool_calls:
                text = _final_text(ai)
                if not text:
                    return "*The model returned empty text for policy-grounded recommendations.*\n"
                return text + "\n"

            messages.extend(_run_tool_calls(ai, tools_by_name))

        return "*Stopped: maximum tool rounds exceeded. Try simplifying metrics or increasing _MAX_TOOL_ROUNDS.*\n"
    except Exception as e:
        return f"*Policy-grounded agent failed: {e}*\n"
