# Especialidad vial y de agregados (plan de implementación)

> **Para agentes:** SUB-SKILL REQUERIDA: superpowers:subagent-driven-development (recomendada) o
> superpowers:executing-plans, tarea por tarea. Los pasos usan casillas (`- [ ]`). Cada tarea termina con su árbitro
> (`MANUAL_ARBITRO.md`) antes de abrir la siguiente. **Agentes de uno en uno**; menores agrupados al cierre de cada
> fase; navegador solo en la Tarea 22.

**Objetivo:** que un presupuesto vial (tramos → cantidades → APU con el costo propio del agregado y de la mezcla →
auditoría vial y conciliación → proyección del riesgo con su comprobación hacia atrás → informe de mejora de la
estimación) corra de punta a punta en Sílice, con cada cifra trazable a su origen y sin un solo cambio en `core/`.

**Arquitectura:** cuatro fases. **A** da costo al gestor de producción (`produccion/`, dominio puro) y lo publica al
catálogo como precio propio desde `aplicacion/costo_propio.py`; va primero porque los costos reales solo existen desde
que la empresa empiece a registrarlos. **B** añade `adapters/vial/` como subespecialidad de civil (`Dominio.CIVIL`,
`especificaciones["especialidad"] = "vial"`), con sus reglas y la conciliación. **C** añade `aplicacion/riesgo/`:
proyección por remuestreo de meses históricos completos sobre `core/budget/escenarios.generar_escenario`, comprobación
hacia atrás e informe de mejora. **D** cubre los pedidos transversales de Eugenio: FCAS por componentes, IVA, módulos
activables, búsqueda con autocompletado y reportes.

**Stack:** Python 3 + FastAPI + SQLAlchemy + Alembic + pytest; React 19 + TypeScript + Carbon 11 (g10) + Vitest;
openpyxl para reportes. Sin dependencias nuevas.

**Especificación:** [docs/especificaciones/2026-10-30-vial-agregados-design.md](../especificaciones/2026-10-30-vial-agregados-design.md)
(§2 objetivos 1–9, §2.1 requisitos transversales, §5 y §5.1 decisiones).

**Base:** rama `inc/vial-agregados` creada en `c1f436b2` (árbol `.worktrees/s2madm`).

**Estado de los datos (2026-10-30):** los presupuestos reales disponibles son de edificación y aún no hay
presupuestos viales ni de obras con piedra picada (llegarán; especificación §7). Nada de este plan depende de ellos:
toda prueba usa casos ficticios. Cuando lleguen, se usan **solo en local** para la medición, sin tocar el plan.

**Aprobación:** diseño y plan aprobados por Eugenio el 2026-10-30, con la orden de desarrollarlo.

## Restricciones globales

Las de `PLAN_REDISENO_MARCO.md` siguen vigentes (es-VE con coma decimal y punto de miles, 1056/1366/1910 px y letra
1/1,25/1,5, accesibilidad AA, vocabulario del usuario, 250 líneas por componente, TDD con rojo visto, jscpd ≤ 1 %,
commit por tarea con `git diff --cached --stat`). Además:

- **`core/` intacto.** Al cerrar cada tarea: `git diff --stat c1f436b2 -- core/` vacío. Si una tarea cree necesitar el
  núcleo, se detiene y lo dice; no lo toca.
- **Ningún dato real en el repositorio**: ni nombre de empresa ni costos, tramos, precios o series reales. Casos y
  series del repositorio son ficticios y lo dicen en su encabezado. Lo real va en `data/` (ignorado), solo en local.
- **Ninguna constante sin fuente**: todo rango, alícuota, porcentaje o factor es una `Constante`
  (`adapters/espacio/especialidades/__init__.py`) con fuente, o lleva «supuesto declarado». Lo no cotejado con la norma
  dice «a cotejar» en su fuente.
- **Nada se sobrescribe**: correcciones de costos, recetas y cálculos son registros nuevos.
- **La IA nunca calcula** una cantidad, un costo ni un percentil.
- Moneda: cada monto guarda moneda original (`Bs` o `USD`), fecha y fuente; la conversión usa la tasa BCV **del día
  exacto** (`aplicacion/tasa_del_dia.py`); sin tasa ese día, error con la lista de lo que no se pudo convertir.
- Cantidades y dinero en `Decimal`; texto en la frontera de la API (un texto que no es decimal es 422).
- `uv run --active` SIEMPRE. Prohibido `--amend`, `reset`, `stash`, `rebase`, `push`, `git add -A`/`.`. Pie:
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (u Opus si la tarea va con Opus).
- La API no cambia ninguna ruta existente; solo añade las de este plan.
- Comandos: `uv run --active pytest <ruta> -q`; front: `npm --prefix frontend-desktop test -- <patrón>`;
  `npm --prefix frontend-desktop run lint`.

## Foco de revisión

1. **Costos de un período en dos monedas con un día sin tasa BCV** (fin de semana o feriado): el cálculo no se hace a
   medias; error que nombra cada costo sin tasa y su fecha. Prueba en Tarea 4.
2. **Período sin producción** (cero toneladas) o con producción pero sin costos: nunca división entre cero ni costo
   cero publicado; error claro «no hubo producción en AAAA-MM» / «no hay costos registrados en AAAA-MM». Prueba en
   Tarea 4.
3. **Tramos con progresivas invertidas, solapadas o con huecos, y archivo con coma decimal** («7,30»): la importación
   lee la coma, rechaza la fila invertida con su número de fila y la regla VR6 marca solapes y huecos. Pruebas en
   Tareas 7 y 9.
4. **Historia de índices corta o con meses faltantes** (menos meses que la ventana, o un mes sin dato en una serie): la
   proyección usa solo meses completos en todas las series, dice cuántos usó, y si son menos de 12 se niega con ese
   número en el mensaje. Prueba en Tarea 13.
5. **Módulo apagado con datos ya guardados** (vial apagado en una obra que tiene tramos): los datos no se borran, la
   pantalla no aparece, la API responde 404 «El módulo vial está apagado en esta instalación.» y al encenderlo todo
   vuelve igual. Prueba en Tarea 19.

## Decisiones por defecto (Eugenio puede cambiarlas; si no dice nada, se construye así)

- **D-V-1 Reparto de la cantera:** los costos con centro `cantera` se reparten entre los agregados **por tonelada
  producida** (mismo costo por tonelada para todos); los de centro `planta` van a la mezcla. Un reparto por pesos
  declarados queda disponible como parámetro.
