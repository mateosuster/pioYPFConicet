"""
Total hydrocarbon rent via direct and indirect methods, cost structure, author comparison.
Replaces Sections '# Renta Hidrocarburífera Total', '## Costos', and
'# Comparación con estimación de otros autores' of preprocesamiento.Rmd (lines ~3801-4017).
"""

from pathlib import Path
import numpy as np
import pandas as pd

from utils.conversores import bep_to_mmbtu_p

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"


def _load_renta_autores() -> pd.DataFrame:
    path = DATA / "otros autores/renta_autores.csv"
    df = pd.read_csv(path, usecols=lambda c: c not in ["Unnamed: 0", ""])
    return df


def build_renta_directo(
    renta_tg: pd.DataFrame,
    criterio_propio: pd.DataFrame,
    subsidios: pd.DataFrame,
    ipc: pd.DataFrame,
    ganancia_pbi: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Direct-method rent (from profit rate differential).

    renta_total = pv/ipc_18 - ppye*tg_normal - subsidios_cefip/ipc_18
    All in Millones de pesos de 2018.
    """
    ipc_map = ipc.set_index("anio")["ipc_18"]

    # Filter to Bolsar stock
    df = renta_tg[renta_tg["stock_seleccionado"] == "Bolsar"][[
        "anio", "ppye", "tg_hidrocarburos", "union_tg"
    ]].rename(columns={"union_tg": "tg_normal"}).copy()

    # Join pv from criterio_propio (in current pesos)
    pv_df = criterio_propio[["anio", "pv"]].dropna(subset=["pv"])
    df = df.merge(pv_df, on="anio", how="left")

    # Subsidies in 2018 pesos
    if "subsidios_cefip" in subsidios.columns:
        sub = subsidios[["anio", "subsidios_cefip"]].copy()
    else:
        sub = subsidios[["anio"]].copy()
        sub["subsidios_cefip"] = np.nan
    sub = sub.merge(ipc[["anio", "ipc_18"]], on="anio", how="left")
    sub["subsidios"] = (sub["subsidios_cefip"] / 1e6) / sub["ipc_18"]
    sub["subsidios"] = sub["subsidios"].fillna(0)
    df = df.merge(sub[["anio", "subsidios"]], on="anio", how="left")

    # Deflate
    df["ipc_18"] = df["anio"].map(ipc_map)
    df["renta_con_tg_normal"] = (df["ppye"] / df["ipc_18"]) * (df["tg_hidrocarburos"] - df["tg_normal"])
    df["gcia_normal_hidrocarburos"] = df["ppye"] * df["tg_normal"]
    df["pv"] = df["pv"] / df["ipc_18"]
    df["renta_total"] = df["pv"] - df["gcia_normal_hidrocarburos"] - df["subsidios"]
    df["unidad"] = "Millones de pesos de 2018"
    df = df[df["anio"] > 1997].copy()

    # vs. PBI/ganancia
    renta_pbi_df = df.merge(
        ganancia_pbi.rename(columns={"unidad": "unidad_pbi_gcia"}),
        on="anio", how="left",
    )
    renta_pbi_df["renta_pv"] = (renta_pbi_df["renta_total"] * renta_pbi_df["ipc_18"]) / renta_pbi_df["ganancia"]
    renta_pbi_df["renta_pbi"] = (renta_pbi_df["renta_total"] * renta_pbi_df["ipc_18"]) / renta_pbi_df["pbi"]

    return df, renta_pbi_df


def build_renta_indirecto(
    renta_crudo_dif: pd.DataFrame,
    renta_gas_dif: pd.DataFrame,
    retenciones_regalias: pd.DataFrame,
    renta_tcp_crudo: pd.DataFrame,
    renta_tcp_gas: pd.DataFrame,
    subsidios: pd.DataFrame,
    renta_tg: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    ipc: pd.DataFrame,
    ganancia_pbi: pd.DataFrame,
) -> pd.DataFrame:
    """
    Indirect-method rent = sum of all rent mechanisms.
    All components converted to Millones de pesos de 2018.
    """
    # Retenciones column
    ret_col = "retenciones_crudo_jk" if "retenciones_crudo_jk" in retenciones_regalias.columns else "retenciones_crudo"

    df = renta_crudo_dif[["anio", "renta_dif_precios_crudo"]].merge(
        renta_gas_dif[["anio", "renta_dif_precios_gas"]], on="anio", how="outer"
    ).merge(
        retenciones_regalias[["anio", ret_col, "regalias_total"]].rename(
            columns={ret_col: "retenciones"}
        ), on="anio", how="left"
    ).merge(
        renta_tcp_crudo[["anio", "renta_sobrevaluacion_crudo"]], on="anio", how="left"
    ).merge(
        renta_tcp_gas[["anio", "renta_sobrevaluacion_gas"]], on="anio", how="left"
    )

    # Subsidies (pesos corrientes)
    if "subsidios_cefip" in subsidios.columns:
        sub = subsidios[["anio", "subsidios_cefip"]].rename(columns={"subsidios_cefip": "subsidios"})
    else:
        sub = subsidios[["anio"]].copy()
        sub["subsidios"] = np.nan
    df = df.merge(sub, on="anio", how="left")

    # Convert all to Millones de pesos corrientes first
    mm_cols = ["renta_dif_precios_crudo", "renta_dif_precios_gas",
               "retenciones", "regalias_total",
               "renta_sobrevaluacion_crudo", "renta_sobrevaluacion_gas", "subsidios"]
    for col in mm_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 1e6

    # Add renta_empresas (already in Millones of current pesos from renta_tg)
    renta_emp = renta_tg[renta_tg["stock_seleccionado"] == "Bolsar"][["anio", "renta_con_tg_union"]].rename(
        columns={"renta_con_tg_union": "renta_empresas"}
    )
    df = df.merge(renta_emp, on="anio", how="left")

    # Exchange rates and deflator
    df = df.merge(tcp_anual[["anio", "tcc", "tcp"]], on="anio", how="left")
    df = df.merge(ganancia_pbi.rename(columns={"unidad": "unidad_pbi_gcia"}), on="anio", how="left")
    df = df.merge(ipc[["anio", "ipc_18"]], on="anio", how="left")

    # Deflate all components to 2018 pesos
    deflate_cols = ["renta_dif_precios_gas", "renta_dif_precios_crudo",
                    "renta_sobrevaluacion_crudo", "renta_sobrevaluacion_gas",
                    "regalias_total", "retenciones", "subsidios", "renta_empresas"]
    for col in deflate_cols:
        if col in df.columns:
            df[col] = df[col] / df["ipc_18"]

    # Total rent
    sign_cols = {
        "renta_dif_precios_crudo": 1,
        "renta_dif_precios_gas": 1,
        "renta_sobrevaluacion_crudo": 1,
        "renta_sobrevaluacion_gas": 1,
        "renta_empresas": 1,
        "regalias_total": 1,
        "retenciones": 1,
        "subsidios": -1,
    }
    comp_cols = [c for c in sign_cols if c in df.columns]
    vals = pd.concat(
        [df[c] * sign_cols[c] for c in comp_cols], axis=1
    )
    df["renta_total"] = vals.sum(axis=1, skipna=True)
    df["proporcion_subsidios"] = df["subsidios"] / df["renta_total"].replace(0, float("nan"))
    df["renta_pv"] = (df["renta_total"] * df["ipc_18"]) / df["ganancia"]
    df["renta_pbi"] = (df["renta_total"] * df["ipc_18"]) / df["pbi"]
    df["unidad"] = "Millones de pesos 2018"
    df["renta_usd_tcc"] = (df["renta_total"] * df["ipc_18"]) / df["tcc"]
    df["renta_usd_tcp"] = (df["renta_total"] * df["ipc_18"]) / df["tcp"]

    df = df.rename(columns={
        "renta_dif_precios_crudo": "renta_diferencial_precios_crudo",
        "renta_dif_precios_gas": "renta_diferencial_precios_gas",
        "renta_sobrevaluacion_crudo": "renta_expo_sobrevaluada_crudo",
        "renta_sobrevaluacion_gas": "renta_expo_sobrevaluada_gas",
    })

    return df.drop_duplicates().query("anio > 1960").sort_values("anio").reset_index(drop=True)


def build_costos(
    prod_total: pd.DataFrame,
    valor_total_produccion: pd.DataFrame,  # long-form, from valor_produccion.run()
    renta_directo: pd.DataFrame,
    empalme_ccnn: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    ipc: pd.DataFrame,
    precios_referencia_crudo: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cost structure in USD/boe.
    costos_totales = ci_extr + ms_extr + consumo_k_fijo
    """
    ipc_map = ipc.set_index("anio")["ipc_18"]
    tcc_map = tcp_anual.set_index("anio")["tcc"]

    df = prod_total[["anio", "unidad", "prod_crudo", "prod_gas", "produccion_total_bep"]].rename(
        columns={"unidad": "unidad_produccion", "prod_crudo": "produccion_crudo",
                 "prod_gas": "produccion_gas", "produccion_total_bep": "produccion_total"}
    )

    # Capital consumption from stock_estimado Bolsar
    ck = empalme_ccnn[["anio", "consumo_k_fijo"]].dropna(subset=["consumo_k_fijo"])
    df = df.merge(ck, on="anio", how="left")

    # CI and MS from empalme_ccnn in 2018 peso → convert to USD tcc
    ci_ms = (
        valor_total_produccion[
            (valor_total_produccion["variable"].isin(["ci_extr", "ms_extr"]))
            & (valor_total_produccion["fuente"] == "Empalme CCNN")
        ][["anio", "variable", "valor"]]
        .copy()
    )
    ci_ms["ipc_18"] = ci_ms["anio"].map(ipc_map)
    ci_ms["tcc"] = ci_ms["anio"].map(tcc_map)
    # valor is in Millones de pesos 2018 → * 1e6 → pesos 2018 → * ipc_18 → current pesos → / tcc → USD
    ci_ms["valor_usd"] = (ci_ms["valor"] * 1e6) * ci_ms["ipc_18"] / ci_ms["tcc"]
    ci_ms["unidad"] = "USD tcc"
    ci_ms = ci_ms.groupby(["anio", "variable"], as_index=False)["valor_usd"].mean()
    ci_wide = ci_ms.pivot(index="anio", columns="variable", values="valor_usd").reset_index()
    df = df.merge(ci_wide, on="anio", how="left")

    # renta_directo provides ppye (current pesos), tg_normal, renta_total (2018 pesos)
    rd = renta_directo[["anio", "ppye", "tg_normal", "renta_total", "ipc_18"]].copy()
    df = df.merge(rd, on="anio", how="left")
    df = df.merge(precios_referencia_crudo[["anio", "precio_me_crudo"]].rename(
        columns={"precio_me_crudo": "precio_referencia_externo"}
    ), on="anio", how="left")

    df = df[df["consumo_k_fijo"].notna()].copy()

    # Convert ppye and renta_total to USD tcc
    df["ppye_usd"] = (df["ppye"] * 1e6) * df["ipc_18"] / df["anio"].map(tcc_map)
    df["renta_total_usd"] = (df["renta_total"] * 1e6) * df["ipc_18"] / df["anio"].map(tcc_map)
    df["unidad_costos"] = "USD/boe"

    df["costos_totales"] = df["ci_extr"].fillna(0) + df["ms_extr"].fillna(0) + df["consumo_k_fijo"].fillna(0)
    df["costos_totales_sum_gcia_normal"] = df["costos_totales"] + (df["ppye_usd"] * df["tg_normal"])
    df["precio_costo"] = df["costos_totales"] / df["produccion_total"]
    df["precio_costo_mmbtu"] = bep_to_mmbtu_p(df["precio_costo"])
    df["precio_produccion"] = df["costos_totales_sum_gcia_normal"] / df["produccion_total"]
    df["precio_venta_potencial"] = (
        df["produccion_total"] * df["precio_referencia_externo"] - df["costos_totales"]
    ) / df["produccion_total"]

    return df.sort_values("anio").reset_index(drop=True)


def build_renta_comparacion(
    renta_indirecto: pd.DataFrame,
    renta_autores: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    ipc_us: pd.DataFrame,
) -> pd.DataFrame:
    """
    Comparison of own rent estimates (USD) with other authors' estimates.
    Own estimates converted from 2018 pesos → USD → constant USD (via ipc_us_20).
    """
    ipc_map = renta_indirecto.set_index("anio")["ipc_18"]
    tcc_map = tcp_anual.set_index("anio")["tcc"]
    tcp_map = tcp_anual.set_index("anio")["tcp"]

    keep_cols = [
        "anio", "tcc", "tcp", "ipc_18",
        "retenciones", "regalias_total",
        "renta_diferencial_precios_crudo", "renta_diferencial_precios_gas",
        "renta_expo_sobrevaluada_crudo", "renta_expo_sobrevaluada_gas",
        "renta_empresas", "renta_total", "subsidios",
    ]
    own = renta_indirecto[[c for c in keep_cols if c in renta_indirecto.columns]].copy()
    own = own[own["anio"] > 1962].copy()

    # Convert 2018 pesos → current pesos → USD tcc
    def to_usd(col):
        return own[col] * own["ipc_18"] / own["tcc"]

    money_cols = [c for c in own.columns if c not in ("anio", "tcc", "tcp", "ipc_18")]
    for col in money_cols:
        own[col] = to_usd(col)

    own["renta_sobrevaluacion"] = (
        own.get("renta_expo_sobrevaluada_crudo", 0).fillna(0)
        + own.get("renta_expo_sobrevaluada_gas", 0).fillna(0)
    )
    own["renta_diferencial_precios"] = (
        own.get("renta_diferencial_precios_crudo", 0).fillna(0)
        + own.get("renta_diferencial_precios_gas", 0).fillna(0)
    )
    own["unidad"] = "Millones de USD"
    own["autor"] = "Propia"

    # Melt to long form
    drop_cols = ["ipc_18", "tcc", "tcp",
                 "renta_expo_sobrevaluada_crudo", "renta_expo_sobrevaluada_gas",
                 "renta_diferencial_precios_crudo", "renta_diferencial_precios_gas"]
    own_long = own.drop(columns=[c for c in drop_cols if c in own.columns]).melt(
        id_vars=["anio", "unidad", "autor"],
        var_name="tipo_de_renta",
        value_name="valor",
    )

    combined = pd.concat([own_long, renta_autores], ignore_index=True)

    # Convert to constant USD via ipc_us_20 and TCP
    if "ipc_us_20" in ipc_us.columns:
        ipc_us_map = ipc_us.set_index("anio")["ipc_us_20"]
    else:
        ipc_us_map = pd.Series(dtype=float)

    combined = combined.merge(tcp_anual[["anio", "tcc", "tcp"]], on="anio", how="left")
    combined = combined.merge(ipc_us.rename(columns=lambda c: c), on="anio", how="left")

    if "ipc_us_20" in combined.columns:
        combined["valor"] = (combined["valor"] * combined["tcc"]) / combined["tcp"] / combined["ipc_us_20"]

    return combined.sort_values(["autor", "anio"]).reset_index(drop=True)


def run(
    renta_tg: pd.DataFrame,
    criterio_propio: pd.DataFrame,
    subsidios: pd.DataFrame,
    renta_crudo_dif: pd.DataFrame,
    renta_gas_dif: pd.DataFrame,
    retenciones_regalias: pd.DataFrame,
    renta_tcp_crudo: pd.DataFrame,
    renta_tcp_gas: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    ipc: pd.DataFrame,
    ganancia_pbi: pd.DataFrame,
    prod_total: pd.DataFrame,
    valor_total_produccion: pd.DataFrame,
    empalme_ccnn: pd.DataFrame,
    ipc_us: pd.DataFrame,
    precios_referencia_crudo: pd.DataFrame,
) -> dict:
    renta_autores = _load_renta_autores()

    renta_directo, renta_directo_pbi = build_renta_directo(
        renta_tg, criterio_propio, subsidios, ipc, ganancia_pbi
    )
    renta_indirecto = build_renta_indirecto(
        renta_crudo_dif, renta_gas_dif, retenciones_regalias,
        renta_tcp_crudo, renta_tcp_gas, subsidios, renta_tg,
        tcp_anual, ipc, ganancia_pbi,
    )
    costos = build_costos(
        prod_total, valor_total_produccion, renta_directo,
        empalme_ccnn, tcp_anual, ipc, precios_referencia_crudo,
    )
    renta_comparacion = build_renta_comparacion(renta_indirecto, renta_autores, tcp_anual, ipc_us)

    return dict(
        renta_directo=renta_directo,
        renta_directo_pbi=renta_directo_pbi,
        renta_indirecto=renta_indirecto,
        costos=costos,
        renta_comparacion=renta_comparacion,
    )
