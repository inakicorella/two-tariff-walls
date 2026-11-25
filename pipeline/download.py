"""Step 1: download the four RAIAVL tables from INEGI into data/raw/.

Run:  python pipeline/download.py
Sales, production and exports come from INEGI's open-data zips (2005 to today).
Hybrid and electric sales by state are only published as a PxWeb table, so we
ask its API for every cell and save the answer as CSV.
"""
import datetime
import json
import pathlib
import zipfile

import requests

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
OPEN_DATA = ("https://www.inegi.org.mx/contenidos/investigacion/datosprimarios/raiavl/"
             "datosabiertos/conjunto_de_datos_raiavl_mensual_{}_csv.zip")
TABLES = {"venta": "sales", "produccion": "production", "exportacion": "exports"}
PXWEB = "https://www.inegi.org.mx/app/tabulados/pxwebv2/api/v1/es/RAIAVL/RAIAVL_11.px"


def get_zip(name):
    print("downloading", name)
    r = requests.get(OPEN_DATA.format(name), timeout=300)
    r.raise_for_status()
    if not r.content.startswith(b"PK"):
        raise RuntimeError(f"{name}: INEGI did not send a zip file")
    path = RAW / f"{name}.zip"
    path.write_bytes(r.content)
    with zipfile.ZipFile(path) as z:
        z.extractall(RAW / name)


def get_electrified():
    print("downloading hybrids and electrics (PxWeb)")
    meta = requests.get(PXWEB, timeout=60).json()
    query = [{"code": v["code"], "selection": {"filter": "all", "values": ["*"]}}
             for v in meta["variables"]]
    r = requests.post(PXWEB, json={"query": query, "response": {"format": "csv"}}, timeout=300)
    r.raise_for_status()
    (RAW / "electrified").mkdir(exist_ok=True)
    (RAW / "electrified" / "hybrids_electrics_by_state.csv").write_bytes(r.content)


def vintage():
    """INEGI's metadata says when each table was published and up to which month."""
    out = {"downloaded": datetime.date.today().isoformat()}
    for name, label in TABLES.items():
        meta = next((RAW / name / "metadatos").glob("*.txt")).read_text(encoding="utf-8", errors="ignore")
        info = dict(line.split(": ", 1) for line in meta.splitlines() if ": " in line)
        out[label] = {"title": info.get("title", ""), "published": info.get("modified", ""),
                      "covers": info.get("temporal", "")}
    (RAW / "vintage.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        get_zip(name)
    get_electrified()
    vintage()
