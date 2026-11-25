"""What the registry can't see: coverage, figure status, harmonization, limits and recommendations."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
from core import INK, INK2, MUTED, NAVY, ORIGIN

MISSING = [("BYD", "China", "Sells in Mexico, never reports to INEGI"), ("Tesla", "United States", "Sells in Mexico, never reports to INEGI")]
STATUS_COLOR = {"Definitive": "#1F3A5F", "Revised": "#86b6ef", "Preliminary": "#eda100"}


def timeline():
    with st.container(border=True):
        core.chart_head("The panel keeps changing", "Who reports to the registry, and when",
                        "Months with sales reported, by brand as INEGI names it. Red: Chinese brands")
        c = core.table("coverage")
        every = st.toggle("Show all brands", key="reg_all", help="Off: only brands that joined or left after 2015, plus brands that never report.")
        gone = core.LAST - pd.DateOffset(months=3)  # no sales in the last four months = left the registry
        if not every:
            c = c[(c["first"] > "2015-01-01") | (c["last"] < gone)]
        c = c.sort_values("first", ascending=False)
        fig = go.Figure()
        for _, r in c.iterrows():
            color = ORIGIN["China"] if r.brand_home == "China" else NAVY
            left = r["last"] < gone
            fig.add_scatter(x=[r["first"], r["last"] + pd.DateOffset(months=1)], y=[r.raw_brand] * 2, mode="lines",
                            line=dict(color=color, width=9), showlegend=False,
                            hovertemplate=f"<b>{r.raw_brand}</b> ({r.group})<br>{r['first']:%b %Y} to {r['last']:%b %Y}<br>{r.units:,.0f} units reported<extra></extra>")
            note = ("renamed Jetour Soueast" if r.raw_brand == "JETOUR" else f"last data {r['last']:%b %Y}") if left else ""
            if note:
                fig.add_annotation(x=r["last"] + pd.DateOffset(months=1), y=r.raw_brand, text=note, showarrow=False, xanchor="left",
                                   xshift=6, font=dict(size=10.5, color=INK2))
        for name, home, why in MISSING:
            fig.add_scatter(x=[core.LAST], y=[f"{name} (never reports)"], mode="markers", showlegend=False,
                            marker=dict(symbol="x-thin-open", size=11, color=ORIGIN["China"] if home == "China" else NAVY, line=dict(width=2)),
                            hovertemplate=f"<b>{name}</b><br>{why}<extra></extra>")
            fig.add_annotation(x=core.LAST, y=f"{name} (never reports)", text="sells in Mexico today, no data ever", showarrow=False,
                               xanchor="right", xshift=-10, font=dict(size=10.5, color=INK2))
        n = len(c) + len(MISSING)
        x0, x1 = c["first"].min() - pd.DateOffset(months=6), core.LAST + pd.DateOffset(months=60)
        core.mark_events(fig, x0, core.LAST, "registry", width_px=700)
        core.style(fig, height=max(380, 22 * n + 80), legend=None, top=26, xrange=(x0, x1))
        fig.update_yaxes(showgrid=False, tickfont=dict(color=INK, size=11), categoryorder="array",
                         categoryarray=[f"{m[0]} (never reports)" for m in MISSING][::-1] + list(c.raw_brand))
        fig.update_xaxes(showgrid=True, gridcolor="#eeede7")
        core.show(fig, "reg_gantt")
        core.takeaway("Most Chinese brands joined after 2020, several left again, and the biggest ones are missing entirely. "
                      "A rise or fall in the China line can come from the panel changing, not the market. That is why the Mexico's wall page has a like-for-like switch.")


def status_strip():
    with st.container(border=True):
        core.chart_head("Which numbers are final", "Figure status by month", "As published in the vintage used here")
        rows = []
        for name in ["sales", "production", "exports"]:
            t = core.table(name)
            t = t[t.date >= "2021-01-01"].groupby("date").status.agg(lambda x: x.mode()[0])
            rows.append(t.rename(name.capitalize()))
        st_tbl = pd.DataFrame(rows)
        code = {k: i for i, k in enumerate(STATUS_COLOR)}
        z = st_tbl.replace(code).astype(float)
        scale = [[0, STATUS_COLOR["Definitive"]], [0.33, STATUS_COLOR["Definitive"]], [0.34, STATUS_COLOR["Revised"]],
                 [0.66, STATUS_COLOR["Revised"]], [0.67, STATUS_COLOR["Preliminary"]], [1, STATUS_COLOR["Preliminary"]]]
        fig = go.Figure(go.Heatmap(z=z.values, x=st_tbl.columns, y=st_tbl.index, colorscale=scale, zmin=0, zmax=2, showscale=False,
                                   xgap=1, ygap=3, customdata=st_tbl.values, hovertemplate="%{y}, %{x|%b %Y}: %{customdata}<extra></extra>"))
        for k, col in STATUS_COLOR.items():
            fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(size=11, color=col, symbol="square"), name=k)
        core.style(fig, height=210, legend="bottom")
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", tickfont=dict(color=INK, size=12))
        fig.update_layout(legend=dict(y=-0.25))
        core.show(fig, "reg_status")
        v = core.vintage()
        st.caption(f"Vintage: published {v['sales']['published']}, downloaded {v['downloaded']}. Sales are revised as soon as they are published; production and exports "
                   "start as preliminary and become revised a month later. Revised figures turn definitive each February, three years on.")


def harmonization():
    with st.container(border=True):
        core.chart_head("How names were harmonized", "One name per brand, one group per company",
                        "Different tables and years spell the same company differently. pipeline/clean.py maps each one")
        c = core.table("coverage")[["raw_brand", "brand", "group", "brand_home", "first", "last", "units"]]
        p = core.table("production").drop_duplicates("raw_brand")[["raw_brand", "brand", "group", "brand_home"]]
        extra = p[~p.raw_brand.isin(c.raw_brand)].assign(note="production and exports only")
        t = pd.concat([c, extra]).rename(columns={"raw_brand": "Name in INEGI file", "brand": "Brand used here", "group": "Group",
                                                  "brand_home": "Brand's home country", "first": "First sale", "last": "Last sale",
                                                  "units": "Units reported", "note": "Note"})
        st.dataframe(t, hide_index=True, width="stretch", height=320,
                     column_config={"First sale": st.column_config.DateColumn(format="MMM YYYY"),
                                    "Last sale": st.column_config.DateColumn(format="MMM YYYY"),
                                    "Units reported": st.column_config.NumberColumn(format="%,d")})
        st.caption("Examples: Stellantis = Chrysler (with Jeep, Dodge and RAM) + Fiat + Peugeot + Alfa Romeo. JETOUR and Jetour Soueast are one brand. "
                   "\"BMW Group\" and \"Mercedes Benz_Prod_Expo\" in the production files are BMW and Mercedes-Benz.")


def page():
    core.page_head("What the registry can't see",
                   "The registry undercounts exactly what the tariff targets",
                   "RAIAVL is an administrative record, not a survey: INEGI publishes what each automaker reports, without statistical treatment, "
                   "and companies revise their figures. That is a strength (it is complete for the companies inside) and a limit (it is blind to the ones outside). "
                   "This page shows the limits, how the dashboard handles them, and what the Subsecretaría should do with the findings.")
    timeline()
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1, st.container(border=True):
        core.chart_head("Blind spots", "Four things the registry cannot see")
        st.html("""<ul class="recs">