- **D-V-2 Códigos de insumo propios:** `AGP-<código del material>` para agregado propio y `MZP-<código>` para mezcla
  propia, unidad `t`, tipo material.
- **D-V-3 Proyección:** 2.000 trayectorias, ventana de 36 meses, horizonte de 6 meses, gasto uniforme en el plazo,
  percentiles 50 y 80; la reserva es P80 − total base.
- **D-V-4 Módulo apagado:** 404 con detalle «El módulo <nombre> está apagado en esta instalación.»
- **D-V-5 IVA:** solo sobre el total del presupuesto y de cada valuación; las retenciones quedan fuera de este plan.

---

## Fase A: costo de producción

### Tarea 1: Costos del período en el gestor de producción

**Modelo:** Sonnet.

**Archivos:**
- Create: `produccion/costos.py`, `migraciones/instalacion/versions/ins_0006_prod_costo.py`
- Modify: `produccion/modelo.py` (tabla `prod_costo`), `seguridad/permisos.py` (acción), `api/rutas/produccion.py`
  (rutas), `api/main.py` solo si hace falta registrar algo nuevo
- Test: `tests/unit/test_produccion_costos.py`, `tests/integration/test_api_produccion_costos.py`

**Interfaces:**
- Produces:
  - `CONCEPTOS = ("gasoil", "equipo", "nomina", "mantenimiento", "explosivos", "energia", "otro")`,
    `CENTROS = ("cantera", "planta")`
  - `@dataclass(frozen=True) CostoDelPeriodo(periodo: str, centro: str, concepto: str, monto: Decimal, moneda: str,
    fecha: date, fuente: str, nota: str = "")` — `periodo` es `"AAAA-MM"`; valida todo en `__post_init__`
  - `@dataclass(frozen=True) CostoRegistrado(id: int, costo: CostoDelPeriodo, usuario: str, registrado: datetime,
    anulado: bool)`
  - `registrar_costo(sesion, costo: CostoDelPeriodo, *, usuario: str, ahora: datetime) -> int`
  - `anular_costo(sesion, costo_id: int, *, motivo: str, usuario: str, ahora: datetime) -> int` (registro nuevo con
    `anula_id`; el original no cambia)
  - `costos_del_periodo(sesion, periodo: str, *, incluir_anulados: bool = False) -> list[CostoRegistrado]`
  - `Accion.REGISTRAR_COSTOS_PRODUCCION = "registrar_costos_produccion"` → roles arma y administrador
  - `POST /v1/produccion/costos` (201, devuelve `id`), `GET /v1/produccion/costos?periodo=AAAA-MM`,
    `POST /v1/produccion/costos/{id}/anular`

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
def test_costo_exige_fuente_fecha_y_periodo_valido():
    with pytest.raises(ValueError, match="fuente"):
        CostoDelPeriodo("2026-11", "cantera", "gasoil", Decimal("10"), "USD", date(2026, 11, 3), fuente=" ")
    with pytest.raises(ValueError, match="periodo"):
        CostoDelPeriodo("2026-13", "cantera", "gasoil", Decimal("10"), "USD", date(2026, 11, 3), fuente="factura 12")

def test_rechaza_concepto_centro_moneda_y_monto_negativo(): ...  # "voladura", "oficina", "EUR", Decimal("-1")

def test_la_fecha_debe_caer_en_el_periodo():  # 2026-11 con fecha 2026-12-01 -> ValueError("fuera del periodo")

def test_anular_no_borra(sesion):
    i = registrar_costo(sesion, costo, usuario="ana", ahora=AHORA)
    anular_costo(sesion, i, motivo="duplicado", usuario="ana", ahora=AHORA)
    assert costos_del_periodo(sesion, "2026-11") == []
    assert len(costos_del_periodo(sesion, "2026-11", incluir_anulados=True)) == 2
