#!/usr/bin/env python3
"""
🎯 EDESUR TV - Launcher Simplificado
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🎯 EDESUR TV - Launcher")
    print("=" * 40)

    # Determinar directorio base
    base_dir = Path(__file__).parent.parent

    print("📁 Directorio de trabajo:", base_dir)
    print("\n🔧 OPCIONES DISPONIBLES:")
    print("1. 🎬 Detectar streams")
    print("2. 📝 Actualizar desde MD")
    print("3. 🚀 Desplegar")
    print("4. 👀 Modo vigilancia")
    print("5. 📊 Estado del sistema")

    choice = input("\nSelecciona (1-5): ").strip()

    if choice == "1":
        print("\n🎬 Ejecutando detección de streams...")
        subprocess.run([sys.executable, "stream_detector_extension.py"], cwd=base_dir)

    elif choice == "2":
        print("\n📝 Actualizando desde coincidencias.md...")
        subprocess.run([sys.executable, "edesur_tv/update_system.py"], cwd=base_dir)

    elif choice == "3":
        print("\n🚀 Desplegando a Cloudflare...")
        subprocess.run([sys.executable, "edesur_tv/auto_deploy_fixed.py", "full"], cwd=base_dir)

    elif choice == "4":
        print("\n👀 Iniciando modo vigilancia...")
        subprocess.run([sys.executable, "edesur_tv/auto_deploy_fixed.py", "watch"], cwd=base_dir)

    elif choice == "5":
        print("\n📊 Verificando estado del sistema...")
        files = [
            "coincidencias.md",
            "edesur_tv/index.html",
            "edesur_tv/styles.css",
            "edesur_tv/script.js"
        ]

        for file in files:
            path = base_dir / file
            status = "✅" if path.exists() else "❌"
            print(f"{status} {file}")

    else:
        print("❌ Opción no válida")

    print("\n✅ ¡Proceso completado!")

if __name__ == "__main__":
    main()
