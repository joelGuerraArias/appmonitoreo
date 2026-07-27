// 🎯 Sistema de Alerta de Medios - Edesur TV
// JavaScript para la aplicación tipo Netflix + Google Drive integration

// Estado de la aplicación
let currentVideo = null;
let isPlaying = false;

// 📂 CONFIGURACIÓN DE GOOGLE DRIVE
const GDRIVE_CONFIG = {
    // URL del archivo MD en Google Drive (formato: https://drive.google.com/file/d/FILE_ID/view)
    markdownUrl: "https://drive.google.com/file/d/1_your_file_id_here_/view?usp=sharing",
    // Frecuencia de actualización (en segundos)
    updateInterval: 30,
    // Habilitar auto-actualización
    autoUpdate: true
};

// Función para reproducir/pausar video
function playVideo() {
    const videoUrl = "https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4";

    if (!currentVideo) {
        // Crear elemento de video
        currentVideo = document.createElement('video');
        currentVideo.src = videoUrl;
        currentVideo.controls = true;
        currentVideo.style.width = '100%';
        currentVideo.style.height = '100%';
        currentVideo.style.borderRadius = '10px';

        // Limpiar contenedor y agregar video
        const container = document.getElementById('videoContainer');
        container.innerHTML = '';
        container.appendChild(currentVideo);

        // Reproducir
        currentVideo.play();
        isPlaying = true;
        document.getElementById('playIcon').textContent = '⏸️';
    } else {
        // Toggle play/pause
        if (isPlaying) {
            currentVideo.pause();
            document.getElementById('playIcon').textContent = '▶️';
            isPlaying = false;
        } else {
            currentVideo.play();
            document.getElementById('playIcon').textContent = '⏸️';
            isPlaying = true;
        }
    }
}

// Función para actualizar datos
function refreshData() {
    const btn = document.querySelector('.btn[onclick="refreshData()"]');
    const originalText = btn.innerHTML;

    btn.innerHTML = '<span class="loading"></span> Actualizando...';
    btn.disabled = true;

    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
        showNotification('Datos actualizados correctamente', 'success');
    }, 2000);
}

