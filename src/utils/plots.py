"""
Plotly theme helpers.
Replaces theme_propio(), plot_theme(), plot_ggplotly() from functiones_hidrocarburos.R.
"""

import plotly.graph_objects as go


_LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    legend=dict(
        orientation="h",
        x=0.1,
        y=-0.2,
    ),
    margin=dict(t=70, b=60),
    font=dict(size=12),
    xaxis=dict(tickangle=45),
)


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply standard light theme with bottom legend and angled x-axis ticks."""
    fig.update_layout(**_LAYOUT_DEFAULTS)
    return fig


def make_ggplotly(fig: go.Figure, title: str, subtitle: str | None = None) -> go.Figure:
    """
    Apply theme and set title/subtitle.
    Mirrors plot_ggplotly(x, title, subtitle) from R.
    """
    apply_theme(fig)
    if subtitle:
        title_text = f"{title}<br><sup>{subtitle}</sup>"
    else:
        title_text = title
    fig.update_layout(title=dict(text=title_text, font=dict(size=14)))
    return fig
