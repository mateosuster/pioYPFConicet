"""
Rent appropriated via currency overvaluation (exports at overvalued exchange rate).
Also assembles retenciones + regalias for use in total rent calculation.
Replaces Section '# Renta apropiada por sobrevaluación cambiaria' and
'# Renta apropiada por el Estado mediante impuestos específicos'
of preprocesamiento.Rmd (lines ~3759-3797).
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parents[2]
DATA_INDEC = ROOT / "data" / "indec" / "complejos_exportadores"


def build_renta_tcp_crudo(
    renta_crudo_dif: pd.DataFrame,
    expo_usd_crudo: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rent from crude exports at overvalued exchange rate.

    Formula:
      renta_sobrevaluacion = expo_crudo * precio_externo * tcp - expo_crudo * precio_externo * tcc
    Cross-check via USD value:
      renta_sobrevaluacion_valor = expo_crudo_usd * tcp - expo_crudo_usd * tcc
    """
    df = renta_crudo_dif[
        ["anio", "unidad_cantidad", "expo_crudo", "precio_externo_crudo", "tcc", "tcp"]
    ].copy()

    df = df.merge(
        expo_usd_crudo[["anio", "expo_crudo_usd"]],
        on="anio", how="left",
    )

    df["renta_sobrevaluacion_crudo"] = (
        df["expo_crudo"] * df["precio_externo_crudo"] * df["tcp"]
        - df["expo_crudo"] * df["precio_externo_crudo"] * df["tcc"]
    )
    # Cross-check using total USD export value
    df["renta_sobrevaluacion_crudo_valor"] = (
        df["expo_crudo_usd"] * df["tcp"] - df["expo_crudo_usd"] * df["tcc"]
    )
    df["dif"] = df["renta_sobrevaluacion_crudo"] / df["renta_sobrevaluacion_crudo_valor"] - 1
    df["unidad_precio"] = "USD"
    df["unidad_renta"] = "Pesos corrientes"

    return df[[
        "anio", "unidad_cantidad", "expo_crudo",
        "unidad_precio", "precio_externo_crudo",
        "tcc", "tcp", "unidad_renta",
        "renta_sobrevaluacion_crudo", "renta_sobrevaluacion_crudo_valor", "dif",
    ]].copy()


def build_renta_tcp_gas(renta_gas_dif: pd.DataFrame) -> pd.DataFrame:
    """
    Rent from gas exports at overvalued exchange rate.

    Formula:
      renta_sobrevaluacion_gas = expo_gas * precio_externo_gas * tcp - expo_gas * precio_externo_gas * tcc
    """
    df = renta_gas_dif[
        ["anio", "unidad_cantidad", "expo_gas", "precio_externo_gas", "tcc", "tcp"]
    ].copy()

    df["renta_sobrevaluacion_gas"] = (
        df["expo_gas"] * df["precio_externo_gas"] * df["tcp"]
        - df["expo_gas"] * df["precio_externo_gas"] * df["tcc"]
    )
    df["unidad_precio"] = "USD"
    df["unidad_renta"] = "Pesos corrientes"

    return df[[
        "anio", "unidad_cantidad", "expo_gas",
        "unidad_precio", "precio_externo_gas",
        "tcc", "tcp", "unidad_renta",
        "renta_sobrevaluacion_gas",
    ]].copy()


def _find_year_row(df: pd.DataFrame):
    """Return (row_index, Series{col_index: year}) for the row containing year headers.
    Strips trailing asterisks (e.g. '2023*' for preliminary data) before parsing."""
    for i, row in df.iterrows():
        cleaned = row.map(
            lambda x: str(x).rstrip("*").strip() if pd.notna(x) else x
        )
        vals = pd.to_numeric(cleaned, errors="coerce")
        years = vals[(vals >= 1990) & (vals <= 2030)].dropna()
        if len(years) >= 4:
            return i, years.astype(int)
    raise ValueError("Year header row not found")


def load_complejos_exportadores() -> pd.DataFrame:
    """
    Load INDEC Complejos Exportadores data.

    Returns DataFrame with columns:
      anio, expo_petroleo_usd_indec, expo_gas_usd_indec, expo_petgas_usd_indec
    All values in Millones de USD.

    For years before 2002, petróleo and gas are not separated in the source.
    The combined value is placed in expo_petroleo_usd_indec; expo_gas_usd_indec is NaN.
    """
    # --- Source 1: 2002-2025 (separate petróleo and gas) ---
    raw = pd.read_excel(
        DATA_INDEC / "complejos_exportadores_serie_2002_2025.xlsx",
        sheet_name=0, header=None,
    )

    year_row_idx, year_series = _find_year_row(raw)

    col0 = raw[0].fillna("").astype(str).str.strip()
    pet_mask = col0.isin(["Petróleo", "Petroleo"])
    gas_mask = col0 == "Gas"

    pet_idx = raw[pet_mask].index[0]
    gas_idx = raw[gas_mask].index[0]

    rows_2002 = []
    for col_idx, year_val in year_series.items():
        rows_2002.append({
            "anio": int(year_val),
            "expo_petroleo_usd_indec": pd.to_numeric(raw.at[pet_idx, col_idx], errors="coerce"),
            "expo_gas_usd_indec": pd.to_numeric(raw.at[gas_idx, col_idx], errors="coerce"),
        })
    df_2002 = pd.DataFrame(rows_2002)
    df_2002["expo_petgas_usd_indec"] = (
        df_2002["expo_petroleo_usd_indec"].fillna(0)
        + df_2002["expo_gas_usd_indec"].fillna(0)
    )

    # --- Source 2: pre-2002 (combined petróleo y gas) ---
    # Combined value goes in expo_petroleo_usd_indec; expo_gas_usd_indec left as NaN.
    path_old = DATA_INDEC / "complexp_variacion_1993_2025.xls"
    sheets_pre2002 = ["1993-1996", "1997-2000", "2001-2004"]

    rows_pre = []
    for sheet in sheets_pre2002:
        raw_s = pd.read_excel(path_old, sheet_name=sheet, header=None)
        _, year_series_s = _find_year_row(raw_s)

        col0_s = raw_s[0].fillna("").astype(str)
        # "Petro" fails on "Petróleo" (accent after "Petr"), so match on "Petr" + "gas"
        petgas_mask = (
            col0_s.str.contains("Petr", case=False, na=False)
            & col0_s.str.contains("gas", case=False, na=False)
        )
        if not petgas_mask.any():
            continue
        petgas_idx = raw_s[petgas_mask].index[0]

        for col_idx, year_val in year_series_s.items():
            if int(year_val) < 2002:
                val = pd.to_numeric(raw_s.at[petgas_idx, col_idx], errors="coerce")
                rows_pre.append({
                    "anio": int(year_val),
                    "expo_petroleo_usd_indec": val,  # combined placed in petróleo column
                    "expo_gas_usd_indec": float("nan"),
                    "expo_petgas_usd_indec": val,
                })

    df_pre = (
        pd.DataFrame(rows_pre)
        if rows_pre
        else pd.DataFrame(
            columns=["anio", "expo_petroleo_usd_indec",
                     "expo_gas_usd_indec", "expo_petgas_usd_indec"]
        )
    )

    result = pd.concat([df_pre, df_2002], ignore_index=True)
    return result.drop_duplicates(subset=["anio"]).sort_values("anio").reset_index(drop=True)


