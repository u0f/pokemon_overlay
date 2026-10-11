# Pruebas y límites conocidos

## Revisión para publicación — 11 de octubre de 2026

- 71 pruebas Python y 7 frontend superadas en el entorno de trabajo.
- Paquete público extraído en una carpeta limpia, sin ROMs ni datos locales: 66 pruebas Python correctas y 1 omitida; 7 frontend correctas; npm ci y compilación correctos.
- Compilación TypeScript/Vite correcta. npm audit: cero vulnerabilidades detectadas; pip check: dependencias compatibles. Esto no constituye una garantía de ausencia de vulnerabilidades.
- Peticiones JSON: origen local, longitud válida y límite real de 64 KiB; probado incluso con cabecera de tamaño falseada. HTTP y WebSocket admiten el puerto elegido por el lanzador.
- Configuración validada en memoria durante las lecturas, persistencia en SQLite al guardar y conservación después de reiniciar.
- Exportación pública con lista de archivos permitidos, comprobación de rutas personales y patrones habituales de credenciales. El paquete excluye datos locales, ROMs, partidas, recursos extraídos, binarios, dependencias instaladas y cachés. Los datos del usuario se conservan únicamente en su carpeta de trabajo.
- No hay repositorio Git ni historial en esta carpeta; esta revisión cubre los archivos actuales y el ZIP de publicación.

## Emulador y ROMs

Las cinco ROMs españolas de Esmeralda rev. 0, Rubí rev. 1, Zafiro rev. 0, Rojo Fuego rev. 0 y Verde Hoja rev. 0 se han abierto en mGBA 0.10.5. Se han comprobado reconocimiento, extracción completa de nombres y recursos, arranque e inicio de partida y lectura de entrenador, ubicación, dinero y tiempo. No se incluyen las ROMs ni los registros de esas partidas en el código público.

Cada ROM genera 386 iconos de especie en su caché local. Se corrigieron las tablas de ubicación españolas de Zafiro rev. 0 y Verde Hoja rev. 0, el marcador NAME_END y el nombre variable de la guarida de Rubí/Zafiro. Rubí rev. 0 y Zafiro rev. 1 solo cuentan con pruebas sintéticas.

El bridge se prueba con un doble de mGBA para los siete perfiles, fragmentación TCP, reconexión, lecturas inválidas y cambio de juego. Las pruebas opcionales con ROMs propias se omiten cuando no existen archivos .gba en roms.

## Navegador y ejecutable

Se han comprobado Chromium 75 y Chromium actual: overlay transparente, seis slots, geometría 1920 × 1080 y ausencia de excepciones JavaScript. Las etiquetas de Inicio, Diseñador y vista previa permanecen por encima del fondo de muestra. Probar ROM acepta las cinco ROMs originales y distingue archivo incompleto, modificado y juego no reconocido; también muestra un error comprensible si falla la conexión.

Cerrar PokeStream se ha probado con el ejecutable: la web muestra el cierre, se libera el puerto y terminan los procesos PyInstaller; el reinicio funciona. El paquete ejecutable no incluye ROMs, emuladores, partidas ni cachés de recursos.

## Pendiente

- Validación completa con partidas reales de equipo, combate, capturas, evoluciones, medallas y todas las ubicaciones.
- Las cargas de savestate hacia delante pueden confundirse con progreso real. Desactivar alertas y recargar el script sigue siendo necesario.
- Pruebas dentro de todas las versiones de OBS: verificar motores de navegador no equivale a comprobar cada versión de OBS.
- Nintendo DS está planificado, sin implementación ni fecha confirmada.
- La configuración de GitHub Actions está preparada; su primera ejecución remota depende de publicar el repositorio.