```

API: `test_revisa_recibe_403`, `test_monto_no_decimal_422` (`"monto": "diez"`), `test_monto_con_coma_422`
(la API recibe punto; la coma es cosa del front), `test_alta_y_lista` (201 y luego aparece en el GET).

- [ ] **Step 2: Correr y ver el rojo** — `uv run --active pytest tests/unit/test_produccion_costos.py tests/integration/test_api_produccion_costos.py -q` → FAIL (módulo inexistente).
- [ ] **Step 3: Implementar** tabla, migración `ins_0006_prod_costo` (`down_revision = "ins_0005_mp_indice_aprobacion"`,
  montos como `String(40)` igual que `ins_0002`), servicio, acción y rutas, siguiendo `produccion/inventario.py` y las
  reglas de frontera de `api/rutas/produccion.py`.
- [ ] **Step 4: Verde** — mismo comando → PASS; `uv run --active pytest tests/unit/test_arquitectura*.py -q` → PASS.
- [ ] **Step 5: Commit** — `feat(produccion): costos del periodo por centro y concepto`.

### Tarea 2: Pantalla «Costos del período»

**Modelo:** Sonnet. Va antes que el resto de la fase para que la empresa pueda empezar a registrar costos.

**Archivos:**
- Create: `frontend-desktop/src/paginas/produccion/CostosDelPeriodo.tsx` (+ `.test.tsx`), funciones en el cliente de
  `frontend-desktop/src/api/` que ya usa `paginas/produccion/`
- Modify: la navegación de producción para mostrar «Costos del período» a quien tenga la acción

**Interfaces:**
- Consumes: rutas de la Tarea 1.
- Produces: `listarCostos(periodo: string)`, `registrarCosto(c: CostoNuevo)`, `anularCosto(id: number, motivo: string)`
  en el cliente.

- [ ] **Step 1: Pruebas que fallan:** `muestra los costos del período con total por centro y moneda` (dos costos USD de
  cantera 1.250,50 y 300 → «Cantera: 1.550,50 USD»); `escribe el monto con coma y lo envía con punto` (escribe
  «1.250,50», la petición lleva `"1250.50"`); `anular pide el motivo y no borra la fila hasta recargar`;
  `sin la acción no aparece el botón Registrar`.
- [ ] **Step 2: Rojo** — `npm --prefix frontend-desktop test -- CostosDelPeriodo` → FAIL.
- [ ] **Step 3: Implementar** con el formato es-VE que ya usan las tablas de producción.
- [ ] **Step 4: Verde** y `npm --prefix frontend-desktop run lint` → sin errores.
- [ ] **Step 5: Commit** — `feat(front): costos del periodo en produccion`.

### Tarea 3: Receta de la planta y consumos al producir mezcla

**Modelo:** Sonnet.

**Archivos:**
- Create: `produccion/receta.py`, `migraciones/instalacion/versions/ins_0007_prod_receta.py`
- Modify: `produccion/modelo.py` (`prod_receta`, `prod_receta_componente`), `produccion/inventario.py` (tipo de
  movimiento `consumo` y `producido_en_periodo`), `api/rutas/produccion.py`
- Test: `tests/unit/test_produccion_receta.py`, `tests/integration/test_api_produccion_receta.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Componente(codigo: str, cantidad_por_t: Decimal, unidad: str, tipo: str)` — `tipo` en
    `("propio", "comprado")`; `unidad` en `("t", "l")`
  - `@dataclass(frozen=True) Receta(id: int, producto: str, componentes: tuple[Componente, ...], fuente: str,
    vigente_desde: date)`
  - `registrar_receta(sesion, producto: str, componentes: Sequence[Componente], *, fuente: str, vigente_desde: date,
    usuario: str, ahora: datetime) -> int`
  - `receta_vigente(sesion, producto: str, fecha: date) -> Receta | None`
  - `producir_con_receta(sesion, producto: str, toneladas: Decimal, fecha: date, *, usuario: str, ahora: datetime)
    -> list[int]` — registra la producción del producto y un `consumo` por cada componente `propio`
  - `producido_en_periodo(sesion, periodo: str) -> dict[str, Decimal]` — toneladas por código de material (m³ × densidad;
    un material en m³ sin densidad es error que lo nombra)
  - `TOLERANCIA_MASA = Constante("receta_masa", "Suma de componentes en t por t de mezcla", Decimal("0.02"), "supuesto declarado")`

- [ ] **Step 1: Pruebas que fallan:** `test_receta_masa_debe_sumar_uno` (0,94 + 0,05 = 0,99 pasa; 0,90 + 0,05 → ValueError
  «suman 0,95 t»); `test_producir_100_t_de_mezcla_consume_94_t_de_agregado` (consumo de `AGR-12` = −94 y ningún
  movimiento para el comprado `CA-30`); `test_sin_receta_vigente_no_produce`; `test_receta_nueva_no_cambia_la_anterior`
  (la de octubre sigue vigente para una fecha de octubre); `test_producido_en_periodo_convierte_m3_con_densidad`
  (100 m³ × 1,6 = 160 t; material en m³ sin densidad → ValueError con su código).
- [ ] **Step 2: Rojo.** **Step 3: Implementar** (`ins_0007`, `down_revision = "ins_0006_prod_costo"`).
  **Step 4: Verde.** **Step 5: Commit** — `feat(produccion): receta de la planta y consumos`.

### Tarea 4: Costo por tonelada del período, guardado con sus entradas

**Modelo:** Opus (conversión de moneda, reparto y la instantánea que la tesis va a citar).

**Archivos:**
- Create: `produccion/costo.py` (puro), `aplicacion/costo_propio.py` (convierte y guarda),
  `migraciones/instalacion/versions/ins_0008_prod_calculo.py`
- Modify: `produccion/modelo.py` (`prod_calculo`), `api/rutas/produccion.py`
- Test: `tests/unit/test_produccion_costo.py`, `tests/unit/test_aplicacion_costo_propio.py`,
  `tests/integration/test_api_produccion_calculo.py`

**Interfaces:**
- Consumes: Tarea 1 (`costos_del_periodo`), Tarea 3 (`receta_vigente`, `producido_en_periodo`),
  `aplicacion/tasa_del_dia.py`.
- Produces:
  - `produccion/costo.py`:
    - `costo_por_tonelada(total: Decimal, toneladas: Mapping[str, Decimal], *, pesos: Mapping[str, Decimal] | None = None)
      -> dict[str, Decimal]` — sin `pesos`, el mismo costo por tonelada para todos (D-V-1); con `pesos` (suman 1),
      `total × peso / toneladas` de cada uno
    - `costo_de_mezcla(receta: Receta, costo_propio: Mapping[str, Decimal], precio_comprado: Mapping[str, Decimal],
      costo_planta_por_t: Decimal) -> Decimal`
  - `aplicacion/costo_propio.py`:
    - `@dataclass(frozen=True) CalculoGuardado(id: int, periodo: str, moneda: str, por_tonelada: dict[str, Decimal],
      huella: str)`
    - `calcular_periodo(sesion_ins, sesion_caso, periodo: str, moneda: str, *, pesos=None, usuario: str,
      ahora: datetime) -> CalculoGuardado` — convierte cada costo a `moneda` con la tasa de su fecha; toma el precio de
      cada componente comprado de la lista vigente de la carpeta; guarda entradas y resultado en JSON canónico con su
      huella SHA-256 en `prod_calculo`
    - `ultimo_calculo(sesion_ins, producto: str) -> CalculoGuardado | None`
  - `POST /v1/produccion/calculos` (`{"periodo", "moneda"}` → 201 con el cálculo), `GET /v1/produccion/calculos/{id}`

- [ ] **Step 1: Pruebas que fallan** (puras primero):

```python
def test_reparto_por_tonelada():
    assert costo_por_tonelada(Decimal("1000"), {"AGR-12": Decimal("150"), "AGR-34": Decimal("50")}) == {
        "AGR-12": Decimal("5"), "AGR-34": Decimal("5")}

def test_reparto_por_pesos():
    r = costo_por_tonelada(Decimal("1000"), {"A": Decimal("100"), "B": Decimal("100")},
                           pesos={"A": Decimal("0.75"), "B": Decimal("0.25")})
    assert r == {"A": Decimal("7.5"), "B": Decimal("2.5")}

def test_costo_de_mezcla():  # 0,94 t AGR a 5 + 0,05 t CA a 600 + 8 l gasoil a 0,5 + planta 12 = 4,70+30+4+12
    assert costo_de_mezcla(receta, {"AGR-12": Decimal("5")}, {"CA-30": Decimal("600"), "GO": Decimal("0.5")},
                           Decimal("12")) == Decimal("50.70")
