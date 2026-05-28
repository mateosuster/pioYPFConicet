"""
Analyze tg_pg_total and stock_empresas sheets from the master Excel output.
Main focus: compare capital stock sources (AFIP, Bolsar, S&P Capital IQ) and
their impact on the estimated profit rate.

Outputs (results/argentina/analisis_tg_stock/):
  report.md
  01_tg_por_fuente.{html,png}
  02_ppye_por_fuente.{html,png}          — TCC/TCP share y-axis
  03_ebe_tiempo.{html,png}
  04_ppye_bolsar.{html,png}              — 3 currency units, shared TCC/TCP scale
  05_ppye_ciq.{html,png}                 — 3 currency units, shared TCC/TCP scale
  06_ppye_sector.{html,png}              — sources side by side, M$ cte18
  06b_ppye_sector_tcc.{html,png}         — sources side by side, USD TCC (shared scale w/ 06c)
  06c_ppye_sector_tcp.{html,png}         — sources side by side, USD TCP (shared scale w/ 06b)
  07_cobertura.{html,png}
  08_tg_empresas_bolsar.{html,png}       — tg_ant / tg_desp by empresa (Bolsar)
  09_tg_empresas_ciq.{html,png}          — tg_ant / tg_desp by empresa (S&P CIQ)
  10_tg_sectorial_bolsar.{html,png}      — sector tg from balance data (Bolsar)
  11_tg_sectorial_ciq.{html,png}         — sector tg from balance data (S&P CIQ)
  12_tg_sectorial_ciq_sin_holding.png    — plot 11 without holding sector (PNG only)
  13_tg_por_fuente_principales.png       — plot 01 with 3 key sources only (PNG only)

Run from project root:
  python src/analysis/tg_stock_analysis.py
"""

import sys
from pathlib import Path
from datetime import date

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "src"))
from utils.plots import make_ggplotly, apply_theme

EXCEL = ROOT / "results" / "argentina" / "renta_de_la_tierra_hidrocarburifera_arg.xlsx"
OUT = ROOT / "results" / "argentina" / "analisis_tg_stock"
OUT_HTML = OUT / "html"
OUT_PNG = OUT / "png"

PALETTE = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692"]

STOCK_SOURCE_SLUG_TO_LABEL = {
    "afip_combinada": "AFIP (combinada)",
    "bolsar": "Bolsar",
    "s_p_capital_iq": "S&P Capital IQ",
    # legacy wide columns on RTPG_mecanismos
    "AFIP_combinada": "AFIP (combinada)",
    "Bolsar": "Bolsar",
    "S_P_Capital_IQ": "S&P Capital IQ",
}


# ── I/O helpers ───────────────────────────────────────────────────────────────

def save_fig(fig: go.Figure, stem: str, png_grids: bool = False) -> str:
    """Save to html/ and png/ subfolders. Return markdown image tag.

    png_grids: add grey horizontal gridlines to the PNG only (HTML stays clean).
    """
    (OUT_HTML / f"{stem}.html").write_bytes(fig.to_html(full_html=True).encode("utf-8"))
    if png_grids:
        fig.update_yaxes(showgrid=True, gridcolor="rgba(200,200,200,0.4)", gridwidth=1)
    fig.write_image(str(OUT_PNG / f"{stem}.png"))
    return f"![{stem}](png/{stem}.png)"


def save_png_only(fig: go.Figure, stem: str, png_grids: bool = False) -> None:
    """Save PNG only — no HTML, no report entry."""
    if png_grids:
        fig.update_yaxes(showgrid=True, gridcolor="rgba(200,200,200,0.4)", gridwidth=1)
    fig.write_image(str(OUT_PNG / f"{stem}.png"))


def load_sheets() -> tuple:
    print(f"  Reading {EXCEL.name}...")
    xls = pd.read_excel(EXCEL, sheet_name=None, engine="openpyxl")
    return (
        xls["tg_pg_total"],
        xls["stock_empresas"],
        xls["ipc"][["anio", "ipc_18"]],
        xls["tipo_cambio"][["anio", "tcc", "tcp"]],
        xls.get("RTPG_mecanismos"),
        xls.get("renta_empresas"),
        xls.get("RTPG_multifuente"),  # legacy long-format sheet
    )


def add_conversions(df: pd.DataFrame, value_cols: list, deflators: pd.DataFrame) -> pd.DataFrame:
    """Merge deflators once and add _cte18, _usd_tcc, _usd_tcp for each value col."""
    df = df.merge(deflators, on="anio", how="left")
    for col in value_cols:
        df[f"{col}_cte18"] = df[col] / df["ipc_18"]
        df[f"{col}_usd_tcc"] = df[col] / df["tcc"]
        df[f"{col}_usd_tcp"] = df[col] / df["tcp"]
    return df


def _rebuild_renta_total_por_fuente(
    mecanismos: pd.DataFrame,
    renta_empresas_by_slug: dict[str, pd.Series],
) -> pd.DataFrame | None:
    """Long renta_total / renta_empresas per stock source from wide renta_empresas columns."""
    required = {"anio", "tcp", "renta_total", "renta_empresas"}
    if not required.issubset(mecanismos.columns) or not renta_empresas_by_slug:
        return None

    base = mecanismos[["anio", "tcp", "renta_total", "renta_empresas"]].copy()
    frames = []
    for slug, series in renta_empresas_by_slug.items():
        label = STOCK_SOURCE_SLUG_TO_LABEL.get(slug, slug.replace("_", " "))
        df = base.copy()
        df["renta_empresas"] = pd.to_numeric(df["anio"].map(series), errors="coerce")
        df["renta_total"] = (
            pd.to_numeric(base["renta_total"], errors="coerce")
            - pd.to_numeric(base["renta_empresas"], errors="coerce")
            + df["renta_empresas"]
        )
        df["renta_usd_tcp"] = df["renta_total"] / pd.to_numeric(df["tcp"], errors="coerce")
        df["stock_fuente"] = label
        frames.append(df)

    if not frames:
        return None
    return (
        pd.concat(frames, ignore_index=True)
        .dropna(subset=["anio", "stock_fuente"])
        .sort_values(["stock_fuente", "anio"])
        .reset_index(drop=True)
    )


