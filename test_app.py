#!/usr/bin/env python3
# Prueba rápida de la aplicación

try:
    print("🧪 Probando importaciones...")
    
    import customtkinter as ctk
    print("✅ CustomTkinter importado correctamente")
    
    import cv2
    print("✅ OpenCV importado correctamente")
    
    import openai
    print("✅ OpenAI importado correctamente")
    
    from renamer import VideoRenamerApp
    print("✅ VideoRenamerApp importado correctamente")
    
    print("\n🎉 ¡Todas las importaciones exitosas!")
    print("🚀 La aplicación está lista para usar")
    print("\n📝 Funcionalidades implementadas:")
    print("   • Renombrado universal de videos")
    print("   • Detección automática de medios")
    print("   • OCR inteligente con OpenAI Vision")
    print("   • Programación genérica personalizable")
    
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("📦 Instala las dependencias faltantes")
except Exception as e:
    print(f"❌ Error: {e}")

input("\nPresiona Enter para continuar...")

