"""
Total production value: VBP, VA, CI, EBE via national accounts and own criteria.
Replaces Section '# Valor total de la producción' of preprocesamiento.Rmd (lines ~3068-3493).
"""

from pathlib import Path
import numpy as np
import pandas as pd

from utils.indices import generar_indice

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data"
RESULTS = ROOT / "results"


# ===== MIP / COU coefficients =====

def _load_imp_prom_97() -> float:
    """Average import coefficient from MIP 1997 (row 140 / row 149, mean across sectors)."""
    mip = pd.read_excel(DATA / "mip/mip_matriz12.xls", skiprows=7, header=0)
    # Drop first col (...1) and rename second col (...2) to 'actividad'
    mip = mip.iloc[:, 1:]
    mip.columns = ["actividad"] + list(mip.columns[1:])
    # Rows 140 and 149 in R (1-indexed) → 139 and 148 in Python (0-indexed)
    x = mip.iloc[[139, 148]]
    ratio = x.iloc[0, 1:].astype(float) / x.iloc[1, 1:].astype(float)
    return float(ratio.mean(skipna=True))


def _load_servicio_s_extraccion() -> float:
    """Services share of extraction VBP from COU 2006-2016."""
    cou = pd.read_excel(DATA / "mip/sh_cou_06_16.xls", skiprows=2, header=0)
    cou.columns = ["producto", "cpc"] + list(cou.columns[2:])
    cou = cou[
        cou["producto"].astype(str).str.match(r".*\d.*")
        & ~cou["producto"].astype(str).str.startswith("N")
    ].copy()
    for col in cou.columns[2:]:
        cou[col] = pd.to_numeric(cou[col], errors="coerce")
    # R: COU[11] and COU[12] — 1-indexed columns 11 and 12 → 0-indexed 10 and 11
    col11 = cou.iloc[:, 10]
    col12 = cou.iloc[:, 11]
    return float(col12.sum() / (col11.sum() + col12.sum()))


# ===== CCNN data =====