def build_renta_multi_from_renta_empresas(
    renta_emp: pd.DataFrame | None,
    mecanismos: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """Rebuild long multi-source comparison from wide `renta_empresas` sheet."""
    if renta_emp is None or renta_emp.empty or mecanismos is None or mecanismos.empty:
        return None

    by_slug = {}
    for col in renta_emp.columns:
        if not col.startswith("renta_empresas_"):
            continue
        slug = col[len("renta_empresas_"):]
        by_slug[slug] = renta_emp.set_index("anio")[col]

    return _rebuild_renta_total_por_fuente(mecanismos, by_slug)


def build_renta_multi_from_mecanismos(mecanismos: pd.DataFrame | None) -> pd.DataFrame | None:
    """Legacy: wide renta_empresas_fuente_* columns on RTPG_mecanismos."""
    if mecanismos is None or mecanismos.empty:
        return None

    by_slug = {}
    for col in mecanismos.columns:
        if not col.startswith("renta_empresas_fuente_"):
            continue
        slug = col.replace("renta_empresas_fuente_", "", 1)
        by_slug[slug] = mecanismos.set_index("anio")[col]

    return _rebuild_renta_total_por_fuente(mecanismos, by_slug)


# ── plots ─────────────────────────────────────────────────────────────────────

def p01_tg_por_fuente(tg: pd.DataFrame) -> go.Figure:
    """Profit rate over time, one line per stock source."""
    df = tg.dropna(subset=["stock_seleccionado"])
    fig = go.Figure()
    for i, (src, grp) in enumerate(df.sort_values("anio").groupby("stock_seleccionado")):
        fig.add_trace(go.Scatter(
            x=grp["anio"], y=grp["tasa_ganancia"],
            mode="lines+markers", name=src,
            line=dict(color=PALETTE[i % len(PALETTE)]),
        ))
    make_ggplotly(
        fig,
        title="Tasa de ganancia sectorial por fuente de stock",
        subtitle="tg = EBE / ppye  |  EBE = criterio propio (precios internacionales)",
    )
    fig.add_hline(y=0, line_color="rgba(80,80,80,0.8)", line_width=1.5)
    fig.update_yaxes(title_text="Tasa de ganancia (ratio)")
    fig.update_xaxes(title_text="Año")
    return fig


def p02_ppye_por_fuente(tg: pd.DataFrame) -> go.Figure:
    """ppye in 3 currency units, one subplot per unit, one line per source."""
    df = tg.dropna(subset=["stock_seleccionado"])
    panels = [
        ("ppye_cte18",    "M$ constantes 2018"),
        ("ppye_usd_tcc",  "M USD — tipo de cambio comercial (TCC)"),
        ("ppye_usd_tcp",  "M USD — tipo de cambio de paridad (TCP)"),
    ]
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[p[1] for p in panels],
        shared_xaxes=True,
        vertical_spacing=0.08,
    )
    sources = sorted(df["stock_seleccionado"].unique())
    color_map = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(sources)}

    for row, (col, _) in enumerate(panels, 1):
        for src in sources:
            grp = df[df["stock_seleccionado"] == src].sort_values("anio")
            fig.add_trace(
                go.Scatter(
                    x=grp["anio"], y=grp[col],
                    mode="lines+markers", name=src,
                    line=dict(color=color_map[src]),
                    showlegend=(row == 1),
                ),
                row=row, col=1,
            )

    # Shared y-axis scale for TCC and TCP panels (same units, comparable)
    shared_usd_max = max(
        df["ppye_usd_tcc"].dropna().max(),
        df["ppye_usd_tcp"].dropna().max(),
    ) * 1.05
    fig.update_yaxes(range=[0, shared_usd_max], row=2, col=1)
    fig.update_yaxes(range=[0, shared_usd_max], row=3, col=1)

    apply_theme(fig)
    fig.update_layout(
        title=dict(
            text="ppye por fuente — tres presentaciones de unidades<br>"
                 "<sup>Propiedad, Planta y Equipo (denominador de la tasa de ganancia)</sup>",
            font=dict(size=14),
        ),
        height=800,
    )
    return fig


def p03_pv_tiempo(tg: pd.DataFrame) -> go.Figure:
    """Plusvalía neta (PV) in 3 currency units, bar chart, one subplot per unit."""
    # PV is the same for all stock sources — take first occurrence per year
    pv = (
        tg.sort_values("anio")
        .drop_duplicates(subset="anio")[
            ["anio",
             "plusvalia_cte18",
             "plusvalia_usd_tcc",
             "plusvalia_usd_tcp"]
        ]
    )
    panels = [
        ("plusvalia_cte18",    "M$ constantes 2018"),
        ("plusvalia_usd_tcc",  "M USD — TCC"),
        ("plusvalia_usd_tcp",  "M USD — TCP"),
    ]
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[p[1] for p in panels],
        shared_xaxes=True,
        vertical_spacing=0.08,
    )
    for row, (col, _) in enumerate(panels, 1):
        fig.add_trace(
            go.Bar(
                x=pv["anio"], y=pv[col],
                name=col, showlegend=False,
                marker_color=PALETTE[row - 1],
            ),
            row=row, col=1,
        )
    apply_theme(fig)
    fig.update_layout(
        title=dict(
            text="Plusvalía neta (PV) — tres presentaciones de unidades<br>"
                 "<sup>PV = EBE_extr − ConKfijo − Imp  (fuente: Criterio propio)</sup>",
            font=dict(size=14),
        ),
        height=800,
    )
    return fig


