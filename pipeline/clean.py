"""Step 2: clean the raw INEGI tables into tidy files the dashboard reads.

Run:  python pipeline/clean.py      (after pipeline/download.py)
Everything is done in code, nothing by hand in Excel:
  - one real monthly date per row
  - brand names harmonized across tables and years (BRANDS below)
  - Spanish labels translated, countries grouped into blocks / regions
  - INEGI's figure status kept (definitive, revised, preliminary)
  - hybrid/electric months that INEGI has not published yet are dropped
"""
import glob
import json
import pathlib
import shutil

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"

# raw MARCA -> (brand, group, home country of the brand)
BRANDS = {
    "Acura": ("Acura", "Honda", "Japan"),
    "Alfa Romeo": ("Alfa Romeo", "Stellantis", "Italy"),
    "Audi": ("Audi", "Volkswagen Group", "Germany"),
    "Auteco": ("Auteco", "Auteco", "Colombia"),
    "BMW": ("BMW", "BMW Group", "Germany"),
    "BMW Group": ("BMW", "BMW Group", "Germany"),
    "Bentley": ("Bentley", "Volkswagen Group", "United Kingdom"),
    "Changan": ("Changan", "Changan", "China"),
    "Chirey": ("Chirey", "Chery", "China"),
    "Omoda": ("Omoda", "Chery", "China"),
    "JETOUR": ("Jetour", "Chery", "China"),
    "Jetour Soueast": ("Jetour", "Chery", "China"),
    "Chrysler": ("Chrysler/Jeep/Dodge/RAM", "Stellantis", "United States"),
    "Fiat": ("Fiat", "Stellantis", "Italy"),
    "Peugeot": ("Peugeot", "Stellantis", "France"),
    "Ford Motor": ("Ford", "Ford", "United States"),
    "Lincoln": ("Lincoln", "Ford", "United States"),
    "Foton": ("Foton", "Foton", "China"),
    "GAC": ("GAC", "GAC", "China"),
    "Geely": ("Geely", "Geely", "China"),
    "Lynk&Co": ("Lynk & Co", "Geely", "China"),
    "Zeekr": ("Zeekr", "Geely", "China"),
    "Volvo": ("Volvo", "Volvo Cars", "Sweden"),
    "General Motors": ("GM", "GM", "United States"),
    "Great Wall Motor": ("Great Wall", "Great Wall", "China"),
    "Honda": ("Honda", "Honda", "Japan"),
    "Hyundai": ("Hyundai", "Hyundai-Kia", "South Korea"),
    "KIA": ("Kia", "Hyundai-Kia", "South Korea"),
    "Infiniti": ("Infiniti", "Nissan", "Japan"),
    "Nissan": ("Nissan", "Nissan", "Japan"),
    "Isuzu": ("Isuzu", "Isuzu", "Japan"),
    "JAC": ("JAC", "JAC", "China"),
    "Jaguar": ("Jaguar", "Jaguar Land Rover", "United Kingdom"),
    "Land Rover": ("Land Rover", "Jaguar Land Rover", "United Kingdom"),
    "Leapmotor": ("Leapmotor", "Leapmotor", "China"),
    "Lexus": ("Lexus", "Toyota", "Japan"),
    "Toyota": ("Toyota", "Toyota", "Japan"),
    "MG Motor": ("MG", "SAIC", "China"),
    "MG ROVER": ("MG Rover", "MG Rover", "United Kingdom"),
    "MOTORNATION": ("Motornation", "Motornation", "China"),  # importer of Changan, BAIC, JMC models
    "Mazda": ("Mazda", "Mazda", "Japan"),
    "Mercedes Benz": ("Mercedes-Benz", "Mercedes-Benz", "Germany"),
    "Mercedes Benz_Prod_Expo": ("Mercedes-Benz", "Mercedes-Benz", "Germany"),
    "Smart": ("Smart", "Mercedes-Benz", "Germany"),
    "Mini": ("MINI", "BMW Group", "Germany"),
    "Mitsubishi": ("Mitsubishi", "Mitsubishi", "Japan"),
    "Porsche": ("Porsche", "Volkswagen Group", "Germany"),
    "Renault": ("Renault", "Renault", "France"),
    "SEAT": ("SEAT", "Volkswagen Group", "Spain"),
    "Subaru": ("Subaru", "Subaru", "Japan"),
    "Suzuki": ("Suzuki", "Suzuki", "Japan"),
    "Volkswagen": ("Volkswagen", "Volkswagen Group", "Germany"),
}
SEGMENTS = {"Compactos": "Compact", "Subcompactos": "Subcompact", "SUV's": "SUV", "De Lujo": "Luxury",
            "Deportivos": "Sports", "Minivans": "Minivan", "Pick Ups": "Pickup", "No Especificado": "Not specified"}
