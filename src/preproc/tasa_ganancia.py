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

# Stock sources on renta_empresas sheet (aligned with tg_pg_total comparisons)
MULTI_STOCK_SOURCES = frozenset({"AFIP (combinada)", "Bolsar", "S&P Capital IQ"})


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
    valor_total_produccion: pd.DataFrame,
    stock_estimado: pd.DataFrame,
    stock_source: str = "Bolsar",
) -> pd.DataFrame:
    """
    Sector profit rate for the selected stock (Criterio propio EBE / ppye).

    Same numerator and denominator basis as ``build_tasa_ganancia_rama_stock`` and
  the ``renta_empresas`` sheet, so ``renta_tg`` matches ``renta_tg_multi`` for
    that source.
    """
    df = build_tasa_ganancia_rama_stock(valor_total_produccion, stock_estimado)
    df = df[df["stock_seleccionado"] == stock_source].copy()
    return df[df["anio"] > 1997].reset_index(drop=True)


def build_tasa_ganancia_rama_stock(
    valor_total_produccion: pd.DataFrame,
    stock_estimado: pd.DataFrame,
) -> pd.DataFrame:
    """
    Profit rate using criterio_propio PV (plusvalía neta) and all stock estimates.
    tasa_ganancia = pv / ppye

    PV = EBE_extr − ConKfijo − Imp  (net surplus after depreciation and generic taxes).
    Using PV ensures consistency with the direct rent formula:
      renta_empresas = ppye × (TG − TG_normal) = PV − ppye × TG_normal
    which equals renta_total + subsidios from build_renta_directo.
    """
    pv = (
        valor_total_produccion[
            (valor_total_produccion["variable"] == "pv")
            & (valor_total_produccion["fuente"] == "Criterio propio")
        ][["anio", "unidad", "valor"]]
        .rename(columns={"valor": "plusvalia"})
        .groupby(["anio", "unidad"], as_index=False)["plusvalia"].mean()
    )

    stock = stock_estimado[["anio", "valor", "fuente_ppye"]].copy()
    stock = stock.rename(columns={"valor": "ppye", "fuente_ppye": "stock_seleccionado"})

    df = pv.merge(stock, on="anio", how="left")
    df["tasa_ganancia"] = df["plusvalia"] / df["ppye"]
    df = df[df["anio"] >= 1993].reset_index(drop=True)
    return df[["anio", "unidad", "plusvalia", "ppye", "stock_seleccionado", "tasa_ganancia"]].copy()


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


def _append_stock_alt(
    stock_estimado: pd.DataFrame,
    stock_rama_alt: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate ppye from stock_rama_alt and append as 'S&P Capital IQ' rows."""
    ppye_alt = (
        stock_rama_alt[
            (stock_rama_alt["variable"] == "ppye")
            & (stock_rama_alt["unidad"] == "Millones de pesos corrientes")
            & (stock_rama_alt["sector"].isin(["integrada", "produccion"]))
        ]
        .groupby("anio", as_index=False)["valor"]
        .sum()
    )
    ppye_alt["fuente_ppye"] = "S&P Capital IQ"
    ppye_alt["unidad"] = "Millones de pesos corrientes"
    for c in stock_estimado.columns:
        if c not in ppye_alt.columns:
            ppye_alt[c] = pd.NA
    return pd.concat(
        [stock_estimado, ppye_alt[stock_estimado.columns]],
        ignore_index=True,
    )


def run(
    empalme_ccnn: pd.DataFrame,
    valor_total_produccion: pd.DataFrame,
    stock_estimado: pd.DataFrame,
    ipc: pd.DataFrame,
    stock_rama_alt: pd.DataFrame | None = None,
    stock_source: str = "Bolsar",
) -> dict:
    tg_industrial = _load_tg_industrial()
    renta_empresa = _load_renta_empresa()

    if stock_rama_alt is not None:
        stock_estimado = _append_stock_alt(stock_estimado, stock_rama_alt)

    tg_rama = build_tasa_ganancia_rama(
        valor_total_produccion, stock_estimado, stock_source=stock_source
    )
    tg_rama_stock = build_tasa_ganancia_rama_stock(valor_total_produccion, stock_estimado)
    renta_tg = build_renta_tg(tg_rama, tg_industrial)

    # Multi-source renta_empresas: EBE/ppye per stock (same basis as tg_pg_total sheet)
    tg_multi = tg_rama_stock[
        tg_rama_stock["stock_seleccionado"].isin(MULTI_STOCK_SOURCES)
        & tg_rama_stock["ppye"].notna()
        & tg_rama_stock["tasa_ganancia"].notna()
    ]
    renta_tg_multi = build_renta_tg(tg_multi, tg_industrial)

    renta_prod_balances = build_renta_produccion_balances(renta_empresa)

    # Write output
    RESULTS.mkdir(parents=True, exist_ok=True)
    tg_rama_stock.to_csv(RESULTS / "tasa_ganancia_rama_stock.csv", index=False)
    print(f"  tasa_ganancia_rama_stock.csv: {tg_rama_stock.shape}")

    return dict(
        tasa_ganancia_rama=tg_rama,
        tasa_ganancia_rama_stock=tg_rama_stock,
        renta_tg=renta_tg,
        renta_tg_multi=renta_tg_multi,
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
