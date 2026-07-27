#!/usr/bin/env python3
"""
Script para verificar sintaxis del archivo transmitral2.py
"""

import ast
import sys

def verificar_sintaxis(archivo_path):
    """Verifica la sintaxis de un archivo Python"""
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            codigo = f.read()

        # Parsear el código
        ast.parse(codigo)

        print(f"✅ Sintaxis correcta: {archivo_path}")
        return True

    except SyntaxError as e:
        print(f"❌ Error de sintaxis en {archivo_path}:")
        print(f"   Línea {e.lineno}: {e.text}")
        print(f"   {e.msg}")
        return False

    except Exception as e:
        print(f"❌ Error leyendo {archivo_path}: {e}")
        return False

if __name__ == "__main__":
    archivo = r"C:\Users\Administrador\Desktop\grabaciones\transmitral2.py"
    exito = verificar_sintaxis(archivo)

    if not exito:
        sys.exit(1)
    else:
        print("🎉 ¡Todas las verificaciones pasaron!")
        sys.exit(0)

