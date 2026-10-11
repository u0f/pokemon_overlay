# Pokémon GBA España: fuentes y mapas de memoria

## Revisión permitida

ROM aportada localmente: Pokémon - Edicion Esmeralda (Spain), 16 777 216 bytes.

- Código: BPES; revisión: 0; idioma GF: 7.
- SHA-1: `fe1558a3dcb0360ab558969e09b690888b846dd9`
- CRC32: `8c4d3108`
- Coincide con la entrada de `nointro.dat` incluida en mGBA 0.10.5.

El preparador verifica SHA-1 completo; el bridge verifica código, revisión y CRC32 del emulador. Los perfiles adicionales reconocidos se enumeran en backend/app/games.py y README.md. No se publica la ROM ni memoria capturada de una partida del usuario.

## Fuentes técnicas consultadas

1. [API oficial de scripting mGBA](https://mgba.io/docs/scripting.html): readRange/read8/read32, checksum, callbacks y socket. Los ejemplos `scripts/pokemon.lua` y `scripts/socketserver.lua` incluidos en la distribución 0.10.5 corroboran las firmas.
2. [Implementación de sockets mGBA 0.10.5](https://github.com/mgba-emu/mgba/blob/0.10.5/src/script/socket.c): sockets aceptados/listen no bloqueantes.
3. [Estructuras Gen III](https://github.com/pret/pokeemerald/blob/master/include/pokemon.h) y [cifrado/orden de subestructuras](https://github.com/pret/pokeemerald/blob/master/src/pokemon.c).
4. [SaveBlock1/2 y Pokédex](https://github.com/pret/pokeemerald/blob/master/include/global.h), [dinero y cambio de clave](https://github.com/pret/pokeemerald/blob/master/src/load_save.c), [redundancia Pokédex](https://github.com/pret/pokeemerald/blob/master/src/pokedex.c).
5. [Cabecera de Game Freak](https://github.com/pret/pokeemerald/blob/master/src/rom_header_gf.c): tablas y offsets, verificados contra los bytes de la ROM española.
6. [Mapa de símbolos](https://github.com/40Cakes/pokebot-gen3/blob/main/modules/data/symbols/pokeemerald.sym) y [correcciones por idioma](https://github.com/40Cakes/pokebot-gen3/blob/main/modules/data/symbols/patches/language/pokeemerald.yml). Este mapa mantiene las RAM listadas para español y cambia las tablas ROM: no se ha utilizado la dirección inglesa para nombres o ubicaciones.
7. [Banderas de medallas](https://github.com/pret/pokeemerald/blob/master/include/constants/flags.h), [gMain.inBattle](https://github.com/pret/pokeemerald/blob/master/include/main.h), [estructura de mapas](https://github.com/pret/pokeemerald/blob/master/include/global.fieldmap.h).

Las fuentes son evidencia estructural; **no reemplazan la validación empírica pendiente con una partida española**. Los tests sintéticos verifican interpretación, tamaños y errores, no prueban por sí mismos una dirección de RAM en ejecución.

## Direcciones bus (hexadecimal)

| Dato | Dirección / estructura | Verificación y prueba |
|---|---|---|
| Cabecera GBA | `080000AC` código, `080000BC` revisión | ROM local; guardas de identificación y tests de rechazo |
| Cabecera GF | `08000100` | Lectura de ROM local; assertions en prepare_rom |
| gPlayerPartyCount | `020244E9`, 1 byte | Mapa de símbolos + parches de idioma; test de seis slots |
| gPlayerParty | `020244EC`, 600 bytes | Mismas fuentes; fixture Lua y 24 permutaciones |
| gSaveBlock1Ptr | `03005D8C`, 4 bytes | Mapa + parches; se valida rango EWRAM antes de leer |
| gSaveBlock2Ptr | `03005D90`, 4 bytes | Mapa + parches; se valida rango EWRAM antes de leer |
| gMapHeader | `02037318`, 28 bytes | Mapa + parches; región en `+14`, grupo/número SB1 `+4/+5` |
| gMain.inBattle | `030026F9`, bit 1 | gMain `030022C0` + `439` (main.h) |
| gBattleOutcome | `0202433A`, 1 byte | Mapa + parches; 7=capturado, test de evidencia de captura |
| gBattleTypeFlags | `02022FEC`, 4 bytes | Mapa + parches; bit 3 combate de entrenador |

EWRAM: `02000000–0203FFFF`; IWRAM: `03000000–03007FFF`. El bridge lee únicamente los símbolos explícitos; punteros SB1/SB2 deben caber íntegramente en EWRAM.

## Offsets relativos

| Campo | Offset | Fuente |
|---|---|---|
| SB1 dinero | `490`, u32 XOR SB2 clave | global.h / load_save.c |
| SB1 flags | `1270`, 300 bytes | cabecera GF `+50` y estructura |
| Medallas | flags `867..86E` | constants/flags.h |
| SB1 seen1 / seen2 | `988` / `3B24`, 52 bytes | GF `+5C/+60` |
| SB2 nombre / ID | `0`, 8 bytes / `A`, u32 | GF `+A0/+9C` y global.h |
| SB2 reloj | `E`, u16 horas; `10/11`, minutos/segundos | global.h |
| SB2 clave | `AC`, u32 | global.h |
| SB2 Pokédex | `18`; owned `+10`, seen `+44` | GF `+58`, global.h |

Pokédex vistos = intersección de seen SB2, seen1 y seen2. Capturados = owned intersectado con vistos; solo primeros 386 bits. Se usa el comportamiento de validación de pokedex.c sin modificar memoria.

## Estructura Pokémon (100 bytes)

PID +0, OT ID +4; apodo +8 (10 bytes), flags +19 decimal, checksum +28 decimal. Bloque cifrado +32..79: doce u32 XOR `(PID ^ OT)`. Checksum: suma de los 24 u16 descifrados módulo 65536. El PID módulo 24 selecciona la posición de las cuatro subestructuras de 12 bytes. Especie en Growth +0, huevo en Misc +4 bit30. Estado +80, nivel +84, PS +86, máximo +88 (offsets decimales). Tests cubren las 24 permutaciones, truncado, corrupción, seis slots y PS cero.

## Catálogos e iconos locales

La cabecera GF de la ROM aporta nombres `0831E82C`, SpeciesInfo `08326688`, tabla de iconos `0857E784`, índices de paleta `0857EE64` y paletas `0857F01C`. El preparador obtiene los punteros de la propia cabecera, valida rangos, extrae nombre/tipos e iconos 4bpp de 32×32. La tabla española de ubicaciones es `085A41E4`, entradas de ocho bytes, 213 entradas, procedente del parche de idioma. Informe reproducible local: `data/rom-validation.json`.

Los iconos son de la ROM del usuario y solo se generan en su equipo. El ejecutable no los incorpora. Iconos alternativos y paletas shiny no implementados; la propiedad shiny sí se decodifica.

## Ampliación española, 11 de octubre de 2026

Registro único: `backend/app/games.py`. `scripts/sync_bridge_profiles.py` genera su tabla Lua; una prueba comprueba que ambas siguen sincronizadas. Los perfiles nuevos son experimentales: comprobados con memoria sintética, no con sus ROMs ni partidas reales todavía.

| Juego | Código | Revisión | CRC32 |
|---|---|---|---|
| Rubí | AXVS | 0 / 1 | eb0729cf / b980fff5 |
| Zafiro | AXPS | 0 / 1 | a04f5f0b / f2c88931 |
| Rojo Fuego | BPRS | 0 | 9f08064e |
| Verde Hoja | BPGS | 0 | 2ca11d59 |

SHA1 y CRC proceden del `nointro.dat` incluido por mGBA. El registro contiene los SHA1 completos. Se rechazan otras combinaciones; no se deduce compatibilidad del título del archivo.

Fuentes consultadas: estructuras [pokeruby/global.h](https://github.com/pret/pokeruby/blob/master/include/global.h), [pokefirered/global.h](https://github.com/pret/pokefirered/blob/master/include/global.h), sus `main.h` y `constants/flags.h`; símbolos y parches de idioma de [pokebot-gen3](https://github.com/40Cakes/pokebot-gen3/tree/main/modules/data/symbols). Para RS españoles se usa la selección `pokeruby_rev1`/`pokesapphire_rev1` y su parche `S`, como indica `modules/game.py`, incluso para revisión española 0. **Las direcciones de equipo españolas difieren de las inglesas.**

| Lectura | Rubí/Zafiro ES | Rojo Fuego/Verde Hoja ES |
|---|---|---|
| SB1 / SB2 | fijos 02025734 / 02024EA4 | punteros en 03004F58 / 03004F5C |
| Tamaño SB1 / SB2 | 3AC0 / 890 | 3D68 / F24 |
| Equipo / contador | 03004370 / 03004360 | 02024284 / 02024029 |
| Dinero SB1 / clave SB2 | 490 / sin cifrar | 290 / F20 |
| Flags / primera medalla | 1220 / 807 | EE0 / 820 |
| Seen1 / seen2 en SB1 | 938 / 3A8C | 5F8 / 3A18 |
| MapHeader | 0202E828 | 02036DFC |
| Main.inBattle (bit 1) | 03001BAD | 03003479 |
| Resultado / flags combate | 02024D26 / 020239F8 | 02023E8A / 02022B4C |

Todos los valores de la tabla son hexadecimales. Nombre, reloj, ID, Pokédex y estructura Pokémon comparten formato. El protocolo mantiene `save2` de B0 bytes y añade `money_key` u32 para FRLG, evitando transmitir todo el bloque hasta F20. Esmeralda sigue aceptando el protocolo del script anterior; FRLG exige la clave explícita.

Catálogos nuevos: `data/catalogs/<sha1>.json`, iconos `/assets/<sha1>/<especie>.png`. Se conserva lectura del catálogo antiguo de Esmeralda. Se verifican SHA1, cabecera GF y offsets antes de extraer. RS omite el puntero SpeciesInfo en GF: se exige una única coincidencia de los prefijos de estadísticas/tipos de Bulbasaur e Ivysaur separados por 28 bytes. Las tablas GF y esa búsqueda se prueban con fixtures sintéticos; también se ha comprobado la extracción real de las cinco ROMs españolas indicadas en README.md. Un fallo deja un diagnóstico y no afecta al catálogo de Esmeralda.

Ubicaciones españolas: Rubí 083EB370, Zafiro rev. 0 083EB0AC y rev. 1 083EB0A4 (88 entradas de 8 bytes); Rojo Fuego 083EBF80, Verde Hoja 083EBDBC (109 punteros, índice de sección desde 58 hex). Las direcciones de ubicaciones proceden de los respectivos parches españoles de símbolos.


## Correcciones verificadas en ROMs reales — 11 de octubre de 2026

Zafiro España rev. 0 (SHA1 3a6489189e581c4b29914071b79207883b8c16d8): tabla de ubicaciones 083EB0AC, no 083EB0A4. Verde Hoja España rev. 0 (SHA1 f9ebee5d228cb695f18ef2ced41630a09fa9eb05): 083EBDBC, no 083EBDB8. Se verificaron las cinco extracciones completas y datos iniciales de partidas en mGBA; los pendientes de ROMs de la sección anterior son históricos. Rubí rev. 0 y Zafiro rev. 1 siguen sin ROM real disponible. FC00 es NAME_END (sin argumento) en texto RS; FD08 en el nombre de la guarida se resuelve según MAGMA/AQUA.
