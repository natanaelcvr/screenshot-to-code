from prompts.system_prompt import SYSTEM_PROMPT


def test_system_prompt_has_a_flutter_section() -> None:
    assert "## Flutter" in SYSTEM_PROMPT


def test_flutter_section_documents_fixed_file_structure() -> None:
    flutter_section = SYSTEM_PROMPT.split("## Flutter", 1)[1]
    flutter_section = flutter_section.split("## General instructions", 1)[0]

    assert "pubspec.yaml" in flutter_section
    assert "lib/" in flutter_section
    assert "lib/main.dart" in flutter_section
    # Must tell the model screenshot_preview isn't offered for this stack.
    assert "screenshot_preview" in flutter_section
    assert "placehold.co" in flutter_section


def test_flutter_section_mentions_standard_widgets() -> None:
    flutter_section = SYSTEM_PROMPT.split("## Flutter", 1)[1]
    flutter_section = flutter_section.split("## General instructions", 1)[0]

    assert "MaterialApp" in flutter_section
    assert "Scaffold" in flutter_section
