import pytest

from codegen.utils import extract_code_content, extract_html_content


def test_extract_html_content_from_wrapped_file_tag() -> None:
    text = '<file path="index.html">\n<html><body><p>Hello</p></body></html>\n</file>'

    result = extract_html_content(text)

    assert result == "<html><body><p>Hello</p></body></html>"


def test_extract_code_content_runs_html_extraction_for_html_stacks() -> None:
    text = '<file path="index.html">\n<html><body><p>Hello</p></body></html>\n</file>'

    result = extract_code_content(text, "html_tailwind")

    assert result == "<html><body><p>Hello</p></body></html>"


def test_extract_code_content_skips_html_extraction_for_flutter(
    capsys: pytest.CaptureFixture[str],
) -> None:
    text = "import 'package:flutter/material.dart';\n\nvoid main() {}\n"

    result = extract_code_content(text, "flutter")

    # Dart source has no <html> tags; extraction must be a no-op and must
    # not print the HTML-extraction "no tags found" warning for this stack.
    assert result == text
    captured = capsys.readouterr()
    assert "HTML Extraction" not in captured.out