```

Aplicación: `test_costo_en_bs_sin_tasa_ese_dia_falla_y_lo_nombra` (Foco 1); `test_periodo_sin_produccion`,
`test_periodo_sin_costos` (Foco 2, mensajes exactos de la sección Foco); `test_mismo_calculo_misma_huella`;
`test_recalcular_crea_otro_calculo` (dos ids distintos, el primero intacto); `test_comprado_sin_precio_en_la_lista`
(ValueError que nombra `CA-30`).
- [ ] **Step 2: Rojo. Step 3: Implementar** (`ins_0008`, `down_revision = "ins_0007_prod_receta"`). Redondeo: solo al
  presentar (dos decimales, `ROUND_HALF_UP`); se guarda exacto. **Step 4: Verde. Step 5: Commit** —
  `feat(produccion): costo por tonelada del periodo con instantanea`.

### Tarea 5: Publicar el costo propio al catálogo

**Modelo:** Sonnet.

**Archivos:**
- Modify: `aplicacion/costo_propio.py`, `api/rutas/produccion.py`, `seguridad/permisos.py`
- Test: `tests/unit/test_aplicacion_costo_propio_publicar.py`, `tests/integration/test_api_produccion_publicar.py`

**Interfaces:**
- Consumes: `CalculoGuardado` (Tarea 4); `core/catalog/empresa.crear_lista_de_empresa`, `PrecioPropio`.
- Produces:
  - `publicar_calculo(sesion_caso, calculo: CalculoGuardado, *, base, empresa_nombre: str, empresa_rif: str,
    usuario: str, ahora: datetime) -> models.ListaPrecios` — da de alta `AGP-…`/`MZP-…` si faltan (D-V-2); fuente de
    cada precio: `f"Producción, período {periodo}, cálculo n.º {id}"`
  - `Accion.PUBLICAR_COSTO_PROPIO = "publicar_costo_propio"` → administrador
  - `POST /v1/produccion/calculos/{id}/publicar` → 201 con el id de la lista

- [ ] **Step 1: Pruebas:** `test_publica_con_la_fuente_exacta` (fuente `"Producción, período 2026-11, cálculo n.º 7"`);
  `test_da_de_alta_el_insumo_una_sola_vez` (dos publicaciones, un solo `MZP-01`); `test_cada_publicacion_es_una_lista_nueva`;
  `test_el_apu_usa_el_costo_publicado` (una composición con `MZP-01` en una versión que referencia la lista da el
  precio del cálculo); `test_arma_recibe_403_al_publicar`.
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(produccion): publicar el costo propio como precio de la empresa`.

### Tarea 6: Pantallas de receta, cálculo y publicación

**Modelo:** Sonnet.

**Archivos:**
- Create: `frontend-desktop/src/paginas/produccion/RecetaPlanta.tsx`, `CostoPorTonelada.tsx` (+ pruebas)
- Modify: navegación de producción; cliente de la API

**Interfaces:**
- Consumes: rutas de las Tareas 3, 4 y 5.

- [ ] **Step 1: Pruebas:** `la receta muestra la suma de masa y bloquea Guardar si no está entre 0,98 y 1,02`;
  `el cálculo muestra costo por tonelada por producto y su fuente`; `un error de tasa faltante lista cada costo con su
  fecha` (Foco 1); `Publicar solo aparece con la acción y muestra la fuente con que quedará el precio`.
- [ ] **Step 2–5:** rojo, implementar, verde + lint, commit — `feat(front): receta, costo por tonelada y publicacion`.

**Cierre de fase A:** menores agrupados, `uv run --active pytest -q` y `npm --prefix frontend-desktop test` completos,
`git diff --stat c1f436b2 -- core/` vacío. Árbitro de fase.

---

## Fase B: especialidad vial

### Tarea 7: Tramos y cantidades viales (`adapters/vial/`)

**Modelo:** Opus (modelo de dominio nuevo y fórmulas que la tesis cita).

**Archivos:**
- Create: `adapters/vial/__init__.py`, `adapters/vial/modelo.py`, `adapters/vial/constantes.py`,
  `adapters/vial/derivacion.py`, `adapters/vial/tabular.py`, `data/samples/vial/via_ficticia.csv`,
  `data/samples/vial/README.md`
- Test: `tests/unit/test_vial_derivacion.py`, `tests/unit/test_vial_tabular.py`

**Interfaces:**
- Produces:
  - `TIPOS_CAPA = ("fresado", "base_granular", "subbase_granular", "imprimacion", "riego_adherencia", "carpeta", "bacheo")`
  - `@dataclass(frozen=True) Capa(tipo: str, espesor_m: Decimal | None, densidad_t_m3: Decimal | None,
    dosis_l_m2: Decimal | None)`
  - `@dataclass(frozen=True) Demarcacion(tipo: str, lineas: int)` — `tipo` en `("continua", "discontinua")`
  - `@dataclass(frozen=True) Tramo(id: str, progresiva_ini_km: Decimal, progresiva_fin_km: Decimal, ancho_m: Decimal,
    capas: tuple[Capa, ...], demarcacion: tuple[Demarcacion, ...] = (), distancia_planta_km: Decimal | None = None)`
    — `longitud_m` propiedad; progresiva final ≤ inicial → ValueError con el id
  - `PARTIDAS_VIALES: dict[str, tuple[str, str, str]]` (clave → código, descripción, unidad); códigos internos
    `VIA-…` con fuente «a cotejar con la norma COVENIN de vialidad»
  - `FRACCION_PINTADA_DISCONTINUA = Constante(...)` con fuente «supuesto declarado»
  - `derivar_tramos(tramos: Sequence[Tramo]) -> list[ItemComputo]` — `dominio=Dominio.CIVIL`,
    `especificaciones={"especialidad": "vial", "capa": tipo}`, `origen_tipo=OrigenTipo.REGLA`,
    `origen_id=f"tramo:{id}:capa:{n}"`, `regla` = la expresión evaluada (p. ej. `"longitud*ancho*espesor*densidad"`)
  - `leer_tramos(ruta: Path) -> list[Tramo]` (CSV con coma o punto decimal; error con número de fila) y
    `class AdaptadorVial(AdaptadorDominio)` con `dominio = Dominio.CIVIL`

- [ ] **Step 1: Pruebas** (oráculos a mano):

