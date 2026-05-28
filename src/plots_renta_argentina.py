"""
Python migration of R renta plots from src/valor_produccion_y_renta.Rmd.
Outputs 9 PNGs to results/argentina/plots_python/.
Run from project root: python src/plots_renta_argentina.py
"""

import shutil
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.colors
from plotly.subplots import make_subplots

ROOT = Path(__file__).parents[1]
EXCEL = ROOT / "results/argentina/renta_de_la_tierra_hidrocarburifera_arg.xlsx"
BLS_CPI = ROOT / "data/bls/CPIAUCSL.csv"
OUT = ROOT / "results/argentina/plots_python"
TG_PLOTS_DIR = ROOT / "results/argentina/analisis_tg_stock/png"
TG_PLOTS_TO_COPY = [
    "10_tg_sectorial_bolsar.png",
    "12_tg_sectorial_ciq_sin_holding.png",
    "13_tg_por_fuente_principales.png",
    "14_renta_total_por_fuente.png",
    "15_renta_empresas_brecha.png",
]

MECH_COLS = [
    "renta_diferencial_precios_crudo",
    "renta_diferencial_precios_gas",
    "renta_expo_sobrevaluada_crudo",
    "renta_expo_sobrevaluada_gas",
    "renta_empresas",
    "regalias_total",
    "retenciones",
    "subsidios",
]

COLORS = plotly.colors.qualitative.Plotly


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _build_ipc_us20() -> pd.Series:
    """Annual US CPI index with 2020 = 1.0, indexed by year."""
    bls = pd.read_csv(BLS_CPI, parse_dates=["observation_date"])
    bls["anio"] = bls["observation_date"].dt.year
    annual = bls.groupby("anio")["CPIAUCSL"].mean()
    return annual / annual[2020]


def load_data():
    mecanismos = pd.read_excel(EXCEL, sheet_name="RTPG_mecanismos")
    pextq = pd.read_excel(EXCEL, sheet_name="RTPG_PextQ")
    comparacion = pd.read_excel(EXCEL, sheet_name="RTPG_comparacion")
    tc = pd.read_excel(EXCEL, sheet_name="tipo_cambio")
    ipc_us20 = _build_ipc_us20()
    return mecanismos, pextq, comparacion, tc, ipc_us20


# ---------------------------------------------------------------------------
# Shared theme helper
# ---------------------------------------------------------------------------

def _apply_theme(fig: go.Figure, title: str, subtitle: str | None = None) -> go.Figure:
    title_text = f"{title}<br><sup>{subtitle}</sup>" if subtitle else title
    fig.update_layout(
        template="plotly_white",
        font=dict(size=12),
        title=dict(text=title_text, font=dict(size=15)),
        legend=dict(orientation="h", x=0.0, y=-0.18, title_text=""),
        margin=dict(t=90, b=100, l=80, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Plot 1 — renta_mecanismos_y_pxq_ARG.png
# ---------------------------------------------------------------------------

def plot_pxq_vs_mec(mecanismos, pextq, tc, ipc_us20, out_dir):
    tc_clean = tc[["anio", "tcp"]].dropna()

    df_pextq = (
        pextq[["anio", "renta_total"]]
        .merge(tc_clean, on="anio")
        .assign(ipc_us_20=lambda d: d["anio"].map(ipc_us20))
        .dropna(subset=["tcp", "ipc_us_20"])
    )
    df_pextq["valor"] = df_pextq["renta_total"] / df_pextq["tcp"] / df_pextq["ipc_us_20"]
    df_pextq = df_pextq[df_pextq["anio"] > 1960]

    df_mec = mecanismos[["anio", "renta_total", "tcp"]].copy()
    df_mec["ipc_us_20"] = df_mec["anio"].map(ipc_us20)
    df_mec = df_mec.dropna(subset=["tcp", "ipc_us_20"])
    df_mec["valor"] = df_mec["renta_total"] / df_mec["tcp"] / df_mec["ipc_us_20"]
    df_mec = df_mec[df_mec["anio"] > 1960]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_pextq["anio"], y=df_pextq["valor"],
        mode="lines", name="Renta por descuentos sobre plusvalía",
        line=dict(color=COLORS[1]),
    ))
    fig.add_trace(go.Scatter(
        x=df_mec["anio"], y=df_mec["valor"],
        mode="lines", name="Renta por suma de mecanismos",
        line=dict(color=COLORS[2]),
    ))

    fig.update_layout(
        yaxis=dict(
            title="Millones de USD TCp de 2020",
            tickformat=",",
        ),
        xaxis=dict(title=""),
    )
    _apply_theme(fig, "Renta hidrocarburífera total de Argentina",
                 "Comparación de estimaciones propias")
    fig.write_image(str(out_dir / "renta_mecanismos_y_pxq_ARG.png"), width=1200, height=1000)
    print("  ok renta_mecanismos_y_pxq_ARG.png")


