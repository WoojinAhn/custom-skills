#!/usr/bin/env python3
"""Validate a rendered trend briefing without network access."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlparse


PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
UNSAFE_SCHEMES = {"data", "javascript", "vbscript"}
BLOCKED_TAGS = {
    "audio",
    "base",
    "embed",
    "form",
    "foreignobject",
    "iframe",
    "img",
    "object",
    "script",
    "source",
    "track",
    "video",
}
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
ALLOWED_LINK_HOSTS = {
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
}
RESOURCE_ATTRIBUTES = {"action", "formaction", "poster", "src", "srcset"}
CSS_URL_RE = re.compile(r"url\s*\(([^)]*)\)", re.IGNORECASE)


@dataclass
class CaptureRegion:
    kind: str
    depth: int
    parts: list[str] = field(default_factory=list)


def has_unsafe_css(css: str) -> bool:
    lowered = css.lower()
    if "@import" in lowered or re.search(r"expression\s*\(", css, re.IGNORECASE):
        return True
    for match in CSS_URL_RE.finditer(css):
        target = match.group(1).strip().strip("'\"").strip()
        if not target.startswith("#"):
            return True
    return False


class BriefingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.links: list[str | None] = []
        self.blocked_tags: set[str] = set()
        self.event_handlers: set[str] = set()
        self.attribute_errors: list[str] = []
        self.structure_errors: list[str] = []
        self.style_parts: list[str] = []
        self.tag_stack: list[str] = []
        self.active_regions: list[CaptureRegion] = []
        self.position_texts: dict[str, list[str]] = {"a": [], "b": []}
        self.summary_texts: list[str] = []
        self._capture_tag: str | None = None
        self._capture_parts: list[str] = []
        self.text_by_tag: dict[str, list[str]] = {"title": [], "h1": []}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attr_map = dict(attrs)
        if tag in BLOCKED_TAGS:
            self.blocked_tags.add(tag)

        for name, value in attrs:
            normalized_name = name.lower()
            if normalized_name.startswith("on"):
                self.event_handlers.add(normalized_name)
            if normalized_name in RESOURCE_ATTRIBUTES:
                self.attribute_errors.append(f"{tag}[{normalized_name}]")
            if normalized_name in {"href", "xlink:href"} and tag not in {
                "a",
                "link",
            }:
                self.attribute_errors.append(f"{tag}[{normalized_name}]")
            if normalized_name == "style" and value and has_unsafe_css(value):
                self.attribute_errors.append(f"{tag}[style]")

        if tag == "meta" and "http-equiv" in attr_map:
            self.attribute_errors.append("meta[http-equiv]")
        if tag == "html":
            self.lang = attr_map.get("lang") or ""
        elif tag == "a":
            self.links.append(attr_map.get("href"))
        elif tag == "link":
            self._validate_link_tag(attr_map)

        if tag not in VOID_TAGS:
            self.tag_stack.append(tag)

        classes = set((attr_map.get("class") or "").split())
        if tag == "div" and "pos" in classes:
            kinds = classes & {"a", "b"}
            if len(kinds) != 1:
                self.structure_errors.append(
                    "each position card must identify exactly one of A or B"
                )
            else:
                self.active_regions.append(
                    CaptureRegion(kind=next(iter(kinds)), depth=len(self.tag_stack))
                )
        if tag == "div" and "summary" in classes:
            self.active_regions.append(
                CaptureRegion(kind="summary", depth=len(self.tag_stack))
            )

        if tag in self.text_by_tag:
            self._capture_tag = tag
            self._capture_parts = []

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._capture_tag:
            self._capture_parts.append(data)
        for region in self.active_regions:
            region.parts.append(data)
        if self.tag_stack and self.tag_stack[-1] == "style":
            self.style_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._capture_tag:
            value = "".join(self._capture_parts).strip()
            self.text_by_tag[tag].append(value)
            self._capture_tag = None
            self._capture_parts = []

        depth = len(self.tag_stack)
        closing_regions = [
            region
            for region in self.active_regions
            if tag == "div" and region.depth == depth
        ]
        for region in closing_regions:
            value = " ".join("".join(region.parts).split())
            if region.kind == "summary":
                self.summary_texts.append(value)
            else:
                self.position_texts[region.kind].append(value)
            self.active_regions.remove(region)

        if tag in VOID_TAGS:
            self.structure_errors.append(f"void tag must not be closed: {tag}")
        elif not self.tag_stack:
            self.structure_errors.append(f"unexpected closing tag: {tag}")
        elif self.tag_stack[-1] != tag:
            self.structure_errors.append(
                f"mismatched closing tag: expected {self.tag_stack[-1]}, got {tag}"
            )
            if tag in self.tag_stack:
                while self.tag_stack and self.tag_stack[-1] != tag:
                    self.tag_stack.pop()
                self.tag_stack.pop()
        else:
            self.tag_stack.pop()

    def close(self) -> None:
        super().close()
        if self.tag_stack:
            self.structure_errors.append(
                f"unclosed tags: {', '.join(self.tag_stack)}"
            )

    def _validate_link_tag(self, attrs: dict[str, str | None]) -> None:
        href = (attrs.get("href") or "").strip()
        rel = set((attrs.get("rel") or "").lower().split())
        if "icon" in rel and href == "data:,":
            return
        parsed = urlparse(href)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or (parsed.hostname or "").lower() not in ALLOWED_LINK_HOSTS
        ):
            self.attribute_errors.append("link[href]")


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        html = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read UTF-8 HTML: {exc}"]

    placeholders = sorted(set(PLACEHOLDER_RE.findall(html)))
    if placeholders:
        preview = ", ".join(placeholders[:8])
        suffix = " ..." if len(placeholders) > 8 else ""
        errors.append(f"unresolved placeholders: {preview}{suffix}")

    parser = BriefingParser()
    parser.feed(html)
    parser.close()

    if parser.lang != "ko":
        errors.append('expected <html lang="ko">')
    if not any(parser.text_by_tag["title"]):
        errors.append("missing non-empty <title>")
    if not any(parser.text_by_tag["h1"]):
        errors.append("missing non-empty <h1>")
    for kind in ("a", "b"):
        if not any(parser.position_texts[kind]):
            errors.append(f"missing non-empty position {kind.upper()} card")
    if not any(parser.summary_texts):
        errors.append("missing non-empty final summary block")
    if parser.blocked_tags:
        errors.append(f"blocked HTML tags: {', '.join(sorted(parser.blocked_tags))}")
    if parser.event_handlers:
        errors.append(
            f"inline event handlers: {', '.join(sorted(parser.event_handlers))}"
        )
    if parser.attribute_errors:
        errors.append(
            f"unsafe resource attributes: {', '.join(sorted(set(parser.attribute_errors)))}"
        )
    if parser.structure_errors:
        errors.extend(parser.structure_errors)
    if has_unsafe_css("".join(parser.style_parts)):
        errors.append("embedded CSS may not import or request external resources")

    for index, href in enumerate(parser.links, start=1):
        if not href or not href.strip():
            errors.append(f"link {index} has an empty href")
            continue
        parsed = urlparse(href.strip())
        scheme = parsed.scheme.lower()
        if scheme in UNSAFE_SCHEMES:
            errors.append(f"link {index} uses unsafe scheme: {parsed.scheme}")
        elif scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"link {index} must use an absolute HTTP(S) URL")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a completed trend-briefing HTML file."
    )
    parser.add_argument("html_file", type=Path)
    args = parser.parse_args()

    errors = validate(args.html_file)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"PASS: {args.html_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
