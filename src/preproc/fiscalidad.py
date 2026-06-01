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

    # Alternative source: AFIP Cap.27 annual series 2018-2023, millions of current ARS
    cap27_raw = pd.read_excel(
        DATA / "afip/retenciones_petroleo_2018_2023-1.xlsx",
        sheet_name="Serie Cap.27",
        header=2,
        usecols=["Año", "Cap.27 (ARS M)"],
    )
    cap27 = (
        cap27_raw
        .rename(columns={"Año": "anio", "Cap.27 (ARS M)": "retenciones_afip_cap27"})
        .dropna(subset=["anio", "retenciones_afip_cap27"])
    )
    cap27["anio"] = cap27["anio"].astype(int)
    cap27["retenciones_afip_cap27"] = cap27["retenciones_afip_cap27"] * 1e6
    cap27["unidad"] = "ars"

    df_old = ret_main.merge(ret_campodonico, on=["anio", "unidad"], how="outer")
    df = pd.concat(
        [df_old, cap27[["anio", "unidad", "retenciones_afip_cap27"]]],
        ignore_index=True,
    ).sort_values("anio").reset_index(drop=True)
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
    # crudo and gasolina CSVs are in USD; gas and glp CSVs are in ARS
    # (gas CSV is labeled "Suma de USD" but values are in ARS — royalties are paid at domestic ARS prices)
    moneda_map = {"crudo": "USD", "gas": "ars", "gasolina": "USD", "glp": "ars"}

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


def build_subsidios(tcp_anual: pd.DataFrame, ganancia_pbi: pd.DataFrame, ipc: pd.DataFrame) -> pd.DataFrame:
    """
    Hydrocarbon subsidies in ARS (current pesos).
    Columns: anio, unidad, subsidios_ejes, subsidios_cefip, subsidios_acij
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

    # ACIJ — constant Dec-2024 pesos → pesos corrientes
    acij_raw = pd.read_excel(
        ROOT / "update" / "Base de datos de petroleras en Argentina.xlsx",
        sheet_name="Base de datos",
    )
    sub_col = [c for c in acij_raw.columns if "Subsidios" in str(c) and "2024" in str(c)][0]
    acij_raw = acij_raw.rename(columns={
        acij_raw.columns[0]: "anio",
        acij_raw.columns[1]: "empresa",
        sub_col: "subsidios_acij_m24",
    })
    acij_raw = acij_raw[["anio", "empresa", "subsidios_acij_m24"]].dropna(subset=["anio"])
    acij_raw["anio"] = acij_raw["anio"].astype(int)
    acij_anual = acij_raw.groupby("anio", as_index=False)["subsidios_acij_m24"].sum()
    # corriente_Y = constante_2024 * (ipc_03_Y / ipc_03_2024) = constante_2024 * ipc_24_Y
    ipc_24_map = ipc.set_index("anio")["ipc_24"]
    acij_anual["ipc_24"] = acij_anual["anio"].map(ipc_24_map)
    acij_anual["subsidios_acij"] = acij_anual["subsidios_acij_m24"] * acij_anual["ipc_24"] * 1e6
    acij_anual = acij_anual[["anio", "subsidios_acij"]]

    df = (
        subsidios_ejes
        .merge(subsidios_cefip, on=["anio", "unidad"], how="outer")
        .merge(acij_anual, on="anio", how="outer")
        .sort_values("anio")
    )
    df["unidad"] = "Pesos corrientes"
    return df


def plot_subsidios_comparison(
    subsidios: pd.DataFrame,
    ipc: pd.DataFrame,
    tcp_anual: pd.DataFrame,
) -> None:
    """Save two line plots comparing subsidios by source: constant ARS and USD TCC."""
    import plotly.graph_objects as go

    RESULTS = ROOT / "results" / "argentina"
    RESULTS.mkdir(parents=True, exist_ok=True)

    ipc_18_map = ipc.set_index("anio")["ipc_18"]
    tcc_map = tcp_anual.set_index("anio")["tcc"]

    df = subsidios.copy()
    df["ipc_18"] = df["anio"].map(ipc_18_map)
    df["tcc"] = df["anio"].map(tcc_map)

    sources = {
        "EJES": "subsidios_ejes",
        "CEFIP": "subsidios_cefip",
        "ACIJ": "subsidios_acij",
    }

    fig1 = go.Figure()
    for label, col in sources.items():
        if col in df.columns:
            y = df[col] / df["ipc_18"] / 1e6
            fig1.add_trace(go.Scatter(x=df["anio"], y=y, mode="lines+markers", name=label))
    fig1.update_layout(
        title="Subsidios hidrocarburos — pesos constantes 2018",
        xaxis_title="Año",
        yaxis_title="Millones de pesos constantes 2018",
        legend_title="Fuente",
    )
    fig1.write_html(str(RESULTS / "subsidios_comparison_ars_constantes.html"))

    fig2 = go.Figure()
    for label, col in sources.items():
        if col in df.columns:
            y = df[col] / df["tcc"] / 1e6
            fig2.add_trace(go.Scatter(x=df["anio"], y=y, mode="lines+markers", name=label))
    fig2.update_layout(
        title="Subsidios hidrocarburos — millones de USD (TCC)",
        xaxis_title="Año",
        yaxis_title="Millones de USD (TCC)",
        legend_title="Fuente",
    )
    fig2.write_html(str(RESULTS / "subsidios_comparison_usd_tcc.html"))


def run(tcp_anual: pd.DataFrame, ganancia_pbi: pd.DataFrame, ipc: pd.DataFrame) -> dict:
    retenciones = build_retenciones(tcp_anual)
    regalias_result = build_regalias(tcp_anual)
    subsidios = build_subsidios(tcp_anual, ganancia_pbi, ipc)
    plot_subsidios_comparison(subsidios, ipc, tcp_anual)

    return dict(
        retenciones=retenciones,
        **regalias_result,
        subsidios=subsidios,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    aux = run_indices()
    result = run(aux["tcp_anual"], aux["ganancia_pbi"], aux["ipc"])
    print("fiscalidad OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
