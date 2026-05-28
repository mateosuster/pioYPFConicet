"""
Domestic market prices for crude oil and natural gas.
Replaces Section 3 (Precio del mercado interno) of preprocesamiento.Rmd (lines ~728-1120).
"""

from pathlib import Path
import pandas as pd
import numpy as np

from utils.conversores import m3_to_bbl_p, m3_to_mmbtu_p
from utils.indices import generar_indice

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"
UPDATE = ROOT / "update"


def _load_mecon_base() -> pd.DataFrame:
    df = pd.read_csv(DATA / "mecon/hidrocarburos_produccion.csv", encoding="ISO-8859-1")
    df["fecha"] = pd.to_datetime(df["indice_tiempo"], dayfirst=True, errors="coerce")
    drop = [c for c in df.columns[:3]] + ["fuente", "indice_tiempo", "alcance_id"]
    df = df.drop(columns=[c for c in drop if c in df.columns], errors="ignore")
    df.insert(0, "fecha", df.pop("fecha"))
    return df


def _load_mecon_update() -> pd.DataFrame:
    return pd.read_csv(UPDATE / "hidrocarburos.csv", encoding="ISO-8859-1")


# ===== CRUDE OIL =====

def build_precio_mi_crudo(
    tcp_anual: pd.DataFrame,
    ipim: pd.DataFrame,
) -> pd.DataFrame:
    """
    Annual domestic crude oil price from multiple sources (USD/bbl).
    Primary series: idee 1963-1988, ypf 1989-1991, mecon 1992+
    """
    from preproc.indices_precios import YEAR_LAST

    mecon_base = _load_mecon_base()
    indicadores = mecon_base["indicador"].unique()

    # YPF memorials
    ypf = pd.read_excel(DATA / "ypf/vtas_valor_cantidad_precio_crudo.xlsx")
    ypf = ypf.rename(columns={
        "m3": "cant_vendida",
        "valor": "valor_vendido",
        "$/m3": "precio_a",
        "Cotiz dic U$S": "tcc_dic",
        "U$S (a diciembre de cada año)": "precio_usd",
    })
    ypf["precio_mi_pesos_ypf_crudo"] = ypf["valor_vendido"] / ypf["cant_vendida"]
    ypf["precio_mi_ypf_crudo"] = ypf["precio_mi_pesos_ypf_crudo"] / ypf["tcc_dic"]
    ypf = ypf[["anio", "moneda", "valor_vendido", "cant_vendida",
               "precio_mi_pesos_ypf_crudo", "tcc_dic", "precio_mi_ypf_crudo"]]

    # MECON historical
    mecon_hist = (
        mecon_base[
            (mecon_base["indicador"] == indicadores[1])
            & (mecon_base["actividad_producto_nombre"] == "Petróleo crudo")
            & (mecon_base["alcance_tipo"] == "PAIS")
        ]
        .copy()
    )
    mecon_hist["anio"] = mecon_hist["fecha"].dt.year
    mecon_hist = (
        mecon_hist.groupby("anio")["valor"].mean().reset_index()
        .rename(columns={"valor": "precio_mi_mecon_crudo"})
    )
    mecon_hist["unidad"] = "USD/m3"

    # MECON update
    upd = _load_mecon_update()
    upd_crudo = upd[
        (upd["indicador"] == "Precio interno_promedios ponderados por volumen de venta")
        & (upd["actividad_producto_nombre"] == "Petróleo crudo")
        & (upd["alcance_tipo"] == "PAIS")
    ].copy()
    upd_crudo["anio"] = pd.to_datetime(upd_crudo["indice_tiempo"]).dt.year
    upd_crudo = (
        upd_crudo[upd_crudo["anio"] > mecon_hist["anio"].max()]
        .groupby("anio")["valor"]
        .mean()
        .reset_index()
        .rename(columns={"valor": "precio_mi_mecon_crudo"})
    )
    upd_crudo["unidad"] = "USD/m3"
    mecon_crudo = pd.concat([mecon_hist, upd_crudo], ignore_index=True)

    # Regalías
    reg = pd.read_csv(
        DATA / "secretaria_energia/regalias/precio_mercado_interno_crudo_regalias.csv",
        sep=";",
    )
    reg = reg.rename(columns={"AÑO": "anio", "MES": "mes", "TOTAL TIPO DE CRUDO": "total_tipo_crudo"})
    reg["anio"] = reg["anio"].ffill()
    reg["unidad"] = "USD/m3"
    reg = reg[reg["anio"] >= 2006]
    precio_regalias = (
        reg.groupby(["anio", "unidad"])["total_tipo_crudo"]
        .mean()
        .reset_index()
        .rename(columns={"total_tipo_crudo": "precio_mi_regalias_crudo"})
    )

    # IDEE
    idee = pd.read_excel(
        DATA / "idee/Precios del petroleo crudo y derivados 1970 - 1989.xlsx",
        skiprows=1,
        sheet_name=3,
    )
    if "precio_crudo_neuquina_tc_oficial" in idee.columns:
        idee_crudo = idee[["anio", "precio_crudo_neuquina_tc_oficial"]].rename(
            columns={"precio_crudo_neuquina_tc_oficial": "precio_mi_idee_crudo"}
        )
    else:
        idee_crudo = pd.DataFrame(columns=["anio", "precio_mi_idee_crudo"])

    # IPIM for estimation
    ipim_col = ipim[["anio", "ipim_nivel_gral_94"]].copy()

    # Merge all price sources with outer joins so no year from any source is lost.
    # ipim_col is an auxiliary deflator (not a price source), so left is correct there.
    df = (
        precio_regalias[["anio", "unidad", "precio_mi_regalias_crudo"]]
        .merge(mecon_crudo, on=["anio", "unidad"], how="outer")
        .merge(ypf[["anio", "precio_mi_ypf_crudo"]], on="anio", how="outer")
        .merge(idee_crudo, on="anio", how="outer")
        .merge(ipim_col, on="anio", how="left")
    )

    # Convert all USD/m3 → USD/bbl
    for col in ["precio_mi_regalias_crudo", "precio_mi_mecon_crudo",
                "precio_mi_ypf_crudo", "precio_mi_idee_crudo"]:
        if col in df.columns:
            df[col] = m3_to_bbl_p(pd.to_numeric(df[col], errors="coerce"))

    df = df.sort_values("anio").reset_index(drop=True)

    # Estimation for 1963-1965 (IDEE indexed from 1972 via YPF)
    if "precio_mi_ypf_crudo" in df.columns and "precio_mi_idee_crudo" in df.columns:
        ypf_1972 = df.loc[df["anio"] == 1972, "precio_mi_ypf_crudo"]
        idee_1972 = df.loc[df["anio"] == 1972, "precio_mi_idee_crudo"]
        ypf_1972_val = ypf_1972.iloc[0] if len(ypf_1972) else np.nan
        idee_1972_val = idee_1972.iloc[0] if len(idee_1972) else np.nan

        df["indice_ypf_72"] = df["precio_mi_ypf_crudo"] / ypf_1972_val if not np.isnan(ypf_1972_val) else np.nan
        df["idee_estimado"] = idee_1972_val * df["indice_ypf_72"]

        mecon_1994 = df.loc[df["anio"] == 1994, "precio_mi_mecon_crudo"]
        mecon_1994_val = mecon_1994.iloc[0] if len(mecon_1994) else np.nan
        df["mecon_estimado"] = mecon_1994_val * df["ipim_nivel_gral_94"]

    conditions = [
        df["anio"].between(1963, 1965),
        df["anio"].between(1966, 1988),
        df["anio"].between(1989, 1991),
        df["anio"] == 1992,
        df["anio"] > 1992,
    ]
    choices = [
        df.get("idee_estimado", np.nan),
        df.get("precio_mi_idee_crudo", np.nan),
        df.get("precio_mi_ypf_crudo", np.nan),
        df.get("mecon_estimado", np.nan),
        df.get("precio_mi_mecon_crudo", np.nan),
    ]
    df["precio_crudo_mdoint"] = np.select(conditions, choices, default=np.nan)
    df["unidad"] = "USD/barriles"
    df["variable"] = "Precio del mercado interno del petróleo crudo según distintas fuentes"

    drop_temp = ["ipim_nivel_gral_94", "idee_estimado", "mecon_estimado", "indice_ypf_72"]
    df = df.drop(columns=[c for c in drop_temp if c in df.columns])

    df = df.rename(columns={
        "precio_mi_regalias_crudo": "regalias",
        "precio_mi_mecon_crudo": "mecon",
        "precio_mi_ypf_crudo": "ypf",
        "precio_mi_idee_crudo": "idee",
    })
    df = df[df["anio"] <= YEAR_LAST]
    front = ["anio", "unidad", "variable", "precio_crudo_mdoint"]
    rest = [c for c in df.columns if c not in front]
    return df[front + rest].reset_index(drop=True)


