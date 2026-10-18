# Sesión 2 — Cambio visual: base y visor de solo lectura (Sílice 1.2.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Primera pantalla de la interfaz nueva: el auditor entra con su cuenta, suelta el libro `.xlsx` de la
empresa y lo ve **tal como se ve en Excel**, con cada hallazgo de la auditoría marcado sobre su celda (severidad con
ícono) y una franja de indicadores Fiori (libro frente a Sílice) con semántica IBCS. Solo lectura; Streamlit sigue
siendo la interfaz principal (RT-4).

**Architecture:** Todo fuera de `core/`. El aspecto del libro lo extrae `adapters/hoja_empresa/visual.py` (tercera
apertura en modo normal, RT-6) y viaja en un contrato **neutro** con coordenadas de Excel (base 1, `ref` sin `$`);
la conversión a la instantánea de Univer (base 0, píxeles, estilos) ocurre **en un solo lugar del frontend**
(`frontend-desktop/src/replica/aUniver.ts`). El FastAPI existente sirve la interfaz compilada en `/app` con CSP
(RT-1, RT-2) y abre una sesión por cookie `HttpOnly` + anti-CSRF para el navegador (RT-9); la clave de API sigue
siendo para integraciones. La interfaz no calcula montos: los indicadores (Δ, Δ%) los calcula la API con `Decimal`.

**Tech Stack:** Python ≥ 3.12 + `uv` (`uv sync --all-extras --frozen`), pytest `-W error`; Node 22 + npm, Vite, React
19, TypeScript, Vitest, `@carbon/react`, Univer (solo Apache-2.0). Versiones en §Versiones.

**Spec y criterio:** [RUTA_SESIONES.md](./RUTA_SESIONES.md) §5 sesión 2, RT-1..RT-9; plan del gestor §4 y §6.2 con
sus enmiendas E-4, E-9, E-10, E-11; skills `.agents/skills/front-carbon-fiori-ibcs/`, `replicacion-excel/`,
`back-clean-arch/`; **producto y diseño:** [`frontend-desktop/PRODUCT.md`](../../frontend-desktop/PRODUCT.md) y
[`frontend-desktop/DESIGN.md`](../../frontend-desktop/DESIGN.md) (impeccable; respuestas de Eugenio del 2026-10-18).

## Global Constraints

- `git diff origin/main -- core/` vacío; `uv run python scripts/guardia_nucleo.py --base origin/main` en OK.
- Libros solo **construidos** (`tests/fixtures/libros_empresa.py` u openpyxl en `tmp_path`); ninguno real. B-3
  (libro anonimizado de la empresa) no bloquea: si llega, se suma como verificación manual, nunca como prueba omitida.
- TDD con rojo visto en Python y en TypeScript; `pytest -W error`, cero omitidas; `npm test`, `npm run lint`,
  `npm run build` limpios.
- Montos y números del libro como texto decimal (`format(d, "f")`), nunca `float` en el contrato.
- Sin red externa (RNF-08): ningún CDN, fuentes IBM Plex desde `/app`, CSP `default-src 'self'`. Sin secretos en el
  navegador: nada en `localStorage` ni en el HTML.
- `package.json` con versiones **exactas** (sin `^` ni `~`), `.npmrc` con `save-exact=true`, `package-lock.json`
  versionado, `npm ci` reproducible. **Prohibido `@univerjs-pro/*`**.
- Diseño: `frontend-desktop/DESIGN.md` manda (Carbon g10 oficial, esquinas rectas, sin animación decorativa, dos
  semánticas de color, el color nunca solo, laptop 1366×768 sin desplazamiento horizontal).
- Commits convencionales en español, asunto sin tildes. Numeración de la ERS reservada: **UC-26, RF-111–RF-118,
  RNF-22–RNF-23** (ruta §8).

## Versiones (tarea 2.0; consultadas en npm el 2026-10-18, publicadas antes del 2026-10-04)

| Paquete | Versión | Publicada | Licencia | Nota |
|---|---|---|---|---|
| react, react-dom | 19.3.0 | 2026-09-09 | MIT | |
| @types/react, @types/react-dom | 19.3.0 | 2026-09-09 | MIT | |
| vite | 8.3.2 | 2026-10-01 | MIT | |
| @vitejs/plugin-react | 6.1.1 | 2026-08-28 | MIT | peer `vite ^8` |
| typescript | **6.0.3** | 2026-04-16 | Apache-2.0 | 7.0.x no: `typescript-eslint` pide `<6.1.0` |
| vitest | 5.0.3 | 2026-09-30 | MIT | |
| jsdom | 30.1.1 | 2026-09-22 | MIT | |
| @testing-library/react | 16.3.3 | 2026-08-27 | MIT | peer `@testing-library/dom ^10` |
| @testing-library/dom | 10.4.2 | 2026-09-13 | MIT | |
| @testing-library/jest-dom | 7.0.1 | 2026-08-09 | MIT | |
| @testing-library/user-event | 14.6.7 | 2026-09-02 | MIT | |
| eslint | 10.12.0 | 2026-10-02 | MIT | |
| @eslint/js | 10.0.1 | 2026-02-06 | MIT | |
| typescript-eslint | 8.71.0 | 2026-09-28 | MIT | |
| eslint-plugin-react-hooks | 7.1.1 | 2026-04-17 | MIT | |
| globals | 17.13.0 | 2026-10-01 | MIT | |
| @carbon/react | 1.117.0 | 2026-09-23 | Apache-2.0 | peer `sass`, `react ^19` |
| @carbon/styles | 1.116.0 | 2026-09-23 | Apache-2.0 | |
| @carbon/icons-react | 11.89.0 | 2026-09-23 | Apache-2.0 | |
| sass | 1.105.1 | 2026-09-29 | MIT | |
| @ibm/plex-sans, @ibm/plex-mono | 1.1.0, 2.5.0 | 2024-11-11, 2026-06-11 | OFL-1.1 | fuentes alojadas |
| @univerjs/presets, @univerjs/preset-sheets-core | 1.0.3 | 2026-09-29 | Apache-2.0 | |
| rxjs | 7.8.2 | 2025-02-22 | Apache-2.0 | peer de Univer |

