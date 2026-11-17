# Plan de desenredo de capas (2026-11-17)

> **Para agentes:** sub-skill obligatoria: superpowers:subagent-driven-development (recomendada) o
> superpowers:executing-plans, tarea por tarea. Cada paso lleva casilla (`- [ ]`).

**Objetivo:** que la deuda de capas deje de crecer (guardias con lista de excepciones congelada) y
después bajarla: una sola lectura y una sola presentación de cifras, una sola política de
«rendimiento vigente» fuera del núcleo, rutas sin consultas SQL propias y módulos de tamaño legible.

**Arquitectura:** primero pruebas de arquitectura que fotografían el estado actual y fallan si
empeora (ola 1). Luego se unifican funciones duplicadas (ola 2), se sacan las consultas de
`api/rutas` hacia `aplicacion`, `seguridad` y `produccion` (ola 3) y se parten los módulos
grandes dejando una fachada que reexporta (ola 4). Los ciclos de importación se planifican, pero
quedan bloqueados hasta el aval del tutor (ola 5). Cada tarea vacía una fila de alguna lista
congelada; la lista solo puede achicarse.

**Tecnología:** Python 3.13, FastAPI, SQLAlchemy 2, pytest, `ast` de la biblioteca estándar.

**Fuente:** revisión del 2026-11-17 sobre `main` 5f910132 (los siete problemas del encargo) y la
decisión de Eugenio del mismo día sobre el redondeo de presentación. Líneas confirmadas en
`.worktrees/s2m4` (rama `feature/mejoras-ola2`, 8edeb9ae).

## Restricciones globales

- `core/` no cambia. Se puede **llamar** a `core.verification.texto.formatear_decimal`
  (`core/verification/texto.py:216`) y leer `DECIMALES_PRESENTACION = 2`
  (`core/verification/informe.py:30`); no se edita ningún archivo de `core/`.
- Cálculo: `Decimal` con 28 dígitos y `ROUND_HALF_EVEN` del contexto. Presentación: dos decimales
  con `ROUND_HALF_UP` (decisión de Eugenio, 2026-11-17).
- El contrato de la API sigue con punto decimal; la coma decimal y el punto de miles los pone el
  navegador (`frontend-desktop/src/indicadores/formatoEsVe.ts`). Los campos que vuelven tal cual
  usan `aplicacion.cifras.texto_de_cifra` (coma), como hoy.
- El simulador (`aplicacion/simulador.py:26-30`, `PASO_DE_PRESENTACION`) conserva su redondeo al
  par hasta que el tutor decida. Ninguna guardia lo toca.
- TDD: la prueba en rojo se ve fallar antes del cambio. Suite completa al cerrar cada ola.
- Casos de prueba construidos a mano; nada de libros reales ni nombres de empresa.
- Las ayudas de las guardias viven en `tests/unit/test_arquitectura.py`
  (`test_ningun_modulo_de_prueba_importa_de_otro_modulo_de_prueba` prohíbe compartirlas).
- Un commit por tarea, con la prueba y el cambio juntos o en dos commits (rojo, verde), como en
  las ramas `feature/depurar-*`.

## Qué puede salir mal y nadie lo prueba (foco de revisión)

1. **Cero con signo al presentar.** `formatear_decimal(Decimal("-0.001"), 2)` da `"-0.00"`; hoy
   `api/rutas/libros.py:604` lo muestra `"0.00"`. La prueba de `monto` lo fija (tarea 2.2).
2. **Montos que no caben al cuantizar.** Un `quantize` con más de ~26 cifras enteras lanza
   `InvalidOperation`; `libros._centesimas` devuelve el exacto. `monto` debe hacer lo mismo
   (tarea 2.2).
3. **Nombre de obra que es un número.** `resolver_proyecto("12")` busca primero el `id` 12;
   `proyecto_por_nombre("12")` debe buscar solo el nombre. Prueba en la tarea 2.5.
4. **Fachadas y `monkeypatch`.** Al mover código de `aplicacion/hoja.py` o `aplicacion/control.py`,
   un `monkeypatch.setattr("aplicacion.hoja.X", ...)` deja de alcanzar la función movida y la prueba
   sigue en verde sin probar nada. Las tareas 4.3 y 4.4 retargetean cada uno (hoy 10 en `tests/`).
5. **Listas congeladas medidas antes de la unión.** Si se toman en `s2m4` sin las ramas de
   depuración, la guardia falla en cuanto se unan (p. ej. `adapters/hoja_empresa/escritor/calculos.py`
   crece 52 líneas en `feature/depurar-lector`). Todas se generan **después** de la precondición.

---

## Precondición: la unión de las ramas de depuración

Ramas en `s2m4` (`git branch --list "feature/depurar-*"`), commits propios sobre
`feature/mejoras-ola2`:

| Rama | Commits | Archivos de producción que toca |
|---|---|---|
| `depurar-api` | 19 | `api/main.py`, `api/admin_acceso.py`, `api/rutas/{admin_*, computos, control, entregas, obras, presupuestos, revision}.py`, `aplicacion/hoja_vista.py` |
| `depurar-desperdicio` | 19 | **el mismo commit que `depurar-api` (11aeada9)**: no aporta nada distinto |
| `depurar-auditar-hoja` | 0 | ninguno (apunta a la base) |
| `depurar-bcv-operacion` | 17 | `adapters/bcv/*`, `adapters/civil/ifc.py`, `api/rutas/admin_instalacion.py`, `operacion/{base_datos, eventos_perdidos, ordenes_100, registro}.py` |
| `depurar-control` | 17 | `aplicacion/{control, mesa, plan_rendimientos, precios_empresa, reajuste, vial}.py` |
| `depurar-hoja` | 8 | solo `frontend-desktop/src/paginas/hoja/*` |
| `depurar-hoja-aplicacion` | 6 | `aplicacion/{hoja_borradores, libro_a_la_hoja}.py` |
| `depurar-lector` | 20 | `adapters/hoja_empresa/{escritor/calculos, escritor/copia, escritor/devolucion, pdf, plantilla, reglas}.py` |
| `depurar-marco` | 4 | solo `frontend-desktop/src/marco/*` |
| `depurar-paginas-a` | 12 | solo `frontend-desktop/src/paginas/*` |
| `depurar-paginas-b` | 10 | solo `frontend-desktop/src/paginas/*` |
| `depurar-planos` | 10 | `adapters/espacio/planos/{dxf, informe}.py` |
| `depurar-revision` | 12 | `aplicacion/{entrega, instalacion, revision}.py`, `paquete/verificar.py` |

Las doce borran 156 líneas de `docs/bitacora/auditoria-agy-2026-11-15.md` y tocan 3 líneas de
`tests/integration/test_api_hoja_libro.py`: es el conflicto que se repite en cada unión.

- [ ] **P.1** Unir las once ramas con contenido en una rama de trabajo (aquí
  `feature/depuracion-unida`; el nombre lo pone quien una) sobre `feature/mejoras-ola2`.
