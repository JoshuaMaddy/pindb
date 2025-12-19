from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from pindb.log import setup_rich_logger
from pindb.search.update import update_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_rich_logger()
    update_all()
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_all, "interval", minutes=5)  # Run every 5 minutes
    scheduler.start()

    yield
    scheduler.shutdown()
