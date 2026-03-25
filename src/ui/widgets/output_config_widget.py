"""Output configuration widget."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QLabel,
    QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer

from ...data.models import OutputConfig
from ...services.config_service import ConfigService
from ...utils.platform_utils import get_default_output_dir
from ...utils.constants import (
    DEFAULT_CONCURRENT_LIMIT,
    MIN_CONCURRENT_LIMIT,
    MAX_CONCURRENT_LIMIT,
)
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir


class OutputConfigWidget(QWidget):
    """
    Output configuration controls.

    Provides controls for:
    - Output directory selection
    - Concurrent download limit (1-20)
    """

    config_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_service = ConfigService()
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_settings)
        self._setup_ui()
        self._connect_signals()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Output directory row
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Output Folder:"))

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        self.output_dir_edit.setAccessibleName("Output Directory")
        self.output_dir_edit.setAccessibleDescription(
            "Path to the folder where downloaded files will be saved"
        )
        dir_layout.addWidget(self.output_dir_edit, stretch=1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setObjectName("btnWire")
        self.browse_btn.setProperty("button_role", "secondary")
        self.browse_btn.setAccessibleName("Browse Output Directory")
        self.browse_btn.setAccessibleDescription(
            "Open a folder picker to select the output directory"
        )
        self.browse_btn.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(self.browse_btn)

        layout.addLayout(dir_layout)

        # Concurrent downloads row
        concurrent_layout = QHBoxLayout()
        concurrent_layout.addWidget(QLabel("Concurrent Downloads:"))

        self.concurrent_slider = QSlider(Qt.Orientation.Horizontal)
        self.concurrent_slider.setRange(MIN_CONCURRENT_LIMIT, MAX_CONCURRENT_LIMIT)
        self.concurrent_slider.setValue(DEFAULT_CONCURRENT_LIMIT)
        self.concurrent_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.concurrent_slider.setTickInterval(5)
        self.concurrent_slider.setAccessibleName("Concurrent Downloads Slider")
        self.concurrent_slider.setAccessibleDescription(
            "Adjust the number of simultaneous downloads"
        )
        concurrent_layout.addWidget(self.concurrent_slider, stretch=1)

        self.concurrent_spinbox = QSpinBox()
        self.concurrent_spinbox.setRange(MIN_CONCURRENT_LIMIT, MAX_CONCURRENT_LIMIT)
        self.concurrent_spinbox.setValue(DEFAULT_CONCURRENT_LIMIT)
        self.concurrent_spinbox.setFixedWidth(60)
        self.concurrent_spinbox.setAccessibleName("Concurrent Downloads")
        self.concurrent_spinbox.setAccessibleDescription(
            "Number of simultaneous downloads, between 1 and 20"
        )
        concurrent_layout.addWidget(self.concurrent_spinbox)

        layout.addLayout(concurrent_layout)

        # Filename format (fixed)
        filename_header = QLabel("Filename Format")
        filename_header.setObjectName("dpanelTitle")
        layout.addWidget(filename_header)

        filename_label = QLabel("Saved as: author - id.ext")
        filename_label.setObjectName("dimLabel")
        layout.addWidget(filename_label)

        filename_help = QLabel(
            "Author uses uploader/creator/channel/artist when available."
        )
        filename_help.setObjectName("dimLabel")
        layout.addWidget(filename_help)

    def _connect_signals(self):
        """Connect internal signals."""
        # Link slider and spinbox
        self.concurrent_slider.valueChanged.connect(self.concurrent_spinbox.setValue)
        self.concurrent_spinbox.valueChanged.connect(self.concurrent_slider.setValue)

        # Emit config changes and save to config service
        self.output_dir_edit.editingFinished.connect(self._on_config_changed)
        self.concurrent_spinbox.valueChanged.connect(self._on_config_changed)

    def _load_settings(self):
        """Load settings from config service."""
        output_dir = self._config_service.get("download.output_dir", "")
        if not output_dir:
            output_dir = str(get_default_output_dir())
        self.output_dir_edit.setText(output_dir)

        concurrent_limit = self._config_service.get(
            "download.concurrent_limit", DEFAULT_CONCURRENT_LIMIT
        )
        self.concurrent_spinbox.setValue(concurrent_limit)

    def _save_settings(self):
        """Save current settings to config service."""
        self._config_service.set("download.output_dir", self.output_dir_edit.text())
        self._config_service.set(
            "download.concurrent_limit", self.concurrent_spinbox.value()
        )

    def _on_config_changed(self):
        """Handle config change - debounce save and emit."""
        self._save_timer.start(500)  # Debounce 500ms
        self.config_changed.emit(self.get_config_dict())

    def _browse_output_dir(self):
        """Open directory picker."""
        current = self.output_dir_edit.text()
        start_dir = get_dialog_start_dir(current, "download.output_dir")
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", start_dir
        )
        if dir_path:
            update_dialog_last_dir(dir_path)
            self.output_dir_edit.setText(dir_path)

    def _emit_config(self):
        """Emit current configuration."""
        self.config_changed.emit(self.get_config_dict())

    def get_config_dict(self) -> dict:
        """Get configuration as dictionary."""
        return {
            "output_dir": self.output_dir_edit.text(),
            "concurrent_limit": self.concurrent_spinbox.value(),
        }

    def get_config(self) -> OutputConfig:
        """Get configuration as OutputConfig object."""
        return OutputConfig(
            output_dir=self.output_dir_edit.text(),
            concurrent_limit=self.concurrent_spinbox.value(),
            force_overwrite=self._config_service.get("download.force_overwrite", False),
            video_only=self._config_service.get("download.video_only", False),
            cookies_path=None,
            filename_templates={},
            default_template="%(title)s",
        )

    def set_config(self, config: dict):
        """Set configuration from dictionary."""
        if "output_dir" in config:
            self.output_dir_edit.setText(config["output_dir"])
        if "concurrent_limit" in config:
            self.concurrent_spinbox.setValue(config["concurrent_limit"])
        if "force_overwrite" in config:
            self._config_service.set(
                "download.force_overwrite", config["force_overwrite"], save=True
            )
        if "video_only" in config:
            self._config_service.set(
                "download.video_only", config["video_only"], save=True
            )

    @property
    def output_dir(self) -> str:
        """Get output directory."""
        return self.output_dir_edit.text()

    @property
    def concurrent_limit(self) -> int:
        """Get concurrent download limit."""
        return self.concurrent_spinbox.value()

    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        self.output_dir_edit.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.concurrent_slider.setEnabled(enabled)
        self.concurrent_spinbox.setEnabled(enabled)