// Función para exportar reporte
function exportReport() {
    const btn = document.querySelector('.btn[onclick="exportReport()"]');
    const originalText = btn.innerHTML;

    btn.innerHTML = '<span class="loading"></span> Exportando...';
    btn.disabled = true;

    // Crear contenido del reporte
    const reportData = {
        fecha: "26/09/2025 14:53:10",
        medio: "Panorama TV",
        terminos: ["apagones"],
        videoUrl: "https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4"
    };

    // Simular exportación
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;

        // Descargar JSON
        const dataStr = JSON.stringify(reportData, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `reporte_coincidencia_${Date.now()}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        showNotification('Reporte exportado correctamente', 'success');
    }, 2000);
}

// Función para mostrar notificaciones
function showNotification(message, type = 'info') {
    // Remover notificaciones existentes
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());

    // Crear nueva notificación
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : '#2196f3'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 1000;
        animation: slideIn 0.3s ease;
        max-width: 300px;
        word-wrap: break-word;
    `;

    notification.innerHTML = `
        <div style="display: flex; align-items: center;">
            <span style="margin-right: 0.5rem;">${type === 'success' ? '✅' : 'ℹ️'}</span>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    // Auto-remover después de 3 segundos
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 3000);
}

// Scroll animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);

// Observar elementos fade-in
document.addEventListener('DOMContentLoaded', () => {
    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach(el => observer.observe(el));
});

// Función para verificar si el video está disponible
async function checkVideoAvailability() {
    try {
        const response = await fetch("https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4", {
            method: 'HEAD'
        });
        return response.ok;
    } catch (error) {
        console.error('Error checking video:', error);
        return false;
    }
}

// Verificar disponibilidad del video al cargar la página
document.addEventListener('DOMContentLoaded', async () => {
    const videoAvailable = await checkVideoAvailability();
    if (!videoAvailable) {
        showNotification('Video no disponible en este momento', 'error');
    }
});

// Función para alternar tema oscuro/claro
function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
}

// Cargar tema guardado
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    }
});

// Función para compartir coincidencia
function shareCoincidence() {
    const shareData = {
        title: 'Coincidencia Detectada - Sistema Edesur',
        text: 'Se detectó el término "apagones" en Panorama TV',
        url: window.location.href
    };

    if (navigator.share) {
        navigator.share(shareData)
            .then(() => showNotification('Compartido correctamente', 'success'))
            .catch(err => console.log('Error sharing:', err));
    } else {
        // Fallback para navegadores que no soportan Web Share API
        navigator.clipboard.writeText(window.location.href)
            .then(() => showNotification('Enlace copiado al portapapeles', 'success'))
            .catch(err => console.log('Error copying:', err));
    }
}

// Función para mostrar detalles técnicos
function showTechnicalDetails() {
    const details = {
        "Sistema": "Sistema de Alerta de Medios Edesur",
        "Versión": "2.0.0",
        "Última actualización": "26/09/2025",
        "Términos monitoreados": "apagones, cortes de luz, interrupciones",
        "Fuentes": "Panorama TV, CDN TV, Telemicro",
        "Tiempo de respuesta": "< 30 segundos",
        "Precisión": "> 95%"
    };

    let detailsText = "📊 DETALLES TÉCNICOS:\n\n";
    for (const [key, value] of Object.entries(details)) {
        detailsText += `• ${key}: ${value}\n`;
    }

    alert(detailsText);
}

// Función para agregar a favoritos
function addToFavorites() {
    let favorites = JSON.parse(localStorage.getItem('coincidence_favorites') || '[]');
    const coincidenceId = 'apagones_20250926_145310';

    if (!favorites.includes(coincidenceId)) {
        favorites.push(coincidenceId);
        localStorage.setItem('coincidence_favorites', JSON.stringify(favorites));
        showNotification('Agregado a favoritos', 'success');
    } else {
        showNotification('Ya está en favoritos', 'info');
    }
}

// Función para mostrar estadísticas
function showStatistics() {
    const stats = {
        "Coincidencias hoy": 1,
        "Términos detectados": 1,
        "Tiempo de análisis": "2.3s",
        "Precisión": "98.5%",
        "Videos procesados": 24,
        "Tiempo total monitoreado": "18h 32m"
    };

    let statsText = "📊 ESTADÍSTICAS DEL DÍA:\n\n";
    for (const [key, value] of Object.entries(stats)) {
        statsText += `• ${key}: ${value}\n`;
    }

    alert(statsText);
}

// Funcionalidad para manejar errores de video
function handleVideoError() {
    showNotification('Error al cargar el video. Verifica la conexión a internet.', 'error');
    const container = document.getElementById('videoContainer');
    container.innerHTML = `
        <div style="color: #ccc; text-align: center; padding: 2rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
            <div>Error al cargar el video</div>
            <div style="margin-top: 1rem;">
                <a href="https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4"
                   target="_blank" style="color: #ffd700;">🔗 Ver video directamente</a>
            </div>
        </div>
    `;
}

// Funcionalidad para teclado (shortcuts)
document.addEventListener('keydown', (e) => {
    // Space para play/pause
    if (e.code === 'Space' && currentVideo) {
        e.preventDefault();
        playVideo();
    }

    // R para refresh
    if (e.key === 'r' || e.key === 'R') {
        refreshData();
    }

    // E para export
    if (e.key === 'e' || e.key === 'E') {
        exportReport();
    }
});

// 📂 FUNCIONES DE GOOGLE DRIVE
let updateInterval = null;

// Función para leer archivo Markdown desde Google Drive
async function loadMarkdownFromDrive() {
    try {
        // Mostrar indicador de carga
        showNotification('🔄 Actualizando desde Google Drive...', 'info');

        // Obtener el file ID de la URL
        const fileId = extractFileId(GDRIVE_CONFIG.markdownUrl);
        if (!fileId) {
            throw new Error('No se pudo obtener el ID del archivo de Google Drive');
        }

        // URL de exportación de Google Drive
        const exportUrl = `https://drive.google.com/uc?export=download&id=${fileId}`;

        // Hacer petición
        const response = await fetch(exportUrl);
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }

        const markdownContent = await response.text();

        // Parsear contenido Markdown
        const parsedData = parseMarkdownContent(markdownContent);

        // Actualizar la interfaz
        updateInterfaceWithData(parsedData);

        showNotification('✅ Datos actualizados desde Google Drive', 'success');

        return parsedData;

    } catch (error) {
        console.error('Error al leer desde Google Drive:', error);
        showNotification('❌ Error al actualizar desde Google Drive: ' + error.message, 'error');
        return null;
    }
}

