from agent.flutter_scaffold import load_flutter_scaffold_files
from agent.state import AgentFileState


def test_agent_file_state_defaults_are_unchanged_for_single_file_stacks() -> None:
    # The six HTML-based stacks only ever read/write path + content; this
    # must stay exactly as it was before `files` was added.
    file_state = AgentFileState()

    assert file_state.path == "index.html"
    assert file_state.content == ""
    assert file_state.files == {}


def test_agent_file_state_supports_independent_multi_file_storage() -> None:
    file_state = AgentFileState()

    file_state.files["lib/main.dart"] = "void main() {}"
    file_state.files["lib/screens/home.dart"] = "class Home {}"

    # Adding files must not disturb the single-file path/content fields that
    # the other stacks rely on.
    assert file_state.path == "index.html"
    assert file_state.content == ""
    assert file_state.files == {
        "lib/main.dart": "void main() {}",
        "lib/screens/home.dart": "class Home {}",
    }


def test_load_flutter_scaffold_files_includes_pubspec_and_web_entrypoint() -> None:
    files = load_flutter_scaffold_files()

    assert "pubspec.yaml" in files
    assert "web/index.html" in files
    assert "name: generated_app" in files["pubspec.yaml"]
    assert "flutter_bootstrap.js" in files["web/index.html"]
    # The scaffold must never include lib/** — the agent always writes its
    # own lib/main.dart via create_file.
    assert not any(path.startswith("lib/") for path in files)


def test_load_flutter_scaffold_files_returns_a_fresh_copy_each_call() -> None:
    first = load_flutter_scaffold_files()
    first["pubspec.yaml"] = "mutated"

    second = load_flutter_scaffold_files()

    assert second["pubspec.yaml"] != "mutated"
