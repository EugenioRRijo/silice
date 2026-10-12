# Plan de construcción de Sílice 0.8.0

> **Para quien ejecute (agentes):** SUB-SKILL REQUERIDA: `superpowers:subagent-driven-development`
> (un subagente por tarea con su ficha de rol `C:\Users\euger\.claude\agents\sf-*.md` y un revisor
> fresco por tarea). Los pasos usan casillas `- [ ]`. Cada tarea lleva su prueba primero, con el
> rojo observado (NORMAS §5).

**Objetivo:** entregar la 0.8.0 de Sílice, que es **S3: el auditor y el paquete**. Cada persona
entra con su cuenta y su rol; toda versión que se guarda queda **sellada en una cadena de huellas**
a nombre de quien la confirmó; una empresa **firma** el paquete con su clave Ed25519; el paquete
`.silice` (formato v1, con anexos) viaja a otra empresa, que lo **verifica** (formato, integridad,
autenticidad, cadena, anterioridad), **reaudita** con sus propias reglas y listas, **compara** con
la entrega anterior y **dictamina**; la misma reauditoría se ofrece por la API (`POST
/v1/auditorias`). Además la auditoría de planos gana el archivo DXF dañado, los requisitos IDS del
IFC, R15 (coherencia geométrica) y R16 (contraste entre dos fuentes con el costo de la diferencia),
y, si el tiempo alcanza, RF-100 (variaciones atípicas de precio).

**Arquitectura:** ocho fases, de las cuales S3-1 y S3-5 son carriles sin núcleo y S3-2 es el único
carril de núcleo.
- **S3-0 (docs, sin núcleo):** licencia de `ifctester` (tarea 1); la parte S3 de la meta única
  (`scripts/meta_silice_s3.py`), la ERS (UC-21 a UC-23, RF-80 a RF-89, RF-100, RNF-16, RNF-17), el
  catálogo de errores de planos, la memoria de diferencias, los dos protocolos de medición con su
  huella, el conjunto exacto de OF-001 limpio y los expedientes SL-E7, SL-E8, SL-E9 y SL-E12
  (tarea 2).
- **S3-1 (seguridad, sin núcleo):** la base de la instalación (`seguridad/`, `ins_0001_seguridad`),
  el lector JSON estricto y `secretos` (Argon2id a AES-GCM), roles, cuentas, sesiones, bloqueo y
  freno global, red local, y la interfaz de acceso con la matriz de roles (tareas 3 a 6).
- **S3-2 (núcleo, SL-E8, SL-E7, SL-E12, SL-E9):** documento canónico, cadena de huellas sellada en
  el embudo, WAL y `BEGIN IMMEDIATE`, diferencia entre versiones y `revalorar` (tareas 7 a 10).
- **S3-5 (planos, sin núcleo):** auditoría del DXF, IDS del IFC y R15 (tarea 11); R16, su costo, el
  sembrador de errores y la medición de detección (tarea 12).
- **S3-3 (paquete):** firma y empresas (13), formato y anexos (14), exportar y verificar (15), la
  pantalla Entregar (16), Administración (17) y los llamadores con `usuario` y responsable (18).
- **S3-4 (revisión):** reauditoría y vista del revisor (19), la pantalla Revisar (20) y la API de
  auditorías (21).
- **S3-6 (opcional):** RF-100 (22). **S3-7 (cierre):** arquitectura, documentos y CI (23); versión
  0.8.0, acceso encendido, base de prueba, manuales y compuerta GS3 (24).

**Tecnología:** Python 3.13, `uv`, SQLAlchemy 2.0, Alembic >= 1.20, Streamlit 1.62 (`AppTest`),
FastAPI, `argon2-cffi` 25.1, `cryptography` 50, `ezdxf` 1.4, `shapely` 2.1 (extra `planos`),
`ifctester` 0.8.5 con `xmlschema` (extra `ifc`), `Decimal` (prec 28, ROUND_HALF_EVEN). Las
dependencias ya están declaradas por A2 de la 0.6.0; S3 no agrega ninguna.

**Specs:** maestro `docs/especificaciones/2026-10-11-silice-1.0.0-design.md` (RV-1 a RV-26, §4, §5,
§6, §9), S3 `docs/especificaciones/2026-10-11-silice-s3-auditor-paquete-design.md` y horizonte
`docs/especificaciones/2026-10-08-horizonte-reorientacion-design.md` (§5.1, §6.1). Todos fueron
aprobados por Eugenio el 2026-10-11. El plan cita los specs por sección y no los repite.

**Cómo se verificó este plan.** El código de cada tarea sale de un sandbox: una copia de
`origin/main` con A, B y los cambios de este plan, donde la suite entera pasa con `-W error` (3 662
pruebas: 3 656 verdes, una omitida por un extra ausente y cinco que dependen de git o de extras no
instalados en ese entorno: `anthropic`, `keyring`, `ollama`, `sentence_transformers` y el historial
de git de `test_meta_silice`; ninguna es de S3). Como la
0.6.0 y la 0.7.0 todavía no estaban fusionadas, el sandbox lleva **stubs mínimos** de S1 y de S2
(tablas y funciones nombradas en «Supuestos sobre 0.6.0 y 0.7.0»). Todo lo que S3 dice de ellas se
prueba contra el stub; la costura real se cierra en la tarea 24, que corre la suite sobre la
0.7.0 verdadera.

**Convención de líneas largas.** Este plan se escribe a 100 columnas. En los bloques de Markdown
(ERS, bitácora, protocolos, catálogo de errores), una línea que empieza con `↳ ` **continúa la
anterior**: al pegarla en el archivo se une con la anterior sin ese signo y sin salto de línea. Un
bloque `diff` sobre un `.md` sigue la misma regla con el prefijo `+`, `-` o espacio delante.

## Restricciones globales

- **Condición de entrada:** la 0.7.0 está fusionada y etiquetada (`v0.7.0`) con su base de prueba, y
  `main` local es `origin/main`. Las firmas que S3 consume están en «Supuestos sobre 0.6.0 y
  0.7.0»; si una no existe tal cual, la tarea que la consume se detiene y se registra, no se
  improvisa otra. S3-1 y S3-5 pueden adelantarse desde `main` antes de la 0.7.0 con el acceso
  apagado (RP8-4); S3-2 espera a S2-3.
- `core/contracts/` no se toca: `git diff v0.7.0..HEAD -- core/contracts/` debe quedar vacío.
- `core/` solo cambia en las ramas `inc/080-s3-2-nucleo` (tareas 7 a 10). Esa rama toca solo
  `core/`, `migraciones/`, `tests/`, `docs/` y `scripts/` (los sembradores y medidores, que pasan
  `usuario`); nunca `ui/`, `adapters/`, `ml/` ni `api/`. Cada uno de sus cuatro expedientes (tarea
  2) se commitea antes del código que cubre y necesita el visto bueno del tutor antes de abrir la
  rama. Nunca hay dos ramas de núcleo abiertas.
- `seguridad/` y `paquete/` no importan `ui`, `api` ni Streamlit. `paquete/` importa `core.budget`
  y `seguridad`; `core/` no importa `seguridad`, `paquete`, `auditoria`, `ui` ni `api`. Lo vigila
  `tests/unit/test_arquitectura.py` y `test_arquitectura_s3.py`.
- `main` es la única rama de integración. Las ramas son cortas, por fase, salen de `origin/main` del
  momento y abren su PR contra `main`. Se fusionan con `gh pr merge <n> --merge` (merge commit,
  nunca *squash*: C3 de la meta lee el orden prueba, implementación) al cruzar su compuerta.
- Todo texto ajeno (nombres de empresa, de archivo, de hoja, notas del dictamen, descripciones de
  hallazgos del paquete) se muestra por `ui.texto_seguro.texto_seguro()` o en celdas; nunca
  `unsafe_allow_html` (RV-14; la meta lo vigila en `S3-M3`).
- Un secreto (contraseña, clave privada, ficha de sesión, clave de API) no se escribe en la base,
  en el registro, en un mensaje ni en un log en claro. Se guardan huellas.
- Cero pruebas omitidas (`scripts/verificar_omitidas.py`), `pytest -W error`, ruff limpio solo
  sobre los archivos tocados (nunca `ruff format .` en todo el repositorio; 100 columnas) y
  `scripts/guardia_nucleo.py --base origin/main`.
- La suite corre sin red: solo 127.0.0.1 y ::1, con `HF_HUB_OFFLINE=1`. La API de pruebas usa
  `base_url="http://127.0.0.1"` porque `TrustedHostMiddleware` rechaza `testserver` (RP8-12).
- Prohibido `pkill`, `taskkill`, `git add -A` y matar procesos ajenos. **Nadie toca
  `data/apu.db`**; las pruebas usan SQLite en memoria o bases en `tmp_path`. Los casos de prueba
  y todos los datos de OF-001, MIN-001 y de los paquetes son **ficticios** (NORMAS §1).
- Comandos: `unset VIRTUAL_ENV; uv sync --all-extras` antes de pytest; `uv run pytest -q -W error`;
  `uv run ruff check <archivos>`; `uv run python scripts/guardia_nucleo.py --base origin/main`.
- Commits convencionales en español, asunto sin tildes, con el trailer final
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (en los bloques, un segundo `-m`).
  Los PR terminan con `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- Las bitácoras y los specs anteriores al 2026-10-11 son historia y no se editan.

## Rulings propios del plan (RP8-n, 2026-10-11)

Al llevar el spec al código aparecieron decisiones que el spec no fija. Se ratifican aquí con el
valor que el código ya prueba; cada una tiene su prueba en la tarea dueña.
- **RP8-1:** `ifctester` pide `bcf-client` (GPLv3). Vive solo en el extra `ifc`; el instalador de S5
  no lo incluye; el producto importa de él únicamente `ifctester.ids`, dentro de una función, y
  nunca `bcf` ni `ifctester.reporter` (guardia por AST). Sin el extra el informe lo dice (T1, T11).
- **RP8-2:** el lector estricto de JSON ajeno es `seguridad/json_estricto.py` (no `paquete/`):
  lo usan `paquete`, `auditoria` y `api`. `core` no lo puede importar, así que `canonico.leer`
  recibe el objeto ya leído y valida cada cifra con el **mismo** patrón, que una prueba compara (T4,
  T7).
- **RP8-3:** la moneda del proyecto de una versión es la última conversión hecha hasta ella (por
  orden de creación, no por fecha) o, si no hay, la primera declaración si ya existía a su fecha:
  ni una conversión ni una declaración posteriores cambian una versión ya sellada (T7).
- **RP8-4:** `SILICE_ACCESO` es el interruptor de transición. Apagado (por omisión hasta GS3),
  `sesion_actual` da un usuario de desarrollo con todos los roles y nada pide entrar; la suite lo
  fija en `0` y las pruebas de S3 lo encienden. La tarea 24 cambia el valor por omisión a `1` (T6,
  T24).
- **RP8-5:** el conjunto exacto de OF-001 limpio es un **literal** en
  `tests/fixtures/errores_planos/of001_limpio.py`: 15 ítems de importación y 8 hallazgos de R8 del
  DXF (R9, R10 y R15 no dan ninguno), y lo mismo del IFC de oficina de `planos_ifc_ids` (OF-001 no
  tiene IFC). Lo regenera `medir_deteccion_planos.py --limpio`; cambiarlo a mano cambia el oráculo
  (T2, T12).
- **RP8-6:** `auditoria/` es un paquete propio (`reauditoria`, `servicios`): la API no puede
  importar `ui/`, y la vista del revisor y la API deben usar el mismo motor (T19).
- **RP8-7:** `shapely` solo propone candidatos (índice espacial en coma flotante); cada medida y
  cada decisión de R15 y R16 es `Decimal` (DA-S3-6) (T11, T12).
- **RP8-8:** la versión se sella en un evento `before_commit` de la transacción **raíz**, ignorando
  los savepoints; `guardar_presupuesto` solo la marca «por sellar». Una prueba de la suite instala
  un usuario de prueba en el embudo (marcador `sin_usuario_por_omision` para los que no lo quieren)
  (T8).
- **RP8-9:** R16 es siempre ADVERTENCIA: si dos fuentes difieren, una está desactualizada y R16 no
  sabe cuál. Emparejadas a <= 0,10 m; desplazadas a <= 1,00 m; más lejos, faltante y sobrante (T12).
- **RP8-10:** SL-E12 usa la opción de ejecución `silice_inmediata` para emitir `BEGIN IMMEDIATE`,
  con `isolation_level = None`, WAL y `busy_timeout = 5000` (T9).
- **RP8-11:** `POST /v1/auditorias` exige `fecha_evaluacion` en el cuerpo: R11 y R12 no usan el
  reloj (M §3.3) (T21).
- **RP8-12:** la clave de API viaja en la cabecera `X-Silice-Clave`; el tope del cuerpo es 20 MiB y
  los hosts permitidos son los del equipo (`TrustedHostMiddleware`) (T21).
- **RP8-13:** las cifras del documento canónico admiten 20 enteros y 28 decimales
  (`^-?[0-9]{1,20}(\.[0-9]{1,28})?$`) y se escriben con `format(valor, "f")`, nunca con exponente
  (T7).
- **RP8-14:** quien solo revisa no ve ninguna pantalla de Trabajo (matriz de S3 §5.1); el recorrido
  guiado omite los pasos de pantallas que el rol no ve (T6, T20).
- **RP8-15:** «Entregar paquete» es una pantalla de la sección Trabajo (UC-22), no un botón de la
  barra: la barra escribe en la hoja y solo la ve quien puede editarla (T6, T16).
- **RP8-16:** las revisiones de caso de S3 (`caso_0007_s3_cadena`, `caso_0008_s3_paquete`) crean sus
  tablas con `crear_o_verificar` y `TablaCongelada`, porque `preparar_base` puede llegar a una base
  creada con `create_all` (T8, T14).
- **RP8-17:** `SesionActiva` lleva `usuario` (texto «Nombre <login>») además del usuario ORM, para
  que el responsable se pueda escribir sin tocar la base (T5).
- **RP8-18:** el protocolo del indicador de quien revisa usa **dos entregas paralelas** (P y Q) de 5
  diferencias cada una, una por tipo de SL-E9, para que lo aprendido en una condición no regale la
  otra; la lista de 10 se congela con su SHA-256 antes de medir (T2).
- **RP8-19:** las comprobaciones avanzadas de la meta cuentan solo filas de S3 hasta que la 0.6.0 y
  la 0.7.0 cierren sus fases; S3-M5 (las ramas de planos y atípicos no tocan `core/`) queda
  PENDIENTE mientras no haya ramas fusionadas (T2).
- **RP8-20:** SL-E7 hace obligatorio el `usuario` al confirmar. Las ramas de S3-2 (tareas 7 a 10) y
  de S3-3 (tareas 13 a 18, que cablean los llamadores) **se apilan y se fusionan seguidas**, sin
  etiqueta intermedia: entre las dos, `main` guarda versiones sin usuario en la interfaz y no se
  instala. La suite no lo nota porque la sesión de pruebas instala un usuario (RP8-8).
- **RP8-21:** `servicios_de_la_instalacion` (referencia MaPreX, tasas y erosión) y la entrada
  `reglas_de_control` de S2 se **inyectan**: la API y la vista usan los de esta instalación, y las
  pruebas los sustituyen. R13 y R14 desde un anexo de control quedan apagadas hasta que S2 entregue
  el servicio que reconstruye su instantánea desde `anexos/control.json` (T19).
- **Para Eugenio:** (a) las cifras de bloqueo (5 fallos, 15 min, freno de 20 en 10 min), de sesión
  (30 min, 12 h) y de claves (Argon2id m = 64 MiB, t = 3, p = 4) son supuestos declarados (RS3-2);
  (b) la red local va sin TLS en la 0.8.0 con las condiciones de S3 §5.6 y el riesgo de reanudación
  de sesión que la bitácora declara (RS3-8); (c) incluir el extra `ifc` en el instalador depende de
  un dictamen sobre `bcf-client` (RP8-1); (d) revocar una clave invalida todos sus paquetes (RS3-7).
  Nada de esto bloquea la 0.8.0; todo queda declarado en pantalla y en la bitácora.

## Supuestos sobre 0.6.0 y 0.7.0

Lo que S3 consume de S1 y S2, con la firma que sus planes declaran. El sandbox de este plan lo
reemplazó por un stub mínimo; la tarea 24 lo cotejó con la rama real.

- **S1, tablas** (`core/models/moneda.py`, revisiones `caso_0002` a `caso_0004`):
  `MonedaProyecto(id, proyecto_id, moneda, desde, version_id, responsable, fuente)`,
  `PrecioOrigen(precio_id, moneda_original, precio_original, fecha_precio, tasa, fecha_tasa,
  fuente_tasa, fuente)`, `ListaEmpresa(lista_id, empresa_nombre, empresa_rif, lista_base_id,
  lista_referencia_id, plazo_vigencia_dias, rango_inferior, rango_superior)`, y las de reajuste que
  viajan en `anexos/reajuste.json` (`TABLAS_DE_REAJUSTE` en `paquete/anexos.py`).
- **S1, funciones:** `core.catalog.origen.origenes_efectivos(session, lista) -> dict[int,
  OrigenEfectivo]` con `OrigenEfectivo(moneda_original, precio_original, fecha_precio, tasa,
  fecha_tasa, fuente_tasa, fuente)`; `core.catalog.indices.{LADO_POR_DEFECTO, TasaNoDisponible,
  tasa_aplicable}`; `core.catalog.moneda.erosion(precio, moneda, tasa_precio, tasa_evaluacion)`;
  `core.catalog.empresa.{PLAZO_VIGENCIA_DIAS, RANGO_INFERIOR, RANGO_SUPERIOR, es_heredado,
  lista_de_referencia}`; `core.verification.precios.{InstantaneaPrecios, PartidaPrecios,
  PrecioAuditado, reglas_precios}` (R11 y R12); `core.models.{SerieIndice, ImportacionIndice,
  ValorIndice, ALCANCE_REFERENCIA}`; `ui.texto_seguro.texto_seguro`.
- **S2, tablas** (`core/models/control.py`, revisiones `caso_0005` y `caso_0006_s2_decision`, la
  última revisión de caso antes de S3): las de `TABLAS_DE_CONTROL` en `paquete/anexos.py`.
- **S2, funciones:** `core.budget.valuaciones.anexo_control(session, proyecto_nombre) -> dict` (el
  anexo que S2 deja listo) y `core.verification.valuaciones.reglas_de_control(instantanea) ->
  tuple[ReglaVerificacion, ...]` (R13 y R14 sobre tipos puros). **Discrepancia:** S3 pide
  `(documento, anexo, fecha) -> reglas` y S2 entrega `(instantanea) -> reglas`; falta el puente que
  reconstruye la instantánea desde el JSON del anexo. Hasta entonces el parámetro
  `reglas_de_control` de `servicios_de_la_instalacion` es `None` y R13 y R14 no corren desde un
  paquete (RP8-21).
- **Cadena de Alembic:** `caso_0007_s3_cadena` cuelga de `caso_0006_s2_decision`; si S2 deja otra
  cabeza, cambia el `down_revision` de esa migración y nada más.
- **Meta:** `scripts/meta_silice.py` ya trae `FASES`, `Parte`, `ParTDD`, `Comprobacion`, `Contexto`,
  `partes()` y `_git` (A4); S3 agrega solo `FASES["0.8.0"]` y su parte.
- **S4** (futuro): `ui/entrega.py` acepta `ia: bytes | None` para el anexo `anexos/ia.json`; la
  firma de `secretos.cifrar` de S3 es `cifrar(secreto, contrasena, *, huella_publica) ->
  SecretoCifrado` (el plan de S4 la supone `cifrar(secreto, contrasena, *, asociado) -> bytes`; ver
  «Discrepancias»).

## Orden y ramas

| Orden | Rama | Tareas | Condición |
|---|---|---|---|
| 1 | `inc/080-s3-0-docs` | 1 a 2 (GS3-0) | 0.7.0 fusionada y etiquetada |
| 2 | `inc/080-s3-1-seguridad` | 3 a 6 (GS3-1) | S3-0 fusionada; sin núcleo; acceso apagado |
| 2' | `inc/080-s3-5-planos` | 11 y 12 (GS3-5) | sin núcleo; la 12 espera a la tarea 10 |
| 3 | `inc/080-s3-2-nucleo` | 7 a 10 (GS3-2) | S2-3 cerrada; aval del tutor de SL-E8, E7, E12, E9 |
| 4 | `inc/080-s3-3-paquete` | 13 a 18 (GS3-3) | pila sobre la rama 3 (RP8-20) |
| 5 | `inc/080-s3-4-revision` | 19 a 21 (GS3-4) | S3-3 fusionada |
| 6 | `inc/080-s3-6-atipicos` | 22 (GS3-6) | opcional; sin núcleo; es lo primero que cae |
| 7 | `inc/080-s3-7-cierre` | 23 a 24 (GS3) | todo lo anterior; etiqueta `v0.8.0` |

S3-1 y S3-5 son independientes y pueden ir en paralelo. **Orden de caída:** S3-6 (RF-100) primero;
luego el contraste con la base del revisor (queda la entrega anterior); la ruta de la API (queda
solo el Excel). Cuentas, cadena, firma, paquete con anexos y reauditoría no se recortan.

---

# S3-0 — Licencia, meta, ERS, oráculos, protocolos y expedientes (rama `inc/080-s3-0-docs`)

Sin núcleo y sin código de producto: documentos, oráculos escritos a mano y la parte S3 de la meta.
Sale de `origin/main` con la 0.7.0 fusionada y etiquetada. Al terminar, la ERS define lo que se
construye, los números que fijan la huella y las diferencias están escritos antes del código, los
dos protocolos de medición tienen su huella, y los cuatro expedientes de núcleo esperan el visto
bueno del tutor.

### Tarea 1: Licencia de `ifctester` y de `bcf-client` (RP-6, RP8-1)

**Rama:** `inc/080-s3-0-docs` (sale de `origin/main`; PR a `main`)   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `docs/licencias_ifc.md`
- Prueba: `tests/unit/test_licencia_ifc.py`

**Interfaces:**
- Consume: `pyproject.toml` con el extra `ifc = ["ifctester>=0.8.5,<0.9"]` y las dependencias base
  (A2 de la 0.6.0); las distribuciones `ifctester`, `bcf-client`, `xmlschema`, `shapely` y `ezdxf`
  instaladas por `uv sync --all-extras`.
- Produce: la guardia por AST de que el producto no importa `bcf` ni `ifctester.reporter`, y el
  documento de licencias que la prueba compara con las distribuciones instaladas.

La decisión (RP8-1) es de Eugenio y de su dictamen: el plan solo deja la prueba que la vigila.
`ifctester` es LGPLv3+ y exige `bcf-client` (GPLv3); instalar el extra `ifc` deja un paquete GPLv3
en el entorno. Mientras no haya dictamen, el instalador de S5 no lo incluye y el producto importa
solo `ifctester.ids` dentro de una función.

- [ ] **Paso 1: Escribir la prueba que falla**
**`tests/unit/test_licencia_ifc.py`**
```python
"""La licencia de `ifctester` y de `bcf-client` frente a la licencia propietaria del producto
(RP-6; spec S3 §11.2). El fallo de cualquiera de estas pruebas obliga a releer
`docs/licencias_ifc.md` antes de seguir: no se arregla cambiando la prueba."""

from __future__ import annotations

import ast
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DOCUMENTO = RAIZ / "docs" / "licencias_ifc.md"
CARPETAS_DE_PRODUCTO = ("adapters", "api", "auditoria", "core", "migraciones", "ml", "operacion",
                        "paquete", "scripts", "seguridad", "ui")
#: Lo que de `ifctester` el producto NO puede importar: arrastra `bcf-client` (GPLv3).
PROHIBIDOS = ("bcf", "ifctester.reporter")


def _extras() -> dict[str, list[str]]:
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(texto)["project"]["optional-dependencies"]


def _importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
            nombres.update(f"{nodo.module}.{a.name}" for a in nodo.names)
    return nombres


def test_ifctester_solo_vive_en_el_extra_ifc_y_no_en_las_dependencias_base() -> None:
    proyecto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not any(r.startswith("ifctester") for r in proyecto["dependencies"])
    donde = [extra for extra, requisitos in _extras().items()
             if any(r.startswith("ifctester") for r in requisitos)]
    assert donde == ["ifc"]


def test_el_producto_no_importa_bcf_ni_el_reporte_bcf_de_ifctester() -> None:
    encontrados = []
    for carpeta in CARPETAS_DE_PRODUCTO:
        for ruta in (RAIZ / carpeta).rglob("*.py"):
            for nombre in _importados(ruta):
                if any(nombre == p or nombre.startswith(p + ".") for p in PROHIBIDOS):
                    encontrados.append(f"{ruta.relative_to(RAIZ).as_posix()}: {nombre}")
    assert encontrados == []


def test_la_guardia_de_licencia_ve_las_formas_de_importar_bcf(tmp_path: Path) -> None:
    for fuente in ("import bcf\n", "from bcf.v2.bcfxml import BcfXml\n",
                   "from ifctester.reporter import Bcf\n", "from ifctester import reporter\n"):
        archivo = tmp_path / "x.py"
        archivo.write_text(fuente, encoding="utf-8")
        assert any(n == p or n.startswith(p + ".") for n in _importados(archivo)
                   for p in PROHIBIDOS), fuente
    archivo.write_text("from ifctester import ids\n", encoding="utf-8")
    assert not any(n == p or n.startswith(p + ".") for n in _importados(archivo)
                   for p in PROHIBIDOS)


def _licencia(distribucion: str) -> str:
    datos = metadata.metadata(distribucion)
    clasificadores = [c for c in datos.get_all("Classifier", []) if c.startswith("License")]
    declarada = datos.get("License-Expression") or datos.get("License") or ""
    return " | ".join([declarada, *clasificadores])


def test_el_documento_de_licencias_dice_lo_que_dicen_las_distribuciones_instaladas() -> None:
    """Si una versión nueva cambia la licencia, la prueba falla y se vuelve a decidir."""
    texto = DOCUMENTO.read_text(encoding="utf-8")
    esperado = {
        "ifctester": ("LGPLv3+", "Lesser General Public License v3"),
        "bcf-client": ("GPLv3", "General Public License v3 (GPLv3)"),
    }
    for distribucion, (en_documento, en_metadatos) in esperado.items():
        assert f"{distribucion} {metadata.version(distribucion)}" in texto, distribucion
        assert en_documento in texto
        assert en_metadatos in _licencia(distribucion), distribucion


@pytest.mark.parametrize("distribucion", ["xmlschema", "shapely", "ezdxf"])
def test_los_demas_terceros_nuevos_de_s3_tienen_licencia_permisiva(distribucion: str) -> None:
    licencia = _licencia(distribucion)
    assert any(clave in licencia for clave in ("MIT", "BSD")), (distribucion, licencia)
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_licencia_ifc.py -v -W error`
Esperado: 1 FAIL, `test_el_documento_de_licencias_dice_lo_que_dicen_las_distribuciones_instaladas`
con `FileNotFoundError: ... docs/licencias_ifc.md`; las demás pasan (el extra ya está declarado y
el producto todavía no importa `bcf`).
```bash
git add tests/unit/test_licencia_ifc.py
git commit -m "test(licencias): guardia de la licencia de ifctester y bcf-client en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima** — el documento de licencias (verificado con el entorno
  bloqueado por `uv.lock` el 2026-10-11; si una versión instalada difiere, se corrige el número
  aquí, no la prueba):
**`docs/licencias_ifc.md`**
```markdown
# Licencias de `ifctester` y de `bcf-client` (RP-6, S3-0)

Sílice es propietaria con todos los derechos reservados (P9). `ifctester` (la validación de IDS
del IFC, S3 §11.2) arrastra una dependencia con copyleft fuerte. Este documento fija qué se
sabe, qué se decide y qué prueba lo vigila. **No es asesoría legal**: la decisión de incluir el
extra `ifc` en el instalador queda a Eugenio, con el dictamen que él consiga.

## Lo verificado (2026-10-11, entorno bloqueado por `uv.lock`)

| Distribución | Versión | Licencia declarada en sus metadatos | Quién la pide |
|---|---|---|---|
| ifctester 0.8.5 | 0.8.5 | LGPLv3+ (`GNU Lesser General Public License v3 or later`) | el extra
↳ `ifc` |
| bcf-client 0.9.0 | 0.9.0 | GPLv3 (`GNU General Public License v3 (GPLv3)`) | `ifctester`
↳ (dependencia dura) |
| xmlschema | 4.3.2 | MIT | `ifctester`; también lo usa `esquema_sin_red` |
| shapely | 2.1.2 | BSD 3-Clause | extra `planos` (R15) |
| ezdxf | 1.4.4 | MIT | extra `planos` (auditoría del archivo DXF) |

`ifctester/reporter.py` importa `bcf.v2.bcfxml` **solo dentro de `Bcf.report`** (la salida de
informes en formato BCF); `ifctester.ids` (abrir un IDS y validar un modelo) no la importa. Aun
así `pip` instala `bcf-client` junto con `ifctester`, así que **instalar el extra `ifc` deja un
paquete GPLv3 en el entorno**.

## Decisión (RP8-1)

1. `ifctester` vive **solo** en el extra `ifc`, fuera de `civil`, de `ml` y de las dependencias
   base, y el instalador de S5 **no** lo incluye. La CI instala todos los extras (cero
   omitidas) porque no distribuye nada.
2. El producto importa de `ifctester` únicamente `ifctester.ids`, dentro de una función
   (`adapters/espacio/planos/ids.py`). Nunca importa `bcf` ni `ifctester.reporter`. La prueba
   `tests/unit/test_licencia_ifc.py` lo vigila por AST sobre todo el código del producto.
3. Sin el extra, la importación de un IFC sigue funcionando y el informe lo dice («IDS no
   comprobado: falta el módulo IFC (extra `ifc`)»); lo prueba
   `test_sin_el_modulo_ifc_el_informe_lo_dice_y_no_falla`.
4. Para que el extra entre al instalador hace falta, antes: (a) que Eugenio obtenga un dictamen
   sobre el efecto de empaquetar `bcf-client` (GPLv3) con un producto propietario, o (b) que
   `ifctester` deje de pedirla, o (c) reemplazar la validación IDS por código propio. Mientras
   tanto el IDS lo audita quien instala el extra en su equipo de desarrollo o de tesis.
5. Si una versión nueva cambia la licencia de cualquiera de las dos, falla la prueba que
   compara este documento con las distribuciones instaladas, y se vuelve a decidir.

## Qué no cubre

La tesis y el prototipo no se distribuyen con `bcf-client`. Este documento no cubre la
distribución comercial; esa pregunta queda para antes de S5-2 (instalador).
```
- [ ] **Paso 4: Correrla y ver el verde**
Run: `uv run pytest tests/unit/test_licencia_ifc.py -v -W error` → 7 passed.
- [ ] **Paso 5: Commit**
```bash
git add docs/licencias_ifc.md
git commit -m "docs(licencias): ifctester en el extra ifc y la guardia de bcf-client" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 2: Meta S3, ERS, oráculos escritos a mano, protocolos y expedientes

**Rama:** `inc/080-s3-0-docs`   **Rol:** sf-lider-de-fase (meta y expedientes), sf-ingeniero-pruebas
(oráculos, catálogo) **Archivos:**
- Crear: `scripts/meta_silice_s3.py`, `scripts/huellas_protocolos_s3.py`
- Crear: `tests/fixtures/canonico/__init__.py`, `tests/fixtures/canonico/ejemplo_v1.py`
- Crear: `tests/fixtures/memorias/diferencias_s3.md`, `tests/fixtures/memorias/atipicos_s3.md`
- Crear: `tests/fixtures/errores_planos/catalogo.md`,
  `tests/fixtures/errores_planos/of001_limpio.py`
- Crear: `docs/protocolo_indicador_administrador.md`,
  `docs/protocolo_indicador_administrador_lista.md`, `docs/protocolo_deteccion_planos.md`,
  `docs/protocolos_s3.json` (lo escribe el script)
- Crear: `docs/bitacora/2026-10-silice-080.md`, `docs/bitacora/2026-10-silice-s3-expedientes.md`
- Modificar: `scripts/meta_silice.py:60` (`FASES["0.8.0"]`), `docs/ERS.md` (UC-21 a UC-23, RF-80 a
  RF-89, RF-100, RNF-16, RNF-17 y la enmienda única de RNF-08)
- Prueba: `tests/unit/test_meta_silice_s3.py`, `tests/unit/test_documentos_s3_0.py`

**Interfaces:**
- Consume: de A4: `scripts.meta_silice.{FASES, Parte, ParTDD, Comprobacion, Contexto, partes,
  validar_partes, fases_hasta, evaluar_requisitos, _git}` y `scripts.meta_alpha.Estado`.
- Produce:
  - `scripts.meta_silice_s3`: `PARTE`, `PARES_S3`, `PROTOCOLOS`, `REQUISITOS_S3_0`, `RUTA_HUELLAS`,
    `huella_de(ruta) -> str`, `evaluar_protocolos`, `evaluar_literal_of001`,
    `evaluar_html_inseguro`, `evaluar_cobertura_en_ci`, `evaluar_ramas_sin_nucleo`.
  - `tests/fixtures/canonico/ejemplo_v1.py`: `EJEMPLO_V1` (el documento a mano), `BYTES_EJEMPLO_V1 =
    2271`, `HUELLA_EJEMPLO_V1`; lo usan las tareas 7, 8, 15, 19 y 21.
  - `tests/fixtures/errores_planos/of001_limpio.py`: `LIMPIO = {"dxf": {...}, "ifc": {...}}`.
  - `FASES["0.8.0"] = ("S3-0", ..., "S3-7")`.

Orden de escritura (spec S3 §14, S3-0): primero las pruebas y los oráculos que no dependen de
código; después la meta, la ERS y los protocolos; al final los expedientes. Ninguna prueba de esta
tarea importa código de S3: el vector de huella se recalcula con `json` y `hashlib` solos.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_meta_silice_s3.py`**
```python
"""Parte S3 de la meta única de Sílice (spec S3 §13.6; plan 0.8.0, tarea 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.meta_alpha import Estado
from scripts.meta_silice import FASES, fases_hasta, partes, validar_partes
from scripts.meta_silice_s3 import (
    PARES_S3,
    PARTE,
    PROTOCOLOS,
    REQUISITOS_S3_0,
    evaluar_cobertura_en_ci,
    evaluar_html_inseguro,
    evaluar_literal_of001,
    evaluar_protocolos,
    evaluar_ramas_sin_nucleo,
    huella_de,
)

RAIZ = Path(__file__).resolve().parents[2]


def test_la_parte_s3_se_descubre_y_sus_fases_existen_en_0_8_0() -> None:
    validar_partes((PARTE,))
    assert any(parte is PARTE for parte in partes())
    assert FASES["0.8.0"] == ("S3-0", "S3-1", "S3-2", "S3-3", "S3-4", "S3-5", "S3-6", "S3-7")
    assert {par.fase for par in PARES_S3} <= set(FASES["0.8.0"])


def test_rf_100_solo_se_exige_con_la_fase_s3_6() -> None:
    assert "RF-100" not in PARTE.requisitos["S3-0"]
    assert PARTE.requisitos["S3-6"] == ("RF-100",)
    assert "S3-6" not in fases_hasta("0.8.0", "S3-5") and "S3-6" in fases_hasta("0.8.0", "S3-6")


def test_la_ers_de_s3_0_pide_cada_uc_rf_y_rnf_de_la_version() -> None:
    assert set(REQUISITOS_S3_0) == {f"UC-{n}" for n in (21, 22, 23)} | {
        f"RF-{n}" for n in range(80, 90)} | {"RNF-16", "RNF-17"}


def test_los_pares_nombran_archivos_del_repositorio_cuando_su_fase_ya_se_construyo() -> None:
    for par in PARES_S3:
        assert par.prueba.startswith("tests/") and "/" in par.implementacion


def test_los_pares_de_las_fases_ya_construidas_existen() -> None:
    """Ninguna fase de la 0.8.0 está construida mientras esta prueba solo vea S3-0."""
    for par in PARES_S3:
        if par.fase == "S3-0":
            assert (RAIZ / par.prueba).is_file(), par.prueba


# --- S3-M1: la huella de los protocolos -------------------------------------------------------


def _protocolos(tmp_path: Path, huellas_malas: tuple[str, ...] = ()) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    escritas = {}
    for relativa in PROTOCOLOS:
        ruta = tmp_path / relativa
        ruta.write_text(f"protocolo {relativa}", encoding="utf-8")
        escritas[relativa] = "0" * 64 if relativa in huellas_malas else huella_de(ruta)
    (docs / "protocolos_s3.json").write_text(json.dumps({"protocolos": escritas}), encoding="utf-8")
    return docs / "protocolos_s3.json"


def test_los_protocolos_con_su_huella_pasan(tmp_path: Path) -> None:
    huellas = _protocolos(tmp_path)
    assert evaluar_protocolos(tmp_path, huellas)[0] is Estado.OK


def test_un_protocolo_cambiado_despues_de_escribir_su_huella_falla(tmp_path: Path) -> None:
    huellas = _protocolos(tmp_path)
    (tmp_path / PROTOCOLOS[1]).write_text("otro texto", encoding="utf-8")
    estado, detalle = evaluar_protocolos(tmp_path, huellas)
    assert estado is Estado.FALLA and "protocolo_deteccion_planos" in detalle


def test_sin_el_archivo_de_huellas_o_sin_un_protocolo_falla(tmp_path: Path) -> None:
    assert evaluar_protocolos(tmp_path, tmp_path / "docs" / "protocolos_s3.json")[0] is Estado.FALLA
    huellas = _protocolos(tmp_path)
    (tmp_path / PROTOCOLOS[0]).unlink()
    assert evaluar_protocolos(tmp_path, huellas)[0] is Estado.FALLA


# --- S3-M2: el literal de OF-001 limpio -------------------------------------------------------


def test_el_literal_de_of001_limpio_exige_items_y_hallazgos(tmp_path: Path) -> None:
    ruta = tmp_path / "of001_limpio.py"
    assert evaluar_literal_of001(ruta)[0] is Estado.FALLA
    ruta.write_text('LIMPIO = {"dxf": {"items": (), "hallazgos": ()}}\n', encoding="utf-8")
    assert evaluar_literal_of001(ruta)[0] is Estado.FALLA
    ruta.write_text(
        'LIMPIO = {"dxf": {"items": (("a", "b", "c"),), '
        '"hallazgos": (("R8", "A", "d"),)}}\n',
        encoding="utf-8")
    assert evaluar_literal_of001(ruta)[0] is Estado.OK


# --- S3-M3: ningún HTML inseguro --------------------------------------------------------------


def test_unsafe_allow_html_se_detecta_en_cualquier_carpeta_vigilada(tmp_path: Path) -> None:
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "ok.py").write_text("st.markdown('x')\n", encoding="utf-8")
    assert evaluar_html_inseguro(tmp_path, ("ui", "api"))[0] is Estado.OK
    (tmp_path / "ui" / "mal.py").write_text("st.markdown(x, unsafe_allow_html=True)\n",
                                            encoding="utf-8")
    estado, detalle = evaluar_html_inseguro(tmp_path, ("ui", "api"))
    assert estado is Estado.FALLA and "ui/mal.py" in detalle


# --- S3-M4: cobertura en la CI ----------------------------------------------------------------


@pytest.mark.parametrize("texto,esperado", [
    (None, Estado.PENDIENTE),
    ("run: coverage report --include=\"core/*\" --fail-under=80\n", Estado.FALLA),
    ("run: coverage report --include=\"seguridad/*,paquete/*\" --fail-under=80\n", Estado.OK),
])
def test_la_cobertura_de_seguridad_y_paquete_se_exige_en_la_ci(texto, esperado) -> None:
    assert evaluar_cobertura_en_ci(texto)[0] is esperado


# --- S3-M5: las ramas de planos y anomalías no tocan core/ ------------------------------------


def test_las_ramas_sin_nucleo_dan_ok_solo_con_diffs_vacios() -> None:
    assert evaluar_ramas_sin_nucleo({})[0] is Estado.PENDIENTE
    assert evaluar_ramas_sin_nucleo({"Merge inc/080-s3-5-planos": None})[0] is Estado.PENDIENTE
    assert evaluar_ramas_sin_nucleo({"Merge inc/080-s3-5-planos": ""})[0] is Estado.OK
    estado, detalle = evaluar_ramas_sin_nucleo({
        "Merge inc/080-s3-5-planos": "", "Merge inc/080-s3-6-anomalias": " core/x.py | 2 +-\n"})
    assert estado is Estado.FALLA and "s3-6" in detalle
```
**`tests/unit/test_documentos_s3_0.py`**
```python
"""Los documentos que S3-0 escribe antes de cualquier código (spec S3 §13.1, §13.5; GS3-0).

Ninguna de estas pruebas importa código de S3: son el oráculo escrito a mano, el catálogo, los
protocolos con su huella y la ERS enmendada. El vector de huella se recalcula aquí con `json` y
`hashlib` solos, sin `core.budget.canonico` (que todavía no existe)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.meta_alpha import Estado
from scripts.meta_silice import evaluar_requisitos
from scripts.meta_silice_s3 import PROTOCOLOS, REQUISITOS_S3_0, huella_de
from tests.fixtures.canonico.ejemplo_v1 import BYTES_EJEMPLO_V1, EJEMPLO_V1, HUELLA_EJEMPLO_V1

RAIZ = Path(__file__).resolve().parents[2]
MEMORIAS = RAIZ / "tests" / "fixtures" / "memorias"
CATALOGO = RAIZ / "tests" / "fixtures" / "errores_planos" / "catalogo.md"


def test_la_ers_define_cada_uc_rf_y_rnf_de_s3_0() -> None:
    texto = (RAIZ / "docs" / "ERS.md").read_text(encoding="utf-8")
    estado, detalle = evaluar_requisitos(texto, REQUISITOS_S3_0)
    assert estado is Estado.OK, detalle


def test_la_ers_declara_rf_100_como_deseable_y_la_enmienda_unica_de_rnf_08() -> None:
    texto = (RAIZ / "docs" / "ERS.md").read_text(encoding="utf-8")
    assert "RF‑100" in texto and "Deseable" in texto
    assert "Enmienda de Sílice 0.8.0" in texto and "RNF‑08" in texto


def test_el_vector_de_huella_se_calcula_aparte_con_el_json_estandar() -> None:
    canonico = json.dumps(EJEMPLO_V1, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")
    assert len(canonico) == BYTES_EJEMPLO_V1 == 2271
    assert hashlib.sha256(canonico).hexdigest() == HUELLA_EJEMPLO_V1
    assert HUELLA_EJEMPLO_V1 == "b4b952dd4d049df5a18f53c00f2594a077c67f49e2b2fd1fb163cf5999003936"


def test_la_memoria_de_diferencias_trae_las_cifras_escritas_a_mano() -> None:
    texto = (MEMORIAS / "diferencias_s3.md").read_text(encoding="utf-8")
    for cifra in ("**840**", "**1130**", "**250**", "**40**", "**290**", "**550**", "**589**",
                  "**39**", "**48,797375**",
                  "**139,15**", "**47,532375**", "**113,85**", "**−59,604**", "**+2,928**",
                  "**+59,604**", "101,640", "85,470"):
        assert cifra in texto, cifra


def test_la_memoria_de_atipicos_fija_el_conjunto_esperado_antes_del_codigo() -> None:
    texto = (MEMORIAS / "atipicos_s3.md").read_text(encoding="utf-8")
    for fragmento in ("`{v8}`", "**vacío**", "**7** variaciones", "0,00390625", "(25 − 20) / 20"):
        assert fragmento in texto, fragmento


def test_el_catalogo_de_errores_trae_los_17_bloques_y_sus_tres_controles() -> None:
    ids = [linea[4:].strip() for linea in CATALOGO.read_text(encoding="utf-8").splitlines()
           if linea.startswith("### ")]
    assert len(ids) == len(set(ids)) == 17 and sum(i.startswith("NO-DET") for i in ids) == 3


def test_los_dos_protocolos_estan_escritos_y_su_huella_coincide() -> None:
    escritas = json.loads((RAIZ / "docs" / "protocolos_s3.json").read_text(encoding="utf-8"))
    assert escritas["algoritmo"] == "sha256" and set(escritas["protocolos"]) == set(PROTOCOLOS)
    for relativa in PROTOCOLOS:
        assert escritas["protocolos"][relativa] == huella_de(RAIZ / relativa), relativa


def test_el_protocolo_de_planos_fija_la_meta_los_controles_y_las_amenazas() -> None:
    texto = (RAIZ / "docs" / "protocolo_deteccion_planos.md").read_text(encoding="utf-8")
    for fragmento in ("100 %", "cero falsas alarmas", "semilla 42", "no detectables",
                      "validez de constructo", "validez externa"):
        assert fragmento in texto.lower().replace("**", ""), fragmento


def test_el_protocolo_del_administrador_fija_condiciones_orden_y_sesgo() -> None:
    texto = (RAIZ / "docs" / "protocolo_indicador_administrador.md").read_text(encoding="utf-8")
    for fragmento in ("a mano", "con el sistema", "contrabalanceado", "lista congelada",
                      "sesgo del autor", "tasa de detección", "falsas alarmas"):
        assert fragmento in texto.lower().replace("**", ""), fragmento
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_meta_silice_s3.py tests/unit/test_documentos_s3_0.py -v -W
error`
Esperado: error de colección `ModuleNotFoundError: No module named 'scripts.meta_silice_s3'`.
```bash
git add tests/unit/test_meta_silice_s3.py tests/unit/test_documentos_s3_0.py
git commit -m "test(meta): parte S3 y documentos de S3-0 en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Escribir los oráculos a mano (antes de cualquier código de S3)**
  El documento mínimo del vector de huella (S3 §13.1). Las cifras se eligieron para que cada monto
  salga exacto (RELLENO de 20 m3, rendimiento 8). Su SHA-256 se calcula en la prueba con `json`
  estándar, sin el módulo que lo producirá:
**`tests/fixtures/canonico/__init__.py`**
```python

```
**`tests/fixtures/canonico/ejemplo_v1.py`**
```python
"""El documento canónico de MIN-001 v001, escrito A MANO (S3 §13.1, SL-E8).

`tests/fixtures/canonico_minimo.py` siembra esta versión. Los montos salen de la memoria de
cálculo del relleno (rendimiento 8, parámetros de la línea base): materiales 1,00 x 14,00 =
14,0000; equipos 1 x 71,00 x 0,10 / 8 = 0,8875; mano de obra (2 x 10,25 x (1 + 6,00) + 1,00 x 2)
/ 8 = 18,1875; costo directo 33,0750; con administración 33,0750 x 1,15 = 38,036250; precio
unitario 38,036250 x 1,10 = 41,83987500; total 20 x 41,83987500 = 836,79750000.

Las claves están ordenadas y cada `Decimal` es el texto exacto que guarda la base. La huella es el
SHA-256 de los bytes del documento canónico (`json_canonico(EJEMPLO_V1)`), calculado aparte con
`sha256sum` y copiado aquí como literal: no se genera con `documento()` para congelarlo después.
"""

HUELLA_EJEMPLO_V1 = "b4b952dd4d049df5a18f53c00f2594a077c67f49e2b2fd1fb163cf5999003936"
BYTES_EJEMPLO_V1 = 2271

EJEMPLO_V1 = {'codigo': '001',
 'composiciones': [{'codigo_partida': 'MIN-001',
                    'descripcion': 'Relleno de prueba',
                    'lineas': [{'cantidad': '1.00',
                                'depreciacion': None,
                                'descripcion': 'Arena',
                                'insumo': 'MAT-001',
                                'modalidad': None,
                                'orden': 0,
                                'precio': '14.00',
                                'precio_origen': {'fecha_precio': '2026-11-01',
                                                  'fecha_tasa': None,
                                                  'fuente': 'prueba',
                                                  'fuente_tasa': '',
                                                  'heredado': None,
                                                  'moneda_original': 'USD',
                                                  'precio_original': '14.00',
                                                  'tasa': None},
                                'referencia': '',
                                'tipo': 'material',
                                'unidad': 'm3'},
                               {'cantidad': '1',
                                'depreciacion': '0.10',
                                'descripcion': 'Compactadora',
                                'insumo': 'EQU-001',
                                'modalidad': None,
                                'orden': 1,
                                'precio': '71.00',
                                'precio_origen': {'fecha_precio': '2026-11-01',
                                                  'fecha_tasa': None,
                                                  'fuente': 'prueba',
                                                  'fuente_tasa': '',
                                                  'heredado': None,
                                                  'moneda_original': 'USD',
                                                  'precio_original': '71.00',
                                                  'tasa': None},
                                'referencia': '',
                                'tipo': 'equipo',
                                'unidad': None},
                               {'cantidad': '2',
                                'depreciacion': None,
                                'descripcion': 'Obrero',
                                'insumo': 'MO-001',
                                'modalidad': 'jornal',
                                'orden': 2,
                                'precio': '10.25',
                                'precio_origen': {'fecha_precio': '2026-11-01',
                                                  'fecha_tasa': None,
                                                  'fuente': 'prueba',
                                                  'fuente_tasa': '',
                                                  'heredado': None,
                                                  'moneda_original': 'USD',
                                                  'precio_original': '10.25',
                                                  'tasa': None},
                                'referencia': '',
                                'tipo': 'mano_obra',
                                'unidad': None}],
                    'rendimiento': '8',
                    'unidad': 'm3'}],
 'curva': [{'acumulado': '836.79750000',
            'monto': '836.79750000',
            'orden': 0,
            'periodo': 'Dia 1 [MIN-001]'}],
 'fecha': '2026-11-01',
 'formato': 'silice-presupuesto',
 'hallazgos': [],
 'lista': {'alcance': 'global',
           'empresa': None,
           'fecha_tasa': None,
           'fecha_vigencia': '2026-11-01',
           'moneda': 'USD',
           'nombre': 'Lista de prueba',
           'origen': 'prueba',
           'tasa': None},
 'moneda': 'USD',
 'moneda_proyecto': None,
 'parametros': {'administracion': '0.15',
                'bono_alimentacion': '1.00',
                'fcas': '6.00',
                'utilidad': '0.10'},
 'pendientes': [],
 'plan': [{'codigo_partida': 'MIN-001',
           'etiqueta': 'Dia 1',
           'fraccion': '1',
           'orden': 0,
           'periodo': 0}],
 'proyecto': 'MIN-001',
 'renglones': [{'cantidad': '20',
                'con_administracion': '38.036250',
                'costo_directo': '33.0750',
                'equipos': '0.8875',
                'item': {'cantidad': '20',
                         'codigo_partida': 'MIN-001',
                         'descripcion': 'Relleno de prueba',
                         'dominio': 'civil',
                         'especificaciones': {},
                         'origen_id': 'FILA-1',
                         'origen_tipo': 'tabular',
                         'parametros': {},
                         'regla': None,
                         'unidad': 'm3',
                         'unidad_original': 'm3'},
                'mano_obra': '18.1875',
                'materiales': '14.0000',
                'orden': 0,
                'precio_unitario': '41.83987500',
                'total': '836.79750000'}],
 'version_formato': 1}
```
  La memoria de diferencias entre versiones (SL-E9; el costo de R16; las dos entregas paralelas P y
  Q del protocolo). Se rehace después con `fractions.Fraction` en la tarea 10:
**`tests/fixtures/memorias/diferencias_s3.md`**
```markdown
# Memoria de cálculo a mano: diferencia entre versiones, revaloración y costo de R16 (S3)

Oráculo de SL-E9 (`core/budget/comparacion.py`) y del costo de R16 (`ui/contraste.py`), spec S3
§13.1. Está hecha a mano, con aritmética exacta, **antes del código**, y no depende de ninguna
función del proyecto. Las pruebas comparan contra estas cifras, no contra la expresión de una
regla. Los datos son ficticios (NORMAS.md §1): números simples para contar a mano.

## 1. Diferencia entre dos versiones

Descomposición (el término cruzado queda en el precio):

    Δ total = q2·PU2 − q1·PU1 = (q2 − q1)·PU1  [Δ cantidad]  +  (PU2 − PU1)·q2  [Δ precio]

Una partida solo en la versión 2 (nueva) toma PU1 := PU2; una solo en la versión 1 (eliminada)
toma PU2 := PU1; así la partida entera es desvío por cantidad.

| Partida | v1: q × PU | v2: q × PU | Δ cantidad | Δ precio | Δ total | Estado |
|---|---|---|---|---|---|---|
| A | 10 × 50 = 500 | 12 × 50 = 600 | (12 − 10)·50 = 100 | 0 | 100 | cambiada |
| B | 5 × 20 = 100 | 5 × 22 = 110 | 0 | (22 − 20)·5 = 10 | 10 | cambiada |
| C | 2 × 100 = 200 | 3 × 110 = 330 | (3 − 2)·100 = 100 | (110 − 100)·3 = 30 | 130 | cambiada |
| D | 4 × 10 = 40 | — | (0 − 4)·10 = −40 | 0 | −40 | eliminada |
| E | — | 3 × 30 = 90 | 3·30 = 90 | 0 | 90 | nueva |

Totales: v1 = 500 + 100 + 200 + 40 = **840**; v2 = 600 + 110 + 330 + 90 = **1130**.
Σ Δ cantidad = 100 + 0 + 100 − 40 + 90 = **250**; Σ Δ precio = 0 + 10 + 30 + 0 + 0 = **40**;
Δ total = 250 + 40 = **290** = 1130 − 840. Orden por |Δ total| descendente: C (130), A (100),
E (90), D (40), B (10).

### 1b. La entrega paralela Q (protocolo del indicador de quien revisa, S3 §13.5 a)

Misma descomposición, otras cifras, para que la persona que revisa no vea dos veces la misma
entrega (`docs/protocolo_indicador_administrador.md` §2). Sus partidas llevan prima.

| Partida | v1: q × PU | v2: q × PU | Δ cantidad | Δ precio | Δ total | Estado |
|---|---|---|---|---|---|---|
| A' | 8 × 25 = 200 | 9 × 25 = 225 | (9 − 8)·25 = 25 | 0 | 25 | cambiada |
| B' | 6 × 15 = 90 | 6 × 16 = 96 | 0 | (16 − 15)·6 = 6 | 6 | cambiada |
| C' | 4 × 40 = 160 | 5 × 44 = 220 | (5 − 4)·40 = 40 | (44 − 40)·5 = 20 | 60 | cambiada |
| D' | 2 × 50 = 100 | — | (0 − 2)·50 = −100 | 0 | −100 | eliminada |
| E' | — | 4 × 12 = 48 | 4·12 = 48 | 0 | 48 | nueva |

Totales: v1 = 200 + 90 + 160 + 100 = **550**; v2 = 225 + 96 + 220 + 48 = **589**.
Σ Δ cantidad = 25 + 0 + 40 − 100 + 48 = **13**; Σ Δ precio = 0 + 6 + 20 + 0 + 0 = **26**;
Δ total = 13 + 26 = **39** = 589 − 550. Orden por |Δ total|: D' (100), C' (60), E' (48), A' (25),
B' (6).

## 2. Revaloración con la lista de quien revisa (MIN-001 del paquete de prueba)

Línea base del paquete: arena 1,00 × 14,00; compactadora 1 × 71,00 × 0,10 / 8 = 0,8875; mano de
obra (2 × 10,25 × (1 + 6,00) + 1,00 × 2) / 8 = 18,1875; PU = 41,839875; cantidad 20.

La lista del revisor trae la arena a 16,00 y el obrero a 12,25; la compactadora **no está** en su
lista: es «no contrastable», conserva 71,00 y no suma al desvío.

- Materiales 1,00 × 16,00 = 16,00. Mano de obra (2 × 12,25 × 7 + 1,00 × 2) / 8 = 173,5 / 8 =
  21,6875. Costo directo 16,00 + 0,8875 + 21,6875 = 38,575.
- Con administración 38,575 × 1,15 = 44,36125; PU = 44,36125 × 1,10 = **48,797375**.
- Δ total = (48,797375 − 41,839875) × 20 = 6,9575 × 20 = **139,15**, todo por precio (Δ cantidad 0).

Con la arena a 15,00 (referencia por «Ref» de precio en vez de por código):
materiales 15,00 → costo directo 15,00 + 0,8875 + 21,6875 = 37,575; × 1,15 = 43,21125; PU =
**47,532375**; Δ total = (47,532375 − 41,839875) × 20 = 5,6925 × 20 = **113,85**.

## 3. Costo de R16 sobre OF-001 (solo la especialidad de datos)

Referencia = OF-001 de `of001.md` (7 puntos de datos, rack `RK1`). Cantidades de la memoria de
OF-001 §3: cajas, *face plates*, *jacks* y certificaciones 7 cada una (sin desperdicio, D-17);
cable UTP cat 6 = 74,900 + 7 × (2,0 + 0,5) = 92,400 × 1,10 = **101,640 m**; canalización EMT
1/2" = DS1 + DS2 + DS3 = 3 + 3 + 2,2 = **8,2 m**; EMT 3/4" = DS4 a DS17 = **23,2 m**.

Precios de la memoria (supuestos de prueba): caja 5,00; *face plate* 3,00; *jack* 4,00;
certificación 12,00; UTP cat 6 1,20 /m; EMT 3/4" 6,00 /m; EMT 1/2" 4,50 /m.

**Escenario A: el plano no trae `PB3` (faltante en el plano).** Sin `PB3` (recorrido 12,2 m):
cajas = *face plates* = *jacks* = certificaciones = 6; cable = (74,900 − 12,2 + 6 × 2,5) × 1,10 =
(62,7 + 15,0) × 1,10 = **85,470 m**; EMT 3/4" sin DS16 (0,5) ni DS17 (2,2) = 23,2 − 2,7 =
**20,5 m**; EMT 1/2" igual (8,2 m).

| Partida | Plano − referencia | × precio | Δ |
|---|---|---|---|
| caja, *face plate*, *jack*, certificación | −1 cada una | 5,00 + 3,00 + 4,00 + 12,00 = 24,00 |
↳ −24,000 |
| UTP cat 6 | 85,470 − 101,640 = −16,170 m | 1,20 | −19,404 |
| EMT 3/4" | 20,5 − 23,2 = −2,7 m | 6,00 | −16,200 |
| EMT 1/2" | 0 | 4,50 | 0 |
| **Total** | | | **−59,604** |

R16 da un único faltante (`PB3`, solo en la referencia) y 32 emparejadas.

**Escenario B: `PB3` está 0,40 m más allá (y = 5,9 en vez de 5,5): desplazado.** 0,40 m queda
entre 0,10 y 1,00 m: desplazado. Los 7 puntos siguen, así que las cuatro piezas no cambian. El
recorrido de `PB3` crece 0,40 m (el tendido en y a z = 2,5): cable = 101,640 + 0,40 × 1,10 =
**102,080 m**; DS16 pasa de 0,5 a 0,9 m y DS17 conserva 2,2: EMT 3/4" = **23,6 m**.
Δ = 0,44 × 1,20 + 0,40 × 6,00 = 0,528 + 2,400 = **+2,928**.

**Escenario C: sobrante.** Es A con las fuentes cambiadas (la referencia sin `PB3` y el plano
con él): un sobrante en el plano y **+59,604**.

## 4. Reauditoría con anexos

El anexo `espacio` de OF-001 en un paquete reauditado da exactamente 33 ADVERTENCIAS de R8 (las
de las constantes supuestas de `of001.md`) y ninguna de R9, R10 ni R15. La importación del DXF de
OF-001 da 8 (6 «altura pendiente» y 2 supuestos de circuito): son dos literales distintos
porque no leen lo mismo (RP8-5).
```
  La memoria de variaciones atípicas (RF-100) fija el conjunto esperado antes del código:
**`tests/fixtures/memorias/atipicos_s3.md`**
```markdown
# Memoria de cálculo a mano: variaciones atípicas en series de precios sembradas (RF-100, S3-6)

Oráculo de `ml/anomaly/series.py` y `ui/atipicos.py` (spec S3 §3.2 y §13.2). Hecha a mano antes
del código; no depende de ninguna función del proyecto. **No valida la tasa real de detección
ni de falsas alarmas** (los datos son ficticios, NORMAS.md §1): solo fija qué punto es atípico
en series construidas para que lo sea. La tesis lo presenta como apoyo a quien revisa.

El detector es el de I6.1 y no se ajusta: `SEMILLA` = 42, `UMBRAL_ATIPICO` = −0,05,
`MINIMO_OBSERVACIONES` = 8 variaciones. Una variación es `(p2 − p1) / p1`.

## 1. Serie de 10 precios con un atípico (9 variaciones)

Precios en USD, uno por mes (2026-01 a 2026-10): 1, 2, 4, 8, 16, 32, 64, 128, 256, **257**.

| Variación | Cálculo | Valor |
|---|---|---|
| v0 a v7 | (2 − 1) / 1 = 1, (4 − 2) / 2 = 1, …, (256 − 128) / 128 | **1** (ocho veces) |
| v8 (2026-09 → 2026-10) | (257 − 256) / 256 | **0,00390625** |

Ocho variaciones iguales a 1 y una de 0,00390625: el atípico es **v8**, el único. Conjunto
esperado de hallazgos: `{v8}`, ADVERTENCIA, con valor 0,00390625 (0,39 %).

## 2. Serie de 10 precios sin atípico

Precios: 1, 2, 4, 8, 16, 32, 64, 128, 256, **512**. Las nueve variaciones valen 1 (todas
iguales): nada se aparta del resto. Conjunto esperado: **vacío**.

## 3. Serie corta: abstención

Precios: 1, 2, 4, 8, 16, 32, 64, 128 (8 precios, **7** variaciones, menos de 8). El detector se
abstiene aunque se le añada un punto raro: conjunto esperado **vacío** y `se_abstuvo` verdadero.

## 4. Conversión a USD con la tasa de cada precio (RF-65)

Dos precios en bolívares de fechas distintas, con la tasa (Bs por USD) de cada fecha:

| Fecha | Precio | Tasa | En USD |
|---|---|---|---|
| 2026-08-03 | 720 Bs | 36 | 720 / 36 = **20** |
| 2026-09-07 | 1 100 Bs | 44 | 1 100 / 44 = **25** |

Variación en USD = (25 − 20) / 20 = **0,25**. En bolívares habría sido (1 100 − 720) / 720 =
0,52777…: la diferencia es la erosión de la moneda, que no es un cambio del precio del insumo.
Un precio en Bs **sin tasa** no se convierte ni se inventa: se omite y se nombra (`sin_tasa`).

## 5. Ordenamiento y emparejamiento

Los puntos se ordenan por fecha y, a igual fecha, por el nombre de su lista; las variaciones
son entre consecutivos. Un precio anterior igual a 0 no genera variación (no se divide por 0).
Las listas de **proyecto** (las que nacen de una cotización) no entran en la serie.
```
  El catálogo de errores sembrados en planos. Lo escribe en parte quien no programa las reglas
  (columna *Autor*, `P`) sin ver R15 ni R16; la prueba de la tarea 12 vigila que sus `id` coincidan
  con los del sembrador:
**`tests/fixtures/errores_planos/catalogo.md`**
```markdown
# Catálogo de errores sembrados en planos (S3 §11.5, RF-89)

Se escribe en S3-0, **antes** del código de R15 y R16. Cada bloque dice qué se siembra, cómo y
qué detección se espera. `scripts/sembrar_errores_planos.py` implementa una siembra por `id` y la
prueba `tests/unit/test_deteccion_planos.py` vigila que los dos conjuntos de `id` coincidan.

## Lenguaje de las detecciones

Cada campo *Detección esperada* y *Consecuencias admitidas* lleva una o más etiquetas separadas
por `;`; una etiqueta puede unir alternativas con `|` (se cumple si se cumple alguna). Frente al
plano limpio, la auditoría AGREGA:

- `estado:<valor>`: el estado de la importación es `<valor>` (`detenida`, `rechazada`);
- `item:<tipo>:<texto>`: un ítem del informe de importación de ese tipo cuyo mensaje contiene
  `<texto>`;
- `regla:<R>:<texto>`: un hallazgo de esa regla (`R8`, `R9`, `R10`, `R15`) cuya descripción
  contiene `<texto>`;
- `r16:<tipo>`: una diferencia de R16 de ese tipo (`faltante`, `sobrante`, `desplazado`) entre el
  plano sembrado y el limpio;
- `ninguna`: nada; es un control no detectable (mide el límite declarado).

Las *consecuencias admitidas* son agregados que el error provoca por fuerza (la escala ×1000
agranda todos los recorridos); lo que se agregue y no esté ni en la detección ni en las
consecuencias es una **falsa alarma**. Lo que el plano limpio ya tenía (sus 15 ítems y sus 8
hallazgos de R8, ver `of001_limpio.py`) no se cuenta.

**Autor.** `P`: lo escribió el ingeniero de pruebas sin ver la implementación de R15 ni de R16
(§13.5 b); `A`: lo escribió quien programa los adaptadores.

Los tres controles **no detectables** miden el límite declarado de la auditoría de planos: sin una
segunda fuente, un plano coherente pero equivocado no se distingue de uno correcto (H-D9). Se
informan con su número; no entran en la tasa de detección ni en las falsas alarmas.

## Errores

### SIN-UNIDAD

- **Categoría:** sin `$INSUNITS`
- **Cómo se siembra:** se borra la unidad del encabezado del DXF
- **Detección esperada:** estado:detenida
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### ENTIDAD-DANADA

- **Categoría:** entidad dañada
- **Cómo se siembra:** una línea con un tipo de línea que no existe
- **Detección esperada:** item:aproximado:error de estructura
- **Consecuencias admitidas:** item:no reconocido:fuera de la convencion
- **Detectable:** sí
- **Autor:** P

### CAPA-EQUIVOCADA

- **Categoría:** bloque en capa equivocada
- **Cómo se siembra:** un punto de datos pasa a la capa `PTO-DATO` (errata)
- **Detección esperada:** item:no reconocido:fuera de la convencion
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### ALTURA-FALTANTE

- **Categoría:** `ALTURA` faltante
- **Cómo se siembra:** a un punto se le quita el atributo `ALTURA`
- **Detección esperada:** item:pendiente:sin atributo ALTURA
- **Consecuencias admitidas:** regla:R8:altura pendiente
- **Detectable:** sí
- **Autor:** P

### ESCALA-X1000

- **Categoría:** escala ×1000
- **Cómo se siembra:** todo el dibujo se multiplica por 1000 con la unidad en metros
- **Detección esperada:** regla:R15:escala imposible
- **Consecuencias admitidas:** regla:R15:de su fuente; regla:R10:enlace de
- **Detectable:** sí
- **Autor:** P

### SUPERPUESTO

- **Categoría:** ambiente superpuesto
- **Cómo se siembra:** un ambiente nuevo que pisa 0,25 m² de ZA y 0,75 m² de ZB
- **Detección esperada:** regla:R15:se superponen
- **Consecuencias admitidas:** item:pendiente:altura pendiente; regla:R8:altura pendiente;
  item:aproximado:cae en varios ambientes
- **Detectable:** sí
- **Autor:** P

### PUNTO-DUPLICADO

- **Categoría:** punto duplicado
- **Cómo se siembra:** un punto de datos se copia sobre sí mismo con otro id
- **Detección esperada:** regla:R15:duplicados
- **Consecuencias admitidas:** item:aproximado:fuente
- **Detectable:** sí
- **Autor:** P

### FUERA-DE-AMBIENTE

- **Categoría:** punto fuera de todo ambiente
- **Cómo se siembra:** un punto de datos se lleva a (30; 30)
- **Detección esperada:** item:no reconocido:queda fuera de todo ambiente
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### SIN-FUENTE

- **Categoría:** punto sin fuente
- **Cómo se siembra:** se borra el rack de datos o el tablero
- **Detección esperada:** item:pendiente:sin fuente compatible|item:pendiente:sin tablero
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### IFC-SIN-ALTURA

- **Categoría:** `IfcSpace` sin altura
- **Cómo se siembra:** el IFC de oficina sin `Qto_SpaceBaseQuantities.Height`
- **Detección esperada:** item:pendiente:IDS «Espacio con altura»
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### IFC-SIN-DIAMETRO

- **Categoría:** aparato sin diámetro
- **Cómo se siembra:** el IFC de oficina sin `Silice_Hoja.DiametroNominal`
- **Detección esperada:** item:pendiente:IDS «Aparato sanitario con diametro»
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### IFC-SIN-CIRCUITO

- **Categoría:** tomacorriente sin circuito
- **Cómo se siembra:** el IFC de oficina sin `Silice_Hoja.Circuito`
- **Detección esperada:** item:pendiente:IDS «Tomacorriente con circuito»
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** A

### ELEMENTO-BORRADO

- **Categoría:** elemento borrado entre dos fuentes
- **Cómo se siembra:** el plano pierde un punto que el levantamiento sí trae
- **Detección esperada:** r16:faltante
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### DESPLAZADO-0-50

- **Categoría:** punto desplazado 0,50 m entre dos fuentes
- **Cómo se siembra:** un punto se corre 0,50 m hacia el interior de su ambiente
- **Detección esperada:** r16:desplazado
- **Consecuencias admitidas:** —
- **Detectable:** sí
- **Autor:** P

### NO-DET-TRASLADO

- **Categoría:** control: todo el plano trasladado
- **Cómo se siembra:** todo el dibujo se corre 0,50 m en x (coherente, pero equivocado)
- **Detección esperada:** ninguna
- **Consecuencias admitidas:** —
- **Detectable:** no
- **Autor:** P

### NO-DET-PERMUTA

- **Categoría:** control: dos puntos con los ids cambiados
- **Cómo se siembra:** `PA1` y `PA2` intercambian sus ids (coherente, pero equivocado)
- **Detección esperada:** ninguna
- **Consecuencias admitidas:** —
- **Detectable:** no
- **Autor:** P

### NO-DET-LUCES

- **Categoría:** control: luminarias corridas
- **Cómo se siembra:** las cuatro luminarias se corren 0,30 m en y (coherente, pero equivocado)
- **Detección esperada:** ninguna
- **Consecuencias admitidas:** —
- **Detectable:** no
- **Autor:** P
```
  El conjunto exacto de OF-001 limpio como literal (RP8-5). Lo comprueba la tarea 12 contra lo que
  la hoja realmente dice; aquí solo se escribe:
**`tests/fixtures/errores_planos/of001_limpio.py`**
```python
"""El conjunto EXACTO de los planos limpios (S3 §11.5 y §13.5 b; de S3-0).

`DXF_*` es lo que la hoja diría del DXF de OF-001 (`tests/fixtures/planos/of001.dxf`): los ítems
del informe de importación que no son «importado» y los hallazgos de R8 a R10 y R15 (R9, R10 y
R15 no dan ninguno). `IFC_*` es lo mismo del IFC de oficina de `planos_ifc_ids`. Lo regenera
`uv run python scripts/medir_deteccion_planos.py --limpio`; cambiarlo a mano es cambiar el
oráculo de la medición. Las constantes son tuplas de `(tipo, tabla, mensaje)` y de
`(regla, severidad, descripción)`.
"""

DXF_ITEMS = (
    ("aproximado", "esp_circuitos",
     "circuito C1: conductores 1-1-1 y 6 puntos maximos son supuestos declarados (SF5-1, "
     "SF5-2); ajustelos en la hoja"),
    ("aproximado", "esp_circuitos",
     "circuito C2: conductores 1-1-1 y 6 puntos maximos son supuestos declarados (SF5-1, "
     "SF5-2); ajustelos en la hoja"),
    ("aproximado", "esp_puntos",
     "PA1: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PA2: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PA3: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PB1: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PB2: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PB3: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("aproximado", "esp_puntos",
     "PR1: fuente RK1 asignada por cercania (no hay una unica en su ambiente)"),
    ("pendiente", "esp_ambientes",
     "ambiente BAN-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente COC-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente CT-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente REC-01: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente ZA: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
    ("pendiente", "esp_ambientes",
     "ambiente ZB: altura pendiente; entra con 2.5 m provisionales hasta cargar la real"),
)

DXF_HALLAZGOS = (
    ("R8", "ADVERTENCIA",
     "ambiente BAN-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente COC-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente CT-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente REC-01: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente ZA: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "ambiente ZB: altura pendiente; la medida vertical es provisional"),
    ("R8", "ADVERTENCIA",
     "circuito C1: circuito importado con conductores y puntos supuestos (1-1-1 y 6 puntos "
     "maximos; SF5-1, SF5-2); declarelos en la hoja"),
    ("R8", "ADVERTENCIA",
     "circuito C2: circuito importado con conductores y puntos supuestos (1-1-1 y 6 puntos "
     "maximos; SF5-1, SF5-2); declarelos en la hoja"),
)

IFC_ITEMS = (
    ("aproximado", "esp_ambientes",
     "SALON-L: no es rectangular; se importa su caja envolvente (6.0000 x 4.0000 m)"),
    ("no reconocido", "IfcOutlet",
     "IfcOutlet AUDIOVISUALOUTLET: 1 elemento fuera de la convencion; no se importan"),
    ("no reconocido", "IfcWall",
     "IfcWall: 1 elemento fuera de la convencion; no se importan"),
    ("pendiente", "esp_puntos",
     "1 aparato(s) sanitario(s): se importo su punto de agua fria; el drenaje no se infiere, "
     "se agrega en la hoja"),
    ("pendiente", "esp_puntos",
     "2 punto(s) electricos sin circuito: el IFC no los trae; se declaran en la hoja"),
    ("pendiente", "esp_puntos",
     "3 punto(s) de agua o datos sin fuente: el IFC no trae montante, colector ni rack; se "
     "asignan en la hoja"),
)

IFC_HALLAZGOS = (
)

LIMPIO = {
    "dxf": {"items": DXF_ITEMS, "hallazgos": DXF_HALLAZGOS},
    "ifc": {"items": IFC_ITEMS, "hallazgos": IFC_HALLAZGOS},
}
```
- [ ] **Paso 4: Escribir la meta, la ERS y los protocolos**
  La parte S3 de la meta única (el descubrimiento es por nombre: `scripts/meta_silice_<parte>.py`):
**`scripts/meta_silice_s3.py`**
```python
"""Parte S3 de la meta única de Sílice (spec S3 §13.6; plan 0.8.0, tarea 2).

`scripts/meta_silice.py` la descubre por su nombre. Con `--version 0.8.0 --hasta S3-n` evalúa,
además de las siete comprobaciones comunes (C1 a C7):

* **C1** (presencia en la ERS): en `S3-0`, UC-21 a UC-23, RF-80 a RF-89, RNF-16 y RNF-17; en
  `S3-6`, RF-100 (deseable: solo se exige si la fase se evalúa; si cae, la meta de la 0.8.0 se
  cierra en `S3-5` y RF-100 se declara no construido);
* **C3** (la prueba antes que la implementación): los pares de `PARES_S3`;
* **S3-M1** (`S3-0`): la huella SHA-256 de los dos protocolos de §13.5 y de la lista congelada
  coincide con la escrita en `docs/protocolos_s3.json`, antes de Med;
* **S3-M2** (`S3-0`): el conjunto exacto de OF-001 limpio está escrito como literal;
* **S3-M3** (`S3-1`): ningún `unsafe_allow_html` en `ui/`, `api/`, `seguridad/`, `paquete/` ni
  `auditoria/`;
* **S3-M4** (`S3-3`): la CI exige cobertura ≥ 80 % de `seguridad/` y `paquete/`;
* **S3-M5** (`S3-5`): las ramas de S3-5 y S3-6 fusionadas no tocan `core/`.
"""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_alpha import Estado  # noqa: E402
from scripts.meta_silice import Comprobacion, Contexto, ParTDD, Parte, _git  # noqa: E402

RUTA_HUELLAS = RAIZ / "docs" / "protocolos_s3.json"
#: Los dos protocolos de §13.5 y la lista congelada de diferencias sembradas del primero.
PROTOCOLOS = (
    "docs/protocolo_indicador_administrador.md",
    "docs/protocolo_deteccion_planos.md",
    "docs/protocolo_indicador_administrador_lista.md",
)
RUTA_LIMPIO = RAIZ / "tests" / "fixtures" / "errores_planos" / "of001_limpio.py"
RUTA_CI = RAIZ / ".github" / "workflows" / "ci.yml"
CARPETAS_SIN_HTML_INSEGURO = ("ui", "api", "seguridad", "paquete", "auditoria")
RAMAS_SIN_NUCLEO = ("inc/080-s3-5", "inc/080-s3-6")
REQUISITOS_S3_0 = (
    "UC-21", "UC-22", "UC-23", "RF-80", "RF-81", "RF-82", "RF-83", "RF-84", "RF-85", "RF-86",
    "RF-87", "RF-88", "RF-89", "RNF-16", "RNF-17",
)

#: Prueba -> implementación, por fase (C3: el commit de la prueba va antes).
PARES_S3: tuple[ParTDD, ...] = (
    ParTDD("tests/unit/test_licencia_ifc.py", "docs/licencias_ifc.md", "S3-0"),
    ParTDD("tests/unit/test_documentos_s3_0.py", "docs/protocolos_s3.json", "S3-0"),
    ParTDD("tests/unit/test_meta_silice_s3.py", "scripts/meta_silice_s3.py", "S3-0"),
    ParTDD("tests/unit/test_json_estricto.py", "seguridad/json_estricto.py", "S3-1"),
    ParTDD("tests/unit/test_secretos.py", "seguridad/secretos.py", "S3-1"),
    ParTDD("tests/unit/test_permisos.py", "seguridad/permisos.py", "S3-1"),
    ParTDD("tests/unit/test_cuentas.py", "seguridad/cuentas.py", "S3-1"),
    ParTDD("tests/unit/test_sesiones.py", "seguridad/sesiones.py", "S3-1"),
    ParTDD("tests/unit/test_ui_acceso.py", "ui/acceso.py", "S3-1"),
    ParTDD("tests/unit/test_ui_marco.py", "ui/sesion.py", "S3-1"),
    ParTDD("tests/integration/test_concurrencia.py", "core/catalog/sesion.py", "S3-2"),
    ParTDD("tests/integration/test_canonico.py", "core/budget/canonico.py", "S3-2"),
    ParTDD("tests/integration/test_cadena.py", "core/budget/cadena.py", "S3-2"),
    ParTDD("tests/unit/test_comparacion.py", "core/budget/comparacion.py", "S3-2"),
    ParTDD("tests/unit/test_firma.py", "seguridad/firma.py", "S3-3"),
    ParTDD("tests/unit/test_empresas.py", "seguridad/empresas.py", "S3-3"),
    ParTDD("tests/unit/test_paquete_formato.py", "paquete/formato.py", "S3-3"),
    ParTDD("tests/unit/test_paquete_verificar.py", "paquete/verificar.py", "S3-3"),
    ParTDD("tests/unit/test_paquete_anterioridad.py", "paquete/verificar.py", "S3-3"),
    ParTDD("tests/integration/test_entrega.py", "ui/entrega.py", "S3-3"),
    ParTDD("tests/unit/test_ui_administracion.py", "ui/paginas/administracion.py", "S3-3"),
    ParTDD("tests/unit/test_ui_revision.py", "ui/revision.py", "S3-4"),
    ParTDD("tests/integration/test_revision_recibir.py", "ui/revision.py", "S3-4"),
    ParTDD("tests/unit/test_ui_revisar.py", "ui/paginas/revisar.py", "S3-4"),
    ParTDD("tests/unit/test_ui_roles.py", "ui/paginas/revisar.py", "S3-4"),
    ParTDD("tests/integration/test_api_auditorias.py", "api/rutas/auditorias.py", "S3-4"),
    ParTDD("tests/unit/test_claves_api_y_red.py", "seguridad/claves_api.py", "S3-3"),
    ParTDD("tests/unit/test_r15_geometria_plano.py",
           "adapters/espacio/planos/geometria_plano.py", "S3-5"),
    ParTDD("tests/unit/test_r16_contraste.py", "adapters/espacio/planos/contraste.py", "S3-5"),
    ParTDD("tests/unit/test_ui_contraste.py", "ui/contraste.py", "S3-5"),
    ParTDD("tests/unit/test_planos_auditoria_s3.py", "adapters/espacio/planos/ids.py", "S3-5"),
    ParTDD("tests/unit/test_deteccion_planos.py", "scripts/medir_deteccion_planos.py", "S3-5"),
    ParTDD("tests/unit/test_series_atipicas.py", "ml/anomaly/series.py", "S3-6"),
    ParTDD("tests/integration/test_atipicos.py", "ui/atipicos.py", "S3-6"),
)


# --- evaluadores puros ------------------------------------------------------------------------


def huella_de(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def evaluar_protocolos(raiz: Path, huellas: Path) -> tuple[Estado, str]:
    """S3-M1: cada protocolo de §13.5 y la lista congelada existen y su SHA-256 es el escrito en
    `protocolos_s3.json`."""
    if not huellas.is_file():
        return Estado.FALLA, f"falta {huellas.name}"
    escritas = json.loads(huellas.read_text(encoding="utf-8")).get("protocolos", {})
    malos = []
    for relativa in PROTOCOLOS:
        ruta = raiz / relativa
        if not ruta.is_file():
            malos.append(f"{relativa}: no existe")
        elif escritas.get(relativa) != huella_de(ruta):
            malos.append(f"{relativa}: la huella no coincide con la escrita")
    if malos:
        return Estado.FALLA, "; ".join(malos)
    return Estado.OK, "huella escrita de los protocolos y su lista: " + ", ".join(
        p.rpartition("/")[2] for p in PROTOCOLOS)


def evaluar_literal_of001(ruta: Path) -> tuple[Estado, str]:
    """S3-M2: el conjunto exacto de OF-001 limpio está escrito (ítems y hallazgos del DXF)."""
    if not ruta.is_file():
        return Estado.FALLA, f"falta {ruta.name}"
    dxf = runpy.run_path(str(ruta)).get("LIMPIO", {}).get("dxf") or {}
    if not dxf.get("items") or not dxf.get("hallazgos"):
        return Estado.FALLA, "el literal de OF-001 no trae los ítems y los hallazgos del DXF"
    items, hallazgos = len(dxf["items"]), len(dxf["hallazgos"])
    return Estado.OK, f"OF-001 limpio: {items} ítems y {hallazgos} hallazgos"


def evaluar_html_inseguro(raiz: Path, carpetas: Iterable[str]) -> tuple[Estado, str]:
    """S3-M3: ningún `unsafe_allow_html` en el código de las carpetas dadas."""
    usan = sorted(
        archivo.relative_to(raiz).as_posix()
        for carpeta in carpetas
        for archivo in (raiz / carpeta).rglob("*.py")
        if "unsafe_allow_html" in archivo.read_text(encoding="utf-8")
    )
    if usan:
        return Estado.FALLA, "usan unsafe_allow_html: " + ", ".join(usan)
    return Estado.OK, "ningún unsafe_allow_html en " + ", ".join(carpetas)


def evaluar_cobertura_en_ci(texto_ci: str | None) -> tuple[Estado, str]:
    """S3-M4: la CI declara el paso de cobertura de `seguridad/` y `paquete/`, mínimo 80."""
    if texto_ci is None:
        return Estado.PENDIENTE, "falta .github/workflows/ci.yml"
    pedido = all(c in texto_ci for c in ("seguridad/*", "paquete/*", "--fail-under=80"))
    if not pedido:
        return Estado.FALLA, "la CI no exige cobertura >= 80 % de seguridad/ y paquete/"
    return Estado.OK, "la CI exige cobertura >= 80 % de seguridad/ y paquete/"


def evaluar_ramas_sin_nucleo(ramas: Mapping[str, str | None]) -> tuple[Estado, str]:
    """S3-M5: `ramas` = rama -> salida de `git diff --stat` sobre `core/` (`None` si no se leyó).
    Sin ramas fusionadas no hay evidencia: PENDIENTE."""
    if not ramas:
        return Estado.PENDIENTE, "ninguna rama de S3-5 ni de S3-6 está fusionada todavía"
    sin_leer = [r for r, d in ramas.items() if d is None]
    if sin_leer:
        return Estado.PENDIENTE, "no se pudo leer el diff de: " + ", ".join(sin_leer)
    tocan = [r for r, d in ramas.items() if d and d.strip()]
    if tocan:
        return Estado.FALLA, "tocan core/: " + ", ".join(tocan)
    return Estado.OK, "no tocan core/: " + ", ".join(ramas)


# --- orquestación: git y disco ----------------------------------------------------------------


def _ramas_fusionadas() -> dict[str, str | None]:
    r = _git("log", "--first-parent", "--merges", "--format=%H|%P|%s")
    if r is None or r.returncode != 0:
        return {}
    ramas: dict[str, str | None] = {}
    for linea in r.stdout.splitlines():
        sha, _, resto = linea.partition("|")
        padres, _, asunto = resto.partition("|")
        if not any(rama in asunto for rama in RAMAS_SIN_NUCLEO):
            continue
        primero = padres.split()[0] if padres.split() else ""
        d = _git("diff", "--stat", primero, sha, "--", "core/")
        ramas[asunto] = d.stdout if d is not None and d.returncode == 0 else None
    return ramas


def _s3_m1(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_protocolos(RAIZ, RUTA_HUELLAS)


def _s3_m2(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_literal_of001(RUTA_LIMPIO)


def _s3_m3(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_html_inseguro(RAIZ, CARPETAS_SIN_HTML_INSEGURO)


def _s3_m4(_ctx: Contexto) -> tuple[Estado, str]:
    texto = RUTA_CI.read_text(encoding="utf-8") if RUTA_CI.is_file() else None
    return evaluar_cobertura_en_ci(texto)


def _s3_m5(_ctx: Contexto) -> tuple[Estado, str]:
    return evaluar_ramas_sin_nucleo(_ramas_fusionadas())


PARTE = Parte(
    nombre="S3 cuentas, cadena, firma, paquete y planos",
    requisitos={"S3-0": REQUISITOS_S3_0, "S3-6": ("RF-100",)},
    pares_tdd=PARES_S3,
    comprobaciones=(
        Comprobacion("S3-M1", "Huella de los dos protocolos de §13.5", "S3-0", _s3_m1),
        Comprobacion("S3-M2", "Conjunto exacto de OF-001 limpio escrito", "S3-0", _s3_m2),
        Comprobacion("S3-M3", "Ningún unsafe_allow_html", "S3-1", _s3_m3),
        Comprobacion("S3-M4", "Cobertura de seguridad/ y paquete/ en la CI", "S3-3", _s3_m4),
        Comprobacion("S3-M5", "Las ramas de planos y anomalías no tocan core/", "S3-5", _s3_m5),
    ),
)
```
  La versión 0.8.0 y sus ocho fases en `FASES`:
```diff
--- a/scripts/meta_silice.py
+++ b/scripts/meta_silice.py
@@ -61,4 +61,5 @@
 FASES: dict[str, tuple[str, ...]] = {
     "0.6.0": ("T0", "S5-1", "S1-0", "S1-1", "S1-2", "S1-3", "S1-4", "S1-5"),
+    "0.8.0": ("S3-0", "S3-1", "S3-2", "S3-3", "S3-4", "S3-5", "S3-6", "S3-7"),
 }
 
```
  La ERS (aplicar cada hunk donde lo indica su contexto; si S1 o S2 movieron el contexto, buscar el
  encabezado de la sección). RF-100 es **Deseable** y RNF-08 se enmienda una sola vez:
```diff
--- a/docs/ERS.md
+++ b/docs/ERS.md
@@ -72,4 +72,16 @@
 > llega con S3 (`instalacion.db` con tablas) y S5‑2. Los conteos los calcula la meta (maestro
 ↳ §6.1).
 
+> **Enmienda de Sílice 0.8.0 (S3‑0; spec
+> [S3](especificaciones/2026-10-11-silice-s3-auditor-paquete-design.md) §3; maestro RV‑7 a RV‑16,
+↳  RV‑20,
+> RV‑23):** se agregan **UC‑21 a UC‑23** (cuentas y sesión, entregar el paquete auditado, revisar
+↳  un
+> paquete o un presupuesto externo), **RF‑80 a RF‑89** y **RF‑100** (deseable: anomalías en las
+> variaciones de precio, fase opcional S3‑6) y los requisitos no funcionales **RNF‑16**
+↳ (seguridad) y
+> **RNF‑17** (usabilidad de quien revisa y de quien administra); los actores *administrador de la
+> instalación* y *herramienta externa* y los tres roles *arma*, *revisa* y *administrador* (§2.3).
+> Se enmiendan UC‑05, UC‑12, UC‑14 y UC‑15 (§2.2), RF‑37, RF‑42 y RF‑43 (cuatro secciones del menú,
+> visibles según el rol) y, **una sola vez**, RNF‑08 (las únicas credenciales son las cuentas
+↳ locales;
+> la redacción final con todas sus excepciones se consolida en S5‑0). Los RF y RNF nuevos quedan
+> **sin implementar** hasta su fase (columna «Incremento»).
+
 | Campo | Valor |
 |---|---|
@@ -670,4 +682,98 @@
   no modifica el presupuesto.
 
+#### UC‑21 — Iniciar sesión y administrar cuentas y claves
+
+- **Actor principal:** cualquier usuario (entrar); administrador de la instalación (administrar).
+- **Precondiciones:** instalación con al menos un administrador, o código de instalación vigente
+↳ (21a).
+- **Flujo principal**
+  1. El usuario abre Sílice; la pantalla de acceso pide usuario y contraseña. Si el cliente no es
+↳  el propio equipo,
+     muestra el aviso «Conexión sin cifrar» (§5.6).
+  2. El sistema verifica la contraseña (Argon2), crea una **ficha de sesión nueva**, lee los
+↳ roles de la base y
+     muestra el menú que esos roles permiten.
+  3. El administrador abre Administración: da de alta una persona con sus roles y una contraseña
+↳ temporal, o cambia
+     roles, desactiva, desbloquea o restablece una cuenta.
+  4. El sistema registra cada acción en `evento_acceso` (sin secretos) y, al cambiar roles,
+↳ desactivar o restablecer
+     una cuenta, **cierra todas sus sesiones abiertas**.
+  5. El usuario cierra sesión; la ficha queda cerrada.
+- **Flujos alternativos**
+  - *21a. Primera vez:* no hay usuarios; se crea el primer administrador con el código de
+↳ instalación (§5.5).
+  - *21b. Contraseña errónea o usuario inexistente:* «Usuario o contraseña incorrectos», el mismo
+↳  mensaje y el mismo
+    contador en los dos casos.
+  - *21c. Cuenta bloqueada por intentos:* mensaje de §5.4; el mismo para un usuario inexistente.
+  - *21d. Sesión expirada:* vuelve al acceso **conservando el borrador** para el mismo usuario.
+  - *21e. Contraseña temporal:* obliga a cambiarla; al cambiarla se emite una ficha nueva.
+  - *21f. El administrador desactiva, desbloquea o restablece una cuenta.*
+  - *21g. El administrador genera, retira o revoca la clave de firma de la empresa* (solo desde
+↳ el propio equipo).
+  - *21h. Registra o revoca la clave pública de otra empresa,* con su huella comprobada (§7.3).
+  - *21i. Muchos fallos seguidos desde cualquier pestaña:* freno global con espera progresiva
+↳ (§5.4).
+  - *21j. Operación sensible pedida desde otro equipo de la red* (firmar, generar o exportar la
+↳ clave de firma,
+    crear claves de API): se rechaza con «Esta operación solo se hace en el equipo donde está
+↳ instalado Sílice».
+- **Postcondiciones:** sesión vigente con usuario y roles leídos de la base; todo intento y toda
+↳ acción de
+  administración en `evento_acceso`; ningún secreto en claro en la base, en el registro ni en los
+↳  mensajes.
+
+#### UC‑22 — Entregar el paquete auditado
+
+- **Actor principal:** quien arma. Para firmar hace falta la contraseña de la clave, que conoce
+↳ **solo** el
+  administrador (maestro §4.1, P1, ratificada por Eugenio el 2026‑10‑11): en una empresa pequeña
+↳ es la misma
+  persona con los dos roles, o el administrador la teclea.
+- **Precondiciones:** versión guardada y sellada; clave de firma de la empresa activa (si no,
+↳ 22a); cliente en el
+  propio equipo para firmar (22e).
+- **Flujo principal**
+  1. Quien arma abre la pantalla **Entregar paquete** (sección Trabajo) y elige el proyecto y la
+     versión.
+  2. El sistema verifica la cadena del proyecto (22c) y muestra el resumen: total, hallazgos por
+↳ severidad, cadena,
+     empresa emisora y anexos que viajarán (espacio, reajuste, control, IA).
+  3. El usuario elige, si quiere, el **destinatario** (una empresa registrada o un nombre) y
+↳ escribe la contraseña
+     de la clave.
+  4. El sistema genera en memoria `presupuesto.json`, `informe.json`, `cadena.json` y los anexos,
+↳  el manifiesto con
+     su `paquete_id` y su `huella_anexos`, y la firma con separación de dominio (§8.1).
+  5. El usuario descarga el `.silice`; el sistema guarda su SHA‑256, su `paquete_id`, la versión
+↳ y el usuario en
+     `evento_acceso`.
+- **Flujos alternativos**
+  - *22a. Sin clave de empresa:* se ofrece exportar **sin firma**, declarado en el paquete.
+  - *22b. Contraseña de la clave errónea:* mensaje, no se escribe nada.
+  - *22c. La cadena del proyecto está rota:* se rechaza la entrega y se dice en qué versión.
+  - *22d. La versión tiene hallazgos ERROR:* se avisa y se entrega igual (el informe viaja).
+  - *22e. Firma pedida desde otro equipo de la red:* se rechaza con el mensaje de 21j; se puede
+↳ exportar sin firma.
+  - *22f. El paquete excedería los límites de §8.4:* se rechaza con el motivo; no se genera un
+↳ paquete que el
+    revisor rechazaría.
+- **Postcondiciones:** un `.silice` descargado; su SHA‑256 y su `paquete_id` en `evento_acceso`;
+↳ la base del caso no
+  cambia.
+
+#### UC‑23 — Revisar un paquete o un presupuesto externo
+
+- **Actor principal:** quien revisa. **Secundario:** herramienta externa (23e).
+- **Precondiciones:** sesión con rol *revisa*, o clave de API vigente (23e).
+- **Flujo principal**
+  1. Quien revisa sube el `.silice` (o un Excel con el formato UC‑05, 23d).
+  2. El sistema lo abre con límites (§8.4), verifica formato, integridad, autenticidad, cadena y
+↳ anterioridad, y
+     muestra el estado con el banner de versión (§8.3).
+  3. El sistema reaudita en memoria con sus propias reglas y los anexos (§9, paso 3).
+  4. Muestra la **diferencia entre versiones** y su costo frente a la entrega anterior o frente a
+↳  su base de precios
+     (§9, paso 4).
+  5. Muestra quién cambió qué y, si quien revisa es también quien armó (usuario emisor o
+↳ responsable de algún
+     eslabón de la cadena del paquete), lo indica (§9, paso 5).
+  6. Quien revisa registra su dictamen; el sistema lo guarda atado al SHA‑256 del archivo y con
+↳ el estado de
+     verificación de ese momento.
+- **Flujos alternativos**
+  - *23a. Sin firma o empresa no registrada:* **no verificado**, se audita igual.
+  - *23b. Alterado (huella o firma no cuadran):* banner rojo, se audita igual para mostrar qué
+↳ cambió.
+  - *23c. El paquete es anterior a uno ya recibido o reescribe su historia* (§6.4).
+  - *23d. Presupuesto externo en Excel (formato UC‑05):* solo se reaudita; «no contrastable» lo
+↳ que no se puede
+    verificar.
+  - *23e. La herramienta externa manda el presupuesto por la API* y recibe el informe.
+  - *23f. Formato o versión del paquete desconocidos:* se rechaza con mensaje.
+  - *23g. El destinatario es otra empresa:* aviso ámbar «Este paquete se emitió para *X*».
+  - *23h. El mismo archivo ya se recibió (mismo SHA‑256):* se abre el registro existente, no se
+↳ duplica.
+- **Postcondiciones:** `paq_recibido` con el SHA‑256 del archivo, su `paquete_id`, su estado y su
+↳  cadena;
+  `paq_dictamen` si se dictaminó, con quién revisó y si coincide con quien armó; nada escrito en
+↳ el catálogo ni en las versiones del caso.
+
+**UC existentes que se enmiendan por S3 (Sílice 0.8.0).**
+
+**UC‑05** (el auditor puede auditar en memoria, sin persistir, desde la vista de revisión; la
+↳ importación
+persistente sigue igual); **UC‑14** (la importación del plano corre la auditoría de archivo DXF,
+↳ el IDS del IFC y las
+reglas R15 y R16); **UC‑15** (el responsable es el usuario de la sesión, no una caja de texto);
+↳ **UC‑12** (los
+recorridos se filtran por rol).
+
 ### 2.3 Características de los usuarios
 
@@ -680,4 +786,7 @@
 | Gerente | decide sobre el presupuesto de un proyecto —no lo edita— y consulta el punto de
 ↳ equilibrio y los totales de la hoja | UC‑16 |
 | Usuario nuevo / evaluador | abre la aplicación por primera vez —tribunal, tutor o
 ↳ presupuestista recién llegado— y necesita orientarse sin formación previa | UC‑12 |
+| Administrador de la instalación | crea cuentas y les da roles; administra la clave de firma de
+↳ la empresa, la empresa propia, las empresas registradas, la red local y las claves de la API; rol
+↳  *administrador* | UC‑21 |
+| Quien revisa | recibe el paquete de otra empresa o de otra área (administrador del contrato,
+↳ cliente, ente contratante, auditor, gerente): lo verifica, lo reaudita, compara y dictamina; rol
+↳ *revisa* | UC‑23 |
+| Herramienta externa | un plugin o programa que llama a la API de Sílice con su **clave de API**
+↳  y recibe el informe; sin rol | UC‑23 |
 
 ### 2.4 Restricciones
@@ -788,11 +897,11 @@
 | RF‑35 | El precio sugerido desde la referencia de mercado es editable por quien presupuesta |
 ↳ Esencial | UC‑10 | P2.3 | El precio sugerido queda en un campo editable y
 ↳ `core.costing.calcular_apu` refleja el precio editado, no el sugerido |
 | RF‑36 | La interfaz abrirá en la pantalla de Inicio, cualquiera que sea el orden del resto del
 ↳ menú | Esencial | UC‑12 | U1 | El Inicio es la página por defecto por identidad, no por posición,
 ↳  y la ruta vacía que Streamlit da a la página por defecto se traduce a `inicio` |
-| RF‑37 | Los recorridos guiados se declararán una sola vez, en un módulo sin Streamlit ni base
-↳ de datos, y el destino de cada paso será la ruta de una página registrada | Esencial | UC‑12 | U1
-↳  | Una sola declaración de recorridos, sin Streamlit ni base de datos; todo `paso.pagina` es la
-↳ ruta de una página visible, con y sin modo entrega; desde el sprint final los recorridos incluyen
-↳  la pantalla «Hoja del proyecto» |
+| RF‑37 | Los recorridos guiados se declararán una sola vez, en un módulo sin Streamlit ni base
+↳ de datos, y el destino de cada paso será la ruta de una página registrada | Esencial | UC‑12 | U1
+↳  | Una sola declaración de recorridos, sin Streamlit ni base de datos; todo `paso.pagina` es la
+↳ ruta de una página visible **para el rol de la sesión**, con y sin modo entrega (S3 filtra los
+↳ pasos que el rol no ve); desde el sprint final los recorridos incluyen la pantalla «Hoja del
+↳ proyecto» |
 | RF‑38 | El archivo de la base se fijará una vez por sesión y todas las pantallas operarán sobre
 ↳  ese mismo caso; ninguna pantalla distinta del Inicio pedirá la ruta | Esencial | UC‑12 | U1 |
 ↳ Resolución sesión → entorno → constante, `RUTA_BASE_POR_DEFECTO` definida una sola vez en `ui/`,
 ↳ y ninguna página salvo el Inicio pide la ruta |
 | RF‑39 | El sistema mostrará en toda pantalla, en solo lectura, el caso abierto y su estado:
 ↳ existencia del archivo, número de partidas, número de insumos y si hay lista de precios vigente |
 ↳  Esencial | UC‑12 | U1 | El estado es correcto sobre una base inexistente, vacía, sembrada e
 ↳ ilegible, sin traza, y el marco lo pinta en cada una de las once pantallas (diez hasta el sprint
 ↳ final, más la «Hoja del proyecto») |
 | RF‑40 | Cuando el caso abierto no exista o no contenga partidas, el Inicio lo declarará y
 ↳ ofrecerá cargar el caso de demostración, sin exponer nunca la opción de reiniciar la base |
 ↳ Esencial | UC‑12 | U1 | Estado vacío, siembra, y ningún botón de sembrar con partidas; el literal
 ↳  del flag de reinicio no aparece en ningún archivo de `ui/` |
 | RF‑41 | Cada pantalla del recorrido activo mostrará su paso siguiente y la posición del usuario
 ↳  en el recorrido, tomados de la declaración única de recorridos; una pantalla que no pertenezca a
 ↳  ningún recorrido no mostrará ninguno de los dos | Deseable | UC‑12 | U1 | `paso_siguiente` y la
 ↳ posición del recorrido salen de la declaración única; el botón «Siguiente» lleva a su destino y
 ↳ una pantalla fuera del recorrido no lo muestra |
-| RF‑42 | El menú presentará cada pantalla con el nombre de su oficio, agrupada en dos secciones
-↳ —Trabajo e Investigación— en el orden del trabajo real; el código del caso de uso permanecerá
-↳ visible como subtítulo; desde el sprint final la «Hoja del proyecto» forma parte de la sección
-↳ Trabajo | Deseable | UC‑12 | U1 | Secciones y orden sin Streamlit, con las once pantallas; ningún
-↳  título lleva código de UC; el subtítulo «Caso de uso …» aparece en las cinco pantallas que
-↳ tienen uno |
-| RF‑43 | Con el modo entrega activo, ninguna pantalla de Trabajo quedará inaccesible | Esencial
-↳ | UC‑12 | U1 | La sección Trabajo es idéntica con y sin modo entrega, y ningún paso de un
-↳ recorrido sale de Trabajo |
+| RF‑42 | El menú presentará cada pantalla con el nombre de su oficio, agrupada en cuatro
+↳ secciones —Trabajo, Revisión, Investigación y Administración— en el orden del trabajo real,
+↳ **visibles según el rol de la cuenta** (S3); el código del caso de uso permanecerá visible como
+↳ subtítulo; desde el sprint final la «Hoja del proyecto» forma parte de la sección Trabajo |
+↳ Deseable | UC‑12 | U1 | Secciones y orden sin Streamlit, con las once pantallas; ningún título
+↳ lleva código de UC; el subtítulo «Caso de uso …» aparece en las cinco pantallas que tienen uno |
+| RF‑43 | Con el modo entrega activo, ninguna pantalla de Trabajo **que el rol de la cuenta
+↳ permita** quedará inaccesible | Esencial | UC‑12 | U1 | La sección Trabajo es idéntica con y sin
+↳ modo entrega, y ningún paso de un recorrido sale de Trabajo; el modo entrega solo oculta
+↳ Investigación |
 | RF‑44 | La hoja de metrajes registrará ambientes, fuentes, puntos, recorridos y orígenes de
 ↳ medida (spec §6.2) | Esencial | UC‑13 | SF1 | Cada tipo de origen exige su referencia (spec
 ↳ §6.3); faltando una, la fila se acepta en la versión y R8 la marca ERROR *La hoja edita orígenes,
 ↳  ambientes, fuentes, puntos y vértices declarados; los circuitos y las sobrescrituras de segmento
 ↳  se conservan pero no se editan.* **Alcance vigente: parcial.** No editable en la hoja
 ↳ (circuitos, sobrescrituras de segmento y orden de la cadena solo se declaran al importar un plano
 ↳  o por la API); limitación vigente. |
 | RF‑45 | El sistema propondrá un recorrido para cada punto (spec §6.4) y el usuario lo
 ↳ reemplazará declarando vértices | Esencial | UC‑13 | SF1 | Las longitudes del recorrido propuesto
 ↳  del baño de OF‑001 igualan la memoria de cálculo; un recorrido declarado sustituye al propuesto
 ↳ |
@@ -816,4 +925,15 @@
 | RF‑63 | La interfaz creará proyectos con nombre único y no vacío | Esencial | UC‑01 | SF4 |
 ↳ Nombre vacío o repetido se rechaza con mensaje |
 | RF‑96 | **Migraciones con respaldo y vuelta atrás, en dos bases.** El esquema se versiona con
 ↳ Alembic en dos destinos, cada uno con su `alembic_version` y su lista `METADATAS` explícita: la
 ↳ **instalación** (`seguridad`) y el **caso** (`core.models`, `METADATA_ESPACIO`, `paquete`,
 ↳ `asistente`). La revisión base del caso es el esquema de la 0.5.0 y cada cambio posterior trae su
 ↳  revisión, desde la 0.6.0. Antes de aplicar cualquier revisión pendiente se respaldan **juntas**
 ↳ la instalación y los casos que se migran, en un juego con una sola ficha; si la migración falla,
 ↳ la base no queda modificada. Las bases de la 0.5.0 se adoptan. Un caso se abre solo con
 ↳ `preparar_base` y desde `datos\casos\` | Esencial | UC‑24 (S5‑0) | S5‑1 (0.6.0) | (a) una base
 ↳ vacía, una base de la 0.5.0 sin `alembic_version` y la base de prueba de cada versión 0.6.0…0.9.0
 ↳  (generada en su compuerta con el código de su etiqueta) llegan a `head` y sus presupuestos
 ↳ recargan con el total literal, la huella del informe y las filas por tabla de su ficha; lo mismo
 ↳ para `instalacion.db` desde la 0.8.0; (b) cada base del juego de respaldo pasa `PRAGMA
 ↳ integrity_check` y su huella está en la ficha; (c) con un fallo inyectado en una revisión, la
 ↳ huella SHA‑256 de cada base tras el intento es igual a la de antes; (d) una base con revisión
 ↳ desconocida o no adoptable no se modifica (huella igual) y el mensaje dice qué hacer; (e) una
 ↳ ruta UNC, absoluta o con `..` se rechaza sin crear archivo, y `estado_caso` no emite DDL; (f)
 ↳ restaurar un juego con `instalacion.db` lista los eventos de seguridad perdidos y deja pendiente
 ↳ la revisión del administrador |
+| RF‑80 | Cuentas locales con roles *arma*, *revisa* y *administrador de la instalación* (uno o
+↳ varios por cuenta) y la matriz de §5.1; contraseñas con Argon2; el primer administrador se crea
+↳ solo con el **código de instalación** de un solo uso, de al menos 100 bits | Esencial | UC‑21 |
+↳ S3‑1 | sin código o con código usado se rechaza; el código tiene 20 caracteres base32; ninguna
+↳ contraseña aparece en la base, en el registro de accesos ni en los mensajes; cada página y cada
+↳ acción de la matriz rechaza un rol que no le corresponde aunque se llegue por URL |
+| RF‑81 | Sesión propia en Streamlit: expira por inactividad (30 min) y por antigüedad (12 h);
+↳ ficha nueva al entrar y al cambiar la contraseña; todas las sesiones de una cuenta se cierran al
+↳ restablecerla, desactivarla o cambiar sus roles; roles leídos de la base en cada ejecución;
+↳ bloqueo tras 5 intentos fallidos seguidos durante 15 min, con el mismo contador y mensaje para
+↳ usuarios inexistentes; freno global con espera progresiva; cierre de sesión; varios usuarios a la
+↳  vez sin mezclar estado | Esencial | UC‑21 | S3‑1 | reloj inyectado: 29:59 sigue, 30:00 expira; 4
+↳  fallos no bloquean, el 5.º sí, con un login existente y con uno inexistente; cambiar los roles
+↳ en la base cambia el menú en la ejecución siguiente; dos sesiones AppTest con usuarios distintos
+↳ no comparten borrador ni caso; prueba de concurrencia de §13.4 |
+| RF‑82 | El responsable de todo `RegistroCambio`, de todo eslabón y de **todo campo
+↳ `responsable`** de las tablas de S1 y S2 (`importacion_indice`, `moneda_proyecto`,
+↳ `clausula_reajuste`, `estudio_reajuste`, `linea_base_control`, `valuacion`, `anulacion_valuacion`, `costo_real`,
+↳ `decision_recuperacion`) es el **usuario autenticado**, congelado como `Nombre <login>` en el
+↳ momento del cambio; la caja «Responsable» desaparece de la hoja y de las pantallas de S1 y S2 |
+↳ Esencial | UC‑15, UC‑21 | S3‑1 | guardar, restaurar, cotizar, convertir, decidir una
+↳ recuperación, crear la primera versión, asegurar la instantánea, importar índices, registrar
+↳ valuaciones, anulaciones y costos reales registran al usuario de la sesión; una prueba recorre
+↳ los metadatos y lista **toda** columna `responsable`: cada una tiene su prueba, y una columna
+↳ nueva sin prueba hace fallar la lista; ningún camino de `ui/` pasa `"sistema"`; desactivar una
+↳ cuenta no cambia sus registros |
+| RF‑83 | Registro encadenado: cada versión nueva, que nace en el embudo `guardar_presupuesto`,
+↳ se sella **al confirmar la transacción que la crea** (evento `before_commit`, §6.2) y en esa
+↳ misma transacción, con un eslabón SHA‑256 que encadena su contenido, sus `RegistroCambio`, sus
+↳ anexos y el eslabón anterior (§6); el sellado es una invariante de **todo** `MOTIVOS_VERSION`
+↳ (incluidos `conversion` de S1 y `recuperacion` de S2) y del motivo vacío (versión sin origen);
+↳ las versiones anteriores se sellan una vez de forma **retroactiva** y declarada; el sistema
+↳ verifica la cadena | Esencial | UC‑15, UC‑22 | S3‑2 | una prueba recorre la tupla
+↳ `MOTIVOS_VERSION` y el motivo vacío, y crea una versión de cada uno; otra enumera a **todos** los
+↳  llamadores del embudo (§1.2) y falla si aparece uno nuevo sin prueba; cambiar un byte de una
+↳ partida, de un registro, de un anexo o de un eslabón en la base rompe la cadena **en esa
+↳ versión** y lo dice; una versión posterior al génesis sin eslabón es un error de cadena;
+↳ confirmar una versión sin usuario se rechaza; guardar y recargar no cambia ninguna huella |
+| RF‑84 | Clave de firma de la empresa Ed25519 generada en el equipo, con la privada **cifrada
+↳ con su propia contraseña** por `seguridad/secretos.py` (Argon2id → AES‑GCM, maestro §4.4); huella
+↳  corta legible (§7.2); registro de claves públicas de otras empresas con la comprobación de su
+↳ huella; retiro (se destruye la privada) y revocación; separación de dominio en todo lo que se
+↳ firma | Esencial | UC‑21 | S3‑3 | la privada nunca aparece sin cifrar en disco ni en el paquete;
+↳ contraseña de clave errónea da `InvalidTag` y un mensaje sin traza; una contraseña de la lista
+↳ corta de comunes se rechaza; la huella es la misma en las dos instalaciones; al retirar, la
+↳ privada deja de existir en la base; una clave revocada deja de verificar |
+| RF‑85 | Exportar el paquete auditado (§8): documento canónico (con moneda del proyecto y
+↳ `precio_origen`), informe, cadena, anexos (`espacio`, `reajuste`, `control`, `ia`), manifiesto
+↳ con `paquete_id`, `destinatario` opcional y `huella_anexos`, y firma; **sin Excel**; el emisor
+↳ guarda el SHA‑256 de cada paquete exportado; firmar solo desde el propio equipo | Esencial |
+↳ UC‑22 | S3‑3 | el paquete exportado se verifica como «Verificado» en otra base con la clave
+↳ registrada; sin clave se exporta «sin firma» y así se declara; la cadena rota impide exportar; el
+↳  SHA‑256 del archivo descargado está en `evento_acceso`; una firma pedida desde una IP que no es
+↳ de bucle local se rechaza |
+| RF‑86 | Importar y verificar un paquete: límites leídos con tope (§8.4), integridad (huellas
+↳ del manifiesto), autenticidad (firma de una empresa registrada y no revocada, con separación de
+↳ dominio), cadena, posición respecto de paquetes ya recibidos y banner de versión; **siempre** se
+↳ reaudita con las reglas propias | Esencial | UC‑23 | S3‑4 | cada caso de §13.3 da su estado
+↳ declarado, con las fronteras exactas de §8.4; un paquete no verificado se audita igual; ninguna
+↳ entrada del ZIP sale de su carpeta ni excede los límites; el banner dice la versión y la última
+↳ recibida |
+| RF‑87 | Vista de revisión: estado de verificación, reauditoría con los anexos (R11–R14
+↳ recomputadas, R12 a la fecha de emisión), **diferencia entre versiones** y su costo (desvío por
+↳ cantidad y por precio) frente a la entrega anterior y frente a la base de precios del revisor,
+↳ Excel regenerado desde `presupuesto.json`, dictamen atado al SHA‑256 del archivo y aviso cuando
+↳ quien revisa es quien armó (maestro §4.1, P2) | Esencial | UC‑23 | S3‑4 | con el par de
+↳ presupuestos de la memoria de diferencias (§13.1) la vista da los montos de la memoria; R11–R14
+↳ del paquete de prueba dan el conjunto exacto de su memoria; el dictamen queda con usuario, fecha,
+↳  SHA‑256 del archivo, estado de verificación y `revisor_armo`; con un paquete de la empresa
+↳ propia, un revisor que es el usuario emisor o el `usuario` de un eslabón ve el aviso y su
+↳ dictamen queda con `revisor_armo` = sí; otro revisor de la misma empresa, o un paquete de una
+↳ empresa ajena, no lo ve |
+| RF‑88 | APU de otras herramientas: Excel con el formato UC‑05 (plantilla descargable) auditado
+↳ en memoria desde la vista de revisión, y ruta `POST /v1/auditorias` con **clave de API** que
+↳ recibe el documento canónico (§6.1) y devuelve el informe; cuerpo limitado por un middleware;
+↳ `TrustedHostMiddleware` | Esencial | UC‑23, UC‑05 | S3‑4 | Excel con partidas del catálogo se
+↳ audita sin el rechazo de `importacion.py:208`; sin clave o con clave revocada, 401 sin auditar;
+↳ cuerpo de 20 MiB pasa y de 20 MiB + 1 B da 413 sin leerlo entero; con clave, el informe coincide
+↳ con el de la vista |
+| RF‑89 | Auditoría de planos: auditoría de archivo DXF, requisitos IDS del IFC con `ifctester`,
+↳ R15 (coherencia geométrica, `shapely`, severidad por condición), R16 (contraste entre dos
+↳ fuentes, con el costo de la diferencia) y evaluación por **errores sembrados** con el protocolo
+↳ de §13.5 | Esencial | UC‑14 | S3‑5 | cada error del catálogo sembrado se detecta con la regla o
+↳ el ítem de informe declarados; cada fila de R15 y R16 cumple sus fronteras (§11.3, §11.4); OF‑001
+↳  limpio da el conjunto exacto escrito en S3‑0; la tasa de detección y las falsas alarmas cumplen
+↳ la meta del protocolo: 100 % de lo detectable y 0 falsas alarmas (ratificada por Eugenio el
+↳ 2026‑10‑11, pregunta P8 del maestro §10.3) |
+| RF‑100 | Anomalías en variaciones de precio: sobre la serie fechada de precios de un insumo
+↳ (listas de la empresa de S1, RF‑67, y listas MaPreX, cada precio con su fecha), llevada a USD con
+↳  la tasa de cada precio (RF‑65) y reducida a variaciones entre puntos consecutivos, el sistema
+↳ marca las variaciones atípicas como **ADVERTENCIA** (`CODIGO_ATIPICO`), **nunca ERROR**,
+↳ reutilizando el detector existente `ml.anomaly.precios_atipicos` (Isolation Forest, `SEMILLA` =
+↳ 42, `UMBRAL_ATIPICO` = −0,05, se abstiene con menos de `MINIMO_OBSERVACIONES` = 8 variaciones) |
+↳ Deseable | UC‑17, UC‑23 | S3‑6 | serie sembrada de 10 precios (9 variaciones) con **un** atípico
+↳ sembrado → el conjunto exacto de hallazgos es ese único punto, con severidad ADVERTENCIA; serie
+↳ de 10 precios **sin** atípico → conjunto vacío; serie de 8 precios (7 variaciones) → abstención
+↳ (vacío); ningún hallazgo de RF‑100 es ERROR ni bloquea guardar, exportar o firmar; sin el extra
+↳ `ml` no hay hallazgo ni traza |
 
 Los criterios de esta tabla son afirmaciones comprobables y no llevan estado. **La prueba que
@@ -846,4 +966,7 @@
 | UC‑15 | RF‑52, RF‑53, RF‑54, RF‑55, RF‑56, RF‑57, RF‑59, RF‑61, RF‑62 | 9 (sin mínimo
 ↳ declarado; UC nuevo, Sesión SF0) |
 | UC‑16 | RF‑58 | 1 (sin mínimo declarado; UC nuevo, Sesión SF0) |
+| UC‑21 | Iniciar sesión y administrar cuentas y claves | S3‑0 (declarado), S3‑1, S3‑3 |
+| UC‑22 | Entregar el paquete auditado | S3‑0 (declarado), S3‑3 |
+| UC‑23 | Revisar un paquete o un presupuesto externo | S3‑0 (declarado), S3‑4 |
 | Transversales | RF‑60 (todos los UC); RF‑63 (UC‑01); RF‑62 (también UC‑05); RF‑56 (también
 ↳ UC‑02 y UC‑07) | — |
 | **Total** | RF‑01 … RF‑31, RF‑33 … RF‑63 (RF‑32 vacante — reservado a UC‑09; RF‑03 traza a dos
 ↳ UC; RF‑33 y RF‑34 trazan a UC‑10 y UC‑11; RF‑56, RF‑61 y RF‑62 trazan a más de un UC) | **62** |
@@ -860,5 +983,5 @@
 | Mantenibilidad | RNF‑06 cobertura de pruebas del núcleo | pytest‑cov | ≥ 80 % |
 | Portabilidad | RNF‑07 instalación con `uv sync` en Windows y Linux | pasos manuales | 0 |
-| Seguridad | RNF‑08 ejecución local: el sistema no requiere credenciales, no invoca servicios
-↳ externos en tiempo de ejecución y los datos residen en un archivo SQLite del equipo del usuario |
-↳  credenciales versionadas; llamadas de red durante la operación | 0 y 0, con dos excepciones
-↳ declaradas: la descarga inicial del modelo de `sentence-transformers` (I2), del lado del
-↳ servidor, que se cachea localmente; y la biblioteca three.js (`r128`), que el navegador descarga
-↳ de `cdnjs.cloudflare.com` cada vez que se abre el Visor 3D (`URL_THREE_JS` en
-↳ `ui/paginas/visor.py`), sin caché propia del sistema (INV‑077) |
+| Seguridad | RNF‑08 ejecución local: el sistema no requiere servicios externos ni credenciales
+↳ de terceros, no invoca servicios externos en tiempo de ejecución y los datos residen en un
+↳ archivo SQLite del equipo del usuario; las únicas credenciales son **locales**: las cuentas de la
+↳  instalación (S3), guardadas en el propio equipo (enmienda única de la 0.8.0; la redacción final
+↳ con todas sus excepciones, en S5‑0) | credenciales versionadas; llamadas de red durante la
+↳ operación | 0 y 0, con dos excepciones declaradas: la descarga inicial del modelo de
+↳ `sentence-transformers` (I2), del lado del servidor, que se cachea localmente; y la biblioteca
+↳ three.js (`r128`), que el navegador descarga de `cdnjs.cloudflare.com` cada vez que se abre el
+↳ Visor 3D (`URL_THREE_JS` en `ui/paginas/visor.py`), sin caché propia del sistema (INV‑077) |
 | Compatibilidad | RNF‑09 entrada IFC 4 de cualquier modelador | archivos de ≥ 2 herramientas (p.
 ↳  ej. Revit y Bonsai) | cantidades extraídas iguales al cálculo manual en ambos; la compuerta G1
 ↳ (I3.1) se cruzó con salvedad sobre un modelo generado programáticamente (sección 2.5); faltan los
 ↳  exports de dos modeladores, y la alternativa declarada es la entrada tabular |
 | Usabilidad | RNF‑10 capacidad de aprendizaje de la interfaz: una persona que nunca vio la
 ↳ aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de auditoría | caso con
 ↳ persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)) y bloque B del anexo A de
 ↳ [dossier_g0.md](dossier_g0.md) | en cada uno de los dos escenarios de CP‑07 (CP‑07 pasa solo si
 ↳ pasan ambos): sin ayuda, ≤ 20 min, bloque B ≥ 4,0 y ningún ítem < 3 |
@@ -867,4 +990,6 @@
 | Usabilidad | RNF‑13 capacidad de uso de la hoja: en las condiciones de CP‑07, con el **mismo
 ↳ número y perfil** de participantes que CP‑07 pero **personas distintas**, cada caso de CP‑08 a
 ↳ CP‑11 se completa sin ayuda | guion de pruebas con personas, en la fase Med; consigna, paradas y
 ↳ criterio fijados antes de medir | ≤ 15 min por todos los participantes, bloque B ≥ 4,0 y ningún
 ↳ ítem < 3; veredicto por caso. El costo en participantes se suma al plan de Med |
 | Mantenibilidad | RNF‑20 cero deriva de esquema en cada destino: una base llevada a `head` por
 ↳ las migraciones es igual a la creada con `create_all` de sus `METADATAS`, la autogeneración de
 ↳ Alembic contra ella no propone cambios, toda `MetaData` con tablas está en la lista de su destino
 ↳  y cada revisión baja y vuelve a subir | `tests/integration/test_migraciones.py` en Linux y
 ↳ Windows en cada PR | deriva 0 en los dos destinos, desde la 0.6.0 |
+| Seguridad | RNF‑16 Contraseñas de cuenta solo como Argon2 (parámetros por defecto de
+↳ `argon2-cffi`, con semáforo); clave privada solo cifrada con `seguridad/secretos.py`; ningún
+↳ secreto en registros, mensajes ni paquete; el 100 % de las alteraciones de §13.3 detectadas;
+↳ ninguna página, acción ni ruta nueva accesible sin sesión, rol o clave; operaciones sensibles
+↳ solo desde el propio equipo; límites del ZIP, del JSON y de la API (§8.4); texto ajeno siempre
+↳ por `texto_seguro()`; mensajes sin traza | pruebas de §13.3 y §13.4; revisión por el encargo de
+↳ seguridad con la tabla de amenazas (§12) | todas las pruebas de §13.3 y §13.4 del spec S3 en
+↳ verde |
+| Usabilidad | RNF‑17 En las condiciones de CP‑07, con personas que no son el autor: (a) quien
+↳ revisa abre un paquete y dice su estado de verificación y quién lo emitió, sin ayuda, en ≤ 5 min;
+↳  (b) encuentra las diferencias sembradas de CP‑R1 en ≤ 20 min; (c) quien administra registra la
+↳ clave de otra empresa comprobando su huella por teléfono en ≤ 10 min; bloque B ≥ 4,0, ningún ítem
+↳  < 3 | guion en Med, con consigna, paradas y criterio fijados antes de medir. El **indicador del
+↳ administrador** (horizonte §6.1) no se reduce a RNF‑17: se mide con su propio protocolo de dos
+↳ condiciones (§13.5 a) | bloque B ≥ 4,0 y ningún ítem < 3, en los tiempos de la medición |
 
 ### 3.4 Reglas de negocio
@@ -902,4 +1027,7 @@
 | UC‑16 | RF‑58 | SF0 (declarado), SF3 | prototipo de entrega AREN.IA (hoy Sílice), fuera de los
 ↳ cinco indicadores |
 | Transversal | RF‑60 | SF4 | prototipo de entrega AREN.IA (hoy Sílice), fuera de los cinco
 ↳ indicadores |
+| UC‑21 | RF‑80, RF‑81, RF‑82, RF‑84 | S3‑0 (declarado), S3‑1, S3‑3 | fuera de los cinco
+↳ indicadores (seguridad de la entrega, S3) |
+| UC‑22 | RF‑83, RF‑84, RF‑85 | S3‑0 (declarado), S3‑2, S3‑3 | fuera de los cinco indicadores
+↳ (seguridad de la entrega, S3) |
+| UC‑23 | RF‑86, RF‑87, RF‑88, RF‑89, RF‑100 | S3‑0 (declarado), S3‑4, S3‑5, S3‑6 | indicador del
+↳  administrador (horizonte §6.1) |
 
 Correspondencia RNF → verificación: RNF‑01 y RNF‑02 se comprueban en UC‑01 y UC‑02 (RF‑06, RF‑14);
@@ -910,5 +1038,7 @@
 (fase Med) de [PLAN_UI.md](../PLAN_UI.md); RNF‑11 en UC‑15 (RF‑52), con `scripts/medir_rnf11.py`
 (SF3); RNF‑12 en UC‑14 y UC‑15 (RF‑50, RF‑51 y RF‑59), por pruebas por caso; RNF‑13 en UC‑13 a
-UC‑16, con los casos con personas CP‑08 a CP‑11 de la fase Med. RNF‑04 y RNF‑10 son requisitos
+UC‑16, con los casos con personas CP‑08 a CP‑11 de la fase Med. RNF‑16 en UC‑21 a UC‑23 (RF‑80 a
+↳ RF‑89), con las pruebas de seguridad de
+S3 (§13.3 y §13.4 del spec) y la revisión del encargo de seguridad; RNF‑17 en UC‑23, con los casos
+con personas CP‑R1 y CP‑R2 de la fase Med. RNF‑04 y RNF‑10 son requisitos
 distintos, con mediciones distintas. El resultado de cada verificación está en [plan_pruebas.md
 ↳ §9](plan_pruebas.md#9-trazabilidad-rnf--verificación).
 
```
  Los dos protocolos de medición de §13.5 y la lista congelada del primero (RP8-18). Se escriben
  completos **antes** de medir; cambiarlos después exige una versión 2 con su huella:
**`docs/protocolo_indicador_administrador.md`**
```markdown
# Protocolo de medición: el indicador de quien revisa (S3 §13.5 a; horizonte §6.1)

Versión 1, escrita en S3-0 **antes** de la fase Med (maestro §7). Su huella SHA-256 está en
[`protocolos_s3.json`](protocolos_s3.json); la meta (`S3-M1`) la vigila. Cambiar algo exige una
versión 2 con su huella. CP-R1 («revisar un paquete con diferencias sembradas») es la condición
«con el sistema» de este protocolo, y el criterio (b) de RNF-17 se mide en esa misma sesión.

## 1. Qué se mide

Si Sílice ayuda a quien revisa a encontrar las diferencias entre dos entregas de un presupuesto
mejor que hacerlo **a mano**, con el Excel de cada entrega. Dos medidas, más el tiempo:

* **Tasa de detección** = diferencias sembradas que la persona reporta ÷ diferencias sembradas.
* **Falsas alarmas** = diferencias que reporta y no están en la lista congelada ÷ las que reporta.
* **Tiempo** hasta que dice «terminé» (tope de 30 minutos por condición), con cronómetro.

## 2. Material (se fija y se congela antes de medir)

* La obra y el presupuesto base son los mismos para todas las personas y las dos condiciones. Para
  que lo aprendido en una condición no regale la otra, hay **dos entregas paralelas** (P y Q) del
  mismo presupuesto: cada una trae la versión anterior y la nueva, y **5 diferencias sembradas**,
  una de cada tipo de SL-E9: de cantidad, de precio, de ambas, partida eliminada y partida nueva
  (memoria de diferencias §1 para la P y §1b para la Q). Ninguna trae más de una por partida.
* **Lista congelada:** las 10 diferencias (5 de P y 5 de Q), con partida, tipo y monto exacto, se
  escriben en `docs/protocolo_indicador_administrador_lista.md` y su SHA-256 se registra en
  `docs/protocolos_s3.json` **antes** de que nadie las vea. Las cifras del monto salen de la
  memoria de diferencias (`tests/fixtures/memorias/diferencias_s3.md` §1 y §1b), no del sistema.
* Condición **a mano:** los dos Excel de la entrega y una hoja de reporte en blanco. Condición
  **con el sistema:** los dos `.silice` y la vista Revisar; el Excel del sistema no se entrega.
* Consigna escrita (se lee textual, sin añadir): «Encuentre las diferencias entre las dos
  versiones de este presupuesto y anótelas con su partida y su monto. Diga *terminé* cuando
  quiera».

## 3. Personas

* **6 personas**, con experiencia mínima de 2 años elaborando o revisando presupuestos de obra
  (ingenieros civiles, estimadores). Criterio de selección: que **no** hayan participado en
  construir Sílice ni en CP-07 a CP-11, y que no conozcan las listas de diferencias.
* **Orden contrabalanceado:** 3 personas hacen primero «a mano» con la entrega P y después «con el
  sistema» con la Q; las otras 3, primero «con el sistema» con la P y después «a mano» con la Q.
  Ninguna persona ve la misma entrega dos veces. La asignación de personas a órdenes se sortea
  con la semilla 42 antes de citarlas.
* Entre las dos condiciones hay 10 minutos de descanso. Una sesión dura unos 90 minutos con
  la explicación de 10 minutos de cómo se usa la vista Revisar (la misma para todas).

## 4. Cómo se analiza

Estadística **descriptiva**: mediana y rango de cada medida por condición y la diferencia dentro
de cada persona. Con 6 personas no se hace prueba de hipótesis (la mínima probabilidad de un
Wilcoxon exacto de dos colas con n = 6 es 0,0625, mayor que 0,05): se reporta lo observado y se
declara que no es una prueba. RNF-17 (a, b) se reporta en la misma sesión: abrir el paquete y
decir su estado y quién lo emitió en ≤ 5 min; hallar las diferencias sembradas en ≤ 20 min.

## 5. Amenazas a la validez (declaradas)

* **Sesgo del autor como facilitador:** quien construyó Sílice conduce la sesión y quiere que
  funcione. Se mitiga leyendo la consigna textual, sin responder preguntas sobre la tarea durante
  la medición y registrando cada ayuda pedida; si hay otra persona del equipo que no escribió la
  vista Revisar, ella conduce. Queda declarado.
* **Validez de constructo:** las diferencias están sembradas por el autor y son de los tipos que
  la vista sabe mostrar (cantidad, precio, partida nueva o eliminada): una diferencia de otro tipo
  no está en el material. «Encontrar diferencias» no es «revisar bien un presupuesto».
* **Validez externa:** una obra y un presupuesto ficticios; 6 personas de un círculo cercano;
  Excel como línea base «a mano», que es lo habitual, pero no la práctica de cada empresa.
* **Validez interna:** orden y aprendizaje (se contrabalancea, no se elimina); fatiga en la
  segunda condición; el tope de 30 minutos cortaría la condición lenta; el cronómetro lo maneja
  el facilitador.
* **Tamaño:** n = 6 es suficiente para ver una diferencia grande y para mejorar la vista, no para
  afirmar una tasa. La tesis lo presenta como un estudio piloto.

## 6. Qué se registra

Por persona y condición: tasa de detección, falsas alarmas, minutos, ayudas pedidas, orden y
comentarios en voz alta. Todo en `docs/bitacora/2026-10-silice-080.md` (sin nombres: P01 a P06),
con la huella de este protocolo y la de la lista congelada.
```
**`docs/protocolo_indicador_administrador_lista.md`**
```markdown
# Lista congelada de diferencias sembradas (protocolo del indicador de quien revisa)

Versión 1, escrita en S3-0 con las cifras de `tests/fixtures/memorias/diferencias_s3.md` §1 y §1b,
hechas a mano. Su SHA-256 está en `protocolos_s3.json` y no cambia después de escrito. Los Excel y
los `.silice` de las dos entregas se generan en la fase Med a partir de estas tablas; generarlos no
cambia la lista.

## Entrega P (total anterior 840, total nuevo 1130, diferencia +290)

| Partida | Tipo de diferencia | Δ cantidad | Δ precio | Δ total |
|---|---|---|---|---|
| A | cantidad (10 → 12 a 50) | +100 | 0 | +100 |
| B | precio (20 → 22, cantidad 5) | 0 | +10 | +10 |
| C | cantidad y precio (2 → 3; 100 → 110) | +100 | +30 | +130 |
| D | partida eliminada (4 a 10) | −40 | 0 | −40 |
| E | partida nueva (3 a 30) | +90 | 0 | +90 |

## Entrega Q (total anterior 550, total nuevo 589, diferencia +39)

| Partida | Tipo de diferencia | Δ cantidad | Δ precio | Δ total |
|---|---|---|---|---|
| A' | cantidad (8 → 9 a 25) | +25 | 0 | +25 |
| B' | precio (15 → 16, cantidad 6) | 0 | +6 | +6 |
| C' | cantidad y precio (4 → 5; 40 → 44) | +40 | +20 | +60 |
| D' | partida eliminada (2 a 50) | −100 | 0 | −100 |
| E' | partida nueva (4 a 12) | +48 | 0 | +48 |

**Qué cuenta como «encontrada»:** la persona nombra la partida y dice que cambió su cantidad,
su precio, que se eliminó o que es nueva; el monto no tiene que ser exacto para contarla, pero se
anota para la medición de la vista Revisar (que sí debe darlo exacto). **Qué es falsa alarma:**
nombrar una partida que no está en su tabla o un cambio que no ocurrió.
```
**`docs/protocolo_deteccion_planos.md`**
```markdown
# Protocolo de medición: tasa de detección en planos (S3 §11.5 y §13.5 b)

Versión 1, escrita en S3-0 **antes** de medir (maestro §7). Su huella SHA-256 está en
[`protocolos_s3.json`](protocolos_s3.json); la meta (`S3-M1`) comprueba que el texto no cambió
después de escribirla. Si algo de aquí debe cambiar, se escribe una versión 2 con su huella nueva
y la 1 queda como historia.

## 1. Qué se mide y la meta

La auditoría de planos de la 0.8.0 (auditoría de archivo del DXF, requisitos IDS del IFC, R15 y
R16) se evalúa **sembrando errores conocidos** en un plano limpio y viendo qué detecta.

* **Tasa de detección** por categoría = errores detectados ÷ errores sembrados **detectables**.
* **Falsa alarma** = todo ítem del informe de importación, hallazgo de R8 a R15 o diferencia de R16
  que la auditoría **agrega** al sembrar el error y que no está ni en la detección esperada ni en
  las consecuencias admitidas de su fila del catálogo. Se cuentan todas, por archivo sembrado.
* **Meta** (ratificada por Eugenio el 2026-10-11, pregunta P8 del maestro §10.3): **100 % de lo
  detectable y cero falsas alarmas** sobre el plano limpio de OF-001 y sobre los archivos sembrados.

## 2. Material

| Pieza | Dónde |
|---|---|
| Catálogo de errores con la detección esperada y los controles no detectables |
↳ `tests/fixtures/errores_planos/catalogo.md` |
| Plano limpio de partida | `tests/fixtures/planos/of001.dxf` y, para el IFC, el IFC de oficina
↳ `tests/fixtures/planos_ifc_ids.py` (OF-001 no tiene IFC) |
| Conjunto exacto del plano limpio (ítems y hallazgos), escrito como literal |
↳ `tests/fixtures/errores_planos/of001_limpio.py` |
| Sembrador | `scripts/sembrar_errores_planos.py` |
| Medición | `scripts/medir_deteccion_planos.py` |

El catálogo lo escribe **en parte quien no programa las reglas**: las filas marcadas `P` las escribe
el ingeniero de pruebas sin ver la implementación de R15 ni de R16 (columna *Autor*); las marcadas
`A`, quien programa los adaptadores. La meta se cuenta con todas.

## 3. Diseño

* **Semilla fija:** semilla 42. La misma semilla, la misma categoría y el mismo índice de variante
  dan siempre el mismo plano y el mismo elemento dañado. Se recorre con
  `uv run python scripts/medir_deteccion_planos.py`.
* **n por categoría:** 3 variantes de cada categoría de DXF que tiene más de un elemento donde
  dañar (la variante cambia el elemento, el factor o el desplazamiento); 1 variante en las que no
  la tienen (`SIN-UNIDAD`, las tres de IFC, `NO-DET-PERMUTA`, `NO-DET-LUCES`). En total 34
  archivos detectables y 5 controles. Con 34 de 34, el límite inferior unilateral al 95 % de la
  tasa verdadera (regla exacta `0,05^(1/34)`) es **91,6 %**: es el máximo que esta medición permite
  afirmar, no 100 %.
* **Un error por archivo.** Las combinaciones **no se siembran juntas** en la 0.8.0: R15, R16 y
  los ítems de la importación miran un elemento a la vez, y dos errores sobre el mismo elemento se
  enmascaran (un punto duplicado que además queda fuera de todo ambiente se informa una vez). Esa
  interacción queda como límite declarado, no se mide.
* **Controles no detectables** (`NO-DET-*`): un plano coherente pero equivocado, sin segunda
  fuente. Deben dar «no detectado» y se informan con su número; miden el **límite declarado** de
  la auditoría de planos (horizonte H-D9), no entran en la tasa. Un control que la auditoría
  señalara se informa aparte: habría que ampliar el catálogo.
* **Segunda fuente de R16:** el plano limpio. R16 no corre en la reauditoría de un paquete.

## 4. Procedimiento

1. `uv run python scripts/medir_deteccion_planos.py --json > medicion.json` (código de salida 0 solo
   si la tasa es 1 y las falsas alarmas son 0).
2. Se copia la tabla (sin el JSON entero) a `docs/bitacora/2026-10-silice-080.md`, con la huella
   de este protocolo, el commit y la semilla.
3. Una prueba (`tests/unit/test_deteccion_planos.py`) repite la medición en cada corrida de la
   CI y exige la meta; otra comprueba que, si R15 dejara de funcionar, la medición lo nota.

## 5. Amenazas a la validez (declaradas)

* **Validez de constructo:** los errores son **sintéticos**, sembrados por el mismo equipo que
  escribió las reglas; no representan los errores que comete una persona dibujando. Detectar todo
  lo sembrado no prueba detectar lo que ocurre en una obra.
* **Validez externa:** un solo plano de oficina (OF-001, ficticio, programático) y un IFC de
  oficina; sin planos de obras ejecutadas. La tasa no se generaliza a otros dibujantes ni a otros
  programas de CAD.
* **Validez de conclusión:** n pequeño y todo en 100 %: el intervalo de §3 es ancho. Cero falsas
  alarmas se mide sobre OF-001; en otro plano las constantes supuestas de R15 (escala, distancia a
  la fuente) y de R16 (0,10 y 1,00 m) pueden dar alarmas que aquí no aparecen.
* **Circularidad:** las detecciones esperadas se escribieron antes del código (columna *Autor* `P`),
  pero el mismo equipo las eligió; la parte escrita por una persona ajena al equipo es una mejora
  para la fase Med.
```
  El script que escribe la huella (se corre UNA vez, cuando el texto ya no cambia):
**`scripts/huellas_protocolos_s3.py`**
```python
"""Escribe `docs/protocolos_s3.json`: la huella SHA-256 de los protocolos de S3 (spec S3 §13.5).

Se corre UNA vez, al cerrar S3-0, cuando el texto de los dos protocolos y de la lista congelada ya
no va a cambiar. Después de Med no se vuelve a correr: la meta (`S3-M1`) compara el texto con esta
huella y falla si cambió. Un cambio de fondo es una versión 2 del protocolo, con su huella nueva.

    uv run python scripts/huellas_protocolos_s3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from scripts.meta_silice_s3 import PROTOCOLOS, RUTA_HUELLAS, huella_de  # noqa: E402


def calcular(raiz: Path = RAIZ) -> dict:
    return {
        "algoritmo": "sha256",
        "protocolos": {relativa: huella_de(raiz / relativa) for relativa in PROTOCOLOS},
    }


def main() -> int:
    datos = calcular()
    RUTA_HUELLAS.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for relativa, huella in datos["protocolos"].items():
        print(f"{huella}  {relativa}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
Run: `uv run python scripts/huellas_protocolos_s3.py` → escribe `docs/protocolos_s3.json` con una
línea `<sha256>  <ruta>` por protocolo.
- [ ] **Paso 5: Escribir la bitácora de la versión y los expedientes**
  `scripts/README.md` gana las dos filas de los scripts nuevos (la prueba
  `test_scripts_documentados` falla si falta alguna), tras la de `meta_silice_s5.py`:
```markdown
| `meta_silice_s3.py` | parte S3 de la meta: UC‑21 a UC‑23, RF‑80 a RF‑89 y RF‑100, protocolos con
↳  huella, OF‑001 limpio (S3‑M1 a S3‑M5) | 0.8.0 |
| `huellas_protocolos_s3.py` | escribe `docs/protocolos_s3.json`: el SHA‑256 de los dos protocolos
↳  de S3 y su lista | 0.8.0 |
```
  La bitácora recoge lo que se verificó de cada biblioteca (API exacta, hallazgos); es historia y no
  se edita después, solo se le agregan secciones de compuerta:
**`docs/bitacora/2026-10-silice-080.md`**
```markdown
# Bitácora de la 0.8.0 de Sílice (S3)

Cada fase agrega su sección: lo verificado, los rulings tomados y la salida de su compuerta. Lo
que dice «verificado» se comprobó con el entorno bloqueado por `uv.lock` el 2026-10-11.

## S3-0 · Lo que S3 supone de las bibliotecas (API exacta, verificada)

**argon2-cffi 25.1.0.** `argon2.PasswordHasher()` usa por defecto `time_cost=3`,
`memory_cost=65536` (KiB, 64 MiB), `parallelism=4`, `hash_len=32`, `salt_len=16` y `Type.ID`.
`hasher.hash(contrasena)` da la huella con sus parámetros; `hasher.verify(huella, contrasena)`
lanza `argon2.exceptions.VerifyMismatchError` si no coincide; `hasher.check_needs_rehash(huella)`
dice si hay que recalcularla. Para la derivación de la clave de una privada se usa
`argon2.low_level.hash_secret_raw(secreto, sal, time_cost, memory_cost, parallelism, hash_len,
Type.ID)`. Cada verificación gasta unos 64 MiB: un semáforo limita las simultáneas a 4.

**cryptography 50.0.2.** `Ed25519PrivateKey.from_private_bytes(32 octetos)`, `.sign(mensaje)`
(firma de 64 octetos); `Ed25519PublicKey.from_public_bytes(32).verify(firma, mensaje)` lanza
`cryptography.exceptions.InvalidSignature`. `AESGCM(clave de 32 octetos).encrypt(nonce de 12,
datos, asociados)`; descifrar con datos asociados distintos o una contraseña errónea lanza
`cryptography.exceptions.InvalidTag`. Los vectores 1 y 2 de RFC 8032 §7.1 (clave secreta,
pública, mensaje y firma) se reprodujeron en este entorno y son los de `tests/unit/test_firma.py`.

**ezdxf 1.4.4.** `ezdxf.readfile(ruta)` abre o falla. `ezdxf.recover.readfile(ruta)` devuelve
`(Drawing, Auditor)`: `auditor.fixes` y `auditor.errors` son listas de entradas con `.message`;
un archivo irrecuperable lanza `ezdxf.DXFStructureError`. **Hallazgo:** `Drawing.audit()` BORRA lo
que no entiende (un `INSERT` sin definición de bloque, que el importador sí lee), así que la
importación abre con `readfile`, y solo si falla recurre a `recover.readfile`; el informe de
reparaciones de un archivo que abrió bien sale de auditar una **segunda lectura**.

**ifctester 0.8.5.** `ifctester.ids.open(ruta)` devuelve un `Ids`; `ids.validate(modelo)` valida
un `ifcopenshell.file`; cada `especificacion.requirements[i].failures` es una lista de diccionarios
con `element` y `reason`. **Hallazgo:** `ids.open` intenta descargar el esquema XSD de internet
cada vez (lo atrapó la guardia de red de la suite); se evita fijando
`ifctester.ids.schema = xmlschema.XMLSchema(<ids.xsd local>, allow="local")` antes de abrir.
`ifctester` declara LGPLv3+ y exige `bcf-client` (GPLv3): ver `licencias_ifc.md`.

**Streamlit 1.62.** `st.context.ip_address` es `None` cuando el cliente es `localhost` y, si no, la
IP de la conexión WebSocket; bajo `AppTest` es un `MagicMock`, así que `ui/sesion.ip_del_cliente`
lo trata como `None` si no es texto. **Hallazgo (reanudación de sesiones):** el servidor reanuda
una sesión cuando el cliente presenta su identificador (`existing_session_id`,
`runtime/runtime.py`) y el único control es que `user_info` sea igual
(`AppSession.matches_user_info`); sin `st.login`, `user_info` es el mismo para toda sesión
anónima, así que **quien escuche el tráfico de la red local sin TLS y vea un identificador
podría reanudar esa sesión**. Eso, y no solo que la contraseña viaje legible, es lo que pesa en
RS3-8 (red local sin TLS en la 0.8.0, con las condiciones de S3 §5.6): queda declarado en la
amenaza de §12 y se cierra con TLS (S5).

**SQLAlchemy 2.0.52 con pysqlite.** Receta de transacciones que empiezan con `BEGIN IMMEDIATE`:
`conexion.isolation_level = None` al conectar (pysqlite deja de emitir su `BEGIN` implícito),
`PRAGMA journal_mode=WAL` y `PRAGMA busy_timeout=5000`, y un evento `begin` que emite
`BEGIN IMMEDIATE` si la opción de ejecución `silice_inmediata` está puesta y `BEGIN` si no. Con
tres hilos que hacen 10 guardados cada uno la cadena queda lineal y sin `database is locked`.

**shapely 2.1.2 y xmlschema 4.3.2.** `shapely.strtree.STRtree` solo propone candidatos (en coma
flotante); cada hallazgo de R15 se decide con `Decimal` (DA-S3-6). Ambos son de licencia permisiva.

## S3-0 · Rulings del plan (RP8)

Los rulings RP8-1 a RP8-19 están en el encabezado de `PLAN_SILICE_080.md`; esta bitácora los
registra al cruzar cada compuerta, con su evidencia.

## Compuertas

*(cada fase agrega aquí la salida de `scripts/meta_silice.py --version 0.8.0 --hasta S3-n` y de la
CI, con la fecha y el commit)*
```
  Los cuatro expedientes, uno por cada cambio de `core/` de S3-2. Se commitean **antes** del código
  y el tutor da su visto bueno antes de abrir `inc/080-s3-2-nucleo`:
````markdown
# Expedientes de la 0.8.0 (S3, auditor y paquete): núcleo

**Fecha:** 2026-10-11 · **Plan:** `PLAN_SILICE_080.md` · **Spec:** `docs/especificaciones/
↳ 2026-10-11-silice-s3-auditor-paquete-design.md` §14.1 · **Bitácora:** [2026-10-silice-080.md]
↳ (2026-10-silice-080.md)

Cuatro expedientes, uno por cambio de `core/` (rama única `inc/080-s3-2-nucleo`), cada uno
commiteado antes de su código y aprobado por el tutor antes de abrir la rama. `core/contracts/`
no se toca. Ningún expediente agrega columnas a una tabla existente.

## SL‑E8 Documento canónico de una versión y su lectura

**Problema.** Para sellar, enviar y reauditar una versión hace falta un solo texto que diga qué es,
con los mismos bytes en cualquier instalación y sin identificadores de fila.
**Diseño.** `core/budget/canonico.py`: `documento(session, version) -> bytes` serializa, desde las
filas guardadas (nunca recalculadas), claves ordenadas, sin espacios, UTF‑8 sin escapar, `Decimal`
como `format(valor, "f")` y sin ningún `id`; `leer(objeto) -> DocumentoLeido` es la inversa y valida
cada cifra con `PATRON_CIFRA` (`^-?[0-9]{1,20}(\.[0-9]{1,28})?$`) antes de construir un `Decimal`.
Incluye la moneda del proyecto (RP8‑3) y el origen de cada precio. `VERSION_FORMATO = 1`.
**Por qué es genérico.** Describe cualquier presupuesto versionado, de cualquier dominio; lo usan la
cadena, el paquete y la API (DRY).
**Qué no toca.** Ninguna tabla, ningún escritor; solo lee. No importa `seguridad` (el patrón de
↳ cifra
se repite y una prueba lo compara con el del lector estricto, RP8‑2).
**Pruebas que lo fijan.** `tests/integration/test_canonico.py`: el vector a mano (2271 bytes,
SHA‑256 `b4b952dd…3936`), ida y vuelta, determinismo entre dos bases, rechazo de cifras fuera de
patrón y del campo `id`.
**Impacto.** Un módulo nuevo. **Costo si es erróneo.** Cambiar el documento exige subir
`VERSION_FORMATO`; los eslabones ya sellados conservan el suyo y se verifican con él.

## SL‑E7 Cadena de huellas sellada en el embudo

**Problema.** Nada impide editar la historia de una versión ni dice quién la confirmó (RF‑83).
**Diseño.** Tabla aditiva `eslabon_version` (`core/models/cadena.py`, revisión
`caso_0007_s3_cadena`, índice único `(proyecto_id, anterior)` que impide dos hijos del mismo
eslabón). `core/budget/cadena.py`: `marcar_por_sellar` (la llama `guardar_presupuesto`, que ahora
recibe `usuario` y `anexos_de`), el sellado en un evento `before_commit` de la transacción raíz
(ignora savepoints, RP8‑8), `verificar_cadena` (recalcula cada huella desde la base),
`sellar_historial` (versiones anteriores a S3, `tipo = "retroactivo"`), `anexos_por_omision`.
Un `commit` sin `usuario` falla con `SelladoSinUsuario` y no escribe nada.
**Por qué es genérico.** Cualquier presupuesto versionado se encadena igual, sin conocer dominios.
**Qué no toca.** El cómputo, los contratos ni las tablas existentes; los llamadores del núcleo
(`cotizacion`, `actualizacion`, `edicion`, `importacion`) solo pasan `usuario`.
**Pruebas que lo fijan.** `tests/integration/test_cadena.py` (huella por componente, sellado
retroactivo, raíz y savepoints, ramificación imposible, `usuario` obligatorio, ruptura detectada
por contenido, por registro, por anexo y por eslabón).
**Impacto.** Una tabla, un módulo, dos parámetros del embudo. **Costo si es erróneo.** Una revisión
de Alembic más; los eslabones se pueden resellar con `tipo = "retroactivo"` declarado.

## SL‑E12 WAL y `BEGIN IMMEDIATE` para varios usuarios

**Problema.** Dos personas guardando a la vez pueden bifurcar la cadena o chocar con
`database is locked`.
**Diseño.** `core/catalog/sesion.py`: `crear_motor` fija WAL, `busy_timeout = 5000`, claves
foráneas e `isolation_level = None`; un evento `begin` emite `BEGIN IMMEDIATE` cuando la opción de
ejecución `silice_inmediata` está puesta (RP8‑10); `abrir_sesion_de_escritura(motor)` la pone.
**Por qué es genérico.** Sirve a cualquier base SQLite con varios escritores.
**Qué no toca.** Las lecturas siguen con `abrir_sesion`; ninguna tabla.
**Pruebas que lo fijan.** `tests/integration/test_concurrencia.py` (PRAGMA, `threading.Barrier`
con 3 hilos por 10 guardados: 30 versiones, cadena lineal, ningún `database is locked`).
**Impacto.** Un cambio de motor. **Costo si es erróneo.** Quitar la opción vuelve al `BEGIN` por
omisión; el índice único de SL‑E7 sigue impidiendo la bifurcación (falla el segundo, no se
↳ corrompe).

## SL‑E9 Diferencia entre versiones y revaloración

**Problema.** Quien revisa necesita saber cuánto cambió una entrega respecto de la anterior y por
qué (cantidad o precio), y valorar un paquete con su propia lista.
**Diseño.** `core/budget/comparacion.py` (puro): `diferencia_entre_versiones` por partida,
`Δ total = (q2 − q1)·PU1 + (PU2 − PU1)·q2` (el término cruzado queda en el precio), partida nueva
o eliminada como desvío de cantidad entero; `revalorar` valora un documento con otra lista
emparejando por referencia de precio o por código, y lista lo que no empareja.
**Por qué es genérico.** Compara dos presupuestos cualesquiera; es distinta de la separación del
desvío de S2 (término cruzado en el consumo) y no la reutiliza (RV‑10).
**Qué no toca.** Ninguna tabla ni lectura de la base.
**Pruebas que lo fijan.** `tests/unit/test_comparacion.py` con `diferencias_s3.md` (840 → 1130,
Δq 250, Δp 40; entrega Q 550 → 589) y su rehacer con fracciones.
**Impacto.** Un módulo nuevo. **Costo si es erróneo.** Cambiar la descomposición es cambiar una
función y su memoria.
````
- [ ] **Paso 6: Correr la meta y las pruebas y ver el verde**
Run: `uv run pytest tests/unit/test_meta_silice_s3.py tests/unit/test_documentos_s3_0.py -v -W
error` → verde. Run: `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-0 --junit
reporte-pruebas.xml` → todas las filas en OK salvo `S3-M5` (PENDIENTE: ninguna rama de planos
fusionada) y `S3-M3`/`S3-M4` (fase S3-1, no evaluadas todavía).
- [ ] **Paso 7: Commit**
```bash
git add scripts/meta_silice_s3.py scripts/meta_silice.py scripts/huellas_protocolos_s3.py \
  tests/fixtures/canonico tests/fixtures/memorias tests/fixtures/errores_planos docs/ERS.md \
  docs/protocolo_indicador_administrador.md docs/protocolo_indicador_administrador_lista.md \
  docs/protocolo_deteccion_planos.md docs/protocolos_s3.json docs/bitacora/2026-10-silice-080.md \
  docs/bitacora/2026-10-silice-s3-expedientes.md
git commit -m "docs(s3): meta, ERS, oraculos a mano, protocolos con huella y expedientes" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS3-0 y foco de revisión de la fase

**Compuerta GS3-0** (se cruza al fusionar `inc/080-s3-0-docs`):
1. `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-0 --junit reporte-pruebas.xml`
   en OK (con `S3-M5` PENDIENTE).
2. CI verde en Linux y Windows, `-W error`, cero omitidas.
3. Los cuatro expedientes (SL-E7, E8, E9, E12) escritos y **el visto bueno del tutor** anotado en
   `docs/bitacora/2026-10-silice-080.md`.
4. Revisión de los encargos de requisitos (UC-21 a UC-23, RF-80 a RF-89, RNF-16, RNF-17 presentes y
   enmienda única de RNF-08), de pruebas (el vector de huella se calcula aparte; los protocolos
   tienen huella) y de arquitectura (los módulos nombrados en los expedientes).

**Foco de revisión de S3-0** (lo que el spec implica y ninguna prueba ejercita todavía):
1. **Un protocolo editado después de medir** pasaría sin que nadie lo vea: `S3-M1` compara la huella
   del texto con `protocolos_s3.json` (esta tarea); cambiar uno exige versión 2.
2. **Un catálogo escrito por quien programa** no mediría independencia: la columna *Autor* y el
   conteo de bloques con `P` (tarea 12,
   `test_el_catalogo_tiene_tres_controles_y_casi_todo_escrito_sin_ver_el_codigo`).
3. **Un conjunto limpio de OF-001 envejecido** se vuelve un oráculo circular: la tarea 12 lo compara
   con lo que la hoja dice hoy (`test_el_plano_limpio_da_el_conjunto_exacto_escrito_en_s3_0`) y
   falla si difieren.

---

# S3-1 — Cuentas, sesión y acceso (rama `inc/080-s3-1-seguridad`)

Sin núcleo: `seguridad/`, `operacion/`, `migraciones/`, `ui/` y `tests/`. Sale de `origin/main` con
S3-0 fusionada (o antes de la 0.7.0, con el acceso apagado: RP8-4). Al terminar, `instalacion.db`
existe con sus nueve tablas, hay cuentas con Argon2id, sesiones con ficha de 256 bits, bloqueo,
freno global y registro de accesos, y la interfaz pide entrar y muestra a cada rol solo sus
pantallas.

### Tarea 3: La base de la instalación (`seguridad/modelo`, `ins_0001_seguridad`)

**Rama:** `inc/080-s3-1-seguridad` (sale de `main`; PR a `main`)   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `seguridad/__init__.py`, `seguridad/base.py`, `seguridad/modelo.py`
- Crear: `operacion/instalacion.py`
- Crear: `migraciones/instalacion/versions/ins_0001_seguridad.py`
- Modificar: `migraciones/metadatos.py:14-17` (`METADATAS_INSTALACION`), `docs/plan_pruebas.md:521`
  (la prueba renombrada)
- Prueba: `tests/integration/test_migracion_instalacion.py`; se enmiendan
  `tests/integration/test_migraciones.py:257`, `tests/integration/test_preparar_base.py:245`,
  `tests/integration/test_respaldo.py:93-110`, `tests/unit/test_migraciones_metadatos.py`,
  `tests/unit/test_arquitectura.py:25` y `tests/unit/test_arquitectura_s5.py:17`

**Interfaces:**
- Consume: de B (S5-1): `operacion.base_datos.{Destino, preparar_base, aplicar_revisiones,
  deshacer_revisiones, revision_head}`, `operacion.config.ruta_instalacion(entorno)`; el destino
  `instalacion` de Alembic con su `env.py` y su carpeta `versions/` vacía; `migraciones.metadatos`.
- Produce:
  - `seguridad.base`: `crear_motor(ruta) -> Engine`, `abrir_sesion(motor) -> Session`.
  - `seguridad.modelo`: `Base` y las nueve tablas `Usuario`, `IntentoAcceso`, `Sesion`,
    `EventoAcceso`, `CodigoInstalacion`, `EmpresaPropia`, `ClaveEmpresa`, `EmpresaRegistrada`,
    `ClaveApi`.
  - `operacion.instalacion`: `motor_de_instalacion(entorno=None) -> Engine`,
    `sesion_de_instalacion(entorno=None)` (context manager), `cerrar_motores()`.
  - La revisión `ins_0001_seguridad` (cabeza del destino `instalacion`) y
    `METADATAS_INSTALACION = (seguridad.modelo.Base.metadata,)`.

Hasta la 0.7.0 la base de la instalación nacía vacía (solo `alembic_version`). Las tres pruebas
que lo afirmaban cambian de afirmación; ninguna cambia de intención.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/integration/test_migracion_instalacion.py`**
```python
"""La base de la instalación: su revisión `ins_0001_seguridad` y la deriva cero (RNF-20, RF-96)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from migraciones.metadatos import METADATAS_INSTALACION
from operacion.base_datos import Destino, aplicar_revisiones, deshacer_revisiones, revision_head
from seguridad.modelo import Base

TABLAS = {
    "usuario", "intento_acceso", "sesion", "evento_acceso", "codigo_instalacion", "empresa_propia",
    "clave_empresa", "empresa_registrada", "clave_api",
}


def _tablas(ruta: Path) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conexion:
        filas = conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {f[0] for f in filas} - {"alembic_version"}


def test_la_cabeza_del_destino_instalacion_es_la_revision_de_seguridad() -> None:
    assert revision_head(Destino.INSTALACION) == "ins_0001_seguridad"
    assert METADATAS_INSTALACION == (Base.metadata,)


def test_subir_crea_las_nueve_tablas_y_bajar_las_quita(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    assert _tablas(ruta) == TABLAS
    deshacer_revisiones(ruta, Destino.INSTALACION)
    assert _tablas(ruta) == set()
    aplicar_revisiones(ruta, Destino.INSTALACION)  # y vuelve a subir
    assert _tablas(ruta) == TABLAS


def test_deriva_cero_la_base_migrada_es_la_del_modelo(tmp_path: Path) -> None:
    ruta = tmp_path / "instalacion.db"
    aplicar_revisiones(ruta, Destino.INSTALACION)
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    try:
        with motor.connect() as conexion:
            contexto = MigrationContext.configure(conexion, opts={"compare_type": True})
            assert compare_metadata(contexto, Base.metadata) == []
    finally:
        motor.dispose()


def test_las_tablas_de_la_instalacion_no_estan_en_los_metadatos_del_caso() -> None:
    from migraciones.metadatos import METADATAS_CASO

    nombres_caso = {t for m in METADATAS_CASO for t in m.tables}
    assert not (TABLAS & nombres_caso)  # DA-S5-7: cuentas y claves nunca viajan con un caso
```
  Las pruebas existentes que decían «nace vacía» pasan a decir «nace con las nueve tablas»:
```diff
--- a/tests/integration/test_migraciones.py
+++ b/tests/integration/test_migraciones.py
@@ -257,12 +257,20 @@
 
 
-def test_la_instalacion_nace_sin_tablas_y_con_su_alembic_version(tmp_path: Path) -> None:
+def test_la_instalacion_nace_con_las_tablas_de_seguridad_y_su_alembic_version(
+    tmp_path: Path,
+) -> None:
+    """S3-1 llena el destino de la instalación (hasta la 0.7.0 nacía vacío)."""
     base = tmp_path / "instalacion.db"
     aplicar_revisiones(base, Destino.INSTALACION)
-    assert revision_head(Destino.INSTALACION) is None
+    assert revision_head(Destino.INSTALACION) == "ins_0001_seguridad"
     with closing(sqlite3.connect(base)) as conexion:
-        tablas = [
+        tablas = {
             n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
-        ]
-        assert tablas == ["alembic_version"]
-        assert conexion.execute("SELECT count(*) FROM alembic_version").fetchone()[0] == 0
+        }
+        assert tablas == {
+            "alembic_version", "usuario", "intento_acceso", "sesion", "evento_acceso",
+            "codigo_instalacion", "empresa_propia", "clave_empresa", "empresa_registrada",
+            "clave_api",
+        }
+        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
+            ("ins_0001_seguridad",)]
```
```diff
--- a/tests/integration/test_preparar_base.py
+++ b/tests/integration/test_preparar_base.py
@@ -245,13 +245,18 @@
 
 
-def test_la_base_de_la_instalacion_nace_vacia_con_su_alembic_version() -> None:
+def test_la_base_de_la_instalacion_nace_con_las_tablas_de_seguridad() -> None:
+    """S3-1 llena el destino de la instalación (hasta la 0.7.0 nacía vacío)."""
     ruta = config.ruta_instalacion()
     primero = preparar_base(ruta, Destino.INSTALACION)
-    assert primero.nueva and primero.revision_destino is None
-    with closing(sqlite3.connect(ruta)) as conexion:
-        tablas = [
+    assert primero.nueva and primero.revision_destino == "ins_0001_seguridad"
+    with closing(sqlite3.connect(ruta)) as conexion:
+        tablas = {
             n for (n,) in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
-        ]
-    assert tablas == ["alembic_version"]
+        }
+    assert tablas == {
+        "alembic_version", "usuario", "intento_acceso", "sesion", "evento_acceso",
+        "codigo_instalacion", "empresa_propia", "clave_empresa", "empresa_registrada",
+        "clave_api",
+    }
     segundo = preparar_base(ruta, Destino.INSTALACION)
     assert segundo.juego is None and not segundo.nueva
```
```diff
--- a/tests/integration/test_respaldo.py
+++ b/tests/integration/test_respaldo.py
@@ -93,5 +93,5 @@
 
 def test_la_instalacion_va_siempre_en_el_juego_aunque_no_se_migre(datos: Datos) -> None:
-    _instalacion_vacia(datos)
+    _instalacion_vacia(datos)  # desde S3-1: en `head`, con las tablas de seguridad sin filas
     juego = _respaldar(datos, [])
     [base] = respaldo.leer_ficha(juego)["bases"]
@@ -99,7 +99,11 @@
         "instalacion.db",
         "instalacion",
-        None,
-    )
-    assert base["filas_por_tabla"] == {"alembic_version": 0}
+        "ins_0001_seguridad",
+    )
+    assert base["filas_por_tabla"] == {
+        "alembic_version": 1, "usuario": 0, "intento_acceso": 0, "sesion": 0,
+        "evento_acceso": 0, "codigo_instalacion": 0, "empresa_propia": 0, "clave_empresa": 0,
+        "empresa_registrada": 0, "clave_api": 0,
+    }
 
 
```
  En `tests/unit/test_migraciones_metadatos.py`, la última prueba y su importación pasan a:
```python
from seguridad.modelo import Base as BaseSeguridad


def test_el_caso_lleva_el_nucleo_y_el_espacio_y_la_instalacion_lleva_seguridad() -> None:
    assert len(METADATAS_CASO) == 2
    assert METADATAS_CASO[0] is Base.metadata
    assert METADATAS_CASO[1] is persistencia.METADATA_ESPACIO
    assert METADATAS_INSTALACION == (BaseSeguridad.metadata,)
```
  En `tests/unit/test_arquitectura_s5.py`, `PUBLICOS_DE_OPERACION` (lo único de `operacion` que
  `ui` y `api` pueden importar) gana el módulo nuevo, que comparten la interfaz y la API:
```diff
--- a/tests/unit/test_arquitectura_s5.py
+++ b/tests/unit/test_arquitectura_s5.py
@@ -17,4 +17,5 @@
     "operacion.respaldo",
     "operacion.base_datos",
+    "operacion.instalacion",  # S3-1: la base de la instalación, la comparten la interfaz y la API
 )
 
```
  `tests/unit/test_arquitectura.py` conoce los paquetes nuevos del proyecto (para distinguir lo
  propio de los terceros):
```diff
--- a/tests/unit/test_arquitectura.py
+++ b/tests/unit/test_arquitectura.py
@@ -25,4 +25,7 @@
     "operacion",
     "migraciones",
+    "seguridad",
+    "paquete",
+    "auditoria",
 )
 
```
  En `docs/plan_pruebas.md:521`, la cita de la prueba renombrada (la prueba
  `test_documentos_s5_1` falla si una cita no existe):
  `test_la_base_de_la_instalacion_nace_vacia_con_su_alembic_version` pasa a
  `test_la_base_de_la_instalacion_nace_con_las_tablas_de_seguridad`.
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/integration/test_migracion_instalacion.py
tests/unit/test_migraciones_metadatos.py tests/integration/test_migraciones.py
tests/integration/test_preparar_base.py tests/integration/test_respaldo.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'seguridad'` (los dos primeros
archivos) y FAIL por `assert None == 'ins_0001_seguridad'` (`test_migraciones`,
`test_preparar_base`, `test_respaldo`).
```bash
git add tests/integration/test_migracion_instalacion.py tests/integration/test_migraciones.py \
  tests/integration/test_preparar_base.py tests/integration/test_respaldo.py \
  tests/unit/test_migraciones_metadatos.py tests/unit/test_arquitectura.py \
  tests/unit/test_arquitectura_s5.py docs/plan_pruebas.md
git commit -m "test(migraciones): la instalacion nace con las tablas de seguridad, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  El paquete y su motor propio (`seguridad` no puede importar `core`, así que repite lo mínimo de
  `crear_motor`):
**`seguridad/__init__.py`**
```python
"""Seguridad de Sílice (S3, 0.8.0): cuentas, sesiones, secretos, firma y empresas.

Todo lo de este paquete vive en la base de la instalación (`instalacion.db`), nunca en la de un
caso (maestro §4.2, RV-4). No importa `core`, `ui`, `api` ni `adapters`: solo la biblioteca
estándar, `sqlalchemy`, `argon2` y `cryptography` (`tests/unit/test_arquitectura_s3.py`). Las
funciones reciben la `Session` de la instalación y el reloj (`ahora`) que usan, para que las
pruebas no dependan del tiempo real.
"""
```
**`seguridad/base.py`**
```python
"""Motor de la base de la instalación: SQLite en WAL, con espera y claves foráneas.

`seguridad` no puede importar `core` (arquitectura), así que repite aquí lo mínimo de
`core.catalog.sesion.crear_motor`. La base se crea y se migra con
`operacion.base_datos.preparar_base(ruta, Destino.INSTALACION)` antes de abrirla.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

ESPERA_OCUPADA_MS = 5000  # SUPUESTO_DECLARADO: igual que SL-E12


def crear_motor(ruta: Path | str) -> Engine:
    motor = create_engine(f"sqlite:///{Path(ruta).as_posix()}")

    @event.listens_for(motor, "connect")
    def _preparar(conexion, _registro) -> None:
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={ESPERA_OCUPADA_MS}")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return motor


def abrir_sesion(motor: Engine) -> Session:
    return Session(motor, expire_on_commit=False)
```
  Las nueve tablas. Ninguna guarda una contraseña, una ficha ni un secreto de API en claro:
**`seguridad/modelo.py`**
```python
"""Tablas de la base de la instalación (`instalacion.db`; spec S3 §7.4; maestro §4.2).

Base propia (`Base`, `Base.metadata`): no comparte metadatos con `core.models`. Su destino de
migración es `migraciones/instalacion/` (revisión `ins_0001_seguridad`) y su lista
`METADATAS_INSTALACION` (`migraciones/metadatos.py`). Ninguna tabla guarda una contraseña, una
ficha de sesión ni un secreto de API en claro: solo huellas (Argon2 o SHA-256) y cifrados.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Metadatos de la base de la instalación."""


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(60), unique=True)  # normalizado, inmutable
    nombre: Mapped[str] = mapped_column(String(120))
    huella_clave: Mapped[str] = mapped_column(String(200))  # Argon2, nunca la contraseña
    roles: Mapped[str] = mapped_column(String(60))  # "arma,revisa" ordenado
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    debe_cambiar_clave: Mapped[bool] = mapped_column(Boolean, default=False)
    restablecida_por_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    creado: Mapped[datetime] = mapped_column(DateTime)
    creado_por: Mapped[str] = mapped_column(String(120), default="")


class IntentoAcceso(Base):
    """Contador por login normalizado; sirve igual para logins que existen y que no (S3 §5.4)."""

    __tablename__ = "intento_acceso"

    login_normalizado: Mapped[str] = mapped_column(String(60), primary_key=True)
    fallos_seguidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    ultimo_fallo: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class Sesion(Base):
    __tablename__ = "sesion"

    huella_ficha: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 de la ficha
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    creada: Mapped[datetime] = mapped_column(DateTime)
    ultima_actividad: Mapped[datetime] = mapped_column(DateTime)
    cerrada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_cierre: Mapped[str] = mapped_column(String(40), default="")


class EventoAcceso(Base):
    """Registro de seguridad solo-agregar. Lo lee `operacion.respaldo` (`id`, `fecha_hora`)."""

    __tablename__ = "evento_acceso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    login_intentado: Mapped[str] = mapped_column(String(60), default="")
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), default=None)
    ip_cliente: Mapped[str] = mapped_column(String(64), default="")
    tipo: Mapped[str] = mapped_column(String(30))
    detalle: Mapped[str] = mapped_column(Text, default="")


class CodigoInstalacion(Base):
    __tablename__ = "codigo_instalacion"

    huella: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 del código
    creado: Mapped[datetime] = mapped_column(DateTime)
    usado: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    motivo: Mapped[str] = mapped_column(String(20))  # primera vez | restablecimiento


class EmpresaPropia(Base):
    """Una sola fila (`id` = 1): la empresa dueña de esta instalación (RV-6, P1)."""

    __tablename__ = "empresa_propia"
    __table_args__ = (CheckConstraint("id = 1", name="ck_empresa_propia_unica"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    rif: Mapped[str] = mapped_column(String(20))
    ciudad: Mapped[str] = mapped_column(String(80), default="")
    actualizada: Mapped[datetime] = mapped_column(DateTime)
    actualizada_por: Mapped[str] = mapped_column(String(120), default="")


class ClaveEmpresa(Base):
    """La clave de firma de la empresa propia. `privada_cifrada` es nula al retirar o revocar."""

    __tablename__ = "clave_empresa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    publica: Mapped[bytes] = mapped_column(LargeBinary)  # 32 B crudos
    huella: Mapped[str] = mapped_column(String(64))  # SHA-256 completo de la pública
    privada_cifrada: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    kdf: Mapped[str | None] = mapped_column(String(160), default=None)
    sal: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    estado: Mapped[str] = mapped_column(String(12))  # activa | retirada | revocada
    creada: Mapped[datetime] = mapped_column(DateTime)
    creada_por: Mapped[str] = mapped_column(String(120), default="")
    fecha_estado: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    motivo: Mapped[str] = mapped_column(String(300), default="")


class EmpresaRegistrada(Base):
    """Una empresa ajena cuya clave pública se registró (la que emite paquetes que se reciben)."""

    __tablename__ = "empresa_registrada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa: Mapped[str] = mapped_column(String(200))
    rif: Mapped[str] = mapped_column(String(20), default="")
    publica: Mapped[bytes] = mapped_column(LargeBinary)
    huella: Mapped[str] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(String(12))  # activa | retirada | revocada
    comprobada_con: Mapped[str] = mapped_column(String(200))
    metodo: Mapped[str] = mapped_column(String(20))  # telefono | en persona | qr
    fecha_comprobacion: Mapped[datetime] = mapped_column(DateTime)
    registrada_por: Mapped[str] = mapped_column(String(120), default="")
    fecha_estado: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    motivo: Mapped[str] = mapped_column(String(300), default="")


class ClaveApi(Base):
    __tablename__ = "clave_api"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    identificador: Mapped[str] = mapped_column(String(8), unique=True)  # público, no es secreto
    huella_secreto: Mapped[str] = mapped_column(String(64))  # SHA-256 de un secreto de 256 bits
    creada: Mapped[datetime] = mapped_column(DateTime)
    creada_por: Mapped[str] = mapped_column(String(120), default="")
    ultimo_uso: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    revocada: Mapped[bool] = mapped_column(Boolean, default=False)
```
  La revisión base del destino `instalacion` (`down_revision = None`):
**`migraciones/instalacion/versions/ins_0001_seguridad.py`**
```python
"""S3-1: las tablas de `seguridad` en la base de la instalación (RF-80, RF-84; spec S3 §7.4).

Revisión base del destino `instalacion` (`down_revision = None`): la base de la instalación no
existía antes de S3. Cuentas, intentos, fichas de sesión, registro de accesos, código de
instalación, empresa propia, clave de firma, empresas registradas y claves de API.
"""

import sqlalchemy as sa
from alembic import op

revision = "ins_0001_seguridad"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("login", sa.String(60), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("huella_clave", sa.String(200), nullable=False),
        sa.Column("roles", sa.String(60), nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False),
        sa.Column("debe_cambiar_clave", sa.Boolean, nullable=False),
        sa.Column("restablecida_por_admin", sa.Boolean, nullable=False),
        sa.Column("creado", sa.DateTime, nullable=False),
        sa.Column("creado_por", sa.String(120), nullable=False),
        sa.UniqueConstraint("login"),
    )
    op.create_table(
        "intento_acceso",
        sa.Column("login_normalizado", sa.String(60), primary_key=True),
        sa.Column("fallos_seguidos", sa.Integer, nullable=False),
        sa.Column("bloqueado_hasta", sa.DateTime, nullable=True),
        sa.Column("ultimo_fallo", sa.DateTime, nullable=True),
    )
    op.create_table(
        "sesion",
        sa.Column("huella_ficha", sa.String(64), primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("creada", sa.DateTime, nullable=False),
        sa.Column("ultima_actividad", sa.DateTime, nullable=False),
        sa.Column("cerrada", sa.Boolean, nullable=False),
        sa.Column("motivo_cierre", sa.String(40), nullable=False),
    )
    op.create_table(
        "evento_acceso",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fecha_hora", sa.DateTime, nullable=False),
        sa.Column("login_intentado", sa.String(60), nullable=False),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("ip_cliente", sa.String(64), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("detalle", sa.Text, nullable=False),
    )
    op.create_table(
        "codigo_instalacion",
        sa.Column("huella", sa.String(64), primary_key=True),
        sa.Column("creado", sa.DateTime, nullable=False),
        sa.Column("usado", sa.DateTime, nullable=True),
        sa.Column("motivo", sa.String(20), nullable=False),
    )
    op.create_table(
        "empresa_propia",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("rif", sa.String(20), nullable=False),
        sa.Column("ciudad", sa.String(80), nullable=False),
        sa.Column("actualizada", sa.DateTime, nullable=False),
        sa.Column("actualizada_por", sa.String(120), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_empresa_propia_unica"),
    )
    op.create_table(
        "clave_empresa",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("publica", sa.LargeBinary, nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("privada_cifrada", sa.LargeBinary, nullable=True),
        sa.Column("kdf", sa.String(160), nullable=True),
        sa.Column("sal", sa.LargeBinary, nullable=True),
        sa.Column("nonce", sa.LargeBinary, nullable=True),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("creada", sa.DateTime, nullable=False),
        sa.Column("creada_por", sa.String(120), nullable=False),
        sa.Column("fecha_estado", sa.DateTime, nullable=True),
        sa.Column("motivo", sa.String(300), nullable=False),
    )
    op.create_table(
        "empresa_registrada",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa", sa.String(200), nullable=False),
        sa.Column("rif", sa.String(20), nullable=False),
        sa.Column("publica", sa.LargeBinary, nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("comprobada_con", sa.String(200), nullable=False),
        sa.Column("metodo", sa.String(20), nullable=False),
        sa.Column("fecha_comprobacion", sa.DateTime, nullable=False),
        sa.Column("registrada_por", sa.String(120), nullable=False),
        sa.Column("fecha_estado", sa.DateTime, nullable=True),
        sa.Column("motivo", sa.String(300), nullable=False),
    )
    op.create_table(
        "clave_api",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("identificador", sa.String(8), nullable=False),
        sa.Column("huella_secreto", sa.String(64), nullable=False),
        sa.Column("creada", sa.DateTime, nullable=False),
        sa.Column("creada_por", sa.String(120), nullable=False),
        sa.Column("ultimo_uso", sa.DateTime, nullable=True),
        sa.Column("revocada", sa.Boolean, nullable=False),
        sa.UniqueConstraint("identificador"),
    )


def downgrade() -> None:
    for tabla in (
        "clave_api", "empresa_registrada", "clave_empresa", "empresa_propia",
        "codigo_instalacion", "evento_acceso", "sesion", "intento_acceso", "usuario",
    ):
        op.drop_table(tabla)
```
  El motor de la instalación, abierto una vez por proceso por la interfaz y por la API:
**`operacion/instalacion.py`**
```python
"""La base de la instalación, abierta una vez por proceso (spec S3 §4.2; DA-S3-2).

Cuentas, sesiones, claves y registro de accesos viven en `instalacion.db`, no en el caso. La
interfaz (`ui.sesion`) y la API (`api.dependencias`) la abren con esta única función: crea y migra
la base con `preparar_base(ruta, Destino.INSTALACION)` y entrega un motor por ruta (un pool de
conexiones: estado del proceso, no de un usuario; excepción declarada de S3 §4.4). Ninguna crea
carpetas por su cuenta fuera de lo que hace `preparar_base`.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from operacion.base_datos import Destino, preparar_base
from operacion.config import ruta_instalacion
from seguridad.base import abrir_sesion, crear_motor

__all__ = ["cerrar_motores", "motor_de_instalacion", "sesion_de_instalacion"]

_MOTORES: dict[Path, Engine] = {}
_CANDADO = threading.Lock()


def motor_de_instalacion(entorno: Mapping[str, str] | None = None) -> Engine:
    ruta = ruta_instalacion(entorno)
    with _CANDADO:
        motor = _MOTORES.get(ruta)
        if motor is None:
            preparar_base(ruta, Destino.INSTALACION)
            motor = _MOTORES[ruta] = crear_motor(ruta)
        return motor


@contextmanager
def sesion_de_instalacion(entorno: Mapping[str, str] | None = None) -> Iterator[Session]:
    sesion = abrir_sesion(motor_de_instalacion(entorno))
    try:
        yield sesion
    finally:
        sesion.close()


def cerrar_motores() -> None:
    """Solo para las pruebas y para el cierre ordenado: cierra los pools abiertos."""
    with _CANDADO:
        for motor in _MOTORES.values():
            motor.dispose()
        _MOTORES.clear()
```
  `migraciones/metadatos.py` lista la `MetaData` de la instalación (la del caso la amplía la
  tarea 14):
```python
from seguridad.modelo import Base as BaseSeguridad

METADATAS_CASO: tuple[MetaData, ...] = (Base.metadata, METADATA_ESPACIO)
METADATAS_INSTALACION: tuple[MetaData, ...] = (BaseSeguridad.metadata,)
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite de migraciones)
Run: `uv run pytest tests/integration/test_migracion_instalacion.py
tests/unit/test_migraciones_metadatos.py tests/integration/test_migraciones.py
tests/integration/test_preparar_base.py tests/integration/test_respaldo.py
tests/unit/test_arquitectura_s5.py tests/unit/test_documentos_s5_1.py -v -W error` → verde.
Run: `uv run ruff check seguridad operacion migraciones` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add seguridad/__init__.py seguridad/base.py seguridad/modelo.py operacion/instalacion.py \
  migraciones/instalacion/versions/ins_0001_seguridad.py migraciones/metadatos.py
git commit -m "feat(seguridad): base de la instalacion con sus nueve tablas e ins_0001" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 4: Lector JSON estricto y `secretos` (Argon2id a AES-GCM)

**Rama:** `inc/080-s3-1-seguridad`   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `seguridad/json_estricto.py`, `seguridad/secretos.py`
- Prueba: `tests/unit/test_json_estricto.py`, `tests/unit/test_secretos.py`

**Interfaces:**
- Consume: nada de tareas anteriores (solo la biblioteca estándar, `argon2-cffi` y `cryptography`).
- Produce:
  - `seguridad.json_estricto`: `class JsonRechazado(ValueError)`
  - `seguridad.json_estricto`: `def a_decimal(texto: object) -> Decimal`
  - `seguridad.json_estricto`: `def leer_json(datos: bytes | str, *, max_niveles:
      int=MAX_NIVELES) -> Any`
  - `seguridad.secretos`: `class ContrasenaRechazada(ValueError)`
  - `seguridad.secretos`: `class ParametrosKdf`
  - `seguridad.secretos`: `class SecretoCifrado`
  - `seguridad.secretos`: `def exigir_contrasena_de_clave(contrasena: str) -> None`
  - `seguridad.secretos`: `def cifrar(secreto: bytes, contrasena: str, huella_publica: str,
      parametros: ParametrosKdf | None=None) -> SecretoCifrado`
  - `seguridad.secretos`: `def descifrar(cifrado: SecretoCifrado, contrasena: str,
      huella_publica: str) -> bytes`

El lector es la única puerta de JSON ajeno (manifiesto, presupuesto, cuerpo de la API): rechaza
`NaN` e infinitos, claves duplicadas (también anidadas), anidamiento de más de 64 niveles y cifras
que no cumplan `^-?[0-9]{1,20}(\.[0-9]{1,28})?$` ANTES de convertirlas a `Decimal`. `secretos` cifra
un secreto de 32 octetos con una clave derivada de la contraseña por Argon2id (m >= 64 MiB, t >= 3,
p >= 4), la sal y el nonce son nuevos en cada cifrado y el dato asociado es la huella pública: la
privada de una empresa no se descifra con la contraseña de otra clave.

- [ ] **Paso 1: Escribir las pruebas que fallan** (las fronteras son exactas: 64 niveles pasa y 65
  no; 28 decimales pasa y 29 no; parámetros por debajo del mínimo no se aceptan)
**`tests/unit/test_json_estricto.py`**
```python
"""Lector JSON estricto (spec S3 §8.4; RV-16): lo que el lector corriente deja pasar."""

from __future__ import annotations

from decimal import Decimal

import pytest

from seguridad.json_estricto import JsonRechazado, a_decimal, leer_json


def test_un_documento_normal_se_lee() -> None:
    assert leer_json(b'{"a": 1, "b": ["x", {"c": 2.50}]}') == {
        "a": 1,
        "b": ["x", {"c": Decimal("2.50")}],
    }


@pytest.mark.parametrize("constante", ["NaN", "Infinity", "-Infinity"])
def test_nan_e_infinitos_se_rechazan(constante: str) -> None:
    with pytest.raises(JsonRechazado, match="constante no admitida"):
        leer_json(f'{{"x": {constante}}}')


def test_una_clave_duplicada_se_rechaza_aunque_sea_anidada() -> None:
    with pytest.raises(JsonRechazado, match="clave JSON duplicada"):
        leer_json('{"a": 1, "a": 2}')
    with pytest.raises(JsonRechazado, match="clave JSON duplicada"):
        leer_json('{"x": {"k": 1, "k": 1}}')


@pytest.mark.parametrize("cifra", ["1E+999999999", "1e5", "1.5E3", "-1E400"])
def test_una_cifra_con_exponente_no_llega_a_decimal(cifra: str) -> None:
    with pytest.raises(JsonRechazado, match="cifra fuera del patron"):
        leer_json(f'{{"x": {cifra}}}')
    with pytest.raises(JsonRechazado, match="cifra fuera del patron"):
        a_decimal(cifra)


def test_el_patron_admite_veintiocho_decimales_y_rechaza_veintinueve() -> None:
    assert a_decimal("8." + "3" * 28) == Decimal("8." + "3" * 28)
    with pytest.raises(JsonRechazado):
        a_decimal("8." + "3" * 29)
    assert a_decimal("9" * 20) == Decimal("9" * 20)
    with pytest.raises(JsonRechazado):
        a_decimal("9" * 21)


@pytest.mark.parametrize("texto", ["+1", " 1", "1 ", "1,5", ".5", "5.", "0x10", "", "1_0", "١٢"])
def test_formas_que_no_son_una_cifra_estricta(texto: str) -> None:
    with pytest.raises(JsonRechazado):
        a_decimal(texto)


def test_anidamiento_64_pasa_y_65_se_rechaza() -> None:
    assert leer_json("[" * 64 + "]" * 64) is not None
    with pytest.raises(JsonRechazado, match="65|64 niveles"):
        leer_json("[" * 65 + "]" * 65)


def test_un_anidamiento_hostil_no_revienta_la_pila() -> None:
    with pytest.raises(JsonRechazado):
        leer_json("[" * 200_000 + "]" * 200_000)


def test_no_es_utf8_o_no_es_json() -> None:
    with pytest.raises(JsonRechazado):
        leer_json(b"\xff\xfe\x00")
    with pytest.raises(JsonRechazado):
        leer_json(b"{no es json")
    with pytest.raises(JsonRechazado):
        leer_json(b"\xef\xbb\xbf{}")  # con BOM: otro lector lo trataria distinto
```
**`tests/unit/test_secretos.py`**
```python
"""Argon2id -> AES-GCM para secretos con contraseña (maestro §4.4, RV-13; spec S3 §7.1)."""

from __future__ import annotations

import pytest

from seguridad.secretos import (
    MINIMO_CLAVE,
    ContrasenaRechazada,
    InvalidTag,
    ParametrosKdf,
    cifrar,
    descifrar,
    exigir_contrasena_de_clave,
)

SECRETO = bytes(range(32))
HUELLA = "A" * 64
CONTRASENA = "una frase larga y propia 2026"


def test_ida_y_vuelta_con_la_contrasena_buena() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    assert descifrar(guardado, CONTRASENA, HUELLA) == SECRETO
    assert SECRETO not in guardado.cifrado  # el secreto no queda en claro
    assert len(guardado.sal) == 16 and len(guardado.nonce) == 12


def test_una_contrasena_erronea_da_invalid_tag() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    with pytest.raises(InvalidTag):
        descifrar(guardado, CONTRASENA + "x", HUELLA)


def test_el_dato_asociado_ata_el_cifrado_a_su_huella() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    with pytest.raises(InvalidTag):
        descifrar(guardado, CONTRASENA, "B" * 64)


def test_sal_y_nonce_cambian_en_cada_cifrado() -> None:
    uno, otro = cifrar(SECRETO, CONTRASENA, HUELLA), cifrar(SECRETO, CONTRASENA, HUELLA)
    assert (uno.sal, uno.nonce, uno.cifrado) != (otro.sal, otro.nonce, otro.cifrado)


def test_los_parametros_se_guardan_y_son_los_minimos_del_spec() -> None:
    guardado = cifrar(SECRETO, CONTRASENA, HUELLA)
    assert ParametrosKdf.de_json(guardado.kdf) == ParametrosKdf(65536, 3, 4)


@pytest.mark.parametrize("memoria,pasadas", [(65535, 3), (65536, 2), (1024, 1)])
def test_parametros_por_debajo_del_minimo_no_se_aceptan(memoria: int, pasadas: int) -> None:
    with pytest.raises(ValueError, match="minimo"):
        ParametrosKdf(memoria, pasadas, 4)


def test_el_kdf_guardado_manda_al_descifrar() -> None:
    fuerte = cifrar(SECRETO, CONTRASENA, HUELLA, ParametrosKdf(131072, 4, 2))
    assert ParametrosKdf.de_json(fuerte.kdf).memoria_kib == 131072
    assert descifrar(fuerte, CONTRASENA, HUELLA) == SECRETO


def test_contrasena_de_clave_corta_o_comun_se_rechaza() -> None:
    with pytest.raises(ContrasenaRechazada, match=str(MINIMO_CLAVE)):
        exigir_contrasena_de_clave("a" * (MINIMO_CLAVE - 1))
    exigir_contrasena_de_clave("a" * MINIMO_CLAVE + "b")  # 13: pasa
    for comun in ("123456789012", "  Administrador  ", "QWERTYUIOPAS"):
        with pytest.raises(ContrasenaRechazada, match="demasiado"):
            exigir_contrasena_de_clave(comun)
    with pytest.raises(ContrasenaRechazada):
        exigir_contrasena_de_clave("x" * 129)
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_json_estricto.py tests/unit/test_secretos.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'seguridad.json_estricto'`
(y `seguridad.secretos`).
```bash
git add tests/unit/test_json_estricto.py tests/unit/test_secretos.py
git commit -m "test(seguridad): lector JSON estricto y cifrado de secretos en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`seguridad/json_estricto.py`**
```python
"""Lector JSON estricto para todo lo que viene de fuera (spec S3 §7.3 y §8.4; RV-16).

Rechaza lo que `json.loads` acepta por omisión y que dos lectores podrían interpretar distinto o
usar para agotar la memoria: `NaN`, `Infinity` y `-Infinity`; claves duplicadas; anidamiento de
más de 64 niveles (o `RecursionError`); y toda cifra fuera del patrón `PATRON_CIFRA`, que se
comprueba ANTES de construir un `Decimal` (un `1E+999999999` no llega a `Decimal`).

El patrón admite hasta 20 dígitos enteros y 28 decimales: el motor no redondea (prec 28,
NORMAS §2), así que un precio unitario guardado puede traer 28 decimales. El ejemplo del spec
(15 y 12) se amplió por eso (RP8-13). Nunca hay exponente ni signo `+`.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from decimal import Decimal
from typing import Any

MAX_NIVELES = 64
PATRON_CIFRA = re.compile(r"^-?[0-9]{1,20}(\.[0-9]{1,28})?$")  # [0-9]: \d acepta otros alfabetos


class JsonRechazado(ValueError):  # noqa: N818
    """Un JSON que no cumple el lector estricto; el mensaje dice por qué, sin traza."""


def a_decimal(texto: object) -> Decimal:
    """`Decimal` de un texto que cumple `PATRON_CIFRA`; `JsonRechazado` si no."""
    if not isinstance(texto, str) or not PATRON_CIFRA.fullmatch(texto):
        raise JsonRechazado(f"cifra fuera del patron estricto: {str(texto)[:40]!r}")
    return Decimal(texto)


def _pares(pares: list[tuple[str, Any]]) -> dict[str, Any]:
    repetidas = [clave for clave, n in Counter(c for c, _ in pares).items() if n > 1]
    if repetidas:
        raise JsonRechazado(f"clave JSON duplicada: {repetidas[0]!r}")
    return dict(pares)


def _constante(nombre: str) -> Any:
    raise JsonRechazado(f"constante no admitida: {nombre}")


def _entero(texto: str) -> int:
    if not PATRON_CIFRA.fullmatch(texto):
        raise JsonRechazado(f"cifra fuera del patron estricto: {texto[:40]!r}")
    return int(texto)


def _decimal(texto: str) -> Decimal:
    return a_decimal(texto)


def _profundidad(valor: Any) -> int:
    """Niveles de anidamiento, sin recursión (un JSON hostil no debe agotar la pila)."""
    maxima, pila = 0, [(valor, 1)]
    while pila:
        actual, nivel = pila.pop()
        if isinstance(actual, dict):
            hijos = list(actual.values())
        elif isinstance(actual, list):
            hijos = actual
        else:
            continue
        maxima = max(maxima, nivel)
        pila.extend((hijo, nivel + 1) for hijo in hijos)
    return maxima


def leer_json(datos: bytes | str, *, max_niveles: int = MAX_NIVELES) -> Any:
    """El valor JSON de `datos` (UTF-8 estricto) o `JsonRechazado`.

    Los números enteros salen como `int` y los que traen punto como `Decimal`; los montos de los
    documentos de Sílice viajan como texto y se convierten con `a_decimal`.
    """
    try:
        texto = datos if isinstance(datos, str) else datos.decode("utf-8")
        valor = json.loads(
            texto,
            object_pairs_hook=_pares,
            parse_constant=_constante,
            parse_int=_entero,
            parse_float=_decimal,
        )
    except JsonRechazado:
        raise
    except RecursionError:
        raise JsonRechazado("JSON demasiado anidado") from None
    except (UnicodeDecodeError, ValueError) as error:
        raise JsonRechazado(f"no es un JSON valido: {str(error)[:80]}") from None
    if _profundidad(valor) > max_niveles:
        raise JsonRechazado(f"JSON anidado a mas de {max_niveles} niveles")
    return valor
```
**`seguridad/secretos.py`**
```python
"""Secretos cifrados con contraseña: Argon2id -> AES-GCM (maestro §4.4, RV-13; spec S3 §7.1).

Un solo módulo para todo secreto de la instalación que se guarda cifrado con una contraseña: la
clave de firma de la empresa (S3) y la clave de IA de la empresa (S4, que lo importa). No hay
criptografía propia: se componen dos primitivas de las bibliotecas.

    clave de 32 B = Argon2id(contraseña, sal de 16 B; m >= 64 MiB, t >= 3)
    cifrado       = AES-GCM(clave, nonce de 12 B, secreto, dato asociado)
    dato asociado = b"silice-clave-v1" + huella pública (UTF-8)

El dato asociado ata el cifrado a la huella de la clave pública: un cifrado movido a otra fila
no descifra. Una contraseña errónea (o un dato asociado distinto) da `InvalidTag`; el llamador
la convierte en un mensaje sin traza.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

__all__ = [
    "InvalidTag",
    "MINIMO_CLAVE",
    "ContrasenaRechazada",
    "ParametrosKdf",
    "SecretoCifrado",
    "cifrar",
    "descifrar",
    "exigir_contrasena_de_clave",
]

PREFIJO_DATO_ASOCIADO = b"silice-clave-v1"
TAMANO_SAL = 16
TAMANO_NONCE = 12
TAMANO_CLAVE = 32
#: Minimo de caracteres de la contraseña de una clave (spec S3 §7.1).
MINIMO_CLAVE = 12
MAXIMO_CLAVE = 128
#: Mínimos de S3 §7.1 para Argon2id (m >= 64 MiB, t >= 3): por debajo no se cifra.
MEMORIA_MINIMA_KIB = 65536
PASADAS_MINIMAS = 3

#: Lista corta de contraseñas comunes que se rechazan (minusculas, sin espacios en los bordes).
#: SUPUESTO_DECLARADO: no es un diccionario completo; es el filtro minimo de S3 §7.1.
CONTRASENAS_COMUNES = frozenset(
    {
        "password", "password1", "password12", "password123", "passw0rd1234", "contrasena",
        "contrasena1", "contrasena12", "contrasena123", "contraseña", "contraseña1",
        "contraseña12", "contraseña123", "123456", "1234567", "12345678", "123456789",
        "1234567890", "12345678901", "123456789012", "1234567890123", "0123456789",
        "qwerty", "qwertyuiop", "qwertyuiopas", "qwerty123456", "asdfghjkl", "asdfghjklñ",
        "abcdefghijkl", "abc123456789", "iloveyou", "letmein", "welcome", "welcome123",
        "admin", "admin123", "administrador", "administrador1", "admin1234567",
        "silice", "silice123", "silice2026", "silice123456", "arenia", "arenia123",
        "venezuela", "venezuela123", "caracas123", "11111111", "111111111111",
        "000000000000", "aaaaaaaaaaaa", "changeme", "changeme123", "cambiame",
    }
)


class ContrasenaRechazada(ValueError):  # noqa: N818
    """La contraseña no cumple la política; el mensaje dice cuál regla y no la repite."""


@dataclass(frozen=True, slots=True)
class ParametrosKdf:
    """Parámetros de Argon2id con que se derivó una clave; se guardan junto al cifrado."""

    memoria_kib: int = 65536
    pasadas: int = 3
    paralelismo: int = 4

    def __post_init__(self) -> None:
        if self.memoria_kib < MEMORIA_MINIMA_KIB or self.pasadas < PASADAS_MINIMAS:
            raise ValueError(
                "parametros de Argon2id por debajo del minimo (m >= 64 MiB, t >= 3)"
            )
        if self.paralelismo < 1:
            raise ValueError("el paralelismo de Argon2id debe ser >= 1")

    def a_json(self) -> str:
        return json.dumps(
            {"alg": "argon2id", "v": 19, "m": self.memoria_kib, "t": self.pasadas,
             "p": self.paralelismo},
            sort_keys=True,
        )

    @classmethod
    def de_json(cls, texto: str) -> ParametrosKdf:
        datos = json.loads(texto)
        if datos.get("alg") != "argon2id" or datos.get("v") != 19:
            raise ValueError("el cifrado no usa Argon2id version 19")
        return cls(datos["m"], datos["t"], datos["p"])


@dataclass(frozen=True, slots=True)
class SecretoCifrado:
    """Lo que se guarda: parámetros del KDF (JSON), sal, nonce y el cifrado con su etiqueta."""

    kdf: str
    sal: bytes
    nonce: bytes
    cifrado: bytes


def exigir_contrasena_de_clave(contrasena: str) -> None:
    """`ContrasenaRechazada` si mide menos de 12, más de 128 o está en la lista de comunes."""
    if len(contrasena) < MINIMO_CLAVE:
        raise ContrasenaRechazada(
            f"La contraseña de la clave debe tener al menos {MINIMO_CLAVE} caracteres."
        )
    if len(contrasena) > MAXIMO_CLAVE:
        raise ContrasenaRechazada(f"La contraseña de la clave admite hasta {MAXIMO_CLAVE}.")
    if contrasena.strip().casefold() in CONTRASENAS_COMUNES:
        raise ContrasenaRechazada("Esa contraseña es demasiado común; elija otra.")


def _derivar(contrasena: str, sal: bytes, parametros: ParametrosKdf) -> bytes:
    return hash_secret_raw(
        contrasena.encode("utf-8"),
        sal,
        time_cost=parametros.pasadas,
        memory_cost=parametros.memoria_kib,
        parallelism=parametros.paralelismo,
        hash_len=TAMANO_CLAVE,
        type=Type.ID,
    )


def _dato_asociado(huella_publica: str) -> bytes:
    return PREFIJO_DATO_ASOCIADO + huella_publica.encode("utf-8")


def cifrar(
    secreto: bytes,
    contrasena: str,
    huella_publica: str,
    parametros: ParametrosKdf | None = None,
) -> SecretoCifrado:
    """Cifra `secreto` con la contraseña. Sal y nonce nuevos en cada llamada."""
    parametros = parametros or ParametrosKdf()
    sal = secrets.token_bytes(TAMANO_SAL)
    nonce = secrets.token_bytes(TAMANO_NONCE)
    clave = _derivar(contrasena, sal, parametros)
    cifrado = AESGCM(clave).encrypt(nonce, secreto, _dato_asociado(huella_publica))
    return SecretoCifrado(parametros.a_json(), sal, nonce, cifrado)


def descifrar(cifrado: SecretoCifrado, contrasena: str, huella_publica: str) -> bytes:
    """El secreto original; `InvalidTag` si la contraseña o la huella no son las del cifrado."""
    parametros = ParametrosKdf.de_json(cifrado.kdf)
    clave = _derivar(contrasena, cifrado.sal, parametros)
    return AESGCM(clave).decrypt(cifrado.nonce, cifrado.cifrado, _dato_asociado(huella_publica))
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_json_estricto.py tests/unit/test_secretos.py -v -W error` →
verde.
Run: `uv run ruff check seguridad/json_estricto.py seguridad/secretos.py` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add seguridad/json_estricto.py seguridad/secretos.py
git commit -m "feat(seguridad): lector JSON estricto y Argon2id a AES-GCM para secretos" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 5: Roles y permisos, cuentas, sesiones, red local y registro de accesos

**Rama:** `inc/080-s3-1-seguridad`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `seguridad/permisos.py`, `seguridad/eventos.py`, `seguridad/cuentas.py`,
  `seguridad/sesiones.py`, `seguridad/red.py`
- Crear: `tests/fixtures/instalacion.py`
- Prueba: `tests/unit/test_permisos.py`, `tests/unit/test_cuentas.py`, `tests/unit/test_sesiones.py`

**Interfaces:**
- Consume: `seguridad.modelo.*`, `seguridad.base.{crear_motor, abrir_sesion}` (tarea 3);
  `seguridad.secretos` no (las cuentas usan `argon2.PasswordHasher`).
- Produce:
  - `seguridad.permisos`: `class Rol(StrEnum)`
  - `seguridad.permisos`: `class Accion(StrEnum)`
  - `seguridad.permisos`: `class Sensible(StrEnum)`
  - `seguridad.permisos`: `class PermisoDenegado(PermissionError)`
  - `seguridad.permisos`: `def roles_de(texto: str) -> frozenset[Rol]`
  - `seguridad.permisos`: `def texto_de_roles(roles: Iterable[Rol | str]) -> str`
  - `seguridad.permisos`: `def permitido(roles: Iterable[Rol], accion: Accion) -> bool`
  - `seguridad.permisos`: `def exigir(roles: Iterable[Rol], accion: Accion) -> None`
  - `seguridad.permisos`: `def aviso_de_roles(roles: Iterable[Rol]) -> str | None`
  - `seguridad.eventos`: `def registrar(session: Session, tipo: str, ahora: datetime, *, login:
      str='', usuario_id: int | None=None, ip: str='', detalle: str='') -> EventoAcceso`
  - `seguridad.eventos`: `def ultimos(session: Session, cuantos: int=200) -> list[EventoAcceso]`
  - `seguridad.cuentas`: `class ErrorDeAcceso(ValueError)`
  - `seguridad.cuentas`: `class CuentaBloqueada(ErrorDeAcceso)`
  - `seguridad.cuentas`: `class ContrasenaInvalida(ValueError)`
  - `seguridad.cuentas`: `class FrenoGlobal`
  - `seguridad.cuentas`: `def normalizar_login(login: str) -> str`
  - `seguridad.cuentas`: `def validar_login(login: str) -> str`
  - `seguridad.cuentas`: `def validar_contrasena(contrasena: str, login: str='') -> None`
  - `seguridad.cuentas`: `def texto_responsable(nombre: str, login: str, restablecida_por_admin:
      bool=False) -> str`
  - `seguridad.cuentas`: `def responsable_de(usuario: Usuario) -> str`
  - `seguridad.cuentas`: `def autenticar(session: Session, login: str, contrasena: str, ahora:
      datetime, *, ip: str='', freno: FrenoGlobal | None=None, dormir: Dormir=time.sleep) ->
      Usuario`
  - `seguridad.cuentas`: `def purgar_intentos_de_inexistentes(session: Session, ahora: datetime)
      -> int`
  - `seguridad.cuentas`: `def formato_codigo(codigo: str) -> str`
  - `seguridad.cuentas`: `def emitir_codigo(session: Session, carpeta: Path, ahora: datetime, *,
      motivo: str='primera vez') -> str`
  - `seguridad.cuentas`: `def hay_usuarios(session: Session) -> bool`
  - `seguridad.cuentas`: `def preparar_primera_vez(session: Session, carpeta: Path, ahora:
      datetime) -> str | None`
  - `seguridad.cuentas`: `def reclamar_instalacion(session: Session, codigo: str, login: str,
      nombre: str, contrasena: str, ahora: datetime, carpeta: Path, *, ip: str='', freno:
      FrenoGlobal | None=None, dormir: Dormir=time.sleep) -> Usuario`
  - `seguridad.cuentas`: `def emitir_codigo_de_restablecimiento(session: Session, carpeta: Path,
      ahora: datetime) -> str`
  - `seguridad.cuentas`: `def crear_usuario(session: Session, actor: Usuario, login: str,
      nombre: str, roles: Iterable[Rol | str], contrasena_temporal: str, ahora: datetime) ->
      Usuario`
  - `seguridad.cuentas`: `def cambiar_roles(session: Session, actor: Usuario, usuario_id: int,
      roles: Iterable[Rol | str], ahora: datetime) -> Usuario`
  - `seguridad.cuentas`: `def desactivar(session: Session, actor: Usuario, usuario_id: int,
      ahora: datetime) -> None`
  - `seguridad.cuentas`: `def reactivar(session: Session, actor: Usuario, usuario_id: int,
      ahora: datetime) -> None`
  - `seguridad.cuentas`: `def desbloquear(session: Session, actor: Usuario, login: str, ahora:
      datetime) -> None`
  - `seguridad.cuentas`: `def restablecer(session: Session, actor: Usuario, usuario_id: int,
      contrasena_temporal: str, ahora: datetime) -> None`
  - `seguridad.cuentas`: `def cambiar_contrasena(session: Session, usuario_id: int, actual: str,
      nueva: str, ahora: datetime) -> str`
  - `seguridad.sesiones`: `class SesionActiva`
  - `seguridad.sesiones`: `def huella_de(ficha: str) -> str`
  - `seguridad.sesiones`: `def abrir(session: Session, usuario: Usuario, ahora: datetime) -> str`
  - `seguridad.sesiones`: `def cerrar(session: Session, ficha: str, motivo: str, ahora:
      datetime) -> bool`
  - `seguridad.sesiones`: `def cerrar_todas(session: Session, usuario_id: int, motivo: str) ->
      int`
  - `seguridad.sesiones`: `def validar(session: Session, ficha: str | None, ahora: datetime) ->
      SesionActiva | None`
  - `seguridad.red`: `def red_local_activa(entorno: Mapping[str, str] | None=None) -> bool`
  - `seguridad.red`: `def es_bucle_local(ip: str | None) -> bool`
  - `seguridad.red`: `def es_local(ip: str | None, *, red_local_encendida: bool) -> bool`
  - `tests.fixtures.instalacion`: `AHORA`, `CONTRASENA`, `instalacion(carpeta)`, `administrador(bd,
    carpeta)`, `persona(bd, admin, login, roles)`.

Fronteras exactas de RS3-2 (supuestos declarados): el quinto fallo seguido bloquea y el cuarto no;
el bloqueo dura 15 minutos exactos; el freno global es de 20 fallos en 10 minutos con espera
progresiva; la sesión expira a los 30 minutos de inactividad (29:59 sigue, 30:00 expira) y a las 12
horas de antigüedad (11:59:59 sigue, 12:00:00 expira); el código de instalación tiene 20
caracteres base32 (100 bits) y su huella no es el código; un login inexistente se verifica contra
una huella de relleno para que el tiempo y el mensaje no delaten si existe; a las 24 horas se
purgan los contadores de logins inexistentes.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/fixtures/instalacion.py`**
```python
"""Base de la instalación de prueba (S3-1): tablas de `seguridad`, en un archivo temporal.

La deriva entre estas tablas y la revisión `ins_0001_seguridad` la vigila
`tests/integration/test_migraciones.py` (RNF-20); aquí basta `create_all`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from seguridad import cuentas
from seguridad.base import abrir_sesion, crear_motor
from seguridad.modelo import Base, Usuario

AHORA = datetime(2026, 11, 10, 9, 0, 0)
CONTRASENA = "una contrasena larga de prueba"


@contextmanager
def instalacion(carpeta: Path) -> Iterator[Session]:
    """Una sesión sobre una `instalacion.db` nueva en `carpeta`."""
    carpeta.mkdir(parents=True, exist_ok=True)
    motor = crear_motor(carpeta / "instalacion.db")
    Base.metadata.create_all(motor)
    sesion = abrir_sesion(motor)
    try:
        yield sesion
    finally:
        sesion.close()
        motor.dispose()


def administrador(sesion: Session, carpeta: Path, login: str = "admin") -> Usuario:
    """El primer administrador, por el camino real: código de instalación y reclamo."""
    codigo = cuentas.emitir_codigo(sesion, carpeta, AHORA)
    return cuentas.reclamar_instalacion(
        sesion, codigo, login, "Admin de Prueba", CONTRASENA, AHORA, carpeta,
        freno=cuentas.FrenoGlobal(),
    )


def persona(
    sesion: Session, actor: Usuario, login: str, roles: tuple[str, ...], nombre: str = ""
) -> Usuario:
    return cuentas.crear_usuario(
        sesion, actor, login, nombre or login.title(), roles, CONTRASENA, AHORA
    )
```
**`tests/unit/test_permisos.py`**
```python
"""La matriz de roles de S3 §5.1, escrita a mano fila por fila (RF-80; P2 ratificada)."""

from __future__ import annotations

import pytest

from seguridad.permisos import (
    PERMISOS,
    Accion,
    PermisoDenegado,
    Rol,
    aviso_de_roles,
    exigir,
    permitido,
    roles_de,
    texto_de_roles,
)

#: (acción, arma, revisa, administrador): la tabla de §5.1, no derivada de PERMISOS.
MATRIZ = (
    (Accion.EDITAR_HOJA, True, False, False),
    (Accion.CONVERTIR_Y_REAJUSTAR, True, False, False),
    (Accion.CONTROL_DE_OBRA, True, False, False),
    (Accion.DECIDIR_RECUPERACION, True, False, False),
    (Accion.ENTREGAR_PAQUETE, True, False, False),
    (Accion.LEER_PROYECTO, True, True, False),
    (Accion.REVISAR_PAQUETE, False, True, False),
    (Accion.CAMBIAR_CASO, True, False, True),
    (Accion.ADMINISTRAR_CUENTAS, False, False, True),
    (Accion.ADMINISTRAR_EMPRESA, False, False, True),
    (Accion.ADMINISTRAR_PRECIOS, False, False, True),
    (Accion.ADMINISTRAR_RED_Y_API, False, False, True),
    (Accion.CAMBIAR_CARPETA_DE_DATOS, False, False, True),
)


def test_la_matriz_cubre_todas_las_acciones() -> None:
    assert {fila[0] for fila in MATRIZ} == set(Accion) == set(PERMISOS)


@pytest.mark.parametrize("accion,arma,revisa,admin", MATRIZ)
def test_cada_fila_de_la_matriz(accion: Accion, arma: bool, revisa: bool, admin: bool) -> None:
    assert permitido({Rol.ARMA}, accion) is arma
    assert permitido({Rol.REVISA}, accion) is revisa
    assert permitido({Rol.ADMINISTRADOR}, accion) is admin
    # varios roles suman
    assert permitido({Rol.ARMA, Rol.REVISA, Rol.ADMINISTRADOR}, accion) is (
        arma or revisa or admin
    )


def test_exigir_rechaza_con_un_mensaje_llano() -> None:
    with pytest.raises(PermisoDenegado, match="no tiene permiso"):
        exigir({Rol.REVISA}, Accion.EDITAR_HOJA)
    exigir({Rol.ARMA}, Accion.EDITAR_HOJA)


def test_los_roles_se_guardan_ordenados_y_sin_repetir() -> None:
    assert texto_de_roles(["revisa", Rol.ARMA, "arma"]) == "arma,revisa"
    assert roles_de("arma,revisa,inventado") == {Rol.ARMA, Rol.REVISA}
    with pytest.raises(ValueError):
        texto_de_roles([])


def test_armar_y_revisar_a_la_vez_se_informa_sin_impedirlo() -> None:
    assert "ella misma armó" in aviso_de_roles({Rol.ARMA, Rol.REVISA})
    assert aviso_de_roles({Rol.ARMA}) is None
```
**`tests/unit/test_cuentas.py`**
```python
"""Cuentas, contraseñas, bloqueo y primer administrador (RF-80, RF-81; spec S3 §5.2 a §5.5)."""

from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest

from seguridad import cuentas, eventos
from seguridad.modelo import CodigoInstalacion, EventoAcceso, Usuario
from seguridad.permisos import PermisoDenegado
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, instalacion, persona

MALA = "mala contrasena larga"


@pytest.fixture
def freno() -> cuentas.FrenoGlobal:
    return cuentas.FrenoGlobal()


def _entrar(sesion, login, contrasena, freno, cuando=AHORA):
    return cuentas.autenticar(
        sesion, login, contrasena, cuando, freno=freno, dormir=lambda segundos: None
    )


# --- primer administrador -------------------------------------------------------------------


def test_el_codigo_tiene_20_caracteres_base32_y_su_huella_no_es_el_codigo(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        assert len(codigo) == 20 and set(codigo) <= set(cuentas.ALFABETO_CODIGO)
        archivo = (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).read_text()
        assert archivo.strip().replace("-", "") == codigo
        fila = sesion.query(CodigoInstalacion).one()
        assert fila.huella != codigo and len(fila.huella) == 64 and fila.usado is None


def test_cien_codigos_no_se_repiten(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        codigos = {cuentas.emitir_codigo(sesion, tmp_path, AHORA) for _ in range(100)}
    assert len(codigos) == 100


def test_el_primer_administrador_se_crea_con_el_codigo_y_el_archivo_se_borra(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.preparar_primera_vez(sesion, tmp_path, AHORA)
        assert codigo is not None and (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).exists()
        assert cuentas.preparar_primera_vez(sesion, tmp_path, AHORA) is None  # ya hay uno vigente
        usuario = cuentas.reclamar_instalacion(
            sesion, codigo.lower(), "Admin", "Ana Admin", CONTRASENA, AHORA, tmp_path
        )
        assert usuario.roles == "administrador" and usuario.login == "admin"
        assert not (tmp_path / cuentas.NOMBRE_ARCHIVO_CODIGO).exists()
        assert sesion.query(CodigoInstalacion).one().usado == AHORA


def test_un_codigo_usado_o_ajeno_se_rechaza(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        codigo = cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        cuentas.reclamar_instalacion(sesion, codigo, "admin", "A", CONTRASENA, AHORA, tmp_path)
        for malo in (codigo, "A" * 20, ""):
            with pytest.raises(cuentas.ErrorDeAcceso, match="código de instalación"):
                cuentas.reclamar_instalacion(
                    sesion, malo, "otro", "B", CONTRASENA, AHORA, tmp_path, freno=freno
                )
        assert sesion.query(Usuario).count() == 1


def test_con_cuentas_el_codigo_de_primera_vez_no_sirve_pero_el_de_restablecimiento_si(
    tmp_path: Path, freno
) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        tardio = cuentas.emitir_codigo(sesion, tmp_path, AHORA)  # primera vez, con cuentas
        with pytest.raises(cuentas.ErrorDeAcceso):
            cuentas.reclamar_instalacion(
                sesion, tardio, "nuevo", "N", CONTRASENA, AHORA, tmp_path, freno=freno
            )
        rescate = cuentas.emitir_codigo_de_restablecimiento(sesion, tmp_path, AHORA)
        otra = "otra contrasena larga distinta"
        recuperado = cuentas.reclamar_instalacion(
            sesion, rescate, admin.login, "Admin", otra, AHORA, tmp_path, freno=freno
        )
        assert recuperado.id == admin.id
        assert _entrar(sesion, "admin", otra, freno).id == admin.id


def test_5_codigos_malos_seguidos_bloquean_el_reclamo(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        cuentas.emitir_codigo(sesion, tmp_path, AHORA)
        for _ in range(4):
            with pytest.raises(cuentas.ErrorDeAcceso) as error:
                cuentas.reclamar_instalacion(
                    sesion, "A" * 20, "x", "x", CONTRASENA, AHORA, tmp_path, freno=freno
                )
            assert not isinstance(error.value, cuentas.CuentaBloqueada)
        with pytest.raises(cuentas.CuentaBloqueada):
            cuentas.reclamar_instalacion(
                sesion, "A" * 20, "x", "x", CONTRASENA, AHORA, tmp_path, freno=freno
            )


# --- contraseñas ----------------------------------------------------------------------------


def test_politica_de_contrasenas() -> None:
    cuentas.validar_contrasena("a" * 10, "ana")  # 10 pasa
    with pytest.raises(cuentas.ContrasenaInvalida):
        cuentas.validar_contrasena("a" * 9, "ana")
    cuentas.validar_contrasena("ñ" * 128, "ana")  # 128 pasa, Unicode
    with pytest.raises(cuentas.ContrasenaInvalida):
        cuentas.validar_contrasena("a" * 129, "ana")
    with pytest.raises(cuentas.ContrasenaInvalida, match="igual al usuario"):
        cuentas.validar_contrasena("administrador", "Administrador")
    with pytest.raises(cuentas.ContrasenaInvalida, match="común"):
        cuentas.validar_contrasena("1234567890", "ana")


def test_ninguna_contrasena_queda_en_la_base_ni_en_los_eventos(tmp_path: Path, freno) -> None:
    secreta = "esta-contrasena-no-debe-aparecer-1"
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        cuentas.crear_usuario(sesion, admin, "luis", "Luis", ["arma"], secreta, AHORA)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "luis", secreta + "x", freno)
        cuentas.restablecer(sesion, admin, 2, secreta + "2", AHORA)
        texto = " ".join(
            f"{e.login_intentado} {e.detalle} {e.tipo}" for e in eventos.ultimos(sesion)
        )
        assert secreta not in texto and CONTRASENA not in texto
        huella = sesion.get(Usuario, 2).huella_clave
        assert huella.startswith("$argon2id$") and secreta not in huella
        sesion.commit()
    bruto = (tmp_path / "instalacion.db").read_bytes()
    for secreto in (secreta, CONTRASENA):
        assert secreto.encode() not in bruto


# --- bloqueo --------------------------------------------------------------------------------


@pytest.mark.parametrize("existe", [True, False])
def test_4_fallos_no_bloquean_y_el_quinto_si(tmp_path: Path, freno, existe: bool) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        login = "admin" if existe else "fantasma"
        for _ in range(4):
            with pytest.raises(cuentas.ErrorDeAcceso) as error:
                _entrar(sesion, login, MALA, freno)
            assert str(error.value) == cuentas.MENSAJE_FALLO
        if existe:  # el cuarto fallo no bloqueó: la contraseña buena aún entra y reinicia
            assert _entrar(sesion, login, CONTRASENA, freno).id == admin.id
            for _ in range(4):
                with pytest.raises(cuentas.ErrorDeAcceso):
                    _entrar(sesion, login, MALA, freno)
        with pytest.raises(cuentas.CuentaBloqueada) as quinto:
            _entrar(sesion, login, MALA, freno)
        assert str(quinto.value) == cuentas.MENSAJE_BLOQUEO
        with pytest.raises(cuentas.CuentaBloqueada):  # ni con la buena mientras dure
            _entrar(sesion, login, CONTRASENA, freno)


def test_el_bloqueo_dura_15_minutos_exactos(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        for _ in range(5):
            with pytest.raises(cuentas.ErrorDeAcceso):
                _entrar(sesion, "admin", MALA, freno)
        casi = AHORA + timedelta(minutes=15) - timedelta(seconds=1)
        with pytest.raises(cuentas.CuentaBloqueada):
            _entrar(sesion, "admin", CONTRASENA, freno, casi)
        assert _entrar(sesion, "admin", CONTRASENA, freno, AHORA + timedelta(minutes=15))


def test_el_administrador_desbloquea(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        for _ in range(5):
            with pytest.raises(cuentas.ErrorDeAcceso):
                _entrar(sesion, "luis", MALA, freno)
        cuentas.desbloquear(sesion, admin, "luis", AHORA)
        assert _entrar(sesion, "luis", CONTRASENA, freno).id == luis.id
        with pytest.raises(PermisoDenegado):  # luis no es administrador
            cuentas.desbloquear(sesion, luis, "luis", AHORA)


def test_un_login_inexistente_se_verifica_contra_la_huella_de_relleno(
    tmp_path: Path, freno, monkeypatch
) -> None:
    vistas: list[str] = []
    verdadera = cuentas._coincide

    def espia(huella: str, contrasena: str) -> bool:
        vistas.append(huella)
        return verdadera(huella, contrasena)

    monkeypatch.setattr(cuentas, "_coincide", espia)
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "no-existe", CONTRASENA, freno)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "admin", MALA, freno)
        assert vistas[0] == cuentas._huella_de_relleno()
        assert vistas[1] == admin.huella_clave != vistas[0]


def test_una_cuenta_desactivada_no_entra_con_el_mismo_mensaje(tmp_path: Path, freno) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        cuentas.desactivar(sesion, admin, luis.id, AHORA)
        with pytest.raises(cuentas.ErrorDeAcceso) as error:
            _entrar(sesion, "luis", CONTRASENA, freno)
        assert str(error.value) == cuentas.MENSAJE_FALLO


@pytest.mark.parametrize(
    "fallos,espera",
    [(19, 0.0), (20, 1.0), (21, 2.0), (22, 4.0), (25, 32.0), (26, 60.0), (40, 60.0)],
)
def test_freno_global_espera_progresiva(fallos: int, espera: float) -> None:
    freno = cuentas.FrenoGlobal()
    for _ in range(fallos):
        freno.registrar_fallo(AHORA)
    assert freno.espera(AHORA) == espera
    assert freno.espera(AHORA + timedelta(minutes=10)) == 0.0  # la ventana de 10 min se vació


def test_el_freno_global_hace_dormir_al_intento(tmp_path: Path) -> None:
    freno, dormidas = cuentas.FrenoGlobal(), []
    for _ in range(20):
        freno.registrar_fallo(AHORA)
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        cuentas.autenticar(sesion, "admin", CONTRASENA, AHORA, freno=freno, dormir=dormidas.append)
    assert dormidas == [1.0]


def test_el_semaforo_limita_las_verificaciones_simultaneas(monkeypatch) -> None:
    activas, maxima, candado = [0], [0], threading.Lock()

    class HasherLento:
        def verify(self, huella: str, contrasena: str) -> bool:
            with candado:
                activas[0] += 1
                maxima[0] = max(maxima[0], activas[0])
            time.sleep(0.03)
            with candado:
                activas[0] -= 1
            return True

    monkeypatch.setattr(cuentas, "_hasher", HasherLento())
    hilos = [threading.Thread(target=cuentas._coincide, args=("h", "c")) for _ in range(16)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert 1 <= maxima[0] <= cuentas.VERIFICACIONES_SIMULTANEAS


def test_los_contadores_de_logins_inexistentes_se_purgan_a_las_24_horas(tmp_path, freno):
    with instalacion(tmp_path) as sesion:
        administrador(sesion, tmp_path)
        with pytest.raises(cuentas.ErrorDeAcceso):
            _entrar(sesion, "fantasma", MALA, freno)
        assert cuentas.purgar_intentos_de_inexistentes(sesion, AHORA + timedelta(hours=23)) == 0
        assert cuentas.purgar_intentos_de_inexistentes(sesion, AHORA + timedelta(hours=24)) == 1


# --- administrar ----------------------------------------------------------------------------


def test_alta_con_temporal_obliga_a_cambiarla_y_cambiarla_da_ficha_nueva(tmp_path, freno):
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        assert luis.debe_cambiar_clave
        entrada = _entrar(sesion, "luis", CONTRASENA, freno)
        nueva = "otra contrasena larga y nueva"
        ficha = cuentas.cambiar_contrasena(sesion, entrada.id, CONTRASENA, nueva, AHORA)
        assert ficha and not sesion.get(Usuario, luis.id).debe_cambiar_clave
        assert _entrar(sesion, "luis", nueva, freno).id == luis.id
        with pytest.raises(cuentas.ErrorDeAcceso):
            cuentas.cambiar_contrasena(sesion, luis.id, "no es la actual", nueva + "2", AHORA)


def test_no_se_puede_dejar_la_instalacion_sin_administrador(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        with pytest.raises(ValueError, match="al menos un administrador"):
            cuentas.desactivar(sesion, admin, admin.id, AHORA)
        with pytest.raises(ValueError, match="al menos un administrador"):
            cuentas.cambiar_roles(sesion, admin, admin.id, ["arma"], AHORA)


def test_un_alta_repetida_o_con_login_malo_se_rechaza(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        persona(sesion, admin, "luis", ("arma",))
        with pytest.raises(ValueError, match="Ya existe"):
            persona(sesion, admin, "LUIS", ("arma",))
        for malo in ("ab", "con espacio", "x" * 41, "ñandú"):
            with pytest.raises(ValueError, match="usuario"):
                cuentas.validar_login(malo)


def test_el_responsable_es_nombre_y_login_y_se_marca_tras_un_restablecimiento(tmp_path):
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",), "Luis Pérez")
        assert cuentas.responsable_de(luis) == "Luis Pérez <luis>"
        cuentas.restablecer(sesion, admin, luis.id, "otra contrasena temporal", AHORA)
        marcado = cuentas.responsable_de(sesion.get(Usuario, luis.id))
        assert marcado == "Luis Pérez <luis> (tras restablecimiento)"
        largo = Usuario(login="x" * 40, nombre="N" * 300, roles="arma", restablecida_por_admin=True)
        assert len(cuentas.responsable_de(largo)) <= 120


def test_cada_accion_de_administracion_queda_en_el_registro(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        cuentas.cambiar_roles(sesion, admin, luis.id, ["arma", "revisa"], AHORA)
        cuentas.desactivar(sesion, admin, luis.id, AHORA)
        tipos = [e.tipo for e in sesion.query(EventoAcceso).order_by(EventoAcceso.id)]
        assert {"alta", "cambio de roles", "baja", "codigo de instalacion"} <= set(tipos)
```
**`tests/unit/test_sesiones.py`**
```python
"""Fichas de sesión: expiración exacta, roles leídos de la base e invalidaciones (RF-81)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from seguridad import cuentas, sesiones
from seguridad.modelo import Sesion
from seguridad.permisos import Rol
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, instalacion, persona


@pytest.fixture
def abierta(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        luis = persona(sesion, admin, "luis", ("arma",))
        ficha = sesiones.abrir(sesion, luis, AHORA)
        yield sesion, admin, luis, ficha


def test_la_ficha_es_aleatoria_y_la_base_guarda_solo_su_huella(abierta) -> None:
    sesion, _, luis, ficha = abierta
    otra = sesiones.abrir(sesion, luis, AHORA)
    assert ficha != otra and len(ficha) >= 43  # 256 bits en base64url
    guardadas = {fila.huella_ficha for fila in sesion.query(Sesion)}
    assert sesiones.huella_de(ficha) in guardadas and ficha not in guardadas


def test_valida_con_los_datos_de_la_cuenta(abierta) -> None:
    sesion, _, luis, ficha = abierta
    activa = sesiones.validar(sesion, ficha, AHORA)
    assert (activa.login, activa.roles) == ("luis", frozenset({Rol.ARMA}))
    assert sesiones.validar(sesion, None, AHORA) is None
    assert sesiones.validar(sesion, "ficha inventada", AHORA) is None


def test_la_sesion_da_el_usuario_con_la_forma_del_responsable(abierta) -> None:
    """S4 lee `.usuario` y `.roles` de la ficha de sesión (interfaz supuesta por su plan)."""
    sesion, _, luis, ficha = abierta
    activa = sesiones.validar(sesion, ficha, AHORA)
    assert activa.usuario == cuentas.responsable_de(luis) and activa.usuario.endswith("<luis>")
    assert "arma" in activa.roles  # `Rol` es un `StrEnum`: la comparación con texto vale


def test_inactividad_29_59_sigue_y_30_00_expira(abierta) -> None:
    sesion, *_, ficha = abierta
    assert sesiones.validar(sesion, ficha, AHORA + timedelta(minutes=29, seconds=59))
    # la actividad se renovó a los 29:59; 30:00 de silencio después ya expira
    renovada = AHORA + timedelta(minutes=29, seconds=59)
    assert sesiones.validar(sesion, ficha, renovada + timedelta(minutes=30)) is None
    assert sesiones.validar(sesion, ficha, renovada + timedelta(seconds=1)) is None  # ya cerrada


def test_la_actividad_se_renueva_como_mucho_una_vez_por_minuto(abierta) -> None:
    sesion, *_, ficha = abierta
    sesiones.validar(sesion, ficha, AHORA + timedelta(seconds=59))
    fila = sesion.get(Sesion, sesiones.huella_de(ficha))
    assert fila.ultima_actividad == AHORA  # menos de un minuto: no escribe
    sesiones.validar(sesion, ficha, AHORA + timedelta(seconds=60))
    assert fila.ultima_actividad == AHORA + timedelta(seconds=60)


def test_antiguedad_11_59_59_sigue_y_12_00_00_expira(abierta) -> None:
    sesion, *_, ficha = abierta
    cuando = AHORA
    while cuando + timedelta(minutes=29) < AHORA + timedelta(hours=11, minutes=59):
        cuando += timedelta(minutes=29)
        assert sesiones.validar(sesion, ficha, cuando)  # activa de continuo: renueva
    assert sesiones.validar(sesion, ficha, AHORA + timedelta(hours=11, minutes=59, seconds=59))
    assert sesiones.validar(sesion, ficha, AHORA + timedelta(hours=12)) is None


def test_los_roles_se_leen_de_la_base_en_cada_validacion(abierta) -> None:
    sesion, admin, luis, ficha = abierta
    cuentas.cambiar_roles(sesion, admin, luis.id, ["revisa"], AHORA)
    # cambiar roles cierra las fichas: hay que entrar de nuevo, y trae los roles nuevos
    assert sesiones.validar(sesion, ficha, AHORA) is None
    nueva = sesiones.abrir(sesion, luis, AHORA)
    assert sesiones.validar(sesion, nueva, AHORA).roles == frozenset({Rol.REVISA})
    luis.roles = "arma,revisa"  # un cambio hecho en la base fuera de las funciones
    sesion.commit()
    assert sesiones.validar(sesion, nueva, AHORA).roles == frozenset({Rol.ARMA, Rol.REVISA})


@pytest.mark.parametrize("como", ["restablecer", "desactivar", "roles", "contrasena"])
def test_cuatro_cambios_de_cuenta_cierran_las_fichas(abierta, como: str) -> None:
    sesion, admin, luis, ficha = abierta
    otra = sesiones.abrir(sesion, luis, AHORA)
    if como == "restablecer":
        cuentas.restablecer(sesion, admin, luis.id, "temporal larga y nueva", AHORA)
    elif como == "desactivar":
        cuentas.desactivar(sesion, admin, luis.id, AHORA)
    elif como == "roles":
        cuentas.cambiar_roles(sesion, admin, luis.id, ["arma", "revisa"], AHORA)
    else:
        nueva = cuentas.cambiar_contrasena(sesion, luis.id, CONTRASENA, "otra larga y nueva", AHORA)
        assert nueva not in {ficha, otra}
        assert sesiones.validar(sesion, nueva, AHORA)  # la ficha nueva sí vale
    assert sesiones.validar(sesion, ficha, AHORA) is None
    assert sesiones.validar(sesion, otra, AHORA) is None


def test_cerrar_sesion_marca_la_ficha_y_no_vuelve_a_valer(abierta) -> None:
    sesion, *_, ficha = abierta
    assert sesiones.cerrar(sesion, ficha, "salida", AHORA) is True
    assert sesiones.cerrar(sesion, ficha, "salida", AHORA) is False
    assert sesiones.validar(sesion, ficha, AHORA) is None
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_permisos.py tests/unit/test_cuentas.py
tests/unit/test_sesiones.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'seguridad.permisos'` (y
`seguridad.cuentas` en los otros dos).
```bash
git add tests/fixtures/instalacion.py tests/unit/test_permisos.py tests/unit/test_cuentas.py \
  tests/unit/test_sesiones.py
git commit -m "test(seguridad): permisos, cuentas y sesiones con sus fronteras exactas en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  La matriz de permisos de S3 §5.1 (una fila por acción; `permitido` es la única función que
  decide) y las operaciones que solo se hacen desde el propio equipo:
**`seguridad/permisos.py`**
```python
"""Roles, acciones y la matriz de permisos (spec S3 §5.1; maestro §4.1, P2 ratificada).

Una fila de la matriz = una `Accion`. `permitido(roles, accion)` es la única función que decide;
la navegación, cada `render()` de `ui/paginas` y cada función de `ui/` que escribe la llaman.
Las operaciones con secretos de la empresa (`Sensible`) exigen además el propio equipo
(`seguridad.red`).
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum


class Rol(StrEnum):
    ARMA = "arma"
    REVISA = "revisa"
    ADMINISTRADOR = "administrador"


class Accion(StrEnum):
    # Trabajo (rol arma)
    EDITAR_HOJA = "editar_hoja"  # crear proyecto, hoja, versiones, planos, contraste, Excel
    CONVERTIR_Y_REAJUSTAR = "convertir_y_reajustar"  # moneda del proyecto y estudios (S1)
    CONTROL_DE_OBRA = "control_de_obra"  # línea base, valuaciones, costos incurridos (S2)
    DECIDIR_RECUPERACION = "decidir_recuperacion"  # (S2)
    ENTREGAR_PAQUETE = "entregar_paquete"
    # Lectura
    LEER_PROYECTO = "leer_proyecto"
    # Revisión (rol revisa)
    REVISAR_PAQUETE = "revisar_paquete"  # abrir paquetes, reauditar, dictamen
    # Compartida
    CAMBIAR_CASO = "cambiar_caso"
    # Administración
    ADMINISTRAR_CUENTAS = "administrar_cuentas"  # cuentas, desbloqueo, sesiones, accesos
    ADMINISTRAR_EMPRESA = "administrar_empresa"  # empresa, clave de firma, empresas registradas
    ADMINISTRAR_PRECIOS = "administrar_precios"  # lista de la empresa e importar el BCV (S1)
    ADMINISTRAR_RED_Y_API = "administrar_red_y_api"  # red local, API y claves de API
    CAMBIAR_CARPETA_DE_DATOS = "cambiar_carpeta_de_datos"  # (S5)


class Sensible(StrEnum):
    """Lo que solo se hace desde el propio equipo (spec S3 §5.6; maestro §4.7)."""

    FIRMAR = "firmar"
    CLAVE_DE_FIRMA = "clave_de_firma"  # generar, exportar, retirar, revocar
    CLAVE_DE_API = "clave_de_api"  # crear
    CLAVE_DE_IA = "clave_de_ia"  # registrar (S4)
    CARPETA_DE_DATOS = "carpeta_de_datos"  # cambiar (S5)


_ARMA, _REVISA, _ADMIN = Rol.ARMA, Rol.REVISA, Rol.ADMINISTRADOR

#: La matriz de S3 §5.1, una fila por acción. Es la única fuente: `test_permisos` la reproduce
#: a mano, fila por fila y rol por rol.
PERMISOS: dict[Accion, frozenset[Rol]] = {
    Accion.EDITAR_HOJA: frozenset({_ARMA}),
    Accion.CONVERTIR_Y_REAJUSTAR: frozenset({_ARMA}),
    Accion.CONTROL_DE_OBRA: frozenset({_ARMA}),
    Accion.DECIDIR_RECUPERACION: frozenset({_ARMA}),
    Accion.ENTREGAR_PAQUETE: frozenset({_ARMA}),
    Accion.LEER_PROYECTO: frozenset({_ARMA, _REVISA}),
    Accion.REVISAR_PAQUETE: frozenset({_REVISA}),
    Accion.CAMBIAR_CASO: frozenset({_ARMA, _ADMIN}),
    Accion.ADMINISTRAR_CUENTAS: frozenset({_ADMIN}),
    Accion.ADMINISTRAR_EMPRESA: frozenset({_ADMIN}),
    Accion.ADMINISTRAR_PRECIOS: frozenset({_ADMIN}),
    Accion.ADMINISTRAR_RED_Y_API: frozenset({_ADMIN}),
    Accion.CAMBIAR_CARPETA_DE_DATOS: frozenset({_ADMIN}),
}

#: La acción de cada operación sensible: además de este rol, exigen el propio equipo.
ROL_DE_LO_SENSIBLE: dict[Sensible, Accion] = {
    Sensible.FIRMAR: Accion.ENTREGAR_PAQUETE,
    Sensible.CLAVE_DE_FIRMA: Accion.ADMINISTRAR_EMPRESA,
    Sensible.CLAVE_DE_API: Accion.ADMINISTRAR_RED_Y_API,
    Sensible.CLAVE_DE_IA: Accion.ADMINISTRAR_EMPRESA,
    Sensible.CARPETA_DE_DATOS: Accion.CAMBIAR_CARPETA_DE_DATOS,
}


class PermisoDenegado(PermissionError):  # noqa: N818
    """El rol no corresponde a la acción; el mensaje está en lenguaje llano, sin traza."""


def roles_de(texto: str) -> frozenset[Rol]:
    """Los roles de una cuenta guardados como `"arma,revisa"`; ignora lo desconocido."""
    conocidos = {rol.value for rol in Rol}
    return frozenset(Rol(r) for r in texto.split(",") if r in conocidos)


def texto_de_roles(roles: Iterable[Rol | str]) -> str:
    """Los roles normalizados para guardar: sin repetidos y en el orden de `Rol`."""
    pedidos = {Rol(r) for r in roles}
    if not pedidos:
        raise ValueError("una cuenta necesita al menos un rol")
    return ",".join(r.value for r in Rol if r in pedidos)


def permitido(roles: Iterable[Rol], accion: Accion) -> bool:
    return bool(set(roles) & PERMISOS[accion])


def exigir(roles: Iterable[Rol], accion: Accion) -> None:
    """`PermisoDenegado` si ningún rol permite `accion`."""
    if not permitido(roles, accion):
        raise PermisoDenegado("Su cuenta no tiene permiso para esta acción.")


def aviso_de_roles(roles: Iterable[Rol]) -> str | None:
    """Lo que la pantalla de cuentas informa sin impedir (S3 §5.1, P2): arma y revisa a la vez."""
    pedidos = set(roles)
    if {Rol.ARMA, Rol.REVISA} <= pedidos:
        return (
            "Esta cuenta podrá revisar paquetes que ella misma armó; la vista de revisión "
            "lo indicará."
        )
    return None
```
**`seguridad/red.py`**
```python
"""¿El cliente es el propio equipo? (spec S3 §5.6; maestro §4.7, RV-15).

`es_local` acepta solo direcciones de bucle local. La IP la da `st.context.ip_address` (la
interfaz la entrega ya como `str | None`, ver `ui/sesion.py`). Si no hay IP, las operaciones
sensibles se permiten únicamente con la red local apagada: con la red encendida y sin IP, no.
El filtro de IP privadas NO es un control (un túnel o proxy local lo anula): el control real es
la sesión y la clave de API (S3 §12).
"""

from __future__ import annotations

import ipaddress
import os
from collections.abc import Mapping

VARIABLE_RED_LOCAL = "SILICE_RED_LOCAL"
VALOR_ENCENDIDA = "1"


def red_local_activa(entorno: Mapping[str, str] | None = None) -> bool:
    """True si el administrador encendió la red local (apagada por defecto)."""
    entorno = os.environ if entorno is None else entorno
    return entorno.get(VARIABLE_RED_LOCAL) == VALOR_ENCENDIDA


def es_bucle_local(ip: str | None) -> bool:
    """True solo para `127.0.0.0/8` y `::1` (y `::ffff:127.x`); texto malo o vacío, False."""
    if not ip:
        return False
    try:
        direccion = ipaddress.ip_address(ip.strip().split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(direccion, ipaddress.IPv6Address) and direccion.ipv4_mapped is not None:
        direccion = direccion.ipv4_mapped
    return direccion.is_loopback


def es_local(ip: str | None, *, red_local_encendida: bool) -> bool:
    """El cliente es el propio equipo (o no se sabe y no hay red local que lo ponga en duda)."""
    if ip is None or not ip.strip():
        return not red_local_encendida
    return es_bucle_local(ip)
```
  El registro de accesos (sin secretos) y las cuentas: alta, bloqueo, freno global, código de
  instalación y restablecimiento:
**`seguridad/eventos.py`**
```python
"""El registro de accesos (`evento_acceso`): solo-agregar y sin secretos (spec S3 §7.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad.modelo import EventoAcceso

TIPOS = (
    "entrada", "fallo", "bloqueo", "salida", "expiracion", "cambio de clave", "alta", "baja",
    "alta de clave", "cambio de roles", "desbloqueo", "restablecimiento", "firma",
    "paquete exportado", "clave de api", "retiro", "revocacion", "codigo de instalacion",
    "empresa", "clave registrada",
)


def registrar(
    session: Session,
    tipo: str,
    ahora: datetime,
    *,
    login: str = "",
    usuario_id: int | None = None,
    ip: str = "",
    detalle: str = "",
) -> EventoAcceso:
    """Agrega un evento. `detalle` no lleva secretos: lo escribe quien llama, y una prueba
    busca contraseñas y fichas en toda la tabla."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo de evento desconocido: {tipo!r}")
    evento = EventoAcceso(
        fecha_hora=ahora, login_intentado=login, usuario_id=usuario_id, ip_cliente=ip,
        tipo=tipo, detalle=detalle,
    )
    session.add(evento)
    session.flush()
    return evento


def ultimos(session: Session, cuantos: int = 200) -> list[EventoAcceso]:
    return list(
        session.scalars(select(EventoAcceso).order_by(EventoAcceso.id.desc()).limit(cuantos))
    )
```
**`seguridad/cuentas.py`**
```python
"""Cuentas locales, contraseñas, bloqueo y primer administrador (spec S3 §5.2, §5.4, §5.5).

Contraseñas solo como Argon2 (`argon2-cffi`, parámetros por defecto de la biblioteca) con un
semáforo que limita las verificaciones simultáneas: cada una usa unos 64 MiB (SEG-11). Un login
inexistente se verifica igual contra una huella de relleno, con el mismo mensaje y el mismo
contador, para que ni el texto ni el tiempo delaten qué cuentas existen. Cinco fallos seguidos
bloquean el login 15 minutos; un freno global con espera progresiva cubre a quien recarga la
pestaña. Todo evento queda en `evento_acceso`, sin secretos.

Cada función que cambia estado **confirma su propia transacción** (la base de la instalación no
comparte transacción con ningún caso). El reloj `ahora` y la espera `dormir` se inyectan.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from seguridad import eventos, sesiones
from seguridad.modelo import CodigoInstalacion, IntentoAcceso, Usuario
from seguridad.permisos import Accion, PermisoDenegado, Rol, exigir, roles_de, texto_de_roles
from seguridad.secretos import CONTRASENAS_COMUNES

MENSAJE_FALLO = "Usuario o contraseña incorrectos."
MENSAJE_BLOQUEO = (
    "Demasiados intentos fallidos. Espere 15 minutos o pida al administrador que desbloquee "
    "la cuenta."
)
MENSAJE_CODIGO = "El código de instalación no es válido o ya se usó."
FALLOS_PARA_BLOQUEAR = 5
BLOQUEO = timedelta(minutes=15)
FRENO_FALLOS = 20
FRENO_VENTANA = timedelta(minutes=10)
FRENO_ESPERA_MAXIMA_S = 60.0
VERIFICACIONES_SIMULTANEAS = 4
MINIMO_CONTRASENA = 10
MAXIMO_CONTRASENA = 128
LONGITUD_CODIGO = 20
ALFABETO_CODIGO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # base32 (RFC 4648)
CLAVE_INTENTOS_CODIGO = "!codigo-de-instalacion"
NOMBRE_ARCHIVO_CODIGO = "codigo_instalacion.txt"
PATRON_LOGIN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
PURGA_DE_INEXISTENTES = timedelta(hours=24)

_hasher = PasswordHasher()
_semaforo = threading.BoundedSemaphore(VERIFICACIONES_SIMULTANEAS)

Dormir = Callable[[float], None]


class ErrorDeAcceso(ValueError):  # noqa: N818
    """Usuario o contraseña incorrectos (el mismo mensaje exista o no el usuario)."""


class CuentaBloqueada(ErrorDeAcceso):  # noqa: N818
    """Cinco fallos seguidos: el mismo mensaje para un login inexistente."""


class ContrasenaInvalida(ValueError):  # noqa: N818
    """La contraseña no cumple la política (10 a 128, distinta del usuario, no común)."""


class FrenoGlobal:
    """Espera progresiva por fallos de todo el proceso (no de un login): 20 en 10 minutos y
    cada intento nuevo espera 1, 2, 4... s, hasta 60 s. Estado del proceso, no de un usuario
    (excepción declarada a la regla de S3 §4.4)."""

    def __init__(self) -> None:
        self._fallos: deque[datetime] = deque()
        self._candado = threading.Lock()

    def registrar_fallo(self, ahora: datetime) -> None:
        with self._candado:
            self._fallos.append(ahora)
            self._podar(ahora)

    def espera(self, ahora: datetime) -> float:
        with self._candado:
            self._podar(ahora)
            exceso = len(self._fallos) - FRENO_FALLOS
        if exceso < 0:
            return 0.0
        return float(min(FRENO_ESPERA_MAXIMA_S, 2**exceso))

    def reiniciar(self) -> None:
        with self._candado:
            self._fallos.clear()

    def _podar(self, ahora: datetime) -> None:
        while self._fallos and ahora - self._fallos[0] >= FRENO_VENTANA:
            self._fallos.popleft()


FRENO = FrenoGlobal()


# --- contraseñas y logins -------------------------------------------------------------------


def normalizar_login(login: str) -> str:
    return login.strip().casefold()


def validar_login(login: str) -> str:
    """El login normalizado, o `ValueError`: 3 a 40 caracteres a-z, 0-9, punto, guion."""
    normal = normalizar_login(login)
    if not PATRON_LOGIN.fullmatch(normal):
        raise ValueError("El usuario son 3 a 40 caracteres: letras, números, punto o guion.")
    return normal


def validar_contrasena(contrasena: str, login: str = "") -> None:
    """Política de S3 §5.2 (línea de NIST SP 800-63B, cita por verificar en S3-0): 10 a 128
    caracteres Unicode, distinta del usuario, fuera de la lista de comunes; sin reglas de
    composición."""
    if len(contrasena) < MINIMO_CONTRASENA:
        raise ContrasenaInvalida(
            f"La contraseña debe tener al menos {MINIMO_CONTRASENA} caracteres."
        )
    if len(contrasena) > MAXIMO_CONTRASENA:
        raise ContrasenaInvalida(f"La contraseña admite hasta {MAXIMO_CONTRASENA} caracteres.")
    if login and contrasena.strip().casefold() == normalizar_login(login):
        raise ContrasenaInvalida("La contraseña no puede ser igual al usuario.")
    if contrasena.strip().casefold() in CONTRASENAS_COMUNES:
        raise ContrasenaInvalida("Esa contraseña es demasiado común; elija otra.")


def _huella(contrasena: str) -> str:
    with _semaforo:
        return _hasher.hash(contrasena)


@cache
def _huella_de_relleno() -> str:
    return _huella("relleno-para-igualar-el-tiempo-de-un-usuario-inexistente")


def _coincide(huella: str, contrasena: str) -> bool:
    with _semaforo:
        try:
            return _hasher.verify(huella, contrasena)
        except (VerificationError, InvalidHashError):
            return False


# --- ayudantes de estado --------------------------------------------------------------------


def _quien(usuario: Usuario | None) -> str:
    return "" if usuario is None else f"{usuario.nombre} <{usuario.login}>"


def texto_responsable(nombre: str, login: str, restablecida_por_admin: bool = False) -> str:
    """El responsable de un cambio: `Nombre <login>`, congelado en el momento (RF-82). Tras un
    restablecimiento del administrador y antes de que la persona cambie su contraseña se
    marca, para la trazabilidad (S3 §5.2, SEG-6). Cabe en `String(120)`."""
    marca = " (tras restablecimiento)" if restablecida_por_admin else ""
    base = f" <{login}>{marca}"
    return nombre[: 120 - len(base)] + base


def responsable_de(usuario: Usuario) -> str:
    return texto_responsable(usuario.nombre, usuario.login, usuario.restablecida_por_admin)


def _usuario(session: Session, usuario_id: int) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise LookupError(f"no hay una cuenta con id {usuario_id}")
    return usuario


def _exigir_administrador(actor: Usuario) -> None:
    if not actor.activo:
        raise PermisoDenegado("La cuenta que actúa está desactivada.")
    exigir(roles_de(actor.roles), Accion.ADMINISTRAR_CUENTAS)


def _intento(session: Session, clave: str) -> IntentoAcceso:
    fila = session.get(IntentoAcceso, clave)
    if fila is None:
        fila = IntentoAcceso(login_normalizado=clave, fallos_seguidos=0)
        session.add(fila)
        session.flush()
    return fila


def _fallar(session: Session, fila: IntentoAcceso, ahora: datetime, freno: FrenoGlobal) -> bool:
    """Cuenta un fallo; True si este fallo bloquea el login."""
    fila.fallos_seguidos += 1
    fila.ultimo_fallo = ahora
    freno.registrar_fallo(ahora)
    if fila.fallos_seguidos >= FALLOS_PARA_BLOQUEAR:
        fila.bloqueado_hasta = ahora + BLOQUEO
        return True
    return False


def _bloqueado(fila: IntentoAcceso, ahora: datetime) -> bool:
    """Bloqueado mientras `ahora < bloqueado_hasta`; al llegar la hora se libera y se reinicia."""
    if fila.bloqueado_hasta is None:
        return False
    if ahora < fila.bloqueado_hasta:
        return True
    fila.bloqueado_hasta, fila.fallos_seguidos = None, 0
    return False


# --- entrar ---------------------------------------------------------------------------------


def autenticar(
    session: Session,
    login: str,
    contrasena: str,
    ahora: datetime,
    *,
    ip: str = "",
    freno: FrenoGlobal | None = None,
    dormir: Dormir = time.sleep,
) -> Usuario:
    """El usuario si el par es correcto. `ErrorDeAcceso` (mismo mensaje exista o no el login) o
    `CuentaBloqueada`. Cuenta y registra el intento; confirma en todos los casos."""
    freno = FRENO if freno is None else freno
    espera = freno.espera(ahora)
    if espera:
        dormir(espera)
    clave = normalizar_login(login)[:60]
    fila = _intento(session, clave)
    if _bloqueado(fila, ahora):
        eventos.registrar(session, "bloqueo", ahora, login=clave, ip=ip, detalle="login bloqueado")
        session.commit()
        raise CuentaBloqueada(MENSAJE_BLOQUEO)
    usuario = session.scalar(select(Usuario).where(Usuario.login == clave))
    existe = usuario is not None and usuario.activo
    huella = usuario.huella_clave if existe else _huella_de_relleno()
    correcta = _coincide(huella, contrasena)
    if existe and correcta:
        fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
        eventos.registrar(session, "entrada", ahora, login=clave, usuario_id=usuario.id, ip=ip)
        if _hace_falta_recalcular(usuario.huella_clave):
            usuario.huella_clave = _huella(contrasena)
        session.commit()
        return usuario
    bloquea = _fallar(session, fila, ahora, freno)
    eventos.registrar(session, "fallo", ahora, login=clave, ip=ip)
    if bloquea:
        eventos.registrar(session, "bloqueo", ahora, login=clave, ip=ip, detalle="5 fallos")
    session.commit()
    raise CuentaBloqueada(MENSAJE_BLOQUEO) if bloquea else ErrorDeAcceso(MENSAJE_FALLO)


def _hace_falta_recalcular(huella: str) -> bool:
    try:
        return _hasher.check_needs_rehash(huella)
    except InvalidHashError:
        return False


def purgar_intentos_de_inexistentes(session: Session, ahora: datetime) -> int:
    """Borra los contadores de logins que no existen y llevan 24 h sin fallar (S3 §5.4)."""
    existentes = set(session.scalars(select(Usuario.login)))
    viejos = [
        fila for fila in session.scalars(select(IntentoAcceso))
        if fila.login_normalizado not in existentes
        and not fila.login_normalizado.startswith("!")
        and fila.ultimo_fallo is not None
        and ahora - fila.ultimo_fallo >= PURGA_DE_INEXISTENTES
    ]
    for fila in viejos:
        session.delete(fila)
    session.commit()
    return len(viejos)


# --- primer administrador y código de instalación -------------------------------------------


def _huella_codigo(codigo: str) -> str:
    limpio = "".join(c for c in codigo.upper() if c.isalnum())
    return hashlib.sha256(limpio.encode("ascii", "ignore")).hexdigest()


def formato_codigo(codigo: str) -> str:
    return "-".join(codigo[i : i + 4] for i in range(0, len(codigo), 4))


def emitir_codigo(
    session: Session, carpeta: Path, ahora: datetime, *, motivo: str = "primera vez"
) -> str:
    """Un código de instalación de un solo uso: 20 caracteres base32 (100 bits) de `secrets`.
    Guarda su SHA-256 y lo escribe en `carpeta/codigo_instalacion.txt`. Confirma."""
    if motivo not in {"primera vez", "restablecimiento"}:
        raise ValueError("motivo de codigo desconocido")
    codigo = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LONGITUD_CODIGO))
    session.add(CodigoInstalacion(huella=_huella_codigo(codigo), creado=ahora, motivo=motivo))
    eventos.registrar(session, "codigo de instalacion", ahora, detalle=motivo)
    session.commit()
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / NOMBRE_ARCHIVO_CODIGO).write_text(formato_codigo(codigo) + "\n", encoding="ascii")
    return codigo


def hay_usuarios(session: Session) -> bool:
    return bool(session.scalar(select(func.count()).select_from(Usuario)))


def preparar_primera_vez(session: Session, carpeta: Path, ahora: datetime) -> str | None:
    """Si no hay cuentas ni un código vigente, emite el de la primera vez (la pantalla de acceso
    lo llama al arrancar). Devuelve el código o `None` si no hacía falta."""
    vigente = session.scalar(
        select(func.count()).select_from(CodigoInstalacion).where(CodigoInstalacion.usado.is_(None))
    )
    if hay_usuarios(session) or vigente:
        return None
    return emitir_codigo(session, carpeta, ahora)


def reclamar_instalacion(
    session: Session,
    codigo: str,
    login: str,
    nombre: str,
    contrasena: str,
    ahora: datetime,
    carpeta: Path,
    *,
    ip: str = "",
    freno: FrenoGlobal | None = None,
    dormir: Dormir = time.sleep,
) -> Usuario:
    """Crea el primer administrador (o, con un código de restablecimiento, devuelve el acceso a
    un administrador). El código solo se acepta mientras no haya cuentas o haya un
    restablecimiento pendiente, con el mismo freno que el acceso; al usarse se borra el archivo
    y se invalida la huella."""
    freno = FRENO if freno is None else freno
    espera = freno.espera(ahora)
    if espera:
        dormir(espera)
    fila = _intento(session, CLAVE_INTENTOS_CODIGO)
    if _bloqueado(fila, ahora):
        session.commit()
        raise CuentaBloqueada(MENSAJE_BLOQUEO)
    pendiente = session.get(CodigoInstalacion, _huella_codigo(codigo))
    aceptable = (
        pendiente is not None
        and pendiente.usado is None
        and (not hay_usuarios(session) or pendiente.motivo == "restablecimiento")
    )
    if not aceptable:
        bloquea = _fallar(session, fila, ahora, freno)
        eventos.registrar(session, "fallo", ahora, login="(codigo)", ip=ip, detalle="codigo")
        session.commit()
        raise CuentaBloqueada(MENSAJE_BLOQUEO) if bloquea else ErrorDeAcceso(MENSAJE_CODIGO)
    login_normal = validar_login(login)
    validar_contrasena(contrasena, login_normal)
    usuario = session.scalar(select(Usuario).where(Usuario.login == login_normal))
    huella = _huella(contrasena)
    if usuario is None:
        usuario = Usuario(
            login=login_normal, nombre=nombre.strip() or login_normal, huella_clave=huella,
            roles=texto_de_roles([Rol.ADMINISTRADOR]), activo=True, debe_cambiar_clave=False,
            restablecida_por_admin=False, creado=ahora, creado_por="código de instalación",
        )
        session.add(usuario)
        session.flush()
    else:  # restablecimiento: el administrador recupera su cuenta
        usuario.huella_clave, usuario.activo = huella, True
        usuario.roles = texto_de_roles({*roles_de(usuario.roles), Rol.ADMINISTRADOR})
        usuario.debe_cambiar_clave = False
        sesiones.cerrar_todas(session, usuario.id, "restablecimiento")
    pendiente.usado = ahora
    fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
    eventos.registrar(
        session, "alta", ahora, login=login_normal, usuario_id=usuario.id, ip=ip,
        detalle=f"administrador por {pendiente.motivo}",
    )
    session.commit()
    (carpeta / NOMBRE_ARCHIVO_CODIGO).unlink(missing_ok=True)
    return usuario


def emitir_codigo_de_restablecimiento(session: Session, carpeta: Path, ahora: datetime) -> str:
    """`scripts/restablecer_administrador.py` (exige acceso al equipo): un código nuevo y cierra
    las sesiones de los administradores (S3 §5.4)."""
    for usuario in session.scalars(select(Usuario)):
        if Rol.ADMINISTRADOR in roles_de(usuario.roles):
            sesiones.cerrar_todas(session, usuario.id, "restablecimiento")
    return emitir_codigo(session, carpeta, ahora, motivo="restablecimiento")


# --- administrar cuentas --------------------------------------------------------------------


def crear_usuario(
    session: Session,
    actor: Usuario,
    login: str,
    nombre: str,
    roles: Iterable[Rol | str],
    contrasena_temporal: str,
    ahora: datetime,
) -> Usuario:
    """Alta por el administrador, con contraseña temporal que obliga a cambiarla al entrar."""
    _exigir_administrador(actor)
    login_normal = validar_login(login)
    validar_contrasena(contrasena_temporal, login_normal)
    if session.scalar(select(Usuario.id).where(Usuario.login == login_normal)) is not None:
        raise ValueError(f"Ya existe una cuenta con el usuario {login_normal!r}.")
    usuario = Usuario(
        login=login_normal, nombre=nombre.strip() or login_normal,
        huella_clave=_huella(contrasena_temporal), roles=texto_de_roles(roles), activo=True,
        debe_cambiar_clave=True, restablecida_por_admin=False, creado=ahora,
        creado_por=_quien(actor),
    )
    session.add(usuario)
    session.flush()
    eventos.registrar(
        session, "alta", ahora, login=login_normal, usuario_id=usuario.id,
        detalle=f"roles {usuario.roles}; por {actor.login}",
    )
    session.commit()
    return usuario


def cambiar_roles(
    session: Session, actor: Usuario, usuario_id: int, roles: Iterable[Rol | str], ahora: datetime
) -> Usuario:
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    nuevos = texto_de_roles(roles)
    if Rol.ADMINISTRADOR in roles_de(usuario.roles) and Rol.ADMINISTRADOR not in roles_de(nuevos):
        _exigir_otro_administrador(session, usuario)
    usuario.roles = nuevos
    sesiones.cerrar_todas(session, usuario.id, "cambio de roles")
    eventos.registrar(
        session, "cambio de roles", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"{nuevos}; por {actor.login}",
    )
    session.commit()
    return usuario


def _exigir_otro_administrador(session: Session, usuario: Usuario) -> None:
    otros = [
        u for u in session.scalars(select(Usuario).where(Usuario.activo.is_(True)))
        if u.id != usuario.id and Rol.ADMINISTRADOR in roles_de(u.roles)
    ]
    if not otros:
        raise ValueError("Debe quedar al menos un administrador activo.")


def desactivar(session: Session, actor: Usuario, usuario_id: int, ahora: datetime) -> None:
    """Las cuentas no se borran: se desactivan, para que sus registros sigan teniendo dueño."""
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    if Rol.ADMINISTRADOR in roles_de(usuario.roles):
        _exigir_otro_administrador(session, usuario)
    usuario.activo = False
    sesiones.cerrar_todas(session, usuario.id, "cuenta desactivada")
    eventos.registrar(
        session, "baja", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"por {actor.login}",
    )
    session.commit()


def reactivar(session: Session, actor: Usuario, usuario_id: int, ahora: datetime) -> None:
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    usuario.activo = True
    eventos.registrar(
        session, "alta", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"reactivada por {actor.login}",
    )
    session.commit()


def desbloquear(session: Session, actor: Usuario, login: str, ahora: datetime) -> None:
    _exigir_administrador(actor)
    clave = normalizar_login(login)
    fila = session.get(IntentoAcceso, clave)
    if fila is not None:
        fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
    eventos.registrar(session, "desbloqueo", ahora, login=clave, detalle=f"por {actor.login}")
    session.commit()


def restablecer(
    session: Session, actor: Usuario, usuario_id: int, contrasena_temporal: str, ahora: datetime
) -> None:
    """Contraseña temporal nueva: obliga a cambiarla, cierra las sesiones de la cuenta y marca
    sus cambios siguientes en la trazabilidad hasta que la persona la cambie."""
    _exigir_administrador(actor)
    usuario = _usuario(session, usuario_id)
    validar_contrasena(contrasena_temporal, usuario.login)
    usuario.huella_clave = _huella(contrasena_temporal)
    usuario.debe_cambiar_clave, usuario.restablecida_por_admin = True, True
    fila = session.get(IntentoAcceso, usuario.login)
    if fila is not None:
        fila.fallos_seguidos, fila.bloqueado_hasta = 0, None
    sesiones.cerrar_todas(session, usuario.id, "restablecimiento")
    eventos.registrar(
        session, "restablecimiento", ahora, login=usuario.login, usuario_id=usuario.id,
        detalle=f"por {actor.login}",
    )
    session.commit()


def cambiar_contrasena(
    session: Session, usuario_id: int, actual: str, nueva: str, ahora: datetime
) -> str:
    """Cambia la contraseña propia: cierra todas las fichas y devuelve una NUEVA (S3 §5.3)."""
    usuario = _usuario(session, usuario_id)
    if not _coincide(usuario.huella_clave, actual):
        raise ErrorDeAcceso(MENSAJE_FALLO)
    validar_contrasena(nueva, usuario.login)
    usuario.huella_clave = _huella(nueva)
    usuario.debe_cambiar_clave, usuario.restablecida_por_admin = False, False
    sesiones.cerrar_todas(session, usuario.id, "cambio de clave")
    eventos.registrar(
        session, "cambio de clave", ahora, login=usuario.login, usuario_id=usuario.id
    )
    session.commit()
    return sesiones.abrir(session, usuario, ahora)
```
  Las sesiones: ficha aleatoria de 256 bits, solo su SHA-256 en la base, validación en cada
  ejecución con los roles releídos de la base:
**`seguridad/sesiones.py`**
```python
"""Fichas de sesión sin servicios externos (spec S3 §5.3; DA-S3-1, DA-S3-8).

La ficha es un secreto aleatorio de 256 bits que solo vive en `st.session_state` del servidor;
la base guarda su SHA-256 (no hace falta Argon2: no es una contraseña elegida por una persona).
`validar` es lo que `exigir_sesion` corre en CADA ejecución del guion: busca la huella, comprueba
cierre, inactividad (30 min) y antigüedad (12 h), que la cuenta siga activa, y **lee los roles
de la base**: cambiar los roles de una cuenta cambia su menú en la ejecución siguiente.
El reloj (`ahora`) se inyecta; las cotas son exactas: 29:59 sigue, 30:00 expira.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from seguridad import eventos
from seguridad.modelo import Sesion, Usuario
from seguridad.permisos import Rol, roles_de

INACTIVIDAD = timedelta(minutes=30)
ANTIGUEDAD = timedelta(hours=12)
#: Como mucho una escritura por minuto para renovar la actividad (no cargar SQLite).
RENOVACION_MINIMA = timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class SesionActiva:
    huella_ficha: str
    usuario_id: int
    login: str
    nombre: str
    roles: frozenset[Rol]
    debe_cambiar_clave: bool
    restablecida_por_admin: bool

    @property
    def usuario(self) -> str:
        """`Nombre <login>`: el responsable que esta persona deja en todo lo que guarda (RF-82);
        es la forma que S4 lee de `st.session_state["silice_sesion"]`."""
        from seguridad.cuentas import texto_responsable

        return texto_responsable(self.nombre, self.login, self.restablecida_por_admin)


def huella_de(ficha: str) -> str:
    return hashlib.sha256(ficha.encode("utf-8")).hexdigest()


def abrir(session: Session, usuario: Usuario, ahora: datetime) -> str:
    """Una ficha NUEVA para `usuario` (al entrar y al cambiar la contraseña). Confirma."""
    ficha = secrets.token_urlsafe(32)
    session.add(
        Sesion(
            huella_ficha=huella_de(ficha), usuario_id=usuario.id, creada=ahora,
            ultima_actividad=ahora, cerrada=False, motivo_cierre="",
        )
    )
    session.commit()
    return ficha


def cerrar(session: Session, ficha: str, motivo: str, ahora: datetime) -> bool:
    """Cierra una ficha (salida, expiración). True si estaba abierta. Confirma."""
    fila = session.get(Sesion, huella_de(ficha))
    if fila is None or fila.cerrada:
        return False
    fila.cerrada, fila.motivo_cierre = True, motivo
    tipo = "expiracion" if motivo in {"inactividad", "antiguedad"} else "salida"
    eventos.registrar(session, tipo, ahora, usuario_id=fila.usuario_id, detalle=motivo)
    session.commit()
    return True


def cerrar_todas(session: Session, usuario_id: int, motivo: str) -> int:
    """Cierra todas las fichas abiertas de una cuenta (restablecer, desactivar, cambiar roles o
    contraseña). Hace `flush`, no `commit`: lo confirma quien llama junto con su cambio."""
    resultado = session.execute(
        update(Sesion)
        .where(Sesion.usuario_id == usuario_id, Sesion.cerrada.is_(False))
        .values(cerrada=True, motivo_cierre=motivo)
    )
    session.flush()
    return resultado.rowcount or 0


def validar(session: Session, ficha: str | None, ahora: datetime) -> SesionActiva | None:
    """La sesión vigente de `ficha`, o `None` si no existe, se cerró o expiró (y la cierra)."""
    if not ficha:
        return None
    fila = session.get(Sesion, huella_de(ficha))
    if fila is None or fila.cerrada:
        return None
    if ahora - fila.creada >= ANTIGUEDAD:
        cerrar(session, ficha, "antiguedad", ahora)
        return None
    if ahora - fila.ultima_actividad >= INACTIVIDAD:
        cerrar(session, ficha, "inactividad", ahora)
        return None
    usuario = session.scalar(select(Usuario).where(Usuario.id == fila.usuario_id))
    if usuario is None or not usuario.activo:
        cerrar(session, ficha, "cuenta desactivada", ahora)
        return None
    if ahora - fila.ultima_actividad >= RENOVACION_MINIMA:
        fila.ultima_actividad = ahora
        session.commit()
    return SesionActiva(
        huella_ficha=fila.huella_ficha,
        usuario_id=usuario.id,
        login=usuario.login,
        nombre=usuario.nombre,
        roles=roles_de(usuario.roles),
        debe_cambiar_clave=usuario.debe_cambiar_clave,
        restablecida_por_admin=usuario.restablecida_por_admin,
    )
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_permisos.py tests/unit/test_cuentas.py
tests/unit/test_sesiones.py -v -W error` → verde. Run: `uv run ruff check seguridad
tests/fixtures/instalacion.py` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add seguridad/permisos.py seguridad/eventos.py seguridad/cuentas.py seguridad/sesiones.py \
  seguridad/red.py
git commit -m "feat(seguridad): roles, cuentas con bloqueo y freno global, sesiones y red local" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 6: Acceso en la interfaz (`ui/sesion`, `ui/acceso`, el marco por rol)

**Rama:** `inc/080-s3-1-seguridad`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/sesion.py`, `ui/acceso.py`, `tests/fixtures/paginas_s3.py`
- Modificar: `ui/app.py` (marco, `DefinicionPagina.accion`, `paginas_visibles(modo_entrega, roles)`,
  `main()`), `ui/recorridos.py:15,58` (`Recorrido.visible_en`), `ui/barra.py:35,112`,
  `ui/caso.py:51,93-98` (`puede_cambiar_de_caso`), `ui/paginas/inicio.py:23,128`
- Modificar (cada `render()` exige su acción en la primera línea): `ui/paginas/catalogo.py`,
  `componer.py`, `elaborar.py`, `escenarios.py`, `historico.py`, `similares.py`, `simulador.py`,
  `visor.py`, `actualizacion.py`, `hoja.py`; `tests/conftest.py` (fixture del interruptor);
  `tests/unit/test_ui_importable.py`
- Prueba: `tests/unit/test_ui_acceso.py`, `tests/unit/test_ui_marco.py`

**Interfaces:**
- Consume: `seguridad.sesiones.{SesionActiva, abrir, validar, cerrar}`, `seguridad.cuentas.*`,
  `seguridad.permisos.{Accion, Rol, Sensible, permitido}`, `seguridad.red.*`,
  `operacion.instalacion.{sesion_de_instalacion, cerrar_motores}`, `ui.texto_seguro.texto_seguro`
  (S1) y `operacion.config.carpeta_datos`.
- Produce:
  - `ui.sesion`: `def acceso_activo(entorno: Mapping[str, str] | None=None) -> bool`
  - `ui.sesion`: `def ahora() -> datetime`
  - `ui.sesion`: `def limpiar_motores() -> None`
  - `ui.sesion`: `def instalacion() -> Iterator[Session]`
  - `ui.sesion`: `def ip_del_cliente() -> str | None`
  - `ui.sesion`: `def sesion_actual() -> SesionActiva | None`
  - `ui.sesion`: `def responsable_actual() -> str`
  - `ui.sesion`: `def responsable_de_la_hoja(escrito: str='') -> str`
  - `ui.sesion`: `def caja_de_responsable(rotulo: str='Responsable', *, key: str | None=None,
      contenedor=st)`
  - `ui.sesion`: `def puede(accion: Accion) -> bool`
  - `ui.sesion`: `def exigir(accion: Accion) -> SesionActiva`
  - `ui.sesion`: `def exigir_local(sensible: Sensible) -> SesionActiva`
  - `ui.acceso`: `def descartar_borrador() -> None`
  - `ui.acceso`: `def exigir_sesion() -> SesionActiva`
  - `ui.acceso`: `def pintar_sesion(sesion: SesionActiva) -> None`
  - `ui.app.DefinicionPagina.accion: Accion | None`;
    `paginas_visibles(modo_entrega, roles=None)` y `secciones_visibles(modo_entrega, roles=None)`;
    `marco(definicion, pintar, ir_a, sesion=None)`.
  - `ui.recorridos.Recorrido.visible_en(rutas) -> Recorrido | None`.
  - `tests.fixtures.paginas_s3`: `preparar(monkeypatch, carpeta, *roles, ip, login) -> str` (la
    ficha) y `con_ficha(at, ficha)`.

**El interruptor (RP8-4).** `SILICE_ACCESO=1` enciende el acceso; sin la variable, `sesion_actual`
devuelve al usuario de desarrollo con todos los roles y nada pide entrar. Así S3-1 se fusiona sin
cambiar la interfaz de nadie hasta la tarea 24. La suite fija `SILICE_ACCESO=0` y las pruebas de S3
lo encienden con `preparar`.
**Cada pantalla vuelve a exigir su acción.** La navegación no es el control: una URL directa a una
pantalla sin permiso muestra el mensaje fijo y detiene el guion. `test_ui_marco` lo comprueba por
AST en la primera instrucción de cada `render()` y exige que toda pantalla menos el Inicio declare
su `accion`; las pantallas que S1 y S2 hayan agregado a `PAGINAS` la reciben aquí o la prueba falla:
`ADMINISTRAR_PRECIOS` para índices y precios de la empresa, `CONVERTIR_Y_REAJUSTAR` para el reajuste
y `CONTROL_DE_OBRA` (o `DECIDIR_RECUPERACION`) para el control de obra.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/fixtures/paginas_s3.py`**
```python
"""Entrar a las páginas de S3 con `AppTest`: instalación temporal, reloj e IP inyectados."""

from __future__ import annotations

from pathlib import Path

from seguridad import sesiones
from seguridad.modelo import Usuario
from tests.fixtures.instalacion import AHORA, administrador, persona
from ui import sesion as ui_sesion
from ui.sesion import CLAVE_FICHA


def preparar(
    monkeypatch, carpeta: Path, *roles: str, ip: str = "127.0.0.1", login: str = "luis"
) -> str:
    """Enciende el acceso sobre una `instalacion.db` nueva en `carpeta`, crea al administrador y,
    si `roles` no es `("administrador",)`, una cuenta `login` con esos roles; abre la sesión de la
    cuenta que corresponde y devuelve su ficha."""
    monkeypatch.setenv("SILICE_ACCESO", "1")
    monkeypatch.setenv("SILICE_DATOS", str(carpeta))
    monkeypatch.setenv("SILICE_INSTALACION", str(carpeta / "instalacion.db"))
    monkeypatch.setattr(ui_sesion, "ahora", lambda: AHORA)
    monkeypatch.setattr(ui_sesion, "ip_del_cliente", lambda: ip)
    ui_sesion.limpiar_motores()
    with ui_sesion.instalacion() as bd:
        admin = administrador(bd, carpeta)
        if tuple(roles) == ("administrador",):
            usuario = admin
        else:
            usuario = persona(bd, admin, login, roles)
            usuario.debe_cambiar_clave = False
            bd.commit()
        return sesiones.abrir(bd, bd.get(Usuario, usuario.id), AHORA)


def con_ficha(at, ficha: str):
    at.session_state[CLAVE_FICHA] = ficha
    return at
```
**`tests/unit/test_ui_acceso.py`**
```python
"""Pantalla de acceso, primer administrador, sesión expirada y 'solo desde el propio equipo'
(RF-80, RF-81, UC-21; spec S3 §5.3 a §5.7). `AppTest` con el reloj y la IP inyectados."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad import cuentas
from seguridad.modelo import Usuario
from tests.fixtures.instalacion import AHORA, CONTRASENA
from ui import sesion as ui_sesion
from ui.acceso import AVISO_EXPIRADA, AVISO_OTRO_USUARIO, AVISO_SIN_CIFRAR


def _app() -> None:
    import streamlit as st

    from ui import acceso

    sesion = acceso.exigir_sesion()
    acceso.pintar_sesion(sesion)
    st.write(f"hola {sesion.login}")
    st.session_state.setdefault("borrador", "mi borrador")


@pytest.fixture
def entorno(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SILICE_ACCESO", "1")
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path))
    monkeypatch.setenv("SILICE_INSTALACION", str(tmp_path / "instalacion.db"))
    reloj = {"ahora": AHORA}
    monkeypatch.setattr(ui_sesion, "ahora", lambda: reloj["ahora"])
    monkeypatch.setattr(ui_sesion, "ip_del_cliente", lambda: "127.0.0.1")
    ui_sesion.limpiar_motores()
    yield tmp_path, reloj
    ui_sesion.limpiar_motores()


def _arrancar() -> AppTest:
    return AppTest.from_function(_app, default_timeout=60).run()


def _texto(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def _crear_administrador(at: AppTest, carpeta: Path) -> AppTest:
    codigo = (carpeta / "codigo_instalacion.txt").read_text().strip()
    at.text_input(key="acceso_codigo").input(codigo)
    at.text_input(key="acceso_nuevo_login").input("admin")
    at.text_input(key="acceso_nuevo_nombre").input("Ana Admin")
    at.text_input(key="acceso_nueva_clave").input(CONTRASENA)
    at.text_input(key="acceso_repetida").input(CONTRASENA)
    at.button[0].click()
    return at.run()


def _entrar(at: AppTest, login: str, clave: str = CONTRASENA) -> AppTest:
    at.text_input(key="acceso_login").input(login)
    at.text_input(key="acceso_contrasena").input(clave)
    at.button[0].click()
    return at.run()


def _alta(carpeta: Path, login: str, roles: tuple[str, ...]) -> None:
    with ui_sesion.instalacion() as bd:
        admin = bd.query(Usuario).filter_by(login="admin").one()
        cuentas.crear_usuario(bd, admin, login, login.title(), roles, CONTRASENA, AHORA)
        usuario = bd.query(Usuario).filter_by(login=login).one()
        usuario.debe_cambiar_clave = False
        bd.commit()


def test_con_el_acceso_apagado_nada_pide_entrar(monkeypatch) -> None:
    monkeypatch.setenv("SILICE_ACCESO", "0")
    at = _arrancar()
    assert "hola desarrollo" in _texto(at) and not at.text_input


def test_la_primera_vez_pide_el_codigo_y_deja_al_administrador_dentro(entorno) -> None:
    carpeta, _ = entorno
    at = _arrancar()
    assert at.title[0].value == "Sílice: acceso" and "Primera vez" in at.subheader[0].value
    at = _crear_administrador(at, carpeta)
    assert "hola admin" in _texto(at) and not at.error
    assert not (carpeta / "codigo_instalacion.txt").exists()  # el código se usó y se borró


def test_el_primer_administrador_con_codigo_malo_o_claves_distintas_no_entra(entorno) -> None:
    at = _arrancar()
    at.text_input(key="acceso_codigo").input("A" * 20)
    at.text_input(key="acceso_nuevo_login").input("admin")
    at.text_input(key="acceso_nueva_clave").input(CONTRASENA)
    at.text_input(key="acceso_repetida").input(CONTRASENA + "x")
    at.button[0].click()
    at = at.run()
    assert at.error[0].value == "Las dos contraseñas no coinciden."
    at.text_input(key="acceso_repetida").input(CONTRASENA)
    at.button[0].click()
    at = at.run()
    assert "no es válido" in at.error[0].value and "hola" not in _texto(at)


def test_entrar_con_usuario_y_contrasena(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    assert "hola admin" in _texto(at)
    assert any("Sesión: Ana Admin (administrador)" in c.value for c in at.sidebar.caption)


def test_contrasena_erronea_da_el_mismo_mensaje_exista_o_no_el_usuario(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    at.button(key="silice_cerrar_sesion").click()
    at = at.run()
    mensajes = []
    for login in ("admin", "fantasma"):
        at = _entrar(at, login, "mala contrasena larga")
        mensajes.append(at.error[0].value)
    assert mensajes == [cuentas.MENSAJE_FALLO, cuentas.MENSAJE_FALLO]


def test_cerrar_sesion_vuelve_al_acceso(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    at.button(key="silice_cerrar_sesion").click()
    at = at.run()
    assert at.title[0].value == "Sílice: acceso" and "hola" not in _texto(at)


def test_sesion_expirada_vuelve_al_acceso_conservando_el_borrador_del_mismo_usuario(entorno):
    carpeta, reloj = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    at.session_state["borrador"] = "cambios sin guardar"
    reloj["ahora"] = AHORA + timedelta(minutes=30)  # 30:00 exacto: expira
    at = at.run()
    assert at.title[0].value == "Sílice: acceso" and any(AVISO_EXPIRADA in i.value for i in at.info)
    assert at.session_state["borrador"] == "cambios sin guardar"
    at = _entrar(at, "admin")
    assert "hola admin" in _texto(at) and at.session_state["borrador"] == "cambios sin guardar"


def test_otro_usuario_en_la_pestana_descarta_el_borrador_con_aviso(entorno) -> None:
    carpeta, reloj = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    _alta(carpeta, "luis", ("arma",))
    at.session_state["borrador"] = "cambios del admin"
    reloj["ahora"] = AHORA + timedelta(minutes=31)
    at = at.run()
    at = _entrar(at, "luis")
    assert "hola luis" in _texto(at)
    assert at.session_state["borrador"] == "mi borrador"  # el del admin no sobrevivió
    assert any(AVISO_OTRO_USUARIO in i.value for i in at.info) or "hola luis" in _texto(at)


def test_una_contrasena_temporal_obliga_a_cambiarla_antes_de_seguir(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    with ui_sesion.instalacion() as bd:
        admin = bd.query(Usuario).filter_by(login="admin").one()
        cuentas.crear_usuario(bd, admin, "luis", "Luis", ["arma"], CONTRASENA, AHORA)
    at.button(key="silice_cerrar_sesion").click()
    at = _entrar(at.run(), "luis")
    assert at.title[0].value == "Cambie su contraseña" and "hola" not in _texto(at)
    at.text_input(key="cambio_actual").input(CONTRASENA)
    at.text_input(key="cambio_nueva").input("otra contrasena larga y nueva")
    at.text_input(key="cambio_repetida").input("otra contrasena larga y nueva")
    at.button[0].click()
    at = at.run()
    assert "hola luis" in _texto(at)


@pytest.mark.parametrize("ip,aviso", [("127.0.0.1", False), ("::1", False), ("192.168.1.20", True)])
def test_el_aviso_de_conexion_sin_cifrar_solo_para_clientes_remotos(
    entorno, monkeypatch, ip, aviso
):
    monkeypatch.setattr(ui_sesion, "ip_del_cliente", lambda: ip)
    at = _arrancar()
    assert any(AVISO_SIN_CIFRAR in w.value for w in at.warning) is aviso


def test_el_nombre_de_una_cuenta_con_markdown_no_se_interpreta(entorno) -> None:
    carpeta, _ = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    with ui_sesion.instalacion() as bd:
        bd.query(Usuario).filter_by(login="admin").one().nombre = "![x](http://127.0.0.1:9/p.png)"
        bd.commit()
    at = at.run()
    pie = [c.value for c in at.sidebar.caption if c.value.startswith("Sesión:")][0]
    assert "![" not in pie and "\\!\\[x\\]" in pie


def test_sin_cambio_de_hora_la_ficha_sigue_valiendo_entre_ejecuciones(entorno) -> None:
    carpeta, reloj = entorno
    at = _crear_administrador(_arrancar(), carpeta)
    reloj["ahora"] = AHORA + timedelta(minutes=29, seconds=59)
    assert "hola admin" in _texto(at.run())


def test_la_fecha_inyectada_es_la_del_reloj_de_la_prueba(entorno) -> None:
    _, reloj = entorno
    assert ui_sesion.ahora() == reloj["ahora"] == datetime(2026, 11, 10, 9, 0, 0)
```
**`tests/unit/test_ui_marco.py`**
```python
"""El marco por rol (RF-80, RF-37; S3 §5.1): lo que no depende de qué pantallas de S3 existen.

La navegación no es el control: se prueba la lista de pantallas de cada rol y, por separado, que
cada pantalla con acción la exige en la primera línea de su `render()` (AST). Las listas exactas
por rol, con Entregar, Revisar y Administración, están en `test_ui_roles.py`."""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad.permisos import Rol
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import sesion as ui_sesion
from ui.app import PAGINAS, paginas_visibles
from ui.recorridos import RECORRIDOS, Paso, Recorrido

RUTA_APP = Path(__file__).resolve().parents[2] / "ui" / "app.py"


def _rutas(roles) -> list[str]:
    return [p.ruta_url for p in paginas_visibles(False, frozenset(roles))]


def test_el_rol_arma_ve_lo_de_trabajo_y_no_ve_la_administracion() -> None:
    rutas = set(_rutas({Rol.ARMA}))
    assert {"inicio", "catalogo", "componer", "elaborar", "hoja", "actualizacion", "historico",
            "escenarios", "similares", "simulador", "visor"} <= rutas
    assert "administracion" not in rutas


def test_el_rol_revisa_ve_la_lectura_y_nada_que_escriba() -> None:
    rutas = set(_rutas({Rol.REVISA}))
    assert {"inicio", "catalogo", "historico"} <= rutas
    assert not {"componer", "elaborar", "hoja", "actualizacion", "escenarios", "similares",
                "simulador", "visor"} & rutas


def test_el_administrador_no_ve_ninguna_pantalla_de_trabajo() -> None:
    rutas = set(_rutas({Rol.ADMINISTRADOR}))
    assert "inicio" in rutas
    assert not {"catalogo", "componer", "elaborar", "hoja", "actualizacion", "historico",
                "escenarios", "similares", "simulador", "visor"} & rutas


def test_varios_roles_suman_sus_pantallas_sin_repetir() -> None:
    todas = _rutas(set(Rol))
    assert todas == [p.ruta_url for p in PAGINAS] and len(set(todas)) == len(todas)


def test_sin_roles_solo_queda_lo_que_no_pide_accion() -> None:
    assert _rutas(set()) == ["inicio"]


def test_toda_pantalla_menos_el_inicio_declara_la_accion_que_la_protege() -> None:
    """Una pantalla nueva (también las de S1 y S2) sin `accion` la vería cualquier cuenta."""
    assert [p.ruta_url for p in PAGINAS if p.accion is None] == ["inicio"]


def test_un_recorrido_omite_los_pasos_de_pantallas_que_el_rol_no_ve() -> None:
    recorrido = next(r for r in RECORRIDOS if len(r.pasos) >= 3)
    visibles = {recorrido.pasos[0].pagina, recorrido.pasos[2].pagina}
    filtrado = recorrido.visible_en(visibles)
    assert [p.pagina for p in filtrado.pasos] == [recorrido.pasos[0].pagina,
                                                  recorrido.pasos[2].pagina]
    assert recorrido.visible_en(set()) is None
    assert all(isinstance(p, Paso) for p in filtrado.pasos) and isinstance(filtrado, Recorrido)


def _primera_instruccion(pagina) -> str:
    """El código de la primera instrucción de `render()` tras el docstring."""
    modulo = ast.parse(textwrap.dedent(inspect.getsource(inspect.getmodule(pagina.render))))
    render = next(n for n in modulo.body if isinstance(n, ast.FunctionDef) and n.name == "render")
    cuerpo = render.body
    if isinstance(cuerpo[0], ast.Expr) and isinstance(cuerpo[0].value, ast.Constant):
        cuerpo = cuerpo[1:]
    return ast.unparse(cuerpo[0])


@pytest.mark.parametrize("pagina", [p for p in PAGINAS if p.accion is not None],
                         ids=lambda p: p.ruta_url)
def test_cada_render_exige_su_accion_en_la_primera_linea(pagina) -> None:
    esperada = f"ui_sesion.exigir(Accion.{pagina.accion.name})"
    assert _primera_instruccion(pagina) in {esperada, f"sesion = {esperada}"}


# --- la aplicación completa -----------------------------------------------------------------


def _aplicacion(monkeypatch, tmp_path: Path, *roles: str, entrar: bool = True) -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, *roles)
    monkeypatch.setenv("SILICE_CASO", str(tmp_path / "caso.db"))
    at = AppTest.from_file(str(RUTA_APP), default_timeout=120)
    return (con_ficha(at, ficha) if entrar else at).run()


def _navegacion(monkeypatch):
    import streamlit as st

    llamadas: list = []
    original = st.navigation

    def espia(paginas, **kwargs):
        llamadas.append(list(paginas))
        return original(paginas, **kwargs)

    monkeypatch.setattr(st, "navigation", espia)
    return llamadas


def test_sin_sesion_la_aplicacion_pide_entrar_y_no_arma_el_menu(monkeypatch, tmp_path) -> None:
    llamadas = _navegacion(monkeypatch)
    at = _aplicacion(monkeypatch, tmp_path, "arma", entrar=False)
    assert at.title[0].value == "Sílice: acceso" and llamadas == []


def test_con_sesion_la_aplicacion_arma_el_menu_con_lo_que_el_rol_ve(monkeypatch, tmp_path) -> None:
    llamadas = _navegacion(monkeypatch)
    at = _aplicacion(monkeypatch, tmp_path, "revisa")
    assert not at.exception and llamadas and "Trabajo" in llamadas[0]
    assert "Investigacion" not in llamadas[0]
    assert any("Sesión: Luis (revisa)" in c.value for c in at.sidebar.caption)


def test_el_rol_revisa_no_ve_la_barra_de_herramientas(monkeypatch, tmp_path) -> None:
    at = _aplicacion(monkeypatch, tmp_path, "revisa")
    assert "Guardar version" not in [b.label for b in at.button]


def test_el_rol_arma_si_ve_la_barra_de_herramientas(monkeypatch, tmp_path) -> None:
    at = _aplicacion(monkeypatch, tmp_path, "arma")
    assert "Guardar version" in [b.label for b in at.button]


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()
```
  `tests/unit/test_ui_importable.py` incluye los dos módulos nuevos en `MODULOS_SIN_PAGINA`:
```python
    "ui.sesion",  # S3: el acceso y la sesion
    "ui.acceso",
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_ui_acceso.py tests/unit/test_ui_marco.py
tests/unit/test_ui_importable.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'ui.sesion'`
(`test_ui_acceso`, `test_ui_marco`) y FAIL de `test_ui_importable` por `ui.sesion`.
```bash
git add tests/fixtures/paginas_s3.py tests/unit/test_ui_acceso.py tests/unit/test_ui_marco.py \
  tests/unit/test_ui_importable.py
git commit -m "test(ui): acceso, sesion y marco por rol en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  La sesión de la pestaña (la ficha vive en `st.session_state`; nada por usuario en variables de
  módulo) y la pantalla de acceso con el primer administrador:
**`ui/sesion.py`**
```python
"""Quién entró y qué puede hacer, en la interfaz (spec S3 §5.1, §5.3 y §5.6; RF-80, RF-81).

Cada pestaña del navegador es una sesión de Streamlit con su `st.session_state`; las sesiones
comparten el proceso, así que **nada por usuario** vive en variables de módulo ni en cachés. La
ficha de sesión (un secreto de 256 bits) vive solo en `st.session_state[CLAVE_FICHA]`; la base de
la instalación guarda su SHA-256. En cada ejecución del guion se vuelve a validar y a leer los
roles de la base.

**Interruptor de transición (RP8-4).** `SILICE_ACCESO=1` activa el acceso; sin ella, `sesion_actual`
devuelve un usuario de desarrollo con todos los roles y nada pide entrar. Así S3-1 puede fusionarse
antes de la 0.7.0 sin cambiar la interfaz de nadie; la compuerta GS3 cambia `VALOR_POR_DEFECTO` a
`"1"`. La suite fija `SILICE_ACCESO=0` y las pruebas de S3 lo encienden.

Excepciones declaradas a «nada por usuario en el proceso» (S3 §4.4): el motor de la base de la
instalación (un pool de conexiones por ruta), el semáforo de Argon2 y el freno global.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime

import streamlit as st
from sqlalchemy.orm import Session

from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from seguridad import sesiones
from seguridad.permisos import ROL_DE_LO_SENSIBLE, Accion, Rol, Sensible, permitido
from seguridad.red import es_local, red_local_activa
from seguridad.sesiones import SesionActiva
from ui.texto_seguro import texto_seguro

__all__ = [
    "CLAVE_FICHA",
    "MENSAJE_SIN_PERMISO",
    "MENSAJE_SOLO_LOCAL",
    "VALOR_POR_DEFECTO",
    "acceso_activo",
    "caja_de_responsable",
    "ahora",
    "exigir",
    "exigir_local",
    "instalacion",
    "limpiar_motores",
    "ip_del_cliente",
    "puede",
    "responsable_actual",
    "responsable_de_la_hoja",
    "sesion_actual",
]

VARIABLE_ACCESO = "SILICE_ACCESO"
VALOR_POR_DEFECTO = "0"  # la compuerta GS3 lo pasa a "1" (RP8-4)
CLAVE_FICHA = "silice_sesion"  # no es de widget
CLAVE_BORRADOR_DE = "silice_borrador_de"
CLAVE_AVISO = "silice_aviso_acceso"
CLAVES_DE_SISTEMA = (CLAVE_FICHA, CLAVE_BORRADOR_DE, CLAVE_AVISO)
MENSAJE_SIN_PERMISO = "Su cuenta no tiene permiso para esta pantalla o acción."
MENSAJE_SOLO_LOCAL = "Esta operación solo se hace en el equipo donde está instalado Sílice."
MENSAJE_SIN_ENTRAR = "Entre con su usuario y contraseña."

#: Con el acceso apagado, quien trabaja es esta persona de desarrollo, con todos los roles.
DESARROLLO = SesionActiva(
    huella_ficha="", usuario_id=0, login="desarrollo", nombre="Desarrollo",
    roles=frozenset(Rol), debe_cambiar_clave=False, restablecida_por_admin=False,
)


def acceso_activo(entorno: Mapping[str, str] | None = None) -> bool:
    entorno = os.environ if entorno is None else entorno
    return entorno.get(VARIABLE_ACCESO, VALOR_POR_DEFECTO) == "1"


def ahora() -> datetime:
    """El reloj de la interfaz; las pruebas lo sustituyen."""
    return datetime.now()


def limpiar_motores() -> None:
    """Solo para las pruebas: cierra los pools de las bases de instalación abiertas."""
    cerrar_motores()


@contextmanager
def instalacion() -> Iterator[Session]:
    """Una sesión de SQLAlchemy sobre `instalacion.db` (la crea y la migra si hace falta)."""
    with sesion_de_instalacion() as sesion:
        yield sesion


def ip_del_cliente() -> str | None:
    """`st.context.ip_address` como texto, o `None` si no se sabe. Bajo `AppTest` Streamlit
    entrega un simulacro que NO es un `str`: se descarta (se sustituye en las pruebas)."""
    ip = getattr(st.context, "ip_address", None)
    return ip if isinstance(ip, str) else None


def sesion_actual() -> SesionActiva | None:
    """La sesión vigente de esta pestaña, o `None`. Valida la ficha y lee los roles de la base."""
    if not acceso_activo():
        return DESARROLLO
    ficha = st.session_state.get(CLAVE_FICHA)
    if not ficha:
        return None
    with instalacion() as bd:
        return sesiones.validar(bd, ficha, ahora())


def responsable_actual() -> str:
    """`Nombre <login>`: lo que la hoja y las pantallas de S1 y S2 escriben como responsable."""
    sesion = sesion_actual()
    if sesion is None:
        raise PermissionError(MENSAJE_SIN_ENTRAR)
    return sesion.usuario


def responsable_de_la_hoja(escrito: str = "") -> str:
    """Quién responde por un cambio de la hoja o de las pantallas de S1 y S2 (RF-82). Con el
    acceso encendido es SIEMPRE el usuario de la sesión, diga lo que diga `escrito` (el cuadro
    «Responsable» ya no existe); con el acceso apagado (transición, RP8-4), lo escrito."""
    return responsable_actual() if acceso_activo() else escrito


def caja_de_responsable(rotulo: str = "Responsable", *, key: str | None = None, contenedor=st):
    """El cuadro «Responsable» de la pantalla. Con el acceso encendido no hay cuadro: muestra
    «Responsable: Ana Pérez» y devuelve al usuario de la sesión; con el acceso apagado, el
    cuadro de siempre. `contenedor` es `st` o una columna."""
    if acceso_activo():
        quien = responsable_actual()
        contenedor.caption(f"{rotulo.strip()}: {texto_seguro(quien)}")
        return quien
    return contenedor.text_input(rotulo, key=key)


def puede(accion: Accion) -> bool:
    sesion = sesion_actual()
    return sesion is not None and permitido(sesion.roles, accion)


def exigir(accion: Accion) -> SesionActiva:
    """Primera línea de `render()` de cada página y de cada función de `ui/` que ejecuta una
    acción: sin sesión o sin el rol, avisa en lenguaje llano y detiene el guion (RF-80)."""
    sesion = sesion_actual()
    if sesion is None:
        st.error(MENSAJE_SIN_ENTRAR)
        st.stop()
    if not permitido(sesion.roles, accion):
        st.error(MENSAJE_SIN_PERMISO)
        st.stop()
    return sesion


def exigir_local(sensible: Sensible) -> SesionActiva:
    """Como `exigir`, y además el cliente debe ser el propio equipo (firmar, clave de firma,
    claves de API...). Rechaza con el mensaje de 21j."""
    sesion = exigir(ROL_DE_LO_SENSIBLE[sensible])
    if not es_local(ip_del_cliente(), red_local_encendida=red_local_activa()):
        st.error(MENSAJE_SOLO_LOCAL)
        st.stop()
    return sesion
```
**`ui/acceso.py`**
```python
"""Pantalla de acceso, primer administrador y barra de sesión (spec S3 §5.3, §5.5 y §5.7).

**Solo la importa `ui/app.py`** (como `ui/barra.py`). `exigir_sesion()` es lo primero que corre
`main()`: devuelve la sesión vigente o pinta el acceso y detiene el guion con `st.stop()`. Todo
mensaje de error es fijo (el mismo exista o no el usuario) y todo nombre que viene de la base
pasa por `texto_seguro` (RV-14). Una sesión que expira conserva el borrador de la pestaña
**marcado con su dueño**: el mismo usuario lo recupera al volver a entrar; otro lo descarta con
aviso (21d).
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from operacion.config import carpeta_datos
from seguridad import cuentas, sesiones
from seguridad.modelo import Sesion, Usuario
from seguridad.permisos import aviso_de_roles
from seguridad.red import es_local, red_local_activa
from seguridad.sesiones import SesionActiva
from ui import sesion as ui_sesion
from ui.sesion import (
    CLAVE_AVISO,
    CLAVE_BORRADOR_DE,
    CLAVE_FICHA,
    CLAVES_DE_SISTEMA,
    DESARROLLO,
    acceso_activo,
)
from ui.texto_seguro import texto_seguro

__all__ = [
    "AVISO_EXPIRADA",
    "AVISO_OTRO_USUARIO",
    "AVISO_SIN_CIFRAR",
    "exigir_sesion",
    "pintar_sesion",
]

AVISO_SIN_CIFRAR = (
    "Conexión sin cifrar: su contraseña viaja legible por la red. Úsela solo en una red de "
    "confianza."
)
AVISO_EXPIRADA = "Su sesión se cerró por inactividad. Entre de nuevo: su borrador sigue aquí."
AVISO_OTRO_USUARIO = "Entró otra persona: el borrador de la sesión anterior se descartó."
TITULO_ACCESO = "Sílice: acceso"


def _ahora():
    return ui_sesion.ahora()  # por el módulo, para que las pruebas puedan sustituir el reloj


def _ip() -> str | None:
    return ui_sesion.ip_del_cliente()


def descartar_borrador() -> None:
    """Quita de la pestaña todo salvo lo que es del acceso (el borrador de otra persona)."""
    for clave in list(st.session_state):
        if clave not in CLAVES_DE_SISTEMA:
            del st.session_state[clave]


def _recordar_dueno(bd: Session, ficha: str) -> None:
    """La ficha ya no vale: el borrador de la pestaña queda a nombre de su dueño."""
    if st.session_state.get(CLAVE_BORRADOR_DE):
        return
    fila = bd.get(Sesion, sesiones.huella_de(ficha))
    usuario = bd.get(Usuario, fila.usuario_id) if fila is not None else None
    if usuario is not None:
        st.session_state[CLAVE_BORRADOR_DE] = usuario.login


def _iniciar(bd: Session, usuario: Usuario) -> None:
    dueno = st.session_state.get(CLAVE_BORRADOR_DE)
    if dueno and dueno != usuario.login:
        descartar_borrador()
        st.session_state[CLAVE_AVISO] = AVISO_OTRO_USUARIO
    else:
        st.session_state.pop(CLAVE_AVISO, None)
    st.session_state.pop(CLAVE_BORRADOR_DE, None)
    st.session_state[CLAVE_FICHA] = sesiones.abrir(bd, usuario, _ahora())
    st.rerun()


def _aviso_de_red() -> None:
    if not es_local(_ip(), red_local_encendida=red_local_activa()):
        st.warning(AVISO_SIN_CIFRAR)


def _formulario_de_entrada(bd: Session) -> None:
    with st.form("silice_acceso"):
        login = st.text_input("Usuario", key="acceso_login")
        contrasena = st.text_input("Contraseña", type="password", key="acceso_contrasena")
        enviar = st.form_submit_button("Entrar", type="primary")
    if not enviar:
        return
    try:
        usuario = cuentas.autenticar(bd, login, contrasena, _ahora(), ip=_ip() or "")
    except cuentas.ErrorDeAcceso as error:  # incluye CuentaBloqueada: mensajes fijos
        st.error(str(error))  # mensaje fijo de seguridad.cuentas: no lleva texto ajeno
        return
    _iniciar(bd, usuario)


def _formulario_primer_administrador(bd: Session) -> None:
    carpeta = carpeta_datos()
    cuentas.preparar_primera_vez(bd, carpeta, _ahora())
    st.subheader("Primera vez en este equipo")
    st.write(
        "No hay ninguna cuenta. Abra el archivo `codigo_instalacion.txt` de la carpeta de datos "
        "de Sílice, copie el código de 20 caracteres y cree la cuenta del administrador."
    )
    with st.form("silice_primer_administrador"):
        codigo = st.text_input("Código de instalación", key="acceso_codigo")
        login = st.text_input("Usuario", key="acceso_nuevo_login")
        nombre = st.text_input("Su nombre", key="acceso_nuevo_nombre")
        clave = st.text_input("Contraseña (10 a 128 caracteres)", type="password",
                              key="acceso_nueva_clave")
        repetida = st.text_input("Repita la contraseña", type="password", key="acceso_repetida")
        enviar = st.form_submit_button("Crear el administrador", type="primary")
    if not enviar:
        return
    if clave != repetida:
        st.error("Las dos contraseñas no coinciden.")
        return
    try:
        usuario = cuentas.reclamar_instalacion(
            bd, codigo, login, nombre, clave, _ahora(), carpeta, ip=_ip() or ""
        )
    except (cuentas.ErrorDeAcceso, cuentas.ContrasenaInvalida, ValueError) as error:
        st.error(str(error))  # mensaje fijo de seguridad.cuentas: no lleva texto ajeno
        return
    _iniciar(bd, usuario)


def _pantalla_de_acceso(bd: Session) -> None:
    st.title(TITULO_ACCESO)
    _aviso_de_red()
    aviso = st.session_state.get(CLAVE_AVISO)
    if aviso:
        st.info(aviso)
    if cuentas.hay_usuarios(bd):
        _formulario_de_entrada(bd)
    else:
        _formulario_primer_administrador(bd)


def _cambio_obligatorio(bd: Session, sesion: SesionActiva) -> None:
    st.title("Cambie su contraseña")
    st.write("Su contraseña es temporal: elija una propia para seguir.")
    with st.form("silice_cambio_de_clave"):
        actual = st.text_input("Contraseña actual", type="password", key="cambio_actual")
        nueva = st.text_input("Contraseña nueva (10 a 128 caracteres)", type="password",
                              key="cambio_nueva")
        repetida = st.text_input("Repita la nueva", type="password", key="cambio_repetida")
        enviar = st.form_submit_button("Cambiar", type="primary")
    if not enviar:
        return
    if nueva != repetida:
        st.error("Las dos contraseñas no coinciden.")
        return
    try:
        ficha = cuentas.cambiar_contrasena(bd, sesion.usuario_id, actual, nueva, _ahora())
    except (cuentas.ErrorDeAcceso, cuentas.ContrasenaInvalida) as error:
        st.error(str(error))  # mensaje fijo de seguridad.cuentas: no lleva texto ajeno
        return
    st.session_state[CLAVE_FICHA] = ficha  # la ficha nueva: la anterior se cerró
    st.rerun()


def exigir_sesion() -> SesionActiva:
    """La sesión vigente, o el acceso y `st.stop()`. Con el acceso apagado, la de desarrollo."""
    if not acceso_activo():
        return DESARROLLO
    with ui_sesion.instalacion() as bd:
        ficha = st.session_state.get(CLAVE_FICHA)
        activa = sesiones.validar(bd, ficha, _ahora())
        if activa is not None:
            if activa.debe_cambiar_clave:
                _cambio_obligatorio(bd, activa)
                st.stop()
            return activa
        if ficha:  # tenía ficha y ya no vale: expiró o se la cerraron
            _recordar_dueno(bd, ficha)
            st.session_state.pop(CLAVE_FICHA, None)
            st.session_state[CLAVE_AVISO] = AVISO_EXPIRADA
        _pantalla_de_acceso(bd)
    st.stop()


def pintar_sesion(sesion: SesionActiva) -> None:
    """«Sesión: Ana Pérez (arma) · Cerrar sesión» en la barra lateral."""
    if sesion is DESARROLLO:
        return
    roles = ", ".join(sorted(rol.value for rol in sesion.roles))
    with st.sidebar:
        st.caption(f"Sesión: {texto_seguro(sesion.nombre)} ({texto_seguro(roles)})")
        aviso = aviso_de_roles(sesion.roles)
        if aviso:
            st.caption(aviso)
        if st.button("Cerrar sesión", key="silice_cerrar_sesion"):
            with ui_sesion.instalacion() as bd:
                sesiones.cerrar(bd, st.session_state.get(CLAVE_FICHA, ""), "salida", _ahora())
            descartar_borrador()
            st.session_state.pop(CLAVE_FICHA, None)
            st.session_state.pop(CLAVE_BORRADOR_DE, None)
            st.rerun()
```
  El interruptor de transición para toda la suite (`tests/conftest.py`):
```python
@pytest.fixture(autouse=True)
def _acceso_apagado(monkeypatch) -> Iterator[None]:
    """S3-1: la interfaz no pide entrar (`SILICE_ACCESO=0`; las pruebas de S3 lo encienden)."""
    monkeypatch.setenv("SILICE_ACCESO", "0")
    yield
```
  El marco: cada página declara su acción; el menú y el recorrido guiado dependen de los roles;
  la barra de herramientas escribe, así que solo la ve quien puede editar la hoja:
```diff
--- a/ui/app.py
+++ b/ui/app.py
@@ -58,10 +58,13 @@
 
 import os
-from collections.abc import Callable, Mapping
+from collections.abc import Callable, Collection, Mapping
 from dataclasses import dataclass
 
 import streamlit as st
 
-from ui import barra
+from seguridad.permisos import Accion, Rol, permitido
+from seguridad.sesiones import SesionActiva
+from ui import acceso, barra
+from ui import sesion as ui_sesion
 from ui.caso import estado_caso, recorrido_activo, resumen_caso, ruta_caso
 from ui.entorno import VARIABLE_MODO_ENTREGA, leer_variable
@@ -98,4 +101,5 @@
     seccion: str
     caso_uso: str | None = None  # codigo de la ERS; el marco lo pinta como subtitulo (RF-42)
+    accion: Accion | None = None  # la de la matriz de roles (S3 5.1); None = toda cuenta la ve
 
     @property
@@ -111,18 +115,26 @@
 PAGINA_INICIO = DefinicionPagina(inicio.render, "Inicio", SECCION_TRABAJO)
 
+_EDITA = Accion.EDITAR_HOJA
+_LEE = Accion.LEER_PROYECTO
+
 PAGINAS: tuple[DefinicionPagina, ...] = (
     PAGINA_INICIO,
-    DefinicionPagina(catalogo.render, "Catalogo de partidas e insumos", SECCION_TRABAJO),
-    DefinicionPagina(componer.render, "Componer una partida", SECCION_TRABAJO, "UC-10 / UC-11"),
-    DefinicionPagina(elaborar.render, "Elaborar un presupuesto", SECCION_TRABAJO, "UC-01"),
-    DefinicionPagina(hoja.render, "Hoja del proyecto", SECCION_TRABAJO),
-    DefinicionPagina(actualizacion.render, "Actualizar precios", SECCION_TRABAJO, "UC-02"),
-    DefinicionPagina(historico.render, "Historico de cambios de precio", SECCION_TRABAJO),
+    DefinicionPagina(catalogo.render, "Catalogo de partidas e insumos", SECCION_TRABAJO,
+                     accion=_LEE),
+    DefinicionPagina(componer.render, "Componer una partida", SECCION_TRABAJO, "UC-10 / UC-11",
+                     _EDITA),
+    DefinicionPagina(elaborar.render, "Elaborar un presupuesto", SECCION_TRABAJO, "UC-01", _EDITA),
+    DefinicionPagina(hoja.render, "Hoja del proyecto", SECCION_TRABAJO, accion=_EDITA),
+    DefinicionPagina(actualizacion.render, "Actualizar precios", SECCION_TRABAJO, "UC-02", _EDITA),
+    DefinicionPagina(historico.render, "Historico de cambios de precio", SECCION_TRABAJO,
+                     accion=_LEE),
     DefinicionPagina(
-        escenarios.render, "Escenarios de sensibilidad", SECCION_INVESTIGACION, "UC-08"
+        escenarios.render, "Escenarios de sensibilidad", SECCION_INVESTIGACION, "UC-08", _EDITA
     ),
-    DefinicionPagina(similares.render, "Partidas similares", SECCION_INVESTIGACION, "UC-03"),
-    DefinicionPagina(simulador.render, "Simulador de listas", SECCION_INVESTIGACION),
-    DefinicionPagina(visor.render, "Visor 3D del modelo", SECCION_INVESTIGACION),
+    DefinicionPagina(similares.render, "Partidas similares", SECCION_INVESTIGACION, "UC-03",
+                     _EDITA),
+    DefinicionPagina(simulador.render, "Simulador de listas", SECCION_INVESTIGACION,
+                     accion=_EDITA),
+    DefinicionPagina(visor.render, "Visor 3D del modelo", SECCION_INVESTIGACION, accion=_EDITA),
 )
 
@@ -139,15 +151,23 @@
 
 
-def paginas_visibles(modo_entrega: bool) -> tuple[DefinicionPagina, ...]:
-    """Las pantallas que se muestran: las once, o sin la seccion Investigacion en modo entrega."""
-    if not modo_entrega:
-        return PAGINAS
-    return tuple(pagina for pagina in PAGINAS if pagina.seccion != SECCION_INVESTIGACION)
-
-
-def secciones_visibles(modo_entrega: bool) -> dict[str, tuple[DefinicionPagina, ...]]:
+def paginas_visibles(
+    modo_entrega: bool, roles: Collection[Rol] | None = None
+) -> tuple[DefinicionPagina, ...]:
+    """Las pantallas que se muestran: las que los `roles` permiten (todas si `roles` es `None`)
+    y, en modo entrega, sin la seccion Investigacion. La navegacion no es el control: cada
+    `render()` vuelve a exigir su accion (S3 5.1)."""
+    return tuple(
+        pagina for pagina in PAGINAS
+        if not (modo_entrega and pagina.seccion == SECCION_INVESTIGACION)
+        and (roles is None or pagina.accion is None or permitido(roles, pagina.accion))
+    )
+
+
+def secciones_visibles(
+    modo_entrega: bool, roles: Collection[Rol] | None = None
+) -> dict[str, tuple[DefinicionPagina, ...]]:
     """Las pantallas visibles agrupadas por seccion; el `dict` conserva el orden de `PAGINAS`."""
     secciones: dict[str, tuple[DefinicionPagina, ...]] = {}
-    for pagina in paginas_visibles(modo_entrega):
+    for pagina in paginas_visibles(modo_entrega, roles):
         secciones[pagina.seccion] = (*secciones.get(pagina.seccion, ()), pagina)
     return secciones
@@ -171,5 +191,8 @@
 
 def marco(
-    definicion: DefinicionPagina, pintar: Callable[[], None], ir_a: Callable[[str], None]
+    definicion: DefinicionPagina,
+    pintar: Callable[[], None],
+    ir_a: Callable[[str], None],
+    sesion: SesionActiva | None = None,
 ) -> None:
     """Los elementos comunes alrededor de una pantalla.
@@ -177,6 +200,11 @@
     `pintar` pinta la pantalla (`Page.run` en la aplicacion, `render` en las pruebas); `ir_a` lleva
     a la pantalla de una ruta (`st.switch_page` en la aplicacion, un registrador en las pruebas).
+    `sesion` es quien entro (S3): sin ella, la de desarrollo con todos los roles. La barra de
+    herramientas escribe, asi que solo la ve quien puede editar la hoja; el recorrido guiado
+    omite los pasos de pantallas que el rol no ve (RF-37).
     """
-    barra.pintar_barra(definicion.ruta_url, ir_a)
+    roles = ui_sesion.DESARROLLO.roles if sesion is None else sesion.roles
+    if permitido(roles, Accion.EDITAR_HOJA):
+        barra.pintar_barra(definicion.ruta_url, ir_a)
     st.title(definicion.titulo)
     if definicion.caso_uso is not None:
@@ -184,4 +212,7 @@
     _pintar_caso_abierto()
     recorrido = recorrido_por_nombre(recorrido_activo())
+    if recorrido is not None:
+        visibles = {pagina.ruta_url for pagina in paginas_visibles(False, roles)}
+        recorrido = recorrido.visible_en(visibles)
     _pintar_posicion(recorrido, definicion.ruta_url)
     pintar()
@@ -222,4 +253,6 @@
     """Punto de entrada de `streamlit run ui/app.py`: configura, enruta y enmarca la pantalla."""
     st.set_page_config(page_title=TITULO_APP, layout="wide")
+    sesion = acceso.exigir_sesion()  # sin sesion valida pinta el acceso y detiene el guion
+    acceso.pintar_sesion(sesion)
     modo_entrega = modo_entrega_activo()
     paginas = {
@@ -230,9 +263,9 @@
             default=definicion is PAGINA_INICIO,
         )
-        for definicion in paginas_visibles(modo_entrega)
+        for definicion in paginas_visibles(modo_entrega, sesion.roles)
     }
     secciones = {
         seccion: [paginas[definicion.ruta_url] for definicion in definiciones]
-        for seccion, definiciones in secciones_visibles(modo_entrega).items()
+        for seccion, definiciones in secciones_visibles(modo_entrega, sesion.roles).items()
     }
     actual = st.navigation(secciones, position=POSICION_NAVEGACION)
@@ -241,4 +274,5 @@
         actual.run,
         lambda ruta: st.switch_page(paginas[ruta]),
+        sesion,
     )
 
```
  El recorrido sin los pasos que el rol no ve (RF-37):
```diff
--- a/ui/recorridos.py
+++ b/ui/recorridos.py
@@ -15,4 +15,5 @@
 from __future__ import annotations
 
+from collections.abc import Collection
 from dataclasses import dataclass
 
@@ -58,4 +60,10 @@
             )
 
+    def visible_en(self, rutas: Collection[str]) -> Recorrido | None:
+        """El recorrido sin los pasos de pantallas que el rol no ve (S3 §5.7, RF-37): ningún
+        paso apunta a una pantalla ausente del menú. `None` si no queda ninguno."""
+        pasos = tuple(paso for paso in self.pasos if paso.pagina in rutas)
+        return Recorrido(self.nombre, self.proposito, pasos) if pasos else None
+
     def posicion(self, ruta: str) -> int | None:
         """Numero del paso (desde 1) que ocurre en la pantalla `ruta`.
```
  La barra, `puede_cambiar_de_caso` y el botón de sembrar el ejemplo del Inicio:
```diff
--- a/ui/barra.py
+++ b/ui/barra.py
@@ -35,4 +35,6 @@
 import streamlit as st
 
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.caso import (
     ACCION_EXPORTAR_EXCEL,
@@ -112,4 +114,5 @@
 
 def _crear_proyecto() -> None:
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     try:
         nombre = crear_proyecto_nuevo(ruta_caso(), st.session_state.get(CLAVE_NOMBRE_NUEVO, ""))
```
```diff
--- a/ui/caso.py
+++ b/ui/caso.py
@@ -50,4 +50,6 @@
 )
 from operacion.config import ruta_caso_por_defecto
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.entorno import VARIABLE_CASO, leer_variable
 
@@ -93,7 +96,7 @@
 
 def puede_cambiar_de_caso() -> bool:
-    """«Cambiar de caso»: solo *arma* y administrador (maestro §4.3). En la 0.6.0 no hay cuentas,
-    asi que todos pueden; S3-1 reemplaza este cuerpo por la comprobacion del rol de la sesion."""
-    return True
+    """«Cambiar de caso»: solo *arma* y administrador (maestro §4.3, S3 §5.1). Con el acceso
+    apagado (transicion, RP8-4) la sesion de desarrollo tiene todos los roles."""
+    return ui_sesion.puede(Accion.CAMBIAR_CASO)
 
 
```
```diff
--- a/ui/paginas/inicio.py
+++ b/ui/paginas/inicio.py
@@ -23,5 +23,7 @@
 from operacion.config import BASE_ANTERIOR, carpeta_casos
 from scripts.seed_demo import main as sembrar_demostracion
+from seguridad.permisos import Accion
 from ui import caso
+from ui import sesion as ui_sesion
 from ui.caso import (
     SIN_PERMISO_DE_CAMBIO,
@@ -128,5 +136,5 @@
         "presupuesto auditado— o abrir otro caso arriba."
     )
-    if st.button(ROTULO_SEMBRAR, type="primary"):
+    if ui_sesion.puede(Accion.EDITAR_HOJA) and st.button(ROTULO_SEMBRAR, type="primary"):
         with st.spinner("Cargando la linea base, la demostracion y su presupuesto auditado..."):
             try:
```
  Cada pantalla vuelve a exigir su acción en la primera línea de `render()`. Para la hoja
  (`ui/paginas/hoja.py`) y para «Actualizar precios» (`ui/paginas/actualizacion.py`) se agregan las
  dos importaciones (`from seguridad.permisos import Accion` y `from ui import sesion as ui_sesion`)
  y esta primera instrucción de `render()`:
```python
    ui_sesion.exigir(Accion.EDITAR_HOJA)
```
  Las demás pantallas (lectura o edición, según su `accion`):
```diff
--- a/ui/paginas/catalogo.py
+++ b/ui/paginas/catalogo.py
@@ -19,4 +19,6 @@
 from core.verification.texto import formatear_decimal
 from operacion.base_datos import preparar_base
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.caso import ruta_caso
 
@@ -24,4 +26,5 @@
 def render() -> None:
     """Dos tablas de solo lectura: partidas del catalogo e insumos con su precio vigente."""
+    ui_sesion.exigir(Accion.LEER_PROYECTO)
     st.caption("Partidas e insumos del catalogo, con el precio vigente de cada insumo.")
 
```
```diff
--- a/ui/paginas/historico.py
+++ b/ui/paginas/historico.py
@@ -21,4 +21,6 @@
 from core.verification.texto import formatear_decimal
 from operacion.base_datos import preparar_base
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.caso import ruta_caso
 
@@ -28,4 +30,5 @@
 def render() -> None:
     """Filtros en la barra lateral; la tabla de cambios en el cuerpo."""
+    ui_sesion.exigir(Accion.LEER_PROYECTO)
     st.caption(
         "Cada fila es un insumo que cambio de precio entre la lista anterior y la lista nueva de "
```
```diff
--- a/ui/paginas/componer.py
+++ b/ui/paginas/componer.py
@@ -56,4 +56,6 @@
 from core.verification.texto import formatear_decimal
 from operacion.base_datos import preparar_base
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.caso import ruta_caso
 from ui.composicion import (
@@ -134,4 +136,5 @@
 def render() -> None:
     """Cabecera de la partida, tres tablas de insumos, desglose en vivo y boton de guardado."""
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     st.caption(
         "Componga una partida a mano: declare su cabecera y sus tres tablas de insumos, vea el "
```
```diff
--- a/ui/paginas/elaborar.py
+++ b/ui/paginas/elaborar.py
@@ -56,5 +56,7 @@
 from core.verification.texto import formatear_decimal
 from operacion.base_datos import preparar_base
+from seguridad.permisos import Accion
 from ui import elaboracion
+from ui import sesion as ui_sesion
 from ui.caso import ruta_caso
 from ui.resultado import mostrar_elaboracion
@@ -88,4 +90,5 @@
 def render() -> None:
     """Selector de dominio y archivo; tabla de cómputo; botón de elaboración e informe."""
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     st.caption(
         "Elige un dominio, carga su archivo de muestra (data/samples/<dominio>/) y extrae el "
```
```diff
--- a/ui/paginas/escenarios.py
+++ b/ui/paginas/escenarios.py
@@ -46,4 +46,6 @@
 from core.verification.texto import formatear_decimal
 from operacion.base_datos import preparar_base
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.caso import ruta_caso
 from ui.composicion import decimal_desde_texto
@@ -56,4 +58,5 @@
 def render() -> None:
     """Selector de presupuesto, formulario de supuestos y tabla comparativa de RF-31."""
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     st.caption(
         "Recalcula un presupuesto guardado variando parametros de costo o precios de insumos. "
```
```diff
--- a/ui/paginas/similares.py
+++ b/ui/paginas/similares.py
@@ -35,4 +35,6 @@
 from core.verification.texto import formatear_decimal
 from operacion.base_datos import preparar_base
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.caso import ruta_caso
 from ui.composicion import sugerir_partidas_similares
@@ -49,4 +51,5 @@
 def render() -> None:
     """Descripcion en texto libre -> tres propuestas con puntaje, desglose y rendimiento."""
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     st.caption(
         "Escribe la descripcion de la partida: el sistema propone las mas parecidas del catalogo "
```
```diff
--- a/ui/paginas/simulador.py
+++ b/ui/paginas/simulador.py
@@ -22,4 +22,6 @@
 from operacion.base_datos import preparar_base
 from scripts.simular_lista import simular
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.caso import ruta_caso
 
@@ -30,4 +32,5 @@
 def render() -> None:
     """Formulario en la barra lateral; vista previa y descarga del CSV en el cuerpo."""
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     st.caption(
         "Toma la lista de precios vigente del catalogo y aplica variaciones deterministas segun "
```
```diff
--- a/ui/paginas/visor.py
+++ b/ui/paginas/visor.py
@@ -44,4 +44,6 @@
 from core.verification.informe import DECIMALES_PRESENTACION
 from core.verification.texto import formatear_decimal
+from seguridad.permisos import Accion
+from ui import sesion as ui_sesion
 from ui.subidas import guardar_subida
 from ui.visor3d import mallas
@@ -76,4 +78,5 @@
 def render() -> None:
     """Selector de archivo IFC; visor three.js y tabla de cómputo lado a lado."""
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     st.caption(
         "Carga un modelo IFC y compara su geometria con el cómputo que extrae el adaptador civil: "
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite de pantallas, que no debe notar el acceso)
Run: `uv run pytest tests/unit/test_ui_acceso.py tests/unit/test_ui_marco.py
tests/unit/test_ui_importable.py tests/unit/test_ui_app.py tests/unit/test_ui_inicio.py
tests/unit/test_ui_hoja.py tests/unit/test_ui_caso.py tests/unit/test_ui_barra.py -v -W error`
→ verde. Run: `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-1 --junit
reporte-pruebas.xml` → `S3-M3` en OK (ningún `unsafe_allow_html`).
- [ ] **Paso 5: Commit**
```bash
git add ui/sesion.py ui/acceso.py ui/app.py ui/recorridos.py ui/barra.py ui/caso.py ui/paginas \
  tests/conftest.py
git commit -m "feat(ui): acceso, sesion por pestana y menu por rol con cada pantalla vigilada" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS3-1 y foco de revisión de la fase

**Compuerta GS3-1** (se cruza al fusionar `inc/080-s3-1-seguridad`):
1. `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-1 --junit reporte-pruebas.xml`
   en OK, salvo `S3-M5` (PENDIENTE: ninguna rama de planos fusionada todavía).
2. CI verde en Linux y Windows, `-W error`, cero omitidas; la suite entera con `SILICE_ACCESO=0`.
3. **El encargo de seguridad** aprueba (Argon2id, fichas, bloqueo, freno global, registro sin
   secretos, red local, la amenaza de reanudación de sesión sin TLS declarada) y **el de
   usabilidad** (Nielsen e ISO 9241-110: mensajes llanos, sin traza, el mismo mensaje exista o no el
   usuario).
4. Compuerta anotada en `docs/bitacora/2026-10-silice-080.md`.

**Foco de revisión de S3-1** (lo que el spec implica y ninguna prueba ejercita todavía):
1. **Enumeración de usuarios por tiempo o por mensaje:**
   `test_contrasena_erronea_da_el_mismo_mensaje_ exista_o_no_el_usuario` y
   `test_un_login_inexistente_se_verifica_contra_la_huella_de_relleno`.
2. **Ficha reutilizada tras entrar:**
   `test_alta_con_temporal_obliga_a_cambiarla_y_cambiarla_da_ficha_ nueva` fija que cambiar la
   contraseña emite una ficha nueva.
3. **Una pantalla sin guardia** (también las de S1 y S2): `test_cada_render_exige_su_accion_en_la_
   primera_linea` y `test_toda_pantalla_menos_el_inicio_declara_la_accion_que_la_protege`.
4. **Un secreto en la base o en el registro:** `test_ninguna_contrasena_queda_en_la_base_ni_en_los_
   eventos`.
5. **Un nombre de cuenta con Markdown** que se interprete en la pantalla: `test_el_nombre_de_una_
   cuenta_con_markdown_no_se_interpreta` y la fila `S3-M3` de la meta.

---

# S3-2 — Núcleo: canónico, cadena, WAL y comparación (rama `inc/080-s3-2-nucleo`)

**Carril único de núcleo.** Solo `core/`, `migraciones/`, `tests/`, `docs/` y `scripts/`; nunca
`ui/`, `adapters/`, `ml/` ni `api/`. Sale de `origin/main` con S2-3 cerrada, y **no se abre sin el
visto bueno del tutor** de SL-E7, SL-E8, SL-E9 y SL-E12 (tarea 2). `core/contracts/` no se toca.
Cada tarea corre `uv run python scripts/guardia_nucleo.py --base origin/main` en 0 antes de su
commit. Al terminar, cada versión que se guarda queda sellada en una cadena de huellas a nombre de
quien la confirmó, el documento canónico tiene un vector de huella escrito a mano, varias personas
pueden guardar a la vez sin bifurcar la cadena, y hay una diferencia entre versiones con su costo.

### Tarea 7: SL-E8 — documento canónico de una versión y su lectura

**Rama:** `inc/080-s3-2-nucleo` (sale de `main` con S2-3 cerrada; PR a `main`, apilada con S3-3,
RP8-20) **Rol:** sf-ingeniero-nucleo **Archivos:**
- Crear: `core/budget/canonico.py`, `tests/fixtures/canonico_minimo.py`
- Prueba: `tests/integration/test_canonico.py`

**Interfaces:**
- Consume: `core.models` (incluidas `MonedaProyecto`, `ListaEmpresa` y `PrecioOrigen` de S1),
  `core.catalog.origen.origenes_efectivos` y `core.catalog.empresa.es_heredado` (S1),
  `core.budget.{crear_proyecto, elaborar, guardar_presupuesto, plan_secuencial}`;
  `seguridad.json_estricto.PATRON_CIFRA` (tarea 4, solo en la prueba, para que los dos patrones
  no diverjan); `tests/fixtures/canonico/ejemplo_v1.py` (tarea 2).
- Produce:
  - `core.budget.canonico`: `class DocumentoInvalido(ValueError)`
  - `core.budget.canonico`: `def texto_decimal(valor: Decimal | None) -> str | None`
  - `core.budget.canonico`: `def json_canonico(objeto: Any) -> bytes`
  - `core.budget.canonico`: `def huella(datos: bytes) -> str`
  - `core.budget.canonico`: `def documento(session: Session, version: models.Presupuesto) ->
      bytes`
  - `core.budget.canonico`: `def estructura(session: Session, version: models.Presupuesto) ->
      dict[str, Any]`
  - `core.budget.canonico`: `class RenglonDeclarado`
  - `core.budget.canonico`: `class LineaLeida`
  - `core.budget.canonico`: `class DocumentoLeido`
  - `core.budget.canonico`: `def contar_filas(objeto: Mapping[str, Any]) -> int`
  - `core.budget.canonico`: `def leer(objeto: Mapping[str, Any]) -> DocumentoLeido`
  - `tests.fixtures.canonico_minimo`: `RELLENO`, `guardar_otra(sesion, proyecto, lista, codigo,
    cantidad="20", **opciones)`, `sembrar_minimo(sesion, **opciones) -> (proyecto, version, lista)`,
    `registro(proyecto, origen, resultante, campo="cantidad", responsable=USUARIO)`.

El documento se serializa **desde las filas guardadas**, nunca recalculado: claves ordenadas, sin
espacios, UTF-8 sin escapar, `Decimal` con `format(valor, "f")` y ningún `id` de fila (cambian entre
instalaciones). Su inversa, `leer`, valida cada cifra con el patrón ANTES de construir un `Decimal`.
Tres decisiones del plan: la moneda del proyecto de una versión (RP8-3), las cifras de 20 enteros
y 28 decimales (RP8-13) y la prohibición de exponentes.

- [ ] **Paso 0: Antes del código** — el expediente SL-E8 está commiteado (tarea 2), el tutor dio su
  visto bueno y `git switch -c inc/080-s3-2-nucleo origin/main` está hecho.
- [ ] **Paso 1: Escribir la prueba que falla** (el vector de huella escrito a mano debe dar los
  2271 bytes y el SHA-256 `b4b952dd…3936` desde las filas de una base real)
  La fixture que siembra «MIN-001» (una partida, tres insumos, un renglón); en esta tarea todavía no
  hay `usuario` en el embudo:
**`tests/fixtures/canonico_minimo.py`**
```python
"""La versión mínima del vector de huella (S3 §13.1): una partida, tres insumos, un renglón.

`sembrar_minimo(sesion)` guarda la versión `001` del proyecto «MIN-001» con lo que describe a mano
`tests/fixtures/canonico/ejemplo_v1.py`. Los números están elegidos para que cada monto salga
exacto: RELLENO de 20 m3 con rendimiento 8 y los parámetros de la línea base.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto, plan_secuencial
from core.catalog import Catalogo
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo

FECHA = date(2026, 11, 1)
PARAMETROS = ParametrosCosto()
USUARIO = "Ana Pérez <ana>"
AHORA = datetime(2026, 11, 1, 10, 0, 0)

RELLENO = ComposicionAPU(
    codigo_partida="MIN-001",
    descripcion="Relleno de prueba",
    unidad="m3",
    rendimiento=Decimal("8"),
    materiales=(LineaMaterial("Arena", "m3", Decimal("1.00"), Decimal("14.00")),),
    equipos=(LineaEquipo("Compactadora", Decimal("1"), Decimal("71.00"), Decimal("0.10")),),
    mano_obra=(LineaManoObra("Obrero", Decimal("2"), Decimal("10.25")),),
)
ITEM = ItemComputo(
    codigo_partida="MIN-001",
    descripcion="Relleno de prueba",
    unidad="m3",
    cantidad=Decimal("20"),
    origen_id="FILA-1",
    origen_tipo=OrigenTipo.TABULAR,
    dominio=Dominio.CIVIL,
)


def _elaborar(codigo: str, cantidad: str):
    item = ItemComputo(
        codigo_partida="MIN-001", descripcion="Relleno de prueba", unidad="m3",
        cantidad=Decimal(cantidad), origen_id="FILA-1", origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.CIVIL,
    )
    return elaborar(
        [item], {"MIN-001": RELLENO}, PARAMETROS, codigo=codigo, fecha=FECHA, moneda="USD",
        plan=plan_secuencial,
    )


def guardar_otra(sesion, proyecto, lista, codigo: str, cantidad: str = "20", **opciones):
    """Otra versión del mismo relleno por el embudo; `opciones` van tal cual a
    `guardar_presupuesto` (`version_origen`, `motivo`...)."""
    resultado = _elaborar(codigo, cantidad)
    return guardar_presupuesto(
        sesion, resultado.presupuesto, resultado.informe, proyecto=proyecto, lista=lista,
        parametros=PARAMETROS, pendientes=resultado.pendientes, **opciones,
    )


def sembrar_minimo(sesion, **opciones):
    """Devuelve `(proyecto, version, lista)`; la sesión queda con la transacción abierta.
    `opciones` va al embudo."""
    lista = models.ListaPrecios(
        nombre="Lista de prueba", moneda="USD", fecha_vigencia=FECHA, origen="prueba"
    )
    sesion.add(lista)
    sesion.flush()
    Catalogo(sesion).cargar_composicion(RELLENO, lista, Dominio.CIVIL, FECHA, "prueba")
    proyecto = crear_proyecto(sesion, "MIN-001", dominio=Dominio.CIVIL)
    version = guardar_otra(sesion, proyecto, lista, "001", **opciones)
    return proyecto, version, lista


def registro(proyecto, origen, resultante, campo="cantidad", responsable=USUARIO):
    """Un `RegistroCambio` de la versión `resultante`, como los que agregan edición y cotización."""
    return models.RegistroCambio(
        proyecto_id=proyecto.id, version_origen_id=origen.id if origen else None,
        version_resultante_id=resultante.id, objeto="apu", clave="MIN-001|Arena", campo=campo,
        valor_anterior="1.00", valor_nuevo="1.50", fuente="memoria rev. B",
        responsable=responsable, fecha_hora=AHORA,
    )
```
**`tests/integration/test_canonico.py`**
```python
"""SL-E8: el documento canónico de una versión, su vector escrito a mano y su ida y vuelta
(RF-83, RF-85; spec S3 §6.1 y §13.1)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal

import pytest

from core import models
from core.budget import canonico
from core.catalog import abrir_sesion
from core.contracts.apu import ParametrosCosto
from seguridad.json_estricto import PATRON_CIFRA as PATRON_DEL_LECTOR
from seguridad.json_estricto import leer_json
from tests.fixtures.canonico.ejemplo_v1 import BYTES_EJEMPLO_V1, EJEMPLO_V1, HUELLA_EJEMPLO_V1
from tests.fixtures.canonico_minimo import RELLENO, guardar_otra, sembrar_minimo


@pytest.fixture
def minimo(motor):
    with abrir_sesion(motor) as sesion:
        proyecto, version, lista = sembrar_minimo(sesion)
        sesion.commit()
        yield sesion, proyecto, version, lista


def test_el_vector_escrito_a_mano_tiene_la_huella_literal() -> None:
    """La huella se calculó aparte con `sha256sum` sobre estos mismos bytes."""
    datos = canonico.json_canonico(EJEMPLO_V1)
    assert len(datos) == BYTES_EJEMPLO_V1
    assert hashlib.sha256(datos).hexdigest() == HUELLA_EJEMPLO_V1
    assert canonico.huella(datos) == HUELLA_EJEMPLO_V1


def test_documento_de_la_version_sembrada_da_exactamente_los_bytes_del_vector(minimo) -> None:
    sesion, _, version, _ = minimo
    datos = canonico.documento(sesion, version)
    assert datos == canonico.json_canonico(EJEMPLO_V1)
    assert canonico.huella(datos) == HUELLA_EJEMPLO_V1


def test_guardar_y_recargar_no_cambia_la_huella(motor, minimo) -> None:
    sesion, _, version, _ = minimo
    antes = canonico.huella(canonico.documento(sesion, version))
    sesion.expire_all()
    with abrir_sesion(motor) as otra:
        recargada = otra.get(models.Presupuesto, version.id)
        assert canonico.huella(canonico.documento(otra, recargada)) == antes


def test_el_documento_no_lleva_ningun_id_de_fila(minimo) -> None:
    sesion, _, version, _ = minimo
    texto = canonico.documento(sesion, version).decode()
    for clave in ("id", "proyecto_id", "presupuesto_id", "lista_id", "insumo_id", "partida_id"):
        assert f'"{clave}":' not in texto


def test_el_documento_no_cambia_al_leer_dos_veces_ni_al_reordenar(minimo) -> None:
    sesion, _, version, _ = minimo
    uno = canonico.documento(sesion, version)
    assert canonico.documento(sesion, version) == uno
    assert list(json.loads(uno)) == sorted(json.loads(uno))  # claves ordenadas


def test_leer_es_la_inversa_de_documento(minimo) -> None:
    sesion, _, version, _ = minimo
    leido = canonico.leer(leer_json(canonico.documento(sesion, version)))
    assert (leido.codigo, leido.moneda, leido.proyecto, leido.moneda_proyecto) == (
        "001", "USD", "MIN-001", None)
    assert leido.parametros == ParametrosCosto()
    assert leido.composiciones["MIN-001"] == RELLENO
    assert leido.items[0].cantidad == Decimal("20") and leido.items[0].origen_id == "FILA-1"
    declarado = leido.declarados[0]
    assert declarado.precio_unitario == Decimal("41.83987500")
    assert declarado.total == Decimal("836.79750000")
    assert leido.plan == (("Dia 1", (("MIN-001", Decimal("1")),)),)
    assert leido.curva[0].acumulado == Decimal("836.79750000")
    assert leido.lineas["MIN-001"][0].insumo == "MAT-001"
    assert leido.lineas["MIN-001"][0].precio_origen["moneda_original"] == "USD"


def test_los_ceros_a_la_derecha_se_conservan(minimo) -> None:
    sesion, _, version, _ = minimo
    renglon = json.loads(canonico.documento(sesion, version))["renglones"][0]
    assert renglon["materiales"] == "14.0000" and renglon["precio_unitario"] == "41.83987500"


def test_un_decimal_con_exponente_se_escribe_posicional() -> None:
    assert canonico.texto_decimal(Decimal("1E+3")) == "1000"
    assert canonico.texto_decimal(Decimal("0.00001")) == "0.00001"
    assert canonico.texto_decimal(None) is None


@pytest.mark.parametrize("cambio", [
    lambda d: d.update(formato="otro"),
    lambda d: d.update(version_formato=2),
    lambda d: d.pop("renglones"),
    lambda d: d["parametros"].update(fcas="1E+5"),
    lambda d: d["renglones"][0]["item"].update(cantidad="1,5"),
    lambda d: d["composiciones"][0]["lineas"][0].update(tipo="inventado"),
])
def test_un_documento_mal_formado_se_rechaza_con_un_mensaje(minimo, cambio) -> None:
    sesion, _, version, _ = minimo
    objeto = json.loads(canonico.documento(sesion, version))
    cambio(objeto)
    with pytest.raises(canonico.DocumentoInvalido):
        canonico.leer(objeto)


def test_el_patron_de_cifras_es_el_del_lector_estricto() -> None:
    """`core` no puede importar `seguridad`: el patrón vive en los dos y no puede divergir."""
    assert canonico.PATRON_CIFRA.pattern == PATRON_DEL_LECTOR.pattern


def test_contar_filas_suma_renglones_y_lineas(minimo) -> None:
    sesion, _, version, _ = minimo
    assert canonico.contar_filas(json.loads(canonico.documento(sesion, version))) == 1 + 3
    assert canonico.contar_filas({"renglones": "no"}) == 0


def test_la_moneda_del_proyecto_sigue_el_orden_de_creacion_y_no_la_fecha(minimo) -> None:
    sesion, proyecto, v1, lista = minimo
    sesion.add(models.MonedaProyecto(
        proyecto_id=proyecto.id, moneda="USD", desde=datetime(2026, 11, 1, 9, 0), version_id=None,
        responsable="ana", fuente="al crear"))
    sesion.commit()
    antes = canonico.documento(sesion, v1)
    assert json.loads(antes)["moneda_proyecto"] == "USD"
    v2 = guardar_otra(sesion, proyecto, lista, "002")
    sesion.add(models.MonedaProyecto(
        proyecto_id=proyecto.id, moneda="Bs", desde=datetime(2026, 11, 1, 9, 0),
        version_id=v2.id, responsable="ana", fuente="conversion"))
    sesion.commit()
    # misma fecha de calendario, pero la conversión nació con v2: v1 NO cambia
    assert canonico.documento(sesion, v1) == antes
    assert json.loads(canonico.documento(sesion, v2))["moneda_proyecto"] == "Bs"


def test_una_declaracion_posterior_a_la_version_no_cambia_su_documento(minimo) -> None:
    sesion, proyecto, v1, _ = minimo
    antes = canonico.documento(sesion, v1)  # la versión es del 2026-11-01 y no hay declaración
    sesion.add(models.MonedaProyecto(
        proyecto_id=proyecto.id, moneda="USD", desde=datetime(2026, 11, 5, 9, 0), version_id=None,
        responsable="ana", fuente="declarada despues"))
    sesion.commit()
    assert canonico.documento(sesion, v1) == antes
    assert json.loads(antes)["moneda_proyecto"] is None
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_canonico.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'core.budget.canonico'`.
```bash
git add tests/fixtures/canonico_minimo.py tests/integration/test_canonico.py
git commit -m "test(nucleo): documento canonico y su vector de huella en rojo (SL-E8)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`core/budget/canonico.py`**
```python
"""SL-E8: el documento canónico de una versión y su lectura (spec S3 §6.1; maestro §4.5).

`documento(session, version)` serializa, **desde las filas guardadas** (nunca recalculadas), todo
lo que define una versión: JSON UTF-8, claves ordenadas, sin espacios, `Decimal` como el texto
posicional exacto de `DecimalExacto`, y sin ningún `id` de fila (cambian entre instalaciones).
Es a la vez el contenido que se encadena (`huella_contenido`), el `presupuesto.json` del paquete
y el cuerpo de `POST /v1/auditorias` (DRY).

`leer(objeto)` es la inversa. Recibe el objeto ya leído por el lector JSON estricto del paquete
(`seguridad.json_estricto`, que `core` no puede importar): aquí solo se valida la forma y que
cada cifra cumpla `PATRON_CIFRA` ANTES de construir un `Decimal`. El patrón es el mismo de aquel
lector; `tests/unit/test_canonico.py` vigila que no diverjan.

Tres decisiones que el spec dejó abiertas (plan 0.8.0, RP8-3 y RP8-13):
* la **moneda del proyecto** de una versión sale de `_moneda_del_proyecto`: la última conversión
  hecha hasta esa versión (por **orden de creación**, no por fecha) o, si no hay, la primera
  declaración si ya existía a su fecha;
* los `Decimal` se escriben con `format(valor, "f")`: nunca con exponente (`1E+3` no pasaría el
  patrón); coincide con `str` para toda cifra sin exponente;
* el patrón admite 20 enteros y 28 decimales: el motor no redondea (prec 28).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.curva import PeriodoPlan
from core.catalog.empresa import es_heredado
from core.catalog.origen import origenes_efectivos
from core.contracts.apu import (
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ParametrosCosto,
)
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import PuntoCurva
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = [
    "FORMATO",
    "PATRON_CIFRA",
    "VERSION_FORMATO",
    "DocumentoInvalido",
    "DocumentoLeido",
    "LineaLeida",
    "RenglonDeclarado",
    "documento",
    "estructura",
    "contar_filas",
    "huella",
    "json_canonico",
    "leer",
    "texto_decimal",
]

FORMATO = "silice-presupuesto"
VERSION_FORMATO = 1
PATRON_CIFRA = re.compile(r"^-?[0-9]{1,20}(\.[0-9]{1,28})?$")


class DocumentoInvalido(ValueError):  # noqa: N818
    """El documento no tiene la forma de `silice-presupuesto` v1; el mensaje dice qué falta."""


# --- serialización --------------------------------------------------------------------------


def texto_decimal(valor: Decimal | None) -> str | None:
    """El texto posicional exacto de un `Decimal` (sin exponente); `None` queda `None`."""
    return None if valor is None else format(valor, "f")


def json_canonico(objeto: Any) -> bytes:
    """Claves ordenadas, sin espacios, UTF-8 sin escapar: la misma entrada, los mismos bytes."""
    return json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def huella(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def documento(session: Session, version: models.Presupuesto) -> bytes:
    """El documento canónico de `version`, leído de la base (sin `commit` ni escritura)."""
    return json_canonico(estructura(session, version))


def estructura(session: Session, version: models.Presupuesto) -> dict[str, Any]:
    lista = version.lista_precios
    precios = {precio.insumo_id: precio for precio in lista.precios}
    origenes = origenes_efectivos(session, lista)
    referencias = dict(
        session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
            .join(models.PrecioInsumo, models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id)
            .where(models.PrecioInsumo.lista_id == lista.id)
        ).all()
    )
    renglones = sorted(version.partidas, key=lambda r: r.orden)
    citados = {r.item_computo_id for r in renglones}
    pendientes = [i for i in _items(session, version) if i.id not in citados]
    return {
        "formato": FORMATO,
        "version_formato": VERSION_FORMATO,
        "codigo": version.codigo,
        "fecha": version.fecha.isoformat(),
        "moneda": version.moneda,
        "moneda_proyecto": _moneda_del_proyecto(session, version),
        "proyecto": version.proyecto.nombre,
        "parametros": {
            "fcas": texto_decimal(version.fcas),
            "bono_alimentacion": texto_decimal(version.bono_alimentacion),
            "administracion": texto_decimal(version.administracion),
            "utilidad": texto_decimal(version.utilidad),
        },
        "lista": _lista(session, lista),
        "renglones": [_renglon(r) for r in renglones],
        "pendientes": [_item(i) for i in pendientes],
        "composiciones": _composiciones(session, version, lista, precios, origenes, referencias),
        "plan": _plan(session, version),
        "curva": [
            {"orden": p.orden, "periodo": p.periodo, "monto": texto_decimal(p.monto),
             "acumulado": texto_decimal(p.acumulado)}
            for p in sorted(version.curva, key=lambda p: p.orden)
        ],
        "hallazgos": _hallazgos(session, version),
    }


def _items(session: Session, version: models.Presupuesto) -> list[models.ItemComputo]:
    return list(
        session.scalars(
            select(models.ItemComputo)
            .where(models.ItemComputo.presupuesto_id == version.id)
            .order_by(models.ItemComputo.id)
        )
    )


def _moneda_del_proyecto(session: Session, version: models.Presupuesto) -> str | None:
    """La moneda del proyecto que regía en `version`, de `moneda_proyecto` (S1). Regla única:
    1) la última conversión (fila con `version_id`) hecha hasta esta versión, por orden de
    creación; 2) si no hay, la PRIMERA declaración sin versión, si ya existía a la fecha de la
    versión; 3) si no, ninguna. Así ni una conversión ni una declaración POSTERIOR cambian el
    documento de una versión ya sellada."""
    filas = list(
        session.scalars(
            select(models.MonedaProyecto)
            .where(models.MonedaProyecto.proyecto_id == version.proyecto_id)
            .order_by(models.MonedaProyecto.id)
        )
    )
    conversiones = [f for f in filas if f.version_id is not None and f.version_id <= version.id]
    if conversiones:
        return conversiones[-1].moneda
    declaraciones = [f for f in filas if f.version_id is None]
    if declaraciones and declaraciones[0].desde.date() <= version.fecha:
        return declaraciones[0].moneda
    return None


def _lista(session: Session, lista: models.ListaPrecios) -> dict[str, Any]:
    origen = session.get(models.ListaPreciosOrigen, lista.id)
    de_empresa = session.get(models.ListaEmpresa, lista.id)
    return {
        "nombre": lista.nombre,
        "moneda": lista.moneda,
        "fecha_vigencia": lista.fecha_vigencia.isoformat(),
        "origen": lista.origen,
        "alcance": origen.alcance if origen else models.ALCANCE_GLOBAL,
        "tasa": texto_decimal(origen.tasa) if origen else None,
        "fecha_tasa": origen.fecha_tasa.isoformat() if origen and origen.fecha_tasa else None,
        "empresa": (
            {"nombre": de_empresa.empresa_nombre, "rif": de_empresa.empresa_rif}
            if de_empresa
            else None
        ),
    }


def _item(item: models.ItemComputo) -> dict[str, Any]:
    return {
        "codigo_partida": item.codigo_partida,
        "descripcion": item.descripcion,
        "unidad": item.unidad,
        "unidad_original": item.unidad_original,
        "cantidad": texto_decimal(item.cantidad),
        "origen_id": item.origen_id,
        "origen_tipo": item.origen_tipo,
        "dominio": item.dominio,
        "regla": item.regla,
        "parametros": json.loads(item.parametros),
        "especificaciones": json.loads(item.especificaciones),
    }


def _renglon(renglon: models.PartidaPresupuestada) -> dict[str, Any]:
    return {
        "orden": renglon.orden,
        "item": _item(renglon.item_computo),
        "cantidad": texto_decimal(renglon.cantidad),
        "materiales": texto_decimal(renglon.materiales),
        "equipos": texto_decimal(renglon.equipos),
        "mano_obra": texto_decimal(renglon.mano_obra),
        "costo_directo": texto_decimal(renglon.costo_directo),
        "con_administracion": texto_decimal(renglon.con_administracion),
        "precio_unitario": texto_decimal(renglon.precio_unitario),
        "total": texto_decimal(renglon.total),
    }


def _composiciones(
    session: Session,
    version: models.Presupuesto,
    lista: models.ListaPrecios,
    precios: Mapping[int, models.PrecioInsumo],
    origenes: Mapping[int, Any],
    referencias: Mapping[int, str],
) -> list[dict[str, Any]]:
    filas = session.scalars(
        select(models.ComposicionVersion)
        .where(models.ComposicionVersion.presupuesto_id == version.id)
        .order_by(models.ComposicionVersion.id)
    )
    salida = []
    for fila in filas:
        lineas = []
        for linea in sorted(fila.lineas, key=lambda x: x.orden):
            precio = precios.get(linea.insumo_id) if linea.insumo_id is not None else None
            lineas.append(
                {
                    "orden": linea.orden,
                    "tipo": linea.tipo,
                    "insumo": linea.insumo.codigo if linea.insumo is not None else None,
                    "descripcion": linea.descripcion,
                    "unidad": linea.unidad,
                    "cantidad": texto_decimal(linea.cantidad),
                    "precio": texto_decimal(linea.precio),
                    "depreciacion": texto_decimal(linea.depreciacion),
                    "modalidad": linea.modalidad,
                    "referencia": referencias.get(precio.id, "") if precio else "",
                    "precio_origen": _precio_origen(session, lista, precio, origenes),
                }
            )
        salida.append(
            {
                "codigo_partida": fila.codigo_partida,
                "descripcion": fila.descripcion,
                "unidad": fila.unidad,
                "rendimiento": texto_decimal(fila.rendimiento),
                "lineas": lineas,
            }
        )
    return salida


def _precio_origen(
    session: Session,
    lista: models.ListaPrecios,
    precio: models.PrecioInsumo | None,
    origenes: Mapping[int, Any],
) -> dict[str, Any] | None:
    """El `precio_origen` de S1 (RF-65): moneda original, precio original, fecha, tasa con su
    fecha y su fuente, y si el precio es propio o heredado de la base."""
    if precio is None or precio.id not in origenes:
        return None
    o = origenes[precio.id]
    return {
        "moneda_original": o.moneda_original,
        "precio_original": texto_decimal(o.precio_original),
        "fecha_precio": o.fecha_precio.isoformat(),
        "tasa": texto_decimal(o.tasa),
        "fecha_tasa": o.fecha_tasa.isoformat() if o.fecha_tasa else None,
        "fuente_tasa": o.fuente_tasa,
        "fuente": o.fuente,
        "heredado": es_heredado(session, lista, precio),
    }


def _plan(session: Session, version: models.Presupuesto) -> list[dict[str, Any]]:
    filas = session.scalars(
        select(models.PlanVersion)
        .where(models.PlanVersion.presupuesto_id == version.id)
        .order_by(models.PlanVersion.periodo, models.PlanVersion.orden, models.PlanVersion.id)
    )
    return [
        {"periodo": f.periodo, "etiqueta": f.etiqueta, "orden": f.orden,
         "codigo_partida": f.codigo_partida, "fraccion": texto_decimal(f.fraccion)}
        for f in filas
    ]


def _hallazgos(session: Session, version: models.Presupuesto) -> list[dict[str, Any]]:
    filas = session.scalars(
        select(models.Hallazgo)
        .where(models.Hallazgo.presupuesto_id == version.id)
        .order_by(models.Hallazgo.id)
    )
    return [
        {"regla": h.regla, "severidad": h.severidad, "descripcion": h.descripcion,
         "impacto": texto_decimal(h.impacto), "origen_ids": json.loads(h.origen_ids),
         "valor_observado": texto_decimal(h.valor_observado),
         "valor_esperado": texto_decimal(h.valor_esperado)}
        for h in filas
    ]


# --- lectura --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RenglonDeclarado:
    """Lo que el emisor declaró para un renglón: se compara con el recálculo, no se cree."""

    orden: int
    codigo_partida: str
    cantidad: Decimal
    materiales: Decimal
    equipos: Decimal
    mano_obra: Decimal
    costo_directo: Decimal
    con_administracion: Decimal
    precio_unitario: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class LineaLeida:
    """Una línea de composición con lo que no cabe en el contrato: insumo, referencia, origen."""

    insumo: str | None
    referencia: str
    precio: Decimal
    precio_origen: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class DocumentoLeido:
    codigo: str
    fecha: date
    moneda: str
    moneda_proyecto: str | None
    proyecto: str
    parametros: ParametrosCosto
    lista: Mapping[str, Any]
    items: tuple[ItemComputo, ...]
    pendientes: tuple[ItemComputo, ...]
    declarados: tuple[RenglonDeclarado, ...]
    composiciones: Mapping[str, ComposicionAPU]
    lineas: Mapping[str, tuple[LineaLeida, ...]]
    plan: tuple[PeriodoPlan, ...] | None
    curva: tuple[PuntoCurva, ...]
    hallazgos: tuple[Hallazgo, ...]


def _dec(texto: object, donde: str) -> Decimal:
    if not isinstance(texto, str) or not PATRON_CIFRA.fullmatch(texto):
        raise DocumentoInvalido(f"{donde}: cifra fuera del patron estricto: {str(texto)[:30]!r}")
    return Decimal(texto)


def _dec_o_nulo(texto: object, donde: str) -> Decimal | None:
    return None if texto is None else _dec(texto, donde)


def _campo(objeto: Mapping[str, Any], clave: str, tipo: type, donde: str) -> Any:
    valor = objeto.get(clave)
    if not isinstance(valor, tipo):
        raise DocumentoInvalido(f"{donde}: falta '{clave}' o no es {tipo.__name__}")
    return valor


def contar_filas(objeto: Mapping[str, Any]) -> int:
    """Renglones más líneas de composición del documento, sin validarlo (para el límite de
    S3 §8.4 antes de leerlo entero)."""
    renglones = objeto.get("renglones")
    composiciones = objeto.get("composiciones")
    total = len(renglones) if isinstance(renglones, list) else 0
    if isinstance(composiciones, list):
        total += sum(
            len(c.get("lineas", ())) for c in composiciones if isinstance(c, dict)
            and isinstance(c.get("lineas", ()), list)
        )
    return total


def _contrato_item(datos: Mapping[str, Any], donde: str) -> ItemComputo:
    try:
        return ItemComputo(
            codigo_partida=_campo(datos, "codigo_partida", str, donde),
            descripcion=_campo(datos, "descripcion", str, donde),
            unidad=_campo(datos, "unidad", str, donde),
            cantidad=_dec(datos.get("cantidad"), f"{donde}.cantidad"),
            origen_id=_campo(datos, "origen_id", str, donde),
            origen_tipo=OrigenTipo(_campo(datos, "origen_tipo", str, donde)),
            dominio=Dominio(_campo(datos, "dominio", str, donde)),
            regla=datos.get("regla"),
            parametros={
                k: _dec(v, f"{donde}.parametros.{k}")
                for k, v in _campo(datos, "parametros", dict, donde).items()
            },
            especificaciones=_campo(datos, "especificaciones", dict, donde),
        )
    except (ValueError, TypeError) as error:
        if isinstance(error, DocumentoInvalido):
            raise
        raise DocumentoInvalido(f"{donde}: {error}") from None


def _composicion(datos: Mapping[str, Any]) -> tuple[ComposicionAPU, tuple[LineaLeida, ...]]:
    """La composición y los datos de sus líneas, alineados con `(*materiales, *equipos,
    *mano_obra)` (el orden de `ComposicionAPU`, como `_insumos_alineados` de S1)."""
    donde = f"composicion {datos.get('codigo_partida')!r}"
    materiales: list[tuple[LineaMaterial, LineaLeida]] = []
    equipos: list[tuple[LineaEquipo, LineaLeida]] = []
    mano_obra: list[tuple[LineaManoObra, LineaLeida]] = []
    for numero, linea in enumerate(_campo(datos, "lineas", list, donde)):
        aqui = f"{donde}, linea {numero}"
        tipo = _campo(linea, "tipo", str, aqui)
        cantidad = _dec(linea.get("cantidad"), f"{aqui}.cantidad")
        precio = _dec(linea.get("precio"), f"{aqui}.precio")
        descripcion = _campo(linea, "descripcion", str, aqui)
        extra = LineaLeida(
            linea.get("insumo"), linea.get("referencia", ""), precio, linea.get("precio_origen")
        )
        if tipo == models.TipoInsumo.MATERIAL:
            material = LineaMaterial(descripcion, linea.get("unidad") or "", cantidad, precio)
            materiales.append((material, extra))
        elif tipo == models.TipoInsumo.EQUIPO:
            dep = _dec(linea.get("depreciacion"), f"{aqui}.depreciacion")
            equipos.append((LineaEquipo(descripcion, cantidad, precio, dep), extra))
        elif tipo == models.TipoInsumo.MANO_OBRA:
            modalidad = linea.get("modalidad") or "jornal"
            mano_obra.append((LineaManoObra(descripcion, cantidad, precio, modalidad), extra))
        else:
            raise DocumentoInvalido(f"{aqui}: tipo de insumo desconocido {tipo!r}")
    composicion = ComposicionAPU(
        codigo_partida=_campo(datos, "codigo_partida", str, donde),
        descripcion=_campo(datos, "descripcion", str, donde),
        unidad=_campo(datos, "unidad", str, donde),
        rendimiento=_dec(datos.get("rendimiento"), f"{donde}.rendimiento"),
        materiales=tuple(m for m, _ in materiales),
        equipos=tuple(e for e, _ in equipos),
        mano_obra=tuple(o for o, _ in mano_obra),
    )
    return composicion, tuple(x for _, x in (*materiales, *equipos, *mano_obra))


def _plan_leido(filas: Sequence[Mapping[str, Any]]) -> tuple[PeriodoPlan, ...] | None:
    if not filas:
        return None
    periodos: dict[int, tuple[str, list[tuple[str, Decimal]]]] = {}
    for fila in filas:
        etiqueta, reparto = periodos.setdefault(fila["periodo"], (fila["etiqueta"], []))
        if fila.get("codigo_partida") is not None and fila.get("fraccion") is not None:
            reparto.append((fila["codigo_partida"], _dec(fila["fraccion"], "plan.fraccion")))
    return tuple((etiqueta, tuple(reparto)) for etiqueta, reparto in periodos.values())


def leer(objeto: Mapping[str, Any]) -> DocumentoLeido:
    """`DocumentoLeido` de un documento canónico ya leído; `DocumentoInvalido` si no tiene la
    forma de `silice-presupuesto` v1 o trae una cifra fuera del patrón estricto."""
    if not isinstance(objeto, Mapping) or objeto.get("formato") != FORMATO:
        raise DocumentoInvalido("no es un presupuesto de Silice (formato)")
    if objeto.get("version_formato") != VERSION_FORMATO:
        raise DocumentoInvalido(f"version_formato {objeto.get('version_formato')!r} desconocida")
    parametros = _campo(objeto, "parametros", dict, "parametros")
    renglones = _campo(objeto, "renglones", list, "documento")
    items, declarados = [], []
    for numero, renglon in enumerate(renglones):
        aqui = f"renglon {numero}"
        items.append(_contrato_item(_campo(renglon, "item", dict, aqui), f"{aqui}.item"))
        declarados.append(
            RenglonDeclarado(
                orden=_campo(renglon, "orden", int, aqui),
                codigo_partida=items[-1].codigo_partida,
                cantidad=_dec(renglon.get("cantidad"), f"{aqui}.cantidad"),
                materiales=_dec(renglon.get("materiales"), f"{aqui}.materiales"),
                equipos=_dec(renglon.get("equipos"), f"{aqui}.equipos"),
                mano_obra=_dec(renglon.get("mano_obra"), f"{aqui}.mano_obra"),
                costo_directo=_dec(renglon.get("costo_directo"), f"{aqui}.costo_directo"),
                con_administracion=_dec(
                    renglon.get("con_administracion"), f"{aqui}.con_administracion"
                ),
                precio_unitario=_dec(renglon.get("precio_unitario"), f"{aqui}.precio_unitario"),
                total=_dec(renglon.get("total"), f"{aqui}.total"),
            )
        )
    composiciones, lineas = {}, {}
    for datos in _campo(objeto, "composiciones", list, "documento"):
        composicion, extra = _composicion(datos)
        composiciones[composicion.codigo_partida] = composicion
        lineas[composicion.codigo_partida] = extra
    try:
        fecha = date.fromisoformat(_campo(objeto, "fecha", str, "documento"))
        costo = ParametrosCosto(
            fcas=_dec(parametros.get("fcas"), "parametros.fcas"),
            bono_alimentacion=_dec(parametros.get("bono_alimentacion"), "parametros.bono"),
            administracion=_dec(parametros.get("administracion"), "parametros.administracion"),
            utilidad=_dec(parametros.get("utilidad"), "parametros.utilidad"),
        )
    except (ValueError, InvalidOperation) as error:
        if isinstance(error, DocumentoInvalido):
            raise
        raise DocumentoInvalido(f"documento: {error}") from None
    return DocumentoLeido(
        codigo=_campo(objeto, "codigo", str, "documento"),
        fecha=fecha,
        moneda=_campo(objeto, "moneda", str, "documento"),
        moneda_proyecto=objeto.get("moneda_proyecto"),
        proyecto=_campo(objeto, "proyecto", str, "documento"),
        parametros=costo,
        lista=_campo(objeto, "lista", dict, "documento"),
        items=tuple(items),
        pendientes=tuple(
            _contrato_item(p, f"pendiente {n}")
            for n, p in enumerate(_campo(objeto, "pendientes", list, "documento"))
        ),
        declarados=tuple(declarados),
        composiciones=composiciones,
        lineas=lineas,
        plan=_plan_leido(_campo(objeto, "plan", list, "documento")),
        curva=tuple(
            PuntoCurva(
                periodo=_campo(p, "periodo", str, "curva"),
                monto=_dec(p.get("monto"), "curva.monto"),
                acumulado=_dec(p.get("acumulado"), "curva.acumulado"),
            )
            for p in _campo(objeto, "curva", list, "documento")
        ),
        hallazgos=tuple(
            Hallazgo(
                regla=_campo(h, "regla", str, "hallazgo"),
                severidad=Severidad(_campo(h, "severidad", int, "hallazgo")),
                descripcion=_campo(h, "descripcion", str, "hallazgo"),
                impacto=_dec_o_nulo(h.get("impacto"), "hallazgo.impacto"),
                origen_ids=tuple(h.get("origen_ids", ())),
                valor_observado=_dec_o_nulo(h.get("valor_observado"), "hallazgo.observado"),
                valor_esperado=_dec_o_nulo(h.get("valor_esperado"), "hallazgo.esperado"),
            )
            for h in _campo(objeto, "hallazgos", list, "documento")
        ),
    )
```
- [ ] **Paso 4: Correrla y ver el verde** (y la suite del módulo)
Run: `uv run pytest tests/integration/test_canonico.py tests/unit/test_documentos_s3_0.py -v -W
error` → verde. Run: `uv run python scripts/guardia_nucleo.py --base origin/main` → 0; `uv run ruff
check core/budget/canonico.py tests/fixtures/canonico_minimo.py` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/canonico.py
git commit -m "feat(nucleo): documento canonico de una version y su lectura estricta (SL-E8)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 8: SL-E7 — cadena de huellas sellada en el embudo

**Rama:** `inc/080-s3-2-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/models/cadena.py`, `core/budget/cadena.py`,
  `migraciones/caso/versions/caso_0007_s3_cadena.py`
- Modificar: `core/models/__init__.py:8,55`, `core/budget/persistencia.py:38,119-150,226`,
  `core/budget/cotizacion.py:116,160,253,305`, `core/budget/actualizacion.py:135,234`,
  `core/budget/edicion.py:136,196`, `core/budget/importacion.py:175,244`
- Modificar (scripts, que ahora pasan `usuario`): `scripts/probar_precios_maprex.py`,
  `scripts/seed_demo.py`, `scripts/medir_rnf03.py`, `scripts/generar_resultados_ml.py`
- Modificar (pruebas): `tests/conftest.py:84,115-150`, `pyproject.toml:73-78`,
  `tests/fixtures/canonico_minimo.py`
- Prueba: `tests/integration/test_cadena.py`

**Interfaces:**
- Consume: `core.budget.canonico.{documento, json_canonico, huella}` (tarea 7),
  `core.models.RegistroCambio`, `core.models.Presupuesto`.
- Produce:
  - `core.budget.cadena`: `def anexos_ninguno(session: Session, version: models.Presupuesto) ->
      Mapping[str, bytes]`
  - `core.budget.cadena`: `class SelladoSinUsuario(ValueError)`
  - `core.budget.cadena`: `class SelladoEnConflicto(RuntimeError)`
  - `core.budget.cadena`: `class FalloDeCadena`
  - `core.budget.cadena`: `class ResultadoCadena`
  - `core.budget.cadena`: `def fila_de_cambio(registro: models.RegistroCambio) -> list[str]`
  - `core.budget.cadena`: `def huella_de_filas_de_cambios(filas: Sequence[Sequence[str]]) -> str`
  - `core.budget.cadena`: `def huella_de_cambios(registros: Sequence[models.RegistroCambio]) ->
      str`
  - `core.budget.cadena`: `def huella_de_anexos(anexos: Mapping[str, bytes]) -> str`
  - `core.budget.cadena`: `def huella_del_eslabon(*, anterior: str, codigo: str, contenido: str,
      cambios: str, anexos: str, usuario: str, fecha_hora: datetime, tipo: str, version_formato:
      int) -> str`
  - `core.budget.cadena`: `def eslabones_de(session: Session, proyecto: models.Proyecto) ->
      list[EslabonVersion]`
  - `core.budget.cadena`: `def sellar_version(session: Session, version: models.Presupuesto,
      usuario: str, *, anexos_de: AnexosDe=anexos_ninguno, tipo: str='normal', ahora: datetime |
      None=None) -> EslabonVersion`
  - `core.budget.cadena`: `def anexos_por_omision(session: Session, anexos_de: AnexosDe) ->
      Session`
  - `core.budget.cadena`: `def marcar_por_sellar(session: Session, version: models.Presupuesto,
      usuario: str | None, anexos_de: AnexosDe | None=None) -> None`
  - `core.budget.cadena`: `def sellar_historial(session: Session, usuario: str, *, anexos_de:
      AnexosDe=anexos_ninguno, ahora: datetime | None=None) -> tuple[str, ...]`
  - `core.budget.cadena`: `def texto_retroactivo(session: Session, proyecto: models.Proyecto) ->
      str | None`
  - `core.budget.cadena`: `def mensaje_de_cadena(resultado: ResultadoCadena) -> str`
  - `core.budget.cadena`: `def verificar_cadena(session: Session, proyecto: models.Proyecto, *,
      anexos_de: AnexosDe=anexos_ninguno) -> ResultadoCadena`
  - `core.models.cadena.EslabonVersion` (tabla `eslabon_version`, índice único
    `(proyecto_id, anterior)`).
  - `guardar_presupuesto(..., usuario: str | None = None, anexos_de: AnexosDe | None = None)`.
  - La revisión `caso_0007_s3_cadena` (cuelga de `caso_0006_s2_decision`).

**Qué se encadena y dónde se sella.** `guardar_presupuesto` es el único embudo de versiones: solo
marca la versión como «por sellar» (`marcar_por_sellar`). Al confirmar la transacción **raíz**, un
evento `before_commit` escribe el eslabón en esa misma transacción: la huella del documento
canónico, la de sus `RegistroCambio`, la de sus anexos y la del eslabón anterior del proyecto
(64 ceros en el génesis). Un `commit` sin `usuario` falla con `SelladoSinUsuario` y no escribe
nada. Los savepoints no sellan. `verificar_cadena` **recalcula** cada huella desde la base y dice
la primera versión que no cuadra. Un proyecto de antes de S3 se sella una vez, con
`tipo = "retroactivo"` y a nombre de quien lo abre (RS3-5).

- [ ] **Paso 0: Antes del código** — el expediente SL-E7 está commiteado y aprobado.
- [ ] **Paso 1: Escribir la prueba que falla**
  La fixture de la tarea 7 gana `usuario` y `anexos_de`, que el embudo ahora recibe:
```diff
--- a/tests/fixtures/canonico_minimo.py
+++ b/tests/fixtures/canonico_minimo.py
@@ -61,17 +61,20 @@
 
 
-def guardar_otra(sesion, proyecto, lista, codigo: str, cantidad: str = "20", **opciones):
+def guardar_otra(
+    sesion, proyecto, lista, codigo: str, cantidad: str = "20", usuario: str | None = USUARIO,
+    **opciones,
+):
     """Otra versión del mismo relleno por el embudo; `opciones` van tal cual a
-    `guardar_presupuesto` (`version_origen`, `motivo`...)."""
+    `guardar_presupuesto` (`version_origen`, `motivo`, `anexos_de`...)."""
     resultado = _elaborar(codigo, cantidad)
     return guardar_presupuesto(
         sesion, resultado.presupuesto, resultado.informe, proyecto=proyecto, lista=lista,
-        parametros=PARAMETROS, pendientes=resultado.pendientes, **opciones,
+        parametros=PARAMETROS, pendientes=resultado.pendientes, usuario=usuario, **opciones,
     )
 
 
-def sembrar_minimo(sesion, **opciones):
+def sembrar_minimo(sesion, usuario: str | None = USUARIO, **opciones):
     """Devuelve `(proyecto, version, lista)`; la sesión queda con la transacción abierta.
-    `opciones` va al embudo."""
+    `opciones` va al embudo (p. ej. `anexos_de=`)."""
     lista = models.ListaPrecios(
         nombre="Lista de prueba", moneda="USD", fecha_vigencia=FECHA, origen="prueba"
@@ -81,5 +84,5 @@
     Catalogo(sesion).cargar_composicion(RELLENO, lista, Dominio.CIVIL, FECHA, "prueba")
     proyecto = crear_proyecto(sesion, "MIN-001", dominio=Dominio.CIVIL)
-    version = guardar_otra(sesion, proyecto, lista, "001", **opciones)
+    version = guardar_otra(sesion, proyecto, lista, "001", usuario=usuario, **opciones)
     return proyecto, version, lista
 
```
**`tests/integration/test_cadena.py`**
```python
"""SL-E7: el registro encadenado, sellado en el embudo al confirmar (RF-83; spec S3 §6.2 a §6.5)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import text

from core import models
from core.budget import cadena
from core.budget.cadena import GENESIS
from core.catalog import abrir_sesion
from core.models.cadena import EslabonVersion
from tests.fixtures.canonico.ejemplo_v1 import HUELLA_EJEMPLO_V1
from tests.fixtures.canonico_minimo import USUARIO, guardar_otra, registro, sembrar_minimo


@pytest.fixture
def sesion(motor):
    with abrir_sesion(motor) as sesion:
        yield sesion


def _tres_versiones(sesion):
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", "30", version_origen=v1, motivo="edicion")
    sesion.add(registro(proyecto, v1, v2))
    sesion.commit()
    v3 = guardar_otra(sesion, proyecto, lista, "003", "35", version_origen=v2, motivo="edicion")
    sesion.add(registro(proyecto, v2, v3, campo="precio"))
    sesion.commit()
    return proyecto, (v1, v2, v3), lista


def _anexo_a(sesion, version):
    """Como `ui.entrega.anexos_de_cadena`: solo las versiones que tienen espacio traen anexo."""
    return {"anexos/espacio.json": b'{"ambientes":[]}'} if version.codigo == "002" else {}


def test_la_version_se_sella_al_confirmar_y_no_antes(sesion) -> None:
    proyecto, v1, _ = sembrar_minimo(sesion)
    assert sesion.get(EslabonVersion, v1.id) is None  # el embudo solo la marcó
    sesion.commit()
    eslabon = sesion.get(EslabonVersion, v1.id)
    assert eslabon.anterior == GENESIS and eslabon.usuario == USUARIO and eslabon.tipo == "normal"
    assert eslabon.huella_contenido == HUELLA_EJEMPLO_V1  # el contenido encadenado es el vector
    assert eslabon.huella_cambios == eslabon.huella_anexos == cadena.huella_de_cambios([])
    assert len(eslabon.huella_eslabon) == 64 != eslabon.huella_contenido


@pytest.mark.sin_usuario_por_omision
def test_confirmar_sin_usuario_se_rechaza_y_no_se_escribe_nada(sesion) -> None:
    sembrar_minimo(sesion, usuario=None)
    with pytest.raises(cadena.SelladoSinUsuario, match="sin usuario"):
        sesion.commit()
    sesion.rollback()
    assert sesion.query(models.Presupuesto).count() == 0
    assert sesion.query(EslabonVersion).count() == 0


@pytest.mark.sin_usuario_por_omision
def test_un_usuario_en_blanco_tampoco_vale(sesion) -> None:
    sembrar_minimo(sesion, usuario="   ")
    with pytest.raises(cadena.SelladoSinUsuario):
        sesion.commit()
    sesion.rollback()


@pytest.mark.sin_usuario_por_omision
def test_el_rollback_olvida_las_versiones_pendientes(sesion) -> None:
    sembrar_minimo(sesion, usuario=None)
    sesion.rollback()
    sesion.commit()  # sin pendientes: ya no exige usuario
    assert sesion.query(EslabonVersion).count() == 0


def test_un_savepoint_no_sella_pero_la_transaccion_raiz_si(sesion) -> None:
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    with sesion.begin_nested():
        v2 = guardar_otra(sesion, proyecto, lista, "002", version_origen=v1, motivo="edicion")
    assert sesion.get(EslabonVersion, v2.id) is None  # liberar el SAVEPOINT no sella
    sesion.add(registro(proyecto, v1, v2))  # llega DESPUÉS del embudo y entra a la huella
    sesion.commit()
    eslabon = sesion.get(EslabonVersion, v2.id)
    registro_de_v2 = sesion.query(models.RegistroCambio).filter_by(
        version_resultante_id=v2.id).one()
    assert eslabon.huella_cambios == cadena.huella_de_cambios([registro_de_v2])


def test_la_cadena_es_lineal_desde_el_genesis(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    e1, e2, e3 = (sesion.get(EslabonVersion, v.id) for v in (v1, v2, v3))
    assert (e1.anterior, e2.anterior, e3.anterior) == (
        GENESIS, e1.huella_eslabon, e2.huella_eslabon)
    ids = [e.presupuesto_id for e in cadena.eslabones_de(sesion, proyecto)]
    assert ids == [v1.id, v2.id, v3.id]
    resultado = cadena.verificar_cadena(sesion, proyecto)
    assert resultado.integra and resultado.versiones == 3
    assert cadena.mensaje_de_cadena(resultado) == "Cadena íntegra: 3 versiones"


def test_cada_proyecto_tiene_su_propio_genesis(sesion) -> None:
    proyecto, (v1, _, _), lista = _tres_versiones(sesion)
    otro = models.Proyecto(nombre="OTRO", descripcion="", dominio="civil")
    sesion.add(otro)
    sesion.flush()
    v = guardar_otra(sesion, otro, lista, "001")
    sesion.commit()
    assert sesion.get(EslabonVersion, v.id).anterior == GENESIS


def test_los_registros_de_cambio_entran_a_la_huella_aunque_lleguen_despues_del_embudo(sesion):
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", version_origen=v1, motivo="edicion")
    sesion.add(registro(proyecto, v1, v2))
    sesion.commit()
    sin_registros = cadena.huella_de_cambios([])
    assert sesion.get(EslabonVersion, v1.id).huella_cambios == sin_registros
    assert sesion.get(EslabonVersion, v2.id).huella_cambios != sin_registros


@pytest.mark.parametrize("motivo", [None, *models.MOTIVOS_VERSION])
def test_todo_motivo_de_version_y_el_motivo_vacio_quedan_sellados(sesion, motivo) -> None:
    """RV-7: la invariante no depende de una lista de caminos, sino del embudo."""
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    opciones = {} if motivo is None else {"version_origen": v1, "motivo": motivo}
    v2 = guardar_otra(sesion, proyecto, lista, "002", **opciones)
    sesion.commit()
    assert sesion.get(EslabonVersion, v2.id) is not None
    assert cadena.verificar_cadena(sesion, proyecto).integra


def _romper(sesion, sentencia: str, **parametros) -> None:
    sesion.execute(text(sentencia), parametros)
    sesion.commit()


def test_un_byte_cambiado_en_el_contenido_rompe_la_cadena_en_esa_version(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(sesion, "UPDATE partida_presupuestada SET cantidad = '31' WHERE presupuesto_id = :v",
            v=v2.id)
    sesion.expire_all()
    resultado = cadena.verificar_cadena(sesion, proyecto)
    assert not resultado.integra and resultado.fallo.codigo_version == "002"
    assert resultado.fallo.motivo == "contenido" and resultado.versiones == 1
    assert "Cadena rota en la versión 002" in cadena.mensaje_de_cadena(resultado)
    assert "Revíselo con el administrador" in cadena.mensaje_de_cadena(resultado)


def test_un_registro_de_cambio_alterado_rompe_la_cadena(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(sesion, "UPDATE registro_cambio SET valor_nuevo = '9' WHERE version_resultante_id = :v",
            v=v3.id)
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("003", "registro")


def test_un_anexo_alterado_rompe_la_cadena(sesion) -> None:
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", anexos_de=_anexo_a)
    sesion.commit()
    assert cadena.verificar_cadena(sesion, proyecto, anexos_de=_anexo_a).integra
    alterado = {"anexos/espacio.json": b'{"ambientes":[1]}'}
    fallo = cadena.verificar_cadena(
        sesion, proyecto, anexos_de=lambda s, v: alterado if v.codigo == "002" else {}
    ).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("002", "anexo")
    assert v2.id != v1.id


def test_un_eslabon_alterado_rompe_la_cadena(sesion) -> None:
    proyecto, (v1, v2, _), _ = _tres_versiones(sesion)
    _romper(sesion, "UPDATE eslabon_version SET usuario = 'otra persona' WHERE presupuesto_id = :v",
            v=v1.id)
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("001", "eslabon")


def test_una_version_posterior_al_genesis_sin_eslabon_es_un_error_de_cadena(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(sesion, "DELETE FROM eslabon_version WHERE presupuesto_id = :v", v=v2.id)
    sesion.expire_all()
    fallo = cadena.verificar_cadena(sesion, proyecto).fallo
    assert (fallo.codigo_version, fallo.motivo) == ("002", "sin_sellar")


def test_el_indice_unico_impide_que_dos_versiones_cuelguen_del_mismo_eslabon(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    e2 = sesion.get(EslabonVersion, v2.id)
    sesion.add(EslabonVersion(
        presupuesto_id=v3.id + 1000, proyecto_id=proyecto.id, anterior=e2.anterior,
        huella_contenido="a" * 64, huella_cambios="b" * 64, huella_anexos="c" * 64,
        huella_eslabon="d" * 64, usuario="x", fecha_hora=datetime(2026, 1, 1), tipo="normal",
        version_formato=1))
    with pytest.raises(Exception, match="FOREIGN KEY|UNIQUE"):
        sesion.flush()
    sesion.rollback()


def test_el_sellado_retroactivo_cubre_lo_anterior_y_se_declara(sesion) -> None:
    proyecto, (v1, v2, v3), _ = _tres_versiones(sesion)
    _romper(sesion, "DELETE FROM eslabon_version")  # bases anteriores a S3: sin eslabones
    sesion.expire_all()
    assert cadena.verificar_cadena(sesion, proyecto).fallo.motivo == "sin_sellar"
    cuando = datetime(2026, 11, 3, 8, 30)
    selladas = cadena.sellar_historial(sesion, "Admin <admin>", ahora=cuando)
    sesion.commit()
    assert selladas == ("MIN-001/001", "MIN-001/002", "MIN-001/003")
    assert {e.tipo for e in cadena.eslabones_de(sesion, proyecto)} == {"retroactivo"}
    assert cadena.verificar_cadena(sesion, proyecto).integra
    assert cadena.texto_retroactivo(sesion, proyecto) == (
        "Versiones 001 a 003 selladas el 2026-11-03: prueban que no cambiaron desde esa fecha; "
        "antes no hay garantía."
    )
    assert cadena.sellar_historial(sesion, "Admin <admin>", ahora=cuando) == ()  # una sola vez


def test_guardar_en_un_proyecto_de_antes_de_s3_sella_primero_lo_anterior_como_retroactivo(
    sesion,
) -> None:
    """La API y los scripts también guardan: la cadena no queda con huecos (S3 §6.5)."""
    proyecto, (v1, v2, v3), lista = _tres_versiones(sesion)
    ids = (v1.id, v2.id, v3.id)
    _romper(sesion, "DELETE FROM eslabon_version")  # el proyecto viene de antes de S3
    sesion.expire_all()
    proyecto = sesion.get(models.Proyecto, proyecto.id)
    lista = sesion.get(models.ListaPrecios, lista.id)
    v3 = sesion.get(models.Presupuesto, ids[2])
    v4 = guardar_otra(sesion, proyecto, lista, "004", "40", version_origen=v3, motivo="edicion")
    sesion.commit()
    tipos = {e.presupuesto_id: e.tipo for e in cadena.eslabones_de(sesion, proyecto)}
    assert tipos == {ids[0]: "retroactivo", ids[1]: "retroactivo", ids[2]: "retroactivo",
                     v4.id: "normal"}
    assert cadena.verificar_cadena(sesion, proyecto).integra
    assert cadena.texto_retroactivo(sesion, proyecto).startswith("Versiones 001 a 003 selladas")


def test_dos_versiones_nuevas_en_la_misma_transaccion_no_se_sellan_como_retroactivas(
    sesion,
) -> None:
    proyecto, v1, lista = sembrar_minimo(sesion)
    v2 = guardar_otra(sesion, proyecto, lista, "002", "30", version_origen=v1, motivo="edicion")
    sesion.commit()
    assert [e.tipo for e in cadena.eslabones_de(sesion, proyecto)] == ["normal", "normal"]
    assert v2.id > v1.id and cadena.verificar_cadena(sesion, proyecto).integra


def test_la_sesion_fija_el_proveedor_de_anexos_de_todo_lo_que_guarda(sesion) -> None:
    """Las pantallas que escriben `esp_*` con la versión no tienen que pasar `anexos_de` en cada
    llamada al embudo: la sesión lo trae (`anexos_por_omision`)."""
    cadena.anexos_por_omision(sesion, _anexo_a)
    proyecto, v1, lista = sembrar_minimo(sesion)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", "30", version_origen=v1, motivo="edicion")
    sesion.add(registro(proyecto, v1, v2))
    sesion.commit()
    assert cadena.verificar_cadena(sesion, proyecto, anexos_de=_anexo_a).integra
    sin = cadena.verificar_cadena(sesion, proyecto)  # el verificador sin proveedor no ve el anexo
    assert not sin.integra and sin.fallo.motivo == "anexo" and sin.fallo.codigo_version == "002"


def test_sin_versiones_retroactivas_no_hay_declaracion(sesion) -> None:
    proyecto, _, _ = _tres_versiones(sesion)
    assert cadena.texto_retroactivo(sesion, proyecto) is None


def test_sellar_dos_veces_la_misma_version_es_un_error(sesion) -> None:
    _, v1, _ = sembrar_minimo(sesion)
    sesion.commit()
    with pytest.raises(ValueError, match="ya esta sellada"):
        cadena.sellar_version(sesion, v1, USUARIO)
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_cadena.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'core.budget.cadena'`.
```bash
git add tests/fixtures/canonico_minimo.py tests/integration/test_cadena.py
git commit -m "test(nucleo): cadena de huellas sellada al confirmar, en rojo (SL-E7)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  La tabla y su revisión (RP8-16: `crear_o_verificar` y `TablaCongelada`, porque `preparar_base`
  puede llegar a una base creada con `create_all`):
**`core/models/cadena.py`**
```python
"""SL-E7: el registro encadenado con huellas (spec S3 §6.2 y §7.4). Tabla aditiva.

Módulo propio, reexportado desde `core.models` (archivos calientes, maestro §3.2). Una fila por
versión: encadena su contenido, sus `RegistroCambio`, sus anexos y el eslabón anterior **del
mismo proyecto**. El índice único (`proyecto_id`, `anterior`) es la salvaguarda de la
concurrencia (S3 §6.3): dos versiones no pueden colgar del mismo eslabón.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base

#: Tipos de sellado: `retroactivo` es el de las versiones que ya existían al abrir el caso con S3.
TIPOS_DE_ESLABON = ("normal", "retroactivo")


class EslabonVersion(Base):
    """SL-E7: el eslabón de una versión. Solo-agregar: ninguna función de `core` lo actualiza."""

    __tablename__ = "eslabon_version"
    __table_args__ = (
        Index("uq_eslabon_proyecto_anterior", "proyecto_id", "anterior", unique=True),
    )

    presupuesto_id: Mapped[int] = mapped_column(
        ForeignKey("presupuesto.id", ondelete="CASCADE"), primary_key=True
    )
    proyecto_id: Mapped[int] = mapped_column(ForeignKey("proyecto.id", ondelete="CASCADE"))
    anterior: Mapped[str] = mapped_column(String(64))  # huella_eslabon previa; génesis: 64 ceros
    huella_contenido: Mapped[str] = mapped_column(String(64))
    huella_cambios: Mapped[str] = mapped_column(String(64))
    huella_anexos: Mapped[str] = mapped_column(String(64))
    huella_eslabon: Mapped[str] = mapped_column(String(64))
    usuario: Mapped[str] = mapped_column(String(120))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    tipo: Mapped[str] = mapped_column(String(12))
    version_formato: Mapped[int] = mapped_column(Integer)
```
**`migraciones/caso/versions/caso_0007_s3_cadena.py`**
```python
"""S3-2 (SL-E7): `eslabon_version`, el registro encadenado con huellas (spec S3 §6.2 y §7.4).

Tabla aditiva de `core/models/cadena.py`: una fila por versión con la huella de su contenido, de sus
`RegistroCambio`, de sus anexos y del eslabón anterior **del mismo proyecto**. El índice único
(`proyecto_id`, `anterior`) es la salvaguarda de la concurrencia (S3 §6.3). Ninguna tabla existente
cambia. Se escribe con `crear_o_verificar` (regla de S5-1): las bases que los `scripts/seed*.py` y
las pruebas crean con `create_all` ya la traen y se adoptan sin error. Las versiones que ya
existían se sellan después, una vez y de forma retroactiva y declarada
(`core.budget.cadena.sellar_historial`), no aquí: una migración no inventa quién las guardó.
"""

from alembic import op

from migraciones.comun import TablaCongelada, borrar_tablas, crear_o_verificar

revision = "caso_0007_s3_cadena"
down_revision = "caso_0006_s2_decision"
branch_labels = None
depends_on = None

TABLAS = (
    TablaCongelada(
        nombre="eslabon_version",
        ddl=(
            "CREATE TABLE eslabon_version (\n"
            "\tpresupuesto_id INTEGER NOT NULL, \n"
            "\tproyecto_id INTEGER NOT NULL, \n"
            "\tanterior VARCHAR(64) NOT NULL, \n"
            "\thuella_contenido VARCHAR(64) NOT NULL, \n"
            "\thuella_cambios VARCHAR(64) NOT NULL, \n"
            "\thuella_anexos VARCHAR(64) NOT NULL, \n"
            "\thuella_eslabon VARCHAR(64) NOT NULL, \n"
            "\tusuario VARCHAR(120) NOT NULL, \n"
            "\tfecha_hora DATETIME NOT NULL, \n"
            "\ttipo VARCHAR(12) NOT NULL, \n"
            "\tversion_formato INTEGER NOT NULL, \n"
            "\tPRIMARY KEY (presupuesto_id), \n"
            "\tFOREIGN KEY(presupuesto_id) REFERENCES presupuesto (id) ON DELETE CASCADE, \n"
            "\tFOREIGN KEY(proyecto_id) REFERENCES proyecto (id) ON DELETE CASCADE\n"
            ")"
        ),
        indices=(
            "CREATE UNIQUE INDEX uq_eslabon_proyecto_anterior "
            "ON eslabon_version (proyecto_id, anterior)",
        ),
    ),
)

def upgrade() -> None:
    crear_o_verificar(op.get_bind(), TABLAS)


def downgrade() -> None:
    borrar_tablas(op.get_bind(), TABLAS)
```
  `core/models/__init__.py` exporta la tabla:
```python
from core.models.cadena import EslabonVersion  # junto a las demás importaciones
# y en __all__, en orden alfabético:  "EslabonVersion",
```
  El sellado, la verificación y el sellado retroactivo:
**`core/budget/cadena.py`**
```python
"""SL-E7: el registro encadenado con huellas SHA-256 (spec S3 §6.2 a §6.5; maestro §3.2, RV-7).

Cada versión lleva un eslabón que encadena su contenido, sus `RegistroCambio`, sus anexos y el
eslabón anterior del mismo proyecto:

    huella_contenido = SHA-256(documento canónico, SL-E8)
    huella_cambios   = SHA-256(JSON canónico de sus RegistroCambio, en orden de id)
    huella_anexos    = SHA-256(JSON canónico de [[nombre, SHA-256(bytes)], ...] ordenado)
    huella_eslabon   = SHA-256(JSON canónico de {anterior, codigo, contenido, cambios, anexos,
                                usuario, fecha_hora, tipo, version_formato})

**Sellado en el embudo.** No depende de una lista de caminos: `guardar_presupuesto` (el único
embudo) llama a `marcar_por_sellar`, y un evento `before_commit` de la sesión sella cada versión
pendiente en la MISMA transacción, cuando ya existen sus `RegistroCambio` y su gancho (la hoja
copia `esp_*` después del embudo). Una versión pendiente sin `usuario` impide confirmar
(`SelladoSinUsuario`; nada se escribe: el llamador hace `rollback`). El `commit` de un SAVEPOINT
no sella; el de la transacción raíz, sí. Un `rollback` olvida lo pendiente.

**Anexos.** `core` no interpreta los anexos de una versión: los da una función inyectada
(`anexos_de`), que corre al sellar y al verificar con las mismas reglas (hoy, el espacio `esp_*`,
que arma `ui.entrega.anexos_de_cadena`). Las entradas de S1 y S2 que viajan en el paquete NO
entran a la cadena: llevan su propia huella (límite declarado, S3 §8.1).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import models
from core.budget import canonico
from core.models.cadena import TIPOS_DE_ESLABON, EslabonVersion

__all__ = [
    "anexos_ninguno",
    "anexos_por_omision",
    "GENESIS",
    "FalloDeCadena",
    "ResultadoCadena",
    "SelladoEnConflicto",
    "SelladoSinUsuario",
    "eslabones_de",
    "fila_de_cambio",
    "huella_de_anexos",
    "huella_de_cambios",
    "huella_de_filas_de_cambios",
    "huella_del_eslabon",
    "marcar_por_sellar",
    "mensaje_de_cadena",
    "sellar_historial",
    "sellar_version",
    "texto_retroactivo",
    "verificar_cadena",
]

GENESIS = "0" * 64
CLAVE_PENDIENTES = "silice_por_sellar"
CLAVE_ANEXOS = "silice_anexos_de"  # el proveedor de anexos de la sesión (S3 §6.2)

#: `anexos_de(session, version) -> {nombre: bytes}`. Lo que da la versión y `core` no interpreta.
AnexosDe = Callable[[Session, models.Presupuesto], Mapping[str, bytes]]


def anexos_ninguno(session: Session, version: models.Presupuesto) -> Mapping[str, bytes]:
    """El proveedor de anexos por omisión: la versión no trae ninguno."""
    return {}


class SelladoSinUsuario(ValueError):  # noqa: N818
    """Se intentó confirmar una versión sin `usuario`: nada se escribe (S3 §6.2, punto 3)."""


class SelladoEnConflicto(RuntimeError):  # noqa: N818
    """Otra transacción selló antes sobre el mismo eslabón: el borrador sigue en la pestaña."""


@dataclass(frozen=True, slots=True)
class FalloDeCadena:
    codigo_version: str
    motivo: str  # contenido | registro | anexo | eslabon | sin_sellar
    mensaje: str


@dataclass(frozen=True, slots=True)
class ResultadoCadena:
    integra: bool
    versiones: int
    fallo: FalloDeCadena | None = None


# --- huellas ---------------------------------------------------------------------------------


def _sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def fila_de_cambio(registro: models.RegistroCambio) -> list[str]:
    """Los ocho campos de un `RegistroCambio` que entran a la huella, en su orden."""
    return [
        registro.objeto, registro.clave, registro.campo, registro.valor_anterior,
        registro.valor_nuevo, registro.fuente, registro.responsable,
        registro.fecha_hora.isoformat(),
    ]


def huella_de_filas_de_cambios(filas: Sequence[Sequence[str]]) -> str:
    """La misma huella a partir de las filas ya extraídas: la usa el verificador del paquete,
    que solo tiene el JSON de `cadena.json` y no la base del emisor."""
    return _sha(canonico.json_canonico([list(fila) for fila in filas]))


def huella_de_cambios(registros: Sequence[models.RegistroCambio]) -> str:
    return huella_de_filas_de_cambios([fila_de_cambio(r) for r in registros])


def huella_de_anexos(anexos: Mapping[str, bytes]) -> str:
    return _sha(canonico.json_canonico([[n, _sha(anexos[n])] for n in sorted(anexos)]))


def huella_del_eslabon(
    *,
    anterior: str,
    codigo: str,
    contenido: str,
    cambios: str,
    anexos: str,
    usuario: str,
    fecha_hora: datetime,
    tipo: str,
    version_formato: int,
) -> str:
    return _sha(
        canonico.json_canonico(
            {
                "anterior": anterior, "codigo": codigo, "contenido": contenido,
                "cambios": cambios, "anexos": anexos, "usuario": usuario,
                "fecha_hora": fecha_hora.isoformat(), "tipo": tipo,
                "version_formato": version_formato,
            }
        )
    )


def _registros(session: Session, version: models.Presupuesto) -> list[models.RegistroCambio]:
    return list(
        session.scalars(
            select(models.RegistroCambio)
            .where(models.RegistroCambio.version_resultante_id == version.id)
            .order_by(models.RegistroCambio.id)
        )
    )


# --- sellar ----------------------------------------------------------------------------------


def eslabones_de(session: Session, proyecto: models.Proyecto) -> list[EslabonVersion]:
    """Los eslabones del proyecto en el orden de sus versiones."""
    return list(
        session.scalars(
            select(EslabonVersion)
            .where(EslabonVersion.proyecto_id == proyecto.id)
            .order_by(EslabonVersion.presupuesto_id)
        )
    )


def _cabeza(session: Session, proyecto_id: int) -> str:
    """La `huella_eslabon` del último eslabón del proyecto (génesis si no hay)."""
    eslabones = list(
        session.scalars(select(EslabonVersion).where(EslabonVersion.proyecto_id == proyecto_id))
    )
    if not eslabones:
        return GENESIS
    referidas = {e.anterior for e in eslabones}
    cabezas = [e.huella_eslabon for e in eslabones if e.huella_eslabon not in referidas]
    if len(cabezas) != 1:
        raise SelladoEnConflicto("La cadena del proyecto se bifurcó: revise con el administrador.")
    return cabezas[0]


def sellar_version(
    session: Session,
    version: models.Presupuesto,
    usuario: str,
    *,
    anexos_de: AnexosDe = anexos_ninguno,
    tipo: str = "normal",
    ahora: datetime | None = None,
) -> EslabonVersion:
    """Escribe el eslabón de `version` en la transacción en curso (no confirma)."""
    if not usuario or not usuario.strip():
        raise SelladoSinUsuario("Falta el usuario: toda versión se confirma a nombre de alguien.")
    if tipo not in TIPOS_DE_ESLABON:
        raise ValueError(f"tipo de eslabon desconocido: {tipo!r}")
    session.flush()
    if session.get(EslabonVersion, version.id) is not None:
        raise ValueError(f"La version {version.codigo} ya esta sellada.")
    anterior = _cabeza(session, version.proyecto_id)
    contenido = canonico.huella(canonico.documento(session, version))
    cambios = huella_de_cambios(_registros(session, version))
    anexos = huella_de_anexos(anexos_de(session, version))
    fecha_hora = ahora or datetime.now()
    eslabon = EslabonVersion(
        presupuesto_id=version.id, proyecto_id=version.proyecto_id, anterior=anterior,
        huella_contenido=contenido, huella_cambios=cambios, huella_anexos=anexos,
        huella_eslabon=huella_del_eslabon(
            anterior=anterior, codigo=version.codigo, contenido=contenido, cambios=cambios,
            anexos=anexos, usuario=usuario, fecha_hora=fecha_hora, tipo=tipo,
            version_formato=canonico.VERSION_FORMATO,
        ),
        usuario=usuario, fecha_hora=fecha_hora, tipo=tipo,
        version_formato=canonico.VERSION_FORMATO,
    )
    session.add(eslabon)
    try:
        session.flush()
    except IntegrityError as error:
        raise SelladoEnConflicto(
            "Otra persona guardó antes sobre la misma versión. Su borrador sigue aquí; "
            "vuelva a abrir la versión vigente y repita el cambio."
        ) from error
    return eslabon


def anexos_por_omision(session: Session, anexos_de: AnexosDe) -> Session:
    """Fija el proveedor de anexos de TODA versión que esta sesión guarde sin pasar el suyo.
    Quien arma la sesión de una pantalla que escribe `esp_*` junto con la versión lo llama una vez
    (`ui.entrega.con_anexos_de_cadena`): así la cadena cubre el espacio sin que cada llamador del
    embudo tenga que acordarse de pasar `anexos_de`."""
    session.info[CLAVE_ANEXOS] = anexos_de
    return session


def marcar_por_sellar(
    session: Session,
    version: models.Presupuesto,
    usuario: str | None,
    anexos_de: AnexosDe | None = None,
) -> None:
    """Lo llama `guardar_presupuesto`: la versión se sella al confirmar la transacción raíz."""
    proveedor = anexos_de or session.info.get(CLAVE_ANEXOS) or anexos_ninguno
    session.info.setdefault(CLAVE_PENDIENTES, []).append((version, usuario, proveedor))


def _sellar_pendientes(session: Session) -> None:
    pendientes = session.info.get(CLAVE_PENDIENTES)
    if not pendientes or session.in_nested_transaction():
        return
    session.info[CLAVE_PENDIENTES] = []  # antes de sellar: los flush de abajo no reentran
    session.flush()
    for version, usuario, _ in pendientes:
        if not usuario or not usuario.strip():
            raise SelladoSinUsuario(
                f"La version {version.codigo} se guardo sin usuario: no se puede confirmar."
            )
    en_curso = {version.id for version, _, _ in pendientes}
    for version, usuario, anexos_de in sorted(pendientes, key=lambda p: p[0].id):
        _sellar_anteriores_sin_eslabon(session, version, usuario, anexos_de, en_curso)
        sellar_version(session, version, usuario, anexos_de=anexos_de)


def _sellar_anteriores_sin_eslabon(
    session: Session, version: models.Presupuesto, usuario: str, anexos_de: AnexosDe,
    en_curso: set[int],
) -> None:
    """S3 §6.5: un proyecto con versiones de antes de S3 las sella primero, una vez, de forma
    retroactiva y en orden de `id`, para que la cadena no tenga huecos aunque el primer guardado
    no pase por la interfaz (la API y los scripts también guardan versiones)."""
    previas = sorted(
        (
            v for v in version.proyecto.presupuestos
            if v.id < version.id and v.id not in en_curso
            and session.get(EslabonVersion, v.id) is None
        ),
        key=lambda v: v.id,
    )
    for previa in previas:
        sellar_version(session, previa, usuario, anexos_de=anexos_de, tipo="retroactivo")


def _olvidar_pendientes(session: Session) -> None:
    session.info.pop(CLAVE_PENDIENTES, None)


if not event.contains(Session, "before_commit", _sellar_pendientes):
    event.listen(Session, "before_commit", _sellar_pendientes)
    event.listen(Session, "after_rollback", _olvidar_pendientes)


# --- historial y verificación ----------------------------------------------------------------


def sellar_historial(
    session: Session,
    usuario: str,
    *,
    anexos_de: AnexosDe = anexos_ninguno,
    ahora: datetime | None = None,
) -> tuple[str, ...]:
    """Sella, una vez y de forma declarada, las versiones que existían antes de S3: por
    proyecto y en orden de `id`, con `tipo = "retroactivo"`. Devuelve `proyecto/codigo` de cada
    una. No confirma. Una versión se puede sellar aunque ya no recargue: el documento sale de
    las filas."""
    ahora = ahora or datetime.now()
    selladas: list[str] = []
    for proyecto in session.scalars(select(models.Proyecto).order_by(models.Proyecto.id)):
        for version in sorted(proyecto.presupuestos, key=lambda v: v.id):
            if session.get(EslabonVersion, version.id) is None:
                sellar_version(
                    session, version, usuario, anexos_de=anexos_de, tipo="retroactivo", ahora=ahora
                )
                selladas.append(f"{proyecto.nombre}/{version.codigo}")
    return tuple(selladas)


def texto_retroactivo(session: Session, proyecto: models.Proyecto) -> str | None:
    """La declaración de S3 §6.5, o `None` si el proyecto no tiene versiones retroactivas."""
    versiones = {v.id: v for v in proyecto.presupuestos}
    retro = [e for e in eslabones_de(session, proyecto) if e.tipo == "retroactivo"]
    if not retro:
        return None
    codigos = [versiones[e.presupuesto_id].codigo for e in retro]
    rango = codigos[0] if len(codigos) == 1 else f"{codigos[0]} a {codigos[-1]}"
    cuando = min(e.fecha_hora for e in retro).date().isoformat()
    plural = "Versión" if len(codigos) == 1 else "Versiones"
    return (
        f"{plural} {rango} selladas el {cuando}: prueban que no cambiaron desde esa fecha; "
        "antes no hay garantía."
    )


_MOTIVOS = {
    "contenido": "su contenido no coincide con su huella",
    "registro": "su registro de cambios no coincide con su huella",
    "anexo": "uno de sus anexos no coincide con su huella",
    "eslabon": "su eslabón no coincide con el anterior o con su propia huella",
    "sin_sellar": "no tiene eslabón",
}


def mensaje_de_cadena(resultado: ResultadoCadena) -> str:
    """El texto de la pestaña Trazabilidad y de la entrega (S3 §6.4)."""
    if resultado.integra:
        return f"Cadena íntegra: {resultado.versiones} versiones"
    fallo = resultado.fallo
    assert fallo is not None
    return (
        f"Cadena rota en la versión {fallo.codigo_version}: {_MOTIVOS[fallo.motivo]}; alguien "
        "cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un "
        "paquete."
    )


def verificar_cadena(
    session: Session, proyecto: models.Proyecto, *, anexos_de: AnexosDe = anexos_ninguno
) -> ResultadoCadena:
    """RECALCULA cada huella desde la base y devuelve el primer fallo."""
    versiones = sorted(proyecto.presupuestos, key=lambda v: v.id)
    por_version = {e.presupuesto_id: e for e in eslabones_de(session, proyecto)}
    anterior = GENESIS
    for numero, version in enumerate(versiones):
        eslabon = por_version.get(version.id)
        if eslabon is None:
            return _roto(numero, version, "sin_sellar")
        contenido = canonico.huella(canonico.documento(session, version))
        cambios = huella_de_cambios(_registros(session, version))
        anexos = huella_de_anexos(anexos_de(session, version))
        if contenido != eslabon.huella_contenido:
            return _roto(numero, version, "contenido")
        if cambios != eslabon.huella_cambios:
            return _roto(numero, version, "registro")
        if anexos != eslabon.huella_anexos:
            return _roto(numero, version, "anexo")
        esperado = huella_del_eslabon(
            anterior=eslabon.anterior, codigo=version.codigo, contenido=contenido,
            cambios=cambios, anexos=anexos, usuario=eslabon.usuario,
            fecha_hora=eslabon.fecha_hora, tipo=eslabon.tipo,
            version_formato=eslabon.version_formato,
        )
        if eslabon.anterior != anterior or esperado != eslabon.huella_eslabon:
            return _roto(numero, version, "eslabon")
        anterior = eslabon.huella_eslabon
    return ResultadoCadena(True, len(versiones))


def _roto(numero: int, version: models.Presupuesto, motivo: str) -> ResultadoCadena:
    fallo = FalloDeCadena(version.codigo, motivo, _MOTIVOS[motivo])
    return ResultadoCadena(False, numero, fallo)
```
  El embudo marca la versión «por sellar» y recibe `usuario` y `anexos_de`:
```diff
--- a/core/budget/persistencia.py
+++ b/core/budget/persistencia.py
@@ -38,4 +38,5 @@
 from core import models
 from core.budget._modelo import _buscar, _parametros_de, _sesion_de
+from core.budget.cadena import AnexosDe, marcar_por_sellar
 from core.budget.curva import PeriodoPlan
 from core.budget.instantanea import composiciones_de_version, congelar
@@ -119,4 +120,6 @@
     motivo: str = "",
     heredar_insumos: bool = False,
+    usuario: str | None = None,
+    anexos_de: AnexosDe | None = None,
 ) -> models.Presupuesto:
     """Persiste el presupuesto con su cómputo, su curva y los hallazgos de su informe.
@@ -141,4 +144,10 @@
     esta; van juntos o ninguno. `heredar_insumos` (solo con `version_origen`: edición y
     restauración) copia el `insumo_id` de cada línea de la instantánea de origen (SF3 R‑7).
+
+    SL‑E7 (S3 §6.2): este es el único embudo de versiones. Marca la versión como **por sellar**:
+    al confirmar la transacción raíz, un evento `before_commit` escribe su eslabón en la misma
+    transacción. `usuario` (quien confirma) es obligatorio AL CONFIRMAR, no al llamar: sin él, el
+    `commit` falla con `SelladoSinUsuario` y no se escribe nada. `anexos_de` da los anexos de la
+    versión que la cadena cubre (hoy, el espacio de la hoja).
     """
     if (version_origen is None) != (motivo == ""):
@@ -217,4 +226,5 @@
         )
         session.flush()
+    marcar_por_sellar(session, modelo, usuario, anexos_de)
     return modelo
 
```
  Los cuatro caminos del núcleo que crean versiones pasan el `usuario` (la edición y la
  restauración lo toman de su `responsable`):
```diff
--- a/core/budget/cotizacion.py
+++ b/core/budget/cotizacion.py
@@ -117,4 +117,5 @@
     lista: models.ListaPrecios,
     reglas: Sequence[ReglaVerificacion],
+    usuario: str,
 ) -> models.Presupuesto:
     """La versión `codigo_nuevo` valorada con `lista`: mismas cantidades, parámetros, pendientes,
@@ -160,4 +161,5 @@
         version_origen=origen,
         motivo="cotizacion",
+        usuario=usuario,
     )
 
@@ -252,5 +254,5 @@
     )
     nueva = _guardar_version(
-        session, proyecto_nombre, codigo_origen, codigo_nuevo, catalogo, lista, reglas
+        session, proyecto_nombre, codigo_origen, codigo_nuevo, catalogo, lista, reglas, responsable
     )
     _registrar(
@@ -304,5 +306,5 @@
     )
     nueva = _guardar_version(
-        session, proyecto_nombre, codigo_origen, codigo_nuevo, catalogo, lista, reglas
+        session, proyecto_nombre, codigo_origen, codigo_nuevo, catalogo, lista, reglas, responsable
     )
     vuelve = _precio_en(base, insumo)
```
```diff
--- a/core/budget/actualizacion.py
+++ b/core/budget/actualizacion.py
@@ -136,4 +136,5 @@
     detectar_atipicos: DetectorAtipicos | None = None,
     reglas: Sequence[ReglaVerificacion] = REGLAS,
+    usuario: str | None = None,
 ) -> tuple[ResultadoElaboracion, Comparativo]:
     """Revalora un presupuesto con `lista_nueva` y lo guarda como versión `codigo_nuevo`.
@@ -234,4 +235,5 @@
         version_origen=modelo,
         motivo="revaloracion",
+        usuario=usuario,
     )
 
```
```diff
--- a/core/budget/edicion.py
+++ b/core/budget/edicion.py
@@ -137,4 +137,5 @@
         motivo="edicion",
         heredar_insumos=True,
+        usuario=responsable,
     )
     momento = ahora or datetime.now()
@@ -196,4 +197,5 @@
         motivo="restauracion",
         heredar_insumos=True,
+        usuario=responsable,
     )
     session.add(
```
```diff
--- a/core/budget/importacion.py
+++ b/core/budget/importacion.py
@@ -176,4 +176,5 @@
     proyecto: models.Proyecto,
     reglas: Sequence[ReglaVerificacion] = REGLAS,
+    usuario: str | None = None,
 ) -> ResultadoElaboracion:
     """UC‑05 con el archivo de un tercero: lee, audita siempre y persiste con su informe.
@@ -244,4 +245,5 @@
         lista=lista,
         parametros=importado.parametros,
+        usuario=usuario,
     )
     return ResultadoElaboracion(presupuesto=presupuesto, informe=informe)
```
  Los scripts del repositorio dejan constancia de que ellos guardaron:
```diff
--- a/scripts/probar_precios_maprex.py
+++ b/scripts/probar_precios_maprex.py
@@ -467,4 +467,5 @@
         parametros=parametros,
         pendientes=resultado.pendientes,
+        usuario="script:probar_precios_maprex",
     )
     sesion.commit()
@@ -530,5 +531,6 @@
     detector: DetectorAtipicos | None = registrado
     nuevo, comparativo = actualizar_precios(
-        sesion, proyecto, codigo, lista, codigo_nuevo, plan=plan, detectar_atipicos=detector
+        sesion, proyecto, codigo, lista, codigo_nuevo, plan=plan, detectar_atipicos=detector,
+        usuario="script:probar_precios_maprex",
     )
     historico = cambios_precio(sesion)
@@ -708,5 +710,6 @@
     )
     _, comparativo = actualizar_precios(
-        sesion, proyecto.nombre, codigo, resumen.lista, f"{codigo}{SUFIJO_VERSION}"
+        sesion, proyecto.nombre, codigo, resumen.lista, f"{codigo}{SUFIJO_VERSION}",
+        usuario="script:probar_precios_maprex",
     )
     sesion.rollback()  # flujo 3a: no hay nada que guardar
```
```diff
--- a/scripts/seed_demo.py
+++ b/scripts/seed_demo.py
@@ -444,5 +444,6 @@
     resultado = elaborar_caso_demo(caso)
     return guardar_presupuesto(
-        sesion, resultado.presupuesto, resultado.informe, proyecto, lista, caso.parametros
+        sesion, resultado.presupuesto, resultado.informe, proyecto, lista, caso.parametros,
+        usuario="script:seed_demo",
     )
 
```
```diff
--- a/scripts/medir_rnf03.py
+++ b/scripts/medir_rnf03.py
@@ -130,4 +130,5 @@
                 lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                 parametros=linea_base.PARAMETROS_LINEA_BASE,
+                usuario="script:medir_rnf03",
             )
             sesion.commit()
@@ -145,5 +146,6 @@
             inicio = time.perf_counter()
             _, comparativo = actualizar_precios(
-                sesion, NOMBRE_PROYECTO, CODIGO_BASE, resumen.lista, CODIGO_NUEVO
+                sesion, NOMBRE_PROYECTO, CODIGO_BASE, resumen.lista, CODIGO_NUEVO,
+                usuario="script:medir_rnf03",
             )
             sesion.commit()
```
```diff
--- a/scripts/generar_resultados_ml.py
+++ b/scripts/generar_resultados_ml.py
@@ -169,4 +169,5 @@
         lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
         parametros=linea_base.PARAMETROS_LINEA_BASE,
+        usuario="script:generar_resultados_ml",
     )
 
@@ -186,4 +187,5 @@
         "002",
         plan=plan_secuencial,
+        usuario="script:generar_resultados_ml",
     )
 
```
  La suite instala un usuario de prueba en el embudo (RF-83) para que las pruebas que no son del
  sellado sigan guardando sin declararlo; el marcador `sin_usuario_por_omision` lo apaga. La
  prueba de arquitectura de la tarea 23 vigila que ningún llamador FUERA de `tests/` dependa de
  este valor. `tests/conftest.py` gana la constante y reemplaza la fixture `_acceso_apagado` de la
  tarea 6 por la que además controla el marcador:
```python
#: El `usuario` que el embudo recibe en las pruebas que no lo declaran (RF-83).
USUARIO_DE_PRUEBA = "Prueba <prueba>"
```
```python

#: Estado de la fixture de abajo: las pruebas marcadas `sin_usuario_por_omision` lo apagan.
_USUARIO_POR_OMISION = {"activo": True}


@pytest.fixture(scope="session", autouse=True)
def _usuario_de_prueba_en_el_embudo() -> Iterator[None]:
    """S3-2 (RF-83): confirmar una versión exige `usuario`. Las pruebas que no son del sellado
    guardan sin declarar uno y el embudo recibe el de prueba. De sesión, y no por prueba, porque
    las fixtures de módulo y de sesión que siembran bases también guardan versiones. La prueba de
    arquitectura vigila que ningún llamador FUERA de `tests/` dependa de este valor."""
    from core.budget import persistencia

    original = persistencia.marcar_por_sellar

    def con_usuario(session, version, usuario, anexos_de=None):
        por_omision = USUARIO_DE_PRUEBA if _USUARIO_POR_OMISION["activo"] else None
        return original(session, version, usuario or por_omision, anexos_de)

    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(persistencia, "marcar_por_sellar", con_usuario)
        yield


@pytest.fixture(autouse=True)
def _acceso_apagado_y_usuario_por_prueba(request, monkeypatch) -> Iterator[None]:
    """S3-1: la interfaz no pide entrar (`SILICE_ACCESO=0`; las pruebas de S3 lo encienden).
    S3-2: `@pytest.mark.sin_usuario_por_omision` apaga el usuario de prueba del embudo."""
    monkeypatch.setenv("SILICE_ACCESO", "0")
    _USUARIO_POR_OMISION["activo"] = request.node.get_closest_marker(
        "sin_usuario_por_omision"
    ) is None
    yield
    _USUARIO_POR_OMISION["activo"] = True
```
  y `pyproject.toml` declara el marcador:
```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -74,2 +74,5 @@
 pythonpath = ["."]
 addopts = "-q --strict-markers"
+markers = [
+    "sin_usuario_por_omision: la prueba guarda versiones sin el usuario de prueba (RF-83).",
+]
```
- [ ] **Paso 4: Correrla y ver el verde** (y TODA la suite: el embudo cambió)
Run: `uv run pytest tests/integration/test_cadena.py tests/integration/test_canonico.py -v -W error`
→ verde. Run: `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml` →
verde.
Run: `uv run python scripts/guardia_nucleo.py --base origin/main` → 0.
- [ ] **Paso 5: Commit**
```bash
git add core/models/cadena.py core/models/__init__.py core/budget/cadena.py \
  core/budget/persistencia.py core/budget/cotizacion.py core/budget/actualizacion.py \
  core/budget/edicion.py core/budget/importacion.py \
  migraciones/caso/versions/caso_0007_s3_cadena.py scripts/probar_precios_maprex.py \
  scripts/seed_demo.py scripts/medir_rnf03.py scripts/generar_resultados_ml.py tests/conftest.py \
  pyproject.toml
git commit -m "feat(nucleo): cadena de huellas sellada al confirmar y usuario obligatorio (SL-E7)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 9: SL-E12 — WAL y `BEGIN IMMEDIATE` para varios usuarios

**Rama:** `inc/080-s3-2-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Modificar: `core/catalog/sesion.py:14-75`, `core/catalog/__init__.py:27-45`
- Prueba: `tests/integration/test_concurrencia.py`

**Interfaces:**
- Consume: `core.budget.cadena` y `core.models.cadena.EslabonVersion` (tarea 8),
  `tests.fixtures.canonico_minimo.{guardar_otra, registro, sembrar_minimo}`.
- Produce:
  - `core.catalog.crear_motor(url)`: ahora en WAL, con `busy_timeout = 5000`, claves foráneas e
    `isolation_level = None`.
  - `core.catalog.abrir_sesion_de_escritura(motor) -> Session`: la que toma el bloqueo de
    escritura al empezar (`BEGIN IMMEDIATE`), para toda transacción que crea una versión.
  - La opción de ejecución `silice_inmediata` que dispara el `BEGIN IMMEDIATE` (RP8-10).

Receta verificada con SQLAlchemy 2.0.52 y pysqlite (bitácora de S3-0): `conexion.isolation_level
= None` al conectar (pysqlite deja de emitir su `BEGIN` implícito), `PRAGMA journal_mode=WAL`,
`PRAGMA busy_timeout=5000` y un evento `begin` que emite `BEGIN IMMEDIATE` si la opción de
ejecución está puesta y `BEGIN` si no. Con tres hilos que guardan 10 versiones cada uno la cadena
queda lineal y sin `database is locked`. El índice único de la tarea 8 sigue siendo la red: si dos
transacciones llegaran a sellar sobre el mismo eslabón, falla la segunda y no se corrompe nada.

- [ ] **Paso 0: Antes del código** — el expediente SL-E12 está commiteado y aprobado.
- [ ] **Paso 1: Escribir la prueba que falla** (sin tiempos de espera fijos: tres hilos
  sincronizados con `threading.Barrier`, un número fijo de guardados por hilo, y se cuentan filas)
**`tests/integration/test_concurrencia.py`**
```python
"""SL-E12: varios usuarios a la vez sobre SQLite (RF-83, RNF-16; spec S3 §6.3 y §13.4, PRU-H20).

Sin tiempos de espera fijos: tres hilos sincronizados con `threading.Barrier`, un número fijo de
guardados por hilo, y se cuentan filas. Lo esperado es exactamente 3 x N versiones y sus
`RegistroCambio`, una cadena lineal y ningún `database is locked`.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from core import models
from core.budget import cadena
from core.catalog import abrir_sesion, abrir_sesion_de_escritura, crear_esquema, crear_motor
from core.catalog import sesion as modulo_sesion
from core.models.cadena import EslabonVersion
from tests.fixtures.canonico_minimo import guardar_otra, registro, sembrar_minimo

HILOS, GUARDADOS = 3, 10


def _base(tmp_path: Path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        proyecto, v1, lista = sembrar_minimo(sesion)
        sesion.commit()
        return motor, proyecto.id, lista.id, v1.id


def test_el_motor_usa_wal_espera_y_claves_foraneas(tmp_path: Path) -> None:
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    try:
        with motor.connect() as conexion:
            assert conexion.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
            assert conexion.exec_driver_sql("PRAGMA busy_timeout").scalar() == (
                modulo_sesion.ESPERA_OCUPADA_MS)
            assert conexion.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    finally:
        motor.dispose()


def test_la_sesion_de_escritura_toma_el_bloqueo_al_empezar(tmp_path: Path, monkeypatch) -> None:
    """Dos sesiones de escritura no pueden estar abiertas a la vez: la segunda espera, y si la
    espera se agota, falla con `database is locked` (prueba de que fue `BEGIN IMMEDIATE`)."""
    monkeypatch.setattr(modulo_sesion, "ESPERA_OCUPADA_MS", 50)
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    primera, segunda = abrir_sesion_de_escritura(motor), abrir_sesion_de_escritura(motor)
    lectora = abrir_sesion(motor)
    try:
        primera.execute(text("SELECT 1"))  # empieza la transacción: ya tiene el bloqueo
        with pytest.raises(OperationalError, match="locked"):
            segunda.execute(text("SELECT 1"))
        assert lectora.execute(text("SELECT count(*) FROM proyecto")).scalar() == 0  # WAL: lee
    finally:
        for sesion in (primera, segunda, lectora):
            sesion.rollback()
            sesion.close()
        motor.dispose()


def test_una_sesion_de_lectura_no_toma_el_bloqueo_de_escritura(tmp_path: Path) -> None:
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    uno, otro = abrir_sesion(motor), abrir_sesion(motor)
    try:
        uno.execute(text("SELECT 1"))
        otro.execute(text("SELECT 1"))  # no espera ni falla
    finally:
        uno.close()
        otro.close()
        motor.dispose()


def test_tres_hilos_guardan_diez_versiones_cada_uno_sin_perder_ninguna(tmp_path: Path) -> None:
    motor, proyecto_id, lista_id, _ = _base(tmp_path)
    barrera, errores = threading.Barrier(HILOS), []

    def trabajar(hilo: int) -> None:
        barrera.wait()
        for i in range(GUARDADOS):
            try:
                with abrir_sesion_de_escritura(motor) as sesion:
                    proyecto = sesion.get(models.Proyecto, proyecto_id)
                    lista = sesion.get(models.ListaPrecios, lista_id)
                    origen = sesion.scalars(
                        select(models.Presupuesto).where(models.Presupuesto.codigo == "001")
                    ).one()
                    nueva = guardar_otra(
                        sesion, proyecto, lista, f"H{hilo}-{i:02d}", version_origen=origen,
                        motivo="edicion", usuario=f"hilo{hilo} <h{hilo}>",
                    )
                    sesion.add(registro(proyecto, origen, nueva, responsable=f"hilo{hilo}"))
                    sesion.commit()
            except Exception as error:  # noqa: BLE001 - se cuenta y se informa abajo
                errores.append(repr(error))

    hilos = [threading.Thread(target=trabajar, args=(h,)) for h in range(HILOS)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert errores == []
    with abrir_sesion(motor) as sesion:
        total = HILOS * GUARDADOS
        assert sesion.query(models.Presupuesto).count() == 1 + total
        assert sesion.query(models.RegistroCambio).count() == total
        assert sesion.query(EslabonVersion).count() == 1 + total
        proyecto = sesion.get(models.Proyecto, proyecto_id)
        resultado = cadena.verificar_cadena(sesion, proyecto)
        assert resultado.integra and resultado.versiones == 1 + total
        eslabones = cadena.eslabones_de(sesion, proyecto)
        # lineal: cada eslabón cuelga del anterior en el orden de las versiones
        assert [e.anterior for e in eslabones[1:]] == [e.huella_eslabon for e in eslabones[:-1]]
    motor.dispose()
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_concurrencia.py -v -W error`
Esperado: error de colección `ImportError: cannot import name 'abrir_sesion_de_escritura' from
'core.catalog'`.
```bash
git add tests/integration/test_concurrencia.py
git commit -m "test(nucleo): tres hilos guardando a la vez sin bifurcar, en rojo (SL-E12)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
```diff
--- a/core/catalog/sesion.py
+++ b/core/catalog/sesion.py
@@ -14,4 +14,9 @@
 _MEMORIA = ":memory:"
 
+#: SL-E12: espera de SQLite ante una base ocupada, en milisegundos. SUPUESTO_DECLARADO (S3 §4.4).
+ESPERA_OCUPADA_MS = 5000
+#: Opción de ejecución que pide `BEGIN IMMEDIATE`: la lleva `abrir_sesion_de_escritura`.
+OPCION_INMEDIATA = "silice_inmediata"
+
 
 def crear_motor(url: str = URL_POR_DEFECTO) -> Engine:
@@ -19,5 +24,8 @@
 
     Activa `PRAGMA foreign_keys` en SQLite: sin él, el motor ignora las claves foráneas y el
-    esquema dejaría de ser el que documenta docs/modelo_datos.md.
+    esquema dejaría de ser el que documenta docs/modelo_datos.md. Desde SL-E12 (varios usuarios a
+    la vez, S3 §6.3) activa además el diario WAL y `busy_timeout`, y toma el control del `BEGIN`
+    (receta de SQLAlchemy para pysqlite): las transacciones que crean versión empiezan con
+    `BEGIN IMMEDIATE` para tomar el bloqueo de escritura ANTES de leer el último eslabón.
     """
     _preparar_directorio(url)
@@ -25,4 +33,6 @@
     if motor.dialect.name == "sqlite":
         event.listen(motor, "connect", _activar_claves_foraneas)
+        event.listen(motor, "connect", _preparar_conexion)
+        event.listen(motor, "begin", _comenzar)
     return motor
 
@@ -43,4 +53,11 @@
 
 
+def abrir_sesion_de_escritura(motor: Engine) -> Session:
+    """Una sesión cuya transacción empieza con `BEGIN IMMEDIATE` (SL-E12): la de todo camino que
+    crea una versión. Quien guarda toma el bloqueo de escritura antes de leer el último eslabón y
+    el otro espera hasta `ESPERA_OCUPADA_MS`; en WAL los lectores no se bloquean."""
+    return Session(motor.execution_options(**{OPCION_INMEDIATA: True}))
+
+
 def _preparar_directorio(url: str) -> None:
     if not url.startswith(_PREFIJO_ARCHIVO_SQLITE):
@@ -56,2 +73,16 @@
     cursor.execute("PRAGMA foreign_keys=ON")
     cursor.close()
+
+
+def _preparar_conexion(conexion, _registro) -> None:
+    # `isolation_level = None`: pysqlite deja de emitir el BEGIN implícito y lo emite `_comenzar`.
+    conexion.isolation_level = None
+    cursor = conexion.cursor()
+    cursor.execute(f"PRAGMA busy_timeout={ESPERA_OCUPADA_MS}")
+    cursor.execute("PRAGMA journal_mode=WAL")
+    cursor.close()
+
+
+def _comenzar(conexion) -> None:
+    inmediata = conexion.get_execution_options().get(OPCION_INMEDIATA, False)
+    conexion.exec_driver_sql("BEGIN IMMEDIATE" if inmediata else "BEGIN")
```
```diff
--- a/core/catalog/__init__.py
+++ b/core/catalog/__init__.py
@@ -25,5 +25,10 @@
 )
 from core.catalog.repositorio import Catalogo, ResumenCarga
-from core.catalog.sesion import abrir_sesion, crear_esquema, crear_motor
+from core.catalog.sesion import (
+    abrir_sesion,
+    abrir_sesion_de_escritura,
+    crear_esquema,
+    crear_motor,
+)
 
 __all__ = [
@@ -38,4 +43,5 @@
     "ResumenLista",
     "abrir_sesion",
+    "abrir_sesion_de_escritura",
     "advertencia_rendimiento",
     "cambios_precio",
```
- [ ] **Paso 4: Correrla y ver el verde** (y la suite del catálogo, que usa `crear_motor`)
Run: `uv run pytest tests/integration/test_concurrencia.py tests/integration/test_cadena.py -v
-W error` → verde. Run: `uv run pytest -q -W error -p no:cacheprovider` → verde.
Run: `uv run python scripts/guardia_nucleo.py --base origin/main` → 0.
- [ ] **Paso 5: Commit**
```bash
git add core/catalog/sesion.py core/catalog/__init__.py
git commit -m "feat(nucleo): WAL, espera y BEGIN IMMEDIATE para varios usuarios (SL-E12)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 10: SL-E9 — diferencia entre versiones y revaloración

**Rama:** `inc/080-s3-2-nucleo`   **Rol:** sf-ingeniero-nucleo
**Archivos:**
- Crear: `core/budget/comparacion.py`
- Prueba: `tests/unit/test_comparacion.py`

**Interfaces:**
- Consume: `core.budget.canonico.DocumentoLeido` (tarea 7), `core.contracts.apu.ComposicionAPU`,
  `core.costing.calcular_apu`; `tests/fixtures/canonico/ejemplo_v1.py` y la memoria
  `tests/fixtures/memorias/diferencias_s3.md` (tarea 2).
- Produce:
  - `core.budget.comparacion`: `class FilaPresupuesto`
  - `core.budget.comparacion`: `class DiferenciaPartida`
  - `core.budget.comparacion`: `class Diferencia`
  - `core.budget.comparacion`: `def diferencia_entre_versiones(a: Sequence[FilaPresupuesto], b:
      Sequence[FilaPresupuesto]) -> Diferencia`
  - `core.budget.comparacion`: `def filas_de(documento: DocumentoLeido) ->
      tuple[FilaPresupuesto, ...]`
  - `core.budget.comparacion`: `class PrecioDeLista`
  - `core.budget.comparacion`: `class NoContrastable`
  - `core.budget.comparacion`: `class Revaloracion`
  - `core.budget.comparacion`: `def revalorar(documento: DocumentoLeido, precios:
      Sequence[PrecioDeLista]) -> Revaloracion`

**Qué calcula.** Por partida, `Δ total = q2·PU2 − q1·PU1 = (q2 − q1)·PU1 [cantidad] + (PU2 − PU1)·q2
[precio]`: el término cruzado queda en el precio y las dos columnas suman EXACTO el Δ total
(`Decimal` sin redondeos). Una partida que solo está en una versión es desvío por cantidad entero
(nueva: `q1 = 0` y `PU1 := PU2`; eliminada: `q2 = 0` y `PU2 := PU1`). `revalorar` valora un
documento con otra lista emparejando por referencia de precio y, si no, por código de insumo; lo
que no empareja es «no contrastable»: conserva su precio, se lista y no suma. Es una descomposición
**distinta** de la separación del desvío de control de S2, que no la reutiliza (RV-10).
Oráculo: totales 840 → 1130, Δ por cantidad 250, Δ por precio 40; la entrega Q 550 → 589.

- [ ] **Paso 0: Antes del código** — el expediente SL-E9 está commiteado y aprobado.
- [ ] **Paso 1: Escribir la prueba que falla** (cifras de la memoria a mano, no del sistema)
**`tests/unit/test_comparacion.py`**
```python
"""SL-E9: diferencia entre versiones y revaloración, contra la memoria hecha a mano
(`tests/fixtures/memorias/diferencias_s3.md`; RF-87, RV-10; spec S3 §9 paso 4 y §13.1)."""

from __future__ import annotations

import copy
from decimal import Decimal

import pytest

from core.budget import canonico
from core.budget.comparacion import (
    FilaPresupuesto,
    PrecioDeLista,
    diferencia_entre_versiones,
    filas_de,
    revalorar,
)
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1


def fila(codigo: str, q: str, pu: str) -> FilaPresupuesto:
    return FilaPresupuesto(codigo, f"partida {codigo}", "m", Decimal(q), Decimal(pu))


#: Versión 004 y versión 005 de la memoria: A cambia solo la cantidad, B solo el precio, C las
#: dos cosas, D se elimina y E es nueva.
V004 = (fila("A", "10", "50.00"), fila("B", "5", "20.00"), fila("C", "2", "100.00"),
        fila("D", "4", "10.00"))
V005 = (fila("A", "12", "50.00"), fila("B", "5", "22.00"), fila("C", "3", "110.00"),
        fila("E", "3", "30.00"))
#: código: (estado, Δ por cantidad, Δ por precio), hechos a mano en la memoria.
MEMORIA = {
    "A": ("cambiada", "100.00", "0.00"),
    "B": ("cambiada", "0.00", "10.00"),
    "C": ("cambiada", "100.00", "30.00"),
    "D": ("eliminada", "-40.00", "0.00"),
    "E": ("nueva", "90.00", "0.00"),
}


def test_la_diferencia_por_partida_es_la_de_la_memoria() -> None:
    diferencia = diferencia_entre_versiones(V004, V005)
    por_codigo = {p.codigo_partida: p for p in diferencia.partidas}
    for codigo, (estado, dq, dp) in MEMORIA.items():
        parcial = por_codigo[codigo]
        assert (parcial.estado, parcial.desvio_cantidad, parcial.desvio_precio) == (
            estado, Decimal(dq), Decimal(dp)), codigo
        assert parcial.desvio_total == Decimal(dq) + Decimal(dp)


def test_los_totales_son_los_de_la_memoria_y_las_dos_columnas_suman_exacto() -> None:
    diferencia = diferencia_entre_versiones(V004, V005)
    assert (diferencia.total_1, diferencia.total_2) == (Decimal("840.00"), Decimal("1130.00"))
    assert (diferencia.desvio_cantidad, diferencia.desvio_precio) == (
        Decimal("250.00"), Decimal("40.00"))
    assert diferencia.desvio_total == Decimal("290.00")
    assert diferencia.desvio_cantidad + diferencia.desvio_precio == (
        diferencia.total_2 - diferencia.total_1)


def test_se_ordena_por_el_valor_absoluto_del_delta() -> None:
    codigos = [p.codigo_partida for p in diferencia_entre_versiones(V004, V005).partidas]
    assert codigos == ["C", "A", "E", "D", "B"]  # 130, 100, 90, 40, 10


def test_el_termino_cruzado_queda_en_el_precio() -> None:
    """C: (3 - 2) x 100 = 100 por cantidad; (110 - 100) x 3 = 30 por precio (no 20)."""
    c = {p.codigo_partida: p for p in diferencia_entre_versiones(V004, V005).partidas}["C"]
    assert (c.desvio_cantidad, c.desvio_precio) == (Decimal("100.00"), Decimal("30.00"))


def test_una_partida_nueva_o_eliminada_es_desvio_por_cantidad_entero() -> None:
    nueva = diferencia_entre_versiones((), (fila("N", "3", "30.00"),)).partidas[0]
    assert (nueva.estado, nueva.cantidad_1, nueva.precio_1) == ("nueva", 0, Decimal("30.00"))
    assert (nueva.desvio_cantidad, nueva.desvio_precio) == (Decimal("90.00"), 0)
    borrada = diferencia_entre_versiones((fila("X", "4", "10.00"),), ()).partidas[0]
    assert (borrada.estado, borrada.cantidad_2, borrada.precio_2) == ("eliminada", 0, Decimal(10))
    assert (borrada.desvio_cantidad, borrada.desvio_precio) == (Decimal("-40.00"), 0)


def test_dos_versiones_iguales_no_difieren() -> None:
    diferencia = diferencia_entre_versiones(V004, V004)
    assert diferencia.desvio_total == 0 and {p.estado for p in diferencia.partidas} == {"igual"}


def test_las_filas_repetidas_de_una_partida_suman_cantidad_con_un_solo_precio() -> None:
    junto = diferencia_entre_versiones(
        (fila("A", "1", "5"), fila("A", "2", "5")), (fila("A", "6", "5"),)
    )
    assert junto.partidas[0].cantidad_1 == Decimal(3) and junto.desvio_total == Decimal(15)
    with pytest.raises(ValueError, match="dos precios unitarios"):
        diferencia_entre_versiones((fila("A", "1", "5"), fila("A", "2", "6")), ())


def test_el_ejemplo_del_spec_no_pierde_centimos() -> None:
    a = (fila("P", "7", "33.333333"),)
    b = (fila("P", "9", "35.100001"),)
    d = diferencia_entre_versiones(a, b)
    assert d.desvio_cantidad + d.desvio_precio == Decimal("9") * Decimal("35.100001") - \
        Decimal("7") * Decimal("33.333333")


# --- revaloración -------------------------------------------------------------------------


def documento(**cambios) -> canonico.DocumentoLeido:
    objeto = copy.deepcopy(EJEMPLO_V1)
    if cambios.get("referencia"):
        objeto["composiciones"][0]["lineas"][0]["referencia"] = cambios["referencia"]
    return canonico.leer(objeto)


def test_filas_de_recalcula_el_precio_en_vez_de_creer_el_declarado() -> None:
    objeto = copy.deepcopy(EJEMPLO_V1)
    objeto["renglones"][0]["precio_unitario"] = "99.00"  # el emisor miente
    leido = canonico.leer(objeto)
    assert filas_de(leido)[0].precio_unitario == Decimal("41.83987500")
    assert leido.declarados[0].precio_unitario == Decimal("99.00")


def test_revalorar_empareja_por_codigo_y_lo_que_no_empareja_no_suma() -> None:
    lista = [PrecioDeLista("MAT-001", "", Decimal("16.00")),
             PrecioDeLista("MO-001", "", Decimal("12.25"))]  # la compactadora no está
    revalorado = revalorar(documento(), lista)
    assert revalorado.filas[0].precio_unitario == Decimal("48.797375")  # memoria, a mano
    assert [(n.insumo, n.descripcion) for n in revalorado.no_contrastables] == [
        ("EQU-001", "Compactadora")]
    diferencia = diferencia_entre_versiones(filas_de(documento()), revalorado.filas)
    assert diferencia.desvio_precio == Decimal("139.15")  # (48.797375 - 41.839875) x 20
    assert diferencia.desvio_cantidad == 0


def test_la_referencia_de_precio_manda_sobre_el_codigo() -> None:
    lista = [PrecioDeLista("OTRO-9", "MP-0042", Decimal("15.00")),
             PrecioDeLista("MAT-001", "", Decimal("16.00")),
             PrecioDeLista("MO-001", "", Decimal("12.25")),
             PrecioDeLista("EQU-001", "", Decimal("71.00"))]
    revalorado = revalorar(documento(referencia="MP-0042"), lista)
    diferencia = diferencia_entre_versiones(filas_de(documento()), revalorado.filas)
    assert revalorado.no_contrastables == ()
    assert revalorado.filas[0].precio_unitario == Decimal("47.532375")  # Arena 15,00; Obrero 12,25
    assert diferencia.desvio_precio == Decimal("113.85")  # (47.532375 - 41.839875) x 20


def test_una_lista_vacia_deja_todo_no_contrastable_y_el_delta_en_cero() -> None:
    revalorado = revalorar(documento(), [])
    assert len(revalorado.no_contrastables) == 3
    assert diferencia_entre_versiones(filas_de(documento()), revalorado.filas).desvio_total == 0
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/unit/test_comparacion.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'core.budget.comparacion'`.
```bash
git add tests/unit/test_comparacion.py
git commit -m "test(nucleo): diferencia entre versiones con la memoria a mano, en rojo (SL-E9)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`core/budget/comparacion.py`**
```python
"""SL-E9: la diferencia entre dos versiones y su costo, y la revaloración en memoria (spec S3 §9,
paso 4; maestro §9.1, RV-10).

Funciones puras: no leen la base ni escriben nada. **Diferencia entre versiones**, por partida:

    Δ total  = q2·PU2 − q1·PU1 = (q2 − q1)·PU1   [desvío por cantidad]
                               + (PU2 − PU1)·q2   [desvío por precio]

El término cruzado queda en el precio. Una partida que solo está en una versión es desvío por
cantidad entero: nueva (q1 = 0 y PU1 := PU2) o eliminada (q2 = 0 y PU2 := PU1). Las dos columnas
suman EXACTO el Δ total (`Decimal` sin redondeos). Es una descomposición **distinta** de la
«separación del desvío de control» de S2 (término cruzado en el consumo): S2 no la reutiliza.

**Revaloración**: el presupuesto de un paquete valorado con los precios de la lista de quien
revisa, emparejando cada línea por **referencia de precio** (Ref MaPreX) o, si no, por código de
insumo. Lo que no empareja es «no contrastable»: conserva su precio, se lista y no suma al Δ.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from core.budget.canonico import DocumentoLeido
from core.contracts.apu import ComposicionAPU
from core.costing import calcular_apu

__all__ = [
    "Diferencia",
    "DiferenciaPartida",
    "FilaPresupuesto",
    "NoContrastable",
    "PrecioDeLista",
    "Revaloracion",
    "diferencia_entre_versiones",
    "filas_de",
    "revalorar",
]

CERO = Decimal(0)
IGUAL, CAMBIADA, NUEVA, ELIMINADA = "igual", "cambiada", "nueva", "eliminada"


@dataclass(frozen=True, slots=True)
class FilaPresupuesto:
    """Una partida de una versión: su cantidad total y su precio unitario recalculado."""

    codigo_partida: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio_unitario: Decimal


@dataclass(frozen=True, slots=True)
class DiferenciaPartida:
    codigo_partida: str
    descripcion: str
    estado: str  # igual | cambiada | nueva | eliminada
    cantidad_1: Decimal
    cantidad_2: Decimal
    precio_1: Decimal
    precio_2: Decimal
    desvio_cantidad: Decimal
    desvio_precio: Decimal

    @property
    def desvio_total(self) -> Decimal:
        return self.desvio_cantidad + self.desvio_precio


@dataclass(frozen=True, slots=True)
class Diferencia:
    partidas: tuple[DiferenciaPartida, ...]  # por |Δ total| descendente, luego por código
    total_1: Decimal
    total_2: Decimal
    desvio_cantidad: Decimal
    desvio_precio: Decimal

    @property
    def desvio_total(self) -> Decimal:
        return self.desvio_cantidad + self.desvio_precio


def _por_codigo(filas: Sequence[FilaPresupuesto]) -> dict[str, FilaPresupuesto]:
    """Junta las filas de una misma partida (cantidades suman); su precio debe ser único."""
    junto: dict[str, FilaPresupuesto] = {}
    for fila in filas:
        previa = junto.get(fila.codigo_partida)
        if previa is None:
            junto[fila.codigo_partida] = fila
        elif previa.precio_unitario != fila.precio_unitario:
            raise ValueError(
                f"la partida {fila.codigo_partida} aparece con dos precios unitarios distintos"
            )
        else:
            junto[fila.codigo_partida] = replace(previa, cantidad=previa.cantidad + fila.cantidad)
    return junto


def diferencia_entre_versiones(
    a: Sequence[FilaPresupuesto], b: Sequence[FilaPresupuesto]
) -> Diferencia:
    """La diferencia de `b` (la versión nueva) respecto de `a` (la anterior)."""
    uno, dos = _por_codigo(a), _por_codigo(b)
    partidas: list[DiferenciaPartida] = []
    for codigo in sorted(set(uno) | set(dos)):
        antes, despues = uno.get(codigo), dos.get(codigo)
        if antes is None:
            q1, p1, q2, p2, estado = CERO, despues.precio_unitario, despues.cantidad, \
                despues.precio_unitario, NUEVA
        elif despues is None:
            q1, p1, q2, p2, estado = antes.cantidad, antes.precio_unitario, CERO, \
                antes.precio_unitario, ELIMINADA
        else:
            q1, p1, q2, p2 = (antes.cantidad, antes.precio_unitario, despues.cantidad,
                              despues.precio_unitario)
            estado = IGUAL if (q1, p1) == (q2, p2) else CAMBIADA
        partidas.append(
            DiferenciaPartida(
                codigo_partida=codigo,
                descripcion=(despues or antes).descripcion,
                estado=estado,
                cantidad_1=q1, cantidad_2=q2, precio_1=p1, precio_2=p2,
                desvio_cantidad=(q2 - q1) * p1,
                desvio_precio=(p2 - p1) * q2,
            )
        )
    partidas.sort(key=lambda p: (-abs(p.desvio_total), p.codigo_partida))
    return Diferencia(
        partidas=tuple(partidas),
        total_1=sum((f.cantidad * f.precio_unitario for f in uno.values()), CERO),
        total_2=sum((f.cantidad * f.precio_unitario for f in dos.values()), CERO),
        desvio_cantidad=sum((p.desvio_cantidad for p in partidas), CERO),
        desvio_precio=sum((p.desvio_precio for p in partidas), CERO),
    )


def filas_de(documento: DocumentoLeido) -> tuple[FilaPresupuesto, ...]:
    """Las partidas de un documento con su precio unitario RECALCULADO por el motor desde las
    composiciones y los parámetros del propio documento (no se confía en lo declarado)."""
    filas: list[FilaPresupuesto] = []
    for item in documento.items:
        composicion = documento.composiciones[item.codigo_partida]
        filas.append(
            FilaPresupuesto(
                item.codigo_partida, item.descripcion, item.unidad, item.cantidad,
                calcular_apu(composicion, documento.parametros).precio_unitario,
            )
        )
    return tuple(filas)


# --- revaloración en memoria -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PrecioDeLista:
    """Un precio de la lista de quien revisa: por referencia de precio y por código de insumo."""

    codigo_insumo: str
    referencia: str
    precio: Decimal


@dataclass(frozen=True, slots=True)
class NoContrastable:
    codigo_partida: str
    descripcion: str
    insumo: str | None


@dataclass(frozen=True, slots=True)
class Revaloracion:
    filas: tuple[FilaPresupuesto, ...]
    no_contrastables: tuple[NoContrastable, ...]


def _revalorada(
    composicion: ComposicionAPU,
    extras: Sequence,
    por_referencia: Mapping[str, Decimal],
    por_codigo: Mapping[str, Decimal],
    sin_par: list[NoContrastable],
) -> ComposicionAPU:
    lineas = [*composicion.materiales, *composicion.equipos, *composicion.mano_obra]
    nuevas = []
    for linea, extra in zip(lineas, extras, strict=True):
        precio = por_referencia.get(extra.referencia) if extra.referencia else None
        if precio is None and extra.insumo is not None:
            precio = por_codigo.get(extra.insumo)
        if precio is None:
            sin_par.append(NoContrastable(composicion.codigo_partida, linea.descripcion,
                                          extra.insumo))
            nuevas.append(linea)
        elif hasattr(linea, "sueldo"):
            nuevas.append(replace(linea, sueldo=precio))
        else:
            nuevas.append(replace(linea, precio=precio))
    nm, ne = len(composicion.materiales), len(composicion.equipos)
    return replace(
        composicion,
        materiales=tuple(nuevas[:nm]),
        equipos=tuple(nuevas[nm : nm + ne]),
        mano_obra=tuple(nuevas[nm + ne :]),
    )


def revalorar(documento: DocumentoLeido, precios: Sequence[PrecioDeLista]) -> Revaloracion:
    """El documento valorado con `precios`, en memoria. Las líneas sin pareja conservan su
    precio, se listan en `no_contrastables` (una vez por partida e insumo) y no suman al Δ."""
    por_referencia = {p.referencia: p.precio for p in precios if p.referencia}
    por_codigo = {p.codigo_insumo: p.precio for p in precios}
    sin_par: list[NoContrastable] = []
    nuevas = {
        codigo: _revalorada(
            composicion, documento.lineas[codigo], por_referencia, por_codigo, sin_par
        )
        for codigo, composicion in documento.composiciones.items()
    }
    filas = tuple(
        FilaPresupuesto(
            item.codigo_partida, item.descripcion, item.unidad, item.cantidad,
            calcular_apu(nuevas[item.codigo_partida], documento.parametros).precio_unitario,
        )
        for item in documento.items
    )
    unicas = tuple(dict.fromkeys(sin_par))
    return Revaloracion(filas=filas, no_contrastables=unicas)
```
- [ ] **Paso 4: Correrla y ver el verde**
Run: `uv run pytest tests/unit/test_comparacion.py -v -W error` → verde; `uv run ruff check
core/budget/comparacion.py`; `uv run python scripts/guardia_nucleo.py --base origin/main` → 0.
- [ ] **Paso 5: Commit**
```bash
git add core/budget/comparacion.py
git commit -m "feat(nucleo): diferencia entre versiones por cantidad y precio (SL-E9)" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS3-2 y foco de revisión de la fase

**Compuerta GS3-2** (se cruza al fusionar `inc/080-s3-2-nucleo`, junto con S3-3, RP8-20):
1. `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-2 --junit reporte-pruebas.xml`
   en OK; las pruebas de núcleo nuevas precedidas por su rojo (C3 lee el orden en el historial).
2. CI verde en Linux y Windows; `uv run python scripts/guardia_nucleo.py --base origin/main` en 0.
3. `git diff v0.7.0..HEAD -- core/contracts/` vacío; ninguna tabla existente ganó columnas.
4. **Aval del tutor** de SL-E7, SL-E8, SL-E9 y SL-E12 anotado en la bitácora (reglas de núcleo).

**Foco de revisión de S3-2** (lo que el spec implica y ninguna prueba ejercita todavía):
1. **Sellar dentro de un savepoint** daría un eslabón que se pierde si el savepoint se revierte:
   `test_un_savepoint_no_sella_pero_la_transaccion_raiz_si` (tarea 8).
2. **Dos versiones nuevas en la misma transacción** no deben sellarse como retroactivas:
   `test_dos_versiones_nuevas_en_la_misma_transaccion_no_se_sellan_como_retroactivas`.
3. **Un cambio de moneda posterior** no puede cambiar el documento de una versión sellada:
   `test_una_declaracion_posterior_a_la_version_no_cambia_su_documento` (tarea 7).
4. **Un `Decimal` con exponente o con un decimal de más** (`1E+3`, 29 decimales) no debe llegar a
   la huella: `test_un_decimal_con_exponente_se_escribe_posicional` y
   `test_el_patron_de_cifras_es_el_del_lector_estricto`.
5. **Una versión sin eslabón en medio de la cadena** es un error de cadena, no un hueco silencioso:
   `test_una_version_posterior_al_genesis_sin_eslabon_es_un_error_de_cadena`.

---

# S3-5 — Auditoría de planos (rama `inc/080-s3-5-planos`)

Carril sin núcleo: `adapters/espacio/`, `scripts/`, `ui/`, `data/ids/` y `tests/`. La tarea 11 puede
salir de `origin/main` antes que cualquier otra de S3; la tarea 12 espera a la tarea 10 (SL-E9)
porque el costo de la diferencia usa `core.budget.comparacion`. Necesita los extras `planos` (ezdxf,
shapely) e `ifc` (ifctester); sin `ifc`, la importación de un IFC sigue funcionando y el informe lo
dice (RP8-1). Al terminar, un DXF dañado se informa en vez de tumbar la importación, un IFC sin lo
mínimo se señala por elemento, R15 audita la geometría con `Decimal`, R16 contrasta dos fuentes con
el costo de la diferencia, y la detección de errores sembrados mide 100 % con cero falsas alarmas.

### Tarea 11: Archivo DXF dañado, requisitos IDS del IFC y R15 (coherencia geométrica)

**Rama:** `inc/080-s3-5-planos` (sale de `main`; PR a `main`)   **Rol:** sf-ingeniero-adaptadores
**Archivos:**
- Crear: `adapters/espacio/serie.py`, `adapters/espacio/planos/auditoria_archivo.py`,
  `adapters/espacio/planos/ids.py`, `adapters/espacio/planos/geometria_plano.py`
- Crear: `data/ids/silice_instalaciones.ids`, `scripts/generar_ids_silice.py`
- Crear: `tests/fixtures/espacio_minimo.py`, `tests/fixtures/planos_ifc_ids.py`
- Modificar: `adapters/espacio/planos/dxf.py:42-62,168-200,818-856`,
  `adapters/espacio/planos/ifc.py:63, 563`, `ui/hoja.py:83,714,1640` (R15 en la hoja),
  `tests/unit/test_arquitectura.py:34-42`, `tests/unit/test_dependencias_silice.py:36`,
  `tests/unit/test_caso_of001.py:167` (el informe de OF-001 declara una regla más)
- Prueba: `tests/unit/test_r15_geometria_plano.py`, `tests/unit/test_planos_auditoria_s3.py`,
  `tests/unit/test_hoja_r15.py`

**Interfaces:**
- Consume: `adapters.espacio.{Espacio, Ambiente, Punto, Fuente, Coord, ...}`,
  `adapters.espacio.especialidades.{SUPUESTO_DECLARADO, Constante}`,
  `adapters.espacio.planos.informe.{ItemInforme, TipoItem, EstadoImportacion}`,
  `core.contracts.verificacion.{Hallazgo, ReglaVerificacion, Severidad}`,
  `ui.hoja.elaborar_hoja`; los extras `planos` e `ifc`.
- Produce:
  - `adapters.espacio.serie`: `class LimiteExcedido(ValueError)`
  - `adapters.espacio.serie`: `def espacio_a_objeto(espacio: Espacio) -> dict[str, Any]`
  - `adapters.espacio.serie`: `def comprobar_limites(objeto: Mapping[str, Any]) -> None`
  - `adapters.espacio.serie`: `def espacio_desde_objeto(objeto: Mapping[str, Any], a_decimal:
      Callable[[Any], Decimal]=Decimal) -> Espacio`
  - `adapters.espacio.planos.auditoria_archivo`: `class Auditoria`
  - `adapters.espacio.planos.auditoria_archivo`: `def auditar_archivo(ruta: Path | str)`
  - `adapters.espacio.planos.auditoria_archivo`: `def texto_del_informe(auditoria: Auditoria) ->
      list[str]`
  - `adapters.espacio.planos.ids`: `def ids_disponible() -> bool`
  - `adapters.espacio.planos.ids`: `def esquema_sin_red(ids) -> None`
  - `adapters.espacio.planos.ids`: `def auditar_ids(modelo, ruta_ids: Path | str=RUTA_IDS) ->
      tuple[ItemInforme, ...]`
  - `adapters.espacio.planos.geometria_plano`: `class CoherenciaGeometrica(ReglaVerificacion)`
  - `adapters.espacio.planos.geometria_plano`: `def reglas_plano(espacio: Espacio) ->
      tuple[ReglaVerificacion, ...]`
  - `data/ids/silice_instalaciones.ids` (4 especificaciones) y `scripts/generar_ids_silice.py
    [--comprobar]`.

**Hallazgos de S3-0 que dan forma al código** (bitácora de la versión):
1. `ezdxf.Drawing.audit()` BORRA lo que no entiende (un `INSERT` sin definición de bloque, que el
   importador sí lee). Por eso la importación abre con `readfile` y solo recurre a
   `recover.readfile` si falla; el informe de reparaciones de un archivo que abrió bien sale de
   auditar una **segunda lectura**. Un DXF vacío o truncado es `RECHAZADA`, no `DETENIDA`.
2. `ifctester.ids.open` intenta descargar el esquema XSD de internet cada vez (lo atrapó la
   guardia de red de la suite): `esquema_sin_red` fija el XSD local antes de abrir.
3. `auditar_ids` se envuelve en `try/except`: un IDS ilegible no tumba la importación y se dice.
4. R15 usa `shapely.strtree.STRtree` solo para proponer candidatos; cada hallazgo se decide con
   `Decimal` (RP8-7), así que 0,0100 m2 pasa y 0,0101 m2 falla sin depender de un `float`.

**R15** (spec S3 §11.3): superposición de ambientes > 0,01 m2 (ERROR), dos puntos de la misma
especialidad y tipo a menos de 0,001 m (ERROR), lado de ambiente fuera de 0,30 m a 200 m
(ADVERTENCIA), altura fuera de 2,00 m a 12 m (ADVERTENCIA) y punto a más de 100 m de su fuente
(ADVERTENCIA). Las dos primeras son tolerancias geométricas del sistema; las tres últimas son
umbrales SUPUESTOS (sin fuente normativa) y por eso ADVERTENCIA. R15 no repite R9: un punto fuera de
su ambiente es de R9. La hoja la evalúa en vivo junto a R8 a R10 (spec S3 §3.4).

- [ ] **Paso 1: Escribir las pruebas que fallan** (las fronteras son exactas en cada fila)
**`tests/fixtures/espacio_minimo.py`**
```python
"""Espacios pequeños para las pruebas de R15 y R16 (S3-5): cada fila declara solo lo que prueba.

Todo en metros y `Decimal`; los ambientes arrancan en (0, 0) salvo que se diga otra cosa. Los
orígenes de medida no se registran: R15 y R16 no los leen (los marca R8).
"""

from __future__ import annotations

from decimal import Decimal

from adapters.espacio import (
    Ambiente,
    Coord,
    Espacio,
    Especialidad,
    Fuente,
    Punto,
    SuperficiePunto,
    TipoFuente,
    TipoPunto,
)

D = Decimal


def ambiente(id_: str, x0="0", y0="0", largo="4", ancho="3", alto="2.5") -> Ambiente:
    return Ambiente(id_, f"Ambiente {id_}", D(x0), D(y0), D(largo), D(ancho), D(alto), "O1")


def punto_de_datos(id_: str, x, y="1", z="0.3", fuente: str | None = None, amb="A") -> Punto:
    return Punto(
        id=id_, nombre=f"Punto {id_}", especialidad=Especialidad.DATOS, tipo=TipoPunto.DATOS,
        ambiente_id=amb, superficie=SuperficiePunto.PARED, posicion=Coord(D(x), D(y), D(z)),
        origen_id="O1", fuente_id=fuente,
    )


def toma(id_: str, x, y="1", z="0.3", amb="A") -> Punto:
    return Punto(
        id=id_, nombre=f"Toma {id_}", especialidad=Especialidad.ELECTRICIDAD,
        tipo=TipoPunto.TOMACORRIENTE, ambiente_id=amb, superficie=SuperficiePunto.PARED,
        posicion=Coord(D(x), D(y), D(z)), origen_id="O1",
    )


def rack(id_: str = "R1", x="0", y="0", z="0", amb="A") -> Fuente:
    return Fuente(
        id=id_, especialidad=Especialidad.DATOS, tipo=TipoFuente.RACK, ambiente_id=amb,
        posicion=Coord(D(x), D(y), D(z)), origen_id="O1",
    )


def espacio(ambientes=(), puntos=(), fuentes=()) -> Espacio:
    """Un espacio sin orígenes registrados (R15 y R16 no los leen)."""
    return Espacio(ambientes=tuple(ambientes), puntos=tuple(puntos), fuentes=tuple(fuentes))
```
**`tests/fixtures/planos_ifc_ids.py`**
```python
"""El IFC de oficina de SF5 con los requisitos del IDS de Sílice (S3-5, RF-89).

`oficina_ifc4(con=...)` parte de `planos_ifc.crear_ifc("IFC4")` (que NO trae propiedades) y
agrega, a elección, cada uno de los requisitos de `data/ids/silice_instalaciones.ids`:
altura de los espacios, diámetro del aparato sanitario y circuito de la toma de corriente (el
tablero ya trae su nombre). Programático, como los demás (RNF-09).
"""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.api.pset

from tests.fixtures.planos_ifc import crear_ifc

REQUISITOS = ("altura", "diametro", "circuito")


def oficina_ifc4(con: tuple[str, ...] = REQUISITOS) -> ifcopenshell.file:
    modelo = crear_ifc("IFC4")
    if "altura" in con:
        for espacio in modelo.by_type("IfcSpace"):
            qto = ifcopenshell.api.pset.add_qto(
                modelo, product=espacio, name="Qto_SpaceBaseQuantities"
            )
            ifcopenshell.api.pset.edit_qto(modelo, qto=qto, properties={"Height": 2.8})
    if "diametro" in con:
        for aparato in modelo.by_type("IfcSanitaryTerminal"):
            pset = ifcopenshell.api.pset.add_pset(modelo, product=aparato, name="Silice_Hoja")
            ifcopenshell.api.pset.edit_pset(modelo, pset=pset, properties={"DiametroNominal": 0.05})
    if "circuito" in con:
        for toma in modelo.by_type("IfcOutlet"):
            if toma.PredefinedType == "POWEROUTLET":
                pset = ifcopenshell.api.pset.add_pset(modelo, product=toma, name="Silice_Hoja")
                ifcopenshell.api.pset.edit_pset(modelo, pset=pset, properties={"Circuito": "C1"})
    return modelo
```
**`tests/unit/test_r15_geometria_plano.py`**
```python
"""R15: coherencia geométrica del plano, con las fronteras exactas de S3 §11.3 (RF-89)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from adapters.espacio.planos.dxf import importar_dxf
from adapters.espacio.planos.geometria_plano import CODIGO_R15, CoherenciaGeometrica, reglas_plano
from adapters.espacio.reglas import CoherenciaEspacial
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Severidad
from tests.fixtures.espacio_minimo import ambiente, espacio, punto_de_datos, rack
from tests.fixtures.espacio_of001 import espacio_of001

RUTA_OF001_DXF = Path(__file__).resolve().parents[1] / "fixtures" / "planos" / "of001.dxf"
PRESUPUESTO = Presupuesto(codigo="X", fecha=date(2026, 11, 1), moneda="USD", partidas=())


def r15(e):
    return CoherenciaGeometrica(e).evaluar(PRESUPUESTO)


# --- superposición (ERROR; 0,0100 m2 pasa, 0,0101 m2 falla) ---------------------------------


def test_superposicion_de_0_0100_m2_pasa() -> None:
    a, b = ambiente("A", largo="1", ancho="1"), ambiente("B", x0="0.99", largo="1", ancho="1")
    assert r15(espacio([a, b])) == []


def test_superposicion_de_0_0101_m2_falla_con_error_y_cita_los_dos_ambientes() -> None:
    a, b = ambiente("A", largo="1", ancho="1"), ambiente("B", x0="0.9899", largo="1", ancho="1")
    [h] = r15(espacio([a, b]))
    assert (h.regla, h.severidad) == (CODIGO_R15, Severidad.ERROR)
    assert h.origen_ids == ("esp_ambientes:A", "esp_ambientes:B")
    assert (h.valor_observado, h.valor_esperado) == (Decimal("0.0101"), Decimal("0.01"))


def test_ambientes_que_solo_se_tocan_o_estan_separados_no_se_superponen() -> None:
    a = ambiente("A", largo="1", ancho="1")
    juntos, lejos = ambiente("B", x0="1", largo="1", ancho="1"), ambiente("C", x0="5")
    assert r15(espacio([a, juntos, lejos])) == []


def test_la_superposicion_se_mide_en_las_dos_direcciones() -> None:
    a = ambiente("A", largo="2", ancho="2")
    b = ambiente("B", x0="1.9", y0="1.9", largo="2", ancho="2")  # 0,1 x 0,1 = 0,01: pasa
    c = ambiente("C", x0="1.89", y0="1.89", largo="2", ancho="2")  # 0,11 x 0,11 = 0,0121
    assert r15(espacio([a, b])) == []
    [h] = r15(espacio([a, c]))
    assert h.valor_observado == Decimal("0.0121")


# --- puntos duplicados (ERROR; 0,0010 m pasa, 0,0009 m falla) ----------------------------------


def test_dos_puntos_a_0_0010_m_pasan() -> None:
    puntos = [punto_de_datos("P1", "1"), punto_de_datos("P2", "1.001")]
    assert r15(espacio([ambiente("A")], puntos)) == []


def test_dos_puntos_a_0_0009_m_son_duplicados() -> None:
    e = espacio([ambiente("A")], [punto_de_datos("P1", "1"), punto_de_datos("P2", "1.0009")])
    [h] = r15(e)
    assert h.severidad is Severidad.ERROR and h.origen_ids == ("esp_puntos:P1", "esp_puntos:P2")
    assert h.valor_observado == Decimal("0.0009")


def test_puntos_de_otro_tipo_en_el_mismo_sitio_no_son_duplicados() -> None:
    from tests.fixtures.espacio_minimo import toma

    e = espacio([ambiente("A")], [punto_de_datos("P1", "1"), toma("T1", "1")])
    assert r15(e) == []


def test_el_duplicado_se_mide_en_tres_dimensiones() -> None:
    e = espacio([ambiente("A")], [punto_de_datos("P1", "1", z="0.3"),
                                  punto_de_datos("P2", "1", z="0.3009")])
    assert len(r15(e)) == 1


# --- escala imposible (ADVERTENCIA) ------------------------------------------------------------


@pytest.mark.parametrize("lado,falla", [("0.300", False), ("0.299", True), ("200.000", False),
                                        ("200.001", True)])
def test_el_lado_de_un_ambiente_tiene_fronteras_inclusivas(lado: str, falla: bool) -> None:
    hallazgos = r15(espacio([ambiente("A", largo=lado, ancho="1")]))
    assert bool(hallazgos) is falla
    if falla:
        assert hallazgos[0].severidad is Severidad.ADVERTENCIA
        assert "largo" in hallazgos[0].descripcion


@pytest.mark.parametrize("alto,falla", [("2.000", False), ("1.999", True), ("12.000", False),
                                        ("12.001", True)])
def test_la_altura_de_un_ambiente_tiene_fronteras_inclusivas(alto: str, falla: bool) -> None:
    hallazgos = r15(espacio([ambiente("A", alto=alto)]))
    assert bool(hallazgos) is falla
    if falla:
        assert hallazgos[0].severidad is Severidad.ADVERTENCIA
        assert "altura" in hallazgos[0].descripcion


# --- punto lejos de su fuente (ADVERTENCIA; 100,000 m pasa, 100,001 m falla) -------------------


@pytest.mark.parametrize("x,falla", [("100", False), ("100.001", True)])
def test_la_distancia_a_la_fuente(x: str, falla: bool) -> None:
    e = espacio([ambiente("A", largo="200")], [punto_de_datos("P1", x, y="0", z="0", fuente="R1")],
                [rack("R1", "0", "0", "0")])
    hallazgos = r15(e)
    assert bool(hallazgos) is falla
    if falla:
        assert hallazgos[0].severidad is Severidad.ADVERTENCIA
        assert hallazgos[0].origen_ids == ("esp_puntos:P1", "esp_fuentes:R1")


def test_un_punto_sin_fuente_no_se_mide() -> None:
    assert r15(espacio([ambiente("A", largo="200")], [punto_de_datos("P1", "150")])) == []


# --- R15 no repite R9 y no inventa hallazgos en el caso limpio ---------------------------------


def test_un_punto_fuera_de_su_ambiente_es_de_r9_y_no_de_r15() -> None:
    e = espacio([ambiente("A", largo="2", ancho="2")], [punto_de_datos("P1", "9", y="9")])
    assert r15(e) == [] and CoherenciaEspacial(e).evaluar(PRESUPUESTO) != []


def test_of001_limpio_no_da_hallazgos_de_r15_ni_en_la_hoja_ni_en_el_dxf() -> None:
    assert r15(espacio_of001()) == []
    importado = importar_dxf(RUTA_OF001_DXF)
    assert r15(importado.espacio()) == []


def test_reglas_plano_devuelve_solo_r15() -> None:
    reglas = reglas_plano(espacio([ambiente("A")]))
    assert [r.codigo for r in reglas] == [CODIGO_R15]


def test_el_orden_de_los_hallazgos_es_estable() -> None:
    e = espacio(
        [ambiente("B", largo="0.2"), ambiente("A", largo="0.2")],
        [punto_de_datos("P2", "1.0001"), punto_de_datos("P1", "1")],
    )
    assert [h.descripcion for h in r15(e)] == [h.descripcion for h in r15(e)]
```
**`tests/unit/test_planos_auditoria_s3.py`**
```python
"""Auditoría de archivo DXF, IDS del IFC y espacio como JSON (RF-89; spec S3 §11.1, §11.2, §6.2)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import ezdxf
import pytest

from adapters.espacio import Espacio
from adapters.espacio.planos import ids as modulo_ids
from adapters.espacio.planos.auditoria_archivo import auditar_archivo, texto_del_informe
from adapters.espacio.planos.dxf import importar_dxf
from adapters.espacio.planos.ids import MENSAJE_SIN_MODULO, RUTA_IDS, auditar_ids
from adapters.espacio.planos.informe import EstadoImportacion, TipoItem
from adapters.espacio.serie import (
    LIMITE_AMBIENTES,
    LIMITE_PUNTOS,
    LIMITE_VERTICES_POR_TRAMO,
    LimiteExcedido,
    comprobar_limites,
    espacio_a_objeto,
    espacio_desde_objeto,
)
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.planos_ifc_ids import oficina_ifc4
from tests.fixtures.sin_extra import SinExtra

RAIZ = Path(__file__).resolve().parents[2]
OF001 = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"


# --- DXF dañado (UC-14d) --------------------------------------------------------------------


def _dxf_con_tipo_de_linea_inexistente() -> bytes:
    """Un plano de la convención de capas con una línea de un tipo de línea que no existe: la
    biblioteca lo arregla al leer con recuperación."""
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    doc.layers.add("AMBIENTES")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (4, 0), (4, 3), (0, 3)], close=True,
                       dxfattribs={"layer": "AMBIENTES"})
    msp.add_line((0, 0), (1, 1), dxfattribs={"layer": "OTRA", "linetype": "NO_EXISTE"})
    flujo = io.StringIO()
    doc.write(flujo)
    return flujo.getvalue().encode("utf-8")


def test_un_plano_limpio_no_tiene_nada_que_reparar() -> None:
    _, auditoria = auditar_archivo(OF001)
    assert auditoria.limpia and texto_del_informe(auditoria) == []


def test_of001_importa_igual_que_antes_sin_items_nuevos() -> None:
    importado = importar_dxf(OF001)
    assert importado.estado is EstadoImportacion.IMPORTADA
    assert importado.conteos[TipoItem.APROXIMADO] == 9  # los 9 de siempre, ninguno de auditoría
    assert not [i for i in importado.informe if i.tabla == "dxf"]


def test_lo_que_ezdxf_repara_se_informa_y_el_plano_se_importa() -> None:
    importado = importar_dxf(_dxf_con_tipo_de_linea_inexistente(), unidades="m")
    reparado = [i for i in importado.informe if i.tabla == "dxf"]
    assert importado.estado is EstadoImportacion.IMPORTADA
    assert len(reparado) == 1 and reparado[0].tipo is TipoItem.APROXIMADO
    assert "se repararon" in reparado[0].mensaje and "no_existe" in reparado[0].mensaje.lower()


def test_un_archivo_irrecuperable_se_rechaza_con_su_mensaje_y_sin_traza() -> None:
    rechazado = importar_dxf(b"\x00\x01 esto no es un DXF " * 20, nombre="malo.dxf")
    assert rechazado.estado is EstadoImportacion.RECHAZADA
    assert "malo.dxf: no se pudo leer como DXF" in rechazado.mensaje
    assert "Traceback" not in rechazado.mensaje and len(rechazado.mensaje) < 300


def test_el_informe_cuenta_los_errores_y_cita_solo_los_primeros() -> None:
    from adapters.espacio.planos.auditoria_archivo import Auditoria

    texto = texto_del_informe(Auditoria(reparaciones=tuple(f"fallo {i}" for i in range(8))))[0]
    assert texto.startswith("el plano tenia 8 errores de estructura que se repararon")
    assert "fallo 4" in texto and "fallo 5" not in texto and "(y 3 mas)" in texto


# --- IDS del IFC ---------------------------------------------------------------------------


def test_el_ids_versionado_es_el_que_genera_el_script() -> None:
    resultado = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "generar_ids_silice.py"), "--comprobar"],
        capture_output=True, text=True, cwd=RAIZ, check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_un_ifc_que_cumple_todo_no_da_items() -> None:
    assert auditar_ids(oficina_ifc4()) == ()


def test_sin_ninguna_propiedad_fallan_los_cuatro_requisitos_con_su_global_id() -> None:
    items = auditar_ids(oficina_ifc4(con=()))
    por_requisito = {}
    for i in items:
        por_requisito.setdefault(i.mensaje.split("»")[0], []).append(i)
    assert {k: len(v) for k, v in por_requisito.items()} == {
        "IDS «Aparato sanitario con diametro": 1,
        "IDS «Espacio con altura": 3,
        "IDS «Tomacorriente con circuito": 1,
    }  # el tablero ya trae su nombre
    assert all(i.tipo is TipoItem.PENDIENTE and i.tabla == "ids" and i.referencia for i in items)
    assert any("lavamanos" in i.mensaje for i in items)


@pytest.mark.parametrize(
    "falta,fragmento",
    [("altura", "Espacio con altura"), ("diametro", "Aparato sanitario"),
     ("circuito", "Tomacorriente")],
)
def test_un_fallo_por_requisito(falta: str, fragmento: str) -> None:
    con = tuple(r for r in ("altura", "diametro", "circuito") if r != falta)
    items = auditar_ids(oficina_ifc4(con=con))
    assert items and all(fragmento in i.mensaje for i in items)


def test_sin_el_modulo_ifc_el_informe_lo_dice_y_no_falla(monkeypatch) -> None:
    """El extra `ifc` ausente de verdad (INV-021): `import ifctester` falla y la importación
    del IFC sigue."""
    modelo = oficina_ifc4()
    with SinExtra(monkeypatch, ("ifctester",), ("ifctester", "ifctester.ids")):
        assert not modulo_ids.ids_disponible()
        [item] = auditar_ids(modelo)
    assert item.mensaje == MENSAJE_SIN_MODULO and modulo_ids.ids_disponible()


def test_un_ifc2x3_recibe_un_item_que_dice_que_el_ids_es_de_ifc4() -> None:
    from tests.fixtures.planos_ifc import crear_ifc

    [item] = auditar_ids(crear_ifc("IFC2X3"))
    assert "solo cubre IFC4" in item.mensaje and "IFC2X3" in item.mensaje


def test_el_ids_existe_y_ifctester_se_importa_de_forma_diferida() -> None:
    assert RUTA_IDS.is_file()
    codigo = "import sys; import adapters.espacio.planos.ids; print('ifctester' in sys.modules)"
    salida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                            cwd=RAIZ, check=True)
    assert salida.stdout.strip() == "False"


# --- el espacio como JSON ------------------------------------------------------------------


def test_el_espacio_de_of001_hace_ida_y_vuelta_exacta() -> None:
    original = espacio_of001()
    objeto = json.loads(json.dumps(espacio_a_objeto(original)))  # pasa por JSON de verdad
    assert espacio_desde_objeto(objeto) == original
    assert Espacio() == espacio_desde_objeto(json.loads(json.dumps(espacio_a_objeto(Espacio()))))


def test_las_cifras_del_espacio_se_validan_con_la_funcion_que_se_inyecta() -> None:
    from seguridad.json_estricto import JsonRechazado, a_decimal

    objeto = espacio_a_objeto(espacio_of001())
    assert espacio_desde_objeto(objeto, a_decimal) == espacio_of001()
    objeto["ambientes"][0]["largo"] = "1E+5"
    with pytest.raises(JsonRechazado):
        espacio_desde_objeto(objeto, a_decimal)
    assert Decimal("1E+5") == Decimal(100000)  # el Decimal corriente sí la tragaría


@pytest.mark.parametrize(
    "clave,tope", [("ambientes", LIMITE_AMBIENTES), ("puntos", LIMITE_PUNTOS)]
)
def test_los_limites_del_anexo_de_espacio_en_su_frontera(clave: str, tope: int) -> None:
    comprobar_limites({clave: [{}] * tope})  # pasa
    with pytest.raises(LimiteExcedido, match=str(tope)):
        comprobar_limites({clave: [{}] * (tope + 1)})


def test_mil_vertices_por_tramo_pasan_y_mil_uno_se_rechaza() -> None:
    def con(n: int) -> dict:
        return {"recorridos": [{"tramos": [{"vertices": [["0", "0", "0"]] * n}]}]}

    comprobar_limites(con(LIMITE_VERTICES_POR_TRAMO))
    with pytest.raises(LimiteExcedido, match="vertices"):
        comprobar_limites(con(LIMITE_VERTICES_POR_TRAMO + 1))


def test_un_anexo_incompleto_es_un_value_error_con_mensaje() -> None:
    with pytest.raises(ValueError, match="incompleto"):
        espacio_desde_objeto({"ambientes": [{"id": "A"}]})


def test_la_importacion_del_ifc_trae_los_items_del_ids_con_el_globalid() -> None:
    from adapters.espacio.planos.ifc import importar_ifc

    contenido = oficina_ifc4(con=("altura", "circuito")).to_string().encode("utf-8")
    importado = importar_ifc(contenido, nombre="oficina.ifc")
    ids = [i for i in importado.informe if i.mensaje.startswith("IDS «")]
    assert ids and all("Aparato sanitario con diametro" in i.mensaje for i in ids)
    assert all(i.tipo is TipoItem.PENDIENTE and i.referencia for i in ids)  # con su GlobalId


def test_un_ids_ilegible_no_tumba_la_importacion_y_se_dice(tmp_path) -> None:
    vacio = tmp_path / "vacio.ids"
    vacio.write_bytes(b"")
    [item] = auditar_ids(oficina_ifc4(), vacio)
    assert item.mensaje.startswith("IDS no comprobado: ") and item.tipo is TipoItem.PENDIENTE
```
  La hoja en vivo evalúa R15 con las demás reglas del espacio (dos ambientes que se superponen en
  más de 0,01 m2 dan un ERROR de R15 en el informe de la hoja y en el de la versión recargada):
**`tests/unit/test_hoja_r15.py`**
```python
"""R15 en la hoja en vivo (spec S3 §3.4): se evalúa con R8 a R10 al elaborar el borrador.

La hoja no pasa por la reauditoría del paquete: usa las mismas reglas del espacio, y R15 es una
de ellas desde la 0.8.0. Las fronteras de R15 las prueba `test_r15_geometria_plano`."""

from __future__ import annotations

from datetime import date

from core.contracts.verificacion import Severidad
from tests.fixtures.espacio_minimo import ambiente, espacio
from tests.fixtures.espacio_of001 import espacio_of001
from ui import hoja


def _r15(resultado) -> list:
    return [h for h in resultado.elaboracion.informe.hallazgos if h.regla == "R15"]


def _elaborar(un_espacio):
    return hoja.elaborar_hoja(un_espacio, {}, codigo="H-R15", fecha=date(2026, 11, 1))


def test_dos_ambientes_que_se_superponen_dan_un_error_de_r15_en_el_informe_de_la_hoja() -> None:
    a = ambiente("A", largo="1", ancho="1")
    b = ambiente("B", x0="0.9899", largo="1", ancho="1")  # 0,0101 m2 de superposición
    [hallazgo] = _r15(_elaborar(espacio([a, b])))
    assert hallazgo.severidad is Severidad.ERROR
    assert hallazgo.origen_ids == ("esp_ambientes:A", "esp_ambientes:B")


def test_en_la_frontera_de_0_0100_m2_la_hoja_no_trae_r15() -> None:
    a = ambiente("A", largo="1", ancho="1")
    b = ambiente("B", x0="0.99", largo="1", ancho="1")  # 0,0100 m2: pasa
    assert _r15(_elaborar(espacio([a, b]))) == []


def test_of001_limpio_no_trae_r15_en_la_hoja() -> None:
    assert _r15(_elaborar(espacio_of001())) == []
```
  Los terceros nuevos de cada adaptador y el dueño del script que escribe el IDS:
```diff
--- a/tests/unit/test_arquitectura.py
+++ b/tests/unit/test_arquitectura.py
@@ -33,5 +36,7 @@
     "bcv": frozenset({"xlrd", "openpyxl"}),
     "civil": frozenset({"ifcopenshell"}),
-    "espacio": frozenset({"sqlalchemy", "ezdxf", "ifcopenshell"}),
+    "espacio": frozenset(
+        {"sqlalchemy", "ezdxf", "ifcopenshell", "shapely", "ifctester", "xmlschema"}
+    ),
     "industrial": frozenset(),
     "sistemas": frozenset(),
```
```diff
--- a/tests/unit/test_dependencias_silice.py
+++ b/tests/unit/test_dependencias_silice.py
@@ -34,5 +34,5 @@
 DUENOS_DE_TERCEROS: dict[str, tuple[str, ...]] = {
     "xlrd": ("adapters/bcv/",),
-    "ifctester": ("adapters/espacio/planos/",),
+    "ifctester": ("adapters/espacio/planos/", "scripts/generar_ids_silice.py"),
     "shapely": ("adapters/espacio/planos/",),
     "anthropic": ("asistente/",),
```
  El informe de OF-001 declara R15 (no da hallazgos): la prueba que contaba diez reglas cuenta once:
```diff
--- a/tests/unit/test_caso_of001.py
+++ b/tests/unit/test_caso_of001.py
@@ -165,7 +165,8 @@
 
 
-def test_el_informe_declara_las_diez_reglas(resultado) -> None:
+def test_el_informe_declara_las_once_reglas(resultado) -> None:
+    """R1 a R10 y, desde la 0.8.0, R15 (coherencia geométrica del plano; no da hallazgos)."""
     reglas = [codigo for codigo, _ in resultado.elaboracion.informe.reglas_evaluadas]
-    assert reglas == [f"R{i}" for i in range(1, 11)]
+    assert reglas == [*(f"R{i}" for i in range(1, 11)), "R15"]
 
 
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_r15_geometria_plano.py tests/unit/test_planos_auditoria_s3.py
tests/unit/test_hoja_r15.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named
'adapters.espacio.planos.geometria_plano'` (R15) y `... 'adapters.espacio.planos.ids'` (auditoría);
`test_hoja_r15` FAIL porque el informe de la hoja no trae R15.
```bash
git add tests/fixtures/espacio_minimo.py tests/fixtures/planos_ifc_ids.py \
  tests/unit/test_r15_geometria_plano.py tests/unit/test_planos_auditoria_s3.py \
  tests/unit/test_hoja_r15.py tests/unit/test_arquitectura.py \
  tests/unit/test_dependencias_silice.py tests/unit/test_caso_of001.py
git commit -m "test(planos): R15, auditoria del DXF y requisitos IDS del IFC, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  El espacio como objeto JSON y de vuelta (con los topes de S3 §8.4: 5 000 ambientes, 50 000 puntos,
  1 000 vértices por tramo), la auditoría del archivo DXF y los requisitos IDS:
**`adapters/espacio/serie.py`**
```python
"""El espacio como objeto JSON y de vuelta: `anexos/espacio.json` del paquete (spec S3 §6.2, §8.1).

`espacio_a_objeto` escribe cada `Decimal` como texto posicional exacto y cada colección en el
orden que ya garantiza `Espacio` (por id); `espacio_desde_objeto` es la inversa y recibe la
función que convierte un texto en `Decimal` (`seguridad.json_estricto.a_decimal` en la
reauditoría: el adaptador no importa `seguridad`, y así el patrón estricto vive en un solo lugar).
Antes de construir nada, `comprobar_limites` aplica los topes de S3 §8.4 (5 000 ambientes,
50 000 puntos, 1 000 vértices por tramo), para que R15 con `shapely` no reciba un anexo hostil.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any

from adapters.espacio.modelo import (
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Fuente,
    Punto,
    Recorrido,
    SobrescrituraSegmento,
    Tramo,
)
from adapters.espacio.origen import OrigenMedida

__all__ = [
    "LIMITE_AMBIENTES",
    "LIMITE_PUNTOS",
    "LIMITE_VERTICES_POR_TRAMO",
    "LimiteExcedido",
    "comprobar_limites",
    "espacio_a_objeto",
    "espacio_desde_objeto",
]

LIMITE_AMBIENTES = 5000
LIMITE_PUNTOS = 50_000
LIMITE_VERTICES_POR_TRAMO = 1000


class LimiteExcedido(ValueError):  # noqa: N818
    """El anexo de espacio excede un tope de S3 §8.4; el mensaje dice cuál."""


def _t(valor: Decimal | None) -> str | None:
    return None if valor is None else format(valor, "f")


def _coord(c: Coord) -> list[str]:
    return [format(c.x, "f"), format(c.y, "f"), format(c.z, "f")]


def espacio_a_objeto(espacio: Espacio) -> dict[str, Any]:
    return {
        "origenes": [
            {"id": o.id, "tipo": o.tipo.value, "referencia": dict(o.referencia)}
            for o in espacio.origenes
        ],
        "ambientes": [
            {"id": a.id, "nombre": a.nombre, "x0": _t(a.x0), "y0": _t(a.y0), "largo": _t(a.largo),
             "ancho": _t(a.ancho), "alto": _t(a.alto), "origen_id": a.origen_id}
            for a in espacio.ambientes
        ],
        "fuentes": [
            {"id": f.id, "especialidad": f.especialidad.value, "tipo": f.tipo.value,
             "ambiente_id": f.ambiente_id, "posicion": _coord(f.posicion), "origen_id": f.origen_id}
            for f in espacio.fuentes
        ],
        "circuitos": [
            {"id": c.id, "tablero": c.tablero, "numero": c.numero,
             "conductores": list(c.conductores), "calibre": c.calibre,
             "puntos_maximos": c.puntos_maximos, "orden": list(c.orden)}
            for c in espacio.circuitos
        ],
        "puntos": [
            {"id": p.id, "nombre": p.nombre, "especialidad": p.especialidad.value,
             "tipo": p.tipo.value, "ambiente_id": p.ambiente_id, "superficie": p.superficie.value,
             "posicion": _coord(p.posicion), "fuente_id": p.fuente_id, "circuito_id": p.circuito_id,
             "especificaciones": dict(p.especificaciones), "origen_id": p.origen_id}
            for p in espacio.puntos
        ],
        "recorridos": [
            {"id": r.id, "modo": r.modo.value, "punto_id": r.punto_id,
             "circuito_id": r.circuito_id,
             "tramos": [
                 {"orden": t.orden, "superficie": t.superficie.value, "empotrado": t.empotrado,
                  "pendiente": _t(t.pendiente), "vertices": [_coord(v) for v in t.vertices]}
                 for t in r.tramos
             ]}
            for r in espacio.recorridos
        ],
        "sobrescrituras": [
            {"clave": s.clave, "diametro": s.diametro, "empotrado": s.empotrado}
            for s in espacio.sobrescrituras
        ],
    }


def comprobar_limites(objeto: Mapping[str, Any]) -> None:
    """Los topes de S3 §8.4, ANTES de construir el `Espacio`. `LimiteExcedido` si se pasa uno."""
    ambientes = objeto.get("ambientes", [])
    puntos = objeto.get("puntos", [])
    if len(ambientes) > LIMITE_AMBIENTES:
        raise LimiteExcedido(f"el anexo de espacio trae mas de {LIMITE_AMBIENTES} ambientes")
    if len(puntos) > LIMITE_PUNTOS:
        raise LimiteExcedido(f"el anexo de espacio trae mas de {LIMITE_PUNTOS} puntos")
    for recorrido in objeto.get("recorridos", []):
        for tramo in recorrido.get("tramos", []):
            if len(tramo.get("vertices", [])) > LIMITE_VERTICES_POR_TRAMO:
                raise LimiteExcedido(
                    f"un tramo del anexo de espacio trae mas de {LIMITE_VERTICES_POR_TRAMO} "
                    "vertices"
                )


def espacio_desde_objeto(
    objeto: Mapping[str, Any], a_decimal: Callable[[Any], Decimal] = Decimal
) -> Espacio:
    """El `Espacio` de un objeto leído por el lector estricto. `ValueError` si le falta algo."""
    comprobar_limites(objeto)

    def coord(valor: list[Any]) -> Coord:
        x, y, z = (a_decimal(v) for v in valor)
        return Coord(x, y, z)

    def decimal(valor: Any) -> Decimal | None:
        return None if valor is None else a_decimal(valor)

    try:
        return Espacio(
            origenes=tuple(
                OrigenMedida(id=o["id"], tipo=o["tipo"], referencia=o["referencia"])
                for o in objeto.get("origenes", [])
            ),
            ambientes=tuple(
                Ambiente(
                    id=a["id"], nombre=a["nombre"], x0=a_decimal(a["x0"]), y0=a_decimal(a["y0"]),
                    largo=a_decimal(a["largo"]), ancho=a_decimal(a["ancho"]),
                    alto=a_decimal(a["alto"]), origen_id=a["origen_id"],
                )
                for a in objeto.get("ambientes", [])
            ),
            fuentes=tuple(
                Fuente(id=f["id"], especialidad=f["especialidad"], tipo=f["tipo"],
                       ambiente_id=f["ambiente_id"], posicion=coord(f["posicion"]),
                       origen_id=f["origen_id"])
                for f in objeto.get("fuentes", [])
            ),
            circuitos=tuple(
                Circuito(id=c["id"], tablero=c["tablero"], numero=c["numero"],
                         conductores=tuple(c["conductores"]), calibre=c["calibre"],
                         puntos_maximos=c["puntos_maximos"], orden=tuple(c["orden"]))
                for c in objeto.get("circuitos", [])
            ),
            puntos=tuple(
                Punto(id=p["id"], nombre=p["nombre"], especialidad=p["especialidad"],
                      tipo=p["tipo"], ambiente_id=p["ambiente_id"], superficie=p["superficie"],
                      posicion=coord(p["posicion"]), fuente_id=p.get("fuente_id"),
                      circuito_id=p.get("circuito_id"), especificaciones=p["especificaciones"],
                      origen_id=p["origen_id"])
                for p in objeto.get("puntos", [])
            ),
            recorridos=tuple(
                Recorrido(
                    id=r["id"], modo=r["modo"], punto_id=r.get("punto_id"),
                    circuito_id=r.get("circuito_id"),
                    tramos=tuple(
                        Tramo(orden=t["orden"], superficie=t["superficie"],
                              empotrado=t.get("empotrado"), pendiente=decimal(t.get("pendiente")),
                              vertices=tuple(coord(v) for v in t["vertices"]))
                        for t in r.get("tramos", [])
                    ),
                )
                for r in objeto.get("recorridos", [])
            ),
            sobrescrituras=tuple(
                SobrescrituraSegmento(clave=s["clave"], diametro=s.get("diametro"),
                                      empotrado=s.get("empotrado"))
                for s in objeto.get("sobrescrituras", [])
            ),
        )
    except (KeyError, TypeError) as error:
        raise ValueError(f"anexo de espacio incompleto o mal formado: {error!r}") from None
```
**`adapters/espacio/planos/auditoria_archivo.py`**
```python
"""Auditoría de archivo de un DXF dañado, con la lectura con recuperación de `ezdxf` (S3 §11.1).

La importación pasaba por `ezdxf.readfile`, que o abre el archivo o falla, y la auditoría de
`ezdxf` nunca se ejecutaba. Ahora el archivo se lee con `ezdxf.recover.readfile`, que devuelve el
documento y un auditor con lo que arregló y lo que no. Lo que la biblioteca arregló se informa
(el plano sigue siendo importable); lo irrecuperable se rechaza con su mensaje (UC-14d).

No es una validación de seguridad: los analizadores en C++ de DXF/IFC quedan fuera (S3 §12).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import ezdxf
from ezdxf import recover

__all__ = ["Auditoria", "auditar_archivo", "texto_del_informe"]

#: Cuántos mensajes se citan en el informe; el resto se cuenta.
MENSAJES_VISIBLES = 5


@dataclass(frozen=True, slots=True)
class Auditoria:
    """Lo que `ezdxf` arregló (`reparaciones`) y lo que no pudo arreglar (`pendientes`)."""

    reparaciones: tuple[str, ...] = ()
    pendientes: tuple[str, ...] = ()

    @property
    def limpia(self) -> bool:
        return not (self.reparaciones or self.pendientes)


def _mensajes(entradas: Sequence) -> tuple[str, ...]:
    return tuple(" ".join(str(e.message).split()) for e in entradas)


def auditar_archivo(ruta: Path | str):
    """`(documento, Auditoria)` de un DXF con recuperación. Lanza lo que `ezdxf` lance si el
    archivo es irrecuperable (`DXFStructureError`, `OSError`...): el lector lo convierte en un
    rechazo con mensaje."""
    ruta = Path(ruta)
    if ruta.stat().st_size == 0:
        raise ezdxf.DXFStructureError("el archivo esta vacio")
    try:
        documento = ezdxf.readfile(str(ruta))  # el que importa: lectura normal, sin mutarlo
    except Exception:  # noqa: BLE001 - dañado: se reintenta con recuperación
        documento, auditor = recover.readfile(str(ruta))
        if len(documento.modelspace()) == 0:  # nada que rescatar: es un rechazo, no una reparación
            raise ezdxf.DXFStructureError("el archivo esta truncado o no tiene entidades") from None
        return documento, _resumen(auditor)
    # `audit()` borra lo que no entiende (p. ej. un INSERT sin bloque) y el importador sí lo
    # usa: se audita una segunda lectura, solo para informar lo que la biblioteca arreglaría
    return documento, _resumen(ezdxf.readfile(str(ruta)).audit())


def _resumen(auditor) -> Auditoria:
    return Auditoria(
        reparaciones=_mensajes(list(auditor.fixes)), pendientes=_mensajes(list(auditor.errors))
    )


def texto_del_informe(auditoria: Auditoria) -> list[str]:
    """Los ítems del informe de importación (uno por grupo), en lenguaje llano."""
    textos = []
    if auditoria.reparaciones:
        n = len(auditoria.reparaciones)
        citados = "; ".join(auditoria.reparaciones[:MENSAJES_VISIBLES])
        mas = f" (y {n - MENSAJES_VISIBLES} mas)" if n > MENSAJES_VISIBLES else ""
        textos.append(
            f"el plano tenia {n} {'error' if n == 1 else 'errores'} de estructura que se "
            f"repararon: {citados}{mas}"
        )
    if auditoria.pendientes:
        n = len(auditoria.pendientes)
        citados = "; ".join(auditoria.pendientes[:MENSAJES_VISIBLES])
        textos.append(
            f"el plano conserva {n} {'error' if n == 1 else 'errores'} de estructura que la "
            f"biblioteca no pudo reparar: {citados}"
        )
    return textos
```
**`adapters/espacio/planos/ids.py`**
```python
"""Requisitos mínimos de un IFC en IDS (Information Delivery Specification, buildingSMART) con
`ifctester` (spec S3 §11.2).

`data/ids/silice_instalaciones.ids` declara lo mínimo que la hoja necesita y la geometría del
IFC no da: espacio con altura (`Qto_SpaceBaseQuantities.Height`), aparato sanitario con diámetro
nominal, tomacorriente con circuito (propiedades `Silice_Hoja.DiametroNominal` y
`Silice_Hoja.Circuito`: un conjunto propio, porque ningún `Pset_` estándar las trae) y tablero con
nombre. `auditar_ids` valida el modelo y entrega, por cada elemento que falla, un ítem del
informe de importación con su `GlobalId`; lo que falte sigue pendiente y R8 lo marca.

`ifctester` se importa DENTRO de la función (extra `ifc`, RP-6): sin el extra la importación del
IFC sigue funcionando y el informe dice «IDS no comprobado: falta el módulo IFC». El IDS solo
cubre IFC4: un IFC2X3 recibe un ítem que lo dice.
"""

from __future__ import annotations

import os
from pathlib import Path

from adapters.espacio.planos.informe import ItemInforme, TipoItem

__all__ = [
    "MENSAJE_SIN_MODULO",
    "RUTA_IDS",
    "auditar_ids",
    "esquema_sin_red",
    "ids_disponible",
]

RUTA_IDS = Path(__file__).resolve().parents[3] / "data" / "ids" / "silice_instalaciones.ids"
MENSAJE_SIN_MODULO = "IDS no comprobado: falta el módulo IFC (extra `ifc`)"
TABLA = "ids"


def ids_disponible() -> bool:
    try:
        import ifctester  # noqa: F401  (extra `ifc`: importación diferida, RP-6)
    except ImportError:
        return False
    return True


def esquema_sin_red(ids) -> None:
    """Fija el esquema XSD del IDS con `allow="local"`. Sin esto, `ifctester` (vía `xmlschema`)
    intenta descargar de internet el esquema XML que importa `ids.xsd` cada vez que abre un
    archivo: lo atrapó la guardia de red de la suite (RV-17) y violaría RF-98 (ninguna
    conexión saliente) en un equipo sin internet. `xmlschema` trae su propia copia."""
    if getattr(ids, "schema", None) is None:
        from xmlschema import XMLSchema

        local = os.path.join(os.path.dirname(ids.__file__), "ids.xsd")
        ids.schema = XMLSchema(local, allow="local")


def _item(mensaje: str, referencia: str = "") -> ItemInforme:
    return ItemInforme(TipoItem.PENDIENTE, TABLA, referencia, "", mensaje)


def auditar_ids(modelo, ruta_ids: Path | str = RUTA_IDS) -> tuple[ItemInforme, ...]:
    """Los ítems del informe por cada elemento de `modelo` (un `ifcopenshell.file`) que no
    cumple un requisito del IDS. Vacío si todo cumple."""
    if not ids_disponible():
        return (_item(MENSAJE_SIN_MODULO),)
    if str(modelo.schema).upper() != "IFC4":
        return (_item(f"IDS no comprobado: solo cubre IFC4 y este archivo es {modelo.schema}"),)
    from ifctester import ids  # importación diferida: extra `ifc`

    try:
        esquema_sin_red(ids)
        especificaciones = ids.open(str(ruta_ids))
        especificaciones.validate(modelo)
    except Exception as error:  # noqa: BLE001 - una librería ajena no tumba la importación (RNF-12)
        motivo = " ".join(str(error).split())
        return (_item(f"IDS no comprobado: {type(error).__name__}: {motivo}"),)
    items: list[ItemInforme] = []
    for especificacion in especificaciones.specifications:
        for requisito in especificacion.requirements:
            for fallo in requisito.failures:
                elemento = fallo["element"]
                global_id = getattr(elemento, "GlobalId", "") or ""
                nombre = (getattr(elemento, "Name", None) or global_id or "(sin nombre)").strip()
                items.append(
                    _item(
                        f"IDS «{especificacion.name}»: {nombre}: {fallo['reason']}", global_id
                    )
                )
    return tuple(sorted(items, key=lambda i: (i.mensaje, i.referencia)))
```
  El importador del DXF lee con recuperación y cuenta lo que `ezdxf` reparó; el del IFC trae los
  ítems del IDS:
```diff
--- a/adapters/espacio/planos/dxf.py
+++ b/adapters/espacio/planos/dxf.py
@@ -42,6 +42,4 @@
 from decimal import Decimal
 from pathlib import Path
-
-import ezdxf
 
 from adapters.espacio.modelo import (
@@ -62,4 +60,5 @@
 )
 from adapters.espacio.origen import OrigenMedida, TipoOrigen
+from adapters.espacio.planos.auditoria_archivo import Auditoria, auditar_archivo, texto_del_informe
 from adapters.espacio.planos.comun import (
     CALIBRE_PENDIENTE,
@@ -168,20 +167,23 @@
 
 def _abrir(ruta: Path):
+    """`(documento, motivo, auditoria)`: lectura con recuperación y auditoría de `ezdxf` (S3
+    §11.1); lo irrecuperable da `documento = None` y su mensaje en `motivo`."""
     try:
-        return ezdxf.readfile(ruta), ""
+        doc, auditoria = auditar_archivo(ruta)
     except Exception as error:  # noqa: BLE001 - un lector de CAD puede lanzar cualquier cosa
-        return None, f"{type(error).__name__}: {en_una_linea(error)}"
+        return None, f"{type(error).__name__}: {en_una_linea(error)}", Auditoria()
+    return doc, "", auditoria
 
 
 def _leer(contenido: bytes | Path | str, nombre: str | None):
-    """`(documento, archivo, rechazo)`: el documento ezdxf o el resultado de rechazo."""
+    """`(documento, archivo, rechazo, auditoria)`: el documento ezdxf o el resultado de rechazo."""
     if isinstance(contenido, bytes | bytearray):
         archivo = nombre or "plano.dxf"
         if len(contenido) > LIMITE_BYTES:
-            return None, archivo, _demasiado_grande(archivo, len(contenido))
+            return None, archivo, _demasiado_grande(archivo, len(contenido)), Auditoria()
         with tempfile.TemporaryDirectory() as carpeta:
             ruta = Path(carpeta) / "plano.dxf"
             ruta.write_bytes(bytes(contenido))
-            doc, motivo = _abrir(ruta)
+            doc, motivo, auditoria = _abrir(ruta)
     else:
         ruta = Path(contenido)
@@ -190,11 +192,11 @@
             tamano = ruta.stat().st_size
         except OSError as error:
-            return None, archivo, _rechazo(archivo, en_una_linea(error))
+            return None, archivo, _rechazo(archivo, en_una_linea(error)), Auditoria()
         if tamano > LIMITE_BYTES:
-            return None, archivo, _demasiado_grande(archivo, tamano)
-        doc, motivo = _abrir(ruta)
+            return None, archivo, _demasiado_grande(archivo, tamano), Auditoria()
+        doc, motivo, auditoria = _abrir(ruta)
     if doc is None:
-        return None, archivo, _rechazo(archivo, motivo)
-    return doc, archivo, None
+        return None, archivo, _rechazo(archivo, motivo), Auditoria()
+    return doc, archivo, None, auditoria
 
 
@@ -818,5 +820,5 @@
     mas entidades que el tope) o `DETENIDA` (falta la unidad, con `pide_unidad`) con su mensaje y
     sin filas."""
-    doc, archivo, rechazo = _leer(contenido, nombre)
+    doc, archivo, rechazo, auditoria = _leer(contenido, nombre)
     if rechazo is not None:
         return rechazo
@@ -852,4 +854,6 @@
     grupos, ajenas, sueltas = _capas(doc)
     lector = _Lector(doc, archivo, factor)
+    for texto in texto_del_informe(auditoria):  # S3 §11.1: lo que `ezdxf` reparó o no pudo
+        lector.acc.item(TipoItem.APROXIMADO, "dxf", texto)
     for tabla, e, mensaje in sueltas:
         lector._no_reconocido(tabla, e, mensaje)
```
```diff
--- a/adapters/espacio/planos/ifc.py
+++ b/adapters/espacio/planos/ifc.py
@@ -63,4 +63,5 @@
     superficie_de,
 )
+from adapters.espacio.planos.ids import auditar_ids
 from adapters.espacio.planos.informe import EstadoImportacion, ResultadoImportacion, TipoItem
 
@@ -563,4 +564,5 @@
     lector.pendientes()
     acc = lector.acc
+    acc.informe.extend(auditar_ids(modelo))  # S3 §11.2: lo que el IDS exige y el IFC no trae
     if not (acc.ambientes or acc.fuentes or acc.puntos):
         return acc.resultado(
```
  El IDS versionado y el script determinista que lo escribe (`--comprobar` falla si difieren); su
  fila de `scripts/README.md`:
```markdown
| `generar_ids_silice.py` | escribe (o con `--comprobar`, verifica)
↳ `data/ids/silice_instalaciones.ids`, los requisitos IDS del IFC | 0.8.0 |
```
**`scripts/generar_ids_silice.py`**
```python
"""Genera `data/ids/silice_instalaciones.ids` (spec S3 §11.2). Determinista: sin fecha del reloj.

Uso: `uv run --extra ifc python scripts/generar_ids_silice.py` (escribe el archivo) o
`... --comprobar` (sale 1 si el archivo versionado difiere del que se generaría).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
DESTINO = RAIZ / "data" / "ids" / "silice_instalaciones.ids"
FECHA = "2026-10-11"  # fija: el archivo versionado no cambia entre corridas


def generar() -> str:
    from ifctester import ids

    from adapters.espacio.planos.ids import esquema_sin_red

    esquema_sin_red(ids)
    conjunto = ids.Ids(
        title="Silice: requisitos minimos de una instalacion", version="1.0", date=FECHA,
        author="silice@invalid.example",
        description="Lo que la hoja de metrajes necesita y la geometria de un IFC no da.",
    )

    def especificacion(nombre: str, descripcion: str, aplica, requisito):
        espec = ids.Specification(
            name=nombre, ifcVersion=["IFC4"], minOccurs=0, maxOccurs="unbounded",
            description=descripcion,
        )
        espec.applicability.append(aplica)
        espec.requirements.append(requisito)
        conjunto.specifications.append(espec)

    especificacion(
        "Espacio con altura", "La altura del espacio, para las cantidades verticales.",
        ids.Entity(name="IFCSPACE"),
        ids.Property(propertySet="Qto_SpaceBaseQuantities", baseName="Height",
                     cardinality="required"),
    )
    especificacion(
        "Aparato sanitario con diametro", "El diametro nominal de la tuberia que lo sirve.",
        ids.Entity(name="IFCSANITARYTERMINAL"),
        ids.Property(propertySet="Silice_Hoja", baseName="DiametroNominal",
                     cardinality="required"),
    )
    especificacion(
        "Tomacorriente con circuito", "El circuito al que pertenece, para agrupar los puntos.",
        ids.Entity(name="IFCOUTLET", predefinedType="POWEROUTLET"),
        ids.Property(propertySet="Silice_Hoja", baseName="Circuito", cardinality="required"),
    )
    especificacion(
        "Tablero con nombre", "El nombre del tablero, que es la fuente de sus circuitos.",
        ids.Entity(name="IFCELECTRICDISTRIBUTIONBOARD"),
        ids.Attribute(name="Name", cardinality="required"),
    )
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    conjunto.to_xml(str(DESTINO))
    return DESTINO.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comprobar", action="store_true")
    args = parser.parse_args(argv)
    previo = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else None
    nuevo = generar()
    if args.comprobar and previo != nuevo:
        DESTINO.write_text(previo or "", encoding="utf-8")
        print("data/ids/silice_instalaciones.ids difiere de lo que generaria el script")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
  y el IDS se **genera**, no se copia (cuatro especificaciones: espacio con altura, aparato
  sanitario con diámetro, tomacorriente con circuito y tablero con nombre; 87 líneas de XML):
Run: `uv run python scripts/generar_ids_silice.py` → escribe `data/ids/silice_instalaciones.ids`;
`uv run python scripts/generar_ids_silice.py --comprobar` → 0.
  R15:
**`adapters/espacio/planos/geometria_plano.py`**
```python
"""R15: coherencia geométrica del plano, con `shapely` como índice espacial (spec S3 §11.3).

`ReglaVerificacion` construida con la instantánea del espacio, como R8 a R10 (DA-SF-8). **Toda
medida y toda comparación salen de las coordenadas `Decimal`** (DA-S3-6): `shapely` trabaja en
coma flotante y solo **propone candidatos** (cajas y puntos cercanos con `STRtree`); cada
hallazgo se decide con aritmética exacta, así que las fronteras (0,0100 m² pasa, 0,0101 m² falla)
no dependen del redondeo de un `float`.

| Condición | Severidad | Pasa | Falla |
|---|---|---|---|
| dos ambientes se superponen en más de 0,01 m² | ERROR | 0,0100 m² | 0,0101 m² |
| dos puntos de la misma especialidad y tipo a menos de 0,001 m | ERROR | 0,0010 m | 0,0009 m |
| lado de ambiente < 0,30 m o > 200 m | ADVERTENCIA | 0,300 y 200,000 | 0,299 y 200,001 |
| altura de ambiente < 2,00 m o > 12 m | ADVERTENCIA | 2,000 y 12,000 | 1,999 y 12,001 |
| punto a más de 100 m de su fuente | ADVERTENCIA | 100,000 m | 100,001 m |

Las dos primeras son tolerancias geométricas del sistema y son ERROR; las tres últimas dependen de
umbrales SUPUESTOS (sin fuente normativa, a verificar) y por eso son ADVERTENCIA desde el diseño,
como R10. R15 no repite R9: un punto fuera de su ambiente o un recorrido imposible es de R9.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from shapely.geometry import Point, box
from shapely.strtree import STRtree

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from adapters.espacio.modelo import Ambiente, Espacio, Punto
from adapters.espacio.origen import clave_esp
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "CODIGO_R15",
    "CONSTANTES_R15",
    "CoherenciaGeometrica",
    "reglas_plano",
]

CODIGO_R15 = "R15"

SUPERPOSICION_MAXIMA = Constante(
    "R15-superposicion", "Superposición máxima entre ambientes (m2)", Decimal("0.01"),
    "tolerancia geométrica del sistema",
)
DUPLICADO_MENOR_QUE = Constante(
    "R15-duplicado", "Distancia bajo la cual dos puntos son duplicados (m)", Decimal("0.001"),
    "tolerancia geométrica del sistema (adapters.espacio.modelo.TOLERANCIA)",
)
LADO_MINIMO = Constante("R15-lado-min", "Lado mínimo de un ambiente (m)", Decimal("0.30"),
                        SUPUESTO_DECLARADO)
LADO_MAXIMO = Constante("R15-lado-max", "Lado máximo de un ambiente (m)", Decimal("200"),
                        SUPUESTO_DECLARADO)
ALTURA_MINIMA = Constante("R15-alto-min", "Altura mínima de un ambiente (m)", Decimal("2.00"),
                          SUPUESTO_DECLARADO)
ALTURA_MAXIMA = Constante("R15-alto-max", "Altura máxima de un ambiente (m)", Decimal("12"),
                          SUPUESTO_DECLARADO)
DISTANCIA_A_LA_FUENTE = Constante(
    "R15-fuente", "Distancia máxima de un punto a su fuente (m)", Decimal("100"),
    SUPUESTO_DECLARADO,
)
CONSTANTES_R15 = (SUPERPOSICION_MAXIMA, DUPLICADO_MENOR_QUE, LADO_MINIMO, LADO_MAXIMO,
                  ALTURA_MINIMA, ALTURA_MAXIMA, DISTANCIA_A_LA_FUENTE)


def _n(valor: Decimal) -> str:
    return format(valor.normalize(), "f")


def _hallazgo(
    severidad: Severidad, origen: tuple[str, ...], descripcion: str,
    observado: Decimal | None = None, esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=CODIGO_R15, severidad=severidad, descripcion=descripcion, origen_ids=origen,
        valor_observado=observado, valor_esperado=esperado,
    )


def _caja(a: Ambiente):
    return box(float(a.x0), float(a.y0), float(a.x0 + a.largo), float(a.y0 + a.ancho))


def _superposiciones(espacio: Espacio) -> list[Hallazgo]:
    ambientes = espacio.ambientes
    if len(ambientes) < 2:
        return []
    cajas = [_caja(a) for a in ambientes]
    arbol = STRtree(cajas)
    parejas = sorted(
        {tuple(sorted((int(i), int(j)))) for i, caja in enumerate(cajas)
         for j in arbol.query(caja) if int(j) != i}
    )
    limite = Decimal(SUPERPOSICION_MAXIMA.valor)
    hallazgos = []
    for i, j in parejas:
        a, b = ambientes[i], ambientes[j]
        ancho_x = min(a.x0 + a.largo, b.x0 + b.largo) - max(a.x0, b.x0)
        ancho_y = min(a.y0 + a.ancho, b.y0 + b.ancho) - max(a.y0, b.y0)
        area = ancho_x * ancho_y if ancho_x > 0 and ancho_y > 0 else Decimal(0)
        if area > limite:
            hallazgos.append(_hallazgo(
                Severidad.ERROR,
                (clave_esp("esp_ambientes", a.id), clave_esp("esp_ambientes", b.id)),
                f"ambientes {a.id} y {b.id}: se superponen en {_n(area)} m2, mas de "
                f"{_n(limite)} m2",
                area, limite,
            ))
    return hallazgos


def _duplicados(espacio: Espacio) -> list[Hallazgo]:
    grupos: dict[tuple[str, str], list[Punto]] = defaultdict(list)
    for p in espacio.puntos:
        grupos[(p.especialidad.value, p.tipo.value)].append(p)
    minimo = Decimal(DUPLICADO_MENOR_QUE.valor)
    cuadrado = minimo * minimo
    radio = float(minimo) * 1.01 + 1e-9
    hallazgos = []
    for _, puntos in sorted(grupos.items()):
        if len(puntos) < 2:
            continue
        geometrias = [Point(float(p.posicion.x), float(p.posicion.y)) for p in puntos]
        arbol = STRtree(geometrias)
        vistos: set[tuple[int, int]] = set()
        for i, geometria in enumerate(geometrias):
            for j in arbol.query(geometria.buffer(radio)):
                j = int(j)
                if j <= i or (i, j) in vistos:
                    continue
                vistos.add((i, j))
                a, b = puntos[i], puntos[j]
                d = b.posicion
                distancia2 = ((a.posicion.x - d.x) ** 2 + (a.posicion.y - d.y) ** 2
                              + (a.posicion.z - d.z) ** 2)
                if distancia2 < cuadrado:
                    distancia = a.posicion.distancia(b.posicion)
                    hallazgos.append(_hallazgo(
                        Severidad.ERROR,
                        (clave_esp("esp_puntos", a.id), clave_esp("esp_puntos", b.id)),
                        f"puntos {a.id} y {b.id}: duplicados a {_n(distancia)} m, menos de "
                        f"{_n(minimo)} m",
                        distancia, minimo,
                    ))
    return sorted(hallazgos, key=lambda h: h.origen_ids)


def _escala(espacio: Espacio) -> list[Hallazgo]:
    hallazgos = []
    lado_min, lado_max = Decimal(LADO_MINIMO.valor), Decimal(LADO_MAXIMO.valor)
    alto_min, alto_max = Decimal(ALTURA_MINIMA.valor), Decimal(ALTURA_MAXIMA.valor)
    for a in espacio.ambientes:
        clave = (clave_esp("esp_ambientes", a.id),)
        for nombre, lado in (("largo", a.largo), ("ancho", a.ancho)):
            if not lado_min <= lado <= lado_max:
                hallazgos.append(_hallazgo(
                    Severidad.ADVERTENCIA, clave,
                    f"ambiente {a.id}: {nombre} de {_n(lado)} m fuera de [{_n(lado_min)}; "
                    f"{_n(lado_max)}] m (escala imposible; supuesto declarado)",
                    lado, lado_min if lado < lado_min else lado_max,
                ))
        if not alto_min <= a.alto <= alto_max:
            hallazgos.append(_hallazgo(
                Severidad.ADVERTENCIA, clave,
                f"ambiente {a.id}: altura de {_n(a.alto)} m fuera de [{_n(alto_min)}; "
                f"{_n(alto_max)}] m (escala imposible; supuesto declarado)",
                a.alto, alto_min if a.alto < alto_min else alto_max,
            ))
    return hallazgos


def _lejos_de_la_fuente(espacio: Espacio) -> list[Hallazgo]:
    fuentes = {f.id: f for f in espacio.fuentes}
    maximo = Decimal(DISTANCIA_A_LA_FUENTE.valor)
    hallazgos = []
    for p in espacio.puntos:
        fuente = fuentes.get(p.fuente_id) if p.fuente_id is not None else None
        if fuente is None:
            continue
        d, q = p.posicion, fuente.posicion
        if (d.x - q.x) ** 2 + (d.y - q.y) ** 2 + (d.z - q.z) ** 2 > maximo * maximo:
            distancia = p.posicion.distancia(fuente.posicion)
            hallazgos.append(_hallazgo(
                Severidad.ADVERTENCIA,
                (clave_esp("esp_puntos", p.id), clave_esp("esp_fuentes", fuente.id)),
                f"punto {p.id}: a {_n(distancia)} m de su fuente {fuente.id}, mas de "
                f"{_n(maximo)} m (supuesto declarado)",
                distancia, maximo,
            ))
    return hallazgos


class CoherenciaGeometrica(ReglaVerificacion):
    """R15: el plano no se superpone, no duplica puntos y tiene una escala posible."""

    codigo = CODIGO_R15
    nombre = "Coherencia geométrica del plano"

    def __init__(self, espacio: Espacio) -> None:
        self.espacio = espacio

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return [
            *_superposiciones(self.espacio),
            *_duplicados(self.espacio),
            *_escala(self.espacio),
            *_lejos_de_la_fuente(self.espacio),
        ]


def reglas_plano(espacio: Espacio) -> tuple[ReglaVerificacion, ...]:
    """Las reglas de plano para `elaborar(reglas=REGLAS + reglas_espacio(e) + reglas_plano(e))`.
    R16 no entra aquí: necesita una segunda fuente (`planos.contraste.ReglaContraste`)."""
    return (CoherenciaGeometrica(espacio),)
```
  La hoja evalúa R15 con R8 a R10, al elaborar el borrador y al recargar una versión:
```python
from adapters.espacio.planos.geometria_plano import reglas_plano  # junto a reglas_espacio

# elaborar_hoja(...), el argumento `reglas` de elaborar(...):
reglas=(*REGLAS, *reglas_espacio(espacio, escritas), *reglas_plano(espacio)),
# abrir_version(...), el argumento `reglas` de cargar_elaboracion(...):
reglas=(*REGLAS, *reglas_espacio(espacio, cantidades), *reglas_plano(espacio)),
```
- [ ] **Paso 4: Correrlas y ver el verde** (y la suite de planos y de la hoja)
Run: `uv run pytest tests/unit/test_r15_geometria_plano.py tests/unit/test_planos_auditoria_s3.py
tests/unit/test_hoja_r15.py tests/unit/test_planos_dxf.py tests/unit/test_planos_ifc.py
tests/unit/test_hoja.py tests/unit/test_hoja_planos.py tests/unit/test_caso_of001.py
tests/unit/test_arquitectura.py tests/unit/test_dependencias_silice.py -v -W error` → verde.
Run: `uv run python scripts/generar_ids_silice.py --comprobar` → 0. Run: `uv run ruff check adapters
scripts/generar_ids_silice.py` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add adapters/espacio/serie.py adapters/espacio/planos/auditoria_archivo.py \
  adapters/espacio/planos/ids.py adapters/espacio/planos/geometria_plano.py \
  adapters/espacio/planos/dxf.py adapters/espacio/planos/ifc.py scripts/generar_ids_silice.py \
  data/ids/silice_instalaciones.ids ui/hoja.py
git commit -m "feat(planos): DXF con recuperacion, requisitos IDS del IFC y R15 con Decimal" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 12: R16 (contraste entre dos fuentes), su costo y la medición de detección

**Rama:** `inc/080-s3-5-planos`   **Rol:** sf-ingeniero-adaptadores (R16, sembrador),
sf-ingeniero-interfaz (costo y hoja), sf-ingeniero-pruebas (medición) **Archivos:**
- Crear: `adapters/espacio/planos/contraste.py`, `ui/contraste.py`
- Crear: `scripts/sembrar_errores_planos.py`, `scripts/medir_deteccion_planos.py`
- Modificar: `ui/paginas/hoja.py:62-66,638,934-983` (el panel «Contrastar con otro plano»)
- Prueba: `tests/unit/test_r16_contraste.py`, `tests/unit/test_ui_contraste.py`,
  `tests/unit/test_ui_hoja_contraste.py`, `tests/unit/test_deteccion_planos.py`

**Interfaces:**
- Consume: `adapters.espacio.planos.geometria_plano.reglas_plano` (tarea 11),
  `core.budget.comparacion.{Diferencia, FilaPresupuesto, diferencia_entre_versiones}` (tarea 10),
  `tests/fixtures/espacio_minimo`, `tests/fixtures/planos_ifc_ids`,
  `tests/fixtures/errores_planos/{catalogo.md, of001_limpio.py}` (tarea 2) y el DXF de OF-001.
- Produce:
  - `adapters.espacio.planos.contraste`: `class Diferencia`
  - `adapters.espacio.planos.contraste`: `class Contraste`
  - `adapters.espacio.planos.contraste`: `def contrastar(espacio: Espacio, referencia: Espacio)
      -> Contraste`
  - `adapters.espacio.planos.contraste`: `class ReglaContraste(ReglaVerificacion)`
  - `ui.contraste`: `class ResultadoDelContraste`
  - `ui.contraste`: `def precios_de_la_hoja(presupuesto: Presupuesto) -> dict[str, Decimal]`
  - `ui.contraste`: `def filas_derivadas(espacio: Espacio, precios: Mapping[str, Decimal],
      especialidades: Sequence[str]=ESPECIALIDADES) -> tuple[list[FilaPresupuesto], tuple[str,
      ...]]`
  - `ui.contraste`: `def contrastar_con_costo(espacio: Espacio, referencia: Espacio, precios:
      Mapping[str, Decimal], especialidades: Sequence[str]=ESPECIALIDADES) ->
      ResultadoDelContraste`
  - `ui.contraste`: `def texto_del_costo(resultado: ResultadoDelContraste, moneda: str) -> str`
  - `scripts/sembrar_errores_planos.py`: una siembra determinista por `id` del catálogo (semilla
    42).
  - `scripts/medir_deteccion_planos.py [--limpio] [--json]`: la tabla de detección y falsas alarmas.

**R16** (spec S3 §11.4): empareja ambientes, fuentes y puntos de las dos fuentes por especialidad,
tipo y posición con el vecino más cercano, uno a uno y de forma determinista. Distancia <= 0,10 m:
emparejado; > 0,10 m y <= 1,00 m: **desplazado**; más lejos: **faltante** (solo en la referencia) y
**sobrante** (solo en el plano). Es siempre ADVERTENCIA (RP8-9). El costo de la diferencia es
`ui.contraste`: la referencia derivada a partidas contra la del plano, con los precios de la hoja,
por `diferencia_entre_versiones`. Oráculo (memoria `diferencias_s3.md`): sin PB3 el plano cuesta
59,604 USD menos; con PB3 a 0,40 m es «desplazado» y cuesta 2,928 más; el sobrante cuesta lo mismo
con el signo contrario. **La medición** (protocolo `docs/protocolo_deteccion_planos.md`, ya con
huella): siembra cada categoría del catálogo con semilla 42 y cuenta lo detectado y lo que se agrega
sin estar declarado; la meta es 100 % de lo detectable y cero falsas alarmas sobre el plano limpio
de OF-001 y sobre los archivos sembrados. Los tres controles no detectables miden el límite
declarado (H-D9).

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_r16_contraste.py`**
```python
"""R16: contraste entre dos fuentes, con las fronteras exactas de S3 §11.4 (RF-89)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from adapters.espacio.planos.contraste import CODIGO_R16, ReglaContraste, contrastar
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Severidad
from tests.fixtures.espacio_minimo import ambiente, espacio, punto_de_datos, rack, toma

PRESUPUESTO = Presupuesto(codigo="X", fecha=date(2026, 11, 1), moneda="USD", partidas=())


def un_punto(x: str):
    return espacio([ambiente("A", largo="10")], [punto_de_datos("P1", x)])


REFERENCIA = un_punto("1")


@pytest.mark.parametrize("x,tipo", [("1.10", None), ("1.11", "desplazado"), ("2.00", "desplazado"),
                                    ("2.01", "faltante")])
def test_fronteras_de_tolerancia_y_de_radio(x: str, tipo: str | None) -> None:
    """0,10 m emparejado / 0,11 desplazado; 1,00 desplazado / 1,01 faltante y sobrante."""
    contraste = contrastar(un_punto(x), REFERENCIA)
    puntos = [d for d in contraste.diferencias if d.tabla == "esp_puntos"]
    if tipo is None:
        assert puntos == [] and contraste.emparejadas == 2  # el ambiente y el punto
    elif tipo == "desplazado":
        [d] = puntos
        assert (d.tipo, d.id_plano, d.id_referencia) == ("desplazado", "P1", "P1")
        assert d.distancia == Decimal(x) - Decimal("1")
    else:
        assert sorted(d.tipo for d in puntos) == ["faltante", "sobrante"]


def test_un_elemento_borrado_entre_las_dos_fuentes_es_faltante() -> None:
    plano = espacio([ambiente("A", largo="10")], [punto_de_datos("P1", "1")])
    levantamiento = espacio([ambiente("A", largo="10")],
                            [punto_de_datos("P1", "1"), punto_de_datos("P2", "5")])
    [d] = contrastar(plano, levantamiento).diferencias
    assert (d.tipo, d.id_plano, d.id_referencia, d.clase) == (
        "faltante", None, "P2", "datos/datos")


def test_un_elemento_que_solo_esta_en_el_plano_es_sobrante() -> None:
    plano = espacio([ambiente("A", largo="10")],
                    [punto_de_datos("P1", "1"), punto_de_datos("P9", "7")])
    [d] = contrastar(plano, REFERENCIA).diferencias
    assert (d.tipo, d.id_plano, d.id_referencia) == ("sobrante", "P9", None)


def test_el_emparejamiento_es_uno_a_uno_y_por_el_vecino_mas_cercano() -> None:
    plano = espacio([ambiente("A", largo="10")],
                    [punto_de_datos("N1", "1.05"), punto_de_datos("N2", "1.5")])
    levantamiento = espacio([ambiente("A", largo="10")], [punto_de_datos("L1", "1")])
    contraste = contrastar(plano, levantamiento)
    tipos = {(d.tipo, d.id_plano, d.id_referencia) for d in contraste.diferencias}
    assert tipos == {("sobrante", "N2", None)}  # N1 se queda con L1 (0,05 m); N2 sobra


def test_no_se_empareja_entre_clases_distintas() -> None:
    plano = espacio([ambiente("A")], [toma("T1", "1")])
    levantamiento = espacio([ambiente("A")], [punto_de_datos("P1", "1")])
    tipos = sorted(d.tipo for d in contrastar(plano, levantamiento).diferencias)
    assert tipos == ["faltante", "sobrante"]


def test_ambientes_y_fuentes_tambien_se_contrastan() -> None:
    plano = espacio([ambiente("A", x0="0.5")], fuentes=[rack("R1", "0", "0", "0")])
    levantamiento = espacio([ambiente("A")], fuentes=[rack("R1", "0", "0", "0")])
    [d] = contrastar(plano, levantamiento).diferencias
    assert (d.tabla, d.tipo, d.distancia) == ("esp_ambientes", "desplazado", Decimal("0.5"))


def test_el_resultado_no_depende_del_orden_de_las_filas() -> None:
    a = [punto_de_datos("P1", "1"), punto_de_datos("P2", "1.5"), punto_de_datos("P3", "9")]
    b = [punto_de_datos("Q1", "1.02"), punto_de_datos("Q2", "1.6")]
    uno = contrastar(
        espacio([ambiente("A", largo="10")], a), espacio([ambiente("A", largo="10")], b)
    )
    otro = contrastar(espacio([ambiente("A", largo="10")], a[::-1]),
                      espacio([ambiente("A", largo="10")], b[::-1]))
    assert uno == otro


def test_dos_espacios_iguales_no_difieren() -> None:
    assert contrastar(REFERENCIA, REFERENCIA).diferencias == ()


def test_la_regla_da_advertencias_con_la_fila_citada() -> None:
    hallazgos = ReglaContraste(un_punto("1.5"), REFERENCIA, "el levantamiento").evaluar(PRESUPUESTO)
    [h] = hallazgos
    assert (h.regla, h.severidad) == (CODIGO_R16, Severidad.ADVERTENCIA)
    assert h.origen_ids == ("esp_puntos:P1",) and "desplazado 0.5 m" in h.descripcion
    assert "el levantamiento" in h.descripcion
```
**`tests/unit/test_ui_contraste.py`**
```python
"""El costo de R16 contra la memoria a mano `diferencias_s3.md` §3 (S3 §11.4).

Los precios y las cifras son los de la memoria, escritos antes del código. OF-001 solo en la
especialidad de datos para que la cuenta a mano quepa en una página."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from adapters.espacio import Coord, Espacio
from tests.fixtures.espacio_of001 import espacio_of001
from ui.contraste import (
    contrastar_con_costo,
    filas_derivadas,
    precios_de_la_hoja,
    texto_del_costo,
)

D = Decimal
DATOS = ("datos",)
PRECIOS = {
    "DT-CAJA": D("5.00"), "DT-FACEPLATE": D("3.00"), "DT-JACK": D("4.00"), "DT-CERT": D("12.00"),
    "DT-UTP-CAT-6": D("1.20"), "DT-CAN-EMT-3/4": D("6.00"), "DT-CAN-EMT-1/2": D("4.50"),
}


def _sin(espacio: Espacio, punto: str) -> Espacio:
    return replace(espacio, puntos=tuple(p for p in espacio.puntos if p.id != punto))


def _mover(espacio: Espacio, punto: str, y: str) -> Espacio:
    return replace(espacio, puntos=tuple(
        replace(p, posicion=Coord(p.posicion.x, D(y), p.posicion.z)) if p.id == punto else p
        for p in espacio.puntos))


def _datos(espacio: Espacio, precios=PRECIOS):
    return filas_derivadas(espacio, precios, ("datos",))[0]


def test_las_cantidades_de_la_referencia_son_las_de_la_memoria_de_of001() -> None:
    cantidades = {f.codigo_partida: f.cantidad for f in _datos(espacio_of001())}
    assert cantidades == {
        "DT-CAJA": 7, "DT-FACEPLATE": 7, "DT-JACK": 7, "DT-CERT": 7,
        "DT-UTP-CAT-6": D("101.640"), "DT-CAN-EMT-1/2": D("8.2"), "DT-CAN-EMT-3/4": D("23.2"),
    }


def _costo(plano: Espacio, referencia: Espacio):
    r = contrastar_con_costo(plano, referencia, PRECIOS, DATOS)
    return r, r.costo.total_2 - r.costo.total_1


def test_escenario_a_el_plano_sin_pb3_cuesta_menos_59_604() -> None:
    of001 = espacio_of001()
    resultado, total = _costo(_sin(of001, "PB3"), of001)
    assert total == D("-59.604")
    por_partida = {p.codigo_partida: p.desvio_total for p in resultado.costo.partidas}
    assert por_partida["DT-UTP-CAT-6"] == D("-19.404")
    assert por_partida["DT-CAN-EMT-3/4"] == D("-16.2")
    assert sum(por_partida[c] for c in ("DT-CAJA", "DT-FACEPLATE", "DT-JACK", "DT-CERT")) == -24
    assert por_partida["DT-CAN-EMT-1/2"] == 0
    [diferencia] = resultado.contraste.diferencias
    assert (diferencia.tipo, diferencia.id_referencia, diferencia.id_plano) == (
        "faltante", "PB3", None)
    assert resultado.contraste.emparejadas == 32 and resultado.sin_precio == ()


def test_escenario_b_pb3_a_0_40_m_es_desplazado_y_cuesta_2_928_mas() -> None:
    of001 = espacio_of001()
    resultado, total = _costo(_mover(of001, "PB3", "5.9"), of001)
    assert total == D("2.928")
    [diferencia] = resultado.contraste.diferencias
    assert (diferencia.tipo, diferencia.distancia) == ("desplazado", D("0.4"))


def test_escenario_c_el_sobrante_cuesta_lo_mismo_con_el_signo_contrario() -> None:
    of001 = espacio_of001()
    resultado, total = _costo(of001, _sin(of001, "PB3"))
    assert total == D("59.604")
    [diferencia] = resultado.contraste.diferencias
    assert (diferencia.tipo, diferencia.id_plano, diferencia.id_referencia) == (
        "sobrante", "PB3", None)


def test_dos_espacios_iguales_no_cuestan_nada_ni_tienen_diferencias() -> None:
    of001 = espacio_of001()
    resultado, total = _costo(of001, of001)
    assert total == 0 and resultado.contraste.diferencias == ()


def test_una_partida_sin_precio_no_suma_y_se_lista() -> None:
    of001 = espacio_of001()
    sin_cable = {c: p for c, p in PRECIOS.items() if c != "DT-UTP-CAT-6"}
    resultado = contrastar_con_costo(_sin(of001, "PB3"), of001, sin_cable, DATOS)
    assert resultado.sin_precio[0] == "DT-UTP-CAT-6"
    assert resultado.costo.total_2 - resultado.costo.total_1 == D("-40.200")  # -24.000 - 16.200


def test_el_texto_del_costo_dice_el_signo_el_monto_y_lo_que_no_se_valoro() -> None:
    of001 = espacio_of001()
    resultado = contrastar_con_costo(_sin(of001, "PB3"), of001, PRECIOS, DATOS)
    assert texto_del_costo(resultado, "USD") == (
        "El plano cuesta menos: -59,60 USD respecto de la otra fuente.")
    asimetrico = contrastar_con_costo(of001, _sin(of001, "PB3"), PRECIOS, DATOS)
    assert "cuesta más: 59,60 USD" in texto_del_costo(asimetrico, "USD")
    sin_cable = contrastar_con_costo(of001, of001, {}, DATOS)
    assert "cuesta igual" in texto_del_costo(sin_cable, "USD") and "DT-CAJA" in texto_del_costo(
        sin_cable, "USD")


def test_los_precios_de_la_hoja_salen_de_las_partidas_valoradas() -> None:
    from types import SimpleNamespace as N

    presupuesto = N(partidas=(
        N(item=N(codigo_partida="X-1"), resultado=N(precio_unitario=D("1.5"))),
        N(item=N(codigo_partida="X-2"), resultado=N(precio_unitario=D("2")))))
    assert precios_de_la_hoja(presupuesto) == {"X-1": D("1.5"), "X-2": D("2")}


@pytest.mark.parametrize("y,tipo", [("5.6", "emparejado"), ("5.61", "desplazado"),
                                    ("6.5", "desplazado"), ("6.51", "faltante")])
def test_las_fronteras_de_0_10_y_1_00_m_se_notan_en_el_costo_de_la_hoja(y, tipo) -> None:
    """0,10 emparejado / 0,11 desplazado; 1,00 desplazado / 1,01 faltante y sobrante."""
    of001 = espacio_of001()
    # el ambiente ZB termina en y = 6: se prueba con la fila movida más allá, solo para R16
    resultado = contrastar_con_costo(_mover(of001, "PB3", y), of001, PRECIOS, DATOS)
    tipos = {d.tipo for d in resultado.contraste.diferencias}
    assert (tipos or {"emparejado"}) == ({"faltante", "sobrante"} if tipo == "faltante"
                                         else {tipo})
```
**`tests/unit/test_ui_hoja_contraste.py`**
```python
"""El panel «Contrastar con otro plano o levantamiento» de la hoja (R16, S3 §11.4).

`AppTest` no sube archivos: la prueba sustituye (con `monkeypatch`, que lo devuelve al terminar)
el cargador y las funciones de la hoja que leen el plano y el cálculo, y deja a prueba el
pegamento entre `ui.contraste` y la pantalla.
La aritmética del costo ya la prueban `test_ui_contraste.py` y la memoria a mano."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _pagina() -> None:
    from ui.paginas import hoja as pantalla

    pantalla._contrastar_plano()


def _sustituir(monkeypatch) -> None:
    import dataclasses
    import io
    from decimal import Decimal
    from types import SimpleNamespace as N

    import streamlit as st

    from tests.fixtures.espacio_of001 import espacio_of001
    from ui.paginas import hoja as pantalla

    completo = espacio_of001()
    sin_pb3 = dataclasses.replace(
        completo, puntos=tuple(p for p in completo.puntos if p.id != "PB3"))
    precios = {"DT-CAJA": "5.00", "DT-FACEPLATE": "3.00", "DT-JACK": "4.00", "DT-CERT": "12.00",
               "DT-UTP-CAT-6": "1.20", "DT-CAN-EMT-3/4": "6.00", "DT-CAN-EMT-1/2": "4.50"}
    presupuesto = N(moneda="USD", partidas=tuple(
        N(item=N(codigo_partida=c), resultado=N(precio_unitario=Decimal(v)))
        for c, v in precios.items()))

    class Subida(io.BytesIO):
        name = "levantamiento.dxf"

    monkeypatch.setattr(st, "file_uploader", lambda *a, key=None, **k: (
        Subida(b"x") if st.session_state.get("_sube") else None))
    monkeypatch.setattr(pantalla, "_borrador", lambda: N(espacio=sin_pb3))
    monkeypatch.setattr(
        pantalla, "_calculo", lambda: (N(elaboracion=N(presupuesto=presupuesto)), []))
    monkeypatch.setattr(pantalla.hoja, "subir_plano", lambda subida, carpeta, **k: (
        None, N(espacio=lambda: st.session_state["_otra"], mensaje="vacío")))


def _correr(monkeypatch, otra) -> AppTest:
    _sustituir(monkeypatch)
    at = AppTest.from_function(_pagina, default_timeout=60)
    at.session_state["_sube"] = otra is not None
    if otra is not None:
        at.session_state["_otra"] = otra
    return at.run()


def test_sin_archivo_el_panel_solo_explica(monkeypatch) -> None:
    at = _correr(monkeypatch, None)
    assert not at.exception and not at.dataframe and not at.info


def test_con_el_levantamiento_dice_el_faltante_y_su_costo(monkeypatch) -> None:
    from tests.fixtures.espacio_of001 import espacio_of001

    at = _correr(monkeypatch, espacio_of001())
    assert not at.exception, [e.value for e in at.exception]
    assert any("El plano cuesta menos" in i.value and "59,60 USD" in i.value for i in at.info)
    [tabla] = at.dataframe
    filas = tabla.value.to_dict("records")
    assert [(f["Qué pasa"], f["En la otra fuente"]) for f in filas] == [
        ("Falta en el plano", "PB3")]


def test_dos_fuentes_iguales_no_tienen_diferencias(monkeypatch) -> None:
    import dataclasses

    from tests.fixtures.espacio_of001 import espacio_of001

    completo = espacio_of001()
    sin_pb3 = dataclasses.replace(
        completo, puntos=tuple(p for p in completo.puntos if p.id != "PB3"))
    at = _correr(monkeypatch, sin_pb3)
    assert any("Sin diferencias" in s.value for s in at.success) and not at.dataframe


def test_una_fuente_sin_filas_se_rechaza_con_el_mensaje_del_lector(monkeypatch) -> None:
    from adapters.espacio import Espacio

    at = _correr(monkeypatch, Espacio())
    assert [e.value for e in at.error] == ["vacío"] and not at.exception
```
**`tests/unit/test_deteccion_planos.py`**
```python
"""La medición por errores sembrados (S3 §11.5, §13.5 b; RF-89): el catálogo, el plano limpio y la
tasa de detección. Meta ratificada por Eugenio (P8): 100 % de lo detectable y 0 falsas alarmas."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from scripts import medir_deteccion_planos as medicion
from scripts import sembrar_errores_planos as siembra

RAIZ = Path(__file__).resolve().parents[2]
LIMPIO = RAIZ / "tests" / "fixtures" / "errores_planos" / "of001_limpio.py"
FORMAS = ("estado", "item", "regla", "r16", "ninguna")


@pytest.fixture(scope="module")
def medida() -> dict:
    return medicion.medir()


def test_el_catalogo_y_las_siembras_tienen_los_mismos_ids() -> None:
    assert set(siembra.catalogo()) == set(siembra.SIEMBRAS)
    assert len(siembra.catalogo()) == 17


def test_cada_fila_del_catalogo_declara_una_deteccion_con_una_forma_conocida() -> None:
    for fila in siembra.catalogo().values():
        assert fila.deteccion, fila.id
        for etiqueta in (*fila.deteccion, *fila.consecuencias):
            for alternativa in etiqueta.split("|"):
                assert alternativa.split(":")[0] in FORMAS, (fila.id, alternativa)
        assert fila.autor in {"P", "A"}
        assert (fila.deteccion == ("ninguna",)) is (not fila.detectable), fila.id


def test_el_catalogo_tiene_tres_controles_y_casi_todo_escrito_sin_ver_el_codigo() -> None:
    filas = siembra.catalogo().values()
    assert sorted(f.id for f in filas if not f.detectable) == [
        "NO-DET-LUCES", "NO-DET-PERMUTA", "NO-DET-TRASLADO"]
    assert sum(1 for f in filas if f.autor == "P") >= 10  # la mayoría, escrita por pruebas


def test_el_plano_limpio_da_el_conjunto_exacto_escrito_en_s3_0() -> None:
    literal = runpy.run_path(str(LIMPIO))["LIMPIO"]
    for formato in ("dxf", "ifc"):
        auditoria = medicion.auditar(siembra.limpio(formato), formato)
        assert auditoria.items == literal[formato]["items"]
        assert auditoria.hallazgos == literal[formato]["hallazgos"]


def test_of001_limpio_no_da_hallazgos_de_r9_r10_ni_r15_y_8_de_r8() -> None:
    hallazgos = medicion.auditar(siembra.limpio("dxf"), "dxf").hallazgos
    reglas = [h[0] for h in hallazgos]
    assert reglas == ["R8"] * 8 and all(h[1] == "ADVERTENCIA" for h in hallazgos)
    assert len(medicion.auditar(siembra.limpio("dxf"), "dxf").items) == 15


def test_la_deteccion_es_total_sin_falsas_alarmas_y_los_controles_no_se_detectan(medida) -> None:
    assert medida["tasa"] == 1 and medida["falsas_alarmas"] == 0
    assert medida["no_detectables"] == 5 and medida["no_detectados"] == 5
    for id_, c in medida["categorias"].items():
        if c["detectables"]:
            assert c["detectados"] == c["sembrados"], id_
            assert c["falsas_alarmas"] == 0, id_


def test_la_tabla_dice_la_tasa_y_las_falsas_alarmas(medida) -> None:
    texto = medicion.tabla(medida)
    assert "Tasa de detección: 100%." in texto and "Falsas alarmas: 0." in texto
    assert texto.count("\n| ") == 17


def test_ningun_error_sembrado_da_r9_y_r15_a_la_vez() -> None:
    base = medicion.auditar(siembra.limpio("dxf"), "dxf")
    for id_, s in siembra.SIEMBRAS.items():
        if s.formato != "dxf":
            continue
        for variante in range(s.variantes):
            sembrado = siembra.sembrar(id_, variante)
            nuevos = medicion.agregado(
                medicion.auditar(sembrado.contenido, "dxf"), base, None).hallazgos
            reglas = {h[0] for h in nuevos}
            assert not {"R9", "R15"} <= reglas, (id_, variante, reglas)


def test_la_siembra_es_determinista_y_la_semilla_la_cambia() -> None:
    a, b = siembra.sembrar("CAPA-EQUIVOCADA", 1), siembra.sembrar("CAPA-EQUIVOCADA", 1)
    assert a.detalle == b.detalle and a.id == b.id
    otros = {siembra.sembrar("CAPA-EQUIVOCADA", v).detalle for v in range(3)}
    assert len(otros) >= 2  # las variantes no repiten siempre el mismo elemento
    por_semilla = {siembra.sembrar("FUERA-DE-AMBIENTE", 0, semilla=s).detalle for s in range(40)}
    assert len(por_semilla) > 1


def test_si_r15_dejara_de_funcionar_la_medicion_lo_nota(monkeypatch) -> None:
    from adapters.espacio.planos import geometria_plano

    monkeypatch.setattr(geometria_plano, "reglas_plano", lambda espacio: ())
    roto = medicion.medir()
    assert roto["tasa"] < 1
    perdidas = {i for i, c in roto["categorias"].items()
                if c["detectables"] and c["detectados"] < c["sembrados"]}
    assert perdidas == {"ESCALA-X1000", "SUPERPUESTO", "PUNTO-DUPLICADO"}


def test_la_salida_json_trae_la_semilla_y_el_plano_limpio(capsys) -> None:
    assert medicion.main(["--json"]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["semilla"] == siembra.SEMILLA == 42 and datos["tasa"] == 1
    assert len(datos["limpio"]["dxf"]["items"]) == 15
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_r16_contraste.py tests/unit/test_ui_contraste.py
tests/unit/test_ui_hoja_contraste.py tests/unit/test_deteccion_planos.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named
'adapters.espacio.planos.contraste'` (R16), `... 'ui.contraste'` y `... 'scripts.medir_deteccion_
planos'`; `test_ui_hoja_contraste` FAIL con `AttributeError: module 'ui.paginas.hoja' has no
attribute '_contrastar_plano'`.
```bash
git add tests/unit/test_r16_contraste.py tests/unit/test_ui_contraste.py \
  tests/unit/test_ui_hoja_contraste.py tests/unit/test_deteccion_planos.py
git commit -m "test(planos): R16, su costo en la hoja y la medicion de deteccion, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`adapters/espacio/planos/contraste.py`**
```python
"""R16: contraste entre dos fuentes del mismo espacio (spec S3 §11.4).

Compara el espacio de la versión («el plano») con otro («la referencia»: un levantamiento, el
plano anterior). Empareja ambientes, fuentes y puntos por especialidad, tipo y posición con el
vecino más cercano de la otra fuente, de forma determinista (pares por distancia creciente y,
a igual distancia, por id) y uno a uno:

| Distancia al vecino más cercano | Resultado | Frontera |
|---|---|---|
| ≤ 0,10 m (tolerancia) | emparejado, sin hallazgo | 0,10 emparejado / 0,11 desplazado |
| > 0,10 m y ≤ 1,00 m (radio de búsqueda) | **desplazado** | 1,00 desplazado / 1,01 faltante |
| > 1,00 m o sin vecino | **faltante** (solo en la referencia) y **sobrante** (solo en el plano) | |

Las distancias se comparan al cuadrado y en `Decimal`, así que las fronteras son exactas. Un
ambiente se ubica por el centro de su rectángulo. Ambas distancias son SUPUESTO_DECLARADO. R16 da
**ADVERTENCIA** siempre (RP8-9): la otra fuente puede ser la desactualizada; ERROR queda para la
geometría imposible (R15). El costo de la diferencia lo calcula la interfaz (`ui/contraste.py`)
con `core.budget.comparacion`. R16 no corre en la reauditoría de un paquete (maestro §3.3).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from adapters.espacio.especialidades import SUPUESTO_DECLARADO, Constante
from adapters.espacio.modelo import Coord, Espacio
from adapters.espacio.origen import clave_esp
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "CODIGO_R16",
    "RADIO_DE_BUSQUEDA",
    "TOLERANCIA_DE_EMPAREJADO",
    "Contraste",
    "Diferencia",
    "ReglaContraste",
    "contrastar",
]

CODIGO_R16 = "R16"
TOLERANCIA_DE_EMPAREJADO = Constante(
    "R16-tolerancia", "Distancia bajo la cual dos filas son la misma (m)", Decimal("0.10"),
    SUPUESTO_DECLARADO,
)
RADIO_DE_BUSQUEDA = Constante(
    "R16-radio", "Radio de búsqueda del vecino más cercano (m)", Decimal("1.00"),
    SUPUESTO_DECLARADO,
)
DESPLAZADO, FALTANTE, SOBRANTE = "desplazado", "faltante", "sobrante"


@dataclass(frozen=True, slots=True)
class Diferencia:
    """Una diferencia entre las dos fuentes. `id_plano` o `id_referencia` es `None` si la fila
    existe solo en la otra fuente."""

    tipo: str  # desplazado | faltante | sobrante
    tabla: str  # esp_ambientes | esp_fuentes | esp_puntos
    clase: str  # "especialidad/tipo" o "ambiente"
    id_plano: str | None
    id_referencia: str | None
    distancia: Decimal | None


@dataclass(frozen=True, slots=True)
class Contraste:
    diferencias: tuple[Diferencia, ...]
    emparejadas: int


def _filas(espacio: Espacio) -> dict[tuple[str, str], list[tuple[str, Coord]]]:
    """`(tabla, clase)` -> `[(id, posición)]`."""
    filas: dict[tuple[str, str], list[tuple[str, Coord]]] = defaultdict(list)
    for a in espacio.ambientes:
        centro = Coord(a.x0 + a.largo / 2, a.y0 + a.ancho / 2, Decimal(0))
        filas[("esp_ambientes", "ambiente")].append((a.id, centro))
    for f in espacio.fuentes:
        filas[("esp_fuentes", f"{f.especialidad.value}/{f.tipo.value}")].append(
            (f.id, f.posicion))
    for p in espacio.puntos:
        filas[("esp_puntos", f"{p.especialidad.value}/{p.tipo.value}")].append(
            (p.id, p.posicion))
    return filas


def _cuadrado(a: Coord, b: Coord) -> Decimal:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2


def contrastar(espacio: Espacio, referencia: Espacio) -> Contraste:
    """Las diferencias de `espacio` (el plano) frente a `referencia`, ordenadas por tabla, clase,
    tipo e id. Determinista: el mismo par de espacios da siempre el mismo resultado."""
    tolerancia2 = Decimal(TOLERANCIA_DE_EMPAREJADO.valor) ** 2
    radio2 = Decimal(RADIO_DE_BUSQUEDA.valor) ** 2
    plano, ref = _filas(espacio), _filas(referencia)
    diferencias: list[Diferencia] = []
    emparejadas = 0
    for clave in sorted(set(plano) | set(ref)):
        tabla, clase = clave
        propios, ajenos = plano.get(clave, []), ref.get(clave, [])
        candidatos = sorted(
            (_cuadrado(pos_a, pos_b), id_b, id_a)
            for id_a, pos_a in propios
            for id_b, pos_b in ajenos
            if _cuadrado(pos_a, pos_b) <= radio2
        )
        usados_plano: set[str] = set()
        usados_ref: set[str] = set()
        for distancia2, id_ref, id_plano in candidatos:
            if id_plano in usados_plano or id_ref in usados_ref:
                continue
            usados_plano.add(id_plano)
            usados_ref.add(id_ref)
            if distancia2 <= tolerancia2:
                emparejadas += 1
            else:
                diferencias.append(
                    Diferencia(DESPLAZADO, tabla, clase, id_plano, id_ref, distancia2.sqrt())
                )
        diferencias += [
            Diferencia(FALTANTE, tabla, clase, None, id_ref, None)
            for id_ref, _ in sorted(ajenos) if id_ref not in usados_ref
        ]
        diferencias += [
            Diferencia(SOBRANTE, tabla, clase, id_plano, None, None)
            for id_plano, _ in sorted(propios) if id_plano not in usados_plano
        ]
    orden = {DESPLAZADO: 0, FALTANTE: 1, SOBRANTE: 2}
    diferencias.sort(key=lambda d: (d.tabla, d.clase, orden[d.tipo], d.id_plano or "",
                                    d.id_referencia or ""))
    return Contraste(tuple(diferencias), emparejadas)


def _n(valor: Decimal) -> str:
    return format(valor.normalize(), "f")


class ReglaContraste(ReglaVerificacion):
    """R16 sobre la instantánea del espacio de la versión y el espacio de referencia."""

    codigo = CODIGO_R16
    nombre = "Contraste entre dos fuentes"

    def __init__(self, espacio: Espacio, espacio_referencia: Espacio,
                 nombre_referencia: str = "la otra fuente") -> None:
        self.espacio = espacio
        self.espacio_referencia = espacio_referencia
        self.nombre_referencia = nombre_referencia

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        hallazgos = []
        for d in contrastar(self.espacio, self.espacio_referencia).diferencias:
            fila = d.id_plano or d.id_referencia or ""
            if d.tipo == DESPLAZADO:
                texto = (f"{d.clase} {d.id_plano}: desplazado {_n(d.distancia)} m respecto de "
                         f"{d.id_referencia} en {self.nombre_referencia}")
            elif d.tipo == FALTANTE:
                texto = (f"{d.clase} {fila}: esta en {self.nombre_referencia} y falta en el plano")
            else:
                texto = (f"{d.clase} {fila}: esta en el plano y no en {self.nombre_referencia}")
            hallazgos.append(Hallazgo(
                regla=CODIGO_R16, severidad=Severidad.ADVERTENCIA, descripcion=texto,
                origen_ids=(clave_esp(d.tabla, fila),), valor_observado=d.distancia,
                valor_esperado=Decimal(TOLERANCIA_DE_EMPAREJADO.valor) if d.distancia else None,
            ))
        return hallazgos
```
**`ui/contraste.py`**
```python
"""R16 en la hoja: contraste con otro plano o levantamiento, con el costo (spec S3 §11.4).

Sin Streamlit. `contrastar_con_costo` empareja las dos fuentes con `adapters.espacio.planos.
contraste` y valora la diferencia: deriva las cantidades de las dos con `adapters.espacio.derivar`,
las valora con **los mismos precios unitarios** (los del presupuesto de la hoja) y compara con
`diferencia_entre_versiones` de `core.budget.comparacion` (SL-E9). El costo es **plano menos
referencia**:
negativo cuando el plano tiene menos obra que el levantamiento. Una partida derivada que no tiene
precio en la hoja no suma y se lista en `sin_precio`: el contraste lo dice en vez de inventarlo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from adapters.espacio import ESPECIALIDADES, Espacio, derivar
from adapters.espacio.planos.contraste import Contraste, contrastar
from core.budget.comparacion import Diferencia, FilaPresupuesto, diferencia_entre_versiones
from core.contracts.presupuesto import Presupuesto

__all__ = [
    "ResultadoDelContraste",
    "contrastar_con_costo",
    "filas_derivadas",
    "precios_de_la_hoja",
    "texto_del_costo",
]


@dataclass(frozen=True, slots=True)
class ResultadoDelContraste:
    contraste: Contraste
    costo: Diferencia  # referencia -> plano: `total_2 - total_1` es plano menos referencia
    sin_precio: tuple[str, ...]  # partidas derivadas sin precio en la hoja: no suman


def precios_de_la_hoja(presupuesto: Presupuesto) -> dict[str, Decimal]:
    """El precio unitario de cada partida valorada del presupuesto de la hoja."""
    return {p.item.codigo_partida: p.resultado.precio_unitario for p in presupuesto.partidas}


def filas_derivadas(
    espacio: Espacio, precios: Mapping[str, Decimal],
    especialidades: Sequence[str] = ESPECIALIDADES,
) -> tuple[list[FilaPresupuesto], tuple[str, ...]]:
    """`(filas, sin_precio)`: las cantidades que deriva el espacio, valoradas con `precios`."""
    juntas: dict[str, list] = {}
    for especialidad in especialidades:
        for item in derivar(espacio, especialidad):
            if item.codigo_partida in juntas:
                juntas[item.codigo_partida][2] += item.cantidad
            else:
                juntas[item.codigo_partida] = [item.descripcion, item.unidad, item.cantidad]
    filas = [
        FilaPresupuesto(codigo, descripcion, unidad, cantidad, precios[codigo])
        for codigo, (descripcion, unidad, cantidad) in sorted(juntas.items())
        if codigo in precios
    ]
    return filas, tuple(sorted(c for c in juntas if c not in precios))


def contrastar_con_costo(
    espacio: Espacio, referencia: Espacio, precios: Mapping[str, Decimal],
    especialidades: Sequence[str] = ESPECIALIDADES,
) -> ResultadoDelContraste:
    del_plano, falta_plano = filas_derivadas(espacio, precios, especialidades)
    de_referencia, falta_referencia = filas_derivadas(referencia, precios, especialidades)
    return ResultadoDelContraste(
        contraste=contrastar(espacio, referencia),
        costo=diferencia_entre_versiones(de_referencia, del_plano),
        sin_precio=tuple(sorted({*falta_plano, *falta_referencia})),
    )


def texto_del_costo(resultado: ResultadoDelContraste, moneda: str) -> str:
    """«El plano cuesta −59,60 USD respecto de la referencia (por cantidad …, por precio …)»."""
    costo = resultado.costo
    total = costo.total_2 - costo.total_1
    cifra = format(total.quantize(Decimal("0.01")), "f").replace(".", ",")
    verbo = "cuesta menos" if total < 0 else "cuesta más" if total > 0 else "cuesta igual"
    texto = f"El plano {verbo}: {cifra} {moneda} respecto de la otra fuente."
    if resultado.sin_precio:
        texto += (" No se valoran por no tener precio en la hoja: "
                  + ", ".join(resultado.sin_precio) + ".")
    return texto
```
  El panel de la hoja (importaciones nuevas: `from ui import caso, contraste, hoja` y
  `from ui.texto_seguro import texto_seguro`):
```diff
--- a/ui/paginas/hoja.py
+++ b/ui/paginas/hoja.py
@@ -934,4 +948,52 @@
 
 
+# --- contrastar con otro plano o levantamiento (R16, S3 §11.4) -------------------------------
+
+_AYUDA_CONTRASTE = (
+    "Suba otro DXF o IFC del mismo espacio (un levantamiento, el plano anterior). Se dice qué "
+    "falta, qué sobra y qué se movió respecto de esta hoja, y cuánto cuesta la diferencia con los "
+    "precios de esta hoja. No cambia el borrador. Si las dos fuentes difieren, una de ellas está "
+    "desactualizada: R16 no sabe cuál."
+)
+ROTULO_CONTRASTAR = "Contrastar con otro plano o levantamiento"
+CLAVE_CONTRASTE_ARCHIVO = "hoja_contraste_archivo"
+_TIPOS_DE_DIFERENCIA = {"desplazado": "Desplazado", "faltante": "Falta en el plano",
+                        "sobrante": "Sobra en el plano"}
+
+
+def _contrastar_plano() -> None:
+    """Pinta el contraste de la hoja con una segunda fuente y el costo de la diferencia."""
+    with st.expander(ROTULO_CONTRASTAR):
+        st.caption(_AYUDA_CONTRASTE)
+        subida = st.file_uploader("Otra fuente", type=["dxf", "ifc"], key=CLAVE_CONTRASTE_ARCHIVO,
+                                  label_visibility="collapsed")
+        if subida is None:
+            return
+        try:
+            _, lectura = hoja.subir_plano(subida, _directorio_de_planos())
+        except (hoja.HojaInvalida, ValueError, OSError) as error:
+            st.error(texto_seguro(str(error)))
+            return
+        referencia = lectura.espacio()
+        if referencia.vacio:
+            st.error(texto_seguro(lectura.mensaje or "El archivo no trae filas del espacio."))
+            return
+        presupuesto = _calculo()[0].elaboracion.presupuesto
+        resultado = contraste.contrastar_con_costo(
+            _borrador().espacio, referencia, contraste.precios_de_la_hoja(presupuesto))
+        st.info(texto_seguro(contraste.texto_del_costo(resultado, presupuesto.moneda)))
+        if not resultado.contraste.diferencias:
+            st.success(f"Sin diferencias: {resultado.contraste.emparejadas} filas emparejadas.")
+            return
+        milimetro = Decimal("0.001")
+        st.dataframe(
+            [{"Qué pasa": _TIPOS_DE_DIFERENCIA[d.tipo], "Tabla": d.tabla, "Clase": d.clase,
+              "En esta hoja": d.id_plano or "", "En la otra fuente": d.id_referencia or "",
+              "Distancia (m)": "" if d.distancia is None else str(d.distancia.quantize(milimetro))}
+             for d in resultado.contraste.diferencias],
+            hide_index=True,
+        )
+
+
 # --- pestana APU ---------------------------------------------------------------------------------
 
@@ -1212,4 +1274,29 @@
     if abierta is not None:
         _abrir(abierta.proyecto, codigo)
+
+
+ROTULO_ATIPICOS = "Buscar variaciones atípicas de precio"
+_AYUDA_ATIPICOS = (
+    "Apoyo a quien revisa, no una medición: compara las variaciones de precio de cada insumo "
+    "(en USD, con la tasa de cada precio) con las de su propio historial. Una serie de menos de "
+    "8 variaciones no se juzga. Solo advierte; no cambia ni bloquea nada."
+)
+
+
+def _pintar_atipicos(precios: Sequence) -> None:
+    """RF-100 (deseable, S3-6): las variaciones de precio atípicas de los insumos de la versión."""
+    if not st.button(ROTULO_ATIPICOS, key="hoja_atipicos"):
+        return
+    st.caption(_AYUDA_ATIPICOS)
+    with _sesion() as sesion:
+        por_insumo = {p.codigo: atipicos.atipicos_del_insumo(sesion, p.codigo) for p in precios}
+    if all(hallazgos is None for hallazgos in por_insumo.values()):
+        st.info("Falta el módulo de aprendizaje automático (extra `ml`): no se busca nada.")
+        return
+    todos = [h for hallazgos in por_insumo.values() for h in hallazgos or []]
+    if not todos:
+        st.success("Ninguna variación atípica en el historial de estos insumos.")
+    for hallazgo in todos:
+        st.warning(texto_seguro(hallazgo.descripcion))
 
 
```
  El sembrador (17 categorías del catálogo, una siembra por `id`), la medición y sus filas de
  `scripts/README.md`:
```markdown
| `sembrar_errores_planos.py` | siembra errores conocidos en el DXF de OF‑001 y en el IFC de
↳ oficina (catálogo de S3) | 0.8.0 |
| `medir_deteccion_planos.py` | mide la tasa de detección y las falsas alarmas de la auditoría de
↳ planos sobre esos errores | 0.8.0 |
```
**`scripts/sembrar_errores_planos.py`**
```python
"""Siembra errores conocidos en el DXF de OF-001 y en el IFC de oficina (S3 §11.5, RF-89).

Cada categoría del catálogo (`tests/fixtures/errores_planos/catalogo.md`) tiene una siembra
determinista: la semilla (`SEMILLA`), la categoría y el índice de la variante fijan el elemento que
se daña, así que la misma corrida da siempre el mismo plano y la misma lista de lo sembrado.
`scripts/medir_deteccion_planos.py` los audita y mide la tasa de detección.

    uv run python scripts/sembrar_errores_planos.py --salida data/errores_planos/
    uv run python scripts/sembrar_errores_planos.py --listar

El DXF de partida es `tests/fixtures/planos/of001.dxf` (la convención de capas del spec §6.6.1).
OF-001 no tiene IFC: las categorías IFC parten del IFC de oficina de `tests/fixtures`
(`oficina_ifc4`, RP8-5). Necesita los extras `planos` e `ifc`.
"""

from __future__ import annotations

import argparse
import io
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

SEMILLA = 42
VARIANTES_POR_CATEGORIA = 3
RUTA_OF001_DXF = RAIZ / "tests" / "fixtures" / "planos" / "of001.dxf"
RUTA_CATALOGO = RAIZ / "tests" / "fixtures" / "errores_planos" / "catalogo.md"

__all__ = [
    "SEMILLA",
    "SIEMBRAS",
    "Sembrado",
    "Siembra",
    "catalogo",
    "limpio",
    "sembrar",
]


@dataclass(frozen=True, slots=True)
class FilaDelCatalogo:
    id: str
    categoria: str
    como: str
    deteccion: tuple[str, ...]
    consecuencias: tuple[str, ...]
    detectable: bool
    autor: str


@dataclass(frozen=True, slots=True)
class Sembrado:
    """Un plano con un error sembrado. `referencia`: la segunda fuente de R16 (el plano limpio)."""

    id: str
    variante: int
    formato: str  # dxf | ifc
    contenido: bytes
    detalle: str  # qué elemento se dañó
    referencia: bytes | None = None


@dataclass(frozen=True, slots=True)
class Siembra:
    id: str
    formato: str
    variantes: int
    aplicar: Callable  # (modelo, azar) -> detalle
    con_referencia: bool = False


def _etiquetas(texto: str) -> tuple[str, ...]:
    return () if texto in {"—", ""} else tuple(e.strip() for e in texto.split(";"))


def catalogo(ruta: Path = RUTA_CATALOGO) -> dict[str, FilaDelCatalogo]:
    """Los bloques `### ID` del catálogo, con sus campos `- **Campo:** valor`, por id."""
    campos: dict[str, dict[str, str]] = {}
    actual: dict[str, str] | None = None
    ultimo = ""
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.startswith("### "):
            actual = campos.setdefault(linea[4:].strip(), {})
        elif actual is not None and linea.startswith("- **") and ":** " in linea:
            ultimo, _, valor = linea[4:].partition(":** ")
            actual[ultimo] = valor.strip()
        elif actual is not None and ultimo and linea.startswith("  ") and linea.strip():
            actual[ultimo] += " " + linea.strip()  # un campo que sigue en la línea de abajo
    return {
        id_: FilaDelCatalogo(
            id_, c["Categoría"], c["Cómo se siembra"], _etiquetas(c["Detección esperada"]),
            _etiquetas(c["Consecuencias admitidas"]), c["Detectable"] == "sí", c["Autor"],
        )
        for id_, c in campos.items()
    }


# --- el DXF ------------------------------------------------------------------------------------


def _leer_dxf():
    import ezdxf

    return ezdxf.readfile(RUTA_OF001_DXF)


def _bytes_dxf(doc) -> bytes:
    flujo = io.StringIO()
    doc.write(flujo)
    return flujo.getvalue().encode("utf-8")


def _insertados(doc, prefijo: str):
    return [e for e in doc.modelspace()
            if e.dxftype() == "INSERT" and e.dxf.layer.startswith(prefijo)]


def _id_de(insercion) -> str:
    return next(a.dxf.text for a in insercion.attribs if a.dxf.tag == "ID")


def _elegir(doc, prefijo: str, azar: random.Random):
    return azar.choice(sorted(_insertados(doc, prefijo), key=_id_de))


def _mover(insercion, dx: float = 0.0, dy: float = 0.0) -> None:
    x, y, z = insercion.dxf.insert
    insercion.dxf.insert = (x + dx, y + dy, z)
    for atributo in insercion.attribs:
        ax, ay, az = atributo.dxf.insert
        atributo.dxf.insert = (ax + dx, ay + dy, az)


def _sin_unidad(doc, azar):
    doc.header["$INSUNITS"] = 0
    return "sin $INSUNITS"


def _entidad_danada(doc, azar):
    x, y = azar.choice((1, 2, 3, 4, 5)), azar.choice((1, 2, 3, 4, 5))
    doc.modelspace().add_line((x, y), (x + 1, y), dxfattribs={
        "layer": "OTRA", "linetype": "NO_EXISTE"})
    return f"línea en ({x}; {y}) con un tipo de línea que no existe"


def _capa_equivocada(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    punto.dxf.layer = "PTO-DATO"
    return f"punto {_id_de(punto)} en la capa PTO-DATO"


def _altura_faltante(doc, azar):
    punto = _elegir(doc, "PTO-", azar)
    punto.attribs[:] = [a for a in punto.attribs if a.dxf.tag != "ALTURA"]
    return f"punto {_id_de(punto)} sin ALTURA"


def _escala(doc, azar):
    from ezdxf.math import Matrix44

    factor = azar.choice((250, 500, 1000))
    for entidad in doc.modelspace():
        entidad.transform(Matrix44.scale(factor, factor, factor))
    return f"dibujo × {factor}"


def _superpuesto(doc, azar):
    s = azar.choice((0.5, 0.4, 0.3))
    x0, y0 = 6 - s, 4 - s
    msp = doc.modelspace()
    msp.add_lwpolyline([(x0, y0), (x0 + 2, y0), (x0 + 2, y0 + 2), (x0, y0 + 2)], close=True,
                       dxfattribs={"layer": "AMBIENTES"})
    msp.add_text("ZX", dxfattribs={"layer": "AMBIENTES", "insert": (x0 + 1.5, y0 + 1.5, 0)})
    return f"ambiente ZX que pisa {s:g} m de ZA y de ZB"


def _punto_duplicado(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    copia = punto.copy()
    doc.modelspace().add_entity(copia)
    for atributo in copia.attribs:
        if atributo.dxf.tag == "ID":
            atributo.dxf.text = _id_de(punto) + "D"
    return f"punto {_id_de(punto)} copiado como {_id_de(punto)}D"


def _fuera_de_ambiente(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    desde = punto.dxf.insert
    _mover(punto, 30 - desde[0], 30 - desde[1])
    return f"punto {_id_de(punto)} en (30; 30)"


def _sin_fuente(doc, azar):
    capa = azar.choice(("FTE-DATOS", "FTE-ELEC"))
    for e in list(_insertados(doc, capa)):
        doc.modelspace().delete_entity(e)
    return f"se borra la fuente de la capa {capa}"


def _elemento_borrado(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    ident = _id_de(punto)
    doc.modelspace().delete_entity(punto)
    return f"punto {ident} borrado"


def _desplazado(doc, azar):
    punto = _elegir(doc, "PTO-DATOS", azar)
    hacia = -0.5 if punto.dxf.insert[0] > 3 else 0.5  # hacia el interior de su ambiente
    _mover(punto, hacia, 0.0)
    return f"punto {_id_de(punto)} corrido 0,50 m hacia el interior de su ambiente"


def _traslado(doc, azar):
    dx, dy = azar.choice(((0.5, 0.0), (0.0, 0.5), (0.5, 0.5)))
    for e in doc.modelspace():
        e.translate(dx, dy, 0)
    return f"todo el dibujo corrido ({dx:g}; {dy:g}) m"


def _permuta(doc, azar):
    a, b = (e for e in _insertados(doc, "PTO-DATOS") if _id_de(e) in {"PA1", "PA2"})
    for e, nuevo in ((a, _id_de(b)), (b, _id_de(a))):
        for atributo in e.attribs:
            if atributo.dxf.tag == "ID":
                atributo.dxf.text = nuevo
    return "PA1 y PA2 cambian de id"


def _luces(doc, azar):
    for e in _insertados(doc, "PTO-LUZ"):
        _mover(e, 0.0, 0.3)
    return "las cuatro luminarias corridas 0,30 m en y"


# --- el IFC de oficina -------------------------------------------------------------------------


def _ifc(faltante: str):
    def aplicar(_modelo, _azar):
        return f"el IFC de oficina sin {faltante}"

    return aplicar


def _crear_ifc(sin: str | None) -> bytes:
    from tests.fixtures.planos_ifc_ids import REQUISITOS, oficina_ifc4

    modelo = oficina_ifc4(tuple(r for r in REQUISITOS if r != sin))
    return modelo.to_string().encode("utf-8")


SIEMBRAS: dict[str, Siembra] = {s.id: s for s in (
    Siembra("SIN-UNIDAD", "dxf", 1, _sin_unidad),
    Siembra("ENTIDAD-DANADA", "dxf", VARIANTES_POR_CATEGORIA, _entidad_danada),
    Siembra("CAPA-EQUIVOCADA", "dxf", VARIANTES_POR_CATEGORIA, _capa_equivocada),
    Siembra("ALTURA-FALTANTE", "dxf", VARIANTES_POR_CATEGORIA, _altura_faltante),
    Siembra("ESCALA-X1000", "dxf", VARIANTES_POR_CATEGORIA, _escala),
    Siembra("SUPERPUESTO", "dxf", VARIANTES_POR_CATEGORIA, _superpuesto),
    Siembra("PUNTO-DUPLICADO", "dxf", VARIANTES_POR_CATEGORIA, _punto_duplicado),
    Siembra("FUERA-DE-AMBIENTE", "dxf", VARIANTES_POR_CATEGORIA, _fuera_de_ambiente),
    Siembra("SIN-FUENTE", "dxf", VARIANTES_POR_CATEGORIA, _sin_fuente),
    Siembra("IFC-SIN-ALTURA", "ifc", 1, _ifc("altura")),
    Siembra("IFC-SIN-DIAMETRO", "ifc", 1, _ifc("diametro")),
    Siembra("IFC-SIN-CIRCUITO", "ifc", 1, _ifc("circuito")),
    Siembra("ELEMENTO-BORRADO", "dxf", VARIANTES_POR_CATEGORIA, _elemento_borrado, True),
    Siembra("DESPLAZADO-0-50", "dxf", VARIANTES_POR_CATEGORIA, _desplazado, True),
    Siembra("NO-DET-TRASLADO", "dxf", VARIANTES_POR_CATEGORIA, _traslado),
    Siembra("NO-DET-PERMUTA", "dxf", 1, _permuta),
    Siembra("NO-DET-LUCES", "dxf", 1, _luces),
)}
_FALTANTE_IFC = {"IFC-SIN-ALTURA": "altura", "IFC-SIN-DIAMETRO": "diametro",
                 "IFC-SIN-CIRCUITO": "circuito"}


def limpio(formato: str) -> bytes:
    """El plano sin errores del que parten todas las siembras."""
    return _bytes_dxf(_leer_dxf()) if formato == "dxf" else _crear_ifc(None)


def sembrar(id_: str, variante: int = 0, semilla: int = SEMILLA) -> Sembrado:
    """El plano con el error `id_` sembrado en su `variante`-ésima forma."""
    siembra = SIEMBRAS[id_]
    azar = random.Random(f"{semilla}:{id_}:{variante}")
    if siembra.formato == "ifc":
        detalle = siembra.aplicar(None, azar)
        return Sembrado(id_, variante, "ifc", _crear_ifc(_FALTANTE_IFC[id_]), detalle)
    doc = _leer_dxf()
    detalle = siembra.aplicar(doc, azar)
    return Sembrado(id_, variante, "dxf", _bytes_dxf(doc), detalle,
                    limpio("dxf") if siembra.con_referencia else None)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--salida", type=Path, help="carpeta donde escribir los planos")
    analizador.add_argument("--listar", action="store_true", help="solo lista lo que se siembra")
    args = analizador.parse_args(argv)
    for id_, siembra in SIEMBRAS.items():
        for variante in range(siembra.variantes):
            sembrado = sembrar(id_, variante)
            print(f"{id_}#{variante}: {sembrado.detalle}")
            if args.salida and not args.listar:
                args.salida.mkdir(parents=True, exist_ok=True)
                (args.salida / f"{id_}-{variante}.{sembrado.formato}").write_bytes(
                    sembrado.contenido)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
**`scripts/medir_deteccion_planos.py`**
```python
"""Mide la tasa de detección y las falsas alarmas de la auditoría de planos (S3 §11.5, §13.5 b).

Para cada categoría del catálogo siembra el error (`scripts/sembrar_errores_planos.py`), audita el
plano sembrado y el limpio con las mismas reglas que la hoja (importación con su informe, R8 a R10
y R15; R16 contra el plano limpio como segunda fuente) y compara lo que la auditoría AGREGA:

* **detectado**: lo agregado cumple una de las detecciones del catálogo;
* **falsa alarma**: algo agregado que no está ni en la detección ni en las consecuencias admitidas;
* los controles **no detectables** se informan con su número y no entran en la tasa.

Meta del protocolo (`docs/protocolo_deteccion_planos.md`, ratificada por Eugenio el 2026-10-11):
100 % de lo detectable y cero falsas alarmas. La salida es una tabla Markdown o, con `--json`, el
mismo contenido para la bitácora.

    uv run python scripts/medir_deteccion_planos.py [--json]
    uv run python scripts/medir_deteccion_planos.py --limpio     # el conjunto exacto de OF-001
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.sembrar_errores_planos import (  # noqa: E402
    SEMILLA,
    SIEMBRAS,
    Sembrado,
    catalogo,
    limpio,
    sembrar,
)

RUTA_LIMPIO = RAIZ / "tests" / "fixtures" / "errores_planos" / "of001_limpio.py"


@dataclass(frozen=True, slots=True)
class Auditoria:
    """Lo que la hoja diría de un plano: estado, ítems del informe, hallazgos y su espacio."""

    estado: str
    items: tuple[tuple[str, str, str], ...]  # (tipo, tabla, mensaje), sin los «importado»
    hallazgos: tuple[tuple[str, str, str], ...]  # (regla, severidad, descripción)
    espacio: object = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class Agregado:
    """Lo que la auditoría del plano sembrado trae de más que la del limpio."""

    estado: str
    items: tuple[tuple[str, str, str], ...]
    hallazgos: tuple[tuple[str, str, str], ...]
    diferencias: tuple[tuple[str, str | None, str | None], ...]  # R16: (tipo, id plano, id ref)


def auditar(contenido: bytes, formato: str) -> Auditoria:
    from datetime import date as fecha

    from adapters.espacio.planos.geometria_plano import reglas_plano
    from adapters.espacio.reglas import reglas_espacio
    from core.contracts.presupuesto import Presupuesto

    if formato == "dxf":
        from adapters.espacio.planos.dxf import importar_dxf

        resultado = importar_dxf(contenido, nombre="plano.dxf")
    else:
        from adapters.espacio.planos.ifc import importar_ifc

        resultado = importar_ifc(contenido, nombre="plano.ifc")
    items = tuple(sorted(
        (i.tipo.value, i.tabla, i.mensaje) for i in resultado.informe if i.tipo.value != "importado"
    ))
    hallazgos: list[tuple[str, str, str]] = []
    espacio = None
    if resultado.estado.value == "importada":
        espacio = resultado.espacio()
        presupuesto = Presupuesto(codigo="X", fecha=fecha(2026, 11, 1), moneda="USD", partidas=())
        for regla in (*reglas_espacio(espacio), *reglas_plano(espacio)):
            hallazgos += [(h.regla, h.severidad.name, h.descripcion)
                          for h in regla.evaluar(presupuesto)]
    return Auditoria(resultado.estado.value, items, tuple(sorted(hallazgos)), espacio)


def agregado(sembrada: Auditoria, base: Auditoria, referencia: Auditoria | None) -> Agregado:
    from adapters.espacio.planos.contraste import contrastar

    diferencias: tuple[tuple[str, str | None, str | None], ...] = ()
    if referencia is not None and sembrada.espacio is not None and referencia.espacio is not None:
        diferencias = tuple(
            (d.tipo, d.id_plano, d.id_referencia)
            for d in contrastar(sembrada.espacio, referencia.espacio).diferencias
        )
    return Agregado(
        sembrada.estado if sembrada.estado != base.estado else "",
        tuple((Counter(sembrada.items) - Counter(base.items)).elements()),
        tuple((Counter(sembrada.hallazgos) - Counter(base.hallazgos)).elements()),
        diferencias,
    )


def cumple(etiqueta: str, agregados: Agregado) -> list[object]:
    """Lo agregado que satisface una etiqueta del catálogo (lista vacía si nada). Las
    alternativas `a|b` suman lo que cumple cada una."""
    if "|" in etiqueta:
        return [x for alternativa in etiqueta.split("|") for x in cumple(alternativa, agregados)]
    forma, _, resto = etiqueta.partition(":")
    if forma == "estado":
        return [agregados.estado] if agregados.estado == resto else []
    if forma == "item":
        tipo, _, texto = resto.partition(":")
        return [i for i in agregados.items if i[0] == tipo and texto in i[2]]
    if forma == "regla":
        regla, _, texto = resto.partition(":")
        return [h for h in agregados.hallazgos if h[0] == regla and texto in h[2]]
    if forma == "r16":
        return [d for d in agregados.diferencias if d[0] == resto]
    return []


@dataclass(frozen=True, slots=True)
class Resultado:
    id: str
    variante: int
    detalle: str
    detectable: bool
    detectado: bool
    falsas_alarmas: tuple[object, ...]


def evaluar(sembrado: Sembrado, base: dict[str, Auditoria], fila) -> Resultado:
    """Audita un plano sembrado y lo compara con el catálogo."""
    sembrada = auditar(sembrado.contenido, sembrado.formato)
    referencia = base["dxf"] if sembrado.referencia is not None else None
    nuevo = agregado(sembrada, base[sembrado.formato], referencia)
    explicados: list[object] = []
    detectado = bool(fila.deteccion) and all(cumple(e, nuevo) for e in fila.deteccion)
    for etiqueta in (*fila.deteccion, *fila.consecuencias):
        explicados += cumple(etiqueta, nuevo)
    pendientes = Counter([*nuevo.items, *nuevo.hallazgos, *nuevo.diferencias])
    pendientes.subtract(Counter(map(tuple, explicados)))
    alarmas = tuple((+pendientes).elements())
    if nuevo.estado and nuevo.estado not in {e.partition(":")[2] for e in fila.deteccion}:
        alarmas += (nuevo.estado,)
    return Resultado(sembrado.id, sembrado.variante, sembrado.detalle, fila.detectable,
                     detectado, alarmas)


def medir(semilla: int = SEMILLA) -> dict:
    """Siembra todo el catálogo y devuelve la medición por categoría."""
    base = {"dxf": auditar(limpio("dxf"), "dxf"), "ifc": auditar(limpio("ifc"), "ifc")}
    filas = catalogo()
    resultados = [
        evaluar(sembrar(id_, variante, semilla), base, filas[id_])
        for id_, siembra in SIEMBRAS.items() for variante in range(siembra.variantes)
    ]
    categorias = {}
    for id_ in SIEMBRAS:
        propios = [r for r in resultados if r.id == id_]
        categorias[id_] = {
            "sembrados": len(propios), "detectables": filas[id_].detectable,
            "detectados": sum(r.detectado for r in propios),
            "falsas_alarmas": sum(len(r.falsas_alarmas) for r in propios),
        }
    detectables = [r for r in resultados if r.detectable]
    return {
        "semilla": semilla, "categorias": categorias, "resultados": resultados,
        "tasa": sum(r.detectado for r in detectables) / len(detectables),
        "falsas_alarmas": sum(len(r.falsas_alarmas) for r in detectables),
        "no_detectables": sum(1 for r in resultados if not r.detectable),
        "no_detectados": sum(1 for r in resultados if not r.detectable and not r.detectado
                             and not r.falsas_alarmas),
        "limpio": {
            "dxf": {"items": [list(i) for i in base["dxf"].items],
                    "hallazgos": [list(h) for h in base["dxf"].hallazgos]},
            "ifc": {"items": [list(i) for i in base["ifc"].items],
                    "hallazgos": [list(h) for h in base["ifc"].hallazgos]},
        },
    }


ENCABEZADO_LIMPIO = """El conjunto EXACTO de los planos limpios (S3 §11.5 y §13.5 b; de S3-0).

`DXF_*` es lo que la hoja diría del DXF de OF-001 (`tests/fixtures/planos/of001.dxf`): los ítems
del informe de importación que no son «importado» y los hallazgos de R8 a R10 y R15 (R9, R10 y
R15 no dan ninguno). `IFC_*` es lo mismo del IFC de oficina de `planos_ifc_ids`. Lo regenera
`uv run python scripts/medir_deteccion_planos.py --limpio`; cambiarlo a mano es cambiar el
oráculo de la medición. Las constantes son tuplas de `(tipo, tabla, mensaje)` y de
`(regla, severidad, descripción)`.
"""
ANCHO = 96


def _literal(texto: str) -> str:
    return json.dumps(texto, ensure_ascii=False)


def _trozos(mensaje: str, sangria: int) -> list[str]:
    """El mensaje partido en literales de una línea cada uno (≤ 100 columnas)."""
    trozos, actual = [], ""
    for palabra in mensaje.split(" "):
        candidato = palabra if not actual else actual + " " + palabra
        if actual and sangria + len(_literal(candidato + " ")) > ANCHO:
            trozos.append(actual + " ")
            actual = palabra
        else:
            actual = candidato
    trozos.append(actual)
    return trozos


def modulo_limpio(limpio: dict) -> str:
    """El texto de `tests/fixtures/errores_planos/of001_limpio.py`."""
    salida = ['"""' + ENCABEZADO_LIMPIO + '"""', ""]
    for formato in ("dxf", "ifc"):
        for clave, nombre in (("items", "ITEMS"), ("hallazgos", "HALLAZGOS")):
            salida.append(f"{formato.upper()}_{nombre} = (")
            for *cortos, largo in limpio[formato][clave]:
                salida.append("    (" + ", ".join(_literal(c) for c in cortos) + ",")
                partes = _trozos(largo, 5)
                salida += [("     " + _literal(p)) for p in partes]
                salida[-1] += "),"
            salida += [")", ""]
    salida.append("LIMPIO = {")
    for formato in ("dxf", "ifc"):
        f = formato.upper()
        salida.append(f'    "{formato}": {{"items": {f}_ITEMS, "hallazgos": {f}_HALLAZGOS}},')
    salida.append("}")
    return "\n".join(salida) + "\n"


def tabla(medicion: dict) -> str:
    filas = ["| Categoría | Sembrados | Detectados | Falsas alarmas | Detectable |",
             "|---|---|---|---|---|"]
    for id_, c in medicion["categorias"].items():
        filas.append(f"| {id_} | {c['sembrados']} | {c['detectados']} | {c['falsas_alarmas']} | "
                     f"{'sí' if c['detectables'] else 'no (control)'} |")
    filas.append("")
    filas.append(f"Tasa de detección: {medicion['tasa']:.0%}. Falsas alarmas: "
                 f"{medicion['falsas_alarmas']}. Controles no detectables: "
                 f"{medicion['no_detectables']} ({medicion['no_detectados']} sin detectar, como "
                 "se espera).")
    return "\n".join(filas)


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--json", action="store_true")
    analizador.add_argument("--limpio", action="store_true",
                            help="escribe el conjunto exacto del plano limpio")
    args = analizador.parse_args(argv)
    medicion = medir()
    if args.limpio:
        print(modulo_limpio(medicion["limpio"]), end="")
        return 0
    if args.json:
        medicion = {k: v for k, v in medicion.items() if k != "resultados"}
        print(json.dumps(medicion, ensure_ascii=False, indent=2, default=str))
    else:
        print(tabla(medicion))
    return 0 if medicion["tasa"] == 1 and medicion["falsas_alarmas"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_r16_contraste.py tests/unit/test_ui_contraste.py
tests/unit/test_ui_hoja_contraste.py tests/unit/test_deteccion_planos.py -v -W error` → verde.
Run: `uv run python scripts/medir_deteccion_planos.py` → 100 % de lo detectable y 0 falsas alarmas;
los tres controles `NO-DET-*` no detectados y declarados. Run: `uv run python
scripts/medir_deteccion_planos.py --limpio` → idéntico al literal de la tarea 2 (si difiere, el
plano limpio cambió y se decide en S3-0, no se edita el literal a ciegas).
- [ ] **Paso 5: Commit**
```bash
git add adapters/espacio/planos/contraste.py ui/contraste.py ui/paginas/hoja.py \
  scripts/sembrar_errores_planos.py scripts/medir_deteccion_planos.py
git commit -m "feat(planos): R16, costo de la diferencia en la hoja y medicion de deteccion" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS3-5 y foco de revisión de la fase

**Compuerta GS3-5** (se cruza al fusionar `inc/080-s3-5-planos`):
1. `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-5 --junit reporte-pruebas.xml`
   en OK, incluida `S3-M5`: el rango de la rama no toca `core/`
   (`git diff --stat origin/main...HEAD -- core/` vacío).
2. CI verde en Linux y Windows con los extras `planos` e `ifc`.
3. La medición del protocolo: 100 % de lo detectable, cero falsas alarmas, y los tres controles no
   detectables informados con su número; se anota la tabla literal en la bitácora.
4. Aprobación del encargo de pruebas y de adaptadores; CP-R2 (guion de planos) recorrido a mano.

**Foco de revisión de S3-5** (lo que el spec implica y ninguna prueba ejercita todavía):
1. **Una conversión a `float` en una frontera** invalidaría los límites exactos: las filas de R15 y
   R16 se prueban en 0,0100/0,0101 m2, 0,0010/0,0009 m, 0,10/0,11 m y 1,00/1,01 m
   (`test_superposicion_de_0_0100_m2_pasa`, `test_fronteras_de_tolerancia_y_de_radio`).
2. **El IDS que baja un XSD de internet** violaría la guardia de red:
   `test_el_ids_existe_y_ifctester_se_importa_de_forma_diferida`.
3. **`Drawing.audit()` borrando lo que el importador lee:** `test_of001_importa_igual_que_antes_sin_
   items_nuevos` y `test_lo_que_ezdxf_repara_se_informa_y_el_plano_se_importa`.
4. **Una falsa alarma que se vuelve normal:** `test_la_deteccion_es_total_sin_falsas_alarmas_y_los_
   controles_no_se_detectan` y el literal de OF-001 limpio.
5. **Un error de plano que R9 y R15 cuentan dos veces:** `test_ningun_error_sembrado_da_r9_y_r15_a_
   la_vez`.

---

# S3-3 — Firma, paquete auditado, Entregar y Administración (rama `inc/080-s3-3-paquete`)

Se apila sobre `inc/080-s3-2-nucleo` (S3-3 necesita S3-2) y se fusiona justo después (RP8-20). Toca
`seguridad/`, `paquete/`, `ui/`, `api/`, `scripts/`, `migraciones/` y `tests/`; no toca `core/`.
Al terminar, una empresa genera su clave de firma desde el propio equipo, quien arma entrega un
`.silice` firmado con anexos y cadena, un administrador gestiona cuentas, claves y accesos, y toda
pantalla y script que guarda versiones lo hace a nombre de la persona de la sesión (RF-82, RF-83).

### Tarea 13: Firma Ed25519, huella legible y empresas (propia y ajenas)

**Rama:** `inc/080-s3-3-paquete` (apilada sobre la rama de núcleo)   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `seguridad/firma.py`, `seguridad/empresas.py`
- Prueba: `tests/unit/test_firma.py`, `tests/unit/test_empresas.py`

**Interfaces:**
- Consume: `seguridad.json_estricto.{leer_json, JsonRechazado}`, `seguridad.secretos.{cifrar,
  descifrar, exigir_contrasena_de_clave, ParametrosKdf, SecretoCifrado, InvalidTag}` (tarea 4),
  `seguridad.modelo.{ClaveEmpresa, EmpresaPropia, EmpresaRegistrada}` (tarea 3),
  `seguridad.eventos` (tarea 5), `tests.fixtures.instalacion` (tarea 5).
- Produce:
  - `seguridad.firma`: `class ParDeClaves`
  - `seguridad.firma`: `class ClavePublicaLeida`
  - `seguridad.firma`: `def huella_completa(publica: bytes) -> str`
  - `seguridad.firma`: `def huella_corta(publica: bytes) -> str`
  - `seguridad.firma`: `def normalizar_huella_corta(texto: str) -> str`
  - `seguridad.firma`: `def generar_par() -> ParDeClaves`
  - `seguridad.firma`: `def publica_de(privada: bytes) -> bytes`
  - `seguridad.firma`: `def firmar(privada: bytes, dominio: bytes, mensaje: bytes) -> bytes`
  - `seguridad.firma`: `def verificar(publica: bytes, dominio: bytes, mensaje: bytes, firma:
      bytes) -> bool`
  - `seguridad.firma`: `def exportar_clave_publica(nombre: str, rif: str, publica: bytes, ahora:
      datetime) -> bytes`
  - `seguridad.firma`: `def leer_clave_publica(datos: bytes) -> ClavePublicaLeida`
  - `seguridad.firma`: `def crear_aviso_revocacion(privada: bytes, motivo: str, ahora: datetime)
      -> bytes`
  - `seguridad.firma`: `def leer_aviso_revocacion(datos: bytes) -> tuple[bytes, str, bool]`
  - `seguridad.empresas`: `class ClaveError(ValueError)`
  - `seguridad.empresas`: `class ContrasenaDeClaveIncorrecta(ClaveError)`
  - `seguridad.empresas`: `class HuellaNoCoincide(ClaveError)`
  - `seguridad.empresas`: `def empresa_propia(session: Session) -> EmpresaPropia | None`
  - `seguridad.empresas`: `def guardar_empresa_propia(session: Session, nombre: str, rif: str,
      ciudad: str, actor: str, ahora: datetime) -> EmpresaPropia`
  - `seguridad.empresas`: `def clave_activa(session: Session) -> ClaveEmpresa | None`
  - `seguridad.empresas`: `def generar_clave(session: Session, contrasena_clave: str, actor:
      str, ahora: datetime, parametros: ParametrosKdf | None=None) -> ClaveEmpresa`
  - `seguridad.empresas`: `def abrir_privada(session: Session, contrasena_clave: str) -> bytes`
  - `seguridad.empresas`: `def exportar_clave_publica_propia(session: Session, ahora: datetime)
      -> bytes`
  - `seguridad.empresas`: `def exportar_respaldo_cifrado(session: Session) -> bytes`
  - `seguridad.empresas`: `def retirar_clave(session: Session, actor: str, ahora: datetime,
      motivo: str='') -> ClaveEmpresa`
  - `seguridad.empresas`: `def revocar_clave_propia(session: Session, actor: str, ahora:
      datetime, motivo: str, contrasena_clave: str | None=None) -> bytes | None`
  - `seguridad.empresas`: `def buscar_por_publica(session: Session, publica: bytes) ->
      EmpresaRegistrada | None`
  - `seguridad.empresas`: `def registrar_empresa_ajena(session: Session, archivo_clave: bytes,
      huella_leida: str, comprobada_con: str, metodo: str, actor: str, ahora: datetime) ->
      EmpresaRegistrada`
  - `seguridad.empresas`: `def retirar_ajena(session: Session, empresa_id: int, fecha_retiro:
      datetime, actor: str, ahora: datetime) -> EmpresaRegistrada`
  - `seguridad.empresas`: `def revocar_ajena(session: Session, empresa_id: int, motivo: str,
      actor: str, ahora: datetime, aviso: bytes | None=None) -> EmpresaRegistrada`

**Dominios (RV-16).** Lo que se firma lleva un prefijo: `b"silice-paquete-v1\0"` + los bytes exactos
de `manifiesto.json`, o `b"silice-revocacion-v1\0"` + el JSON canónico del aviso sin su firma. Una
firma de un dominio nunca vale en el otro. **Huella corta:** los primeros 100 bits del SHA-256 de la
clave pública en el alfabeto de Crockford (sin I, L, O ni U), en cinco grupos de cuatro; sirve solo
para compararla por teléfono: toda búsqueda interna usa la huella completa. **Empresas:** una sola
propia por instalación (RV-6) y, a lo sumo, una clave activa cuya privada vive cifrada con su
propia contraseña; retirar o revocar **destruye** la privada de la base; una ajena solo se registra
con su huella comprobada por otro canal (teléfono, en persona o QR).

- [ ] **Paso 1: Escribir las pruebas que fallan** (los vectores 1 y 2 de RFC 8032 §7.1 se
  reprodujeron en el entorno de S3-0; la clave pública de tamaño malo y la firma truncada son falsas
  sin lanzar)
**`tests/unit/test_firma.py`**
```python
"""Firma Ed25519 con separación de dominio y huella legible (spec S3 §7; RFC 8032 §7.1)."""

from __future__ import annotations

from datetime import datetime

import pytest

from seguridad import firma
from seguridad.json_estricto import JsonRechazado

#: Vectores de prueba del RFC 8032, sección 7.1 (TEST 1 y TEST 2): la biblioteca se usa bien.
RFC_8032 = (
    (
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e3970"
        "1cf9b46bd25bf5f0595bbe24655141438e7a100b",
    ),
    (
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613"
        "d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    ),
)
AHORA = datetime(2026, 11, 10, 9, 30)


@pytest.mark.parametrize("privada,publica,mensaje,firma_esperada", RFC_8032)
def test_vectores_del_rfc_8032(privada: str, publica: str, mensaje: str, firma_esperada: str):
    privada_b, publica_b = bytes.fromhex(privada), bytes.fromhex(publica)
    assert firma.publica_de(privada_b) == publica_b
    # sin dominio: el vector del RFC es la firma del mensaje tal cual
    assert firma.firmar(privada_b, b"", bytes.fromhex(mensaje)).hex() == firma_esperada
    assert firma.verificar(publica_b, b"", bytes.fromhex(mensaje), bytes.fromhex(firma_esperada))


def test_la_huella_corta_son_cinco_grupos_de_cuatro_sin_simbolos_ambiguos() -> None:
    par = firma.generar_par()
    corta = firma.huella_corta(par.publica)
    grupos = corta.split("-")
    assert [len(g) for g in grupos] == [4, 4, 4, 4, 4]
    assert set(corta.replace("-", "")) <= set(firma.ALFABETO_HUELLA)
    assert not set("ILOU") & set(corta)
    assert firma.huella_corta(par.publica) == corta  # determinista
    assert firma.normalizar_huella_corta(corta.lower().replace("-", " ")) == corta


def test_la_huella_corta_toma_los_primeros_100_bits_de_la_completa() -> None:
    par = firma.generar_par()
    completa = int(firma.huella_completa(par.publica), 16)
    corta = firma.huella_corta(par.publica).replace("-", "")
    valor = 0
    for simbolo in corta:
        valor = (valor << 5) | firma.ALFABETO_HUELLA.index(simbolo)
    assert valor == completa >> (256 - 100)


def test_normalizar_rechaza_lo_que_no_es_una_huella() -> None:
    for malo in ("", "ABC", "K7QF-M9XR-A2PT-W4HN-C8D", "K7QF-M9XR-A2PT-W4HN-C8DI"):
        with pytest.raises(ValueError):
            firma.normalizar_huella_corta(malo)


def test_una_firma_de_un_dominio_no_vale_en_el_otro() -> None:
    par = firma.generar_par()
    mensaje = b"{}"
    del_paquete = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, mensaje)
    assert firma.verificar(par.publica, firma.DOMINIO_PAQUETE, mensaje, del_paquete)
    assert not firma.verificar(par.publica, firma.DOMINIO_REVOCACION, mensaje, del_paquete)


@pytest.mark.parametrize("tamano", [0, 63, 65])
def test_firma_vacia_o_truncada_es_falsa_sin_lanzar(tamano: int) -> None:
    par = firma.generar_par()
    buena = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, b"m")
    assert not firma.verificar(par.publica, firma.DOMINIO_PAQUETE, b"m", (buena + b"x")[:tamano])


def test_una_clave_publica_de_tamano_malo_es_falsa_sin_lanzar() -> None:
    assert not firma.verificar(b"corta", firma.DOMINIO_PAQUETE, b"m", b"x" * 64)


def test_exportar_y_leer_la_clave_publica_calcula_la_huella_el_sistema() -> None:
    par = firma.generar_par()
    archivo = firma.exportar_clave_publica(
        "Contratista Demo, C.A.", "J-00000000-0", par.publica, AHORA
    )
    leida = firma.leer_clave_publica(archivo)
    assert (leida.nombre, leida.rif, leida.publica) == (
        "Contratista Demo, C.A.", "J-00000000-0", par.publica)
    assert leida.huella == firma.huella_completa(par.publica) and leida.huella_coincide


def test_una_huella_declarada_falsa_se_nota() -> None:
    par, otra = firma.generar_par(), firma.generar_par()
    archivo = firma.exportar_clave_publica("X", "", par.publica, AHORA)
    falso = archivo.replace(firma.huella_corta(par.publica).encode(),
                            firma.huella_corta(otra.publica).encode())
    assert not firma.leer_clave_publica(falso).huella_coincide


def test_un_archivo_de_clave_con_clave_duplicada_se_rechaza() -> None:
    with pytest.raises(JsonRechazado):
        firma.leer_clave_publica(b'{"formato":"silice-clave","formato":"silice-clave"}')
    with pytest.raises(JsonRechazado):
        firma.leer_clave_publica(b'{"formato":"otro"}')


def test_el_aviso_de_revocacion_firmado_se_valida_y_uno_falso_no() -> None:
    par = firma.generar_par()
    aviso = firma.crear_aviso_revocacion(par.privada, "se perdio el equipo", AHORA)
    publica, motivo, valida = firma.leer_aviso_revocacion(aviso)
    assert (publica, motivo, valida) == (par.publica, "se perdio el equipo", True)
    manipulado = aviso.replace(b"se perdio el equipo", b"otro motivo")
    assert firma.leer_aviso_revocacion(manipulado)[2] is False


def test_una_firma_de_paquete_no_sirve_de_aviso_de_revocacion() -> None:
    import base64
    import json

    par = firma.generar_par()
    cuerpo = {"formato": firma.FORMATO_REVOCACION, "version_formato": 1,
              "huella": firma.huella_completa(par.publica),
              "clave_publica": base64.b64encode(par.publica).decode(), "motivo": "m",
              "fecha": AHORA.isoformat(timespec="seconds")}
    canonico = json.dumps(cuerpo, sort_keys=True, separators=(",", ":")).encode()
    mala = firma.firmar(par.privada, firma.DOMINIO_PAQUETE, canonico)  # dominio equivocado
    falso = json.dumps({**cuerpo, "firma": base64.b64encode(mala).decode()}).encode()
    assert firma.leer_aviso_revocacion(falso)[2] is False
```
**`tests/unit/test_empresas.py`**
```python
"""Empresa propia, clave de firma y empresas ajenas (RF-84; spec S3 §7)."""

from __future__ import annotations

import base64
import json
from datetime import timedelta
from pathlib import Path

import pytest

from seguridad import empresas, firma
from seguridad.modelo import ClaveEmpresa, EmpresaRegistrada
from seguridad.secretos import ContrasenaRechazada
from tests.fixtures.instalacion import AHORA, instalacion

CLAVE = "frase de firma larga y propia"


@pytest.fixture
def con_empresa(tmp_path: Path):
    with instalacion(tmp_path) as sesion:
        empresas.guardar_empresa_propia(
            sesion, "Contratista Demo, C.A.", "J-00000000-0", "Caracas", "ana", AHORA
        )
        yield sesion


def _archivo_ajeno(nombre: str = "Otra Empresa, C.A.") -> tuple[bytes, firma.ParDeClaves]:
    par = firma.generar_par()
    return firma.exportar_clave_publica(nombre, "J-11111111-1", par.publica, AHORA), par


def test_generar_cifra_la_privada_y_la_huella_es_la_misma_en_otra_base(tmp_path: Path):
    with instalacion(tmp_path / "a") as una, instalacion(tmp_path / "b") as otra:
        for sesion in (una, otra):
            empresas.guardar_empresa_propia(sesion, "X", "J-1", "", "ana", AHORA)
        clave = empresas.generar_clave(una, CLAVE, "ana", AHORA)
        privada = empresas.abrir_privada(una, CLAVE)
        assert clave.privada_cifrada != privada and privada not in (clave.privada_cifrada or b"")
        assert firma.publica_de(privada) == clave.publica
        # la misma clave pública da la misma huella en la otra instalación
        assert firma.huella_corta(clave.publica) == firma.huella_corta(firma.publica_de(privada))
    bruto = (tmp_path / "a" / "instalacion.db").read_bytes()
    assert privada not in bruto  # la privada nunca está sin cifrar en el archivo


def test_contrasena_de_clave_erronea_da_un_mensaje_sin_traza(con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    with pytest.raises(empresas.ContrasenaDeClaveIncorrecta, match="no es correcta") as error:
        empresas.abrir_privada(con_empresa, CLAVE + "x")
    assert error.value.__cause__ is None and not isinstance(error.value, KeyError)


def test_contrasena_corta_o_comun_no_genera_clave(con_empresa) -> None:
    for mala in ("corta", "administrador"):
        with pytest.raises(ContrasenaRechazada):
            empresas.generar_clave(con_empresa, mala, "ana", AHORA)
    assert con_empresa.query(ClaveEmpresa).count() == 0


def test_solo_una_clave_activa_y_hace_falta_la_empresa(tmp_path: Path, con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    with pytest.raises(empresas.ClaveError, match="Ya hay una clave activa"):
        empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    with instalacion(tmp_path / "vacia") as sin_empresa:
        with pytest.raises(empresas.ClaveError, match="datos de la empresa"):
            empresas.generar_clave(sin_empresa, CLAVE, "ana", AHORA)


def test_retirar_destruye_la_privada_en_la_base(con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    retirada = empresas.retirar_clave(con_empresa, "ana", AHORA, "cambio de equipo")
    assert (retirada.estado, retirada.privada_cifrada, retirada.sal, retirada.nonce) == (
        "retirada", None, None, None)
    with pytest.raises(empresas.ClaveError, match="no tiene una clave de firma activa"):
        empresas.abrir_privada(con_empresa, CLAVE)
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)  # ya se puede generar otra


def test_revocar_con_la_contrasena_da_un_aviso_firmado_y_destruye_la_privada(con_empresa):
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    aviso = empresas.revocar_clave_propia(con_empresa, "ana", AHORA, "robo", CLAVE)
    publica, motivo, valida = firma.leer_aviso_revocacion(aviso)
    assert (publica, motivo, valida) == (clave.publica, "robo", True)
    assert con_empresa.get(ClaveEmpresa, clave.id).privada_cifrada is None


def test_revocar_sin_la_contrasena_no_da_aviso(con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    assert empresas.revocar_clave_propia(con_empresa, "ana", AHORA, "se perdio la clave") is None
    assert con_empresa.query(ClaveEmpresa).one().estado == "revocada"


def test_el_respaldo_cifrado_no_trae_la_privada_en_claro(con_empresa) -> None:
    empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    privada = empresas.abrir_privada(con_empresa, CLAVE)
    respaldo = empresas.exportar_respaldo_cifrado(con_empresa)
    assert privada not in respaldo and base64.b64encode(privada) not in respaldo
    assert json.loads(respaldo)["formato"] == "silice-clave-cifrada"


def test_registrar_una_ajena_exige_la_huella_leida_y_con_quien_se_comprobo(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    corta = firma.huella_corta(par.publica)
    with pytest.raises(empresas.HuellaNoCoincide, match="No se registró nada"):
        empresas.registrar_empresa_ajena(
            con_empresa, archivo, "AAAA-AAAA-AAAA-AAAA-AAAA", "Pedro", "telefono", "ana", AHORA)
    with pytest.raises(empresas.ClaveError, match="con quién"):
        empresas.registrar_empresa_ajena(con_empresa, archivo, corta, " ", "telefono", "ana", AHORA)
    with pytest.raises(empresas.ClaveError, match="cómo se comprobó"):
        empresas.registrar_empresa_ajena(
            con_empresa, archivo, corta, "Pedro", "carta", "ana", AHORA)
    assert con_empresa.query(EmpresaRegistrada).count() == 0
    fila = empresas.registrar_empresa_ajena(
        con_empresa, archivo, corta.lower(), "Pedro, gerente", "telefono", "ana", AHORA)
    assert (fila.estado, fila.publica, fila.huella) == (
        "activa", par.publica, firma.huella_completa(par.publica))
    with pytest.raises(empresas.ClaveError, match="ya está registrada"):
        empresas.registrar_empresa_ajena(con_empresa, archivo, corta, "Pedro", "qr", "ana", AHORA)


def test_la_huella_declarada_en_el_archivo_no_se_cree(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    otra = firma.generar_par()
    falso = archivo.replace(firma.huella_corta(par.publica).encode(),
                            firma.huella_corta(otra.publica).encode())
    # quien llama por teléfono lee la huella de la empresa REAL: la del archivo falso no coincide
    with pytest.raises(empresas.HuellaNoCoincide):
        empresas.registrar_empresa_ajena(
            con_empresa, falso, firma.huella_corta(otra.publica), "Pedro", "telefono", "ana", AHORA)


def test_la_propia_clave_no_se_registra_como_ajena(con_empresa) -> None:
    clave = empresas.generar_clave(con_empresa, CLAVE, "ana", AHORA)
    archivo = empresas.exportar_clave_publica_propia(con_empresa, AHORA)
    with pytest.raises(empresas.ClaveError, match="misma empresa"):
        empresas.registrar_empresa_ajena(
            con_empresa, archivo, firma.huella_corta(clave.publica), "yo", "qr", "ana", AHORA)


def test_dos_claves_con_la_misma_huella_corta_no_se_confunden(con_empresa) -> None:
    """La búsqueda interna usa la clave completa: aunque dos filas compartan la huella (la corta
    solo sirve por teléfono), cada clave pública encuentra la suya."""
    uno, otro = firma.generar_par(), firma.generar_par()
    for nombre, par in (("Uno", uno), ("Otro", otro)):
        con_empresa.add(EmpresaRegistrada(
            empresa=nombre, rif="", publica=par.publica, huella="mismos-100-bits", estado="activa",
            comprobada_con="t", metodo="telefono", fecha_comprobacion=AHORA))
    con_empresa.commit()
    assert empresas.buscar_por_publica(con_empresa, uno.publica).empresa == "Uno"
    assert empresas.buscar_por_publica(con_empresa, otro.publica).empresa == "Otro"
    assert empresas.buscar_por_publica(con_empresa, firma.generar_par().publica) is None


def test_retiro_y_revocacion_ajenos(con_empresa) -> None:
    archivo, par = _archivo_ajeno()
    fila = empresas.registrar_empresa_ajena(
        con_empresa, archivo, firma.huella_corta(par.publica), "Pedro", "telefono", "ana", AHORA)
    retiro = AHORA + timedelta(days=2)
    retirada = empresas.retirar_ajena(con_empresa, fila.id, retiro, "ana", AHORA)
    assert (retirada.estado, retirada.fecha_estado) == ("retirada", retiro)
    falso = firma.crear_aviso_revocacion(firma.generar_par().privada, "x", AHORA)
    with pytest.raises(empresas.ClaveError, match="no es válido"):
        empresas.revocar_ajena(con_empresa, fila.id, "", "ana", AHORA, aviso=falso)
    bueno = firma.crear_aviso_revocacion(par.privada, "robo", AHORA)
    revocada = empresas.revocar_ajena(con_empresa, fila.id, "", "ana", AHORA, aviso=bueno)
    assert (revocada.estado, revocada.motivo) == ("revocada", "robo")
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_firma.py tests/unit/test_empresas.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'seguridad.firma'` (y
`seguridad.empresas`).
```bash
git add tests/unit/test_firma.py tests/unit/test_empresas.py
git commit -m "test(seguridad): firma Ed25519 con dominios y empresas, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`seguridad/firma.py`**
```python
"""Firma Ed25519 por empresa, huella legible y archivos firmados (spec S3 §7; maestro §4.4).

Nada de criptografía propia: `cryptography` genera, firma y verifica; aquí solo se fijan los
**dominios** (prefijos) de lo que se firma y la forma de los archivos:

* paquete: `b"silice-paquete-v1\\0"` + los bytes exactos de `manifiesto.json`;
* aviso de revocación: `b"silice-revocacion-v1\\0"` + el JSON canónico del aviso sin su firma.

Una firma de un dominio nunca vale en el otro (RV-16). La huella corta son los primeros 100 bits
del SHA-256 de la clave pública en el alfabeto de Crockford (sin I, L, O ni U), en cinco grupos
de cuatro: sirve solo para compararla por teléfono; toda búsqueda interna usa la clave completa.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from seguridad.json_estricto import JsonRechazado, leer_json

DOMINIO_PAQUETE = b"silice-paquete-v1\0"
DOMINIO_REVOCACION = b"silice-revocacion-v1\0"
ALFABETO_HUELLA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
FORMATO_CLAVE = "silice-clave"
FORMATO_REVOCACION = "silice-revocacion"
EXTENSION_CLAVE = ".silice-clave"
BITS_HUELLA_CORTA = 100


@dataclass(frozen=True, slots=True)
class ParDeClaves:
    privada: bytes  # 32 B crudos
    publica: bytes  # 32 B crudos


@dataclass(frozen=True, slots=True)
class ClavePublicaLeida:
    """Lo que trae un archivo `.silice-clave`. La huella se calcula; la declarada se compara."""

    nombre: str
    rif: str
    publica: bytes
    huella: str  # completa, calculada por el sistema
    huella_corta: str  # la que se compara por teléfono, calculada por el sistema
    huella_corta_declarada: str  # la que trae el archivo

    @property
    def huella_coincide(self) -> bool:
        return self.huella_corta == self.huella_corta_declarada


def huella_completa(publica: bytes) -> str:
    """SHA-256 (64 hex) de la clave pública cruda: la huella que usa todo el sistema."""
    return hashlib.sha256(publica).hexdigest()


def huella_corta(publica: bytes) -> str:
    """`K7QF-M9XR-A2PT-W4HN-C8DV`: 100 bits en 20 símbolos de 5 bits, en 5 grupos de 4."""
    entero = int.from_bytes(hashlib.sha256(publica).digest(), "big") >> (256 - BITS_HUELLA_CORTA)
    simbolos = [
        ALFABETO_HUELLA[(entero >> (5 * (19 - i))) & 31] for i in range(BITS_HUELLA_CORTA // 5)
    ]
    texto = "".join(simbolos)
    return "-".join(texto[i : i + 4] for i in range(0, len(texto), 4))


def normalizar_huella_corta(texto: str) -> str:
    """La huella corta tecleada: mayúsculas, sin espacios y con los guiones en su lugar."""
    limpia = "".join(c for c in texto.upper() if c.isalnum())
    if len(limpia) != BITS_HUELLA_CORTA // 5 or any(c not in ALFABETO_HUELLA for c in limpia):
        raise ValueError("la huella corta son 20 caracteres (sin I, L, O ni U)")
    return "-".join(limpia[i : i + 4] for i in range(0, len(limpia), 4))


def generar_par() -> ParDeClaves:
    privada = Ed25519PrivateKey.generate()
    return ParDeClaves(
        privada=privada.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        ),
        publica=privada.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ),
    )


def publica_de(privada: bytes) -> bytes:
    return (
        Ed25519PrivateKey.from_private_bytes(privada)
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )


def firmar(privada: bytes, dominio: bytes, mensaje: bytes) -> bytes:
    """Firma `dominio + mensaje`. Ed25519 es determinista: el mismo par da la misma firma."""
    return Ed25519PrivateKey.from_private_bytes(privada).sign(dominio + mensaje)


def verificar(publica: bytes, dominio: bytes, mensaje: bytes, firma: bytes) -> bool:
    """True solo si `firma` es de `publica` sobre `dominio + mensaje`. Nunca lanza por la firma:
    una vacía, truncada o de otro dominio es False."""
    try:
        Ed25519PublicKey.from_public_bytes(publica).verify(firma, dominio + mensaje)
    except (InvalidSignature, ValueError):
        return False
    return True


def _canonico(objeto: dict) -> bytes:
    return json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def exportar_clave_publica(nombre: str, rif: str, publica: bytes, ahora: datetime) -> bytes:
    """El archivo `.silice-clave`: nombre, RIF, clave pública (base64), huella y fecha."""
    return _canonico(
        {
            "formato": FORMATO_CLAVE,
            "version_formato": 1,
            "nombre": nombre,
            "rif": rif,
            "clave_publica": base64.b64encode(publica).decode("ascii"),
            "huella": huella_corta(publica),
            "fecha": ahora.isoformat(timespec="seconds"),
        }
    )


def leer_clave_publica(datos: bytes) -> ClavePublicaLeida:
    """Lee un `.silice-clave` con el lector estricto. La huella es la que CALCULA el sistema."""
    documento = leer_json(datos)
    if not isinstance(documento, dict) or documento.get("formato") != FORMATO_CLAVE:
        raise JsonRechazado("no es un archivo de clave publica de Silice")
    try:
        publica = base64.b64decode(documento["clave_publica"], validate=True)
        nombre, rif = str(documento["nombre"]).strip(), str(documento.get("rif", "")).strip()
    except (KeyError, ValueError) as error:
        raise JsonRechazado("archivo de clave publica incompleto o dañado") from error
    if len(publica) != 32 or not nombre:
        raise JsonRechazado("la clave publica debe ser Ed25519 de 32 bytes y llevar nombre")
    return ClavePublicaLeida(
        nombre=nombre,
        rif=rif,
        publica=publica,
        huella=huella_completa(publica),
        huella_corta=huella_corta(publica),
        huella_corta_declarada=str(documento.get("huella", "")),
    )


def crear_aviso_revocacion(privada: bytes, motivo: str, ahora: datetime) -> bytes:
    """El aviso de revocación firmado con la propia clave (dominio de revocación)."""
    publica = publica_de(privada)
    cuerpo = {
        "formato": FORMATO_REVOCACION,
        "version_formato": 1,
        "huella": huella_completa(publica),
        "clave_publica": base64.b64encode(publica).decode("ascii"),
        "motivo": motivo,
        "fecha": ahora.isoformat(timespec="seconds"),
    }
    firma = firmar(privada, DOMINIO_REVOCACION, _canonico(cuerpo))
    return _canonico({**cuerpo, "firma": base64.b64encode(firma).decode("ascii")})


def leer_aviso_revocacion(datos: bytes) -> tuple[bytes, str, bool]:
    """`(clave pública, motivo, firma válida)`. La validez se comprueba con la clave que TRAE el
    aviso; el llamador además exige que sea una clave que tiene registrada."""
    documento = leer_json(datos)
    if not isinstance(documento, dict) or documento.get("formato") != FORMATO_REVOCACION:
        raise JsonRechazado("no es un aviso de revocacion de Silice")
    try:
        publica = base64.b64decode(documento["clave_publica"], validate=True)
        firma = base64.b64decode(documento["firma"], validate=True)
    except (KeyError, ValueError) as error:
        raise JsonRechazado("aviso de revocacion incompleto o dañado") from error
    cuerpo = {k: v for k, v in documento.items() if k != "firma"}
    valida = verificar(publica, DOMINIO_REVOCACION, _canonico(cuerpo), firma)
    return publica, str(documento.get("motivo", "")), valida
```
**`seguridad/empresas.py`**
```python
"""La empresa propia, su clave de firma y las empresas ajenas registradas (spec S3 §7).

Una sola empresa propia por instalación (RV-6, P1) y, a lo sumo, una clave de firma **activa**.
La privada vive cifrada con su propia contraseña (`seguridad.secretos`) y solo la conoce el
administrador. Retirar o revocar **destruye** la privada de la base (los respaldos anteriores la
conservan cifrada: la pantalla lo advierte). Las empresas de los paquetes que se reciben se
registran como ajenas, con su clave pública y la huella comprobada por otro canal: sin esa marca
no se registra nada. Cada función confirma su transacción; nada de aquí guarda una contraseña.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad import eventos, firma
from seguridad.modelo import ClaveEmpresa, EmpresaPropia, EmpresaRegistrada
from seguridad.secretos import (
    InvalidTag,
    ParametrosKdf,
    SecretoCifrado,
    cifrar,
    descifrar,
    exigir_contrasena_de_clave,
)

ACTIVA, RETIRADA, REVOCADA = "activa", "retirada", "revocada"
METODOS = ("telefono", "en persona", "qr")
PIE_DE_RESPALDOS = (
    "Los respaldos hechos antes de retirar la clave todavía la contienen, cifrada con su "
    "contraseña."
)


class ClaveError(ValueError):  # noqa: N818
    """Un rechazo de la gestión de claves, en lenguaje llano y sin traza."""


class ContrasenaDeClaveIncorrecta(ClaveError):  # noqa: N818
    """La contraseña de la clave de firma no es la que la cifró."""


class HuellaNoCoincide(ClaveError):  # noqa: N818
    """La huella leída por el otro canal no es la que calculó el sistema."""


# --- empresa propia -------------------------------------------------------------------------


def empresa_propia(session: Session) -> EmpresaPropia | None:
    return session.get(EmpresaPropia, 1)


def guardar_empresa_propia(
    session: Session, nombre: str, rif: str, ciudad: str, actor: str, ahora: datetime
) -> EmpresaPropia:
    if not nombre.strip() or not rif.strip():
        raise ClaveError("La empresa necesita nombre y RIF.")
    fila = empresa_propia(session)
    if fila is None:
        fila = EmpresaPropia(id=1, nombre="", rif="", actualizada=ahora)
        session.add(fila)
    fila.nombre, fila.rif, fila.ciudad = nombre.strip(), rif.strip(), ciudad.strip()
    fila.actualizada, fila.actualizada_por = ahora, actor
    eventos.registrar(session, "empresa", ahora, detalle=f"{fila.nombre}; por {actor}")
    session.commit()
    return fila


# --- clave de firma propia ------------------------------------------------------------------


def clave_activa(session: Session) -> ClaveEmpresa | None:
    return session.scalar(select(ClaveEmpresa).where(ClaveEmpresa.estado == ACTIVA))


def generar_clave(
    session: Session,
    contrasena_clave: str,
    actor: str,
    ahora: datetime,
    parametros: ParametrosKdf | None = None,
) -> ClaveEmpresa:
    """Genera el par Ed25519 en este equipo y guarda la privada cifrada (Argon2id -> AES-GCM)."""
    if empresa_propia(session) is None:
        raise ClaveError("Registre primero los datos de la empresa.")
    if clave_activa(session) is not None:
        raise ClaveError("Ya hay una clave activa: retírela o revóquela antes de generar otra.")
    exigir_contrasena_de_clave(contrasena_clave)
    par = firma.generar_par()
    huella = firma.huella_completa(par.publica)
    guardado = cifrar(par.privada, contrasena_clave, huella, parametros)
    clave = ClaveEmpresa(
        publica=par.publica, huella=huella, privada_cifrada=guardado.cifrado, kdf=guardado.kdf,
        sal=guardado.sal, nonce=guardado.nonce, estado=ACTIVA, creada=ahora, creada_por=actor,
    )
    session.add(clave)
    session.flush()
    eventos.registrar(
        session, "alta de clave", ahora, detalle=f"{firma.huella_corta(par.publica)}; por {actor}"
    )
    session.commit()
    return clave


def abrir_privada(session: Session, contrasena_clave: str) -> bytes:
    """La privada de la clave activa. `ContrasenaDeClaveIncorrecta` (sin traza) si no es la
    contraseña; el `InvalidTag` de la biblioteca no sale de aquí."""
    clave = clave_activa(session)
    if clave is None or clave.privada_cifrada is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    cifrado = SecretoCifrado(clave.kdf or "", clave.sal or b"", clave.nonce or b"",
                             clave.privada_cifrada)
    try:
        return descifrar(cifrado, contrasena_clave, clave.huella)
    except InvalidTag:
        raise ContrasenaDeClaveIncorrecta("La contraseña de la clave no es correcta.") from None


def exportar_clave_publica_propia(session: Session, ahora: datetime) -> bytes:
    """El `.silice-clave` para mandarlo a quien recibe los paquetes."""
    clave, empresa = clave_activa(session), empresa_propia(session)
    if clave is None or empresa is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    return firma.exportar_clave_publica(empresa.nombre, empresa.rif, clave.publica, ahora)


def exportar_respaldo_cifrado(session: Session) -> bytes:
    """La clave activa tal como está guardada (cifrada), para un respaldo aparte. Nunca sale la
    privada en claro; solo se hace desde el propio equipo."""
    clave = clave_activa(session)
    if clave is None or clave.privada_cifrada is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    def b64(octetos: bytes | None) -> str:
        return base64.b64encode(octetos or b"").decode("ascii")

    return json.dumps(
        {"formato": "silice-clave-cifrada", "version_formato": 1, "huella": clave.huella,
         "clave_publica": b64(clave.publica), "kdf": clave.kdf, "sal": b64(clave.sal),
         "nonce": b64(clave.nonce), "cifrado": b64(clave.privada_cifrada)},
        sort_keys=True,
    ).encode("utf-8")


def _destruir_privada(clave: ClaveEmpresa) -> None:
    clave.privada_cifrada = clave.kdf = clave.sal = clave.nonce = None


def retirar_clave(session: Session, actor: str, ahora: datetime, motivo: str = "") -> ClaveEmpresa:
    """Sustitución sin compromiso: **se destruye la privada** en la base."""
    clave = clave_activa(session)
    if clave is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    _destruir_privada(clave)
    clave.estado, clave.fecha_estado, clave.motivo = RETIRADA, ahora, motivo
    eventos.registrar(session, "retiro", ahora, detalle=f"{firma.huella_corta(clave.publica)}")
    session.commit()
    return clave


def revocar_clave_propia(
    session: Session, actor: str, ahora: datetime, motivo: str, contrasena_clave: str | None = None
) -> bytes | None:
    """Comprometida o perdida. Con la contraseña genera el **aviso de revocación** firmado con la
    propia clave (dominio de revocación); sin ella (se perdió) no hay aviso y se avisa por
    teléfono. Destruye la privada en ambos casos."""
    clave = clave_activa(session)
    if clave is None:
        raise ClaveError("La empresa no tiene una clave de firma activa.")
    aviso = None
    if contrasena_clave is not None:
        privada = abrir_privada(session, contrasena_clave)
        aviso = firma.crear_aviso_revocacion(privada, motivo, ahora)
    _destruir_privada(clave)
    clave.estado, clave.fecha_estado, clave.motivo = REVOCADA, ahora, motivo
    eventos.registrar(
        session, "revocacion", ahora, detalle=f"{firma.huella_corta(clave.publica)}; {motivo}"
    )
    session.commit()
    return aviso


# --- empresas ajenas ------------------------------------------------------------------------


def buscar_por_publica(session: Session, publica: bytes) -> EmpresaRegistrada | None:
    """Búsqueda interna por la CLAVE PÚBLICA COMPLETA (la corta solo se compara a viva voz)."""
    return session.scalar(select(EmpresaRegistrada).where(EmpresaRegistrada.publica == publica))


def registrar_empresa_ajena(
    session: Session,
    archivo_clave: bytes,
    huella_leida: str,
    comprobada_con: str,
    metodo: str,
    actor: str,
    ahora: datetime,
) -> EmpresaRegistrada:
    """Registra la clave de otra empresa. El sistema calcula la huella él mismo (no confía en la
    escrita en el archivo) y exige la que se leyó por otro canal: sin coincidencia, nada."""
    leida = firma.leer_clave_publica(archivo_clave)
    if metodo not in METODOS:
        raise ClaveError(f"Indique cómo se comprobó la huella: {', '.join(METODOS)}.")
    if not comprobada_con.strip():
        raise ClaveError("Indique con quién se comprobó la huella.")
    try:
        vista = firma.normalizar_huella_corta(huella_leida)
    except ValueError as error:
        raise HuellaNoCoincide(str(error)) from None
    if vista != leida.huella_corta:
        raise HuellaNoCoincide(
            f"La huella leída no coincide con la de la clave ({leida.huella_corta}). "
            "No se registró nada."
        )
    if buscar_por_publica(session, leida.publica) is not None:
        raise ClaveError("Esa clave ya está registrada.")
    propia = clave_activa(session)
    if propia is not None and propia.publica == leida.publica:
        raise ClaveError("Esa es la clave de esta misma empresa; no se registra como ajena.")
    fila = EmpresaRegistrada(
        empresa=leida.nombre, rif=leida.rif, publica=leida.publica, huella=leida.huella,
        estado=ACTIVA, comprobada_con=comprobada_con.strip(), metodo=metodo,
        fecha_comprobacion=ahora, registrada_por=actor,
    )
    session.add(fila)
    session.flush()
    eventos.registrar(
        session, "clave registrada", ahora, detalle=f"{leida.nombre}; {leida.huella_corta}"
    )
    session.commit()
    return fila


def retirar_ajena(
    session: Session, empresa_id: int, fecha_retiro: datetime, actor: str, ahora: datetime
) -> EmpresaRegistrada:
    """La contratista avisó que retiró su clave. 'Verificado (retirada)' vale solo para paquetes
    recibidos ANTES de `fecha_retiro`."""
    fila = _ajena(session, empresa_id)
    fila.estado, fila.fecha_estado = RETIRADA, fecha_retiro
    eventos.registrar(session, "retiro", ahora, detalle=f"{fila.empresa}; por {actor}")
    session.commit()
    return fila


def revocar_ajena(
    session: Session,
    empresa_id: int,
    motivo: str,
    actor: str,
    ahora: datetime,
    aviso: bytes | None = None,
) -> EmpresaRegistrada:
    """Importar el aviso firmado (se verifica con la clave registrada) o marcarla a mano con el
    motivo. Tras revocar, ningún paquete de esa clave verifica."""
    fila = _ajena(session, empresa_id)
    if aviso is not None:
        publica, motivo_aviso, valida = firma.leer_aviso_revocacion(aviso)
        if publica != fila.publica or not valida:
            raise ClaveError("El aviso de revocación no es válido para esta clave.")
        motivo = motivo or motivo_aviso
    fila.estado, fila.fecha_estado, fila.motivo = REVOCADA, ahora, motivo
    eventos.registrar(session, "revocacion", ahora, detalle=f"{fila.empresa}; {motivo}")
    session.commit()
    return fila


def _ajena(session: Session, empresa_id: int) -> EmpresaRegistrada:
    fila = session.get(EmpresaRegistrada, empresa_id)
    if fila is None:
        raise ClaveError("No hay una empresa registrada con ese número.")
    return fila
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_firma.py tests/unit/test_empresas.py tests/unit/test_secretos.py
-v -W error` → verde. Run: `uv run ruff check seguridad` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add seguridad/firma.py seguridad/empresas.py
git commit -m "feat(seguridad): firma por empresa, huella corta, retiro y revocacion de claves" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 14: Paquete `.silice` — formato con límites, tablas del revisor y anexos

**Rama:** `inc/080-s3-3-paquete`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `paquete/__init__.py`, `paquete/formato.py`, `paquete/modelo.py`, `paquete/anexos.py`
- Crear: `migraciones/caso/versions/caso_0008_s3_paquete.py`
- Modificar: `migraciones/metadatos.py:12-17`, `.github/workflows/ci.yml:112-140`,
  `tests/unit/test_migraciones_metadatos.py`, `scripts/meta_silice_s3.py` (`S3-M4` pasa a la fase
  `S3-3`: la cobertura de `paquete/` solo existe desde aquí)
- Prueba: `tests/unit/test_paquete_formato.py`, `tests/unit/test_paquete_anexos.py`

**Interfaces:**
- Consume: `core.budget.cadena.huella_de_anexos` y `core.budget.canonico.{huella, json_canonico}`
  (tareas 7 y 8), `seguridad.json_estricto.{leer_json, JsonRechazado}` (tarea 4),
  `migraciones.comun.{TablaCongelada, crear_o_verificar, borrar_tablas}` (B), `core.models.Base`.
- Produce:
  - `paquete.formato`: `class PaqueteRechazado(ValueError)`
  - `paquete.formato`: `def relacion_aceptable(descomprimido: int, comprimido: int) -> bool`
  - `paquete.formato`: `def abrir_zip(datos: bytes) -> dict[str, bytes]`
  - `paquete.formato`: `def comprobar_salida(archivos: Mapping[str, bytes], tamano_zip: int) ->
      None`
  - `paquete.modelo`: `def crear_esquema_paquete(destino: Engine | Connection) -> None`
  - `paquete.modelo`: `def buscar_por_huella(sesion: Session, huella_archivo: str)`
  - `paquete.modelo`: `def paquetes_del_proyecto(sesion: Session, proyecto: str, huella_clave:
      str)`
  - `paquete.modelo`: `def registrar_recibido(sesion: Session, **valores) -> int`
  - `paquete.modelo`: `def registrar_dictamen(sesion: Session, *, paquete_id: int,
      huella_archivo: str, resultado: str, notas: str, usuario: str, fecha: datetime,
      estado_verificacion: str, revisor_armo: bool) -> int`
  - `paquete.modelo`: `def dictamenes_de(sesion: Session, huella_archivo: str)`
  - `paquete.anexos`: `def anexo_de_tablas(sesion: Session, nombre: str, tablas: Sequence[str],
      proyecto_id: int) -> bytes | None`
  - `paquete.anexos`: `def huellas_de_entradas(anexo: dict[str, Any]) -> list[str]`
  - `paquete.modelo.METADATA_PAQUETE` (tablas `paq_recibido` y `paq_dictamen`) y la revisión
    `caso_0008_s3_paquete` (cuelga de `caso_0007_s3_cadena`); `METADATAS_CASO` pasa a tres
    elementos.

**Formato.** Un ZIP con nombres fijos (manifiesto, firma, presupuesto, informe, cadena y los cuatro
anexos admitidos) y ningún otro. Se lee **en memoria, sin extraer al disco y sin confiar en los
tamaños de las cabeceras**: cada entrada se lee con tope (`read(limite + 1)`) contando los bytes
reales. Límites (SUPUESTO_DECLARADO, con su frontera exacta): archivo de 20 MiB (20 971 521 B se
rechaza), 50 MiB descomprimidos por entrada, 100 MiB en total, compresión de 100:1 (101:1 se
rechaza), 200 000 renglones más líneas y 64 niveles de anidamiento. Se rechazan además el nombre
fuera de la lista, el repetido, la ruta absoluta, con `..` o con barra invertida, la entrada cifrada
y los métodos de compresión que no sean almacenado o *deflate*. **Anexos:** filas con huella por
entrada y sin cadena propia (límite declarado); una tabla que esta versión de Sílice no conoce se
omite sin error, y una prueba exige que toda tabla con columna `responsable` viaje o esté en la
lista de las que no viajan.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_paquete_formato.py`**
```python
"""Abrir un ZIP ajeno sin riesgo: las fronteras exactas de S3 §8.4 (RNF-16, RF-86)."""

from __future__ import annotations

import io
import zipfile

import pytest

from paquete import formato
from paquete.formato import PaqueteRechazado, abrir_zip, relacion_aceptable

NOMBRE = "presupuesto.json"
#: Una entrada sin compresión en un ZIP de Python pesa N + 98 + 2 x len(nombre): cabecera local
#: (30), directorio central (46) y fin del directorio central (22), con el nombre en dos.
SOBRECARGA = 98 + 2 * len(NOMBRE)


def zip_de(entradas: dict[str, bytes], metodo=zipfile.ZIP_STORED) -> bytes:
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w", metodo) as z:
        for nombre, octetos in entradas.items():
            z.writestr(nombre, octetos)
    return flujo.getvalue()


def test_los_limites_son_los_numeros_literales_del_spec() -> None:
    assert (formato.LIMITE_ARCHIVO, formato.LIMITE_ENTRADA, formato.LIMITE_TOTAL) == (
        20_971_520, 52_428_800, 104_857_600)
    assert (formato.RELACION_MAXIMA, formato.LIMITE_FILAS) == (100, 200_000)


def test_el_archivo_de_20_mib_exactos_pasa_y_con_un_byte_mas_se_rechaza() -> None:
    justo = zip_de({NOMBRE: b"x" * (formato.LIMITE_ARCHIVO - SOBRECARGA)})
    assert len(justo) == formato.LIMITE_ARCHIVO
    assert len(abrir_zip(justo)[NOMBRE]) == formato.LIMITE_ARCHIVO - SOBRECARGA
    mas = zip_de({NOMBRE: b"x" * (formato.LIMITE_ARCHIVO - SOBRECARGA + 1)})
    assert len(mas) == formato.LIMITE_ARCHIVO + 1
    with pytest.raises(PaqueteRechazado, match="20 MiB"):
        abrir_zip(mas)


@pytest.mark.parametrize("tamano,pasa", [(1000, True), (1001, False)])
def test_el_limite_por_entrada_en_su_frontera(monkeypatch, tamano: int, pasa: bool) -> None:
    monkeypatch.setattr(formato, "LIMITE_ENTRADA", 1000)
    datos = zip_de({NOMBRE: b"y" * tamano})
    if pasa:
        assert len(abrir_zip(datos)[NOMBRE]) == 1000
    else:
        with pytest.raises(PaqueteRechazado, match="descomprimido excede 1000"):
            abrir_zip(datos)


@pytest.mark.parametrize("ultimo,pasa", [(500, True), (501, False)])
def test_el_limite_total_en_su_frontera(monkeypatch, ultimo: int, pasa: bool) -> None:
    monkeypatch.setattr(formato, "LIMITE_TOTAL", 2500)
    datos = zip_de({NOMBRE: b"a" * 1000, "informe.json": b"b" * 1000, "cadena.json": b"c" * ultimo})
    if pasa:
        assert sum(len(v) for v in abrir_zip(datos).values()) == 2500
    else:
        with pytest.raises(PaqueteRechazado, match="en total"):
            abrir_zip(datos)


def test_la_relacion_de_compresion_en_enteros() -> None:
    assert relacion_aceptable(100, 1) and not relacion_aceptable(101, 1)
    assert relacion_aceptable(0, 0) and not relacion_aceptable(1, 0)
    assert relacion_aceptable(10_000, 100) and not relacion_aceptable(10_001, 100)


def test_una_bomba_de_compresion_se_rechaza_sin_extraerse() -> None:
    bomba = zip_de({NOMBRE: b"\x00" * (5 * 1024 * 1024)}, zipfile.ZIP_DEFLATED)
    assert len(bomba) < 20_000
    with pytest.raises(PaqueteRechazado, match="comprime más de 100:1"):
        abrir_zip(bomba)


def test_un_tamano_de_cabecera_que_miente_por_debajo_no_deja_pasar_mas_bytes() -> None:
    datos = bytearray(zip_de({NOMBRE: b"z" * 400}))
    for firma_cabecera, desplazamiento in ((b"PK\x03\x04", 22), (b"PK\x01\x02", 24)):
        posicion = datos.find(firma_cabecera)
        fin = posicion + desplazamiento
        datos[fin : fin + 4] = (10).to_bytes(4, "little")
    with pytest.raises(PaqueteRechazado, match="dañado"):
        abrir_zip(bytes(datos))


@pytest.mark.parametrize("nombre", ["../manifiesto.json", "/manifiesto.json", "a/../b.json"])
def test_rutas_inseguras_se_rechazan(nombre: str) -> None:
    with pytest.raises(PaqueteRechazado, match="ruta insegura"):
        abrir_zip(zip_de({nombre: b"{}"}))


def test_ruta_con_barra_invertida_se_rechaza() -> None:
    datos = zip_de({"x_x.json": b"{}"}).replace(b"x_x.json", b"x\\x.json")  # mismo largo
    with pytest.raises(PaqueteRechazado, match="ruta insegura|no admitido"):  # Windows la normaliza
        abrir_zip(datos)


def test_nombre_fuera_de_la_lista_y_directorios_se_rechazan() -> None:
    for nombre in ("otro.json", "anexos/otro.json", "anexos/", "presupuesto.xlsx"):
        with pytest.raises(PaqueteRechazado):
            abrir_zip(zip_de({nombre: b"{}"}))


def test_nombre_repetido_se_rechaza() -> None:
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w") as z:
        z.writestr(NOMBRE, b"{}")
        with pytest.warns(UserWarning, match="Duplicate name"):
            z.writestr(NOMBRE, b"{}")
    with pytest.raises(PaqueteRechazado, match="repite"):
        abrir_zip(flujo.getvalue())


def test_lo_que_no_es_un_zip_se_rechaza_con_un_mensaje() -> None:
    for basura in (b"", b"PK\x03\x04 truncado", b"no soy un zip" * 100):
        with pytest.raises(PaqueteRechazado, match="dañado"):
            abrir_zip(basura)


def test_un_paquete_que_cabe_se_lee_completo() -> None:
    entradas = {NOMBRE: b"{}", "informe.json": b"[]", "anexos/ia.json": b"{}"}
    assert abrir_zip(zip_de(entradas, zipfile.ZIP_DEFLATED)) == entradas
```
**`tests/unit/test_paquete_anexos.py`**
```python
"""Los anexos del paquete (S3 §8.1): filas con huella, filtradas por proyecto, sin cadena propia.

`anexo_de_tablas` serializa lo que existe: una tabla que esta versión no conoce se omite, una
tabla hija se filtra por los padres ya incluidos, y cada entrada trae la huella de su fila. Una
tabla con columna `responsable` está en un anexo o en la lista de las que no viajan (RF-82)."""

from __future__ import annotations

import json

import pytest

from core.budget import crear_proyecto
from core.budget.canonico import huella, json_canonico
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from core.contracts.dominio import Dominio
from migraciones.metadatos import METADATAS_CASO
from paquete import anexos
from tests.fixtures.canonico_minimo import registro, sembrar_minimo


@pytest.fixture
def caso():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        yield sesion
    motor.dispose()


def _anexo(sesion, tablas, proyecto_id) -> dict:
    octetos = anexos.anexo_de_tablas(sesion, "prueba", tablas, proyecto_id)
    return json.loads(octetos)


def test_cada_entrada_trae_la_huella_de_su_fila_y_solo_las_del_proyecto(caso) -> None:
    proyecto, version, _ = sembrar_minimo(caso)
    caso.add(registro(proyecto, None, version))
    otro = crear_proyecto(caso, "OTRO", dominio=Dominio.CIVIL)
    ajeno = registro(proyecto, None, version)
    ajeno.proyecto_id = otro.id  # una fila de otro proyecto no debe viajar
    caso.add(ajeno)
    caso.commit()
    anexo = _anexo(caso, ("registro_cambio",), proyecto.id)
    assert (anexo["formato"], anexo["nombre"], anexo["version_formato"]) == (
        anexos.FORMATO_ANEXO, "prueba", 1)
    [entrada] = anexo["entradas"]
    assert entrada["tabla"] == "registro_cambio"
    assert entrada["huella"] == huella(json_canonico(entrada["fila"]))
    assert entrada["fila"]["proyecto_id"] == proyecto.id
    assert anexos.huellas_de_entradas(anexo) == [entrada["huella"]]


def test_una_tabla_desconocida_se_omite_y_sin_filas_no_hay_anexo(caso) -> None:
    proyecto, _, _ = sembrar_minimo(caso)
    caso.commit()
    assert anexos.anexo_de_tablas(caso, "x", ("tabla_que_no_existe",), proyecto.id) is None
    assert anexos.anexo_de_tablas(caso, "x", ("registro_cambio",), proyecto.id) is None


def test_una_tabla_hija_se_filtra_por_los_padres_incluidos(caso) -> None:
    proyecto, version, _ = sembrar_minimo(caso)
    caso.commit()
    anexo = _anexo(caso, ("presupuesto", "item_computo"), proyecto.id)
    tablas = [e["tabla"] for e in anexo["entradas"]]
    assert tablas.count("presupuesto") == 1 and tablas.count("item_computo") >= 1
    hijos = [e["fila"] for e in anexo["entradas"] if e["tabla"] == "item_computo"]
    assert {h["presupuesto_id"] for h in hijos} == {version.id}


def test_los_decimales_van_como_texto_y_las_fechas_como_iso(caso) -> None:
    proyecto, version, _ = sembrar_minimo(caso)
    caso.commit()
    anexo = _anexo(caso, ("presupuesto",), proyecto.id)
    fila = anexo["entradas"][0]["fila"]
    assert isinstance(fila["fcas"], str) and fila["fecha"] == "2026-11-01"


def test_toda_tabla_con_responsable_viaja_o_esta_en_la_lista_de_las_que_no() -> None:
    declaradas = {*anexos.TABLAS_DE_REAJUSTE, *anexos.TABLAS_DE_CONTROL,
                  *anexos.TABLAS_QUE_NO_VIAJAN}
    con_responsable = {
        tabla.name for metadata in METADATAS_CASO for tabla in metadata.tables.values()
        if "responsable" in tabla.c
    }
    assert sorted(con_responsable - declaradas) == []
```
  `tests/unit/test_migraciones_metadatos.py` ya no dice que el caso lleva dos `MetaData`:
```python
from paquete.modelo import METADATA_PAQUETE


def test_el_caso_lleva_nucleo_espacio_y_paquete_y_la_instalacion_lleva_seguridad() -> None:
    assert len(METADATAS_CASO) == 3
    assert METADATAS_CASO[0] is Base.metadata
    assert METADATAS_CASO[1] is persistencia.METADATA_ESPACIO
    assert METADATAS_CASO[2] is METADATA_PAQUETE
    assert METADATAS_INSTALACION == (BaseSeguridad.metadata,)
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_paquete_formato.py tests/unit/test_paquete_anexos.py
tests/unit/test_migraciones_metadatos.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'paquete'`.
```bash
git add tests/unit/test_paquete_formato.py tests/unit/test_paquete_anexos.py \
  tests/unit/test_migraciones_metadatos.py
git commit -m "test(paquete): formato .silice con sus fronteras y anexos con huella, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`paquete/__init__.py`**
```python
"""Paquete auditado de Sílice (S3)."""
```
**`paquete/formato.py`**
```python
"""Formato `.silice` v1 y su lectura con límites (spec S3 §8.1 y §8.4; maestro §4.5, RV-8).

Un ZIP con nombres fijos y ningún otro. Se lee **en memoria, sin extraer al disco y sin confiar en
los tamaños de las cabeceras**: cada entrada se lee con tope (`read(limite + 1)`) contando los
bytes reales. Los límites son `SUPUESTO_DECLARADO` hasta medir paquetes reales, y cada uno tiene su
frontera exacta (pasa / se rechaza):

| Límite | Pasa | Se rechaza |
|---|---|---|
| tamaño del archivo | 20 MiB (20 971 520 B) | 20 971 521 B |
| descomprimido por entrada | 50 MiB (52 428 800 B) | 52 428 801 B |
| descomprimido en total | 100 MiB (104 857 600 B) | 104 857 601 B |
| relación de compresión por entrada | 100:1 | 101:1 |
| renglones más líneas de composición | 200 000 | 200 001 |
| anidamiento de cualquier JSON | 64 niveles | 65 |

Además se rechaza: nombre fuera de la lista, nombre repetido, ruta absoluta, con `..` o con barra
invertida, entrada cifrada y método de compresión que no sea almacenado o *deflate*.
"""

from __future__ import annotations

import io
import zipfile
from collections import Counter
from collections.abc import Mapping

from core.budget.cadena import huella_de_anexos
from seguridad.json_estricto import JsonRechazado, leer_json

__all__ = [
    "ANEXOS_ADMITIDOS",
    "FORMATO_PAQUETE",
    "LIMITE_ARCHIVO",
    "LIMITE_ENTRADA",
    "LIMITE_FILAS",
    "LIMITE_TOTAL",
    "NOMBRES_FIJOS",
    "OBLIGATORIOS",
    "RELACION_MAXIMA",
    "VERSION_FORMATO",
    "JsonRechazado",
    "PaqueteRechazado",
    "abrir_zip",
    "huella_de_anexos",
    "leer_json",
    "relacion_aceptable",
]

FORMATO_PAQUETE = "silice-paquete"
VERSION_FORMATO = 1
EXTENSION = ".silice"

NOMBRE_MANIFIESTO = "manifiesto.json"
NOMBRE_FIRMA = "firma.ed25519"
NOMBRES_FIJOS = (
    NOMBRE_MANIFIESTO, NOMBRE_FIRMA, "presupuesto.json", "informe.json", "cadena.json",
)
ANEXOS_ADMITIDOS = (
    "anexos/espacio.json", "anexos/reajuste.json", "anexos/control.json", "anexos/ia.json",
)
OBLIGATORIOS = (NOMBRE_MANIFIESTO, "presupuesto.json", "informe.json", "cadena.json")
ADMITIDOS = frozenset(NOMBRES_FIJOS) | frozenset(ANEXOS_ADMITIDOS)

MIB = 1024 * 1024
LIMITE_ARCHIVO = 20 * MIB  # 20 971 520
LIMITE_ENTRADA = 50 * MIB  # 52 428 800
LIMITE_TOTAL = 100 * MIB  # 104 857 600
RELACION_MAXIMA = 100
LIMITE_FILAS = 200_000
METODOS_ADMITIDOS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)


class PaqueteRechazado(ValueError):  # noqa: N818
    """El archivo no se puede abrir como paquete; el mensaje dice por qué y qué hacer."""


def relacion_aceptable(descomprimido: int, comprimido: int) -> bool:
    """`descomprimido <= 100 x comprimido`, en enteros (100:1 pasa, 101:1 se rechaza)."""
    return descomprimido <= RELACION_MAXIMA * comprimido


def _nombre_inseguro(nombre: str) -> bool:
    return (
        nombre.startswith(("/", "\\"))
        or "\\" in nombre
        or ":" in nombre
        or any(parte in {"..", "."} for parte in nombre.split("/"))
        or nombre.endswith("/")
    )


def abrir_zip(datos: bytes) -> dict[str, bytes]:
    """Los archivos del paquete por nombre, o `PaqueteRechazado`. No toca el disco."""
    if len(datos) > LIMITE_ARCHIVO:
        raise PaqueteRechazado(
            f"El archivo pesa {len(datos)} bytes y el máximo es {LIMITE_ARCHIVO} (20 MiB). "
            "Pida al emisor un paquete más pequeño."
        )
    try:
        zip_ = zipfile.ZipFile(io.BytesIO(datos))
    except (zipfile.BadZipFile, OSError, ValueError):
        raise PaqueteRechazado(
            "El archivo no es un paquete de Silice válido (el ZIP está dañado). Pida uno nuevo."
        ) from None
    with zip_:
        informacion = zip_.infolist()
        repetidos = [n for n, c in Counter(i.filename for i in informacion).items() if c > 1]
        if repetidos:
            raise PaqueteRechazado(f"El paquete repite el archivo {repetidos[0]!r}: es inseguro.")
        for i in informacion:
            if _nombre_inseguro(i.filename):
                raise PaqueteRechazado(f"El paquete trae una ruta insegura: {i.filename!r}.")
            if i.filename not in ADMITIDOS:
                raise PaqueteRechazado(f"El paquete trae un archivo no admitido: {i.filename!r}.")
            if i.flag_bits & 0x1:
                raise PaqueteRechazado(f"El archivo {i.filename!r} del paquete está cifrado.")
            if i.compress_type not in METODOS_ADMITIDOS:
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} usa un método de compresión no admitido."
                )
        contenido: dict[str, bytes] = {}
        total = 0
        for i in informacion:
            try:
                with zip_.open(i) as flujo:
                    octetos = flujo.read(LIMITE_ENTRADA + 1)
            except (zipfile.BadZipFile, EOFError, OSError, RuntimeError, NotImplementedError):
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} del paquete está dañado. Pida uno nuevo."
                ) from None
            if len(octetos) > LIMITE_ENTRADA:
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} descomprimido excede {LIMITE_ENTRADA} bytes."
                )
            total += len(octetos)
            if total > LIMITE_TOTAL:
                raise PaqueteRechazado(
                    f"El paquete descomprimido excede {LIMITE_TOTAL} bytes en total (bomba de "
                    "compresión)."
                )
            if not relacion_aceptable(len(octetos), i.compress_size):
                raise PaqueteRechazado(
                    f"El archivo {i.filename!r} se comprime más de {RELACION_MAXIMA}:1: es "
                    "sospechoso."
                )
            contenido[i.filename] = octetos
    return contenido


def comprobar_salida(archivos: Mapping[str, bytes], tamano_zip: int) -> None:
    """Lo que `exportar` exige antes de ofrecer el paquete: que el revisor no lo rechace (22f)."""
    if tamano_zip > LIMITE_ARCHIVO:
        raise PaqueteRechazado(
            f"El paquete pesaría {tamano_zip} bytes y el máximo es {LIMITE_ARCHIVO}: no se "
            "genera un paquete que el revisor rechazaría."
        )
    for nombre, octetos in archivos.items():
        if len(octetos) > LIMITE_ENTRADA:
            raise PaqueteRechazado(f"{nombre} excede {LIMITE_ENTRADA} bytes: no se genera.")
    if sum(len(o) for o in archivos.values()) > LIMITE_TOTAL:
        raise PaqueteRechazado("El paquete excede el total descomprimido permitido.")
```
**`paquete/modelo.py`**
```python
"""Tablas `paq_*` de la base del caso: lo que quien revisa guarda de cada paquete (S3 §7.4).

Como `esp_*`, viven en un `MetaData` propio y no llevan clave foránea a `core.models`: su destino
de migración es el del caso (`METADATAS_CASO`, revisión `caso_NNNN_s3_paquete`). Un paquete se
guarda por el SHA-256 de su archivo (único: el mismo archivo no se duplica, 23h). Nada de esto
entra a las versiones del caso ni al catálogo (DA-S3-7): el paquete se reaudita en memoria.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Connection,
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
)
from sqlalchemy.orm import Session

__all__ = [
    "METADATA_PAQUETE",
    "TABLAS",
    "buscar_por_huella",
    "crear_esquema_paquete",
    "dictamenes_de",
    "paquetes_del_proyecto",
    "paq_dictamen",
    "paq_recibido",
    "registrar_dictamen",
    "registrar_recibido",
]

METADATA_PAQUETE = MetaData()

paq_recibido = Table(
    "paq_recibido",
    METADATA_PAQUETE,
    Column("id", Integer, primary_key=True),
    Column("archivo", String(255), nullable=False),
    Column("huella_archivo", String(64), nullable=False, unique=True),
    Column("paquete_id", String(36), nullable=False),
    Column("destinatario", String(200), nullable=False),
    Column("ruta", String(500), nullable=False),
    Column("empresa_declarada", String(200), nullable=False),
    Column("empresa_verificada", String(200), nullable=False),
    Column("huella_clave", String(64), nullable=False),
    Column("estado", String(20), nullable=False),
    Column("proyecto", String(200), nullable=False),
    Column("codigo", String(40), nullable=False),
    Column("emitido", DateTime, nullable=False),
    Column("cadena", Text, nullable=False),
    Column("huellas_anexos", Text, nullable=False),
    Column("recibido_por", String(120), nullable=False),
    Column("fecha", DateTime, nullable=False),
)
paq_dictamen = Table(
    "paq_dictamen",
    METADATA_PAQUETE,
    Column("id", Integer, primary_key=True),
    Column("paquete_id", Integer, ForeignKey("paq_recibido.id"), nullable=False),
    Column("huella_archivo", String(64), nullable=False),
    Column("resultado", String(20), nullable=False),  # conforme | con observaciones | rechazado
    Column("notas", Text, nullable=False),
    Column("usuario", String(120), nullable=False),
    Column("fecha", DateTime, nullable=False),
    Column("estado_verificacion", String(20), nullable=False),
    Column("revisor_armo", Boolean, nullable=False),
)
TABLAS = (paq_recibido, paq_dictamen)
RESULTADOS = ("conforme", "con observaciones", "rechazado")


def crear_esquema_paquete(destino: Engine | Connection) -> None:
    """Crea las tablas `paq_*` que falten (las pruebas; en el producto las crea la revisión)."""
    METADATA_PAQUETE.create_all(destino)


def buscar_por_huella(sesion: Session, huella_archivo: str):
    """La fila de `paq_recibido` con ese SHA-256, o `None` (23h: ya se recibió este archivo)."""
    return sesion.execute(
        select(paq_recibido).where(paq_recibido.c.huella_archivo == huella_archivo)
    ).mappings().first()


def paquetes_del_proyecto(sesion: Session, proyecto: str, huella_clave: str):
    """Lo recibido del mismo proyecto y emisor, del más viejo al más nuevo (para §6.5)."""
    return sesion.execute(
        select(paq_recibido)
        .where(paq_recibido.c.proyecto == proyecto, paq_recibido.c.huella_clave == huella_clave)
        .order_by(paq_recibido.c.id)
    ).mappings().all()


def registrar_recibido(sesion: Session, **valores) -> int:
    """Guarda un paquete recibido y devuelve su id. No confirma."""
    resultado = sesion.execute(insert(paq_recibido).values(**valores))
    return int(resultado.inserted_primary_key[0])


def registrar_dictamen(
    sesion: Session,
    *,
    paquete_id: int,
    huella_archivo: str,
    resultado: str,
    notas: str,
    usuario: str,
    fecha: datetime,
    estado_verificacion: str,
    revisor_armo: bool,
) -> int:
    """Guarda el dictamen atado al SHA-256 del archivo. Notas obligatorias salvo «conforme»."""
    if resultado not in RESULTADOS:
        raise ValueError(f"resultado desconocido: {resultado!r}; se espera {RESULTADOS}")
    if resultado != "conforme" and not notas.strip():
        raise ValueError("Un dictamen con observaciones o de rechazo necesita notas.")
    fila = sesion.execute(
        insert(paq_dictamen).values(
            paquete_id=paquete_id, huella_archivo=huella_archivo, resultado=resultado,
            notas=notas.strip(), usuario=usuario, fecha=fecha,
            estado_verificacion=estado_verificacion, revisor_armo=revisor_armo,
        )
    )
    return int(fila.inserted_primary_key[0])


def dictamenes_de(sesion: Session, huella_archivo: str):
    return sesion.execute(
        select(paq_dictamen).where(paq_dictamen.c.huella_archivo == huella_archivo)
        .order_by(paq_dictamen.c.id)
    ).mappings().all()
```
**`paquete/anexos.py`**
```python
"""Los anexos de S1 y S2 del paquete: filas con huella, SIN cadena propia (spec S3 §8.1).

`anexo_de_tablas` serializa, de las tablas que se le piden, las filas del proyecto (por su
`proyecto_id` o, si no la tienen, por la clave foránea hacia una tabla ya incluida). Cada fila lleva
su propia huella SHA-256; borrar una fila en la base antes de exportar NO se detecta dentro de la
base (límite declarado, S3 §12): solo entre entregas (`anterioridad`).

Los nombres de las tablas son los de S1 y S2 (specs, §5.2 y §6.1). Una tabla que esta versión de
Sílice no conoce se omite sin error: el anexo trae lo que existe. Una prueba recorre los metadatos
y exige que **toda tabla con una columna `responsable`** esté en un anexo o en la lista de las que
no viajan (RF-82), así que una tabla nueva sin dueño hace fallar la lista.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Table, false, select
from sqlalchemy.orm import Session

from core.budget.canonico import huella, json_canonico
from core.models import Base

__all__ = [
    "FORMATO_ANEXO",
    "TABLAS_DE_CONTROL",
    "TABLAS_DE_REAJUSTE",
    "TABLAS_QUE_NO_VIAJAN",
    "anexo_de_tablas",
    "huellas_de_entradas",
]

FORMATO_ANEXO = "silice-anexo"
#: S1 (`anexos/reajuste.json`): índices usados con su fuente y la huella del archivo del BCV;
#: moneda del proyecto, cláusula y estudios de reajuste.
TABLAS_DE_REAJUSTE = (
    "serie_indice", "importacion_indice", "valor_indice", "moneda_proyecto", "lista_empresa",
    "clausula_reajuste", "componente_clausula", "estudio_reajuste", "periodo_reajuste",
    "ejecutado_periodo",
)
#: S2 (`anexos/control.json`): línea base y calendario, valuaciones, anulaciones, costos incurridos y
#: decisiones de recuperación, con la fecha de registro de cada valuación.
TABLAS_DE_CONTROL = (
    "linea_base_control", "calendario_obra", "parametros_control", "valuacion",
    "linea_valuacion", "anulacion_valuacion", "costo_real", "decision_recuperacion",
)
#: Tablas con columna `responsable` que NO viajan: ya están en `presupuesto.json` y `cadena.json`
#: (el `RegistroCambio` va en la cadena) o son del catálogo.
TABLAS_QUE_NO_VIAJAN = ("registro_cambio",)


def _valor(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return base64.b64encode(valor).decode("ascii")
    return valor


def _filas(sesion: Session, tabla: Table, condicion) -> list[dict[str, Any]]:
    consulta = select(tabla)
    if condicion is not None:
        consulta = consulta.where(condicion)
    llaves = list(tabla.primary_key.columns)
    if llaves:
        consulta = consulta.order_by(*llaves)
    return [
        {col: _valor(valor) for col, valor in fila.items()}
        for fila in sesion.execute(consulta).mappings()
    ]


def anexo_de_tablas(
    sesion: Session, nombre: str, tablas: Sequence[str], proyecto_id: int
) -> bytes | None:
    """El JSON canónico del anexo `nombre`, o `None` si no hay ninguna fila que enviar."""
    incluidas: dict[str, list[dict[str, Any]]] = {}
    for tabla_nombre in tablas:
        tabla = Base.metadata.tables.get(tabla_nombre)
        if tabla is None:
            continue
        condicion = None
        if "proyecto_id" in tabla.c:
            condicion = tabla.c.proyecto_id == proyecto_id
        else:  # sin proyecto: se filtra por el padre ya incluido; sin padre, es global
            for clave in tabla.foreign_keys:
                padre = clave.column.table.name
                if padre in incluidas:
                    ids = {fila[clave.column.name] for fila in incluidas[padre]}
                    condicion = clave.parent.in_(ids) if ids else false()
                    break
        incluidas[tabla_nombre] = _filas(sesion, tabla, condicion)
    entradas = [
        {"tabla": tabla, "fila": fila, "huella": huella(json_canonico(fila))}
        for tabla, filas in incluidas.items()
        for fila in filas
    ]
    if not entradas:
        return None
    return json_canonico({"formato": FORMATO_ANEXO, "nombre": nombre, "version_formato": 1,
                          "entradas": entradas})


def huellas_de_entradas(anexo: dict[str, Any]) -> list[str]:
    """Las huellas de cada entrada de un anexo ya leído (para comparar entre entregas, §6.5)."""
    return [entrada["huella"] for entrada in anexo.get("entradas", [])]
```
**`migraciones/caso/versions/caso_0008_s3_paquete.py`**
```python
"""S3-3: `paq_recibido` y `paq_dictamen`, lo que recibe y dictamina quien revisa (spec S3 §8.3, §9).

Tablas aditivas de `paquete/modelo.py` en la base del caso, sin clave foránea a `core.models`: el
archivo recibido se guarda en la carpeta de paquetes y aquí quedan su SHA-256 (único), su estado de
verificación y la cadena que traía; el dictamen queda atado al SHA-256 del archivo y al estado de
ese momento. Ninguna tabla existente cambia. `crear_o_verificar`: se adopta una base que ya las
tenga (`paquete.modelo.crear_esquema_paquete`).
"""

from alembic import op

from migraciones.comun import TablaCongelada, borrar_tablas, crear_o_verificar

revision = "caso_0008_s3_paquete"
down_revision = "caso_0007_s3_cadena"
branch_labels = None
depends_on = None

TABLAS = (
    TablaCongelada(
        nombre="paq_recibido",
        ddl=(
            "CREATE TABLE paq_recibido (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tarchivo VARCHAR(255) NOT NULL, \n"
            "\thuella_archivo VARCHAR(64) NOT NULL, \n"
            "\tpaquete_id VARCHAR(36) NOT NULL, \n"
            "\tdestinatario VARCHAR(200) NOT NULL, \n"
            "\truta VARCHAR(500) NOT NULL, \n"
            "\tempresa_declarada VARCHAR(200) NOT NULL, \n"
            "\tempresa_verificada VARCHAR(200) NOT NULL, \n"
            "\thuella_clave VARCHAR(64) NOT NULL, \n"
            "\testado VARCHAR(20) NOT NULL, \n"
            "\tproyecto VARCHAR(200) NOT NULL, \n"
            "\tcodigo VARCHAR(40) NOT NULL, \n"
            "\temitido DATETIME NOT NULL, \n"
            "\tcadena TEXT NOT NULL, \n"
            "\thuellas_anexos TEXT NOT NULL, \n"
            "\trecibido_por VARCHAR(120) NOT NULL, \n"
            "\tfecha DATETIME NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tUNIQUE (huella_archivo)\n"
            ")"
        ),
    ),
    TablaCongelada(
        nombre="paq_dictamen",
        ddl=(
            "CREATE TABLE paq_dictamen (\n"
            "\tid INTEGER NOT NULL, \n"
            "\tpaquete_id INTEGER NOT NULL, \n"
            "\thuella_archivo VARCHAR(64) NOT NULL, \n"
            "\tresultado VARCHAR(20) NOT NULL, \n"
            "\tnotas TEXT NOT NULL, \n"
            "\tusuario VARCHAR(120) NOT NULL, \n"
            "\tfecha DATETIME NOT NULL, \n"
            "\testado_verificacion VARCHAR(20) NOT NULL, \n"
            "\trevisor_armo BOOLEAN NOT NULL, \n"
            "\tPRIMARY KEY (id), \n"
            "\tFOREIGN KEY(paquete_id) REFERENCES paq_recibido (id)\n"
            ")"
        ),
    ),
)

def upgrade() -> None:
    crear_o_verificar(op.get_bind(), TABLAS)


def downgrade() -> None:
    borrar_tablas(op.get_bind(), TABLAS)
```
  La `MetaData` del paquete entra a la lista del caso:
```python
from paquete.modelo import METADATA_PAQUETE

METADATAS_CASO: tuple[MetaData, ...] = (Base.metadata, METADATA_ESPACIO, METADATA_PAQUETE)
```
  La CI mide la cobertura de `seguridad/` y de `paquete/` y exige 80 %; `S3-M4` de la meta lo
  vigila (cambiar la fase de `S3-M4` en `scripts/meta_silice_s3.py` de `"S3-1"` a `"S3-3"`):
```diff
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -113,5 +113,6 @@
           uv run --no-sync pytest -W error -p no:cacheprovider
           --junitxml=reporte-pruebas.xml
-          --cov=core --cov=ml --cov=api --cov=adapters --cov-report=term
+          --cov=core --cov=ml --cov=api --cov=adapters --cov=seguridad --cov=paquete
+          --cov-report=term
 
       - name: Sin pruebas omitidas
@@ -135,4 +136,9 @@
         run: uv run --no-sync coverage report --include="adapters/espacio/*" --fail-under=80
 
+      - name: Cobertura de seguridad/ y paquete/ >= 80 % (S3, RNF-16)
+        if: runner.os == 'Linux'
+        run: >-
+          uv run --no-sync coverage report --include="seguridad/*,paquete/*" --fail-under=80
+
       - name: Artefactos reproducibles
         if: runner.os == 'Linux'
```
- [ ] **Paso 4: Correrlas y ver el verde** (y las migraciones del caso)
Run: `uv run pytest tests/unit/test_paquete_formato.py tests/unit/test_paquete_anexos.py
tests/unit/test_migraciones_metadatos.py tests/integration/test_migraciones.py
tests/unit/test_meta_silice_s3.py -v -W error` → verde. Run: `uv run ruff check paquete migraciones`
→ limpio.
- [ ] **Paso 5: Commit**
```bash
git add paquete migraciones/caso/versions/caso_0008_s3_paquete.py migraciones/metadatos.py \
  .github/workflows/ci.yml scripts/meta_silice_s3.py
git commit -m "feat(paquete): formato .silice con limites, tablas del revisor y anexos con huella" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 15: Exportar y verificar un paquete

**Rama:** `inc/080-s3-3-paquete`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `paquete/exportar.py`, `paquete/verificar.py`, `tests/fixtures/paquetes.py`
- Prueba: `tests/unit/test_paquete_verificar.py`, `tests/unit/test_paquete_anterioridad.py`

**Interfaces:**
- Consume: `paquete.formato.*` (tarea 14), `seguridad.firma.*` (tarea 13),
  `core.budget.cadena.{GENESIS, huella_de_anexos, huella_de_filas_de_cambios, huella_del_eslabon}`
  (tarea 8), `core.budget.canonico.{json_canonico, leer}` (tarea 7),
  `tests/fixtures/canonico/ejemplo_v1.py`.
- Produce:
  - `paquete.exportar`: `class Emisor`
  - `paquete.exportar`: `def construir_paquete(*, presupuesto: bytes, informe: bytes, cadena:
      bytes, anexos: Mapping[str, bytes], emisor: Emisor, destinatario: str | None, proyecto:
      str, codigo: str, moneda: str, total: str, ultima_huella: str, ahora: datetime,
      version_silice: str, privada: bytes | None=None, paquete_id: str | None=None) -> bytes`
  - `paquete.verificar`: `class EmpresaConocida`
  - `paquete.verificar`: `class Verificacion`
  - `paquete.verificar`: `def armar_cadena_json(eslabones: Sequence[Mapping[str, Any]], cambios:
      Mapping[str, Sequence[Sequence[str]]]) -> dict[str, Any]`
  - `paquete.verificar`: `def verificar(datos: bytes, *, buscar_empresa: BuscarEmpresa,
      recibido_en: datetime, mi_empresa: tuple[str | None, str | None]=(None, None)) ->
      Verificacion`
  - `paquete.verificar`: `class Anterioridad`
  - `paquete.verificar`: `def evaluar_anterioridad(manifiesto: Mapping[str, Any], cadena:
      Mapping[str, Any], huellas_de_anexos: Mapping[str, Sequence[str]], sha256: str, previos:
      Sequence[Mapping]) -> Anterioridad`
  - `paquete.verificar`: `def banner(v: Verificacion, nombre_seguro: Callable[[str], str]=lambda
      texto: texto) -> tuple[str, str]`
  - `tests.fixtures.paquetes`: `EMPRESA`, `paquete(par, presupuesto, anexos, **mas) -> bytes`, y el
    resto de fabricantes de paquetes (firmados, sin firma, alterados).

**Estados** (S3 §8.3): **verificado** (todo cuadra y la firma es de una empresa registrada y activa,
o retirada si el archivo se recibió antes del retiro), **no verificado** (sin firma, empresa no
registrada, clave revocada, o retirada y recibido después; se audita igual), **alterado** (una
huella, la firma o la cadena no cuadran; se audita igual para mostrar qué contiene) y **rechazado**
(ZIP dañado o inseguro, fuera de límites, de un formato que no se conoce). La verificación **nunca
usa la clave que trae el paquete**: busca la empresa por la huella completa de su clave en lo que
`verificar` recibe de la base de quien revisa. `verificar` no toca la base. La **anterioridad**
(S3 §6.5) compara la cadena con la del último paquete recibido del mismo proyecto y emisor: si una
versión anterior cambió, lo dice con la versión y la fecha. **No viaja el Excel** (DA-S3-10): quien
revisa lo regenera. El ZIP es reproducible: con el mismo `paquete_id` y la misma fecha, los
mismos bytes.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/fixtures/paquetes.py`**
```python
"""Paquetes `.silice` armados a mano para las pruebas de verificación (S3-3; spec §13.3).

`paquete(...)` construye un paquete SIN pasar por la base: el `presupuesto.json` es el texto que se
le da (la verificación no lo interpreta) y la cadena es sintética pero consistente (sus huellas se
calculan con las mismas funciones públicas de `core.budget.cadena`). `reempaquetar` cambia, quita
o agrega archivos de un paquete ya hecho SIN tocar su manifiesto ni su firma: así se fabrican las
alteraciones de la tabla de S3 §13.3.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Mapping
from datetime import datetime

from core.budget.cadena import (
    GENESIS,
    huella_de_anexos,
    huella_de_filas_de_cambios,
    huella_del_eslabon,
)
from core.budget.canonico import huella, json_canonico
from paquete.exportar import Emisor, construir_paquete
from paquete.verificar import armar_cadena_json
from seguridad import firma

EMITIDO = datetime(2026, 11, 10, 9, 30, 0)
PRESUPUESTO = b'{"formato":"silice-presupuesto","version_formato":1,"nota":"de prueba"}'
INFORME = b'{"formato":"silice-informe","version_formato":1,"hallazgos":[]}'
ESPACIO = b'{"ambientes":[],"puntos":[]}'
CONTROL = b'{"formato":"silice-anexo","nombre":"control","entradas":[]}'
REAJUSTE = b'{"formato":"silice-anexo","nombre":"reajuste","entradas":[]}'
IA = b'{"formato":"silice-ia","pasos":[]}'
CUATRO_ANEXOS = {
    "anexos/espacio.json": ESPACIO, "anexos/reajuste.json": REAJUSTE,
    "anexos/control.json": CONTROL, "anexos/ia.json": IA,
}
EMPRESA = "Contratista Demo, C.A."


def cadena_para(presupuesto: bytes, anexos: Mapping[str, bytes], codigos=("004", "005")):
    """`(cadena.json, ultima huella)`: una cadena de `codigos`, la última atada a `presupuesto`."""
    eslabones, cambios, anterior = [], {}, GENESIS
    for i, codigo in enumerate(codigos):
        ultima = i == len(codigos) - 1
        filas = [["apu", "MIN-001|Arena", "cantidad", "1.00", "1.50", "memoria", "Ana <ana>",
                  f"2026-11-0{i + 1}T08:00:00"]]
        contenido = huella(presupuesto) if ultima else huella(f"v{codigo}".encode())
        anexos_v = {"anexos/espacio.json": anexos["anexos/espacio.json"]} if (
            ultima and "anexos/espacio.json" in anexos) else {}
        cambios_h, anexos_h = huella_de_filas_de_cambios(filas), huella_de_anexos(anexos_v)
        fecha = datetime(2026, 11, 1 + i, 8, 0, 0)
        h = huella_del_eslabon(
            anterior=anterior, codigo=codigo, contenido=contenido, cambios=cambios_h,
            anexos=anexos_h, usuario="Ana <ana>", fecha_hora=fecha, tipo="normal",
            version_formato=1,
        )
        eslabones.append({
            "codigo": codigo, "anterior": anterior, "huella_contenido": contenido,
            "huella_cambios": cambios_h, "huella_anexos": anexos_h, "huella_eslabon": h,
            "usuario": "Ana <ana>", "fecha_hora": fecha.isoformat(), "tipo": "normal",
            "version_formato": 1,
        })
        cambios[codigo] = filas
        anterior = h
    return json_canonico(armar_cadena_json(eslabones, cambios)), anterior


def paquete(
    *, par: firma.ParDeClaves | None = None, empresa: str | None = EMPRESA,
    anexos: Mapping[str, bytes] | None = None, destinatario: str | None = None,
    paquete_id: str = "11111111-1111-4111-8111-111111111111", codigo: str = "005",
    presupuesto: bytes = PRESUPUESTO, codigos=("004", "005"), declarar_clave: bool = True,
    emitido: datetime = EMITIDO,
) -> bytes:
    """Un paquete válido. Con `par` lo firma y declara su huella; sin él, queda sin firma."""
    anexos = dict(CUATRO_ANEXOS if anexos is None else anexos)
    cadena, ultima = cadena_para(presupuesto, anexos, codigos)
    huella_clave = firma.huella_completa(par.publica) if par and declarar_clave else None
    return construir_paquete(
        presupuesto=presupuesto, informe=INFORME, cadena=cadena, anexos=anexos,
        emisor=Emisor(empresa, huella_clave, "Ana <ana>"), destinatario=destinatario,
        proyecto="MIN-001", codigo=codigo, moneda="USD", total="836.79750000",
        ultima_huella=ultima, ahora=emitido, version_silice="0.8.0",
        privada=par.privada if par else None, paquete_id=paquete_id,
    )


def leer_zip(datos: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        return {i.filename: z.read(i) for i in z.infolist()}


def escribir_zip(archivos: Mapping[str, bytes]) -> bytes:
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, octetos in archivos.items():
            z.writestr(nombre, octetos)
    return flujo.getvalue()


def reempaquetar(datos: bytes, cambios: Mapping[str, bytes | None]) -> bytes:
    """El mismo paquete con `cambios` (`None` quita el archivo); sin tocar manifiesto ni firma."""
    archivos = leer_zip(datos)
    for nombre, octetos in cambios.items():
        if octetos is None:
            archivos.pop(nombre, None)
        else:
            archivos[nombre] = octetos
    return escribir_zip(archivos)


def con_manifiesto(datos: bytes, **campos) -> bytes:
    """El paquete con campos del manifiesto cambiados (la firma queda la vieja)."""
    archivos = leer_zip(datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    manifiesto.update(campos)
    archivos["manifiesto.json"] = json_canonico(manifiesto)
    return escribir_zip(archivos)


def refirmar(datos: bytes, par: firma.ParDeClaves, huella_declarada: str | None = None) -> bytes:
    """Rehace el manifiesto con una huella de clave (opcional) y lo firma con `par`."""
    archivos = leer_zip(datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    if huella_declarada is not None:
        manifiesto["huella_clave"] = huella_declarada
    archivos["manifiesto.json"] = json_canonico(manifiesto)
    archivos["firma.ed25519"] = firma.firmar(
        par.privada, firma.DOMINIO_PAQUETE, archivos["manifiesto.json"]
    )
    return escribir_zip(archivos)
```
**`tests/unit/test_paquete_verificar.py`**
```python
"""Seguridad del paquete: el estado esperado de cada caso de S3 §13.3 (RF-85, RF-86, RNF-16)."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta

import pytest

from core.budget.canonico import json_canonico
from paquete.verificar import (
    ALTERADO,
    NO_VERIFICADO,
    RECHAZADO,
    VERIFICADO,
    EmpresaConocida,
    banner,
    verificar,
)
from seguridad import firma
from tests.fixtures.paquetes import (
    CUATRO_ANEXOS,
    EMPRESA,
    ESPACIO,
    con_manifiesto,
    escribir_zip,
    leer_zip,
    paquete,
    reempaquetar,
    refirmar,
)

RECIBIDO = datetime(2026, 11, 12, 10, 0)
PAR = firma.generar_par()
HUELLA = firma.huella_completa(PAR.publica)


def conocidas(estado="activa", fecha=None, par=PAR, nombre=EMPRESA):
    conocida = EmpresaConocida(nombre, par.publica, estado, fecha)
    tabla = {firma.huella_completa(par.publica): conocida}
    return tabla.get


def ver(datos, buscar=None, recibido=RECIBIDO, **mas):
    return verificar(datos, buscar_empresa=buscar or conocidas(), recibido_en=recibido, **mas)


def firmado(**mas) -> bytes:
    return paquete(par=PAR, **mas)


def test_integro_firmado_con_los_cuatro_anexos_es_verificado() -> None:
    v = ver(firmado())
    assert (v.estado, v.motivo, v.empresa_verificada) == (VERIFICADO, "firma_valida", EMPRESA)
    assert set(v.archivos) >= {"manifiesto.json", "firma.ed25519", *CUATRO_ANEXOS}
    color, texto = banner(v)
    assert color == "verde" and texto.startswith(
        "Verificado: emitido por Contratista Demo, C.A. el 2026-11-10. No se alteró")


def test_firmada_con_clave_retirada_vale_si_se_recibio_antes_del_retiro() -> None:
    retiro = RECIBIDO + timedelta(days=1)
    v = ver(firmado(), conocidas("retirada", retiro))
    assert (v.estado, v.retirada) == (VERIFICADO, True) and v.avisos
    assert "retirada" in v.motivo


def test_firmada_con_clave_retirada_y_recibida_despues_es_no_verificado() -> None:
    v = ver(firmado(), conocidas("retirada", RECIBIDO - timedelta(days=1)))
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "retirada_tarde")


def test_un_byte_cambiado_en_el_presupuesto_sin_tocar_el_manifiesto_es_alterado() -> None:
    malo = reempaquetar(firmado(), {"presupuesto.json": b'{"formato":"silice-presupuesto","x":2}'})
    v = ver(malo)
    assert (v.estado, v.motivo) == (ALTERADO, "integridad")
    assert "presupuesto.json cambió después de firmarse" in v.detalle
    assert "Alterado: presupuesto.json cambió después de firmarse" in banner(v)[1]


def test_un_byte_cambiado_en_un_anexo_es_alterado() -> None:
    v = ver(reempaquetar(firmado(), {"anexos/control.json": b"{}"}))
    assert v.estado == ALTERADO and "anexos/control.json cambió" in v.detalle


def test_presupuesto_cambiado_con_manifiesto_rehecho_y_firma_vieja_es_alterado_por_la_firma():
    original = firmado()
    nuevo = b'{"formato":"silice-presupuesto","version_formato":1,"nota":"otra"}'
    archivos = leer_zip(original)
    manifiesto = json.loads(archivos["manifiesto.json"])
    from core.budget.canonico import huella

    for a in manifiesto["archivos"]:
        if a["nombre"] == "presupuesto.json":
            a["sha256"], a["tamano"] = huella(nuevo), len(nuevo)
    archivos["presupuesto.json"], archivos["manifiesto.json"] = nuevo, json_canonico(manifiesto)
    v = ver(escribir_zip(archivos))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


@pytest.mark.parametrize("tamano", [0, 63])
def test_firma_vacia_o_truncada_es_alterado(tamano: int) -> None:
    datos = firmado()
    firma_buena = leer_zip(datos)["firma.ed25519"]
    v = ver(reempaquetar(datos, {"firma.ed25519": firma_buena[:tamano]}))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_la_firma_de_un_aviso_de_revocacion_no_vale_como_firma_de_paquete() -> None:
    datos = firmado()
    manifiesto = leer_zip(datos)["manifiesto.json"]
    otro_dominio = firma.firmar(PAR.privada, firma.DOMINIO_REVOCACION, manifiesto)
    v = ver(reempaquetar(datos, {"firma.ed25519": otro_dominio}))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")


def test_el_manifiesto_que_lista_un_archivo_ausente_es_alterado() -> None:
    v = ver(reempaquetar(firmado(), {"anexos/ia.json": None}))
    assert v.estado == ALTERADO and "falta anexos/ia.json" in v.detalle


def test_un_archivo_admitido_que_el_manifiesto_no_lista_es_alterado() -> None:
    datos = paquete(par=PAR, anexos={"anexos/espacio.json": ESPACIO})
    v = ver(reempaquetar(datos, {"anexos/ia.json": b"{}"}))
    assert v.estado == ALTERADO and "anexos/ia.json" in v.detalle and "no lo lista" in v.detalle


def test_un_manifiesto_con_clave_duplicada_se_rechaza() -> None:
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = b'{"formato":"silice-paquete","formato":"silice-paquete"}'
    v = ver(escribir_zip(archivos))
    assert v.estado == RECHAZADO and "duplicada" in v.detalle


def test_refirmado_con_otra_clave_que_dice_ser_la_empresa_registrada_es_alterado() -> None:
    impostor = firma.generar_par()
    v = ver(refirmar(firmado(), impostor, huella_declarada=HUELLA))
    assert (v.estado, v.motivo) == (ALTERADO, "firma")  # se verifica con la clave REGISTRADA


def test_refirmado_con_clave_no_registrada_y_otro_nombre_es_no_verificado_con_dice_venir_de():
    impostor = firma.generar_par()
    ajeno = paquete(par=impostor, empresa="**Empresa Falsa** ![x](http://127.0.0.1:9/p.png)")
    v = ver(ajeno)
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "empresa_no_registrada")
    color, texto = banner(v, nombre_seguro=lambda s: s.replace("*", "\\*").replace("![", "\\!["))
    assert color == "ambar" and "dice venir de \\*\\*Empresa Falsa\\*\\*" in texto
    assert "![" not in texto.replace("\\![", "")


def test_sin_firma_es_no_verificado_y_el_banner_lo_dice_con_esas_palabras() -> None:
    v = ver(paquete(par=None))
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "sin_firma")
    assert "no que nadie lo cambió" in banner(v)[1] and "Se audita igual" in banner(v)[1]


def test_clave_revocada_es_no_verificado() -> None:
    v = ver(firmado(), conocidas("revocada"))
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "revocada")


def test_formato_2_se_rechaza_con_su_mensaje() -> None:
    v = ver(con_manifiesto(firmado(), version_formato=2))
    assert v.estado == RECHAZADO and "versión de formato 2" in v.detalle


@pytest.mark.parametrize("valor", ["NaN", "Infinity", "-Infinity"])
def test_constantes_no_finitas_en_el_manifiesto_se_rechazan(valor: str) -> None:
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = (b'{"formato":"silice-paquete","version_formato":1,"x":%s}'
                                   % valor.encode())
    assert ver(escribir_zip(archivos)).estado == RECHAZADO


def test_un_manifiesto_con_cifra_hostil_se_rechaza() -> None:
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = (
        b'{"formato":"silice-paquete","version_formato":1,"x":1E+999999999}'
    )
    assert ver(escribir_zip(archivos)).estado == RECHAZADO


def test_anidamiento_de_65_niveles_en_el_manifiesto_se_rechaza() -> None:
    archivos = leer_zip(firmado())
    archivos["manifiesto.json"] = b"[" * 65 + b"]" * 65
    assert ver(escribir_zip(archivos)).estado == RECHAZADO


def test_un_paquete_alterado_se_audita_igual_y_conserva_sus_archivos() -> None:
    v = ver(reempaquetar(firmado(), {"presupuesto.json": b"{}"}))
    assert v.estado == ALTERADO and v.legible and "presupuesto.json" in v.archivos


def test_un_paquete_rechazado_no_se_audita() -> None:
    v = ver(b"no es un zip")
    assert v.estado == RECHAZADO and not v.legible
    assert "dañado" in v.detalle and banner(v)[0] == "rojo"


def test_la_cadena_que_no_cuadra_es_alterada_aunque_no_tenga_firma() -> None:
    datos = paquete(par=None)
    archivos = leer_zip(datos)
    cadena = json.loads(archivos["cadena.json"])
    cadena["eslabones"][0]["usuario"] = "Otra Persona"
    nueva = json_canonico(cadena)
    manifiesto = json.loads(archivos["manifiesto.json"])
    from core.budget.canonico import huella

    for a in manifiesto["archivos"]:
        if a["nombre"] == "cadena.json":
            a["sha256"], a["tamano"] = huella(nueva), len(nueva)
    archivos["cadena.json"], archivos["manifiesto.json"] = nueva, json_canonico(manifiesto)
    v = ver(escribir_zip(archivos))
    assert (v.estado, v.motivo) == (ALTERADO, "cadena") and "no cuadra" in v.detalle


def test_el_destinatario_de_otra_empresa_avisa() -> None:
    v = ver(firmado(destinatario="Otra Constructora, C.A."), mi_empresa=("Mi Empresa", "abc"))
    assert v.estado == VERIFICADO
    assert any("Otra Constructora" in a for a in v.avisos)
    sin_aviso = ver(firmado(destinatario="Mi Empresa"), mi_empresa=("Mi Empresa", "abc"))
    assert not any("emitió para" in a for a in sin_aviso.avisos)


def test_la_verificacion_nunca_usa_la_clave_que_trae_el_paquete() -> None:
    """Un paquete bien firmado por una clave que NO está registrada no se verifica solo porque
    su manifiesto la nombre: sin registro, es no verificado."""
    v = verificar(firmado(), buscar_empresa=lambda huella: None, recibido_en=RECIBIDO)
    assert v.estado == NO_VERIFICADO


def test_zip_con_entradas_propias_del_formato_pero_con_un_nombre_extra_se_rechaza() -> None:
    archivos = leer_zip(firmado())
    archivos["anexos/otro.json"] = b"{}"
    v = ver(escribir_zip(archivos))
    assert v.estado == RECHAZADO and "no admitido" in v.detalle


def test_el_zip_que_miente_en_el_tamano_declarado_se_rechaza(tmp_path) -> None:
    import struct

    datos = bytearray(firmado())
    posicion = datos.find(b"PK\x01\x02")  # primer registro del directorio central
    datos[posicion + 24 : posicion + 28] = struct.pack("<I", 1)  # tamaño descomprimido: 1 B
    assert ver(bytes(datos)).estado == RECHAZADO


def test_zip_cifrado_se_rechaza() -> None:
    datos = bytearray(firmado())
    posicion = datos.find(b"PK")
    datos[posicion + 8] |= 0x01  # bit 0 del indicador general: entrada cifrada
    assert "cifrado" in ver(bytes(datos)).detalle


def test_compresion_que_no_es_almacenado_ni_deflate_se_rechaza() -> None:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_BZIP2) as z:
        z.writestr("manifiesto.json", b"{}")
    v = ver(salida.getvalue())
    assert v.estado == RECHAZADO and "método de compresión no admitido" in v.detalle
```
**`tests/unit/test_paquete_anterioridad.py`**
```python
"""Anterioridad entre paquetes, reenvío y banner de versión (S3 §6.5 y §8.3; 23c, 23h)."""

from __future__ import annotations

import json
from datetime import datetime

from paquete.verificar import evaluar_anterioridad
from tests.fixtures.paquetes import cadena_para

RECIBIDO_ANTES = datetime(2026, 11, 3, 8, 0)


def cadena_de(*codigos: str) -> dict:
    # el contenido de cada versión es `v<codigo>`: la misma versión da la misma huella en
    # cualquier paquete, como en la realidad (el eslabón es de la versión, no del paquete)
    datos, _ = cadena_para(f"v{codigos[-1]}".encode(), {}, codigos)
    return json.loads(datos)


def previo(cadena: dict, codigo: str, sha="aaa", paquete_id="p-0", anexos=None) -> dict:
    return {
        "huella_archivo": sha, "paquete_id": paquete_id, "codigo": codigo,
        "emitido": datetime(2026, 11, 3), "fecha": RECIBIDO_ANTES,
        "cadena": json.dumps([[e["codigo"], e["huella_eslabon"]] for e in cadena["eslabones"]]),
        "huellas_anexos": json.dumps(anexos or {}),
    }


def evaluar(cadena, previos, sha="nuevo", paquete_id="p-1", huellas=None):
    return evaluar_anterioridad({"paquete_id": paquete_id}, cadena, huellas or {}, sha, previos)


def test_el_primer_paquete_que_se_recibe_no_tiene_aviso_ni_ultima_recibida() -> None:
    r = evaluar(cadena_de("004", "005"), [])
    assert (r.avisos, r.ya_recibido, r.ultima_recibida) == ((), False, "")


def test_un_paquete_que_extiende_el_ultimo_recibido_no_avisa() -> None:
    anterior = cadena_de("004")
    r = evaluar(cadena_de("004", "005"), [previo(anterior, "004")])
    assert r.avisos == () and r.ultima_recibida == "versión 004 del 2026-11-03"


def test_un_paquete_que_reescribe_la_historia_lo_dice_con_la_version_y_la_fecha() -> None:
    recibida = cadena_de("003", "004")
    otra = cadena_de("003", "004b")  # la 004 tiene otra huella
    otra["eslabones"][1]["huella_eslabon"] = "f" * 64
    r = evaluar(otra, [previo(recibida, "004")])
    assert r.avisos == (
        "Este paquete reescribe la historia: la versión 004 que recibió el 2026-11-03 tenía "
        "otra huella.",)


def test_un_paquete_anterior_a_uno_ya_recibido_se_avisa() -> None:
    recibida = cadena_de("004", "005")
    r = evaluar(cadena_de("004"), [previo(recibida, "005")])
    assert r.avisos == (
        "Este paquete es anterior a uno que ya recibió (versión 005 del 2026-11-03).",
    )


def test_el_mismo_paquete_otra_vez_se_reconoce_por_el_sha_256_o_por_el_paquete_id() -> None:
    cadena = cadena_de("004", "005")
    visto = previo(cadena, "005", sha="igual", paquete_id="p-9")
    por_sha = evaluar(cadena, [visto], sha="igual", paquete_id="otro")
    por_id = evaluar(cadena, [visto], sha="distinto", paquete_id="p-9")
    for r in (por_sha, por_id):
        assert r.ya_recibido and r.avisos == ("Ya recibió este mismo paquete el 2026-11-03.",)


def test_una_entrada_de_un_anexo_que_ya_no_viene_se_avisa() -> None:
    cadena = cadena_de("004", "005")
    visto = previo(cadena_de("004"), "004", anexos={"anexos/control.json": ["h1", "h2", "h3"]})
    r = evaluar(cadena, [visto], huellas={"anexos/control.json": ["h1", "h3"]})
    assert r.avisos == (
        "1 entrada(s) de anexos/control.json que recibió el 2026-11-03 ya no vienen.",
    )


def test_solo_cuenta_el_ultimo_paquete_recibido() -> None:
    viejo = previo(cadena_de("001"), "001", sha="v", paquete_id="p-v")
    ultimo = previo(cadena_de("001", "002", "003"), "003", sha="u", paquete_id="p-u")
    r = evaluar(cadena_de("001", "002", "003", "004"), [viejo, ultimo])
    assert r.avisos == () and r.ultima_recibida.startswith("versión 003")
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_paquete_verificar.py tests/unit/test_paquete_anterioridad.py
-v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'paquete.verificar'`.
```bash
git add tests/fixtures/paquetes.py tests/unit/test_paquete_verificar.py \
  tests/unit/test_paquete_anterioridad.py
git commit -m "test(paquete): verificar los cuatro estados y la anterioridad, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`paquete/exportar.py`**
```python
"""Construir el `.silice` (spec S3 §8.1 y §8.2; maestro §4.5).

`construir_paquete` recibe los bytes ya generados de cada archivo (el documento canónico, el
informe, la cadena y los anexos) y arma el ZIP: el manifiesto lleva el SHA-256 y el tamaño de cada
archivo, la huella de todos los anexos y la última huella de la cadena; la firma cubre el
manifiesto con el prefijo de dominio de paquete. **No viaja el Excel** (DA-S3-10): el revisor lo
regenera. El ZIP es reproducible (fechas fijas, orden fijo): con el mismo `paquete_id` y la misma
fecha, los mismos bytes.
"""

from __future__ import annotations

import hashlib
import io
import uuid
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from core.budget.canonico import json_canonico
from paquete.formato import (
    ANEXOS_ADMITIDOS,
    FORMATO_PAQUETE,
    NOMBRE_FIRMA,
    NOMBRE_MANIFIESTO,
    VERSION_FORMATO,
    PaqueteRechazado,
    comprobar_salida,
    huella_de_anexos,
)
from seguridad import firma

__all__ = ["Emisor", "construir_paquete"]

FECHA_FIJA_ZIP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class Emisor:
    """Quién emite: la empresa y la huella COMPLETA de su clave (o `None` sin firma) y el
    usuario que entregó. No hay no repudio individual: es lo que declara el emisor (SEG-6)."""

    empresa: str | None
    huella_clave: str | None
    usuario: str


def _sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def construir_paquete(
    *,
    presupuesto: bytes,
    informe: bytes,
    cadena: bytes,
    anexos: Mapping[str, bytes],
    emisor: Emisor,
    destinatario: str | None,
    proyecto: str,
    codigo: str,
    moneda: str,
    total: str,
    ultima_huella: str,
    ahora: datetime,
    version_silice: str,
    privada: bytes | None = None,
    paquete_id: str | None = None,
) -> bytes:
    """El archivo `.silice`. Con `privada`, lo firma; sin ella, queda «sin firma»."""
    desconocidos = sorted(set(anexos) - set(ANEXOS_ADMITIDOS))
    if desconocidos:
        raise PaqueteRechazado(f"anexo no admitido por el formato v1: {desconocidos[0]!r}")
    if privada is not None and not emisor.huella_clave:
        raise ValueError("para firmar hace falta la huella de la clave del emisor")
    archivos = {"presupuesto.json": presupuesto, "informe.json": informe, "cadena.json": cadena,
                **anexos}
    manifiesto = json_canonico(
        {
            "formato": FORMATO_PAQUETE,
            "version_formato": VERSION_FORMATO,
            "version_silice": version_silice,
            "paquete_id": paquete_id or str(uuid.uuid4()),
            "emitido": ahora.isoformat(timespec="seconds"),
            "empresa": emisor.empresa,
            "huella_clave": emisor.huella_clave,
            "usuario_emisor": emisor.usuario,
            "destinatario": destinatario or None,
            "proyecto": proyecto,
            "codigo": codigo,
            "moneda": moneda,
            "total": total,
            "archivos": [
                {"nombre": n, "sha256": _sha(archivos[n]), "tamano": len(archivos[n])}
                for n in sorted(archivos)
            ],
            "huella_anexos": huella_de_anexos(anexos),
            "ultima_huella_eslabon": ultima_huella,
            "algoritmo": "Ed25519",
        }
    )
    contenido: dict[str, bytes] = {NOMBRE_MANIFIESTO: manifiesto}
    if privada is not None:
        contenido[NOMBRE_FIRMA] = firma.firmar(privada, firma.DOMINIO_PAQUETE, manifiesto)
    contenido.update({n: archivos[n] for n in sorted(archivos)})
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w", zipfile.ZIP_DEFLATED) as zip_:
        for nombre, octetos in contenido.items():
            info = zipfile.ZipInfo(nombre, date_time=FECHA_FIJA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zip_.writestr(info, octetos)
    datos = flujo.getvalue()
    comprobar_salida(contenido, len(datos))
    return datos
```
**`paquete/verificar.py`**
```python
"""Verificar un `.silice` ajeno (spec S3 §8.3, §6.5 y §13.3; maestro §4.5).

Pasos: abrir con límites -> formato -> integridad (huellas del manifiesto y `huella_anexos`) ->
autenticidad (la firma, con **la clave registrada** y nunca la que trae el paquete, y con el
prefijo de dominio) -> cadena -> anterioridad y destinatario. Cuatro estados:

* **verificado**: todo cuadra y la firma es de una empresa registrada y activa (o retirada, solo si
  el archivo se recibió antes de registrar el retiro);
* **no verificado**: sin firma, empresa no registrada, clave revocada o retirada y recibido
  después. Se audita igual; sin firma las huellas solo prueban que no se dañó por accidente;
* **alterado**: una huella, la firma o la cadena no cuadran. Se audita igual para mostrar qué
  contiene;
* **rechazado**: ZIP dañado o inseguro, fuera de límites o de un formato que no se conoce.

`verificar` no toca la base: recibe una función que busca la empresa por la huella completa de su
clave y la fecha en que se recibió el archivo.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.budget.cadena import (
    GENESIS,
    huella_de_anexos,
    huella_de_filas_de_cambios,
    huella_del_eslabon,
)
from paquete.formato import (
    ADMITIDOS,
    FORMATO_PAQUETE,
    NOMBRE_FIRMA,
    NOMBRE_MANIFIESTO,
    OBLIGATORIOS,
    VERSION_FORMATO,
    JsonRechazado,
    PaqueteRechazado,
    abrir_zip,
    leer_json,
)
from seguridad import firma

__all__ = [
    "Anterioridad",
    "EmpresaConocida",
    "Verificacion",
    "armar_cadena_json",
    "banner",
    "evaluar_anterioridad",
    "verificar",
]

VERIFICADO, NO_VERIFICADO, ALTERADO, RECHAZADO = (
    "verificado", "no_verificado", "alterado", "rechazado",
)
FORMATO_CADENA = "silice-cadena"
ADMITE_ESPACIO = "anexos/espacio.json"


@dataclass(frozen=True, slots=True)
class EmpresaConocida:
    """Lo que la instalación sabe de una empresa registrada (`empresa_registrada`)."""

    empresa: str
    publica: bytes
    estado: str  # activa | retirada | revocada
    fecha_estado: datetime | None = None


BuscarEmpresa = Callable[[str], "EmpresaConocida | None"]


@dataclass(frozen=True, slots=True)
class Verificacion:
    estado: str
    motivo: str  # clave corta: ver MOTIVOS
    detalle: str  # qué archivo cambió, qué empresa dice ser...
    sha256: str
    archivos: Mapping[str, bytes] = field(default_factory=dict)
    manifiesto: Mapping[str, Any] | None = None
    cadena: Mapping[str, Any] | None = None
    empresa_declarada: str | None = None
    empresa_verificada: str | None = None
    retirada: bool = False
    avisos: tuple[str, ...] = ()

    @property
    def legible(self) -> bool:
        """Se puede reauditar: todo menos «rechazado» (en «alterado» se audita para mostrar)."""
        return self.estado != RECHAZADO and bool(self.archivos)


def _sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def _rechazo(sha: str, detalle: str) -> Verificacion:
    return Verificacion(RECHAZADO, "rechazado", detalle, sha)


# --- la cadena del paquete -------------------------------------------------------------------


def armar_cadena_json(
    eslabones: Sequence[Mapping[str, Any]], cambios: Mapping[str, Sequence[Sequence[str]]]
) -> dict[str, Any]:
    """El objeto de `cadena.json`: los eslabones hasta la versión entregada y, por código de
    versión, las filas de sus `RegistroCambio` (las mismas que entran a `huella_cambios`)."""
    return {
        "formato": FORMATO_CADENA, "version_formato": 1, "eslabones": list(eslabones),
        "cambios": {codigo: [list(f) for f in filas] for codigo, filas in cambios.items()},
    }


def _comprobar_cadena(cadena: Mapping[str, Any], manifiesto: Mapping[str, Any],
                      archivos: Mapping[str, bytes]) -> str | None:
    """Motivo si la cadena no cuadra; `None` si sí. Verifica los enlaces y que cada eslabón
    sea consistente consigo mismo y con sus cambios; del contenido de las versiones anteriores
    solo hay huellas (DA-S3-4), así que solo el último eslabón se ata al `presupuesto.json`."""
    eslabones = cadena.get("eslabones")
    if cadena.get("formato") != FORMATO_CADENA or not isinstance(eslabones, list) or not eslabones:
        return "cadena.json no tiene la forma esperada"
    anterior = GENESIS
    for e in eslabones:
        try:
            esperado = huella_del_eslabon(
                anterior=e["anterior"], codigo=e["codigo"], contenido=e["huella_contenido"],
                cambios=e["huella_cambios"], anexos=e["huella_anexos"], usuario=e["usuario"],
                fecha_hora=datetime.fromisoformat(e["fecha_hora"]), tipo=e["tipo"],
                version_formato=e["version_formato"],
            )
            cambios = huella_de_filas_de_cambios(cadena.get("cambios", {}).get(e["codigo"], []))
        except (KeyError, TypeError, ValueError):
            return "un eslabón de cadena.json está incompleto"
        if e["anterior"] != anterior or esperado != e["huella_eslabon"]:
            return f"el eslabón de la versión {e['codigo']} no cuadra"
        if cambios != e["huella_cambios"]:
            return f"los cambios de la versión {e['codigo']} no coinciden con su huella"
        anterior = e["huella_eslabon"]
    ultimo = eslabones[-1]
    if ultimo["huella_eslabon"] != manifiesto.get("ultima_huella_eslabon"):
        return "el último eslabón no es el que firma el manifiesto"
    if ultimo["codigo"] != manifiesto.get("codigo"):
        return "el último eslabón no es de la versión que declara el manifiesto"
    if ultimo["huella_contenido"] != _sha(archivos["presupuesto.json"]):
        return "el contenido de presupuesto.json no es el que selló el último eslabón"
    espacio = {n: archivos[n] for n in (ADMITE_ESPACIO,) if n in archivos}
    if ultimo["huella_anexos"] != huella_de_anexos(espacio):
        return "el anexo de espacio no es el que selló el último eslabón"
    return None


# --- verificar -------------------------------------------------------------------------------


def verificar(
    datos: bytes, *, buscar_empresa: BuscarEmpresa, recibido_en: datetime,
    mi_empresa: tuple[str | None, str | None] = (None, None),
) -> Verificacion:
    """El estado de `datos`. `mi_empresa` = (nombre, huella de clave) de la instalación que
    recibe, para avisar si el paquete se emitió para otra empresa (23g)."""
    sha = _sha(datos)
    try:
        archivos = abrir_zip(datos)
    except PaqueteRechazado as error:
        return _rechazo(sha, str(error))
    if NOMBRE_MANIFIESTO not in archivos:
        return _rechazo(sha, "El paquete no trae manifiesto.json: no se puede leer.")
    try:
        manifiesto = leer_json(archivos[NOMBRE_MANIFIESTO])
    except JsonRechazado as error:
        return _rechazo(sha, f"El manifiesto no es un JSON válido: {error}.")
    if not isinstance(manifiesto, dict) or manifiesto.get("formato") != FORMATO_PAQUETE:
        return _rechazo(sha, "El archivo no es un paquete de Silice (formato desconocido).")
    if manifiesto.get("version_formato") != VERSION_FORMATO:
        return _rechazo(
            sha, f"El paquete es de la versión de formato {manifiesto.get('version_formato')!r} "
            "y esta instalación solo lee la 1. Pida al emisor un paquete compatible.",
        )
    declarada = manifiesto.get("empresa")
    huella_clave = manifiesto.get("huella_clave")

    def resultado(estado: str, motivo: str, detalle: str = "", **mas) -> Verificacion:
        return Verificacion(
            estado, motivo, detalle, sha, archivos, manifiesto, mas.pop("cadena", None),
            declarada, mas.pop("verificada", None), **mas,
        )

    alterado = _integridad(manifiesto, archivos)
    if alterado is not None:
        return resultado(ALTERADO, "integridad", alterado)
    firmado = archivos.get(NOMBRE_FIRMA)
    manifiesto_bytes = archivos[NOMBRE_MANIFIESTO]
    estado, motivo, detalle, verificada, retirada = NO_VERIFICADO, "sin_firma", "", None, False
    if firmado is not None:
        if len(firmado) != 64 or not huella_clave:
            return resultado(ALTERADO, "firma", "firma.ed25519 no es una firma válida")
        conocida = buscar_empresa(huella_clave)
        if conocida is None:
            estado, motivo = NO_VERIFICADO, "empresa_no_registrada"
        elif not firma.verificar(
            conocida.publica, firma.DOMINIO_PAQUETE, manifiesto_bytes, firmado
        ):
            return resultado(ALTERADO, "firma", "la firma no es válida con la clave registrada")
        elif conocida.estado == "revocada":
            estado, motivo = NO_VERIFICADO, "revocada"
        elif conocida.estado == "retirada":
            antes = conocida.fecha_estado is not None and recibido_en < conocida.fecha_estado
            estado, motivo = (
                (VERIFICADO, "retirada") if antes else (NO_VERIFICADO, "retirada_tarde")
            )
            verificada, retirada = (conocida.empresa if antes else None), antes
        else:
            estado, motivo, verificada = VERIFICADO, "firma_valida", conocida.empresa
    try:
        cadena = leer_json(archivos["cadena.json"])
    except JsonRechazado as error:
        return resultado(ALTERADO, "cadena", f"cadena.json no es un JSON válido: {error}")
    fallo = _comprobar_cadena(cadena, manifiesto, archivos)
    if fallo is not None:
        return resultado(ALTERADO, "cadena", fallo, cadena=cadena)
    avisos = []
    nombre_mio, huella_mia = mi_empresa
    destinatario = manifiesto.get("destinatario")
    if destinatario and destinatario not in {nombre_mio, huella_mia}:
        avisos.append(f"Este paquete se emitió para {destinatario}.")
    if retirada:
        avisos.append("La clave del emisor se retiró después de que usted recibió este paquete.")
    return resultado(estado, motivo, detalle, cadena=cadena, verificada=verificada,
                     retirada=retirada, avisos=tuple(avisos))


def _integridad(manifiesto: Mapping[str, Any], archivos: Mapping[str, bytes]) -> str | None:
    """Texto de lo que no cuadra, o `None`. Falta, sobra o cambió algún archivo."""
    try:
        listados = {a["nombre"]: a for a in manifiesto["archivos"]}
    except (KeyError, TypeError):
        return "el manifiesto no lista sus archivos"
    for nombre in OBLIGATORIOS:
        if nombre != NOMBRE_MANIFIESTO and nombre not in listados:
            return f"el manifiesto no lista {nombre}"
    for nombre, entrada in listados.items():
        if nombre not in ADMITIDOS or nombre in (NOMBRE_MANIFIESTO, NOMBRE_FIRMA):
            return f"el manifiesto lista un archivo que no es del formato: {nombre!r}"
        if nombre not in archivos:
            return f"falta {nombre}, que el manifiesto lista"
        if len(archivos[nombre]) != entrada.get("tamano") or _sha(archivos[nombre]) != entrada.get(
            "sha256"
        ):
            return f"{nombre} cambió después de firmarse"
    for nombre in archivos:
        if nombre not in listados and nombre not in (NOMBRE_MANIFIESTO, NOMBRE_FIRMA):
            return f"{nombre} está en el paquete y el manifiesto no lo lista"
    anexos = {n: b for n, b in archivos.items() if n.startswith("anexos/")}
    if huella_de_anexos(anexos) != manifiesto.get("huella_anexos"):
        return "los anexos no coinciden con la huella de anexos del manifiesto"
    return None


# --- anterioridad y banner -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Anterioridad:
    avisos: tuple[str, ...]
    ya_recibido: bool
    ultima_recibida: str  # «versión 004 del 2026-11-03» o «» si es la primera


def evaluar_anterioridad(
    manifiesto: Mapping[str, Any], cadena: Mapping[str, Any],
    huellas_de_anexos: Mapping[str, Sequence[str]], sha256: str, previos: Sequence[Mapping],
) -> Anterioridad:
    """§6.5. `previos`: lo ya recibido del mismo proyecto y emisor, del más viejo al más nuevo,
    con `huella_archivo`, `paquete_id`, `codigo`, `emitido`, `cadena` (JSON de `[[codigo,
    huella]...]`) y `huellas_anexos` (JSON `{anexo: [huella...]}`). Defensa PARCIAL: un revisor que
    nunca recibió un paquete más nuevo, otro revisor o una base restaurada no la tienen."""
    avisos: list[str] = []
    for p in previos:
        if p["huella_archivo"] == sha256 or p["paquete_id"] == manifiesto.get("paquete_id"):
            return Anterioridad((f"Ya recibió este mismo paquete el {_dia(p['fecha'])}.",), True,
                                _ultima(previos))
    if not previos:
        return Anterioridad((), False, "")
    ultimo = previos[-1]
    hay = [[e["codigo"], e["huella_eslabon"]] for e in cadena["eslabones"]]
    vista = json.loads(ultimo["cadena"])
    comun = min(len(hay), len(vista))
    if hay[:comun] != vista[:comun]:
        donde = next(i for i in range(comun) if hay[i] != vista[i])
        avisos.append(
            f"Este paquete reescribe la historia: la versión {vista[donde][0]} que recibió el "
            f"{_dia(ultimo['fecha'])} tenía otra huella."
        )
    elif len(hay) <= len(vista):
        avisos.append(
            f"Este paquete es anterior a uno que ya recibió (versión {ultimo['codigo']} del "
            f"{_dia(ultimo['emitido'])})."
        )
    antes = json.loads(ultimo["huellas_anexos"])
    for anexo, huellas in sorted(antes.items()):
        faltan = set(huellas) - set(huellas_de_anexos.get(anexo, ()))
        if faltan:
            avisos.append(
                f"{len(faltan)} entrada(s) de {anexo} que recibió el {_dia(ultimo['fecha'])} "
                "ya no vienen."
            )
    return Anterioridad(tuple(avisos), False, _ultima(previos))


def _dia(valor: Any) -> str:
    return valor.date().isoformat() if isinstance(valor, datetime) else str(valor)[:10]


def _ultima(previos: Sequence[Mapping]) -> str:
    if not previos:
        return ""
    ultimo = previos[-1]
    return f"versión {ultimo['codigo']} del {_dia(ultimo['emitido'])}"


def banner(
    v: Verificacion, nombre_seguro: Callable[[str], str] = lambda texto: texto
) -> tuple[str, str]:
    """`(color, texto)` del banner de estado (S3 §8.3). `nombre_seguro` escapa lo que viene del
    paquete: la interfaz le pasa `texto_seguro`."""
    emitido = str((v.manifiesto or {}).get("emitido", ""))[:10]
    quien = nombre_seguro(v.empresa_declarada or "una empresa que no se indica")
    if v.estado == VERIFICADO:
        extra = " (clave retirada después)" if v.retirada else ""
        return "verde", (
            f"Verificado: emitido por {nombre_seguro(v.empresa_verificada or '')} el {emitido}. "
            f"No se alteró desde que se firmó.{extra}"
        )
    if v.estado == NO_VERIFICADO:
        razones = {
            "sin_firma": "El paquete no está firmado: las huellas solo prueban que no se dañó "
                         "por accidente, no que nadie lo cambió.",
            "empresa_no_registrada": "Su clave no está registrada en esta instalación.",
            "revocada": "Su clave fue revocada.",
            "retirada_tarde": "Su clave se retiró antes de que usted recibiera el paquete.",
        }
        return "ambar", (
            f"No verificado: dice venir de {quien}, pero no se pudo comprobar. "
            f"{razones.get(v.motivo, '')} Se audita igual."
        )
    if v.estado == ALTERADO:
        return "rojo", (
            f"Alterado: {nombre_seguro(v.detalle)}. No confíe en este paquete; pida uno nuevo."
        )
    return "rojo", f"Rechazado: {nombre_seguro(v.detalle)}"
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_paquete_verificar.py tests/unit/test_paquete_anterioridad.py
tests/unit/test_paquete_formato.py tests/unit/test_firma.py -v -W error` → verde.
- [ ] **Paso 5: Commit**
```bash
git add paquete/exportar.py paquete/verificar.py
git commit -m "feat(paquete): exportar el .silice firmado y verificarlo en cuatro estados" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 16: Entregar el paquete (UC-22): `ui/entrega.py` y la pantalla

**Rama:** `inc/080-s3-3-paquete`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/entrega.py`, `ui/paginas/entregar.py`
- Modificar: `ui/app.py` (importación y entrada de «Entregar paquete» en la sección Trabajo),
  `tests/unit/test_ui_app.py`, `tests/unit/test_ui_importable.py`,
  `tests/unit/test_arquitectura_s5.py:69-85`
- Prueba: `tests/integration/test_entrega.py`, `tests/unit/test_ui_entregar.py`

**Interfaces:**
- Consume: `paquete.exportar.{Emisor, construir_paquete}`, `paquete.anexos.*`,
  `paquete.formato.EXTENSION`, `paquete.verificar.armar_cadena_json` (tareas 14 y 15),
  `seguridad.{empresas, eventos}` (tareas 5 y 13), `core.budget.{cadena, canonico}`,
  `adapters.espacio.{cargar_espacio}` y `adapters.espacio.serie.espacio_a_objeto` (tarea 11),
  `ui.sesion.{exigir, exigir_local}` (tarea 6).
- Produce:
  - `ui.entrega`: `class EntregaRechazada(ValueError)`
  - `ui.entrega`: `def anexos_de_cadena(session: Session, version: models.Presupuesto) ->
      Mapping[str, bytes]`
  - `ui.entrega`: `def anexos_del_paquete(session: Session, version: models.Presupuesto, ia:
      bytes | None=None) -> dict[str, bytes]`
  - `ui.entrega`: `def con_anexos_de_cadena(session: Session) -> Session`
  - `ui.entrega`: `class EstadoDeLaCadena`
  - `ui.entrega`: `def estado_de_la_cadena(session: Session, proyecto_nombre: str) ->
      EstadoDeLaCadena | None`
  - `ui.entrega`: `class Resumen`
  - `ui.entrega`: `def resumen_de_entrega(session: Session, instalacion: Session, version:
      models.Presupuesto) -> Resumen`
  - `ui.entrega`: `class Entrega`
  - `ui.entrega`: `def nombre_de_archivo(proyecto: str, codigo: str) -> str`
  - `ui.entrega`: `def entregar(session: Session, instalacion: Session, version:
      models.Presupuesto, *, usuario: str, ahora: datetime, version_silice: str, destinatario:
      str | None=None, contrasena_clave: str | None=None, ia: bytes | None=None) -> Entrega`
  - `ui.paginas.entregar`: `def version_de_silice() -> str`
  - `ui.paginas.entregar`: `def render() -> None`

**Flujo** (UC-22). Quien arma abre la pantalla, elige el proyecto y la versión; el sistema verifica
la cadena (22c: si está rota, se rechaza y se dice en qué versión) y muestra el resumen (total,
hallazgos por severidad, cadena, empresa emisora y anexos que viajarán); el usuario elige, si
quiere, el destinatario y escribe la contraseña de la clave de firma; el sistema genera todo en
memoria y registra en `evento_acceso` el SHA-256 del archivo, el `paquete_id`, la versión y el
usuario. Sin clave de empresa se ofrece exportar **sin firma**, declarado (22a). La firma solo se
pide desde el propio equipo (22e: `exigir_local`). Un paquete que excedería los límites del formato
no se genera (22f). La base del caso **no cambia**. `anexos_de_cadena` es el proveedor que
`guardar_presupuesto(..., anexos_de=...)` y `verificar_cadena` usan para que la cadena cubra el
espacio de la versión.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/integration/test_entrega.py`**
```python
"""Entregar el paquete: de la base del emisor a un `.silice` que otra instalación verifica
(UC-22, RF-85; spec S3 §8.2 y §13.2). Dos bases temporales y la firma de verdad."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from adapters.espacio import crear_esquema_espacio, guardar_espacio
from core import models
from core.catalog import abrir_sesion
from paquete.formato import PaqueteRechazado, abrir_zip
from paquete.verificar import NO_VERIFICADO, VERIFICADO, EmpresaConocida, verificar
from seguridad import empresas
from seguridad.modelo import EventoAcceso
from tests.fixtures.canonico_minimo import USUARIO, sembrar_minimo
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.instalacion import AHORA, instalacion
from ui import entrega

CLAVE = "frase de firma larga y propia"


@pytest.fixture
def emisor(motor, tmp_path: Path):
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "emisor") as bd:
        empresas.guardar_empresa_propia(
            bd, "Contratista Demo, C.A.", "J-00000000-0", "", "ana", AHORA
        )
        crear_esquema_espacio(caso.connection())
        proyecto, version, lista = sembrar_minimo(caso, anexos_de=entrega.anexos_de_cadena)
        guardar_espacio(caso, version.id, espacio_of001())
        caso.commit()
        yield caso, bd, proyecto, version, lista


def _conocida(bd) -> dict:
    clave = empresas.clave_activa(bd)
    return {clave.huella: EmpresaConocida("Contratista Demo, C.A.", clave.publica, "activa")}


def _entregar(caso, bd, version, **mas):
    return entrega.entregar(
        caso, bd, version, usuario=USUARIO, ahora=datetime(2026, 11, 10, 9, 30),
        version_silice="0.8.0", **mas,
    )


def test_el_paquete_firmado_se_verifica_en_otra_instalacion(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE, destinatario="Cliente S.A.")
    assert e.firmado and e.nombre == "MIN-001-001.silice"
    v = verificar(e.datos, buscar_empresa=_conocida(bd).get, recibido_en=datetime(2026, 11, 11),
                  mi_empresa=("Cliente S.A.", None))
    assert (v.estado, v.empresa_verificada) == (VERIFICADO, "Contratista Demo, C.A.")
    assert v.avisos == ()
    manifiesto = v.manifiesto
    assert manifiesto["proyecto"] == "MIN-001" and manifiesto["codigo"] == "001"
    assert manifiesto["usuario_emisor"] == USUARIO and manifiesto["destinatario"] == "Cliente S.A."
    assert manifiesto["total"] == "836.79750000" and manifiesto["paquete_id"] == e.paquete_id
    assert "anexos/espacio.json" in v.archivos  # el espacio cubierto por la cadena
    assert not any(n.endswith(".xlsx") for n in v.archivos)  # el Excel no viaja (DA-S3-10)


def test_el_presupuesto_del_paquete_es_el_documento_canonico_de_la_version(emisor) -> None:
    from core.budget import canonico

    caso, bd, _, version, _ = emisor
    e = _entregar(caso, bd, version)
    assert abrir_zip(e.datos)["presupuesto.json"] == canonico.documento(caso, version)


def test_sin_clave_se_exporta_sin_firma_y_se_declara(emisor) -> None:
    caso, bd, _, version, _ = emisor
    e = _entregar(caso, bd, version)
    assert not e.firmado
    v = verificar(e.datos, buscar_empresa=lambda h: None, recibido_en=datetime(2026, 11, 11))
    assert (v.estado, v.motivo) == (NO_VERIFICADO, "sin_firma")
    assert v.manifiesto["huella_clave"] is None and "firma.ed25519" not in v.archivos


def test_contrasena_de_clave_erronea_no_genera_nada_y_no_deja_registro(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    antes = bd.scalar(select(func.count()).select_from(EventoAcceso))
    with pytest.raises(empresas.ContrasenaDeClaveIncorrecta):
        _entregar(caso, bd, version, contrasena_clave=CLAVE + "x")
    assert bd.scalar(select(func.count()).select_from(EventoAcceso)) == antes


def test_el_sha256_del_archivo_descargado_queda_en_el_registro_de_accesos(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    e = _entregar(caso, bd, version, contrasena_clave=CLAVE)
    eventos = {x.tipo: x.detalle for x in bd.scalars(select(EventoAcceso))}
    assert e.sha256 in eventos["paquete exportado"] and e.paquete_id in eventos["firma"]
    assert f"version {version.codigo}" in eventos["paquete exportado"]


def test_la_base_del_caso_no_cambia_al_entregar(emisor) -> None:
    caso, bd, *_ = emisor
    version = caso.scalars(select(models.Presupuesto)).one()
    tablas = [models.Presupuesto, models.RegistroCambio, models.Hallazgo, models.ComposicionVersion]
    antes = [caso.scalar(select(func.count()).select_from(t)) for t in tablas]
    _entregar(caso, bd, version)
    assert [caso.scalar(select(func.count()).select_from(t)) for t in tablas] == antes
    assert not caso.in_transaction() or not caso.dirty


def test_una_cadena_rota_impide_entregar_y_dice_en_que_version(emisor) -> None:
    caso, bd, proyecto, version, lista = emisor
    caso.execute(models.PartidaPresupuestada.__table__.update().values(cantidad=models.Decimal(5))
                 if False else
                 __import__("sqlalchemy").text("UPDATE partida_presupuestada SET cantidad = '21'"))
    caso.commit()
    caso.expire_all()
    with pytest.raises(entrega.EntregaRechazada, match="Cadena rota en la versión 001"):
        _entregar(caso, bd, version)


def test_una_version_sin_sellar_no_se_entrega(emisor) -> None:
    caso, bd, proyecto, version, lista = emisor
    caso.execute(__import__("sqlalchemy").text("DELETE FROM eslabon_version"))
    caso.commit()
    caso.expire_all()
    with pytest.raises(entrega.EntregaRechazada,
         match="no tiene eslabón|no está sellada|Cadena rota"):
        _entregar(caso, bd, version)


def test_el_resumen_dice_total_cadena_empresa_y_anexos(emisor) -> None:
    caso, bd, _, version, _ = emisor
    empresas.generar_clave(bd, CLAVE, "ana", AHORA)
    r = entrega.resumen_de_entrega(caso, bd, version)
    assert (r.codigo, r.cadena_integra, r.empresa, r.firma_disponible) == (
        "001", True, "Contratista Demo, C.A.", True)
    assert str(r.total) == "836.79750000" and "anexos/espacio.json" in r.anexos
    assert r.mensaje_de_cadena == "Cadena íntegra: 1 versiones"


def test_los_anexos_de_s1_viajan_con_huella_por_entrada(emisor) -> None:
    caso, bd, proyecto, version, lista = emisor
    caso.add(models.MonedaProyecto(proyecto_id=proyecto.id, moneda="USD",
                                   desde=datetime(2026, 11, 5), version_id=None,
                                   responsable="ana", fuente="al crear"))
    caso.commit()
    e = _entregar(caso, bd, version)
    anexo = json.loads(abrir_zip(e.datos)["anexos/reajuste.json"])
    [entrada] = [x for x in anexo["entradas"] if x["tabla"] == "moneda_proyecto"]
    assert entrada["fila"]["moneda"] == "USD" and len(entrada["huella"]) == 64
    assert "anexos/control.json" not in abrir_zip(e.datos)  # sin tablas de S2 en esta base


def test_un_paquete_de_mas_de_20_mib_no_se_genera(emisor, monkeypatch) -> None:
    from paquete import formato

    caso, bd, _, version, _ = emisor
    monkeypatch.setattr(formato, "LIMITE_ARCHIVO", 500)
    with pytest.raises(PaqueteRechazado, match="no se genera un paquete que el revisor"):
        _entregar(caso, bd, version)


def test_el_nombre_de_archivo_no_lleva_caracteres_peligrosos() -> None:
    nombre = entrega.nombre_de_archivo("OF-001: oficina/../x?", "003")
    assert nombre == "OF-001--oficina----x-003.silice"
```
**`tests/unit/test_ui_entregar.py`**
```python
"""Entregar paquete (UC-22, RF-85; spec S3 §8.2): rol, equipo local, firma y cadena rota."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest

from adapters.espacio import crear_esquema_espacio
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from paquete.modelo import crear_esquema_paquete
from seguridad import empresas
from seguridad.modelo import EventoAcceso
from tests.fixtures.canonico_minimo import sembrar_minimo
from tests.fixtures.instalacion import AHORA
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import entrega
from ui import sesion as ui_sesion
from ui.sesion import MENSAJE_SIN_PERMISO, MENSAJE_SOLO_LOCAL

CLAVE = "frase de firma larga y propia"


def _pagina() -> None:
    from ui.paginas import entregar

    entregar.render()


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


@pytest.fixture
def caso_db(tmp_path: Path, monkeypatch) -> Path:
    ruta = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        crear_esquema_espacio(sesion.connection())
        crear_esquema_paquete(sesion.connection())
        sembrar_minimo(sesion, anexos_de=entrega.anexos_de_cadena)
        sesion.commit()
    motor.dispose()
    monkeypatch.setenv("SILICE_CASO", str(ruta))
    return ruta


def _abrir(monkeypatch, tmp_path: Path, rol: str = "arma", ip: str = "127.0.0.1") -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, rol, ip=ip)
    return con_ficha(AppTest.from_function(_pagina, default_timeout=60), ficha).run()


def _con_empresa_y_clave(tmp_path: Path) -> None:
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, "Contratista Demo, C.A.", "J-0", "", "admin", AHORA)
        empresas.generar_clave(bd, CLAVE, "admin", AHORA)


def _generar(at: AppTest, contrasena: str = "") -> AppTest:
    if contrasena:
        at.text_input(key="entregar_clave").input(contrasena)
    at.button(key="entregar_enviar").click()
    return at.run()


def test_el_resumen_dice_el_total_la_cadena_y_que_saldra_sin_firma(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    assert not at.exception
    valores = {m.label: m.value for m in at.metric}
    assert valores["Cadena"] == "íntegra" and valores["Total"].startswith("836")
    assert any("Todavía no hay empresa" in w.value for w in at.warning)


def test_con_empresa_sin_clave_avisa_que_saldra_sin_firma_y_la_entrega_sale_sin_firma(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, "Contratista Demo, C.A.", "J-0", "", "admin", AHORA)
    at = at.run()
    assert any("SIN FIRMA" in w.value for w in at.warning)
    at = _generar(at)
    assert any("(sin firma)" in s.value for s in at.success)
    assert at.get("download_button")


def test_con_clave_en_el_equipo_el_paquete_sale_firmado_y_queda_en_el_registro(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    _con_empresa_y_clave(tmp_path)
    at = _generar(at.run(), CLAVE)
    assert not at.exception and any("firmado" in s.value for s in at.success)
    with ui_sesion.instalacion() as bd:
        tipos = {e.tipo for e in bd.query(EventoAcceso)}
    assert {"firma", "paquete exportado"} <= tipos


def test_contrasena_de_clave_erronea_da_mensaje_sin_traza_y_sin_descarga(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path)
    _con_empresa_y_clave(tmp_path)
    at = _generar(at.run(), CLAVE + "x")
    assert [e.value for e in at.error] == ["La contraseña de la clave no es correcta."]
    assert not at.get("download_button") and not at.exception


def test_la_firma_no_se_pide_desde_otra_maquina(monkeypatch, tmp_path, caso_db) -> None:
    at = _abrir(monkeypatch, tmp_path, ip="192.168.1.20")
    _con_empresa_y_clave(tmp_path)
    at = _generar(at.run(), CLAVE)
    assert MENSAJE_SOLO_LOCAL in [e.value for e in at.error] and not at.get("download_button")


def test_una_cadena_rota_se_muestra_y_no_deja_entregar(monkeypatch, tmp_path, caso_db) -> None:
    motor = crear_motor(f"sqlite:///{caso_db.as_posix()}")
    with motor.begin() as conexion:
        conexion.execute(text("UPDATE partida_presupuestada SET cantidad = '31'"))
    motor.dispose()
    at = _abrir(monkeypatch, tmp_path)
    assert {m.label: m.value for m in at.metric}["Cadena"] == "ROTA" and at.error
    assert at.button(key="entregar_enviar").disabled


@pytest.mark.parametrize("rol", ["revisa", "administrador"])
def test_otros_roles_no_entregan_aunque_lleguen_por_la_url(monkeypatch, tmp_path, caso_db, rol):
    at = _abrir(monkeypatch, tmp_path, rol)
    assert [e.value for e in at.error] == [MENSAJE_SIN_PERMISO] and not at.metric
```
  La pantalla se registra en el marco; las pruebas del marco cuentan una página más:
```diff
--- a/ui/app.py
+++ b/ui/app.py
@@ -74,4 +74,5 @@
     componer,
     elaborar,
+    entregar,
     escenarios,
     historico,
@@ -129,4 +130,6 @@
     DefinicionPagina(historico.render, "Historico de cambios de precio", SECCION_TRABAJO,
                      accion=_LEE),
+    DefinicionPagina(entregar.render, "Entregar paquete", SECCION_TRABAJO, "UC-22",
+                     Accion.ENTREGAR_PAQUETE),
     DefinicionPagina(
         escenarios.render, "Escenarios de sensibilidad", SECCION_INVESTIGACION, "UC-08", _EDITA
```
```diff
--- a/tests/unit/test_ui_app.py
+++ b/tests/unit/test_ui_app.py
@@ -46,4 +46,5 @@
     "Actualizar precios",
     "Historico de cambios de precio",
+    "Entregar paquete",
 )
 
@@ -61,4 +62,5 @@
     "escenarios": "UC-08",
     "similares": "UC-03",
+    "entregar": "UC-22",
 }
 
@@ -101,5 +103,5 @@
 
 
-def test_las_cinco_pantallas_con_caso_de_uso_lo_declaran() -> None:
+def test_las_seis_pantallas_con_caso_de_uso_lo_declaran() -> None:
     declarados = {p.ruta_url: p.caso_uso for p in PAGINAS if p.caso_uso is not None}
     assert declarados == CASOS_DE_USO
@@ -124,5 +126,5 @@
 def test_cada_pagina_tiene_una_ruta_url_propia() -> None:
     rutas = [pagina.ruta_url for pagina in paginas_visibles(False)]
-    assert len(set(rutas)) == len(rutas) == len(TITULOS_TRABAJO) + len(TITULOS_INVESTIGACION)
+    assert len(set(rutas)) == len(rutas) == len(PAGINAS)
     assert "componer" in rutas
 
@@ -351,7 +353,7 @@
 
 
-def test_son_once_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
+def test_son_doce_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
     rutas = [p.ruta_url for p in PAGINAS]
-    assert len(rutas) == 11
+    assert len(rutas) == 12
     assert rutas.index("hoja") == rutas.index("elaborar") + 1
     assert pagina_por_ruta("hoja").seccion == SECCION_TRABAJO
```
  `tests/unit/test_ui_importable.py`: `"ui.entrega"` entra a `MODULOS_SIN_PAGINA` y la cifra
  `len(modulos) == len(MODULOS_SIN_PAGINA) + N` sube en uno. `tests/unit/test_arquitectura_s5.py`:
  `"entregar"` entra a `PAGINAS_QUE_ABREN_EL_CASO` (todas preparan el caso con `preparar_base`).
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/integration/test_entrega.py tests/unit/test_ui_entregar.py
tests/unit/test_ui_app.py tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py -v
-W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'ui.entrega'` y FAIL de
`test_ui_app` por el título «Entregar paquete» ausente.
```bash
git add tests/integration/test_entrega.py tests/unit/test_ui_entregar.py tests/unit/test_ui_app.py \
  tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py
git commit -m "test(ui): entregar el paquete firmado desde la pantalla, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`ui/entrega.py`**
```python
"""Entregar el paquete auditado, sin Streamlit (spec S3 §8.2, UC-22; RF-85).

Orquesta lo que `core`, `paquete`, `seguridad` y `adapters.espacio` no pueden orquestar entre sí
(el núcleo no conoce a los demás): el anexo de espacio, los anexos de S1, S2 y S4, la cadena, el
informe del emisor, la firma y el registro en `evento_acceso`. La base del caso **no cambia**: lo
único que se escribe es el registro de la entrega en la base de la instalación.

`anexos_de_cadena` es el proveedor que `guardar_presupuesto(..., anexos_de=...)` y
`verificar_cadena` usan para que la cadena cubra el espacio de la versión: lo pasa todo
camino que escribe `esp_*` (la hoja, los sembradores).
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.espacio import cargar_espacio
from adapters.espacio.serie import espacio_a_objeto
from core import models
from core.budget import cadena, canonico
from core.contracts.verificacion import Severidad
from core.models.cadena import EslabonVersion
from paquete import anexos as anexos_paquete
from paquete.exportar import Emisor, construir_paquete
from paquete.formato import EXTENSION
from paquete.verificar import armar_cadena_json
from seguridad import empresas, eventos

__all__ = [
    "Entrega",
    "EstadoDeLaCadena",
    "EntregaRechazada",
    "Resumen",
    "anexos_de_cadena",
    "anexos_del_paquete",
    "con_anexos_de_cadena",
    "entregar",
    "estado_de_la_cadena",
    "nombre_de_archivo",
    "resumen_de_entrega",
]

NOMBRE_ANEXO_ESPACIO = "anexos/espacio.json"
FORMATO_INFORME = "silice-informe"


class EntregaRechazada(ValueError):  # noqa: N818
    """No se puede entregar; el mensaje dice por qué (22c, 22e, 22f)."""


def anexos_de_cadena(session: Session, version: models.Presupuesto) -> Mapping[str, bytes]:
    """Los anexos que la cadena cubre: solo el espacio, y solo si la versión lo tiene."""
    espacio = cargar_espacio(session, version.id)
    if espacio.vacio:
        return {}
    return {NOMBRE_ANEXO_ESPACIO: canonico.json_canonico(espacio_a_objeto(espacio))}


def anexos_del_paquete(
    session: Session, version: models.Presupuesto, ia: bytes | None = None
) -> dict[str, bytes]:
    """Los anexos que viajan: espacio (cubierto por la cadena), reajuste de S1, control de S2 y, si
    el asistente de S4 los dejó, el registro de IA. Los de S1 y S2 llevan huella por entrada y no
    tienen cadena propia (límite declarado)."""
    salida = dict(anexos_de_cadena(session, version))
    reajuste = anexos_paquete.anexo_de_tablas(
        session, "reajuste", anexos_paquete.TABLAS_DE_REAJUSTE, version.proyecto_id
    )
    control = anexos_paquete.anexo_de_tablas(
        session, "control", anexos_paquete.TABLAS_DE_CONTROL, version.proyecto_id
    )
    if reajuste is not None:
        salida["anexos/reajuste.json"] = reajuste
    if control is not None:
        salida["anexos/control.json"] = control
    if ia is not None:
        salida["anexos/ia.json"] = ia
    return salida


def _cadena_json(session: Session, version: models.Presupuesto) -> bytes:
    proyecto = version.proyecto
    codigos = {v.id: v.codigo for v in proyecto.presupuestos}
    eslabones = [e for e in cadena.eslabones_de(session, proyecto)
                 if e.presupuesto_id <= version.id]
    objetos, cambios = [], {}
    for e in eslabones:
        objetos.append({
            "codigo": codigos[e.presupuesto_id], "anterior": e.anterior,
            "huella_contenido": e.huella_contenido, "huella_cambios": e.huella_cambios,
            "huella_anexos": e.huella_anexos, "huella_eslabon": e.huella_eslabon,
            "usuario": e.usuario, "fecha_hora": e.fecha_hora.isoformat(), "tipo": e.tipo,
            "version_formato": e.version_formato,
        })
        registros = session.scalars(
            select(models.RegistroCambio)
            .where(models.RegistroCambio.version_resultante_id == e.presupuesto_id)
            .order_by(models.RegistroCambio.id)
        )
        filas = [cadena.fila_de_cambio(r) for r in registros]
        if filas:
            cambios[codigos[e.presupuesto_id]] = filas
    return canonico.json_canonico(armar_cadena_json(objetos, cambios))


def con_anexos_de_cadena(session: Session) -> Session:
    """La sesión de una pantalla que guarda versiones con su espacio: la cadena lo cubre."""
    return cadena.anexos_por_omision(session, anexos_de_cadena)


@dataclass(frozen=True, slots=True)
class EstadoDeLaCadena:
    """Lo que la pestaña Trazabilidad dice de la cadena de un proyecto (S3 §6.4 y §6.5)."""

    integra: bool
    mensaje: str
    declaracion: str | None  # «Versiones 001 a 004 selladas el …», si hay retroactivas


def estado_de_la_cadena(session: Session, proyecto_nombre: str) -> EstadoDeLaCadena | None:
    """Verifica la cadena del proyecto recalculando cada huella; `None` si el proyecto no existe."""
    proyecto = session.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == proyecto_nombre)
    ).first()
    if proyecto is None:
        return None
    resultado = cadena.verificar_cadena(session, proyecto, anexos_de=anexos_de_cadena)
    return EstadoDeLaCadena(
        resultado.integra, cadena.mensaje_de_cadena(resultado),
        cadena.texto_retroactivo(session, proyecto),
    )


@dataclass(frozen=True, slots=True)
class Resumen:
    """Lo que la pantalla muestra antes de pedir la contraseña (UC-22 paso 2)."""

    codigo: str
    total: Decimal
    hallazgos_por_severidad: Mapping[str, int]
    cadena_integra: bool
    mensaje_de_cadena: str
    empresa: str | None
    firma_disponible: bool
    anexos: tuple[str, ...]


def resumen_de_entrega(
    session: Session, instalacion: Session, version: models.Presupuesto
) -> Resumen:
    resultado = cadena.verificar_cadena(session, version.proyecto, anexos_de=anexos_de_cadena)
    empresa = empresas.empresa_propia(instalacion)
    severidades: dict[str, int] = {}
    for h in session.scalars(
        select(models.Hallazgo).where(models.Hallazgo.presupuesto_id == version.id)
    ):
        nombre = Severidad(h.severidad).name
        severidades[nombre] = severidades.get(nombre, 0) + 1
    return Resumen(
        codigo=version.codigo,
        total=sum((r.total for r in version.partidas), Decimal(0)),
        hallazgos_por_severidad=severidades,
        cadena_integra=resultado.integra,
        mensaje_de_cadena=cadena.mensaje_de_cadena(resultado),
        empresa=empresa.nombre if empresa else None,
        firma_disponible=empresas.clave_activa(instalacion) is not None,
        anexos=tuple(sorted(anexos_del_paquete(session, version))),
    )


@dataclass(frozen=True, slots=True)
class Entrega:
    datos: bytes
    nombre: str
    sha256: str
    paquete_id: str
    firmado: bool


def nombre_de_archivo(proyecto: str, codigo: str) -> str:
    """`PROYECTO-codigo.silice` con solo caracteres seguros."""
    limpio = "".join(c if c.isalnum() else "-" for c in proyecto).strip("-")[:60] or "proyecto"
    return f"{limpio}-{codigo}{EXTENSION}"


def entregar(
    session: Session,
    instalacion: Session,
    version: models.Presupuesto,
    *,
    usuario: str,
    ahora: datetime,
    version_silice: str,
    destinatario: str | None = None,
    contrasena_clave: str | None = None,
    ia: bytes | None = None,
) -> Entrega:
    """Genera el `.silice` de `version` en memoria. Con `contrasena_clave` lo firma (la UI ya
    exigió el propio equipo). `EntregaRechazada` si la cadena está rota (22c) o la versión no
    está sellada; `ContrasenaDeClaveIncorrecta` (22b) y `PaqueteRechazado` (22f) propagan."""
    resultado = cadena.verificar_cadena(session, version.proyecto, anexos_de=anexos_de_cadena)
    if not resultado.integra:
        raise EntregaRechazada(cadena.mensaje_de_cadena(resultado))
    eslabon = session.get(EslabonVersion, version.id)
    if eslabon is None:
        raise EntregaRechazada(f"La versión {version.codigo} no está sellada.")
    estructura = canonico.estructura(session, version)
    privada, huella_clave = None, None
    if contrasena_clave is not None:
        privada = empresas.abrir_privada(instalacion, contrasena_clave)
        huella_clave = empresas.clave_activa(instalacion).huella
    empresa = empresas.empresa_propia(instalacion)
    total = sum((r.total for r in version.partidas), Decimal(0))
    paquete_id = str(uuid.uuid4())
    datos = construir_paquete(
        presupuesto=canonico.json_canonico(estructura),
        informe=canonico.json_canonico(
            {"formato": FORMATO_INFORME, "version_formato": 1,
             "codigo": version.codigo, "hallazgos": estructura["hallazgos"]}
        ),
        cadena=_cadena_json(session, version),
        anexos=anexos_del_paquete(session, version, ia),
        emisor=Emisor(empresa.nombre if empresa else None, huella_clave, usuario),
        destinatario=destinatario, proyecto=version.proyecto.nombre, codigo=version.codigo,
        moneda=version.moneda, total=format(total, "f"), ultima_huella=eslabon.huella_eslabon,
        ahora=ahora, version_silice=version_silice, privada=privada, paquete_id=paquete_id,
    )
    sha = hashlib.sha256(datos).hexdigest()
    detalle = f"{paquete_id}; version {version.codigo}; sha256 {sha}"
    if privada is not None:
        eventos.registrar(instalacion, "firma", ahora, detalle=detalle)
    eventos.registrar(instalacion, "paquete exportado", ahora, detalle=detalle)
    instalacion.commit()
    return Entrega(
        datos, nombre_de_archivo(version.proyecto.nombre, version.codigo), sha, paquete_id,
        privada is not None,
    )
```
**`ui/paginas/entregar.py`**
```python
"""Entregar el paquete auditado (UC-22; spec S3 §8.2; RF-85).

El rol *arma* elige un proyecto y una versión, ve lo que va a viajar (total, hallazgos, cadena,
anexos, empresa y si hay clave de firma) y descarga el `.silice`. Si hay clave de firma, pide su
contraseña **en un formulario que se vacía al enviar** y solo desde el propio equipo
(`exigir_local`); sin clave, el paquete sale «sin firma» y la pantalla lo dice. Una cadena rota
impide entregar y se muestra con su mensaje. La base del caso no cambia.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from importlib import metadata

import streamlit as st
from sqlalchemy import select

from core import models
from core.catalog import abrir_sesion, crear_motor
from core.verification.texto import formatear_decimal
from operacion.base_datos import ErrorDeBase, preparar_base
from paquete.formato import PaqueteRechazado
from seguridad.empresas import ContrasenaDeClaveIncorrecta
from seguridad.permisos import Accion, Sensible
from ui import entrega
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.texto_seguro import texto_seguro

CLAVE_ULTIMA = "entregar_ultima"  # la última `Entrega` generada, para mostrar su descarga


def version_de_silice() -> str:
    try:
        return metadata.version("silice")
    except metadata.PackageNotFoundError:  # corrida desde el código fuente sin instalar
        return "0.8.0"


def _ahora() -> datetime:
    return ui_sesion.ahora()


def _resumen(resumen: entrega.Resumen) -> None:
    columnas = st.columns(3)
    columnas[0].metric("Total", formatear_decimal(resumen.total.quantize(Decimal("0.01"))))
    columnas[1].metric("Hallazgos", sum(resumen.hallazgos_por_severidad.values()))
    columnas[2].metric("Cadena", "íntegra" if resumen.cadena_integra else "ROTA")
    if resumen.hallazgos_por_severidad:
        st.caption(", ".join(f"{texto_seguro(str(n))} {texto_seguro(k.lower())}" for k, n in
                             sorted(resumen.hallazgos_por_severidad.items())))
    if not resumen.cadena_integra:
        st.error(texto_seguro(resumen.mensaje_de_cadena))
    nombres = [a.removeprefix("anexos/").removesuffix(".json") for a in resumen.anexos]
    st.caption("Viaja con: " + ", ".join(texto_seguro(n) for n in ("presupuesto", "informe",
                                                                   "cadena", *nombres)) + ".")
    if resumen.empresa is None:
        st.warning("Todavía no hay empresa en Administración: el paquete no dirá quién lo emite.")
    elif not resumen.firma_disponible:
        st.warning("No hay clave de firma: el paquete saldrá SIN FIRMA y quien lo reciba lo "
                   "verá como «no verificado».")


def render() -> None:
    ui_sesion.exigir(Accion.ENTREGAR_PAQUETE)
    ruta = ruta_caso()
    try:
        preparar_base(ruta)  # RV-5: la única puerta a la base del caso
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as caso, ui_sesion.instalacion() as bd:
            proyectos = caso.scalars(
                select(models.Proyecto).order_by(models.Proyecto.nombre)).all()
            if not proyectos:
                st.info("Este caso todavía no tiene proyectos.")
                return
            por_id = {p.id: p for p in proyectos}  # ids: un objeto de otro ciclo ya no sirve
            proyecto = por_id[st.selectbox("Proyecto", list(por_id),
                                           format_func=lambda i: por_id[i].nombre,
                                           key="entregar_proyecto")]
            versiones = sorted(proyecto.presupuestos, key=lambda v: v.id, reverse=True)
            if not versiones:
                st.info("Este proyecto todavía no tiene versiones.")
                return
            codigos = {v.id: v for v in versiones}
            version = codigos[st.selectbox("Versión", list(codigos),
                                           format_func=lambda i: codigos[i].codigo,
                                           key="entregar_version")]
            resumen = entrega.resumen_de_entrega(caso, bd, version)
            _resumen(resumen)
            with st.form("entregar_formulario", clear_on_submit=True):
                destinatario = st.text_input("Para quién es (opcional)", key="entregar_destino")
                contrasena = st.text_input(
                    "Contraseña de la clave de firma", type="password", key="entregar_clave",
                    disabled=not resumen.firma_disponible)
                enviar = st.form_submit_button("Generar paquete", type="primary",
                                               key="entregar_enviar",
                                               disabled=not resumen.cadena_integra)
            if enviar:
                firmar = resumen.firma_disponible
                if firmar:
                    ui_sesion.exigir_local(Sensible.FIRMAR)
                try:
                    generada = entrega.entregar(
                        caso, bd, version, usuario=ui_sesion.responsable_actual(), ahora=_ahora(),
                        version_silice=version_de_silice(),
                        destinatario=destinatario.strip() or None,
                        contrasena_clave=contrasena if firmar else None)
                    st.session_state[CLAVE_ULTIMA] = (version.id, generada)
                except ContrasenaDeClaveIncorrecta:
                    st.error("La contraseña de la clave no es correcta.")
                except (entrega.EntregaRechazada, PaqueteRechazado) as error:
                    st.error(texto_seguro(str(error)))
            version_y_entrega = st.session_state.get(CLAVE_ULTIMA)
            if version_y_entrega is not None and version_y_entrega[0] == version.id:
                ultima = version_y_entrega[1]
                st.success("Paquete listo" + (" y firmado." if ultima.firmado else " (sin firma)."))
                st.caption(f"SHA-256: {texto_seguro(ultima.sha256)}")
                st.download_button("Descargar el paquete", ultima.datos,
                                   file_name=ultima.nombre, mime="application/zip",
                                   key="entregar_bajar")
    finally:
        motor.dispose()
```
  y la entrada de la pantalla en `ui/app.py` (ya incluida en el diff del paso 1: la importación
  `entregar` y su `DefinicionPagina` con `Accion.ENTREGAR_PAQUETE`).
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/integration/test_entrega.py tests/unit/test_ui_entregar.py
tests/unit/test_ui_app.py tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py
tests/unit/test_ui_marco.py -v -W error` → verde. Run: `uv run ruff check ui` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add ui/entrega.py ui/paginas/entregar.py ui/app.py
git commit -m "feat(ui): pantalla Entregar paquete con resumen, firma y registro" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 17: Administración (cuentas, empresa, claves, accesos) y restablecer el administrador

**Rama:** `inc/080-s3-3-paquete`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/paginas/administracion.py`, `seguridad/claves_api.py`,
  `scripts/restablecer_administrador.py`
- Modificar: `ui/app.py`, `tests/unit/test_ui_app.py`, `tests/unit/test_ui_importable.py`,
  `scripts/README.md`
- Prueba: `tests/unit/test_ui_administracion.py`, `tests/unit/test_claves_api_y_red.py`,
  `tests/integration/test_restablecer_administrador.py`

**Interfaces:**
- Consume: `seguridad.{cuentas, empresas, eventos, firma}` (tareas 5 y 13),
  `seguridad.modelo.{Usuario, ClaveApi}`, `seguridad.permisos.{Accion, Rol, Sensible,
  aviso_de_roles}`, `seguridad.red.*`, `ui.sesion` (tarea 6), `operacion.instalacion`.
- Produce:
  - `seguridad.claves_api`: `def crear(session: Session, nombre: str, actor: str, ahora:
      datetime) -> tuple[str, ClaveApi]`
  - `seguridad.claves_api`: `def verificar(session: Session, presentada: str | None, ahora:
      datetime) -> ClaveApi | None`
  - `seguridad.claves_api`: `def revocar(session: Session, clave_id: int, actor: str, ahora:
      datetime) -> None`
  - `seguridad.claves_api`: `def etiqueta(fila: ClaveApi) -> str`
  - `ui.paginas.administracion`: `def render() -> None`
  - `scripts.restablecer_administrador`: `def restablecer(ahora: datetime | None=None) ->
      tuple[str, Path]`
  - `scripts.restablecer_administrador`: `def main(argv: list[str] | None=None) -> int`

**Pestañas** (S3 §5.7): Cuentas (alta con contraseña temporal, roles, desactivar, desbloquear,
restablecer, y el aviso de que una cuenta con *arma* y *revisa* podrá revisar lo que armó), Empresa
y clave de firma (solo desde el propio equipo), Empresas registradas (con la huella comprobada),
Claves de API (la clave se muestra **una vez**; la base guarda el SHA-256 de un secreto de 256 bits)
y Accesos. **Restablecer al administrador** (S3 §5.4): quien tiene acceso al equipo corre el script,
que emite un código de instalación nuevo de un solo uso (20 caracteres base32, 100 bits) en
`<datos>/codigo_instalacion.txt` y en la consola, cierra las sesiones de los administradores y deja
el hecho en `evento_acceso`.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_claves_api_y_red.py`**
```python
"""Claves de API y 'solo desde el propio equipo' (RF-88, RNF-16; spec S3 §5.6 y §10)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from seguridad import claves_api
from seguridad.modelo import ClaveApi
from seguridad.red import es_bucle_local, es_local, red_local_activa
from tests.fixtures.instalacion import AHORA, instalacion


def test_la_clave_se_muestra_una_vez_y_la_base_guarda_solo_la_huella(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        clave, fila = claves_api.crear(sesion, "plugin de AutoCAD", "admin", AHORA)
        identificador, secreto = clave.split(".")
        assert len(identificador) == 8 and len(secreto) >= 43  # 256 bits
        assert fila.huella_secreto != secreto and secreto not in fila.huella_secreto
        assert claves_api.verificar(sesion, clave, AHORA).id == fila.id
        sesion.commit()
    assert secreto.encode() not in (tmp_path / "instalacion.db").read_bytes()


@pytest.mark.parametrize(
    "presentada", [None, "", "sinpunto", "a.b.c", "ABCDEFGH.secreto-equivocado", "ZZZZZZZZ.x"]
)
def test_clave_ausente_mal_formada_o_desconocida_no_vale(tmp_path: Path, presentada) -> None:
    with instalacion(tmp_path) as sesion:
        claves_api.crear(sesion, "plugin", "admin", AHORA)
        assert claves_api.verificar(sesion, presentada, AHORA) is None


def test_una_clave_revocada_no_vale_y_el_ultimo_uso_se_registra(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion:
        clave, fila = claves_api.crear(sesion, "plugin", "admin", AHORA)
        assert fila.ultimo_uso is None
        claves_api.verificar(sesion, clave, AHORA + timedelta(minutes=5))
        assert fila.ultimo_uso == AHORA + timedelta(minutes=5)
        claves_api.revocar(sesion, fila.id, "admin", AHORA)
        assert claves_api.verificar(sesion, clave, AHORA) is None
        assert sesion.get(ClaveApi, fila.id).revocada
        assert claves_api.etiqueta(fila) == f"api:{fila.identificador}"


def test_una_clave_necesita_nombre(tmp_path: Path) -> None:
    with instalacion(tmp_path) as sesion, pytest.raises(ValueError, match="nombre"):
        claves_api.crear(sesion, "  ", "admin", AHORA)


@pytest.mark.parametrize(
    "ip,bucle",
    [("127.0.0.1", True), ("127.1.2.3", True), ("::1", True), ("::ffff:127.0.0.1", True),
     ("192.168.1.20", False), ("10.0.0.5", False), ("0.0.0.0", False), ("fe80::1%eth0", False),
     ("", False), ("no es ip", False), (None, False)],
)
def test_solo_el_bucle_local_es_el_propio_equipo(ip, bucle: bool) -> None:
    assert es_bucle_local(ip) is bucle


def test_sin_ip_manda_si_la_red_local_esta_encendida() -> None:
    assert es_local(None, red_local_encendida=False) is True
    assert es_local(None, red_local_encendida=True) is False
    assert es_local("192.168.1.20", red_local_encendida=False) is False
    assert es_local("127.0.0.1", red_local_encendida=True) is True


def test_la_red_local_esta_apagada_por_defecto() -> None:
    assert red_local_activa({}) is False
    assert red_local_activa({"SILICE_RED_LOCAL": "1"}) is True
    assert red_local_activa({"SILICE_RED_LOCAL": "true"}) is False
```
**`tests/unit/test_ui_administracion.py`**
```python
"""Administración (UC-21; RF-80, RF-84, RF-88; spec S3 §5.7): rol, equipo local y secretos."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad import empresas
from seguridad.modelo import ClaveApi, ClaveEmpresa, Usuario
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import sesion as ui_sesion
from ui.sesion import MENSAJE_SIN_PERMISO, MENSAJE_SOLO_LOCAL


def _pagina() -> None:
    from ui.paginas import administracion

    administracion.render()


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


def _abrir(monkeypatch, tmp_path: Path, *roles: str, ip: str = "127.0.0.1") -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, *roles, ip=ip)
    return con_ficha(AppTest.from_function(_pagina, default_timeout=60), ficha).run()


def _guardar_empresa(at: AppTest) -> AppTest:
    at.text_input(key="adm_empresa_nombre").input("Contratista Demo, C.A.")
    at.text_input(key="adm_empresa_rif").input("J-00000000-0")
    at.button(key="adm_empresa_enviar").click()
    return at.run()


def test_el_administrador_ve_las_cinco_pestanas(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path, "administrador")
    assert not at.exception
    assert [t.label for t in at.tabs] == [
        "Cuentas", "Empresa y clave de firma", "Empresas registradas", "Claves de API", "Accesos"]


@pytest.mark.parametrize("rol", ["arma", "revisa"])
def test_un_rol_que_no_es_administrador_no_ve_nada_aunque_llegue_por_la_url(
    monkeypatch, tmp_path, rol
) -> None:
    at = _abrir(monkeypatch, tmp_path, rol)
    assert [e.value for e in at.error] == [MENSAJE_SIN_PERMISO] and not at.tabs


def test_sin_sesion_pide_entrar(monkeypatch, tmp_path) -> None:
    preparar(monkeypatch, tmp_path, "administrador")
    at = AppTest.from_function(_pagina, default_timeout=60).run()
    assert [e.value for e in at.error] == ["Entre con su usuario y contraseña."] and not at.tabs


def test_crear_una_cuenta_la_deja_con_contrasena_temporal_y_avisa_si_arma_y_revisa(
    monkeypatch, tmp_path
) -> None:
    at = _abrir(monkeypatch, tmp_path, "administrador")
    at.text_input(key="adm_login").input("pedro")
    at.text_input(key="adm_nombre").input("Pedro Pérez")
    at.multiselect(key="adm_roles").set_value(["arma", "revisa"])
    at.text_input(key="adm_temporal").input("una contrasena temporal larga")
    at.button(key="adm_crear_enviar").click()
    at = at.run()
    assert not at.exception and any("Cuenta creada" in s.value for s in at.success)
    assert any("revisar paquetes que ella misma armó" in w.value for w in at.warning)
    with ui_sesion.instalacion() as bd:
        pedro = bd.query(Usuario).filter_by(login="pedro").one()
        assert pedro.debe_cambiar_clave and "una contrasena temporal" not in pedro.huella_clave


def test_una_contrasena_temporal_corta_se_rechaza_con_mensaje_y_sin_cuenta(
    monkeypatch, tmp_path
) -> None:
    at = _abrir(monkeypatch, tmp_path, "administrador")
    at.text_input(key="adm_login").input("pedro")
    at.text_input(key="adm_nombre").input("Pedro")
    at.multiselect(key="adm_roles").set_value(["arma"])
    at.text_input(key="adm_temporal").input("corta")
    at.button(key="adm_crear_enviar").click()
    at = at.run()
    assert at.error and not at.exception
    with ui_sesion.instalacion() as bd:
        assert bd.query(Usuario).filter_by(login="pedro").count() == 0


def test_la_clave_de_firma_solo_se_genera_desde_el_propio_equipo(monkeypatch, tmp_path) -> None:
    at = _guardar_empresa(_abrir(monkeypatch, tmp_path, "administrador", ip="192.168.1.20"))
    at.text_input(key="adm_clave_uno").input("una clave de firma larga y unica")
    at.text_input(key="adm_clave_dos").input("una clave de firma larga y unica")
    at.button(key="adm_generar_enviar").click()
    at = at.run()
    assert MENSAJE_SOLO_LOCAL in [e.value for e in at.error]
    with ui_sesion.instalacion() as bd:
        assert bd.query(ClaveEmpresa).count() == 0


def test_generar_la_clave_en_el_equipo_muestra_la_huella_y_nunca_la_privada(
    monkeypatch, tmp_path
) -> None:
    at = _guardar_empresa(_abrir(monkeypatch, tmp_path, "administrador"))
    contrasena = "una clave de firma larga y unica"
    at.text_input(key="adm_clave_uno").input(contrasena)
    at.text_input(key="adm_clave_dos").input(contrasena)
    at.button(key="adm_generar_enviar").click()
    at = at.run()
    assert not at.exception
    with ui_sesion.instalacion() as bd:
        clave = empresas.clave_activa(bd)
        assert clave is not None and clave.privada_cifrada
        assert contrasena.encode() not in clave.privada_cifrada
    visible = " ".join([*(m.value for m in at.markdown), *(m.value for m in at.metric)])
    assert contrasena not in visible
    assert at.metric and len(at.metric[0].value) == 24  # 5 grupos de 4 y 4 guiones


def test_la_clave_de_api_se_muestra_una_vez_y_la_base_guarda_solo_su_huella(
    monkeypatch, tmp_path
) -> None:
    at = _abrir(monkeypatch, tmp_path, "administrador")
    at.text_input(key="adm_api_nombre").input("plugin de Revit")
    at.button(key="adm_api_enviar").click()
    at = at.run()
    secreto = at.code[0].value
    assert "." in secreto and any("no se vuelve a mostrar" in s.value for s in at.success)
    with ui_sesion.instalacion() as bd:
        fila = bd.query(ClaveApi).one()
        assert secreto.split(".", 1)[1] not in fila.huella_secreto and not fila.revocada
    assert not at.run().code  # el siguiente ciclo ya no la muestra


def test_la_clave_de_api_no_se_crea_desde_otra_maquina(monkeypatch, tmp_path) -> None:
    at = _abrir(monkeypatch, tmp_path, "administrador", ip="10.0.0.5")
    at.text_input(key="adm_api_nombre").input("plugin")
    at.button(key="adm_api_enviar").click()
    at = at.run()
    assert MENSAJE_SOLO_LOCAL in [e.value for e in at.error]
    with ui_sesion.instalacion() as bd:
        assert bd.query(ClaveApi).count() == 0
```
**`tests/integration/test_restablecer_administrador.py`**
```python
"""`scripts/restablecer_administrador.py`: devolver el acceso con acceso al equipo (S3 §5.4)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from operacion.instalacion import cerrar_motores, sesion_de_instalacion
from scripts import restablecer_administrador as script
from seguridad import cuentas, sesiones
from seguridad.modelo import CodigoInstalacion, EventoAcceso, Sesion, Usuario
from tests.fixtures.instalacion import AHORA, CONTRASENA, administrador, persona


@pytest.fixture
def instalacion_con_gente(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SILICE_DATOS", str(tmp_path))
    monkeypatch.setenv("SILICE_INSTALACION", str(tmp_path / "instalacion.db"))
    cerrar_motores()
    with sesion_de_instalacion() as bd:
        admin = administrador(bd, tmp_path)
        luis = persona(bd, admin, "luis", ("arma",))
        fichas = (sesiones.abrir(bd, admin, AHORA), sesiones.abrir(bd, luis, AHORA))
    yield tmp_path, fichas
    cerrar_motores()


def test_emite_un_codigo_cierra_las_sesiones_de_los_administradores_y_deja_registro(
    instalacion_con_gente,
) -> None:
    carpeta, (ficha_admin, ficha_luis) = instalacion_con_gente
    codigo, archivo = script.restablecer(AHORA)
    assert len(codigo) == 20 and archivo == carpeta / "codigo_instalacion.txt"
    assert archivo.read_text(encoding="ascii").replace("-", "").strip() == codigo
    with sesion_de_instalacion() as bd:
        assert sesiones.validar(bd, ficha_admin, AHORA) is None  # la del administrador, cerrada
        assert sesiones.validar(bd, ficha_luis, AHORA) is not None  # la de Luis sigue
        [fila] = bd.query(CodigoInstalacion).filter_by(motivo="restablecimiento").all()
        assert fila.usado is None
        eventos = bd.query(EventoAcceso).filter_by(tipo="codigo de instalacion")
        assert "restablecimiento" in [e.detalle for e in eventos]
        cerradas = bd.query(Sesion).filter_by(cerrada=True, motivo_cierre="restablecimiento")
        assert cerradas.count() == 1


def test_con_el_codigo_se_recupera_la_cuenta_aunque_ya_haya_usuarios(
    instalacion_con_gente,
) -> None:
    carpeta, _ = instalacion_con_gente
    codigo, _ = script.restablecer(AHORA)
    nueva = "otra contrasena larga y nueva"
    with sesion_de_instalacion() as bd:
        usuario = cuentas.reclamar_instalacion(
            bd, codigo, "admin", "Admin de Prueba", nueva, AHORA, carpeta,
            freno=cuentas.FrenoGlobal(),
        )
        assert usuario.login == "admin" and bd.query(Usuario).count() == 2
        assert not (carpeta / "codigo_instalacion.txt").exists()  # el código se usó y se borró
        with pytest.raises(cuentas.ErrorDeAcceso):  # y no sirve dos veces
            cuentas.reclamar_instalacion(
                bd, codigo, "admin", "Admin de Prueba", nueva, AHORA, carpeta,
                freno=cuentas.FrenoGlobal(),
            )
        entra = cuentas.autenticar(bd, "admin", nueva, AHORA, freno=cuentas.FrenoGlobal())
        assert entra.login == "admin"
    assert CONTRASENA != nueva


def test_la_consola_muestra_el_codigo_y_donde_esta(instalacion_con_gente, capsys) -> None:
    assert script.main([]) == 0
    salida = capsys.readouterr().out
    assert "Código de instalación nuevo" in salida and "codigo_instalacion.txt" in salida
    assert "sesiones de los administradores quedaron cerradas" in salida


def test_el_script_no_toca_la_hora_de_otros_eventos(instalacion_con_gente) -> None:
    antes = datetime.now()
    script.restablecer()
    with sesion_de_instalacion() as bd:
        ultimo = bd.query(EventoAcceso).order_by(EventoAcceso.id.desc()).first()
        assert ultimo.fecha_hora >= antes.replace(microsecond=0)
```
```diff
--- a/ui/app.py
+++ b/ui/app.py
@@ -71,4 +71,5 @@
 from ui.paginas import (
     actualizacion,
+    administracion,
     catalogo,
     componer,
@@ -89,4 +90,5 @@
 SECCION_TRABAJO = "Trabajo"
 SECCION_INVESTIGACION = "Investigacion"
+SECCION_ADMINISTRACION = "Administracion"
 ROTULO_SIGUIENTE = "Siguiente: {}"
 CLAVE_BOTON_SIGUIENTE = "marco_siguiente"
@@ -140,4 +142,6 @@
                      accion=_EDITA),
     DefinicionPagina(visor.render, "Visor 3D del modelo", SECCION_INVESTIGACION, accion=_EDITA),
+    DefinicionPagina(administracion.render, "Administracion", SECCION_ADMINISTRACION, "UC-21",
+                     Accion.ADMINISTRAR_CUENTAS),
 )
 
```
```diff
--- a/tests/unit/test_ui_app.py
+++ b/tests/unit/test_ui_app.py
@@ -25,4 +25,5 @@
     PAGINAS,
     ROTULO_SIGUIENTE,
+    SECCION_ADMINISTRACION,
     SECCION_INVESTIGACION,
     SECCION_TRABAJO,
@@ -49,4 +50,6 @@
 )
 
+TITULOS_ADMINISTRACION = ("Administracion",)
+
 TITULOS_INVESTIGACION = (
     "Escenarios de sensibilidad",
@@ -63,4 +66,5 @@
     "similares": "UC-03",
     "entregar": "UC-22",
+    "administracion": "UC-21",
 }
 
@@ -73,14 +77,17 @@
 
 
-def test_sin_modo_entrega_dos_secciones_en_el_orden_del_trabajo() -> None:
+def test_sin_modo_entrega_tres_secciones_en_el_orden_del_trabajo() -> None:
+    """S3 §5.7 enmienda RF-42: Administración se suma a las dos de siempre."""
     secciones = secciones_visibles(False)
-    assert tuple(secciones) == (SECCION_TRABAJO, SECCION_INVESTIGACION)
+    assert tuple(secciones) == (
+        SECCION_TRABAJO, SECCION_INVESTIGACION, SECCION_ADMINISTRACION)
     assert _titulos(secciones[SECCION_TRABAJO]) == TITULOS_TRABAJO
     assert _titulos(secciones[SECCION_INVESTIGACION]) == TITULOS_INVESTIGACION
+    assert _titulos(secciones[SECCION_ADMINISTRACION]) == TITULOS_ADMINISTRACION
 
 
 def test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo() -> None:
     secciones = secciones_visibles(True)
-    assert tuple(secciones) == (SECCION_TRABAJO,)
+    assert tuple(secciones) == (SECCION_TRABAJO, SECCION_ADMINISTRACION)
     assert secciones[SECCION_TRABAJO] == secciones_visibles(False)[SECCION_TRABAJO]
 
@@ -103,5 +110,5 @@
 
 
-def test_las_seis_pantallas_con_caso_de_uso_lo_declaran() -> None:
+def test_las_siete_pantallas_con_caso_de_uso_lo_declaran() -> None:
     declarados = {p.ruta_url: p.caso_uso for p in PAGINAS if p.caso_uso is not None}
     assert declarados == CASOS_DE_USO
@@ -312,5 +319,5 @@
 
 
-def test_la_aplicacion_declara_la_navegacion_arriba_con_los_dos_grupos(
+def test_la_aplicacion_declara_la_navegacion_arriba_con_los_tres_grupos(
     monkeypatch, tmp_path: Path
 ) -> None:
@@ -330,8 +337,9 @@
     paginas, kwargs = llamadas[0]
     assert kwargs.get("position") == "top"
-    assert list(paginas) == [SECCION_TRABAJO, SECCION_INVESTIGACION]
-
-
-def test_modo_entrega_declara_solo_el_grupo_trabajo_en_la_navegacion_superior(
+    assert list(paginas) == [
+        SECCION_TRABAJO, SECCION_INVESTIGACION, SECCION_ADMINISTRACION]
+
+
+def test_modo_entrega_omite_solo_el_grupo_investigacion_en_la_navegacion_superior(
     monkeypatch, tmp_path: Path
 ) -> None:
@@ -350,10 +358,10 @@
     paginas, kwargs = llamadas[0]
     assert kwargs.get("position") == "top"
-    assert list(paginas) == [SECCION_TRABAJO]
-
-
-def test_son_doce_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
+    assert list(paginas) == [SECCION_TRABAJO, SECCION_ADMINISTRACION]
+
+
+def test_son_trece_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
     rutas = [p.ruta_url for p in PAGINAS]
-    assert len(rutas) == 12
+    assert len(rutas) == 13
     assert rutas.index("hoja") == rutas.index("elaborar") + 1
     assert pagina_por_ruta("hoja").seccion == SECCION_TRABAJO
@@ -421,3 +429,3 @@
     assert "Importar plano" in rotulos
     assert "Guardar version" in rotulos
-    assert list(llamadas[0]) == [SECCION_TRABAJO]  # ninguna seccion de Investigacion
+    assert list(llamadas[0]) == [SECCION_TRABAJO, SECCION_ADMINISTRACION]
```
  `tests/unit/test_ui_importable.py`: la cifra de páginas sube en uno. `scripts/README.md` gana la
  fila del script (la prueba `test_scripts_documentados` falla si falta).
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_claves_api_y_red.py tests/unit/test_ui_administracion.py
tests/integration/test_restablecer_administrador.py tests/unit/test_ui_app.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'seguridad.claves_api'` y
`... 'scripts.restablecer_administrador'`; `test_ui_administracion` FAIL con `ModuleNotFoundError:
No module named 'ui.paginas.administracion'` dentro de la página de prueba.
```bash
git add tests/unit/test_claves_api_y_red.py tests/unit/test_ui_administracion.py \
  tests/integration/test_restablecer_administrador.py tests/unit/test_ui_app.py \
  tests/unit/test_ui_importable.py
git commit -m "test(ui): administracion de cuentas, empresa, claves y accesos, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`seguridad/claves_api.py`**
```python
"""Claves de API para herramientas externas (spec S3 §10; DA-S3-8; SEG-15).

La clave se muestra UNA vez como `<identificador>.<secreto>`: el identificador público de 8
caracteres va aparte del secreto, que conserva sus 256 bits. La base guarda solo el SHA-256 del
secreto (Argon2 en cada petición de la API sería lento y no aporta: el secreto es aleatorio).
La comparación es de tiempo constante.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from seguridad import eventos
from seguridad.modelo import ClaveApi

ALFABETO_IDENTIFICADOR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
LONGITUD_IDENTIFICADOR = 8
CABECERA = "X-Silice-Clave"
RENOVACION_MINIMA = timedelta(minutes=1)


def _huella(secreto: str) -> str:
    return hashlib.sha256(secreto.encode("utf-8")).hexdigest()


def crear(session: Session, nombre: str, actor: str, ahora: datetime) -> tuple[str, ClaveApi]:
    """`(clave en claro, fila)`. La clave en claro no se guarda y no se puede recuperar."""
    if not nombre.strip():
        raise ValueError("La clave de API necesita un nombre (por ejemplo, el plugin que la usa).")
    while True:
        identificador = "".join(
            secrets.choice(ALFABETO_IDENTIFICADOR) for _ in range(LONGITUD_IDENTIFICADOR)
        )
        existente = select(ClaveApi.id).where(ClaveApi.identificador == identificador)
        if session.scalar(existente) is None:
            break
    secreto = secrets.token_urlsafe(32)
    fila = ClaveApi(
        nombre=nombre.strip(), identificador=identificador, huella_secreto=_huella(secreto),
        creada=ahora, creada_por=actor, revocada=False,
    )
    session.add(fila)
    session.flush()
    eventos.registrar(session, "clave de api", ahora, detalle=f"creada {identificador}; {actor}")
    session.commit()
    return f"{identificador}.{secreto}", fila


def verificar(session: Session, presentada: str | None, ahora: datetime) -> ClaveApi | None:
    """La fila de la clave si es vigente; `None` si falta, está mal formada, es desconocida o
    fue revocada. No distingue entre esos casos hacia afuera."""
    if not presentada or presentada.count(".") != 1:
        return None
    identificador, secreto = presentada.split(".")
    fila = session.scalar(select(ClaveApi).where(ClaveApi.identificador == identificador))
    esperada = fila.huella_secreto if fila is not None else _huella("relleno")
    coincide = hmac.compare_digest(esperada, _huella(secreto))
    if fila is None or fila.revocada or not coincide:
        return None
    if fila.ultimo_uso is None or ahora - fila.ultimo_uso >= RENOVACION_MINIMA:
        fila.ultimo_uso = ahora
        session.commit()
    return fila


def revocar(session: Session, clave_id: int, actor: str, ahora: datetime) -> None:
    fila = session.get(ClaveApi, clave_id)
    if fila is None:
        raise LookupError("No hay una clave de API con ese número.")
    fila.revocada = True
    eventos.registrar(session, "clave de api", ahora, detalle=f"revocada {fila.identificador}")
    session.commit()


def etiqueta(fila: ClaveApi) -> str:
    """Lo que la API pone como `usuario` de lo que cree: `api:<identificador>` (S3 §6.2)."""
    return f"api:{fila.identificador}"
```
**`ui/paginas/administracion.py`**
```python
"""Administración de la instalación (UC-21; spec S3 §5.7, §7 y §10; RF-80, RF-84, RF-88).

Cinco pestañas: Cuentas, Empresa y clave de firma, Empresas registradas, Claves de API y Accesos.
Solo el rol *administrador de la instalación* llega aquí (`exigir` es lo primero de `render()`);
lo que toca un secreto (clave de firma, claves de API) exige además el propio equipo
(`exigir_local`, S3 §5.6): el mensaje es el de 21j. Todo nombre que viene de la base pasa por
`texto_seguro`; ninguna contraseña ni clave privada se pinta, se registra ni se guarda en la
sesión de Streamlit. La clave de API y la contraseña temporal se muestran **una vez**.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st
from sqlalchemy.orm import Session

from seguridad import claves_api, cuentas, empresas, eventos, firma
from seguridad.modelo import Usuario
from seguridad.permisos import Accion, Rol, Sensible, aviso_de_roles
from ui import sesion as ui_sesion
from ui.texto_seguro import texto_seguro

TITULO_PESTANAS = ("Cuentas", "Empresa y clave de firma", "Empresas registradas",
                   "Claves de API", "Accesos")
ROLES_ELEGIBLES = tuple(rol.value for rol in Rol)


def _ahora() -> datetime:
    return ui_sesion.ahora()


def _responsable(bd: Session, actor: ui_sesion.SesionActiva) -> Usuario:
    usuario = bd.get(Usuario, actor.usuario_id)
    if usuario is None:  # la sesión de desarrollo (acceso apagado) no tiene cuenta
        st.error("Con el acceso apagado no hay cuenta de administrador que firme esta acción.")
        st.stop()
    return usuario


def _intentar(accion, exito: str) -> bool:
    """Corre `accion()`; el mensaje de un error esperado se muestra tal cual, sin traza."""
    try:
        accion()
    except (cuentas.ErrorDeAcceso, cuentas.ContrasenaInvalida, empresas.ClaveError,
            PermissionError, ValueError) as error:
        st.error(texto_seguro(str(error)))
        return False
    st.success(exito)
    return True


# --- cuentas -----------------------------------------------------------------------------------


def _pestana_cuentas(bd: Session, actor: Usuario) -> None:
    filas = bd.query(Usuario).order_by(Usuario.login).all()
    st.dataframe(
        [{"Usuario": texto_seguro(u.login), "Nombre": texto_seguro(u.nombre),
          "Roles": u.roles, "Activa": "sí" if u.activo else "no"} for u in filas],
        hide_index=True,
    )
    with st.form("adm_crear_cuenta"):
        st.subheader("Crear una cuenta")
        login = st.text_input("Usuario", key="adm_login")
        nombre = st.text_input("Nombre", key="adm_nombre")
        roles = st.multiselect("Roles", ROLES_ELEGIBLES, key="adm_roles")
        temporal = st.text_input("Contraseña temporal (10 a 128 caracteres)", type="password",
                                 key="adm_temporal")
        crear = st.form_submit_button("Crear", type="primary", key="adm_crear_enviar")
    if crear:
        aviso = aviso_de_roles(roles)
        if _intentar(lambda: cuentas.crear_usuario(bd, actor, login, nombre, roles, temporal,
                                                   _ahora()), "Cuenta creada."):
            st.info("La persona deberá cambiar la contraseña al entrar.")
            if aviso:
                st.warning(aviso)
    if not filas:
        return
    st.subheader("Cambiar una cuenta")
    por_id = {u.id: u for u in filas}  # se eligen ids: un objeto de otro ciclo ya no sirve
    elegida = por_id[st.selectbox("Cuenta", list(por_id), key="adm_cuenta",
                                  format_func=lambda i: por_id[i].login)]
    nuevos = st.multiselect("Roles de la cuenta", ROLES_ELEGIBLES,
                            default=[r for r in elegida.roles.split(",") if r],
                            key=f"adm_roles_de_{elegida.id}")
    columnas = st.columns(4)
    if columnas[0].button("Guardar roles", key="adm_guardar_roles"):
        _intentar(lambda: cuentas.cambiar_roles(bd, actor, elegida.id, nuevos, _ahora()),
                  "Roles cambiados; sus sesiones se cerraron.")
    if elegida.activo:
        if columnas[1].button("Desactivar", key="adm_desactivar"):
            _intentar(lambda: cuentas.desactivar(bd, actor, elegida.id, _ahora()),
                      "Cuenta desactivada; sus registros se conservan.")
    elif columnas[1].button("Reactivar", key="adm_reactivar"):
        _intentar(lambda: cuentas.reactivar(bd, actor, elegida.id, _ahora()), "Cuenta reactivada.")
    if columnas[2].button("Desbloquear", key="adm_desbloquear"):
        _intentar(lambda: cuentas.desbloquear(bd, actor, elegida.login, _ahora()),
                  "Cuenta desbloqueada.")
    temporal_nueva = st.text_input("Contraseña temporal nueva", type="password",
                                   key="adm_restablecer_clave")
    if columnas[3].button("Restablecer", key="adm_restablecer"):
        _intentar(lambda: cuentas.restablecer(bd, actor, elegida.id, temporal_nueva, _ahora()),
                  "Contraseña restablecida; sus sesiones se cerraron.")


# --- empresa y clave de firma ------------------------------------------------------------------


def _pestana_empresa(bd: Session, actor: Usuario) -> None:
    propia = empresas.empresa_propia(bd)
    with st.form("adm_empresa"):
        nombre = st.text_input("Nombre de la empresa", value=propia.nombre if propia else "",
                               key="adm_empresa_nombre")
        rif = st.text_input("RIF", value=propia.rif if propia else "", key="adm_empresa_rif")
        ciudad = st.text_input("Ciudad", value=propia.ciudad if propia else "",
                               key="adm_empresa_ciudad")
        guardar = st.form_submit_button("Guardar empresa", key="adm_empresa_enviar")
    if guardar:
        _intentar(lambda: empresas.guardar_empresa_propia(bd, nombre, rif, ciudad, actor.login,
                                                          _ahora()), "Empresa guardada.")
    propia = empresas.empresa_propia(bd)  # de nuevo: acaso se guardó en este mismo ciclo
    clave = empresas.clave_activa(bd)
    if clave is None:
        _generar_clave(bd, actor, propia is not None)
        return
    st.metric("Huella de la clave de firma", firma.huella_corta(clave.publica))
    st.caption("Léala por teléfono a quien reciba sus paquetes: es lo que comprueba su clave.")
    st.download_button("Descargar la clave pública",
                       empresas.exportar_clave_publica_propia(bd, _ahora()),
                       file_name="clave-publica.silice-clave", key="adm_bajar_publica")
    st.download_button("Descargar el respaldo cifrado de la clave",
                       empresas.exportar_respaldo_cifrado(bd),
                       file_name="respaldo-clave.silice-respaldo", key="adm_bajar_respaldo")
    with st.expander("Retirar o revocar la clave"):
        motivo = st.text_input("Motivo", key="adm_motivo_clave")
        contrasena = st.text_input("Contraseña de la clave (para el aviso de revocación)",
                                   type="password", key="adm_clave_revocar")
        if st.button("Retirar (se destruye la privada)", key="adm_retirar"):
            ui_sesion.exigir_local(Sensible.CLAVE_DE_FIRMA)
            _intentar(lambda: empresas.retirar_clave(bd, actor.login, _ahora(), motivo),
                      "Clave retirada.")
        if st.button("Revocar", key="adm_revocar"):
            ui_sesion.exigir_local(Sensible.CLAVE_DE_FIRMA)
            if motivo.strip() == "":
                st.error("Escriba el motivo de la revocación.")
            else:
                try:
                    aviso = empresas.revocar_clave_propia(
                        bd, actor.login, _ahora(), motivo, contrasena or None)
                except (empresas.ClaveError, ValueError) as error:
                    st.error(texto_seguro(str(error)))
                else:
                    st.success("Clave revocada: los paquetes firmados con ella dejan de verificar.")
                    if aviso:
                        st.download_button("Descargar el aviso de revocación", aviso,
                                           file_name="revocacion.silice-revocacion",
                                           key="adm_bajar_aviso")


def _generar_clave(bd: Session, actor: Usuario, hay_empresa: bool) -> None:
    if not hay_empresa:
        st.info("Primero guarde el nombre de la empresa.")
        return
    with st.form("adm_generar_clave"):
        st.subheader("Generar la clave de firma")
        uno = st.text_input("Contraseña de la clave (12 a 128 caracteres)", type="password",
                            key="adm_clave_uno")
        dos = st.text_input("Repítala", type="password", key="adm_clave_dos")
        generar = st.form_submit_button("Generar", type="primary", key="adm_generar_enviar")
    if not generar:
        return
    ui_sesion.exigir_local(Sensible.CLAVE_DE_FIRMA)
    if uno != dos:
        st.error("Las dos contraseñas no coinciden.")
        return
    if _intentar(lambda: empresas.generar_clave(bd, uno, actor.login, _ahora()),
                 "Clave generada. Guarde la contraseña: sin ella no se puede firmar."):
        st.rerun()


# --- empresas registradas ----------------------------------------------------------------------


def _pestana_registradas(bd: Session, actor: Usuario) -> None:
    from seguridad.modelo import EmpresaRegistrada

    filas = bd.query(EmpresaRegistrada).order_by(EmpresaRegistrada.id).all()
    st.dataframe(
        [{"Empresa": texto_seguro(f.empresa), "Huella": firma.huella_corta(f.publica),
          "Estado": f.estado, "Comprobada con": texto_seguro(f.comprobada_con),
          "Método": f.metodo} for f in filas],
        hide_index=True,
    )
    st.subheader("Registrar la clave de otra empresa")
    archivo = st.file_uploader("Archivo de la clave pública", key="adm_subir_clave")
    if archivo is None:
        return
    try:
        leida = firma.leer_clave_publica(archivo.getvalue())
    except ValueError as error:
        st.error(texto_seguro(str(error)))
        return
    st.write(f"Empresa declarada: **{texto_seguro(leida.nombre)}**")
    st.metric("Huella del archivo", firma.huella_corta(leida.publica))
    st.caption("Pida a la otra empresa que le lea su huella por teléfono y escríbala aquí.")
    with st.form("adm_registrar_ajena"):
        huella = st.text_input("Huella leída por teléfono", key="adm_huella_leida")
        con_quien = st.text_input("Comprobada con (persona)", key="adm_comprobada_con")
        metodo = st.selectbox("Cómo se comprobó", empresas.METODOS,
                              key="adm_metodo")
        registrar = st.form_submit_button("Registrar", type="primary",
                                          key="adm_registrar_enviar")
    if registrar:
        _intentar(lambda: empresas.registrar_empresa_ajena(
            bd, archivo.getvalue(), huella, con_quien, metodo, actor.login, _ahora()),
            "Empresa registrada.")


# --- claves de API -----------------------------------------------------------------------------


def _pestana_api(bd: Session, actor: Usuario) -> None:
    from seguridad.modelo import ClaveApi

    st.dataframe(
        [{"Clave": claves_api.etiqueta(f), "Nombre": texto_seguro(f.nombre),
          "Estado": "revocada" if f.revocada else "vigente"}
         for f in bd.query(ClaveApi).order_by(ClaveApi.id)],
        hide_index=True,
    )
    with st.form("adm_crear_clave_api"):
        nombre = st.text_input("Para qué es esta clave", key="adm_api_nombre")
        crear = st.form_submit_button("Crear clave de API", key="adm_api_enviar")
    if crear:
        ui_sesion.exigir_local(Sensible.CLAVE_DE_API)
        if nombre.strip() == "":
            st.error("Escriba para qué es la clave.")
        else:
            secreto, _ = claves_api.crear(bd, nombre.strip(), actor.login, _ahora())
            st.success("Clave creada. Cópiela ahora: no se vuelve a mostrar.")
            st.code(secreto)
    vigentes = [f for f in bd.query(ClaveApi).filter_by(revocada=False)]
    if vigentes:
        por_id = {f.id: f for f in vigentes}
        elegida = por_id[st.selectbox("Revocar", list(por_id), key="adm_api_revocar",
                                      format_func=lambda i: claves_api.etiqueta(por_id[i]))]
        if st.button("Revocar la clave", key="adm_api_boton_revocar"):
            ui_sesion.exigir_local(Sensible.CLAVE_DE_API)
            claves_api.revocar(bd, elegida.id, actor.login, _ahora())
            st.success("Clave revocada.")


# --- accesos -----------------------------------------------------------------------------------


def _pestana_accesos(bd: Session) -> None:
    st.dataframe(
        [{"Fecha": e.fecha_hora.isoformat(sep=" "), "Evento": e.tipo,
          "Usuario": texto_seguro(e.login_intentado), "IP": e.ip_cliente,
          "Detalle": texto_seguro(e.detalle)} for e in eventos.ultimos(bd, 200)],
        hide_index=True,
    )


def render() -> None:
    sesion = ui_sesion.exigir(Accion.ADMINISTRAR_CUENTAS)
    with ui_sesion.instalacion() as bd:
        actor = _responsable(bd, sesion)
        pestanas = st.tabs(TITULO_PESTANAS)
        with pestanas[0]:
            _pestana_cuentas(bd, actor)
        with pestanas[1]:
            ui_sesion.exigir(Accion.ADMINISTRAR_EMPRESA)
            _pestana_empresa(bd, actor)
        with pestanas[2]:
            _pestana_registradas(bd, actor)
        with pestanas[3]:
            ui_sesion.exigir(Accion.ADMINISTRAR_RED_Y_API)
            _pestana_api(bd, actor)
        with pestanas[4]:
            _pestana_accesos(bd)
```
**`scripts/restablecer_administrador.py`**
```python
"""Devuelve el acceso de un administrador que perdió su contraseña o quedó bloqueado (S3 §5.4).

Exige **acceso al equipo**: corre en la máquina donde está instalado Sílice, con Sílice detenido o
no. Emite un código de instalación nuevo de un solo uso (20 caracteres base32, 100 bits) en
`<datos>/codigo_instalacion.txt` y en la consola, y **cierra las sesiones de los
administradores**. Con ese código, la pantalla de acceso deja crear de nuevo una cuenta de
administrador (o devolverle el acceso a la que existe) aunque ya haya usuarios; el código se
borra al usarse. Quien lo corre queda en `evento_acceso` (tipo `codigo de instalacion`, motivo
`restablecimiento`).

    uv run python scripts/restablecer_administrador.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from operacion.config import carpeta_datos  # noqa: E402
from operacion.instalacion import cerrar_motores, sesion_de_instalacion  # noqa: E402
from seguridad import cuentas  # noqa: E402


def restablecer(ahora: datetime | None = None) -> tuple[str, Path]:
    """`(código, archivo)`: emite el código de restablecimiento y cierra las sesiones de los
    administradores de la instalación de `SILICE_INSTALACION` / la carpeta de datos."""
    carpeta = carpeta_datos()
    with sesion_de_instalacion() as bd:
        codigo = cuentas.emitir_codigo_de_restablecimiento(bd, carpeta, ahora or datetime.now())
    return codigo, carpeta / cuentas.NOMBRE_ARCHIVO_CODIGO


def main(argv: list[str] | None = None) -> int:
    try:
        codigo, archivo = restablecer()
    finally:
        cerrar_motores()
    print("Código de instalación nuevo (de un solo uso):")
    print(f"  {cuentas.formato_codigo(codigo)}")
    print(f"También está en {archivo}. Las sesiones de los administradores quedaron cerradas.")
    print("Escríbalo en la pantalla de acceso de Sílice para crear o recuperar la cuenta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```
  Fila de `scripts/README.md`:
```markdown
| `restablecer_administrador.py` | emite un código de instalación nuevo y cierra las sesiones de
↳ los administradores (exige el equipo) | 0.8.0 |
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_claves_api_y_red.py tests/unit/test_ui_administracion.py
tests/integration/test_restablecer_administrador.py tests/unit/test_ui_app.py
tests/unit/test_scripts_documentados.py tests/unit/test_ui_marco.py -v -W error` → verde.
- [ ] **Paso 5: Commit**
```bash
git add seguridad/claves_api.py ui/paginas/administracion.py scripts/restablecer_administrador.py \
  scripts/README.md ui/app.py
git commit -m "feat(ui): administracion de la instalacion y restablecimiento del administrador" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 18: Llamadores: el `usuario` de la sesión en todo lo que guarda y el sellado al abrir

**Rama:** `inc/080-s3-3-paquete`   **Rol:** sf-ingeniero-interfaz (pantallas), sf-ingeniero-pruebas
**Archivos:**
- Modificar: `ui/hoja.py:1586-1600,1896`, `ui/paginas/hoja.py` (responsable en 4 sitios, cadena en
  la pestaña Trazabilidad, anexos por omisión), `ui/paginas/actualizacion.py:325-335`,
  `ui/paginas/inicio.py:73-80`, `ui/caso.py:64,116-135`, `api/dependencias.py:22-25`,
  `api/rutas/presupuestos.py:30,172-180,224,338`, `scripts/seed_of001.py:55-60`,
  `tests/fixtures/hoja_en_base.py:21-110`, `tests/unit/test_ui_hoja.py:291`
- Modificar (S1 y S2, sin código en el sandbox): toda pantalla de `ui/paginas/` que agregaron
  con un cuadro «Responsable» propio
- Crear (pruebas): `tests/unit/test_responsables.py`, `tests/unit/test_ui_hoja_responsable.py`,
  `tests/unit/test_ui_sellado_al_abrir.py`

**Interfaces:**
- Consume: `ui.sesion.{responsable_de_la_hoja, responsable_actual, caja_de_responsable}` (tarea 6),
  `ui.entrega.{con_anexos_de_cadena, anexos_de_cadena, estado_de_la_cadena}` (tarea 16),
  `core.budget.cadena.{sellar_historial, verificar_cadena}` (tarea 8),
  `core.catalog.abrir_sesion_de_escritura` (tarea 9), `guardar_presupuesto(..., usuario=...)`.
- Produce:
  - `ui.hoja.RESPONSABLE_POR_OMISION = "sistema"`: el ÚNICO literal con ese texto en `ui/`.
  - `ui.caso.CLAVE_SELLADO` y `ui.caso.sellar_al_abrir(ruta, usuario) -> tuple[str, ...]`.
  - `api.dependencias.USUARIO_SIN_CLAVE = "api (sin clave)"`: quien firma lo que crean las rutas
    antiguas, que S3 no protege con clave (S5 decide).
  - `tests.fixtures.hoja_en_base.USUARIO_DE_LA_PLANTILLA` y su uso en `plantilla_of001` y
    `plantilla_ti001`.

**RF-82.** El responsable de lo que se guarda es el **usuario de la sesión**, no una caja de texto.
Con el acceso encendido no hay cuadro «Responsable»: la pantalla dice «Responsable: Ana Pérez» y el
valor escrito a mano por otra vía no cambia nada. Con el acceso apagado (transición) el cuadro de
siempre sigue. **RF-83.** Todo camino que crea versiones pasa por el embudo con `usuario`; la hoja
usa una sesión cuyo proveedor de anexos cubre el espacio. **Sellado retroactivo (RS3-5).** La
primera vez que se abre un caso con S3, sus versiones anteriores se sellan una vez, a nombre de
quien lo abre y con `tipo = "retroactivo"`; la pantalla de Inicio lo dice. Las pantallas que S1 y
S2 agregaron con su propio cuadro «Responsable» (conversión de moneda, reajuste, control de obra)
pasan a `ui.sesion.caja_de_responsable(rotulo, key=...)`; `test_responsables` las encuentra por
AST y falla mientras alguna conserve su `st.text_input("Responsable...")`, y su lista de
`COBERTURA` exige una prueba por cada tabla con columna `responsable` (las de S1 y S2 se suman a
`_CAJA`).

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_responsables.py`**
```python
"""RF-82: el responsable es el usuario de la sesión, en toda columna `responsable` (S3 §3.2, §13.2).

Tres vigilancias: (1) la lista de toda columna `responsable` de los metadatos, cada una con la
prueba que dice que la escribe el usuario de la sesión (una columna nueva sin dueño hace fallar la
lista); (2) ninguna pantalla pide «Responsable» con un cuadro propio; (3) el literal `"sistema"`
aparece una sola vez en `ui/`."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from migraciones.metadatos import METADATAS_CASO, METADATAS_INSTALACION

RAIZ = Path(__file__).resolve().parents[2]

#: tabla -> «archivo::prueba» que demuestra que la escribe el usuario de la sesión. Las tablas de
#: S1 y S2 entran en cuanto existen en los metadatos; su prueba la agrega la tarea que cablea su
#: pantalla (`ui.sesion.caja_de_responsable`), siguiendo el patrón de `test_ui_hoja_responsable`.
_HOJA = "tests/unit/test_ui_hoja_responsable.py::test_guardar_registra_al_usuario"
_CAJA = "tests/unit/test_responsables.py::test_las_pantallas_de_s1_y_s2_usan_la_caja"
COBERTURA = {
    "registro_cambio": _HOJA,
    **dict.fromkeys(
        ("importacion_indice", "moneda_proyecto", "clausula_reajuste", "estudio_reajuste",
         "linea_base_control", "valuacion", "anulacion_valuacion", "costo_real",
         "decision_recuperacion"),
        _CAJA,
    ),
}


def _tablas_con_responsable() -> set[str]:
    metadatas = (*METADATAS_CASO, *METADATAS_INSTALACION)
    return {
        tabla.name for metadata in metadatas for tabla in metadata.tables.values()
        if "responsable" in tabla.c
    }


def test_toda_columna_responsable_tiene_su_prueba() -> None:
    sin_dueno = sorted(_tablas_con_responsable() - set(COBERTURA))
    assert sin_dueno == [], f"columna `responsable` sin prueba en COBERTURA: {sin_dueno}"


def test_las_pruebas_de_la_lista_existen() -> None:
    for tabla in _tablas_con_responsable():
        archivo, _, prueba = COBERTURA[tabla].partition("::")
        texto = (RAIZ / archivo).read_text(encoding="utf-8")
        assert f"def {prueba}(" in texto, f"{tabla}: no existe {COBERTURA[tabla]}"


def _llamadas_a_text_input(archivo: Path):
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "text_input" and nodo.args
                and isinstance(nodo.args[0], ast.Constant) and isinstance(nodo.args[0].value, str)):
            yield nodo


def test_las_pantallas_de_s1_y_s2_usan_la_caja() -> None:
    """Ninguna pantalla de `ui/` pide «Responsable» con su propio `text_input`: todas pasan por
    `ui.sesion.caja_de_responsable` (que con el acceso encendido no es un cuadro)."""
    propios = sorted(
        f"{archivo.relative_to(RAIZ).as_posix()}:{nodo.lineno}"
        for archivo in (RAIZ / "ui").rglob("*.py")
        if archivo.name != "sesion.py"
        for nodo in _llamadas_a_text_input(archivo)
        if nodo.args[0].value.strip().lower().startswith("responsable")
    )
    assert propios == []


def test_el_literal_sistema_aparece_una_sola_vez_en_ui() -> None:
    donde = sorted(
        f"{archivo.relative_to(RAIZ).as_posix()}:{nodo.lineno}"
        for archivo in (RAIZ / "ui").rglob("*.py")
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8")))
        if isinstance(nodo, ast.Constant) and nodo.value == "sistema"
    )
    assert donde == ["ui/hoja.py:" + donde[0].split(":")[1]] and len(donde) == 1


def test_la_vigilancia_de_cuadros_propios_ve_el_cuadro(tmp_path: Path) -> None:
    archivo = tmp_path / "x.py"
    archivo.write_text('st.text_input("Responsable ")\nst.text_input("Fuente")\n', encoding="utf-8")
    [nodo] = [n for n in _llamadas_a_text_input(archivo) if n.args[0].value.startswith("Resp")]
    assert nodo.lineno == 1


@pytest.mark.parametrize("tabla", sorted(COBERTURA))
def test_la_lista_no_nombra_tablas_que_no_son_de_responsable(tabla: str) -> None:
    """Una entrada de COBERTURA es una tabla de S1/S2/S3 con `responsable` o aún no existe."""
    assert tabla in _tablas_con_responsable() or tabla not in {
        t for m in (*METADATAS_CASO, *METADATAS_INSTALACION) for t in m.tables
    }
```
**`tests/unit/test_ui_hoja_responsable.py`**
```python
"""RF-82 en la hoja: con el acceso encendido el responsable es el usuario de la sesión y no hay
cuadro «Responsable» (S3 §3.2, §5.7). Con el acceso apagado (transición, RP8-4) el cuadro sigue."""

from __future__ import annotations

import importlib
import shutil
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from core import models
from core.catalog import abrir_sesion, crear_motor
from tests.fixtures.hoja_en_base import NOMBRE_OF001, plantilla_of001
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import sesion as ui_sesion
from ui.paginas.hoja import CLAVE_FUENTE, CLAVE_PESTANA, CLAVE_PROYECTO, CLAVE_RESPONSABLE

SCRIPT = "from ui.paginas.hoja import render\nrender()\n"


@pytest.fixture(scope="module")
def _plantilla(tmp_path_factory) -> Path:
    return plantilla_of001(tmp_path_factory.mktemp("resp") / "of001.db")


@pytest.fixture
def base_of(_plantilla, tmp_path, monkeypatch) -> Path:
    copia = tmp_path / "of001.db"
    shutil.copy(_plantilla, copia)
    importlib.import_module("ui.caso")
    monkeypatch.setattr("ui.caso.RUTA_BASE_POR_DEFECTO", str(copia))
    return copia


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


def _abrir(base: Path, ficha: str | None = None) -> AppTest:
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state[CLAVE_PROYECTO] = NOMBRE_OF001
    at.session_state[CLAVE_PESTANA] = "Parámetros"
    if ficha:
        con_ficha(at, ficha)
    return at.run()


def _responsables(base: Path) -> list[str]:
    motor = crear_motor(f"sqlite:///{base.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            return list(sesion.scalars(select(models.RegistroCambio.responsable)))
    finally:
        motor.dispose()


def _guardar(at: AppTest) -> AppTest:
    campo = next(t for t in at.text_input if t.key and "param_administracion" in t.key)
    campo.set_value("0.20").run()
    at.text_input(key=CLAVE_FUENTE).set_value("memoria rev. D").run()
    next(b for b in at.button if b.label == "Guardar version").click().run()
    return at


def test_guardar_registra_al_usuario(monkeypatch, base_of, tmp_path) -> None:
    ficha = preparar(monkeypatch, tmp_path, "arma", login="luis")
    at = _abrir(base_of, ficha)
    assert not at.exception, [e.value for e in at.exception]
    assert CLAVE_RESPONSABLE not in [t.key for t in at.text_input]  # no hay cuadro
    assert any("Responsable: Luis" in c.value for c in at.caption)
    _guardar(at)
    assert not at.exception, [e.value for e in at.exception]
    assert _responsables(base_of) == ["Luis <luis>"]


def test_lo_que_alguien_escriba_a_mano_no_cambia_al_responsable(monkeypatch, base_of, tmp_path):
    ficha = preparar(monkeypatch, tmp_path, "arma", login="luis")
    at = _abrir(base_of, ficha)
    at.session_state[CLAVE_RESPONSABLE] = "Otra Persona <otra>"  # el cuadro ya no existe
    _guardar(at)
    assert _responsables(base_of) == ["Luis <luis>"]


def test_con_el_acceso_apagado_el_cuadro_de_siempre_sigue(monkeypatch, base_of) -> None:
    monkeypatch.setenv("SILICE_ACCESO", "0")
    at = _abrir(base_of)
    assert CLAVE_RESPONSABLE in [t.key for t in at.text_input]
    assert date.today().year >= 2026
```
**`tests/unit/test_ui_sellado_al_abrir.py`**
```python
"""El sellado retroactivo al abrir un caso con S3 (RS3-5; spec S3 §6.5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest

from core import models
from core.budget import cadena
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from tests.fixtures.canonico_minimo import guardar_otra, sembrar_minimo
from ui import caso
from ui import sesion as ui_sesion


@pytest.fixture
def caso_antiguo(tmp_path: Path, monkeypatch) -> Path:
    """Un caso con dos versiones guardadas ANTES de S3: sin eslabones."""
    ruta = tmp_path / "antiguo.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        proyecto, v1, lista = sembrar_minimo(sesion)
        sesion.commit()
        guardar_otra(sesion, proyecto, lista, "002", "30", version_origen=v1, motivo="edicion")
        sesion.commit()
        sesion.execute(text("DELETE FROM eslabon_version"))
        sesion.commit()
    motor.dispose()
    monkeypatch.setenv("SILICE_CASO", str(ruta))
    return ruta


def _cadena_integra(ruta: Path) -> tuple[bool, str | None]:
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            proyecto = sesion.query(models.Proyecto).one()
            return (cadena.verificar_cadena(sesion, proyecto).integra,
                    cadena.texto_retroactivo(sesion, proyecto))
    finally:
        motor.dispose()


def test_abrir_un_caso_antiguo_sella_sus_versiones_una_vez_y_a_nombre_de_quien_abre(
    caso_antiguo,
) -> None:
    assert not _cadena_integra(caso_antiguo)[0]
    selladas = caso.sellar_al_abrir(caso_antiguo, "Ana <ana>")
    assert selladas == ("MIN-001/001", "MIN-001/002")
    integra, declaracion = _cadena_integra(caso_antiguo)
    assert integra and declaracion.startswith("Versiones 001 a 002 selladas")
    assert caso.sellar_al_abrir(caso_antiguo, "Ana <ana>") == ()  # una sola vez


def _inicio() -> None:
    from ui.paginas import inicio

    inicio._preparar_abierto()


def test_el_inicio_sella_al_entrar_lo_dice_y_no_repite_en_la_misma_sesion(
    caso_antiguo, monkeypatch
) -> None:
    monkeypatch.setenv("SILICE_ACCESO", "0")
    at = AppTest.from_function(_inicio, default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Se sellaron 2 versiones" in i.value for i in at.info)
    assert at.session_state[caso.CLAVE_SELLADO] == str(caso_antiguo)
    assert not at.run().info  # el segundo ciclo de la misma sesión ya no lo repite
    assert _cadena_integra(caso_antiguo)[0]
    ui_sesion.limpiar_motores()
```
  La fixture de las plantillas guarda a nombre de alguien (fuera de pytest no hay usuario por
  omisión) y la pestaña Trazabilidad dice que la cadena está íntegra:
```diff
--- a/tests/fixtures/hoja_en_base.py
+++ b/tests/fixtures/hoja_en_base.py
@@ -22,8 +22,12 @@
 from tests.fixtures.espacio_of001 import espacio_of001
 from ui import hoja
+from ui.entrega import con_anexos_de_cadena
 
 NOMBRE_OF001 = "OF-001: oficina con baño, cocineta y puestos (caso de prueba)"
 NOMBRE_TI001 = "TI-001: telecomunicaciones (caso de prueba)"
 CONDICIONES = "caso de prueba de la hoja: rendimiento supuesto"
+#: Quien guarda la versión `001` de las plantillas (RF-83: toda versión se confirma a nombre de
+#: alguien; `scripts/generar_base_prueba.py` las corre fuera de pytest, sin el usuario de prueba).
+USUARIO_DE_LA_PLANTILLA = "Plantilla <plantilla>"
 
 
@@ -44,4 +48,5 @@
     try:
         with abrir_sesion(motor) as sesion:
+            con_anexos_de_cadena(sesion)  # la cadena cubre el espacio que se guarda abajo
             lista = _lista(sesion, "Lista MaPreX jul-2026 (OF-001)", "USD", caso_of001.FECHA)
             catalogo = Catalogo(sesion)
@@ -71,4 +76,5 @@
                 pendientes=resultado.elaboracion.pendientes,
                 plan=resultado.plan,
+                usuario=USUARIO_DE_LA_PLANTILLA,
             )
             guardar_espacio(sesion, version.id, espacio)
@@ -102,4 +108,5 @@
                 pendientes=resultado.pendientes,
                 plan=caso_ti001.PLAN,
+                usuario=USUARIO_DE_LA_PLANTILLA,
             )
             sesion.commit()
```
```diff
--- a/tests/unit/test_ui_hoja.py
+++ b/tests/unit/test_ui_hoja.py
@@ -291,4 +291,13 @@
 
 
+def test_la_pestana_trazabilidad_dice_que_la_cadena_esta_integra(monkeypatch, base_of):
+    """RF-83: la cadena de huellas se recalcula desde la base y se dice, con el espacio de la
+    versión dentro de lo que cubre (S3 §6.2)."""
+    at = _abrir_of(monkeypatch, base_of, **{CLAVE_PESTANA: "Trazabilidad"})
+
+    assert [s.value for s in at.success] == ["Cadena íntegra: 1 versiones"]
+    assert [e.value for e in at.error] == []
+
+
 # --- parametros: campos de texto -----
 
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_responsables.py tests/unit/test_ui_hoja_responsable.py
tests/unit/test_ui_sellado_al_abrir.py tests/unit/test_ui_hoja.py -v -W error`
Esperado: `test_responsables` FAIL (`test_las_pantallas_de_s1_y_s2_usan_la_caja` lista los
`st.text_input("Responsable...")` de la hoja; `test_el_literal_sistema_aparece_una_sola_vez_en_ui`
cuenta más de una vez), `test_ui_hoja_responsable` FAIL (todavía hay cuadro «Responsable»),
`test_ui_sellado_al_abrir` FAIL con `AttributeError: module 'ui.caso' has no attribute
'CLAVE_SELLADO'`.
```bash
git add tests/unit/test_responsables.py tests/unit/test_ui_hoja_responsable.py \
  tests/unit/test_ui_sellado_al_abrir.py tests/fixtures/hoja_en_base.py tests/unit/test_ui_hoja.py
git commit -m "test(ui): responsable = usuario de la sesion y sellado al abrir, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
  La hoja (el literal único, y el `usuario` que recibe el embudo al guardar la primera versión):
```diff
--- a/ui/hoja.py
+++ b/ui/hoja.py
@@ -81,4 +81,5 @@
     fusionar,
 )
+from adapters.espacio.planos.geometria_plano import reglas_plano
 from adapters.espacio.reglas import CantidadEscrita, reglas_espacio
 from core import models
@@ -712,5 +713,5 @@
         moneda=moneda,
         plan=plan_final,
-        reglas=(*REGLAS, *reglas_espacio(espacio, escritas)),
+        reglas=(*REGLAS, *reglas_espacio(espacio, escritas), *reglas_plano(espacio)),
     )
     if usado:
@@ -1586,4 +1587,10 @@
 
 
+#: Quién responde por lo que la hoja registra al abrir una versión sin que nadie lo diga. Solo con
+#: el acceso apagado (transición, RP8-4): con el acceso encendido manda la sesión (RF-82). Es el
+#: ÚNICO lugar de `ui/` con este literal; lo vigila `tests/unit/test_responsables.py`.
+RESPONSABLE_POR_OMISION = "sistema"
+
+
 def abrir_version(
     sesion: Session,
@@ -1592,5 +1599,5 @@
     codigo: str,
     *,
-    responsable: str = "sistema",
+    responsable: str = RESPONSABLE_POR_OMISION,
     ahora: datetime | None = None,
 ) -> VersionAbierta:
@@ -1632,5 +1639,5 @@
             codigo,
             catalogo,
-            reglas=(*REGLAS, *reglas_espacio(espacio, cantidades)),
+            reglas=(*REGLAS, *reglas_espacio(espacio, cantidades), *reglas_plano(espacio)),
         )
     except (ValueError, CatalogoIncompleto, KeyError) as error:
@@ -1890,4 +1897,5 @@
             pendientes=elaboracion.pendientes,
             plan=resultado.plan,
+            usuario=responsable,
         )
         sesion.add(
```
  La pantalla de la hoja: el responsable sale de la sesión en cuatro sitios, la sesión de base de
  la pantalla cubre el espacio en la cadena, y la pestaña Trazabilidad dice si la cadena está
  íntegra. Importaciones nuevas: `from ui import caso, contraste, entrega, hoja`.
```diff
--- a/ui/paginas/hoja.py
+++ b/ui/paginas/hoja.py
@@ -139,5 +149,5 @@
     try:
         with abrir_sesion(motor) as sesion:
-            yield sesion
+            yield entrega.con_anexos_de_cadena(sesion)
     finally:
         motor.dispose()
@@ -243,5 +253,8 @@
         try:
             with _sesion() as sesion:
-                abierta = hoja.abrir_version(sesion, Catalogo(sesion), proyecto, codigo)
+                abierta = hoja.abrir_version(
+                    sesion, Catalogo(sesion), proyecto, codigo,
+                    responsable=ui_sesion.responsable_de_la_hoja(hoja.RESPONSABLE_POR_OMISION),
+                )
         except hoja.HojaInvalida as error:
             st.error(str(error))
@@ -394,5 +407,5 @@
                 borrador,
                 fuente=st.session_state.get(CLAVE_FUENTE, ""),
-                responsable=st.session_state.get(CLAVE_RESPONSABLE, ""),
+                responsable=_responsable(),
             )
     except hoja.HojaInvalida as error:
@@ -435,5 +448,5 @@
                 borrador,
                 fuente=st.session_state.get(CLAVE_FUENTE, ""),
-                responsable=st.session_state.get(CLAVE_RESPONSABLE, ""),
+                responsable=_responsable(),
             )
     except hoja.HojaInvalida as error:
@@ -517,5 +530,5 @@
             key=CLAVE_FUENTE,
         )
-        responsable.text_input("Responsable", key=CLAVE_RESPONSABLE)
+        ui_sesion.caja_de_responsable("Responsable", key=CLAVE_RESPONSABLE, contenedor=responsable)
         if abierta is not None:
             motivo = hoja.motivo_para_no_guardar(
@@ -523,5 +536,5 @@
                 _borrador(),
                 st.session_state.get(CLAVE_FUENTE, ""),
-                st.session_state.get(CLAVE_RESPONSABLE, ""),
+                _responsable(),
             )
         elif proyecto_nuevo is not None:
@@ -529,5 +542,5 @@
                 _borrador(),
                 st.session_state.get(CLAVE_FUENTE, ""),
-                st.session_state.get(CLAVE_RESPONSABLE, ""),
+                _responsable(),
             )
         else:
@@ -638,4 +651,5 @@
 def _pestana_espacio() -> None:
     _importar_plano()
+    _contrastar_plano()
     st.caption(_AYUDA_ESPACIO)
     base = hoja.filas_desde_espacio(_partida().espacio)
@@ -1305,5 +1393,5 @@
             )
             motivo = st.text_input("Por que se retira")
-            quien = st.text_input("Responsable ")
+            quien = ui_sesion.caja_de_responsable("Responsable ")
             retirar = st.form_submit_button("Retirar cotizacion")
         if retirar:
@@ -1403,5 +1491,7 @@
                 codigo,
                 fuente=st.session_state.get("hoja_restaurar_fuente", ""),
-                responsable=st.session_state.get("hoja_restaurar_responsable", ""),
+                responsable=ui_sesion.responsable_de_la_hoja(
+                    st.session_state.get("hoja_restaurar_responsable", "")
+                ),
             )
     except (hoja.HojaInvalida, SQLAlchemyError) as error:
@@ -1420,4 +1510,9 @@
         historial = hoja.historial_de_versiones(sesion, abierta.proyecto)
         registros = hoja.registros_de_version(sesion, abierta.proyecto, abierta.codigo)
+        cadena = entrega.estado_de_la_cadena(sesion, abierta.proyecto)
+    if cadena is not None:  # RF-83: la cadena de huellas, recalculada, y su sellado retroactivo
+        (st.success if cadena.integra else st.error)(texto_seguro(cadena.mensaje))
+        if cadena.declaracion:
+            st.caption(texto_seguro(cadena.declaracion))
     st.subheader("Versiones del proyecto")
     st.dataframe(
@@ -1464,5 +1559,5 @@
         elegida = st.selectbox("Version a restaurar", [v.codigo for v in historial])
         st.text_input("Fuente (por que se restaura)", key="hoja_restaurar_fuente")
-        st.text_input("Responsable", key="hoja_restaurar_responsable")
+        ui_sesion.caja_de_responsable("Responsable", key="hoja_restaurar_responsable")
         enviar = st.form_submit_button("Restaurar")
     if enviar:
@@ -1484,4 +1579,5 @@
 def render() -> None:
     """La hoja del proyecto: version abierta, guardado y la pestana activa."""
+    ui_sesion.exigir(Accion.EDITAR_HOJA)
     _borrador()
     accion = _atender()
```
  La página «Actualizar precios» pasa el usuario (importación `from ui.sesion import
  responsable_actual`):
```python
        usuario=responsable_actual(),  # en la llamada a actualizar_precios(...)
```
  El sellado retroactivo al abrir el caso y su aviso en el Inicio:
```diff
--- a/ui/caso.py
+++ b/ui/caso.py
@@ -60,4 +62,5 @@
 CLAVE_PROYECTO = "silice_proyecto_abierto"
 CLAVE_ACCION = "silice_accion_pedida"
+CLAVE_SELLADO = "silice_sellado_de"  # el caso cuyo historial ya se selló en esta sesión
 #: Acciones que la barra superior le pide a la hoja del proyecto (`pedir_accion`).
 ACCION_PRECIOS = "precios"
@@ -111,4 +114,22 @@
     fijar_caso(ruta)
     return ruta
+
+
+def sellar_al_abrir(ruta: Path, usuario: str) -> tuple[str, ...]:
+    """RS3-5 (S3 §6.5): la primera vez que se abre un caso con S3, sus versiones anteriores se
+    sellan una vez, a nombre de quien lo abre, con `tipo = "retroactivo"`. Devuelve
+    `proyecto/codigo` de cada una; vacío si ya estaban selladas (casi siempre)."""
+    from core.budget.cadena import sellar_historial
+    from core.catalog import abrir_sesion_de_escritura, crear_motor
+    from ui.entrega import anexos_de_cadena
+
+    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
+    try:
+        with abrir_sesion_de_escritura(motor) as sesion:
+            selladas = sellar_historial(sesion, usuario, anexos_de=anexos_de_cadena)
+            sesion.commit()
+    finally:
+        motor.dispose()
+    return selladas
 
 
```
```diff
--- a/ui/paginas/inicio.py
+++ b/ui/paginas/inicio.py
@@ -73,5 +75,11 @@
     try:
         preparar_base(ruta)
-    except ErrorDeBase as error:
+        if st.session_state.get(caso.CLAVE_SELLADO) != str(ruta):  # una vez por caso y sesión
+            selladas = caso.sellar_al_abrir(ruta, ui_sesion.responsable_actual())
+            st.session_state[caso.CLAVE_SELLADO] = str(ruta)
+            if selladas:
+                st.info(f"Se sellaron {len(selladas)} versiones anteriores a la cadena de huellas "
+                        "(no hay garantía de lo que pasó antes de hoy).")
+    except (ErrorDeBase, ValueError, SQLAlchemyError) as error:
         st.error(str(error))
 
```
  La API firma lo que crean sus rutas antiguas y los scripts dejan su nombre:
```diff
--- a/api/dependencias.py
+++ b/api/dependencias.py
@@ -23,4 +23,6 @@
 VARIABLE_BASE = "APU_BASE"
 _PREFIJO_ARCHIVO = "sqlite:///"
+#: El `usuario` de lo que crean las rutas antiguas, que S3 no protege con clave (S5 decide).
+USUARIO_SIN_CLAVE = "api (sin clave)"
 _motor = None
 
```
```diff
--- a/api/rutas/presupuestos.py
+++ b/api/rutas/presupuestos.py
@@ -31,5 +31,5 @@
 
 from api.archivos import guardar_subida
-from api.dependencias import SesionDep
+from api.dependencias import USUARIO_SIN_CLAVE, SesionDep
 from api.esquemas import (
     ActualizacionPeticion,
@@ -178,4 +178,5 @@
         parametros=parametros,
         pendientes=resultado.pendientes,
+        usuario=USUARIO_SIN_CLAVE,
     )
     sesion.commit()
@@ -221,5 +222,5 @@
         comprobar_libro_legible(ruta)
         try:
-            resultado = importar_presupuesto(sesion, ruta, destino)
+            resultado = importar_presupuesto(sesion, ruta, destino, usuario=USUARIO_SIN_CLAVE)
         except ValueError:
             sesion.rollback()
@@ -342,4 +343,5 @@
         peticion.codigo_nuevo,
         detectar_atipicos=_detector_de_atipicos(),
+        usuario=USUARIO_SIN_CLAVE,
     )
     if comparativo.insumos_afectados == 0:
```
```diff
--- a/scripts/seed_of001.py
+++ b/scripts/seed_of001.py
@@ -56,5 +56,8 @@
     try:
         with abrir_sesion(motor) as sesion:
-            abierta = hoja.abrir_version(sesion, Catalogo(sesion), NOMBRE_OF001, CODIGO_VERSION)
+            abierta = hoja.abrir_version(
+                sesion, Catalogo(sesion), NOMBRE_OF001, CODIGO_VERSION,
+                responsable="script:seed_of001",
+            )
             presupuesto = abierta.guardada.presupuesto
             print(f"Base de datos: {ruta}")
```
- [ ] **Paso 4: Correrlas y ver el verde** (y TODA la suite: cambiaron los llamadores)
Run: `uv run pytest tests/unit/test_responsables.py tests/unit/test_ui_hoja_responsable.py
tests/unit/test_ui_sellado_al_abrir.py tests/unit/test_ui_hoja.py tests/unit/test_seed_of001.py -v
-W error` → verde. Run: `uv run pytest -q -W error -p no:cacheprovider` → verde, con la sesión de
pruebas SIN el usuario por omisión en `tests/unit/test_ui_hoja_responsable.py` y
`tests/unit/test_ui_sellado_al_abrir.py` (marcador `sin_usuario_por_omision` donde corresponda).
- [ ] **Paso 5: Commit**
```bash
git add ui/hoja.py ui/paginas/hoja.py ui/paginas/actualizacion.py ui/paginas/inicio.py ui/caso.py \
  api/dependencias.py api/rutas/presupuestos.py scripts/seed_of001.py
git commit -m "feat(ui): responsable = usuario de la sesion y sellado al abrir el caso" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS3-3 y foco de revisión de la fase

**Compuerta GS3-3** (se cruza al fusionar `inc/080-s3-3-paquete`, justo después de S3-2):
1. `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-3 --junit reporte-pruebas.xml`
   en OK, incluida `S3-M4` (la CI exige 80 % de `seguridad/` y `paquete/`).
2. CI verde en Linux y Windows. La cobertura de `seguridad/` y `paquete/` no baja de 80 %.
3. **El encargo de seguridad** aprueba (firma con dominios, huella corta, verificación que nunca usa
   la clave del paquete, límites del ZIP y del JSON, la privada destruida al retirar o revocar, la
   firma solo desde el propio equipo) y el de pruebas y calidad.
4. Recorrido a mano de Eugenio: generar la clave, entregar un paquete, verlo verificado en otra
   instalación (o con la misma y otro rol), y el restablecimiento del administrador.

**Foco de revisión de S3-3** (lo que el spec implica y ninguna prueba ejercita todavía):
1. **Un paquete refirmado con otra clave que dice ser la empresa registrada** debe salir
   «alterado»: `test_refirmado_con_otra_clave_que_dice_ser_la_empresa_registrada_es_alterado`.
2. **Una firma de aviso de revocación presentada como firma de paquete:**
   `test_la_firma_de_un_aviso_de_revocacion_no_vale_como_firma_de_paquete`.
3. **Una bomba de compresión o un tamaño que miente:** `test_una_bomba_de_compresion_se_rechaza_sin_
   extraerse` y `test_un_tamano_de_cabecera_que_miente_por_debajo_no_deja_pasar_mas_bytes`.
4. **Un anexo que ya no viene** (se borró una fila entre entregas): `test_una_entrada_de_un_anexo_
   que_ya_no_viene_se_avisa`.
5. **Una tabla de S1 o S2 con nombre mal escrito en `TABLAS_DE_*`** se omitiría en silencio: la
   tarea 24 corre una prueba contra las tablas reales de 0.6.0 y 0.7.0 que exige que cada nombre
   exista.

---

# S3-4 — Reauditoría, vista del revisor y API de auditorías (rama `inc/080-s3-4-revision`)

Sale de `origin/main` con S3-3 fusionada. Toca `auditoria/`, `ui/`, `api/`, `tests/` y `docs/`; no
toca `core/`. Al terminar, quien revisa abre un paquete (o el Excel de otra herramienta), ve su
estado de verificación, la reauditoría con las reglas de ESTA instalación, las diferencias contra la
entrega anterior y contra su propia lista, regenera el Excel y guarda un dictamen atado al archivo;
y otra herramienta puede pedir la misma reauditoría por `POST /v1/auditorias` con una clave de API.

### Tarea 19: Reauditoría en memoria y la vista de quien revisa (`auditoria/`, `ui/revision.py`)

**Rama:** `inc/080-s3-4-revision` (sale de `main` con S3-3 fusionada; PR a `main`)
**Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `auditoria/__init__.py`, `auditoria/reauditoria.py`, `auditoria/servicios.py`,
  `ui/revision.py`
- Prueba: `tests/unit/test_ui_revision.py`, `tests/integration/test_revision_recibir.py`,
  `tests/unit/test_auditoria_servicios.py`

**Interfaces:**
- Consume: `core.budget.canonico.{leer, contar_filas, json_canonico, DocumentoLeido}` (tarea 7),
  `core.budget.comparacion.{diferencia_entre_versiones, revalorar, filas_de}` (tarea 10),
  `core.budget.presupuesto.elaborar`, `core.budget.excel`, `core.budget.importacion`,
  `core.verification.REGLAS`, `adapters.espacio.reglas.reglas_espacio`,
  `adapters.espacio.planos.geometria_plano.reglas_plano` y `adapters.espacio.serie` (tarea 11),
  `paquete.{formato, modelo, verificar}` (tareas 14 y 15), `seguridad.json_estricto` (tarea 4),
  `seguridad.{empresas, firma}` (tarea 13) y, de S1, `core.catalog.{empresa, indices, moneda,
  origen}` y `core.verification.precios` (ver «Supuestos sobre 0.6.0 y 0.7.0»).
- Produce:
  - `auditoria.reauditoria`: `class ReferenciaDeMercado`
  - `auditoria.reauditoria`: `class Servicios`
  - `auditoria.reauditoria`: `def leer_documento(archivos: Mapping[str, bytes]) ->
      canonico.DocumentoLeido`
  - `auditoria.reauditoria`: `def leer_documento_json(datos: bytes) -> canonico.DocumentoLeido`
  - `auditoria.reauditoria`: `def instantanea_del_documento(doc: canonico.DocumentoLeido,
      servicios: Servicios, fecha_emision: date) -> InstantaneaPrecios`
  - `auditoria.reauditoria`: `class DiferenciaDeclarada`
  - `auditoria.reauditoria`: `class Reauditoria`
  - `auditoria.reauditoria`: `def reauditar(doc: canonico.DocumentoLeido, servicios: Servicios,
      fecha_evaluacion: date, *, espacio_json: bytes | None=None, control_json: bytes |
      None=None, tiempo_maximo: float=LIMITE_SEGUNDOS) -> Reauditoria`
  - `auditoria.servicios`: `def servicios_de_la_instalacion(session: Session, *, lado:
      str=LADO_POR_DEFECTO, reglas_de_control: ReglasDeControl | None=None) -> Servicios`
  - `ui.revision`: `def reauditar(v: Verificacion, servicios: Servicios, *, tiempo_maximo:
      float=LIMITE_SEGUNDOS) -> Reauditoria`
  - `ui.revision`: `def precios_de_lista(session: Session, lista: models.ListaPrecios) ->
      list[PrecioDeLista]`
  - `ui.revision`: `def contra_la_entrega_anterior(actual: canonico.DocumentoLeido, anterior:
      canonico.DocumentoLeido) -> Diferencia`
  - `ui.revision`: `def contra_la_base_del_revisor(doc: canonico.DocumentoLeido, precios:
      Sequence[PrecioDeLista]) -> tuple[Diferencia, Revaloracion]`
  - `ui.revision`: `def declaracion_retroactiva(cadena: Mapping[str, Any]) -> str | None`
  - `ui.revision`: `def login_de(responsable: str) -> str | None`
  - `ui.revision`: `def cambios_nuevos(cadena: Mapping[str, Any], huellas_previas:
      Sequence[str]) -> list[dict[str, str]]`
  - `ui.revision`: `def revisor_armo(v: Verificacion, *, login_revisor: str, empresa_propia:
      tuple[str | None, str | None]) -> list[str]`
  - `ui.revision`: `class Recibido`
  - `ui.revision`: `def recibir(datos: bytes, nombre: str, *, caso: Session, instalacion:
      Session, carpeta_paquetes: Path, revisor: str, ahora: datetime, mi_empresa: tuple[str |
      None, str | None]=(None, None)) -> Recibido`
  - `ui.revision`: `def dictaminar(caso: Session, recibido: Recibido, *, resultado: str, notas:
      str, revisor: str, ahora: datetime, armo: bool) -> int`
  - `ui.revision`: `class EntregaAnterior`
  - `ui.revision`: `def entrega_anterior(caso: Session, instalacion: Session, v: Verificacion)
      -> EntregaAnterior | None`
  - `ui.revision`: `def empresa_propia_para_revisar(instalacion: Session) -> tuple[str | None,
      str | None]`
  - `ui.revision`: `def tablas_de_revision(v: Verificacion, r: Reauditoria, diferencia:
      Diferencia | None, cambios: Sequence[dict]) -> tuple[TablaExportable, ...]`
  - `ui.revision`: `def excel_de_presupuesto(r: Reauditoria, *, extras:
      Sequence[TablaExportable]=()) -> bytes`
  - `ui.revision`: `def excel_de_revision(v: Verificacion, r: Reauditoria, diferencia:
      Diferencia | None, cambios: Sequence[dict]) -> bytes`
  - `ui.revision`: `def plantilla_uc05() -> bytes`
  - `ui.revision`: `def auditar_excel_externo(ruta: Path)`

**Por qué `auditoria/` y no `ui/`.** El spec ponía la reauditoría en `ui/revision.py`, pero la API
no puede importar `ui/` (RP8-6): el motor vive en `auditoria/` y lo comparten la vista y la ruta. La
reauditoría **recalcula cada precio unitario con el motor** desde las composiciones y los parámetros
del documento (no se confía en los precios ni en los totales escritos), corre `REGLAS` y las reglas
externas del contexto «reauditoría» (maestro §3.3): R8 a R10 y R15 con el anexo de espacio; R11 y
R12 con el `precio_origen` del documento, **a la fecha de emisión que se le da** (nunca el reloj),
contra la referencia MaPreX de quien revisa; R13 y R14 con el anexo de control **si hay servicio de
S2** (RP8-21); R16 no corre aquí. Se corta a los 60 segundos y lo dice. Separa los hallazgos que el
emisor **no declaró**, los que declaró y **ya no aparecen**, y los comunes. Todo es en memoria: lo
único que se guarda es el archivo recibido (`<datos>/paquetes/<sha256>.silice`), su registro
(`paq_recibido`) y el dictamen (`paq_dictamen`). **Aviso de P2 (RS3-4):** si quien revisa es quien
armó el paquete (su login coincide con el usuario del eslabón o del emisor, de la empresa propia),
la vista lo indica y el dictamen lo registra (`revisor_armo`). **Excel:** no viaja; se regenera del
JSON, y todo texto del paquete se escribe como texto con prefijo de comilla (`quotePrefix`), nunca
como fórmula; al leer un Excel externo se toma el valor y no la fórmula.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_ui_revision.py`**
```python
"""La vista de quien revisa, sin Streamlit: reauditoría, diferencias, quién cambió qué y Excel
(UC-23, RF-86, RF-87; spec S3 §9 y §13.2)."""

from __future__ import annotations

import copy
import threading
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from adapters.espacio.serie import espacio_a_objeto
from auditoria import reauditoria
from core.budget.canonico import json_canonico
from core.contracts.verificacion import Severidad
from paquete.formato import PaqueteRechazado
from paquete.verificar import EmpresaConocida, verificar
from seguridad import firma
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.espacio_of001 import espacio_of001
from tests.fixtures.paquetes import EMPRESA, paquete
from ui import revision
from ui.revision import ReferenciaDeMercado, Servicios

PAR = firma.generar_par()
RECIBIDO = datetime(2026, 11, 12, 10, 0)


def doc_json(**cambios) -> bytes:
    objeto = copy.deepcopy(EJEMPLO_V1)
    for ruta, valor in cambios.items():
        destino = objeto
        *camino, ultimo = ruta.split("__")
        for paso in camino:
            destino = destino[int(paso)] if paso.isdigit() else destino[paso]
        destino[int(ultimo) if ultimo.isdigit() else ultimo] = valor
    return json_canonico(objeto)


def verificado(presupuesto: bytes, **mas):
    datos = paquete(par=PAR, presupuesto=presupuesto, **mas)
    return verificar(
        datos, recibido_en=RECIBIDO,
        buscar_empresa=lambda h: EmpresaConocida(EMPRESA, PAR.publica, "activa"),
    )


def test_la_reauditoria_recalcula_los_precios_en_vez_de_creer_los_declarados() -> None:
    mentira = doc_json(renglones__0__precio_unitario="99.00", renglones__0__total="1980.00")
    r = revision.reauditar(verificado(mentira, anexos={}), Servicios())
    assert r.total_recalculado == Decimal("836.79750000")
    campos = {d.campo: d for d in r.diferencias}
    assert campos["precio_unitario"].declarado == Decimal("99.00")
    assert campos["precio_unitario"].recalculado == Decimal("41.83987500")
    assert campos["precio_unitario"].monto == (Decimal("99.00") - Decimal("41.83987500")) * 20
    assert campos["total"].monto == Decimal("1980.00") - Decimal("836.79750000")


def test_un_paquete_honesto_no_tiene_diferencias_de_precio() -> None:
    r = revision.reauditar(verificado(doc_json(), anexos={}), Servicios())
    assert r.diferencias == () and r.contextos == ("R1-R7", "R11-R12") and not r.no_termino


def test_los_hallazgos_se_separan_en_no_declarados_ya_no_y_comunes() -> None:
    declarado = {"regla": "R11", "severidad": 1, "descripcion": "algo viejo", "impacto": None,
                 "origen_ids": [], "valor_observado": None, "valor_esperado": None}
    r = revision.reauditar(verificado(doc_json(hallazgos=[declarado]), anexos={}), Servicios())
    assert [h.descripcion for h in r.ya_no] == ["algo viejo"]
    assert len(r.nuevos) == 1 and r.nuevos[0].regla == "R11" and r.comunes == ()


def test_r11_marca_el_precio_fuera_de_rango_contra_la_referencia_de_quien_revisa() -> None:
    presupuesto = doc_json(composiciones__0__lineas__0__referencia="MP-0042")
    servicios = Servicios(
        referencia_de=lambda c: ReferenciaDeMercado("MP-0042", Decimal("10.00"), "USD", None)
    )
    r = revision.reauditar(verificado(presupuesto, anexos={}), servicios)
    [h] = [h for h in r.nuevos if h.regla == "R11" and h.severidad is Severidad.ADVERTENCIA]
    assert "+40.00 %" in h.descripcion and "MP-0042" in h.descripcion


def test_r12_se_evalua_a_la_fecha_de_emision_y_no_cambia_de_un_dia_a_otro() -> None:
    antiguo = doc_json(
        composiciones__0__lineas__0__precio_origen__fecha_precio="2026-09-01",
        composiciones__0__lineas__1__precio_origen__fecha_precio="2026-09-01",
        composiciones__0__lineas__2__precio_origen__fecha_precio="2026-09-01",
    )
    v = verificado(antiguo, anexos={})
    primera = revision.reauditar(v, Servicios())
    segunda = revision.reauditar(v, Servicios())
    r12 = [h for h in primera.nuevos if h.regla == "R12"]
    assert len(r12) == 3 and "70 dias al 10/11/2026" in r12[0].descripcion
    otras = [h.descripcion for h in segunda.nuevos if h.regla == "R12"]
    assert [h.descripcion for h in r12] == otras


def test_con_el_anexo_de_espacio_corren_r8_a_r10_y_r15() -> None:
    espacio = json_canonico(espacio_a_objeto(espacio_of001()))
    r = revision.reauditar(verificado(doc_json(), anexos={"anexos/espacio.json": espacio}),
                           Servicios())
    assert r.contextos == ("R1-R7", "R8-R10", "R15", "R11-R12")
    assert sum(1 for h in r.nuevos if h.regla == "R8") == 33  # el conjunto exacto de OF-001
    assert not [h for h in r.nuevos if h.regla in {"R9", "R10", "R15"}]


def test_con_el_anexo_de_control_y_el_servicio_de_s2_corren_r13_y_r14() -> None:
    llamadas = []

    def reglas_de_control(doc, anexo, corte):
        llamadas.append((doc.codigo, anexo["formato"], corte))
        return ()

    control = b'{"formato":"silice-anexo","nombre":"control","entradas":[]}'
    r = revision.reauditar(
        verificado(doc_json(), anexos={"anexos/control.json": control}),
        Servicios(reglas_de_control=reglas_de_control),
    )
    assert "R13-R14" in r.contextos and llamadas == [("001", "silice-anexo", date(2026, 11, 10))]
    sin = revision.reauditar(verificado(doc_json(), anexos={"anexos/control.json": control}),
                             Servicios())
    assert "R13-R14" not in sin.contextos


def test_la_reauditoria_se_corta_a_los_60_segundos_y_lo_dice() -> None:
    suelta = threading.Event()
    servicios = Servicios(tasa_en=lambda fecha: (suelta.wait(10), None)[1])
    r = revision.reauditar(verificado(doc_json(), anexos={}), servicios, tiempo_maximo=0.05)
    suelta.set()
    assert r.no_termino and r.resultado is None and "no terminó" in r.avisos[0]
    assert revision.LIMITE_SEGUNDOS == 60


def test_un_paquete_con_mas_de_200_000_filas_se_rechaza(monkeypatch) -> None:
    monkeypatch.setattr(reauditoria, "LIMITE_FILAS", 3)  # 1 renglón + 3 líneas = 4 > 3
    with pytest.raises(PaqueteRechazado, match="renglones y líneas"):
        revision.leer_documento(verificado(doc_json(), anexos={}).archivos)


# --- diferencias ---------------------------------------------------------------------------


def test_diferencia_contra_la_entrega_anterior_y_contra_la_base_del_revisor() -> None:
    actual = revision.leer_documento(
        verificado(doc_json(renglones__0__item__cantidad="25", renglones__0__cantidad="25"),
                   anexos={}).archivos)
    anterior = revision.leer_documento(verificado(doc_json(), anexos={}).archivos)
    d = revision.contra_la_entrega_anterior(actual, anterior)
    assert (d.desvio_cantidad, d.desvio_precio) == (Decimal("209.19937500"), Decimal(0))
    base = [revision.PrecioDeLista("MAT-001", "", Decimal("16.00"))]
    diferencia, revalorado = revision.contra_la_base_del_revisor(anterior, base)
    assert diferencia.desvio_cantidad == 0 and diferencia.desvio_precio > 0
    assert {n.insumo for n in revalorado.no_contrastables} == {"EQU-001", "MO-001"}


# --- quién cambió qué -----------------------------------------------------------------------


def test_los_cambios_nuevos_son_los_de_las_versiones_que_la_entrega_anterior_no_traia() -> None:
    v = verificado(doc_json(), anexos={})
    cadena = v.cadena
    previas = [cadena["eslabones"][0]["huella_eslabon"]]
    [cambio] = revision.cambios_nuevos(cadena, previas)
    assert (cambio["version"], cambio["responsable"], cambio["despues"]) == (
        "005", "Ana <ana>", "1.50")
    assert revision.cambios_nuevos(cadena, [e["huella_eslabon"] for e in cadena["eslabones"]]) == []


def test_un_cambio_hecho_tras_un_restablecimiento_se_marca() -> None:
    cadena = copy.deepcopy(verificado(doc_json(), anexos={}).cadena)
    cadena["cambios"]["005"][0][6] = "Luis Pérez <luis> (tras restablecimiento)"
    [cambio] = revision.cambios_nuevos(cadena, [])[1:]
    assert cambio["marca"] == "hecho tras un restablecimiento del administrador"


def test_la_declaracion_retroactiva_sale_de_los_eslabones_del_paquete() -> None:
    cadena = copy.deepcopy(verificado(doc_json(), anexos={}).cadena)
    assert revision.declaracion_retroactiva(cadena) is None  # todos los eslabones son normales
    for e in cadena["eslabones"]:
        e["tipo"] = "retroactivo"
    assert revision.declaracion_retroactiva(cadena) == (
        "Versiones 004 a 005 selladas el 2026-11-01: prueban que no cambiaron desde esa fecha; "
        "antes no hay garantía.")
    cadena["eslabones"] = cadena["eslabones"][:1]
    assert revision.declaracion_retroactiva(cadena).startswith("Versión 004 sellada")


def test_el_login_se_saca_del_responsable() -> None:
    assert revision.login_de("Ana Pérez <ana>") == "ana"
    assert revision.login_de("Luis <luis> (tras restablecimiento)") == "luis"
    assert revision.login_de("script:seed_demo") is None


# --- quien revisa es quien armó (P2 ratificada) ---------------------------------------------


HUELLA_PROPIA = firma.huella_completa(PAR.publica)


def test_revisor_igual_al_usuario_emisor_de_un_paquete_de_la_empresa_propia_lo_avisa() -> None:
    v = verificado(doc_json(), anexos={})
    assert revision.revisor_armo(v, login_revisor="ana", empresa_propia=(EMPRESA, HUELLA_PROPIA))


def test_revisor_igual_al_usuario_de_un_eslabon_anterior_tambien_lo_avisa() -> None:
    v = verificado(doc_json(), anexos={})
    v.cadena["eslabones"][0]["usuario"] = "Luis <luis>"
    donde = revision.revisor_armo(v, login_revisor="luis",
                                  empresa_propia=(EMPRESA, HUELLA_PROPIA))
    assert donde == ["004"]


def test_otro_revisor_de_la_misma_empresa_no_ve_el_aviso() -> None:
    v = verificado(doc_json(), anexos={})
    donde = revision.revisor_armo(
        v, login_revisor="pedro", empresa_propia=(EMPRESA, HUELLA_PROPIA)
    )
    assert donde == []


def test_un_paquete_de_una_empresa_ajena_con_un_login_igual_no_avisa() -> None:
    v = verificado(doc_json(), anexos={})
    assert revision.revisor_armo(v, login_revisor="ana", empresa_propia=("Otra", "0" * 64)) == []


def test_un_paquete_sin_firma_con_el_nombre_de_la_empresa_propia_cuenta_como_propio() -> None:
    sin_firma = verificar(paquete(par=None, presupuesto=doc_json(), anexos={}),
                          buscar_empresa=lambda h: None, recibido_en=RECIBIDO)
    assert revision.revisor_armo(sin_firma, login_revisor="ana", empresa_propia=(EMPRESA, None))


# --- Excel ---------------------------------------------------------------------------------


def test_el_excel_se_regenera_desde_el_json_y_lleva_las_hojas_de_la_revision(tmp_path) -> None:
    v = verificado(doc_json(), anexos={})
    r = revision.reauditar(v, Servicios())
    sin_extras = openpyxl.load_workbook(__import__("io").BytesIO(revision.excel_de_presupuesto(r)))
    assert "Presupuesto" in sin_extras.sheetnames and "Verificación" not in sin_extras.sheetnames
    tablas = revision.tablas_de_revision(v, r, None, revision.cambios_nuevos(v.cadena, []))
    con = openpyxl.load_workbook(
        __import__("io").BytesIO(revision.excel_de_revision(v, r, None, [])))
    assert {"Verificación", "Hallazgos", "Diferencias", "Cambios"} <= set(con.sheetnames)
    assert [t.titulo for t in tablas] == ["Verificación", "Hallazgos", "Diferencias", "Cambios"]


def test_una_formula_en_el_texto_de_un_paquete_no_se_ejecuta_al_exportar() -> None:
    maligna = '=HYPERLINK("http://127.0.0.1:9/robo","clic")'
    v = verificado(doc_json(renglones__0__item__descripcion=maligna), anexos={})
    r = revision.reauditar(v, Servicios())
    libro = openpyxl.load_workbook(__import__("io").BytesIO(revision.excel_de_presupuesto(r)))
    celdas = [c for hoja in libro for fila in hoja.iter_rows() for c in fila
              if isinstance(c.value, str) and c.value.startswith("=HYPERLINK")]
    assert celdas and all(c.data_type == "s" and c.quotePrefix for c in celdas)


def test_sin_reauditoria_no_hay_excel() -> None:
    v = verificado(doc_json(), anexos={})
    no_termino = revision.Reauditoria(documento=revision.leer_documento(v.archivos),
                                      resultado=None, contextos=(), no_termino=True)
    with pytest.raises(ValueError, match="no terminó"):
        revision.excel_de_presupuesto(no_termino)


# --- presupuesto externo en Excel (23d) ------------------------------------------------------


def test_la_plantilla_descargada_se_audita_y_no_toca_ninguna_base(tmp_path: Path) -> None:
    ruta = tmp_path / "plantilla.xlsx"
    ruta.write_bytes(revision.plantilla_uc05())
    importado, informe = revision.auditar_excel_externo(ruta)
    assert importado.presupuesto.codigo == "EJ-001"
    assert importado.presupuesto.total == Decimal("836.79750000")
    assert informe.codigo_presupuesto == "EJ-001"


def test_un_excel_con_formula_se_lee_por_su_valor_nunca_por_la_formula(tmp_path: Path) -> None:
    ruta = tmp_path / "externo.xlsx"
    ruta.write_bytes(revision.plantilla_uc05())
    libro = openpyxl.load_workbook(ruta)
    libro["Presupuesto"]["B2"] = '=HYPERLINK("http://127.0.0.1:9/robo","clic")'
    libro.save(ruta)
    importado, _ = revision.auditar_excel_externo(ruta)
    descripcion = importado.presupuesto.partidas[0].item.descripcion
    assert "HYPERLINK" not in descripcion and "127.0.0.1" not in descripcion
```
**`tests/integration/test_revision_recibir.py`**
```python
"""Recibir, dictaminar y encontrar la entrega anterior (UC-23, RF-86/87; spec S3 §6.5 y §9).

Una base de caso temporal con las tablas `paq_*` y una `instalacion.db` temporal con la empresa
emisora registrada. El archivo recibido se guarda una vez por SHA-256 (23h)."""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from core.budget.canonico import json_canonico
from core.catalog import abrir_sesion, crear_motor
from paquete import modelo as paq
from seguridad import firma
from seguridad.modelo import EmpresaRegistrada
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.instalacion import AHORA, instalacion
from tests.fixtures.paquetes import EMPRESA, paquete
from ui import revision

PAR = firma.generar_par()
ANTES = datetime(2026, 11, 3, 9, 0)
DESPUES = datetime(2026, 11, 10, 9, 30)
RECIBIDO = datetime(2026, 11, 12, 10, 0)


def _doc(**cambios) -> bytes:
    objeto = copy.deepcopy(EJEMPLO_V1)
    objeto.update(cambios)
    return json_canonico(objeto)


def _paquete(emitido: datetime, codigo: str, paquete_id: str, **mas) -> bytes:
    return paquete(par=PAR, presupuesto=_doc(), emitido=emitido, codigo=codigo,
                   paquete_id=paquete_id, anexos={}, **mas)


@pytest.fixture
def mundo(tmp_path: Path):
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    paq.crear_esquema_paquete(motor)
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "revisor") as bd:
        bd.add(EmpresaRegistrada(
            empresa=EMPRESA, rif="J-00000000-0", publica=PAR.publica,
            huella=firma.huella_completa(PAR.publica), estado="activa",
            comprobada_con="Ana, por teléfono", metodo="telefono", fecha_comprobacion=AHORA,
            registrada_por="admin"))
        bd.commit()
        yield caso, bd, tmp_path / "paquetes"
    motor.dispose()


def _recibir(mundo, datos: bytes, nombre: str = "a.silice", **mas):
    caso, bd, carpeta = mundo
    return revision.recibir(datos, nombre, caso=caso, instalacion=bd, carpeta_paquetes=carpeta,
                            revisor="Luis <luis>", ahora=RECIBIDO, **mas)


def test_recibir_un_paquete_firmado_lo_verifica_lo_guarda_y_lo_registra_una_vez(mundo) -> None:
    caso, _, carpeta = mundo
    datos = _paquete(DESPUES, "005", "11111111-1111-4111-8111-111111111111")
    r = _recibir(mundo, datos)
    assert r.verificacion.estado == "verificado" and not r.ya_recibido
    assert r.ruta.read_bytes() == datos and r.ruta.parent == carpeta
    assert r.ruta.name.startswith(r.verificacion.sha256)
    otra = _recibir(mundo, datos)  # el mismo archivo: no se duplica (23h)
    assert otra.ya_recibido and otra.paquete_id == r.paquete_id
    assert caso.scalar(select(func.count()).select_from(paq.paq_recibido)) == 1
    assert len(list(carpeta.iterdir())) == 1


def test_un_archivo_que_no_es_un_paquete_se_rechaza_y_no_se_guarda_nada(mundo) -> None:
    caso, _, carpeta = mundo
    r = _recibir(mundo, b"esto no es un zip", "malo.silice")
    assert r.verificacion.estado == "rechazado" and r.paquete_id == 0 and not r.ya_recibido
    assert caso.scalar(select(func.count()).select_from(paq.paq_recibido)) == 0
    assert not carpeta.exists() or not list(carpeta.iterdir())


def test_el_nombre_del_archivo_recibido_no_escapa_de_la_carpeta(mundo) -> None:
    _, _, carpeta = mundo
    datos = _paquete(DESPUES, "005", "11111111-1111-4111-8111-111111111111")
    r = _recibir(mundo, datos, "..\\..\\afuera.silice")
    assert r.ruta.parent == carpeta and ".." not in r.ruta.name


def test_sin_la_empresa_registrada_el_paquete_queda_no_verificado(mundo) -> None:
    caso, bd, carpeta = mundo
    bd.query(EmpresaRegistrada).delete()
    bd.commit()
    r = _recibir(mundo, _paquete(DESPUES, "005", "11111111-1111-4111-8111-111111111111"))
    assert r.verificacion.estado == "no_verificado"
    assert caso.execute(select(paq.paq_recibido.c.estado)).scalar_one() == "no_verificado"


def test_el_dictamen_queda_atado_al_sha256_y_al_estado_de_ese_momento(mundo) -> None:
    caso, _, _ = mundo
    r = _recibir(mundo, _paquete(DESPUES, "005", "11111111-1111-4111-8111-111111111111"))
    revision.dictaminar(caso, r, resultado="con observaciones", notas="Falta la memoria de R4",
                        revisor="Luis <luis>", ahora=RECIBIDO, armo=False)
    fila = paq.dictamenes_de(caso, r.verificacion.sha256)[0]
    assert (fila["resultado"], fila["usuario"], fila["estado_verificacion"], fila["revisor_armo"]
            ) == ("con observaciones", "Luis <luis>", "verificado", False)
    assert fila["huella_archivo"] == r.verificacion.sha256


def test_un_dictamen_con_observaciones_sin_notas_se_rechaza_y_no_se_guarda(mundo) -> None:
    caso, _, _ = mundo
    r = _recibir(mundo, _paquete(DESPUES, "005", "11111111-1111-4111-8111-111111111111"))
    with pytest.raises(ValueError, match="necesita notas"):
        revision.dictaminar(caso, r, resultado="rechazado", notas="  ", revisor="Luis <luis>",
                            ahora=RECIBIDO, armo=False)
    assert not paq.dictamenes_de(caso, r.verificacion.sha256)


def test_la_entrega_anterior_es_la_ultima_del_mismo_proyecto_y_emisor_emitida_antes(mundo) -> None:
    caso, bd, _ = mundo
    primera = _recibir(mundo, _paquete(ANTES, "004", "22222222-2222-4222-8222-222222222222"))
    actual = _recibir(mundo, _paquete(DESPUES, "005", "11111111-1111-4111-8111-111111111111"))
    previa = revision.entrega_anterior(caso, bd, actual.verificacion)
    assert previa is not None and previa.codigo == "004"
    assert previa.documento.codigo == "001"
    assert previa.huellas == tuple(
        e["huella_eslabon"] for e in primera.verificacion.cadena["eslabones"])
    assert revision.entrega_anterior(caso, bd, primera.verificacion) is None  # nada antes


def test_si_el_archivo_anterior_ya_no_esta_no_hay_entrega_anterior(mundo) -> None:
    caso, bd, _ = mundo
    primera = _recibir(mundo, _paquete(ANTES, "004", "22222222-2222-4222-8222-222222222222"))
    actual = _recibir(mundo, _paquete(DESPUES, "005", "11111111-1111-4111-8111-111111111111"))
    primera.ruta.unlink()
    assert revision.entrega_anterior(caso, bd, actual.verificacion) is None


def test_la_empresa_propia_para_revisar_da_su_nombre_y_la_huella_de_su_clave(mundo) -> None:
    from seguridad import empresas

    _, bd, _ = mundo
    assert revision.empresa_propia_para_revisar(bd) == (None, None)
    empresas.guardar_empresa_propia(bd, EMPRESA, "J-00000000-0", "", "admin", AHORA)
    assert revision.empresa_propia_para_revisar(bd) == (EMPRESA, None)
    clave = empresas.generar_clave(bd, "una clave de firma larga y unica", "admin", AHORA)
    assert revision.empresa_propia_para_revisar(bd) == (EMPRESA, clave.huella)
```
**`tests/unit/test_auditoria_servicios.py`**
```python
"""Los servicios de ESTA instalación para la reauditoría (spec S3 §9 paso 3): la referencia MaPreX,
la tasa del BCV y la erosión, leídas de la base de quien revisa (S1: listas, orígenes y tasas).

La reauditoría recibe estos servicios por inyección (`Servicios`); aquí se prueba el armado real
contra una base en memoria. Si S1 expresa distinto alguna de sus funciones, esta prueba lo dice."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from auditoria.reauditoria import ReferenciaDeMercado
from auditoria.servicios import servicios_de_la_instalacion
from core import models
from core.catalog import abrir_sesion, crear_esquema, crear_motor

D = Decimal
FECHA = date(2026, 11, 10)


@pytest.fixture
def base():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    with abrir_sesion(motor) as sesion:
        yield sesion
    motor.dispose()


def _referencia(sesion, moneda="USD", tasa=None):
    lista = models.ListaPrecios(
        nombre="MaPreX de referencia", moneda=moneda, fecha_vigencia=FECHA, origen="maprex")
    sesion.add(lista)
    sesion.flush()
    sesion.add(models.ListaPreciosOrigen(
        lista_id=lista.id, tasa=tasa, fecha_tasa=FECHA if tasa else None,
        alcance=models.ALCANCE_REFERENCIA))
    unico = models.Insumo(codigo="MAT-1", tipo="material", descripcion="Cemento", unidad="saco")
    repetido_a = models.Insumo(codigo="MAT-2", tipo="material", descripcion="Arena", unidad="m3")
    repetido_b = models.Insumo(codigo="MAT-3", tipo="material", descripcion="Arena fina",
                               unidad="m3")
    sesion.add_all([unico, repetido_a, repetido_b])
    sesion.flush()
    for insumo, ref, precio in ((unico, "MP-0042", D("10.00")), (repetido_a, "MP-0099", D("5.00")),
                                (repetido_b, "MP-0099", D("6.00"))):
        fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=precio)
        sesion.add(fila)
        sesion.flush()
        sesion.add(models.ReferenciaPrecio(precio_id=fila.id, referencia=ref))
    sesion.flush()
    return lista


def _tasas(sesion, *valores: tuple[date, str]) -> None:
    serie = models.SerieIndice(
        codigo="BCV-USD-VENTA", nombre="USD venta", organismo="BCV", unidad="Bs/USD",
        periodicidad="diaria")
    sesion.add(serie)
    sesion.flush()
    importacion = models.ImportacionIndice(
        serie_id=serie.id, archivo="tasas.xls", huella="a" * 64, fuente="prueba",
        fecha_descarga=FECHA, fecha_importacion=datetime(2026, 11, 10), responsable="admin",
        filas_leidas=len(valores), filas_rechazadas=0)
    sesion.add(importacion)
    sesion.flush()
    for fecha, valor in valores:
        sesion.add(models.ValorIndice(
            serie_id=serie.id, importacion_id=importacion.id, fecha=fecha, valor=D(valor)))
    sesion.flush()


def test_sin_lista_de_referencia_no_hay_precio_de_mercado(base) -> None:
    servicios = servicios_de_la_instalacion(base)
    assert servicios.referencia_de("MP-0042") is None


def test_la_referencia_de_un_codigo_unico_trae_su_precio_y_su_moneda(base) -> None:
    _referencia(base)
    servicios = servicios_de_la_instalacion(base)
    assert servicios.referencia_de("MP-0042") == ReferenciaDeMercado(
        "MP-0042", D("10.00"), "USD", None)
    assert servicios.referencia_de("MP-9999") is None


def test_una_ref_repetida_en_la_referencia_no_contrasta(base) -> None:
    """S1 §6.3: si dos insumos de la lista de referencia comparten la misma Ref, no se sabe cuál
    es la del mercado y no se contrasta ninguno."""
    _referencia(base)
    assert servicios_de_la_instalacion(base).referencia_de("MP-0099") is None


def test_la_referencia_en_bs_trae_la_tasa_de_su_lista(base) -> None:
    _referencia(base, moneda="Bs", tasa=D("36.50"))
    ref = servicios_de_la_instalacion(base).referencia_de("MP-0042")
    assert (ref.moneda, ref.tasa) == ("Bs", D("36.50"))


def test_la_tasa_es_la_ultima_hasta_la_fecha_y_a_mas_de_7_dias_no_hay(base) -> None:
    _tasas(base, (date(2026, 11, 3), "36.00"), (date(2026, 11, 9), "37.25"))
    servicios = servicios_de_la_instalacion(base)
    assert servicios.tasa_en(date(2026, 11, 10)) == D("37.25")  # la de mayor fecha <= la pedida
    assert servicios.tasa_en(date(2026, 11, 16)) == D("37.25")  # 7 días naturales: todavía vale
    assert servicios.tasa_en(date(2026, 11, 17)) is None  # 8 días: no se convierte (S1-R2)
    assert servicios.tasa_en(date(2026, 11, 1)) is None  # antes de la primera: no hay


def test_la_erosion_de_un_precio_en_usd_es_cero_y_sin_tasa_es_desconocida(base) -> None:
    erosion = servicios_de_la_instalacion(base).erosion
    assert erosion(D("100"), "USD", "USD", D("100"), None, None) == D(0)
    assert erosion(D("3650"), "Bs", "Bs", D("3650"), None, D("40")) is None


def test_la_erosion_en_bs_es_la_diferencia_a_la_tasa_de_hoy(base) -> None:
    erosion = servicios_de_la_instalacion(base).erosion
    # 100 Bs a tasa 40 valían 2,50 USD; hoy, a tasa 50, 2,00 USD: perdió 100*(50/40) - 100 = 25 Bs
    assert erosion(D("100"), "Bs", "Bs", D("100"), D("40"), D("50")) == D("25")
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_ui_revision.py tests/integration/test_revision_recibir.py
tests/unit/test_auditoria_servicios.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'auditoria'`
(`auditoria.reauditoria` en `test_ui_revision`, `ui.revision` en `test_revision_recibir`).
```bash
git add tests/unit/test_ui_revision.py tests/integration/test_revision_recibir.py \
  tests/unit/test_auditoria_servicios.py
git commit -m "test(revision): reauditoria en memoria, recibir, dictamen y servicios, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`auditoria/__init__.py`**
```python
"""Reauditoría en memoria de un documento ajeno: la comparten `ui` y `api` (S3, RP8-6)."""
```
**`auditoria/reauditoria.py`**
```python
"""La reauditoría en memoria de un documento ajeno (spec S3 §9 paso 3 y §10; RF-87, RF-88).

La comparten la vista de quien revisa (`ui/revision.py`) y la ruta `POST /v1/auditorias`
(`api/rutas/auditorias.py`): por eso vive en un paquete aparte, fuera del núcleo, que importa
`core`, `adapters.espacio` y `paquete` y que **ni `ui` ni `api` ni el núcleo tocan al revés**
(RP8-6; el spec la ponía en `ui/revision.py`, pero la API no puede importar `ui`).

Recalcula cada precio unitario con el motor desde las composiciones y los parámetros del
documento (no se confía en los precios ni en los totales escritos), corre `REGLAS` y las reglas
externas del contexto «reauditoría» (maestro §3.3): R8-R10 y R15 con el anexo de espacio; R11-R12
con el `precio_origen` del documento, **a la fecha de emisión que se le da** (nunca el reloj),
contra la referencia MaPreX de quien revisa; R13-R14 con el anexo de control si hay servicio de S2.
R16 no corre aquí. Toda reevaluación es en memoria: no reescribe nada.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from adapters.espacio import Espacio
from adapters.espacio.planos.geometria_plano import reglas_plano
from adapters.espacio.reglas import reglas_espacio
from adapters.espacio.serie import espacio_desde_objeto
from core.budget import canonico
from core.budget.presupuesto import ResultadoElaboracion, elaborar
from core.catalog.empresa import PLAZO_VIGENCIA_DIAS, RANGO_INFERIOR, RANGO_SUPERIOR
from core.contracts.verificacion import Hallazgo, ReglaVerificacion
from core.verification import REGLAS
from core.verification.precios import (
    InstantaneaPrecios,
    PartidaPrecios,
    PrecioAuditado,
    reglas_precios,
)
from paquete.formato import LIMITE_FILAS, PaqueteRechazado
from seguridad.json_estricto import a_decimal, leer_json

__all__ = [
    "LIMITE_SEGUNDOS",
    "NOMBRE_CONTROL",
    "NOMBRE_ESPACIO",
    "DiferenciaDeclarada",
    "Reauditoria",
    "ReferenciaDeMercado",
    "Servicios",
    "instantanea_del_documento",
    "leer_documento",
    "reauditar",
]

LIMITE_SEGUNDOS = 60
NOMBRE_ESPACIO = "anexos/espacio.json"
NOMBRE_CONTROL = "anexos/control.json"

#: `erosion(precio, moneda_lista, moneda_original, precio_original, tasa_del_precio, tasa_de_hoy)`
#: es la de S1 §5.3: por unidad y en la moneda de la lista; `None` sin tasa; 0 si el
#: original es USD.
Erosion = Callable[
    [Decimal, str, str, Decimal, "Decimal | None", "Decimal | None"], "Decimal | None"
]


@dataclass(frozen=True, slots=True)
class ReferenciaDeMercado:
    """El precio MaPreX de la referencia de un insumo en la instalación que revisa."""

    codigo: str
    precio: Decimal
    moneda: str
    tasa: Decimal | None  # a la fecha de la referencia; None en USD


@dataclass(frozen=True, slots=True)
class Servicios:
    """Lo que la reauditoría necesita de la base de quien revisa. `auditoria.servicios` lo arma
    con S1 y S2; las pruebas, con funciones a mano."""

    referencia_de: Callable[[str], ReferenciaDeMercado | None] = lambda codigo: None
    tasa_en: Callable[[date], Decimal | None] = lambda fecha: None
    erosion: Erosion = lambda precio, lista, original, p_original, t0, t1: Decimal(0)
    reglas_de_control: (
        Callable[[canonico.DocumentoLeido, Mapping[str, Any], date], Sequence[ReglaVerificacion]]
        | None
    ) = None
    rango: tuple[Decimal, Decimal] = (RANGO_INFERIOR, RANGO_SUPERIOR)
    plazo_vigencia_dias: int = PLAZO_VIGENCIA_DIAS


def leer_documento(archivos: Mapping[str, bytes]) -> canonico.DocumentoLeido:
    """`presupuesto.json` con el lector estricto y el tope de filas (S3 §8.4)."""
    return leer_documento_json(archivos["presupuesto.json"])


def leer_documento_json(datos: bytes) -> canonico.DocumentoLeido:
    objeto = leer_json(datos)
    if canonico.contar_filas(objeto) > LIMITE_FILAS:
        raise PaqueteRechazado(
            f"El presupuesto trae más de {LIMITE_FILAS} renglones y líneas de composición."
        )
    return canonico.leer(objeto)


def _insumos_alineados(ids: Mapping[str, int], lineas) -> tuple[int | None, ...]:
    return tuple(ids.get(extra.insumo) if extra.insumo else None for extra in lineas)


def instantanea_del_documento(
    doc: canonico.DocumentoLeido, servicios: Servicios, fecha_emision: date
) -> InstantaneaPrecios:
    """R11 y R12 de un documento ajeno, en memoria: los precios que usa, con su `precio_origen`
    (S1), contra la referencia de quien revisa y a `fecha_emision`."""
    moneda = str(doc.lista.get("moneda", doc.moneda))
    tasa_evaluacion = servicios.tasa_en(fecha_emision)
    ids: dict[str, int] = {}
    precios: dict[str, PrecioAuditado] = {}
    for codigo, composicion in doc.composiciones.items():
        todas = [*composicion.materiales, *composicion.equipos, *composicion.mano_obra]
        for linea, extra in zip(todas, doc.lineas[codigo], strict=True):
            if extra.insumo is None or extra.insumo in precios:
                continue
            ids[extra.insumo] = len(ids) + 1
            origen = extra.precio_origen or {}
            precio = extra.precio
            fecha_precio = date.fromisoformat(
                origen.get("fecha_precio") or str(doc.lista["fecha_vigencia"])
            )
            tasa = a_decimal(origen["tasa"]) if origen.get("tasa") else None
            fecha_tasa = (
                date.fromisoformat(origen["fecha_tasa"]) if origen.get("fecha_tasa") else None
            )
            a_su_fecha = (
                None if tasa is not None or moneda == "USD" else servicios.tasa_en(fecha_precio)
            )
            moneda_original = origen.get("moneda_original") or moneda
            precio_original = (
                a_decimal(origen["precio_original"]) if origen.get("precio_original") else precio
            )
            referencia = servicios.referencia_de(extra.referencia) if extra.referencia else None
            precios[extra.insumo] = PrecioAuditado(
                insumo_id=ids[extra.insumo], codigo=extra.insumo, descripcion=linea.descripcion,
                precio=precio, moneda=moneda, moneda_original=moneda_original,
                precio_original=precio_original, fecha_precio=fecha_precio, tasa=tasa,
                fecha_tasa=fecha_tasa, fuente_tasa=origen.get("fuente_tasa") or "",
                tasa_a_su_fecha=a_su_fecha,
                referencia=referencia.precio if referencia else None,
                moneda_referencia=referencia.moneda if referencia else moneda,
                tasa_referencia=referencia.tasa if referencia else None,
                codigo_referencia=extra.referencia or "",
                erosion=servicios.erosion(
                    precio, moneda, moneda_original, precio_original, tasa or a_su_fecha,
                    tasa_evaluacion,
                ),
                heredado=origen.get("heredado"),
            )
    cantidades: dict[str, Decimal] = {}
    for item in doc.items:
        previa = cantidades.get(item.codigo_partida, Decimal(0))
        cantidades[item.codigo_partida] = previa + item.cantidad
    partidas = tuple(
        PartidaPrecios(c, q, doc.composiciones[c], _insumos_alineados(ids, doc.lineas[c]))
        for c, q in cantidades.items()
    )
    return InstantaneaPrecios(
        fecha_evaluacion=fecha_emision, moneda=doc.moneda,
        precios=tuple(sorted(precios.values(), key=lambda p: p.insumo_id)),
        tasa_evaluacion=tasa_evaluacion, rango_inferior=servicios.rango[0],
        rango_superior=servicios.rango[1], plazo_vigencia_dias=servicios.plazo_vigencia_dias,
        partidas=partidas, parametros=doc.parametros,
    )


@dataclass(frozen=True, slots=True)
class DiferenciaDeclarada:
    """Un precio unitario o un total declarado que no cuadra con el recálculo, con su monto."""

    codigo_partida: str
    campo: str  # precio_unitario | total
    declarado: Decimal
    recalculado: Decimal
    monto: Decimal  # lo declarado menos lo recalculado, a la cantidad del renglón


@dataclass(frozen=True, slots=True)
class Reauditoria:
    documento: canonico.DocumentoLeido
    resultado: ResultadoElaboracion | None
    contextos: tuple[str, ...]
    fecha_evaluacion: date | None = None
    nuevos: tuple[Hallazgo, ...] = ()  # el emisor no los declaró
    ya_no: tuple[Hallazgo, ...] = ()  # los declaró y ya no aparecen
    comunes: tuple[Hallazgo, ...] = ()
    diferencias: tuple[DiferenciaDeclarada, ...] = ()
    total_recalculado: Decimal | None = None
    no_termino: bool = False
    avisos: tuple[str, ...] = field(default=())


def _clave(h: Hallazgo) -> tuple:
    return (h.regla, int(h.severidad), tuple(h.origen_ids), h.descripcion)


def _reglas_externas(
    doc: canonico.DocumentoLeido, espacio_json: bytes | None, control_json: bytes | None,
    servicios: Servicios, fecha_evaluacion: date,
) -> tuple[list[ReglaVerificacion], list[str]]:
    reglas: list[ReglaVerificacion] = []
    contextos = ["R1-R7"]
    if espacio_json is not None:
        espacio: Espacio = espacio_desde_objeto(leer_json(espacio_json), a_decimal)
        reglas += [*reglas_espacio(espacio), *reglas_plano(espacio)]
        contextos += ["R8-R10", "R15"]
    reglas += list(reglas_precios(instantanea_del_documento(doc, servicios, fecha_evaluacion)))
    contextos.append("R11-R12")
    if control_json is not None and servicios.reglas_de_control is not None:
        reglas += list(
            servicios.reglas_de_control(doc, leer_json(control_json), fecha_evaluacion)
        )
        contextos.append("R13-R14")
    return reglas, contextos


def reauditar(
    doc: canonico.DocumentoLeido,
    servicios: Servicios,
    fecha_evaluacion: date,
    *,
    espacio_json: bytes | None = None,
    control_json: bytes | None = None,
    tiempo_maximo: float = LIMITE_SEGUNDOS,
) -> Reauditoria:
    """La reauditoría de `doc` a `fecha_evaluacion` (R12; la de emisión en un paquete, la que
    manda el cuerpo en la API). Si pasa de `tiempo_maximo` segundos se corta y se informa «no
    terminó» (S3 §8.4)."""

    def trabajo() -> Reauditoria:
        externas, contextos = _reglas_externas(
            doc, espacio_json, control_json, servicios, fecha_evaluacion
        )
        resultado = elaborar(
            [*doc.items, *doc.pendientes], doc.composiciones, doc.parametros, codigo=doc.codigo,
            fecha=doc.fecha, moneda=doc.moneda, plan=list(doc.plan) if doc.plan else None,
            reglas=(*REGLAS, *externas),
        )
        recalculado = {
            (p.item.codigo_partida, p.item.origen_id): p for p in resultado.presupuesto.partidas
        }
        diferencias: list[DiferenciaDeclarada] = []
        for d, item in zip(doc.declarados, doc.items, strict=True):
            real = recalculado[(item.codigo_partida, item.origen_id)]
            for campo, declarado, calculado in (
                ("precio_unitario", d.precio_unitario, real.resultado.precio_unitario),
                ("total", d.total, real.total),
            ):
                if declarado != calculado:
                    por = d.cantidad if campo == "precio_unitario" else 1
                    diferencias.append(
                        DiferenciaDeclarada(
                            item.codigo_partida, campo, declarado, calculado,
                            (declarado - calculado) * por,
                        )
                    )
        declarados = {_clave(h): h for h in doc.hallazgos}
        propios = {_clave(h): h for h in resultado.informe.hallazgos}
        return Reauditoria(
            documento=doc, resultado=resultado, contextos=tuple(contextos),
            fecha_evaluacion=fecha_evaluacion,
            nuevos=tuple(h for k, h in propios.items() if k not in declarados),
            ya_no=tuple(h for k, h in declarados.items() if k not in propios),
            comunes=tuple(h for k, h in propios.items() if k in declarados),
            diferencias=tuple(diferencias), total_recalculado=resultado.presupuesto.total,
        )

    with ThreadPoolExecutor(max_workers=1) as ejecutor:
        futuro = ejecutor.submit(trabajo)
        try:
            return futuro.result(timeout=tiempo_maximo)
        except TiempoAgotado:
            ejecutor.shutdown(wait=False, cancel_futures=True)
            return Reauditoria(
                documento=doc, resultado=None, contextos=(), fecha_evaluacion=fecha_evaluacion,
                no_termino=True, avisos=(f"La reauditoría no terminó en {tiempo_maximo:g} s.",),
            )
```
**`auditoria/servicios.py`**
```python
"""Los `Servicios` de la reauditoría armados con la base de quien revisa (S1 y S2; spec S3 §3.4).

La reauditoría contrasta los precios de un documento ajeno con **la referencia MaPreX de esta
instalación** (`lista_de_referencia`, S1 §6.2) y los lleva a una moneda con **las tasas del BCV
que esta instalación importó** (`tasa_aplicable`, S1). Un día sin tasa no revienta: la tasa es
`None` y R11/R12 lo dicen («no contrastable», impacto sin cuantificar). La erosión es la de S1
§5.3, copiada de `core.catalog.empresa` en su forma pública: 0 si el original es USD, `None` sin
tasa, y por unidad en la moneda de la lista.

Depende de S1 (0.6.0) y, para R13-R14, de lo que S2 (0.7.0) exponga para reauditar un
`anexos/control.json`; sin él, R13-R14 no corren y el contexto lo dice.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from auditoria.reauditoria import ReferenciaDeMercado, Servicios
from core import models
from core.budget import canonico
from core.catalog.empresa import lista_de_referencia
from core.catalog.indices import LADO_POR_DEFECTO, TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import erosion
from core.catalog.origen import origenes_efectivos
from core.contracts.verificacion import ReglaVerificacion

__all__ = ["servicios_de_la_instalacion"]

ReglasDeControl = Callable[
    [canonico.DocumentoLeido, Mapping[str, Any], date], Sequence[ReglaVerificacion]
]


def _erosion(
    precio: Decimal, moneda_lista: str, moneda_original: str, precio_original: Decimal,
    t0: Decimal | None, t1: Decimal | None,
) -> Decimal | None:
    if moneda_original == "USD":
        return Decimal(0)
    if t0 is None or t1 is None:
        return None
    if moneda_lista == "Bs":
        return erosion(precio, "Bs", t0, t1).bs
    return erosion(precio_original, "Bs", t0, t1).usd


def servicios_de_la_instalacion(
    session: Session, *, lado: str = LADO_POR_DEFECTO,
    reglas_de_control: ReglasDeControl | None = None,
) -> Servicios:
    """La referencia, las tasas y la erosión de esta instalación. `reglas_de_control` es el
    servicio de S2 para R13-R14 desde un anexo (`None` mientras S2 no lo entregue)."""
    referencia = lista_de_referencia(session)
    por_ref: dict[str, models.PrecioInsumo] = {}
    origenes = {}
    if referencia is not None:
        refs = dict(
            session.execute(
                select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
                .join(
                    models.PrecioInsumo,
                    models.PrecioInsumo.id == models.ReferenciaPrecio.precio_id,
                )
                .where(models.PrecioInsumo.lista_id == referencia.id)
            ).all()
        )
        veces = Counter(refs.values())
        por_id = {p.id: p for p in referencia.precios}
        # una Ref repetida en la referencia no contrasta (S1 §6.3): solo las únicas
        por_ref = {ref: por_id[pid] for pid, ref in refs.items() if veces[ref] == 1}
        origenes = origenes_efectivos(session, referencia)

    def referencia_de(codigo: str) -> ReferenciaDeMercado | None:
        precio = por_ref.get(codigo)
        if precio is None or referencia is None:
            return None
        return ReferenciaDeMercado(
            codigo, precio.precio, referencia.moneda, origenes[precio.id].tasa
        )

    def tasa_en(fecha: date) -> Decimal | None:
        try:
            return tasa_aplicable(session, fecha, lado=lado).valor
        except TasaNoDisponible:
            return None

    return Servicios(
        referencia_de=referencia_de, tasa_en=tasa_en, erosion=_erosion,
        reglas_de_control=reglas_de_control,
    )
```
**`ui/revision.py`**
```python
"""Revisar un paquete o un presupuesto externo, sin Streamlit (S3 §9 y §10, UC-23; RF-86/87).

Orquesta lo que `core`, `paquete`, `seguridad` y `adapters.espacio` no pueden orquestar entre sí.
Todo el análisis es **en memoria**: el paquete se reaudita con las reglas de ESTA instalación
sobre el documento canónico que trae (`canonico.leer`), sin cargarlo al catálogo ni escribir una
sola fila de las versiones del caso (DA-S3-7, maestro §3.3). Lo único que se guarda es el archivo
recibido (`datos\\paquetes\\`), su registro (`paq_recibido`) y el dictamen (`paq_dictamen`).

La reauditoría recalcula cada precio unitario con el motor desde las composiciones y los parámetros
del paquete (no se confía en los precios ni en los totales escritos), corre `REGLAS`, las reglas
externas del contexto «reauditoría» (R8-R10 y R15 con el anexo de espacio; R11-R12 con el
`precio_origen` del documento, **a la fecha de emisión**, contra la referencia MaPreX de quien
revisa; R13-R14 con el anexo de control) y separa los hallazgos que el emisor **no declaró**, los
que declaró y **ya no aparecen** y los comunes. R16 no corre aquí (maestro §3.3).
"""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from auditoria.reauditoria import (
    LIMITE_SEGUNDOS,
    NOMBRE_CONTROL,
    NOMBRE_ESPACIO,
    DiferenciaDeclarada,
    Reauditoria,
    ReferenciaDeMercado,
    Servicios,
    instantanea_del_documento,
    leer_documento,
)
from auditoria.reauditoria import reauditar as _reauditar
from core import models
from core.budget import canonico
from core.budget.comparacion import (
    Diferencia,
    PrecioDeLista,
    Revaloracion,
    diferencia_entre_versiones,
    filas_de,
    revalorar,
)
from core.budget.excel import TablaExportable, exportar_hoja
from core.budget.importacion import (
    COLUMNAS_APU,
    COLUMNAS_CURVA,
    COLUMNAS_DATOS,
    COLUMNAS_INSUMOS,
    COLUMNAS_PRESUPUESTO,
    HOJA_APU,
    HOJA_CURVA,
    HOJA_DATOS,
    HOJA_INSUMOS,
    HOJA_PRESUPUESTO,
    leer_presupuesto_tabular,
)
from core.verification import REGLAS, auditar
from paquete import modelo as paq
from paquete.verificar import EmpresaConocida, Verificacion, evaluar_anterioridad, verificar
from seguridad import empresas
from seguridad.json_estricto import leer_json
from seguridad.modelo import EmpresaRegistrada
from ui.subidas import nombre_seguro

__all__ = [
    "LIMITE_SEGUNDOS",
    "auditar_excel_externo",
    "plantilla_uc05",
    "DiferenciaDeclarada",
    "EntregaAnterior",
    "Recibido",
    "Reauditoria",
    "ReferenciaDeMercado",
    "Servicios",
    "cambios_nuevos",
    "contra_la_base_del_revisor",
    "contra_la_entrega_anterior",
    "declaracion_retroactiva",
    "dictaminar",
    "empresa_propia_para_revisar",
    "entrega_anterior",
    "excel_de_presupuesto",
    "excel_de_revision",
    "instantanea_del_documento",
    "leer_documento",
    "login_de",
    "precios_de_lista",
    "reauditar",
    "recibir",
    "revisor_armo",
    "tablas_de_revision",
]

_CAMPOS_DE_CAMBIO = ("version", "objeto", "clave", "campo", "antes", "despues", "fuente",
                     "responsable", "fecha", "marca")
_LOGIN = re.compile(r"<([^<>]+)>")


def reauditar(
    v: Verificacion, servicios: Servicios, *, tiempo_maximo: float = LIMITE_SEGUNDOS
) -> Reauditoria:
    """La reauditoría de un paquete legible (todo menos «rechazado») a la FECHA DE EMISIÓN del
    manifiesto: el mismo paquete reauditado otro día da lo mismo (maestro §3.3)."""
    emision = datetime.fromisoformat(str(v.manifiesto["emitido"])).date()
    return _reauditar(
        leer_documento(v.archivos), servicios, emision,
        espacio_json=v.archivos.get(NOMBRE_ESPACIO), control_json=v.archivos.get(NOMBRE_CONTROL),
        tiempo_maximo=tiempo_maximo,
    )


# --- diferencia entre versiones -------------------------------------------------------------


def precios_de_lista(session: Session, lista: models.ListaPrecios) -> list[PrecioDeLista]:
    """Los precios de una lista de quien revisa, con su referencia de precio (Ref MaPreX)."""
    referencias = dict(
        session.execute(
            select(models.ReferenciaPrecio.precio_id, models.ReferenciaPrecio.referencia)
        ).all()
    )
    return [
        PrecioDeLista(p.insumo.codigo, referencias.get(p.id, ""), p.precio) for p in lista.precios
    ]


def contra_la_entrega_anterior(
    actual: canonico.DocumentoLeido, anterior: canonico.DocumentoLeido
) -> Diferencia:
    return diferencia_entre_versiones(filas_de(anterior), filas_de(actual))


def contra_la_base_del_revisor(
    doc: canonico.DocumentoLeido, precios: Sequence[PrecioDeLista]
) -> tuple[Diferencia, Revaloracion]:
    """El paquete revalorado en memoria con la lista de quien revisa; lo que no empareja es
    «no contrastable» y no suma."""
    revalorado = revalorar(doc, precios)
    return diferencia_entre_versiones(filas_de(doc), revalorado.filas), revalorado


def declaracion_retroactiva(cadena: Mapping[str, Any]) -> str | None:
    """S3 §6.5: «Versiones 001 a 004 selladas el …», si la cadena del paquete trae eslabones
    retroactivos; `None` si no. Es la misma declaración de la hoja, leída del paquete."""
    retro = [e for e in cadena["eslabones"] if e.get("tipo") == "retroactivo"]
    if not retro:
        return None
    codigos = [e["codigo"] for e in retro]
    rango = codigos[0] if len(codigos) == 1 else f"{codigos[0]} a {codigos[-1]}"
    cuando = min(str(e["fecha_hora"]) for e in retro)[:10]
    plural = "Versión" if len(codigos) == 1 else "Versiones"
    return (f"{plural} {rango} selladas el {cuando}: prueban que no cambiaron desde esa fecha; "
            "antes no hay garantía.")


# --- quién cambió qué y quién revisa --------------------------------------------------------


def login_de(responsable: str) -> str | None:
    """`ana` de `Ana Pérez <ana> (tras restablecimiento)`; `None` si no hay `<login>`."""
    hallados = _LOGIN.findall(responsable or "")
    return hallados[-1] if hallados else None


def cambios_nuevos(
    cadena: Mapping[str, Any], huellas_previas: Sequence[str]
) -> list[dict[str, str]]:
    """Los `RegistroCambio` de las versiones que la entrega anterior no traía."""
    conocidas = set(huellas_previas)
    filas = []
    for e in cadena["eslabones"]:
        if e["huella_eslabon"] in conocidas:
            continue
        for fila in cadena.get("cambios", {}).get(e["codigo"], []):
            objeto, clave, campo, antes, despues, fuente, responsable, cuando = fila
            filas.append({
                "version": e["codigo"], "objeto": objeto, "clave": clave, "campo": campo,
                "antes": antes, "despues": despues, "fuente": fuente, "responsable": responsable,
                "fecha": cuando,
                "marca": "hecho tras un restablecimiento del administrador"
                if "(tras restablecimiento)" in responsable else "",
            })
    return filas


def revisor_armo(
    v: Verificacion, *, login_revisor: str, empresa_propia: tuple[str | None, str | None]
) -> list[str]:
    """Las versiones en que quien revisa figura como quien armó (P2, ratificada): solo si el
    paquete es de la empresa propia (firmado con su clave, o sin firma con su nombre) y su login
    es el del usuario emisor o el de algún eslabón. Vacío si no."""
    if v.manifiesto is None or v.cadena is None:
        return []
    nombre, huella = empresa_propia
    huella_clave = v.manifiesto.get("huella_clave")
    propia = (huella_clave is not None and huella_clave == huella) or (
        huella_clave is None and nombre is not None and v.manifiesto.get("empresa") == nombre
    )
    if not propia:
        return []
    donde = [e["codigo"] for e in v.cadena["eslabones"] if login_de(e["usuario"]) == login_revisor]
    if login_de(v.manifiesto.get("usuario_emisor", "")) == login_revisor and not donde:
        donde = [v.manifiesto["codigo"]]
    return donde


# --- recibir, guardar y dictaminar ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Recibido:
    verificacion: Verificacion
    paquete_id: int
    ruta: Path
    ya_recibido: bool
    avisos: tuple[str, ...]
    ultima_recibida: str


def _buscar_empresa(instalacion: Session):
    def buscar(huella: str) -> EmpresaConocida | None:
        fila = instalacion.scalars(
            select(EmpresaRegistrada).where(EmpresaRegistrada.huella == huella)
            .order_by(EmpresaRegistrada.id.desc())
        ).first()
        if fila is None:
            return None
        return EmpresaConocida(fila.empresa, fila.publica, fila.estado, fila.fecha_estado)

    return buscar


def recibir(
    datos: bytes,
    nombre: str,
    *,
    caso: Session,
    instalacion: Session,
    carpeta_paquetes: Path,
    revisor: str,
    ahora: datetime,
    mi_empresa: tuple[str | None, str | None] = (None, None),
) -> Recibido:
    """Verifica `datos`, guarda el archivo y su registro (una vez por SHA-256: 23h) y evalúa la
    anterioridad respecto de lo ya recibido. Un paquete «rechazado» no se guarda."""
    v = verificar(
        datos, buscar_empresa=_buscar_empresa(instalacion), recibido_en=ahora, mi_empresa=mi_empresa
    )
    if not v.legible or v.cadena is None:
        return Recibido(v, 0, Path(), False, (), "")
    existente = paq.buscar_por_huella(caso, v.sha256)
    huella_clave = v.manifiesto.get("huella_clave") or ""
    previos = paq.paquetes_del_proyecto(caso, v.manifiesto["proyecto"], huella_clave)
    anexos_huellas = {
        n: [e["huella"] for e in leer_json(b).get("entradas", [])]
        for n, b in v.archivos.items() if n in ("anexos/reajuste.json", NOMBRE_CONTROL)
    }
    anterioridad = evaluar_anterioridad(v.manifiesto, v.cadena, anexos_huellas, v.sha256, previos)
    avisos = (*v.avisos, *anterioridad.avisos)
    if existente is not None:
        return Recibido(v, existente["id"], Path(existente["ruta"]), True, avisos,
                        anterioridad.ultima_recibida)
    carpeta_paquetes.mkdir(parents=True, exist_ok=True)
    ruta = carpeta_paquetes / f"{v.sha256}-{nombre_seguro(nombre)}"
    ruta.write_bytes(datos)
    identificador = paq.registrar_recibido(
        caso, archivo=nombre_seguro(nombre), huella_archivo=v.sha256,
        paquete_id=str(v.manifiesto["paquete_id"]),
        destinatario=str(v.manifiesto.get("destinatario") or ""),
        ruta=str(ruta), empresa_declarada=str(v.empresa_declarada or ""),
        empresa_verificada=str(v.empresa_verificada or ""), huella_clave=huella_clave,
        estado=v.estado, proyecto=v.manifiesto["proyecto"], codigo=v.manifiesto["codigo"],
        emitido=datetime.fromisoformat(v.manifiesto["emitido"]),
        cadena=json.dumps([[e["codigo"], e["huella_eslabon"]] for e in v.cadena["eslabones"]]),
        huellas_anexos=json.dumps(anexos_huellas), recibido_por=revisor, fecha=ahora,
    )
    caso.commit()
    return Recibido(v, identificador, ruta, False, avisos, anterioridad.ultima_recibida)


def dictaminar(
    caso: Session, recibido: Recibido, *, resultado: str, notas: str, revisor: str,
    ahora: datetime, armo: bool,
) -> int:
    """El dictamen, atado al SHA-256 del archivo y al estado de verificación de ESE momento."""
    identificador = paq.registrar_dictamen(
        caso, paquete_id=recibido.paquete_id, huella_archivo=recibido.verificacion.sha256,
        resultado=resultado, notas=notas, usuario=revisor, fecha=ahora,
        estado_verificacion=recibido.verificacion.estado, revisor_armo=armo,
    )
    caso.commit()
    return identificador


@dataclass(frozen=True, slots=True)
class EntregaAnterior:
    """Lo que esta instalación recibió antes del mismo proyecto y emisor (maestro §3.3)."""

    codigo: str
    documento: canonico.DocumentoLeido
    huellas: tuple[str, ...]  # las huellas de eslabón que esa entrega ya traía


def entrega_anterior(
    caso: Session, instalacion: Session, v: Verificacion
) -> EntregaAnterior | None:
    """La última entrega del mismo proyecto y emisor emitida ANTES de `v`, releída del archivo
    guardado (con el mismo lector seguro). `None` si no hay, o si el archivo ya no está."""
    if v.manifiesto is None:
        return None
    emitido = datetime.fromisoformat(str(v.manifiesto["emitido"]))
    previas = [
        f for f in paq.paquetes_del_proyecto(
            caso, v.manifiesto["proyecto"], v.manifiesto.get("huella_clave") or "")
        if f["huella_archivo"] != v.sha256 and f["emitido"] < emitido
    ]
    if not previas:
        return None
    fila = max(previas, key=lambda f: f["emitido"])
    ruta = Path(fila["ruta"])
    if not ruta.is_file():
        return None
    antes = verificar(ruta.read_bytes(), buscar_empresa=_buscar_empresa(instalacion),
                      recibido_en=fila["fecha"])
    if not antes.legible:
        return None
    return EntregaAnterior(
        fila["codigo"], leer_documento(antes.archivos),
        tuple(huella for _, huella in json.loads(fila["cadena"])),
    )


def empresa_propia_para_revisar(instalacion: Session) -> tuple[str | None, str | None]:
    """`(nombre, huella de la clave activa)` de la empresa de esta instalación, para el aviso de
    «quien revisa es quien armó»; `None` donde falte."""
    propia = empresas.empresa_propia(instalacion)
    clave = empresas.clave_activa(instalacion)
    return (propia.nombre if propia else None, clave.huella if clave else None)


# --- tablas y Excel -------------------------------------------------------------------------


def tablas_de_revision(
    v: Verificacion, r: Reauditoria, diferencia: Diferencia | None, cambios: Sequence[dict],
) -> tuple[TablaExportable, ...]:
    """Las hojas Verificación, Hallazgos, Diferencias y Cambios (todo texto con el escape de M-1
    de `exportar_hoja`)."""
    verificacion = TablaExportable(
        "Verificación", ("Dato", "Valor"),
        (("Estado", v.estado), ("Motivo", v.motivo), ("Detalle", v.detalle),
         ("Empresa declarada", v.empresa_declarada or ""),
         ("Empresa verificada", v.empresa_verificada or ""), ("SHA-256", v.sha256),
         *(("Aviso", a) for a in v.avisos)),
    )
    hallazgos = TablaExportable(
        "Hallazgos", ("Origen", "Regla", "Severidad", "Descripción"),
        tuple(
            (origen, h.regla, h.severidad.name, h.descripcion)
            for origen, lote in (("No declarado por el emisor", r.nuevos),
                                 ("Declarado y ya no aparece", r.ya_no), ("Común", r.comunes))
            for h in lote
        ),
    )
    filas = (
        tuple((p.codigo_partida, p.descripcion, p.estado, p.desvio_cantidad, p.desvio_precio,
               p.desvio_total) for p in diferencia.partidas)
        if diferencia else ()
    )
    return (
        verificacion,
        hallazgos,
        TablaExportable("Diferencias", ("Partida", "Descripción", "Estado", "Δ cantidad",
                                        "Δ precio", "Δ total"), filas),
        TablaExportable(
            "Cambios", ("Versión", "Objeto", "Clave", "Campo", "Antes", "Después", "Fuente",
                        "Responsable", "Fecha", "Marca"),
            tuple(tuple(c[k] for k in _CAMPOS_DE_CAMBIO) for c in cambios),
        ),
    )


def excel_de_presupuesto(r: Reauditoria, *, extras: Sequence[TablaExportable] = ()) -> bytes:
    """El Excel del presupuesto del paquete REGENERADO desde `presupuesto.json` con
    `exportar_hoja` en esta instalación; nunca el del emisor (DA-S3-10)."""
    if r.resultado is None:
        raise ValueError("la reauditoría no terminó: no hay presupuesto que exportar")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "presupuesto.xlsx"
        exportar_hoja(
            r.resultado.presupuesto, r.resultado.informe, ruta, r.documento.parametros,
            hojas_extra=tuple(extras),
        )
        return ruta.read_bytes()


def excel_de_revision(
    v: Verificacion, r: Reauditoria, diferencia: Diferencia | None, cambios: Sequence[dict]
) -> bytes:
    return excel_de_presupuesto(r, extras=tablas_de_revision(v, r, diferencia, cambios))



# --- presupuesto externo en Excel (UC-05, 23d) y su plantilla ---------------------------------


def plantilla_uc05() -> bytes:
    """La plantilla descargable del formato UC-05: las cinco hojas de `core.budget.importacion`
    (su fuente única) y una fila de ejemplo en cada una."""
    libro = Workbook()
    datos = libro.active
    datos.title = HOJA_DATOS
    filas = {
        HOJA_DATOS: [COLUMNAS_DATOS, ("codigo", "EJ-001"), ("fecha", "2026-11-01"),
                     ("moneda", "USD"), ("dominio", "civil"), ("fcas", "6.00"),
                     ("bono_alimentacion", "1.00"), ("administracion", "0.15"),
                     ("utilidad", "0.10")],
        HOJA_PRESUPUESTO: [COLUMNAS_PRESUPUESTO, ("EJ-P1", "Relleno de ejemplo", "m3", "20",
                                                  "FILA-1", "", "{}", "{}")],
        HOJA_APU: [COLUMNAS_APU, ("EJ-P1", "Relleno de ejemplo", "m3", "8")],
        HOJA_INSUMOS: [
            COLUMNAS_INSUMOS,
            ("EJ-P1", "material", "Arena", "m3", "1.00", "14.00", "", ""),
            ("EJ-P1", "equipo", "Compactadora", "", "1", "71.00", "0.10", ""),
            ("EJ-P1", "mano de obra", "Obrero", "", "2", "10.25", "", "jornal"),
        ],
        HOJA_CURVA: [COLUMNAS_CURVA, ("Dia 1", "836.7975", "836.7975")],
    }
    for nombre, lineas in filas.items():
        hoja = datos if nombre == HOJA_DATOS else libro.create_sheet(nombre)
        for linea in lineas:
            hoja.append(list(linea))
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "plantilla.xlsx"
        libro.save(ruta)
        return ruta.read_bytes()


def auditar_excel_externo(ruta: Path):
    """UC-05 sin persistir: lee SOLO valores (nunca fórmulas ni vínculos externos) y audita en
    memoria con `REGLAS`. Siempre «no verificado»: un Excel no trae cadena ni firma."""
    importado = leer_presupuesto_tabular(ruta)
    return importado, auditar(importado.presupuesto, REGLAS)
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_ui_revision.py tests/integration/test_revision_recibir.py
tests/unit/test_auditoria_servicios.py tests/unit/test_arquitectura_s3.py -v -W error` → verde.
Run: `uv run ruff check auditoria ui/revision.py` → limpio.
- [ ] **Paso 5: Commit**
```bash
git add auditoria ui/revision.py
git commit -m "feat(revision): reauditoria en memoria y vista de quien revisa" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 20: La pantalla Revisar (UC-23) y el recorrido del paquete

**Rama:** `inc/080-s3-4-revision`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `ui/paginas/revisar.py`
- Modificar: `ui/app.py`, `ui/recorridos.py:25,143-170` (el recorrido «Entregar y revisar un
  paquete»), `tests/unit/test_ui_app.py`, `tests/unit/test_ui_recorridos.py`,
  `tests/unit/test_ui_importable.py`, `tests/unit/test_arquitectura_s5.py`
- Prueba: `tests/unit/test_ui_revisar.py`, `tests/unit/test_ui_roles.py`

**Interfaces:**
- Consume: `ui.revision.*` (tarea 19), `paquete.modelo`, `paquete.verificar.banner`,
  `ui.sesion.exigir` (tarea 6), `ui.texto_seguro.texto_seguro` (S1),
  `operacion.base_datos.preparar_base`.
- Produce:
  - `ui.paginas.revisar`: `def servicios_de_la_instalacion(caso: Session) -> revision.Servicios`
  - `ui.paginas.revisar`: `def render() -> None`
  - `ui.recorridos.NOMBRE_PAQUETE = "Entregar y revisar un paquete"` (un recorrido de dos pasos:
    entregar y revisar) y el menú completo de S3 en `ui.app.PAGINAS` (14 pantallas en el sandbox).

**La pantalla.** Quien revisa elige un archivo `.silice` (o el Excel de otra herramienta): el banner
dice el estado (verificado, no verificado, alterado, rechazado) con las palabras del spec; la
pestaña de reauditoría separa los hallazgos; la de diferencias muestra la entrega anterior y la
comparación con la lista propia; el aviso de P2 aparece solo cuando corresponde; el dictamen
(conforme, con observaciones, rechazado) pide notas si hay observaciones y queda atado al SHA-256
y al estado de ese momento. Todo texto del paquete pasa por `texto_seguro`. Trabaja con ids, no
con objetos ORM (Streamlit conserva el valor elegido entre ejecuciones). **Recorrido:** quien solo
arma ve el primer paso, quien solo revisa ve el segundo (RF-37 por rol).

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_ui_revisar.py`**
```python
"""Revisar (UC-23, RF-86/87; spec S3 §9): estado, reauditoría, aviso de P2, dictamen y Excel.

`st.file_uploader` no lo maneja `AppTest`: la prueba lo sustituye (con `monkeypatch`, que lo
devuelve al terminar) por un archivo en memoria con los octetos que dejó en `st.session_state`."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.budget.canonico import json_canonico
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from paquete import modelo as paq
from seguridad import empresas, firma
from seguridad.modelo import EmpresaRegistrada
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.instalacion import AHORA
from tests.fixtures.paginas_s3 import con_ficha, preparar
from tests.fixtures.paquetes import EMPRESA, paquete
from ui import revision
from ui import sesion as ui_sesion
from ui.sesion import MENSAJE_SIN_PERMISO

PAR = firma.generar_par()


def _pagina() -> None:
    from ui.paginas import revisar

    revisar.render()


def _sustituir(monkeypatch) -> None:
    import io

    import streamlit as st

    from ui import revision as rev
    from ui.paginas import revisar

    class Archivo(io.BytesIO):
        name = "recibido.silice"

    def subida(*_, key=None, **__):
        octetos = st.session_state.get("_archivos", {}).get(key)
        return Archivo(octetos) if octetos is not None else None

    monkeypatch.setattr(st, "file_uploader", subida)
    monkeypatch.setattr(revisar, "servicios_de_la_instalacion", lambda caso: rev.Servicios())


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()


@pytest.fixture
def caso_db(tmp_path: Path, monkeypatch) -> Path:
    ruta = tmp_path / "caso.db"
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    crear_esquema(motor)
    paq.crear_esquema_paquete(motor)
    motor.dispose()
    monkeypatch.setenv("SILICE_CASO", str(ruta))
    return ruta


def _registrar_emisora() -> None:
    with ui_sesion.instalacion() as bd:
        bd.add(EmpresaRegistrada(
            empresa=EMPRESA, rif="J-0", publica=PAR.publica,
            huella=firma.huella_completa(PAR.publica), estado="activa", comprobada_con="Ana",
            metodo="telefono", fecha_comprobacion=AHORA, registrada_por="admin"))
        bd.commit()


def _documento() -> bytes:
    return json_canonico(copy.deepcopy(EJEMPLO_V1))


def _abrir(monkeypatch, tmp_path: Path, archivos: dict, rol: str = "revisa",
           login: str = "luis") -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, rol, login=login)
    _sustituir(monkeypatch)
    _registrar_emisora()
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    at.session_state["_archivos"] = archivos
    return at.run()


def _firmado(**mas) -> bytes:
    return paquete(par=PAR, presupuesto=_documento(), anexos={}, **mas)


def test_un_paquete_verificado_muestra_su_banner_su_total_y_los_hallazgos(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": _firmado()})
    assert not at.exception
    assert any(s.value.startswith("Verificado: emitido por") for s in at.success)
    assert {m.label: m.value for m in at.metric}["Total recalculado"].startswith("836")
    assert any("no recibió una entrega anterior" in c.value for c in at.caption)
    assert at.get("download_button")


def test_un_paquete_sin_firma_se_audita_igual_y_se_dice_no_verificado(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path,
                {"rev_archivo": paquete(par=None, presupuesto=_documento(), anexos={})})
    assert any(w.value.startswith("No verificado") for w in at.warning)
    assert {m.label for m in at.metric} >= {"Total recalculado"}


def test_un_archivo_que_no_es_un_paquete_se_rechaza_con_mensaje_y_sin_traza(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": b"esto no es un zip"})
    assert not at.exception and at.error and not at.metric


def test_quien_revisa_y_figura_como_quien_armo_ve_el_aviso(monkeypatch, tmp_path, caso_db) -> None:
    ficha = preparar(monkeypatch, tmp_path, "arma", "revisa", login="ana")
    _sustituir(monkeypatch)
    _registrar_emisora()
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-0", "", "admin", AHORA)
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    at.session_state["_archivos"] = {
        "rev_archivo": paquete(par=None, presupuesto=_documento(), anexos={})}
    at = at.run()
    assert any("Usted figura como quien armó la versión 004, 005" in w.value for w in at.warning)


def test_otro_revisor_de_la_misma_empresa_no_ve_el_aviso(monkeypatch, tmp_path, caso_db) -> None:
    ficha = preparar(monkeypatch, tmp_path, "revisa", login="pedro")
    _sustituir(monkeypatch)
    _registrar_emisora()
    with ui_sesion.instalacion() as bd:
        empresas.guardar_empresa_propia(bd, EMPRESA, "J-0", "", "admin", AHORA)
    at = con_ficha(AppTest.from_function(_pagina, default_timeout=120), ficha)
    at.session_state["_archivos"] = {
        "rev_archivo": paquete(par=None, presupuesto=_documento(), anexos={})}
    assert not any("figura como quien armó" in w.value for w in at.run().warning)


def test_el_dictamen_se_guarda_atado_al_archivo_y_pide_notas_si_hay_observaciones(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": _firmado()})
    at.radio(key="rev_resultado").set_value("con observaciones")
    at.button(key="rev_enviar").click()
    at = at.run()
    assert any("necesita notas" in e.value for e in at.error)
    at.radio(key="rev_resultado").set_value("con observaciones")
    at.text_area(key="rev_notas").input("Falta la memoria de cálculo de R4")
    at.button(key="rev_enviar").click()
    at = at.run()
    assert any("Dictamen guardado" in s.value for s in at.success)
    motor = crear_motor(f"sqlite:///{caso_db.as_posix()}")
    with abrir_sesion(motor) as caso:
        [fila] = caso.execute(paq.paq_dictamen.select()).mappings().all()
    motor.dispose()
    assert (fila["resultado"], fila["usuario"], fila["estado_verificacion"]) == (
        "con observaciones", "Luis <luis>", "verificado")


def test_un_excel_externo_se_audita_en_memoria_y_se_dice_no_verificado(
    monkeypatch, tmp_path, caso_db
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_excel": revision.plantilla_uc05()})
    assert any("un Excel no trae cadena ni firma" in w.value for w in at.warning)
    assert any(m.label == "Total" and m.value.startswith("836") for m in at.metric)


@pytest.mark.parametrize("rol", ["arma", "administrador"])
def test_otros_roles_no_revisan_aunque_lleguen_por_la_url(
    monkeypatch, tmp_path, caso_db, rol
) -> None:
    at = _abrir(monkeypatch, tmp_path, {"rev_archivo": _firmado()}, rol=rol)
    assert [e.value for e in at.error] == [MENSAJE_SIN_PERMISO] and not at.metric
```
**`tests/unit/test_ui_roles.py`**
```python
"""Menú por rol con las pantallas de S3 (RF-80, RF-37; S3 §5.1, §5.7): quién ve Entregar, Revisar
y Administración. Lo genérico (cada `render()` exige su acción, la sesión, la barra) está en
`test_ui_marco.py`; aquí, las listas exactas por rol y el recorrido del paquete."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from seguridad.permisos import Rol
from tests.fixtures.paginas_s3 import con_ficha, preparar
from ui import sesion as ui_sesion
from ui.app import paginas_visibles, secciones_visibles
from ui.recorridos import RECORRIDOS

RUTA_APP = Path(__file__).resolve().parents[2] / "ui" / "app.py"


def _rutas(roles) -> list[str]:
    return [p.ruta_url for p in paginas_visibles(False, frozenset(roles))]


def test_el_rol_arma_ve_el_trabajo_y_la_investigacion_pero_no_revisar_ni_administrar() -> None:
    rutas = _rutas({Rol.ARMA})
    assert {"hoja", "entregar", "componer", "visor", "catalogo", "inicio"} <= set(rutas)
    assert not {"revisar", "administracion"} & set(rutas)


def test_el_rol_revisa_solo_ve_el_inicio_la_lectura_y_la_revision() -> None:
    assert _rutas({Rol.REVISA}) == ["inicio", "catalogo", "historico", "revisar"]


def test_el_administrador_solo_ve_el_inicio_y_la_administracion() -> None:
    assert _rutas({Rol.ADMINISTRADOR}) == ["inicio", "administracion"]


def test_las_secciones_siguen_el_orden_de_s3_y_omiten_las_vacias() -> None:
    assert tuple(secciones_visibles(False, frozenset({Rol.REVISA}))) == ("Trabajo", "Revision")
    assert tuple(secciones_visibles(False, frozenset({Rol.ADMINISTRADOR}))) == (
        "Trabajo", "Administracion")


def test_ningun_recorrido_apunta_a_una_pantalla_que_el_rol_no_ve() -> None:
    """RF-37 con roles: quien arma ve completos los recorridos de trabajo y, del recorrido del
    paquete, solo el paso de entregar; quien revisa, solo el de revisar."""
    visibles = {p.ruta_url for p in paginas_visibles(False, frozenset({Rol.ARMA}))}
    for recorrido in RECORRIDOS[:3]:
        assert recorrido.visible_en(visibles).pasos == recorrido.pasos
    paquete = RECORRIDOS[3]
    assert [p.pagina for p in paquete.visible_en(visibles).pasos] == ["entregar"]
    de_revision = {p.ruta_url for p in paginas_visibles(False, frozenset({Rol.REVISA}))}
    assert [p.pagina for p in paquete.visible_en(de_revision).pasos] == ["revisar"]
    assert RECORRIDOS[0].visible_en(de_revision).pasos[0].pagina == "catalogo"


def _aplicacion(monkeypatch, tmp_path: Path, *roles: str) -> AppTest:
    ficha = preparar(monkeypatch, tmp_path, *roles)
    monkeypatch.setenv("SILICE_CASO", str(tmp_path / "caso.db"))
    at = AppTest.from_file(str(RUTA_APP), default_timeout=120)
    return con_ficha(at, ficha).run()


def test_la_aplicacion_arma_el_menu_con_las_secciones_del_rol(monkeypatch, tmp_path) -> None:
    import streamlit as st

    llamadas: list = []
    original = st.navigation

    def espia(paginas, **kwargs):
        llamadas.append(list(paginas))
        return original(paginas, **kwargs)

    monkeypatch.setattr(st, "navigation", espia)
    at = _aplicacion(monkeypatch, tmp_path, "revisa")
    assert not at.exception and llamadas == [["Trabajo", "Revision"]]
    assert any("Sesión: Luis (revisa)" in c.value for c in at.sidebar.caption)


@pytest.fixture(autouse=True)
def _cerrar_motores():
    yield
    ui_sesion.limpiar_motores()
```
  El marco lista la pantalla en su sección y el recorrido existe:
```diff
--- a/ui/app.py
+++ b/ui/app.py
@@ -80,4 +80,5 @@
     hoja,
     inicio,
+    revisar,
     similares,
     simulador,
@@ -89,4 +90,5 @@
 VALOR_MODO_ENTREGA = "1"
 SECCION_TRABAJO = "Trabajo"
+SECCION_REVISION = "Revision"
 SECCION_INVESTIGACION = "Investigacion"
 SECCION_ADMINISTRACION = "Administracion"
@@ -134,4 +136,6 @@
     DefinicionPagina(entregar.render, "Entregar paquete", SECCION_TRABAJO, "UC-22",
                      Accion.ENTREGAR_PAQUETE),
+    DefinicionPagina(revisar.render, "Revisar un paquete", SECCION_REVISION, "UC-23",
+                     Accion.REVISAR_PAQUETE),
     DefinicionPagina(
         escenarios.render, "Escenarios de sensibilidad", SECCION_INVESTIGACION, "UC-08", _EDITA
```
```diff
--- a/tests/unit/test_ui_app.py
+++ b/tests/unit/test_ui_app.py
@@ -27,4 +27,5 @@
     SECCION_ADMINISTRACION,
     SECCION_INVESTIGACION,
+    SECCION_REVISION,
     SECCION_TRABAJO,
     VARIABLE_MODO_ENTREGA,
@@ -50,4 +51,5 @@
 )
 
+TITULOS_REVISION = ("Revisar un paquete",)
 TITULOS_ADMINISTRACION = ("Administracion",)
 
@@ -66,4 +68,5 @@
     "similares": "UC-03",
     "entregar": "UC-22",
+    "revisar": "UC-23",
     "administracion": "UC-21",
 }
@@ -77,10 +80,11 @@
 
 
-def test_sin_modo_entrega_tres_secciones_en_el_orden_del_trabajo() -> None:
-    """S3 §5.7 enmienda RF-42: Administración se suma a las dos de siempre."""
+def test_sin_modo_entrega_cuatro_secciones_en_el_orden_del_trabajo() -> None:
+    """S3 §5.7 enmienda RF-42: de dos a cuatro secciones, visibles según el rol."""
     secciones = secciones_visibles(False)
     assert tuple(secciones) == (
-        SECCION_TRABAJO, SECCION_INVESTIGACION, SECCION_ADMINISTRACION)
+        SECCION_TRABAJO, SECCION_REVISION, SECCION_INVESTIGACION, SECCION_ADMINISTRACION)
     assert _titulos(secciones[SECCION_TRABAJO]) == TITULOS_TRABAJO
+    assert _titulos(secciones[SECCION_REVISION]) == TITULOS_REVISION
     assert _titulos(secciones[SECCION_INVESTIGACION]) == TITULOS_INVESTIGACION
     assert _titulos(secciones[SECCION_ADMINISTRACION]) == TITULOS_ADMINISTRACION
@@ -89,5 +93,5 @@
 def test_modo_entrega_omite_investigacion_y_conserva_todo_trabajo() -> None:
     secciones = secciones_visibles(True)
-    assert tuple(secciones) == (SECCION_TRABAJO, SECCION_ADMINISTRACION)
+    assert tuple(secciones) == (SECCION_TRABAJO, SECCION_REVISION, SECCION_ADMINISTRACION)
     assert secciones[SECCION_TRABAJO] == secciones_visibles(False)[SECCION_TRABAJO]
 
@@ -110,5 +114,5 @@
 
 
-def test_las_siete_pantallas_con_caso_de_uso_lo_declaran() -> None:
+def test_las_ocho_pantallas_con_caso_de_uso_lo_declaran() -> None:
     declarados = {p.ruta_url: p.caso_uso for p in PAGINAS if p.caso_uso is not None}
     assert declarados == CASOS_DE_USO
@@ -319,5 +323,5 @@
 
 
-def test_la_aplicacion_declara_la_navegacion_arriba_con_los_tres_grupos(
+def test_la_aplicacion_declara_la_navegacion_arriba_con_los_cuatro_grupos(
     monkeypatch, tmp_path: Path
 ) -> None:
@@ -338,5 +342,5 @@
     assert kwargs.get("position") == "top"
     assert list(paginas) == [
-        SECCION_TRABAJO, SECCION_INVESTIGACION, SECCION_ADMINISTRACION]
+        SECCION_TRABAJO, SECCION_REVISION, SECCION_INVESTIGACION, SECCION_ADMINISTRACION]
 
 
@@ -358,10 +362,10 @@
     paginas, kwargs = llamadas[0]
     assert kwargs.get("position") == "top"
-    assert list(paginas) == [SECCION_TRABAJO, SECCION_ADMINISTRACION]
-
-
-def test_son_trece_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
+    assert list(paginas) == [SECCION_TRABAJO, SECCION_REVISION, SECCION_ADMINISTRACION]
+
+
+def test_son_catorce_pantallas_y_la_hoja_va_justo_despues_de_elaborar() -> None:
     rutas = [p.ruta_url for p in PAGINAS]
-    assert len(rutas) == 13
+    assert len(rutas) == 14
     assert rutas.index("hoja") == rutas.index("elaborar") + 1
     assert pagina_por_ruta("hoja").seccion == SECCION_TRABAJO
@@ -429,3 +433,3 @@
     assert "Importar plano" in rotulos
     assert "Guardar version" in rotulos
-    assert list(llamadas[0]) == [SECCION_TRABAJO, SECCION_ADMINISTRACION]
+    assert list(llamadas[0]) == [SECCION_TRABAJO, SECCION_REVISION, SECCION_ADMINISTRACION]
```
```diff
--- a/tests/unit/test_ui_recorridos.py
+++ b/tests/unit/test_ui_recorridos.py
@@ -12,4 +12,5 @@
 from ui.recorridos import (
     NOMBRE_DEMOSTRACION,
+    NOMBRE_PAQUETE,
     NOMBRE_PRECIOS,
     NOMBRE_PRESUPUESTO,
@@ -26,10 +27,19 @@
 
 
-def test_hay_tres_recorridos_en_el_orden_declarado() -> None:
+def test_hay_cuatro_recorridos_en_el_orden_declarado() -> None:
     assert tuple(r.nombre for r in RECORRIDOS) == (
         NOMBRE_DEMOSTRACION,
         NOMBRE_PRESUPUESTO,
         NOMBRE_PRECIOS,
+        NOMBRE_PAQUETE,
     )
+
+
+def test_el_recorrido_del_paquete_pasa_por_entregar_y_revisar() -> None:
+    recorrido = recorrido_por_nombre(NOMBRE_PAQUETE)
+    assert [paso.pagina for paso in recorrido.pasos] == ["entregar", "revisar"]
+    # quien solo arma ve el primer paso; quien solo revisa, el segundo (RF-37 por rol)
+    assert [p.pagina for p in recorrido.visible_en({"entregar"}).pasos] == ["entregar"]
+    assert [p.pagina for p in recorrido.visible_en({"revisar"}).pasos] == ["revisar"]
 
 
```
  `tests/unit/test_ui_importable.py`: `"ui.revision"` entra a `MODULOS_SIN_PAGINA` y la cifra de
  páginas sube en uno. `tests/unit/test_arquitectura_s5.py`: `"revisar"` entra a
  `PAGINAS_QUE_ABREN_EL_CASO`.
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_ui_revisar.py tests/unit/test_ui_roles.py
tests/unit/test_ui_app.py tests/unit/test_ui_recorridos.py tests/unit/test_ui_importable.py -v -W
error`
Esperado: `test_ui_revisar` FAIL con `ModuleNotFoundError: No module named 'ui.paginas.revisar'`
dentro de la página de prueba; `test_ui_roles` e `test_ui_recorridos` FAIL por la pantalla y el
recorrido que faltan.
```bash
git add tests/unit/test_ui_revisar.py tests/unit/test_ui_roles.py tests/unit/test_ui_app.py \
  tests/unit/test_ui_recorridos.py tests/unit/test_ui_importable.py \
  tests/unit/test_arquitectura_s5.py
git commit -m "test(ui): pantalla Revisar, menu por rol y recorrido del paquete, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`ui/paginas/revisar.py`**
```python
"""Revisar un paquete `.silice` o un presupuesto de otra herramienta (UC-23; spec S3 §9 y §10).

Quien revisa elige un archivo y la pantalla lo **verifica** (banner de estado), lo **reaudita** con
las reglas de esta instalación, lo **compara** con la entrega anterior y con su propia lista de
precios, muestra **quién cambió qué**, avisa si quien revisa es quien armó, regenera el Excel y
guarda el **dictamen** atado al SHA-256 del archivo. Todo en memoria: el caso no cambia salvo el
registro de lo recibido. Todo texto del paquete pasa por `texto_seguro`. La pantalla trabaja con
ids, no con objetos de otro ciclo (Streamlit conserva el valor elegido entre ejecuciones).
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.budget.comparacion import Diferencia
from core.catalog import abrir_sesion_de_escritura, crear_motor
from core.verification.texto import formatear_decimal
from operacion.base_datos import ErrorDeBase, preparar_base
from operacion.config import carpeta_datos
from paquete import modelo as paq
from paquete.formato import PaqueteRechazado
from paquete.verificar import banner
from seguridad.json_estricto import JsonRechazado
from seguridad.permisos import Accion
from ui import revision
from ui import sesion as ui_sesion
from ui.caso import ruta_caso
from ui.texto_seguro import texto_seguro

COLORES = {"verde": st.success, "ambar": st.warning, "rojo": st.error}
CARPETA_PAQUETES = "paquetes"


def _ahora() -> datetime:
    return ui_sesion.ahora()


def servicios_de_la_instalacion(caso: Session) -> revision.Servicios:
    """La referencia MaPreX y las tasas de ESTA instalación (S1). Las pruebas lo sustituyen."""
    from auditoria.servicios import servicios_de_la_instalacion as armar

    return armar(caso)


def _tabla_diferencia(d: Diferencia, titulo: str) -> None:
    st.subheader(titulo)
    columnas = st.columns(3)
    columnas[0].metric("Total antes", formatear_decimal(d.total_1))
    columnas[1].metric("Total después", formatear_decimal(d.total_2))
    columnas[2].metric("Diferencia", formatear_decimal(d.total_2 - d.total_1))
    st.caption(f"Por cantidad: {formatear_decimal(d.desvio_cantidad)}. "
               f"Por precio: {formatear_decimal(d.desvio_precio)}.")
    st.dataframe(
        [{"Partida": texto_seguro(p.codigo_partida), "Descripción": texto_seguro(p.descripcion),
          "Estado": p.estado, "Δ cantidad": str(p.desvio_cantidad),
          "Δ precio": str(p.desvio_precio), "Δ total": str(p.desvio_total)}
         for p in d.partidas if p.estado != "igual"],
        hide_index=True,
    )


def _hallazgos(r: revision.Reauditoria) -> None:
    for titulo, lote in (("El emisor no los declaró", r.nuevos),
                         ("Los declaró y ya no aparecen", r.ya_no), ("En común", r.comunes)):
        st.subheader(f"{titulo} ({len(lote)})")
        st.dataframe(
            [{"Regla": h.regla, "Severidad": h.severidad.name,
              "Descripción": texto_seguro(h.descripcion)} for h in lote],
            hide_index=True,
        )


def _diferencias_de_precio(r: revision.Reauditoria) -> None:
    if not r.diferencias:
        st.success("Los precios y totales que declara el paquete coinciden con los recalculados.")
        return
    st.error("Hay precios o totales declarados que no coinciden con el recálculo.")
    st.dataframe(
        [{"Partida": texto_seguro(d.codigo_partida), "Campo": d.campo,
          "Declarado": str(d.declarado), "Recalculado": str(d.recalculado),
          "Diferencia": str(d.monto)} for d in r.diferencias],
        hide_index=True,
    )


def _contra_mi_lista(caso: Session, r: revision.Reauditoria) -> None:
    listas = {x.id: x for x in caso.scalars(select(models.ListaPrecios).order_by(
        models.ListaPrecios.fecha_vigencia.desc()))}
    if not listas:
        st.caption("Este caso no tiene listas de precios para contrastar.")
        return
    eleccion = st.selectbox("Contrastar con mi lista", list(listas), key="rev_lista",
                            format_func=lambda i: texto_seguro(listas[i].nombre))
    precios = revision.precios_de_lista(caso, listas[eleccion])
    diferencia, revalorado = revision.contra_la_base_del_revisor(r.documento, precios)
    _tabla_diferencia(diferencia, "El paquete con los precios de mi lista")
    if revalorado.no_contrastables:
        st.caption("No contrastables (no están en mi lista; no suman): " + ", ".join(
            texto_seguro(n.insumo) for n in revalorado.no_contrastables))


def _cambios(v, previa: revision.EntregaAnterior | None) -> Sequence[dict]:
    cambios = revision.cambios_nuevos(v.cadena, previa.huellas if previa else ())
    st.subheader("Quién cambió qué" + (" desde la entrega anterior" if previa else ""))
    st.dataframe(
        [{k: texto_seguro(str(x)) for k, x in c.items()} for c in cambios], hide_index=True)
    return cambios


def _dictamen(caso: Session, recibido: revision.Recibido, armo: bool, login: str) -> None:
    antes = paq.dictamenes_de(caso, recibido.verificacion.sha256)
    for d in antes:
        st.caption(f"Dictamen anterior: {texto_seguro(d['resultado'])} · "
                   f"{texto_seguro(d['usuario'])} · {d['fecha']:%Y-%m-%d %H:%M}")
    with st.form("rev_dictamen", clear_on_submit=True):
        resultado = st.radio("Dictamen", paq.RESULTADOS, key="rev_resultado")
        notas = st.text_area("Notas", key="rev_notas")
        enviar = st.form_submit_button("Guardar dictamen", type="primary", key="rev_enviar")
    if not enviar:
        return
    try:
        revision.dictaminar(caso, recibido, resultado=resultado, notas=notas,
                            revisor=ui_sesion.responsable_actual(), ahora=_ahora(), armo=armo)
    except ValueError as error:
        st.error(texto_seguro(str(error)))
        return
    st.success("Dictamen guardado, atado al SHA-256 de este archivo.")


def _paquete() -> None:
    sesion = ui_sesion.sesion_actual()
    archivo = st.file_uploader("Paquete .silice", key="rev_archivo")
    if archivo is None:
        st.caption("Elija el archivo `.silice` que recibió.")
        return
    ruta = ruta_caso()
    try:
        preparar_base(ruta)  # RV-5: la única puerta a la base del caso
    except ErrorDeBase as error:
        st.error(texto_seguro(str(error)))
        return
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion_de_escritura(motor) as caso, ui_sesion.instalacion() as bd:
            mi_empresa = revision.empresa_propia_para_revisar(bd)
            recibido = revision.recibir(
                archivo.getvalue(), archivo.name, caso=caso, instalacion=bd,
                carpeta_paquetes=carpeta_datos() / CARPETA_PAQUETES, revisor=sesion.usuario,
                ahora=_ahora(), mi_empresa=mi_empresa)
            v = recibido.verificacion
            COLORES.get(banner(v, texto_seguro)[0], st.error)(banner(v, texto_seguro)[1])
            if recibido.ultima_recibida:
                st.caption("Esta instalación ya había recibido la "
                           + texto_seguro(recibido.ultima_recibida) + ".")
            for aviso in recibido.avisos:
                st.warning(texto_seguro(aviso))
            retroactiva = revision.declaracion_retroactiva(v.cadena) if v.cadena else None
            if retroactiva:
                st.caption(texto_seguro(retroactiva))
            if not v.legible:
                st.error(texto_seguro(v.detalle))
                return
            donde = revision.revisor_armo(v, login_revisor=sesion.login, empresa_propia=mi_empresa)
            if donde:
                st.warning("Usted figura como quien armó la versión "
                           + ", ".join(texto_seguro(codigo) for codigo in donde)
                           + ": su dictamen lo dejará registrado.")
            r = revision.reauditar(v, servicios_de_la_instalacion(caso))
            for aviso in r.avisos:
                st.warning(texto_seguro(aviso))
            if r.resultado is None:
                return
            st.metric("Total recalculado", formatear_decimal(r.total_recalculado))
            st.caption("Reglas corridas: " + ", ".join(texto_seguro(c) for c in r.contextos) + ".")
            _diferencias_de_precio(r)
            _hallazgos(r)
            previa = revision.entrega_anterior(caso, bd, v)
            diferencia = None
            if previa is not None:
                diferencia = revision.contra_la_entrega_anterior(r.documento, previa.documento)
                _tabla_diferencia(
                    diferencia, f"Contra la entrega anterior ({texto_seguro(previa.codigo)})")
            else:
                st.caption("Esta instalación no recibió una entrega anterior de este proyecto.")
            _contra_mi_lista(caso, r)
            cambios = _cambios(v, previa)
            st.download_button(
                "Descargar el Excel de la revisión",
                revision.excel_de_revision(v, r, diferencia, cambios),
                file_name=f"revision-{v.sha256[:12]}.xlsx", key="rev_bajar_excel")
            _dictamen(caso, recibido, bool(donde), sesion.login)
    except (PaqueteRechazado, JsonRechazado, ValueError) as error:
        st.error(texto_seguro(str(error)))
    finally:
        motor.dispose()


def _excel_externo() -> None:
    st.download_button("Descargar la plantilla del formato", revision.plantilla_uc05(),
                       file_name="plantilla-presupuesto.xlsx", key="rev_plantilla")
    archivo = st.file_uploader("Presupuesto en Excel", type=["xlsx"], key="rev_excel")
    if archivo is None:
        return
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "externo.xlsx"
        ruta.write_bytes(archivo.getvalue())
        try:
            importado, informe = revision.auditar_excel_externo(ruta)
        except (ValueError, KeyError) as error:
            st.error(texto_seguro(str(error)))
            return
    st.warning("No verificado: un Excel no trae cadena ni firma. Se audita igual.")
    st.metric("Total", formatear_decimal(importado.presupuesto.total))
    st.dataframe(
        [{"Regla": h.regla, "Severidad": h.severidad.name,
          "Descripción": texto_seguro(h.descripcion)} for h in informe.hallazgos],
        hide_index=True,
    )


def render() -> None:
    ui_sesion.exigir(Accion.REVISAR_PAQUETE)
    pestanas = st.tabs(["Paquete .silice", "Presupuesto en Excel"])
    with pestanas[0]:
        _paquete()
    with pestanas[1]:
        _excel_externo()
```
  El recorrido «Entregar y revisar un paquete» (constante y recorrido):
```diff
--- a/ui/recorridos.py
+++ b/ui/recorridos.py
@@ -24,4 +25,5 @@
 NOMBRE_PRESUPUESTO = "Armar un presupuesto"
 NOMBRE_PRECIOS = "Actualizar precios"
+NOMBRE_PAQUETE = "Entregar y revisar un paquete"
 
 
@@ -143,4 +151,25 @@
                 "pulse «Revalorar presupuesto».",
                 "Aparecen el comparativo por partida y la auditoria de la version nueva.",
+            ),
+        ),
+    ),
+    Recorrido(
+        NOMBRE_PAQUETE,
+        "Para quien entrega y quien recibe: arma el paquete auditado de una version y lo revisa "
+        "como lo haria otra persona (con las dos cuentas, o con una que tenga los dos roles).",
+        (
+            Paso(
+                "Entregar el paquete",
+                "entregar",
+                "Elija el proyecto y la version, revise el resumen y la cadena, escriba la "
+                "contraseña de la clave de firma y pulse «Generar paquete».",
+                "Se descarga el archivo .silice y la pantalla dice si va firmado.",
+            ),
+            Paso(
+                "Revisar el paquete",
+                "revisar",
+                "Suba el .silice: lea el estado de verificacion, la reauditoria y las diferencias "
+                "con la entrega anterior; guarde su dictamen.",
+                "El dictamen queda registrado con el estado de verificacion de ese momento.",
             ),
         ),
```
  y la entrada de la pantalla en la sección Revisión (`SECCION_REVISION`, ya incluida en el diff de
  `ui/app.py` del paso 1).
- [ ] **Paso 4: Correrlas y ver el verde** (y las pantallas, que ahora comparten el marco)
Run: `uv run pytest tests/unit/test_ui_revisar.py tests/unit/test_ui_roles.py
tests/unit/test_ui_marco.py tests/unit/test_ui_app.py tests/unit/test_ui_recorridos.py
tests/unit/test_ui_importable.py tests/unit/test_arquitectura_s5.py -v -W error` → verde.
- [ ] **Paso 5: Commit**
```bash
git add ui/paginas/revisar.py ui/app.py ui/recorridos.py
git commit -m "feat(ui): pantalla Revisar con dictamen y el recorrido de entregar y revisar" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 21: `POST /v1/auditorias`, claves de API, tope de cuerpo y hosts

**Rama:** `inc/080-s3-4-revision`   **Rol:** sf-ingeniero-interfaz
**Archivos:**
- Crear: `api/seguridad.py`, `api/rutas/auditorias.py`
- Modificar: `api/main.py:3-30`, `docs/api.json` (regenerado), `tests/integration/conftest.py:69`,
  `tests/integration/test_api_preparar_base.py:24`
- Prueba: `tests/integration/test_api_auditorias.py`

**Interfaces:**
- Consume: `seguridad.claves_api.*` y `seguridad.eventos` (tareas 5 y 17), `operacion.instalacion.
  sesion_de_instalacion` (tarea 3), `auditoria.reauditoria.{Servicios, leer_documento_json,
  reauditar}` y `auditoria.servicios.servicios_de_la_instalacion` (tarea 19),
  `api.dependencias.SesionDep`, `paquete.formato.PaqueteRechazado`, `seguridad.json_estricto` (tarea
  4), `adapters.espacio.serie` (tarea 11).
- Produce:
  - `api.seguridad`: `def ahora() -> datetime`
  - `api.seguridad`: `def hosts_permitidos(entorno: Mapping[str, str] | None=None) -> list[str]`
  - `api.seguridad`: `def sesion_instalacion() -> Iterator[Session]`
  - `api.seguridad`: `def exigir_clave(instalacion: InstalacionDep, x_silice_clave:
      Annotated[str | None, Header(alias=CABECERA)]=None) -> ClaveApi`
  - `api.seguridad`: `class LimiteDeCuerpo`
  - `api.rutas.auditorias`: `def servicios_de_la_api(sesion: SesionDep) -> Servicios`
  - `api.rutas.auditorias`: `class HallazgoRespuesta(BaseModel)`
  - `api.rutas.auditorias`: `class DiferenciaRespuesta(BaseModel)`
  - `api.rutas.auditorias`: `class AuditoriaRespuesta(BaseModel)`
  - `api.rutas.auditorias`: `def auditar_documento(peticion: Request, clave: ClaveDep,
      servicios: ServiciosDep) -> AuditoriaRespuesta`
  - La ruta `POST /v1/auditorias` y la dependencia `servicios_de_la_api` (las pruebas la
    sustituyen).

**La ruta.** El cuerpo es JSON con `documento` (el documento canónico), `fecha_evaluacion` (ISO,
**obligatoria**: la misma petición da siempre el mismo informe, RP8-11) y, opcional,
`anexo_espacio`. Se lee con el lector estricto (422 ante `NaN`, claves duplicadas, cifras fuera del
patrón o más de 64 niveles). Reaudita en memoria con las reglas de ESTA instalación y devuelve el
informe con los montos como texto; **no guarda nada**. **Seguridad:** toda ruta `/v1/` exige
`X-Silice-Clave:
<identificador>.<secreto>` (RP8-12); sin clave, con una desconocida o con una revocada responde 401
con el mismo mensaje y deja un `fallo` en `evento_acceso`; `LimiteDeCuerpo` corta en 20 MiB (413)
mirando `Content-Length` y, si falta o miente, contando los bytes a medida que llegan; el
`TrustedHostMiddleware` rechaza hosts ajenos (DNS rebinding) y acepta los que ponga
`SILICE_HOSTS_PERMITIDOS`. El filtro de IP no es un control: el control es la clave (S3 §12).

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/integration/test_api_auditorias.py`**
```python
"""`POST /v1/auditorias`: clave de API, tope de cuerpo, hosts y lector estricto (RF-88, RNF-16;
spec S3 §10 y §13.2). La instalación es una `instalacion.db` temporal."""

from __future__ import annotations

import asyncio
import copy
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import seguridad as api_seguridad
from api.main import app
from api.rutas.auditorias import servicios_de_la_api
from auditoria.reauditoria import ReferenciaDeMercado, Servicios
from core.budget.canonico import json_canonico
from seguridad import claves_api
from seguridad.modelo import EventoAcceso
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.instalacion import AHORA, instalacion

HOY = "2026-11-10"


@pytest.fixture
def api(tmp_path: Path):
    """`(cliente, clave, sesión de instalación)`; la clave de API ya existe y es válida."""
    with instalacion(tmp_path) as bd:
        clave, _ = claves_api.crear(bd, "plugin de prueba", "admin", AHORA)
        app.dependency_overrides[api_seguridad.sesion_instalacion] = lambda: bd
        app.dependency_overrides[servicios_de_la_api] = lambda: Servicios()
        with TestClient(app, base_url="http://127.0.0.1") as cliente:
            yield cliente, clave, bd
        app.dependency_overrides.clear()


def cuerpo(**cambios) -> bytes:
    objeto = {"documento": copy.deepcopy(EJEMPLO_V1), "fecha_evaluacion": HOY}
    objeto.update(cambios)
    return json.dumps(objeto).encode()


def post(cliente, clave, datos: bytes, **cabeceras):
    return cliente.post(
        "/v1/auditorias", content=datos,
        headers={api_seguridad.CABECERA: clave, "content-type": "application/json", **cabeceras},
    )


def test_con_clave_valida_devuelve_el_informe_y_los_montos_como_texto(api) -> None:
    cliente, clave, _ = api
    r = post(cliente, clave, cuerpo())
    assert r.status_code == 200, r.text
    datos = r.json()
    assert datos["fecha_evaluacion"] == HOY and datos["termino"] is True
    assert datos["total_recalculado"] == "836.79750000" and datos["diferencias"] == []
    assert datos["contextos"] == ["R1-R7", "R11-R12"]
    assert isinstance(datos["total_recalculado"], str)  # los montos viajan como texto


def test_la_misma_peticion_da_siempre_el_mismo_informe(api) -> None:
    cliente, clave, _ = api
    assert post(cliente, clave, cuerpo()).json() == post(cliente, clave, cuerpo()).json()


def test_declarado_contra_recalculado_se_informa_con_su_monto(api) -> None:
    cliente, clave, _ = api
    documento = copy.deepcopy(EJEMPLO_V1)
    documento["renglones"][0]["precio_unitario"] = "99.00"
    r = post(cliente, clave, cuerpo(documento=documento))
    [d] = [d for d in r.json()["diferencias"] if d["campo"] == "precio_unitario"]
    assert (d["declarado"], d["recalculado"]) == ("99.00", "41.83987500")
    assert Decimal(d["monto"]) == (Decimal("99.00") - Decimal("41.83987500")) * 20


def test_con_el_anexo_de_espacio_corren_r8_a_r10_y_r15(api) -> None:
    from adapters.espacio.serie import espacio_a_objeto
    from tests.fixtures.espacio_of001 import espacio_of001

    cliente, clave, _ = api
    r = post(cliente, clave, cuerpo(anexo_espacio=espacio_a_objeto(espacio_of001())))
    assert r.json()["contextos"] == ["R1-R7", "R8-R10", "R15", "R11-R12"]
    assert sum(1 for h in r.json()["no_declarados"] if h["regla"] == "R8") == 33


def test_r11_usa_los_servicios_de_la_instalacion_que_revisa(api) -> None:
    cliente, clave, _ = api
    documento = copy.deepcopy(EJEMPLO_V1)
    documento["composiciones"][0]["lineas"][0]["referencia"] = "MP-0042"
    app.dependency_overrides[servicios_de_la_api] = lambda: Servicios(
        referencia_de=lambda c: ReferenciaDeMercado("MP-0042", Decimal("10.00"), "USD", None)
    )
    r = post(cliente, clave, cuerpo(documento=documento))
    [r11] = [h for h in r.json()["no_declarados"] if h["regla"] == "R11"
             and h["severidad"] == "ADVERTENCIA"]
    assert "MP-0042" in r11["descripcion"]


def test_sin_clave_o_con_una_mala_o_revocada_es_401_con_el_mismo_mensaje(api) -> None:
    cliente, clave, bd = api
    revocada, fila = claves_api.crear(bd, "otra", "admin", AHORA)
    claves_api.revocar(bd, fila.id, "admin", AHORA)
    antes = bd.query(EventoAcceso).count()
    mensajes = set()
    for presentada in (None, "", "no-es-una-clave", "ABCDEFGH.inventada", revocada):
        r = cliente.post("/v1/auditorias", content=cuerpo(),
                         headers={api_seguridad.CABECERA: presentada} if presentada is not None
                         else {})
        assert r.status_code == 401
        mensajes.add(r.json()["detalle"])
    assert mensajes == {api_seguridad.MENSAJE_SIN_CLAVE}
    assert bd.query(EventoAcceso).count() == antes + 5  # cada rechazo queda en el registro
    assert post(cliente, clave, cuerpo()).status_code == 200  # la buena sigue sirviendo


def test_toda_ruta_v1_exige_la_clave(api) -> None:
    """Recorre las rutas publicadas en OpenAPI: ninguna de `/v1/` responde sin clave."""
    cliente, _, _ = api
    rutas = [(p, m) for p, ops in app.openapi()["paths"].items() if p.startswith("/v1/")
             for m in ops if m in {"get", "post", "put", "patch", "delete"}]
    assert ("/v1/auditorias", "post") in rutas
    for ruta, metodo in rutas:
        r = cliente.request(metodo.upper(), ruta.replace("{", "x").replace("}", ""))
        assert r.status_code == 401, (metodo, ruta, r.status_code)


def test_un_host_ajeno_se_rechaza_contra_el_dns_rebinding(api) -> None:
    cliente, clave, _ = api
    r = cliente.post("/v1/auditorias", content=cuerpo(),
                     headers={api_seguridad.CABECERA: clave, "host": "evil.example.com"})
    assert r.status_code == 400


def test_los_hosts_extra_los_pone_el_administrador() -> None:
    assert api_seguridad.hosts_permitidos({}) == ["127.0.0.1", "localhost"]
    extra = {"SILICE_HOSTS_PERMITIDOS": "192.168.1.20, obra.local"}
    assert api_seguridad.hosts_permitidos(extra) == [
        "127.0.0.1", "localhost", "192.168.1.20", "obra.local"]


@pytest.mark.parametrize("malo", [
    b'{"documento": NaN, "fecha_evaluacion": "2026-11-10"}',
    b'{"documento": {}, "documento": {}, "fecha_evaluacion": "2026-11-10"}',
    b'{"documento": {"x": 1E+999999999}, "fecha_evaluacion": "2026-11-10"}',
    b"[" * 65 + b"]" * 65,
    b'{"documento": {}}',
    b'{"documento": {}, "fecha_evaluacion": "ayer"}',
    b"no es json",
])
def test_json_hostil_o_incompleto_es_422_y_no_llega_al_motor(api, malo: bytes) -> None:
    cliente, clave, _ = api
    r = post(cliente, clave, malo)
    assert r.status_code == 422 and "detalle" in r.json()


def test_una_cifra_con_exponente_dentro_del_documento_es_422(api) -> None:
    cliente, clave, _ = api
    documento = copy.deepcopy(EJEMPLO_V1)
    documento["parametros"]["fcas"] = "1E+999999999"
    assert post(cliente, clave, cuerpo(documento=documento)).status_code == 422


def test_el_cuerpo_de_exactamente_20_mib_pasa_y_con_un_byte_mas_es_413(api) -> None:
    cliente, clave, _ = api
    base = cuerpo()
    justo = base + b" " * (api_seguridad.LIMITE_CUERPO - len(base))
    assert len(justo) == 20 * 1024 * 1024
    assert post(cliente, clave, justo).status_code == 200
    mas = post(cliente, clave, justo + b" ")
    assert mas.status_code == 413 and "20 MiB" in mas.json()["detalle"]


def test_el_middleware_corta_el_cuerpo_sin_leerlo_entero() -> None:
    """Con el cuerpo en trozos y sin `Content-Length`, deja de leer al pasar el tope."""
    leidos, respuestas = [], []
    trozos = [{"type": "http.request", "body": b"x" * 100, "more_body": True} for _ in range(1000)]

    async def app_vacia(scope, receive, send):
        while True:
            mensaje = await receive()
            leidos.append(len(mensaje["body"]))
            if not mensaje.get("more_body"):
                break

    async def recibir():
        return trozos.pop(0)

    async def enviar(mensaje):
        respuestas.append(mensaje)

    mw = api_seguridad.LimiteDeCuerpo(app_vacia, limite=1000)
    asyncio.run(mw({"type": "http", "headers": []}, recibir, enviar))
    assert respuestas[0]["status"] == 413 and len(leidos) == 10  # 10 x 100 B = 1000 B pasan
    assert len(trozos) == 1000 - 11  # el undécimo trozo ya excedió; el resto no se leyó


def test_un_content_length_mayor_que_el_tope_se_rechaza_sin_llamar_a_la_app() -> None:
    llamadas, respuestas = [], []

    async def app_vacia(scope, receive, send):
        llamadas.append(1)

    async def enviar(mensaje):
        respuestas.append(mensaje)

    mw = api_seguridad.LimiteDeCuerpo(app_vacia, limite=1000)
    scope = {"type": "http", "headers": [(b"content-length", b"1001")]}
    asyncio.run(mw(scope, lambda: None, enviar))
    assert llamadas == [] and respuestas[0]["status"] == 413


def test_la_reevaluacion_a_otra_fecha_cambia_solo_r12(api) -> None:
    cliente, clave, _ = api
    documento = copy.deepcopy(EJEMPLO_V1)
    for linea in documento["composiciones"][0]["lineas"]:
        linea["precio_origen"]["fecha_precio"] = "2026-09-01"
    pronto = post(cliente, clave, cuerpo(documento=documento, fecha_evaluacion="2026-09-10")).json()
    tarde = post(cliente, clave, cuerpo(documento=documento, fecha_evaluacion=HOY)).json()
    assert not [h for h in pronto["no_declarados"] if h["regla"] == "R12"]
    assert len([h for h in tarde["no_declarados"] if h["regla"] == "R12"]) == 3


def test_el_reloj_de_la_api_es_inyectable(monkeypatch) -> None:
    monkeypatch.setattr(api_seguridad, "ahora", lambda: datetime(2026, 1, 1))
    assert api_seguridad.ahora() == datetime(2026, 1, 1)
    assert json_canonico({"a": 1}) == b'{"a":1}'
```
  Los clientes de prueba de la API usan el host del equipo (el middleware rechaza `testserver`):
```diff
--- a/tests/integration/conftest.py
+++ b/tests/integration/conftest.py
@@ -70,5 +70,5 @@
     app.dependency_overrides[sesion_api] = fabrica_de_sesion
     try:
-        with TestClient(app) as cliente:
+        with TestClient(app, base_url="http://127.0.0.1") as cliente:
             yield cliente
     finally:
```
```diff
--- a/tests/integration/test_api_preparar_base.py
+++ b/tests/integration/test_api_preparar_base.py
@@ -22,5 +22,5 @@
     def abrir(ruta: Path) -> TestClient:
         monkeypatch.setenv(dependencias.VARIABLE_BASE, f"sqlite:///{ruta.as_posix()}")
-        return TestClient(app)
+        return TestClient(app, base_url="http://127.0.0.1")  # S3: solo hosts del equipo (S3 §10)
 
     yield abrir
```
- [ ] **Paso 2: Correrla y ver el rojo**
Run: `uv run pytest tests/integration/test_api_auditorias.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'api.seguridad'`.
```bash
git add tests/integration/test_api_auditorias.py tests/integration/conftest.py \
  tests/integration/test_api_preparar_base.py
git commit -m "test(api): auditar un presupuesto ajeno con clave, tope de cuerpo y hosts, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`api/seguridad.py`**
```python
"""Seguridad de la API (spec S3 §10; RF-88, RNF-16): clave de API, tope de cuerpo y hosts.

* **Clave de API.** Las rutas `/v1/` exigen `X-Silice-Clave: <identificador>.<secreto>`. Sin clave,
  con una desconocida o revocada: **401** con `{"detalle": ...}`, el mismo mensaje en los tres
  casos, y un `fallo` en `evento_acceso`. La clave la crea el administrador solo desde el propio
  equipo y se muestra una vez (`seguridad.claves_api`).
* **Tope del cuerpo.** FastAPI y Uvicorn no limitan el cuerpo: `LimiteDeCuerpo` corta en 20 MiB
  (413) mirando `Content-Length` y, si falta o miente, contando los bytes a medida que llegan; no
  lee el resto.
* **Hosts.** `TrustedHostMiddleware` contra el *DNS rebinding*: solo `127.0.0.1` y `localhost`, más
  los que ponga `SILICE_HOSTS_PERMITIDOS` (la IP explícita de la red local, S5).

El filtro de IP no es un control (un túnel local anula la IP): el control es la clave (S3 §12).
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from operacion.instalacion import sesion_de_instalacion
from seguridad import claves_api, eventos
from seguridad.modelo import ClaveApi

__all__ = [
    "CABECERA",
    "LIMITE_CUERPO",
    "MENSAJE_SIN_CLAVE",
    "ClaveDep",
    "InstalacionDep",
    "LimiteDeCuerpo",
    "ahora",
    "hosts_permitidos",
]

CABECERA = claves_api.CABECERA
LIMITE_CUERPO = 20 * 1024 * 1024  # 20 971 520 B; con un byte más, 413
MENSAJE_SIN_CLAVE = "Clave de API ausente, desconocida o revocada."
HOSTS_POR_DEFECTO = ("127.0.0.1", "localhost")
VARIABLE_HOSTS = "SILICE_HOSTS_PERMITIDOS"


def ahora() -> datetime:
    """El reloj de la API; las pruebas lo sustituyen."""
    return datetime.now()


def hosts_permitidos(entorno: Mapping[str, str] | None = None) -> list[str]:
    entorno = os.environ if entorno is None else entorno
    extras = [h.strip() for h in entorno.get(VARIABLE_HOSTS, "").split(",") if h.strip()]
    return [*HOSTS_POR_DEFECTO, *extras]


def sesion_instalacion() -> Iterator[Session]:
    with sesion_de_instalacion() as sesion:
        yield sesion


InstalacionDep = Annotated[Session, Depends(sesion_instalacion)]


def exigir_clave(
    instalacion: InstalacionDep,
    x_silice_clave: Annotated[str | None, Header(alias=CABECERA)] = None,
) -> ClaveApi:
    """La dependencia de toda ruta `/v1/`: devuelve la clave vigente o responde 401."""
    fila = claves_api.verificar(instalacion, x_silice_clave, ahora())
    if fila is None:
        eventos.registrar(instalacion, "fallo", ahora(), login="(api)", detalle="clave de api")
        instalacion.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, MENSAJE_SIN_CLAVE)
    return fila


ClaveDep = Annotated[ClaveApi, Depends(exigir_clave)]


class _CuerpoExcedido(Exception):  # noqa: N818
    pass


class LimiteDeCuerpo:
    """Middleware ASGI puro: responde 413 sin leer el cuerpo entero (S3 §10)."""

    def __init__(self, app: ASGIApp, limite: int = LIMITE_CUERPO) -> None:
        self.app = app
        self.limite = limite

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declarado = dict(scope["headers"]).get(b"content-length")
        if declarado is not None and declarado.isdigit() and int(declarado) > self.limite:
            await self._rechazar(send)
            return
        total = 0
        empezo = False

        async def recibir() -> Message:
            nonlocal total
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                total += len(mensaje.get("body", b""))
                if total > self.limite:
                    raise _CuerpoExcedido
            return mensaje

        async def enviar(mensaje: Message) -> None:
            nonlocal empezo
            empezo = empezo or mensaje["type"] == "http.response.start"
            await send(mensaje)

        try:
            await self.app(scope, recibir, enviar)
        except _CuerpoExcedido:
            if not empezo:
                await self._rechazar(send)

    async def _rechazar(self, send: Send) -> None:
        cuerpo = b'{"detalle":"El cuerpo de la peticion excede el maximo de 20 MiB."}'
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(cuerpo)).encode())]})
        await send({"type": "http.response.body", "body": cuerpo})
```
**`api/rutas/auditorias.py`**
```python
"""`POST /v1/auditorias`: auditar un presupuesto de otra herramienta (spec S3 §10; RF-88, UC-23e).

El cuerpo es JSON con tres claves: `documento` (el documento canónico, `core.budget.canonico`),
`fecha_evaluacion` (ISO, **obligatoria**: la misma petición da siempre el mismo informe; RP8-11) y,
opcional, `anexo_espacio`. Se lee con el lector estricto (sin `NaN`, claves duplicadas, cifras
fuera del patrón ni más de 64 niveles: 422). Reaudita en memoria con las reglas de ESTA
instalación (contexto de la API: R8-R10 y R15 si viene el anexo de espacio; R11-R12 con lo
que traiga el documento; R13-R14 no) y devuelve el informe. **No guarda nada.** Los montos
viajan como texto.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependencias import SesionDep
from api.seguridad import ClaveDep
from auditoria.reauditoria import Servicios, leer_documento_json, reauditar
from core.budget.canonico import DocumentoInvalido, json_canonico
from paquete.formato import PaqueteRechazado
from seguridad.json_estricto import JsonRechazado, leer_json

router = APIRouter(prefix="/v1", tags=["auditorias"])


def servicios_de_la_api(sesion: SesionDep) -> Servicios:
    """Los servicios de ESTA instalación (referencia MaPreX y tasas del BCV, S1). Las pruebas
    sustituyen esta dependencia."""
    from auditoria.servicios import servicios_de_la_instalacion

    return servicios_de_la_instalacion(sesion)


ServiciosDep = Annotated[Servicios, Depends(servicios_de_la_api)]


class HallazgoRespuesta(BaseModel):
    regla: str
    severidad: str
    descripcion: str
    origen_ids: list[str]
    impacto: str | None = None


class DiferenciaRespuesta(BaseModel):
    codigo_partida: str
    campo: str
    declarado: str
    recalculado: str
    monto: str


class AuditoriaRespuesta(BaseModel):
    fecha_evaluacion: str
    contextos: list[str]
    termino: bool
    total_recalculado: str | None
    hallazgos: list[HallazgoRespuesta]
    no_declarados: list[HallazgoRespuesta]
    diferencias: list[DiferenciaRespuesta]


def _texto(valor: Any) -> str | None:
    return None if valor is None else format(valor, "f")


def _hallazgo(h) -> HallazgoRespuesta:
    return HallazgoRespuesta(
        regla=h.regla, severidad=h.severidad.name, descripcion=h.descripcion,
        origen_ids=list(h.origen_ids), impacto=_texto(h.impacto),
    )


@router.post(
    "/auditorias",
    response_model=AuditoriaRespuesta,
    openapi_extra={"requestBody": {"required": True, "content": {"application/json": {
        "schema": {"type": "object", "required": ["documento", "fecha_evaluacion"],
                   "properties": {"documento": {"type": "object"},
                                  "fecha_evaluacion": {"type": "string", "format": "date"},
                                  "anexo_espacio": {"type": "object"}}}}}}},
)
async def auditar_documento(
    peticion: Request, clave: ClaveDep, servicios: ServiciosDep
) -> AuditoriaRespuesta:
    cuerpo = await peticion.body()
    try:
        objeto = leer_json(cuerpo)
        if not isinstance(objeto, dict) or not isinstance(objeto.get("documento"), dict):
            raise HTTPException(422, "falta 'documento'")
        evaluacion = objeto.get("fecha_evaluacion")
        if not isinstance(evaluacion, str):
            raise HTTPException(422, "falta 'fecha_evaluacion'")
        fecha = date.fromisoformat(evaluacion)
        documento = leer_documento_json(json_canonico(objeto["documento"]))
        espacio = objeto.get("anexo_espacio")
    except (JsonRechazado, DocumentoInvalido, PaqueteRechazado, ValueError) as error:
        raise HTTPException(422, str(error)) from None
    r = await run_in_threadpool(
        reauditar, documento, servicios, fecha,
        espacio_json=json_canonico(espacio) if isinstance(espacio, dict) else None,
    )
    return AuditoriaRespuesta(
        fecha_evaluacion=fecha.isoformat(), contextos=list(r.contextos), termino=not r.no_termino,
        total_recalculado=_texto(r.total_recalculado),
        hallazgos=[_hallazgo(h) for h in (r.resultado.informe.hallazgos if r.resultado else ())],
        no_declarados=[_hallazgo(h) for h in r.nuevos],
        diferencias=[
            DiferenciaRespuesta(
                codigo_partida=d.codigo_partida, campo=d.campo, declarado=_texto(d.declarado),
                recalculado=_texto(d.recalculado), monto=_texto(d.monto),
            )
            for d in r.diferencias
        ],
    )
```
```diff
--- a/api/main.py
+++ b/api/main.py
@@ -3,6 +3,8 @@
 from fastapi import FastAPI, HTTPException, Request
 from fastapi.responses import JSONResponse
+from starlette.middleware.trustedhost import TrustedHostMiddleware
 
-from api.rutas import catalogo, computos, listas, presupuestos, rendimientos
+from api.rutas import auditorias, catalogo, computos, listas, presupuestos, rendimientos
+from api.seguridad import LimiteDeCuerpo, hosts_permitidos
 from core.catalog import CatalogoIncompleto
 
@@ -22,4 +24,8 @@
 app.include_router(presupuestos.router)
 app.include_router(rendimientos.router)
+app.include_router(auditorias.router)
+# S3 §10: tope de cuerpo (20 MiB) y hosts (DNS rebinding); la clave de API la exige cada ruta /v1/.
+app.add_middleware(LimiteDeCuerpo)
+app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts_permitidos())
 
 
```
  y se regenera el esquema (`docs/api.json` debe cubrir `/v1/auditorias`):
Run: `uv run python scripts/exportar_openapi.py`
- [ ] **Paso 4: Correrla y ver el verde** (y toda la API)
Run: `uv run pytest tests/integration/test_api_auditorias.py tests/integration/test_api.py
tests/integration/test_api_preparar_base.py tests/unit/test_openapi.py -v -W error` → verde.
- [ ] **Paso 5: Commit**
```bash
git add api/seguridad.py api/rutas/auditorias.py api/main.py docs/api.json
git commit -m "feat(api): POST /v1/auditorias con clave de API, tope de cuerpo y hosts permitidos" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Compuerta GS3-4 y foco de revisión de la fase

**Compuerta GS3-4** (se cruza al fusionar `inc/080-s3-4-revision`):
1. `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-4 --junit reporte-pruebas.xml`
   en OK.
2. CI verde en Linux y Windows. La API no importa `ui/` (`test_arquitectura_s3`).
3. **Los encargos de seguridad (clave de API, 401 sin distinguir, tope de cuerpo, hosts, texto
   ajeno) y de usabilidad** (Nielsen e ISO 9241-110 sobre la vista de revisión) aprueban.
4. **CP-R1** (el protocolo del indicador de quien revisa, seis personas, dos condiciones) se
   mide en la fase Med con la huella ya escrita en `docs/protocolos_s3.json`; no bloquea la
   compuerta de código pero sí la declaración de RNF-17.

**Foco de revisión de S3-4** (lo que el spec implica y ninguna prueba ejercita todavía):
1. **Una fórmula en un texto del paquete** (`=cmd|...`) ejecutada al abrir el Excel regenerado:
   `test_una_formula_en_el_texto_de_un_paquete_no_se_ejecuta_al_exportar`.
2. **El mismo informe a otra fecha cambia solo R12:** `test_r12_se_evalua_a_la_fecha_de_emision_y_
   no_cambia_de_un_dia_a_otro` y `test_la_reevaluacion_a_otra_fecha_cambia_solo_r12`.
3. **Una cabecera `Content-Length` que miente:** `test_el_middleware_corta_el_cuerpo_sin_leerlo_
   entero`.
4. **Quien revisa es quien armó, con un login igual en una empresa ajena:** `test_un_paquete_de_una_
   empresa_ajena_con_un_login_igual_no_avisa`.
5. **Una reauditoría que no termina:** `test_la_reauditoria_se_corta_a_los_60_segundos_y_lo_dice`.

---

# S3-6 — Variaciones atípicas de precio, RF-100 (rama `inc/080-s3-6-atipicos`, opcional)

**Es lo primero que cae** (decisión de Eugenio, P5): no tiene número de RNF, no toca `core/` y no
entra en el criterio de éxito. Si cae, la meta de la 0.8.0 se cierra en `S3-5` y RF-100 se declara
no construido. Solo `ml/`, `ui/` y `tests/`. Sale de `origin/main` con S1 fusionada (necesita la
lista de la empresa y los orígenes de precio).

### Tarea 22: La serie fechada de un insumo en USD y su advertencia

**Rama:** `inc/080-s3-6-atipicos` (sale de `main`; PR a `main`)   **Rol:** sf-ingeniero-interfaz
(serie y botón), sf-ingeniero-pruebas (memoria y series sembradas)
**Archivos:**
- Crear: `ml/anomaly/series.py`, `ui/atipicos.py`
- Modificar: `ui/paginas/hoja.py:62,1276-1300,1336` (el botón en la pestaña Precios)
- Prueba: `tests/unit/test_series_atipicas.py`, `tests/integration/test_atipicos.py`,
  `tests/unit/test_ui_hoja_atipicos.py`

**Interfaces:**
- Consume: `ml.anomaly.detector.{MINIMO_OBSERVACIONES, PrecioAtipico, precios_atipicos}` (I6.1, no
  se toca), `core.budget.presupuesto.CODIGO_ATIPICO`, `core.contracts.verificacion.{Hallazgo,
  Severidad}`, `core.models.{PrecioInsumo, ListaPrecios, PrecioOrigen}` (S1) y la memoria
  `tests/fixtures/memorias/atipicos_s3.md` (tarea 2).
- Produce:
  - `ml.anomaly.series`: `class PuntoDePrecio`
  - `ml.anomaly.series`: `class SerieEnUsd`
  - `ml.anomaly.series`: `class ResultadoDeSerie`
  - `ml.anomaly.series`: `def a_usd(puntos: Sequence[PuntoDePrecio]) -> SerieEnUsd`
  - `ml.anomaly.series`: `def variaciones(serie: SerieEnUsd) -> dict[str, Decimal]`
  - `ml.anomaly.series`: `def analizar(puntos: Sequence[PuntoDePrecio]) -> ResultadoDeSerie`
  - `ui.atipicos`: `def puntos_del_insumo(session: Session, codigo: str, series: ModuleType |
      None=None) -> list`
  - `ui.atipicos`: `def hallazgos_de_la_serie(codigo: str, resultado) -> list[Hallazgo]`
  - `ui.atipicos`: `def atipicos_del_insumo(session: Session, codigo: str, cargar_series:
      Callable[[], ModuleType]=_cargar_series) -> list[Hallazgo] | None`

**Qué hace.** Sobre los precios de un insumo en el tiempo (las listas de la empresa y las MaPreX,
cada precio con su fecha; las listas de **proyecto**, que nacen de una cotización, no entran): lleva
cada precio a **USD con la tasa de ese precio** (uno en Bs entre la tasa de su fecha; uno en USD
queda igual; **uno en Bs sin tasa no se inventa**: se omite y se nombra), ordena por fecha, reduce a
variaciones `(p2 - p1) / p1` y se las pasa al detector existente. Con menos de 8 variaciones el
detector se abstiene (la serie corta no es sospechosa, es insuficiente). Cada variación atípica es
un hallazgo `ATIPICO` de severidad **ADVERTENCIA**, nunca ERROR; no guarda nada y no bloquea
guardar, exportar ni firmar. Sin el extra `ml` devuelve `None`, sin hallazgo ni traza. **Oráculo
(memoria a mano, antes del código):** la serie `[1, 2, 4, ..., 256, 257]` marca solo la última
variación (la 8.ª); la serie `[1, 2, 4, ..., 512]` no marca ninguna; con 8 precios hay 7 variaciones
y el detector se abstiene. **Amenaza declarada:** con datos ficticios no se valida la tasa real de
detección ni de falsas alarmas; la tesis lo presenta como apoyo a quien revisa, no como medición.

- [ ] **Paso 1: Escribir las pruebas que fallan**
**`tests/unit/test_series_atipicas.py`**
```python
"""RF-100 contra `tests/fixtures/memorias/atipicos_s3.md`: series sembradas, conjunto exacto de
hallazgos, abstención por debajo de 8 variaciones, conversión a USD con la tasa de cada precio y
ningún hallazgo ERROR. El detector y sus umbrales son los de I6.1 y no se tocan."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ml.anomaly.series import PuntoDePrecio, a_usd, analizar, variaciones

D = Decimal


def serie(precios, moneda="USD"):
    """Un precio por mes, desde enero de 2026."""
    return [PuntoDePrecio(date(2026, k + 1, 1), D(p), moneda, None, f"L{k + 1:02d}")
            for k, p in enumerate(precios)]


def test_una_serie_de_10_con_un_atipico_marca_solo_la_ultima_variacion() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128, 256, 257]))
    assert [a.id for a in r.atipicas] == ["2026-09-01>2026-10-01#8"]
    assert r.atipicas[0].valor == D("0.00390625") and not r.se_abstuvo
    assert len(r.variaciones) == 9
    assert [v for k, v in r.variaciones.items() if not k.endswith("#8")] == [D(1)] * 8


def test_una_serie_de_10_sin_atipico_da_el_conjunto_vacio() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128, 256, 512]))
    assert r.atipicas == () and not r.se_abstuvo and set(r.variaciones.values()) == {D(1)}


def test_con_8_precios_hay_7_variaciones_y_el_detector_se_abstiene() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128]))
    assert len(r.variaciones) == 7 and r.atipicas == () and r.se_abstuvo
    con_raro = analizar(serie([1, 2, 4, 8, 16, 32, 64, 65]))
    assert con_raro.atipicas == () and con_raro.se_abstuvo  # la serie corta no es sospechosa


def test_el_noveno_precio_da_8_variaciones_y_ya_juzga() -> None:
    r = analizar(serie([1, 2, 4, 8, 16, 32, 64, 128, 129]))
    assert len(r.variaciones) == 8 and not r.se_abstuvo
    assert [a.id.split("#")[0] for a in r.atipicas] == ["2026-08-01>2026-09-01"]


def test_dos_precios_en_bs_con_tasas_distintas_dan_la_variacion_en_usd() -> None:
    puntos = [PuntoDePrecio(date(2026, 8, 3), D(720), "Bs", D(36), "Lista agosto"),
              PuntoDePrecio(date(2026, 9, 7), D(1100), "Bs", D(44), "Lista septiembre")]
    usd = a_usd(puntos)
    assert [(f.isoformat(), p) for f, p, _ in usd.puntos] == [
        ("2026-08-03", D(20)), ("2026-09-07", D(25))]
    [valor] = variaciones(usd).values()
    assert valor == D("0.25") != (D(1100) - D(720)) / D(720)


def test_un_precio_en_bs_sin_tasa_se_omite_y_se_nombra_sin_inventarla() -> None:
    puntos = [PuntoDePrecio(date(2026, 8, 3), D(720), "Bs", None, "Lista sin tasa"),
              PuntoDePrecio(date(2026, 9, 7), D(25), "USD", None, "Lista en USD"),
              PuntoDePrecio(date(2026, 10, 7), D(500), "Bs", D(0), "Tasa cero")]
    usd = a_usd(puntos)
    assert usd.sin_tasa == ("Lista sin tasa", "Tasa cero")
    assert [p for _, p, _ in usd.puntos] == [D(25)] and variaciones(usd) == {}


def test_los_puntos_se_ordenan_por_fecha_sin_importar_como_llegan() -> None:
    desordenada = list(reversed(serie([1, 2, 4])))
    assert [p for _, p, _ in a_usd(desordenada).puntos] == [D(1), D(2), D(4)]


def test_un_precio_anterior_igual_a_cero_no_genera_variacion() -> None:
    assert variaciones(a_usd(serie([0, 5, 10]))) == {"2026-02-01>2026-03-01#1": D(1)}


@pytest.mark.parametrize("precios", [[1, 2, 4, 8, 16, 32, 64, 128, 256, 257],
                                     [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]])
def test_la_misma_serie_da_siempre_el_mismo_resultado(precios) -> None:
    assert analizar(serie(precios)) == analizar(serie(precios))
```
**`tests/integration/test_atipicos.py`**
```python
"""RF-100 sobre las listas del caso: ADVERTENCIA, nunca ERROR; listas de proyecto fuera; la tasa
de cada precio; y sin el extra `ml`, nada (S3 §3.2 y §13.2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from core import models
from core.contracts.verificacion import Severidad
from tests.fixtures.sin_extra import SinExtra
from ui import atipicos

D = Decimal
SERIE_CON_ATIPICO = [1, 2, 4, 8, 16, 32, 64, 128, 256, 257]


def _lista(sesion: Session, mes: int, nombre: str, moneda: str = "USD", tasa=None,
           alcance: str = models.ALCANCE_GLOBAL):
    lista = models.ListaPrecios(nombre=nombre, moneda=moneda, fecha_vigencia=date(2026, mes, 1),
                                origen="prueba")
    sesion.add(lista)
    sesion.flush()
    if tasa is not None or alcance != models.ALCANCE_GLOBAL:
        sesion.add(models.ListaPreciosOrigen(lista_id=lista.id, tasa=tasa, alcance=alcance))
    return lista


def _precio(sesion: Session, lista, insumo, valor):
    fila = models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=D(valor))
    sesion.add(fila)
    sesion.flush()
    return fila


@pytest.fixture
def insumo(sesion: Session):
    fila = models.Insumo(codigo="ATIP-001", tipo="material", descripcion="Arena", unidad="m3")
    sesion.add(fila)
    sesion.flush()
    return fila


def _sembrar(sesion, insumo, precios) -> None:
    for mes, precio in enumerate(precios, start=1):
        _precio(sesion, _lista(sesion, mes, f"MaPreX {mes:02d}"), insumo, precio)


def test_la_serie_sembrada_de_10_precios_da_un_unico_hallazgo_advertencia(sesion, insumo) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    [h] = atipicos.atipicos_del_insumo(sesion, "ATIP-001")
    assert (h.regla, h.severidad) == ("ATIPICO", Severidad.ADVERTENCIA)
    assert h.valor_observado == D("0.00390625") and "0.39 %" in h.descripcion
    assert h.origen_ids == ("ATIP-001|2026-09-01>2026-10-01#8",)


def test_con_serie_corta_el_conjunto_es_vacio(sesion, insumo) -> None:
    _sembrar(sesion, insumo, [1, 2, 4, 8, 16, 32, 64, 128])
    assert atipicos.atipicos_del_insumo(sesion, "ATIP-001") == []


def test_ningun_hallazgo_de_rf_100_es_error(sesion, insumo) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    assert all(h.severidad is Severidad.ADVERTENCIA
               for h in atipicos.atipicos_del_insumo(sesion, "ATIP-001"))


def test_las_listas_de_proyecto_no_entran_en_la_serie(sesion, insumo) -> None:
    _precio(sesion, _lista(sesion, 1, "Global"), insumo, 10)
    _precio(sesion, _lista(sesion, 2, "Cotización", alcance=models.ALCANCE_PROYECTO), insumo, 99)
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.origen, p.monto) for p in puntos] == [("Global", D(10))]


def test_un_precio_en_bs_lleva_la_tasa_de_su_lista(sesion, insumo) -> None:
    _precio(sesion, _lista(sesion, 8, "Agosto", "Bs", tasa=D(36)), insumo, 720)
    _precio(sesion, _lista(sesion, 9, "Septiembre", "Bs", tasa=D(44)), insumo, 1100)
    puntos = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert [(p.moneda, p.monto, p.tasa) for p in puntos] == [("Bs", D(720), D(36)),
                                                              ("Bs", D(1100), D(44))]


def test_el_origen_del_precio_manda_sobre_la_lista(sesion, insumo) -> None:
    lista = _lista(sesion, 5, "Empresa", "Bs", tasa=D(10))
    precio = _precio(sesion, lista, insumo, 500)
    sesion.add(models.PrecioOrigen(
        precio_id=precio.id, moneda_original="USD", precio_original=D(12),
        fecha_precio=date(2026, 4, 20), tasa=None))
    [punto] = atipicos.puntos_del_insumo(sesion, "ATIP-001")
    assert (punto.fecha, punto.moneda, punto.monto) == (date(2026, 4, 20), "USD", D(12))


def test_sin_el_extra_ml_no_hay_hallazgo_ni_traza(sesion, insumo, monkeypatch) -> None:
    _sembrar(sesion, insumo, SERIE_CON_ATIPICO)
    relacionados = ("ml", "ml.anomaly", "ml.anomaly.series", "ml.anomaly.detector")
    with SinExtra(monkeypatch, ("ml",), relacionados):
        assert atipicos.atipicos_del_insumo(sesion, "ATIP-001") is None


def test_un_insumo_sin_precios_no_da_nada(sesion) -> None:
    assert atipicos.atipicos_del_insumo(sesion, "NO-EXISTE") == []
```
**`tests/unit/test_ui_hoja_atipicos.py`**
```python
"""El botón «Buscar variaciones atípicas de precio» de la pestaña Precios (RF-100, S3-6).

`AppTest` con la sesión de la hoja y el buscador sustituidos (con `monkeypatch`, que los devuelve
al terminar la prueba): prueba el pegamento. La serie y sus cifras las prueban
`test_series_atipicas.py` y `test_atipicos.py`."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _pagina() -> None:
    from types import SimpleNamespace as N

    from ui.paginas import hoja as pantalla

    pantalla._pintar_atipicos([N(codigo=c) for c in ("MAT-001", "MAT-002", "MAT-003")])


def _sustituir(monkeypatch) -> None:
    from contextlib import contextmanager
    from decimal import Decimal

    import streamlit as st

    from core.contracts.verificacion import Hallazgo, Severidad
    from ui.paginas import hoja as pantalla

    @contextmanager
    def sin_base():
        yield None

    dicho = {
        "MAT-001": [Hallazgo("ATIPICO", Severidad.ADVERTENCIA, "MAT-001: variación de 0.39 %",
                             valor_observado=Decimal("0.0039"))],
        "MAT-002": [],
        "MAT-003": [],
    }
    monkeypatch.setattr(pantalla, "_sesion", sin_base)
    monkeypatch.setattr(pantalla.atipicos, "atipicos_del_insumo", lambda sesion, codigo: (
        None if st.session_state.get("_sin_ml") else dicho[codigo]))


def _correr(monkeypatch, sin_ml: bool = False, pulsar: bool = True) -> AppTest:
    _sustituir(monkeypatch)
    at = AppTest.from_function(_pagina, default_timeout=60)
    at.session_state["_sin_ml"] = sin_ml
    at = at.run()
    if pulsar:
        at.button(key="hoja_atipicos").click()
        at = at.run()
    return at


def test_sin_pulsar_no_busca_ni_muestra_nada(monkeypatch) -> None:
    at = _correr(monkeypatch, pulsar=False)
    assert not at.warning and not at.success and not at.exception


def test_pulsado_muestra_cada_variacion_atipica_como_advertencia(monkeypatch) -> None:
    at = _correr(monkeypatch)
    assert [w.value for w in at.warning] == ["MAT\\-001: variación de 0\\.39 %"]
    assert not at.error and not at.exception  # nunca ERROR


def test_sin_el_extra_ml_lo_dice_y_no_busca(monkeypatch) -> None:
    at = _correr(monkeypatch, sin_ml=True)
    assert any("extra `ml`" in i.value for i in at.info) and not at.warning
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_series_atipicas.py tests/integration/test_atipicos.py
tests/unit/test_ui_hoja_atipicos.py -v -W error`
Esperado: error de colección `ModuleNotFoundError: No module named 'ml.anomaly.series'` y
`... 'ui.atipicos'`; `test_ui_hoja_atipicos` FAIL con `AttributeError: module 'ui.paginas.hoja' has
no attribute '_pintar_atipicos'`.
```bash
git add tests/unit/test_series_atipicas.py tests/integration/test_atipicos.py \
  tests/unit/test_ui_hoja_atipicos.py
git commit -m "test(ml): variaciones atipicas de precio con series sembradas, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación mínima**
**`ml/anomaly/series.py`**
```python
"""RF-100: la serie fechada de precios de un insumo, en USD, reducida a variaciones (spec S3 §3.2).

El detector (`ml.anomaly.precios_atipicos`, I6.1) no se toca: este módulo solo arma lo que le
llega. Sobre los precios de un insumo en el tiempo (las listas de la empresa de S1, RF-67, y las
MaPreX, cada precio con su fecha):

1. cada precio se lleva a **USD con la tasa de ese precio** (RF-65): un precio en Bs entre la
   tasa de su fecha; uno en USD queda igual; **uno en Bs sin tasa no se inventa**: se omite y se
   dice cuál;
2. la serie se ordena por fecha y se reduce a variaciones entre puntos consecutivos,
   `(p2 - p1) / p1` como fracción (0,05 = subió 5 %);
3. `precios_atipicos` juzga las variaciones. Con menos de `MINIMO_OBSERVACIONES` (8) variaciones
   se abstiene: la serie corta no es sospechosa, es insuficiente (`se_abstuvo`).

Sin acceso a la base (`ml/` no la conoce): recibe puntos planos. `ui/atipicos.py` los arma.
Los umbrales y la semilla son los del detector (SUPUESTO_DECLARADO, RS3-6); no se ajustan aquí.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ml.anomaly.detector import MINIMO_OBSERVACIONES, PrecioAtipico, precios_atipicos

__all__ = [
    "PuntoDePrecio",
    "ResultadoDeSerie",
    "SerieEnUsd",
    "a_usd",
    "analizar",
    "variaciones",
]


@dataclass(frozen=True, slots=True)
class PuntoDePrecio:
    """Un precio de un insumo en una fecha. `tasa` es Bs por USD de la fecha del precio."""

    fecha: date
    monto: Decimal
    moneda: str  # "USD" o "Bs"
    tasa: Decimal | None = None
    origen: str = ""  # la lista de donde sale, para citarlo


@dataclass(frozen=True, slots=True)
class SerieEnUsd:
    puntos: tuple[tuple[date, Decimal, str], ...]  # (fecha, USD, origen), por fecha
    sin_tasa: tuple[str, ...]  # los orígenes de los precios en Bs a los que les faltó la tasa


@dataclass(frozen=True, slots=True)
class ResultadoDeSerie:
    serie: SerieEnUsd
    variaciones: dict[str, Decimal]
    atipicas: tuple[PrecioAtipico, ...]
    se_abstuvo: bool  # menos de `MINIMO_OBSERVACIONES` variaciones


def a_usd(puntos: Sequence[PuntoDePrecio]) -> SerieEnUsd:
    """Cada precio en USD con la tasa de su fecha; ordenada por fecha (y origen, a igual fecha)."""
    llevados: list[tuple[date, Decimal, str]] = []
    sin_tasa: list[str] = []
    for p in puntos:
        if p.moneda == "USD":
            llevados.append((p.fecha, p.monto, p.origen))
        elif p.tasa is not None and p.tasa > 0:
            llevados.append((p.fecha, p.monto / p.tasa, p.origen))
        else:
            sin_tasa.append(p.origen or p.fecha.isoformat())
    llevados.sort(key=lambda t: (t[0], t[2]))
    return SerieEnUsd(tuple(llevados), tuple(sin_tasa))


def variaciones(serie: SerieEnUsd) -> dict[str, Decimal]:
    """`{«AAAA-MM-DD>AAAA-MM-DD#k»: variación}` entre puntos consecutivos con anterior > 0."""
    salida: dict[str, Decimal] = {}
    pares = zip(serie.puntos, serie.puntos[1:], strict=False)
    for k, ((f1, p1, _), (f2, p2, _)) in enumerate(pares):
        if p1 > 0:
            salida[f"{f1.isoformat()}>{f2.isoformat()}#{k}"] = (p2 - p1) / p1
    return salida


def analizar(puntos: Sequence[PuntoDePrecio]) -> ResultadoDeSerie:
    """La serie del insumo en USD, sus variaciones y las que el detector marca como atípicas."""
    serie = a_usd(puntos)
    cambios = variaciones(serie)
    return ResultadoDeSerie(
        serie=serie,
        variaciones=cambios,
        atipicas=tuple(precios_atipicos(cambios)),
        se_abstuvo=len(cambios) < MINIMO_OBSERVACIONES,
    )
```
**`ui/atipicos.py`**
```python
"""RF-100 (deseable, S3-6): variaciones atípicas en la serie de precios de un insumo, sin Streamlit.

Arma la serie fechada de un insumo desde las listas del caso (la de la empresa de S1 y las MaPreX;
las listas de **proyecto**, que nacen de una cotización, no entran), con la moneda, la fecha y la
tasa de cada precio (`PrecioOrigen` si existe; si no, la lista y su tasa), y se la pasa a
`ml.anomaly.series.analizar`. Cada variación atípica es un hallazgo `ATIPICO` de severidad
**ADVERTENCIA**, nunca ERROR: apoya a quien revisa, no mide (la tesis lo presenta así). No guarda
nada y no bloquea guardar, exportar ni firmar. Sin el extra `ml` devuelve `None` (sin hallazgo ni
traza). `ml/` no conoce la base: aquí se arman los puntos y allí se juzgan.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from types import ModuleType

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core import models
from core.budget.presupuesto import CODIGO_ATIPICO
from core.contracts.verificacion import Hallazgo, Severidad

__all__ = ["atipicos_del_insumo", "hallazgos_de_la_serie", "puntos_del_insumo"]

DOS_DECIMALES = Decimal("0.01")


def _cargar_series() -> ModuleType:
    import ml.anomaly.series

    return ml.anomaly.series


def puntos_del_insumo(session: Session, codigo: str, series: ModuleType | None = None) -> list:
    """Los `PuntoDePrecio` del insumo `codigo`, uno por precio de cada lista global."""
    series = series or _cargar_series()
    filas = session.execute(
        select(models.PrecioInsumo, models.ListaPrecios, models.PrecioOrigen,
               models.ListaPreciosOrigen)
        .join(models.Insumo, models.Insumo.id == models.PrecioInsumo.insumo_id)
        .join(models.ListaPrecios, models.ListaPrecios.id == models.PrecioInsumo.lista_id)
        .outerjoin(models.PrecioOrigen, models.PrecioOrigen.precio_id == models.PrecioInsumo.id)
        .outerjoin(models.ListaPreciosOrigen,
                   models.ListaPreciosOrigen.lista_id == models.ListaPrecios.id)
        .where(models.Insumo.codigo == codigo)
        .where(or_(models.ListaPreciosOrigen.alcance.is_(None),
                   models.ListaPreciosOrigen.alcance == models.ALCANCE_GLOBAL))
        .order_by(models.ListaPrecios.fecha_vigencia, models.ListaPrecios.id)
    ).all()
    puntos = []
    for precio, lista, origen, de_lista in filas:
        if origen is not None:  # S1: el precio dice su moneda original, su fecha y su tasa
            moneda, monto, fecha, tasa = (
                origen.moneda_original, origen.precio_original, origen.fecha_precio, origen.tasa)
        else:  # sin fila, manda la lista
            moneda, monto, fecha = lista.moneda, precio.precio, lista.fecha_vigencia
            tasa = de_lista.tasa if de_lista is not None else None
        puntos.append(series.PuntoDePrecio(fecha, monto, moneda, tasa, lista.nombre))
    return puntos


def hallazgos_de_la_serie(codigo: str, resultado) -> list[Hallazgo]:
    """Un hallazgo ADVERTENCIA por variación atípica, con su monto en porcentaje."""
    hallazgos = []
    for atipica in resultado.atipicas:
        porcentaje = format((atipica.valor * 100).quantize(DOS_DECIMALES), "f")
        antes, despues = atipica.id.split("#")[0].split(">")
        hallazgos.append(Hallazgo(
            regla=CODIGO_ATIPICO, severidad=Severidad.ADVERTENCIA,
            descripcion=(f"{codigo}: variación de {porcentaje} % entre {antes} y {despues} "
                         "(en USD) se aparta del historial de variaciones del insumo"),
            origen_ids=(f"{codigo}|{atipica.id}",), valor_observado=atipica.valor,
        ))
    return hallazgos


def atipicos_del_insumo(
    session: Session, codigo: str, cargar_series: Callable[[], ModuleType] = _cargar_series
) -> list[Hallazgo] | None:
    """Los hallazgos de RF-100 del insumo, o `None` si el extra `ml` no está instalado.
    Una lista vacía es «nada atípico» o «serie corta» (el detector se abstiene)."""
    try:
        series = cargar_series()
        resultado = series.analizar(puntos_del_insumo(session, codigo, series))
    except ImportError:  # `scikit-learn` llega tarde: al ajustar el bosque
        return None
    return hallazgos_de_la_serie(codigo, resultado)
```
  El botón «Buscar variaciones atípicas de precio» en la pestaña Precios (la importación pasa a
  `from ui import atipicos, caso, contraste, entrega, hoja`):
```diff
--- a/ui/paginas/hoja.py
+++ b/ui/paginas/hoja.py
@@ -1247,4 +1334,5 @@
         width="stretch",
     )
+    _pintar_atipicos(precios)
     if cambios:
         st.warning(
@@ -1266,5 +1354,5 @@
         fecha = c.date_input("Fecha de la cotizacion", value=date.today())
         fuente = st.text_input("Evidencia (opcional: archivo, enlace, nota)")
-        responsable = st.text_input("Responsable")
+        responsable = ui_sesion.caja_de_responsable("Responsable")
         enviar = st.form_submit_button("Cotizar")
     if enviar:
```
- [ ] **Paso 4: Correrlas y ver el verde**
Run: `uv run pytest tests/unit/test_series_atipicas.py tests/integration/test_atipicos.py
tests/unit/test_ui_hoja_atipicos.py tests/unit/test_anomalias.py tests/unit/test_arquitectura.py -v
-W error` → verde. Run: `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-6 --junit
reporte-pruebas.xml` → `RF-100` presente en la ERS (tarea 2) y los dos pares de la fase en OK.
- [ ] **Paso 5: Commit**
```bash
git add ml/anomaly/series.py ui/atipicos.py ui/paginas/hoja.py
git commit -m "feat(ml): variaciones atipicas de precio como advertencia en la pestana Precios" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

**Compuerta GS3-6** (opcional): `meta_silice.py --hasta S3-6` en OK; la rama no toca `core/`
(`S3-M5`); las series sembradas dan exactamente el conjunto de la memoria. **Foco:** una advertencia
que bloquee algo sería un error de diseño: `test_ningun_hallazgo_de_rf_100_es_error` y
`test_sin_el_extra_ml_no_hay_hallazgo_ni_traza`.

---

# S3-7 — Cierre: documentos, versión 0.8.0 y base de prueba (rama `inc/080-s3-7-cierre`)

Sale de `origin/main` con S3-0 a S3-5 fusionadas (S3-6 si se construyó). Al terminar, la
arquitectura de S3 está vigilada por pruebas, la documentación está al día, el acceso viene
encendido por omisión, la versión es 0.8.0 con su base de prueba y se cruza GS3.

### Tarea 23: Reglas de arquitectura de S3 y documentos enmendados

**Rama:** `inc/080-s3-7-cierre`   **Rol:** sf-ingeniero-pruebas
**Archivos:**
- Crear: `tests/unit/test_arquitectura_s3.py`
- Modificar: `docs/arquitectura.md`, `docs/modelo_datos.md`, `docs/plan_pruebas.md`

**Interfaces:**
- Consume: todo lo de S3 ya fusionado; `tests/fixtures/arquitectura.py` de B (ayudantes
  compartidos) y la lista de llamadores del embudo.
- Produce: `tests.unit.test_arquitectura_s3` (13 pruebas) y las secciones «Enmienda de Sílice 0.8.0
  (S3)» de la arquitectura y del modelo de datos, el bloque 8.3 y las filas de RNF-16 y RNF-17 del
  plan de pruebas.

**Reglas** (spec S3 §4.1 y §13.2): `seguridad` no conoce al núcleo, a las pantallas ni a los
adaptadores; `paquete` solo usa el núcleo y `seguridad`; `auditoria` la usan la API y la interfaz y
no importa a ninguna; la API no importa la interfaz; las orquestaciones de S3 no usan Streamlit;
solo el marco importa `ui/acceso`; solo las pantallas y el marco importan `ui/entrega` y
`ui/revision`; ningún `unsafe_allow_html`; ninguna caché compartida guarda datos de una persona;
todo texto que llega a Streamlit es literal o pasa por `texto_seguro`; y **todo llamador del embudo
dice quién guarda** (`usuario=` o `responsable=`), con la lista de llamadores completa. Al integrar
sobre la 0.7.0, el conjunto `LLAMADORES` gana los que S1 y S2 agregaron (convertir moneda, la
decisión de recuperación...): el mensaje de fallo de `test_la_lista_de_llamadores_del_embudo_esta_
completa` los lista como `nuevos: [...]`, y cada uno debe pasar la prueba anterior.

- [ ] **Paso 1: Escribir la prueba**
**`tests/unit/test_arquitectura_s3.py`**
```python
"""Quién importa a quién en lo que agrega S3 (spec S3 §4.1 y §13.2, fila «Arquitectura»).

Complementa a `test_arquitectura.py` (que vigila `core/` y los adaptadores): aquí, `seguridad`,
`paquete`, `auditoria`, la interfaz de S3, la API y la regla de que ningún texto ajeno llega
a Streamlit sin `texto_seguro`."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
            nombres.update(f"{nodo.module}.{a.name}" for a in nodo.names)  # `from ui import x`
    return nombres


def _archivos(carpeta: str) -> list[Path]:
    return sorted((RAIZ / carpeta).rglob("*.py"))


def _raices(ruta: Path) -> set[str]:
    return {nombre.split(".")[0] for nombre in _importados(ruta)}


@pytest.mark.parametrize("ruta", _archivos("seguridad"), ids=lambda r: r.name)
def test_seguridad_no_conoce_ni_al_nucleo_ni_a_las_pantallas_ni_a_los_adaptadores(ruta) -> None:
    prohibidas = {"core", "ui", "api", "adapters", "ml", "paquete", "auditoria", "streamlit"}
    assert not (_raices(ruta) & prohibidas), _raices(ruta) & prohibidas


@pytest.mark.parametrize("ruta", _archivos("paquete"), ids=lambda r: r.name)
def test_paquete_solo_usa_el_nucleo_y_seguridad_nunca_las_pantallas(ruta) -> None:
    prohibidas = {"ui", "api", "adapters", "ml", "auditoria", "streamlit", "fastapi"}
    assert not (_raices(ruta) & prohibidas), _raices(ruta) & prohibidas


@pytest.mark.parametrize("ruta", _archivos("auditoria"), ids=lambda r: r.name)
def test_auditoria_la_usan_la_api_y_la_interfaz_y_no_importa_ninguna(ruta) -> None:
    """RP8-6: vive aparte porque la API no puede importar `ui/`."""
    assert not (_raices(ruta) & {"ui", "api", "streamlit", "fastapi"})


def test_la_api_no_importa_la_interfaz() -> None:
    for ruta in _archivos("api"):
        assert not (_raices(ruta) & {"ui", "streamlit"}), ruta.name


@pytest.mark.parametrize("modulo", ["ui/entrega.py", "ui/revision.py", "ui/texto_seguro.py"])
def test_las_orquestaciones_de_s3_no_usan_streamlit(modulo: str) -> None:
    assert "streamlit" not in _raices(RAIZ / modulo)


def test_solo_el_marco_importa_ui_acceso() -> None:
    importadores = sorted(
        ruta.relative_to(RAIZ).as_posix()
        for ruta in _archivos("ui")
        if ruta.name != "acceso.py" and any(
            n == "ui.acceso" or n.startswith("ui.acceso.") for n in _importados(ruta))
    )
    assert importadores == ["ui/app.py"]


def test_solo_las_pantallas_y_el_marco_importan_ui_entrega_y_ui_revision() -> None:
    permitidos = {"ui/app.py", "ui/caso.py", "ui/paginas/entregar.py", "ui/paginas/revisar.py",
                  "ui/paginas/hoja.py"}  # `caso` sella al abrir; `hoja` verifica la cadena
    importadores = {
        ruta.relative_to(RAIZ).as_posix()
        for ruta in _archivos("ui")
        if any(n in {"ui.entrega", "ui.revision"} for n in _importados(ruta))
    }
    assert importadores <= permitidos


def test_ningun_modulo_usa_unsafe_allow_html() -> None:
    cuales = [
        ruta.relative_to(RAIZ).as_posix()
        for carpeta in ("ui", "api", "seguridad", "paquete", "auditoria")
        for ruta in _archivos(carpeta)
        if "unsafe_allow_html" in ruta.read_text(encoding="utf-8")
    ]
    assert cuales == []


#: Nada por usuario en cachés compartidas por el proceso (S3 §4.4): estas son las únicas
#: cachés de `ui/`, `seguridad/` y `paquete/`, y ninguna guarda datos de una persona.
CACHES_PERMITIDAS = {"seguridad/cuentas.py": 1}  # la huella de relleno para usuarios inexistentes


def test_ninguna_cache_compartida_guarda_datos_de_una_persona() -> None:
    cuantas: dict[str, int] = {}
    for carpeta in ("ui", "seguridad", "paquete", "auditoria", "api"):
        for ruta in _archivos(carpeta):
            texto = ruta.read_text(encoding="utf-8")
            n = sum(texto.count(marca) for marca in (
                "st.cache_data", "st.cache_resource", "@cache", "lru_cache", "functools.cache"))
            if n:
                cuantas[ruta.relative_to(RAIZ).as_posix()] = n
    assert cuantas == CACHES_PERMITIDAS


# --- texto ajeno -----------------------------------------------------------------------------

PAGINAS_CON_TEXTO_AJENO = ("ui/paginas/administracion.py", "ui/paginas/entregar.py",
                           "ui/paginas/revisar.py", "ui/acceso.py")
LLAMADAS_DE_TEXTO = {"markdown", "info", "warning", "error", "success", "caption", "write",
                     "subheader", "header", "title", "text_input", "metric", "toast"}
SEGURAS = {"texto_seguro", "formatear_decimal", "len", "sum", "sorted", "isoformat"}


#: Variables que solo reciben literales propios (un título, un aviso fijo): se vigilan en su
#: origen con la misma regla. Cualquier otro nombre sin `texto_seguro` es sospechoso.
LITERALES_PROPIOS = {"titulo", "exito", "aviso"}
#: Expresiones que un módulo puede pasar sin `texto_seguro` porque su texto es fijo por diseño.
FIJAS_POR_MODULO = {"ui/acceso.py": {"str(error)"}}  # mensajes fijos de `seguridad.cuentas`


def _formateado_seguro(valor: ast.FormattedValue) -> bool:
    """`{x:%Y-%m-%d}` y `{x:.2f}` no pueden inyectar marcado; `{x}` sí si `x` es ajeno."""
    return valor.format_spec is not None or _segura(valor.value)


def _segura(nodo: ast.AST) -> bool:
    """Una expresión de texto es segura si es literal o pasa por una función de `SEGURAS`."""
    if isinstance(nodo, ast.Constant):
        return True
    if isinstance(nodo, ast.Name):  # una constante del módulo, o un literal propio que se pasa
        return nodo.id.isupper() or nodo.id in LITERALES_PROPIOS
    if isinstance(nodo, ast.JoinedStr):
        return all(_formateado_seguro(v) if isinstance(v, ast.FormattedValue) else True
                   for v in nodo.values)
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        return _segura(nodo.left) and _segura(nodo.right)
    if isinstance(nodo, ast.Call):
        nombre = nodo.func.id if isinstance(nodo.func, ast.Name) else getattr(nodo.func, "attr", "")
        if nombre == "join":  # ", ".join(<generador>): seguro si lo es cada elemento
            argumento = nodo.args[0]
            elemento = getattr(argumento, "elt", argumento)
            return _segura(elemento)
        return nombre in SEGURAS
    if isinstance(nodo, ast.IfExp):
        return _segura(nodo.body) and _segura(nodo.orelse)
    return False


def _llamadas_de_texto(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in LLAMADAS_DE_TEXTO and nodo.args):
            yield nodo


@pytest.mark.parametrize("modulo", PAGINAS_CON_TEXTO_AJENO)
def test_todo_texto_que_llega_a_streamlit_es_literal_o_pasa_por_texto_seguro(modulo: str) -> None:
    sospechosas = [
        f"{modulo}:{n.lineno}: {ast.unparse(n.args[0])[:70]}"
        for n in _llamadas_de_texto(RAIZ / modulo)
        if not _segura(n.args[0])
        and ast.unparse(n.args[0]) not in FIJAS_POR_MODULO.get(modulo, ())
    ]
    assert sospechosas == []


def test_la_regla_de_texto_ajeno_distingue_lo_seguro_de_lo_que_no(tmp_path: Path) -> None:
    def hallazgos(fuente: str) -> int:
        archivo = tmp_path / "x.py"
        archivo.write_text(fuente, encoding="utf-8")
        return sum(1 for n in _llamadas_de_texto(archivo) if not _segura(n.args[0]))

    assert hallazgos("st.info('fijo')\n") == 0
    assert hallazgos("st.info(f'hola {texto_seguro(nombre)}')\n") == 0
    assert hallazgos("st.info(f'hola {nombre}')\n") == 1
    assert hallazgos("st.error(str(error))\n") == 1
    assert hallazgos("st.error(texto_seguro(str(error)))\n") == 0
    assert hallazgos("st.caption('a ' + valor)\n") == 1
    assert hallazgos("st.caption(', '.join(texto_seguro(x) for x in xs))\n") == 0
    assert hallazgos("st.caption(', '.join(x for x in xs))\n") == 1
    assert hallazgos("st.caption(f'{fecha:%Y-%m-%d}')\n") == 0
    assert hallazgos("st.info(AVISO_FIJO)\n") == 0
    assert hallazgos("st.info(texto_libre)\n") == 1


# --- el embudo: todo llamador dice quién guarda (RF-82, RF-83) -----------------------------------

#: Las funciones que crean una versión (o escriben su `RegistroCambio`) y el argumento con el que
#: dicen quién lo hace. S1 y S2 agregan las suyas (`convertir_version`, la decisión de
#: recuperación...) en la tarea que las crea.
EMBUDO = {
    "guardar_presupuesto": "usuario", "actualizar_precios": "usuario",
    "importar_presupuesto": "usuario", "guardar_edicion": "responsable",
    "restaurar_version": "responsable", "cotizar_insumo": "responsable",
    "retirar_cotizacion": "responsable", "_retirar_cotizacion": "responsable",
    "guardar_version": "responsable", "crear_primera_version": "responsable",
    "restaurar": "responsable", "cotizar": "responsable", "abrir_version": "responsable",
}
#: Los llamadores de hoy, fuera de `tests/`. Uno nuevo hace fallar la prueba hasta que se agrega
#: aquí con su prueba de que dice quién es.
LLAMADORES = {
    ("core/budget/actualizacion.py", "guardar_presupuesto"),
    ("core/budget/cotizacion.py", "guardar_presupuesto"),
    ("core/budget/edicion.py", "guardar_presupuesto"),
    ("core/budget/importacion.py", "guardar_presupuesto"),
    ("ui/hoja.py", "guardar_edicion"), ("ui/hoja.py", "guardar_presupuesto"),
    ("ui/hoja.py", "restaurar_version"), ("ui/hoja.py", "cotizar_insumo"),
    ("ui/hoja.py", "_retirar_cotizacion"),
    ("ui/paginas/actualizacion.py", "actualizar_precios"),
    ("ui/paginas/hoja.py", "guardar_version"), ("ui/paginas/hoja.py", "crear_primera_version"),
    ("ui/paginas/hoja.py", "restaurar"), ("ui/paginas/hoja.py", "abrir_version"),
    ("ui/paginas/hoja.py", "cotizar"), ("ui/paginas/hoja.py", "retirar_cotizacion"),
    ("api/rutas/presupuestos.py", "guardar_presupuesto"),
    ("api/rutas/presupuestos.py", "actualizar_precios"),
    ("api/rutas/presupuestos.py", "importar_presupuesto"),
    ("scripts/generar_resultados_ml.py", "guardar_presupuesto"),
    ("scripts/generar_resultados_ml.py", "actualizar_precios"),
    ("scripts/medir_rnf03.py", "guardar_presupuesto"),
    ("scripts/medir_rnf03.py", "actualizar_precios"),
    ("scripts/probar_precios_maprex.py", "guardar_presupuesto"),
    ("scripts/probar_precios_maprex.py", "actualizar_precios"),
    ("scripts/seed_demo.py", "guardar_presupuesto"),
    ("scripts/seed_of001.py", "abrir_version"),
}


def _llamadas_del_embudo():
    for carpeta in ("core", "ui", "api", "scripts", "adapters", "ml", "seguridad", "paquete"):
        for archivo in _archivos(carpeta):
            for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
                if not isinstance(nodo, ast.Call):
                    continue
                nombre = nodo.func.id if isinstance(nodo.func, ast.Name) else getattr(
                    nodo.func, "attr", None)
                if nombre in EMBUDO:
                    yield archivo.relative_to(RAIZ).as_posix(), nombre, nodo


def test_todo_llamador_del_embudo_dice_quien_guarda() -> None:
    sin_quien = sorted(
        f"{archivo}:{nodo.lineno} {nombre}() sin {EMBUDO[nombre]}="
        for archivo, nombre, nodo in _llamadas_del_embudo()
        if EMBUDO[nombre] not in {k.arg for k in nodo.keywords}
    )
    assert sin_quien == []


def test_la_lista_de_llamadores_del_embudo_esta_completa() -> None:
    encontrados = {(archivo, nombre) for archivo, nombre, _ in _llamadas_del_embudo()}
    nuevos, perdidos = sorted(encontrados - LLAMADORES), sorted(LLAMADORES - encontrados)
    assert encontrados == LLAMADORES, f"nuevos: {nuevos}; ya no existen: {perdidos}"
```
- [ ] **Paso 2: Ver el rojo de una regla** (es una guardia: se observa fallar con una violación
  deliberada y temporal)
Agregar `import streamlit  # noqa: F401` a `paquete/formato.py`.
Run: `uv run pytest
tests/unit/test_arquitectura_s3.py::test_las_orquestaciones_de_s3_no_usan_streamlit -v -W error`
Esperado: FAIL, el mensaje cita `paquete/formato.py`. Quitar la línea.
```bash
git add tests/unit/test_arquitectura_s3.py
git commit -m "test(arquitectura): reglas de seguridad, paquete, auditoria y embudo de S3" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Documentos**
  Se agrega al final de `docs/arquitectura.md` (con los finales de línea del archivo, CRLF):
**`docs/arquitectura.md`**
```markdown

## Enmienda de Sílice 0.8.0 (S3): cuentas, cadena de huellas, firma, paquete y planos

Fuente: [spec S3](especificaciones/2026-10-11-silice-s3-auditor-paquete-design.md) §4 y plan
[PLAN_SILICE_080.md](../PLAN_SILICE_080.md). Vale lo que dice §7 y se suma lo de aquí.

### Principio que se conserva

`core/` sigue cerrado: no conoce a `seguridad`, `paquete`, `auditoria`, `ui` ni `api` (lo vigila
`tests/unit/test_arquitectura.py`, que ahora lista esos tres paquetes). S3 toca el núcleo en cuatro
expedientes genéricos (SL‑E7 a SL‑E9 y SL‑E12), cada uno con su prueba y el visto bueno del tutor.

### Vista lógica: paquetes nuevos

- `seguridad/`: `json_estricto` (lector de JSON ajeno), `secretos` (Argon2id → AES‑GCM), `firma`
  (Ed25519 con separación de dominio), `permisos` (roles y matriz), `cuentas`, `sesiones`,
  `empresas` (empresa propia, clave de firma, empresas registradas), `claves_api`, `red`, `eventos`,
  `modelo` y `base`. No importa `core`, `ui`, `api`, `adapters` ni Streamlit.
- `paquete/`: `formato` (límites del ZIP y del JSON), `modelo` (`paq_recibido`, `paq_dictamen`),
  `anexos`, `exportar` y `verificar`. Importa `core.budget` (documento canónico, huellas) y
  `seguridad`; nunca `ui` ni `api`.
- `auditoria/`: `reauditoria` (el motor de la revisión: el mismo para la vista y para la API) y
  `servicios` (referencia de mercado y tasas de ESTA instalación). Existe aparte porque la API no
  puede importar `ui/` (RP8‑6).
- `operacion/instalacion.py`: el motor de `instalacion.db`, abierto una vez por proceso con
  `preparar_base(..., Destino.INSTALACION)`; lo usan `ui.sesion` y `api.seguridad`.
- `core/budget/canonico.py` (documento canónico y su lectura), `core/budget/cadena.py` (eslabones,
  sellado al confirmar, verificación), `core/budget/comparacion.py` (diferencia entre versiones y
  revaloración), `core/models/cadena.py` (`eslabon_version`) y `core/catalog/sesion.py` (WAL y
  `BEGIN IMMEDIATE`).
- `adapters/espacio/planos/`: `geometria_plano` (R15), `contraste` (R16), `auditoria_archivo`
  (DXF con recuperación) e `ids` (requisitos IDS del IFC); `adapters/espacio/serie.py` serializa el
  espacio para el anexo del paquete.
- `ui/`: `sesion` (sesión, roles, responsable), `acceso` (solo la importa `app.py`), `entrega`,
  `revision`, `contraste`, `atipicos`, `texto_seguro` y las páginas `entregar`, `revisar` y
  `administracion`. `ml/anomaly/series.py` arma la serie de precios de RF‑100.

### Vista de procesos

- **Guardar una versión.** Todo camino pasa por `guardar_presupuesto(..., usuario, anexos_de)`, que
  solo marca la versión «por sellar». Al confirmar la transacción raíz, el evento `before_commit`
  la sella en esa misma transacción: eslabón con la huella del documento canónico, la de sus
  `RegistroCambio`, la de sus anexos y la del eslabón anterior del proyecto. Un guardado sin
  usuario no confirma. Las transacciones que crean versión empiezan con `BEGIN IMMEDIATE` y la
  base está en WAL: dos personas guardando a la vez no bifurcan la cadena (S3 §6.3).
- **Entregar.** Verifica la cadena, arma `presupuesto.json`, `informe.json`, `cadena.json` y los
  anexos, escribe el manifiesto con las huellas y lo firma con la privada que se abre con la
  contraseña de la clave (solo desde el propio equipo). Todo en memoria; la base del caso no cambia.
- **Revisar.** Abre el ZIP con límites, verifica formato, integridad, autenticidad, cadena y
  anterioridad, reaudita con las reglas de esta instalación (R1 a R7; R8 a R10 y R15 con el
  anexo de espacio; R11 y R12 a la fecha de emisión; R13 y R14 con el anexo de control cuando S2
  entrega el servicio) y compara con la entrega anterior y con la lista propia. Solo guarda el
  archivo recibido, su registro y el dictamen.

### Vista física

Dos bases por instalación: `instalacion.db` (cuentas, sesiones, claves, registro de accesos;
nunca viaja con un caso) y el caso. Los paquetes recibidos viven en `<datos>/paquetes/` con su
SHA‑256 en el nombre. Las claves privadas solo existen cifradas en `instalacion.db`.

### Decisiones de diseño

| Id | Decisión | Alternativa descartada |
|---|---|---|
| RP8‑4 | `SILICE_ACCESO` enciende el acceso; por defecto apagado hasta la compuerta GS3 | cuentas
↳  desde S3‑1 |
| RP8‑6 | `auditoria/` como paquete propio | la reauditoría en `ui/` y la API importándola |
| RP8‑7 | `shapely` solo propone candidatos; las medidas son `Decimal` | decidir en `float` |
| RP8‑8 | Sellar en el `before_commit` raíz, ignorando los savepoints | sellar en cada llamador |
| RP8‑10 | `BEGIN IMMEDIATE` por opción de ejecución de la sesión | bloqueo global del proceso |
```
  al final de `docs/modelo_datos.md`:
**`docs/modelo_datos.md`**
```markdown

## Enmienda de Sílice 0.8.0 (S3): tablas de la instalación, de la cadena y del paquete

Fuente: spec S3 §7.4 y §8. Las tablas son aditivas: ninguna cambia una existente. Cada destino
tiene su revisión de Alembic y su lista `METADATAS` (`migraciones/metadatos.py`).

### Base de la instalación (`instalacion.db`, `seguridad/modelo.py`, revisión `ins_0001_seguridad`)

- `usuario`: `id`, `login` (único, normalizado), `nombre`, `huella_clave` (Argon2, nunca la
  contraseña), `roles` (`"arma,revisa"`, ordenado), `activo`, `debe_cambiar_clave`,
  `restablecida_por_admin`, `creado`, `creado_por`. Las cuentas no se borran: se desactivan.
- `intento_acceso`: `login_normalizado` (clave), `fallos_seguidos`, `bloqueado_hasta`,
  `ultimo_fallo`; vale también para logins que no existen.
- `sesion`: `huella_ficha` (SHA‑256 de la ficha; la ficha no se guarda), `usuario_id`, `creada`,
  `ultima_actividad`, `cerrada`, `motivo_cierre`.
- `evento_acceso`: `id`, `fecha_hora`, `login_intentado`, `usuario_id`, `ip_cliente`, `tipo`,
  `detalle`; sin secretos.
- `codigo_instalacion`: `huella` (SHA‑256 del código), `creado`, `usado`, `motivo`.
- `empresa_propia` (una sola fila, `id = 1`): `nombre`, `rif`, `ciudad`, `actualizada`,
  `actualizada_por`.
- `clave_empresa`: `publica` (32 octetos), `huella` (SHA‑256 completo), `privada_cifrada`, `kdf`,
  `sal`, `nonce`, `estado` (`activa`, `retirada`, `revocada`), `creada`, `creada_por`,
  `fecha_estado`, `motivo`. Retirar destruye `privada_cifrada`, `kdf`, `sal` y `nonce`.
- `empresa_registrada`: `empresa`, `rif`, `publica`, `huella`, `estado`, `comprobada_con`,
  `metodo` (`telefono`, `en persona`, `qr`), `fecha_comprobacion`, `registrada_por`,
  `fecha_estado`, `motivo`.
- `clave_api`: `nombre`, `identificador` (8 caracteres, público), `huella_secreto` (SHA‑256 de un
  secreto de 256 bits), `creada`, `creada_por`, `ultimo_uso`, `revocada`.

### Base del caso

- `eslabon_version` (`core/models/cadena.py`, revisión `caso_0007_s3_cadena`): `presupuesto_id`
  (clave, borra en cascada con la versión), `proyecto_id`, `anterior` (huella del eslabón previo;
  64 ceros en el génesis), `huella_contenido`, `huella_cambios`, `huella_anexos`, `huella_eslabon`,
  `usuario`, `fecha_hora`, `tipo` (`normal` o `retroactivo`), `version_formato`. El índice único
  (`proyecto_id`, `anterior`) hace imposible que dos versiones cuelguen del mismo eslabón.
- `paq_recibido` y `paq_dictamen` (`paquete/modelo.py`, revisión `caso_0008_s3_paquete`): lo
  recibido por quien revisa, con el SHA‑256 único del archivo, su estado de verificación, su
↳ cadena y
  las huellas de sus anexos; y el dictamen, atado a ese SHA‑256 y al estado de ese momento, con
  `revisor_armo`.

### Qué viaja en un paquete y qué no

`presupuesto.json` es el documento canónico de la versión (claves ordenadas, `Decimal` como texto,
sin identificadores de fila). Los anexos `espacio.json`, `reajuste.json`, `control.json` e `ia.json`
llevan una huella por entrada. Nada de `instalacion.db` viaja: ni cuentas, ni claves privadas.
```
  y en `docs/plan_pruebas.md`, tras la sección 8.2 y antes de «## 9. Trazabilidad RNF →
  verificación», el bloque 8.3 (cada prueba citada existe: `test_documentos_s5_1` lo comprueba):
**`docs/plan_pruebas.md`**
```markdown
### 8.3 Filas de Sílice 0.8.0 (S3): RF‑80 a RF‑89 y RF‑100

Fuente: [spec S3 §13](especificaciones/2026-10-11-silice-s3-auditor-paquete-design.md). El commit
de cada prueba va antes que el de su implementación, con el rojo observado. Estas filas no entran
en el resumen de §8.

| RF | Prueba(s) que lo demuestran | Estado |
|---|---|---|
| RF‑80 | `tests/unit/test_permisos.py::test_cada_fila_de_la_matriz`, `tests/unit/test_cuentas.py:
↳ :test_el_codigo_tiene_20_caracteres_base32_y_su_huella_no_es_el_codigo`, `tests/unit/test_cuentas.
↳ py::test_el_primer_administrador_se_crea_con_el_codigo_y_el_archivo_se_borra`,
↳ `tests/unit/test_cuentas.py::test_ninguna_contrasena_queda_en_la_base_ni_en_los_eventos` | verde |
| RF‑81 | `tests/unit/test_sesiones.py::test_inactividad_29_59_sigue_y_30_00_expira`,
↳ `tests/unit/test_sesiones.py::test_antiguedad_11_59_59_sigue_y_12_00_00_expira`,
↳ `tests/unit/test_sesiones.py::test_cuatro_cambios_de_cuenta_cierran_las_fichas`,
↳ `tests/unit/test_cuentas.py::test_4_fallos_no_bloquean_y_el_quinto_si`,
↳ `tests/unit/test_cuentas.py::test_el_bloqueo_dura_15_minutos_exactos`,
↳ `tests/unit/test_cuentas.py::test_freno_global_espera_progresiva`,
↳ `tests/unit/test_ui_acceso.py::test_contrasena_erronea_da_el_mismo_mensaje_exista_o_no_el_usuario`
↳  | verde |
| RF‑82 | `tests/unit/test_responsables.py::test_las_pantallas_de_s1_y_s2_usan_la_caja`,
↳ `tests/unit/test_responsables.py::test_el_literal_sistema_aparece_una_sola_vez_en_ui`,
↳ `tests/unit/test_ui_hoja_responsable.py::test_guardar_registra_al_usuario` | verde |
| RF‑83 | `tests/integration/test_cadena.py::test_la_version_se_sella_al_confirmar_y_no_antes`,
↳ `tests/integration/test_cadena.py::test_confirmar_sin_usuario_se_rechaza_y_no_se_escribe_nada`, `t
↳ ests/integration/test_cadena.py::test_un_byte_cambiado_en_el_contenido_rompe_la_cadena_en_esa_vers
↳ ion`,
↳ `tests/integration/test_cadena.py::test_el_sellado_retroactivo_cubre_lo_anterior_y_se_declara`, `t
↳ ests/integration/test_concurrencia.py::test_tres_hilos_guardan_diez_versiones_cada_uno_sin_perder_
↳ ninguna`,
↳ `tests/integration/test_canonico.py::test_el_vector_escrito_a_mano_tiene_la_huella_literal` |
↳ verde |
| RF‑84 | `tests/unit/test_firma.py::test_vectores_del_rfc_8032`,
↳ `tests/unit/test_firma.py::test_una_firma_de_un_dominio_no_vale_en_el_otro`,
↳ `tests/unit/test_empresas.py::test_retirar_destruye_la_privada_en_la_base`, `tests/unit/test_empre
↳ sas.py::test_revocar_con_la_contrasena_da_un_aviso_firmado_y_destruye_la_privada`,
↳ `tests/unit/test_secretos.py::test_el_dato_asociado_ata_el_cifrado_a_su_huella` | verde |
| RF‑85 |
↳ `tests/integration/test_entrega.py::test_el_paquete_firmado_se_verifica_en_otra_instalacion`,
↳ `tests/integration/test_entrega.py::test_sin_clave_se_exporta_sin_firma_y_se_declara`, `tests/inte
↳ gration/test_entrega.py::test_el_sha256_del_archivo_descargado_queda_en_el_registro_de_accesos`,
↳ `tests/integration/test_entrega.py::test_la_base_del_caso_no_cambia_al_entregar`,
↳ `tests/integration/test_entrega.py::test_una_cadena_rota_impide_entregar_y_dice_en_que_version` |
↳ verde |
| RF‑86 |
↳ `tests/unit/test_paquete_verificar.py::test_integro_firmado_con_los_cuatro_anexos_es_verificado`,
↳ `tests/unit/test_paquete_verificar.py::test_un_byte_cambiado_en_el_presupuesto_sin_tocar_el_manifi
↳ esto_es_alterado`, `tests/unit/test_paquete_verificar.py::test_refirmado_con_otra_clave_que_dice_s
↳ er_la_empresa_registrada_es_alterado`, `tests/unit/test_paquete_formato.py::test_el_archivo_de_20_
↳ mib_exactos_pasa_y_con_un_byte_mas_se_rechaza`, `tests/unit/test_paquete_anterioridad.py::test_un_
↳ paquete_que_reescribe_la_historia_lo_dice_con_la_version_y_la_fecha` | verde |
| RF‑87 | `tests/unit/test_ui_revision.py::test_diferencia_contra_la_entrega_anterior_y_contra_la_
↳ base_del_revisor`, `tests/unit/test_ui_revision.py::test_r12_se_evalua_a_la_fecha_de_emision_y_no_
↳ cambia_de_un_dia_a_otro`, `tests/unit/test_ui_revision.py::test_el_excel_se_regenera_desde_el_json
↳ _y_lleva_las_hojas_de_la_revision`, `tests/integration/test_revision_recibir.py::test_el_dictamen_
↳ queda_atado_al_sha256_y_al_estado_de_ese_momento`, `tests/unit/test_comparacion.py::test_los_total
↳ es_son_los_de_la_memoria_y_las_dos_columnas_suman_exacto`,
↳ `tests/unit/test_ui_revisar.py::test_quien_revisa_y_figura_como_quien_armo_ve_el_aviso` | verde |
| RF‑88 | `tests/integration/test_api_auditorias.py::test_con_clave_valida_devuelve_el_informe_y_l
↳ os_montos_como_texto`, `tests/integration/test_api_auditorias.py::test_sin_clave_o_con_una_mala_o_
↳ revocada_es_401_con_el_mismo_mensaje`, `tests/integration/test_api_auditorias.py::test_el_cuerpo_d
↳ e_exactamente_20_mib_pasa_y_con_un_byte_mas_es_413`,
↳ `tests/integration/test_api_auditorias.py::test_un_host_ajeno_se_rechaza_contra_el_dns_rebinding`,
↳  `tests/unit/test_ui_revision.py::test_la_plantilla_descargada_se_audita_y_no_toca_ninguna_base` |
↳  verde |
| RF‑89 | `tests/unit/test_r15_geometria_plano.py::test_superposicion_de_0_0100_m2_pasa`, `tests/u
↳ nit/test_r15_geometria_plano.py::test_superposicion_de_0_0101_m2_falla_con_error_y_cita_los_dos_am
↳ bientes`, `tests/unit/test_r16_contraste.py::test_fronteras_de_tolerancia_y_de_radio`, `tests/unit
↳ /test_planos_auditoria_s3.py::test_lo_que_ezdxf_repara_se_informa_y_el_plano_se_importa`, `tests/u
↳ nit/test_planos_auditoria_s3.py::test_sin_ninguna_propiedad_fallan_los_cuatro_requisitos_con_su_gl
↳ obal_id`, `tests/unit/test_deteccion_planos.py::test_la_deteccion_es_total_sin_falsas_alarmas_y_lo
↳ s_controles_no_se_detectan` | verde |
| RF‑100 | `tests/unit/test_series_atipicas.py::test_una_serie_de_10_con_un_atipico_marca_solo_la_
↳ ultima_variacion`, `tests/unit/test_series_atipicas.py::test_con_8_precios_hay_7_variaciones_y_el_
↳ detector_se_abstiene`, `tests/integration/test_atipicos.py::test_la_serie_sembrada_de_10_precios_d
↳ a_un_unico_hallazgo_advertencia`,
↳ `tests/integration/test_atipicos.py::test_ningun_hallazgo_de_rf_100_es_error` | verde (deseable) |
```
  y, al final de la tabla de la sección 9, las dos filas nuevas:
**`docs/plan_pruebas.md`**
```markdown
| RNF‑16 seguridad | las pruebas de §13.3 y §13.4 de la spec S3 (alteraciones, límites, sesiones,
↳ claves, hosts y concurrencia), la cobertura de `seguridad/` y `paquete/` (`coverage report
↳ --include="seguridad/*,paquete/*" --fail-under=80` en la CI) y la revisión del encargo de
↳ seguridad con la tabla de amenazas (§12) | cumple en la compuerta GS3 |
| RNF‑17 usabilidad de acceso y revisión | CP‑R1 y la tarea del administrador (registrar la clave
↳ de otra empresa comprobando su huella) con el protocolo de
↳ `docs/protocolo_indicador_administrador.md`, en la fase Med | pendiente (Med) |
```
- [ ] **Paso 4: Correr y ver el verde**
Run: `uv run pytest tests/unit/test_arquitectura_s3.py tests/unit/test_arquitectura.py
tests/unit/test_arquitectura_s5.py tests/unit/test_documentos_s5_1.py -v -W error` → verde.
- [ ] **Paso 5: Commit**
```bash
git add docs/arquitectura.md docs/modelo_datos.md docs/plan_pruebas.md
git commit -m "docs(s3): arquitectura, modelo de datos y trazabilidad de las pruebas de S3" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Tarea 24: Versión 0.8.0, acceso encendido, manuales, base de prueba y etiqueta

**Rama:** `inc/080-s3-7-cierre` (cierre) y, tras la etiqueta, `inc/080-s3-7-base` (sale de
`origin/main` en `v0.8.0`; PR a `main`)   **Rol:** sf-lider-de-fase **Archivos:**
- Crear (cierre): `tests/fixtures/caso_s3.py`
- Modificar (cierre): `ui/sesion.py:11,55` (`VALOR_POR_DEFECTO = "1"`),
  `tests/unit/test_ui_acceso.py`, `scripts/generar_base_prueba.py` (`CONSTRUCTORES` gana `"s3.db"`),
  `tests/unit/test_generar_base_prueba.py`, `tests/unit/test_paquete_anexos.py`, `pyproject.toml:3`
  (`version = "0.8.0"`), `uv.lock` (con `uv lock`), `CHANGELOG.md`, `docs/manual_usuario.md`,
  `docs/manual_tecnico.md`, `docs/bitacora/2026-10-silice-080.md`, `.github/workflows/ci.yml` (el
  paso de la meta ya dice `--hasta S3-7`)
- Crear (base): `tests/integration/test_base_prueba_v0_8_0.py`, `tests/fixtures/bases/v0_8_0/` (las
  bases y `ficha.json`, **generadas con el código de la etiqueta**, no a mano)

**Interfaces:**
- Consume: de B: `scripts/generar_base_prueba.py` (`CONSTRUCTORES: dict[str, Callable[[Path],
  object]]`, `main(["--salida", ..., "--version", ..., "--etiqueta", ..., "--commit", ...])`, que
  llama a `preparar_base` antes de cada constructor), `tests.fixtures.bases_prueba.{copiar_base,
  diferencias_con_ficha, ficha, nombres}`, `operacion.base_datos.{preparar_base, leer_estado,
  revision_head, Destino}`; de las tareas 3 a 22: `core.budget.cadena`, `paquete.modelo`,
  `tests.fixtures.canonico_minimo.{guardar_otra, registro, sembrar_minimo}`.
- Produce:
  - `tests.fixtures.caso_s3`: `def sembrar_caso_s3(sesion) -> None`
  - `tests.fixtures.caso_s3`: `def plantilla_s3(ruta: Path) -> Path`
  y `tests/fixtures/bases/v0_8_0/` con su `ficha.json` (formato de B: `version`, `etiqueta`,
  `commit`, `bases` con `revision_alembic = "caso_0008_s3_paquete"`, `sha256_base`,
  `filas_por_tabla` y los `presupuestos` con su total literal y la huella del informe).

- [ ] **Paso 1: Escribir las pruebas que fallan (rama `inc/080-s3-7-cierre`)**
  El acceso viene encendido por omisión desde la 0.8.0 (RP8-4); en `tests/unit/test_ui_acceso.py`:
```python
def test_desde_la_0_8_0_el_acceso_viene_encendido_por_omision() -> None:
    assert ui_sesion.VALOR_POR_DEFECTO == "1"
    assert ui_sesion.acceso_activo({}) is True
    assert ui_sesion.acceso_activo({"SILICE_ACCESO": "0"}) is False  # el interruptor de desarrollo
```
  `test_los_casos_de_la_base_de_prueba` (en `tests/unit/test_generar_base_prueba.py`) pasa a la
  lista que ya traen B, S1 y S2 más el caso de S3:
```python
def test_los_casos_de_la_base_de_prueba() -> None:
    assert list(generador.CONSTRUCTORES) == [
        "demo.db", "of001.db", "ti001.db", "s1.db", "s2.db", "s3.db"]
```
  Las tablas de los anexos del paquete existen de verdad en la 0.7.0 (un nombre mal escrito en
  `TABLAS_DE_REAJUSTE` o `TABLAS_DE_CONTROL` se omitiría en silencio); en
  `tests/unit/test_paquete_anexos.py`:
```python
def test_todo_nombre_de_los_anexos_es_una_tabla_real_del_caso() -> None:
    reales = {t for metadata in METADATAS_CASO for t in metadata.tables}
    declaradas = {*anexos.TABLAS_DE_REAJUSTE, *anexos.TABLAS_DE_CONTROL}
    assert sorted(declaradas - reales) == []
```
  El caso S3 se siembra en una base nueva en `head` y da lo que dice la memoria: tres versiones
  selladas en cadena, un paquete recibido y su dictamen:
**`tests/fixtures/caso_s3.py`**
```python
"""El caso S3 de la base de prueba de la 0.8.0 (RV-3, PRU-H15; plan 0.8.0, tarea 24).

Una base en `head` con lo que agrega S3: el proyecto mínimo `MIN-001` con tres versiones
selladas en cadena a nombre de una persona de plantilla (la tercera con sus `RegistroCambio`), y
un paquete recibido con su dictamen (`paq_recibido`, `paq_dictamen`).
`scripts/generar_base_prueba.py` la construye con el código de la etiqueta `v0.8.0`, después de
que `preparar_base` la creó en `head`. Casos construidos (NORMAS.md §1): ningún dato es real.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.catalog import abrir_sesion, crear_motor
from paquete import modelo as paq
from tests.fixtures.canonico_minimo import guardar_otra, registro, sembrar_minimo

USUARIO_DEL_CASO = "Plantilla <plantilla>"
FECHA_DEL_PAQUETE = datetime(2026, 11, 10, 9, 30)
HUELLA_DEL_ARCHIVO = "a" * 64


def sembrar_caso_s3(sesion) -> None:
    """MIN-001 con tres versiones encadenadas y un paquete dictaminado. No hace `commit`."""
    proyecto, v1, lista = sembrar_minimo(sesion, usuario=USUARIO_DEL_CASO)
    sesion.commit()
    v2 = guardar_otra(sesion, proyecto, lista, "002", "30", usuario=USUARIO_DEL_CASO,
                      version_origen=v1, motivo="edicion")
    sesion.add(registro(proyecto, v1, v2, responsable=USUARIO_DEL_CASO))
    sesion.commit()
    v3 = guardar_otra(sesion, proyecto, lista, "003", "35", usuario=USUARIO_DEL_CASO,
                      version_origen=v2, motivo="edicion")
    sesion.add(registro(proyecto, v2, v3, campo="precio", responsable=USUARIO_DEL_CASO))
    identificador = paq.registrar_recibido(
        sesion, archivo="MIN-001-003.silice", huella_archivo=HUELLA_DEL_ARCHIVO,
        paquete_id="11111111-1111-4111-8111-111111111111", destinatario="",
        ruta="paquetes/MIN-001-003.silice", empresa_declarada="Contratista Demo, C.A.",
        empresa_verificada="Contratista Demo, C.A.", huella_clave="b" * 64, estado="verificado",
        proyecto="MIN-001", codigo="003", emitido=FECHA_DEL_PAQUETE, cadena="[]",
        huellas_anexos="{}", recibido_por=USUARIO_DEL_CASO, fecha=FECHA_DEL_PAQUETE,
    )
    paq.registrar_dictamen(
        sesion, paquete_id=identificador, huella_archivo=HUELLA_DEL_ARCHIVO, resultado="conforme",
        notas="", usuario=USUARIO_DEL_CASO, fecha=FECHA_DEL_PAQUETE,
        estado_verificacion="verificado", revisor_armo=False,
    )


def plantilla_s3(ruta: Path) -> Path:
    """Siembra el caso S3 en `ruta` (ya en `head`) y confirma."""
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            sembrar_caso_s3(sesion)
            sesion.commit()
    finally:
        motor.dispose()
    return ruta
```
- [ ] **Paso 2: Correrlas y ver el rojo**
Run: `uv run pytest tests/unit/test_ui_acceso.py tests/unit/test_generar_base_prueba.py
tests/unit/test_paquete_anexos.py -v -W error`
Esperado: FAIL de `test_desde_la_0_8_0...` por `assert '0' == '1'`; FAIL de
`test_los_casos_de_la_base_de_prueba` (la lista no trae `s3.db`);
`test_todo_nombre_de_los_anexos...` verde si S1 y S2 usan esos nombres, o FAIL con la lista de los
que no existen: se corrigen en `paquete/anexos.py`, nunca se ignoran.
```bash
git add tests/fixtures/caso_s3.py tests/unit/test_ui_acceso.py \
  tests/unit/test_generar_base_prueba.py tests/unit/test_paquete_anexos.py
git commit -m "test(release): acceso por omision, anexos reales y caso S3, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
- [ ] **Paso 3: Implementación**
  El acceso encendido (`ui/sesion.py`): la constante pasa a `"1"` y el comentario del módulo deja
  de hablar de «la compuerta GS3 lo cambia»:
```python
VALOR_POR_DEFECTO = "1"  # desde la 0.8.0 el acceso viene encendido (SILICE_ACCESO=0 lo apaga)
```
  El generador construye el caso S3 como sexta base (en el docstring de
  `scripts/generar_base_prueba.py`, «Cinco bases» pasa a «Seis bases (la sexta, desde la 0.8.0)» y
  se agrega una viñeta: «`s3.db` (desde la 0.8.0): `MIN-001` con tres versiones selladas en cadena y
  un paquete recibido con su dictamen (`tests.fixtures.caso_s3.plantilla_s3`)»):
```python
from tests.fixtures.caso_s3 import plantilla_s3  # noqa: E402
# en CONSTRUCTORES:
    "s3.db": plantilla_s3,
```
  Versión: `pyproject.toml` `version = "0.8.0"`; `uv lock`. `CHANGELOG.md`, bajo «Sin publicar», en
  «Agregado»:
```markdown
- S3 (0.8.0): cuentas con roles, sesión y registro de accesos; cadena de huellas de las versiones
  sellada al confirmar (núcleo: documento canónico, WAL y BEGIN IMMEDIATE, diferencia entre
  versiones); firma Ed25519 por empresa; paquete auditado .silice con anexos, pantallas Entregar,
  Revisar y Administración, y POST /v1/auditorias con clave de API; auditoría de planos (DXF dañado,
  IDS del IFC, R15 y R16) y, si entra, variaciones atípicas de precio (RF-100).
```
  Manual de usuario, §3.11 nueva (antes de «## 4. El informe de auditoría»):
````markdown
### 3.11 Entrar, entregar y revisar un paquete (UC-21 a UC-23)

**Entrar.** Sílice pide usuario y contraseña. La primera vez, cuando no hay cuentas, la pantalla
pide el *código de instalación* (20 caracteres, está en `codigo_instalacion.txt` de la carpeta de
datos) y crea al primer administrador; el código se borra al usarse. Cada pestaña del navegador
tiene su propia sesión: expira a los 30 minutos sin actividad y a las 12 horas de haber entrado, y
su borrador se conserva si vuelve a entrar la misma persona. Cinco contraseñas erróneas seguidas
bloquean la cuenta 15 minutos. Si el administrador pierde su contraseña, quien tiene acceso al
equipo corre `uv run python scripts/restablecer_administrador.py` y obtiene un código nuevo.
**Cada cuenta ve lo que su rol permite:** *arma* (trabajo: hoja, planos, precios, entregar),
*revisa* (leer y revisar paquetes) y *administrador* (cuentas, empresa, claves y accesos). Una
↳ cuenta
puede tener varios roles; si arma y revisa, la revisión le avisa cuando el paquete lo armó ella.
**Aviso de red:** si abre Sílice desde otro equipo de la red, la pantalla dice «Conexión sin
cifrar»: en la 0.8.0 la red local va sin TLS y firmar o crear claves solo se hace en el equipo donde
está instalado.

**Entregar.** En «Entregar paquete» elija el proyecto y la versión, revise el resumen (total,
hallazgos, cadena, empresa emisora y anexos) y, si va firmado, escriba la contraseña de la clave de
la empresa (la conoce solo el administrador). Descargue el `.silice`. Si la cadena del proyecto está
rota, no se entrega y la pantalla dice en qué versión. Sin clave de empresa se puede entregar **sin
firma**; el paquete lo declara.

**Revisar.** En «Revisar un paquete» suba el `.silice`: el banner dice si está *verificado*, *no
verificado* (sin firma, empresa no registrada, clave revocada) o *alterado*, y por quién fue
emitido; debajo, la reauditoría con las reglas de esta instalación, qué cambió respecto de la
↳ entrega
anterior y cuánto cuesta (por cantidad y por precio), y el Excel regenerado. Guarde su dictamen
(conforme, con observaciones, rechazado): queda atado al archivo y al estado de ese momento.
**Administración.** Cuentas (alta con contraseña temporal, roles, desbloqueo, restablecimiento),
empresa y clave de firma, empresas registradas (siempre comprobando su huella de cinco grupos por
otro canal, p. ej. por teléfono), claves de API y accesos. Retirar o revocar una clave destruye la
privada; los respaldos anteriores la conservan cifrada.
````
  Manual técnico, §15 nueva al final:
````markdown
## 15. Seguridad, cadena de huellas y paquete (S3, 0.8.0)

- **Paquetes nuevos.** `seguridad/` (cuentas, sesiones, secretos, firma, empresas, claves de API,
  red local), `paquete/` (formato `.silice`, anexos, exportar, verificar), `auditoria/` (reauditoría
  y servicios de esta instalación). Reglas en `tests/unit/test_arquitectura_s3.py`.
- **Dos bases por instalación:** `instalacion.db` (migrada por Alembic, destino `instalacion`,
  revisión `ins_0001_seguridad`) y el caso. Nada de `instalacion.db` viaja en un paquete.
- **Todo guardado de una versión pasa por `guardar_presupuesto(..., usuario, anexos_de)`.** Marca
  la versión «por sellar»; el sellado ocurre en el `before_commit` de la transacción raíz. Un
  llamador nuevo debe pasar `usuario=` o `responsable=`: lo exige la prueba de arquitectura.
- **Añadir una acción a la matriz de roles:** una fila en `seguridad.permisos.PERMISOS` y su
  prueba en `test_permisos`; la pantalla la exige en la primera línea de su `render()`
  (`ui_sesion.exigir(Accion.X)`), y su `DefinicionPagina` la declara en `accion=`.
- **Añadir un anexo al paquete:** una tabla más en `TABLAS_DE_*` de `paquete/anexos.py` (con
  `responsable` si lo tiene) y su fila en `ANEXOS_ADMITIDOS` de `paquete/formato.py`.
- **Cambiar el documento canónico** exige subir `VERSION_FORMATO` y no tocar los eslabones ya
  sellados: cada uno se verifica con su `version_formato`.
- **Auditoría de planos:** `uv run python scripts/medir_deteccion_planos.py` mide la detección con
  la semilla 42 y debe dar 100 % de lo detectable y cero falsas alarmas (protocolo con huella).
- **Interruptor de desarrollo:** `SILICE_ACCESO=0` apaga el acceso; la suite lo fija así.
````
  Bitácora de la versión: la sección «Compuertas» recibe la salida literal de la meta de cada fase.
- [ ] **Paso 4: Correr y ver el verde**
Run: `uv sync --all-extras` → ok. Run: `uv run pytest tests/unit/test_ui_acceso.py
tests/unit/test_generar_base_prueba.py tests/unit/test_paquete_anexos.py -v -W error` → verde.
Run: `uv run pytest -q -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml` → verde, **sobre
la 0.7.0 real**: es la costura con S1 y S2; cualquier discrepancia con «Supuestos sobre 0.6.0 y
0.7.0» se anota en «Discrepancias» de la bitácora y se corrige en el módulo de S3 que la consume.
Run: `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-7 --junit reporte-pruebas.xml`
→ todas las filas en OK (`S3-M5` en PENDIENTE si S3-5 y S3-6 se fusionaron por otra vía). Run: `uv
run ruff check` sobre los archivos tocados; `uv run python scripts/guardia_nucleo.py --base v0.7.0`.
- [ ] **Paso 5: Commit, fusión y etiqueta**
```bash
git add tests/fixtures/caso_s3.py ui/sesion.py scripts/generar_base_prueba.py pyproject.toml \
  uv.lock CHANGELOG.md docs/manual_usuario.md docs/manual_tecnico.md \
  docs/bitacora/2026-10-silice-080.md tests/unit/test_ui_acceso.py \
  tests/unit/test_generar_base_prueba.py tests/unit/test_paquete_anexos.py
git commit -m "chore(release): Silice 0.8.0 con acceso encendido y el caso S3" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -u origin inc/080-s3-7-cierre
gh pr create --base main --head inc/080-s3-7-cierre --title "S3-7: Silice 0.8.0" --body-file -
gh pr merge <n> --merge
git fetch origin --tags
git tag -a v0.8.0 -m "Silice 0.8.0: S3 (cuentas, cadena de huellas, firma, paquete auditado y \
  planos)" origin/main
git push origin v0.8.0
```
  (La etiqueta marca el código; la base de prueba se genera **de** ella en el paso siguiente, como
  la de la 0.5.0, la 0.6.0 y la 0.7.0. El cuerpo del PR termina con la línea de Claude Code.)
- [ ] **Paso 6: Base de prueba de la 0.8.0 (rama `inc/080-s3-7-base`)**
```bash
git switch -c inc/080-s3-7-base origin/main
```
Prueba primero (la ficha es de la etiqueta; la cadena de `s3.db` se verifica con el código de hoy y
sale íntegra, y el dictamen conserva su archivo):
**`tests/integration/test_base_prueba_v0_8_0.py`**
```python
"""RV-3, PRU-H15: la base de prueba de la 0.8.0, generada con el código de la etiqueta v0.8.0,
abre por `preparar_base` y recarga igual que su ficha (`tests/fixtures/bases_prueba.py`).

`s3.db` es el caso de S3: `MIN-001` con tres versiones selladas en cadena y un paquete recibido
con su dictamen. La cadena se verifica con el código de hoy: si alguien cambia el documento
canónico sin subir `version_formato`, esta prueba lo ve (S3 §6.2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from core import models
from core.budget.cadena import eslabones_de, verificar_cadena
from core.catalog import abrir_sesion, crear_motor
from operacion.base_datos import Destino, leer_estado, preparar_base, revision_head
from paquete import modelo as paq
from tests.fixtures.bases_prueba import copiar_base, diferencias_con_ficha, ficha, nombres
from tests.fixtures.caso_s3 import USUARIO_DEL_CASO


def test_la_ficha_es_de_la_etiqueta_v0_8_0() -> None:
    datos = ficha("0.8.0")
    assert (datos["version"], datos["etiqueta"]) == ("0.8.0", "v0.8.0")
    assert {"demo.db", "of001.db", "ti001.db", "s3.db"} <= set(datos["bases"])
    assert {b["revision_alembic"] for b in datos["bases"].values()} == {"caso_0008_s3_paquete"}


@pytest.mark.parametrize("nombre", nombres("0.8.0"))
def test_cada_base_0_8_0_abre_en_head_y_recarga_su_ficha(tmp_path: Path, nombre: str) -> None:
    ruta = copiar_base("0.8.0", nombre, tmp_path / nombre)
    preparar_base(ruta)
    assert leer_estado(ruta).revision == revision_head(Destino.CASO)
    assert diferencias_con_ficha(ruta, ficha("0.8.0")["bases"][nombre]) == []


def test_la_base_s3_conserva_su_cadena_integra_y_su_dictamen(tmp_path: Path) -> None:
    ruta = copiar_base("0.8.0", "s3.db", tmp_path / "s3.db")
    preparar_base(ruta)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            proyecto = sesion.scalars(
                select(models.Proyecto).where(models.Proyecto.nombre == "MIN-001")
            ).one()
            resultado = verificar_cadena(sesion, proyecto)
            assert resultado.integra and resultado.versiones == 3, resultado
            assert [e.usuario for e in eslabones_de(sesion, proyecto)] == [USUARIO_DEL_CASO] * 3
            [recibido] = sesion.execute(select(paq.paq_recibido)).mappings().all()
            [dictamen] = sesion.execute(select(paq.paq_dictamen)).mappings().all()
            assert dictamen["huella_archivo"] == recibido["huella_archivo"]
            assert dictamen["resultado"] == "conforme"
    finally:
        motor.dispose()
```
Run: `uv run pytest tests/integration/test_base_prueba_v0_8_0.py -v -W error` → error de colección
`FileNotFoundError: .../tests/fixtures/bases/v0_8_0/ficha.json`.
```bash
git add tests/integration/test_base_prueba_v0_8_0.py
git commit -m "test(migraciones): base de prueba de v0.8.0 contra su ficha, en rojo" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
Generación (procedimiento de B con la etiqueta nueva), en Git Bash desde la raíz del worktree:
```bash
REPO="$(pwd)"
V080="${TMPDIR:-/tmp}/silice-v0.8.0"
rm -rf "$V080" && mkdir -p "$V080"
git archive v0.8.0 | tar -x -C "$V080"
(
  cd "$V080" && unset VIRTUAL_ENV \
  && export UV_PROJECT_ENVIRONMENT="$V080/.venv" \
  && uv sync --frozen --all-extras \
  && uv run --frozen python scripts/generar_base_prueba.py \
       --salida "$REPO/tests/fixtures/bases/v0_8_0" --version 0.8.0 --etiqueta v0.8.0 \
       --commit "$(git -C "$REPO" rev-parse 'v0.8.0^{commit}')"
)
```
(`scripts/generar_base_prueba.py` ya está en el árbol de la etiqueta: no se copia.)
Run: `uv run pytest tests/integration/test_base_prueba_v0_8_0.py
tests/integration/test_base_0_7_0.py tests/integration/test_base_0_6_0.py
tests/integration/test_base_prueba_v0_5_0.py -v -W error` → verde. Run: `uv run pytest -q -W error
-p no:cacheprovider --junitxml=reporte-pruebas.xml` → verde.
```bash
git add tests/fixtures/bases/v0_8_0/demo.db tests/fixtures/bases/v0_8_0/of001.db \
  tests/fixtures/bases/v0_8_0/ti001.db tests/fixtures/bases/v0_8_0/s1.db \
  tests/fixtures/bases/v0_8_0/s2.db tests/fixtures/bases/v0_8_0/s3.db \
  tests/fixtures/bases/v0_8_0/ficha.json
git commit -m "test(migraciones): bases de prueba de v0.8.0 y su ficha generadas con la etiqueta" \
  -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push -u origin inc/080-s3-7-base
gh pr create --base main --head inc/080-s3-7-base --title "S3-7: base de prueba de v0.8.0" \
  --body-file -
```
Fusionar con `gh pr merge <n> --merge` con la CI verde: con esa fusión se cruza GS3.

---

## Compuerta GS3 (etiqueta `v0.8.0`; se cruza al fusionar `inc/080-s3-7-base`)

1. `uv run python scripts/meta_silice.py --version 0.8.0 --hasta S3-7 --junit reporte-pruebas.xml` →
   `RESULTADO` con todas las filas en OK: C1 (los requisitos de la 0.6.0 y la 0.7.0 y los de S3:
   UC-21 a UC-23, RF-80 a RF-89, RNF-16 y RNF-17; RF-100 si S3-6 se construyó), las demás
   comprobaciones comunes (C2 cero omitidas, C3 el commit de cada prueba precede al de su
   implementación, hasta C7) y las cinco filas `S3-M1` a `S3-M5`.
2. CI verde en Linux y Windows, `HF_HUB_OFFLINE=1`, `-W error`, cero omitidas, y la cobertura de
   `seguridad/` y `paquete/` en 80 % como mínimo (en el sandbox de este plan: 96 %, medido con las
   pruebas de esos paquetes).
3. **Bloque de regresión literal** (sección siguiente) en verde sin editar una sola de esas pruebas.
4. Prueba de deriva RNF-20 en verde con las revisiones `ins_0001_seguridad`, `caso_0007_s3_cadena` y
   `caso_0008_s3_paquete`; las bases de `tests/fixtures/bases/v0_5_0/` a `v0_8_0/` abren en `head` y
   recargan igual que su ficha (la de `s3.db` con la cadena íntegra).
5. `uv run python scripts/guardia_nucleo.py --base v0.7.0` en 0, `git diff v0.7.0..HEAD --
   core/contracts/` vacío y `uv run ruff check` sobre los archivos tocados.
6. **Aprobación de los encargos:** requisitos (UC-21 a UC-23 con flujo y postcondiciones, RF-80 a
   RF-89, RNF-16, RNF-17 y la enmienda única de RNF-08), arquitectura (las reglas de la tarea 23),
   pruebas y calidad (oráculos independientes, fronteras exactas, ninguna prueba circular),
   **seguridad** (GS3-1, GS3-3 y GS3-4: Argon2id, fichas, bloqueo, firma con dominios, límites del
   ZIP, del JSON y de la API, clave de API, hosts, texto ajeno, la reanudación de sesión sin TLS
   declarada) y **usabilidad** (GS3-1 y GS3-4: Nielsen e ISO 9241-110), y el **verificador de
   hechos** sobre la licencia de `ifctester` y `bcf-client` (RP8-1), los parámetros de Argon2id y
   Ed25519 y `st.context.ip_address`, con su resultado anotado en la bitácora.
7. Aval del tutor de SL-E7, SL-E8, SL-E9 y SL-E12 (ya dado en GS3-2) y recorrido a mano de Eugenio
   con la base `s3.db`: entrar con las tres cuentas, entregar un paquete firmado desde el propio
   equipo, revisarlo (estado, reauditoría, diferencias), guardar el dictamen, registrar la clave de
   otra empresa con su huella y restablecer al administrador.
8. **No bloquea la etiqueta, pero queda declarado:** las mediciones de la fase Med (el indicador de
   quien revisa y la detección de planos con su protocolo ya con huella) y la decisión sobre incluir
   el extra `ifc` en el instalador (RP8-1).

---

## Bloque de regresión (literal)

Lo que la 0.8.0 no puede cambiar de la 0.7.0, y cómo se comprueba:
- `git diff v0.7.0..HEAD -- core/contracts/` vacío.
- Las memorias a mano de S1 y S2 no se editan (`git diff v0.7.0..HEAD -- tests/fixtures/memorias/`
  solo puede **agregar** `diferencias_s3.md` y `atipicos_s3.md`).
- El resultado de las pruebas de regresión de la línea base (7 de 7 reglas, `punto_equilibrio` de
  TI-001 en 28 586,76 USD, Día 6, las huellas de RNF-04) no cambia: `ARCHIVOS_REGRESION` de
  `scripts/ meta_silice.py` sin diferencias salvo las enmiendas declaradas en las tareas 8, 9, 11 y
  18.
- Las bases de prueba de la 0.5.0, la 0.6.0 y la 0.7.0 abren y recargan igual que su ficha: S3 no
  cambia ninguna columna de una tabla existente (solo agrega `eslabon_version`, `paq_recibido`,
  `paq_dictamen` y las nueve tablas de `instalacion.db`).
- Con `SILICE_ACCESO=0` la interfaz se comporta como en la 0.7.0 (la suite entera lo prueba).

---

## Foco de revisión de la 0.8.0 (transversal)

Cinco condiciones que el spec implica y ninguna prueba de una sola tarea ejercita; cada una con la
prueba que la fija, añadida a la tarea dueña:
1. **El respaldo de la instalación conserva la privada** de una clave retirada: la pantalla lo
   advierte y `test_el_respaldo_cifrado_no_trae_la_privada_en_claro` (tarea 13) fija que está
   cifrada.
2. **Una sesión reanudada por quien escucha la red sin TLS:** riesgo declarado (RS3-8); lo acota el
   aviso `test_el_aviso_de_conexion_sin_cifrar_solo_para_clientes_remotos` (tarea 6) y se cierra con
   TLS (S5).
3. **Una base de la 0.8.0 con la cadena rota por un cambio del documento canónico sin subir
   `VERSION_FORMATO`:** `test_la_base_s3_conserva_su_cadena_integra_y_su_dictamen` (tarea 24).
4. **Un nombre de tabla de anexo mal escrito** que se omitiría en silencio:
   `test_todo_nombre_de_los_anexos_es_una_tabla_real_del_caso` (tarea 24).
5. **Un llamador nuevo del embudo sin `usuario`** (de S1, S2 o S4): `test_todo_llamador_del_embudo_
   dice_quien_guarda` (tarea 23).

---

## Anexo A: lo que S4 y S5 consumen de S3

- La sesión vigente la da `ui.sesion.sesion_actual() -> SesionActiva | None`, con `.usuario`
  (`Nombre <login>`) y `.roles`. `st.session_state["silice_sesion"]` guarda solo la **ficha** (un
  texto secreto de 256 bits), no el objeto de la sesión.
  - `seguridad.sesiones`: `class SesionActiva`
  - `seguridad.sesiones`: `def huella_de(ficha: str) -> str`
  - `seguridad.sesiones`: `def abrir(session: Session, usuario: Usuario, ahora: datetime) -> str`
  - `seguridad.sesiones`: `def cerrar(session: Session, ficha: str, motivo: str, ahora:
      datetime) -> bool`
  - `seguridad.sesiones`: `def cerrar_todas(session: Session, usuario_id: int, motivo: str) ->
      int`
  - `seguridad.sesiones`: `def validar(session: Session, ficha: str | None, ahora: datetime) ->
      SesionActiva | None`
  - `ui.sesion`: `def acceso_activo(entorno: Mapping[str, str] | None=None) -> bool`
  - `ui.sesion`: `def ahora() -> datetime`
  - `ui.sesion`: `def limpiar_motores() -> None`
  - `ui.sesion`: `def instalacion() -> Iterator[Session]`
  - `ui.sesion`: `def ip_del_cliente() -> str | None`
  - `ui.sesion`: `def sesion_actual() -> SesionActiva | None`
  - `ui.sesion`: `def responsable_actual() -> str`
  - `ui.sesion`: `def responsable_de_la_hoja(escrito: str='') -> str`
  - `ui.sesion`: `def caja_de_responsable(rotulo: str='Responsable', *, key: str | None=None,
      contenedor=st)`
  - `ui.sesion`: `def puede(accion: Accion) -> bool`
  - `ui.sesion`: `def exigir(accion: Accion) -> SesionActiva`
  - `ui.sesion`: `def exigir_local(sensible: Sensible) -> SesionActiva`
- `secretos.cifrar(secreto, contrasena, huella_publica, parametros=...) -> SecretoCifrado` y
  `descifrar` (S4 guarda su clave de IA con ellos):
  - `seguridad.secretos`: `class ContrasenaRechazada(ValueError)`
  - `seguridad.secretos`: `class ParametrosKdf`
  - `seguridad.secretos`: `class SecretoCifrado`
  - `seguridad.secretos`: `def exigir_contrasena_de_clave(contrasena: str) -> None`
  - `seguridad.secretos`: `def cifrar(secreto: bytes, contrasena: str, huella_publica: str,
      parametros: ParametrosKdf | None=None) -> SecretoCifrado`
  - `seguridad.secretos`: `def descifrar(cifrado: SecretoCifrado, contrasena: str,
      huella_publica: str) -> bytes`
- `ui/entrega.py` arma el paquete; S4 agrega el anexo `anexos/ia.json` pasando `ia: bytes | None` a
  `anexos_del_paquete`:
  - `ui.entrega`: `class EntregaRechazada(ValueError)`
  - `ui.entrega`: `def anexos_de_cadena(session: Session, version: models.Presupuesto) ->
      Mapping[str, bytes]`
  - `ui.entrega`: `def anexos_del_paquete(session: Session, version: models.Presupuesto, ia:
      bytes | None=None) -> dict[str, bytes]`
  - `ui.entrega`: `def con_anexos_de_cadena(session: Session) -> Session`
  - `ui.entrega`: `class EstadoDeLaCadena`
  - `ui.entrega`: `def estado_de_la_cadena(session: Session, proyecto_nombre: str) ->
      EstadoDeLaCadena | None`
  - `ui.entrega`: `class Resumen`
  - `ui.entrega`: `def resumen_de_entrega(session: Session, instalacion: Session, version:
      models.Presupuesto) -> Resumen`
  - `ui.entrega`: `class Entrega`
  - `ui.entrega`: `def nombre_de_archivo(proyecto: str, codigo: str) -> str`
  - `ui.entrega`: `def entregar(session: Session, instalacion: Session, version:
      models.Presupuesto, *, usuario: str, ahora: datetime, version_silice: str, destinatario:
      str | None=None, contrasena_clave: str | None=None, ia: bytes | None=None) -> Entrega`
- `ui/paginas/administracion.py` tiene cinco pestañas (`TITULO_PESTANAS`); S4 y S5 agregan las suyas
  ahí o en una pantalla nueva con su propia `accion`.

---

## Discrepancias encontradas

1. **S2 entrega `reglas_de_control(instantanea)` y S3 pide `(documento, anexo, fecha)`.** Falta el
   puente que reconstruye la instantánea desde `anexos/control.json`; hasta que S2 o una tarea
   de integración lo entregue, `servicios_de_la_instalacion(reglas_de_control=None)` y R13 y R14 no
   corren desde un paquete (RP8-21). El anexo viaja igual (`paquete.anexos`).
2. **S2 deja `anexo_control(session, proyecto_nombre)`** y S3 arma el anexo `control.json` leyendo
   las tablas de `TABLAS_DE_CONTROL` con huella por entrada. Ambos deben converger en un solo
   serializador; mientras tanto el de S3 no depende de S2.
3. **S4 supone dos cosas que S3 entrega distinto.** (a) `secretos.cifrar(secreto, contrasena, *,
   asociado) -> bytes`; S3 entrega `cifrar(secreto, contrasena, huella_publica, parametros=None) ->
   SecretoCifrado` con `sal`, `nonce`, `kdf` y `cifrado` por separado (la base los guarda en
   columnas). (b) `st.session_state["silice_sesion"]` como objeto con `.usuario` y `.roles`; en S3
   guarda la ficha (texto) y el objeto se pide con `ui.sesion.sesion_actual()`. S4 adapta sus
   llamadas al anexo A.
4. **El spec ponía la reauditoría en `ui/revision.py`; vive en `auditoria/`** porque la API no puede
   importar `ui/` (RP8-6). `ui/revision.py` queda como la orquestación de la pantalla.
5. **El spec §14 pone `ui/texto_seguro.py` en S3-1**, pero el plan de la 0.6.0 (S1) ya lo crea y
   lo usa: S3 solo lo importa. Si S1 no llegara a crearlo, la tarea 6 lo agrega (4 líneas).
6. **R15 en la hoja:** el spec la pide en vivo (§3.4) y el primer diseño la dejaba solo en la
   reauditoría; la tarea 11 la cablea en `ui/hoja.py` (dos sitios) con su prueba.
7. **El protocolo de planos citaba `of001_limpio.json`** y el literal es `of001_limpio.py` (un `.py`
   mantiene las líneas a 100 columnas y se lee con `runpy`); corregido antes de calcular la huella.
8. **`S3-M4` (cobertura en la CI) pasa de la fase S3-1 a S3-3**, porque `paquete/` solo existe desde
   la tarea 14 y medir un paquete ausente haría fallar `pytest-cov` con `-W error`.
9. **RF-82 en las pantallas de S1 y S2** se cierra en la tarea 18 (S3-3), como dice el spec §14; el
   sandbox no las tiene y la tarea lo hace con la prueba de AST de `test_responsables`.
10. **Pruebas que parchaban `st.file_uploader` y la hoja sin devolverlos** contaminaban a las demás
    (fallaban 34 pruebas en el orden de la suite completa). Las tres pruebas de la interfaz (hoja
    con contraste, hoja con atípicos y Revisar) usan ahora `monkeypatch`; la regla queda en el
    manual técnico.
11. **El sandbox no pudo ejecutar** `auditoria/servicios.py` contra S1 real (usa stubs mínimos con
    las firmas del plan de la 0.6.0), ni R13 y R14 desde un anexo, ni el cableado de las pantallas
    de S1 y S2 con `caja_de_responsable`. La tarea 24 corre toda la suite sobre la 0.7.0 real para
    cerrarlo.
12. **Orden de fusión.** El spec dice que S3-3 sale de `main` con S3-2 ya fusionada; como el
    `usuario` es obligatorio al confirmar y los llamadores de la interfaz y de la API se cablean en
    la tarea 18, las dos ramas se apilan y se fusionan seguidas (RP8-20). El plan tiene 24 tareas.
