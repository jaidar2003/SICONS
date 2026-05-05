from datetime import date
from urllib.error import HTTPError

import pytest

from app.modules.pricing.infrastructure import datos_argentina_client as client


class FakeResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_series_parsea_respuesta_valida(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout: int) -> FakeResponse:
        assert "ids=SERIE_TEST" in request.full_url
        assert "start_date=2026-01-01" in request.full_url
        assert "end_date=2026-03-01" in request.full_url
        assert request.headers["User-agent"] == "SICONS/1.0 (+https://buildwise.local)"
        assert request.headers["Accept"] == "application/json"
        assert timeout == client.DEFAULT_TIMEOUT_SECONDS
        return FakeResponse('{"data":[["2026-01-01",100.5],["2026-02-01",101.75]]}')

    monkeypatch.setattr(client, "urlopen", fake_urlopen)

    points = client.fetch_series("SERIE_TEST", start_date=date(2026, 1, 1), end_date=date(2026, 3, 1))

    assert len(points) == 2
    assert points[0].date == date(2026, 1, 1)
    assert str(points[0].value) == "100.5"
    assert points[1].date == date(2026, 2, 1)
    assert str(points[1].value) == "101.75"


def test_fetch_series_falla_con_respuesta_vacia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "urlopen", lambda *_args, **_kwargs: FakeResponse('{"data": []}'))

    with pytest.raises(client.DatosArgentinaClientError, match="respuesta vacia"):
        client.fetch_series("SERIE_TEST")


def test_fetch_series_propaga_error_http_claro(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*_args, **_kwargs):
        raise HTTPError("https://apis.datos.gob.ar", 503, "Service Unavailable", hdrs=None, fp=None)

    monkeypatch.setattr(client, "urlopen", fake_urlopen)

    with pytest.raises(client.DatosArgentinaClientError, match="HTTP 503"):
        client.fetch_series("SERIE_TEST")
