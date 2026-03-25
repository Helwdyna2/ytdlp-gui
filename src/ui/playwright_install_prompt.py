"""Shared Playwright install prompt helpers."""

import logging
from typing import Optional, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMessageBox,
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QDialogButtonBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
)

from ..core.auth_manager import AuthManager

logger = logging.getLogger(__name__)


def is_playwright_setup_message(message: str) -> bool:
    """Check if message indicates missing Playwright browsers."""
    return "Playwright browsers are not installed" in message


def show_playwright_install_prompt(
    parent: QWidget,
    message: str,
    auth_manager: Optional[AuthManager],
    title: str = "Authentication Error",
) -> bool:
    """
    Show an install prompt for missing Playwright browsers.

    Returns True if the install action was triggered.
    """
    if not is_playwright_setup_message(message):
        QMessageBox.warning(parent, title, message)
        return False

    return show_playwright_browser_install_dialog(
        parent=parent,
        message=message,
        auth_manager=auth_manager,
        title=title,
        force=False,
    )


def show_playwright_browser_install_dialog(
    parent: QWidget,
    message: str,
    auth_manager: Optional[AuthManager],
    title: str = "Install Playwright Browsers",
    force: bool = False,
) -> bool:
    """Show a browser selection dialog for Playwright installation."""
    # First show browser selection dialog
    selection_dialog = _BrowserSelectionDialog(parent, message, title)
    if selection_dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    browsers = selection_dialog.get_selected_browsers()
    if not browsers:
        QMessageBox.warning(
            parent, title, "Select at least one browser to install."
        )
        return False

    # Then show installation progress dialog with streaming output
    if auth_manager:
        install_dialog = PlaywrightInstallDialog(
            parent=parent,
            auth_manager=auth_manager,
            browsers=browsers,
            force=force,
            title=title,
        )
        install_dialog.exec()
        return install_dialog.installation_succeeded()

    return False


class _BrowserSelectionDialog(QDialog):
    """Dialog for selecting which browsers to install."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        message: str = "",
        title: str = "Install Playwright Browsers",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.chromium_cb = QCheckBox("Chromium")
        self.firefox_cb = QCheckBox("Firefox")
        self.webkit_cb = QCheckBox("WebKit")
        self.chromium_cb.setChecked(True)

        layout.addWidget(self.chromium_cb)
        layout.addWidget(self.firefox_cb)
        layout.addWidget(self.webkit_cb)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText("Install")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_browsers(self) -> List[str]:
        """Return list of selected browser names."""
        browsers: List[str] = []
        if self.chromium_cb.isChecked():
            browsers.append("chromium")
        if self.firefox_cb.isChecked():
            browsers.append("firefox")
        if self.webkit_cb.isChecked():
            browsers.append("webkit")
        return browsers


class PlaywrightInstallDialog(QDialog):
    """
    Dialog that shows real-time Playwright browser installation progress.

    Streams the installation output to a text area so users can see
    what's happening during the potentially long installation process.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        auth_manager: Optional[AuthManager] = None,
        browsers: Optional[List[str]] = None,
        force: bool = False,
        title: str = "Installing Playwright Browsers",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        self._auth_manager = auth_manager
        self._browsers = browsers or ["chromium"]
        self._force = force
        self._succeeded = False
        self._error_message = ""

        self._setup_ui()
        self._connect_signals()
        self._start_installation()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)

        # Status label
        browser_label = ", ".join(self._browsers)
        self.status_label = QLabel(f"Installing {browser_label}...")
        self.status_label.setAccessibleName("Installation Status")
        layout.addWidget(self.status_label)

        # Progress bar (indeterminate since we don't know exact progress)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setAccessibleName("Installation Progress")
        layout.addWidget(self.progress_bar)

        # Output text area
        output_label = QLabel("Installation output:")
        layout.addWidget(output_label)

        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.output_text.setAccessibleName("Installation Output")
        self.output_text.setAccessibleDescription(
            "Real-time output from the Playwright browser installation process"
        )
        layout.addWidget(self.output_text, 1)  # Stretch to fill space

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect to auth manager signals."""
        if self._auth_manager:
            self._auth_manager.install_progress.connect(self._on_progress)
            self._auth_manager.install_output.connect(self._on_output_received)
            self._auth_manager.install_completed.connect(self._on_completed)
            self._auth_manager.install_failed.connect(self._on_failed)
            self._auth_manager.error.connect(self._on_error)

    def _start_installation(self) -> None:
        """Start the browser installation."""
        if self._auth_manager:
            self._auth_manager.install_browsers(self._browsers, force=self._force)

    def _on_progress(self, message: str) -> None:
        """Handle progress updates."""
        self.status_label.setText(message)
        self.output_text.appendPlainText(message)
        self._scroll_to_bottom()

    def _on_output_received(self, line: str) -> None:
        """Handle streamed output lines from the installation process."""
        self.output_text.appendPlainText(line)
        self._scroll_to_bottom()

    def _on_completed(self) -> None:
        """Handle successful completion."""
        self._succeeded = True
        self.status_label.setText("Installation completed successfully!")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.output_text.appendPlainText("\n✓ Installation complete")
        self._scroll_to_bottom()
        self.close_button.setEnabled(True)

    def _on_failed(self, error_message: str) -> None:
        """Handle installation failure."""
        self._succeeded = False
        self._error_message = error_message
        self.status_label.setText("Installation failed")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.output_text.appendPlainText(f"\n✗ Installation failed:\n{error_message}")
        self._scroll_to_bottom()
        self.close_button.setEnabled(True)

    def _on_error(self, message: str) -> None:
        """Handle generic errors."""
        self._succeeded = False
        self._error_message = message
        self.status_label.setText("Error during installation")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.output_text.appendPlainText(f"\n✗ Error: {message}")
        self._scroll_to_bottom()
        self.close_button.setEnabled(True)

    def _scroll_to_bottom(self) -> None:
        """Auto-scroll output to the bottom."""
        scrollbar = self.output_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def installation_succeeded(self) -> bool:
        """Return True if installation completed successfully."""
        return self._succeeded

    def get_error_message(self) -> str:
        """Return error message if installation failed."""
        return self._error_message
