"""Mexico's wall: what the January 2026 tariff has (and hasn't) done to imported car sales."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
from core import ORIGIN, INK, INK2, MUTED, GRAY, NAVY

SEGMENTS = ["Subcompact", "Compact", "SUV", "Pickup", "Minivan", "Luxury", "Sports"]
CUSTOMS_URL = "https://www.larepublica.co/globoeconomia/importaciones-de-autos-chinos-a-mexico-caen-31-1-con-arancel-de-50-4471274"
NO_DEAL = ("China", "Other no-deal countries")


def filters(s, start, end):
    with st.sidebar:
        st.html('<p class="sb-h">Filters for this page</p>')
        segs = st.multiselect("Segment", SEGMENTS, placeholder="All segments", key="imp_seg")
        top = s[s.date.dt.year == end.year].groupby("group").units.sum().sort_values(ascending=False).index
        groups = st.multiselect("Manufacturer group", list(top), placeholder="All groups", key="imp_grp")
        same = st.toggle("Like-for-like brands", key="imp_same",
                         help="Keep only brands that were already reporting in the first month of the time window and still report in the last one. "
                              "Brands entering or leaving the registry can then no longer move the lines.")
    d = s
    if segs:
        d = d[d.segment.isin(segs)]
    if groups:
        d = d[d.group.isin(groups)]
    if same:
        c = core.table("coverage")
        d = d[d.raw_brand.isin(c[(c["first"] <= start) & (c["last"] >= end)].raw_brand)]
    label = [", ".join(x) for x in (segs, groups) if x] + (["like-for-like brands"] if same else [])
    return d, (" for " + "; ".join(label)) if label else ""


def by_block(d, start, end):
    months = pd.date_range(start - pd.DateOffset(months=11), end, freq="MS")
    m = d[d.date.isin(months)].pivot_table(index="date", columns="origin_block", values="units", aggfunc="sum")
    m = m.reindex(months).fillna(0).reindex(columns=list(ORIGIN), fill_value=0)
    return core.rolling12(m).loc[start:end]


def hero(d, start, end, label):
    r = by_block(d, start, end)
    with st.container(border=True):
        if r.empty or r.sum().sum() == 0:
            st.info("No sales match these filters.")
            return
        sh = r.div(r.sum(axis=1), axis=0)
        cn, mx = sh.China.iloc[-1], sh["Made in Mexico"].iloc[-1]
        core.chart_head("The long run", f"{cn:.0%} of the cars sold in Mexico are now made in China",
                        f"Share of light-vehicle sales by where the car was built, 12-month rolling total{label}")
        view = st.segmented_control("View", ["Share of sales", "Units (12-month total)"], default="Share of sales", required=True,
                                    key="imp_view", label_visibility="collapsed")
        units = view == "Units (12-month total)"
        y = r if units else sh
        fig = go.Figure()
        for name, color in ORIGIN.items():
            fig.add_scatter(x=y.index, y=y[name], name=name, mode="lines", line=dict(color=color, width=2.6 if name == "China" else 2),
                            hovertemplate=("%{y:,.0f}" if units else "%{y:.1%}") + f"<extra>{name}</extra>")
        rows = core.mark_events(fig, start, end, "sales", width_px=640)
        core.style(fig, height=440, top=24 + rows * 15, ypct=not units, yfmt=",.0f", xrange=(start, end))
        core.end_labels(fig, y, ORIGIN, fmt="{:,.0f}" if units else "{:.0%}")
        fig.update_layout(hovermode="x unified")
        core.show(fig, "imp_hero")
        core.event_key()
        cn0 = sh.China.iloc[0]
        core.takeaway(f"Mexico builds about four million cars a year, yet only <b>{mx:.0%}</b> of the cars Mexicans buy are made here. "
                      f"The China-made share went from <b>{cn0:.0%}</b> to <b>{cn:.0%}</b> over this window, and it kept rising after the January 2026 tariff, "
                      "the opposite of what the tariff was meant to do.")
        c1, c2 = st.columns(2)
        with c1:
            core.numbers(y.assign(**{"Total (12 months)": r.sum(axis=1)}).round(3).rename_axis("Month").sort_index(ascending=False))
        with c2:
            core.event_list(start, end, "sales")


def after_tariff(d, s, start, end, label):
    c1, c2 = st.columns([1.5, 1], gap="medium")
    months = pd.date_range(max(start, end - pd.DateOffset(months=21)), end, freq="MS")
    m = d.assign(china=d.origin_block.eq("China")).pivot_table(index="date", columns="china", values="units", aggfunc="sum").fillna(0)
    m = m.reindex(columns=[True, False], fill_value=0)
    yoy = (m / m.shift(12).where(m.shift(12) > 0) - 1).reindex(months)
    since = yoy.loc["2026-01-01":, True].dropna()
    with c1, st.container(border=True):
        title = (f"China-made sales beat the year before in {(since > 0).sum()} of the {len(since)} months since the tariff"
                 if len(since) else "China-made sales against the year before")
        core.chart_head("After 1 January 2026", title, f"Change against the same month a year earlier{label}")
        fig = go.Figure()
        fig.add_bar(x=yoy.index, y=yoy[True], name="Made in China", marker=dict(color=ORIGIN["China"], cornerradius=3),
                    hovertemplate="%{y:+.0%}<extra>Made in China</extra>")
        fig.add_bar(x=yoy.index, y=yoy[False], name="All other cars", marker=dict(color=GRAY, cornerradius=3),
                    hovertemplate="%{y:+.0%}<extra>All other cars</extra>")
        fig.add_hline(y=0, line=dict(color="#c3c2b7", width=1))
        rows = core.mark_events(fig, months[0], end, "sales", width_px=480)
        core.style(fig, height=340, top=22 + rows * 15, ypct=True,
                   xrange=(months[0] - pd.Timedelta(days=16), end + pd.Timedelta(days=16)))
        fig.update_layout(bargap=0.25, bargroupgap=0.08, hovermode="x unified")
        fig.update_yaxes(tickformat="+.0%")
        core.show(fig, "imp_yoy")
        core.numbers(yoy.rename(columns={True: "Made in China", False: "All other cars"}).round(3).rename_axis("Month"))
    with c2, st.container(border=True):
        h1 = lambda y: s[(s.date.dt.year == y) & (s.date.dt.month <= 6) & (s.origin_block == "China")].units.sum()
        core.chart_head("Two numbers that disagree", "Sales went up while shipments fell", "First half of 2026 against the first half of 2025")
        st.html(f"""<div class="vs">
