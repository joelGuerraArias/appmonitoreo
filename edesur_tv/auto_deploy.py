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
from update_system import CoincidenciasUpdater
from cloudflare_deploy import CloudflareDeployer

class AutoDeploySystem:
    """Sistema completo de auto-despliegue"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.updater = CoincidenciasUpdater()
        self.deployer = CloudflareDeployer()

    def check_requirements(self):
        """Verificar que todos los requisitos estén instalados"""
        requirements = {
            "git": "Git no está instalado",
            "node": "Node.js no está instalado",
            "npm": "npm no está instalado"
        }

        missing = []
        for req, error_msg in requirements.items():
            try:
                subprocess.run([req, "--version"], capture_output=True, check=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                missing.append(f"{req}: {error_msg}")

        if missing:
            print("❌ Requisitos faltantes:")
            for item in missing:
                print(f"   - {item}")
            print("\n💡 Instala los requisitos e intenta de nuevo")
            return False

        return True

    def install_wrangler(self):
        """Instalar Cloudflare Wrangler CLI"""
        try:
            print("📦 Instalando Wrangler CLI...")
            subprocess.run([sys.executable, "-m", "pip", "install", "wrangler-cli"], check=True)
            print("✅ Wrangler CLI instalado")
            return True
        except Exception as e:
            print(f"❌ Error instalando Wrangler: {e}")
            return False

    def full_auto_deploy(self):
        """Proceso completo de auto-despliegue"""
        print("🎯 Iniciando auto-despliegue completo...")
        print("=" * 60)

        # 1. Verificar requisitos
        if not self.check_requirements():
            return False

        # 2. Actualizar desde MD
        print("📝 Paso 1: Actualizando desde coincidencias.md...")
        if not self.updater.update_html():
            print("❌ Error en la actualización")
            return False

        # 3. Configurar Git si es necesario
        print("🔧 Paso 2: Configurando Git...")
        if not self.setup_git():
            print("❌ Error en configuración Git")
            return False

        # 4. Hacer commit de cambios
        print("💾 Paso 3: Guardando cambios...")
        if not self.commit_changes():
            print("❌ Error al guardar cambios")
            return False

        # 5. Desplegar a Cloudflare Pages
        print("🚀 Paso 4: Desplegando a Cloudflare Pages...")
        if not self.deployer.deploy_to_pages():
            print("❌ Error en el despliegue")
            return False

        return True

    def setup_git(self):
        """Configurar Git para el proyecto"""
        try:
            # Inicializar git si no existe
            if not (self.base_dir / ".git").exists():
                subprocess.run(["git", "init"], cwd=self.base_dir, check=True)

            # Configurar usuario
            subprocess.run(["git", "config", "user.name", "Edesur TV Auto Deploy"],
                          cwd=self.base_dir, check=True)
            subprocess.run(["git", "config", "user.email", "autodeploy@edesur.tv"],
                          cwd=self.base_dir, check=True)

            return True
        except Exception as e:
            print(f"❌ Error en setup Git: {e}")
            return False

    def commit_changes(self):
        """Hacer commit de los cambios"""
        try:
            # Agregar archivos
            subprocess.run(["git", "add", "."], cwd=self.base_dir, check=True)

            # Verificar si hay cambios
            result = subprocess.run(["git", "diff", "--cached", "--name-only"],
                                  cwd=self.base_dir, capture_output=True, text=True)

            if not result.stdout.strip():
                print("ℹ️ No hay cambios para commitear")
                return True

            # Hacer commit
            commit_message = f"Auto-deploy: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", commit_message],
                          cwd=self.base_dir, check=True)

            print(f"✅ Commit creado: {commit_message}")
            return True

        except Exception as e:
            print(f"❌ Error en commit: {e}")
            return False

    def watch_and_deploy(self):
        """Modo vigilancia: detectar cambios y desplegar automáticamente"""
        print("👀 Iniciando modo vigilancia...")
        print("📝 Monitoreando cambios en coincidencias.md")
        print("🚀 Despliegue automático activado")
        print("🛑 Presiona Ctrl+C para detener")
        print("=" * 60)

        last_md_time = 0
        last_html_time = 0

        try:
            while True:
                try:
                    # Verificar cambios en MD
                    current_md_time = os.path.getmtime(self.updater.md_file)

                    if current_md_time > last_md_time:
                        print("
📝 ¡Cambio detectado en coincidencias.md!"                        print("🔄 Actualizando sistema...")

                        if self.updater.update_html():
                            print("✅ HTML actualizado")

                            # Commit y deploy si está configurado
                            if self.commit_changes():
                                print("💾 Cambios guardados")

                                if self.deployer.config.get("auto_deploy", False):
                                    print("🚀 Desplegando automáticamente...")
                                    self.deployer.deploy_to_pages()
                                else:
                                    print("ℹ️ Despliegue automático desactivado")

                        last_md_time = current_md_time

                    # Pequeña pausa
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
            # Despliegue completo
            if system.full_auto_deploy():
                print("\n🎉 ¡Auto-despliegue completado exitosamente!")
            else:
                print("\n❌ Error en auto-despliegue")

        elif command == "watch":
            # Modo vigilancia
            system.watch_and_deploy()

        elif command == "update":
            # Solo actualizar
            if system.updater.update_html():
                print("✅ Actualización completada")
            else:
                print("❌ Error en actualización")

        elif command == "deploy":
            # Solo desplegar
            if system.deployer.deploy_to_pages():
                print("✅ Despliegue completado")
            else:
                print("❌ Error en despliegue")

        elif command == "setup":
            # Configuración inicial
            print("⚙️ Configuración inicial...")

            # Configurar despliegue
            if system.deployer.configure_deployment():
                print("✅ Despliegue configurado")

                # Configurar Git
                if system.setup_git():
                    print("✅ Git configurado")

                    # Hacer commit inicial
                    if system.commit_changes():
                        print("✅ Commit inicial creado")
                    else:
                        print("❌ Error en commit inicial")
                else:
                    print("❌ Error en configuración Git")
            else:
                print("❌ Error en configuración de despliegue")

        else:
            print("❌ Comando no reconocido")
            print("💡 Comandos disponibles:")
            print("   full    - Despliegue completo")
            print("   watch   - Modo vigilancia")
            print("   update  - Solo actualizar HTML")
            print("   deploy  - Solo desplegar")
            print("   setup   - Configuración inicial")

    else:
        print("🚀 Despliegue rápido...")
        if system.full_auto_deploy():
            print("\n🎉 ¡Proceso completado exitosamente!")
        else:
            print("\n❌ Error en el proceso")
            print("💡 Usa 'python auto_deploy.py setup' para configurar")

if __name__ == "__main__":
    main()
