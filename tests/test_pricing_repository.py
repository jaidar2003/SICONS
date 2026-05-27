from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.catalog.infrastructure.models import Fuente
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.modules.pricing.infrastructure.repositories import SQLAlchemyPricingRepository
from app.shared.database.base import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_sqlalchemy_pricing_repository(db_session):
    repo = SQLAlchemyPricingRepository(db_session)
    
    # Create test data
    f1 = Fuente(nombre="Fuente 1")
    db_session.add(f1)
    db_session.commit()
    db_session.refresh(f1)
    
    p1 = PrecioHistorico(
        material_id=1,
        fecha=date(2026, 1, 1),
        precio_original=100.0,
        precio_normalizado=100.0,
        fuente_id=f1.id,
        moneda="ARS"
    )
    p2 = PrecioHistorico(
        material_id=1,
        fecha=date(2025, 1, 1),
        precio_original=90.0,
        precio_normalizado=90.0,
        fuente_id=f1.id,
        moneda="ARS"
    )
    db_session.add_all([p1, p2])
    db_session.commit()
    
    # Test get_historical_prices
    prices = repo.get_historical_prices(1, date(2026, 1, 1))
    assert len(prices) == 1
    assert prices[0].precio_original == 100.0
    assert prices[0].fuente.nombre == "Fuente 1"
    
    all_prices = repo.get_historical_prices(1, date(2020, 1, 1))
    assert len(all_prices) == 2
    assert all_prices[0].fecha == date(2025, 1, 1) # Ordered by date asc
