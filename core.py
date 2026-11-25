"""Shared pieces for every page: data, colors, events, chart style, small layout helpers."""
import json
import pathlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"


@st.cache_data
def table(name):
    return pd.read_parquet(DATA / "processed" / f"{name}.parquet")


@st.cache_data
def vintage():
    return json.loads((DATA / "processed" / "vintage.json").read_text())


@st.cache_data
def geo():
    return json.loads((DATA / "geo" / "mexico_states.geojson").read_text())


LAST = pd.Timestamp("2026-10-01")  # checked against the data in app.py

# ---------- colors (validated with the dataviz palette checker; lines always carry direct labels)
ORIGIN = {"Made in Mexico": "#008300", "Trade-deal partners": "#2a78d6",
          "Other no-deal countries": "#eda100", "China": "#e34948"}
DEST = {"United States": "#2a78d6", "Canada": "#eb6834", "Latin America": "#1baf7a",
        "Europe": "#6250d6", "Other & not specified": "#eda100"}
TECH = {"HEV": "#2a78d6", "PHEV": "#eb6834", "BEV": "#1baf7a"}
TECH_NAME = {"HEV": "Hybrid", "PHEV": "Plug-in hybrid", "BEV": "Battery electric"}
INK, INK2, MUTED, GRID, AXIS, GRAY = "#16181d", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#c9c7bf"
NAVY = "#1F3A5F"
RED_RAMP = [[0, "#fbf3f2"], [0.15, "#f7c9c6"], [0.35, "#ef8582"], [0.6, "#e34948"], [1, "#7d1d1d"]]
BLUE_RAMP = [[0, "#eef4fc"], [0.25, "#b7d3f6"], [0.5, "#6da7ec"], [0.75, "#256abf"], [1, "#0d366b"]]
DIVERGE = [[0, "#b52f2f"], [0.25, "#ef8582"], [0.5, "#f0efec"], [0.75, "#6da7ec"], [1, "#1c5cab"]]

# ---------- events that explain the data (kind decides the line style)
EVENTS = [
    dict(d="2018-01", short="GM China imports", on=('sales',), kind="market",
         long="GM starts selling China-built Chevrolets in Mexico: China-made sales jump from 4,674 (2017) to 109,814 (2018)."),
    dict(d="2020-04", end="2020-06", short="COVID-19", on=('sales', 'exports', 'production', 'ev'), kind="market",
         long="Plants stop as non-essential activity in April and May 2020; April production falls to almost zero."),
    dict(d="2020-07", short="USMCA", on=('exports', 'production'), kind="policy", long="USMCA replaces NAFTA on 1 July 2020, with stricter rules of origin for cars."),
    dict(d="2020-10", short="MG joins", on=('sales',), kind="registry", long="MG (SAIC, China) starts reporting to the registry in October 2020."),
    dict(d="2021-01", end="2022-12", short="Chip shortage", on=('sales', 'exports', 'production'), kind="market",
         long="The global semiconductor shortage cuts output and dealer stock through 2021 and 2022."),
    dict(d="2022-07", short="Chirey joins", on=('sales',), kind="registry", long="Chirey (Chery, China) starts reporting in July 2022; Omoda follows in October."),
    dict(d="2024-01", short="Geely, GAC join", on=('sales',), kind="registry",
         long="Geely and Foton start reporting in January 2024. GAC joined in November 2026 with data back to January 2024, so 2024 totals were rewritten after the fact."),
    dict(d="2025-03", short="Chirey exits", on=('sales',), kind="registry",
         long="Chirey Motor México stops reporting (last data March 2025). Its cars are still sold, the registry just stops seeing them."),
    dict(d="2025-04", short="US 25% tariff", on=('exports', 'production'), kind="policy",
         long="US Section 232 tariff of 25% on imported cars from 3 April 2025; USMCA cars pay it on their non-US content."),
    dict(d="2025-09", short="Tariff announced", on=('sales', 'ev'), kind="policy",
         long="On 10 September 2025 Mexico proposes tariffs of up to 50% on cars from countries without a trade agreement. Importers start shipping stock early."),
    dict(d="2026-01", short="50% tariff", on=('sales', 'ev', 'registry'), kind="policy",
         long="From 1 January 2026, light vehicles from countries without a trade agreement (China, India, South Korea, Thailand, Indonesia...) pay up to 50%."),
    dict(d="2026-03", short="CIVAC closes", on=('production',), kind="market", long="Nissan's CIVAC plant (Morelos) builds its last vehicle on 26 March 2026 (press reports)."),
    dict(d="2026-05", short="COMPAS closes", on=('production',), kind="market", long="The Nissan and Mercedes-Benz COMPAS plant (Aguascalientes) ends production in May 2026 (press reports)."),
    dict(d="2026-06", short="Motornation exits", on=(), kind="registry",
         long="Motornation (importer of Changan, BAIC and JMC models) reports for the last time in June 2026 and leaves the registry from the November 2026 report."),
]
KIND_STYLE = {"policy": (NAVY, "solid"), "market": ("#7a786f", "dot"), "registry": ("#6250d6", "dash")}
KIND_NAME = {"policy": "Policy", "market": "Market and plants", "registry": "Registry change"}
PRIORITY = {"policy": 0, "registry": 1, "market": 2}