def p04_ppye_empresas(stock_ppye: pd.DataFrame, fuente: str) -> go.Figure:
    """ppye by empresa in 3 currency units (3 subplots), shared TCC/TCP y-axis."""
    df = stock_ppye[stock_ppye["fuente"] == fuente].sort_values("anio")
    empresas = sorted(df["empresa"].unique())

    panels = [
        ("valor_cte18",   "M$ constantes 2018"),
        ("valor_usd_tcc", "M USD — TCC"),
        ("valor_usd_tcp", "M USD — TCP"),
    ]
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[p[1] for p in panels],
        shared_xaxes=True,
        vertical_spacing=0.08,
    )
    color_map = {emp: PALETTE[i % len(PALETTE)] for i, emp in enumerate(empresas)}

    for row, (col, _) in enumerate(panels, 1):
        for emp in empresas:
            grp = df[df["empresa"] == emp]
            fig.add_trace(
                go.Scatter(
                    x=grp["anio"], y=grp[col],
                    mode="lines+markers", name=emp,
                    line=dict(color=color_map[emp]),
                    showlegend=(row == 1),
                ),
                row=row, col=1,
            )

    # Shared y-axis scale for TCC and TCP (same USD units)
    shared_usd_max = max(
        df["valor_usd_tcc"].dropna().max(),
        df["valor_usd_tcp"].dropna().max(),
    ) * 1.05
    fig.update_yaxes(range=[0, shared_usd_max], row=2, col=1)
    fig.update_yaxes(range=[0, shared_usd_max], row=3, col=1)

    apply_theme(fig)
    fig.update_layout(
        title=dict(
            text=f"ppye por empresa — {fuente}<br>"
                 "<sup>Propiedad, Planta y Equipo — tres presentaciones de unidades</sup>",
            font=dict(size=14),
        ),
        height=800,
    )
    return fig


def p06_ppye_sector(stock_ppye: pd.DataFrame) -> go.Figure:
    """ppye stacked bar by sector — sources side by side (no mixing), M$ constantes 2018."""
    fuentes = sorted(stock_ppye["fuente"].unique())
    sectors = sorted(stock_ppye["sector"].unique())
    sector_colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(sectors)}

    fig = make_subplots(
        rows=1, cols=len(fuentes),
        subplot_titles=fuentes,
        shared_yaxes=True,
        horizontal_spacing=0.06,
    )
    for col, fuente in enumerate(fuentes, 1):
        agg = (
            stock_ppye[stock_ppye["fuente"] == fuente]
            .groupby(["anio", "sector"])["valor_cte18"]
            .sum()
            .reset_index()
            .sort_values("anio")
        )
        for sec in sectors:
            grp = agg[agg["sector"] == sec]
            if grp.empty:
                continue
            fig.add_trace(
                go.Bar(
                    x=grp["anio"], y=grp["valor_cte18"],
                    name=sec,
                    marker_color=sector_colors[sec],
                    showlegend=(col == 1),
                ),
                row=1, col=col,
            )

    fig.update_layout(barmode="stack")
    apply_theme(fig)
    fig.update_layout(
        title=dict(
            text="ppye por sector — fuentes separadas<br>"
                 "<sup>Millones de pesos constantes 2018  |  Bolsar y S&P Capital IQ no se suman</sup>",
            font=dict(size=14),
        ),
        height=500,
    )
    return fig


def p06_ppye_sector_usd(
    stock_ppye: pd.DataFrame, unit_col: str, unit_label: str, y_max: float | None = None
) -> go.Figure:
    """ppye stacked bar by sector in USD (TCC or TCP) — sources side by side."""
    fuentes = sorted(stock_ppye["fuente"].unique())
    sectors = sorted(stock_ppye["sector"].unique())
    sector_colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(sectors)}

    fig = make_subplots(
        rows=1, cols=len(fuentes),
        subplot_titles=fuentes,
        shared_yaxes=True,
        horizontal_spacing=0.06,
    )
    for col, fuente in enumerate(fuentes, 1):
        agg = (
            stock_ppye[stock_ppye["fuente"] == fuente]
            .groupby(["anio", "sector"])[unit_col]
            .sum()
            .reset_index()
            .sort_values("anio")
        )
        for sec in sectors:
            grp = agg[agg["sector"] == sec]
            if grp.empty:
                continue
            fig.add_trace(
                go.Bar(
                    x=grp["anio"], y=grp[unit_col],
                    name=sec,
                    marker_color=sector_colors[sec],
                    showlegend=(col == 1),
                ),
                row=1, col=col,
            )

    fig.update_layout(barmode="stack")
    if y_max is not None:
        fig.update_yaxes(range=[0, y_max])
    apply_theme(fig)
    fig.update_layout(
        title=dict(
            text=f"ppye por sector — {unit_label}<br>"
                 "<sup>Bolsar y S&P Capital IQ no se suman</sup>",
            font=dict(size=14),
        ),
        height=500,
    )
    return fig


def p_tg_fuentes_principales(tg: pd.DataFrame) -> go.Figure:
    """Like p01 but filtered to the 3 most comparable sources (PNG only)."""
    keep = {"AFIP (combinada)", "Bolsar", "S&P Capital IQ"}
    df = tg[tg["stock_seleccionado"].isin(keep)].dropna(subset=["stock_seleccionado"])
    sources = sorted(df["stock_seleccionado"].unique())
    color_map = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(sources)}

    fig = go.Figure()
    for src in sources:
        grp = df[df["stock_seleccionado"] == src].sort_values("anio")
        fig.add_trace(go.Scatter(
            x=grp["anio"], y=grp["tasa_ganancia"],
            mode="lines+markers", name=src,
            line=dict(color=color_map[src]),
        ))
    make_ggplotly(
        fig,
        title="Tasa de ganancia — fuentes principales",
        subtitle="AFIP (combinada), Bolsar, S&P Capital IQ  |  tg = EBE / ppye",
    )
    fig.add_hline(y=0, line_color="rgba(80,80,80,0.8)", line_width=1.5)
    fig.update_yaxes(title_text="Tasa de ganancia (ratio)")
    fig.update_xaxes(title_text="Año")
    return fig


