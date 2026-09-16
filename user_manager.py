"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CipherVault — User & Session Manager                                      ║
║  CSV-backed activity logging, user profiles, and session tracking           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import csv
import os
import uuid
from datetime import datetime


# Path to user data CSV (stored alongside the app)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_CSV = os.path.join(_APP_DIR, "user_data.csv")
USER_PROFILE_FILE = os.path.join(_APP_DIR, "user_profile.txt")

# CSV column headers
CSV_HEADERS = [
    "timestamp",        # ISO-8601 datetime of the operation
    "session_id",       # UUID for current app session
    "username",         # Active username
    "operation",        # encrypt_text | decrypt_text | encrypt_image | decrypt_image
    "input_preview",    # First 60 chars of input (truncated for privacy)
    "input_size",       # Size in chars (text) or bytes (image)
    "output_size",      # Size in chars (text) or bytes (image)
    "status",           # success | error
    "details",          # Additional info (dimensions, filename, etc.)
]


class UserManager:
    """Manages user profiles, sessions, and activity logging."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())[:8]
        self.session_start = datetime.now()
        self.operation_count = 0
        self.username = self._load_username()
        self._ensure_csv()

    # ── Username persistence ─────────────────────────────────────────────────

    def _load_username(self) -> str:
        """Load saved username or fallback to system username."""
        if os.path.exists(USER_PROFILE_FILE):
            try:
                with open(USER_PROFILE_FILE, 'r', encoding='utf-8') as f:
                    name = f.read().strip()
                    if name:
                        return name
            except Exception:
                pass
        return os.getlogin()

    def save_username(self, name: str):
        """Persist the username to profile file."""
        self.username = name.strip() or os.getlogin()
        with open(USER_PROFILE_FILE, 'w', encoding='utf-8') as f:
            f.write(self.username)

    # ── CSV management ───────────────────────────────────────────────────────

    def _ensure_csv(self):
        """Create CSV with headers if it doesn't exist."""
        if not os.path.exists(USER_DATA_CSV):
            with open(USER_DATA_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)

    def log_operation(
        self,
        operation: str,
        input_preview: str = "",
        input_size: int = 0,
        output_size: int = 0,
        status: str = "success",
        details: str = "",
    ):
        """
        Log an operation to the CSV file.
        
        Args:
            operation: One of encrypt_text, decrypt_text, encrypt_image, decrypt_image
            input_preview: Truncated preview of input data
            input_size: Size of input in chars or bytes
            output_size: Size of output in chars or bytes
            status: 'success' or 'error'
            details: Additional context
        """
        self.operation_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Truncate preview for privacy and CSV safety
        preview = input_preview[:60].replace('\n', ' ').replace(',', ';')

        row = [
            timestamp,
            self.session_id,
            self.username,
            operation,
            preview,
            str(input_size),
            str(output_size),
            status,
            details,
        ]

        try:
            with open(USER_DATA_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"[UserManager] Failed to log: {e}")

    # ── Activity history ─────────────────────────────────────────────────────

    def get_activity_history(self, limit: int = 100) -> list[dict]:
        """
        Read the activity log from CSV.
        
        Returns:
            List of dicts, most recent first, limited to `limit` entries.
        """
        if not os.path.exists(USER_DATA_CSV):
            return []

        rows = []
        try:
            with open(USER_DATA_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        except Exception:
            return []

        # Return most recent first
        rows.reverse()
        return rows[:limit]

    def get_stats(self) -> dict:
        """Get aggregate statistics from the activity log."""
        history = self.get_activity_history(limit=9999)

        total = len(history)
        encryptions = sum(1 for h in history if 'encrypt' in h.get('operation', '') and 'decrypt' not in h.get('operation', ''))
        decryptions = sum(1 for h in history if 'decrypt' in h.get('operation', ''))
        image_ops = sum(1 for h in history if 'image' in h.get('operation', ''))
        text_ops = sum(1 for h in history if 'text' in h.get('operation', ''))
        errors = sum(1 for h in history if h.get('status') == 'error')

        # Session uptime
        uptime = datetime.now() - self.session_start
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        return {
            'total_operations': total,
            'encryptions': encryptions,
            'decryptions': decryptions,
            'image_operations': image_ops,
            'text_operations': text_ops,
            'errors': errors,
            'success_rate': f"{((total - errors) / total * 100):.1f}%" if total > 0 else "—",
            'session_ops': self.operation_count,
            'session_uptime': f"{hours}h {minutes}m {seconds}s",
            'session_id': self.session_id,
            'username': self.username,
        }

    def clear_history(self):
        """Clear all activity history (re-create CSV with just headers)."""
        with open(USER_DATA_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
