"""
Company assets (balance sheets, AFIP, YPF historical segments).
Replaces Section 9+10 (Activos) of preprocesamiento.Rmd (lines ~2656-2910).
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"


def build_stock_segmentos(ipc_18: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    YPF and Petrobras segment-level assets.
    Returns:
      stock_segmentos   — raw in current pesos, long form
      union_segmentos   — deflated to 2018 pesos, aggregated by sector+variable
    """
    ypf = pd.read_csv(DATA / "ypf/ypf_segmentos.csv").drop(columns=["...1"], errors="ignore")
    ypf["sector"] = ypf["sector"].replace("quimica", "petroquimica")
    ypf["anio"] = pd.to_datetime(ypf["fecha"]).dt.year
    ypf_sel = ypf[["anio", "empresa", "sector", "unidad"]].copy()
    ypf_sel["activo"] = ypf["activos"]

    pet = pd.read_csv(DATA / "balances/petrobras_arg_segmentos.csv").drop(columns=["...1"], errors="ignore")
    pet = pet.rename(columns={"fecha": "anio", "ppye": "prop_planta_equipo", "activos": "activo"})
    pet_sel = pet[["anio", "empresa", "unidad", "sector", "prop_planta_equipo", "activo"]].copy()

    # Melt to long form
    ypf_long = ypf_sel.melt(id_vars=["anio", "empresa", "sector", "unidad"],
                             var_name="variable", value_name="valor")
    pet_long = pet_sel.melt(id_vars=["anio", "empresa", "sector", "unidad"],
                             var_name="variable", value_name="valor")
    stock_seg = pd.concat([ypf_long, pet_long], ignore_index=True)
    stock_seg["unidad"] = "Millones de pesos corrientes"

    # Deflate to 2018 pesos
    union = stock_seg.copy()
    union["ipc_18"] = union["anio"].map(ipc_18)
    union["valor"] = union["valor"] / union["ipc_18"]
    union["unidad"] = "Millones de pesos 2018"
    union = union.drop(columns=["ipc_18"])
    union = (
        union.groupby(["anio", "sector", "variable", "unidad"])["valor"]
        .sum()
        .reset_index()
    )
    union["fuente"] = "Activo de YPF y Petrobras"
    union["variable_sector"] = union["variable"] + " " + union["sector"]

    return stock_seg, union


