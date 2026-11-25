"""Briefing: who I am, who this is for, the decision, and the story in five numbers."""
import pandas as pd
import streamlit as st

import core


def spark(series, end):
    return core.rolling12(series).loc[end - pd.DateOffset(months=59):end].round(4).tolist()


def page():
    s, p, e, h = core.table("sales"), core.table("production"), core.table("exports"), core.table("electrified")
    _, end = core.window()
    now, bef = core.period_label(end), core.period_label(end, 1)

    core.page_head(f"Briefing note, {pd.Timestamp(core.vintage()['downloaded']):%B %Y}, data to {core.LAST:%B %Y}",
                   "Mexico is caught between two tariff walls",
                   "Mexico builds about four million light vehicles a year and exports most of them, while its own buyers increasingly choose imports. "
                   "In 2025 and 2026 two tariff walls went up: the United States taxed the cars Mexico sends north, and Mexico taxed the cars coming from countries "
                   "without a trade agreement, China first of all. This dashboard reads INEGI's vehicle registry to see what each wall has done so far, "
                   "and what the registry cannot see.")

    st.html("""<div class="role">
<div><p class="l">My role</p><p>Analyst in the economic intelligence team of the <b>Secretaría de Economía</b>, which designed the January 2026 tariff and negotiates with the US.</p></div>
<div><p class="l">Who this is for</p><p>The <b>Subsecretaría de Industria y Comercio</b>: the people who set tariff rates, meet the automakers and AMIA, and brief the Secretary before each trade meeting.</p></div>
<div><p class="l">The decision</p><p>Whether to <b>keep, adjust or extend</b> the 50% tariff on light vehicles in its first review, how to defend export volumes in the US, and whether to require <b>every brand</b> to report to the registry.</p></div>
</div>""")

    # five numbers, each the same months of the year against the year before
    ytd = lambda df, back=0: core.ytd(df, end, back).units.sum()
    cn = s[s.origin_block == "China"]
    cn_sh, cn_sh0 = ytd(cn) / ytd(s), ytd(cn, 1) / ytd(s, 1)
    us = e[e.dest_country == "United States"]
    el_sh, el_sh0 = ytd(h) / ytd(s), ytd(h, 1) / ytd(s, 1)
    monthly = lambda df: df.groupby("date").units.sum()
    share_series = monthly(cn).reindex(monthly(s).index).fillna(0)
    c = st.columns(5)
    c[0].metric("Sales in Mexico", core.k(ytd(s)), f"{core.chg(ytd(s), ytd(s, 1)):+.1%}",
                border=True, chart_data=spark(monthly(s), end), help="Retail sales, year to date. Sparkline: 12-month total, last five years.")
    c[1].metric("Made in China", f"{cn_sh:.1%}", f"{(cn_sh - cn_sh0) * 100:+.1f} pts",
                delta_color="inverse", border=True,
                chart_data=(core.rolling12(share_series) / core.rolling12(monthly(s))).loc[end - pd.DateOffset(months=59):end].round(4).tolist(),
                help="Share of retail sales built in China, year to date. Sparkline: 12-month share, last five years.")
    c[2].metric("Production", core.k(ytd(p)), f"{core.chg(ytd(p), ytd(p, 1)):+.1%}",
                border=True, chart_data=spark(monthly(p), end), help="Production, year to date. The last month is preliminary.")
    c[3].metric("Exports to US", core.k(ytd(us)), f"{core.chg(ytd(us), ytd(us, 1)):+.1%}",
                border=True, chart_data=spark(monthly(us), end), help="Exports to the United States, year to date. The last month is preliminary.")
    c[4].metric("Electrified", f"{el_sh:.1%}", f"{(el_sh - el_sh0) * 100:+.1f} pts",
                border=True, chart_data=(core.rolling12(monthly(h)) / core.rolling12(monthly(s))).loc[end - pd.DateOffset(months=59):end].round(4).tolist(),
                help="Hybrid, plug-in hybrid and battery electric sales as a share of all sales, year to date.")
    st.caption(f"{now} against {bef}, the same months a year before, so seasons cancel out. Sparklines: 12-month rolling, last five years.")

    st.html('<p class="eyebrow" style="margin:1.4rem 0 .5rem">Three things to know</p>')
    h1 = lambda y: s[(s.date.dt.year == y) & (s.date.dt.month <= 6) & (s.origin_block == "China")].units.sum()
    can = e[e.dest_country == "Canada"]
    st.html(f"""<div class="find">
<div class="china"><p class="n">{core.chg(h1(2026), h1(2025)):+.0%}</p><p class="t">China-made sales, first half of 2026</p>
<p class="b">The tariff started in January, yet China-made sales rose while the Ministry's own figures show Chinese car imports down 31%. Dealers are selling stock shipped in early. The tariff's real test is still ahead.</p></div>
<div class="us"><p class="n">{core.chg(ytd(us), ytd(us, 1)):+.0%}</p><p class="t">Exports to the US, {now}</p>
<p class="b">The US wall costs more than Mexico's own wall protects: {ytd(us, 1) - ytd(us):,.0f} fewer cars went north. Canada ({core.chg(ytd(can), ytd(can, 1)):+.0%}) helps, but it takes only {ytd(can) / ytd(us):.0%} as many cars as the US.</p></div>
<div class="gap"><p class="n">0</p><p class="t">Cars reported by BYD, ever</p>
<p class="b">The best-selling Chinese brand never reports, Chirey stopped in 2025 and new brands join with rewritten history. The registry undercounts exactly what the tariff targets.</p></div>
</div>""")

    st.html('<p class="eyebrow" style="margin:1.6rem 0 .3rem">Questions guiding this briefing</p>')
    c1, c2 = st.columns([1.15, 1], gap="large")
    with c1:
        st.html("""<ol class="qs">
<li>Has the January 2026 tariff slowed sales of China-made cars? <small><a href="imports" target="_self">Mexico's wall</a></small></li>
<li>Who actually sells China-made cars, and in which segments, so who does the tariff hit? <small><a href="imports" target="_self">Mexico's wall</a></small></li>
<li>How much are exports to the US losing, which brands carry it, and is diversification real? <small><a href="exports" target="_self">The US wall</a></small></li>
<li>Is electrification helped or hurt by a tariff that also covers electric cars? <small><a href="electric" target="_self">Electrification</a></small></li>
<li>What can't the registry see, and how does that change the answers? <small><a href="registry" target="_self">What the registry can't see</a></small></li>
</ol>""")
    with c2:
        st.html("""<table class="tbl"><tr><th>RAIAVL table</th><th>Why I use it</th></tr>
<tr><td>Ventas al público</td><td>The only table with the <b>country where each car was built</b>. It shows what the tariff should be stopping.</td></tr>
<tr><td>Exportación</td><td>Exports by <b>destination country</b>: the US exposure and any diversification.</td></tr>
<tr><td>Producción</td><td>What Mexico builds by brand. Crossed with exports and sales, it shows where output goes.</td></tr>
<tr><td>Híbridos y eléctricos</td><td>Technology by <b>state</b>. Crossed with sales, it shows that electrification depends on imports.</td></tr>
</table>""")
    st.caption("Use the time window and filters in the sidebar. Lines and shaded bands on the charts mark the events behind each change; the amber boxes say what the data cannot show.")
