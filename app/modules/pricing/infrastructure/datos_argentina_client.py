from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://apis.datos.gob.ar/series/api/series"
DEFAULT_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class DatosArgentinaPoint:
    date: date
    value: Decimal


class DatosArgentinaClientError(RuntimeError):
    pass


def _build_url(series_id: str, start_date: date | None = None, end_date: date | None = None) -> str:
    params: dict[str, str] = {
        "ids": series_id,
        "limit": "1000",
        "format": "json",
    }
    if start_date is not None:
        params["start_date"] = start_date.isoformat()
    if end_date is not None:
        params["end_date"] = end_date.isoformat()
    return f"{BASE_URL}?{urlencode(params)}"


def _parse_points(payload: dict) -> list[DatosArgentinaPoint]:
    raw_data = payload.get("data")
    if not isinstance(raw_data, list) or not raw_data:
        raise DatosArgentinaClientError("La API de Datos Argentina devolvio una respuesta vacia.")

    points: list[DatosArgentinaPoint] = []
    for row in raw_data:
        if not isinstance(row, list) or len(row) < 2:
            continue
        raw_date, raw_value = row[0], row[1]
        if raw_date is None or raw_value is None:
            continue
        points.append(
            DatosArgentinaPoint(
                date=date.fromisoformat(str(raw_date)),
                value=Decimal(str(raw_value)),
            )
        )

    if not points:
        raise DatosArgentinaClientError("La API de Datos Argentina no devolvio puntos validos.")
    return points


def fetch_series(series_id: str, start_date: date | None = None, end_date: date | None = None) -> list[DatosArgentinaPoint]:
    url = _build_url(series_id, start_date=start_date, end_date=end_date)
    request = Request(
        url,
        headers={
            "User-Agent": "SICONS/1.0 (+https://buildwise.local)",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            if response.status >= 400:
                raise DatosArgentinaClientError(f"Datos Argentina respondio con HTTP {response.status}.")
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise DatosArgentinaClientError(f"Datos Argentina respondio con HTTP {exc.code}.") from exc
    except URLError as exc:
        raise DatosArgentinaClientError("No fue posible conectar con Datos Argentina.") from exc
    except TimeoutError as exc:
        raise DatosArgentinaClientError("Timeout al consultar Datos Argentina.") from exc
    except json.JSONDecodeError as exc:
        raise DatosArgentinaClientError("Datos Argentina devolvio JSON invalido.") from exc

    return _parse_points(payload)
