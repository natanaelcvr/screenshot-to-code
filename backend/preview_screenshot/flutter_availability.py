"""Availability probe for the flutter_preview tool.

Mirrors the screenshot_preview "graceful degradation" pattern: if the
capability can't run here, the tool is simply never offered to the model —
a missing/broken Flutter SDK must never fail a generation.

Unlike screenshot_preview's Chromium probe (which has to actually launch the
browser once and cache the result), checking for the `flutter` binary is a
cheap, synchronous PATH lookup with nothing worth caching or warming up.
"""

import shutil


def is_flutter_build_available() -> bool:
    """Whether the `flutter` CLI is on PATH, so flutter_preview can run."""
    return shutil.which("flutter") is not None