def mark_events(fig, start, end, tag, width_px=700):
    """Draw this chart's event lines/bands with short labels stacked in rows so they never overlap."""
    if not st.session_state.get("show_events", True):
        return 0
    span = max((end - start).days, 1)
    rows = []  # per row: list of (left, right) label spans as axis fractions
    for e in sorted(EVENTS, key=lambda e: PRIORITY[e["kind"]]):  # policy labels get the first rows
        x0 = pd.Timestamp(e["d"])
        if tag not in e["on"] or not (start <= x0 <= end):
            continue
        color, dash = KIND_STYLE[e["kind"]]
        if "end" in e:
            fig.add_vrect(x0=x0, x1=pd.Timestamp(e["end"]), fillcolor="#e9e7df", opacity=0.55, layer="below", line_width=0)
        else:
            fig.add_vline(x=x0, line=dict(color=color, width=1.2, dash=dash), layer="below")
        at = (x0 - start).days / span
        w = (len(e["short"]) * 6.6 + 14) / width_px
        flip = at + w > 1  # near the right edge the label hangs to the left of its line
        a, b = (at - w, at) if flip else (at, at + w)
        row = next((i for i, r in enumerate(rows) if all(b < x or a > y for x, y in r)), None)
        if row is None:
            if len(rows) == 4:
                continue  # no room for a label: the line stays and the events table lists it
            rows.append([])
            row = len(rows) - 1
        rows[row].append((a, b))
        fig.add_annotation(x=x0, y=1, yref="paper", yanchor="bottom", xanchor="right" if flip else "left", showarrow=False,
                           text=e["short"], hovertext=e["long"], yshift=4 + row * 15,
                           font=dict(size=10.5, color=color), xshift=-2 if flip else 2)
    return len(rows)


def event_list(start, end, tag):
    rows = [dict(Month=pd.Timestamp(e["d"]).strftime("%b %Y"), Event=e["short"], Kind=KIND_NAME[e["kind"]], What=e["long"])
            for e in EVENTS if tag in e["on"] and start <= pd.Timestamp(e["d"]) <= end]
    if rows:
        with st.expander("Events marked on this chart"):
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                         column_config={"What": st.column_config.TextColumn(width="large")})


# ---------- chart style
def style(fig, height=380, legend="bottom", top=None, ypct=False, yfmt=None, xrange=None):
    fig.update_layout(
        template="none", height=height, separators=".,",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK2),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=10, t=top if top is not None else 12, b=6),
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID, font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK)),
        showlegend=legend is not None,
        legend=dict(orientation="h", x=0, xanchor="left", y=-0.1 if legend == "bottom" else 1.02,
                    yanchor="top" if legend == "bottom" else "bottom", font=dict(size=12, color=INK2),
                    bgcolor="rgba(0,0,0,0)", itemclick="toggleothers"),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, ticks="", tickfont=dict(color=MUTED, size=11), title=None, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, ticks="", tickfont=dict(color=MUTED, size=11), title=None, automargin=True,
                     tickformat=".0%" if ypct else yfmt)
    if xrange is not None:
        fig.update_xaxes(range=list(xrange))
    return fig


def show(fig, key=None):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False}, key=key)


def end_labels(fig, df, color_map, fmt="{:.0%}", min_gap=None):
    """Direct labels at the right end of each line, nudged apart so they don't collide."""
    last = df.iloc[-1].dropna().sort_values()
    if last.empty:
        return
    gap = min_gap if min_gap is not None else (df.max().max() - min(0, df.min().min())) * 0.06
    ys, prev = {}, None
    for name, y in last.items():
        y2 = y if prev is None else max(y, prev + gap)
        ys[name], prev = y2, y2
    for name, y in last.items():
        fig.add_annotation(x=df.index[-1], y=ys[name], text=f"<b>{fmt.format(y)}</b> {name}", showarrow=False,
                           xanchor="left", xshift=6, font=dict(size=11.5, color=INK), align="left")
    fig.update_layout(margin=dict(r=170))


# ---------- numbers
def ytd(df, end, years_back=0):
    """Rows from January to the month of `end`, in the year of `end` minus years_back."""
    y = end.year - years_back
    return df[(df.date.dt.year == y) & (df.date.dt.month <= end.month)]


def period_label(end, years_back=0):
    y = end.year - years_back
    return f"Jan–{end.strftime('%b')} {y}" if end.month > 1 else f"Jan {y}"


def rolling12(series_by_month):
    """12-month rolling total: removes seasonality without hiding the trend."""
    return series_by_month.rolling(12, min_periods=12).sum()


def k(n):
    return f"{n / 1e6:.2f}M" if abs(n) >= 1e6 else f"{n / 1e3:.0f}k" if abs(n) >= 1e4 else f"{n:,.0f}"


def chg(a, b):
    return (a / b - 1) if b else float("nan")


# ---------- layout helpers (HTML pieces styled in assets/style.css)
def page_head(eyebrow, title, lead):
    st.html(f'<div class="phead"><p class="eyebrow">{eyebrow}</p><h1>{title}</h1><p class="lead">{lead}</p></div>')


def chart_head(eyebrow, title, sub=""):
    st.html(f'<div class="chead"><p class="eyebrow">{eyebrow}</p><h3>{title}</h3>' + (f'<p class="sub">{sub}</p>' if sub else "") + "</div>")


def takeaway(text):
    st.html(f'<p class="take">{text}</p>')


def coverage(title, items):
    li = "".join(f"<li>{i}</li>" for i in items)
    st.html(f'<div class="cover"><p class="ct"><span class="ci">!</span>{title}</p><ul>{li}</ul></div>')


def event_key():
    keys = "".join(f'<span class="ek ek-{k}"><i></i>{v}</span>' for k, v in KIND_NAME.items())
    st.html(f'<div class="ekey">{keys}<span class="ek ek-band"><i></i>Period</span><span class="eh">Hover a label for details</span></div>')


def numbers(df, label="See the numbers"):
    with st.expander(label):
        st.dataframe(df, width="stretch")


def window():
    return st.session_state.get("window", (pd.Timestamp("2016-01-01"), LAST))
