# -*- coding: utf-8 -*-
"""Consulta duplicados prm/Presidencia en alertas_medios."""
import os
from collections import Counter
from dotenv import load_dotenv

load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_ANON_KEY", "")
if not url or not key:
    print("NO_SUPABASE_ENV")
    raise SystemExit(1)

sb = create_client(url, key)
r = (
    sb.table("alertas_medios")
    .select("id,termino_detectado,nombre_archivo,nombre_medio,fecha_detencion,url_video")
    .eq("termino_detectado", "prm")
    .order("id", desc=True)
    .limit(20)
    .execute()
)
rows = r.data or []
print(f"Registros prm (ultimos 20): {len(rows)}")
for x in rows:
    print(
        f"  id={x.get('id')} | {x.get('fecha_detencion')} | "
        f"medio={x.get('nombre_medio')} | archivo={x.get('nombre_archivo', '')[:55]}"
    )

keys = [(x.get("termino_detectado"), x.get("nombre_archivo")) for x in rows]
for k, n in Counter(keys).most_common():
    if n > 1:
        print(f"DUPLICADO: {k} -> {n} veces")

pres = [x for x in rows if (x.get("nombre_medio") or "").lower() == "presidencia"]
print(f"Con nombre_medio=Presidencia: {len(pres)}")
