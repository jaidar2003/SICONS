from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.alerts import generar_alertas_proactivas
from app.modules.pricing.application.forecast_service import ProphetRow
from app.modules.pricing.infrastructure.models import Alerta, PrecioHistorico
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead
from app.shared.database.base import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

class MockForecast:
    def __init__(self, y_actual=100.0, y_futuro=120.0, mape=5.0, precio_pesimista=125.0):
        self.dataset = [ProphetRow(ds=date.today(), y=y_actual)]
        self.forecast = [ForecastPuntoRead(
            fecha=date.today(), 
            precio_proyectado=Decimal(str(y_futuro)), 
            precio_optimista=Decimal(str(y_futuro*0.9)), 
            precio_pesimista=Decimal(str(precio_pesimista))
        )]
        self.metricas = ForecastMetricasRead(mape=mape, mae=mape, folds=1, efectividad_informal=95.0)

def test_generar_alertas_oportunidad_compra(db_session, monkeypatch):
    material = Material(nombre="Cemento Test", unidad_base="kg", activo=True)
    db_session.add(material)
    db_session.commit()
    
    monkeypatch.setattr("app.modules.pricing.application.alerts.forecast_material", lambda *args, **kwargs: MockForecast(y_actual=100.0, y_futuro=120.0))
    
    count = generar_alertas_proactivas(db_session, None)
    assert count >= 1
    alerta = db_session.query(Alerta).filter_by(tipo="OPORTUNIDAD_COMPRA").first()
    assert alerta is not None

def test_generar_alertas_deterioro_confianza(db_session, monkeypatch):
    material = Material(nombre="Pastina Test", unidad_base="kg", activo=True)
    db_session.add(material)
    db_session.commit()
    
    monkeypatch.setattr("app.modules.pricing.application.alerts.forecast_material", lambda *args, **kwargs: MockForecast(mape=20.0))
    
    count = generar_alertas_proactivas(db_session, None)
    assert count >= 1
    alerta = db_session.query(Alerta).filter_by(tipo="DETERIORO_CONFIANZA").first()
    assert alerta is not None

def test_generar_alertas_desvio_precio(db_session, monkeypatch):
    material = Material(nombre="Hierro Test", unidad_base="u", activo=True)
    db_session.add(material)
    db_session.commit()
    
    # Mock pesimista = 110
    monkeypatch.setattr("app.modules.pricing.application.alerts.forecast_material", lambda *args, **kwargs: MockForecast(precio_pesimista=110.0))
    
    # Real = 120 (> 110)
    real_price = PrecioHistorico(
        material_id=material.id,
        fecha=date.today(),
        precio_original=Decimal("120.00"),
        precio_normalizado=Decimal("120.00"),
        moneda="ARS",
        origen_dato="REAL"
    )
    db_session.add(real_price)
    db_session.commit()
    
    count = generar_alertas_proactivas(db_session, None)
    assert count >= 1
    alerta = db_session.query(Alerta).filter_by(tipo="DESVIO_PRECIO").first()
    assert alerta is not None