def p07_cobertura(stock: pd.DataFrame) -> go.Figure:
    """Heatmap: empresa × year, colored by which fuente(s) cover that cell."""
    sub = stock[stock["variable"] == "ppye"].copy()
    fuentes_sorted = sorted(sub["fuente"].unique())

    # Assign integer code per fuente; if both present use len(fuentes) as "Ambas"
    single_codes = {f: i for i, f in enumerate(fuentes_sorted)}
    ambas_code = len(fuentes_sorted)

    cov = (
        sub.groupby(["empresa", "anio"])
        .agg(
            fuentes=("fuente", lambda x: sorted(x.unique())),
            fuente_str=("fuente", lambda x: " + ".join(sorted(x.unique()))),
        )
        .reset_index()
    )
    cov["code"] = cov["fuentes"].apply(
        lambda fs: ambas_code if len(fs) > 1 else single_codes.get(fs[0], 0)
    )

    pivot_z = cov.pivot(index="empresa", columns="anio", values="code")
    pivot_text = cov.pivot(index="empresa", columns="anio", values="fuente_str").fillna("")

    # Build colorscale for N+1 categories
    n = len(fuentes_sorted)
    tick_vals = list(range(n + 1))
    tick_text = fuentes_sorted + ["Ambas"]
    raw_colors = PALETTE[: n + 1]
    # Normalize to [0, 1]
    colorscale = [[i / n, raw_colors[i]] for i in range(n + 1)]

    fig = go.Figure(go.Heatmap(
        z=pivot_z.values,
        x=pivot_z.columns.tolist(),
        y=pivot_z.index.tolist(),
        colorscale=colorscale,
        zmin=0, zmax=n,
        colorbar=dict(title="Fuente", tickvals=tick_vals, ticktext=tick_text),
        text=pivot_text.values,
        hovertemplate="Empresa: %{y}<br>Año: %{x}<br>Fuente(s): %{text}<extra></extra>",
    ))
    make_ggplotly(
        fig,
        title="Cobertura de datos por empresa y año",
        subtitle="Variable: ppye",
    )
    fig.update_layout(height=max(350, 30 * len(pivot_z)))
    return fig


def p08_tg_empresas(stock: pd.DataFrame, fuente: str) -> go.Figure:
    """tg_ant and tg_desp by empresa — 2 subplots, dimensionless ratios."""
    df = stock[
        (stock["fuente"] == fuente)
        & (stock["variable"].isin(["tg_ant", "tg_desp"]))
    ].dropna(subset=["valor"])
    empresas = sorted(df["empresa"].unique())
    color_map = {emp: PALETTE[i % len(PALETTE)] for i, emp in enumerate(empresas)}

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[
            "tg_ant — tasa de ganancia antes de impuestos",
            "tg_desp — tasa de ganancia después de impuestos",
        ],
        shared_xaxes=True,
        vertical_spacing=0.1,
    )
    for row, var in enumerate(["tg_ant", "tg_desp"], 1):
        for emp in empresas:
            grp = df[(df["empresa"] == emp) & (df["variable"] == var)].sort_values("anio")
            if grp.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=grp["anio"], y=grp["valor"],
                    mode="lines+markers", name=emp,
                    line=dict(color=color_map[emp]),
                    showlegend=(row == 1),
                ),
                row=row, col=1,
            )

    fig.add_hline(y=0, line_color="rgba(80,80,80,0.8)", line_width=1.5, row="all", col="all")
    apply_theme(fig)
    fig.update_layout(
        title=dict(
            text=f"Tasa de ganancia por empresa — {fuente}<br>"
                 "<sup>tg_ant = gcia_ant / KTA  |  tg_desp = gcia_desp / KTA</sup>",
            font=dict(size=14),
        ),
        height=650,
    )
    return fig


def p_tg_sectorial_balances(
    stock: pd.DataFrame, fuente: str, exclude_sectors: list | None = None
) -> go.Figure:
    """Sector-level profit rate from balance data: tg = Σ(gcia_ant) / Σ(KTA) per sector/year."""
    df = stock[stock["fuente"] == fuente]
    if exclude_sectors:
        excl = [s.lower() for s in exclude_sectors]
        df = df[~df["sector"].str.lower().isin(excl)]

    gcia = df[df["variable"] == "gcia_ant"].groupby(["anio", "sector"])["valor"].sum()
    kta  = df[df["variable"] == "KTA"].groupby(["anio", "sector"])["valor"].sum()
    tg = (gcia / kta).dropna().reset_index(name="tg_sector")

    sectors = sorted(tg["sector"].unique())
    fig = go.Figure()
    for i, sec in enumerate(sectors):
        grp = tg[tg["sector"] == sec].sort_values("anio")
        fig.add_trace(go.Scatter(
            x=grp["anio"], y=grp["tg_sector"],
            mode="lines+markers", name=sec,
            line=dict(color=PALETTE[i % len(PALETTE)]),
        ))

    excl_note = f"  |  excluye: {', '.join(exclude_sectors)}" if exclude_sectors else ""
    make_ggplotly(
        fig,
        title=f"Tasa de ganancia sectorial por rubro — {fuente}",
        subtitle=f"tg = Σ(gcia_ant) / Σ(KTA) agregado por sector y año  |  balances{excl_note}",
    )
    fig.add_hline(y=0, line_color="rgba(80,80,80,0.8)", line_width=1.5)
    fig.update_yaxes(title_text="Tasa de ganancia (ratio)")
    fig.update_xaxes(title_text="Año")
    return fig


# ── multi-source renta plots ──────────────────────────────────────────────────

def _y_range_padded(ymin: float, ymax: float, *, pad: float = 0.08, ymin_floor: float | None = None) -> list[float]:
    """Linear y-axis limits with padding; optional floor on the lower bound."""
    if pd.isna(ymin) or pd.isna(ymax):
        return [0, 1]
    if ymax <= ymin:
        ymax = ymin + max(abs(ymin), 1) * 0.1
    span = ymax - ymin
    lo = ymin - span * pad
    hi = ymax + span * pad
    if ymin_floor is not None and ymin >= ymin_floor:
        lo = ymin_floor
    return [lo, hi]


def p_renta_por_fuente(renta_multi: pd.DataFrame) -> go.Figure:
    """Total rent in nominal USD TCP over time, one line per stock source."""
    fuentes = sorted(renta_multi["stock_fuente"].dropna().unique())
    color_map = {f: PALETTE[i % len(PALETTE)] for i, f in enumerate(fuentes)}

    fig = go.Figure()
    for fuente in fuentes:
        grp = renta_multi[renta_multi["stock_fuente"] == fuente].sort_values("anio")
        fig.add_trace(go.Scatter(
            x=grp["anio"], y=grp["renta_usd_tcp"],
            mode="lines+markers", name=fuente,
            line=dict(color=color_map[fuente]),
            marker=dict(size=5),
        ))

    make_ggplotly(
        fig,
        title="Renta total por fuente de stock de capital",
        subtitle="Método indirecto (suma de mecanismos) — M USD tipo de cambio de paridad (TCP) corriente",
    )
    fig.add_hline(y=0, line_color="rgba(80,80,80,0.8)", line_width=1.5)
    tot_vals = pd.to_numeric(renta_multi["renta_usd_tcp"], errors="coerce").dropna()
    if not tot_vals.empty:
        fig.update_yaxes(
            title_text="Millones de USD TCP",
            range=_y_range_padded(0.0, float(tot_vals.max()), ymin_floor=0.0),
            tickformat=",.0f",
        )
    else:
        fig.update_yaxes(title_text="Millones de USD TCP")
    fig.update_xaxes(title_text="Año")
    return fig


