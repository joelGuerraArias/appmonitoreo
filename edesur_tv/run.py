#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 EDESUR TV - Launcher Principal
Script principal para ejecutar todo el sistema
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    """Imprimir header del sistema"""
    print("🎯 EDESUR TV - Sistema de Alerta de Medios")
    print("=" * 60)
    print("🚀 Sistema completo de detección y despliegue")
    print("📅 Fecha:", __import__('datetime').datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("=" * 60)

def show_menu():
    """Mostrar menú principal"""
    print("\n📋 MENÚ PRINCIPAL:")
    print("=" * 30)
    print("1. 🎬 Detectar streams HLS")
    print("2. 📝 Actualizar desde Markdown")
    print("3. 🚀 Desplegar a Cloudflare")
    print("4. 👀 Modo vigilancia 24/7")
    print("5. 🔧 Configuración inicial")
    print("6. 📊 Ver estado del sistema")
    print("7. 🌐 Abrir aplicación web")
    print("8. 📖 Documentación completa")
    print("0. ❌ Salir")
    print("=" * 30)

def run_stream_detection():
    """Ejecutar detección de streams"""
    print("\n🎬 Iniciando detección de streams...")
    try:
        result = subprocess.run([
            sys.executable, "stream_detector_extension.py"
        ], cwd=Path(__file__).parent.parent)

        if result.returncode == 0:
            print("✅ Detección completada")
        else:
            print("❌ Error en detección")
    except Exception as e:
        print(f"❌ Error: {e}")

def run_markdown_update():
    """Actualizar desde Markdown"""
    print("\n📝 Actualizando desde coincidencias.md...")
    try:
        result = subprocess.run([
            sys.executable, "update_system.py"
        ], cwd=Path(__file__).parent)

        if result.returncode == 0:
            print("✅ Actualización completada")
        else:
            print("❌ Error en actualización")
    except Exception as e:
        print(f"❌ Error: {e}")

def run_cloudflare_deploy():
    """Desplegar a Cloudflare"""
    print("\n🚀 Desplegando a Cloudflare Pages...")
    try:
        result = subprocess.run([
            sys.executable, "auto_deploy_fixed.py", "deploy"
        ], cwd=Path(__file__).parent)

        if result.returncode == 0:
            print("✅ Despliegue completado")
        else:
            print("❌ Error en despliegue")
    except Exception as e:
        print(f"❌ Error: {e}")

def run_watch_mode():
    """Modo vigilancia 24/7"""
    print("\n👀 Iniciando modo vigilancia...")
    print("🛑 Presiona Ctrl+C para detener")
    try:
        subprocess.run([
            sys.executable, "auto_deploy_fixed.py", "watch"
        ], cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\n🛑 Vigilancia detenida por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")

def run_initial_setup():
    """Configuración inicial"""
    print("\n🔧 Configuración inicial del sistema...")

    try:
        # Configurar Cloudflare
        print("📝 Configurando Cloudflare Pages...")
        result1 = subprocess.run([
            sys.executable, "cloudflare_deploy.py", "config"
        ], cwd=Path(__file__).parent)

        # Setup inicial
        print("⚙️ Configuración del sistema...")
        result2 = subprocess.run([
            sys.executable, "auto_deploy_fixed.py", "setup"
        ], cwd=Path(__file__).parent)

        if result1.returncode == 0 and result2.returncode == 0:
            print("✅ Configuración completada")
        else:
            print("❌ Error en configuración")

    except Exception as e:
        print(f"❌ Error: {e}")

def show_system_status():
    """Mostrar estado del sistema"""
    print("\n📊 ESTADO DEL SISTEMA:")
    print("=" * 40)

    base_dir = Path(__file__).parent.parent
    files_to_check = {
        "coincidencias.md": "Archivo de coincidencias",
        "edesur_tv/index.html": "Página principal",
        "edesur_tv/styles.css": "Estilos CSS",
        "edesur_tv/script.js": "JavaScript",
        "edesur_tv/update_system.py": "Sistema de actualización",
        "edesur_tv/auto_deploy_fixed.py": "Auto despliegue"
    }

    for file_path, description in files_to_check.items():
        full_path = base_dir / file_path
        status = "✅" if full_path.exists() else "❌"
        print(f"{status} {description}: {file_path}")

    # Verificar dependencias
    print("\n🔧 DEPENDENCIAS:")
    dependencies = ["python", "node", "npm", "git"]
    for dep in dependencies:
        try:
            result = subprocess.run([dep, "--version"],
                                  capture_output=True, text=True)
            status = "✅" if result.returncode == 0 else "❌"
            version = result.stdout.strip().split('\n')[0] if result.returncode == 0 else "No instalado"
            print(f"{status} {dep}: {version}")
        except:
            print(f"❌ {dep}: No instalado")

def open_web_app():
    """Abrir aplicación web"""
    print("\n🌐 Abriendo aplicación web...")

    html_file = Path(__file__).parent / "index.html"

    if html_file.exists():
        try:
            import webbrowser
            webbrowser.open(f"file://{html_file.absolute()}")
            print("✅ Aplicación abierta en navegador")
        except Exception as e:
            print(f"❌ Error al abrir navegador: {e}")
    else:
        print("❌ No se encontró index.html")

def show_documentation():
    """Mostrar documentación"""
    print("\n📖 DOCUMENTACIÓN COMPLETA:")
    print("=" * 50)

    readme_file = Path(__file__).parent / "README_COMPLETO.md"

    if readme_file.exists():
        try:
            with open(readme_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Mostrar secciones principales
            lines = content.split('\n')
            in_section = False
            for line in lines[:50]:  # Primeras 50 líneas
                if line.startswith('#') or line.startswith('##'):
                    print(f"\n{line}")
                    in_section = True
                elif in_section and line.strip():
                    if len(line) < 100:  # Líneas cortas
                        print(line)
                    else:
                        print(line[:100] + "...")
                    in_section = False
                elif not line.strip():
                    in_section = False

            print("
📄 Documentación completa en: README_COMPLETO.md"
        except Exception as e:
            print(f"❌ Error al leer documentación: {e}")
    else:
        print("❌ No se encontró README_COMPLETO.md")

def main():
    """Función principal"""
    print_header()

    while True:
        show_menu()

        try:
            choice = input("\n🔹 Selecciona una opción (0-8): ").strip()

            if choice == "1":
                run_stream_detection()
            elif choice == "2":
                run_markdown_update()
            elif choice == "3":
                run_cloudflare_deploy()
            elif choice == "4":
                run_watch_mode()
            elif choice == "5":
                run_initial_setup()
            elif choice == "6":
                show_system_status()
            elif choice == "7":
                open_web_app()
            elif choice == "8":
                show_documentation()
            elif choice == "0":
                print("\n👋 ¡Hasta luego!")
                break
            else:
                print("\n❌ Opción no válida. Intenta de nuevo.")

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")

        input("\n🔄 Presiona Enter para continuar...")

if __name__ == "__main__":
    main()
