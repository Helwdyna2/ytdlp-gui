"""Crash detection and recovery service."""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

from ..data.models import Session
from ..data.repositories.session_repository import SessionRepository
from ..utils.platform_utils import get_data_dir

logger = logging.getLogger(__name__)


class CrashRecoveryService:
    """
    Crash detection and recovery.

    Uses a lock file to detect unclean shutdowns.
    """

    def __init__(self, session_repository: SessionRepository):
        self.session_repo = session_repository
        self.lock_file = get_data_dir() / '.running.lock'
        self._has_lock = False

    def check_crash(self) -> bool:
        """
        Check if last session crashed.

        Returns True if a crash was detected.
        """
        if not self.lock_file.exists():
            return False

        try:
            with open(self.lock_file, 'r') as f:
                data = json.load(f)
                last_pid = data.get('pid')

                # Check if process is still running
                if not self._is_process_running(last_pid):
                    logger.warning("Detected unclean shutdown from previous session")
                    return True
                else:
                    # Process still running - another instance?
                    logger.warning("Lock file exists and process is running")
                    return False

        except Exception as e:
            logger.error(f"Error reading lock file: {e}")
            return True

    def acquire_lock(self) -> bool:
        """
        Acquire lock file on startup.

        Returns True if lock was acquired successfully.
        """
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.lock_file, 'w') as f:
                json.dump({
                    'pid': os.getpid(),
                    'started_at': datetime.now().isoformat()
                }, f)

            self._has_lock = True
            logger.info("Acquired application lock")
            return True

        except Exception as e:
            logger.error(f"Error acquiring lock: {e}")
            return False

    def release_lock(self):
        """Release lock file on clean shutdown."""
        if not self._has_lock:
            return

        try:
            self.lock_file.unlink(missing_ok=True)
            self._has_lock = False
            logger.info("Released application lock")
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")

    def get_recoverable_session(self) -> Optional[Session]:
        """
        Get a session that can be recovered after crash.

        Returns Session if there's a recoverable session, None otherwise.
        """
        # Get last active session
        session = self.session_repo.get_active()

        if session and session.pending_urls:
            logger.info(f"Found recoverable session with {len(session.pending_urls)} pending URLs")
            return session

        return None

    def mark_recovered(self, session: Session):
        """Mark a session as recovered (update its timestamp)."""
        session.updated_at = datetime.now()
        self.session_repo.save(session)
        logger.info(f"Marked session {session.id} as recovered")

    def discard_session(self, session: Session):
        """Discard a session (mark as inactive)."""
        self.session_repo.mark_inactive(session.id)
        logger.info(f"Discarded session {session.id}")

    def _is_process_running(self, pid: int) -> bool:
        """Check if process with PID is running (cross-platform)."""
        if pid is None:
            return False

        import sys
        
        if sys.platform == 'win32':
            # Windows: Use ctypes to check process existence
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                try:
                    exit_code = ctypes.c_ulong()
                    if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                        return exit_code.value == STILL_ACTIVE
                finally:
                    kernel32.CloseHandle(handle)
            return False
        else:
            # Unix/macOS: Send signal 0 to check if process exists
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    def __del__(self):
        """Cleanup on deletion."""
        if self._has_lock:
            self.release_lock()
