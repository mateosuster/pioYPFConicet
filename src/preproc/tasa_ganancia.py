"""
Profit rates and enterprise-captured rent for the hydrocarbon sector.
Replaces Section '# Tasa de ganancia y renta apropiada por las empresas'
of preprocesamiento.Rmd (lines ~3498-3678).
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"
RESULTS = ROOT / "results" / "argentina"


def _load_tg_industrial() -> pd.DataFrame:
    """Industrial profit rate benchmarks (JIC pre-1993, EM post-1993)."""
    df = pd.read_csv(DATA / "ccnn/tg_industrial.csv", sep=";")
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    return df


def _load_renta_empresa() -> pd.DataFrame:
    """Company-level rent from balance sheets."""
    df = pd.read_csv(
        DATA / "balances/renta_empresa.csv",
        usecols=lambda c: c not in ["Unnamed: 0", "X1"],
    )
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["anio"] = df["fecha"].dt.year
    return df


def build_tasa_ganancia_rama(
    empalme_ccnn: pd.DataFrame,
    stock_estimado: pd.DataFrame,
    ipc: pd.DataFrame,
) -> pd.DataFrame:
    """
    Sector profit rate using empalme_ccnn.pv and Bolsar stock.
    tasa_ganancia = pv / ppye_real
    """
    ipc_map = ipc.set_index("anio")["ipc_18"]
    stock_bolsar = stock_estimado[stock_estimado["fuente_ppye"] == "Bolsar"].copy()
    stock_bolsar["ipc_18"] = stock_bolsar["anio"].map(ipc_map)
    stock_bolsar["ppye"] = stock_bolsar["valor"] * stock_bolsar["ipc_18"]
    stock_bolsar["fuente_pozo"] = "Estimación sin pozos"

    pv_df = (
        empalme_ccnn[["anio", "unidad", "pv"]]
        .drop_duplicates()
        .query("anio > 1997")
    )

    df = pv_df.merge(
        stock_bolsar[["anio", "ppye", "fuente_ppye", "fuente_pozo"]],
        on="anio",
        how="left",
    )
    df["tasa_ganancia"] = df["pv"] / df["ppye"]
    df = df[df["fuente_ppye"].notna()].rename(columns={"fuente_ppye": "stock_seleccionado"})
    return df[["anio", "unidad", "pv", "ppye", "stock_seleccionado", "tasa_ganancia"]].copy()


def build_tasa_ganancia_rama_stock(
    valor_total_produccion: pd.DataFrame,
    stock_estimado: pd.DataFrame,
) -> pd.DataFrame:
    """
    Profit rate using criterio_propio ebe_tot and all stock estimates.
    tasa_ganancia = ebe_tot / ppye
    """
    ebe = (
        valor_total_produccion[
            (valor_total_produccion["variable"] == "ebe_tot")
            & (valor_total_produccion["fuente"] == "Criterio propio")
        ][["anio", "unidad", "valor"]]
        .rename(columns={"valor": "excedente_bruto_explotacion"})
    )

    stock = stock_estimado[["anio", "valor", "fuente_ppye"]].copy()
    stock = stock.rename(columns={"valor": "ppye", "fuente_ppye": "stock_seleccionado"})

    df = ebe.merge(stock, on="anio", how="left")
    df["tasa_ganancia"] = df["excedente_bruto_explotacion"] / df["ppye"]
    return df[["anio", "unidad", "excedente_bruto_explotacion", "ppye", "stock_seleccionado", "tasa_ganancia"]].copy()


def build_renta_tg(
    tasa_ganancia_rama: pd.DataFrame,
    tg_industrial: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rent appropriated by enterprises via profit rate differential.
    renta_con_tg = ppye * (tg_hidrocarburos - tg_industrial_benchmark)
    """
    df = tasa_ganancia_rama[["anio", "unidad", "ppye", "stock_seleccionado", "tasa_ganancia"]].copy()
    df = df.merge(tg_industrial, on="anio", how="left")
    df = df.rename(columns={"tasa_ganancia": "tg_hidrocarburos"})

    df["union_tg"] = np.where(df["anio"] < 1993, df["tg_indu_jic"], df["tg_indu_em"])
    df["renta_con_tg_jic"] = df["ppye"] * (df["tg_hidrocarburos"] - df["tg_indu_jic"])
    df["renta_con_tg_em"] = df["ppye"] * (df["tg_hidrocarburos"] - df["tg_indu_em"])
    df["renta_con_tg_union"] = df["ppye"] * (df["tg_hidrocarburos"] - df["union_tg"])
    return df.drop_duplicates().reset_index(drop=True)


