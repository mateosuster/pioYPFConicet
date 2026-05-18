"""
Rent appropriated via currency overvaluation (exports at overvalued exchange rate).
Also assembles retenciones + regalias for use in total rent calculation.
Replaces Section '# Renta apropiada por sobrevaluación cambiaria' and
'# Renta apropiada por el Estado mediante impuestos específicos'
of preprocesamiento.Rmd (lines ~3759-3797).
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parents[2]


def build_renta_tcp_crudo(
    renta_crudo_dif: pd.DataFrame,
    expo_usd_crudo: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rent from crude exports at overvalued exchange rate.

    Formula:
      renta_sobrevaluacion = expo_crudo * precio_externo * tcp - expo_crudo * precio_externo * tcc
    Cross-check via USD value:
      renta_sobrevaluacion_valor = expo_crudo_usd * tcp - expo_crudo_usd * tcc
    """
    df = renta_crudo_dif[
        ["anio", "unidad_cantidad", "expo_crudo", "precio_externo_crudo", "tcc", "tcp"]
    ].copy()

    df = df.merge(
        expo_usd_crudo[["anio", "expo_crudo_usd"]],
        on="anio", how="left",
    )

    df["renta_sobrevaluacion_crudo"] = (
        df["expo_crudo"] * df["precio_externo_crudo"] * df["tcp"]
        - df["expo_crudo"] * df["precio_externo_crudo"] * df["tcc"]
    )
    # Cross-check using total USD export value
    df["renta_sobrevaluacion_crudo_valor"] = (
        df["expo_crudo_usd"] * df["tcp"] - df["expo_crudo_usd"] * df["tcc"]
    )
    df["dif"] = df["renta_sobrevaluacion_crudo"] / df["renta_sobrevaluacion_crudo_valor"] - 1
    df["unidad_precio"] = "USD"
    df["unidad_renta"] = "Pesos corrientes"

    return df[[
        "anio", "unidad_cantidad", "expo_crudo",
        "unidad_precio", "precio_externo_crudo",
        "tcc", "tcp", "unidad_renta",
        "renta_sobrevaluacion_crudo", "renta_sobrevaluacion_crudo_valor", "dif",
    ]].copy()


def build_renta_tcp_gas(renta_gas_dif: pd.DataFrame) -> pd.DataFrame:
    """
    Rent from gas exports at overvalued exchange rate.

    Formula:
      renta_sobrevaluacion_gas = expo_gas * precio_externo_gas * tcp - expo_gas * precio_externo_gas * tcc
    """
    df = renta_gas_dif[
        ["anio", "unidad_cantidad", "expo_gas", "precio_externo_gas", "tcc", "tcp"]
    ].copy()

    df["renta_sobrevaluacion_gas"] = (
        df["expo_gas"] * df["precio_externo_gas"] * df["tcp"]
        - df["expo_gas"] * df["precio_externo_gas"] * df["tcc"]
    )
    df["unidad_precio"] = "USD"
    df["unidad_renta"] = "Pesos corrientes"

    return df[[
        "anio", "unidad_cantidad", "expo_gas",
        "unidad_precio", "precio_externo_gas",
        "tcc", "tcp", "unidad_renta",
        "renta_sobrevaluacion_gas",
    ]].copy()


def build_retenciones_regalias(
    regalias: pd.DataFrame,
    retenciones: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine royalties and export taxes for total rent calculation.
    Uses retenciones_crudo_jk column from retenciones (JK series).
    """
    ret_cols = ["anio"]
    if "retenciones_crudo_jk" in retenciones.columns:
        ret_cols.append("retenciones_crudo_jk")
    elif "retenciones_crudo" in retenciones.columns:
        ret_cols.append("retenciones_crudo")

    ret = retenciones[ret_cols].copy()
    df = regalias.merge(ret, on="anio", how="left")
    return df.sort_values("anio").reset_index(drop=True)


def run(
    renta_crudo_dif: pd.DataFrame,
    renta_gas_dif: pd.DataFrame,
    expo_usd_crudo: pd.DataFrame,
    regalias: pd.DataFrame,
    retenciones: pd.DataFrame,
) -> dict:
    renta_tcp_crudo = build_renta_tcp_crudo(renta_crudo_dif, expo_usd_crudo)
    renta_tcp_gas = build_renta_tcp_gas(renta_gas_dif)
    retenciones_regalias = build_retenciones_regalias(regalias, retenciones)

    return dict(
        renta_tcp_crudo=renta_tcp_crudo,
        renta_tcp_gas=renta_tcp_gas,
        retenciones_regalias=retenciones_regalias,
    )
