#!/usr/bin/env python3
"""
Script de instalación automática para renamer.py
================================================

Este script verifica e instala automáticamente todas las dependencias
necesarias para ejecutar el Renombrador de Videos por Programación.
"""

import subprocess
import sys
import os
from pathlib import Path

def print_header():
    """Muestra el encabezado del instalador"""
    print("=" * 60)
    print("🎬 INSTALADOR - Renombrador de Videos por Programación")
    print("=" * 60)
    print()

def check_python_version():
    """Verifica la versión de Python"""
    print("🐍 Verificando versión de Python...")
    
    if sys.version_info < (3, 7):
        print("❌ Error: Se requiere Python 3.7 o superior")
        print(f"   Versión actual: {sys.version}")
        print("   Descarga Python desde: https://python.org")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detectado")
    return True

def check_pip():
    """Verifica si pip está disponible"""
    print("\n📦 Verificando pip...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
        print("✅ pip está disponible")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error: pip no está disponible")
        print("   Instala pip desde: https://pip.pypa.io/en/stable/installation/")
        return False

def install_package(package_name):
    """Instala un paquete usando pip"""
    print(f"\n📥 Instalando {package_name}...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            package_name, "--upgrade"
        ], check=True, capture_output=True, text=True)
        
        print(f"✅ {package_name} instalado correctamente")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando {package_name}")
        print(f"   Error: {e}")
        return False

def check_customtkinter():
    """Verifica si CustomTkinter está instalado y funciona"""
    print("\n🎨 Verificando CustomTkinter...")
    
    try:
        import customtkinter as ctk
        print(f"✅ CustomTkinter {ctk.__version__} está disponible")
        return True
    except ImportError:
        print("⚠️ CustomTkinter no está instalado")
        return False
    except Exception as e:
        print(f"⚠️ Error con CustomTkinter: {e}")
        return False

def verify_renamer_files():
    """Verifica que los archivos necesarios estén presentes"""
    print("\n📁 Verificando archivos del proyecto...")
    
    current_dir = Path(__file__).parent
    required_files = [
        "renamer.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file in required_files:
        file_path = current_dir / file
        if file_path.exists():
            print(f"✅ {file} encontrado")
        else:
            print(f"❌ {file} no encontrado")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️ Archivos faltantes: {', '.join(missing_files)}")
        return False
    
    return True

def create_desktop_shortcut():
    """Crea un acceso directo en el escritorio (Windows)"""
    if os.name != 'nt':
        return False
        
    print("\n🔗 Creando acceso directo en el escritorio...")
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Renombrador de Videos.lnk")
        target = os.path.join(os.path.dirname(__file__), "renamer.py")
        wDir = os.path.dirname(__file__)
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{target}"'
        shortcut.WorkingDirectory = wDir
        shortcut.IconLocation = sys.executable
        shortcut.save()
        
        print("✅ Acceso directo creado en el escritorio")
        return True
        
    except ImportError:
        print("⚠️ No se pudo crear acceso directo (librerías Windows no disponibles)")
        return False
    except Exception as e:
        print(f"⚠️ Error creando acceso directo: {e}")
        return False

def run_test():
    """Ejecuta una prueba básica de la aplicación"""
    print("\n🧪 Ejecutando prueba básica...")
    
    try:
        # Importar sin ejecutar la GUI
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Test de importación
        import customtkinter as ctk
        import tkinter as tk
        from tkinter import filedialog, messagebox
        import json
        import datetime
        import re
        from pathlib import Path
        import threading
        
        print("✅ Todas las importaciones exitosas")
        print("✅ La aplicación debería funcionar correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False

def main():
    """Función principal del instalador"""
    print_header()
    
    # Verificaciones básicas
    if not check_python_version():
        input("\nPresiona Enter para salir...")
        return
    
    if not check_pip():
        input("\nPresiona Enter para salir...")
        return
    
    if not verify_renamer_files():
        input("\nPresiona Enter para salir...")
        return
    
    # Verificar/instalar CustomTkinter
    if not check_customtkinter():
        print("\n🔧 Instalando dependencias...")
        if not install_package("customtkinter>=5.2.0"):
            print("\n❌ Error en la instalación. Intenta instalar manualmente:")
            print("   pip install customtkinter")
            input("\nPresiona Enter para salir...")
            return
    
    # Verificar instalación
    if not check_customtkinter():
        print("\n❌ Error: CustomTkinter no se instaló correctamente")
        input("\nPresiona Enter para salir...")
        return
    
    # Prueba final
    if not run_test():
        print("\n❌ Error: La aplicación no pasó las pruebas básicas")
        input("\nPresiona Enter para salir...")
        return
    
    # Crear acceso directo (opcional)
    create_desktop_shortcut()
    
    # Finalización exitosa
    print("\n" + "=" * 60)
    print("🎉 INSTALACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print()
    print("✅ Todas las dependencias están instaladas")
    print("✅ El Renombrador de Videos está listo para usar")
    print()
    print("🚀 Para ejecutar la aplicación:")
    print(f"   python {os.path.join(os.path.dirname(__file__), 'renamer.py')}")
    print()
    print("📺 Medios soportados: CDN37, TELECENTRO, TELEMICRO, COLOR VISION")
    print()
    
    # Preguntar si ejecutar ahora
    respuesta = input("¿Deseas ejecutar la aplicación ahora? (s/n): ").lower().strip()
    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n🎬 Iniciando Renombrador de Videos...")
        try:
            import renamer
            renamer.main()
        except Exception as e:
            print(f"❌ Error ejecutando la aplicación: {e}")
            input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Instalación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        input("\nPresiona Enter para salir...")