# ---------------------------------------------------------------------------
# Plots 2–4 — renta_mecanismos*.png
# ---------------------------------------------------------------------------

def plot_mecanismos(mecanismos, ipc_us20, unit, out_dir):
    df = mecanismos[["anio"] + MECH_COLS + ["ipc_18", "tcc", "tcp"]].copy()
    df["subsidios"] = -df["subsidios"]

    df_melt = df.melt(
        id_vars=["anio", "ipc_18", "tcc", "tcp"],
        value_vars=MECH_COLS,
        var_name="mecanismo",
        value_name="valor_ars",
    )

    if unit == "ars2018":
        df_melt["valor"] = df_melt["valor_ars"] / df_melt["ipc_18"]
        ylab = "Millones de pesos 2018"
        subtitle = "Cursos de apropiación. Millones pesos de 2018"
        filename = "renta_mecanismos.png"
        yticks = None
    elif unit == "usd_tcc":
        df_melt["ipc_us_20"] = df_melt["anio"].map(ipc_us20)
        df_melt["valor"] = df_melt["valor_ars"] / df_melt["tcc"] / df_melt["ipc_us_20"]
        ylab = "Millones USD TCc de 2020"
        subtitle = "Cursos de apropiación"
        filename = "renta_mecanismos_tcc.png"
        yticks = list(range(0, 50001, 10000))
    else:
        df_melt["ipc_us_20"] = df_melt["anio"].map(ipc_us20)
        df_melt["valor"] = df_melt["valor_ars"] / df_melt["tcp"] / df_melt["ipc_us_20"]
        ylab = "Millones USD TCp de 2020"
        subtitle = "Cursos de apropiación"
        filename = "renta_mecanismos_tcp.png"
        yticks = list(range(0, 50001, 10000))

    fig = go.Figure()
    for i, mec in enumerate(MECH_COLS):
        sub = df_melt[df_melt["mecanismo"] == mec].sort_values("anio")
        fig.add_trace(go.Bar(
            x=sub["anio"], y=sub["valor"],
            name=mec,
            marker_color=COLORS[i % len(COLORS)],
        ))

    yaxis_cfg = dict(title=ylab, tickformat=",")
    if yticks:
        yaxis_cfg["tickvals"] = yticks

    fig.update_layout(
        barmode="relative",
        yaxis=yaxis_cfg,
        xaxis=dict(dtick=5),
    )
    _apply_theme(fig, "Renta de la tierra hidrocarburífera", subtitle)
    fig.write_image(str(out_dir / filename), width=1400, height=800)
    print(f"  ok {filename}")


# ---------------------------------------------------------------------------
# Plots 4 & 5 — comparacion_autores.png / comparacion_autores_usd_tcp.png
# ---------------------------------------------------------------------------

