# Two Tariff Walls

A Streamlit dashboard on Mexico's light-vehicle industry, built on INEGI's
*Registro Administrativo de la Industria Automotriz de Vehículos Ligeros* (RAIAVL).

**Role:** analyst at the Secretaría de Economía. **Audience:** the Subsecretaría de Industria y Comercio.
**Decision:** keep, adjust or extend the 50% tariff on light vehicles from countries without a trade
agreement (in force since 1 January 2026), how to defend exports facing the US tariff, and whether to
require every brand to report to the registry.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The cleaned data is already in `data/processed/`, so the app runs without downloading anything.

## Rebuild the data from INEGI

```bash
python pipeline/download.py   # 4 tables -> data/raw/ (about 65 MB, not committed)
python pipeline/clean.py      # tidy parquet files -> data/processed/, with self-checks
```

| Table | Source | Used for |
|---|---|---|
| Ventas al público | open-data zip, 2005 to today | country where each sold car was built |
| Producción | open-data zip | output by brand |
| Exportación | open-data zip | exports by destination country |
| Híbridos y eléctricos | PxWeb API (`RAIAVL_11.px`), 2016 to today | HEV, PHEV, BEV sales by state |

`clean.py` builds monthly dates, harmonizes brand names across tables and years (Stellantis,
BMW Group, Jetour...), translates labels, groups countries into origin blocks and destination
regions, keeps INEGI's figure status (definitive, revised, preliminary) and drops the months INEGI
has not published yet. It asserts the January to October 2026 sales total against INEGI's bulletin.

## Pages

1. **Briefing**: role, stakeholders, decision, five numbers, guiding questions, tables used.
2. **Mexico's wall**: China-made share of sales, after-tariff months, who sells China-made cars, segments, origins.
3. **The US wall**: exports by destination, month-by-month change, brands losing the US, where output goes, production.
4. **Electrification**: HEV/PHEV/BEV by month and state, share of the market, plug-in models by build country.
5. **What the registry can't see**: who reports and when, figure status, name harmonization, limits, recommendations.

## Files

```
app.py              navigation, time window, footer
core.py             data loading, colors, events, chart style, helpers
views/              one module per page
pipeline/           download.py, clean.py
notebooks/          china_made_share.ipynb: the main finding as one static chart (matplotlib), then 8 pieces, one observation each (story/)
notebooks/fonts/    Inter, the dashboard's font, for the charts (SIL Open Font License, OFL.txt)
notebooks/logos/    brand logos for the main chart, one gray, sources in SOURCES.md
data/processed/     cleaned tables the app reads
data/geo/           Mexican state outlines (amCharts geodata via github.com/angelnmara/geojson)
assets/style.css    page styling
```

Outside sources used only for context are named on screen: Secretaría de Economía figures on Chinese
car imports (via El Economista / La República, 31 Aug 2026), the US Section 232 auto tariff (April 2025),
press reports on Nissan's CIVAC and COMPAS closures, and the 2020 census for per-capita rates.

Class assignment, not an official government document.
