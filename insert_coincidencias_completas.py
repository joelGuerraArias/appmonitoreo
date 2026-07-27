#!/usr/bin/env python3
"""
Script para insertar todas las coincidencias detectadas en Supabase
"""

from datetime import datetime, date, time
from supabase import create_client, Client

# Configuración de Supabase
SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

def verificar_campos_requeridos(coincidencias):
    """Verifica que todos los campos requeridos estén presentes"""
    campos_requeridos = [
        'fecha_detencion', 'termino_detectado', 'nombre_medio', 
        'hora_programa', 'fecha_programa', 'url_video', 
        'nombre_archivo', 'enlace_directo', 'contexto', 
        'resumen_ejecutivo', 'transcripcion', 'relevancia'
    ]
    
    print("🔍 Verificando campos requeridos...")
    for i, coincidencia in enumerate(coincidencias, 1):
        campos_faltantes = []
        for campo in campos_requeridos:
            if campo not in coincidencia or coincidencia[campo] is None or coincidencia[campo] == '':
                campos_faltantes.append(campo)
        
        if campos_faltantes:
            print(f"❌ Coincidencia {i}: Faltan campos: {', '.join(campos_faltantes)}")
            return False
        else:
            print(f"✅ Coincidencia {i}: Todos los campos presentes")
    
    print("✅ Todas las coincidencias tienen todos los campos requeridos")
    return True

