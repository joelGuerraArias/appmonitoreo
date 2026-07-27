"""Prueba directa: registrar una coincidencia en informe_general.md (sin Streamlit)."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

INFORME = Path(os.path.expanduser("~")) / "Desktop" / "informes" / "informe_general.md"
MARCA = f"TEST-REGISTRO-{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def append_prueba():
    INFORME.parent.mkdir(parents=True, exist_ok=True)
    existe = INFORME.is_file() and INFORME.stat().st_size > 0
    hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bloque = f"""
---

# 🧪 PRUEBA REGISTRO COINCIDENCIA — {MARCA}

- **Archivo:** `Teleuniverso_480p_TEST_seg999.mp4`
- **Término:** intrant
- **Motivo:** script `_test_registro_informe_coincidencia.py`
- **Hora:** {hora}

Texto de prueba para verificar escritura en informe general.
"""
    with INFORME.open("a", encoding="utf-8") as f:
        if not existe:
            f.write("# Informe General — Video Analyzer\n\n")
        f.write("\n---\n\n")
        f.write(f"## Coincidencia PRUEBA - intrant - {MARCA}\n\n")
        f.write(f"> Registrado: {hora}\n\n")
        f.write(bloque.strip())
        f.write("\n")
    return str(INFORME.resolve())


if __name__ == "__main__":
    path = append_prueba()
    tail = INFORME.read_text(encoding="utf-8")[-800:]
    ok = MARCA in tail
    print(f"INFORME: {path}")
    print(f"MARCA_EN_COLA: {ok}")
    print("--- ULTIMAS LINEAS ---")
    print(tail)
    sys.exit(0 if ok else 1)