Si `npm ci` revela un conflicto de pares, se baja a la versión anterior que cumpla la regla de ≥ 2 semanas y se
anota el ruling; nunca se sube a una más nueva. Acción de CI: `actions/setup-node@v6.5.0` (etiqueta verificada con
`gh api repos/actions/setup-node/git/matching-refs/tags/v6`).

## Rulings de la sesión (ratificables)

| # | Ruling | Costo si es erróneo |
|---|---|---|
| RS2-1 | Contrato de réplica **neutro** (coordenadas de Excel); la instantánea de Univer la arma el frontend en `src/replica/aUniver.ts`. Un cambio de versión de Univer no toca Python. | Bajo |
| RS2-2 | Carbon **oficial** (`@carbon/react` + `@carbon/styles`), no tokens recreados a mano (skill taste §2.A; impeccable). Sin Tailwind: la descripción de la skill del front lo nombra, pero Carbon trae su propio sistema y mezclar dos rompe la regla de un sistema por proyecto. | Bajo |
| RS2-3 | Tema **g10** (claro) solamente en 1.2.0 (Eugenio: laptop, a veces en obra). g100 diferido. | Bajo |
| RS2-4 | Anti-CSRF **sin migración**: `csrf = sha256("csrf:" + ficha)`; la API lo recalcula desde la cookie. Se entrega en el cuerpo de `POST/GET /v1/sesion`; se exige en la cabecera `X-Silice-CSRF` de todo POST/DELETE con cookie, además de `Origin` igual al `Host`. | Bajo |
| RS2-5 | Rutas de libros con **clave o sesión**: con `X-Silice-Clave` se comporta como hoy; sin ella, cookie válida + CSRF + rol con `Accion.LEER_PROYECTO` (arma o revisa). La matriz de permisos no cambia. | Medio: si el administrador también debe auditar, hace falta una acción nueva |
| RS2-6 | Cookie **sin `Secure`**: la red local va por HTTP (`operacion/config.py`); se documenta como límite y se revisa en la sesión 5. | Medio |
| RS2-7 | Indicadores calculados por la API: campo nuevo y **aditivo** `indicadores` en `LibroAuditadoRespuesta` (actual = libro, meta = Sílice, `sentido = "costo"`: que el libro declare más de lo que calcula Sílice es desfavorable). | Bajo |
| RS2-8 | Halos como capa DOM sincronizada con el viewport de Univer (no se pintan estilos dentro de la réplica: la réplica debe verse como el original). | Medio: si la API de rectángulos de Univer no basta, se usa su popup anclado a celda |
| RS2-9 | La interfaz nueva se usa con la API encendida (`[api] activa = true`), en `http://127.0.0.1:<puerto_api>/app/`; el lanzador no cambia en 1.2.0. | Bajo |
| RS2-10 | Las celdas cubiertas por una combinada no se listan en la réplica salvo que traigan valor o borde propio: Excel dibuja el rango con el estilo de la celda de origen (oráculo de la 2.6). | Bajo |

## Review Focus

1. **Coordenadas:** una celda `PRESUPUESTO!F12` del contrato cae en `cellData[11][5]` de la hoja `PRESUPUESTO` de
   Univer y su halo se pide para esa misma fila y columna; las combinadas, las filas/columnas ocultas y los nombres
   de hoja con espacios no desplazan nada.
2. **Seguridad del navegador:** login con freno y bloqueo (`seguridad.cuentas.autenticar`), cookie `HttpOnly`
   `SameSite=Strict`, CSRF y `Origin` en cada POST con cookie, sesión expirada → 401 limpio, `debe_cambiar_clave`
   → 403 con el mensaje de ir a la interfaz clásica; ninguna clave en el HTML ni en `localStorage`.
3. **IBCS:** `+` en costo es desfavorable (rojo), `-` favorable (verde), `0.00` y `-0.00` sin variación; `Δ%` nulo
   con meta cero; nunca verde por signo.
4. **Sin red externa:** el `dist` no contiene `http://` ni `https://` hacia otro anfitrión (fuentes, mapas de
   fuente, telemetría de Univer apagada); la CSP no tiene `unsafe-eval`.
5. **Lo que ya funciona:** `/v1/libros/*` con clave responde igual que antes (salvo el campo aditivo); `docs/api.json`
   regenerado; Streamlit intacto.

---

### Task 2.0: Plan, versiones y licencias (este documento) · orquestador · Opus high

- [x] Plan, `PRODUCT.md`, `DESIGN.md`, versiones y licencias (arriba). Commit `docs(planes): plan de la sesion 2`.

### Task 2.0b: Enmienda de la ERS · orquestador · Opus high

**Files:** Modify `docs/ERS.md` (nueva sección «Enmienda Sílice 1.2.0 (2026-10-18): interfaz nueva y visor de solo
lectura», después de la enmienda 1.5; filas nuevas en la matriz de trazabilidad), `CHANGELOG.md` («Sin publicar»).

