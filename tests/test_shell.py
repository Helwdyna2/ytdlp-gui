"""Tests for Shell component."""
import pytest
import sys

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_shell_creates(qapp):
    from src.ui.shell import Shell
    shell = Shell()
    assert shell is not None


def test_shell_has_sidebar(qapp):
    from src.ui.shell import Shell
    shell = Shell()
    assert shell.sidebar is not None
    assert shell.content_stack is not None


def test_shell_register_tool(qapp):
    from src.ui.shell import Shell
    from PyQt6.QtWidgets import QWidget
    shell = Shell()
    shell.register_tool("convert", QWidget())
    assert shell.content_stack.count() >= 1


def test_shell_switch_to_tool(qapp):
    from src.ui.shell import Shell
    from PyQt6.QtWidgets import QWidget
    shell = Shell()
    shell.register_tool("add_urls", QWidget())
    shell.register_tool("convert", QWidget())
    shell.switch_to_tool("convert")
    assert shell.active_tool() == "convert"


def test_shell_register_stage_compat(qapp):
    """Backward compat: register_stage(definition, widget) maps to register_tool."""
    from src.ui.shell import Shell
    from src.ui.stage_definitions import StageDefinition
    from PyQt6.QtWidgets import QWidget
    shell = Shell()
    shell.register_stage(StageDefinition("prepare", "Prepare"), QWidget())
    assert shell.content_stack.count() >= 1


def test_shell_switch_to_stage_compat(qapp):
    """Backward compat: switch_to_stage maps to switch_to_tool."""
    from src.ui.shell import Shell
    from src.ui.stage_definitions import StageDefinition
    from PyQt6.QtWidgets import QWidget
    shell = Shell()
    shell.register_stage(StageDefinition("ingest", "Ingest"), QWidget())
    shell.register_stage(StageDefinition("prepare", "Prepare"), QWidget())
    shell.switch_to_stage("prepare")
    assert shell.active_stage() == "prepare"