- [ ] **P.2** Línea base verde, con la salida guardada para comparar:
  `uv run pytest -W error -q` · `uv run ruff check .` · `uv run python scripts/meta_datos.py` ·
  `uv run python scripts/guardia_nucleo.py`.
- [ ] **P.3** Anotar el commit de la unión en la cabecera de este plan. Todas las listas
  congeladas de la ola 1 se miden sobre ese commit.

Ninguna tarea empieza antes de P.3. Las ramas sugeridas salen de `feature/depuracion-unida`.

---

## Ola 1: guardias con lista congelada (solo pruebas; 7 tareas)

Todas siguen el mismo patrón de trinquete, en `tests/unit/test_arquitectura.py`:

- un diccionario o conjunto congelado con lo que hoy incumple, con la fecha `2026-11-17`;
- `test_<regla>`: lo que no está en la lista cumple la regla y lo que está no empeora;
- `test_<regla>_sin_sobrantes`: si una fila ya cumple, la prueba falla hasta que se borre la fila
  (así la lista solo se achica);
- `test_<regla>_ve_la_falta` con `tmp_path`: la ayuda detecta un caso construido (el rojo tiene que fallar de verdad).

Ninguna tarea de esta ola cambia código de producción, así que no choca con ninguna rama
`depurar-*` (ya están unidas). Ninguna toca `core/`.

### Tarea 1.1: matriz de dependencias entre paquetes

**Archivos:** Modificar `tests/unit/test_arquitectura.py` (después de `PAQUETES_FUERA_DEL_NUCLEO`,
línea 18).

**Interfaces:**
- Produce: `_imports_de_ejecucion_de_paquete(paquete: str) -> dict[str, set[str]]` (paquete de
  primer nivel importado → archivos que lo importan; incluye imports locales dentro de funciones,
  excluye los bloques `if TYPE_CHECKING:`). La usan 1.3 y 1.2.
- Produce: `DEPENDENCIAS_PERMITIDAS: dict[str, frozenset[str]]`, una fila por paquete de
  `PAQUETES_FUERA_DEL_NUCLEO` más `core`.

- [ ] **Paso 1: escribir las pruebas**
  - `test_cada_paquete_solo_importa_su_lista_blanca`: para cada paquete, los paquetes internos
    importados ⊆ `DEPENDENCIAS_PERMITIDAS[paquete]`; el mensaje cita `archivo:línea`.
  - `test_la_matriz_cubre_todo_paquete`: claves de `DEPENDENCIAS_PERMITIDAS` ==
    `set(PAQUETES_FUERA_DEL_NUCLEO) | {"core"}`.
  - `test_la_matriz_ve_un_import_local(tmp_path)`: un archivo con `def f(): from api import x`
    dentro de un paquete falso produce la arista hacia `api`.
  - `test_la_matriz_ignora_type_checking(tmp_path)`: un import bajo `if TYPE_CHECKING:` no cuenta.
- [ ] **Paso 2:** con la matriz vacía, correr
  `uv run pytest -W error -q tests/unit/test_arquitectura.py -k matriz` y ver el rojo con la lista
  de aristas reales.
- [ ] **Paso 3:** llenar `DEPENDENCIAS_PERMITIDAS` con lo medido en la unión. Referencia medida en
  `s2m4`: `api → adapters, aplicacion, asistente, auditoria, core, fusion, ml, operacion, paquete,
  produccion, seguridad`; `aplicacion → adapters, asistente, auditoria, core, ml, operacion,
  paquete, produccion, seguridad`; `seguridad → operacion`; `operacion → migraciones, ml,
  seguridad`; `migraciones → adapters, aplicacion, asistente, fusion, paquete, produccion,
  seguridad`. Las aristas que forman ciclo (`seguridad → operacion`, `migraciones → aplicacion`,
  `asistente → aplicacion`, `fusion → aplicacion`) llevan un comentario `# ciclo, ola 5`.
- [ ] **Paso 4:** verde con el mismo comando.
- [ ] **Paso 5:** commit.

**Verificación:** `uv run pytest -W error -q tests/unit/test_arquitectura.py`.
**Rama:** `feature/desenredo-guardias` (las siete tareas de la ola en la misma rama, un commit cada una).
**Choques:** ninguno.
**Aval:** la prueba entra sin aval porque solo congela lo que hay. Corregir la tabla de
`docs/arquitectura.md` §4 (hoy dice `api → core, adapters, ml` y la realidad son once paquetes) es
enmienda de la vista de desarrollo: **con aval del tutor**. Mientras no lo haya, la matriz es la
fuente y §4 lleva una nota que la cita.

### Tarea 1.2: rutas sin `select()`, sin `core.models` y sin el núcleo por dentro

**Archivos:** Modificar `tests/unit/test_arquitectura.py`.

**Interfaces:**
- Produce: `SELECT_EN_RUTAS: dict[str, int]` (archivo → número de llamadas `select(` hoy).
  Medido en `s2m4`: `admin_claves_api.py 1, admin_empresas_registradas.py 1, cuentas.py 1,
  entregas.py 1, listas.py 1, presupuestos.py 4, produccion.py 2, reajuste.py 1, rendimientos.py 1`.
- Produce: `MODELOS_EN_RUTAS: frozenset[str]` (archivos de `api/rutas` que importan `core.models`
  o `from core import models`). Medido: `entregas, listas, presupuestos, reajuste, rendimientos,
  revision`.
- Produce: `NUCLEO_PROFUNDO_EN_RUTAS: dict[str, frozenset[str]]` (archivo → módulos `core.X.Y`
  que no son `core.contracts.*` ni `core.verification.texto`). Medido: 13 archivos.

- [ ] **Paso 1:** pruebas `test_las_rutas_no_consultan_la_base`,
  `test_las_rutas_no_importan_los_modelos_del_nucleo`,
  `test_las_rutas_no_entran_al_nucleo_por_dentro`, cada una con su `_sin_sobrantes` y su
  `_ve_la_falta(tmp_path)`. La cuenta de `select(` se hace por AST (`ast.Call` cuyo nombre es
  `select`), no por texto: así un comentario no cuenta.
- [ ] **Paso 2:** rojo con las listas vacías; **Paso 3:** llenarlas con lo medido en la unión;
  **Paso 4:** verde; **Paso 5:** commit.

**Verificación:** `uv run pytest -W error -q tests/unit/test_arquitectura.py -k rutas`.
**Choques:** ninguno. **Aval:** no.

### Tarea 1.3: cero ciclos nuevos

**Archivos:** Modificar `tests/unit/test_arquitectura.py` (junto a `_hay_ciclo`, línea 506).

**Interfaces:**
- Consume: `_imports_de_ejecucion_de_paquete` (1.1).
- Produce: `_componentes_fuertes(grafo: dict[str, set[str]]) -> list[frozenset[str]]`
  (Tarjan; solo componentes de dos o más nodos).
