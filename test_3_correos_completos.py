#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de 3 correos completos con video, transcripción y resumen
"""

import sys
import os
from datetime import datetime

# Importar las funciones del sistema principal
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transmistral2 import enviar_correo_brevo, obtener_correos_activos

def test_correos_completos():
    """Enviar 3 correos de prueba con diferentes configuraciones"""
    print("📧 ENVIANDO 3 CORREOS DE PRUEBA COMPLETOS")
    print("=" * 60)
    
    correos = obtener_correos_activos()
    print(f"👥 Enviando a {len(correos)} destinatarios:")
    for correo in correos:
        print(f"   📧 {correo}")
    
    resultados = []
    
    # === CORREO 1: CON VIDEO DE GOOGLE DRIVE ===
    print("\n🎬 CORREO 1: Con video de Google Drive")
    print("-" * 40)
    
    # Simular URL de Google Drive
    video_url_gdrive = "https://drive.google.com/file/d/1example_video_id/view"
    
    transcripcion_1 = """En esta parte del programa se discute sobre los parientes de la menor y las implicaciones legales del caso. El presentador menciona que "los parientes de la menor han solicitado una audiencia especial" y continúa explicando los detalles del procedimiento judicial."""
    
    resumen_1 = """**ANÁLISIS DE COINCIDENCIA - PARIENTES**

**CONTEXTO DETECTADO:**
Se identificó una mención específica del término "parientes" en el contexto de un caso judicial relacionado con una menor.

**PUNTOS CLAVE:**
- Solicitud de audiencia especial por parte de los parientes
- Procedimiento judicial en curso
- Implicaciones legales del caso

**RELEVANCIA:**
Alta relevancia para seguimiento debido al contexto judicial y la protección de menores."""
    
    contenido_completo_1 = f"""**TRANSCRIPCIÓN DEL CONTENIDO:**

{transcripcion_1}

---

**RESUMEN EJECUTIVO:**

{resumen_1}"""
    
    try:
        exito_1, mensaje_1 = enviar_correo_brevo(
            "parientes",
            contenido_completo_1,
            "LUNA TV_720p_2025-09-19_23-20-53_seg006.mp4",
            None,  # No hay video local
            "Luna TV - 11:20 PM del 19 de septiembre de 2025",
            ["parientes"],
            video_url_gdrive  # URL de Google Drive
        )
        
        if exito_1:
            print("   ✅ CORREO 1 ENVIADO EXITOSAMENTE")
            resultados.append(("Correo 1 (Google Drive)", True, mensaje_1))
        else:
            print(f"   ❌ ERROR: {mensaje_1}")
            resultados.append(("Correo 1 (Google Drive)", False, mensaje_1))
            
    except Exception as e:
        print(f"   ❌ EXCEPCIÓN: {e}")
        resultados.append(("Correo 1 (Google Drive)", False, str(e)))
    
    # === CORREO 2: CON VIDEO DE CLOUDINARY ===
    print("\n☁️ CORREO 2: Con video de Cloudinary")
    print("-" * 40)
    
    # URL de video de Cloudinary que sabemos que funciona
    video_cloudinary = "https://res.cloudinary.com/demo/video/upload/v1574671934/elephants.mp4"
    
    transcripcion_2 = """En este segmento se aborda el tema de la justicia y los procedimientos legales vigentes. El reportero explica que "la justicia debe seguir su curso normal" y detalla las diferentes etapas del proceso judicial."""
    
    resumen_2 = """**ANÁLISIS DE COINCIDENCIA - JUSTICIA**

**CONTEXTO DETECTADO:**
Mención del término "justicia" en el contexto de procedimientos legales y procesos judiciales.

**PUNTOS CLAVE:**
- Curso normal de los procedimientos
- Etapas del proceso judicial
- Importancia del debido proceso

**RELEVANCIA:**
Relevante para monitoreo de temas judiciales y procesos legales."""
    
    contenido_completo_2 = f"""**TRANSCRIPCIÓN DEL CONTENIDO:**

{transcripcion_2}

---

**RESUMEN EJECUTIVO:**