TYPES = {"Automóviles": "Cars", "Camiones ligeros": "Light trucks", "No Especificado": "Not specified"}
STATUS = {"Cifras Definitivas": "Definitive", "Cifras Revisadas": "Revised", "Cifras Preliminares": "Preliminary"}
COUNTRIES = {
    "México": "Mexico", "Estados Unidos": "United States", "Canadá": "Canada", "China": "China",
    "Japón": "Japan", "Corea del Sur": "South Korea", "India": "India", "Tailandia": "Thailand",
    "Indonesia": "Indonesia", "Brasil": "Brazil", "Argentina": "Argentina", "Alemania": "Germany",
    "España": "Spain", "Reino Unido": "United Kingdom", "Francia": "France", "Italia": "Italy",
    "Hungría": "Hungary", "República Checa": "Czech Republic", "Eslovaquia": "Slovakia",
    "Polonia": "Poland", "Bélgica": "Belgium", "Suecia": "Sweden", "Austria": "Austria",
    "Países Bajos": "Netherlands", "Portugal": "Portugal", "Turquía": "Turkey", "Taiwán": "Taiwan",
    "Sudáfrica": "South Africa", "Colombia": "Colombia", "Chile": "Chile", "Perú": "Peru",
    "Ecuador": "Ecuador", "Uruguay": "Uruguay", "Paraguay": "Paraguay", "Bolivia": "Bolivia",
    "Venezuela": "Venezuela", "Guatemala": "Guatemala", "El Salvador": "El Salvador",
    "Honduras": "Honduras", "Nicaragua": "Nicaragua", "Costa Rica": "Costa Rica", "Panamá": "Panama",
    "República Dominicana": "Dominican Republic", "Puerto Rico": "Puerto Rico", "Cuba": "Cuba",
    "Australia": "Australia", "Nueva Zelanda": "New Zealand", "Arabia Saudita": "Saudi Arabia",
    "Emiratos Árabes Unidos": "United Arab Emirates", "Kuwait": "Kuwait", "Qatar": "Qatar",
    "Israel": "Israel", "Suiza": "Switzerland", "Noruega": "Norway", "Finlandia": "Finland",
    "Dinamarca": "Denmark", "Irlanda": "Ireland", "Rumania": "Romania", "Eslovenia": "Slovenia",
    "Vietnam": "Vietnam", "Malasia": "Malaysia", "Filipinas": "Philippines", "Singapur": "Singapore",
    "Federación Rusa": "Russia", "Egipto": "Egypt", "Marruecos": "Morocco", "Jamaica": "Jamaica",
    "Grecia": "Greece", "Croacia": "Croatia", "Bulgaria": "Bulgaria", "Estonia": "Estonia",
    "Letonia": "Latvia", "Lituania": "Lithuania", "Chipre": "Cyprus", "Malta": "Malta",
    "Islandia": "Iceland", "Ucrania": "Ukraine", "Bielorrusia": "Belarus", "Serbia": "Serbia",
    "Serbia y Montenegro": "Serbia", "Montenegro": "Montenegro", "Macedonia": "North Macedonia",
    "Bosnia y Herzegovina": "Bosnia and Herzegovina", "Moldavia": "Moldova", "Albania": "Albania",
    "Gibraltar": "Gibraltar", "Europa": "Europe (not specified)", "Haití": "Haiti", "Belice": "Belize",
    "Trinidad y Tobago": "Trinidad and Tobago", "Barbados": "Barbados", "Bahamas": "Bahamas",
    "Aruba": "Aruba", "Curazao": "Curaçao", "Guyana Francesa": "French Guiana", "Surinam": "Suriname",
    "Martinica": "Martinique", "Santa Lucía": "Saint Lucia", "Antigua y Barbuda": "Antigua and Barbuda",
    "Anguila": "Anguilla", "Islas Caimán": "Cayman Islands", "Islas Turcas y Caicos": "Turks and Caicos",
    "Islas Vírgenes (EU)": "US Virgin Islands", "Islas Vírgenes (Reino Unido)": "British Virgin Islands",
    "Guadalupe y Dependencias": "Guadeloupe",
}
# Countries with no trade agreement with Mexico that sell cars here: their light vehicles
# pay up to 50% from 1 Jan 2026. Brazil and Argentina keep duty-free access under ACE 55.
NO_DEAL = {"China", "India", "South Korea", "Thailand", "Indonesia", "Taiwan", "Turkey",
           "South Africa", "Russia"}