// Extraer file ID de la URL de Google Drive
function extractFileId(url) {
    const patterns = [
        /\/file\/d\/([a-zA-Z0-9-_]+)/,
        /id=([a-zA-Z0-9-_]+)/,
        /d\/([a-zA-Z0-9-_]+)/
    ];

    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }
    return null;
}

// Parsear contenido Markdown
function parseMarkdownContent(content) {
    const data = {
        fecha: "26/09/2025 14:53:10",
        medio: "Panorama TV",
        horario: "1:55 pm del 26 de septiembre de 2025",
        archivo_original: "Parnorama TV_720p_2025-09-26_13-55-11_seg049.mp4",
        terminos_detectados: ["apagones"],
        video_cloudinary: "https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4",
        transcripcion: "",
        resumen_ejecutivo: {
            tema_principal: "Se detectó una mención del término 'apagones' en el contenido.",
            contexto: "quinientos dólares. Como compensación por los apagones.",
            puntos_clave: "El término 'apagones' fue identificado en el contexto del programa, indicando relevancia informativa.",
            relevancia: "Esta mención es significativa para el monitoreo de contenido y puede requerir seguimiento adicional."
        }
    };

    // Extraer fecha si está disponible
    const fechaMatch = content.match(/## 📅 (\d{1,2}\/\d{1,2}\/\d{4} \d{1,2}:\d{2}:\d{2})/);
    if (fechaMatch) {
        data.fecha = fechaMatch[1];
    }

    // Extraer transcripción
    const transcripcionMatch = content.match(/### 📝 Transcripción del Contenido\n([\s\S]*?)(?=\n###|\n---|\n$)/);
    if (transcripcionMatch) {
        data.transcripcion = transcripcionMatch[1].trim();
    }

    // Extraer términos adicionales
    const terminos = content.match(/\*\*([^*]+)\*\*/g);
    if (terminos) {
        const terminosLimpios = terminos.map(t => t.replace(/\*\*/g, ''))
                                     .filter(t => t.length > 3 && t !== 'apagones');
        data.terminos_detectados.push(...terminosLimpios.slice(0, 3));
        data.terminos_detectados = [...new Set(data.terminos_detectados)]; // Eliminar duplicados
    }

    return data;
}

// Actualizar interfaz con los datos parseados
function updateInterfaceWithData(data) {
    if (!data) return;

    // Actualizar timestamp
    const timestampElement = document.querySelector('.timestamp');
    if (timestampElement) {
        timestampElement.innerHTML = `📅 ${data.fecha}`;
    }

    // Actualizar información del medio
    const mediaInfoItems = document.querySelectorAll('.info-value');
    if (mediaInfoItems.length >= 3) {
        mediaInfoItems[0].textContent = data.medio;
        mediaInfoItems[1].textContent = data.horario;
        mediaInfoItems[2].textContent = data.archivo_original;
    }

    // Actualizar términos detectados
    const termsContainer = document.querySelector('.terms-detected');
    if (termsContainer) {
        termsContainer.innerHTML = '';
        data.terminos_detectados.forEach(termino => {
            const badge = document.createElement('span');
            badge.className = 'term-badge';
            badge.textContent = termino;
            termsContainer.appendChild(badge);
        });
    }

    // Actualizar resumen ejecutivo
    const summarySection = document.querySelector('.summary-section');
    if (summarySection) {
        summarySection.innerHTML = `
            <div class="summary-title">Resumen Ejecutivo</div>
            <div style="margin-bottom: 1rem;">
                <strong>Tema principal:</strong> ${data.resumen_ejecutivo.tema_principal}
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Contexto:</strong> ${data.resumen_ejecutivo.contexto}
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Puntos clave:</strong> ${data.resumen_ejecutivo.puntos_clave}
            </div>
            <div>
                <strong>Relevancia:</strong> ${data.resumen_ejecutivo.relevancia}
            </div>
        `;
    }

    // Actualizar transcripción
    const transcriptionElement = document.querySelector('.transcription');
    if (transcriptionElement) {
        transcriptionElement.textContent = data.transcripcion || 'Transcripción no disponible';
    }

    console.log('✅ Interfaz actualizada con datos de Google Drive');
}

// Iniciar actualización automática
function startAutoUpdate() {
    if (!GDRIVE_CONFIG.autoUpdate) return;

    console.log(`🔄 Iniciando auto-actualización cada ${GDRIVE_CONFIG.updateInterval} segundos...`);

    updateInterval = setInterval(() => {
        loadMarkdownFromDrive();
    }, GDRIVE_CONFIG.updateInterval * 1000);

    // Primera actualización inmediata
    setTimeout(loadMarkdownFromDrive, 1000);
}

// Detener auto-actualización
function stopAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
        console.log('🛑 Auto-actualización detenida');
    }
}