def plot_comparacion_total(comparacion, subtitle, filename, out_dir):
    df = comparacion[
        (comparacion["tipo_de_renta"] == "renta_total") & (comparacion["anio"] > 1990)
    ].copy()
    df["valor_tcp_2020"] = df["valor"] * (df["tcc"] / df["tcp"]) / df["ipc_us_20"]

    autores = sorted(df["autor"].unique())
    fig = go.Figure()
    for i, autor in enumerate(autores):
        sub = df[df["autor"] == autor].sort_values("anio")
        fig.add_trace(go.Scatter(
            x=sub["anio"], y=sub["valor_tcp_2020"],
            mode="lines+markers", name=autor,
            line=dict(color=COLORS[i % len(COLORS)]),
            marker=dict(size=5),
        ))

    fig.update_layout(
        yaxis=dict(title="Millones de USD TCp de 2020", tickformat=","),
        xaxis=dict(dtick=5, tickangle=45),
        annotations=[dict(
            text="Nota: en la estimación propia se utilizó la renta por mecanismos",
            showarrow=False, xref="paper", yref="paper",
            x=1.0, y=-0.22, xanchor="right", font=dict(size=10),
        )],
    )
    _apply_theme(fig, "Renta de la tierra hidrocarburífera total de Argentina", subtitle)
    fig.write_image(str(out_dir / filename), width=1000, height=500)
    print(f"  ok {filename}")


# ---------------------------------------------------------------------------
# Plots 6, 7 & 8 — comparacion_autores_tipo_renta*.png (faceted)
# ---------------------------------------------------------------------------