```python
TRAMO = Tramo("T1", Decimal("0"), Decimal("1"), Decimal("7.3"),
              (Capa("carpeta", Decimal("0.05"), Decimal("2.35"), None),
               Capa("base_granular", Decimal("0.20"), None, None),
               Capa("riego_adherencia", None, None, Decimal("0.5"))),
              (Demarcacion("continua", 2),), Decimal("12"))

def test_carpeta_en_m2_y_toneladas():   # 1000 × 7,3 = 7300 m²; × 0,05 × 2,35 = 857,75 t
def test_base_en_m3():                   # 7300 × 0,20 = 1460 m³
def test_riego_en_m2_y_litros():         # 7300 m²; 3650 l
def test_demarcacion_continua_en_m():    # 2000 m
def test_transporte_t_km():              # 857,75 × 12 = 10293 t·km
def test_origen_y_especialidad():        # origen_id "tramo:T1:capa:1", especificaciones["especialidad"] == "vial"
def test_progresiva_invertida():         # Tramo("T2", 2, 1, ...) -> ValueError("T2")
```

Tabular: `test_lee_coma_decimal` («7,30» → `Decimal("7.30")`, Foco 3); `test_fila_invertida_dice_su_numero`;
`test_capa_desconocida_rechazada`; `test_via_ficticia_completa` (el CSV de muestra produce los ítems esperados).
- [ ] **Step 2–5:** rojo, implementar, verde (+ `tests/unit/test_arquitectura*.py`), commit —
  `feat(vial): tramos y cantidades viales trazables`.

### Tarea 8: Tramos guardados por versión, API y pantalla

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/vial.py`, `migraciones/caso/versions/caso_0019_vial_tramos.py`, `api/rutas/vial.py`,
  `frontend-desktop/src/paginas/vial/Tramos.tsx` (+ pruebas)
- Modify: `api/main.py` (router), sección de la obra en el marco («Tramos» solo en obras viales)
- Test: `tests/unit/test_aplicacion_vial.py`, `tests/integration/test_api_vial.py`

**Interfaces:**
- Consumes: Tarea 7.
- Produces: `guardar_tramos(sesion, version_id: int, tramos: Sequence[Tramo], *, usuario: str, ahora: datetime) -> None`,
  `tramos_de_version(sesion, version_id: int) -> list[Tramo]`; `GET`/`PUT` de tramos de una versión e
  `POST …/tramos/importar` (CSV), siguiendo el estilo de rutas de la Hoja; acción existente `EDITAR_HOJA`.

- [ ] **Step 1: Pruebas:** `test_guardar_y_leer_igual` (ida y vuelta exacta); `test_version_aprobada_no_se_edita`
  (mismo criterio que la Hoja: 409); `test_importar_csv_con_fila_mala_no_guarda_nada` (todo o nada, 422 con el número
  de fila); front: `muestra m², t y t·km por tramo con coma decimal`, `el error de importación nombra la fila`.
- [ ] **Step 2–5:** rojo, implementar (`caso_0019`, `down_revision = "caso_0018_mp_corte_tasa"`), verde, commit —
  `feat(vial): tramos por version, API y pantalla`.

### Tarea 9: Reglas viales del auditor

**Modelo:** Sonnet.

**Archivos:**
- Create: `adapters/vial/reglas.py`
- Modify: `aplicacion/vial.py` (los hallazgos viales entran como `externos` en la auditoría, igual que los de `Espacio`)
- Test: `tests/unit/test_vial_reglas.py`

**Interfaces:**
- Consumes: Tarea 7; `core.contracts` `Hallazgo`, `Severidad`; patrón `_hallazgo` de `adapters/espacio/reglas.py`.
- Produces: `auditar_vial(tramos: Sequence[Tramo], presupuesto: Presupuesto, *, receta: Receta | None = None) ->
  list[Hallazgo]` con las reglas:
  - `VR1` toneladas de carpeta en el presupuesto ≠ área × espesor × densidad (tolerancia `Constante` 0,5 %)
  - `VR2` porcentaje de asfalto de la receta fuera del rango declarado
  - `VR3` dosis de riego o imprimación fuera de rango (l/m²)
  - `VR4` t·km de transporte ≠ toneladas × distancia declarada
  - `VR5` pintura por kilómetro de línea fuera de rango
  - `VR6` progresivas solapadas o con huecos en la misma vía
  - `VR7` unidad de la partida incompatible con su capa
  Cada rango es `Constante` en `adapters/vial/constantes.py` con fuente o «a cotejar».

- [ ] **Step 1: Pruebas** por regla, con su frontera: dentro del rango → sin hallazgo; justo fuera → un hallazgo con
  `origen_ids == ("tramo:T1:capa:1",)`, `valor_observado` y `valor_esperado` exactos. `VR6`: T1 0–1 km y T2 0,9–2 km →
  un hallazgo «solape de 0,1 km entre T1 y T2»; T1 0–1 y T2 1,2–2 → «hueco de 0,2 km» (Foco 3).
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(vial): reglas VR1 a VR7 del auditor`.

### Tarea 10: Conciliación entre APU, presupuesto, tramos y costo propio

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/conciliacion.py`
- Test: `tests/unit/test_aplicacion_conciliacion.py`

**Interfaces:**
- Consumes: Tareas 4, 7 y 8; motor de costos existente para recalcular el APU.
- Produces: `conciliar(presupuesto, composiciones, parametros, *, items_viales: Sequence[ItemComputo],
  costos_propios: Mapping[str, CalculoGuardado]) -> list[Hallazgo]`:
  - `CV1` precio unitario del renglón ≠ el recalculado de su APU (tolerancia 0,01 en la moneda). **Antes de escribirla,
    comprobar si una regla R existente ya lo hace; si sí, se reutiliza y `CV1` no se crea** (decirlo en el commit).
  - `CV2` cantidad del renglón ≠ suma de las cantidades de los tramos para esa partida
  - `CV3` precio de `AGP-…`/`MZP-…` usado ≠ el del último cálculo publicado (con el n.º de ambos)

- [ ] **Step 1: Pruebas:** un caso coherente → `[]`; cada CV alterada aisladamente → exactamente su hallazgo con
  origen.
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(vial): conciliacion APU presupuesto tramos costo propio`.

### Tarea 11: Mutaciones viales para el ensayo de estrés

**Modelo:** Sonnet.

**Archivos:**
- Create: `asistente/experimento/mutaciones_viales.py`
- Test: `tests/unit/test_mutaciones_viales.py`

**Interfaces:**
- Consumes: Tareas 7, 9 y 10. No cambia el sembrador de `Espacio`.
- Produces: `TIPOS_VIALES = ("EV1_espesor_x10", "EV2_densidad_coma", "EV3_dosis", "EV4_unidad", "EV5_digitos",
  "EV6_progresiva")`; `@dataclass(frozen=True) MutanteVial(tipo: str, tramos: tuple[Tramo, ...], descripcion: str)`;
  `sembrar_vial(tramos: Sequence[Tramo], *, semilla: int, por_tipo: int) -> list[MutanteVial]`;
  `matriz_de_deteccion(mutantes, auditar) -> dict[str, tuple[int, int]]` (detectados, total por tipo).