- Produce: `CICLOS_CONOCIDOS: dict[frozenset[str], str]` (componente → «2026-11-17, motivo»), y
  `CICLO_DE_PAQUETES_CONOCIDO: frozenset[str]`.

Medido en `s2m4` (imports de ejecución, locales incluidos, sin `TYPE_CHECKING`):
- módulos: `{seguridad.cuentas, seguridad.sesiones}` y uno de once en `aplicacion`:
  `{aprobaciones, control, entrega, frentes, hoja, hoja_partidas, mercado, mesa,
  precios_declarados, procura, vial}`;
- paquetes: `{aplicacion, asistente, auditoria, fusion, migraciones, operacion, paquete, seguridad}`.
- Sin contar los imports locales no hay ningún ciclo: todos están esquivados dentro de funciones.

- [ ] **Paso 1:** `test_el_detector_de_componentes_ve_dos_ciclos_separados` (grafo a mano
  `a→b→a`, `c→d→c`, `e` suelto: dos componentes, `e` fuera); `test_no_aparecen_ciclos_nuevos`
  (cada componente medido es uno de `CICLOS_CONOCIDOS` o está contenido en uno);
  `test_un_ciclo_conocido_no_crece`; `test_ciclos_conocidos_sin_sobrantes` (un componente
  conocido que ya no existe obliga a borrar su fila); lo mismo para paquetes.
- [ ] **Pasos 2 a 5:** rojo con listas vacías, llenar, verde, commit.

**Verificación:** `uv run pytest -W error -q tests/unit/test_arquitectura.py -k ciclo`.
**Choques:** ninguno. **Aval:** la guardia no necesita aval (no rompe nada); **salir** de los
ciclos sí (ola 5).

### Tarea 1.4: una sola presentación numérica en la API

**Archivos:** Modificar `tests/unit/test_arquitectura.py`.

**Interfaces:**
- Produce: `PRESENTACION_SUELTA_EN_API: dict[str, int]` (archivo de `api/` → número de sitios).
  Un sitio es, por AST: una llamada `.quantize(`, un nombre `ROUND_HALF_*`, una llamada
  `format(<x>, "f")` o una función privada cuyo parámetro se anota `Decimal` y devuelve `str`.
  Excluido: `api/presentacion.py` (tarea 2.2) y las llamadas a `texto_de_cifra`.
- Medido en `s2m4` (orientativo): `rutas/aprobaciones, auditorias_libro, entregas, fcas,
  hoja_libro, indices, libros, mercado, obras, produccion, revision, riesgo, tablero` y
  `esquemas_hoja, esquemas_informe, esquemas_vial`.

- [ ] **Paso 1:** `test_la_api_presenta_cifras_en_un_solo_sitio`, `_sin_sobrantes`,
  `_ve_la_falta(tmp_path)` (un `def _x(v: Decimal) -> str: return format(v, "f")` cuenta como un
  sitio).
- [ ] **Pasos 2 a 5:** rojo, llenar, verde, commit.

**Verificación:** `uv run pytest -W error -q tests/unit/test_arquitectura.py -k presenta`.
**Choques:** ninguno. **Aval:** no.

### Tarea 1.5: tope de tamaño por módulo

**Archivos:** Modificar `tests/unit/test_arquitectura.py`.

**Interfaces:**
- Produce: `TOPE_DE_LINEAS = 1000` y `MODULOS_GRANDES: dict[str, int]` (archivo → líneas en la
  unión). Medido en `s2m4`: `aplicacion/hoja.py 3195, adapters/hoja_empresa/reglas.py 1705,
  aplicacion/control.py 1571, aplicacion/composicion.py 1471, adapters/hoja_empresa/pdf.py 1388,
  api/rutas/hoja.py 1348, adapters/hoja_empresa/escritor/calculos.py 1289,
  api/rutas/presupuestos.py 1119, api/esquemas_hoja.py 1061, api/rutas/libros.py 1038,
  aplicacion/hoja_vista.py 1029`. Tras la unión cambian al menos `control.py`, `presupuestos.py`,
  `hoja_vista.py`, `reglas.py`, `pdf.py` y `calculos.py`: **medir de nuevo**.

- [ ] **Paso 1:** `test_ningun_modulo_pasa_del_tope` (todo `.py` de producción fuera de `core/` y
  `tests/`), `test_un_modulo_grande_no_crece` (líneas ≤ su valor congelado),
  `test_modulos_grandes_sin_sobrantes` (si baja del tope, se borra la fila; si baja de su valor
  congelado, el valor se actualiza a la baja: la prueba muestra el número nuevo).
- [ ] **Pasos 2 a 5.**

**Verificación:** `uv run pytest -W error -q tests/unit/test_arquitectura.py -k tope`.
**Choques:** ninguno tras la unión. **Aval:** no.

### Tarea 1.6: toda tabla está en el modelo de datos

**Archivos:** Modificar `tests/unit/test_arquitectura.py`.

**Interfaces:**
- Consume: `migraciones.metadatos.METADATAS_CASO` y `METADATAS_INSTALACION`
  (`migraciones/metadatos.py:34` y `:51`).
- Produce: `TABLAS_SIN_DOCUMENTAR: frozenset[str]`. Criterio: el nombre de la tabla aparece entre
  comillas invertidas en `docs/modelo_datos.md`. Medido en `s2m4`: 96 tablas, 48 sin mención
  (entre ellas `partida`, `presupuesto`, `insumo`, `clave_api`, las `mp_*` y `prod_calculo`).

- [ ] **Paso 1:** `test_toda_tabla_esta_en_el_modelo_de_datos`, `_sin_sobrantes`.
- [ ] **Pasos 2 a 5.**

**Verificación:** `uv run pytest -W error -q tests/unit/test_arquitectura.py -k modelo_de_datos`.
**Choques:** ninguno. **Aval:** no. Vaciar la lista es trabajo de documentación aparte (fuera de
este plan; cada fila se borra cuando su tabla entra en `docs/modelo_datos.md`).

### Tarea 1.7: todo RF del ERS está en el plan de pruebas

**Archivos:** Modificar `tests/unit/test_arquitectura.py`.

**Interfaces:**
- Produce: `RF_SIN_PRUEBA: frozenset[str]`. Criterio: `RF‑N` o `RF-N` (con guion normal o el de no
  separación U+2011) que aparece en `docs/ERS.md` y no en `docs/plan_pruebas.md` entre `## 8.` y
  `## 9.`. Medido en `s2m4`: 191 RF en el ERS, 111 en §8, 80 sin fila (RF‑80 a RF‑89, RF‑101 a
  RF‑110, RF‑166 a RF‑193, entre otros).

- [ ] **Paso 1:** `test_todo_rf_tiene_fila_en_el_plan_de_pruebas`, `_sin_sobrantes`,
  `test_la_trazabilidad_lee_los_dos_guiones` (texto a mano con `RF‑7` y `RF-8`).
- [ ] **Pasos 2 a 5.**

