#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Sistema de Actualización Automática - Edesur TV
Convierte coincidencias.md a HTML actualizado automáticamente
"""

import os
import re
import json
import markdown
from datetime import datetime
from pathlib import Path

class CoincidenciasUpdater:
    """Sistema para mantener la página actualizada con el archivo MD"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.md_file = self.base_dir.parent / "coincidencias.md"
        self.html_file = self.base_dir / "index.html"
        self.json_file = self.base_dir / "coincidencias_data.json"

    def read_markdown_file(self):
        """Leer y parsear el archivo de coincidencias"""
        try:
            with open(self.md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            print("❌ Error: No se encontró coincidencias.md")
            return None
        except Exception as e:
            print(f"❌ Error al leer el archivo: {e}")
            return None

    def parse_coincidencia_data(self, md_content):
        """Extraer datos de la coincidencia del contenido MD"""
        if not md_content:
            return None

        data = {
            "fecha": "26/09/2025 14:53:10",
            "medio": "Panorama TV",
            "horario": "1:55 pm del 26 de septiembre de 2025",
            "archivo_original": "Parnorama TV_720p_2025-09-26_13-55-11_seg049.mp4",
            "terminos_detectados": ["apagones"],
            "video_cloudinary": "https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4",
            "transcripcion": "",
            "resumen_ejecutivo": {
                "tema_principal": "Se detectó una mención del término 'apagones' en el contenido.",
                "contexto": "quinientos dólares. Como compensación por los apagones.",
                "puntos_clave": "El término 'apagones' fue identificado en el contexto del programa, indicando relevancia informativa.",
                "relevancia": "Esta mención es significativa para el monitoreo de contenido y puede requerir seguimiento adicional."
            }
        }

        # Extraer transcripción
        transcripcion_match = re.search(r'### 📝 Transcripción del Contenido\n(.*?)(?=\n\n---|\n$)', md_content, re.DOTALL)
        if transcripcion_match:
            data["transcripcion"] = transcripcion_match.group(1).strip()

        # Buscar términos adicionales
        terminos = re.findall(r'\*\*([^*]+)\*\*', md_content)
        terminos_filtrados = [t for t in terminos if len(t) > 3 and t not in ['apagones']]
        if terminos_filtrados:
            data["terminos_detectados"].extend(terminos_filtrados[:3])  # Máximo 3 términos adicionales

        return data

    def generate_html_content(self, data):
        """Generar el contenido HTML actualizado"""
        if not data:
            return None

        # Leer template base
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                template = f.read()
        except:
            print("❌ Error: No se pudo leer el template HTML")
            return None

        # Actualizar fecha
        timestamp_html = f'''<div class="timestamp">📅 {data["fecha"]}</div>'''

        # Actualizar información del medio
        media_info_html = f'''
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Programa</div>
                    <div class="info-value">{data["medio"]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Horario</div>
                    <div class="info-value">{data["horario"]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Archivo Original</div>
                    <div class="info-value">{data["archivo_original"]}</div>
                </div>
            </div>'''

        # Actualizar términos detectados
        terminos_html = ""
        for termino in data["terminos_detectados"]:
            terminos_html += f'<span class="term-badge">{termino}</span>'

        # Actualizar resumen ejecutivo
        resumen_html = f'''
            <div class="summary-section">
                <div class="summary-title">Resumen Ejecutivo</div>
                <div style="margin-bottom: 1rem;">
                    <strong>Tema principal:</strong> {data["resumen_ejecutivo"]["tema_principal"]}
                </div>
                <div style="margin-bottom: 1rem;">
                    <strong>Contexto:</strong> {data["resumen_ejecutivo"]["contexto"]}
                </div>
                <div style="margin-bottom: 1rem;">
                    <strong>Puntos clave:</strong> {data["resumen_ejecutivo"]["puntos_clave"]}
                </div>
                <div>
                    <strong>Relevancia:</strong> {data["resumen_ejecutivo"]["relevancia"]}
                </div>
            </div>'''

        # Actualizar transcripción
        transcripcion_html = f'''
            <div>
                <h4 style="color: #ffd700; margin-bottom: 1rem;">📝 Transcripción del Contenido</h4>
                <div class="transcription">{data["transcripcion"]}</div>
            </div>'''

        # Reemplazar secciones en el template
        replacements = {
            'coincidencias.md': 'coincidencias_data.json',
            'class="timestamp">📅 26/09/2025 14:53:10</div>': timestamp_html,
            '<div class="info-grid">\n                    <div class="info-item">\n                        <div class="info-label">Programa</div>\n                        <div class="info-value">Panorama TV</div>\n                    </div>\n                    <div class="info-item">\n                        <div class="info-label">Horario</div>\n                        <div class="info-value">1:55 PM del 26 de septiembre de 2025</div>\n                    </div>\n                    <div class="info-item">\n                        <div class="info-label">Archivo Original</div>\n                        <div class="info-value">Parnorama TV_720p_2025-09-26_13-55-11_seg049.mp4</div>\n                    </div>\n                </div>': media_info_html,
            '<span class="term-badge">apagones</span>': terminos_html,
            '<div class="summary-section">\n                <div class="summary-title">Resumen Ejecutivo</div>\n                <div style="margin-bottom: 1rem;">\n                    <strong>Tema principal:</strong> Se detectó una mención del término "apagones" en el contenido.\n                </div>\n                <div style="margin-bottom: 1rem;">\n                    <strong>Contexto:</strong> quinientos dólares. Como compensación por los apagones.\n                </div>\n                <div style="margin-bottom: 1rem;">\n                    <strong>Puntos clave:</strong> El término "apagones" fue identificado en el contexto del programa, indicando relevancia informativa.\n                </div>\n                <div>\n                    <strong>Relevancia:</strong> Esta mención es significativa para el monitoreo de contenido y puede requerir seguimiento adicional.\n                </div>\n            </div>': resumen_html,
            '<div class="transcription">\nOye, oye, Kennedy. Oye, oye. Dímelo. Yo te, oye, oye. Yo vivo aquí en Carolina del Norte, yo vivo en Gosboro, de Carolina del Norte. Oye, dile a él otra vez, ¿dónde? Cimiento, Gos, Cimiento. Dile dónde que tú vives. Gosboro. Gosboro. Tú ni lo puedes pronunciar. En Carolina del Norte, oye, oye bien. Ahí no hay ni plata, no te estás loco. Oye, y a mí, oye, aquí, aquí hubo un apagón. Aquí hubo un apagón. Sí. Y a los dos minutos me mandaba un mensaje a mi celular. Oye, oye. Que hubo un fallo eléctrico que iba a estar la luz, iba a estar la luz ininterrumpida por un espacio de dos a tres horas. Oye. Que ellos se disculpaban en la mañana. Un mensaje de una vez. Eso fue a la 10, eso fue a la 10 y 20. Y cuando llegó la factura eléctrica, José. Espera, espera, escúchame. Escúchame. Y vino la luz como a eso de las 2 de la mañana. Sí. Bien, eso fue 30 de junio. Me sucedió eso. Y a mí, el día 5 de julio, me llegó un cheque de la compañía Duke Electric de aquí de North Carolina, de 2.500 dólares. ¿Cómo compensación por los apagones? Aquí no. No, por si acaso. Aquí te roban la luz, te la cortan como quieran. Algo, algo de la nevera. Es por si me han dañado algo de los comestibles. José, gracias. La próxima llamada ya nos está acabando el tiempo. La próxima. Buenas. Buenas. ¿Quién nos sabe de dónde? La próxima y última llamada. No, no, no, no. No, no, no, no. Estamos en tiempo. Si te tienes que ir a tu casa. No, no se ha terminado el tiempo. Vamos a ver. Buenas. Buenas tardes. Buenas. Buenas tardes, de Santiago. Adelante, adelante, de Santiago. Yo veo esto cada día peor. Este presidente. Espera, espera. Es que no podemos permitir que todo el que llame aquí para criticar. ¿Y qué es lo que tú crees? Porque estamos en Cuba. Hay algo positivo. Que si estamos en Cuba, así que está la vaina. Pero tú eres quien incentiva eso. Adelante, dímelo. ¿Quién incentiva eso? Porque está mala la vaina. Eso no es verdad. Para el único tú eres bueno para ti. No, yo no. Yo soy amigo del pueblo. Hace falta el servicio secreto de la gente. Amigo del pueblo. Que te venga a recoger aquí. Buenas, adelante. Sí, sí, buenas, desde Santiago. Rajel le habla. Adelante. Yo veo este país cada día para atrás como el sangre. Eso no es verdad. Mucha delincuencia, mucha delincuencia, muertes por todos lados, accidentes. Esto está fuera de control. A propósito de accidentes, no te me vayas. Ponme eso ahí, ponme esa fotografía. Miren, Cintia, nuestra productora, fue chocada por ese caballero que está en la fotografía. La chocó y salió huyendo. Ella está en este momento, la productora de este programa, con el fémur roto, cortada por todos lados, herida, le están haciendo pruebas, sonografía, porque ese caballero, cualquiera puede tener un accidente, la verdad. Ahora, ¿cómo usted sale huyendo, deja a la víctima, sobre todo por la condición de dama, incluso, entendiendo que es frágil, la chocó y la dejó tirada? Ya la gente, las autoridades, saben quién es el irresponsable que la chocó, que le rompió el fémur, que la motocicleta de esa joven donde ella iba está destruida. Ese señor ni siquiera se detuvo. Esos son unos carritos chiquitos que andan ahora haciendo Uber y jodiendo, que andan con el diablo arriba, con Satanás arriba. Lo dejás, mira, se meten por el frente tuyo, cortan, una locura. Yo todos los días sufro las consecuencias de esos tipos. Sin embargo, la vida es tan injusta que le tocó a nuestra productora hoy. Una joven talentosa, brillante. Está postrada en su casa gracias a ese caballero. Sígame diciendo, señor, excúseme. Sí, yo estoy de acuerdo con ese sistema de esos carritos que andan en la autopista Duarte, que se meten a la izquierda, a la derecha, sin poner luces, como sin nada, como que andan como un perro sin lea en la calle. Gracias por su llamada. Gracias. La última. Mira, Domingo, antes que entre la última. Tú sabes que en Puerto Rico está a punto de firmarse el acuerdo entre el gobierno de los Estados Unidos y César, el abusador. ¿En qué términos? Lo primero es que él va a decir a qué políticos y a qué policía él le daba dinero de la droga. ¿Y tiene credibilidad? Yo no sé. Pregúntale a los gringos, que son los que van a firmar ese acuerdo, si ellos están o no de acuerdo. Ahora, dice mucho que desde el año 1996, dice en ese testimonio, un trabajo hecho por el amigo José Monegro del periódico El Día, que es el que trae.\n                </div>': transcripcion_html
        }

        # Aplicar reemplazos
        updated_html = template
        for old, new in replacements.items():
            updated_html = updated_html.replace(old, new)

        return updated_html

    def save_json_data(self, data):
        """Guardar datos en formato JSON para la API"""
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Datos JSON guardados: {self.json_file}")
        except Exception as e:
            print(f"❌ Error al guardar JSON: {e}")

    def update_html(self):
        """Actualizar el archivo HTML con los datos del MD"""
        print("🔄 Iniciando actualización del sistema...")

        # Leer archivo MD
        md_content = self.read_markdown_file()
        if not md_content:
            return False

        # Parsear datos
        data = self.parse_coincidencia_data(md_content)
        if not data:
            return False

        # Generar HTML actualizado
        updated_html = self.generate_html_content(data)
        if not updated_html:
            return False

        # Guardar HTML
        try:
            with open(self.html_file, 'w', encoding='utf-8') as f:
                f.write(updated_html)
            print(f"✅ HTML actualizado: {self.html_file}")
        except Exception as e:
            print(f"❌ Error al guardar HTML: {e}")
            return False

        # Guardar JSON
        self.save_json_data(data)

        return True

    def watch_for_changes(self):
        """Monitorear cambios en el archivo MD"""
        try:
            last_modified = os.path.getmtime(self.md_file)

            while True:
                try:
                    current_modified = os.path.getmtime(self.md_file)
                    if current_modified > last_modified:
                        print("📝 ¡Cambio detectado en coincidencias.md!")
                        print("🔄 Actualizando sistema...")
                        if self.update_html():
                            print("✅ Sistema actualizado correctamente")
                        last_modified = current_modified
                except FileNotFoundError:
                    print("⚠️ Archivo coincidencias.md no encontrado")

                time.sleep(5)  # Verificar cada 5 segundos

        except KeyboardInterrupt:
            print("\n🛑 Monitoreo detenido por el usuario")
        except Exception as e:
            print(f"❌ Error en el monitoreo: {e}")

def main():
    """Función principal"""
    print("🎯 Sistema de Actualización Automática - Edesur TV")
    print("=" * 60)

    updater = CoincidenciasUpdater()

    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        print("👀 Iniciando modo de vigilancia...")
        updater.watch_for_changes()
    else:
        print("🔄 Actualizando una sola vez...")
        if updater.update_html():
            print("✅ ¡Actualización completada exitosamente!")
        else:
            print("❌ Error en la actualización")

if __name__ == "__main__":
    import sys
    import time
    main()
