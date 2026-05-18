"""
Retenciones, regalías, subsidios.
Replaces Sections 5-7 of preprocesamiento.Rmd (lines ~2209-2376).
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"


def build_retenciones(tcp_anual: pd.DataFrame) -> pd.DataFrame:
    """
    Export withholding taxes (retenciones) in ARS.
    Columns: anio, unidad, retenciones_hc, retenciones_crudo_jk, retenciones_crudo_bfr
    """
    # USD sheet → ARS
    ret_usd = pd.read_excel(DATA / "afip/retenciones.xlsx", sheet_name="usd")
    tcc_map = tcp_anual.set_index("anio")["tcc"]
    ret_usd["tcc"] = ret_usd["anio"].map(tcc_map)
    ret_usd["retenciones_hc"] = ret_usd["retenciones_hg"] * ret_usd["tcc"] * 1_000_000
    ret_usd["unidad"] = "ars"
    ret_campodonico = ret_usd[["anio", "unidad", "retenciones_hc"]]

    # Default sheet (JK + BFR estimates)
    ret_main = pd.read_excel(DATA / "afip/retenciones.xlsx")
    ret_main = ret_main.rename(columns={
        "retenciones_jk": "retenciones_crudo_jk",
        "retenciones_bfr_M$2008": "retenciones_crudo_bfr",
    })
    if "ipc08_bfr" in ret_main.columns:
        ret_main["retenciones_crudo_bfr"] = ret_main["retenciones_crudo_bfr"] * ret_main["ipc08_bfr"] * 1000
        ret_main = ret_main.drop(columns=["ipc08_bfr"])
    ret_main["unidad"] = "ars"

    df = ret_main.merge(ret_campodonico, on=["anio", "unidad"], how="outer")
    return df


def build_regalias(tcp_anual: pd.DataFrame, renta_hidrocarburos_fr: pd.DataFrame = None) -> dict:
    """
    Royalties from Secretaría de Energía (4 products: crudo, gas, gasolina, glp) → ARS.
    Returns:
      regalias_sec_en  — by product and year
      regalias         — annual total
      regalias_usd     — total in USD
    """
    productos = ["crudo", "gas", "gasolina", "glp"]
    moneda_map = {"crudo": "USD", "gas": "USD", "gasolina": "USD", "glp": "ars"}

    frames = []
    for prod in productos:
        path = DATA / f"secretaria_energia/regalias/regalias_{prod}.csv"
        df = pd.read_csv(path, sep=";", skiprows=1)
        df["moneda"] = moneda_map[prod]
        df["producto"] = prod
        frames.append(df)

    regalias_all = pd.concat(frames, ignore_index=True)
    regalias_all = regalias_all.rename(columns={
        "AÑO": "anio",
        "MES": "mes",
        "TOTAL PROVINCIA": "regalias_se",
    })
    tcc_map = tcp_anual.set_index("anio")["tcc"]
    regalias_all["TCC"] = regalias_all["anio"].map(tcc_map)
    regalias_all = (
        regalias_all.groupby(["producto", "anio", "moneda"])["regalias_se"]
        .sum()
        .reset_index()
    )
    regalias_all["TCC"] = regalias_all["anio"].map(tcc_map)
    regalias_all["regalias_se"] = np.where(
        regalias_all["moneda"] == "USD",
        regalias_all["regalias_se"] * regalias_all["TCC"],
        regalias_all["regalias_se"],
    )
    regalias_all["unidad"] = "ars"
    regalias_sec_en = regalias_all.drop(columns=["TCC", "moneda"])

    # Annual totals
    regalias_total = (
        regalias_sec_en.groupby(["anio", "unidad"])["regalias_se"]
        .sum()
        .reset_index()
        .rename(columns={"regalias_se": "regalias_se"})
    )
    regalias_total["regalias_total"] = np.where(
        regalias_total["anio"] < 1991,
        0,
        regalias_total["regalias_se"],
    )

    regalias_usd = regalias_total.copy()
    regalias_usd["tcc"] = regalias_usd["anio"].map(tcc_map)
    regalias_usd["regalias"] = regalias_usd["regalias_total"] / regalias_usd["tcc"]
    regalias_usd["unidad"] = "USD"
    regalias_usd = regalias_usd[["anio", "unidad", "regalias_se", "regalias"]]

    return dict(
        regalias_sec_en=regalias_sec_en,
        regalias=regalias_total.sort_values("anio"),
        regalias_usd=regalias_usd.sort_values("anio"),
    )


def build_subsidios(tcp_anual: pd.DataFrame, ganancia_pbi: pd.DataFrame) -> pd.DataFrame:
    """
    Hydrocarbon subsidies in ARS (current pesos).
    Columns: anio, unidad, subsidios_ejes, subsidios_cefip
    """
    # CEFIP — % of GDP
    cefip_raw = pd.read_excel(DATA / "cefip/subsidios.xlsx")
    cefip = cefip_raw.melt(id_vars=[cefip_raw.columns[0]], var_name="anio",
                            value_name="subsidios_porcentaje_pbi")
    cefip.columns.values[0] = "sector"
    cefip = cefip[cefip["sector"].isin(["Plan Gas", "Subsidios FF GN y GLP"])]
    cefip["anio"] = pd.to_numeric(cefip["anio"], errors="coerce")
    pbi_map = ganancia_pbi.set_index("anio")["pbi"]
    cefip["pbi"] = cefip["anio"].map(pbi_map)
    cefip["subsidios_porcentaje_pbi"] = pd.to_numeric(cefip["subsidios_porcentaje_pbi"], errors="coerce")
    cefip["subsidios_cefip"] = cefip["subsidios_porcentaje_pbi"] / 100 * cefip["pbi"] * 1e6
    subsidios_cefip = (
        cefip.groupby("anio")
        .agg(subsidios_cefip=("subsidios_cefip", "sum"))
        .reset_index()
    )
    subsidios_cefip["unidad"] = "Pesos corrientes"

    # EJES — USD → ARS
    ejes_raw = pd.read_excel(DATA / "ejes/subsidios.xlsx")
    ejes_raw = ejes_raw.rename(columns={"subsidios_hidrocarburos": "subsidios_usd"})
    tcc_map = tcp_anual.set_index("anio")["tcc"]
    ejes_raw["tcc"] = ejes_raw["anio"].map(tcc_map)
    ejes_raw["subsidios_ejes"] = ejes_raw["subsidios_usd"] * ejes_raw["tcc"] * 1e6
    subsidios_ejes = ejes_raw.groupby("anio").agg(subsidios_ejes=("subsidios_ejes", "sum")).reset_index()
    subsidios_ejes["unidad"] = "Pesos corrientes"

    df = (
        subsidios_ejes.merge(subsidios_cefip, on=["anio", "unidad"], how="outer")
        .sort_values("anio", ascending=False)
    )
    df["unidad"] = "Pesos corrientes"
    df.sort_values("anio", ascending=True, inplace=True)
    return df


def run(tcp_anual: pd.DataFrame, ganancia_pbi: pd.DataFrame) -> dict:
    retenciones = build_retenciones(tcp_anual)
    regalias_result = build_regalias(tcp_anual)
    subsidios = build_subsidios(tcp_anual, ganancia_pbi)

    return dict(
        retenciones=retenciones,
        **regalias_result,
        subsidios=subsidios,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    aux = run_indices()
    result = run(aux["tcp_anual"], aux["ganancia_pbi"])
    print("fiscalidad OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
