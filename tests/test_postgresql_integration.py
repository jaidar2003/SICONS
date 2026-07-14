import os

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.catalog.infrastructure.models import Material
from app.operations.bootstrap.seed import seed
from app.shared.config.settings import settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_INTEGRATION") != "1",
    reason="requiere PostgreSQL efimero migrado",
)


@pytest.fixture
def postgres_engine():
    engine = create_engine(settings.sqlalchemy_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


def test_schema_migrado_coincide_con_identificadores_e_indices(postgres_engine) -> None:
    inspector = inspect(postgres_engine)

    assert "alertas" in inspector.get_table_names()
    alert_columns = {column["name"]: str(column["type"]) for column in inspector.get_columns("alertas")}
    assert alert_columns["id"] == "BIGINT"
    assert alert_columns["usuario_id"] == "BIGINT"
    assert alert_columns["material_id"] == "BIGINT"

    chat_columns = {column["name"]: str(column["type"]) for column in inspector.get_columns("chat_messages")}
    assert chat_columns["material_resuelto_id"] == "BIGINT"
    assert {index["name"] for index in inspector.get_indexes("alertas")} == {
        "idx_alertas_created_at",
        "idx_alertas_material_id",
        "idx_alertas_usuario_leida",
    }


def test_bootstrap_es_idempotente_en_postgresql(postgres_engine) -> None:
    with Session(postgres_engine) as db:
        seed(db)
        db.commit()
        first_materials = db.scalar(select(func.count()).select_from(Material))
        first_users = db.scalar(select(func.count()).select_from(Usuario))

        seed(db)
        db.commit()
        assert db.scalar(select(func.count()).select_from(Material)) == first_materials
        assert db.scalar(select(func.count()).select_from(Usuario)) == first_users
