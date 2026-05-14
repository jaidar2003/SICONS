from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.shared.config.settings import settings
from app.shared.database.base import Base
from app.shared.database.audit_models import AuditLog  # noqa: F401
from app.modules.auth.infrastructure.models import Usuario  # noqa: F401
from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion  # noqa: F401
from app.modules.pricing.infrastructure.models import CommercialMargin, ExternalIndexValue, PrecioHistorico  # noqa: F401


config = context.config
config.set_main_option("sqlalchemy.url", settings.sqlalchemy_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.sqlalchemy_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