**Verificación:** `uv run pytest -W error -q tests/unit/test_arquitectura.py -k plan_de_pruebas`.
**Choques:** ninguno. **Aval:** no.

**Cierre de la ola 1:** suite completa y `ruff`; la ola no cambia ninguna salida del programa.

---

## Ola 2: unificar funciones (5 tareas)

### Tarea 2.1: un solo `decimal_desde_texto`

**Archivos:**
- Modificar `api/esquemas.py:19-33` (se borra la definición; se importa).
- Se queda: `aplicacion/composicion.py:92-104`.
- Prueba: `tests/unit/test_arquitectura.py` y `tests/unit/test_api_esquemas_decimal.py` (nueva).

**Interfaces:**
- Consume: `aplicacion.composicion.decimal_desde_texto(texto: str, campo: str) -> Decimal`, que
  lanza `ComposicionInvalida` (subclase de `ValueError`, `aplicacion/composicion.py:83`), así que
  `api.main.manejar_value_error` (`api/main.py:264`) sigue devolviendo 422.

- [ ] **Paso 1:** pruebas en rojo:
  - `test_una_sola_lectura_de_decimal_de_maquina`: en todo el repositorio fuera de `core/` y
    `tests/` hay exactamente un `def decimal_desde_texto`.
  - `test_la_api_usa_la_lectura_de_aplicacion`:
    `api.esquemas.decimal_desde_texto is aplicacion.composicion.decimal_desde_texto`.
  - `test_un_monto_ilegible_en_la_api_es_422_y_nombra_el_campo`: `POST /presupuestos` con
    `cantidad = "12,50"` responde 422 y el `detail` contiene `"cantidad de "` y
    `"no es un numero decimal valido"`.
- [ ] **Paso 2:** ver el rojo (`-k "decimal_de_maquina or lectura_de_aplicacion or monto_ilegible"`).
- [ ] **Paso 3:** borrar la función de `api/esquemas.py` y poner
  `from aplicacion.composicion import decimal_desde_texto` (los dos importadores,
  `api/rutas/presupuestos.py:56` y `api/rutas/rendimientos.py:31`, no cambian). El mensaje de la
  API pasa de «monto decimal valido» a «numero decimal valido»: ninguna prueba de `tests/` afirma el
  texto viejo (comprobado con grep).
- [ ] **Paso 4:** verde; suite de la API: `uv run pytest -W error -q tests/integration -k api`.
- [ ] **Paso 5:** commit.

**Rama:** `feature/desenredo-cifras` (tareas 2.1 a 2.3).
**Choques:** `depurar-api` y `depurar-desperdicio` tocan `api/rutas/presupuestos.py` (líneas
31-430), no la importación de la línea 56. Bajo.
**Aval:** no.

### Tarea 2.2: `api/presentacion.py`, el único sitio que presenta cifras

**Archivos:** Crear `api/presentacion.py`; prueba nueva `tests/unit/test_api_presentacion.py`.

**Interfaces (las consumen 2.3, 2.4 y la guardia 1.4):**
- `monto(valor: Decimal) -> str`: `formatear_decimal(valor, DECIMALES_PRESENTACION)`
  (`ROUND_HALF_UP`), el cero con signo sale sin signo y, si cuantizar lanza `InvalidOperation`,
  devuelve `exacto_sin_ceros(valor)`.
- `monto_o_nada(valor: Decimal | None) -> str | None`.
- `porcentaje(parte: Decimal, total: Decimal, decimales: int = DECIMALES_PRESENTACION) -> str | None`:
  `None` si `total == 0` o si no cabe; `ROUND_HALF_UP`; sin signo en cero.
- `exacto(valor: Decimal) -> str` y `exacto_o_nada(valor: Decimal | None) -> str | None`:
  `format(valor, "f")`, sin redondear ni recortar (es lo que hoy hacen diez `_texto`).
- `exacto_sin_ceros(valor: Decimal) -> str`: `formatear_decimal(valor)` y `"-0"` → `"0"`
  (lo que hoy hacen `libros._exacto` y `esquemas_hoja._decimal_fijo`).
- `redondeado(valor: Decimal, lugares: int) -> str`: `formatear_decimal(valor, lugares)`, para las
  cifras que no son montos y llevan otro número de decimales (el FCAS de `api/rutas/fcas.py:123`).
- `cifra_presentada(valor: Decimal, decimales: int = DECIMALES_PRESENTACION) -> str`:
  `texto_de_cifra` del valor cuantizado con `ROUND_HALF_UP` (coma; para `api/rutas/indices.py:350`).

- [ ] **Paso 1:** pruebas en rojo (el módulo no existe):
  - `monto(Decimal("0.125")) == "0.13"`; `monto(Decimal("-0.125")) == "-0.13"`;
    `monto(Decimal("2.675")) == "2.68"`; `monto(Decimal("-0.001")) == "0.00"`;
    `monto(Decimal("1E+3")) == "1000.00"`;
    `monto(Decimal("1" + "0" * 30)) == "1" + "0" * 30` (no cabe: exacto, sin excepción).
  - `monto_o_nada(None) is None`; `exacto(Decimal("12.50")) == "12.50"`;
    `exacto_sin_ceros(Decimal("4358.2082500")) == "4358.20825"`;
    `exacto_sin_ceros(Decimal("-0.000")) == "0"`.
  - `porcentaje(Decimal("1.25"), Decimal("1000"), 2) == "0.13"`;
    `porcentaje(Decimal("1"), Decimal("0")) is None`;
    `porcentaje(Decimal("-0.00001"), Decimal("1000")) == "0.00"`.
  - `cifra_presentada(Decimal("1234.565")) == "1.234,57"`; `redondeado(Decimal("1.2345"), 3) == "1.235"`.
  - `test_presentacion_no_redondea_al_par`: el módulo no contiene `ROUND_HALF_EVEN`.
- [ ] **Paso 2:** `uv run pytest -W error -q tests/unit/test_api_presentacion.py` → rojo por
  `ModuleNotFoundError`.
- [ ] **Paso 3:** escribir el módulo con esas firmas. Importa de `core` solo
  `core.verification.texto.formatear_decimal` y `core.verification.informe.DECIMALES_PRESENTACION`,
  y de `aplicacion.cifras` solo `texto_de_cifra`.
- [ ] **Paso 4:** verde; `uv run pytest -W error -q tests/unit/test_arquitectura.py`.
- [ ] **Paso 5:** commit.

**Choques:** ninguno (archivo nuevo). **Aval:** no; no toca `core/`.

### Tarea 2.3: los libros presentan al alza

**Archivos:**
- Modificar `api/rutas/libros.py:577-617` (`_texto`, `_montos`, `_exacto`, `_centesimas`,
  `_porcentaje`) y `:883-886` (`_dos_decimales`); borrar `ROUND_HALF_EVEN` de la línea 85.
- Pruebas: `tests/unit/test_api_libros_replica.py:395-410` y `:420-440`;
  `tests/integration/test_api_libros.py:459` (comentario).

