"""flutter_preview: self-check for the Flutter stack.

Builds the current Flutter project for Web and screenshots it with
Playwright, mirroring screenshot_preview's contract (same ToolExecutionResult
shape, same desktop/mobile image parts) but for a real multi-file project
tree instead of inline HTML: write the current files to a temp dir,
`flutter build web`, serve `build/web` statically, screenshot that, then
clean everything up.

Never raises: a missing Flutter SDK, a failed build, or a failed screenshot
are all reported as `ok=False` with a clear message, never an unhandled
exception — a broken/absent Flutter toolchain must never abort a generation.
"""

import asyncio
import base64
import functools
import http.server
import shutil
import socket
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agent.state import AgentFileState
from agent.tools.types import ToolExecutionResult, ToolMultimodalPart
from preview_screenshot import capture_preview_screenshot_url, is_flutter_build_available

PREVIEW_VIEWPORTS = ("desktop", "mobile")
FLUTTER_BUILD_TIMEOUT_S = 120
# Tail of stderr kept for diagnostics when the build fails; the full log
# would bloat the tool result without being more actionable for the model.
STDERR_TAIL_CHARS = 4000


def _write_project_files(root: Path, files: Dict[str, str]) -> None:
    for relative_path, content in files.items():
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


class _StaticPreviewServer:
    """Serves a build output directory on localhost for one screenshot
    capture, then shuts down.

    A plain stdlib HTTP server on a background thread is enough: this is a
    short-lived, single-client, localhost-only preview — not a production
    file server — so it isn't worth pulling in a real ASGI/WSGI stack.
    """

    def __init__(self, directory: str) -> None:
        handler_cls = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=directory
        )
        # Bind to port 0 (OS-assigned free port) to avoid races with
        # whatever else might be listening locally.
        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        port = self._httpd.server_address[1]
        return f"http://127.0.0.1:{port}/"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


async def _run_flutter_build_web(project_dir: str) -> Tuple[bool, str]:
    """Run `flutter build web --release` in `project_dir`.

    Returns (ok, error_message). error_message is empty on success.
    """
    flutter_bin = shutil.which("flutter")
    if not flutter_bin:
        return (
            False,
            "The Flutter SDK (`flutter` binary) is not available on this server.",
        )

    try:
        process = await asyncio.create_subprocess_exec(
            flutter_bin,
            "build",
            "web",
            "--release",
            cwd=project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as exc:
        return False, f"Failed to launch `flutter build web`: {exc}"

    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(), timeout=FLUTTER_BUILD_TIMEOUT_S
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return (
            False,
            f"`flutter build web` timed out after {FLUTTER_BUILD_TIMEOUT_S}s.",
        )

    if process.returncode != 0:
        tail = stderr.decode("utf-8", errors="replace")[-STDERR_TAIL_CHARS:]
        return (
            False,
            f"`flutter build web` failed (exit code {process.returncode}):\n{tail}",
        )

    return True, ""


async def run_flutter_preview(
    _args: Dict[str, Any],
    *,
    file_state: AgentFileState,
) -> ToolExecutionResult:
    """Build the current Flutter project for Web and return screenshots."""
    if not is_flutter_build_available():
        return ToolExecutionResult(
            ok=False,
            result={"error": "The Flutter SDK is not available on this server."},
            summary={"error": "Flutter unavailable"},
        )

    if "lib/main.dart" not in file_state.files:
        return ToolExecutionResult(
            ok=False,
            result={"error": "No lib/main.dart exists yet. Call create_file first."},
            summary={"error": "No Flutter project to preview"},
        )

    with tempfile.TemporaryDirectory(prefix="flutter_preview_") as tmp_dir:
        project_dir = Path(tmp_dir)
        _write_project_files(project_dir, file_state.files)

        build_ok, build_error = await _run_flutter_build_web(str(project_dir))
        if not build_ok:
            print(f"[flutter_preview] build failed: {build_error}")
            return ToolExecutionResult(
                ok=False,
                result={"error": build_error},
                summary={"error": "flutter build web failed"},
            )

        build_web_dir = project_dir / "build" / "web"
        if not (build_web_dir / "index.html").exists():
            return ToolExecutionResult(
                ok=False,
                result={
                    "error": (
                        "flutter build web did not produce a build/web/index.html "
                        "output."
                    )
                },
                summary={"error": "Missing build output"},
            )

        server = _StaticPreviewServer(str(build_web_dir))
        server.start()
        try:
            screenshots: List[Dict[str, Any]] = []
            multimodal_parts: List[ToolMultimodalPart] = []
            for viewport in PREVIEW_VIEWPORTS:
                try:
                    image_bytes = await capture_preview_screenshot_url(
                        server.base_url, device=viewport, full_page=True
                    )
                except Exception as exc:
                    print(f"[flutter_preview] screenshot failed: {exc}")
                    return ToolExecutionResult(
                        ok=False,
                        result={"error": f"Screenshot failed: {exc}"},
                        summary={"error": "Screenshot failed"},
                    )

                display_name = f"flutter_preview_{viewport}.png"
                image_part_index = len(multimodal_parts)
                encoded_image = base64.b64encode(image_bytes).decode("ascii")
                data_url = f"data:image/png;base64,{encoded_image}"
                screenshots.append(
                    {
                        "viewport": viewport,
                        "full_page": True,
                        "image_part_index": image_part_index,
                        "image_display_name": display_name,
                        "image_bytes": len(image_bytes),
                        # Inlined for the UI thumbnail only — never stored as
                        # an asset, same as screenshot_preview.
                        "image_url": data_url,
                        "status": "ok",
                    }
                )
                multimodal_parts.append(
                    ToolMultimodalPart(
                        display_name=display_name,
                        mime_type="image/png",
                        data=image_bytes,
                    )
                )
        finally:
            server.stop()

        result: Dict[str, Any] = {
            "content": (
                "Full-page desktop and mobile screenshots of the Flutter Web "
                "build are attached."
            ),
            "details": {
                "screenshots": [
                    {
                        "viewport": screenshot["viewport"],
                        "full_page": screenshot["full_page"],
                        "image_part_index": screenshot["image_part_index"],
                        "image_display_name": screenshot["image_display_name"],
                        "image_bytes": screenshot["image_bytes"],
                    }
                    for screenshot in screenshots
                ],
            },
        }
        summary: Dict[str, Any] = {"screenshots": screenshots, "status": "ok"}
        return ToolExecutionResult(
            ok=True,
            result=result,
            summary=summary,
            multimodal_parts=multimodal_parts,
        )