def p_renta_empresas_brecha(renta_multi: pd.DataFrame) -> go.Figure:
    """renta_empresas (the component that varies by source) and the resulting total rent gap."""
    fuentes = sorted(renta_multi["stock_fuente"].dropna().unique())
    color_map = {f: PALETTE[i % len(PALETTE)] for i, f in enumerate(fuentes)}

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[
            "renta_empresas por fuente (componente variable)",
            "renta_total por fuente",
        ],
        shared_xaxes=False,
        vertical_spacing=0.12,
    )

    empresas_series: list[pd.Series] = []
    total_series: list[pd.Series] = []

    for fuente in fuentes:
        grp = renta_multi[renta_multi["stock_fuente"] == fuente].sort_values("anio")
        if "renta_empresas" not in grp.columns:
            continue
        y_emp = pd.to_numeric(grp["renta_empresas"], errors="coerce") / pd.to_numeric(grp["tcp"], errors="coerce")
        empresas_series.append(y_emp)
        mask = y_emp.notna()
        fig.add_trace(
            go.Scatter(
                x=grp.loc[mask, "anio"], y=y_emp[mask],
                mode="lines+markers", name=fuente,
                line=dict(color=color_map[fuente]),
                showlegend=True,
                marker=dict(size=4),
            ),
            row=1, col=1,
        )

    for fuente in fuentes:
        grp = renta_multi[renta_multi["stock_fuente"] == fuente].sort_values("anio")
        if "renta_usd_tcp" not in grp.columns:
            continue
        y_tot = pd.to_numeric(grp["renta_usd_tcp"], errors="coerce")
        total_series.append(y_tot)
        mask = y_tot.notna()
        fig.add_trace(
            go.Scatter(
                x=grp.loc[mask, "anio"], y=y_tot[mask],
                mode="lines+markers", name=fuente,
                line=dict(color=color_map[fuente]),
                showlegend=False,
                marker=dict(size=4),
            ),
            row=2, col=1,
        )

    emp_vals = pd.concat(empresas_series).dropna() if empresas_series else pd.Series(dtype=float)
    tot_vals = pd.concat(total_series).dropna() if total_series else pd.Series(dtype=float)

    if not emp_vals.empty:
        emp_range = _y_range_padded(float(emp_vals.min()), float(emp_vals.max()))
    else:
        emp_range = [0, 1]
    if not tot_vals.empty:
        tot_range = _y_range_padded(0.0, float(tot_vals.max()), ymin_floor=0.0)
    else:
        tot_range = [0, 1]

    fig.add_hline(y=0, line_color="rgba(80,80,80,0.8)", line_width=1.5, row="all", col="all")
    apply_theme(fig)
    fig.update_yaxes(
        title_text="M USD TCP (renta_empresas)",
        range=emp_range,
        tickformat=",.0f",
        row=1, col=1,
    )
    fig.update_yaxes(
        title_text="M USD TCP (renta_total)",
        range=tot_range,
        tickformat=",.0f",
        row=2, col=1,
    )
    fig.update_xaxes(title_text="Año", row=2, col=1)
    fig.update_layout(
        title=dict(
            text="Brecha en renta por fuente de stock<br>"
                 "<sup>Solo renta_empresas varía entre fuentes; el resto de mecanismos es idéntico</sup>",
            font=dict(size=14),
        ),
        height=650,
    )
    return fig


# ── markdown helpers ─────────────────────────────────────────────────────────

def _df_to_md(df: pd.DataFrame, index: bool = True) -> str:
    """Render DataFrame as a markdown table without requiring tabulate."""
    if index:
        df = df.reset_index()
    cols = df.columns.tolist()
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(v) if not pd.isna(v) else "" for v in row) + " |")
    return "\n".join([header, sep] + rows)


# ── narrative helpers ─────────────────────────────────────────────────────────

def _ypf_share(df: pd.DataFrame) -> float:
    total = df["valor_cte18"].sum()
    if total == 0 or pd.isna(total):
        return float("nan")
    ypf_val = df[df["empresa"].str.upper() == "YPF"]["valor_cte18"].sum()
    return ypf_val / total


def _tg_stats_table(tg: pd.DataFrame) -> pd.DataFrame:
    tg = tg.dropna(subset=["stock_seleccionado", "tasa_ganancia"])
    last_yr = tg["anio"].max()
    rows = []
    for src, grp in tg.groupby("stock_seleccionado"):
        last = grp[grp["anio"] == last_yr]["tasa_ganancia"]
        peak = grp.loc[grp["tasa_ganancia"].idxmax()]
        rows.append({
            "Fuente": src,
            "TG media": round(grp["tasa_ganancia"].mean(), 3),
            "TG máxima": round(grp["tasa_ganancia"].max(), 3),
            "Año del máximo": int(peak["anio"]),
            f"TG en {int(last_yr)}": round(last.values[0], 3) if len(last) else None,
            "Período": f"{int(grp['anio'].min())}–{int(grp['anio'].max())}",
        })
    return pd.DataFrame(rows).set_index("Fuente")


def _insights_tg(tg: pd.DataFrame) -> str:
    tg = tg.dropna(subset=["stock_seleccionado", "tasa_ganancia"])
    stats = _tg_stats_table(tg)
    last_yr = int(tg["anio"].max())
    lines = []

    best = stats["TG media"].idxmax()
    worst = stats["TG media"].idxmin()
    lines.append(
        f"- La fuente **{best}** produce la mayor tasa de ganancia promedio "
        f"({stats.loc[best, 'TG media']:.3f}), mientras que **{worst}** produce "
        f"la menor ({stats.loc[worst, 'TG media']:.3f}). Esta diferencia se explica "
        f"principalmente por el tamaño del stock de capital (ppye) usado como denominador."
    )

    last_col = f"TG en {last_yr}"
    if last_col in stats.columns:
        vals = stats[last_col].dropna()
        if len(vals) >= 2:
            src_hi = vals.idxmax()
            src_lo = vals.idxmin()
            diff = vals[src_hi] - vals[src_lo]
            lines.append(
                f"- En {last_yr}, la brecha entre la estimación más alta "
                f"(**{src_hi}**: {vals[src_hi]:.3f}) y la más baja "
                f"(**{src_lo}**: {vals[src_lo]:.3f}) es de **{diff:.3f} puntos**. "
                f"Esta incertidumbre debe considerarse al interpretar la renta apropiada."
            )

    peak_src = stats["TG máxima"].idxmax()
    lines.append(
        f"- El máximo histórico fue registrado con la fuente **{peak_src}** "
        f"en {int(stats.loc[peak_src, 'Año del máximo'])} "
        f"(tg = {stats.loc[peak_src, 'TG máxima']:.3f})."
    )
    return "\n".join(lines)


