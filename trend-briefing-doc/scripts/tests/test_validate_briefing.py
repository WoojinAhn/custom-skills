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