- **UC-26 Auditar un libro en el visor.** Actor: ingeniero de costos (rol arma o revisa). Flujo: entra con su
  cuenta → suelta el libro → la API devuelve réplica y auditoría → ve la hoja con halos → toca un hallazgo y la hoja
  va a su celda → toca una celda marcada y la lista resalta su hallazgo.
- **RF-111** Réplica visual del libro `POST /v1/libros/replica`: hojas en orden, visibilidad, anchos, altos,
  combinadas, filas/columnas ocultas, paneles fijos y por celda valor mostrado y estilo. Criterio: el libro
  sintético de 2.6 reproduce su oráculo a mano celda por celda.
- **RF-112** La interfaz nueva se sirve en `/app` (estática, sin secretos) con CSP `default-src 'self'`.
- **RF-113** Acceso del navegador por cuenta: `POST/GET/DELETE /v1/sesion`, cookie `HttpOnly` + `SameSite=Strict`,
  CSRF, roles (RS2-4, RS2-5). Criterio: las pruebas de 2.3 (sin cookie 401, sin CSRF 403, rol administrador 403).
- **RF-114** Visor de solo lectura: la hoja se dibuja en lienzo (Univer) con el aspecto de RF-111 y no se puede editar.
- **RF-115** Halos de severidad con ícono y texto accesible sobre la celda de cada hallazgo; siguen la celda al
  desplazar, al cambiar de hoja y al acercar.
- **RF-116** Indicadores Fiori (valor, meta, Δ, Δ%) calculados por la API (`indicadores`) y coloreados según IBCS.
- **RF-117** El instalador lleva la interfaz compilada y la CI controla el tamaño del `dist`.
- **RF-118** Lista de hallazgos filtrable por severidad, sincronizada con la hoja; los hallazgos sin celda
  ubicable se listan aparte («sin celda en el libro»).
- **RNF-22** Sin red externa ni secretos en el navegador: CSP, fuentes locales, licencias permisivas sin
  `@univerjs-pro`, `dist` sin URL externas.
- **RNF-23** Usabilidad y accesibilidad: WCAG 2.1 AA (4,5:1 texto, 3:1 gráficos, color nunca solo, teclado), 1366×768
  sin desplazamiento horizontal, `prefers-reduced-motion`, `dist` ≤ 15 MB sin comprimir.
- [ ] Commit `docs(ers): enmienda 1.2.0, interfaz nueva y visor (UC-26, RF-111..118, RNF-22..23)`.

### Task 2.1: Andamiaje de `frontend-desktop/` · `silice-frontend` · Sonnet high · worktree `.worktrees/s2a`

**Files:**
- Create: `frontend-desktop/{package.json,package-lock.json,.npmrc,.gitignore,index.html,vite.config.ts,
  vitest.config.ts (o bloque test en vite.config.ts),tsconfig.json,tsconfig.node.json,eslint.config.js}`,
  `src/main.tsx`, `src/App.tsx`, `src/estilos/{tokens.scss,app.scss,fuentes.scss}`, `src/test/setup.ts`,
  `scripts/verificar_licencias.mjs`, `scripts/verificar_dist.mjs`, `README.md` (cómo correr, cómo probar).
- Modify: `.github/workflows/ci.yml` (job nuevo `interfaz`), `.gitignore` raíz si hace falta (`frontend-desktop/node_modules`, `frontend-desktop/dist`).

**Contrato:**
- `vite.config.ts`: `base: "/app/"`; en desarrollo, `server.proxy` de `/v1` a `http://127.0.0.1:8000`; `build.sourcemap: false`.
- Scripts npm: `dev`, `build` (`tsc -b && vite build`), `test` (`vitest run`), `lint` (`eslint . && tsc -b --noEmit`),
  `licencias` (`node scripts/verificar_licencias.mjs`), `dist` (`node scripts/verificar_dist.mjs`).
- `tokens.scss`: `@use '@carbon/styles/scss/themes'` g10; variables CSS propias **solo como alias** de tokens y
  colores de Carbon: `--silice-sev-critico` (red-60), `--silice-sev-error` (orange-50), `--silice-sev-advertencia`
  (yellow-30), `--silice-sev-info` (blue-60), `--silice-atipico` (purple-60), `--silice-verificado` (green-50),
  `--silice-ibcs-favorable` (green-50), `--silice-ibcs-desfavorable` (red-60), `--silice-ibcs-neutro` (gray-70).
- Fuentes: IBM Plex Sans y Mono desde `@ibm/plex-sans`/`@ibm/plex-mono` empaquetadas por Vite (woff2 en el `dist`),
  con la carga de fuentes de Carbon apagada o apuntada a esos archivos (revisar `$font-path` / `css--font-face` de
  `@carbon/styles`). `font-display: swap`.
- `App.tsx` de esta tarea: `Theme` g10 + `Header` de Carbon «Sílice» y un `main` vacío con el estado «Entrar» (2.4
  lo completa). Nada de animaciones; `@media (prefers-reduced-motion: reduce)` anula transiciones.
- `verificar_licencias.mjs`: recorre `package-lock.json` y falla si algún paquete es `@univerjs-pro/*` o su licencia
  no está en {MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, 0BSD, OFL-1.1, BlueOak-1.0.0, CC0-1.0, Python-2.0,
  (MIT OR Apache-2.0) y combinaciones OR de esas}; imprime la cuenta por licencia.
- `verificar_dist.mjs`: falla si `dist/` pasa de **15 000 000 bytes** o si algún archivo contiene `http://` o
  `https://` seguido de un anfitrión distinto de `www.w3.org` (espacios de nombres SVG/XML) — lista blanca explícita
  en el script, con prueba.
