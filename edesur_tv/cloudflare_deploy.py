#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Cloudflare Pages Deployer - Edesur TV
Sistema de despliegue automático a Cloudflare Pages
"""

import os
import json
import requests
import subprocess
from pathlib import Path

class CloudflareDeployer:
    """Sistema de despliegue automático a Cloudflare Pages"""

    def __init__(self, config_file="deploy_config.json"):
        self.config_file = Path(config_file)
        self.config = self.load_config()

    def load_config(self):
        """Cargar configuración de despliegue"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "api_token": "",
                "account_id": "",
                "project_name": "edesur-tv",
                "github_repo": "",
                "auto_deploy": True
            }

    def save_config(self):
        """Guardar configuración"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def configure_deployment(self):
        """Configurar despliegue"""
        print("⚙️ Configuración de despliegue a Cloudflare Pages")
        print("=" * 50)

        config = {}

        # API Token
        token = input("🔑 API Token de Cloudflare: ").strip()
        if not token:
            print("❌ Se necesita API Token")
            return False
        config["api_token"] = token

        # Account ID
        account_id = input("🏢 Account ID de Cloudflare: ").strip()
        if not account_id:
            print("❌ Se necesita Account ID")
            return False
        config["account_id"] = account_id

        # Project Name
        project_name = input("📁 Nombre del proyecto (por defecto: edesur-tv): ").strip()
        config["project_name"] = project_name or "edesur-tv"

        # GitHub Repo (opcional)
        github_repo = input("🔗 Repositorio GitHub (opcional): ").strip()
        config["github_repo"] = github_repo

        # Auto deploy
        auto_deploy = input("🚀 ¿Despliegue automático? (y/n): ").lower().startswith('y')
        config["auto_deploy"] = auto_deploy

        self.config = config
        self.save_config()

        print("✅ Configuración guardada")
        return True

    def create_pages_project(self):
        """Crear proyecto en Cloudflare Pages"""
        headers = {
            "Authorization": f"Bearer {self.config['api_token']}",
            "Content-Type": "application/json"
        }

        # Datos del proyecto
        project_data = {
            "name": self.config["project_name"],
            "production_branch": "main"
        }

        # Si hay repo de GitHub, configurar
        if self.config.get("github_repo"):
            project_data["source"] = {
                "type": "github",
                "config": {
                    "owner": self.config["github_repo"].split("/")[0],
                    "repo_name": self.config["github_repo"].split("/")[1],
                    "production_branch": "main"
                }
            }
        else:
            # Configuración manual
            project_data["source"] = {
                "type": "direct_upload"
            }

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.config['account_id']}/pages/projects"

        try:
            response = requests.post(url, headers=headers, json=project_data)
            result = response.json()

            if response.status_code == 200 and result.get("success"):
                print("✅ Proyecto creado en Cloudflare Pages")
                print(f"📊 ID del proyecto: {result['result']['id']}")
                return result["result"]
            else:
                print(f"❌ Error al crear proyecto: {result.get('errors', 'Error desconocido')}")
                return None

        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return None

    def deploy_to_pages(self, directory=None):
        """Desplegar a Cloudflare Pages"""
        if not directory:
            directory = Path(__file__).parent

        print(f"🚀 Desplegando {directory} a Cloudflare Pages...")

        # Verificar que existe el directorio
        if not Path(directory).exists():
            print(f"❌ Error: No existe el directorio {directory}")
            return False

        # Si no hay proyecto, crearlo
        if not self.config.get("project_id"):
            print("📝 Creando proyecto...")
            project = self.create_pages_project()
            if not project:
                return False
            self.config["project_id"] = project["id"]
            self.save_config()

        # Para despliegue directo, usar Wrangler CLI
        try:
            cmd = [
                "npx", "wrangler", "pages", "deploy",
                str(directory),
                "--project-name", self.config["project_name"]
            ]

            print(f"📥 Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ ¡Despliegue exitoso!")
                print("🌐 Tu sitio está disponible en:")
                # Extraer URL del output
                for line in result.stdout.split('\n'):
                    if 'https://' in line and '.pages.dev' in line:
                        print(f"   🔗 {line.strip()}")
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

    def setup_github_integration(self):
        """Configurar integración con GitHub"""
        if not self.config.get("github_repo"):
            print("❌ No hay repositorio GitHub configurado")
            return False

        try:
            # Inicializar git si no existe
            if not Path(".git").exists():
                subprocess.run(["git", "init"], check=True)
                subprocess.run(["git", "config", "user.name", "Edesur TV Bot"], check=True)
                subprocess.run(["git", "config", "user.email", "bot@edesur.tv"], check=True)

            # Agregar archivos
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

            # Agregar remote si no existe
            result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True)
            if result.returncode != 0:
                subprocess.run(["git", "remote", "add", "origin", self.config["github_repo"]], check=True)

            print("✅ GitHub integration configurada")
            return True

        except Exception as e:
            print(f"❌ Error en GitHub integration: {e}")
            return False

def main():
    """Función principal"""
    print("🎯 Cloudflare Pages Deployer - Edesur TV")
    print("=" * 60)

    deployer = CloudflareDeployer()

    if len(os.sys.argv) > 1:
        command = os.sys.argv[1]

        if command == "config":
            deployer.configure_deployment()
        elif command == "deploy":
            directory = os.sys.argv[2] if len(os.sys.argv) > 2 else None
            deployer.deploy_to_pages(directory)
        elif command == "github":
            deployer.setup_github_integration()
        else:
            print("❌ Comando no reconocido")
            print("💡 Comandos disponibles: config, deploy, github")
    else:
        print("🚀 Despliegue rápido...")
        if deployer.deploy_to_pages():
            print("✅ ¡Despliegue completado!")
        else:
            print("❌ Error en el despliegue")
            print("💡 Usa 'python cloudflare_deploy.py config' para configurar")

if __name__ == "__main__":
    import sys
    main()