<li><b>Brands that don't report.</b> BYD and Tesla never have, Chirey and Omoda stopped in 2025, Motornation leaves in November 2026. INEGI adds brands with back data (GAC), so past totals can change.</li>
<li><b>Imports at the border.</b> Sales by country of origin are retail sales of reporting brands, not import flows. Stock shipped early, like the cars that beat the January tariff, only shows up months later.</li>
<li><b>Prices.</b> Nothing on prices or values, so whether brands absorbed the 50% tariff or passed it to buyers is invisible. So is the value lost on US exports.</li>
<li><b>Plants and used cars.</b> Output is by brand, not plant or state, and imported used cars are outside the registry.</li>
</ul>""")
    with c2, st.container(border=True):
        core.chart_head("What I did about it", "How the dashboard handles the gaps")
        st.html("""<ul class="recs">
<li><b>Said it on screen.</b> Every page has an amber box with its own blind spots, and the timeline above shows who is in and out.</li>
<li><b>Like-for-like switch.</b> On Mexico's wall you can keep only brands present for the whole time window, so panel changes can't move the lines.</li>
<li><b>Harmonized names.</b> One brand and group per company across tables and years (table below).</li>
<li><b>Seasons removed.</b> 12-month rolling totals for the long run, same months of the year before for 2026.</li>
<li><b>Status kept.</b> The pipeline keeps INEGI's status column, and preliminary months are flagged.</li>
</ul>""")
    status_strip()
    harmonization()
    with st.container(border=True):
        core.chart_head("For the Subsecretaría", "Recommendations")
        st.html("""<ul class="recs">