def _load_ccnn_mecon(masa_salarial_hidrocarburos: pd.DataFrame,
                     servicio_s_extraccion: float) -> pd.DataFrame:
    """
    Load national accounts from MECON 'base-mineria' file.
    Used ONLY to compute mean_coef_ms — overwritten later by INDEC version.
    """
    df = pd.read_excel(
        DATA / "mecon/base-mineria-e-hidrocarburos cuentas nacionales.xls",
        sheet_name="Cuentas Nacionales",
        skiprows=5,
        header=0,
    )
    # R renames columns 5 and 15 (1-indexed) → 0-indexed 4 and 14
    cols = list(df.columns)
    rename_map = {
        cols[0]: "anio",
        cols[1]: "periodo",
        cols[4]: "vbp_extraccion_y_servicios_hidrocarburos",
        cols[14]: "va_extraccion_y_servicios_hidrocarburos",
    }
    df = df.rename(columns=rename_map)
    # Keep only annual rows (periodo is NA/NaN)
    df = df[df["periodo"].isna() & df["anio"].notna()].copy()
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df[df["anio"].notna()].copy()

    for col in ["vbp_extraccion_y_servicios_hidrocarburos", "va_extraccion_y_servicios_hidrocarburos"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["vbp_extraccion_hidrocarburos"] = df["vbp_extraccion_y_servicios_hidrocarburos"] * (1 - servicio_s_extraccion)
    df["va_extraccion_hidrocarburos"] = df["va_extraccion_y_servicios_hidrocarburos"] * (1 - servicio_s_extraccion)
    df["ci_extraccion_y_servicios_hidrocarburos"] = (
        df["vbp_extraccion_y_servicios_hidrocarburos"] - df["va_extraccion_y_servicios_hidrocarburos"]
    )
    df["ci_extraccion_hidrocarburos"] = df["vbp_extraccion_hidrocarburos"] - df["va_extraccion_hidrocarburos"]

    # Convert from miles de pesos → millones de pesos
    value_cols = [
        "vbp_extraccion_y_servicios_hidrocarburos",
        "va_extraccion_y_servicios_hidrocarburos",
        "ci_extraccion_y_servicios_hidrocarburos",
        "vbp_extraccion_hidrocarburos",
        "va_extraccion_hidrocarburos",
        "ci_extraccion_hidrocarburos",
    ]
    for col in value_cols:
        df[col] = df[col] / 1e3

    df["unidad"] = "Millones de pesos corrientes"

    # Rename to short names
    df = df.rename(columns={
        "vbp_extraccion_y_servicios_hidrocarburos": "vbp_tot",
        "va_extraccion_y_servicios_hidrocarburos": "va_tot",
        "ci_extraccion_y_servicios_hidrocarburos": "ci_tot",
        "vbp_extraccion_hidrocarburos": "vbp_extr",
        "va_extraccion_hidrocarburos": "va_extr",
        "ci_extraccion_hidrocarburos": "ci_extr",
    })

    # Join wage bill
    ms_sel = masa_salarial_hidrocarburos[["anio", "unidad", "masa_salarial_total_oede", "masa_salarial_extraccion_oede"]].rename(
        columns={"masa_salarial_total_oede": "ms_tot", "masa_salarial_extraccion_oede": "ms_extr"}
    )
    df = df.merge(ms_sel, on=["anio", "unidad"], how="left")
    df["ebe_tot"] = df["va_tot"] - df["ms_tot"]
    df["ebe_extr"] = df["va_extr"] - df["ms_extr"]
    df["fuente"] = "CCNN oficial"
    return df[["anio", "unidad", "fuente", "vbp_tot", "vbp_extr", "ci_tot", "ci_extr",
               "va_tot", "va_extr", "ebe_tot", "ebe_extr", "ms_tot", "ms_extr"]].copy()


def _load_ccnn_indec(masa_salarial_hidrocarburos: pd.DataFrame,
                     servicio_s_extraccion: float) -> pd.DataFrame:
    """Load INDEC-based national accounts (2004-2020). Final ccnn_oficial."""
    # Sheet 3 (0-indexed: 2): VBP
    vbp_raw = pd.read_excel(
        DATA / "indec/sh_VBP_VAB_03_26.xls", sheet_name=2, skiprows=3, header=0
    ).dropna(how="all")
    vbp_raw.columns = ["sector"] + list(range(2004, 2004 + len(vbp_raw.columns) - 1))
    vbp_long = vbp_raw.melt(id_vars="sector", var_name="anio", value_name="vbp_tot")

    # Sheet 5 (0-indexed: 4): VA, select only "Total" columns
    va_raw = pd.read_excel(
        DATA / "indec/sh_VBP_VAB_03_26.xls", sheet_name=4, skiprows=4, header=0
    )
    total_cols = [c for c in va_raw.columns if "Total" in str(c) or "total" in str(c)]
    va_raw = va_raw.iloc[:, [0] + [va_raw.columns.get_loc(c) for c in total_cols]].dropna(how="all")
    va_raw.columns = ["sector"] + list(range(2004, 2004 + len(va_raw.columns) - 1))
    va_long = va_raw.melt(id_vars="sector", var_name="anio", value_name="va_tot")

    # Filter to extraction sector
    pattern = "Extracción de petróleo"
    ccnn = (
        va_long[va_long["sector"].str.contains(pattern, na=False)]
        .merge(
            vbp_long[vbp_long["sector"].str.contains(pattern, na=False)],
            on=["sector", "anio"],
        )
        .copy()
    )
    ccnn["anio"] = pd.to_numeric(ccnn["anio"], errors="coerce")
    ccnn["vbp_tot"] = pd.to_numeric(ccnn["vbp_tot"], errors="coerce")
    ccnn["va_tot"] = pd.to_numeric(ccnn["va_tot"], errors="coerce")

    # Join wage bill
    ms_sel = masa_salarial_hidrocarburos[["anio", "unidad", "masa_salarial_total_oede", "masa_salarial_extraccion_oede"]].rename(
        columns={"masa_salarial_total_oede": "ms_tot", "masa_salarial_extraccion_oede": "ms_extr"}
    )
    ccnn = ccnn.merge(ms_sel, on="anio", how="left")

    ccnn["vbp_extr"] = ccnn["vbp_tot"] * (1 - servicio_s_extraccion)
    ccnn["va_extr"] = ccnn["va_tot"] * (1 - servicio_s_extraccion)
    ccnn["ci_tot"] = ccnn["vbp_tot"] - ccnn["va_tot"]
    ccnn["ci_extr"] = ccnn["vbp_extr"] - ccnn["va_extr"]
    ccnn["ebe_tot"] = ccnn["va_tot"] - ccnn["ms_tot"]
    ccnn["ebe_extr"] = ccnn["va_extr"] - ccnn["ms_extr"]
    ccnn["unidad"] = "Millones de pesos corrientes"
    ccnn["fuente"] = "CCNN oficial"

    return ccnn[["anio", "unidad", "fuente", "vbp_tot", "vbp_extr", "ci_tot", "ci_extr",
                 "va_tot", "va_extr", "ebe_tot", "ebe_extr", "ms_tot", "ms_extr"]].sort_values("anio").reset_index(drop=True)


def _load_coef_consumo_intermedio(ccnn_oficial: pd.DataFrame) -> pd.DataFrame:
    """
    Build intermediate consumption coefficient series 1960-current.
    Pre-2004: from PBI base 1993 (MECON); 2004+: from INDEC CCNN.
    """
    # 1993-base MECON data for pre-2004 period
    vbp_93 = pd.read_excel(
        DATA / "mecon/PBI_Base 1993_PM.xlsx", sheet_name="VBP c", skiprows=6, header=0
    )
    va_93 = pd.read_excel(
        DATA / "mecon/PBI_Base 1993_PM.xlsx", sheet_name="VAB c", skiprows=6, header=0
    )

    def _reshape(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # First col is sector, remaining cols alternate quarterly/annual; select annual (not "I" cols)
        col0 = df.columns[0]
        keep = [col0] + [c for c in df.columns[1:] if "I" not in str(c)]
        df = df[keep]
        years = list(range(1993, 1993 + len(df.columns) - 1))
        df.columns = ["sector"] + years
        return df.melt(id_vars="sector", var_name="anio", value_name=None)

    # Reshape: melt each, drop missing, join
    vbp_93_m = _reshape(vbp_93)
    vbp_93_m.columns = ["sector", "anio", "vbp_tot"]
    va_93_m = _reshape(va_93)
    va_93_m.columns = ["sector", "anio", "va_tot"]

    valor_93 = vbp_93_m.merge(va_93_m, on=["sector", "anio"])
    valor_93["anio"] = pd.to_numeric(valor_93["anio"], errors="coerce")
    valor_93["vbp_tot"] = pd.to_numeric(valor_93["vbp_tot"], errors="coerce")
    valor_93["va_tot"] = pd.to_numeric(valor_93["va_tot"], errors="coerce")

    # Filter to mining sector and compute CI coefficient
    ci_93 = valor_93[valor_93["sector"].str.contains("EXPLOTACION DE MINAS", na=False)].copy()
    ci_93 = ci_93.dropna(subset=["vbp_tot", "va_tot"])
    ci_93["coef_tec_93"] = 1 - ci_93["va_tot"] / ci_93["vbp_tot"]

    # Create index relative to 2004 base
    if 2004 in ci_93["anio"].values:
        ci_93["coef_tec_93_index"] = generar_indice(
            ci_93["coef_tec_93"].reset_index(drop=True),
            ci_93["anio"].reset_index(drop=True),
            2004,
        ).values
    else:
        ci_93["coef_tec_93_index"] = np.nan

    # Full year range
    coef_df = pd.DataFrame({"anio": range(1960, 2031)})
    coef_df = coef_df.merge(
        ccnn_oficial[["anio", "vbp_tot", "va_tot"]].dropna(),
        on="anio", how="left",
    )
    coef_df = coef_df.merge(
        ci_93[["anio", "coef_tec_93_index"]],
        on="anio", how="left",
    )
    coef_df["coef_ci_ccnn"] = 1 - coef_df["va_tot"] / coef_df["vbp_tot"]
    ci_base_2004 = coef_df.loc[coef_df["anio"] == 2004, "coef_ci_ccnn"].values
    ci_base = ci_base_2004[0] if len(ci_base_2004) else np.nan

    coef_df["coef_ci"] = np.where(
        coef_df["anio"] <= 2004,
        coef_df["coef_tec_93_index"] * ci_base,
        coef_df["coef_ci_ccnn"],
    )
    return coef_df[["anio", "coef_ci"]].copy()


def _load_stock_estimado() -> pd.DataFrame:
    return pd.read_csv(DATA / "balances/stock_estimado(temporal).csv")


def _load_consumo_k_fijo_ypf() -> float:
    """Average depreciation rate for YPF = mean(depreciaciones / ppye)."""
    df = pd.read_csv(
        DATA / "balances/balances_arg.csv",
        usecols=lambda c: c not in ["Unnamed: 0", "X1"],
    )
    ypf = df[df["empresa"] == "YPF"].copy()
    ypf["tasa"] = pd.to_numeric(ypf["depreciaciones"], errors="coerce") / pd.to_numeric(ypf["ppye"], errors="coerce")
    return float(ypf["tasa"].mean(skipna=True))


# ===== Build production value DataFrames =====

def _build_precios_y_cantidades(
    prod_crudo: pd.DataFrame,
    expo_crudo: pd.DataFrame,
    prod_gas_mmbtu: pd.DataFrame,
    expo_gas: pd.DataFrame,
    precio_crudo_mi: pd.DataFrame,
    precio_gas_mi_usd_mmbtu: pd.DataFrame,
    precio_mdomundial_gas: pd.DataFrame,
    precios_referencia_crudo: pd.DataFrame,
    tcp_anual: pd.DataFrame,
) -> pd.DataFrame:
    """Merge all quantities and prices into a single wide DataFrame."""
    df = prod_crudo[["anio", "unidad", "prod_crudo"]].rename(columns={"unidad": "unidad_cant_crudo"})

    expo_c = expo_crudo[["anio", "expo_crudo"]].copy()
    expo_c["expo_crudo"] = expo_c["expo_crudo"].fillna(0)
    df = df.merge(expo_c, on="anio", how="left")
    df["expo_crudo"] = df["expo_crudo"].fillna(0)

    df = df.merge(
        precio_crudo_mi[["anio", "precio_crudo_mdoint"]],
        on="anio", how="left",
    )
    df = df.merge(
        precios_referencia_crudo[["anio", "precio_me_crudo"]],
        on="anio", how="left",
    )

    gas = prod_gas_mmbtu[["anio", "unidad", "prod_gas"]].rename(columns={"unidad": "unidad_cant_gas"})
    df = df.merge(gas, on="anio", how="right")

    expo_g = expo_gas[["anio", "expo_gas"]].copy()
    expo_g["expo_gas"] = expo_g["expo_gas"].fillna(0)
    df = df.merge(expo_g, on="anio", how="left")
    df["expo_gas"] = df["expo_gas"].fillna(0)

    df = df.merge(
        precio_mdomundial_gas[["anio", "precio_externo_gas", "precio_exportacion_gas_ar"]],
        on="anio", how="right",
    )
    df = df.merge(
        precio_gas_mi_usd_mmbtu[["anio", "precio_gas_mdoint"]],
        on="anio", how="left",
    )
    df = df.merge(tcp_anual[["anio", "tcc", "tcp"]], on="anio", how="left")
    return df


def build_criterio_ccnn(
    precios_y_cantidades: pd.DataFrame,
    coef_consumo_intermedio: pd.DataFrame,
    servicio_s_extraccion: float,
    mean_coef_ms: dict,
) -> pd.DataFrame:
    """Estimate VBP/VA/CI/EBE using CCNN methodology with own prices."""
    df = precios_y_cantidades.merge(coef_consumo_intermedio, on="anio", how="left")
    df["crudo_mdo_interno"] = df["prod_crudo"] - df["expo_crudo"]
    df["gas_mdo_interno"] = df["prod_gas"] - df["expo_gas"]
    df["unidad"] = "Millones de pesos corrientes"

    df["vbp_tot"] = (
        (
            df["crudo_mdo_interno"] * df["precio_crudo_mdoint"]
            + df["expo_crudo"] * df["precio_me_crudo"]
            + df["gas_mdo_interno"] * df["precio_gas_mdoint"]
            + df["expo_gas"] * df["precio_exportacion_gas_ar"]
        )
        * df["tcc"]
    ) / 1e6

    df["vbp_extr"] = df["vbp_tot"] * (1 - servicio_s_extraccion)
    df["ci_tot"] = df["vbp_tot"] * df["coef_ci"]
    df["ci_extr"] = df["vbp_extr"] * df["coef_ci"]
    df["va_tot"] = df["vbp_tot"] - df["ci_tot"]
    df["va_extr"] = df["vbp_extr"] - df["ci_extr"]
    df["ms_extr"] = df["vbp_extr"] * mean_coef_ms["coef_ms_extr"]
    df["ms_tot"] = df["vbp_tot"] * mean_coef_ms["coef_ms_tot"]
    df["ebe_tot"] = df["va_tot"] - df["ms_tot"]
    df["ebe_extr"] = df["va_extr"] - df["ms_tot"]  # R uses ms_tot here
    df["fuente"] = "Criterio CCNN"
    return df


def build_empalme_ccnn(
    ccnn_oficial: pd.DataFrame,
    criterio_ccnn: pd.DataFrame,
    coef_consumo_intermedio: pd.DataFrame,
    stock_estimado: pd.DataFrame,
    ipc: pd.DataFrame,
    consumo_k_fijo_ypf: float,
    imp_prom_97: float,
    mean_coef_ms: dict,
    stock_source: str = "Bolsar",
) -> pd.DataFrame:
    """Splice CCNN series: pre-2004 extrapolated via criterio_ccnn index; 2004+ from INDEC."""
    # Build index from criterio_ccnn; collapse 4-row price-ref duplicates first
    idx_df = criterio_ccnn[["anio", "vbp_tot"]].copy()
    idx_df = idx_df.groupby("anio", as_index=False)["vbp_tot"].mean()
    idx_df = idx_df[idx_df["vbp_tot"].notna() & (idx_df["anio"] >= 1960)]
    if 2004 in idx_df["anio"].values:
        idx_df["vbp_criterio_ccnn_04"] = generar_indice(
            idx_df["vbp_tot"].reset_index(drop=True),
            idx_df["anio"].reset_index(drop=True),
            2004,
        ).values
    else:
        idx_df["vbp_criterio_ccnn_04"] = np.nan

    # Get 2004 anchor values from ccnn_oficial
    row_2004 = ccnn_oficial[ccnn_oficial["anio"] == 2004]
    vbp_extr_2004 = row_2004["vbp_extr"].iloc[0] if len(row_2004) else np.nan
    vbp_tot_2004 = row_2004["vbp_tot"].iloc[0] if len(row_2004) else np.nan

    # Full merge
    emp = (
        ccnn_oficial
        .merge(coef_consumo_intermedio, on="anio", how="outer")
        .merge(idx_df[["anio", "vbp_criterio_ccnn_04"]], on="anio", how="outer")
        .sort_values("anio")
        .reset_index(drop=True)
    )

    # Splice pre-2004
    emp["vbp_extr"] = np.where(
        emp["anio"] < 2004,
        vbp_extr_2004 * emp["vbp_criterio_ccnn_04"],
        emp["vbp_extr"],
    )
    emp["vbp_tot"] = np.where(
        emp["anio"] < 2004,
        vbp_tot_2004 * emp["vbp_criterio_ccnn_04"],
        emp["vbp_tot"],
    )

    emp["ci_extr"] = emp["vbp_extr"] * emp["coef_ci"]
    emp["ci_tot"] = emp["vbp_tot"] * emp["coef_ci"]
    emp["va_tot"] = emp["va_tot"].where(emp["va_tot"].notna(), emp["vbp_tot"] - emp["ci_tot"])
    emp["va_extr"] = emp["va_extr"].where(emp["va_extr"].notna(), emp["vbp_extr"] - emp["ci_extr"])
    emp["ms_tot"] = emp["ms_tot"].where(emp["ms_tot"].notna(), emp["vbp_tot"] * mean_coef_ms["coef_ms_tot"])
    emp["ms_extr"] = emp["ms_extr"].where(emp["ms_extr"].notna(), emp["vbp_tot"] * mean_coef_ms["coef_ms_extr"])
    emp["ebe_tot"] = emp["ebe_tot"].where(emp["ebe_tot"].notna(), emp["va_tot"] - emp["ms_tot"])
    emp["ebe_extr"] = emp["ebe_extr"].where(emp["ebe_extr"].notna(), emp["va_extr"] - emp["ms_extr"])
    emp["fuente"] = "Empalme CCNN"
    emp["unidad"] = "Millones de pesos corrientes"

    # Add capital consumption (depreciation)
    stock_bolsar = stock_estimado[stock_estimado["fuente_ppye"] == stock_source].copy()
    stock_bolsar["consumo_k_fijo"] = stock_bolsar["valor"] * consumo_k_fijo_ypf
    ck = stock_bolsar[["anio", "consumo_k_fijo"]]
    emp = emp.merge(ck, on="anio", how="left")
    emp["pv"] = emp["ebe_extr"] - emp["consumo_k_fijo"] - (emp["vbp_tot"] * imp_prom_97)
    return emp


def build_criterio_propio(
    precios_y_cantidades: pd.DataFrame,
    empalme_ccnn: pd.DataFrame,
    stock_estimado: pd.DataFrame,
    ipc: pd.DataFrame,
    consumo_k_fijo_ypf: float,
    imp_prom_97: float,
    stock_source: str = "Bolsar",
) -> pd.DataFrame:
    """Estimate VBP/VA/EBE using world prices (criterio propio)."""
    ci_ms = empalme_ccnn[["anio", "unidad", "ci_tot", "ci_extr", "ms_tot", "ms_extr"]].copy()
    df = precios_y_cantidades.merge(ci_ms, on="anio", how="left")

    stock_bolsar = stock_estimado[stock_estimado["fuente_ppye"] == stock_source].copy()
    stock_bolsar["consumo_k_fijo"] = stock_bolsar["valor"] * consumo_k_fijo_ypf
    df = df.merge(stock_bolsar[["anio", "consumo_k_fijo"]], on="anio", how="left")

    df["vbp_tot"] = ((df["prod_crudo"] * df["precio_me_crudo"] + df["prod_gas"] * df["precio_externo_gas"]) * df["tcp"]) / 1e6
    df["va_tot"] = df["vbp_tot"] - df["ci_tot"]
    df["ebe_tot"] = df["va_tot"] - df["ms_tot"]
    df["vbp_extr"] = np.nan
    df["ebe_extr"] = np.nan
    df["va_extr"] = np.nan
    df["fuente"] = "Criterio propio"
    df["unidad"] = "Millones de pesos corrientes"
    df["pv"] = df["ebe_tot"] - df["consumo_k_fijo"]  - (df["vbp_tot"] * imp_prom_97)
    return df


def build_valor_total_produccion(
    ccnn_oficial: pd.DataFrame,
    criterio_ccnn: pd.DataFrame,
    empalme_ccnn: pd.DataFrame,
    criterio_propio: pd.DataFrame,
    ipc: pd.DataFrame,
) -> pd.DataFrame:
    """Combine all fuentes into a long-form current-peso table and write to CSV."""
    filtro = ["anio", "unidad", "fuente", "vbp_tot", "vbp_extr",
              "ci_tot", "ci_extr", "ms_tot", "ms_extr",
              "va_tot", "va_extr", "ebe_tot", "ebe_extr"]

    valor_corr = pd.concat(
        [
            ccnn_oficial[filtro],
            criterio_ccnn[[c for c in filtro if c in criterio_ccnn.columns]],
            empalme_ccnn[[c for c in filtro if c in empalme_ccnn.columns]],
            criterio_propio[[c for c in filtro if c in criterio_propio.columns]],
        ],
        ignore_index=True,
    )

    val_cols = [c for c in filtro if c not in ("anio", "unidad", "fuente")]
    valor_corr = valor_corr.melt(
        id_vars=["anio", "unidad", "fuente"],
        value_vars=val_cols,
        var_name="variable",
        value_name="valor",
    )

    valor = valor_corr.copy()
    valor["unidad"] = "Millones de pesos corrientes"
    return valor[["anio", "fuente", "variable", "unidad", "valor"]].copy()


# ===== Entry point =====

def run(
    masa_salarial_hidrocarburos: pd.DataFrame,
    prod_crudo: pd.DataFrame,
    expo_crudo: pd.DataFrame,
    prod_gas_mmbtu: pd.DataFrame,
    expo_gas: pd.DataFrame,
    precio_crudo_mi: pd.DataFrame,
    precio_gas_mi_usd_mmbtu: pd.DataFrame,
    precio_mdomundial_gas: pd.DataFrame,
    precios_referencia_crudo: pd.DataFrame,
    tcp_anual: pd.DataFrame,
    ipc: pd.DataFrame,
    stock_estimado: pd.DataFrame = None,
    stock_source: str = "Bolsar",
) -> dict:
    imp_prom_97 = _load_imp_prom_97()
    servicio_s_extraccion = _load_servicio_s_extraccion()
    consumo_k_fijo_ypf = _load_consumo_k_fijo_ypf()
    if stock_estimado is None:
        stock_estimado = _load_stock_estimado()

    # Load MECON ccnn first (used only for mean_coef_ms)
    ccnn_mecon = _load_ccnn_mecon(masa_salarial_hidrocarburos, servicio_s_extraccion)
    mean_coef_ms = {
        "coef_ms_tot": float((ccnn_mecon["ms_tot"] / ccnn_mecon["vbp_tot"]).mean(skipna=True)),
        "coef_ms_extr": float((ccnn_mecon["ms_extr"] / ccnn_mecon["vbp_extr"]).mean(skipna=True)),
    }

    # Final ccnn_oficial from INDEC
    ccnn_oficial = _load_ccnn_indec(masa_salarial_hidrocarburos, servicio_s_extraccion)

    coef_ci = _load_coef_consumo_intermedio(ccnn_oficial)

    pqc = _build_precios_y_cantidades(
        prod_crudo, expo_crudo, prod_gas_mmbtu, expo_gas,
        precio_crudo_mi, precio_gas_mi_usd_mmbtu,
        precio_mdomundial_gas, precios_referencia_crudo, tcp_anual,
    )

    criterio_ccnn = build_criterio_ccnn(pqc, coef_ci, servicio_s_extraccion, mean_coef_ms)
    empalme_ccnn = build_empalme_ccnn(
        ccnn_oficial, criterio_ccnn, coef_ci, stock_estimado, ipc,
        consumo_k_fijo_ypf, imp_prom_97, mean_coef_ms, stock_source=stock_source,
    )
    criterio_propio = build_criterio_propio(
        pqc, empalme_ccnn, stock_estimado, ipc, consumo_k_fijo_ypf, imp_prom_97,
        stock_source=stock_source,
    )
    valor_total_produccion = build_valor_total_produccion(
        ccnn_oficial, criterio_ccnn, empalme_ccnn, criterio_propio, ipc
    )

    # Write output
    out_dir = RESULTS / "data_viz"
    out_dir.mkdir(parents=True, exist_ok=True)
    valor_total_produccion.to_csv(out_dir / "valor_total_produccion.csv", index=False)
    print(f"  valor_total_produccion.csv: {valor_total_produccion.shape}")

    return dict(
        valor_total_produccion=valor_total_produccion,
        empalme_ccnn=empalme_ccnn,
        criterio_propio=criterio_propio,
        ccnn_oficial=ccnn_oficial,
        criterio_ccnn=criterio_ccnn,
        stock_estimado=stock_estimado,
        consumo_k_fijo_ypf=consumo_k_fijo_ypf,
        servicio_s_extraccion=servicio_s_extraccion,
        mean_coef_ms=mean_coef_ms,
        imp_prom_97=imp_prom_97,
        coef_consumo_intermedio=coef_ci,
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

    idx = run_idx()
    prod = run_prod()
    prec = run_mi(idx["tcp_anual"], idx["ipc"], idx["ipim"], idx["conversor_pesos"])
    pme = run_me(idx["tcp_anual"], idx["ipc"], idx["conversor_pesos"])
    cx = run_cx()
    emp = run_emp(idx["conversor_pesos"])

    result = run(
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
    print("valor_produccion OK")
    for k, v in result.items():
        if isinstance(v, pd.DataFrame):
            print(f"  {k}: {v.shape}")
        elif isinstance(v, dict):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
