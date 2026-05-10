from pathlib import Path

from fastapi import HTTPException

CMDSTAN_VERSION = "cmdstan-2.38.0"


def importar_dependencias_forecast():
    try:
        import cmdstanpy
        import pandas as pd
        from prophet import Prophet
        from prophet.models import CmdStanPyBackend, IStanBackend
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Faltan dependencias para generar el forecast.") from exc
    return cmdstanpy, pd, Prophet, CmdStanPyBackend, IStanBackend


def configurar_cmdstan(cmdstanpy, CmdStanPyBackend, IStanBackend) -> None:
    cmdstan_global = Path.home() / ".cmdstan" / CMDSTAN_VERSION
    if not cmdstan_global.exists():
        raise HTTPException(status_code=500, detail="No se encontro CmdStan para correr Prophet.")

    cmdstanpy.set_cmdstan_path(str(cmdstan_global))

    def fixed_init(self):
        cmdstanpy.set_cmdstan_path(str(cmdstan_global))
        IStanBackend.__init__(self)

    CmdStanPyBackend.__init__ = fixed_init
