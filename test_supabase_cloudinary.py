import sys
import os
import json
import cloudinary
import cloudinary.uploader
from datetime import datetime
from supabase import create_client

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from videoAnalizerv2 import (
    subir_video_cloudinary, 
    enviar_supabase_cliente,
    cargar_clientes
)

def test_supabase_cloudinary_flow():
    """
    Test the flow from Cloudinary upload to Supabase insertion.
    """
    print("🧪 Starting Supabase & Cloudinary Integration Test...")
    
    # 1. Load config
    clientes = cargar_clientes()
    if not clientes:
        print("❌ Could not load client configuration.")
        return
    
    # Use client 'default' for testing
    client_to_test = next((c for c in clientes if c['id'] == 'default'), clientes[0])
    print(f"👤 Testing with client: {client_to_test['nombre']} (ID: {client_to_test['id']})")
    
    # 2. Check a dummy file to upload
    test_file = "test_upload.txt"
    with open(test_file, "w") as f:
        f.write("This is a test file for Cloudinary and Supabase integration.")
    
    try:
        # 3. Simulate Cloudinary Upload
        print("☁️ Uploading dummy file to Cloudinary...")
        # Configure cloudinary for upload
        cloud_config = client_to_test.get('cloudinary', {})
        cloudinary.config(
            cloud_name=cloud_config['cloud_name'],
            api_key=cloud_config['api_key'],
            api_secret=cloud_config['api_secret']
        )
        
        # We'll use a txt file but tell Cloudinary it's raw or just use the helper
        # Actually subir_video_cloudinary expects a video, so let's mock the result if we don't want to upload a real video
        # or just try to upload the tiny txt as a 'raw' file if supported.
        # For simplicity in this test script, we'll assume we have a real URL or use the actual function if a small video exists.
        
        test_video = "small_test_video.mp4"
        if not os.path.exists(test_video):
            # Create a very tiny valid-ish file or just mock the URL
            print("⚠️ small_test_video.mp4 not found, using a mock URL for Supabase test part.")
            url_cloudinary = "https://res.cloudinary.com/demo/video/upload/v1234567/sample.mp4"
        else:
            url_cloudinary, msg = subir_video_cloudinary(test_video, "test_term")
            if not url_cloudinary:
                print(f"❌ Cloudinary upload failed: {msg}")
                return
            print(f"✅ Cloudinary URL: {url_cloudinary}")

        # 4. Test Supabase Insertion with the new table names
        tabla_nombre = client_to_test['supabase']['tabla_nombre']
        print(f"🗄️ Testing Supabase insertion to table: {tabla_nombre}...")
        
        # Check columns of the table
        try:
            supabase_url = client_to_test['supabase']['url']
            supabase_key = client_to_test['supabase']['anon_key']
            temp_client = create_client(supabase_url, supabase_key)
            res = temp_client.table(tabla_nombre).select("*").limit(1).execute()
            if res.data:
                print(f"📋 Columns in {tabla_nombre}: {list(res.data[0].keys())}")
            else:
                print(f"📋 Table {tabla_nombre} is empty, cannot easily inspect columns via select *.")
        except Exception as e:
            print(f"⚠️ Could not inspect columns: {e}")
        
        coincidencias_items = [
            {
                'termino': 'test_edesur',
                'contexto': 'Este es un mensaje de prueba para verificar que el link de Cloudinary llega a Supabase.'
            }
        ]
        
        success, msg = enviar_supabase_cliente(
            client_to_test, 
            coincidencias_items, 
            "test_video_file.mp4", 
            "video", 
            "Resumen Ejecutivo de Prueba", 
            "Transcripción completa de prueba.", 
            url_cloudinary, 
            "https://drive.google.com/test_link"
        )
        
        if success:
            print(f"✅ Supabase Insertion SUCCESS: {msg}")
        else:
            print(f"❌ Supabase Insertion FAILED: {msg}")
            
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_supabase_cloudinary_flow()