def build_renta_produccion_balances(renta_empresa: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate company balance-sheet rent for production/integrated sectors.
    """
    excl = {"chevron_global", "petrobras_global"}
    df = renta_empresa[
        ~renta_empresa["empresa"].isin(excl)
        & renta_empresa["sector"].isin(["integrada", "produccion"])
    ].copy()

    agg_cols = {
        "KTA": "sum",
        "gcia_ant": "sum",
        "renta_ant_corr": "sum",
        "renta_desp_corr": "sum",
    }
    # Use available columns only
    agg = {k: v for k, v in agg_cols.items() if k in df.columns}

    grp_cols = ["anio"]
    if "moneda" in df.columns:
        grp_cols = ["anio", "moneda"]

    result = df.groupby(grp_cols, as_index=False).agg(
        KTA=("KTA", "sum") if "KTA" in df.columns else ("gcia_ant", "sum"),
        **{k: (k, "sum") for k in ["gcia_ant", "renta_ant_corr", "renta_desp_corr"] if k in df.columns},
    )
    if "moneda" in result.columns:
        result = result.rename(columns={"moneda": "unidad"})
    return result.sort_values("anio").reset_index(drop=True)


def run(
    empalme_ccnn: pd.DataFrame,
    valor_total_produccion: pd.DataFrame,
    stock_estimado: pd.DataFrame,
    ipc: pd.DataFrame,
) -> dict:
    tg_industrial = _load_tg_industrial()
    renta_empresa = _load_renta_empresa()

    tg_rama = build_tasa_ganancia_rama(empalme_ccnn, stock_estimado, ipc)
    tg_rama_stock = build_tasa_ganancia_rama_stock(valor_total_produccion, stock_estimado)
    renta_tg = build_renta_tg(tg_rama, tg_industrial)
    renta_prod_balances = build_renta_produccion_balances(renta_empresa)

    # Write output
    RESULTS.mkdir(parents=True, exist_ok=True)
    tg_rama_stock.to_csv(RESULTS / "tasa_ganancia_rama_stock.csv", index=False)
    print(f"  tasa_ganancia_rama_stock.csv: {tg_rama_stock.shape}")

    return dict(
        tasa_ganancia_rama=tg_rama,
        tasa_ganancia_rama_stock=tg_rama_stock,
        renta_tg=renta_tg,
        renta_produccion_balances=renta_prod_balances,
    )


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parents[1]))
    from preproc.indices_precios import run as run_idx
    from preproc.produccion import run as run_prod
    from preproc.precios_mi import run as run_mi
    from preproc.precios_me import run as run_me
    from preproc.comex import run as run_cx
    from preproc.empleo import run as run_emp
    from preproc.valor_produccion import run as run_vp

    idx = run_idx()
    prod = run_prod()
    prec = run_mi(idx["tcp_anual"], idx["ipc"], idx["ipim"], idx["conversor_pesos"])
    pme = run_me(idx["tcp_anual"], idx["ipc"], idx["conversor_pesos"])
    cx = run_cx()
    emp = run_emp(idx["conversor_pesos"])

    vprod = run_vp(
        masa_salarial_hidrocarburos=emp["masa_salarial_hidrocarburos"],
        prod_crudo=prod["prod_crudo"],
        expo_crudo=cx["expo_crudo"],
        prod_gas_mmbtu=prod["prod_gas_mmbtu"],
        expo_gas=cx["expo_gas"],
        precio_crudo_mi=prec["precio_crudo_mi"],
        precio_gas_mi_usd_mmbtu=prec["precio_gas_mi_usd_mmbtu"],
        precio_mdomundial_gas=pme["precio_mdomundial_gas_MMBTU"],
        precios_referencia_crudo=pme["precios_referencia_crudo"],
        tcp_anual=idx["tcp_anual"],
        ipc=idx["ipc"],
    )

    result = run(
        empalme_ccnn=vprod["empalme_ccnn"],
        valor_total_produccion=vprod["valor_total_produccion"],
        stock_estimado=vprod["stock_estimado"],
        ipc=idx["ipc"],
    )
    print("tasa_ganancia OK")
    for k, v in result.items():
        if isinstance(v, pd.DataFrame):
            print(f"  {k}: {v.shape}")