**Interfaces:** consume `monto`, `porcentaje`, `exacto`, `exacto_sin_ceros` (2.2).
`indicadores_de` (línea 620) conserva su firma; `_porcentaje` hoy devuelve `Decimal | None` y su
consumidor (línea 635) lo formatea: el cambio deja que `porcentaje` devuelva el texto y borra el
paso intermedio.

- [ ] **Paso 1:** rojo cambiando las expectativas (decisión del 2026-11-17):
  `test_delta_pct_en_centesimas_con_redondeo_al_par` se renombra
  `test_delta_pct_en_centesimas_con_redondeo_al_alza`, con
  `("1001.25", "1.25", "0.13")`, `("1001.35", "1.35", "0.14")`, `("998.75", "-1.25", "-0.13")` y
  las dos filas de cero sin cambio. En la tabla de RS2-12 la fila
  `("4203.93325", "4358.20825", …)` queda igual (154,275 → 154,28 en los dos modos) y se agrega
  `("1000.125", "1000", ("1000.13", "1000.00", "0.13", "0.01"))`. El comentario «al par» pasa a
  «al alza (decisión de Eugenio, 2026-11-17)».
- [ ] **Paso 2:** `uv run pytest -W error -q tests/unit/test_api_libros_replica.py` → rojo en
  esas filas.
- [ ] **Paso 3:** reemplazar las cinco ayudas por las de `api/presentacion.py`; quitar la fila
  `api/rutas/libros.py` de `PRESENTACION_SUELTA_EN_API`.
- [ ] **Paso 4:** verde: `uv run pytest -W error -q tests/unit/test_api_libros_replica.py
  tests/integration/test_api_libros.py tests/unit/test_arquitectura.py`.
- [ ] **Paso 5:** commit; anotar en `docs/ESTADO.md` §4 que RS2-12 cambió de modo y por qué.

**Choques:** ninguna rama `depurar-*` toca `api/rutas/libros.py`. **Aval:** no (es presentación;
el cálculo no cambia).

### Tarea 2.4: el resto de la API usa `api/presentacion.py`

**Archivos (cada uno sale de `PRESENTACION_SUELTA_EN_API` en el mismo commit):**
`api/rutas/fcas.py:123`, `hoja_libro.py:94`, `obras.py:157-168` y `:195`,
`aprobaciones.py:272`, `auditorias_libro.py:78`, `mercado.py:294-302`, `produccion.py:260`,
`revision.py:228`, `riesgo.py:259` y `:363`, `tablero.py:135`, `entregas.py:168`,
`indices.py:350`, `api/esquemas_hoja.py:766`, `api/esquemas_vial.py:228`,
`api/esquemas_informe.py:54`.

- [ ] **Paso 1:** la prueba en rojo es la propia guardia: borrar a mano las filas de esos archivos
  de `PRESENTACION_SUELTA_EN_API` y ver el rojo de `test_la_api_presenta_cifras_en_un_solo_sitio`.
  Además, una prueba de conducta en el único cambio de modo: `api/rutas/indices.py:351` cuantiza
  sin `rounding` (al par del contexto). `test_indices_presenta_al_alza`: el texto de un índice
  `Decimal("100.125")` con dos decimales es `"100,13"` (hoy `"100,12"`), en el archivo de pruebas
  de índices que ya exista (`grep -l "indices" tests/unit/test_api_*`).
- [ ] **Paso 2:** ver el rojo.
- [ ] **Paso 3:** reemplazo uno a uno, sin cambiar salidas salvo `indices`: `format(v, "f")` →
  `exacto`; `quantize(…, ROUND_HALF_UP)` a dos → `monto`; `_porcentaje` de obras (una décima) →
  `porcentaje(parte, bac, 1)`; `fcas._redondeado(v, n)` → `redondeado(v, n)`;
  `_decimal_fijo` → `exacto_sin_ceros`; `indices._con` → `cifra_presentada`.
- [ ] **Paso 4:** `uv run pytest -W error -q` (suite completa: los contratos de texto de la API
  están fijados por muchas pruebas de integración y son el oráculo de que nada más cambió).
- [ ] **Paso 5:** commit, uno por archivo o por grupo pequeño.

**Rama:** `feature/desenredo-presentacion`.
**Choques:** `depurar-api` toca `obras.py` (líneas 33 y 105-116), `entregas.py` (47 y 105-116) y
`revision.py` (pocas líneas, `RutaSinCache`): no son las líneas de esta tarea, pero el archivo es
el mismo; tras la unión no hay conflicto.
**Aval:** no.

### Tarea 2.5: una sola política de «rendimiento vigente» y una sola búsqueda de obra por nombre

Dos unificaciones chicas, juntas porque las dos vacían filas de la tarea 1.2 en
`api/rutas/presupuestos.py`.

**Archivos:**
- `aplicacion/elaboracion.py:284-326` (se queda la política; nace el predicado).
- `api/rutas/presupuestos.py:1002-1028` (`_rendimientos_por_declarar` se borra), `:184` (su uso),
  `:909-917` (`_proyecto`).
- `aplicacion/hoja_vial.py:232-234`.
- `aplicacion/proyectos.py:187-206` (nace `proyecto_por_nombre`; `resolver_proyecto` lo usa).
- Búsquedas por nombre que pasan a usarlo: `api/rutas/entregas.py:122`, `api/rutas/reajuste.py:147`,
  `aplicacion/entrega.py:202`, `aplicacion/hoja.py:2273`, `aplicacion/listas_para_armar.py:361`.
- `docs/arquitectura.md` §6.1, fila «rendimiento estimado vigente».
- Pruebas: `tests/unit/test_plan_rendimientos.py` o la de elaboración que exista; nueva
  `tests/unit/test_aplicacion_proyectos_por_nombre.py`.

**Interfaces:**
- `aplicacion.elaboracion.es_rendimiento_vigente(tipo: TipoRendimiento | str, fecha_rendimiento: date, fecha: date) -> bool`
  (acepta el `str` de la fila ORM que usa `hoja_vial`, vía `TipoRendimiento(tipo)`).
- `aplicacion.proyectos.proyecto_por_nombre(sesion: Session, nombre: str) -> models.Proyecto | None`
  (nombre exacto; nunca interpreta dígitos como `id`).
- Se consume sin cambio `aplicacion.elaboracion.rendimientos_por_declarar(sesion, items, fecha)
  -> tuple[RendimientoPorDeclarar, ...]` y `api.rutas.rendimientos.propuesta_respuesta`.