- [ ] **Step 1: Pruebas:** `test_misma_semilla_mismos_mutantes`; `test_cada_tipo_altera_un_solo_campo`;
  `test_matriz_sobre_via_ficticia` (deja escrita la matriz esperada; un tipo que no detecte ninguna regla queda en la
  prueba como límite declarado, no se esconde).
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(experimento): mutaciones viales y matriz de deteccion`.

**Cierre de fase B:** menores, suites completas, `core/` sin cambios. Árbitro de fase.

---

## Fase C: riesgo y mejora de la estimación

### Tarea 12: Series viales y su mapa a insumos

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/riesgo/__init__.py`, `aplicacion/riesgo/series.py`, `data/samples/vial/series_ficticias.csv`
- Test: `tests/unit/test_riesgo_series.py`

**Interfaces:**
- Consumes: `core/catalog/indices.registrar_importacion`, `DefinicionSerie`, `Observacion`, `valor_en`.
- Produces:
  - `SERIES_VIALES: tuple[DefinicionSerie, ...]` — `CEMENTO_ASFALTICO_USD` (USD/t, mensual), `GASOIL_USD` (USD/l,
    mensual); la tasa BCV es la serie existente
  - `importar_serie_csv(sesion, codigo: str, ruta: Path, *, fuente: str, responsable: str, hoy: date) -> int | None`
  - `@dataclass(frozen=True) MapaSeries(serie_por_insumo: Mapping[str, str])` — clave: **descripción** del insumo
    (así indexa `generar_escenario` sus `precios`)
  - `historia_mensual(sesion, codigos: Sequence[str], desde: date, hasta: date) -> dict[str, dict[date, Decimal]]`

- [ ] **Step 1: Pruebas:** `test_importar_dos_veces_misma_huella_no_duplica` (segunda vez `None`);
  `test_unidad_distinta_rechazada` (mismo código con otra unidad → el error de `_serie`); `test_historia_por_mes`.
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(riesgo): series viales y mapa a insumos`.

### Tarea 13: Proyección del riesgo

**Modelo:** Opus.

**Archivos:**
- Create: `aplicacion/riesgo/proyeccion.py`
- Test: `tests/unit/test_riesgo_proyeccion.py`

**Interfaces:**
- Consumes: Tarea 12; `generar_escenario`; Tarea 4 (`costo_de_mezcla`) y Tarea 3 (`Receta`).
- Produces:
  - `@dataclass(frozen=True) ParametrosProyeccion(inicio: date, meses: int = 6, semilla: int = 1, trayectorias: int = 2000,
    ventana_meses: int = 36, percentiles: tuple[int, ...] = (50, 80))`
  - `@dataclass(frozen=True) Proyeccion(total_base: Decimal, percentiles: dict[int, Decimal], reserva: Decimal,
    contribucion: tuple[tuple[str, Decimal], ...], meses_usados: int, semilla: int, supuestos: tuple[str, ...])`
  - `proyectar(presupuesto, composiciones, parametros_costo, historia: Mapping[str, Mapping[date, Decimal]],
    mapa: MapaSeries, p: ParametrosProyeccion, *, recetas: Mapping[str, Receta] = {},
    costo_planta_por_t: Mapping[str, Decimal] = {}) -> Proyeccion`

Algoritmo (fijado por la especificación §5.1, puntos 2 y 3):

```
meses válidos = meses de la ventana con dato en TODAS las series del mapa y en la tasa
si len < 12: ValueError(f"solo hay {n} meses completos; se necesitan 12")
variación del mes m de la serie s = valor[m] / valor[m-1]
rng = random.Random(semilla)
por trayectoria: elegir `meses` meses válidos con reemplazo (el MISMO mes para todas las series)
  multiplicador acumulado de cada serie por mes del plazo
  factor de cada insumo = promedio de sus multiplicadores en el plazo (gasto uniforme, D-V-3)
  insumo en Bs sin serie: factor = factor de la tasa (USD fijo × tasa)
  mezcla propia: costo_de_mezcla con los componentes ya multiplicados
  total = generar_escenario(..., precios=precios multiplicados).total
percentiles por rango ordenado (método «más cercano por rango», documentado); reserva = P80 − total base
contribucion = por insumo, cantidad × precio × (media del factor − 1), ordenado de mayor a menor
```

- [ ] **Step 1: Pruebas:**

```python
def test_crecimiento_constante_da_un_solo_valor():
    # toda la historia sube 1 % mensual: todas las trayectorias iguales
    p = proyectar(...,  ParametrosProyeccion(inicio=date(2027, 1, 1), meses=6, trayectorias=200))
    esperado = total_base * promedio(1.01 ** k for k in 1..6)   # calculado a mano en la prueba
    assert p.percentiles[50] == p.percentiles[80]
    assert abs(p.percentiles[50] - esperado) < Decimal("0.01")   # se guarda exacto; se redondea al presentar

def test_misma_semilla_mismo_resultado(): ...
def test_otra_semilla_otro_resultado(): ...
def test_menos_de_12_meses_completos():  # ValueError("solo hay 9 meses completos; se necesitan 12") (Foco 4)
def test_mes_faltante_en_una_serie_se_descarta_para_todas():  # meses_usados baja en 1
def test_la_mezcla_sube_si_sube_el_asfalto():  # con solo CA subiendo, el precio de MZP-01 en el escenario sube
def test_insumo_en_bs_sin_serie_sigue_la_tasa():
def test_supuestos_declarados():  # "gasto uniforme", "USD fijo × tasa" en p.supuestos
```

- [ ] **Step 2–5:** rojo, implementar, verde (con 200 trayectorias la prueba corre en menos de 30 s), commit —
  `feat(riesgo): proyeccion por remuestreo de meses completos`.

### Tarea 14: Comprobación hacia atrás

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/riesgo/comprobacion.py`
- Test: `tests/unit/test_riesgo_comprobacion.py`

