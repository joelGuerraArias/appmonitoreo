#!/usr/bin/env python3
"""
Script para completar los campos fecha_detencion que faltan en Supabase
"""

from datetime import datetime
from supabase import create_client, Client

# Configuración de Supabase
SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

def verificar_registros_sin_fecha_detencion():
    """Verifica qué registros no tienen fecha_detencion"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Cliente de Supabase inicializado correctamente")
        
        print("🔍 Buscando registros sin fecha_detencion...")
        result = supabase.table('alertas_medios').select('*').is_('fecha_detencion', 'null').execute()
        
        if result.data:
            print(f"❌ Encontrados {len(result.data)} registros sin fecha_detencion:")
            for i, registro in enumerate(result.data, 1):
                print(f"  {i}. ID: {registro.get('id', 'N/A')} - {registro.get('termino_detectado', 'N/A')} en {registro.get('nombre_medio', 'N/A')}")
                print(f"     Fecha programa: {registro.get('fecha_programa', 'N/A')} {registro.get('hora_programa', 'N/A')}")
                print(f"     Archivo: {registro.get('nombre_archivo', 'N/A')}")
                print()
            return result.data
        else:
            print("✅ Todos los registros tienen fecha_detencion")
            return []
            
    except Exception as e:
        print(f"❌ Error verificando registros: {str(e)}")
        return []

def completar_fechas_detencion(registros):
    """Completa las fechas de detención faltantes"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        print(f"🔧 Completando {len(registros)} registros sin fecha_detencion...")
        
        for registro in registros:
            registro_id = registro['id']
            fecha_programa = registro.get('fecha_programa')
            hora_programa = registro.get('hora_programa')
            
            # Crear fecha_detencion basada en fecha_programa y hora_programa
            if fecha_programa and hora_programa:
                try:
                    # Combinar fecha y hora
                    fecha_detencion = f"{fecha_programa} {hora_programa}"
                    print(f"  📅 Actualizando ID {registro_id}: {fecha_detencion}")
                    
                    # Actualizar el registro
                    result = supabase.table('alertas_medios').update({
                        'fecha_detencion': fecha_detencion
                    }).eq('id', registro_id).execute()
                    
                    if result.data:
                        print(f"  ✅ ID {registro_id} actualizado correctamente")
                    else:
                        print(f"  ❌ Error actualizando ID {registro_id}")
                        
                except Exception as e:
                    print(f"  ❌ Error procesando ID {registro_id}: {str(e)}")
            else:
                # Si no hay fecha_programa, usar fecha actual
                fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"  📅 Actualizando ID {registro_id} con fecha actual: {fecha_actual}")
                
                result = supabase.table('alertas_medios').update({
                    'fecha_detencion': fecha_actual
                }).eq('id', registro_id).execute()
                
                if result.data:
                    print(f"  ✅ ID {registro_id} actualizado con fecha actual")
                else:
                    print(f"  ❌ Error actualizando ID {registro_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error completando fechas: {str(e)}")
        return False

def verificar_todos_los_registros():
    """Verifica todos los registros en la tabla"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        print("🔍 Verificando todos los registros en alertas_medios...")
        result = supabase.table('alertas_medios').select('*').order('id', desc=True).execute()
        
        if result.data:
            print(f"📊 Total de registros: {len(result.data)}")
            print("\n📋 Todos los registros:")
            for i, registro in enumerate(result.data, 1):
                fecha_detencion = registro.get('fecha_detencion', 'None')
                status = "✅" if fecha_detencion and fecha_detencion != 'None' else "❌"
                print(f"  {i}. {status} ID: {registro.get('id', 'N/A')} - {registro.get('termino_detectado', 'N/A')} en {registro.get('nombre_medio', 'N/A')}")
                print(f"     Fecha detección: {fecha_detencion}")
                print(f"     Fecha programa: {registro.get('fecha_programa', 'N/A')} {registro.get('hora_programa', 'N/A')}")
                print()
            return True
        else:
            print("ℹ️ No hay registros en la tabla")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando registros: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 Completando campos fecha_detencion faltantes en Supabase...")
    print("=" * 80)
    
    # 1. Verificar registros sin fecha_detencion
    print("1️⃣ Verificando registros sin fecha_detencion...")
    registros_sin_fecha = verificar_registros_sin_fecha_detencion()
    
    if registros_sin_fecha:
        print(f"\n2️⃣ Completando {len(registros_sin_fecha)} registros...")
        if completar_fechas_detencion(registros_sin_fecha):
            print("✅ Fechas completadas exitosamente")
        else:
            print("❌ Error completando fechas")
    else:
        print("✅ No hay registros que necesiten fecha_detencion")
    
    print("\n3️⃣ Verificación final de todos los registros...")
    verificar_todos_los_registros()
    
    print("\n" + "=" * 80)
    print("🎉 ¡Verificación completada!")
    print("🔍 Puedes verificar los datos en tu panel de Supabase:")
    print("   https://supabase.com/dashboard")