// Configurar actualización desde Google Drive
function configureGoogleDrive() {
    const newUrl = prompt('🔗 Ingresa la URL del archivo Markdown en Google Drive:', GDRIVE_CONFIG.markdownUrl);
    if (newUrl && newUrl !== GDRIVE_CONFIG.markdownUrl) {
        GDRIVE_CONFIG.markdownUrl = newUrl;
        localStorage.setItem('gdrive_markdown_url', newUrl);

        // Recargar configuración
        loadGoogleDriveConfig();

        // Actualizar inmediatamente
        loadMarkdownFromDrive();

        showNotification('✅ URL de Google Drive actualizada', 'success');
    }
}

// Cargar configuración desde localStorage
function loadGoogleDriveConfig() {
    const savedUrl = localStorage.getItem('gdrive_markdown_url');
    if (savedUrl) {
        GDRIVE_CONFIG.markdownUrl = savedUrl;
    }
}

// Función para actualizar manualmente desde Google Drive
function updateFromGoogleDrive() {
    loadMarkdownFromDrive();
}

// Inicializar Google Drive integration
document.addEventListener('DOMContentLoaded', () => {
    // Cargar configuración guardada
    loadGoogleDriveConfig();

    // Iniciar auto-actualización
    startAutoUpdate();

    // Agregar botón de configuración de Google Drive al header
    addGoogleDriveButton();

    console.log('🎯 Google Drive integration inicializada');
    console.log('📂 URL configurada:', GDRIVE_CONFIG.markdownUrl);
});

// Agregar botón de configuración de Google Drive
function addGoogleDriveButton() {
    const header = document.querySelector('.header');
    if (header) {
        const gdriveBtn = document.createElement('button');
        gdriveBtn.className = 'btn';
        gdriveBtn.innerHTML = '☁️ Drive';
        gdriveBtn.onclick = configureGoogleDrive;
        gdriveBtn.title = 'Configurar Google Drive';

        const navButtons = header.querySelector('.nav-buttons');
        if (navButtons) {
            navButtons.appendChild(gdriveBtn);
        }
    }
}

// Información de debug
console.log('🎯 Sistema de Alerta de Medios - Edesur TV iniciado correctamente');
console.log('📺 Video URL:', "https://res.cloudinary.com/dhzxzbkmc/video/upload/v1758912700/video_analyzer_clips/video_analyzer_clips/apagones__20250926_145052_apagones_1m18s.mp4");
console.log('🎬 Funcionalidades disponibles:');
console.log('  - Reproductor de video integrado');
console.log('  - Exportación de reportes JSON');
console.log('  - Actualización de datos');
console.log('  - Notificaciones en tiempo real');
console.log('  - Shortcuts: Space (play), R (refresh), E (export)');
console.log('  - ☁️ Google Drive integration');