def plot_comparacion_tipos(comparacion, currency, title, subtitle, filename, out_dir):
    exclude = {"renta_total", "renta_estado_total"}
    df = comparacion[
        (comparacion["anio"] > 1990) & (~comparacion["tipo_de_renta"].isin(exclude))
    ].copy()

    if currency == "tcp":
        df["valor_conv"] = df["valor"] * (df["tcc"] / df["tcp"]) / df["ipc_us_20"]
        ylab = "Millones USD TCp de 2020"
    else:
        df["valor_conv"] = df["valor"] / df["ipc_us_20"]
        ylab = "Millones USD TCc de 2020"

    tipos = sorted(df["tipo_de_renta"].unique())
    autores = sorted(df["autor"].unique())
    ncols = 4
    nrows = (len(tipos) + ncols - 1) // ncols

    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=tipos,
        vertical_spacing=0.10,
        horizontal_spacing=0.06,
    )

    for idx, tipo in enumerate(tipos):
        row = idx // ncols + 1
        col = idx % ncols + 1
        sub_tipo = df[df["tipo_de_renta"] == tipo]

        # zero reference line
        xmin = int(sub_tipo["anio"].min()) - 1
        xmax = int(sub_tipo["anio"].max()) + 1
        fig.add_trace(
            go.Scatter(
                x=[xmin, xmax], y=[0, 0],
                mode="lines", line=dict(color="black", width=1),
                showlegend=False, hoverinfo="skip",
            ),
            row=row, col=col,
        )

        for j, autor in enumerate(autores):
            sub = sub_tipo[sub_tipo["autor"] == autor].sort_values("anio")
            if sub.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=sub["anio"], y=sub["valor_conv"],
                    mode="lines+markers", name=autor,
                    showlegend=(idx == 0),
                    line=dict(color=COLORS[j % len(COLORS)]),
                    marker=dict(size=3),
                ),
                row=row, col=col,
            )

    fig.update_xaxes(dtick=5, tickangle=45)
    fig.update_yaxes(tickformat=",")

    title_text = f"{title}<br><sup>{subtitle}</sup>" if subtitle else title
    fig.update_layout(
        template="plotly_white",
        font=dict(size=11),
        title=dict(text=title_text, font=dict(size=14)),
        legend=dict(orientation="h", x=0.0, y=-0.06, title_text=""),
        margin=dict(t=90, b=110, l=60, r=20),
        height=1000,
    )

    # shared y-axis label via annotation
    fig.add_annotation(
        text=ylab, xref="paper", yref="paper",
        x=-0.04, y=0.5, textangle=-90,
        showarrow=False, font=dict(size=12),
    )

    fig.write_image(str(out_dir / filename), width=1600, height=1000)
    print(f"  ok {filename}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _nota_from_excel(clave: str) -> str:
    """Read a value from the master Excel `notas` sheet, or return empty string."""
    try:
        notas = pd.read_excel(EXCEL, sheet_name="notas")
        match = notas.loc[notas["clave"] == clave, "valor"]
        if not match.empty:
            return str(match.iloc[0])
    except Exception:
        pass
    return ""


def _copy_supporting_tg_plots(run_dir: Path) -> None:
    """Copy selected TG analysis plots into the timestamped output folder."""
    copied = 0
    for name in TG_PLOTS_TO_COPY:
        src = TG_PLOTS_DIR / name
        dst = run_dir / name
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
            print(f"  ok {name} (copied)")
        else:
            print(f"  skip {name} (missing)")
    print(f"  TG supporting plots copied: {copied}/{len(TG_PLOTS_TO_COPY)}")


def main(
    stock_source: str = "",
    renta_sv_source: str = "",
    out_dir: Path | None = None,
):
    if not stock_source:
        stock_source = _nota_from_excel("stock_source_seleccionado")
    if not renta_sv_source:
        renta_sv_source = _nota_from_excel("renta_sv_source_seleccionado") or "sesco"

    base_dir = out_dir if out_dir is not None else OUT
    base_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    src_slug = stock_source.replace(" ", "_").replace("/", "-").replace("(", "").replace(")", "")
    run_dir = base_dir / f"{ts}_{src_slug}" if src_slug else base_dir / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    notes_path = run_dir / "notes.txt"
    notes_path.write_text(
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"STOCK_SOURCE: {stock_source}\n"
        f"RENTA_SV_SOURCE: {renta_sv_source}\n",
        encoding="utf-8",
    )

    print(f"Loading data from {EXCEL.name} ...")
    mecanismos, pextq, comparacion, tc, ipc_us20 = load_data()
    print(f"Saving plots to {run_dir} ...")

    plot_pxq_vs_mec(mecanismos, pextq, tc, ipc_us20, run_dir)
    plot_mecanismos(mecanismos, ipc_us20, unit="ars2018", out_dir=run_dir)
    plot_mecanismos(mecanismos, ipc_us20, unit="usd_tcc", out_dir=run_dir)
    plot_mecanismos(mecanismos, ipc_us20, unit="usd_tcp", out_dir=run_dir)

    plot_comparacion_total(
        comparacion,
        subtitle="Comparación con otras estimaciones a tipo de cambio de paridad",
        filename="comparacion_autores.png",
        out_dir=run_dir,
    )
    plot_comparacion_total(
        comparacion,
        subtitle="Comparación con otras estimaciones",
        filename="comparacion_autores_usd_tcp.png",
        out_dir=run_dir,
    )

    plot_comparacion_tipos(
        comparacion, currency="tcp",
        title="Renta hidrocarburífera",
        subtitle="Comparación de estimaciones. Millones USD TCp de 2020",
        filename="comparacion_autores_tipo_renta.png",
        out_dir=run_dir,
    )
    plot_comparacion_tipos(
        comparacion, currency="tcp",
        title="Renta de la tierra hidrocarburífera",
        subtitle="Comparación de estimaciones",
        filename="comparacion_autores_tipo_renta_usd_tcp.png",
        out_dir=run_dir,
    )
    plot_comparacion_tipos(
        comparacion, currency="tcc",
        title="Renta hidrocarburífera",
        subtitle="Comparación de estimaciones. Millones USD TCc de 2020",
        filename="comparacion_autores_tipo_renta_usd_tcc.png",
        out_dir=run_dir,
    )

    if EXCEL.exists():
        shutil.copy2(EXCEL, run_dir / EXCEL.name)
        print(f"  ok {EXCEL.name} (copied)")

    _copy_supporting_tg_plots(run_dir)

    print("Done.")


if __name__ == "__main__":
    import sys

    _stock = ""
    _renta_sv = ""
    for _a in sys.argv[1:]:
        if _a.startswith("--STOCK_SOURCE="):
            _stock = _a.split("=", 1)[1].strip("'\"")
        elif _a.startswith("--RENTA_SV_SOURCE="):
            _renta_sv = _a.split("=", 1)[1].strip("'\"")
    main(stock_source=_stock, renta_sv_source=_renta_sv)