- [ ] **Paso 1:** pruebas en rojo:
  - `test_es_rendimiento_vigente`: ESTIMADO del mismo día → `True`; ESTIMADO del día siguiente →
    `False`; tipo distinto de ESTIMADO del mismo día → `False`; con `"ESTIMADO"` como `str` igual.
  - `test_la_politica_de_vigencia_vive_en_un_solo_sitio` (en `test_arquitectura.py`): fuera de
    `core/`, la comparación `TipoRendimiento.ESTIMADO` junto a `fecha <=` aparece solo en
    `aplicacion/elaboracion.py` (hoy también en `api/rutas/presupuestos.py:1024` y
    `aplicacion/hoja_vial.py:233`).
  - `test_proyecto_por_nombre_no_lee_digitos_como_codigo`: con las obras «Torre B» (id 1) y «1»
    (id 2), `proyecto_por_nombre(s, "1").id == 2` y `resolver_proyecto(s, "1").id == 1`;
    `proyecto_por_nombre(s, "torre b") is None` (exacto).
  - `test_una_sola_busqueda_de_obra_por_nombre` (en `test_arquitectura.py`): el patrón
    `select(models.Proyecto).where(models.Proyecto.nombre ==` aparece solo en
    `aplicacion/proyectos.py`.
  - El 409 de `POST /presupuestos` (flujo 3b) ya lo fijan `tests/integration/test_api_ola2_elaborar.py`
    y `tests/integration/test_api_plan_y_rendimiento.py`: son el oráculo de conducta.
- [ ] **Paso 2:** ver el rojo.
- [ ] **Paso 3:** cambio mínimo: `rendimientos_por_declarar` y `rendimiento_por_declarar` usan el
  predicado; `hoja_vial._por_que` también; la ruta llama a
  `aplicacion_elaboracion.rendimientos_por_declarar(sesion, items, peticion.fecha)` y convierte cada
  entrada con `propuesta_respuesta` (la ruta ya filtra los códigos que existen, línea 178, y la
  función de aplicación vuelve a filtrar: mismo resultado); los cinco sitios de búsqueda por nombre
  llaman a `proyecto_por_nombre`. La fila de §6.1 pasa de «tres sitios» a «uno fuera del núcleo».
- [ ] **Paso 4:** `uv run pytest -W error -q` completa.
- [ ] **Paso 5:** commit (dos: vigencia; búsqueda por nombre).

**Rama:** `feature/desenredo-politicas`.
**Choques:** `depurar-api`/`depurar-desperdicio` tocan `api/rutas/presupuestos.py` y
`entregas.py` (otras líneas); `depurar-revision` toca `aplicacion/entrega.py` (líneas 27 y
118-127, no la 202). Bajo, tras la unión.
**Aval:** no para esto. **Bloqueado hasta aval:** el cierre definitivo, un
`Catalogo.rendimiento_vigente(codigo, fecha)` público en `core.catalog` (§6.1), porque toca `core/`.

**Cierre de la ola 2:** suite completa, `ruff`, `meta_datos.py`, y en el navegador la franja de
indicadores de un libro y la pantalla de índices (las dos salidas que cambian de modo).

---

## Ola 3: adelgazar rutas (4 tareas)

Cada tarea saca consultas de `api/rutas` y borra su fila de `SELECT_EN_RUTAS` y, si toca,
de `MODELOS_EN_RUTAS`. La prueba en rojo de cada una es esa guardia con la fila ya borrada, más
una prueba unitaria de la función nueva contra una base en memoria construida a mano.

### Tarea 3.1: listados y cargas del caso

**Archivos:** `api/rutas/presupuestos.py:285` (`listar_presupuestos`), `:379` (lista por nombre),
`:1084-1095` (`_cargar`); `api/rutas/listas.py:39`; `api/rutas/rendimientos.py:72`.
Destino: `aplicacion/elaboracion.py` (presupuestos) y `aplicacion/listas_para_armar.py` (listas).

**Interfaces:**
- `aplicacion.elaboracion.presupuestos_guardados(sesion: Session) -> list[models.Presupuesto]`
  (por código).
- `aplicacion.elaboracion.presupuesto_por_codigo(sesion: Session, codigo: str, proyecto: str | None) -> models.Presupuesto`
  (`LookupError` si no hay; el 409 de duplicados sigue en la ruta).
- `aplicacion.listas_para_armar.listas_de_precios(sesion: Session) -> list[models.ListaPrecios]`
  (por `fecha_vigencia`, `id`) y `lista_por_nombre(sesion: Session, nombre: str) -> models.ListaPrecios | None`.
- `aplicacion.elaboracion.ejecuciones(sesion: Session) -> list[models.Ejecucion]`
  (por `fecha_inicio`, `id`).

- [ ] **Paso 1:** pruebas unitarias del orden (tres filas construidas fuera de orden salen
  ordenadas) y de `LookupError`; borrar las filas de la guardia; ver el rojo.
- [ ] **Paso 2-4:** mover, verde con la suite completa.
- [ ] **Paso 5:** commit.

**Rama:** `feature/desenredo-rutas` (tareas 3.1 a 3.4).
**Choques:** `depurar-api`/`depurar-desperdicio` en `presupuestos.py` (otras líneas). **Aval:** no.

### Tarea 3.2: administración sin SQL en la ruta

**Archivos:** `api/rutas/admin_claves_api.py:75` → `seguridad/claves_api.py`;
`api/rutas/admin_empresas_registradas.py:92` → `seguridad/empresas.py`; `api/rutas/cuentas.py:232`
→ `seguridad/cuentas.py`.

**Interfaces:** `seguridad.claves_api.claves(bd: Session) -> list[ClaveApi]` (por `id`);
`seguridad.empresas.registradas(bd: Session) -> list[EmpresaRegistrada]` (por `id`);
`seguridad.cuentas.usuarios(bd: Session) -> list[Usuario]` (por `login`).

- [ ] Pasos como en 3.1 (prueba del orden con tres filas, rojo de la guardia, mover, verde, commit).

**Choques:** `depurar-api` cambia 6 líneas en `admin_claves_api.py` y en
`admin_empresas_registradas.py` (rechazos con `no-store`), no las consultas. Bajo.
**Aval:** no. Ojo con la ola 5: `seguridad/empresas.py` ya importa `operacion` dentro de una
función; esta tarea no añade imports a `operacion`.

### Tarea 3.3: producción sin SQL en la ruta

**Archivos:** `api/rutas/produccion.py:238` y `:316` → `produccion/inventario.py`.

**Interfaces:** `produccion.inventario.material_por_codigo(sesion: Session, codigo: str) -> Material | None`
(recorta blancos, como hoy `codigo.strip()`); `produccion.inventario.materiales(sesion: Session) -> list[Material]`
(por `codigo`).

- [ ] Pasos como en 3.1; la prueba de `material_por_codigo(s, "  AR-01 ")` encuentra `AR-01`.

**Choques:** ninguno. **Aval:** no.

### Tarea 3.4: rutas sin `core.models`

**Archivos:** los que queden en `MODELOS_EN_RUTAS` tras 2.5, 3.1 y 3.2 (medido hoy:
`entregas, listas, presupuestos, reajuste, rendimientos, revision`). Las anotaciones de tipo
`models.X` en firmas de ayudas privadas pasan a recibir lo que devuelve la función de `aplicacion`
(o a `if TYPE_CHECKING:`, que la guardia 1.2 debe ignorar como la 1.1).