- CI `interfaz` (ubuntu): checkout, `actions/setup-node@v6.5.0` con `node-version: 22` y caché npm del
  `frontend-desktop/package-lock.json`, `npm ci`, `npm run licencias`, `npm run lint`, `npm test`, `npm run build`,
  `npm run dist`. `working-directory: frontend-desktop`.

**Pruebas (Vitest, rojo primero):**
- `src/App.test.tsx`: `test_la_cabecera_dice_silice` (rol `banner` con texto «Sílice»).
- `scripts/verificar_dist.test.mjs` (o `.test.ts`): un directorio temporal con `a.js` que contiene
  `https://cdn.example.com/x.woff2` → falla; con `http://www.w3.org/2000/svg` → pasa; 15 000 001 bytes → falla.
- `scripts/verificar_licencias.test.mjs`: un lock de juguete con `@univerjs-pro/sheets` → falla; con `GPL-3.0` → falla;
  con `(MIT OR Apache-2.0)` → pasa.

- [ ] Rojo visto, verde, `npm run lint`, `npm run build`, `npm run dist`; commit `feat(interfaz): andamiaje de frontend-desktop con Carbon g10`.

### Task 2.2: `adapters/hoja_empresa/visual.py` · `silice-replica-excel` · Sonnet high · worktree `.worktrees/s2b`

**Files:** Create `adapters/hoja_empresa/visual.py`, `tests/unit/test_visual_libro.py`. Modify
`tests/unit/test_arquitectura.py` solo si la regla de `adapters/hoja_empresa` lo exige (solo agregar líneas).

**Contrato (dataclasses congeladas con `slots=True`, en `visual.py`):**

```python
@dataclass(frozen=True, slots=True)
class EstiloVisual:          # se deduplica: las celdas apuntan a un índice de `LibroVisual.estilos`
    relleno: str | None      # "#RRGGBB" o None (sin relleno)
    fuente: str | None       # nombre, p. ej. "Arial"
    tamano: str | None       # puntos como texto decimal, "10" / "10.5"
    negrita: bool
    cursiva: bool
    subrayado: bool
    color: str | None        # "#RRGGBB"
    alineacion_h: str | None # "left" | "center" | "right" | "justify" | None (general)
    alineacion_v: str | None # "top" | "center" | "bottom" | None
    ajustar_texto: bool
    formato_numero: str      # el código de Excel tal cual, "General" por omisión
    bordes: tuple[str | None, str | None, str | None, str | None]  # arriba, derecha, abajo, izquierda: "thin" | "medium" | "thick" | "double" | "dashed" | "dotted" | "hair" | None

@dataclass(frozen=True, slots=True)
class CeldaVisual:
    ref: str                 # "F12", sin $
    fila: int                # base 1
    columna: int             # base 1
    mostrado: str            # el valor guardado como texto (Decimal en "f", fecha ISO, texto); "" si vacío
    formula: str | None      # "=F11*E12" si la celda tiene fórmula
    estilo: int              # índice en LibroVisual.estilos

@dataclass(frozen=True, slots=True)
class HojaVisual:
    nombre: str
    visible: bool            # False si hidden o veryHidden
    filas: int               # max_row usado
    columnas: int            # max_column usado
    anchos: Mapping[int, str]   # columna base 1 → ancho en caracteres de Excel, texto decimal
    altos: Mapping[int, str]    # fila base 1 → alto en puntos, texto decimal
    ocultas_filas: tuple[int, ...]
    ocultas_columnas: tuple[int, ...]
    combinadas: tuple[str, ...]  # "A1:D1"
    fijas: str | None            # celda de panes congelados, "B5"
    celdas: tuple[CeldaVisual, ...]  # solo las que tienen valor o estilo distinto del por omisión

@dataclass(frozen=True, slots=True)
class LibroVisual:
    nombre: str
    sha256: str
    hojas: tuple[HojaVisual, ...]  # en el orden del libro
    estilos: tuple[EstiloVisual, ...]

class LibroDemasiadoGrande(ArchivoRechazado): ...   # más de MAX_CELDAS_VISUALES celdas

MAX_CELDAS_VISUALES = 200_000

def replicar_libro(datos: bytes, nombre: str) -> LibroVisual: ...
```

- Primero `adapters.hoja_empresa.guardia.verificar_archivo(datos, nombre)`; luego **una** apertura en modo normal
  (`load_workbook(io.BytesIO(datos), data_only=False)`) para el aspecto y otra `data_only=True` en solo lectura para
  `mostrado` (o reusar la lectura de valores que ya hace `lector.py` si se puede sin cambiarlo; `lector.py` y
  `guardia.py` **no se modifican**).
- Colores: `rgb` ARGB → `#RRGGBB`; `indexed` con la paleta por omisión de Excel (constante con fuente: ECMA-376
  §18.8.27); `theme` con la paleta de Office por omisión y `tint` según ECMA-376 §18.8.19. Límite declarado en el
  docstring: los temas personalizados del libro no se leen.
- `mostrado` usa `Decimal(str(v))` y `format(d, "f")` para números (el formato numérico lo aplica el frontend con
  el código de `formato_numero`); fechas ISO.
- El ancho por omisión de Excel (8,43 caracteres) y el alto (15 pt) no se escriben en los mapas.

**Pruebas (`tests/unit/test_visual_libro.py`, libro construido con openpyxl en `tmp_path`, oráculo a mano):**
- `test_hojas_en_orden_y_visibilidad`: libro con «PORTADA», «APU-01», «Oculta» (hidden) → nombres en ese orden,
  `visible == (True, True, False)`.
