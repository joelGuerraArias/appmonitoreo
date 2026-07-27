#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Auto Deploy System - Edesur TV
Sistema completo de actualización y despliegue automático
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

class CoincidenciasUpdater:
    """Sistema para mantener la página actualizada con el archivo MD"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.md_file = self.base_dir / "coincidencias.md"
        self.html_file = self.base_dir / "edesur_tv" / "index.html"
        self.json_file = self.base_dir / "edesur_tv" / "coincidencias_data.json"

    def update_html(self):
        """Actualizar el archivo HTML con los datos del MD"""
        print("🔄 Actualizando desde coincidencias.md...")

        try:
            # Leer archivo MD
            with open(self.md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Leer template HTML
            with open(self.html_file, 'r', encoding='utf-8') as f:
                template = f.read()

            # Actualizar contenido
            updated_html = template.replace(
                'coincidencias.md',
                'coincidencias_data.json'
            )

            # Guardar HTML actualizado
            with open(self.html_file, 'w', encoding='utf-8') as f:
                f.write(updated_html)

            print("✅ HTML actualizado correctamente")
            return True

        except Exception as e:
            print(f"❌ Error en actualización: {e}")
            return False

class CloudflareDeployer:
    """Sistema de despliegue a Cloudflare Pages"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent / "edesur_tv"

    def deploy_to_pages(self):
        """Desplegar a Cloudflare Pages"""
        print("🚀 Desplegando a Cloudflare Pages...")

        try:
            # Verificar que existe el directorio
            if not self.base_dir.exists():
                print(f"❌ Error: No existe el directorio {self.base_dir}")
                return False

            # Usar Wrangler CLI para desplegar
            cmd = [
                "npx", "wrangler", "pages", "deploy",
                str(self.base_dir),
                "--project-name", "edesur-tv"
            ]

            print(f"📥 Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ ¡Despliegue exitoso!")
                return True
            else:
                print(f"❌ Error en despliegue: {result.stderr}")
                return False

        except FileNotFoundError:
            print("❌ Error: Wrangler CLI no está instalado")
            print("💡 Instala con: npm install -g wrangler")
            return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False

class AutoDeploySystem:
    """Sistema completo de auto-despliegue"""

    def __init__(self):
        self.updater = CoincidenciasUpdater()
        self.deployer = CloudflareDeployer()

    def full_auto_deploy(self):
        """Proceso completo de auto-despliegue"""
        print("🎯 Iniciando auto-despliegue completo...")
        print("=" * 60)

        # 1. Actualizar desde MD
        if not self.updater.update_html():
            return False

        # 2. Desplegar a Cloudflare Pages
        if not self.deployer.deploy_to_pages():
            return False

        return True

    def watch_and_deploy(self):
        """Modo vigilancia"""
        print("👀 Iniciando modo vigilancia...")
        print("📝 Monitoreando cambios en coincidencias.md")
        print("🛑 Presiona Ctrl+C para detener")
        print("=" * 60)

        last_md_time = 0

        try:
            while True:
                try:
                    # Verificar cambios en MD
                    current_md_time = os.path.getmtime(self.updater.md_file)

                    if current_md_time > last_md_time:
                        print("\n📝 ¡Cambio detectado en coincidencias.md!")
                        print("🔄 Actualizando sistema...")

                        if self.updater.update_html():
                            print("✅ HTML actualizado")

                            if self.deployer.deploy_to_pages():
                                print("🚀 Despliegue automático completado")
                            else:
                                print("❌ Error en despliegue automático")

                        last_md_time = current_md_time

                    time.sleep(3)

                except FileNotFoundError:
                    print("⚠️ Archivo coincidencias.md no encontrado")
                    time.sleep(5)
                except KeyboardInterrupt:
                    print("\n🛑 Vigilancia detenida por el usuario")
                    break
                except Exception as e:
                    print(f"❌ Error en vigilancia: {e}")
                    time.sleep(5)

        except Exception as e:
            print(f"❌ Error fatal: {e}")

def main():
    """Función principal"""
    print("🎯 Auto Deploy System - Edesur TV")
    print("Sistema completo de actualización y despliegue")
    print("=" * 60)

    system = AutoDeploySystem()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "full":
            if system.full_auto_deploy():
                print("\n🎉 ¡Auto-despliegue completado!")
            else:
                print("\n❌ Error en auto-despliegue")

        elif command == "watch":
            system.watch_and_deploy()

        elif command == "update":
            if system.updater.update_html():
                print("✅ Actualización completada")
            else:
                print("❌ Error en actualización")

        elif command == "deploy":
            if system.deployer.deploy_to_pages():
                print("✅ Despliegue completado")
            else:
                print("❌ Error en despliegue")

        else:
            print("❌ Comando no reconocido")
            print("💡 Comandos: full, watch, update, deploy")

    else:
        print("🚀 Despliegue rápido...")
        if system.full_auto_deploy():
            print("\n🎉 ¡Proceso completado!")
        else:
            print("\n❌ Error en el proceso")

if __name__ == "__main__":
    main()