**Interfaces:**
- Consumes: Tarea 13.
- Produces: `@dataclass(frozen=True) ResultadoCorte(corte: date, p50: Decimal, p80: Decimal, real: Decimal, dentro: bool)`;
  `@dataclass(frozen=True) Comprobacion(cortes: tuple[ResultadoCorte, ...], cobertura: Decimal, n_cortes: int)`;
  `comprobar_hacia_atras(presupuesto, composiciones, parametros_costo, historia, mapa, p: ParametrosProyeccion,
  **kw) -> Comprobacion` — cortes mensuales móviles; en cada corte proyecta solo con la historia anterior al corte y
  compara con el total revalorizado con los valores reales del horizonte; `dentro` = `real <= p80`.

- [ ] **Step 1: Pruebas:** `test_sin_sorpresas_cobertura_uno` (crecimiento constante → todos dentro, cobertura 1);
  `test_un_choque_queda_fuera` (un mes de +40 % después de un corte → ese corte `dentro=False`);
  `test_la_proyeccion_no_ve_el_futuro` (alterar un valor posterior al corte no cambia su p80);
  `test_informa_el_numero_de_cortes`.
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(riesgo): comprobacion hacia atras con cortes moviles`.

### Tarea 15: Informe de mejora de la estimación

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/riesgo/mejora.py`, `api/rutas/riesgo.py` (primera ruta)
- Modify: `api/main.py`, `seguridad/permisos.py` (`Accion.VER_RIESGO = "ver_riesgo"` → arma, revisa, administrador)
- Test: `tests/unit/test_riesgo_mejora.py`, `tests/integration/test_api_riesgo.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) Mejora(error_original_pct: Decimal, error_silice_pct: Decimal, mejora_pp: Decimal)`;
  `mejora_de_estimacion(costo_final_real: Decimal, presupuesto_original: Decimal, estimacion_silice: Decimal) -> Mejora`
  — error = |estimado − real| ÷ real × 100, dos decimales `ROUND_HALF_UP`; `POST /v1/riesgo/mejora`.

- [ ] **Step 1: Pruebas:** real 130, original 100, Sílice 125 → `Mejora(Decimal("23.08"), Decimal("3.85"),
  Decimal("19.23"))`; real 0 → ValueError; Sílice peor que el original → `mejora_pp` negativa (no se esconde); API 403
  sin `ver_riesgo`, 422 con texto no decimal.
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(riesgo): informe de mejora de la estimacion`.

### Tarea 16: Pantalla «Riesgo de la obra» y el asistente que la explica

**Modelo:** Opus.

**Archivos:**
- Create: rutas de proyección y comprobación en `api/rutas/riesgo.py`; `frontend-desktop/src/paginas/riesgo/RiesgoDeLaObra.tsx`
  (+ pruebas); herramienta de solo lectura `explicar_riesgo` junto a las de `asistente/herramientas.py`
- Test: `tests/integration/test_api_riesgo.py` (ampliar), `tests/unit/test_asistente_explicar_riesgo.py`

**Interfaces:**
- Consumes: Tareas 13, 14 y 15; `aplicacion/riesgo/series.historia_mensual`.
- Produces: `POST /v1/obras/{obra}/versiones/{v}/riesgo/proyeccion` y `…/riesgo/comprobacion` (cuerpo: parámetros
  de D-V-3, fechas de la línea base si existe, si no inicio y meses declarados); la herramienta devuelve los números
  ya calculados y el asistente solo los narra; la validación existente de citas rechaza un número que no venga de la
  herramienta.

- [ ] **Step 1: Pruebas:** front: `muestra P50, P80, reserva y los tres insumos que más empujan, con coma decimal`;
  `muestra la cobertura y el número de cortes`; `el error de pocos meses muestra el número` (Foco 4); asistente:
  `una respuesta con una cifra que no está en la herramienta se rechaza`.
- [ ] **Step 2–5:** rojo, implementar, verde + lint, commit — `feat(riesgo): pantalla de riesgo y explicacion del asistente`.

**Cierre de fase C:** menores, suites completas, `core/` sin cambios. Árbitro de fase.

---

## Fase D: pedidos transversales

### Tarea 17: FCAS por componentes

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/fcas.py`, `api/rutas/fcas.py`, `frontend-desktop/src/paginas/precios_empresa/CalculadoraFCAS.tsx`
  (+ pruebas)
- Test: `tests/unit/test_aplicacion_fcas.py`, `tests/integration/test_api_fcas.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) ComponenteFCAS(id: str, nombre: str, base: str, valor: Decimal, fuente: str)` —
  `base` en `("dias", "porcentaje")`; `COMPONENTES_FCAS: tuple[ComponenteFCAS, ...]` con, entre otros, `paro_forzoso`
  (Régimen Prestacional de Empleo) y `utilidades` (de los trabajadores), cada uno con fuente en
  `docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt` o `docs/fuentes/CCT_Construccion_GO_6752_Ext_2023-07-06.txt`
  (artículo o cláusula) o «a cotejar» si no se encuentra; `calcular_fcas(componentes, dias_trabajados: Decimal) ->
  ResultadoFCAS(fcas: Decimal, desglose: tuple[tuple[str, Decimal], ...], a_cotejar: tuple[str, ...])` con
  `fcas = Σ días ÷ días_trabajados + Σ porcentajes`; `POST /v1/fcas/calcular`.

- [ ] **Step 1: Pruebas:** 120 días ÷ 240 + 0,10 → `Decimal("0.60")`; el desglose suma el total; un componente
  «a cotejar» aparece en `a_cotejar` y la pantalla lo avisa; la pantalla muestra el FCAS calculado al lado del de la
  versión (6,00 por defecto) y **no lo aplica sola**: aplicar usa la edición de parámetros que ya existe.
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(costos): FCAS por componentes con su base legal`.

### Tarea 18: IVA sobre el presupuesto y las valuaciones

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/impuestos.py`
- Modify: la respuesta del resumen del presupuesto y la de valuaciones (añadir campos, sin quitar ni renombrar), y
  sus vistas en el front
- Test: `tests/unit/test_aplicacion_impuestos.py`, pruebas de API y front de esas vistas

**Interfaces:**
- Produces: `ALICUOTA_IVA = Constante("iva_general", "Alícuota general del IVA", Decimal("0.16"), "Ley del IVA, alícuota
  general — a cotejar con la Gaceta vigente")`; `@dataclass(frozen=True) ResumenImpuestos(subtotal: Decimal,
  iva: Decimal, total: Decimal)`; `con_iva(subtotal: Decimal, alicuota: Decimal = ALICUOTA_IVA.valor) -> ResumenImpuestos`
  (dos decimales `ROUND_HALF_UP`).