<div><p class="n up">{core.chg(h1(2026), h1(2025)):+.0%}</p><div><p class="l">Sold to Mexican buyers</p>
<p class="d">China-made cars sold by brands in the registry: {h1(2026):,.0f} units (INEGI, RAIAVL).</p></div></div>
<div><p class="n down">−31%</p><div><p class="l">Arriving from China</p>
<p class="d">Chinese car imports: 158,571 units, as reported by the Secretaría de Economía.
<a href="{CUSTOMS_URL}" target="_blank">El Economista via La República, 31 Aug 2026</a>. Not in the registry.</p></div></div></div>""")
        core.takeaway("Buyers kept getting more China-made cars while fewer arrived. The likeliest bridge is stock shipped in after the September 2025 announcement and before January. "
                      "So 2026 sales overstate how open the border still is, and the real test comes when that stock runs out.")
        st.caption("The two sources count different things (retail sales of reporting brands vs. all imports, BYD included), so only their direction is compared.")


def who_sells(d, end, label):
    cn = d[d.origin_block == "China"]
    now = core.ytd(cn, end).groupby("brand").units.sum()
    before = core.ytd(cn, end, 1).groupby("brand").units.sum()
    t = pd.DataFrame({"before": before, "now": now}).fillna(0)
    t = t[(t.now + t.before) > 300].sort_values("now")
    with st.container(border=True):
        if t.empty:
            core.chart_head("Who sells them", "China-made cars by brand")
            st.info("No China-made sales match these filters.")
            return
        info = d.drop_duplicates("brand").set_index("brand")
        chinese = [info.brand_home.get(b) == "China" for b in t.index]
        cov = core.table("coverage").groupby("brand")["last"].max()
        gone = {b for b in t.index if cov.get(b, core.LAST) < core.LAST - pd.DateOffset(months=3)}
        top = t.now.idxmax()
        top_cn = info.brand_home.get(top) == "China"
        core.chart_head("Who sells them",
                        f"The biggest seller of China-made cars is {top}" + ("" if top_cn else ", not a Chinese brand"),
                        f"China-made cars sold, {core.period_label(end, 1)} vs {core.period_label(end)}{label}")
        fig = go.Figure()
        for b, row in t.iterrows():
            fig.add_scatter(x=[row.before, row.now], y=[b, b], mode="lines", line=dict(color="#d9d7cf", width=3), showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=t.before, y=t.index, mode="markers", name=core.period_label(end, 1),
                        marker=dict(size=10, color="#fff", line=dict(color=MUTED, width=2)),
                        hovertemplate="%{x:,.0f}<extra>" + core.period_label(end, 1) + "</extra>")
        fig.add_scatter(x=t.now, y=t.index, mode="markers", showlegend=False,
                        marker=dict(size=12, color=[ORIGIN["China"] if c else NAVY for c in chinese], line=dict(color="#fff", width=2)),
                        hovertemplate="%{x:,.0f}<extra>" + core.period_label(end) + "</extra>")
        for name, col in [("Chinese brand", ORIGIN["China"]), ("global brand", NAVY)]:
            fig.add_scatter(x=[None], y=[None], mode="markers", name=f"{core.period_label(end)}, {name}", marker=dict(size=12, color=col))
        for b, row in t.iterrows():
            if b in gone:
                txt = f"{row.now:,.0f}  (stopped reporting)"
            elif row.before:
                txt = f"{row.now:,.0f}  ({core.chg(row.now, row.before):+.0%})"
            else:
                txt = f"{row.now:,.0f}  (new in the registry)"
            fig.add_annotation(x=max(row.now, row.before), y=b, text=txt, showarrow=False, xanchor="left", xshift=10,
                               font=dict(size=11, color=INK2))
        core.style(fig, height=max(300, 30 * len(t) + 80), legend="top", top=40)
        fig.update_xaxes(gridcolor="#eeede7", showgrid=True, tickformat=",.0f", range=[0, t.max().max() * 1.25])
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=12))
        core.show(fig, "imp_who")
        glob_share = t.now[[not c for c in chinese]].sum() / t.now.sum() if t.now.sum() else 0
        global_names = ", ".join(dict.fromkeys(info.group.get(b) for b in t[[not c for c in chinese]].sort_values("now", ascending=False).index[:5]))
        core.takeaway(f"<b>{glob_share:.0%}</b> of the China-made cars sold in {core.period_label(end)} carry a non-Chinese badge ({global_names}). "
                      "These brands build the cars in China and import them, so a tariff on Chinese-made cars also taxes American, Korean and European brands. "
                      "They belong in any negotiation. Brands marked \"stopped reporting\" did not stop selling, the registry just stopped seeing them.")
        core.numbers(t.assign(change=lambda x: (x.now / x.before.where(x.before > 0) - 1).round(3)).sort_values("now", ascending=False)
                     .rename(columns={"before": core.period_label(end, 1), "now": core.period_label(end)}))


def segments_and_origins(d, start, end, label):
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        years = list(range(max(start.year, 2017), end.year + 1))
        cols = {}
        for y in years:
            yy = d[(d.date.dt.year == y) & (d.date <= end)]
            cols[f"’{y % 100:02d}" + ("*" if y == end.year and end.month < 12 else "")] = (
                yy[yy.origin_block == "China"].groupby("segment").units.sum() / yy.groupby("segment").units.sum())
        hm = pd.DataFrame(cols).reindex([x for x in SEGMENTS if x in d.segment.unique()]).fillna(0)
        last = hm.iloc[:, -1].sort_values(ascending=False)
        core.chart_head("Where they win", f"China-made cars hold {last.iloc[0]:.0%} of {last.index[0].lower()} sales",
                        f"Share of each segment's sales built in China{label}")
        fig = go.Figure(go.Heatmap(z=hm.values, x=list(hm.columns), y=list(hm.index), colorscale=core.RED_RAMP, zmin=0, zmax=0.5,
                                   text=[[f"{v:.0%}" for v in r] for r in hm.values], texttemplate="%{text}",
                                   textfont=dict(size=11), xgap=2, ygap=2, showscale=False,
                                   hovertemplate="%{y}, %{x}: %{z:.1%} made in China<extra></extra>"))
        core.style(fig, height=330, legend=None)
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK, size=12))
        fig.update_xaxes(type="category", side="top", linecolor="rgba(0,0,0,0)")
        core.show(fig, "imp_seg_heat")
        st.caption(f"\\* {core.period_label(end)}. Colour scale tops out at 50%.")
        core.takeaway("China-made cars are strongest in subcompacts, SUVs and minivans, the segments where first-time and family buyers shop. "
                      "Luxury is the newest front: Geely's Zeekr and Lynk & Co arrived in January 2026, the same month the tariff started.")
    with c2, st.container(border=True):
        now = core.ytd(d, end).groupby(["origin_country", "origin_block"]).units.sum()
        bef = core.ytd(d, end, 1).groupby(["origin_country", "origin_block"]).units.sum()
        t = pd.DataFrame({"now": now, "before": bef}).fillna(0).reset_index()
        t = t[t.origin_block != "Not specified"].nlargest(10, "now")
        t["chg"] = t.now / t.before.where(t.before > 0) - 1
        t = t.dropna(subset=["chg"]).sort_values("chg")
        nd = t[t.origin_block.isin(NO_DEAL)]
        up, down = nd[nd.chg > 0].sort_values("chg", ascending=False).origin_country.tolist(), nd[nd.chg <= 0].origin_country.tolist()
        core.chart_head("Which origins grew", f"{len(up)} of the {len(nd)} biggest no-deal origins still grew",
                        f"Sales by country where the car was built, {core.period_label(end)} vs {core.period_label(end, 1)}{label}")
        fig = go.Figure(go.Bar(x=t.chg, y=t.origin_country, orientation="h", showlegend=False,
                               marker=dict(color=[ORIGIN[b] for b in t.origin_block], cornerradius=3),
                               customdata=t[["now", "before"]], text=[f"{v:+.0%}" for v in t.chg], textposition="outside",
                               textfont=dict(size=11, color=INK2), cliponaxis=False,
                               hovertemplate="%{y}: %{customdata[0]:,.0f} vs %{customdata[1]:,.0f} (%{x:+.1%})<extra></extra>"))
        fig.add_vline(x=0, line=dict(color="#c3c2b7", width=1))
        for b, col in ORIGIN.items():
            fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, color=col, symbol="square"), name=b)
        core.style(fig, height=360, legend="bottom")
        lo, hi = t.chg.min(), t.chg.max()
        fig.update_xaxes(tickformat="+.0%", showgrid=True, gridcolor="#eeede7", range=[min(lo, 0) - 0.12, max(hi, 0) + 0.12])
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=12))
        fig.update_layout(legend=dict(y=-0.14))
        core.show(fig, "imp_orig")
        core.takeaway(f"The ten largest origins this year. If the tariff were biting, the amber and red bars would be the ones shrinking. "
                      f"Instead {', '.join(up) or 'none'} grew" + (f", and only {', '.join(down)} fell" if down else "") + ". "
                      "Some brands are already switching sources: Honda stopped selling India- and Indonesia-built cars here and sells more from Brazil, a trade-deal partner.")


def page():
    s = core.table("sales")
    start, end = core.window()
    d, label = filters(s, start, end)
    core.page_head("Mexico's wall: imports",
                   "The tariff wall is up, but China-made sales are still climbing",
                   "Since 1 January 2026, cars from countries without a trade agreement with Mexico pay up to 50%. "
                   "Ten months in, the registry shows China-made sales above last year almost every month. "
                   "This page asks whether the tariff is working, who it really hits, and why the answer is not in yet.")
    hero(d, start, end, label)
    c = core.table("coverage").set_index("raw_brand")
    core.coverage("What this page cannot see", [
        "<b>BYD and Tesla have never reported to INEGI.</b> BYD is widely reported as Mexico's best-selling Chinese brand, "
        "so its cars are missing from every line on this page.",
        f"<b>Chirey and Omoda stopped reporting after {c.loc['Chirey', 'last']:%B %Y}.</b> They had reported "
        f"{c.loc['Chirey', 'units'] + c.loc['Omoda', 'units']:,.0f} cars by then. When the China line dips after that, "
        "it's because the registry lost them, not because buyers did.",
        "<b>GAC joined in November 2026 and sent its sales back to January 2024</b>, so the 2024 and 2025 totals changed after the fact. "
        "Jetour changed its name to Jetour Soueast, and I count both names as one brand.",
        f"<b>Motornation last reported in {c.loc['MOTORNATION', 'last']:%B %Y}.</b> It's the distributor behind Changan, BAIC and JMC models, "
        "and INEGI drops it from November 2026.",
        "All of this points the same way: the real China-made share is <b>higher</b> than shown. To compare like with like, "
        "turn on <i>Like-for-like brands</i> in the sidebar. It keeps only brands that reported for the whole time window.",
    ])
    after_tariff(d, s, start, end, label)
    who_sells(d, end, label)
    segments_and_origins(d, start, end, label)
