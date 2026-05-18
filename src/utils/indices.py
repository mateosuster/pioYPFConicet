"""
Time-series index and growth helpers.
Direct translation of functiones_hidrocarburos.R.
"""

import pandas as pd


def generar_indice(serie: pd.Series, fecha: pd.Series, fecha_base) -> pd.Series:
    """
    Rebase a numeric series so that the value at fecha_base == 1.

    Parameters
    ----------
    serie      : pd.Series  numeric values
    fecha      : pd.Series  corresponding dates/years (same index as serie)
    fecha_base : scalar     value in `fecha` to use as base (e.g. "2018-01-01" or 2018)

    Returns
    -------
    pd.Series  rebased index
    """
    mask = fecha == fecha_base
    if not mask.any():
        raise ValueError(f"fecha_base {fecha_base!r} not found in fecha series")
    valor_base = serie[mask].iloc[0]
    return serie / valor_base


def cambio_porcentual(x: pd.Series) -> pd.Series:
    """Period-over-period percentage change (equivalent to R lag-based x/lag(x)-1)."""
    return x / x.shift(1) - 1


def variacion_interanual(x: pd.Series) -> pd.Series:
    """Year-over-year absolute change."""
    return x - x.shift(1)


def tasa_crecimiento(x: pd.Series) -> pd.Series:
    """Year-over-year growth rate."""
    return (x - x.shift(1)) / x.shift(1)