- `test_combinadas_anchos_altos_y_ocultas`: `A1:D1` combinada, columna B ancho 20, fila 3 alto 30, columna C oculta,
  fila 5 oculta → `combinadas == ("A1:D1",)`, `anchos[2] == "20"`, `altos[3] == "30"`, `ocultas_columnas == (3,)`,
  `ocultas_filas == (5,)`.
- `test_coordenadas_base_1_y_ref_sin_dolar`: valor en `F12` → `CeldaVisual(ref="F12", fila=12, columna=6, ...)`.
- `test_valor_mostrado_es_el_guardado_y_conserva_la_formula`: libro de XlsxWriter con `=E12*2` y valor guardado
  `24.5` → `mostrado == "24.5"`, `formula == "=E12*2"`.
- `test_estilos_deduplicados`: 3 celdas con negrita roja `FFFF0000` → un solo `EstiloVisual` con `color="#FF0000"`,
  `negrita=True`; las tres apuntan al mismo índice.
- `test_color_de_tema_con_tinte`: tema 4 (accent1 `#4472C4`), tint `0.3999755851924192` → valor esperado calculado a
  mano en el docstring de la prueba (fórmula HSL de ECMA-376) y escrito como literal.
- `test_libro_sintetico_de_la_empresa`: `libro_limpio()` de `tests/fixtures/libros_empresa.py` → existen las hojas
  PORTADA, INSUMOS, APU-01, APU-02, APU-03 y PRESUPUESTO; el monto de APU-01 en PRESUPUESTO se muestra como
  `"1738.407"` (memoria del fixture).
- `test_rechaza_lo_que_rechaza_la_guardia` (bytes que no son zip → `ArchivoRechazado`) y
  `test_rechaza_mas_de_200000_celdas` (con `MAX_CELDAS_VISUALES` parcheado a 10 → `LibroDemasiadoGrande`).
- `test_no_escribe_sobre_el_original`: los bytes de entrada no cambian (sha256 antes y después).

- [ ] Rojo visto, verde, `uv run ruff check adapters tests`, commit `feat(hoja_empresa): replica visual del libro para el visor`.

### Task 2.3a: Sesión del navegador y `/app` con CSP · `silice-backend` · Opus high · worktree `.worktrees/s2c`

**Files:**
- Create: `api/sesion_web.py` (cookie, CSRF, dependencias), `api/rutas/sesion.py` (`/v1/sesion`), `api/interfaz.py`
  (montaje de `/app` y cabeceras), `tests/unit/test_api_sesion_web.py`, `tests/unit/test_api_interfaz.py`.
- Modify: `api/main.py` (solo agregar líneas: router de sesión **sin** `CON_CLAVE`, montaje de `/app`),
  `tests/unit/test_arquitectura.py` (solo agregar, si la regla de `api/` lo pide), `docs/api.json` (regenerado).

**Contrato:**
- Cookie `silice_sesion` = ficha de `seguridad.sesiones.abrir`; `HttpOnly`, `SameSite=Strict`, `Path=/`, sin `Max-Age`
  (de sesión), sin `Secure` (RS2-6).
- `csrf_de(ficha: str) -> str` = `hashlib.sha256(b"csrf:" + ficha.encode()).hexdigest()`; comparación con
  `hmac.compare_digest`.
- `POST /v1/sesion` `{login, contrasena}` → 200 `{login, nombre, roles: [..], csrf}` + `Set-Cookie`; credenciales
  malas → 401 `{detalle: MENSAJE_FALLO}`; bloqueada → 423 `{detalle: MENSAJE_BLOQUEO}`; `debe_cambiar_clave` → 403
  «Cambie su contraseña en la interfaz clásica antes de usar la nueva.» (sin cookie). Pasa la IP del cliente a
  `autenticar`.
- `GET /v1/sesion` → 200 con el mismo cuerpo (renueva `csrf`) o 401 sin sesión válida.
- `DELETE /v1/sesion` (exige CSRF) → 204, cierra la ficha (`sesiones.cerrar(..., "salida")`) y borra la cookie.
- Dependencia `exigir_clave_o_sesion(accion: Accion)`: con cabecera `X-Silice-Clave` → `exigir_clave_api` de hoy;
  si no, cookie válida (`sesiones.validar`) → si no hay, 401; si el método no es GET/HEAD, exige `X-Silice-CSRF`
  correcto y `Origin` igual a `http://<Host>` (si `Origin` falta, 403) → si no, 403; rol sin `accion` → 403.