def build_stock_balances_empresas(ipc_18: pd.Series) -> pd.DataFrame:
    """
    Company-level assets from balance sheets (Bolsar).
    Deflated to 2018 pesos.
    """
    df = pd.read_csv(DATA / "balances/balances_arg.csv",
                     usecols=lambda c: c not in ["...1", "Unnamed: 0"])
    df = df[~df["empresa"].isin(["chevron_global", "petrobras_global"])]
    df["anio"] = pd.to_datetime(df["fecha"]).dt.year
    df["fuente"] = "Bolsar"
    df["unidad"] = "Millones de pesos 2018"
    drop_cols = ["fecha", "pais", "tg_ant", "tg_desp", "rotacion"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    id_cols = ["anio", "fuente", "unidad", "empresa", "sector"]
    val_cols = [c for c in df.columns if c not in id_cols]
    long = df.melt(id_vars=id_cols, value_vars=val_cols, var_name="variable", value_name="valor")

    long["ipc_18"] = long["anio"].map(ipc_18)
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce") / long["ipc_18"]

    empresa_map = {
        "petrobras_ar": "Petrobras",
        "tecpetrol": "Tecpetrol",
        "camuzzi_pamp": "Camuzzi Gas Pampeana",
        "metrogas": "Metrogas",
    }
    long["empresa"] = long["empresa"].replace(empresa_map)

    long = (
        long.groupby(["anio", "empresa", "fuente", "sector", "unidad", "variable"])["valor"]
        .sum()
        .reset_index()
    )
    keep_vars = ["KTA", "ppye", "ppye_neta", "inventarios", "activo_no_corr", "activo"]
    return long[long["variable"].isin(keep_vars)].reset_index(drop=True)


def build_stock_balances_rama(
    stock_balances_empresas: pd.DataFrame,
    union_segmentos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Branch-level capital stock: company balance sheets + YPF/Petrobras upstream segment.
    """
    upstream_ppye = union_segmentos[
        union_segmentos["variable_sector"] == "activo upstream"
    ].copy()
    upstream_ppye["sector"] = "produccion"
    upstream_ppye["variable"] = "ppye"
    upstream_ppye["fuente"] = "Bolsar"
    upstream_ppye["empresa"] = "YPF y Petrobras"
    upstream_ppye = upstream_ppye.drop(columns=["variable_sector"])

    combined = pd.concat([
        stock_balances_empresas.reset_index(drop=True),
        upstream_ppye[["anio", "sector", "variable", "unidad", "fuente", "valor"]],
    ], ignore_index=True)

    return (
        combined.groupby(["anio", "sector", "variable", "unidad", "fuente"])["valor"]
        .sum()
        .reset_index()
    )


def build_stock_afip(ipc_18: pd.Series) -> pd.DataFrame:
    """
    AFIP capital stock for extraction and petroleum services sectors.
    Deflated to 2018 pesos.
    """
    df = pd.read_excel(DATA / "afip/gcia_v8.xlsx", skiprows=4)
    df = df.iloc[:, :48]  # drop columns 49+
    df = df.rename(columns={"year": "anio", "idrama": "idsector"})
    df["sector"] = np.where(
        df["rama"] == "petro", "extraccion_petroleo_gas",
        np.where(df["rama"] == "ser_petro", "servicios_petroleros", df["rama"])
    )
    df["unidad"] = "pesos corrientes"

    agg = (
        df.groupby(["anio", "idsector", "sector", "unidad"])
        .apply(lambda g: pd.Series({
            "KTA": g[["disponibilidades", "bscambio", "inventarios", "bsuso"]].sum(axis=1).sum(),
            "ppye": g["bsuso"].sum(),
            "activo": g["activo"].sum(),
        }))
        .reset_index()
    )
    agg["ipc_18"] = agg["anio"].map(ipc_18)
    for col in ["KTA", "ppye", "activo"]:
        agg[col] = (agg[col] / 1e6) / agg["ipc_18"]
    agg["unidad"] = "Millones de pesos 2018"
    agg = agg.drop(columns=["ipc_18", "idsector"])

    agg = agg[agg["sector"].isin(["extraccion_petroleo_gas", "servicios_petroleros"])]
    long = agg.melt(id_vars=["anio", "sector", "unidad"],
                    value_vars=["KTA", "ppye", "activo"],
                    var_name="variable", value_name="valor")
    long["fuente"] = "AFIP"
    return long.sort_values(["sector", "anio"]).reset_index(drop=True)


def build_balance_ypf(ipc_18: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    YPF historical balance sheet (Betania spreadsheet).
    Returns: balance_ypf (wide), stock_ypf (long, KTA/activo/ppye only)
    """
    df = pd.read_excel(
        DATA / "ypf/Calculos Betania Tg.xls",
        sheet_name="YPF_A $HOY_PARADEFLACYCALCULAR",
        skiprows=1,
    )
    df = df.iloc[:, :11].apply(pd.to_numeric, errors="coerce")
    df = df.rename(columns={
        "Año": "anio",
        "moneda": "unidad",
        "Ventas...3": "ventas",
        "Costo de las Ventas...4": "costo_ventas",
        "Utilidad neta": "utilidad_neta",
        "Utilidad operativa": "utilidad_operativa",
        "Bs Uso": "ppye",
        "Bs Cambio": "bienes_de_cambio",
        "UN antes de impuestos (g´ activos y dividendos)": "utilidad_neta_antes_impuestos",
        "Activo Total": "activo",
        "Patrimonio Neto": "patrimonio_neto",
    })
    df = df.dropna(subset=["anio"])
    num_cols = [c for c in df.columns if c not in ("anio", "unidad")]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 1e6

    df["ipc_18"] = df["anio"].map(ipc_18)
    for col in num_cols:
        df[col] = df[col] / df["ipc_18"]
    df["unidad"] = "Millones de pesos  de 2018"
    df["KTA"] = df["ppye"] + df["bienes_de_cambio"]
    df["sector"] = "Memoria de YPF"
    df = df.drop(columns=["ipc_18"])

    # Zero out known bad years
    bad_years = [1983, 1985, 1986, 1987, 1988]
    for col in ["KTA", "activo", "ppye"]:
        df.loc[df["anio"].isin(bad_years), col] = 0

    stock_ypf = df.melt(
        id_vars=["anio", "sector", "unidad"],
        value_vars=["KTA", "activo", "ppye"],
        var_name="variable",
        value_name="valor",
    )
    return df, stock_ypf


def run(ipc_18: pd.Series) -> dict:
    stock_seg, union_seg = build_stock_segmentos(ipc_18)
    stock_empresas = build_stock_balances_empresas(ipc_18)
    stock_rama = build_stock_balances_rama(stock_empresas, union_seg)
    stock_afip = build_stock_afip(ipc_18)
    balance_ypf, stock_ypf = build_balance_ypf(ipc_18)

    stock_total = pd.concat([stock_afip, stock_rama], ignore_index=True)

    return dict(
        stock_segmentos=stock_seg,
        union_segmentos=union_seg,
        stock_balances_empresas=stock_empresas,
        stock_balances_rama=stock_rama,
        stock_afip=stock_afip,
        balance_ypf=balance_ypf,
        stock_ypf=stock_ypf,
        stock_rama=stock_total,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    aux = run_indices()
    result = run(aux["ipc_18"])
    print("activos OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
