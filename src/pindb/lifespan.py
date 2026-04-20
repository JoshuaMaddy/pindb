"""FastAPI lifespan: logging, seed data, Meilisearch index, scheduled search sync."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from sqlalchemy import select

from pindb.config import CONFIGURATION
from pindb.database import seed_currencies, session_maker
from pindb.database.user import User
from pindb.log import setup_rich_logger
from pindb.search.update import setup_index, update_all

LOGGER = logging.getLogger("pindb.lifespan")


def _ensure_admins() -> None:
    """Promote configured usernames to admin on startup when not already admin."""
    usernames = CONFIGURATION.bootstrap_admin_username_list
    if not usernames:
        return
    with session_maker.begin() as db:
        for username in usernames:
            user: User | None = db.scalars(
                select(User).where(User.username == username)
            ).first()
            if user is not None and not user.is_admin:
                user.is_admin = True
                LOGGER.info(f"Granted admin to user '{username}'.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging, DB seeds, search index, and background Meilisearch sync.

    Args:
        app (FastAPI): Application instance (unused but required by Starlette).

    Yields:
        None: Control after startup hooks; shuts down the APScheduler on exit.
    """
    setup_rich_logger()
    seed_currencies()
    _ensure_admins()
    setup_index()
    update_all()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=update_all,
        trigger="interval",
        minutes=CONFIGURATION.search_sync_interval_minutes,
    )
    scheduler.start()

    yield
    scheduler.shutdown()
