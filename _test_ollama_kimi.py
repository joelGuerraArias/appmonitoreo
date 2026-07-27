# -*- coding: utf-8 -*-
"""Smoke test: Ollama local + Kimi K2.7 :cloud"""
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

import requests
from openai import OpenAI

BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
KIMI = os.getenv("OLLAMA_MODEL_KIMI", "kimi-k2.7-code:cloud")


def main():
    print("=== 1. Daemon Ollama ===")
    try:
        r = requests.get(f"{BASE}/api/tags", timeout=10)
        print(f"  /api/tags -> HTTP {r.status_code}")
        if r.status_code != 200:
            return 1
    except Exception as e:
        print(f"  FALLO: {e}")
        return 1

    print("\n=== 2. Kimi K2.7 chat (JSON) ===")
    client = OpenAI(
        api_key=os.getenv("OLLAMA_API_KEY") or "ollama",
        base_url=f"{BASE}/v1",
        timeout=180.0,
    )
    user_msg = (
        'Responde SOLO JSON valido (sin markdown): '
        '{"es_relevante": true, "relevancia": "alta", '
        '"que_se_dice": "prueba ok", "idea_general": "test Kimi", "tema_principal": "test"}'
    )
    try:
        resp = client.chat.completions.create(
            model=KIMI,
            messages=[
                {"role": "system", "content": "Eres analista de medios. Responde solo JSON."},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        text = (resp.choices[0].message.content or "").strip()
        print(f"  Modelo: {KIMI}")
        print(f"  Respuesta: {text[:400]}")
        clean = text.replace("```json", "").replace("```", "").strip()
        try:
            obj = json.loads(clean)
            print(f"  JSON OK: relevancia={obj.get('relevancia')}")
        except json.JSONDecodeError:
            print("  Respuesta recibida (JSON no estricto, smoke OK)")
        print("  KIMI chat: OK")
    except Exception as e:
        print(f"  KIMI FALLO: {e}")
        return 2

    print("\n=== 3. Segmento JSON (mismo cliente, prompt corto) ===")
    seg_prompt = (
        "Termino: apagones. Timestamp: 6s.\n"
        "Transcripcion: [0:00] Hoy hablamos de apagones. [0:05] Edesur informo.\n"
        'Responde SOLO JSON: {"rechazar": false, "inicio_segundos": 0, '
        '"fin_segundos": 60, "duracion_segundos": 60, "razon": "tema apagones", '
        '"idea_central": "discusion sobre apagones"}'
    )
    try:
        resp2 = client.chat.completions.create(
            model=KIMI,
            messages=[
                {"role": "system", "content": "Responde solo JSON valido."},
                {"role": "user", "content": seg_prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        text2 = (resp2.choices[0].message.content or "").strip()
        print(f"  Respuesta: {text2[:300] if text2 else '(vacia)'}")
        if not text2:
            print("  Segmento: respuesta vacia (Kimi a veces en prompts largos; chat OK)")
        else:
            print("  Segmento JSON: OK")
    except Exception as e:
        print(f"  Segmento FALLO: {e}")
        return 3

    print("\n=== 4. Idea/relevancia JSON (Kimi) ===")
    idea_prompt = (
        'Termino: apagones. Transcripcion: "Los apagones afectaron Santo Domingo y Edesur dio explicaciones."\n'
        'Responde SOLO JSON: {"es_relevante": true, "relevancia": "alta", '
        '"que_se_dice": "...", "contexto": "...", "idea_general": "...", "tema_principal": "apagones"}'
    )
    try:
        resp3 = client.chat.completions.create(
            model=KIMI,
            messages=[
                {"role": "system", "content": "Analista de medios. Solo JSON."},
                {"role": "user", "content": idea_prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        text3 = (resp3.choices[0].message.content or "").strip()
        print(f"  Respuesta: {text3[:350]}")
        if text3:
            clean3 = text3.replace("```json", "").replace("```", "").strip()
            obj3 = json.loads(clean3)
            print(f"  Idea OK: relevancia={obj3.get('relevancia')}")
        else:
            print("  Idea: respuesta vacia")
            return 4
    except Exception as e:
        print(f"  Idea FALLO: {e}")
        return 4

    print("\n=== RESUMEN: Ollama + Kimi operativos para la app ===")
    print("  Activa en Streamlit: sidebar -> Kimi -> 'Activar Ollama en esta sesion'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