# ===== NATURAL GAS =====

def build_precio_mi_gas(
    tcp_anual: pd.DataFrame,
    ipc: pd.DataFrame,
    conversor_pesos: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Annual domestic gas price.
    Returns:
      precio_mi_gas    — ARS/Miles de m3
      precio_mi_gas_mmbtu — ARS/MMBTU
      precio_interno_gas_mmbtu_usd — USD/MMBTU
    """
    from preproc.indices_precios import YEAR_LAST

    mecon_base = _load_mecon_base()
    indicadores = mecon_base["indicador"].unique()
    ipc_70 = ipc.set_index("fecha")["ipc_70"] if "fecha" in ipc.columns else ipc.set_index("anio")["ipc_70"]

    # YPF memorials gas
    ypf_crudo = pd.read_excel(DATA / "ypf/vtas_valor_cantidad_precio_crudo.xlsx")
    ypf_crudo = ypf_crudo.rename(columns={"Cotiz dic U$S": "tcc_dic"})
    ypf_crudo = ypf_crudo[["anio", "moneda", "tcc_dic"]]

    ypf_gas = pd.read_excel(DATA / "ypf/vtas_valor_cantidad_precio_gas.xlsx")
    ypf_gas = ypf_gas.rename(columns={"m3": "cant_vendida", "$": "valor_vendido", "Moneda": "moneda"})
    ypf_gas = ypf_gas.merge(ypf_crudo[["anio", "moneda", "tcc_dic"]], on=["anio", "moneda"], how="left")
    ypf_gas["precio_mi_ypf_gas_moneda_original"] = (ypf_gas["valor_vendido"] / ypf_gas["cant_vendida"]) / 1000
    ypf_gas["precio_mi_usd_ypf_gas"] = ypf_gas["precio_mi_ypf_gas_moneda_original"] / ypf_gas["tcc_dic"]

    conditions = [
        ypf_gas["moneda"] == "m$n",
        ypf_gas["moneda"] == "$ley",
        ypf_gas["moneda"] == "$arg",
        ypf_gas["moneda"] == "A",
    ]
    choices = [
        ypf_gas["precio_mi_ypf_gas_moneda_original"] / conversor_pesos["m$n"],
        ypf_gas["precio_mi_ypf_gas_moneda_original"] / conversor_pesos["$Ley"],
        ypf_gas["precio_mi_ypf_gas_moneda_original"] / conversor_pesos["$a"],
        ypf_gas["precio_mi_ypf_gas_moneda_original"] / conversor_pesos["A"],
    ]
    ypf_gas["precio_mi_ypf_gas"] = np.select(conditions, choices,
                                               default=ypf_gas["precio_mi_ypf_gas_moneda_original"])
    ypf_gas["unidad"] = "ars/Miles de m3"

    # MECON gas historical
    mecon_hist_gas = (
        mecon_base[
            (mecon_base["indicador"] == indicadores[1])
            & (mecon_base["actividad_producto_nombre"] == "Gas natural")
            & (mecon_base["alcance_tipo"] == "PAIS")
        ]
        .copy()
    )
    mecon_hist_gas["anio"] = mecon_hist_gas["fecha"].dt.year
    mecon_hist_gas = (
        mecon_hist_gas.groupby("anio")["valor"].mean().reset_index()
        .rename(columns={"valor": "precio_mi_mecon_gas"})
    )
    mecon_hist_gas["unidad"] = "ars/Miles de m3"

    upd = _load_mecon_update()
    upd_gas = upd[
        (upd["indicador"] == "Precio interno_promedios ponderados por volumen de venta")
        & (upd["actividad_producto_nombre"] == "Gas natural")
        & (upd["alcance_tipo"] == "PAIS")
    ].copy()
    upd_gas["anio"] = pd.to_datetime(upd_gas["indice_tiempo"]).dt.year
    upd_gas = (
        upd_gas[upd_gas["anio"] > mecon_hist_gas["anio"].max()]
        .groupby("anio")["valor"].mean().reset_index()
        .rename(columns={"valor": "precio_mi_mecon_gas"})
    )
    upd_gas["unidad"] = "ars/Miles de m3"
    mecon_gas = pd.concat([mecon_hist_gas, upd_gas], ignore_index=True)

    # Regalías gas pre-1999
    reg_pre99 = pd.read_excel(
        DATA / "secretaria_energia/regalias/precio_mi_gas.xlsx", sheet_name="jk"
    )
    reg_pre99 = reg_pre99[reg_pre99["anio"] < 1999].copy()
    reg_pre99["precio_total_gas"] = reg_pre99["precio_mi_gas"] * 1000
    reg_pre99["unidad"] = "ars/Miles de m3"
    reg_pre99 = reg_pre99[["anio", "precio_total_gas", "unidad"]]

    # Regalías gas post-1999
    reg_post = pd.read_csv(
        DATA / "secretaria_energia/regalias/precio_mercado_interno_gas_regalias.csv",
        sep=";",
    )
    reg_post = reg_post.rename(columns={"AÑO": "anio", "MES": "mes", "TOTAL CUENCA": "total_cuenca"})
    reg_post["anio"] = reg_post["anio"].ffill()
    reg_post["unidad"] = "ars/Miles de m3"
    # Melt all cuenca columns
    id_cols = ["anio", "mes", "unidad"]
    val_cols = [c for c in reg_post.columns if c not in id_cols]
    reg_post_long = reg_post.melt(id_vars=id_cols, value_vars=val_cols,
                                   var_name="cuenca", value_name="valor")
    reg_post_long["valor"] = pd.to_numeric(
        reg_post_long["valor"].astype(str).str.replace(",", ""), errors="coerce"
    )
    reg_post_mean = (
        reg_post_long[reg_post_long["cuenca"] == "total_cuenca"]
        .groupby(["anio", "unidad", "cuenca"])["valor"].mean().reset_index()
        .rename(columns={"valor": "precio_promedio_cuenca"})
    )
    reg_post_mean = reg_post_mean.merge(reg_pre99[["anio", "precio_total_gas"]], on="anio", how="outer")
    reg_post_mean["precio_mi_regalias_gas"] = np.where(
        reg_post_mean["anio"] < 1999,
        reg_post_mean["precio_total_gas"],
        reg_post_mean["precio_promedio_cuenca"],
    )

    # IDEE gas
    idee_gas = pd.read_excel(
        DATA / "idee/Precios del gas natural y derivados 1970 - 1988.xlsx",
        skiprows=1,
        sheet_name=1,
    )
    if "precio_transferencia" in idee_gas.columns:
        idee_gas = idee_gas[["anio", "unidad", "precio_transferencia"]].copy()
        ipc_70_ser = ipc.set_index("anio")["ipc_70"] if "ipc_70" in ipc.columns else None
        if ipc_70_ser is not None:
            idee_gas["ipc_70"] = idee_gas["anio"].map(ipc_70_ser)
            idee_gas["precio_mi_indexado_pesos"] = (
                idee_gas["precio_transferencia"] * idee_gas["ipc_70"] / conversor_pesos["$Ley"]
            )
            tcp_tcc = tcp_anual.set_index("anio")["tcc"]
            idee_gas["tcc"] = idee_gas["anio"].map(tcp_tcc)
            idee_gas["precio_mi_indexado_usd"] = idee_gas["precio_mi_indexado_pesos"] / idee_gas["tcc"]

    # Anuario combustible
    anuario = pd.read_excel(DATA / "anuario_de_combustibles/anuario de combustible.xlsx")
    anuario = anuario[anuario["mercancia"] == "gas_natural"]
    anuario = (
        anuario.groupby(["anio", "mes", "unidad"])["valor"].mean().reset_index()
        .groupby(["anio", "unidad"])["valor"].mean().reset_index()
        .rename(columns={"valor": "precio_mi_anuario_gas"})
    )
    anuario["precio_mi_anuario_gas"] = (
        anuario["precio_mi_anuario_gas"] / conversor_pesos["A"] / 1000
    )
    anuario["unidad"] = "ars/Miles de m3"

    # Merge
    df = (
        reg_post_mean[["anio", "unidad", "precio_mi_regalias_gas"]]
        .merge(mecon_gas, on=["anio", "unidad"], how="outer")
        .merge(ypf_gas[["anio", "precio_mi_ypf_gas"]], on="anio", how="outer")
    )
    if "precio_mi_indexado_pesos" in idee_gas.columns:
        df = df.merge(idee_gas[["anio", "precio_mi_indexado_pesos"]].rename(
            columns={"precio_mi_indexado_pesos": "precio_mi_idee_indexado"}
        ), on="anio", how="outer")
    df = df.merge(anuario[["anio", "precio_mi_anuario_gas"]], on="anio", how="outer")

    conditions = [
        df["anio"].between(1970, 1988),
        df["anio"].between(1992, 2021),
        df["anio"] > 2021,
    ]
    choices = [
        df.get("precio_mi_idee_indexado", np.nan),
        df.get("precio_mi_regalias_gas", np.nan),
        df.get("precio_mi_mecon_gas", np.nan),
    ]
    df["precio_gas_mdoint"] = np.select(conditions, choices, default=np.nan)
    df["variable"] = "Precio del mercado interno del gas natural según distintas fuentes"
    df["unidad"] = "ars/Miles de m3"

    df = df.rename(columns={
        "precio_mi_regalias_gas": "regalias",
        "precio_mi_mecon_gas": "mecon",
        "precio_mi_ypf_gas": "ypf",
        "precio_mi_idee_indexado": "idee",
        "precio_mi_anuario_gas": "anuario",
    })
    df = df[df["anio"] <= YEAR_LAST].sort_values("anio").reset_index(drop=True)

    # Convert to MMBTU (ARS/Miles m3 / 1000 = ARS/m3 → ARS/MMBTU)
    numeric_cols = [c for c in df.columns if c not in ("anio", "variable", "unidad")]
    mmbtu = df.copy()
    for col in numeric_cols:
        mmbtu[col] = m3_to_mmbtu_p(pd.to_numeric(df[col], errors="coerce") / 1000)
    mmbtu["unidad"] = "ars/MMBTU"

    # USD/MMBTU
    tcc_map = tcp_anual.set_index("anio")["tcc"]
    usd_mmbtu = mmbtu.copy()
    usd_mmbtu["tcc"] = usd_mmbtu["anio"].map(tcc_map)
    for col in numeric_cols:
        usd_mmbtu[col] = pd.to_numeric(usd_mmbtu[col], errors="coerce") / usd_mmbtu["tcc"]
    usd_mmbtu = usd_mmbtu.drop(columns=["tcc"])
    usd_mmbtu["unidad"] = "USD/MMBTU"

    return df, mmbtu, usd_mmbtu


def run(tcp_anual: pd.DataFrame, ipc: pd.DataFrame,
        ipim: pd.DataFrame, conversor_pesos: pd.Series) -> dict:
    precio_crudo = build_precio_mi_crudo(tcp_anual, ipim)
    precio_gas, precio_gas_mmbtu, precio_gas_usd = build_precio_mi_gas(tcp_anual, ipc, conversor_pesos)

    return dict(
        precio_crudo_mi=precio_crudo,
        precio_gas_mi=precio_gas,
        precio_gas_mi_mmbtu=precio_gas_mmbtu,
        precio_gas_mi_usd_mmbtu=precio_gas_usd,
    )


if __name__ == "__main__":
    from preproc.indices_precios import run as run_indices
    aux = run_indices()
    result = run(aux["tcp_anual"], aux["ipc"], aux["ipim"], aux["conversor_pesos"])
    print("precios_mi OK")
    for k, v in result.items():
        print(f"  {k}: {v.shape}")
