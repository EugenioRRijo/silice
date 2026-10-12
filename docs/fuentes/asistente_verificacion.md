# Verificación de datos externos del asistente de IA (S4.0, tarea 3)

Una fila por dato, con valor, fuente y fecha. Verificado el 2026-10-12 por el ejecutor de la tarea 3
con las fuentes públicas citadas. «No comprobado» significa que ningún dato se inventó en su lugar.

| Dato | Valor | Fuente | Fecha | Destino |
|---|---|---|---|---|
| Modelo `claude-opus-5-5`: precios (USD por millón de fichas) | entrada 4; salida 20; escritura de caché 5m 5; lectura de caché 0,20 | https://platform.claude.com/docs/en/about-claude/pricing (fila «Claude Opus 5.5») | 2026-10-12 | `asistente/precios_ia.json` (fecha_verificacion 2026-10-12) |
| Id del modelo en la API (`GET /v1/models/claude-opus-5-5`) | no comprobado (requiere clave de API; lo hace la prueba manual de la tarea 13) | — | — | — |
| Esfuerzo por defecto `medium`, `tool_choice` forzado = 400, `strict: true`, palabras clave de JSON Schema admitidas, `fallbacks` | no comprobado contra la documentación vigente; se conservan los valores del plan y la tarea 11 los relee | skill `claude-api` (caché del 2026-09-25) | — | `NO_ADMITIDAS_EN_ESTRICTO` (tarea 11) |
| Beta del Tool Runner (S4 §4, enfoque B) | no comprobado; decisión RS4-2 ya tomada | — | — | — |
| SDK `anthropic` | 1.13.0 instalada; licencia MIT; `pyproject.toml` pide `>=1.0` | `importlib.metadata` del entorno | 2026-10-12 | `pyproject.toml` (sin cambio) |
| Cliente `ollama` para Python | 0.6.3; licencia MIT; anfitrión por defecto `http://127.0.0.1:11434` (puerto 11434, a confirmar en el equipo con `GET /api/version`) | `importlib.metadata`; el puerto, documentación de Ollama (no recargada hoy) | 2026-10-12 | bitácora |
| Versión mínima de Ollama | **0.35.0**: corrige CVE-2026-103663 (recorrido de rutas en `/api/pull`, ejecución remota de código, CVSS 9,4, publicado 2026-10-08; afectadas las anteriores a 0.35.0). Antes: CVE-2026-7482 corregida en 0.17.1; CVE-2024-37032 corregida en 0.1.34. El repositorio de Ollama no publica avisos en su pestaña de seguridad, así que la fuente es el registro de CVE | https://app.opencve.io/cve/CVE-2026-103663 ; https://thehackernews.com/2026/05/ollama-out-of-bounds-read-vulnerability.html | 2026-10-12 | `asistente/config_ia.json` |
| Modelo local candidato (Ollama) | **muse-glimmer**: 30B, licencia Apache 2.0 y capacidad `tools` según el listado de ollama.com. Salida restringida a un esquema, ventana de contexto, segundos por turno, memoria y **calidad en español: no comprobados** (no hay Ollama en el equipo del ejecutor). 30B puede exceder el equipo de una PYME | https://ollama.com/search?c=tools | 2026-10-12 | `protocolo.json::modelo_local` |
| `keyring` | 25.7.0, licencia MIT; backend `WinVaultKeyring` en Windows 11; ida y vuelta y borrado: sí. Comportamiento sin sesión de usuario: no comprobado | `uv run python scripts/explorar_ia.py keyring` | 2026-10-12 | bitácora; respaldo cifrado (RS4-8) |
| Retención y uso de los datos del proveedor | no comprobado (política vigente por leer y fechar al escribir el manual, tarea 16) | — | — | `docs/manual_usuario.md` |

## Decisiones que quedan para Eugenio y el tutor

- El modelo local queda como **candidato sin probar**: hasta que se corra
  `scripts/explorar_ia.py ollama --modelo muse-glimmer` en un equipo de PYME y se mida su calidad en español con el
  banco de desarrollo, el modo local es «solo para pruebas» (S4 §8.6) y RF‑90 (b) no se da por cumplido en silencio.
- `estructurado` queda en `false` (se asume llamada a herramientas); cambia a `true` si la exploración muestra lo contrario.
