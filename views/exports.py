"""The US wall: exports, destinations and what Mexico's plants make."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
from core import DEST, INK, INK2, MUTED, GRAY, NAVY

REGIONS = list(DEST)


def region(e):
    return e.dest_region.replace({"Rest of world": "Other & not specified", "Not specified": "Other & not specified"})


def filters(e, end):
    with st.sidebar:
        st.html('<p class="sb-h">Filters for this page</p>')
        top = e[e.date.dt.year == end.year].groupby("group").units.sum().sort_values(ascending=False).index
        groups = st.multiselect("Manufacturer group", list(top), placeholder="All groups", key="exp_grp")
        dests = st.multiselect("Destination", REGIONS, placeholder="All destinations", key="exp_dest")
        kind = st.segmented_control("Vehicle type", ["Cars", "Light trucks"], key="exp_type",
                                    help="Light trucks are SUVs, pickups and minivans. Leave both off to see everything.")
    label = [", ".join(x) for x in (groups, dests) if x] + ([kind] if kind else [])
    return groups, dests, kind, (" for " + "; ".join(label)) if label else ""


def apply(df, groups, kind):
    if groups:
        df = df[df.group.isin(groups)]
    if kind:
        df = df[df.type == kind]
    return df


def destinations(e, dests, start, end, label):
    months = pd.date_range(start - pd.DateOffset(months=11), end, freq="MS")
    m = e.assign(region=region(e)).pivot_table(index="date", columns="region", values="units", aggfunc="sum")
    m = m.reindex(months).fillna(0).reindex(columns=REGIONS, fill_value=0)
    r = core.rolling12(m).loc[start:end]
    us = r["United States"] / r.sum(axis=1)
    with st.container(border=True):
        core.chart_head("The long run", f"{us.iloc[-1]:.0%} of exported cars go to one customer, the United States",
                        f"Light-vehicle exports by destination, 12-month rolling total{label}")
        show = dests or REGIONS
        fig = go.Figure()
        for name in REGIONS[::-1]:
            if name in show:
                fig.add_scatter(x=r.index, y=r[name], name=name, stackgroup="one", mode="lines",
                                line=dict(color="#fff", width=1.2), fillcolor=DEST[name],
                                hovertemplate="%{y:,.0f}<extra>" + name + "</extra>")
        rows = core.mark_events(fig, start, end, "exports", width_px=820)
        core.style(fig, height=420, top=24 + rows * 15, yfmt="~s", xrange=(start, end))
        fig.update_layout(hovermode="x unified", legend=dict(traceorder="reversed"))
        core.show(fig, "exp_area")
        core.event_key()
        core.takeaway(f"The United States took <b>{us.iloc[-1]:.0%}</b> of the last twelve months' exports (it was {us.iloc[0]:.0%} at the start of the window). "
                      "Exports took until 2024 to get back to their 2019 level after the pandemic and the chip shortage, and have slipped again since the US 25% tariff in April 2025. "
                      "Canada's slice has grown since then, but it is still a fraction of the US.")
        c1, c2 = st.columns(2)
        with c1:
            core.numbers(r.round(0).assign(**{"US share": us.round(3)}).rename_axis("Month").sort_index(ascending=False))
        with c2:
            core.event_list(start, end, "exports")


def yoy_strip(e, start, end, label):
    with st.container(border=True):
        core.chart_head("Month by month", "Since the US tariff, the US is the market that keeps shrinking",
                        f"Exports against the same month a year earlier{label}")
        months = pd.date_range(max(start, end - pd.DateOffset(months=21)), end, freq="MS")
        m = e.assign(region=region(e)).pivot_table(index="date", columns="region", values="units", aggfunc="sum").fillna(0)
        m = m.reindex(columns=REGIONS, fill_value=0)
        m["All destinations"] = m.sum(axis=1)
        yoy = (m / m.shift(12).where(m.shift(12) > 0) - 1).reindex(months)
        z = yoy.T.clip(-0.6, 0.6)
        fig = go.Figure(go.Heatmap(z=z.values, x=yoy.index,
                                   y=z.index, colorscale=core.DIVERGE, zmid=0, zmin=-0.6, zmax=0.6, xgap=2, ygap=2, showscale=False,
                                   text=[[("" if pd.isna(v) else f"{v * 100:+.0f}") for v in r] for r in yoy.T.values],
                                   texttemplate="%{text}", textfont=dict(size=10),
                                   customdata=yoy.T.values, hovertemplate="%{y}, %{x|%b %Y}: %{customdata:+.1%}<extra></extra>"))
        core.style(fig, height=290, legend=None)
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK, size=12))
        fig.update_xaxes(linecolor="rgba(0,0,0,0)", tickfont=dict(size=10.5), tickvals=list(yoy.index),
                         ticktext=[d.strftime("%b<br>%Y") if d.month == 1 or d == yoy.index[0] else d.strftime("%b") for d in yoy.index])
        core.show(fig, "exp_strip")
        prelim = e[e.status == "Preliminary"].date.max()
        st.caption(f"Numbers are % change. Blue: more than a year earlier, red: less; colours stop at ±60%. {prelim:%B %Y} is preliminary and will be revised next month.")
        since = yoy.loc["2025-04-01":, "United States"].dropna()
        can = yoy.loc["2025-04-01":, "Canada"].dropna()
        core.takeaway("Each cell compares a month with the same month a year before, so seasons cancel out. "
                      f"Since the US tariff (April 2025), exports to the US fell against the year before in <b>{(since < 0).sum()} of {len(since)}</b> months, "
                      f"while exports to Canada rose in {(can > 0).sum()} of {len(can)}. Diversification is real, but small next to the US loss."
                      if len(since) else "Each cell compares a month with the same month a year before, so seasons cancel out.")


def brands_us(e, end, label):
    with st.container(border=True):
        core.chart_head("Who is losing the US", "Exports to the United States by brand",
                        f"{core.period_label(end)} vs {core.period_label(end, 1)}{label}")
        us = e[e.dest_country == "United States"]
        now, bef = core.ytd(us, end).groupby("brand").units.sum(), core.ytd(us, end, 1).groupby("brand").units.sum()
        t = pd.DataFrame({"now": now, "before": bef}).fillna(0)
        t = t[t.before > 5000]
        if t.empty:
            st.info("No exports to the US match these filters.")
            return
        t["chg"] = t.now / t.before - 1
        t["diff"] = t.now - t.before
        t = t.sort_values("chg")
        fig = go.Figure(go.Bar(x=t.chg, y=t.index, orientation="h",
                               marker=dict(color=["#b52f2f" if v < 0 else "#2a78d6" for v in t.chg], cornerradius=3),
                               text=[f"{c:+.0%}" for c in t.chg], textposition="outside",
                               textfont=dict(size=11, color=INK2), cliponaxis=False, customdata=t[["now", "before", "diff"]],
                               hovertemplate="%{y}: %{customdata[0]:,.0f} vs %{customdata[1]:,.0f} (%{customdata[2]:+,.0f})<extra></extra>"))
        fig.add_vline(x=0, line=dict(color="#c3c2b7", width=1))
        core.style(fig, height=max(300, 30 * len(t) + 40), legend=None)
        fig.update_xaxes(tickformat="+.0%", showgrid=True, gridcolor="#eeede7", range=[min(t.chg.min(), 0) - (t.chg.max() - t.chg.min()) * 0.35, max(t.chg.max(), 0) + (t.chg.max() - t.chg.min()) * 0.3])
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=12))
        core.show(fig, "exp_brands")
        lost = t["diff"].clip(upper=0).sum()
        worst = ", ".join(t[t.chg < 0].sort_values("diff").index[:3])
        best = ", ".join(t[t.chg > 0].sort_values("diff", ascending=False).index[:2])
        core.takeaway(f"Brands that cut US shipments lost <b>{-lost:,.0f}</b> units against last year, most of it at {worst}"
                      + (f", while {best} grew" if best else "") + ". The tariff hits by brand and model, so the Ministry's support has to be targeted too.")


def where_it_went(p, e, s, groups, kind, end, label):
    with st.container(border=True):
        core.chart_head("Where the output went", f"What Mexico built in {core.period_label(end)}, and where it went",
                        f"Production split into exports by destination and sales at home{label}")
        prod = core.ytd(apply(p, groups, kind), end).units.sum()
        ex = core.ytd(apply(e, groups, kind), end).assign(region=lambda x: region(x)).groupby("region").units.sum().reindex(REGIONS).fillna(0)
        home = core.ytd(apply(s[s.origin_block == "Made in Mexico"], groups, kind), end).units.sum()
        rest = prod - ex.sum() - home
        labels = [f"Built in Mexico<br>{prod:,.0f}"] + [f"{r}  {v:,.0f}" for r, v in ex.items()] + [f"Sold in Mexico  {home:,.0f}"]
        colors = [NAVY] + [DEST[r] for r in REGIONS] + ["#008300"]
        values = list(ex.values) + [home]
        if rest > 0:
            labels.append(f"Stock and other  {rest:,.0f}")
            colors.append(GRAY)
            values.append(rest)
        fig = go.Figure(go.Sankey(
            arrangement="snap", valueformat=",.0f",
            node=dict(label=labels, color=colors, pad=14, thickness=14, line=dict(width=0),
                      hovertemplate="%{label}<extra></extra>"),
            link=dict(source=[0] * len(values), target=list(range(1, len(values) + 1)), value=values,
                      color=[c + "55" for c in colors[1:]], hovertemplate="%{value:,.0f} units<extra></extra>")))
        core.style(fig, height=360, legend=None)
        fig.update_layout(font=dict(size=12, color=INK))
        core.show(fig, "exp_sankey")
        if prod:
            core.takeaway(f"<b>{ex.sum() / prod:.0%}</b> of what Mexico builds is exported, and <b>{ex['United States'] / prod:.0%}</b> goes to the US alone. "
                          f"Only {home / prod:.0%} is sold at home. A US tariff is a tariff on most of the industry, which is why it outweighs anything Mexico's own wall can protect.")
        if rest < 0:
            st.caption("These brands sold and exported more than they built this year, drawing down stock.")


def plants(p, start, end, label):
    with st.container(border=True):
        core.chart_head("Production", "Two plant closures show up as brand-level drops",
                        f"Light vehicles built in Mexico by manufacturer group, 12-month rolling total{label}")
        months = pd.date_range(start - pd.DateOffset(months=11), end, freq="MS")
        m = p.pivot_table(index="date", columns="group", values="units", aggfunc="sum").reindex(months).fillna(0)
        r = core.rolling12(m).loc[start:end]
        r = r.loc[:, r.iloc[-1].sort_values(ascending=False).index]
        r = r.loc[:, r.max() > 20000]
        hl = st.multiselect("Highlight", list(r.columns), default=[g for g in ("Nissan", "Mercedes-Benz") if g in r.columns],
                            key="exp_hl", placeholder="Pick groups to highlight")
        fig = go.Figure()
        for g in r.columns:
            on = g in hl
            fig.add_scatter(x=r.index, y=r[g], name=g, mode="lines", showlegend=on,
                            line=dict(color=NAVY if on else "#d4d2ca", width=2.4 if on else 1.3),
                            hovertemplate="%{y:,.0f}<extra>" + g + "</extra>", opacity=1 if on else 0.9)
        for g in hl:
            fig.add_annotation(x=r.index[-1], y=r[g].iloc[-1], text=f"<b>{g}</b> {r[g].iloc[-1]:,.0f}", showarrow=False,
                               xanchor="left", xshift=6, font=dict(size=11.5, color=INK))
        rows = core.mark_events(fig, start, end, "production", width_px=640)
        core.style(fig, height=420, top=24 + rows * 15, yfmt="~s", legend=None, xrange=(start, end))
        fig.update_layout(margin=dict(r=150), hovermode="closest")
        fig.data = tuple(sorted(fig.data, key=lambda t: t.name in hl))  # highlighted lines drawn on top
        core.show(fig, "exp_plants")
        tbl = pd.DataFrame({core.period_label(end): core.ytd(p, end).groupby("group").units.sum(),
                            core.period_label(end, 1): core.ytd(p, end, 1).groupby("group").units.sum()}).fillna(0)
        tbl["change"] = (tbl.iloc[:, 0] / tbl.iloc[:, 1] - 1).round(3)
        core.takeaway("Nissan closed its CIVAC plant in March 2026 and the Nissan and Mercedes-Benz COMPAS plant in May. "
                      "The registry counts output by brand, not by plant, so the closures only show up as these brand-level falls. "
                      "Every unit lost here is mostly an export lost, because the work moved to plants abroad.")
        c1, c2 = st.columns(2)
        with c1:
            core.numbers(tbl.sort_values(tbl.columns[0], ascending=False), "Production by group, year to date")
        with c2:
            core.event_list(start, end, "production")


def page():
    p, e, s = core.table("production"), core.table("exports"), core.table("sales")
    start, end = core.window()
    groups, dests, kind, label = filters(e, end)
    ef = apply(e, groups, kind)
    ef_d = ef[region(ef).isin(dests)] if dests else ef
    core.page_head("The US wall: exports",
                   "The bigger wall is the one Mexico does not control",
                   "About 86% of the cars built in Mexico are exported, and almost 80% of exports go to the United States. "
                   "Since April 2025 those cars pay a US tariff on their non-US content. This page shows what that is costing, which brands carry it, "
                   "and whether other markets can make up the difference.")
    destinations(ef, dests, start, end, label)
    prelim = e[e.status == "Preliminary"].date.max()
    core.coverage("What this page cannot see", [
        f"<b>{prelim:%B %Y} numbers are still preliminary.</b> INEGI revises them next month, "
        "and they stay \"revised\" for three years before they become final.",
        "<b>INEGI counts cars by brand, not by plant or state.</b> The CIVAC and COMPAS closures come from the press, not from the registry.",
        "<b>Only automakers that belong to AMIA report</b>, so any exporter outside it is missing.",
        "<b>Exports come in units, with no price or value.</b> If brands shift to cheaper or pricier models, this page can't see it.",
        "<b>Some exports have no destination.</b> INEGI marks them \"not specified\" (201,000 cars in 2017 alone), "
        "and I group them with the rest of the world.",
    ])
    yoy_strip(ef_d, start, end, label)
    c1, c2 = st.columns([1, 1.15], gap="medium")
    with c1:
        brands_us(ef, end, label)
    with c2:
        where_it_went(p, e, s, groups, kind, end, label)  # always every destination, or the split would not add up
    plants(apply(p, groups, kind), start, end, label)
