"""Test configuration: use in-memory SQLite so tests never touch the disk."""
import os

# Must be set before app.config / app.db import.
os.environ.setdefault("ISNAD_DATABASE_URL", "sqlite://")
