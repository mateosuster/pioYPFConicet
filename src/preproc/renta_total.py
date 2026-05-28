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

# Stock sources on renta_empresas sheet. Keys = stock_seleccionado; values = column suffix.
MULTI_STOCK_SOURCE_SLUGS = {
    "AFIP (combinada)": "afip_combinada",
    "Bolsar": "bolsar",
    "S&P Capital IQ": "s_p_capital_iq",
}


def _load_renta_autores() -> pd.DataFrame:
    path = DATA / "otros autores/renta_autores.csv"
    df = pd.read_csv(path, usecols=lambda c: c not in ["Unnamed: 0", ""])
    return df


def _subsidios_hibrido(subsidios: pd.DataFrame) -> pd.DataFrame:
    """CEFIP for anio ≤2012, ACIJ for anio ≥2013 (pesos corrientes). Returns [anio, subsidios]."""
    df = subsidios[["anio"]].copy()
    cefip = subsidios["subsidios_cefip"] if "subsidios_cefip" in subsidios.columns else pd.Series(np.nan, index=subsidios.index)
    acij = subsidios["subsidios_acij"] if "subsidios_acij" in subsidios.columns else pd.Series(np.nan, index=subsidios.index)
    df["subsidios"] = np.where(subsidios["anio"].values <= 2012, cefip.values, acij.values)
    return df.drop_duplicates(subset=["anio"]).reset_index(drop=True)


