"""Two Tariff Walls: Mexico's light-vehicle industry, a briefing dashboard built on INEGI's RAIAVL.

Run:  streamlit run app.py
"""
import pandas as pd
import streamlit as st

import core
from views import briefing, electric, exports, imports, registry

st.set_page_config(page_title="Two Tariff Walls", page_icon=":material/directions_car:", layout="wide")
st.html(f"<style>{(core.HERE / 'assets' / 'style.css').read_text()}</style>")

assert core.table("sales").date.max() == core.LAST, "new data: update core.LAST"

pages = [
    st.Page(briefing.page, title="Briefing", icon=":material/description:", url_path="briefing", default=True),
    st.Page(imports.page, title="Mexico's wall", icon=":material/south_east:", url_path="imports"),
    st.Page(exports.page, title="The US wall", icon=":material/north_east:", url_path="exports"),
    st.Page(electric.page, title="Electrification", icon=":material/bolt:", url_path="electric"),
    st.Page(registry.page, title="What the registry can't see", icon=":material/visibility_off:", url_path="registry"),
]
pg = st.navigation(pages, position="top")

months = list(pd.date_range("2005-01-01", core.LAST, freq="MS"))
with st.sidebar:
    st.html('<p class="sb-h">Time window</p>')
    st.select_slider("Months shown", options=months, value=(pd.Timestamp("2016-01-01"), core.LAST),
                     format_func=lambda d: d.strftime("%b %Y"), key="window", label_visibility="collapsed")
    st.toggle("Show events on charts", value=True, key="show_events")
    st.html('<p class="sb-note">Ten years by default, so 2026 sits next to the 2020 pandemic and the 2021-22 chip shortage. '
            'Totals are 12-month rolling or Jan–Oct against the same months a year before, so seasons never fake a trend.</p>')

pg.run()

v = core.vintage()
st.html(f"""<div class="foot">
<p><b>Data:</b> INEGI, Registro Administrativo de la Industria Automotriz de Vehículos Ligeros (RAIAVL), published {v['sales']['published']},
covering January 2005 to October 2026. Sales are revised figures; production and exports for October 2026 are preliminary.
Downloaded {v['downloaded']} by <code>pipeline/download.py</code>, cleaned by <code>pipeline/clean.py</code>.</p>
<p>Prepared by Fernando Iñaki Corella Fernández for a class assignment, in the role of an analyst at the Secretaría de Economía.
Not an official government document.</p></div>""")
