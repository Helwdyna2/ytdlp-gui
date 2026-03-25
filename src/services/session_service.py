"""Session management service."""

from datetime import datetime
from typing import Optional, List
import logging

from PyQt6.QtCore import QObject, QTimer

from ..data.models import Session, OutputConfig
from ..data.repositories.session_repository import SessionRepository
from ..utils.constants import AUTO_SAVE_INTERVAL_MS

logger = logging.getLogger(__name__)


class SessionService(QObject):
    """
    Session management - single source of truth for session state.

    Handles auto-save of session state and restoration on startup.
    All session operations should go through this service to ensure
    consistent state management and auto-save behavior.
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        parent=None
    ):
        super().__init__(parent)
        self.session_repo = session_repository
        self._auto_save_timer: Optional[QTimer] = None
        self._current_session: Optional[Session] = None
        self._dirty: bool = False  # Track if session needs saving

    def start_auto_save(self, interval_ms: int = AUTO_SAVE_INTERVAL_MS):
        """
        Start auto-save timer.

        Args:
            interval_ms: Auto-save interval in milliseconds. Defaults to
                        AUTO_SAVE_INTERVAL_MS (5000ms).
        """
        if self._auto_save_timer:
            self._auto_save_timer.stop()

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._auto_save_timer.start(interval_ms)
        logger.info(f"Auto-save started with {interval_ms}ms interval")

    def stop_auto_save(self):
        """
        Stop auto-save timer and save any pending changes.

        Should be called on application exit to ensure session is saved.
        """
        if self._auto_save_timer:
            self._auto_save_timer.stop()
            self._auto_save_timer = None
            logger.debug("Auto-save timer stopped")

        # Save any pending changes before stopping
        if self._dirty and self._current_session:
            self._save_session()
            logger.info("Saved pending session changes on stop")

    def mark_dirty(self):
        """
        Mark session as needing save.

        Call this whenever session state changes to ensure it gets
        saved on the next auto-save cycle or on exit.
        """
        if self._current_session:
            self._dirty = True

    def create_session(
        self,
        urls: List[str],
        config: OutputConfig
    ) -> Session:
        """
        Create a new session.

        Args:
            urls: List of URLs to download.
            config: Output configuration for the session.

        Returns:
            The created Session object with ID assigned.
        """
        session = Session(
            pending_urls=urls,
            output_dir=config.output_dir,
            concurrent_limit=config.concurrent_limit,
            force_overwrite=config.force_overwrite,
            video_only=config.video_only,
            cookies_path=config.cookies_path
        )
        session.id = self.session_repo.save(session)
        self._current_session = session
        self._dirty = False  # Fresh session, no need to save yet
        logger.info(f"Created session {session.id} with {len(urls)} URLs")
        return session

    def update_pending_urls(self, pending_urls: List[str]):
        """
        Update pending URLs for current session.

        This is the primary method for updating session state during
        downloads. Marks session as dirty for auto-save.

        Args:
            pending_urls: List of URLs still pending download.
        """
        if not self._current_session:
            return

        self._current_session.pending_urls = pending_urls
        self._current_session.updated_at = datetime.now()
        self._dirty = True

    def complete_session(self):
        """
        Mark current session as complete.

        Marks the session as inactive in the database and clears
        the current session reference.
        """
        if self._current_session:
            self.session_repo.mark_inactive(self._current_session.id)
            logger.info(f"Session {self._current_session.id} completed")
            self._current_session = None
            self._dirty = False

    def save_if_dirty(self):
        """
        Immediately save session if there are pending changes.

        Call this before application exit or when immediate
        persistence is required.
        """
        if self._dirty and self._current_session:
            self._save_session()

    def get_active_session(self) -> Optional[Session]:
        """Get active session if one exists."""
        return self.session_repo.get_active()

    def get_recoverable_session(self) -> Optional[Session]:
        """Get a session that can be recovered."""
        session = self.session_repo.get_active()
        if session and session.pending_urls:
            return session
        return None

    def clear_session(self, session_id: int):
        """Clear a specific session."""
        self.session_repo.delete(session_id)
        if self._current_session and self._current_session.id == session_id:
            self._current_session = None
            self._dirty = False

    def cleanup_old_sessions(self):
        """Clean up old inactive sessions."""
        count = self.session_repo.delete_inactive()
        if count > 0:
            logger.info(f"Cleaned up {count} inactive sessions")

    def _save_session(self):
        """Save current session to database and clear dirty flag."""
        if self._current_session:
            self._current_session.updated_at = datetime.now()
            self.session_repo.save(self._current_session)
            self._dirty = False

    def _auto_save(self):
        """
        Auto-save callback - saves session if dirty.

        Called periodically by the auto-save timer.
        """
        if self._dirty and self._current_session:
            self._save_session()
            logger.debug(f"Auto-saved session {self._current_session.id}")

    @property
    def current_session(self) -> Optional[Session]:
        """Get current session."""
        return self._current_session

    @property
    def has_active_session(self) -> bool:
        """Check if there's an active session."""
        return self._current_session is not None

    @property
    def is_dirty(self) -> bool:
        """Check if session has unsaved changes."""
        return self._dirty
