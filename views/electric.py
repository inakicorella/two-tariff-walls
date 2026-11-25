"""Electrification: hybrids, plug-ins and battery electrics by state."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
from core import TECH, TECH_NAME, INK, INK2

# INEGI Censo de Población y Vivienda 2020, people per state (for per-capita rates)
POP = {"Aguascalientes": 1425607, "Baja California": 3769020, "Baja California Sur": 798447, "Campeche": 928363,
       "Coahuila": 3146771, "Colima": 731391, "Chiapas": 5543828, "Chihuahua": 3741869, "Ciudad de México": 9209944,
       "Durango": 1832650, "Guanajuato": 6166934, "Guerrero": 3540685, "Hidalgo": 3082841, "Jalisco": 8348151,
       "Estado de México": 16992418, "Michoacán": 4748846, "Morelos": 1971520, "Nayarit": 1235456, "Nuevo León": 5784442,
       "Oaxaca": 4132148, "Puebla": 6583278, "Querétaro": 2368467, "Quintana Roo": 1857985, "San Luis Potosí": 2822255,
       "Sinaloa": 3026943, "Sonora": 2944840, "Tabasco": 2402598, "Tamaulipas": 3527735, "Tlaxcala": 1342977,
       "Veracruz": 8062579, "Yucatán": 2320898, "Zacatecas": 1622138}
assert sum(POP.values()) == 126_014_024  # national total of the 2020 census
GEO_NAME = {"Estado de México": "México"}  # the map file's name for the state
# model names that mark a plug-in hybrid or battery-electric car in the sales table (the EV table has no models)
PLUG = (r"EM-i|EM-I|IDD|iDD|DM-i|DM-I|PHEV|\bEV\b|\bBEV\b|Mach-E|e-tron|\bEQ[ABCES]\b|\bEQE\b|\bEQS\b|\bID\.\d"
        r"|Ioniq|IONIQ|\bLeaf\b|\biX\d?\b|\bi[457]\b|\bOra\b|\bORA\b")
ALL_ELECTRIC_BRANDS = ("Zeekr", "Leapmotor")


def filters(h):
    with st.sidebar:
        st.html('<p class="sb-h">Filters for this page</p>')
        techs = st.multiselect("Technology", list(TECH), format_func=lambda t: f"{TECH_NAME[t]} ({t})",
                               placeholder="All technologies", key="ev_tech")
        states = st.multiselect("State", sorted(POP), placeholder="All states", key="ev_state")
    d = h[h.tech.isin(techs)] if techs else h
    if states:
        d = d[d.state.isin(states)]
    label = [", ".join(techs)] if techs else []
    if states:
        label.append(", ".join(states) if len(states) <= 3 else f"{len(states)} states")
    return d, techs or list(TECH), states, (" for " + "; ".join(label)) if label else ""


def kpis(d, end, techs):
    cols = st.columns(len(techs) + 1)
    total_now, total_bef = core.ytd(d, end).units.sum(), core.ytd(d, end, 1).units.sum()
    cols[0].metric(f"Electrified, {core.period_label(end)}", f"{total_now:,.0f}", f"{core.chg(total_now, total_bef):+.0%} vs {end.year - 1}", border=True)
    for c, t in zip(cols[1:], techs):
        a, b = core.ytd(d[d.tech == t], end).units.sum(), core.ytd(d[d.tech == t], end, 1).units.sum()
        c.metric(TECH_NAME[t], f"{a:,.0f}", f"{core.chg(a, b):+.0%} vs {end.year - 1}" if b else None, border=True)


def monthly(d, techs, start, end, label):
    with st.container(border=True):
        core.chart_head("Month by month", "The tariff covers electric cars too, yet plug-in hybrids tripled",
                        f"Hybrid and electric sales per month{label}")
        s0 = max(start, pd.Timestamp("2016-01-01"))
        m = d[(d.date >= s0) & (d.date <= end)].pivot_table(index="date", columns="tech", values="units", aggfunc="sum").fillna(0)
        fig = go.Figure()
        for t in [t for t in TECH if t in techs and t in m]:
            fig.add_bar(x=m.index, y=m[t], name=TECH_NAME[t], marker=dict(color=TECH[t], line=dict(color="#fff", width=0.6)),
                        hovertemplate="%{y:,.0f}<extra>" + TECH_NAME[t] + "</extra>")
        rows = core.mark_events(fig, s0, end, "ev", width_px=820)
        core.style(fig, height=380, top=24 + rows * 15, yfmt=",.0f", xrange=(s0 - pd.Timedelta(days=16), end + pd.Timedelta(days=16)))
        fig.update_layout(barmode="stack", bargap=0.15, hovermode="x unified")
        core.show(fig, "ev_month")
        core.takeaway("Electrified sales went from a niche to more than one new car in ten. Plug-in hybrids tripled in 2026, the year the 50% tariff began, "
                      "and the sales table shows that most of the new plug-in and electric models are built in China (next chart). "
                      "Mexico's electrification now runs through the very imports the tariff targets.")
        core.numbers(m.loc[::-1].astype(int).rename_axis("Month"))


def share(h_all, techs, start, end):
    with st.container(border=True):
        core.chart_head("Against the whole market", "Share of new cars that are electrified",
                        "Hybrid and electric sales over all light-vehicle sales, 12-month rolling")
        s = core.table("sales").groupby("date").units.sum()
        months = pd.date_range(max(start, pd.Timestamp("2017-01-01")) - pd.DateOffset(months=11), end, freq="MS")
        m = h_all.pivot_table(index="date", columns="tech", values="units", aggfunc="sum").reindex(months).fillna(0)
        tot = core.rolling12(s.reindex(months))
        r = core.rolling12(m).div(tot, axis=0).loc[max(start, pd.Timestamp("2017-01-01")):end]
        fig = go.Figure()
        for t in [t for t in TECH if t in techs]:
            fig.add_scatter(x=r.index, y=r[t], name=TECH_NAME[t], stackgroup="one", mode="lines",
                            line=dict(color="#fff", width=1), fillcolor=TECH[t], hovertemplate="%{y:.1%}<extra>" + TECH_NAME[t] + "</extra>")
        core.style(fig, height=300, ypct=True, xrange=(r.index[0], r.index[-1]))
        fig.update_layout(hovermode="x unified")
        core.show(fig, "ev_share")
        core.takeaway(f"<b>{r[techs].sum(axis=1).iloc[-1]:.1%}</b> of the last twelve months' sales were electrified. "
                      "The real figure is higher: BYD, widely reported as the leading seller of electric cars in Mexico, is not in the registry.")


def named_models(end):
    with st.container(border=True):
        s = core.ytd(core.table("sales"), end)
        m = s[s.model.str.contains(PLUG, regex=True) | s.brand.isin(ALL_ELECTRIC_BRANDS)]
        cn = m[m.origin_block == "China"].units.sum()
        core.chart_head("Crossing two tables", f"{cn / m.units.sum():.0%} of plug-in and electric models sold are built in China",
                        f"Models whose name marks them as plug-in or electric, {core.period_label(end)}")
        top = m.groupby(["brand", "model", "origin_country"]).units.sum().sort_values(ascending=False).head(8).reset_index()
        rows = "".join(f'<tr><td>{r.brand} {r.model}</td><td style="color:{core.ORIGIN["China"] if r.origin_country == "China" else core.INK2}">{r.origin_country}</td>'
                       f'<td style="text-align:right">{r.units:,.0f}</td></tr>' for r in top.itertuples())
        st.html(f'<table class="tbl"><tr><th>Model</th><th>Built in</th><th style="text-align:right">Units</th></tr>{rows}</table>')
        core.takeaway(f"<b>{cn:,.0f}</b> of {m.units.sum():,.0f} units. Exempting electric cars from the tariff would mostly help Chinese factories; "
                      "keeping them in slows electrification. That trade-off has to be decided on purpose.")


def states_map(d, end, label):
    with st.container(border=True):
        core.chart_head("Where", "Electrified sales by state", f"Last 12 months to {end:%B %Y}{label}")
        metric = st.segmented_control("Measure", ["Per 100,000 people", "Units"], default="Per 100,000 people", required=True,
                                      key="ev_metric", label_visibility="collapsed")
        last12 = d[(d.date > end - pd.DateOffset(months=12)) & (d.date <= end) & (d.state != "Not specified")]
        g = last12.groupby("state").units.sum().reindex(list(POP)).fillna(0)
        val = g / pd.Series(POP) * 1e5 if metric != "Units" else g
        fig = go.Figure(go.Choropleth(
            geojson=core.geo(), featureidkey="properties.name", locations=[GEO_NAME.get(s, s) for s in val.index],
            z=val.values, colorscale=core.BLUE_RAMP, marker=dict(line=dict(color="#fff", width=0.7)),
            customdata=list(zip(val.index, g.values)),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]:,.0f} units<br>%{z:,.1f}" + (" per 100,000 people" if metric != "Units" else "") + "<extra></extra>",
            colorbar=dict(thickness=10, len=0.6, outlinewidth=0, tickfont=dict(size=10, color=INK2), x=0.98)))
        fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator")
        core.style(fig, height=300, legend=None)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        core.show(fig, "ev_map")
        top = val.sort_values(ascending=False)
        core.takeaway(f"{top.index[0]} leads ({top.iloc[0]:,.0f}{' per 100,000 people' if metric != 'Units' else ' units'}), followed by {top.index[1]} and {top.index[2]}. "
                      "Demand sits in the big, richer metro areas, so any incentive or tariff relief for electric cars would mostly reach these states.")


def mix(d, end, label):
    with st.container(border=True):
        last12 = d[(d.date > end - pd.DateOffset(months=12)) & (d.date <= end) & (d.state != "Not specified")]
        t = last12.pivot_table(index="state", columns="tech", values="units", aggfunc="sum").fillna(0)
        t = t.loc[t.sum(axis=1).nlargest(12).index]
        sh = t.div(t.sum(axis=1), axis=0).sort_values("HEV" if "HEV" in t else t.columns[0])
        lead = sh.BEV.sort_values(ascending=False).index[:2] if "BEV" in sh else []
        core.chart_head("What kind", "Hybrids lead everywhere" + (f"; battery electrics do best in {lead[0]} and {lead[1]}" if len(lead) == 2 else ""),
                        f"Technology mix in the 12 biggest states, last 12 months{label}")
        fig = go.Figure()
        for c in [c for c in TECH if c in sh]:
            fig.add_bar(y=sh.index, x=sh[c], name=TECH_NAME[c], orientation="h", marker=dict(color=TECH[c], line=dict(color="#fff", width=1.5)),
                        customdata=t.loc[sh.index, c], hovertemplate="%{y}: %{x:.0%} (%{customdata:,.0f})<extra>" + TECH_NAME[c] + "</extra>")
        core.style(fig, height=380, legend="top", top=30)
        fig.update_layout(barmode="stack", bargap=0.25)
        fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor="#eeede7")
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=11.5))
        core.show(fig, "ev_mix")
        if "HEV" in sh:
            core.takeaway(f"Hybrids, which never need a plug, are between <b>{sh.HEV.min():.0%}</b> and <b>{sh.HEV.max():.0%}</b> of electrified sales in each of these states. "
                          "Plug-in hybrids take a similar slice everywhere, so the 2026 plug-in boom is national, not a Mexico City story.")


def page():
    h = core.table("electrified")
    start, end = core.window()
    d, techs, states, label = filters(h)
    core.page_head("Electrification",
                   "The electric boom runs on the imports the tariff targets",
                   "INEGI publishes hybrid (HEV), plug-in hybrid (PHEV) and battery electric (BEV) sales by state since 2016. "
                   "That table has no brand or origin, so I cross it with the sales table, where plug-in and electric models can be spotted by name. "
                   "Together they show that the 2026 jump in plug-in and electric cars is mostly a jump in Chinese imports.")
    kpis(d, end, techs)
    core.coverage("What this page cannot see", [
        "<b>BYD and Tesla do not report</b>, so battery-electric and plug-in sales are undercounted, probably by a lot: BYD is widely reported as Mexico's top seller of electric and plug-in cars.",
        "This table has <b>no brand, model or country of origin</b>. The link to Chinese imports comes from the sales table, by model name (EM-i, iDD, PHEV, EV...), so it is a lower bound: plug-ins without a telltale name are missed.",
        f"INEGI fills months it has not published with zeros. Months after {end:%B %Y} are dropped. In 2016 some cells say \"-\" and are read as zero.",
    ])
    monthly(d, techs, start, end, label)
    c1, c2 = st.columns([1.5, 1], gap="medium")
    with c1:
        if states:
            st.info("The share of the whole market is national only (the sales table has no states), so it is hidden while a state filter is on.")
        else:
            share(d, techs, start, end)
    with c2:
        named_models(end)
    c1, c2 = st.columns([1.2, 1], gap="medium")
    with c1:
        states_map(d, end, label)
    with c2:
        mix(d, end, label)
