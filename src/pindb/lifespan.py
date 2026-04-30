"""FastAPI lifespan: logging, seed data, Meilisearch index, scheduled search sync."""

import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from sqlalchemy import select

from pindb.config import CONFIGURATION
from pindb.database import async_engine, async_session_maker, seed_currencies
from pindb.database.user import User
from pindb.log import setup_rich_logger
from pindb.search.update import setup_index, update_all

LOGGER = logging.getLogger("pindb.lifespan")


async def _ensure_admins() -> None:
    """Promote configured usernames to admin on startup when not already admin."""
    usernames = CONFIGURATION.bootstrap_admin_username_list
    if not usernames:
        return
    async with async_session_maker.begin() as db:
        for username in usernames:
            res = await db.execute(select(User).where(User.username == username))
            user: User | None = res.scalars().first()
            if user is not None and not user.is_admin:
                user.is_admin = True
                LOGGER.info("Granted admin to user '%s'.", username)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging, DB seeds, search index, and background Meilisearch sync.

    Args:
        app (FastAPI): Application instance (unused but required by Starlette).

    Yields:
        None: Control after startup hooks; shuts down the APScheduler on exit.
    """
    setup_rich_logger()
    await seed_currencies()
    await _ensure_admins()
    await setup_index()
    await update_all()
    # Only the dedicated scheduler container runs the recurring sync to avoid
    # duplicate jobs when multiple web replicas are up during a blue/green swap.
    scheduler: AsyncIOScheduler | None = None
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            update_all,
            trigger="interval",
            minutes=CONFIGURATION.search_sync_interval_minutes,
        )
        scheduler.start()

    yield
    if scheduler is not None:
        scheduler.shutdown(wait=True)
    await CONFIGURATION.aclose_meili()
    await async_engine.dispose()
