# Recursos y dependencias

El código de PokeStream se distribuye bajo la licencia MIT incluida en LICENSE. La interfaz utiliza formas geométricas y distintivos de medallas genéricos.

Nombres, tipos, ubicaciones e iconos de Pokémon se obtienen únicamente de la ROM aportada por el usuario, como caché local en `data/`. No se otorga licencia sobre esos recursos y no se incluyen en paquetes distribuidos. ROM, BIOS y emuladores de terceros también quedan fuera del ejecutable.

Dependencias principales: Python (PSF), FastAPI (MIT), Pydantic (MIT), Uvicorn (BSD-3-Clause), websockets (BSD-3-Clause), Pillow (HPND), React (MIT), Vite (MIT), TypeScript (Apache-2.0). Desarrollo: pytest (MIT), httpx (BSD-3-Clause), Vitest (MIT), Lupa (MIT). PyInstaller usa GPL con una excepción que permite distribuir aplicaciones compiladas bajo su propia licencia; conservar los avisos de sus componentes.

Las APIs y estructuras se han documentado a partir de fuentes enlazadas en MEMORY.md. Los ejemplos de mGBA se consultaron como documentación de su API; la implementación de bridge es independiente. No se incorporan árboles de código de terceros. `research/` contiene material consultado y queda excluido de distribución.

Para empaquetar una entrega pública, conserva los avisos de las dependencias instaladas, revisa las licencias de cualquier recurso adicional que añadas y excluye íntegramente `data/` y `mGBA-*/`.
