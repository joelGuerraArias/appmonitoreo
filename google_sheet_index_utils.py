# -*- coding: utf-8 -*-
"""Utilidades para filas en Google Sheets (índice en columna A) sin depender de Streamlit."""
from __future__ import annotations


def titulo_hoja_desde_range_a1(range_a1: str) -> str:
    """
    Obtiene el nombre de la pestaña desde 'Hoja 1!A:G' o 'Sheet1!A:F'.
    Sin '!' asume primera hoja con nombre típico (compat).
    """
    s = (range_a1 or "").strip()
    if not s:
        return "Sheet1"
    if "!" not in s:
        return "Sheet1"
    t = s.split("!", 1)[0].strip()
    if t.startswith("'") and t.endswith("'") and len(t) >= 2:
        return t[1:-1].replace("''", "'")
    return t


def parse_indice_columna_a(val) -> int | None:
    """Si la celda es un índice entero (>0), devuelve su valor; fechas (/), texto etc. → None."""
    if val is None:
        return None
    raw = str(val).strip()
    if not raw or "/" in raw:
        return None
    raw_lower = raw.lower()
    if raw_lower in ("#", "indice", "índice", "id", ""):
        return None
    try:
        x = float(raw.replace(",", "."))
        if x <= 0 or x != int(x):
            return None
        return int(x)
    except ValueError:
        pass
    if raw.isdigit():
        return int(raw)
    return None


def siguiente_indice_columna_a(service_sheets_v4, spreadsheet_id: str, sheet_title: str) -> int:
    """
    Lee la columna A de la pestaña y devuelve max(índices numéricos) + 1.
    Ignora cabeceras, fechas mal colocadas en A, texto, etc.
    """
    qs = "'" + sheet_title.replace("'", "''") + "'"
    rng = qs + "!A:A"
    res = (
        service_sheets_v4.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=rng)
        .execute()
    )
    rows = res.get("values") or []
    m = 0
    for r in rows:
        if not r:
            continue
        n = parse_indice_columna_a(r[0])
        if n is not None:
            m = max(m, n)
    return max(1, m + 1)
