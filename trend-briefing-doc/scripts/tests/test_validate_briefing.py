from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from validate_briefing import validate  # noqa: E402


VALID_HTML = """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8" /><title>검증 문서</title></head>
<body>
  <h1>검증 문서</h1>
  <div class="pos a"><h2>관점 A</h2><p>근거 A</p></div>
  <div class="pos b"><h2>관점 B</h2><p>근거 B</p></div>
  <a href="https://example.com/source">출처</a>
  <div class="summary"><p>한 줄 정리</p></div>
</body>
</html>
"""

EVIDENCE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8" /><title>근거 브리핑</title></head>
<body data-briefing-mode="evidence">
  <h1>근거 브리핑</h1>
  <div class="pos facts"><p>확인한 사실</p></div>
  <div class="pos implications"><p>실무적 의미</p></div>
  <div class="pos uncertainties"><p>아직 모르는 점</p></div>
  <a href="https://example.com/source">출처</a>
  <div class="summary"><p>한 줄 정리</p></div>
</body>
</html>
"""


class ValidateBriefingTest(unittest.TestCase):
    def validate_html(self, html: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "briefing.html"
            path.write_text(html, encoding="utf-8")
            return validate(path)

    def assert_rejected(self, html: str, expected: str) -> None:
        errors = self.validate_html(html)
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected {expected!r} in {errors!r}",
        )

    def test_accepts_valid_static_report(self) -> None:
        self.assertEqual(self.validate_html(VALID_HTML), [])

    def test_accepts_explicit_comparison_mode(self) -> None:
        html = VALID_HTML.replace("<body>", '<body data-briefing-mode="comparison">')
        self.assertEqual(self.validate_html(html), [])

    def test_accepts_evidence_mode_without_comparison_cards(self) -> None:
        self.assertEqual(self.validate_html(EVIDENCE_HTML), [])

    def test_rejects_missing_or_empty_evidence_sections(self) -> None:
        for kind, text in (
            ("facts", "확인한 사실"),
            ("implications", "실무적 의미"),
            ("uncertainties", "아직 모르는 점"),
        ):
            card = f'<div class="pos {kind}"><p>{text}</p></div>'
            for replacement in ("", f'<div class="pos {kind}"><p> </p></div>'):
                with self.subTest(kind=kind, replacement=replacement):
                    self.assertTrue(self.validate_html(EVIDENCE_HTML.replace(card, replacement)))

    def test_rejects_unknown_or_empty_explicit_mode(self) -> None:
        for mode in ("timeline", "", "Evidence"):
            with self.subTest(mode=mode):
                html = VALID_HTML.replace("<body>", f'<body data-briefing-mode="{mode}">')
                self.assertTrue(self.validate_html(html))

    def test_rejects_mixed_or_inactive_card_kinds(self) -> None:
        for original, replacement, report in (
            ('class="pos facts"', 'class="pos facts implications"', EVIDENCE_HTML),
            ('class="pos facts"', 'class="pos facts a"', EVIDENCE_HTML),
            ('class="pos facts"', 'class="pos a"', EVIDENCE_HTML),
            ('class="pos a"', 'class="pos a facts"', VALID_HTML),
        ):
            with self.subTest(replacement=replacement):
                self.assertTrue(self.validate_html(report.replace(original, replacement)))

    def test_requires_source_anchor_not_just_font_links(self) -> None:
        source = '<a href="https://example.com/source">출처</a>'
        for replacement in (
            "",
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono" />',
            '<link rel="preconnect" href="https://fonts.gstatic.com" />',
        ):
            for report in (VALID_HTML, EVIDENCE_HTML):
                with self.subTest(replacement=replacement, evidence=report == EVIDENCE_HTML):
                    self.assertTrue(self.validate_html(report.replace(source, replacement)))

    def test_rejects_invalid_source_anchors(self) -> None:
        for href in (
            "",
            "#source",
            "/source",
            "https:///source",
            "https://:443/source",
            "mailto:author@example.com",
            "javascript:alert(1)",
        ):
            with self.subTest(href=href):
                html = VALID_HTML.replace('href="https://example.com/source"', f'href="{href}"')
                self.assertTrue(self.validate_html(html))

    def test_accepts_http_source_anchor(self) -> None:
        html = EVIDENCE_HTML.replace("https://example.com/source", "http://example.com/source")
        self.assertEqual(self.validate_html(html), [])

    def test_allows_local_svg_fragment_in_css(self) -> None:
        html = VALID_HTML.replace(
            "</body>", '<svg><path style="marker-end:url(#arrow)" /></svg></body>'
        )
        self.assertEqual(self.validate_html(html), [])

    def test_rejects_placeholder(self) -> None:
        self.assert_rejected(VALID_HTML.replace("검증 문서", "{{TITLE}}", 1), "placeholder")

    def test_rejects_script_and_event_handler(self) -> None:
        html = VALID_HTML.replace(
            "<body>", '<body onload="alert(1)"><script>alert(1)</script>'
        )
        self.assert_rejected(html, "blocked HTML tags")
        self.assert_rejected(html, "inline event handlers")

    def test_rejects_non_anchor_resource_url(self) -> None:
        html = VALID_HTML.replace(
            "</body>", '<img src="javascript:alert(1)" /></body>'
        )
        self.assert_rejected(html, "unsafe resource attributes")

    def test_rejects_meta_refresh(self) -> None:
        html = VALID_HTML.replace(
            "<head>", '<head><meta http-equiv="refresh" content="0;url=https://evil.invalid" />'
        )
        self.assert_rejected(html, "meta[http-equiv]")

    def test_rejects_unapproved_stylesheet(self) -> None:
        html = VALID_HTML.replace(
            "</head>", '<link rel="stylesheet" href="https://evil.invalid/x.css" /></head>'
        )
        self.assert_rejected(html, "link[href]")

    def test_rejects_external_css_request(self) -> None:
        html = VALID_HTML.replace(
            "</head>", "<style>body{background:url(https://evil.invalid/x)}</style></head>"
        )
        self.assert_rejected(html, "embedded CSS")

    def test_rejects_unclosed_html(self) -> None:
        self.assert_rejected(
            VALID_HTML.replace("</body>\n</html>", ""), "unclosed tags"
        )

    def test_rejects_combined_position_card(self) -> None:
        html = VALID_HTML.replace(
            '<div class="pos a"><h2>관점 A</h2><p>근거 A</p></div>\n'
            '  <div class="pos b"><h2>관점 B</h2><p>근거 B</p></div>',
            '<div class="pos a b"><p>겸용 카드</p></div>',
        )
        self.assert_rejected(html, "exactly one of A or B")

    def test_rejects_empty_position_or_summary(self) -> None:
        self.assert_rejected(
            VALID_HTML.replace("<h2>관점 B</h2><p>근거 B</p>", ""),
            "non-empty position B",
        )
        self.assert_rejected(
            VALID_HTML.replace("<p>한 줄 정리</p>", ""),
            "non-empty final summary",
        )


if __name__ == "__main__":
    unittest.main()