EUROPE = {"Germany", "Spain", "United Kingdom", "France", "Italy", "Hungary", "Czech Republic",
          "Slovakia", "Poland", "Belgium", "Sweden", "Austria", "Netherlands", "Portugal",
          "Switzerland", "Norway", "Finland", "Denmark", "Ireland", "Romania", "Slovenia", "Turkey",
          "Greece", "Croatia", "Bulgaria", "Estonia", "Latvia", "Lithuania", "Cyprus", "Malta", "Iceland",
          "Ukraine", "Belarus", "Serbia", "Montenegro", "North Macedonia", "Bosnia and Herzegovina",
          "Moldova", "Albania", "Gibraltar", "Europe (not specified)"}
LATAM = {"Brazil", "Argentina", "Colombia", "Chile", "Peru", "Ecuador", "Uruguay", "Paraguay",
         "Bolivia", "Venezuela", "Guatemala", "El Salvador", "Honduras", "Nicaragua", "Costa Rica",
         "Panama", "Dominican Republic", "Puerto Rico", "Cuba", "Jamaica", "Haiti", "Belize",
         "Trinidad and Tobago", "Barbados", "Bahamas", "Aruba", "Curaçao", "French Guiana", "Suriname",
         "Martinique", "Saint Lucia", "Antigua and Barbuda", "Anguilla", "Cayman Islands",
         "Turks and Caicos", "US Virgin Islands", "British Virgin Islands", "Guadeloupe"}
MONTHS_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
             "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def read(table):
    files = sorted(glob.glob(str(RAW / table / "conjunto_de_datos" / "*.csv")))
    d = pd.concat([pd.read_csv(f, dtype={"ID_MES": str}) for f in files], ignore_index=True)
    unknown = set(d.MARCA) - set(BRANDS)
    assert not unknown, f"{table}: add these brands to BRANDS: {unknown}"
    out = pd.DataFrame({"date": pd.to_datetime(d.ANIO.astype(str) + "-" + d.ID_MES + "-01")})
    out["brand"] = d.MARCA.map(lambda b: BRANDS[b][0])
    out["group"] = d.MARCA.map(lambda b: BRANDS[b][1])
    out["brand_home"] = d.MARCA.map(lambda b: BRANDS[b][2])
    out["raw_brand"] = d.MARCA
    out["model"] = d.MODELO.astype(str).str.strip()
    out["type"] = d.TIPO.map(TYPES).fillna("Not specified")
    out["segment"] = d.SEGMENTO.map(SEGMENTS).fillna("Not specified")
    out["status"] = d.ESTATUS.map(STATUS)
    out["units"] = d.UNI_VEH.astype(int)
    assert out.status.notna().all() and out.units.sum() == d.UNI_VEH.sum()
    return out, d


def country_names(table, id_col):
    cat = next((RAW / table / "catalogos").glob("tc_pais_*.csv"))
    names = pd.read_csv(cat).set_index(id_col).iloc[:, 0]
    return names.map(lambda n: COUNTRIES.get(n, "Not specified" if n.startswith("No Especificado") else n))


