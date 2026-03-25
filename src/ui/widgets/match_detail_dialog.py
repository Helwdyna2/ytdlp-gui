"""Dialog for viewing and selecting from multiple match candidates."""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QFrame,
    QButtonGroup,
    QRadioButton,
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from ...data.models import MatchResult, SceneMetadata

logger = logging.getLogger(__name__)


class MatchDetailDialog(QDialog):
    """
    Dialog for viewing and selecting from multiple match candidates.

    Shows side-by-side comparison with:
    - Thumbnails (if available)
    - Title, Studio, Performers
    - Date, Duration
    - Source database and URL
    - Confidence score
    - Select button for each option
    """

    match_selected = pyqtSignal(object)  # SceneMetadata

    def __init__(self, result: MatchResult, parent=None):
        """
        Initialize the dialog.

        Args:
            result: MatchResult with multiple matches
            parent: Parent widget
        """
        super().__init__(parent)
        self._result = result
        self._selected: Optional[SceneMetadata] = None
        self._button_group = QButtonGroup(self)
        self._network_manager = QNetworkAccessManager(self)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build dialog layout."""
        self.setWindowTitle("Select Match")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel(
            f"<h2>Select Match for: {self._result.original_filename}</h2>"
        )
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Scrollable area for match cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container widget for cards
        cards_widget = QWidget()
        cards_layout = QVBoxLayout(cards_widget)
        cards_layout.setSpacing(10)

        # Add a card for each match
        for i, match in enumerate(self._result.matches):
            card = self._create_match_card(match, i)
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        scroll_area.setWidget(cards_widget)
        layout.addWidget(scroll_area)

        # Bottom buttons
        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("btnWire")
        self.cancel_button.clicked.connect(self.reject)

        self.apply_button = QPushButton("Apply Selected")
        self.apply_button.setObjectName("btnCyan")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        self.apply_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)

    def _create_match_card(self, match: SceneMetadata, index: int) -> QFrame:
        """
        Create a card widget for a single match.

        Args:
            match: SceneMetadata to display
            index: Index in matches list

        Returns:
            QFrame containing match information
        """
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        card.setLineWidth(1)

        card_layout = QHBoxLayout(card)

        # Radio button for selection
        radio = QRadioButton()
        radio.toggled.connect(lambda checked: self._on_radio_toggled(checked, match))
        self._button_group.addButton(radio, index)
        card_layout.addWidget(radio)

        # Thumbnail (placeholder if not available)
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(QSize(160, 90))
        thumbnail_label.setScaledContents(True)
        thumbnail_label.setFrameStyle(QFrame.Shape.Box)

        if match.thumbnail_url:
            # Load thumbnail asynchronously
            self._load_thumbnail(match.thumbnail_url, thumbnail_label)
        else:
            thumbnail_label.setText("No\nImage")
            thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(thumbnail_label)

        # Match details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(5)

        # Title
        title_label = QLabel(f"<b>{match.title}</b>")
        title_label.setWordWrap(True)
        details_layout.addWidget(title_label)

        # Studio
        studio_label = QLabel(f"<b>Studio:</b> {match.studio}")
        details_layout.addWidget(studio_label)

        # Performers
        if match.performers:
            performers_text = ", ".join(match.performers)
            performers_label = QLabel(f"<b>Performers:</b> {performers_text}")
            performers_label.setWordWrap(True)
            details_layout.addWidget(performers_label)

        # Date
        if match.date:
            date_label = QLabel(f"<b>Date:</b> {match.date}")
            details_layout.addWidget(date_label)

        # Source database
        source_label = QLabel(f"<b>Source:</b> {match.source_database.upper()}")
        details_layout.addWidget(source_label)

        # Confidence (if available)
        if hasattr(match, "confidence"):
            confidence_label = QLabel(
                f"<b>Confidence:</b> {int(match.confidence * 100)}%"
            )
            details_layout.addWidget(confidence_label)

        # URL (if available)
        if match.source_url:
            url_label = QLabel(
                f"<b>URL:</b> <a href='{match.source_url}'>{match.source_url}</a>"
            )
            url_label.setOpenExternalLinks(True)
            url_label.setWordWrap(True)
            details_layout.addWidget(url_label)

        details_layout.addStretch()
        card_layout.addLayout(details_layout, 1)

        return card

    def _load_thumbnail(self, url: str, label: QLabel) -> None:
        """
        Load thumbnail image asynchronously.

        Args:
            url: Image URL
            label: QLabel to display image in
        """
        request = QNetworkRequest(url)
        reply = self._network_manager.get(request)
        reply.finished.connect(lambda: self._on_thumbnail_loaded(reply, label))

    def _on_thumbnail_loaded(self, reply: QNetworkReply, label: QLabel) -> None:
        """
        Handle thumbnail loaded.

        Args:
            reply: Network reply with image data
            label: QLabel to display image in
        """
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                label.setPixmap(pixmap)
            else:
                label.setText("Error\nLoading")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logger.warning(f"Error loading thumbnail: {reply.errorString()}")
            label.setText("Load\nFailed")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        reply.deleteLater()

    def _on_radio_toggled(self, checked: bool, match: SceneMetadata) -> None:
        """
        Handle radio button toggled.

        Args:
            checked: Whether button is checked
            match: Associated SceneMetadata
        """
        if checked:
            self._selected = match
            self.apply_button.setEnabled(True)

    def _on_apply_clicked(self) -> None:
        """Handle apply button click."""
        if self._selected:
            self.match_selected.emit(self._selected)
            self.accept()

    def get_selected_match(self) -> Optional[SceneMetadata]:
        """
        Return the selected match.

        Returns:
            Selected SceneMetadata or None
        """
        return self._selected
