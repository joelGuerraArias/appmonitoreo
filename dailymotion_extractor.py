import requests
import re
import json
from urllib.parse import urlparse, parse_qs, unquote

def extract_dailymotion_info(page_url):
    """Extraer información específica de Dailymotion de la página"""
    print(f"[INFO] Analizando: {page_url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Referer': page_url
    }

    try:
        # Obtener el contenido de la página
        response = requests.get(page_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[ERROR] No se pudo cargar la página: {response.status_code}")
            return None

        content = response.text
        print(f"[OK] Página cargada ({len(content)} caracteres)")

        # Buscar URLs de Dailymotion
        dailymotion_patterns = [
            r'["\']([^"\']*dailymotion[^"\']*)["\']',
            r'["\']([^"\']*video[^"\']*x[0-9a-zA-Z]+[^"\']*)["\']',
            r'["\']([^"\']*player[^"\']*dailymotion[^"\']*)["\']'
        ]

        found_urls = []
        for pattern in dailymotion_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 10:
                    found_urls.append(match)

        # Buscar IDs de video (formato x9lincs)
        video_id_pattern = r'x([0-9a-zA-Z]{6})'
        video_ids = re.findall(video_id_pattern, content, re.IGNORECASE)

        # Buscar configuraciones de player
        config_patterns = [
            r'window\.playerConfig\s*=\s*({[^}]+})',
            r'playerConfig\s*:\s*({[^}]+})',
            r'"videoId"\s*:\s*"([^"]+)"',
            r'videoId\s*:\s*["\']([^"\']+)["\']'
        ]

        configs = []
        for pattern in config_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if isinstance(match, str):
                    configs.append(match)
                else:
                    configs.extend(match)

        return {
            'dailymotion_urls': list(set(found_urls)),
            'video_ids': list(set(video_ids)),
            'configs': configs,
            'page_content_length': len(content)
        }

    except Exception as e:
        print(f"[ERROR] Error al analizar la página: {e}")
        return None

def test_dailymotion_stream(video_id):
    """Probar si un video de Dailymotion es accesible"""
    if not video_id:
        return None

    print(f"\n[TESTING] Video ID: {video_id}")

    # URLs de Dailymotion para probar
    test_urls = [
        f"https://www.dailymotion.com/video/{video_id}",
        f"https://geo.dailymotion.com/player/{video_id}.html",
        f"https://www.dailymotion.com/embed/video/{video_id}"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Referer': 'https://cdn.com.do/'
    }

    for url in test_urls:
        try:
            print(f"  Probando: {url}")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                content = response.text[:1000]

                # Buscar manifest HLS en el contenido
                hls_patterns = [
                    r'["\']([^"\']*\.m3u8[^"\']*)["\']',
                    r'["\']([^"\']*video[^"\']*\.mp4[^"\']*)["\']'
                ]

                for pattern in hls_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if match and len(match) > 10:
                            print(f"    [STREAM FOUND] {match}")
                            return {
                                'video_id': video_id,
                                'stream_url': match,
                                'source_url': url,
                                'status': 'found'
                            }

                if 'dailymotion' in content.lower():
                    print(f"    [DAILYMOTION PAGE] OK")
                    return {
                        'video_id': video_id,
                        'stream_url': url,
                        'source_url': url,
                        'status': 'dailymotion_page'
                    }

        except Exception as e:
            print(f"    [ERROR] {e}")

    return None

# Main
if __name__ == "__main__":
    print("=== Dailymotion Stream Extractor ===")
    page_url = "https://cdn.com.do/envivo/"

    # Analizar la página principal
    info = extract_dailymotion_info(page_url)

    if not info:
        print("[ERROR] No se pudo analizar la página")
        sys.exit(1)

    print("\n[RESULTS]")
    print(f"URLs de Dailymotion encontradas: {len(info['dailymotion_urls'])}")
    for url in info['dailymotion_urls'][:5]:  # Mostrar solo las primeras 5
        print(f"  - {url}")

    print(f"\nVideo IDs encontrados: {len(info['video_ids'])}")
    for vid in info['video_ids'][:5]:  # Mostrar solo los primeros 5
        print(f"  - x{vid}")

    # Probar cada video ID encontrado
    found_streams = []
    for video_id in info['video_ids']:
        stream = test_dailymotion_stream(video_id)
        if stream:
            found_streams.append(stream)

    print(f"\n[STREAMS FOUND] {len(found_streams)} streams detectados:")
    for i, stream in enumerate(found_streams, 1):
        print(f"  {i}. {stream['stream_url']}")
        print(f"     Video ID: {stream['video_id']}")
        print(f"     Tipo: {stream['status']}")

    if not found_streams:
        print("\n[!] No se encontraron streams accesibles")
        print("Posibles causas:")
        print("  - El video requiere autenticación")
        print("  - El stream está protegido")
        print("  - La URL del video ha cambiado")
        print("  - Dailymotion bloquea el acceso automatizado")

    print("\n[FIN] Análisis completado")
