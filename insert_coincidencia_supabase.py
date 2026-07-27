#!/usr/bin/env python3
"""
Script para insertar una coincidencia de prueba en Supabase
"""

from datetime import datetime, date, time
from supabase import create_client, Client

# Configuración de Supabase
SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

def insertar_coincidencia_prueba():
    """Inserta una coincidencia de prueba en Supabase"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Cliente de Supabase inicializado correctamente")
        
        # Datos de coincidencia de prueba
        coincidencia_prueba = {
            'termino_detectado': 'apagones',
            'nombre_medio': 'Parnorama Tv',
            'hora_programa': '13:55:00',
            'fecha_programa': '2025-09-26',
            'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4',
            'nombre_archivo': 'Parnorama TV_720p_2025-09-26_13-55-11_seg049.mp4',
            'enlace_directo': 'https://drive.google.com/file/d/1ABC123XYZ/view',
            'contexto': 'quinientos dólares. Como compensación por los apagones.',
            'resumen_ejecutivo': 'Se detectó una mención del término "apagones" en el contenido. El término "apagones" fue identificado en el contexto del programa, indicando relevancia informativa.',
            'transcripcion': 'Oye, oye, Kennedy. Oye, oye. Dímelo. Yo te, oye, oye. Yo vivo aquí en Carolina del Norte, yo vivo en Gosboro, de Carolina del Norte. Oye, dile a él otra vez, ¿dónde? Cimiento, Gos, Cimiento. Dile dónde que tú vives. Gosboro. Gosboro. Tú ni lo puedes pronunciar. En Carolina del Norte, oye, oye bien. Ahí no hay ni plata, no te estás loco. Oye, y a mí, oye, aquí, aquí hubo un apagón. Aquí hubo un apagón. Sí. Y a los dos minutos me mandaba un mensaje a mi celular. Oye, oye. Que hubo un fallo eléctrico que iba a estar la luz, iba a estar la luz ininterrumpida por un espacio de dos a tres horas. Oye. Que ellos se disculpaban en la mañana. Un mensaje de una vez. Eso fue a la 10, eso fue a la 10 y 20. Y cuando llegó la factura eléctrica, José. Espera, espera, escúchame. Escúchame. Y vino la luz como a eso de las 2 de la mañana. Sí. Bien, eso fue 30 de junio. Me sucedió eso. Y a mí, el día 5 de julio, me llegó un cheque de la compañía Duke Electric de aquí de North Carolina, de 2.500 dólares. ¿Cómo compensación por los apagones? Aquí no. No, por si acaso. Aquí te roban la luz, te la cortan como quieran. Algo, algo de la nevera. Es por si me han dañado algo de los comestibles.',
            'relevancia': 'Alta'
        }
        
        print("🗄️ Insertando coincidencia de prueba en alertas_medios...")
        result = supabase.table('alertas_medios').insert([coincidencia_prueba]).execute()
        
        if result.data:
            print("✅ Coincidencia insertada correctamente en Supabase")
            print(f"📊 ID del registro: {result.data[0]['id']}")
            
            # Mostrar el registro insertado
            registro = result.data[0]
            print("\n📋 Registro insertado:")
            print(f"  - ID: {registro['id']}")
            print(f"  - Término: {registro['termino_detectado']}")
            print(f"  - Medio: {registro['nombre_medio']}")
            print(f"  - Archivo: {registro['nombre_archivo']}")
            print(f"  - URL Cloudinary: {registro['url_video']}")
            print(f"  - URL Drive: {registro['enlace_directo']}")
            print(f"  - Relevancia: {registro['relevancia']}")
            print(f"  - Fecha detección: {registro['fecha_detencion']}")
            
            return True
        else:
            print("❌ Error al insertar coincidencia en Supabase")
            print(f"🔍 Resultado: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error insertando coincidencia: {str(e)}")
        return False

def verificar_registros_existentes():
    """Verifica qué registros existen en la tabla"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        print("🔍 Verificando registros existentes en alertas_medios...")
        result = supabase.table('alertas_medios').select('*').order('id', desc=True).limit(5).execute()
        
        if result.data:
            print(f"✅ Encontrados {len(result.data)} registros en la tabla")
            print("\n📋 Últimos 5 registros:")
            for i, registro in enumerate(result.data, 1):
                print(f"  {i}. ID: {registro.get('id', 'N/A')} - {registro.get('termino_detectado', 'N/A')} en {registro.get('nombre_medio', 'N/A')} ({registro.get('relevancia', 'N/A')})")
                if registro.get('url_video'):
                    print(f"     Cloudinary: {registro['url_video'][:50]}...")
                if registro.get('enlace_directo'):
                    print(f"     Drive: {registro['enlace_directo'][:50]}...")
            return True
        else:
            print("ℹ️ No hay registros en la tabla")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando registros: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Insertando coincidencia de prueba en Supabase...")
    print("=" * 60)
    
    # Verificar registros existentes
    print("1️⃣ Verificando registros existentes...")
    verificar_registros_existentes()
    
    print("\n2️⃣ Insertando coincidencia de prueba...")
    if insertar_coincidencia_prueba():
        print("✅ Coincidencia de prueba insertada exitosamente")
    else:
        print("❌ Error insertando coincidencia de prueba")
    
    print("\n3️⃣ Verificando registros después de inserción...")
    verificar_registros_existentes()
    
    print("\n" + "=" * 60)
    print("🎉 ¡Prueba completada!")
    print("🔍 Puedes verificar los datos en tu panel de Supabase:")
    print("   https://supabase.com/dashboard")
    print("\n✅ La coincidencia está guardada en la tabla alertas_medios")
    print("📊 Incluye URL de Cloudinary, URL de Drive y todos los datos completos")




