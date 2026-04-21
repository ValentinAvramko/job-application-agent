from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourceChannelRule:
    contains: str
    channel: str


@dataclass(frozen=True)
class ResponseMethodRule:
    contains: str
    method: str


@dataclass(frozen=True)
class SourceChannelConfig:
    manual_channel: str
    website_channel: str
    default_response_method: str
    host_channel_rules: tuple[SourceChannelRule, ...]
    company_site_host_tokens: tuple[str, ...]
    company_site_path_tokens: tuple[str, ...]
    response_method_by_channel: dict[str, str]
    response_method_host_rules: tuple[ResponseMethodRule, ...]


@lru_cache(maxsize=1)
def load_source_channel_config() -> SourceChannelConfig:
    payload = json.loads(resources.files("application_agent.data").joinpath("source_channels.json").read_text(encoding="utf-8"))
    defaults = payload["defaults"]
    return SourceChannelConfig(
        manual_channel=str(defaults["manual"]),
        website_channel=str(defaults["website"]),
        default_response_method=str(defaults["response_method"]),
        host_channel_rules=tuple(
            SourceChannelRule(contains=str(item["contains"]).lower(), channel=str(item["channel"]))
            for item in payload.get("host_channel_rules", [])
        ),
        company_site_host_tokens=tuple(str(item).lower() for item in payload.get("company_site_host_tokens", [])),
        company_site_path_tokens=tuple(str(item).lower() for item in payload.get("company_site_path_tokens", [])),
        response_method_by_channel={
            str(key).lower(): str(value) for key, value in payload.get("response_method_by_channel", {}).items()
        },
        response_method_host_rules=tuple(
            ResponseMethodRule(contains=str(item["contains"]).lower(), method=str(item["method"]))
            for item in payload.get("response_method_host_rules", [])
        ),
    )


SOURCE_CHANNEL_CONFIG = load_source_channel_config()


def infer_source_channel(source_url: str, source_text: str, explicit: str = "") -> str:
    if explicit.strip():
        return explicit.strip()
    url = source_url.strip()
    if not url:
        return SOURCE_CHANNEL_CONFIG.manual_channel
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if host.startswith("www."):
        host = host[4:]
    for rule in SOURCE_CHANNEL_CONFIG.host_channel_rules:
        if rule.contains in host:
            return rule.channel
    if any(token in host for token in SOURCE_CHANNEL_CONFIG.company_site_host_tokens):
        return "Company Site"
    if any(token in path for token in SOURCE_CHANNEL_CONFIG.company_site_path_tokens):
        return "Company Site"
    if source_text.strip():
        return SOURCE_CHANNEL_CONFIG.website_channel
    return SOURCE_CHANNEL_CONFIG.website_channel


def normalize_response_method(source_channel: str, source_url: str) -> str:
    normalized_channel = source_channel.strip().lower()
    if normalized_channel in SOURCE_CHANNEL_CONFIG.response_method_by_channel:
        return SOURCE_CHANNEL_CONFIG.response_method_by_channel[normalized_channel]

    host = source_url.strip().lower()
    for rule in SOURCE_CHANNEL_CONFIG.response_method_host_rules:
        if rule.contains in host:
            return rule.method
    if any(token in host for token in SOURCE_CHANNEL_CONFIG.company_site_host_tokens):
        return SOURCE_CHANNEL_CONFIG.response_method_by_channel.get("company site", "Сайт компании")
    return SOURCE_CHANNEL_CONFIG.default_response_method
