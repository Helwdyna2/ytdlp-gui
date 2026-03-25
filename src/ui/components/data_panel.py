"""DataPanel — Signal Deck styled container replacing QGroupBox.

Provides a header bar with title, optional status tag, and optional action
button slot, plus a body area where callers add their own content via
``body_layout``.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class DataPanel(QWidget):
    """Themed panel container with header and body sections.

    Args:
        title: Text displayed in the header (rendered in title case).
        parent: Optional parent widget.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("dpanel")

        self._header_tag: Optional[QLabel] = None

        self._setup_ui(title)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def body_layout(self) -> QVBoxLayout:
        """Layout where callers add content widgets."""
        return self._body_layout

    def set_header_tag(self, text: str, color_name: str) -> None:
        """Show or update a small status tag in the header.

        Args:
            text: Tag label (e.g. "ACTIVE", "ERROR").
            color_name: Semantic color key (e.g. "cyan", "red").  Applied
                as a Qt dynamic property so QSS can style by color.
        """
        if self._header_tag is None:
            self._header_tag = QLabel()
            self._header_tag.setObjectName("statusTag")
            self._header_layout.addWidget(self._header_tag)

        self._header_tag.setText(text)
        self._header_tag.setProperty("color", color_name)
        # Force QSS re-evaluation after dynamic property change.
        self._header_tag.style().unpolish(self._header_tag)
        self._header_tag.style().polish(self._header_tag)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _setup_ui(self, title: str) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Header ---
        header = QWidget()
        header.setObjectName("dpanelHeader")

        self._header_layout = QHBoxLayout(header)
        self._header_layout.setContentsMargins(10, 4, 10, 4)
        self._header_layout.setSpacing(8)

        self._title_label = QLabel(title.title())
        self._title_label.setObjectName("dpanelTitle")
        self._header_layout.addWidget(self._title_label)

        self._header_layout.addStretch(1)

        outer.addWidget(header)

        # --- Body ---
        body = QWidget()
        body.setObjectName("dpanelBody")

        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(10, 8, 10, 8)
        self._body_layout.setSpacing(6)

        outer.addWidget(body)