- [ ] **Paso 1:** vaciar `MODELOS_EN_RUTAS` en la prueba; ver el rojo con la lista de archivos.
- [ ] **Paso 2-4:** archivo por archivo; suite completa.
- [ ] **Paso 5:** commit por archivo.

**Choques:** `depurar-api` en `entregas.py`, `presupuestos.py`, `revision.py`. Bajo tras la unión.
**Aval:** no. `NUCLEO_PROFUNDO_EN_RUTAS` **no** se vacía en este plan: muchas de esas importaciones
(`core.budget.instantanea`, `core.catalog.precios`…) son la API pública que §4 reconoce; decidir
cuáles son «internas» es enmienda de §4, **con aval del tutor**. La lista queda congelada.

**Cierre de la ola 3:** suite completa; `SELECT_EN_RUTAS` y `MODELOS_EN_RUTAS` vacías (la guardia
pasa a ser una prohibición pura y se borran los diccionarios).

---

## Ola 4: partir módulos (4 tareas)

Regla para las cuatro: **mover sin cambiar conducta**. El módulo original queda como fachada que
reexporta los nombres públicos (102 archivos importan `aplicacion.hoja`), con `__all__`. La prueba
en rojo es `test_un_modulo_grande_no_crece` con el valor congelado bajado al objetivo, más
`test_<modulo>_reexporta_lo_mismo`: el conjunto de nombres públicos de la fachada antes y después
es igual (se guarda la lista medida en la prueba). Cada movimiento se verifica con la suite
completa y con la guardia de ciclos (1.3): partir no puede crear un componente nuevo.

### Tarea 4.1: `api/rutas/presupuestos.py` (1119 líneas)

**Archivos:** crear `api/rutas/presupuestos_escenarios.py` con las rutas de escenarios y
comparativos (`:560-712`) y `api/rutas/presupuestos_ayudas.py` con la sección «Ayudantes»
(`:715` en adelante, ya adelgazada por 2.5 y 3.1); registrar el router nuevo en `api/main.py`.
**Objetivo:** cada archivo < 600 líneas; `docs/api.json` idéntico
(`uv run python scripts/exportar_openapi.py` y `git diff --exit-code docs/api.json`).
**Rama:** `feature/desenredo-modulos`. **Choques:** `depurar-api` toca `api/main.py` (+20) y
`presupuestos.py`: después de la unión, nada. **Aval:** no.

### Tarea 4.2: `api/rutas/hoja.py` (1348 líneas)

**Archivos:** crear `api/rutas/hoja_cadena.py` con la sección «S2 a S6 (3d-2): versiones nuevas
desde una guardada y la cadena» (`:1234` al final) y, si sigue sobre el tope, las rutas de
guardado; registrar el router en `api/main.py`.
**Objetivo:** < 1000 líneas cada uno; `docs/api.json` idéntico. **Choques:** ninguno directo.
**Aval:** no.

### Tarea 4.3: `aplicacion/control.py` (1571 líneas en `s2m4`)

**Archivos:** partir por sus cinco secciones ya marcadas:
`aplicacion/control_linea_base.py` («Línea base, valuaciones, anulación y costos», `:241-616`),
`aplicacion/control_calculo.py` («Cálculo y opciones», `:618-758`),
`aplicacion/control_tablas.py` («Tablas para la pantalla y para el Excel», `:760-1356`),
`aplicacion/control_parametros.py` («Parámetros de control y la curva PV/EV/AC», `:1358-1483`);
las «Consultas cortas» (`:1485`) y los tipos de cabecera se quedan en `control.py`, que reexporta.
**Paso extra:** `grep -rn "aplicacion.control\." tests | grep monkeypatch` y retargetear cada
parche al módulo donde vive la función.
**Choques:** **alto con `depurar-control`** (líneas 319, 654-735 y 846-868): solo después de la
unión. `control` está en el ciclo de once módulos: medir con 1.3 tras cada movimiento.
**Aval:** no, mientras no se mueva nada entre paquetes.

### Tarea 4.4: `aplicacion/hoja.py` (3195 líneas)

En cuatro entregas, cada una con su commit y su suite verde; las secciones ya están marcadas:

- **4.4a** «Excel de la hoja» (`:2789-2925`) a `aplicacion/hoja_exportar.py` (165 líneas hoy) e
  «importar un plano» (`:2926` al final) a `aplicacion/hoja_plano.py` (613).
- **4.4b** «cambios entre dos borradores» (`:1367-1648`) a `aplicacion/hoja_cambios.py` y «Estado
  por fila» (`:1649-1774`) a `aplicacion/hoja_estado.py`.
- **4.4c** «abrir una version guardada» (`:1775-2110`) y «guardar, restaurar y versiones»
  (`:2111-2596`) a `aplicacion/hoja_versiones.py` (236) y `aplicacion/hoja_guardado.py` (307),
  sin pasar ninguno de 1000.
- **4.4d** «cifras tecleadas en la hoja» (`:385-725`) a `aplicacion/hoja_cifras.py` y
  «derivacion y elaboracion» + «items, claves y cantidades» (`:726-976`) a
  `aplicacion/hoja_derivacion.py`.

**Objetivo:** `aplicacion/hoja.py` < 1000 líneas (fachada, tipos `Borrador`, `VersionAbierta` y lo
que quede de edición del APU, tablas, parámetros y plan).
**Paso extra en cada entrega:** retargetear los `monkeypatch` sobre `aplicacion.hoja.*` (10 hoy).
**Riesgo:** `aplicacion/hoja_borradores.py:49` importa `Borrador` y `VersionAbierta` de `hoja` en
el nivel del módulo; si un módulo nuevo importa `hoja_borradores`, nace un ciclo. La guardia 1.3
lo detiene; la salida es dejar esos dos tipos en `hoja.py` o en un `aplicacion/hoja_tipos.py` hoja
(sin dependencias de `aplicacion`).
**Choques:** `depurar-hoja-aplicacion` toca `hoja_borradores.py`; ninguna rama toca `hoja.py`.
**Aval:** no.

**Cierre de la ola 4:** suite completa; `MODULOS_GRANDES` sin `api/rutas/presupuestos.py`,
`api/rutas/hoja.py`, `aplicacion/control.py` ni `aplicacion/hoja.py`. Quedan, fuera de este plan,
`adapters/hoja_empresa/{reglas, pdf, escritor/calculos}.py`, `aplicacion/composicion.py`,
`api/esquemas_hoja.py`, `api/rutas/libros.py` y `aplicacion/hoja_vista.py`.

---

## Ola 5: salir de los ciclos (4 tareas; BLOQUEADA HASTA AVAL DEL TUTOR, decisión D2)

Se deja escrita para que el aval sea sobre algo concreto. Cada tarea borra una fila de
`CICLOS_CONOCIDOS` o achica el componente; esa es su prueba en rojo, más
`test_importar_<modulo>_en_frio` (un subproceso `python -c "import <modulo>"` sin nada cargado
antes, para ver que el orden de import no dependía del ciclo).

