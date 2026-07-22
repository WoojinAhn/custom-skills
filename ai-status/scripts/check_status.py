#!/usr/bin/env python3
"""Fetch AI provider status from machine-readable JSON APIs in parallel."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

USER_AGENT = "ai-status-skill/1.0 (+cursor-skill)"
TIMEOUT_SEC = 12
AIWATCH_TIMEOUT_SEC = 5
AIWATCH_CACHED_URL = (
    "https://aiwatch-worker.p2c2kbf.workers.dev/api/status/cached?src=ai-status-skill"
)

# Worst status wins when aggregating components.
STATUS_RANK = {
    "operational": 0,
    "degraded": 1,
    "partial_outage": 2,
    "major_outage": 3,
    "unknown": 4,
}

STATUSPAGE_INDICATOR = {
    "none": "operational",
    "minor": "degraded",
    "major": "major_outage",
    "critical": "major_outage",
}

STATUSPAGE_COMPONENT = {
    "operational": "operational",
    "degraded_performance": "degraded",
    "partial_outage": "partial_outage",
    "major_outage": "major_outage",
    "under_maintenance": "degraded",
}

GOOGLE_IMPACT = {
    "AVAILABLE": "operational",
    "SERVICE_INFORMATION": "operational",
    "SERVICE_DISRUPTION": "partial_outage",
    "SERVICE_OUTAGE": "major_outage",
}

GEMINI_PRODUCT_ID = "npdyhgECDJ6tB66MxXyo"

PROVIDERS: dict[str, dict[str, Any]] = {
    "claude": {
        "label": "Claude (Anthropic)",
        "type": "statuspage",
        "url": "https://status.claude.com/api/v2/summary.json",
        "status_url": "https://status.claude.com",
        "component_filter": None,
    },
    "openai": {
        "label": "OpenAI (ChatGPT / API / Codex)",
        "type": "statuspage",
        "url": "https://status.openai.com/api/v2/summary.json",
        "status_url": "https://status.openai.com",
        "component_filter": [
            "chatgpt",
            "codex",
            "api",
            "login",
            "app",
            "gpt",
            "responses",
            "realtime",
            "conversations",
        ],
    },
    "cursor": {
        "label": "Cursor (IDE / Agents)",
        "type": "statuspage",
        "url": "https://status.cursor.com/api/v2/summary.json",
        "status_url": "https://status.cursor.com",
        "component_filter": ["ide", "cloud agents", "cli", "automations", "bugbot"],
    },
    "github": {
        "label": "GitHub",
        "type": "statuspage",
        "url": "https://www.githubstatus.com/api/v2/summary.json",
        "status_url": "https://www.githubstatus.com",
        "component_filter": None,
    },
    "gemini_workspace": {
        "label": "Google Gemini (Workspace)",
        "type": "google_workspace",
        "url": "https://www.google.com/appsstatus/dashboard/incidents.json",
        "status_url": "https://www.google.com/appsstatus/dashboard/",
        "product_id": GEMINI_PRODUCT_ID,
    },
    "gemini_vertex": {
        "label": "Google Gemini (Vertex AI)",
        "type": "google_cloud",
        "url": "https://status.cloud.google.com/incidents.json",
        "status_url": "https://status.cloud.google.com",
        "keywords": ["gemini", "vertex ai"],
    },
}

# Extended providers via AIWatch cached API (hybrid fallback).
# See https://github.com/bentleypark/aiwatch — reference only, no code copy (AGPL).
EXTENDED_PROVIDERS: dict[str, dict[str, Any]] = {
    "mistral": {
        "label": "Mistral API",
        "aiwatch_id": "mistral",
        "status_url": "https://status.mistral.ai",
    },
    "xai": {
        "label": "xAI (Grok)",
        "aiwatch_id": "xai",
        "status_url": "https://status.x.ai",
    },
    "deepseek": {
        "label": "DeepSeek API",
        "aiwatch_id": "deepseek",
        "status_url": "https://status.deepseek.com",
    },
    "copilot": {
        "label": "GitHub Copilot",
        "aiwatch_id": "copilot",
        "status_url": "https://www.githubstatus.com",
    },
    "groq": {
        "label": "Groq Cloud",
        "aiwatch_id": "groq",
        "status_url": "https://status.groq.com",
    },
    "perplexity": {
        "label": "Perplexity",
        "aiwatch_id": "perplexity",
        "status_url": "https://status.perplexity.ai",
    },
    "openrouter": {
        "label": "OpenRouter",
        "aiwatch_id": "openrouter",
        "status_url": "https://status.openrouter.ai",
    },
    "windsurf": {
        "label": "Windsurf (Codeium)",
        "aiwatch_id": "windsurf",
        "status_url": "https://status.codeium.com",
    },
    "bedrock": {
        "label": "Amazon Bedrock",
        "aiwatch_id": "bedrock",
        "status_url": "https://health.aws.amazon.com/health/status",
    },
    "cohere": {
        "label": "Cohere API",
        "aiwatch_id": "cohere",
        "status_url": "https://status.cohere.com",
    },
}

AIWATCH_STATUS = {
    "operational": "operational",
    "degraded": "degraded",
    "partial": "partial_outage",
    "partial_outage": "partial_outage",
    "down": "major_outage",
    "major_outage": "major_outage",
    "unknown": "unknown",
}

AIWATCH_IMPACT = {
    "none": "operational",
    "minor": "degraded",
    "major": "partial_outage",
    "critical": "major_outage",
}

STATUSPAGE_IMPACT = {
    "none": "operational",
    "minor": "degraded",
    "major": "partial_outage",
    "critical": "major_outage",
}

OPERATIONAL_INCIDENT_KINDS = frozenset({"operational_outage", "operational_degraded"})

POLICY_COMPLIANCE_RE = re.compile(
    r"(suspend(ed|ing|s)?|export control|directive|government|compliance|"
    r"recall|disabled access|legal directive|foreign national|national security)",
    re.I,
)
SCOPE_LIMITED_RE = re.compile(
    r"(fedramp|specific org|dedicated workspace|workspace.*only|tenant|scoped to)",
    re.I,
)
MODEL_RESTRICTION_RE = re.compile(r"\b(fable|mythos)\b", re.I)

INCIDENT_REFERENCE_URLS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"fable|mythos", re.I),
        "https://www.anthropic.com/news/fable-mythos-access",
    ),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return json.loads(resp.read().decode(charset))


def worst_status(*statuses: str) -> str:
    best = "operational"
    for status in statuses:
        if STATUS_RANK.get(status, 99) > STATUS_RANK.get(best, 0):
            best = status
    return best


def truncate(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def first_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = re.sub(r"[*#_`]", "", line).strip()
        if cleaned:
            return cleaned
    return truncate(text)


def all_components_operational(components: list[dict[str, Any]]) -> bool:
    return bool(components) and all(c.get("status") == "operational" for c in components)


def component_operational_status(components: list[dict[str, Any]]) -> str:
    if not components:
        return "operational"
    return worst_status(*(c.get("status", "unknown") for c in components))


def classify_incident_kind(
    name: str,
    body: str,
    impact: str | None,
    *,
    all_components_operational: bool,
) -> str:
    text = f"{name} {body}"
    if re.search(r"maintenance|under maintenance|scheduled maintenance", text, re.I):
        return "maintenance"
    if POLICY_COMPLIANCE_RE.search(text) or (
        re.search(r"suspend", text, re.I) and MODEL_RESTRICTION_RE.search(text)
    ):
        return "policy_compliance"
    if SCOPE_LIMITED_RE.search(text):
        return "scope_limited"
    if not all_components_operational:
        if impact in ("critical", "major"):
            return "operational_outage"
        return "operational_degraded"
    if impact in ("major", "critical") and MODEL_RESTRICTION_RE.search(text):
        return "policy_compliance"
    if impact in ("minor", "major", "critical") and all_components_operational:
        if "fedramp" in text.lower():
            return "scope_limited"
        if re.search(r"learn more|information|announcement", text, re.I):
            return "informational"
    return "unknown"


def incident_reference_url(name: str, body: str) -> str | None:
    text = f"{name} {body}"
    for pattern, url in INCIDENT_REFERENCE_URLS:
        if pattern.search(text):
            return url
    return None


def enrich_incident(
    raw: dict[str, Any],
    *,
    all_components_operational: bool,
) -> dict[str, Any]:
    name = raw.get("name") or ""
    body = raw.get("latest_update") or ""
    impact = raw.get("impact")
    kind = classify_incident_kind(
        name,
        body,
        impact,
        all_components_operational=all_components_operational,
    )
    enriched: dict[str, Any] = {
        **raw,
        "kind": kind,
    }
    ref = incident_reference_url(name, body)
    if ref:
        enriched["reference_url"] = ref
    if kind == "policy_compliance":
        enriched["impact_scope"] = "product"
        if MODEL_RESTRICTION_RE.search(name):
            enriched["affected_products"] = [
                m.group(0).title() for m in MODEL_RESTRICTION_RE.finditer(name)
            ]
    elif kind == "scope_limited":
        enriched["impact_scope"] = "tenant"
    return enriched


def compute_operational_display(
    page_status: str,
    components: list[dict[str, Any]],
    incidents: list[dict[str, Any]],
) -> tuple[str, str, dict[str, bool], str | None]:
    """Return (display_status, operational_status, alerts, status_reason)."""
    operational_status = (
        component_operational_status(components) if components else page_status
    )
    alerts = {"policy": False, "operational": False, "scope_limited": False}
    status_reason: str | None = None

    for inc in incidents:
        kind = inc.get("kind", "unknown")
        if kind == "policy_compliance":
            alerts["policy"] = True
        elif kind == "scope_limited":
            alerts["scope_limited"] = True
        elif kind in OPERATIONAL_INCIDENT_KINDS:
            alerts["operational"] = True

    if operational_status == "operational":
        display = "operational"
        for inc in incidents:
            if inc.get("kind") in OPERATIONAL_INCIDENT_KINDS:
                display = worst_status(
                    display,
                    STATUSPAGE_IMPACT.get(inc.get("impact"), "degraded"),
                )
                alerts["operational"] = True
        if display == "operational":
            if alerts["policy"]:
                status_reason = "components_all_operational_despite_policy_incident"
            elif alerts["scope_limited"]:
                status_reason = "components_all_operational_despite_scope_limited_incident"
    else:
        display = operational_status
        alerts["operational"] = True
        status_reason = "component_degradation"

    return display, operational_status, alerts, status_reason


def parse_statuspage(data: dict[str, Any], component_filter: list[str] | None) -> dict[str, Any]:
    page_status = STATUSPAGE_INDICATOR.get(
        (data.get("status") or {}).get("indicator", "none"),
        "unknown",
    )

    components_raw = data.get("components") or []
    if component_filter:
        needles = [n.lower() for n in component_filter]
        components_raw = [
            c
            for c in components_raw
            if any(n in (c.get("name") or "").lower() for n in needles)
        ] or components_raw

    components = [
        {
            "name": c.get("name"),
            "status": STATUSPAGE_COMPONENT.get(c.get("status", ""), "unknown"),
            "raw_status": c.get("status"),
        }
        for c in components_raw
    ]

    components_green = all_components_operational(components)

    incidents_raw = []
    for inc in data.get("incidents") or []:
        updates = inc.get("incident_updates") or inc.get("updates") or []
        latest = updates[-1] if updates else {}
        body = latest.get("body") or latest.get("text") or ""
        incidents_raw.append(
            {
                "name": inc.get("name"),
                "status": inc.get("status"),
                "impact": inc.get("impact"),
                "latest_update": truncate(body),
            }
        )

    incidents = [
        enrich_incident(inc, all_components_operational=components_green)
        for inc in incidents_raw
    ]

    display_status, operational_status, alerts, status_reason = compute_operational_display(
        page_status, components, incidents
    )

    degraded = [c for c in components if c["status"] != "operational"]
    summary = (data.get("status") or {}).get("description") or ""
    if not summary and degraded:
        summary = ", ".join(f"{c['name']}: {c['status']}" for c in degraded[:3])
    if display_status == "operational" and alerts["policy"] and not degraded:
        summary = summary or "All tracked components operational"
    if display_status == "operational" and alerts["scope_limited"] and not degraded:
        summary = summary or "Tracked ChatGPT/Codex components operational"

    return {
        "status": display_status,
        "display_status": display_status,
        "operational_status": operational_status,
        "page_status": page_status,
        "status_reason": status_reason,
        "alerts": alerts,
        "summary": summary,
        "components": components,
        "incidents": incidents,
    }


def incident_matches_product(incident: dict[str, Any], product_id: str) -> bool:
    if incident.get("service_key") == product_id:
        return True
    for product in incident.get("affected_products") or []:
        if product.get("id") == product_id:
            return True
    return False


def parse_google_workspace(data: list[dict[str, Any]], product_id: str) -> dict[str, Any]:
    related = [i for i in data if incident_matches_product(i, product_id)]
    active = [i for i in related if not i.get("end")]

    incidents = []
    for inc in active:
        latest = inc.get("most_recent_update") or {}
        text = latest.get("text") or inc.get("external_desc") or ""
        raw_status = latest.get("status") or inc.get("status_impact")
        incidents.append(
            {
                "name": first_line(inc.get("external_desc") or "Gemini incident"),
                "status": raw_status,
                "impact": inc.get("severity"),
                "latest_update": truncate(text),
            }
        )

    if not active:
        return {
            "status": "operational",
            "summary": "No active Gemini Workspace incidents",
            "components": [],
            "incidents": [],
        }

    statuses = [GOOGLE_IMPACT.get(i.get("status_impact", ""), "degraded") for i in active]
    return {
        "status": worst_status(*statuses),
        "summary": first_line(active[0].get("external_desc") or ""),
        "components": [],
        "incidents": incidents,
    }


def parse_google_cloud(data: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any]:
    needles = [k.lower() for k in keywords]
    related = [
        i
        for i in data
        if any(n in json.dumps(i).lower() for n in needles)
    ]
    active = [i for i in related if not i.get("end")]

    incidents = []
    for inc in active:
        updates = inc.get("updates") or []
        latest = updates[-1] if updates else {}
        text = latest.get("text") or inc.get("external_desc") or ""
        incidents.append(
            {
                "name": first_line(inc.get("external_desc") or "Vertex/Gemini incident"),
                "status": latest.get("status") or "investigating",
                "impact": inc.get("severity"),
                "latest_update": truncate(text),
            }
        )

    if not active:
        return {
            "status": "operational",
            "summary": "No active Vertex AI / Gemini incidents",
            "components": [],
            "incidents": [],
        }

    return {
        "status": "partial_outage",
        "summary": first_line(active[0].get("external_desc") or ""),
        "components": [],
        "incidents": incidents,
    }


def check_provider(provider_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    base = {
        "id": provider_id,
        "label": cfg["label"],
        "status_url": cfg.get("status_url"),
        "source": "direct",
        "ok": True,
        "error": None,
    }
    try:
        data = fetch_json(cfg["url"])
        ptype = cfg["type"]
        if ptype == "statuspage":
            parsed = parse_statuspage(data, cfg.get("component_filter"))
        elif ptype == "google_workspace":
            parsed = parse_google_workspace(data, cfg["product_id"])
        elif ptype == "google_cloud":
            parsed = parse_google_cloud(data, cfg.get("keywords") or [])
        else:
            raise ValueError(f"Unknown provider type: {ptype}")
        base.update(parsed)
    except Exception as exc:  # noqa: BLE001 — per-provider isolation
        base.update(
            {
                "ok": False,
                "status": "unknown",
                "summary": "",
                "components": [],
                "incidents": [],
                "error": str(exc),
            }
        )
    return base


def fetch_aiwatch_cache() -> tuple[dict[str, Any], str | None]:
    """Return (services_by_id, cached_at_iso_or_none)."""
    data = fetch_json_with_timeout(AIWATCH_CACHED_URL, AIWATCH_TIMEOUT_SEC)
    services = data.get("services") or []
    by_id = {svc["id"]: svc for svc in services if svc.get("id")}
    cached_at = data.get("cachedAt")
    return by_id, cached_at


def fetch_json_with_timeout(url: str, timeout_sec: int) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return json.loads(resp.read().decode(charset))


def parse_aiwatch_service(service: dict[str, Any]) -> dict[str, Any]:
    raw_status = (service.get("status") or "unknown").lower()
    page_status = AIWATCH_STATUS.get(raw_status, "unknown")

    incidents_raw = []
    for inc in service.get("incidents") or []:
        if inc.get("status") == "resolved":
            continue
        impact = inc.get("impact")
        title = inc.get("title") or inc.get("name") or "Incident"
        incidents_raw.append(
            {
                "name": title,
                "status": inc.get("status"),
                "impact": impact,
                "latest_update": truncate(title, 120),
            }
        )

    components_green = page_status == "operational"
    incidents = [
        enrich_incident(inc, all_components_operational=components_green)
        for inc in incidents_raw
    ]

    display_status, operational_status, alerts, status_reason = compute_operational_display(
        page_status, [], incidents
    )

    summary_parts = []
    if service.get("latency") is not None:
        summary_parts.append(f"latency {service['latency']}ms")
    if service.get("uptime30d") is not None:
        summary_parts.append(f"uptime30d {service['uptime30d']}%")
    if incidents and display_status != "operational":
        summary_parts.insert(0, incidents[0]["name"])
    elif incidents and alerts["policy"]:
        summary_parts.insert(0, "Components operational; policy incident active")
    summary = " · ".join(summary_parts) if summary_parts else raw_status

    return {
        "status": display_status,
        "display_status": display_status,
        "operational_status": operational_status,
        "page_status": page_status,
        "status_reason": status_reason,
        "alerts": alerts,
        "summary": summary,
        "components": [],
        "incidents": incidents,
    }


def check_extended_provider(
    provider_id: str,
    cfg: dict[str, Any],
    aiwatch_by_id: dict[str, Any] | None,
    aiwatch_error: str | None,
) -> dict[str, Any]:
    base = {
        "id": provider_id,
        "label": cfg["label"],
        "status_url": cfg.get("status_url"),
        "source": "aiwatch",
        "ok": True,
        "error": None,
    }
    if aiwatch_error:
        base.update(
            {
                "ok": False,
                "status": "unknown",
                "summary": "",
                "components": [],
                "incidents": [],
                "error": aiwatch_error,
            }
        )
        return base

    service = (aiwatch_by_id or {}).get(cfg["aiwatch_id"])
    if not service:
        base.update(
            {
                "ok": False,
                "status": "unknown",
                "summary": "",
                "components": [],
                "incidents": [],
                "error": f"AIWatch service id not found: {cfg['aiwatch_id']}",
            }
        )
        return base

    base.update(parse_aiwatch_service(service))
    return base


STATUS_EMOJI = {
    "operational": "🟢",
    "degraded": "🟡",
    "partial_outage": "🟠",
    "major_outage": "🔴",
    "unknown": "⚪",
}

STATUS_KO = {
    "operational": "정상",
    "degraded": "저하/경미",
    "partial_outage": "부분 장애",
    "major_outage": "주요 장애",
    "unknown": "확인 불가",
}


def render_human(payload: dict[str, Any]) -> str:
    lines = [f"AI 서비스 상태 ({payload['checked_at']})", ""]
    if payload.get("strategy") == "hybrid":
        cached = (payload.get("aiwatch") or {}).get("cached_at")
        if cached:
            lines.append(f"(확장 provider: AIWatch cached {cached})")
        else:
            lines.append("(확장 provider: AIWatch cached API)")
        lines.append("")

    core_ids = set(PROVIDERS.keys())
    extended_ids = set(EXTENDED_PROVIDERS.keys())

    def render_block(title: str | None, ids: set[str]) -> None:
        block = [(pid, info) for pid, info in payload["providers"].items() if pid in ids]
        if not block:
            return
        if title:
            lines.append(f"## {title}")
            lines.append("")

        policy_lines: list[str] = []
        operational_lines: list[str] = []

        for pid, info in block:
            emoji = STATUS_EMOJI.get(info.get("status", "unknown"), "⚪")
            label = info.get("label", pid)
            status_ko = STATUS_KO.get(info.get("status", "unknown"), "확인 불가")
            source = info.get("source")
            source_tag = " [AIWatch]" if source == "aiwatch" else ""

            if not info.get("ok"):
                lines.append(f"{emoji} **{label}** — 확인 실패 ({info.get('error')}){source_tag}")
                lines.append("")
                continue

            lines.append(f"{emoji} **{label}** — {status_ko}{source_tag}")
            if info.get("summary"):
                lines.append(f"   {info['summary']}")

            degraded = [c for c in info.get("components", []) if c.get("status") != "operational"]
            if degraded:
                comp_text = ", ".join(
                    f"{c['name']} ({STATUS_KO.get(c['status'], c['status'])})" for c in degraded[:5]
                )
                lines.append(f"   영향 컴포넌트: {comp_text}")

            for inc in info.get("incidents", [])[:3]:
                kind = inc.get("kind", "unknown")
                if kind in ("policy_compliance", "scope_limited", "informational"):
                    ref = f" ({inc['reference_url']})" if inc.get("reference_url") else ""
                    policy_lines.append(
                        f"   ⚖ {label}: {inc.get('name')} [{kind}]{ref}"
                    )
                elif info.get("status") != "operational" or kind in OPERATIONAL_INCIDENT_KINDS:
                    operational_lines.append(
                        f"   ⚠ {label}: {inc.get('name')} [{inc.get('status')}]"
                    )
                    if inc.get("latest_update"):
                        operational_lines[-1] += f"\n     → {inc['latest_update']}"

            lines.append("")

        if policy_lines:
            lines.append("## 정책·규제 이슈 (운영 장애 아님)")
            lines.append("")
            lines.extend(policy_lines)
            lines.append("")
        if operational_lines:
            lines.append("## 운영 장애·저하")
            lines.append("")
            lines.extend(operational_lines)
            lines.append("")

    render_block(None if payload.get("strategy") != "hybrid" else "핵심 (공식 API 직접)", core_ids)
    if payload.get("strategy") == "hybrid":
        render_block("확장 (AIWatch)", extended_ids)

    return "\n".join(lines).rstrip() + "\n"


def compact_payload(
    results: dict[str, dict[str, Any]],
    *,
    strategy: str = "direct",
    aiwatch_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "checked_at": utc_now_iso(),
        "strategy": strategy,
        "providers": {
            pid: {
                "label": r["label"],
                "status": r.get("status"),
                "display_status": r.get("display_status", r.get("status")),
                "operational_status": r.get("operational_status", r.get("status")),
                "page_status": r.get("page_status"),
                "status_reason": r.get("status_reason"),
                "alerts": r.get("alerts"),
                "summary": r.get("summary"),
                "ok": r.get("ok"),
                "error": r.get("error"),
                "source": r.get("source", "direct"),
                "status_url": r.get("status_url"),
                "components": r.get("components", []),
                "incidents": r.get("incidents", []),
            }
            for pid, r in results.items()
        },
    }
    if aiwatch_meta is not None:
        payload["aiwatch"] = aiwatch_meta
    return payload


def all_provider_ids(extended: bool) -> list[str]:
    ids = list(PROVIDERS.keys())
    if extended:
        ids.extend(EXTENDED_PROVIDERS.keys())
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AI provider status via JSON APIs")
    parser.add_argument(
        "--providers",
        nargs="*",
        default=None,
        help="Provider ids (default: all core, or all core+extended with --extended)",
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Include extended providers via AIWatch cached API (Mistral, xAI, Copilot, …)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "human", "both"],
        default="both",
        help="Output format (default: both)",
    )
    args = parser.parse_args()

    available = all_provider_ids(args.extended)
    selected = args.providers or available
    unknown = [p for p in selected if p not in available]
    if unknown:
        print(f"Unknown providers: {', '.join(unknown)}", file=sys.stderr)
        print(f"Available: {', '.join(available)}", file=sys.stderr)
        if not args.extended and any(p in EXTENDED_PROVIDERS for p in selected):
            print("Hint: extended providers require --extended", file=sys.stderr)
        return 2

    core_selected = [p for p in selected if p in PROVIDERS]
    extended_selected = [p for p in selected if p in EXTENDED_PROVIDERS]

    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(core_selected)))) as pool:
        futures = {
            pool.submit(check_provider, pid, PROVIDERS[pid]): pid for pid in core_selected
        }
        for future in as_completed(futures):
            pid = futures[future]
            results[pid] = future.result()

    aiwatch_meta: dict[str, Any] | None = None
    if extended_selected:
        aiwatch_by_id: dict[str, Any] | None = None
        aiwatch_error: str | None = None
        try:
            aiwatch_by_id, cached_at = fetch_aiwatch_cache()
            aiwatch_meta = {"ok": True, "cached_at": cached_at, "url": AIWATCH_CACHED_URL}
        except Exception as exc:  # noqa: BLE001
            aiwatch_error = str(exc)
            aiwatch_meta = {"ok": False, "error": aiwatch_error, "url": AIWATCH_CACHED_URL}

        for pid in extended_selected:
            results[pid] = check_extended_provider(
                pid,
                EXTENDED_PROVIDERS[pid],
                aiwatch_by_id,
                aiwatch_error,
            )

    strategy = "hybrid" if extended_selected else "direct"
    payload = compact_payload(results, strategy=strategy, aiwatch_meta=aiwatch_meta)

    if args.format in ("human", "both"):
        human = render_human(payload)
        if args.format == "both":
            print(human, end="")
        else:
            print(human, end="")

    if args.format in ("json", "both"):
        json_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if args.format == "both":
            print(json_text, file=sys.stderr)
        else:
            print(json_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