def _insights_stock(stock_ppye: pd.DataFrame) -> str:
    lines = []
    fuente_last: dict = {}

    # Per-source: use last year with valid cte18 data
    for fuente, grp in stock_ppye.groupby("fuente"):
        valid = grp.dropna(subset=["valor_cte18"])
        if valid.empty:
            continue
        last_yr = int(valid["anio"].max())
        last = valid[valid["anio"] == last_yr]
        fuente_last[fuente] = {"yr": last_yr, "total": last["valor_cte18"].sum(), "df": last}
        top_emp = last.loc[last["valor_cte18"].idxmax(), "empresa"]
        ypf_sh = _ypf_share(last)
        ypf_str = f"{ypf_sh:.1%}" if not pd.isna(ypf_sh) else "N/D"
        lines.append(
            f"- **{fuente} ({last_yr})**: empresa con mayor ppye: **{top_emp}**. "
            f"Participación de YPF en el total: **{ypf_str}**."
        )

    # Cross-source comparison: find last year with valid data in both sources
    if len(fuente_last) >= 2:
        names = list(fuente_last.keys())
        # Find most recent year present in both
        common = stock_ppye.dropna(subset=["valor_cte18"])
        shared_years = set(
            common[common["fuente"] == names[0]]["anio"]
        ) & set(common[common["fuente"] == names[1]]["anio"])
        if shared_years:
            compare_yr = int(max(shared_years))
            sub = common[common["anio"] == compare_yr]
            totals = {f: sub[sub["fuente"] == f]["valor_cte18"].sum() for f in names}
            if totals[names[0]] > 0:
                ratio = totals[names[1]] / totals[names[0]]
                direction = "mayor" if ratio > 1 else "menor"
                impl = "tasas de ganancia menores" if ratio > 1 else "tasas de ganancia mayores"
                lines.append(
                    f"- En {compare_yr} (último año con cobertura simultánea), el stock agregado "
                    f"de **{names[1]}** es **{ratio:.2f}x {direction}** que el de **{names[0]}** "
                    f"(pesos constantes 2018), lo que implica {impl} al usar {names[1]}."
                )

    return "\n".join(lines)


def _insights_renta_multi(renta_multi: pd.DataFrame) -> str:
    if renta_multi is None or renta_multi.empty:
        return "_Sin datos de comparación multi-fuente disponibles._"
    lines = []
    fuentes = sorted(renta_multi["stock_fuente"].dropna().unique())
    last_yr = int(renta_multi["anio"].max())

    # Last-year totals in USD TCP
    last = renta_multi[renta_multi["anio"] == last_yr].copy()
    last_vals = {f: last[last["stock_fuente"] == f]["renta_usd_tcp"].values for f in fuentes}
    valid = {f: v[0] for f, v in last_vals.items() if len(v) > 0 and not pd.isna(v[0])}

    if len(valid) >= 2:
        hi_f = max(valid, key=valid.get)
        lo_f = min(valid, key=valid.get)
        lines.append(
            f"- En {last_yr}, la renta total estimada varía entre "
            f"**M USD {valid[lo_f]:,.0f}** ({lo_f}) y "
            f"**M USD {valid[hi_f]:,.0f}** ({hi_f}), "
            f"una brecha de **M USD {valid[hi_f] - valid[lo_f]:,.0f}**."
        )

    lines.append(
        "- La diferencia entre fuentes se explica exclusivamente por `renta_empresas` "
        "(`ppye × (tg_hc − tg_normal)`): un stock de capital mayor implica mayor ppye "
        "y por ende mayor renta apropiada por las empresas."
    )
    return "\n".join(lines)


def _conclusiones(tg: pd.DataFrame) -> str:
    tg = tg.dropna(subset=["stock_seleccionado", "tasa_ganancia"])
    stats = _tg_stats_table(tg)
    lines = [
        "- La elección de la fuente de stock de capital es determinante para el cálculo "
        "de la tasa de ganancia sectorial. Las diferencias entre Bolsar, S&P Capital IQ y "
        "AFIP no son sólo técnicas: reflejan distintos universos de empresas, períodos de "
        "cobertura y criterios de valuación contable.",
        "- Para el cálculo de renta de la tierra es recomendable presentar los resultados "
        "bajo las distintas fuentes como **bandas de incertidumbre**, en lugar de una "
        "estimación puntual.",
    ]
    if len(stats) >= 2:
        best = stats["TG media"].idxmax()
        worst = stats["TG media"].idxmin()
        lines.append(
            f"- La fuente **{best}** produce sistemáticamente las tasas de ganancia más altas, "
            f"lo que indica un stock de capital (ppye) más pequeño que el de **{worst}**. "
            f"Usar **{best}** como denominador sobreestima la tasa de ganancia y, por ende, "
            f"la renta apropiada por las empresas, en comparación con usar **{worst}**."
        )
    return "\n".join(lines)


# ── markdown builder ──────────────────────────────────────────────────────────

