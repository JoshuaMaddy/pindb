"""Alembic environment: loads ORM metadata and runs migrations against ``CONFIGURATION``."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import pindb.database.artist  # noqa: F401
import pindb.database.change_log  # noqa: F401
import pindb.database.currency  # noqa: F401
import pindb.database.grade  # noqa: F401
import pindb.database.joins  # noqa: F401
import pindb.database.link  # noqa: F401
import pindb.database.pending_edit  # noqa: F401
import pindb.database.pin  # noqa: F401
import pindb.database.pin_set  # noqa: F401
import pindb.database.session  # noqa: F401
import pindb.database.shop  # noqa: F401
import pindb.database.tag  # noqa: F401
import pindb.database.user  # noqa: F401
import pindb.database.user_auth_provider  # noqa: F401
import pindb.database.user_owned_pin  # noqa: F401
import pindb.database.user_wanted_pin  # noqa: F401
from alembic import context

# Load pindb config for the database URL
from pindb.config import CONFIGURATION

# Import Base and all models so they register with Base.metadata.
# Import individual model modules directly to avoid the side effects
# (engine creation, seeding) in pindb.database.__init__.
from pindb.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment / .env
config.set_main_option("sqlalchemy.url", CONFIGURATION.database_connection)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
