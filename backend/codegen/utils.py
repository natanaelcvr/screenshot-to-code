import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompts.prompt_types import Stack

# Stacks whose generated content is not HTML, so the <html>/<file> extraction
# below doesn't apply and its "no <html> tags found" warning is just noise.
NON_HTML_STACKS = frozenset({"flutter"})


def extract_code_content(text: str, stack: "Stack") -> str:
    """Extract the primary generated code from a model response.

    Dispatches to `extract_html_content` for HTML-based stacks (the six
    existing stacks, all single-file HTML), and returns the text unchanged
    for non-HTML stacks (e.g. Flutter/Dart) — their content has no <html>
    tags to find, and running that extraction would only print a confusing
    "No <html> tags found" warning on every create_file/edit_file call.
    """
    if stack in NON_HTML_STACKS:
        return text
    return extract_html_content(text)


def extract_html_content(text: str) -> str:
    file_match = re.search(
        r"<file\s+path=\"[^\"]+\">\s*(.*?)\s*</file>",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if file_match:
        return extract_html_content(file_match.group(1).strip())

    # First, strip markdown code fences if present
    text = re.sub(r'^```html?\s*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)

    # Try to find DOCTYPE + html tags together
    match_with_doctype = re.search(
        r"(<!DOCTYPE\s+html[^>]*>.*?<html.*?>.*?</html>)", text, re.DOTALL | re.IGNORECASE
    )
    if match_with_doctype:
        return match_with_doctype.group(1)

    # Fall back to just <html> tags
    match = re.search(r"(<html.*?>.*?</html>)", text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        # Otherwise, we just send the previous HTML over
        print(
            "[HTML Extraction] No <html> tags found in the generated content"
        )
        return text