def build_report(
    tg: pd.DataFrame,
    stock: pd.DataFrame,
    stock_ppye: pd.DataFrame,
    plot_refs: dict,
    renta_multi: pd.DataFrame = None,
) -> str:
    today = date.today().strftime("%Y-%m-%d")
    last_yr_tg = int(tg["anio"].max())
    last_yr_st = int(stock["anio"].max())

    tg_stats = _tg_stats_table(tg)

    coverage = (
        stock[stock["variable"] == "ppye"]
        .groupby("fuente")
        .agg(empresas=("empresa", "nunique"),
             desde=("anio", "min"),
             hasta=("anio", "max"))
        .reset_index()
        .rename(columns={"fuente": "Fuente", "empresas": "Empresas",
                         "desde": "Desde", "hasta": "Hasta"})
    )

    sources_tg = ", ".join(sorted(tg["stock_seleccionado"].dropna().unique()))

    lines = [
        "# Análisis: Tasa de Ganancia y Stock de Capital — Sector Hidrocarburos Argentina",
        "",
        f"_Generado: {today}_",
        "",
        "---",
        "",
        "## Datos utilizados",
        "",
        f"- **Fuente**: `renta_de_la_tierra_hidrocarburifera_arg.xlsx`",
        f"- **Hojas analizadas**: `tg_pg_total`, `stock_empresas`, `RTPG_mecanismos` y `renta_empresas`",
        f"- **Período tg\\_pg\\_total**: {int(tg['anio'].min())}–{last_yr_tg}",
        f"- **Período stock\\_empresas**: {int(stock['anio'].min())}–{last_yr_st}",
        "- **Unidad de origen**: Millones de pesos corrientes",
        "- **Conversiones presentadas**:",
        "  - Pesos constantes 2018: `valor / ipc_18` (ipc_18 rebased 2018 = 1)",
        "  - USD TCC: `valor / tcc` (tipo de cambio comercial)",
        "  - USD TCP: `valor / tcp` (tipo de cambio de paridad)",
        "",
        "### Cobertura de fuentes en stock_empresas (variable ppye)",
        "",
        _df_to_md(coverage, index=False),
        "",
        "---",
        "",
        "## 1. Tasa de Ganancia por fuente de stock (`tg_pg_total`)",
        "",
        "### Descripción",
        "",
        "La hoja `tg_pg_total` calcula la **tasa de ganancia sectorial** como `tg = EBE / ppye`.",
        "El EBE (Excedente Bruto de Explotación) proviene del Criterio propio (precios internacionales)",
        f"y es único para todos los años. El **stock de capital (ppye)** varía según la fuente: {sources_tg}.",
        "Comparar las tasas de ganancia entre fuentes permite evaluar la sensibilidad del resultado",
        "a la elección del stock de capital.",
        "",
        "### Estadísticas por fuente",
        "",
        _df_to_md(tg_stats),
        "",
        "### Insights",
        "",
        _insights_tg(tg),
        "",
        "### Gráficos",
        "",
        plot_refs["01"],
        "",
        "_Figura 1: Tasa de ganancia sectorial por fuente de stock de capital._",
        "",
        plot_refs["02"],
        "",
        "_Figura 2: ppye (denominador de la tasa de ganancia) por fuente en pesos constantes 2018, USD TCC y USD TCP._",
        "",
        plot_refs["03"],
        "",
        "_Figura 3: Excedente Bruto de Explotación en tres unidades._",
        "",
        "---",
        "",
        "## 2. Stock de Capital por Empresa (`stock_empresas`)",
        "",
        "### Descripción",
        "",
        "La hoja `stock_empresas` contiene activos y resultados de empresas del sector en formato largo.",
        "Variables disponibles: `KTA`, `ppye`, `ppye_neta`, `inventarios`, `activo_no_corr`, `activo`,",
        "`gcia_ant`, `gcia_desp`, `tg_ant`, `tg_desp`.",
        "El análisis se focaliza en **ppye** (denominador de la tasa de ganancia) y en las",
        "**tasas de ganancia por empresa y sector** derivadas directamente de los balances.",
        "",
        "### Insights",
        "",
        _insights_stock(stock_ppye),
        "",
        "### Gráficos",
        "",
        plot_refs["04"],
        "",
        "_Figura 4: ppye por empresa — Bolsar, en pesos constantes 2018, USD TCC y USD TCP (TCC/TCP comparten escala)._",
        "",
        plot_refs["05"],
        "",
        "_Figura 5: ppye por empresa — S&P Capital IQ, mismas tres unidades._",
        "",
        plot_refs["06"],
        "",
        "_Figura 6: ppye por sector — Bolsar y S&P Capital IQ en subgráficos separados (no se suman). M$ constantes 2018._",
        "",
        plot_refs["06b"],
        "",
        "_Figura 6b: ppye por sector en USD tipo de cambio comercial (TCC)._",
        "",
        plot_refs["06c"],
        "",
        "_Figura 6c: ppye por sector en USD tipo de cambio de paridad (TCP). Misma escala que 6b._",
        "",
        plot_refs["07"],
        "",
        "_Figura 7: Cobertura de datos — qué empresa y año están cubiertos por cada fuente._",
        "",
        "### Tasa de ganancia por empresa (desde balances)",
        "",
        plot_refs["08"],
        "",
        "_Figura 8: tg\\_ant y tg\\_desp por empresa — Bolsar. tg = gcia / KTA, dos paneles (antes y después de impuestos)._",
        "",
        plot_refs["09"],
        "",
        "_Figura 9: tg\\_ant y tg\\_desp por empresa — S&P Capital IQ._",
        "",
        "### Tasa de ganancia sectorial (desde balances)",
        "",
        plot_refs["10"],
        "",
        "_Figura 10: tg sectorial — Bolsar. tg = Σ(gcia\\_ant) / Σ(KTA) por sector y año._",
        "",
        plot_refs["11"],
        "",
        "_Figura 11: tg sectorial — S&P Capital IQ._",
        "",
        "---",
        "",
        "## 3. Renta total por fuente de stock (desde `renta_empresas`)",
        "",
        "### Descripción",
        "",
        "La hoja `renta_empresas` reúne los insumos de la renta apropiada por empresas "
        "(`renta_empresas = ppye × (tg − tg_normal)`) con columnas anchas por fuente de stock "
        "(`ppye_afip_combinada`, `tg_bolsar`, `renta_empresas_s_p_capital_iq`, etc.) más "
        "variables compartidas (`pv`, `plusvalia`, `tg_normal`). "
        "La renta total por fuente se reconstruye a partir de `RTPG_mecanismos` sustituyendo "
        "solo el componente `renta_empresas`.",
        "",
        "### Insights",
        "",
        _insights_renta_multi(renta_multi),
        "",
        "### Gráficos",
        "",
        plot_refs.get("14", "_No disponible — ejecutar preprocesamiento primero._"),
        "",
        "_Figura 14: Renta total (M USD TCP) por fuente de stock._",
        "",
        plot_refs.get("15", "_No disponible — ejecutar preprocesamiento primero._"),
        "",
        "_Figura 15: renta\\_empresas (componente variable) y renta\\_total en dos paneles, comparados por fuente._",
        "",
        "---",
        "",
        "## Conclusiones",
        "",
        _conclusiones(tg),
    ]
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_HTML.mkdir(exist_ok=True)
    OUT_PNG.mkdir(exist_ok=True)

    tg_raw, stock_raw, ipc, tc, mecanismos_raw, renta_emp_raw, renta_multi_legacy = load_sheets()
    deflators = ipc.merge(tc, on="anio", how="outer").sort_values("anio")

    # tg sheet: add conversions for ppye and plusvalia
    tg = add_conversions(
        tg_raw.copy(),
        ["ppye", "plusvalia"],
        deflators,
    )

    # stock sheet: add conversions for valor
    stock = add_conversions(stock_raw.copy(), ["valor"], deflators)
    stock_ppye = stock[stock["variable"] == "ppye"].copy()

    # Check which fuentes are present for empresa plots
    fuentes_stock = sorted(stock_ppye["fuente"].unique())
    has_bolsar = "Bolsar" in fuentes_stock
    has_ciq = any("Capital IQ" in f or "CIQ" in f for f in fuentes_stock)
    ciq_label = next((f for f in fuentes_stock if "Capital IQ" in f or "CIQ" in f), None)

    print("Generating plots...")
    plot_refs = {}

    plot_refs["01"] = save_fig(p01_tg_por_fuente(tg), "01_tg_por_fuente", png_grids=True)
    plot_refs["02"] = save_fig(p02_ppye_por_fuente(tg), "02_ppye_por_fuente")
    plot_refs["03"] = save_fig(p03_pv_tiempo(tg), "03_pv_tiempo")

    if has_bolsar:
        plot_refs["04"] = save_fig(p04_ppye_empresas(stock_ppye, "Bolsar"), "04_ppye_bolsar")
    else:
        plot_refs["04"] = "_No hay datos de Bolsar en stock\\_empresas._"

    if has_ciq:
        plot_refs["05"] = save_fig(p04_ppye_empresas(stock_ppye, ciq_label), "05_ppye_ciq")
    else:
        plot_refs["05"] = "_No hay datos de S&P Capital IQ en stock\\_empresas._"

    plot_refs["06"] = save_fig(p06_ppye_sector(stock_ppye), "06_ppye_sector")

    # 06b and 06c: TCC and TCP sector ppye, shared y-axis range between them
    shared_usd_max = max(
        stock_ppye.groupby(["anio", "fuente"])["valor_usd_tcc"].sum().max(),
        stock_ppye.groupby(["anio", "fuente"])["valor_usd_tcp"].sum().max(),
    ) * 1.05
    plot_refs["06b"] = save_fig(
        p06_ppye_sector_usd(stock_ppye, "valor_usd_tcc", "M USD — tipo de cambio comercial (TCC)", y_max=shared_usd_max),
        "06b_ppye_sector_tcc",
    )
    plot_refs["06c"] = save_fig(
        p06_ppye_sector_usd(stock_ppye, "valor_usd_tcp", "M USD — tipo de cambio de paridad (TCP)", y_max=shared_usd_max),
        "06c_ppye_sector_tcp",
    )

    plot_refs["07"] = save_fig(p07_cobertura(stock_raw), "07_cobertura")

    if has_bolsar:
        plot_refs["08"] = save_fig(p08_tg_empresas(stock, "Bolsar"), "08_tg_empresas_bolsar", png_grids=True)
    else:
        plot_refs["08"] = "_No hay datos de Bolsar._"

    if has_ciq:
        plot_refs["09"] = save_fig(p08_tg_empresas(stock, ciq_label), "09_tg_empresas_ciq", png_grids=True)
    else:
        plot_refs["09"] = "_No hay datos de S&P Capital IQ._"

    if has_bolsar:
        plot_refs["10"] = save_fig(p_tg_sectorial_balances(stock, "Bolsar"), "10_tg_sectorial_bolsar", png_grids=True)
    else:
        plot_refs["10"] = "_No hay datos de Bolsar._"

    if has_ciq:
        plot_refs["11"] = save_fig(p_tg_sectorial_balances(stock, ciq_label), "11_tg_sectorial_ciq", png_grids=True)
        save_png_only(
            p_tg_sectorial_balances(stock, ciq_label, exclude_sectors=["holding"]),
            "12_tg_sectorial_ciq_sin_holding",
            png_grids=True,
        )
    else:
        plot_refs["11"] = "_No hay datos de S&P Capital IQ._"

    # PNG-only: 3-source TG comparison
    save_png_only(p_tg_fuentes_principales(tg), "13_tg_por_fuente_principales", png_grids=True)

    # Multi-source renta comparison (long format for plots)
    renta_multi = build_renta_multi_from_renta_empresas(renta_emp_raw, mecanismos_raw)
    if renta_multi is None or renta_multi.empty:
        renta_multi = build_renta_multi_from_mecanismos(mecanismos_raw)
    if (renta_multi is None or renta_multi.empty) and renta_multi_legacy is not None:
        if "stock_fuente" in renta_multi_legacy.columns:
            renta_multi = renta_multi_legacy.copy()

    if renta_multi is not None and not renta_multi.empty:
        plot_refs["14"] = save_fig(p_renta_por_fuente(renta_multi), "14_renta_total_por_fuente", png_grids=True)
        plot_refs["15"] = save_fig(p_renta_empresas_brecha(renta_multi), "15_renta_empresas_brecha", png_grids=True)
    else:
        print("  (skipping plots 14-15: no renta_empresas sheet or legacy multifuente columns)")

    print("Building report...")
    report = build_report(tg, stock_raw, stock_ppye, plot_refs, renta_multi=renta_multi)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    print(f"\nDone. Output: {OUT}")
    print(f"  report.md")
    for f in sorted(OUT_PNG.iterdir()):
        print(f"  png/{f.name}")
    for f in sorted(OUT_HTML.iterdir()):
        print(f"  html/{f.name}")


if __name__ == "__main__":
    main()
