# pyright: reportUnknownVariableType=false
from dataclasses import dataclass, field
from typing import Any, Dict, List

from openai.types.chat import ChatCompletionMessageParam

from codegen.utils import extract_html_content


@dataclass
class AgentFileState:
    """The agent's view of the files it has written so far.

    `path`/`content` are the original (and still the only) fields that the
    six HTML-based stacks use: one file, always kept up to date as "the"
    current file. They are real dataclass fields (not derived), so every
    existing caller that reads/writes them directly keeps working exactly
    as before — this is a pure addition, not a refactor of the old shape.

    `files` is the multi-file store used only by the Flutter stack (a real
    `pubspec.yaml` + `lib/**` project): a path -> content map covering every
    file written so far (scaffold + agent edits). For Flutter, `path`/
    `content` still get updated on every create_file/edit_file call, but
    only to mirror whichever file was most recently touched — enough for
    today's single-file code preview stream — while `files` remains the
    source of truth for the full project tree.
    """

    path: str = "index.html"
    content: str = ""
    files: Dict[str, str] = field(default_factory=dict)


def ensure_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def extract_text_content(message: ChatCompletionMessageParam) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return ensure_str(part.get("text"))
    return ""


def seed_file_state_from_messages(
    file_state: AgentFileState,
    prompt_messages: List[ChatCompletionMessageParam],
) -> None:
    if file_state.content:
        return

    for message in reversed(prompt_messages):
        if message.get("role") != "assistant":
            continue
        raw_text = extract_text_content(message)
        if not raw_text:
            continue
        extracted = extract_html_content(raw_text)
        file_state.content = extracted or raw_text
        if not file_state.path:
            file_state.path = "index.html"
        return

    if not prompt_messages:
        return

    system_message = prompt_messages[0]
    if system_message.get("role") != "system":
        return

    system_text = extract_text_content(system_message)
    markers = [
        "Here is the code of the app:",
    ]
    for marker in markers:
        if marker not in system_text:
            continue
        raw_text = system_text.split(marker, 1)[1].strip()
        extracted = extract_html_content(raw_text)
        file_state.content = extracted or raw_text
        if not file_state.path:
            file_state.path = "index.html"
        return