### Tarea 5.1: `entrega` ↔ `aprobaciones` y `aprobaciones` ↔ `mesa`

- `anexos_de_cadena` (lo importa `aplicacion/aprobaciones.py:57` desde `entrega`) pasa a
  `aplicacion/anexos.py`, que no importa ni `entrega` ni `aprobaciones`; se borra el import local
  de `aplicacion/entrega.py:86`.
- `Pendiente` y `Siguiente` (importados en `aplicacion/aprobaciones.py:580` desde `mesa`) pasan a
  `aplicacion/tablas_mesa.py` como tipos de datos sin lógica; `mesa` los reexporta; se borra el
  import local.
- Medir el componente de once con 1.3; lo que quede (`control`, `hoja`, `mercado`, `procura`,
  `vial`, `frentes`, `hoja_partidas`, `precios_declarados`) se lista en el acta del aval para una
  segunda vuelta.

**Choques:** `depurar-revision` (`entrega.py`) y `depurar-control` (`mesa.py`): solo tras la unión.

### Tarea 5.2: `seguridad` ↔ `operacion`

- `operacion.red.es_cliente_local` (`operacion/red.py:108`, importado dentro de
  `seguridad/empresas.py:57`) pasa a `seguridad/red.py`, que ya tiene `es_bucle_local` y
  `es_local`; `operacion/red.py` lo reexporta. Hacer lo mismo con el otro import local
  `seguridad → operacion` que mide 1.1.
- Objetivo: `seguridad` deja de depender de `operacion` en la matriz (1.1).
- `seguridad.cuentas` ↔ `seguridad.sesiones`: mover a `seguridad/modelo.py` o a un módulo de tipos
  lo que cada uno toma del otro.

### Tarea 5.3: `aplicacion → operacion → migraciones → aplicacion`

- `migraciones/metadatos.py:13-26` importa catorce `aplicacion.tablas_*`. Salida: un paquete hoja
  `tablas/` (solo `sqlalchemy`) con esas declaraciones; `aplicacion.tablas_*` lo reexporta mientras
  haya importadores; `migraciones` importa `tablas`. Añade un paquete de primer nivel: enmienda de
  §4 y fila nueva en `PAQUETES_FUERA_DEL_NUCLEO` y en la matriz.

### Tarea 5.4: el resto del ciclo de paquetes

- `asistente → aplicacion`, `fusion → aplicacion`, `paquete → seguridad → operacion`: medir de
  nuevo tras 5.2 y 5.3 y proponer en el acta, arista por arista, mover o declarar la dependencia.

**Aval necesario para toda la ola:** cambia la vista de desarrollo (`docs/arquitectura.md` §4) y,
en 5.3, la lista de paquetes. Ningún paso toca `core/`.

---

## Anexo: hallazgos del arbitraje de la depuración unida (2026-11-17)

El [arbitraje xhigh](../bitacora/arbitrajes/depuracion-unida-claude-xhigh.md) de `feature/depuracion-unida` mandó
aquí los hallazgos de la segunda opinión que tocan código anterior a la unión (decisión simulada DS-4). Cada uno
entra en la ola que dice la tabla, con TDD como las demás tareas; las líneas son las de `feature/depuracion-unida`.

| Tarea | Hallazgo | Qué se hace | Ola | Prueba en rojo |
|---|---|---|---|---|
| A.1 | H1, H7 | `adapters/hoja_empresa/pdf.py:262-270` (`_fmt`) y `aplicacion/libro_a_la_hoja.py:221-223` (`_pct`) presentan con `texto_de_cifra` (al alza, coma y punto de miles; sin «-0»). El adaptador no importa `api/`: usa la ayuda de `aplicacion`, o la de `core.verification.texto` | 2 (junto a 2.3) | `_fmt(Decimal("1.00005")) == "1,0001"`, `_fmt(Decimal("-0")) == "0"`, `_pct(Decimal("12.5")) == "1.250"` |
| A.2 | H11 | Los 18 routers con `RutaSinCache` dejan de poner `Cache-Control` a mano (constantes `SIN_CACHE` locales y `headers=`) | 3 | Guardia en `tests/unit/test_arquitectura.py`: un módulo con `route_class` derivada de `RutaSinCache` no contiene el literal `"Cache-Control"`; las pruebas de `no-store` existentes son el oráculo de conducta |
| A.3 | H8 y DS-2 | `declarar_rendimiento_propuesto` (`api/rutas/presupuestos.py:601`), `rendimientos.py:97` y las escrituras con BEGIN diferido de `control.py` pasan a `SesionDeEscrituraDep`; se decide si el 503 genérico de `api/main.py` sigue siendo el último recurso | 3 | Añadirlas a `QUE_ESCRIBEN` de `tests/unit/test_api_escritura_inmediata.py` |
| A.4 | H9, H10 | `_carpetas_visibles` (`api/rutas/obras.py:304-335`) a `aplicacion`; un solo texto para `EventosIlegibles` junto a la excepción, citado por la API (409) y por la CLI (`operacion/ordenes_100.py:155-164`) | 3 | El `detalle` del 409 y la salida de la CLI contienen la misma constante |
| A.5 | H13 | En `useEdicionDeSeccion.ts`, el `reenviar` que nace en el `finally` de una acción con la pestaña ya desmontada se registra con `registrarEnvio` | 4 (front de la Hoja) | Acción pendiente, se escribe, se desmonta la pestaña, se resuelve la acción: `esperarEnvios(borrador)` espera también el PUT del reenvío |
| A.6 | DS-3, opción B | Mejora: el desglose del desperdicio cuenta como cambio y guardar escribe sus trazas sin crear versión (hoy E6 rechaza la edición que solo cambia el desglose). Toca `hoja_vista`, `hoja_guardado`, el contrato de guardar y el front | Después de la ola 4; pide el visto bueno de Eugenio | Editar solo el desglose deja `cambios > 0` y guardar responde 200 con las trazas nuevas |

Rechazados por el arbitraje, sin tarea: H12 (descartar dentro de la pausa de 400 ms; inocuo) y H14 (el doble POST
no ocurre).


## Resumen

| Ola | Tareas | Necesita aval |
|---|---|---|
| 1. Guardias congeladas | 7 | no (la nota de §4 en 1.1, sí) |
| 2. Unificar funciones | 5 | no (`Catalogo.rendimiento_vigente`, sí: queda fuera) |
| 3. Adelgazar rutas | 4 | no (vaciar `NUCLEO_PROFUNDO_EN_RUTAS`, sí: queda congelada) |
| 4. Partir módulos | 4 | no |
| 5. Ciclos | 4 | **sí, toda la ola** (D2) |

Al cerrar cada ola: `uv run pytest -W error -q`, `uv run ruff check .`,
`uv run python scripts/meta_datos.py`, `uv run python scripts/guardia_nucleo.py`, y una fila en
`docs/ESTADO.md`.