def build_renta_directo(
    renta_tg: pd.DataFrame,
    criterio_propio: pd.DataFrame,
    subsidios: pd.DataFrame,
    ipc: pd.DataFrame,
    ganancia_pbi: pd.DataFrame,
    stock_source: str = "Bolsar",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Direct-method rent (from profit rate differential).

    renta_total = pv - ppye*tg_normal - subsidios_cefip
    All in Millones de pesos corrientes.
    """
    # Filter to selected stock source; deduplicate in case empalme_ccnn had multi-unit rows
    df = renta_tg[renta_tg["stock_seleccionado"] == stock_source][[
        "anio", "ppye", "tg_hidrocarburos", "union_tg"
    ]].rename(columns={"union_tg": "tg_normal"}).drop_duplicates(subset=["anio"]).copy()

    # Join pv from criterio_propio (in current pesos); average across 4-row price-ref combinations
    pv_df = criterio_propio[["anio", "pv"]].dropna(subset=["pv"])
    pv_df = pv_df.groupby("anio", as_index=False)["pv"].mean()
    df = df.merge(pv_df, on="anio", how="left")

    # Subsidies in current pesos — CEFIP ≤2012, ACIJ ≥2013
    sub = _subsidios_hibrido(subsidios)
    sub["subsidios"] = sub["subsidios"] / 1e6
    df = df.merge(sub[["anio", "subsidios"]], on="anio", how="left")
    # fillna after merge: catches NaN both within sub and for years absent from subsidios entirely
    df["subsidios"] = df["subsidios"].fillna(0)

    df["renta_con_tg_normal"] = df["ppye"] * (df["tg_hidrocarburos"] - df["tg_normal"])
    df["gcia_normal_hidrocarburos"] = df["ppye"] * df["tg_normal"]
    df["renta_total"] = df["pv"] - df["gcia_normal_hidrocarburos"] - df["subsidios"]
    df["unidad"] = "Millones de pesos corrientes"
    df = df[df["anio"] > 1997].copy()

    # vs. PBI/ganancia
    renta_pbi_df = df.merge(
        ganancia_pbi.rename(columns={"unidad": "unidad_pbi_gcia"}),
        on="anio", how="left",
    )
    renta_pbi_df["renta_pv"] = renta_pbi_df["renta_total"] / renta_pbi_df["ganancia"]
    renta_pbi_df["renta_pbi"] = renta_pbi_df["renta_total"] / renta_pbi_df["pbi"]

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
    stock_source: str = "Bolsar",
    renta_tcp_indec: pd.DataFrame = None,
    renta_sv_source: str = "sesco",
) -> pd.DataFrame:
    """
    Indirect-method rent = sum of all rent mechanisms.
    All components in Millones de pesos corrientes.
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

    if renta_sv_source == "indec" and renta_tcp_indec is not None:
        df = df.merge(
            renta_tcp_indec[["anio", "renta_sobrevaluacion_petroleo_indec",
                              "renta_sobrevaluacion_gas_indec"]],
            on="anio", how="left",
        )

    # Subsidies (pesos corrientes) — CEFIP ≤2012, ACIJ ≥2013
    sub = _subsidios_hibrido(subsidios)
    df = df.merge(sub, on="anio", how="left")

    # Convert all to Millones de pesos corrientes first
    mm_cols = ["renta_dif_precios_crudo", "renta_dif_precios_gas",
               "retenciones", "regalias_total",
               "renta_sobrevaluacion_crudo", "renta_sobrevaluacion_gas", "subsidios"]
    if renta_sv_source == "indec":
        mm_cols += ["renta_sobrevaluacion_petroleo_indec", "renta_sobrevaluacion_gas_indec"]
    for col in mm_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 1e6
    if "subsidios" in df.columns:
        df["subsidios"] = df["subsidios"].fillna(0)

    # INDEC mode: fall back to SESCO for years before 1993 where INDEC has no data.
    # For 1993-2001 the combined value is already in renta_sobrevaluacion_petroleo_indec
    # (gas is NaN, not a missing-data NaN), so gas fallback must only apply to pre-1993.
    if renta_sv_source == "indec" and "renta_sobrevaluacion_petroleo_indec" in df.columns:
        has_indec = df["renta_sobrevaluacion_petroleo_indec"].notna()
        df["renta_sobrevaluacion_petroleo_indec"] = df["renta_sobrevaluacion_petroleo_indec"].fillna(
            df["renta_sobrevaluacion_crudo"]
        )
        # Gas fallback: only for truly pre-INDEC years (no petróleo data either)
        df["renta_sobrevaluacion_gas_indec"] = df["renta_sobrevaluacion_gas_indec"].fillna(
            df["renta_sobrevaluacion_gas"].where(~has_indec, other=0)
        )

    # Add renta_empresas (already in Millones of current pesos from renta_tg)
    renta_emp = renta_tg[renta_tg["stock_seleccionado"] == stock_source][["anio", "renta_con_tg_union"]].rename(
        columns={"renta_con_tg_union": "renta_empresas"}
    )
    df = df.merge(renta_emp, on="anio", how="left")

    # Exchange rates and deflator
    df = df.merge(tcp_anual[["anio", "tcc", "tcp"]], on="anio", how="left")
    df = df.merge(ganancia_pbi.rename(columns={"unidad": "unidad_pbi_gcia"}), on="anio", how="left")
    df = df.merge(ipc[["anio", "ipc_18"]], on="anio", how="left")

    # Total rent — overvaluation source selected by renta_sv_source flag
    if renta_sv_source == "indec":
        sign_cols = {
            "renta_dif_precios_crudo": 1,
            "renta_dif_precios_gas": 1,
            "renta_sobrevaluacion_petroleo_indec": 1,
            "renta_sobrevaluacion_gas_indec": 1,
            "renta_empresas": 1,
            "regalias_total": 1,
            "retenciones": 1,
            "subsidios": -1,
        }
    else:
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
    df["renta_pv"] = df["renta_total"] / df["ganancia"]
    df["renta_pbi"] = df["renta_total"] / df["pbi"]
    df["unidad"] = "Millones de pesos corrientes"
    df["renta_usd_tcc"] = df["renta_total"] / df["tcc"]
    df["renta_usd_tcp"] = df["renta_total"] / df["tcp"]

    rename_map = {
        "renta_dif_precios_crudo": "renta_diferencial_precios_crudo",
        "renta_dif_precios_gas": "renta_diferencial_precios_gas",
        "renta_sobrevaluacion_crudo": "renta_expo_sobrevaluada_crudo",
        "renta_sobrevaluacion_gas": "renta_expo_sobrevaluada_gas",
    }
    if renta_sv_source == "indec":
        rename_map["renta_sobrevaluacion_petroleo_indec"] = "renta_expo_sobrevaluada_petroleo_indec"
        rename_map["renta_sobrevaluacion_gas_indec"] = "renta_expo_sobrevaluada_gas_indec"
    df = df.rename(columns=rename_map)

    return df.drop_duplicates(subset=["anio"]).query("anio > 1960").sort_values("anio").reset_index(drop=True)


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
    tcc_map = tcp_anual.set_index("anio")["tcc"]

    df = prod_total[["anio", "unidad", "prod_crudo", "prod_gas", "produccion_total_bep"]].rename(
        columns={"unidad": "unidad_produccion", "prod_crudo": "produccion_crudo",
                 "prod_gas": "produccion_gas", "produccion_total_bep": "produccion_total"}
    )

    # Capital consumption from stock_estimado Bolsar
    ck = empalme_ccnn[["anio", "consumo_k_fijo"]].dropna(subset=["consumo_k_fijo"])
    df = df.merge(ck, on="anio", how="left")

    # CI and MS from empalme_ccnn in current pesos → convert to USD tcc
    ci_ms = (
        valor_total_produccion[
            (valor_total_produccion["variable"].isin(["ci_extr", "ms_extr"]))
            & (valor_total_produccion["fuente"] == "Empalme CCNN")
        ][["anio", "variable", "valor"]]
        .copy()
    )
    ci_ms["tcc"] = ci_ms["anio"].map(tcc_map)
    # valor is in Millones de pesos corrientes → * 1e6 → pesos corrientes → / tcc → USD
    ci_ms["valor_usd"] = (ci_ms["valor"] * 1e6) / ci_ms["tcc"]
    ci_ms["unidad"] = "USD tcc"
    ci_ms = ci_ms.groupby(["anio", "variable"], as_index=False)["valor_usd"].mean()
    ci_wide = ci_ms.pivot(index="anio", columns="variable", values="valor_usd").reset_index()
    df = df.merge(ci_wide, on="anio", how="left")

    # renta_directo provides ppye, tg_normal, renta_total (all current pesos)
    rd = renta_directo[["anio", "ppye", "tg_normal", "renta_total"]].copy()
    df = df.merge(rd, on="anio", how="left")
    df = df.merge(precios_referencia_crudo[["anio", "precio_me_crudo"]].rename(
        columns={"precio_me_crudo": "precio_referencia_externo"}
    ), on="anio", how="left")

    df = df[df["consumo_k_fijo"].notna()].copy()

    # Convert ppye and renta_total to USD tcc
    df["ppye_usd"] = (df["ppye"] * 1e6) / df["anio"].map(tcc_map)
    df["renta_total_usd"] = (df["renta_total"] * 1e6) / df["anio"].map(tcc_map)
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
    Own estimates converted from current pesos → USD → constant USD (via ipc_us_20).
    """
    tcc_map = tcp_anual.set_index("anio")["tcc"]
    tcp_map = tcp_anual.set_index("anio")["tcp"]

    keep_cols = [
        "anio", "tcc", "tcp", "ipc_18",
        "retenciones", "regalias_total",
        "renta_diferencial_precios_crudo", "renta_diferencial_precios_gas",
        "renta_expo_sobrevaluada_crudo", "renta_expo_sobrevaluada_gas",
        "renta_expo_sobrevaluada_petroleo_indec", "renta_expo_sobrevaluada_gas_indec",
        "renta_empresas", "renta_total", "subsidios",
    ]
    own = renta_indirecto[[c for c in keep_cols if c in renta_indirecto.columns]].copy()
    own = own[own["anio"] > 1962].copy()

    # Convert current pesos → USD tcc
    def to_usd(col):
        return own[col] / own["tcc"]

    money_cols = [c for c in own.columns if c not in ("anio", "tcc", "tcp", "ipc_18")]
    for col in money_cols:
        own[col] = to_usd(col)

    # Aggregate overvaluation rent from whichever source was active
    if "renta_expo_sobrevaluada_petroleo_indec" in own.columns:
        own["renta_sobrevaluacion"] = (
            own["renta_expo_sobrevaluada_petroleo_indec"].fillna(0)
            + own.get("renta_expo_sobrevaluada_gas_indec", pd.Series(0, index=own.index)).fillna(0)
        )
    else:
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
                 "renta_expo_sobrevaluada_petroleo_indec", "renta_expo_sobrevaluada_gas_indec",
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


def _pivot_source_column(
    df: pd.DataFrame,
    value_col: str,
    prefix: str,
    sources: dict[str, str],
    source_col: str = "stock_seleccionado",
) -> pd.DataFrame:
    """Pivot one variable to wide columns: {prefix}_{slug} per stock source."""
    sub = df[df[source_col].isin(sources)][["anio", source_col, value_col]].drop_duplicates(
        subset=["anio", source_col]
    )
    wide = sub.pivot(index="anio", columns=source_col, values=value_col)
    wide = wide.rename(
        columns={src: f"{prefix}_{slug}" for src, slug in sources.items() if src in wide.columns}
    )
    return wide.reset_index()


def build_renta_empresas_sheet(
    renta_tg_multi: pd.DataFrame | None,
    tasa_ganancia_rama_stock: pd.DataFrame | None = None,
    criterio_propio: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Wide sheet of inputs for renta apropiada por empresas (ppye × (tg − tg_normal)).

    One column per stock source for ppye, tg and renta_empresas; shared columns for pv,
    plusvalia (PV neta) and industrial profit-rate benchmarks.
    """
    if renta_tg_multi is None or renta_tg_multi.empty:
        return pd.DataFrame()

    sources = {
        src: slug
        for src, slug in MULTI_STOCK_SOURCE_SLUGS.items()
        if src in renta_tg_multi["stock_seleccionado"].values
    }
    if not sources:
        return pd.DataFrame()

    tg = renta_tg_multi[renta_tg_multi["stock_seleccionado"].isin(sources)].copy()

    # Shared industrial benchmarks (identical across stock sources)
    bench_cols = [c for c in ["union_tg", "tg_indu_jic", "tg_indu_em"] if c in tg.columns]
    out = tg.groupby("anio", as_index=False)[bench_cols].first() if bench_cols else tg[["anio"]].drop_duplicates()

    if "unidad" in tg.columns:
        unidad = tg["unidad"].dropna().iloc[0] if tg["unidad"].notna().any() else "Millones de pesos corrientes"
        out.insert(1, "unidad", unidad)

    # pv (plusvalía / EBE sectorial — same for all sources in this comparison)
    if criterio_propio is not None and "pv" in criterio_propio.columns:
        pv = criterio_propio[["anio", "pv"]].dropna(subset=["pv"]).groupby("anio", as_index=False)["pv"].mean()
        out = out.merge(pv, on="anio", how="left")

    # Plusvalía neta (PV) — identical across stock sources; one shared column
    if tasa_ganancia_rama_stock is not None and not tasa_ganancia_rama_stock.empty:
        ebe_col = "plusvalia"
        if ebe_col in tasa_ganancia_rama_stock.columns:
            ebe = (
                tasa_ganancia_rama_stock.groupby("anio", as_index=False)[ebe_col]
                .first()
            )
            out = out.merge(ebe, on="anio", how="left")

    # Per-source: ppye, tg, renta_empresas
    for value_col, prefix in [
        ("ppye", "ppye"),
        ("tg_hidrocarburos", "tg"),
        ("renta_con_tg_union", "renta_empresas"),
    ]:
        if value_col not in tg.columns:
            continue
        wide = _pivot_source_column(tg, value_col, prefix, sources)
        out = out.merge(wide, on="anio", how="outer")

    out = out.rename(columns={"union_tg": "tg_normal"})
    return out.sort_values("anio").reset_index(drop=True)


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
    stock_source: str = "Bolsar",
    renta_tcp_indec: pd.DataFrame = None,
    renta_sv_source: str = "sesco",
    renta_tg_multi: pd.DataFrame | None = None,
    tasa_ganancia_rama_stock: pd.DataFrame | None = None,
) -> dict:
    renta_autores = _load_renta_autores()

    renta_directo, renta_directo_pbi = build_renta_directo(
        renta_tg, criterio_propio, subsidios, ipc, ganancia_pbi,
        stock_source=stock_source,
    )
    renta_indirecto = build_renta_indirecto(
        renta_crudo_dif, renta_gas_dif, retenciones_regalias,
        renta_tcp_crudo, renta_tcp_gas, subsidios, renta_tg,
        tcp_anual, ipc, ganancia_pbi, stock_source=stock_source,
        renta_tcp_indec=renta_tcp_indec, renta_sv_source=renta_sv_source,
    )
    renta_empresas = build_renta_empresas_sheet(
        renta_tg_multi=renta_tg_multi,
        tasa_ganancia_rama_stock=tasa_ganancia_rama_stock,
        criterio_propio=criterio_propio,
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
        renta_empresas=renta_empresas,
        costos=costos,
        renta_comparacion=renta_comparacion,
    )