- `/app`: `StaticFiles(directory=RAIZ / "frontend-desktop" / "dist", html=True)` montado en `/app`; si la carpeta no
  existe, `/app` responde 404 `{detalle: "La interfaz nueva no está compilada (npm run build en frontend-desktop)."}`.
  `GET /app` redirige 307 a `/app/`. Cabeceras en toda respuesta de `/app`: `Content-Security-Policy:
  default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src
  'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'`
  (`'unsafe-inline'` en estilos solo si Univer o Carbon lo exigen; 2.4 lo comprueba en el navegador y, si no hace
  falta, se quita), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-cache`
  para `index.html`.

**Pruebas (`TestClient`, base de instalación temporal con `tests/fixtures/instalacion.py`, rojo primero):**
- `test_entrar_pone_cookie_httponly_samesite_strict_y_devuelve_csrf`.
- `test_contrasena_mala_da_401_sin_cookie` y `test_cinco_fallos_bloquean_con_423`.
- `test_cuenta_que_debe_cambiar_clave_da_403_sin_cookie`.
- `test_get_sesion_sin_cookie_da_401` / `test_get_sesion_con_cookie_da_el_usuario`.
- `test_salir_sin_csrf_da_403` / `test_salir_cierra_la_ficha_y_borra_la_cookie`.
- `test_sesion_expirada_por_inactividad_da_401` (reloj inyectado o fila con `ultima_actividad` vieja).
- `test_post_con_cookie_sin_csrf_da_403`, `test_post_con_csrf_y_origin_ajeno_da_403`,
  `test_post_con_csrf_sin_origin_da_403`, `test_post_con_cookie_y_csrf_pasa`.
- `test_rol_administrador_solo_da_403_en_libros` (RS2-5) y `test_rol_revisa_pasa`.
- `test_con_clave_de_api_las_rutas_de_libros_siguen_igual` (sin cookie).
- `test_app_sin_compilar_da_404_con_mensaje`, `test_app_sirve_index_con_csp` (carpeta `dist` falsa en `tmp_path`
  parcheando la ruta), `test_app_redirige_a_la_barra_final`, `test_ninguna_clave_en_el_html_servido`.
- `test_la_csp_no_permite_unsafe_eval_ni_anfitriones_externos`.

- [ ] Rojo visto, verde, `uv run python scripts/exportar_openapi.py`, `ruff`, commit `feat(api): sesion del navegador con cookie y anti-CSRF y /app con CSP`.

### Task 2.3b: `POST /v1/libros/replica` e `indicadores` · `silice-backend` · Opus high · tras 2.2 y 2.3a

**Files:** Modify `api/rutas/libros.py` (ruta nueva; campo aditivo `indicadores`; las rutas de libros pasan de
`CON_CLAVE` a `exigir_clave_o_sesion(Accion.LEER_PROYECTO)`), `api/main.py` (solo esa línea), `docs/api.json`.
Test: `tests/unit/test_api_libros_replica.py`, ampliar `tests/integration/test_api_libros.py` existente con
`indicadores`.

**Contrato:**
- `POST /v1/libros/replica` multipart `libro` (misma validación 415/413 que `/auditoria`) → `LibroVisualRespuesta`
  (espejo Pydantic de `LibroVisual`; `anchos`/`altos` como `dict[str, str]` con la columna/fila en texto). Errores
  de la guardia o `LibroDemasiadoGrande` → 422 con su mensaje; otro fallo → 500 fijo (reusar `_rechazo`).
- `IndicadorRespuesta {clave, titulo, actual, meta, delta, delta_pct: str | None, sentido: "costo"}`; claves
  `SUBSINIVA` («Subtotal sin IVA»), `IVATOT` («IVA»), `TOTALGEN` («Total general»), solo las presentes en los dos
  totales. `delta = actual - meta`; `delta_pct = (delta / meta * 100).quantize(Decimal("0.01"), ROUND_HALF_EVEN)`,
  `None` si `meta == 0`. Función pura `indicadores_de(totales_libro, totales_silice) -> list[...]` con su prueba.

**Pruebas:**
- `test_replica_del_libro_limpio_trae_sus_hojas_y_el_monto_de_apu_01` (`"1738.407"`).
- `test_replica_rechaza_lo_que_no_es_xlsx_con_415` y `test_replica_de_un_zip_roto_da_422`.
- `test_indicadores_del_libro_limpio_no_tienen_variacion` (`delta == "0"` o `"0.00..."` según el `format`; fijar el
  literal en la prueba tras verlo, con el oráculo de la memoria del fixture).
- `test_indicadores_con_sobreprecio_sembrado`: libro con una siembra que cambia el total (de las siembras H del
  fixture) → `delta` y `delta_pct` contra cuenta a mano escrita en la prueba.
- `test_meta_cero_da_delta_pct_nulo` (función pura).
- `test_replica_con_cookie_y_csrf_pasa` y `test_replica_sin_nada_da_401`.

- [ ] Rojo visto, verde, `docs/api.json` regenerado, commit `feat(api): replica visual del libro e indicadores de la auditoria`.

### Task 2.4: Visor `UniverGrid` + capa de halos + entrada · `silice-frontend` · Sonnet high · tras 2.1 (y contrato de 2.3)

**Files (en `frontend-desktop/src/`):**
- `api/cliente.ts` (fetch con `credentials: "same-origin"`, `X-Silice-CSRF` en POST/DELETE, error `{detalle}` →
  `ErrorDeApi`), `api/tipos.ts` (espejo de `LibroVisualRespuesta`, `LibroAuditadoRespuesta`, `IndicadorRespuesta`).
- `sesion/Entrar.tsx` (Carbon `Form`, `TextInput`, `PasswordInput`, `Button`, `InlineNotification`), `sesion/useSesion.ts`.
- `replica/aUniver.ts` (**único** lugar de la conversión base 1 → base 0, caracteres → px, puntos → px, estilos →
  `IStyleData`, combinadas → `mergeData`, ocultas → `hd: 1`); `replica/formatoNumero.ts` (formato de texto mostrado
  con el código de Excel: subconjunto `General`, `0`, `0.00`, `#,##0.00`, porcentajes y fechas; lo demás se muestra
  como llega).
