"""Static scaffold for the Flutter stack.

Design decision: a real Flutter project normally starts from `flutter create`,
which generates `pubspec.yaml`, `android/`, `web/`, and Gradle/Manifest
boilerplate. Running that at request time would require the Flutter SDK to be
installed and runnable (not guaranteed in every deployment, e.g. this sandbox),
and would add real latency to every generation.

Instead, this module ships a minimal, static, hand-written scaffold — just
enough for `flutter build web` to later succeed against it — committed to the
repo like any other source file. It covers `pubspec.yaml` and the Flutter Web
entry point (`web/index.html`, `web/manifest.json`); it deliberately does NOT
include `android/` (no on-device/emulator build is attempted in this phase,
see the project plan's fases 0/3) or a placeholder `lib/main.dart` (the agent
always writes that itself via `create_file`).

This is a deliberate simplification relative to the original plan (which
called for a dynamic `flutter create --platforms=android,web` at the start of
a generation): it trades a little bit of scaffold fidelity (a real
`flutter create` also emits a Gradle/Android project and a fuller web
manifest/icon set) for zero SDK dependency and zero added latency on every
Flutter generation, which matters far more given this phase only targets the
Flutter Web self-check (see `agent/tools/flutter_preview.py`), not an Android
build.
"""

from pathlib import Path
from typing import Dict

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_flutter_scaffold_files() -> Dict[str, str]:
    """Read the static scaffold into a {relative_path: content} map.

    Paths are relative to the Flutter project root (e.g. "pubspec.yaml",
    "web/index.html") and use forward slashes on every OS, matching the
    paths the agent's create_file/edit_file tools use for `lib/**` files.
    """
    files: Dict[str, str] = {}
    for file_path in sorted(_TEMPLATES_DIR.rglob("*")):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(_TEMPLATES_DIR).as_posix()
        files[relative_path] = file_path.read_text(encoding="utf-8")
    return files
