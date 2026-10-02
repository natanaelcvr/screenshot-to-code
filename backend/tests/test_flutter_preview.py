import pytest

from agent.state import AgentFileState
from agent.tools.flutter_preview import run_flutter_preview
from preview_screenshot.flutter_availability import is_flutter_build_available


def test_is_flutter_build_available_reflects_path_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    assert is_flutter_build_available() is False

    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/flutter")
    assert is_flutter_build_available() is True


@pytest.mark.asyncio
async def test_run_flutter_preview_fails_gracefully_when_sdk_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agent.tools.flutter_preview.is_flutter_build_available", lambda: False
    )
    file_state = AgentFileState(files={"lib/main.dart": "void main() {}"})

    result = await run_flutter_preview({}, file_state=file_state)

    assert result.ok is False
    assert "Flutter SDK" in result.result["error"]
    assert result.multimodal_parts is None


@pytest.mark.asyncio
async def test_run_flutter_preview_requires_main_dart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agent.tools.flutter_preview.is_flutter_build_available", lambda: True
    )
    file_state = AgentFileState(files={"pubspec.yaml": "name: generated_app\n"})

    result = await run_flutter_preview({}, file_state=file_state)

    assert result.ok is False
    assert "create_file" in result.result["error"]


@pytest.mark.asyncio
async def test_run_flutter_preview_reports_build_failure_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Flutter "is" available (binary on PATH) but the build itself fails —
    # e.g. broken Dart syntax. Must surface as ok=False, never an exception.
    monkeypatch.setattr(
        "agent.tools.flutter_preview.is_flutter_build_available", lambda: True
    )

    async def fake_run_flutter_build_web(_project_dir: str) -> tuple[bool, str]:
        return False, "flutter build web failed (exit code 1):\nsome dart error"

    monkeypatch.setattr(
        "agent.tools.flutter_preview._run_flutter_build_web",
        fake_run_flutter_build_web,
    )

    file_state = AgentFileState(
        files={
            "pubspec.yaml": "name: generated_app\n",
            "lib/main.dart": "this is not valid dart",
        }
    )

    result = await run_flutter_preview({}, file_state=file_state)

    assert result.ok is False
    assert "dart error" in result.result["error"]
    assert result.multimodal_parts is None