def origin_block(country):
    if country == "Mexico":
        return "Made in Mexico"
    if country == "China":
        return "China"
    if country in NO_DEAL:
        return "Other no-deal countries"
    if country == "Not specified":
        return "Not specified"
    return "Trade-deal partners"


def dest_region(country):
    if country in ("United States", "Canada"):
        return country
    if country in EUROPE:
        return "Europe"
    if country in LATAM:
        return "Latin America"
    if country == "Not specified":
        return "Not specified"
    return "Rest of world"


def sales():
    s, d = read("venta")
    s["origin_country"] = d.ID_PAIS_ORIGEN.map(country_names("venta", "ID_PAIS_ORIGEN")).fillna("Not specified")
    s["origin_block"] = s.origin_country.map(origin_block)
    # ORIGEN (NACIONAL/IMPORTADO) must agree with the country code
    assert ((d.ORIGEN == "NACIONAL") == (s.origin_country == "Mexico")).mean() > 0.999
    return s


def exports():
    e, d = read("exportacion")
    e["dest_country"] = d.ID_PAIS_DESTINO.map(country_names("exportacion", "ID_PAIS_DESTINO")).fillna("Not specified")
    e["dest_region"] = e.dest_country.map(dest_region)
    return e


def electrified(last_month):
    h = pd.read_csv(RAW / "electrified" / "hybrids_electrics_by_state.csv", encoding="utf-8-sig")
    h.columns = ["year", "month", "state", "BEV", "PHEV", "HEV"]
    h["date"] = pd.to_datetime(h.year.astype(str) + "-" + h.month.map(lambda m: MONTHS_ES.index(m) + 1).astype(str) + "-01")
    h = h.melt(["date", "state"], ["BEV", "PHEV", "HEV"], var_name="tech", value_name="units")
    h["units"] = pd.to_numeric(h.units, errors="coerce").fillna(0).astype(int)  # INEGI writes "-" for none
    h["state"] = h.state.replace({"México": "Estado de México", "Coahuila de Zaragoza": "Coahuila",
                                  "Michoacán de Ocampo": "Michoacán", "Veracruz de Ignacio de la Llave": "Veracruz",
                                  "No especificado": "Not specified"})
    return h[h.date <= last_month]  # INEGI fills months not yet published with zeros


def coverage(s):
    """When did each raw brand first and last report a sale? (the registry panel)"""
    live = s[s.units > 0]
    c = live.groupby("raw_brand").agg(brand=("brand", "first"), group=("group", "first"),
                                      brand_home=("brand_home", "first"),
                                      first=("date", "min"), last=("date", "max"), units=("units", "sum"))
    return c.reset_index().sort_values("first")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    s, p, e = sales(), read("produccion")[0], exports()
    last = s.date.max()
    h = electrified(last)
    for name, df in [("sales", s), ("production", p), ("exports", e), ("electrified", h), ("coverage", coverage(s))]:
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"{name:12s} {len(df):7d} rows")
    shutil.copy(RAW / "vintage.json", OUT / "vintage.json")

    # self-checks against numbers we know from INEGI's October 2026 bulletin
    ytd = lambda df, y: df[(df.date.dt.year == y) & (df.date.dt.month <= 10)].units.sum()
    assert ytd(s, 2026) == 1_287_225, ytd(s, 2026)
    assert s.date.min() == pd.Timestamp("2005-01-01") and last == pd.Timestamp("2026-10-01")
    assert set(p[p.status == "Preliminary"].date) == {last} == set(e[e.status == "Preliminary"].date)
    print("Jan-Oct 2026 vs 2025:",
          {n: f"{ytd(df, 2026):,} ({ytd(df, 2026) / ytd(df, 2025) - 1:+.1%})" for n, df in [("sales", s), ("production", p), ("exports", e)]})
    print(json.dumps(s[s.date.dt.year == 2026].groupby("origin_block").units.sum().to_dict()))