- [ ] **Step 1: Pruebas:** 1000 → 160,00 → 1160,00; 0,05 → IVA 0,01; la respuesta del resumen trae `subtotal`, `iva`,
  `total` y la fuente de la alícuota; el APU no cambia (prueba de que un precio unitario es el mismo antes y después).
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(impuestos): IVA sobre presupuesto y valuaciones`.

### Tarea 19: Especialidades y módulos activables

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/modulos.py`, `migraciones/instalacion/versions/ins_0009_modulo.py`, `api/rutas/modulos.py`,
  pantalla en Administración
- Modify: `seguridad/permisos.py` (`Accion.ACTIVAR_MODULOS` → administrador); routers de producción, vial y riesgo
  (dependencia `requiere_modulo`); marco del front (oculta lo apagado)
- Test: `tests/unit/test_aplicacion_modulos.py`, `tests/integration/test_api_modulos.py`,
  `tests/unit/test_arquitectura_vial.py`

**Interfaces:**
- Produces: `MODULOS = ("produccion", "vial", "edificacion", "riesgo")`; `modulos_activos(sesion) -> frozenset[str]`
  (todos activos por defecto); `fijar_modulo(sesion, clave: str, activo: bool, *, usuario: str, ahora: datetime) -> None`;
  `requiere_modulo(clave: str)` (dependencia FastAPI, D-V-4); `GET /v1/modulos`, `PUT /v1/modulos/{clave}`.

- [ ] **Step 1: Pruebas:** apagar `vial` → `GET` de tramos 404 con el detalle exacto de D-V-4 y los tramos siguen en la
  base; encender → mismos tramos (Foco 5); `revisa` recibe 403 al cambiar; arquitectura: nada en `core/` importa
  `adapters.vial`, `produccion` ni `aplicacion.riesgo`; la aplicación arranca y responde con todo lo nuevo apagado.
- [ ] **Step 2–5:** rojo, implementar (`ins_0009`, `down_revision = "ins_0008_prod_calculo"`), verde, commit —
  `feat(modulos): especialidades y modulos activables por instalacion`.

### Tarea 20: Búsqueda con autocompletado en tablas venezolanas

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/consulta.py`, `api/rutas/consulta.py`, `frontend-desktop/src/comun/CampoConSugerencias.tsx`
  (+ pruebas)
- Modify: los campos de capa y partida (Tarea 8), componentes de receta (Tarea 6) y concepto de costo (Tarea 2)

**Interfaces:**
- Produces: `TABLAS = ("partidas_viales", "insumos", "tasa_bcv", "salarios_cct")`;
  `@dataclass(frozen=True) Sugerencia(valor: str, etiqueta: str, fuente: str)`;
  `buscar(sesion, tabla: str, q: str, *, limite: int = 10) -> list[Sugerencia]` (sin distinguir mayúsculas ni
  acentos); `GET /v1/consulta/{tabla}?q=&limite=`.

- [ ] **Step 1: Pruebas:** «carpeta» y «CARPÉTA» dan la misma primera sugerencia; tabla desconocida → 404; cada
  sugerencia trae su fuente; front: el campo navega con flechas, Enter elige, Escape cierra, y el lector de pantalla
  anuncia el número de sugerencias.
- [ ] **Step 2–5:** rojo, implementar, verde + lint, commit — `feat(consulta): autocompletado con tablas venezolanas`.

### Tarea 21: Reportes

**Modelo:** Sonnet.

**Archivos:**
- Create: `aplicacion/reportes_viales.py`, rutas en `api/rutas/vial.py` y `api/rutas/riesgo.py`
- Test: `tests/unit/test_reportes_viales.py`

**Interfaces:**
- Consumes: Tareas 4, 7–10, 13–15 y 18; patrón de `aplicacion/hoja_exportar.py` (openpyxl).
- Produces: `computos_por_tramo(...)`, `apu_con_origen(...)`, `costo_de_produccion(...)`, `informe_de_riesgo(...)`,
  `informe_de_mejora(...)`, `resumen_con_iva(...)`, cada uno `-> bytes` (xlsx) con hoja de portada que dice la fuente
  de cada cifra; descarga con `GET …/reportes/{tipo}`.

- [ ] **Step 1: Pruebas:** abrir cada libro con openpyxl y comprobar nombres de hoja y celdas clave (857,75 t del
  tramo T1; la fuente «Producción, período …, cálculo n.º …» en el APU; P50/P80 y supuestos en el de riesgo; 23,08 /
  3,85 / 19,23 en el de mejora); formato numérico es-VE.
- [ ] **Step 2–5:** rojo, implementar, verde, commit — `feat(reportes): reportes viales, de riesgo y de mejora`.

### Tarea 22: Cierre

**Modelo:** Sonnet para los menores; el orquestador corre la suite, la medida del núcleo y el navegador.

- [ ] **Step 1:** crear `data/samples/produccion/` con una cantera y una planta ficticias (materiales, producción de
  dos meses, costos por centro y una receta), declaradas ficticias en su README; prueba de punta a punta
  `tests/integration/test_vial_extremo_a_extremo.py` con la vía, la cantera, la planta y las series ficticias: costos → cálculo → publicación → tramos → APU → auditoría y conciliación →
  proyección → comprobación → mejora → reportes.
- [ ] **Step 2:** menores agrupados de las fases.
- [ ] **Step 3:** `uv run --active pytest -q`, `npm --prefix frontend-desktop test`, `npm --prefix frontend-desktop run lint`
  completos; salidas guardadas en el scratchpad de la sesión.
- [ ] **Step 4:** **medida del núcleo:** `git diff --stat c1f436b2 -- core/` vacío; anotar en la bitácora el número de
  archivos y líneas añadidos fuera de `core/` (es la cifra de «ampliación sin tocar el núcleo» para la tesis).
- [ ] **Step 5:** única pasada de navegador (1056/1366/1910, letra 1 y 1,5): costos del período, receta, cálculo,
  tramos, riesgo, módulos apagados; capturas de datos reales solo en el scratchpad.
- [ ] **Step 6:** bitácora `docs/bitacora/AAAA-MM-DD-cierre-vial.md` y CHANGELOG. Árbitro final.

## Fuera de este plan

- Retenciones de IVA e ISLR en valuaciones (D-V-5).
- Diseño estructural de pavimentos, alineamientos y modelos 3D de vías (especificación §3).
- La medición formal de la tesis con los economistas: se hace con este sistema congelado y con datos reales en local.