- `visor/UniverGrid.tsx` (Univer de `@univerjs/presets` + `preset-sheets-core`, **solo lectura**: sin barra de
  herramientas ni de fórmulas, edición bloqueada con el permiso de hoja/libro de Univer; telemetría apagada; sin
  workers), `visor/celdas.ts` (parseo de `HOJA!REF` → `{hoja, fila0, columna0}`; separa por el **último** `!`;
  `REF` que no es A1 → `null`), `visor/capaHalos.ts` (hallazgos → halos; severidad → token + ícono + texto),
  `visor/CapaHalos.tsx` (posiciones desde los rectángulos de celda de Univer; se recalcula en desplazamiento,
  acercamiento y cambio de hoja; sin animación), `visor/ListaHallazgos.tsx` (`DataTable` Carbon `size="sm"`, filtro
  por severidad con `Tag`s, celda en Plex Mono, impacto alineado a la derecha; grupo «Sin celda en el libro»),
  `visor/Visor.tsx` (`FileUploaderDropContainer` solo `.xlsx`, fecha de devolución = hoy editable, llama a
  `/v1/libros/replica` y `/v1/libros/auditoria` en paralelo; esqueletos de Carbon mientras carga; errores con el
  `detalle`).
- `App.tsx`: sin sesión → `Entrar`; con sesión → cabecera con nombre y «Salir» + `Visor`.

**Diseño (DESIGN.md manda):** primera vista con hoja a la izquierda y lista de 320 px a la derecha; franja de
indicadores arriba (2.5); a 1366×768 no hay desplazamiento horizontal de la página (la hoja desplaza dentro de su
lienzo). Clic en un hallazgo → Univer va a esa hoja y celda y la selecciona; clic en una celda marcada → la fila de
la lista se resalta y recibe el foco. Íconos de severidad de `@carbon/icons-react`. Copia en español llano.

**Pruebas (Vitest + RTL; Univer se sustituye por un doble en jsdom, rojo primero):**
- `celdas.test.ts`: `"PRESUPUESTO!F12"` → `{hoja:"PRESUPUESTO", fila0:11, columna0:5}`; `"APU-01!G48"` →
  `{fila0:47, columna0:6}`; `"PLAN DE PAGOS!AA3"` → `columna0:26`; `"APU-01!Rendimiento"` → `null`; `""` → `null`;
  `"A!B!C3"` → hoja `"A!B"`.
- `aUniver.test.ts`: con el JSON de 2.6 (`tests/fixtures/replica/libro_minimo.json`) → `cellData[11][5].v` es el
  `mostrado` de `F12`; combinada `A1:D1` → `{startRow:0,startColumn:0,endRow:0,endColumn:3}`; columna 3 oculta →
  `columnData[2].hd === 1`; ancho 20 caracteres → px según la fórmula de Excel (`trunc((20*7+5)/7*256)/256*7`,
  redondeado, con el valor esperado escrito en la prueba); alto 30 pt → 40 px.
- `capaHalos.test.ts`: CRITICO → `{token:"--silice-sev-critico", icono:"ErrorFilled", texto:"Crítico"}`; ERROR,
  ADVERTENCIA, INFO con los suyos; código `ATIPICO` → `--silice-atipico` (morado) cualquiera sea su severidad;
  hallazgo sin celda → fuera de los halos y dentro de `sinCelda`.
- `ListaHallazgos.test.tsx`: filtrar por «Crítico» deja solo esos; cada fila tiene el nombre de la severidad en texto
  (no solo color); clic llama a `irACelda` con la hoja y la celda.
- `Entrar.test.tsx`: credenciales malas muestran el `detalle` de la API; el formulario no guarda nada en
  `localStorage` (espía sobre `Storage.prototype.setItem` sin llamadas).
- `cliente.test.ts`: POST lleva `X-Silice-CSRF`; `credentials: "same-origin"`; 401 → `ErrorDeApi` con `estado 401`.
- **Verificación manual obligatoria** (no prueba automática): `npm run build`, API con `/app`, libro limpio del
  fixture; capturas a 1366×768 y 1920×1080; consola del navegador sin violaciones de CSP (si Univer exige
  `'unsafe-inline'` o `blob:`, se deja y se justifica en la bitácora; si no, se quita de la CSP de 2.3a).

- [ ] Rojo visto, verde, lint, build, capturas; commit `feat(interfaz): visor de solo lectura con halos de severidad`.

### Task 2.5: Tarjeta `IndicadorFiori` con semántica IBCS · `silice-frontend` · Sonnet medium · tras 2.1, en paralelo con 2.4

**Files:** `frontend-desktop/src/indicadores/{ibcs.ts,IndicadorFiori.tsx,FranjaIndicadores.tsx}` y sus pruebas.

**Contrato:** `semanticaIbcs(delta: string, sentido: "costo" | "rendimiento"): "favorable" | "desfavorable" |
"neutro"` sin `Number()` (signo por texto; cero si coincide con `/^-?0*(\.0*)?$/`). `IndicadorFiori` según la skill
§2 (valor grande `heading-03`, meta en secundario, Δ y Δ% con ▲/▼ y texto oculto «favorable»/«desfavorable»); la
meta se dibuja con **contorno** y el valor real con relleno sólido en el mini-gráfico de barra (IBCS §3.2); sin
tarjetas con sombra: celdas separadas por divisores de 1 px. `FranjaIndicadores` pinta la lista `indicadores` de la
API más los conteos por severidad (`Tag` con ícono; un conteo no es una variación: sin rojo/verde IBCS).

**Pruebas:**
- `ibcs.test.ts`: costo `"12.50"` → desfavorable; costo `"-3.10"` → favorable; rendimiento `"4"` → favorable;
  rendimiento `"-4"` → desfavorable; `"0"`, `"0.00"`, `"-0.00"` → neutro en los dos sentidos.
- `IndicadorFiori.test.tsx`: con `delta_pct: null` no se muestra «%»; la clase de color es `ibcs-desfavorable` para
  costo positivo; el texto accesible «desfavorable» está en el DOM; los montos se muestran **exactos** como llegan
  (`"1738.407"` no se redondea).

