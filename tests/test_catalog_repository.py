import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.catalog.infrastructure.models import Material
from app.modules.catalog.infrastructure.repositories import SQLAlchemyMaterialRepository
from app.shared.database.base import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_sqlalchemy_material_repository(db_session):
    repo = SQLAlchemyMaterialRepository(db_session)
    
    # Create test data
    m1 = Material(nombre="Material 1", activo=True, unidad_base="kg")
    m2 = Material(nombre="Material 2", activo=False, unidad_base="un")
    db_session.add(m1)
    db_session.add(m2)
    db_session.commit()
    db_session.refresh(m1)
    
    # Test get_by_id
    found = repo.get_by_id(m1.id)
    assert found.id == m1.id
    assert found.nombre == "Material 1"
    
    not_found = repo.get_by_id(999)
    assert not_found is None
    
    # Test list_active
    active = repo.list_active()
    assert len(active) == 1
    assert active[0].id == m1.id