<li><b>1. Don't judge the tariff on 2026 sales.</b> Stock shipped before January is still being sold. Track customs imports from China next to registry sales each month. If China-made sales are still above 20% of the market in the twelve months to mid-2027, after the stock is gone, the tariff is being absorbed rather than blocking volume. Revisit it then.</li>
<li><b>2. Close the registry gap before the review.</b> Ask every brand selling new light vehicles in Mexico, starting with BYD and Chirey, to report to the RAIAVL, for example as a condition for using import programs. A tariff review based on data that misses its main target is weak at the table.</li>
<li><b>3. Talk to the global brands, not only the Chinese ones.</b> GM, Kia, Ford and Stellantis sell a large share of the China-made cars. They also build in Mexico and can move models here, which is what the tariff is for.</li>
<li><b>4. Put the US wall first.</b> Exports to the US lost far more units this year than Mexico's tariff could ever protect. Brand-level tracking (Mazda, Nissan, Ford down; Stellantis, Kia up) should guide where to spend negotiating effort. Canada and Latin America are worth supporting, but they cannot replace the US.</li>
<li><b>5. Decide what the tariff means for electric cars.</b> Plug-in hybrids tripled, largely with Chinese models. A lower rate for electric models from no-deal countries, tied to a plan to assemble them in Mexico, would keep the tariff's purpose without stalling electrification.</li>
</ul>""")
    with st.expander("Method and sources"):
        st.markdown(f"""
- **Data:** INEGI RAIAVL open data (sales, production, exports; 2005 to October 2026) and the PxWeb table *Venta de vehículos híbridos y eléctricos por entidad federativa* (2016 onwards). Downloaded by `pipeline/download.py`, cleaned by `pipeline/clean.py`.
- **Seasonality:** long-run charts use 12-month rolling totals. Year-to-date numbers compare the same months of the previous year. Month-by-month charts compare each month with the same month a year before.
- **Origin groups (my classification, not an official list):** *Other no-deal countries* = India, South Korea, Thailand, Indonesia, Taiwan, Turkey, South Africa, Russia, which have no trade agreement with Mexico and fall under the 2026 tariff increase. Brazil and Argentina are counted as trade-deal partners because light vehicles trade under the ACE 55 automotive agreement.
- **Per-capita map:** INEGI Censo de Población y Vivienda 2020. State outlines: public GeoJSON (amCharts geodata, via github.com/angelnmara/geojson).
- **Outside sources for context (not in the registry):** Chinese car imports −31.1% in H1 2026 (Secretaría de Economía via El Economista / La República, 31 Aug 2026); US Section 232 auto tariff (April 2025); Nissan CIVAC and COMPAS closures (press, 2025-2026); INEGI RAIAVL bulletins for brands entering and leaving.
""")