def build_renta_tcp_indec(
    complejos: pd.DataFrame,
    tcp_anual: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rent from petroleum+gas exports (INDEC Complejos Exportadores) at overvalued exchange rate.

    Separate petróleo and gas rents when data allows (2002+).
    For pre-2002, the combined value is in expo_petroleo_usd_indec; expo_gas_usd_indec is NaN.

    Formula: renta = expo_usd * 1e6 * (tcp - tcc)
    expo values are in Millones USD → *1e6 → USD → *(tcp-tcc) → pesos corrientes (absolute).
    Result is consistent with SESCO-based renta_sobrevaluacion columns.
    """
    df = complejos.merge(tcp_anual[["anio", "tcc", "tcp"]], on="anio", how="left")
    tcp_minus_tcc = df["tcp"] - df["tcc"]

    df["renta_sobrevaluacion_petroleo_indec"] = (
        df["expo_petroleo_usd_indec"] * 1e6 * tcp_minus_tcc
    )
    df["renta_sobrevaluacion_gas_indec"] = (
        df["expo_gas_usd_indec"] * 1e6 * tcp_minus_tcc
    )
    # Total: gas is NaN for pre-2002, so skipna sum equals petroleum (= combined) value
    df["renta_sobrevaluacion_petgas_indec"] = (
        df["renta_sobrevaluacion_petroleo_indec"].fillna(0)
        + df["renta_sobrevaluacion_gas_indec"].fillna(0)
    )
    df["unidad_renta"] = "Pesos corrientes"

    return df[[
        "anio",
        "expo_petroleo_usd_indec", "expo_gas_usd_indec", "expo_petgas_usd_indec",
        "tcc", "tcp", "unidad_renta",
        "renta_sobrevaluacion_petroleo_indec",
        "renta_sobrevaluacion_gas_indec",
        "renta_sobrevaluacion_petgas_indec",
    ]].copy()


def build_retenciones_regalias(
    regalias: pd.DataFrame,
    retenciones: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine royalties and export taxes for total rent calculation.
    Primary: retenciones_crudo_jk (2002-2015); gap-filled with retenciones_afip_cap27 (2018-2023).
    """
    ret = retenciones[["anio"]].copy()

    if "retenciones_crudo_jk" in retenciones.columns:
        ret["retenciones_crudo_jk"] = retenciones["retenciones_crudo_jk"]
    elif "retenciones_crudo" in retenciones.columns:
        ret["retenciones_crudo_jk"] = retenciones["retenciones_crudo"]

    if "retenciones_afip_cap27" in retenciones.columns:
        if "retenciones_crudo_jk" in ret.columns:
            ret["retenciones_crudo_jk"] = ret["retenciones_crudo_jk"].fillna(
                retenciones["retenciones_afip_cap27"]
            )
        else:
            ret["retenciones_crudo_jk"] = retenciones["retenciones_afip_cap27"]

    df = regalias.merge(ret, on="anio", how="left")
    return df.sort_values("anio").reset_index(drop=True)


def run(
    renta_crudo_dif: pd.DataFrame,
    renta_gas_dif: pd.DataFrame,
    expo_usd_crudo: pd.DataFrame,
    regalias: pd.DataFrame,
    retenciones: pd.DataFrame,
    tcp_anual: pd.DataFrame,
) -> dict:
    renta_tcp_crudo = build_renta_tcp_crudo(renta_crudo_dif, expo_usd_crudo)
    renta_tcp_gas = build_renta_tcp_gas(renta_gas_dif)
    retenciones_regalias = build_retenciones_regalias(regalias, retenciones)
    complejos = load_complejos_exportadores()
    renta_tcp_indec = build_renta_tcp_indec(complejos, tcp_anual)

    return dict(
        renta_tcp_crudo=renta_tcp_crudo,
        renta_tcp_gas=renta_tcp_gas,
        retenciones_regalias=retenciones_regalias,
        renta_tcp_indec=renta_tcp_indec,
    )