- [ ] Rojo visto, verde, commit `feat(interfaz): indicadores Fiori con semantica IBCS`.

### Task 2.6: Pruebas de coordenadas, oráculo compartido · `silice-pruebas` · Sonnet high · tras 2.2, **antes** de 2.4

> Orden corregido en la ejecución (2026-10-18): las pruebas de `aUniver.test.ts` de la 2.4 leen el JSON de
> esta tarea, así que el oráculo (lado Python) se escribe primero; la comprobación del lado TS la agrega la 2.4.

**Files:** Create `tests/fixtures/replica/libro_minimo.py` (construye el libro con openpyxl: hojas `PORTADA` y
`PLAN DE PAGOS` con espacio, `A1:D1` combinada, columna C oculta, fila 5 oculta, `F12` con fórmula y valor guardado,
`AA3` con texto), `tests/fixtures/replica/libro_minimo.json` (salida esperada **escrita a mano**, no generada por
`visual.py`), `tests/fixtures/replica/ORACULO.md` (la tabla celda → valor → fila0/columna0 hecha a mano),
`tests/unit/test_replica_oraculo.py`. El JSON lo leen también las pruebas de `aUniver.test.ts`.

**Pruebas:**
- `test_visual_reproduce_el_oraculo_a_mano`: `replicar_libro(libro_minimo())` serializado como lo serializa la API
  == `libro_minimo.json` (comparación campo a campo con mensajes legibles).
- `test_la_api_responde_el_oraculo`: `POST /v1/libros/replica` con ese libro == el JSON.
- `test_el_oraculo_y_su_tabla_coinciden`: cada fila de `ORACULO.md` está en el JSON (evita que el JSON y la tabla
  diverjan).
- En TS (`aUniver.test.ts`, ya en 2.4): cada fila de la tabla cae en `cellData[fila0][columna0]` y su halo se pide
  para esa misma posición.
- Revisión de no circularidad: el JSON se escribe a mano desde `ORACULO.md`; si `visual.py` y el JSON discrepan, se
  corrige el código, nunca el JSON sin explicación en la bitácora.

- [ ] Rojo visto, verde, commit `test(replica): oraculo compartido de coordenadas backend y pantalla`.

### Task 2.7: Instalador con la interfaz compilada y presupuesto de tamaño · `silice-backend` · Sonnet medium (excepción RS-7) · tras 2.1 y 2.3a

**Files:** Modify `instalador/manifiesto.toml` (`[interfaz] dist = "frontend-desktop/dist"`), `instalador/construir.py`
(copia el `dist` ya compilado a `frontend-desktop/dist` dentro de la app; si falta, el build falla con mensaje
claro), `.github/workflows/instalador.yml` (paso Node 22 + `npm ci` + `npm run build` antes de construir),
`tests/unit/test_instalador_*.py` (el manifiesto incluye el `dist`; sin `dist` el constructor falla).

**Criterio:** el instalador básico sigue ≤ 150 MB (`instalador/tamanos.py`); la CI de PR del instalador lo mide
porque `instalador/**` cambia. El presupuesto del `dist` (≤ 15 MB) lo controla el job `interfaz` (2.1).

- [ ] Rojo visto, verde, commit `feat(instalador): la interfaz nueva compilada viaja en el instalador`.

### Task 2.8: Cierre 1.2.0 · orquestador + `silice-escriba` (Haiku low)

- [ ] `git fetch && git merge origin/main` (PR #87 y la sesión 1 pueden haber llegado); `docs/api.json` regenerado.
- [ ] Suite completa una vez: `uv run pytest -W error --junitxml=reporte-pruebas.xml` +
  `uv run python scripts/verificar_omitidas.py reporte-pruebas.xml`; `uv run ruff check .`;
  `uv run python scripts/guardia_nucleo.py --base origin/main`; en `frontend-desktop/`: `npm ci`, `npm run
  licencias`, `npm run lint`, `npm test`, `npm run build`, `npm run dist`.
- [ ] Detector de impeccable una vez sobre la interfaz terminada:
  `node ~/.claude/skills/impeccable/scripts/detect.mjs --json frontend-desktop/src`.
- [ ] Revisores de la sesión 2 (ruta §3.2): arquitectura, seguridad, requisitos, pruebas, **diseño** (con
  `PRODUCT.md`, `DESIGN.md` y las capturas) y hechos; además `impeccable-finish-reviewer` sobre el visor. Hallazgos
  bloqueantes → se corrigen y se vuelve a pasar.
- [ ] Versión **1.2.0** (o la siguiente libre en `main`, RT-8) en `pyproject.toml` en el último commit; CHANGELOG;
  bitácora `docs/bitacora/2026-10-ruta-s2.md` con rulings RS2-*, bloqueos (B-3) y diferidos.
- [ ] PR a `main`, CI verde (calidad, ubuntu, windows, interfaz), fusión con merge commit.

## Diferido (con motivo)

| Qué | Motivo | Cuándo |
|---|---|---|
| Tema oscuro g100 | RS2-3 | sesión 3 o cuando se pida |
| Halo morado alimentado por RF-100 | RF-100 corre en la pestaña Precios, no en `/v1/libros` | sesión 3 (3.5) |
| Popover y acciones de 1 clic, Capa Delta | sesión 3 | sesión 3 |
| Cookie `Secure` / HTTPS en la red local | RS2-6 | sesión 5 |
| Libro real anonimizado como verificación | B-3 | cuando Eugenio lo entregue |
