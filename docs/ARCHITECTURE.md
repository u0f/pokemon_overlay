# Arquitectura y contratos

`mGBA (Lua, solo lectura) → TCP 127.0.0.1:8766 → Python/FastAPI → estado validado → WebSocket → React / OBS`

Python es el cliente TCP: la llamada `socket.connect` de mGBA bloquea, mientras que el servidor Lua utiliza sockets no bloqueantes. Se acepta un solo cliente, se mantiene como máximo un mensaje pendiente y se omite una nueva muestra si el consumidor todavía no ha recibido la anterior. No hay bucles de espera ni escritura en RAM.

## Mensaje de memoria, protocolo 1

Una línea JSON ASCII terminada en LF, máximo 12 000 bytes. Modelo exacto: `backend/app/models.py:Wire`. Incluye `protocol`, cabecera de ROM (`code`, `crc32`, `revision`), secuencia, época de reset/conexión, fotograma, indicador ready y bloques binarios codificados como hexadecimal. Solo se admiten los bloques de la lista fija del bridge, nunca peticiones de direcciones arbitrarias. El único comando Python → Lua es `INTERVAL n\n`, 6–60 fotogramas.

Cada snapshot sirve de heartbeat; timeout de cuatro segundos. Se consulta a ~4 Hz por defecto. Los offsets internos se interpretan únicamente en Python. Las lecturas se realizan juntas al terminar un fotograma; checksums y longitudes detectan bloques corruptos. Cambiar ROM o resetear incrementa la época. CRC calculado al iniciar/resetear, no en cada fotograma.

## Estado normalizado

`State` y `Pokemon` son modelos Pydantic; el frontend usa `frontend/src/types.ts`. `null` significa no disponible, `0` es cero real y `connection=error` indica una lectura rechazada. En error/desconexión se conserva el último estado válido y su timestamp. Antes de cargar partida no se representa un equipo inexistente como una lectura correcta.

`identity=PID-OTID` mantiene la identidad durante evoluciones y cambios de slot. La especie usa ID interno Gen III, no número nacional; los huecos 252–276 se rechazan. Las extensiones de Esmeralda incluyen estado de combate, resultado, banderas, Pokédex y continuidad de tiempo. No se envían bytes de RAM al navegador.

La identidad usa valores del juego; no se puede garantizar unicidad entre clones. Duplicados dentro del equipo se rechazan de forma conservadora.

## API

- GET `/api/health`, `/api/state`, `/api/events`, `/api/diagnostics`
- GET/PUT `/api/settings`
- GET `/api/profiles`, PUT `/api/profiles/{id}`
- GET `/api/games` (perfiles reconocidos)
- POST `/api/shutdown` (cierre ordenado del lanzador)
- POST `/api/alerts/test` (no persiste en historial real)
- GET `/api/nuzlocke`, PUT `/api/nuzlocke/{id}` para confirmar/descartar
- POST `/api/runs` (conserva las runs antiguas)
- `/ws`: mensajes `state`, `test_alert`, `heartbeat`, `shutdown`; reconexión navegador automática.
- `/dashboard`, `/preview`, `/overlay?profile=default`

Perfiles definidos en coordenadas lógicas 1920×1080, reescaladas proporcionalmente. El tamaño de la fuente OBS debe coincidir con la resolución elegida. Coordenadas verificadas en servidor; JSON importado pasa por el mismo modelo que el editor. No se admiten scripts, HTML ni CSS arbitrario.

## Persistencia y concurrencia

SQLite en `data/pokestream.sqlite3`, modo WAL, con configuraciones, perfiles, eventos, run actual y muertes. Historial limitado a los últimos 5000 eventos para no crecer sin límite; registros Nuzlocke se conservan. Estado en RAM, no reanimado desde una partida anterior al iniciar.

Endpoints mutables y loop de lectura se ejecutan en el mismo event loop. Cada navegador tiene una cola de dos mensajes; uno lento no bloquea el lector. Alertas: cola frontend de hasta 20, ordenada por prioridad, duración configurable. No se reproduce el historial antiguo al conectar OBS.

## Límites de confianza

Servidor y bridge solo localhost. Host/Origin validados, mutaciones JSON, perfiles tipados y tamaños acotados. La API no sirve la carpeta del proyecto, ROMs ni partidas; solo los iconos locales en `data/assets/` y los ficheros estáticos compilados. No hay CORS abierto, telemetría ni servicios de terceros.

## Extensión futura

El decoder no depende de HTTP ni de React, y el bridge no sabe de componentes. Para un juego nuevo se requiere una nueva huella, mapa documentado, decoder y fixtures. En este MVP no existe todavía un cargador de plugins públicos; agregar adaptadores futuros no equivale a declarar compatibilidad.
