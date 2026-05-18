"""
Rent by price differential between domestic and international reference prices.
Replaces Section 'Renta por diferencial de precios' of preprocesamiento.Rmd (lines ~3682-3755).

World reference prices are now received from precios_me.run() rather than loaded here.
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"


def build_renta_crudo(
    prod_crudo: pd.DataFrame,
    expo_crudo: pd.DataFrame,
    precio_mi_crudo: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    precios_referencia_crudo: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rent from crude domestic/international price differential.

    Formula:
      renta_dif = prod_mdo_interno * precio_me * tcp - prod_mdo_interno * precio_mi * tcc
    """
    df = prod_crudo[["anio", "unidad", "prod_crudo"]].copy()
    df = df.merge(
        expo_crudo[["anio", "unidad", "expo_crudo"]],
        on=["anio", "unidad"], how="left",
    )
    df["expo_crudo"] = df["expo_crudo"].fillna(0)
    df["prod_mdo_interno"] = df["prod_crudo"] - df["expo_crudo"]

    df = df.merge(precio_mi_crudo[["anio", "precio_crudo_mdoint"]], on="anio", how="left")
    df = df.merge(
        precios_referencia_crudo[["anio", "precio_me_crudo", "brent_iea"]],
        on="anio", how="left",
    )
    df = df.merge(tcp_anual[["anio", "tcc", "tcp"]], on="anio", how="left")

    df["renta_dif_precios_crudo"] = (
        df["prod_mdo_interno"] * df["precio_me_crudo"] * df["tcp"]
        - df["prod_mdo_interno"] * df["precio_crudo_mdoint"] * df["tcc"]
    )
    df["renta_dif_precios_brent"] = (
        df["prod_mdo_interno"] * df["brent_iea"] * df["tcp"]
        - df["prod_mdo_interno"] * df["precio_crudo_mdoint"] * df["tcc"]
    )
    df["unidad_precio"] = "USD"
    df["unidad_renta"] = "Pesos corrientes"

    return df.rename(columns={
        "unidad": "unidad_cantidad",
        "precio_crudo_mdoint": "precio_interno_crudo",
        "precio_me_crudo": "precio_externo_crudo",
    })


def build_renta_gas(
    prod_gas_mmbtu: pd.DataFrame,
    expo_gas: pd.DataFrame,
    precio_mi_gas_mmbtu: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    precio_mdomundial_gas: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rent from gas domestic/international price differential.

    Formula:
      renta_dif_gas = prod_mdo_interno * tcp * precio_externo - prod_mdo_interno * tcc * precio_interno
    """
    df = prod_gas_mmbtu[["anio", "unidad", "prod_gas"]].copy()
    df = df.merge(expo_gas[["anio", "expo_gas"]], on="anio", how="left")
    df["expo_gas"] = df["expo_gas"].fillna(0)
    df["prod_mdo_interno"] = df["prod_gas"] - df["expo_gas"]

    df = df.merge(precio_mi_gas_mmbtu[["anio", "precio_gas_mdoint"]], on="anio", how="left")
    df = df.merge(
        precio_mdomundial_gas[["anio", "precio_externo_gas"]],
        on="anio", how="left",
    )
    df = df.merge(tcp_anual[["anio", "tcc", "tcp"]], on="anio", how="left")

    # Convert internal gas price from ARS/MMBTU to USD/MMBTU
    df["precio_interno_gas"] = df["precio_gas_mdoint"] / df["tcc"]

    df["renta_dif_precios_gas"] = (
        df["prod_mdo_interno"] * df["tcp"] * df["precio_externo_gas"]
        - df["prod_mdo_interno"] * df["tcc"] * df["precio_interno_gas"]
    )
    df["renta_abaratamiento_sobrevaluacion_gas"] = (
        df["prod_mdo_interno"] * df["precio_interno_gas"] * (df["tcp"] / df["tcc"] - 1)
    )
    df["unidad_precio"] = "USD"
    df["unidad_renta"] = "Pesos corrientes"

    return df.rename(columns={"unidad": "unidad_cantidad"})


def run(
    prod_crudo: pd.DataFrame,
    prod_gas_mmbtu: pd.DataFrame,
    expo_crudo: pd.DataFrame,
    expo_gas: pd.DataFrame,
    precio_mi_crudo: pd.DataFrame,
    precio_mi_gas_mmbtu: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    precios_referencia_crudo: pd.DataFrame,
    precio_mdomundial_gas: pd.DataFrame,
) -> dict:
    renta_crudo = build_renta_crudo(
        prod_crudo, expo_crudo, precio_mi_crudo, tcp_anual, precios_referencia_crudo
    )
    renta_gas = build_renta_gas(
        prod_gas_mmbtu, expo_gas, precio_mi_gas_mmbtu, tcp_anual, precio_mdomundial_gas
    )

    return dict(
        renta_crudo_dif=renta_crudo,
        renta_gas_dif=renta_gas,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    from preproc.produccion import run as run_prod
    from preproc.comex import run as run_comex
    from preproc.precios_mi import run as run_precios
    from preproc.precios_me import run as run_precios_me

    aux = run_indices()
    prod = run_prod()
    comex = run_comex()
    prec = run_precios(aux["tcp_anual"], aux["ipc"], aux["ipim"], aux["conversor_pesos"])
    pme = run_precios_me(aux["tcp_anual"], aux["ipc"], aux["conversor_pesos"])

    result = run(
        prod["prod_crudo"], prod["prod_gas_mmbtu"],
        comex["expo_crudo"], comex["expo_gas"],
        prec["precio_crudo_mi"], prec["precio_gas_mi_mmbtu"],
        aux["tcp_anual"],
        pme["precios_referencia_crudo"],
        pme["precio_mdomundial_gas_MMBTU"],
    )
    print("renta_dif OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