{resumen_2}"""
    
    try:
        exito_2, mensaje_2 = enviar_correo_brevo(
            "justicia",
            contenido_completo_2,
            "LUNA TV_720p_2025-09-19_23-20-53_seg007.mp4",
            None,  # No hay video local
            "Luna TV - 11:25 PM del 19 de septiembre de 2025",
            ["justicia"],
            video_cloudinary  # URL de Cloudinary como si fuera Google Drive
        )
        
        if exito_2:
            print("   ✅ CORREO 2 ENVIADO EXITOSAMENTE")
            resultados.append(("Correo 2 (Cloudinary)", True, mensaje_2))
        else:
            print(f"   ❌ ERROR: {mensaje_2}")
            resultados.append(("Correo 2 (Cloudinary)", False, mensaje_2))
            
    except Exception as e:
        print(f"   ❌ EXCEPCIÓN: {e}")
        resultados.append(("Correo 2 (Cloudinary)", False, str(e)))
    
    # === CORREO 3: SIN VIDEO (SOLO TRANSCRIPCIÓN Y RESUMEN) ===
    print("\n📝 CORREO 3: Solo transcripción y resumen (sin video)")
    print("-" * 40)
    
    transcripcion_3 = """Durante la cobertura deportiva se menciona el equipo San Lorenzo y sus últimos resultados. El comentarista deportivo indica que "San Lorenzo ha mostrado una mejora significativa" y analiza las estadísticas del equipo."""
    
    resumen_3 = """**ANÁLISIS DE COINCIDENCIA - SAN LORENZO**

**CONTEXTO DETECTADO:**
Mención del término "San Lorenzo" en el contexto deportivo, específicamente sobre el rendimiento del equipo.

**PUNTOS CLAVE:**
- Mejora significativa del equipo
- Análisis de estadísticas deportivas
- Cobertura deportiva especializada

**RELEVANCIA:**
Relevante para seguimiento de información deportiva y menciones del equipo."""
    
    contenido_completo_3 = f"""**TRANSCRIPCIÓN DEL CONTENIDO:**

{transcripcion_3}

---

**RESUMEN EJECUTIVO:**

{resumen_3}"""
    
    try:
        exito_3, mensaje_3 = enviar_correo_brevo(
            "san lorenzo",
            contenido_completo_3,
            "LUNA TV_720p_2025-09-19_23-20-53_seg008.mp4",
            None,  # No hay video local ni URL
            "Luna TV - 11:30 PM del 19 de septiembre de 2025",
            ["san lorenzo"],
            None  # No hay video
        )
        
        if exito_3:
            print("   ✅ CORREO 3 ENVIADO EXITOSAMENTE")
            resultados.append(("Correo 3 (Sin video)", True, mensaje_3))
        else:
            print(f"   ❌ ERROR: {mensaje_3}")
            resultados.append(("Correo 3 (Sin video)", False, mensaje_3))
            
    except Exception as e:
        print(f"   ❌ EXCEPCIÓN: {e}")
        resultados.append(("Correo 3 (Sin video)", False, str(e)))
    
    return resultados

if __name__ == "__main__":
    print(f"🕐 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    resultados = test_correos_completos()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    exitosos = 0
    for nombre, exito, mensaje in resultados:
        if exito:
            print(f"✅ {nombre}: EXITOSO")
            exitosos += 1
        else:
            print(f"❌ {nombre}: ERROR - {mensaje[:100]}")
    
    print(f"\n📈 ESTADÍSTICAS:")
    print(f"   ✅ Exitosos: {exitosos}/{len(resultados)}")
    print(f"   ❌ Fallidos: {len(resultados) - exitosos}/{len(resultados)}")
    
    if exitosos == len(resultados):
        print("\n🎉 ¡TODOS LOS CORREOS ENVIADOS EXITOSAMENTE!")
        print("=" * 60)
        print("📬 REVISA TUS CORREOS:")
        print("   📧 info@fgjmedios.com")
        print("   📧 autosemana@gmail.com")
        print("\n📧 BUSCA LOS CORREOS CON ASUNTOS:")
        print("   '🎯 Coincidencia: parientes'")
        print("   '🎯 Coincidencia: justicia'") 
        print("   '🎯 Coincidencia: san lorenzo'")
        print("\n🎬 CADA CORREO DEBE INCLUIR:")
        print("   ✅ Transcripción completa del contenido")
        print("   ✅ Resumen ejecutivo detallado")
        print("   ✅ Player de video incrustado (correos 1 y 2)")
        print("   ✅ Información completa del medio")
        print("   ✅ Términos detectados destacados")
        print("   ✅ Diseño profesional y moderno")
    else:
        print(f"\n⚠️ {len(resultados) - exitosos} CORREOS FALLARON")
        print("🔧 Revisa la configuración y los logs")
    
    print(f"\n🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
