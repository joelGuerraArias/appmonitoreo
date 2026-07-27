#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para corregir la indentación del bloque try-except en transmistral2.py"""

# Leer el archivo
with open('transmistral2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Líneas a modificar: desde 6273 hasta 6803 (inclusive)
# Necesitan 4 espacios adicionales de indentación
start_line = 6272  # línea 6273 en editor (índice 6272 en array)
end_line = 6802    # línea 6803 en editor (índice 6802 en array)

print(f"Indentando líneas {start_line+1} a {end_line+1}...")

# Agregar 4 espacios de indentación a cada línea en el rango
for i in range(start_line, end_line + 1):
    if i < len(lines):
        # Solo indentar si la línea no está vacía
        if lines[i].strip():
            lines[i] = '    ' + lines[i]

print("Indentación aplicada")

# Guardar el archivo
with open('transmistral2.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Archivo guardado exitosamente!")
print("Verificando compilación...")

import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'transmistral2.py'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("✅ ¡Compilación exitosa!")
else:
    print("❌ Error de compilación:")
    print(result.stderr)