def insertar_coincidencias():
    """Inserta todas las coincidencias detectadas en Supabase"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Cliente de Supabase inicializado correctamente")
        
        # Datos de todas las coincidencias
        coincidencias = [
            {
                'fecha_detencion': '2025-09-27 11:05:54',
                'termino_detectado': 'edesur',
                'nombre_medio': 'Politikal 26 Septiembre',
                'hora_programa': '11:05:54',
                'fecha_programa': '2025-09-27',
                'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758985435/video_analyzer_clips/video_analyzer_clips/edesur__20250927_110335_edesur_0m34s.mp4',
                'nombre_archivo': 'Politikal 26 Septiembre.mp4',
                'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758985435/video_analyzer_clips/video_analyzer_clips/edesur__20250927_110335_edesur_0m34s.mp4',
                'contexto': 'edesur, o contratista, edesur, contactó a mi esposa para decirle que ellos habían hecho una revisión en mi medidor',
                'resumen_ejecutivo': 'Se detectó una mención del término "edesur" en el contenido. El término "edesur" fue identificado en el contexto del programa, indicando relevancia informativa.',
                'transcripcion': 'Bueno, yo quiero aprovechar esta tribuna, no me acostumbro a este tipo de cosas, pero yo creo que la situación lo amerita. En la mañana de hoy, tengo y tengo las imágenes que voy a pedir que por favor me ayuden a difundirlas. En la mañana de hoy, un individuo que se identifica como técnico de la empresa distribuidora de electricidad EDESUR o contratista EDESUR, contactó a mi esposa para decirle que ellos habían hecho una revisión en mi medidor y que habían determinado que el medidor estaba alterado y que eso le podría traer problemas, problemas de sanciones pecuniarias y temas legales con EDESUR.',
                'relevancia': 'Alta'
            },
            {
                'fecha_detencion': '2025-09-27 00:31:50',
                'termino_detectado': 'apagones',
                'nombre_medio': 'Cdn Canal 37',
                'hora_programa': '22:39:50',
                'fecha_programa': '2025-09-26',
                'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758947383/video_analyzer_clips/video_analyzer_clips/apagones__20250927_002921_apagones_2m06s.mp4',
                'nombre_archivo': 'CDN CANAL 37_720p_2025-09-26_22-39-50_seg001.mp4',
                'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758947383/video_analyzer_clips/video_analyzer_clips/apagones__20250927_002921_apagones_2m06s.mp4',
                'contexto': 'El problema actual de Cuba se llaman los apagones',
                'resumen_ejecutivo': 'Se detectó una mención del término "apagones" en el contenido. El término "apagones" fue identificado en el contexto del programa, indicando relevancia informativa.',
                'transcripcion': 'El discurso de la guerra para mantener cohesionados de la mejor forma posible a lo interno de Venezuela para que el ciudadano venezolano, dentro de todo su descontento y desazón y decepción y de penurias que ha vivido durante muchos años, de alguna manera sienta que la soberanía de su país, la decisión soberana de su país de cuál debe ser el rumbo de Venezuela está amenazado por la injerencia de Estados Unidos en este caso.',
                'relevancia': 'Alta'
            },
            {
                'fecha_detencion': '2025-09-26 14:53:10',
                'termino_detectado': 'apagones',
                'nombre_medio': 'Parnorama Tv',
                'hora_programa': '13:55:11',
                'fecha_programa': '2025-09-26',
                'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4',
                'nombre_archivo': 'Parnorama TV_720p_2025-09-26_13-55-11_seg049.mp4',
                'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4',
                'contexto': 'quinientos dólares. Como compensación por los apagones.',
                'resumen_ejecutivo': 'Se detectó una mención del término "apagones" en el contenido. El término "apagones" fue identificado en el contexto del programa, indicando relevancia informativa.',
                'transcripcion': 'Oye, oye, Kennedy. Oye, oye. Dímelo. Yo te, oye, oye. Yo vivo aquí en Carolina del Norte, yo vivo en Gosboro, de Carolina del Norte. Oye, dile a él otra vez, ¿dónde? Cimiento, Gos, Cimiento. Dile dónde que tú vives. Gosboro. Gosboro. Tú ni lo puedes pronunciar. En Carolina del Norte, oye, oye bien. Ahí no hay ni plata, no te estás loco. Oye, y a mí, oye, aquí, aquí hubo un apagón. Aquí hubo un apagón. Sí. Y a los dos minutos me mandaba un mensaje a mi celular.',
                'relevancia': 'Alta'
            },
            {
                'fecha_detencion': '2025-09-26 13:40:47',
                'termino_detectado': 'apagones',
                'nombre_medio': 'Parnorama Tv',
                'hora_programa': '13:10:54',
                'fecha_programa': '2025-09-26',
                'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758908367/video_analyzer_clips/video_analyzer_clips/apagones__20250926_133851_apagones_4m43s.mp4',
                'nombre_archivo': 'Parnorama TV_720p_2025-09-26_13-10-54_seg040.mp4',
                'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758908367/video_analyzer_clips/video_analyzer_clips/apagones__20250926_133851_apagones_4m43s.mp4',
                'contexto': 'con el tema de los apagones, leonele bien hablar del pollo',
                'resumen_ejecutivo': 'Se detectó una mención del término "apagones" en el contenido. El término "apagones" fue identificado en el contexto del programa, indicando relevancia informativa.',
                'transcripcion': 'En el proceso de campaña, uno de los presidentes de los partidos, estoy hablando en este caso de Jorge Radamez Sorriza, presidente del Partido Cívico Renovador. Ese señor en los gobiernos, primero era de Hipólito, en el gobierno de Hipólito era jefe del ejército y jefe de la guardia presidencial.',
                'relevancia': 'Alta'
            },
            {
                'fecha_detencion': '2025-09-26 13:23:14',
                'termino_detectado': 'apagones',
                'nombre_medio': 'Show del Mediodia',
                'hora_programa': '11:59:01',
                'fecha_programa': '2025-09-26',
                'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758907226/video_analyzer_clips/video_analyzer_clips/apagones__20250926_131908_apagones_0m58s.mp4',
                'nombre_archivo': 'Show_del_Mediodia_20250926_115901\\Show_del_Mediodia_20250926_115901_seg014.mp4',
                'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758907226/video_analyzer_clips/video_analyzer_clips/apagones__20250926_131908_apagones_0m58s.mp4',
                'contexto': 'porque los apagones',
                'resumen_ejecutivo': 'Se detectó una mención del término "apagones" en el contenido. El término "apagones" fue identificado en el contexto del programa, indicando relevancia informativa.',
                'transcripcion': 'Estamos viviendo los sabanece y aquellos que nos visitan. Pues aquí en Samaná, como ustedes pueden ver, el cielo parcialmente nublado entre llovizna, aguaceros, tronadas, relámpagos. Pues aquí están pasando algunas cosas, no como está sucediendo en Santiago, en la capital.',
                'relevancia': 'Alta'
            },
            {
                'fecha_detencion': '2025-09-26 00:22:56',
                'termino_detectado': 'apagones',
                'nombre_medio': 'Cdn Canal 37',
                'hora_programa': '21:31:51',
                'fecha_programa': '2025-09-25',
                'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758860437/video_analyzer_clips/video_analyzer_clips/apagones__20250926_002013_apagones_2m52s.mp4',
                'nombre_archivo': 'CDN CANAL 37_720p_2025-09-25_21-31-51_seg004.mp4',
                'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758860437/video_analyzer_clips/video_analyzer_clips/apagones__20250926_002013_apagones_2m52s.mp4',
                'contexto': 'Los apagones siguen afectando la vida diaria de los habitantes',
                'resumen_ejecutivo': 'Se detectó una mención del término "apagones" en el contenido. El término "apagones" fue identificado en el contexto del programa, indicando relevancia informativa.',
                'transcripcion': 'Hablamos educación y deporte, la fórmula es ganadora. La gran fiesta del deporte escolar está por comenzar. La fórmula ganadora. Por más de 15 años, en el Hospital Metropolitano de Santiago, hemos contribuido a la salud de la población de República Dominicana.',
                'relevancia': 'Alta'
            }
        ]
        
        # Verificar que todos los campos estén presentes
        if not verificar_campos_requeridos(coincidencias):
            print("❌ Error: Faltan campos requeridos. No se puede proceder con la inserción.")
            return False
        
        print(f"🗄️ Insertando {len(coincidencias)} coincidencias en alertas_medios...")
        result = supabase.table('alertas_medios').insert(coincidencias).execute()
        
        if result.data:
            print(f"✅ {len(result.data)} coincidencias insertadas correctamente en Supabase")
            
            # Mostrar resumen de los registros insertados
            print("\n📋 Resumen de coincidencias insertadas:")
            for i, registro in enumerate(result.data, 1):
                print(f"  {i}. ID: {registro['id']} - {registro['termino_detectado']} en {registro['nombre_medio']} ({registro['relevancia']})")
                print(f"     Archivo: {registro['nombre_archivo']}")
                print(f"     Fecha: {registro['fecha_programa']} {registro['hora_programa']}")
                if registro.get('url_video'):
                    print(f"     Cloudinary: {registro['url_video'][:60]}...")
                print()
            
            return True
        else:
            print("❌ Error al insertar coincidencias en Supabase")
            print(f"🔍 Resultado: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error insertando coincidencias: {str(e)}")
        return False

def verificar_registros_existentes():
    """Verifica qué registros existen en la tabla"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        
        print("🔍 Verificando registros existentes en alertas_medios...")
        result = supabase.table('alertas_medios').select('*').order('id', desc=True).limit(10).execute()
        
        if result.data:
            print(f"✅ Encontrados {len(result.data)} registros en la tabla")
            print("\n📋 Últimos 10 registros:")
            for i, registro in enumerate(result.data, 1):
                print(f"  {i}. ID: {registro.get('id', 'N/A')} - {registro.get('termino_detectado', 'N/A')} en {registro.get('nombre_medio', 'N/A')} ({registro.get('relevancia', 'N/A')})")
                print(f"     Fecha detección: {registro.get('fecha_detencion', 'N/A')}")
                print(f"     Fecha programa: {registro.get('fecha_programa', 'N/A')} {registro.get('hora_programa', 'N/A')}")
                if registro.get('url_video'):
                    print(f"     Cloudinary: {registro['url_video'][:50]}...")
                print()
            return True
        else:
            print("ℹ️ No hay registros en la tabla")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando registros: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Insertando todas las coincidencias detectadas en Supabase...")
    print("=" * 80)
    
    # Verificar registros existentes
    print("1️⃣ Verificando registros existentes...")
    verificar_registros_existentes()
    
    print("\n2️⃣ Insertando coincidencias detectadas...")
    if insertar_coincidencias():
        print("✅ Todas las coincidencias insertadas exitosamente")
    else:
        print("❌ Error insertando coincidencias")
    
    print("\n3️⃣ Verificando registros después de inserción...")
    verificar_registros_existentes()
    
    print("\n" + "=" * 80)
    print("🎉 ¡Inserción completada!")
    print("🔍 Puedes verificar los datos en tu panel de Supabase:")
    print("   https://supabase.com/dashboard")
    print("\n✅ Las coincidencias están guardadas en la tabla alertas_medios")
    print("📊 Incluyen URLs de Cloudinary, contexto, transcripciones y relevancia")
    print(f"📈 Total de coincidencias procesadas: 6")
    print("   - 1 coincidencia de 'edesur'")
    print("   - 5 coincidencias de 'apagones'")

