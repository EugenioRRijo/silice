# Expedientes de la fase C1 del cierre (núcleo)

**Fecha:** 2026‑09‑23 · **Rama:** `inc/cierre-C1` · **Inventario:**
[docs/auditoria/2026-09-inventario.md](../auditoria/2026-09-inventario.md) · **Spec:**
[§4 y §5](../superpowers/specs/2026-09-23-plan-cierre-tesis-design.md) · **Paquete para el tutor:**
[docs/tesis/revisiones/2026-09-paquete-tutor.md](../tesis/revisiones/2026-09-paquete-tutor.md).

La spec (§5, fila C1) exige un expediente previo por cada hallazgo de `core/`, y (§4) que la
corrección que cambia un contrato de `core/contracts/` espere el aval del tutor. La sección A
reúne los tres hallazgos que cambian contratos: quedan **aceptados por decisión de arquitectura
registrada (pendiente del aval del tutor)**, el único caso en que ese estado es válido. Si el aval
llega antes de `v1.0-tesis`, el hallazgo vuelve a quedar abierto y se corrige; si se niega, se
declara en el capítulo de limitaciones con este expediente. La sección B reúne los hallazgos de
`core/` que C1 cierra sin tocar contratos; cada entrada se escribió antes de su código y enumera
la decisión que Eugenio ratifica en GC1.

## A. Hallazgos cuyo cierre exige cambiar un contrato

### A.1 INV-001: los enumerados de `Rendimiento` e `ItemComputo` no se convierten

**Problema.** `Rendimiento.__post_init__` (`core/contracts/apu.py:193`) e
`ItemComputo.__post_init__` (`core/contracts/item_computo.py:54`) comparan el enumerado con `is`
sin convertir la entrada. Con la cadena en lugar del miembro (`tipo="medido"`,
`origen_tipo="regla"`) se saltan sus invariantes: un rendimiento MEDIDO sin
`referencia_ejecucion` y un ítem REGLA sin `regla`. `dominio` tampoco se convierte. El contrato
vecino ya lo hace bien: `LineaManoObra` convierte `modalidad` (`core/contracts/apu.py:99`).

**Evidencia.** Reproducido en el registro de la Tarea 5 de C0 (inventario §5). Ningún llamador
actual de `adapters/`, `ml/`, `api/`, `ui/` ni `scripts/` pasa cadenas (dictamen R6): el riesgo es
latente, no hay dato corrompido.

**Cambio de contrato propuesto.**

```python
# core/contracts/apu.py, primera línea de Rendimiento.__post_init__:
object.__setattr__(self, "tipo", TipoRendimiento(self.tipo))

# core/contracts/item_computo.py, en ItemComputo.__post_init__, antes de la comprobación de REGLA:
object.__setattr__(self, "origen_tipo", OrigenTipo(self.origen_tipo))
object.__setattr__(self, "dominio", Dominio(self.dominio))
```

Es retrocompatible: un miembro del enumerado pasa sin cambio (`StrEnum(miembro) is miembro`) y una
cadena válida se convierte. Una cadena inválida ahora lanza `ValueError`, cuando antes pasaba sin
aviso. Se acompaña de cuatro casos en `tests/unit/test_contracts.py` (cadena válida convertida y
cadena que salta la invariante, para cada contrato).

| Alternativa | Por qué no |
|---|---|
| Validar en cada frontera (API, adaptadores, UI) | Repite la regla en cada capa (DRY) y deja al contrato sin proteger su propia invariante (CLAUDE.md §5) |
| `isinstance` estricto con `TypeError` | Más estricto que el precedente de `LineaManoObra`; rompe a un llamador que envíe texto de un JSON o CSV |
| No cambiar y declarar la limitación | Es el estado mientras no llegue el aval |

**Costo de hacerlo:** seis líneas en dos contratos «estables» (CLAUDE.md §5), más las pruebas. La
línea base no cambia porque sus datos usan miembros.

**Costo de no hacerlo:** un llamador futuro que construya contratos desde texto (la API recibe
JSON) podría crear un rendimiento MEDIDO sin ejecución, lo que rompe RF‑25, o un ítem REGLA sin
expresión, lo que rompe la trazabilidad de R1. Queda declarado en limitaciones.

**Paquete para el tutor:** punto `INV‑001`.

### A.2 INV-002: montos y parámetros de los contratos no exigen `Decimal` ni signo

**Problema.** No exigen `Decimal` ni signo:

- `ItemComputo.parametros` (`core/contracts/item_computo.py:42,57`);
- los seis montos de `ResultadoAPU` (`core/contracts/apu.py:161-170`);
- `PuntoCurva.monto` y `acumulado` (`core/contracts/presupuesto.py:33-39`);
- `Hallazgo.impacto`, `valor_observado` y `valor_esperado` (`core/contracts/verificacion.py:28-38`).

Aceptan `1.5`, `-2.0` y `0.1` (comprobado en C0).

**Evidencia.** No se detectó uso real de `float` (R6): falta la validación, no hay dato corrompido.
La consecuencia más grave, que un `float` en `parametros` abortara el informe, la cierra C1 **sin
contrato** en INV‑003: el evaluador rechaza lo que no es `Decimal` (expediente B.1).

**Cambio de contrato propuesto.**

```python
# ItemComputo.__post_init__, antes de congelar `parametros`:
for nombre, valor in self.parametros.items():
    if not isinstance(valor, Decimal):
        raise TypeError(f"parametros[{nombre!r}] debe ser Decimal, no {type(valor).__name__}")

# ResultadoAPU (nuevo __post_init__):
def __post_init__(self) -> None:
    for nombre in ("materiales", "equipos", "mano_obra", "costo_directo",
                   "con_administracion", "precio_unitario"):
        _no_negativo(nombre, getattr(self, nombre))

# PuntoCurva (nuevo __post_init__):
def __post_init__(self) -> None:
    _no_negativo("monto", self.monto)
    _no_negativo("acumulado", self.acumulado)

# Hallazgo.__post_init__: tipo sin signo. R5 produce negativos por diseño: su diferencia lleva
# signo y su valor esperado sale del balance (core/verification/reglas.py:475). R7 toma abs() en
# el impacto (:681, :696, :711) y solo arrastra el signo de los montos que copia a
# valor_observado y valor_esperado:
for nombre in ("impacto", "valor_observado", "valor_esperado"):
    valor = getattr(self, nombre)
    if valor is not None:
        _exigir_decimal(nombre, valor)
```

`_exigir_decimal` y `_no_negativo` viven hoy en `core/contracts/apu.py:13-23`. Para que
`presupuesto.py`, `verificacion.py` e `item_computo.py` los usen sin importar privados de un
módulo hermano se propone moverlos a `core/contracts/_validacion.py`.

Antes de aplicar, dos comprobaciones. Primero, que `core/budget/curva.generar_curva` con
`cuantizar` no pueda dejar el último período en negativo: su monto es el total menos lo repartido,
y el redondeo hacia arriba de los anteriores podría excederlo. Segundo, que una prueba de R5 con
balance negativo siga produciendo el informe (prueba de aceptación del inventario).

| Alternativa | Por qué no |
|---|---|
| Validar solo en las fronteras (adaptadores, API) | Los contratos son la única forma que cruza paquetes; validar afuera repite la regla |
| `_no_negativo` también en `Hallazgo` | Rompe R5, que informa desviaciones negativas por diseño (`core/verification/reglas.py:475`; dictamen R7 de GC0). En R7 el impacto usa `abs()` (`:681`, `:696`, `:711`): un negativo solo es plausible si `PuntoCurva.monto` no se valida, que es justo lo que plantea INV‑002 |

**Costo de hacerlo:** cuatro contratos «estables» cambian, más el módulo de validación compartido
y las pruebas. Existe el riesgo del último período negativo, a comprobar antes.

**Costo de no hacerlo:** un `float` o un monto negativo pueden cruzar fronteras sin aviso (principio
3). El camino que más dañaba, la aritmética de R1 y R5, ya queda cerrado por INV‑003. Queda
declarado en limitaciones.

**Paquete para el tutor:** punto `INV‑002`.

### A.3 INV-006: el evaluador de expresiones en cinco copias

**Problema.** El evaluador aritmético de expresiones trazables existe cinco veces:
`core/verification/expresiones.py` (167 líneas) y `adapters/{civil,industrial,sistemas,telecom}/evaluador.py`
(74, 79, 60 y 66 líneas). Las copias civil e industrial son idénticas salvo el docstring. Es deuda
declarada: la ADR 8 y §6.1 de `docs/arquitectura.md:930,944` declaran dos copias, y las bitácoras de
I5 las otras tres. La propia ADR 8 prevé su cierre en `core.contracts.expresiones`.

**Evidencia.** Inventario §3, filas INV‑006 e INV‑058. Hay un costo nuevo y concreto: la corrección
de INV‑003 en C1 (rechazar lo que no es `Decimal`) solo llega a la copia del núcleo, y las cuatro de
los adaptadores siguen lanzando `TypeError` con un `float`.

**Cambio de contrato propuesto.** Un módulo nuevo `core/contracts/expresiones.py`, el único que los
adaptadores pueden importar (CLAUDE.md §2):

```python
OPERADORES_ARITMETICOS: frozenset[type[ast.operator]] = frozenset(
    {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow}
)

class ExpresionInvalida(ValueError): ...
class ParametroFaltante(KeyError): ...

def evaluar(
    expresion: str,
    valores: Mapping[str, Decimal],
    operadores: frozenset[type[ast.operator]] = OPERADORES_ARITMETICOS,
    unarios: bool = True,
) -> Decimal: ...
```

`core/verification/expresiones.py` conserva `codigos_de`, `sustituir_codigos` y `nombres_de`, y
delega `evaluar`. En la **subtarea de C2**, que depende del aval, los cuatro adaptadores importan
`core.contracts.expresiones.evaluar` con sus subconjuntos: sistemas `{Add, Mult}`, telecom
`{Add, Sub, Mult, Div}`, civil e industrial los cinco. El módulo nuevo agrega una fila a la tabla de
CLAUDE.md §5.

| Alternativa | Por qué no |
|---|---|
| Mantener las cinco copias con pruebas de equivalencia | Es el precio declarado hoy (ADR 8); cada corrección se aplica cinco veces |
| Módulo compartido dentro de `adapters/` | Rompe la autonomía de los adaptadores (dictamen R5 de GC0; `tests/unit/test_adapter_telecom.py:154-170`) |
| Que los adaptadores importen `core.verification` | Viola la regla «los adaptadores solo importan `core.contracts`» y la hipótesis central |

**Costo de hacerlo:** un contrato nuevo de unas 100 líneas. En C2 se migran cuatro adaptadores
(unas 280 líneas menos) conservando los subconjuntos reducidos. Tienen que seguir pasando
`test_arquitectura.py` y las pruebas de adaptadores.

**Costo de no hacerlo:** cinco copias declaradas en el capítulo de limitaciones; INV‑058 (C4)
documenta cinco y no dos; toda corrección del evaluador, como INV‑003, queda parcial.

**Paquete para el tutor:** punto `INV‑006`.

## B. Expedientes previos de los hallazgos de `core/` que no cambian contratos

### B.1 INV-003: un `float` en `parametros` aborta el informe

**Corrección.** `core/verification/expresiones._evaluar_nodo` rechaza con `ExpresionInvalida` todo
parámetro que no sea `Decimal`. R1 y R5 ya convierten esa excepción en hallazgo.

**Alternativa descartada.** Capturar `TypeError` en `_evaluar_binario`, que es la redacción literal
del inventario. No cubre la expresión de un solo nombre (`"longitud"`), donde el `TypeError` aparece
después, al comparar con la cantidad (`reglas.py:151`). Con la validación en el nodo, ese
`TypeError` es inalcanzable y no se agrega un `except` muerto.

**Línea base y 7 de 7:** no cambian; sus parámetros son `Decimal`.

**Ratificar:** la desviación de la redacción literal.

### B.2 INV-012: regla no evaluable por falta de datos, INFO; R2 y R7 no aplicables sin plan

**Corrección.** Manda la ERS: RF‑23 y UC‑05 3a piden INFO «regla no evaluable» cuando una regla
no tiene los datos que necesita, y UC‑05 2a pide declarar R7 no aplicable sin plan. Se distingue
el dato que **falta** del dato que **está mal**:

- INFO «regla no evaluable»: `ParametroFaltante` en R1 y en R5, y la referencia no resuelta del
  balance de R5 (cita una partida que no está en el presupuesto).
- Sigue siendo ERROR: `ExpresionInvalida` en R1 y R5, es decir, sintaxis no analizable, un
  parámetro que no es `Decimal` (INV‑003) y el desborde aritmético. Es un dato erróneo, no uno
  ausente, y un presupuesto con un dato erróneo no cumple.
- R2 y R7 sin curva emiten INFO «no aplicable». R2 ya era INFO: solo cambia su texto.

Regla y prueba cambian en el mismo commit; la ERS no cambia. Las pruebas de desborde
(`tests/unit/test_verification.py:526,539`) no cambian, y la del `float` (Tarea 7) afirma
severidad ≥ ERROR.

**Alternativas descartadas.**

| Alternativa | Por qué no |
|---|---|
| Cambiar la ERS a ERROR | Sería modificar un requisito esencial para ajustarlo al código |
| INFO para todo lo inevaluable, `ExpresionInvalida` incluida | Un `float`, una sintaxis rota o un desborde son datos erróneos: bajar a INFO dejaría CUMPLE un presupuesto con datos corruptos (revisión de arquitectura del plan, hallazgo 1) |
| ADVERTENCIA para `ExpresionInvalida` | Admisible por la revisión; se prefiere ERROR porque no cambia ningún veredicto actual |

**Efecto.** Un presupuesto que era NO CUMPLE *solo* por un parámetro o una referencia ausentes
pasa a CUMPLE. Todo presupuesto sin curva gana un INFO de R7, así que los conteos de hallazgos sin
filtrar suben en uno (API, interfaz, sembradores, Excel); ese INFO no lleva `origen_ids` y
`tests/integration/test_auditoria_7_de_7.py:63` lo exime junto a R2. El presupuesto del 7 de 7
tiene curva y todas sus reglas son evaluables, así que no cambia; se comprueba en la Tarea 8.

**Ratificar:** la severidad INFO solo para lo ausente, ERROR para lo inválido, y su efecto sobre
`cumple` y sobre los conteos.

### B.3 INV-004: dos fórmulas de variación que difieren con base nula

**Corrección.** Una sola función, `core.catalog.precios.variacion_relativa`, que importan
`CambioDetectado.variacion` y `core/budget/actualizacion.py`. Política declarada: con precio
anterior 0 devuelve 0, y el registro conserva `precio_anterior = 0`, que distingue ese caso de «no
cambió».

**Alternativa descartada.** Devolver `None`. La columna `variacion` no es nula
(`docs/modelo_datos.md:147`) y cambiar el esquema es una migración, fuera del límite (spec §2).

**Ratificar:** la política de base nula.

### B.4 INV-005: dos registros de rendimiento

**Corrección.** `core.catalog.rendimientos.registrar_rendimiento` construye el contrato y delega en
`Catalogo.registrar_rendimiento` y en `a_rendimiento`. La excepción única ante una ejecución
inexistente es `LookupError`, con el mensaje que orienta al usuario.

**Alternativa descartada.** Unificar en `CatalogoIncompleto`. La API la traduce a 409
(`api/main.py:26-29`) y hoy responde 404 (`tests/integration/test_api_rendimientos.py:82`); una
ejecución que no existe es un recurso ausente, no un catálogo incompleto.

**Ratificar:** que la excepción única sea `LookupError`.

### B.5 INV-013: UC‑01 3a sin cambio de contrato

**Corrección, ruta sin contrato.** `elaborar` separa los ítems cuya partida no tiene composición: no
entran al presupuesto ni al total, van en `ResultadoElaboracion.pendientes` (el tipo es de
`core/budget/`, no un contrato) y el informe los declara con un `Hallazgo` del contrato vigente, de
código `PENDIENTE` y severidad ERROR. `Presupuesto` no cambia (`core/contracts/presupuesto.py:42-47`).
`generar_presupuesto` sigue exigiendo composición: es el paso intermedio (INV‑037, a limitaciones).

**Precondición estricta que se conserva.** `actualizar_precios` (`core/budget/actualizacion.py:151`)
y `generar_escenario` (`core/budget/escenarios.py:95`) llaman a `elaborar` y hoy dependen de que
`elaborar` lance `ValueError` ante un renglón sin composición. Revalorar o simular un presupuesto
no puede perder renglones en silencio, así que ambas exigen composición para todo renglón **antes**
de elaborar y de guardar, con `exigir_composiciones`, la misma comprobación de
`generar_presupuesto`. Cada una tiene su prueba. `scripts/medir_rnf03.py:117` no cambia: pide las
composiciones al catálogo para los mismos códigos que elabora.

**Fuera de C1.** La propuesta de las tres partidas similares (UC‑03) es de `ui/`. La interfaz y la
API piden hoy las composiciones al catálogo, que lanza `KeyError` ante una partida desconocida, así
que 3a no se alcanza de punta a punta: se registra como hallazgo nuevo para C2 y C3.

**Ratificar:** el código `PENDIENTE` con severidad ERROR (un presupuesto incompleto no cumple).

### B.6 INV-069: el protocolo de elaboración en cuatro sitios

**Corrección.** `elaborar` acepta en `plan` una secuencia o una función del presupuesto valorado
(`plan=plan_secuencial`), y absorbe el borrador. Los llamadores migran en commits separados:
`ui/paginas/elaborar.py`, `ui/paginas/componer.py`, `api/rutas/presupuestos.py`,
`scripts/seed_demo.py` y un quinto sitio que el inventario no citaba,
`scripts/generar_resultados_ml.py:158-167`. `actualizar_precios(plan=...)` pasa a aceptar el mismo
tipo (`Sequence[PeriodoPlan] | GeneradorPlan | None`), porque delega en `elaborar`; así
`scripts/generar_resultados_ml.py:187` pasa `plan=plan_secuencial` en vez de calcularlo sobre la
versión anterior.

**Alternativa descartada.** Una función nueva `elaborar_con_plan_secuencial`: sería un segundo punto
de entrada para el mismo hecho.

**Ratificar:** que el punto único sea `elaborar` con `plan` invocable, y la inclusión del quinto
llamador.

### B.7 INV-011: RF‑20 sin implementación, declarado en limitaciones

**Hallazgo al planificar.** RF‑19 tiene capacidad (las reglas paramétricas de `adapters/civil/reglas.py`
se reevalúan) y solo le falta la prueba. RF‑20 **no tiene implementación**: `_comparar`
(`core/budget/actualizacion.py:267-303`) es privado, supone los mismos renglones y no da el
diferencial de cantidad. Aun así, `docs/ERS.md:466` y `docs/plan_pruebas.md:147` lo presentan
como cubierto por una prueba de `tests/unit/test_budget.py` que no existe, y el plan de pruebas lo
marca «verde».

**Corrección (decisión de Eugenio del 2026‑09‑23).** La corrección de INV‑011 aprobada en GC0 dice
«si RF‑20 no tiene implementación, declararlo sin cumplir». C1 no implementa `diferencial.py`, que
sería el tercer comparador del núcleo (junto a `actualizacion._comparar` y
`escenarios.comparar_por_partida`) y no tendría llamador en `ui/` ni en `api/`. En su lugar:

- escribe la prueba de RF‑19 y la de los pasos 1 a 4 de UC‑04, que sí existen;
- corrige el «verde» falso de RF‑20 en `docs/ERS.md` y `docs/plan_pruebas.md` a «no implementado;
  declarado en limitaciones», sin cambiar el texto del requisito;
- agrega RF‑20 a la lista de limitaciones del inventario, §4 (c).

Es una corrección documental dentro de C1, así que INV‑011 se cierra en C1.

**Fuera de C1.** Los flujos alternativos 1a, 2a y 2b de UC‑04 viven en la capa de adaptadores (o no
existen). Se registran como hallazgo nuevo para C2 y C4.

**Ratificado:** por Eugenio el 2026‑09‑23, antes de ejecutar.

### B.8 INV-015: UC‑02 7a, fuera de C1

**Hallazgo al planificar.** «Descartar» hoy es no confirmar la transacción. Eso también deshace los
`CambioPrecio`, contra 7a («se marca como descartada, pero el registro de cambios se conserva»,
`docs/ERS.md:170`). La interfaz no ofrece descartar.

**Corrección (decisión de Eugenio del 2026‑09‑23).** C1 no implementa 7a. En C1, INV‑015 solo
agrega la prueba de UC‑02 2b. El flujo 7a queda como **subtarea de C3** en la fila de INV‑015 del
inventario: una función del núcleo y un botón en la página de actualización, fieles a la ERS
(«se marca como descartada»; el registro de cambios se conserva), que nunca descarten una versión
que no sea la última del presupuesto. La ERS **no** se enmienda para ajustarla al código; la forma
de la marca la fija el plan de C3.

**Alternativa descartada.** Una `descartar_version` en C1 que borre la versión: contradice la ERS,
excede lo aprobado para INV‑015 («una prueba por flujo alternativo»), no tendría llamador hasta C3
y borraría cualquier versión, incluida la base (revisión de arquitectura del plan, hallazgo 2).

**Ratificado:** por Eugenio el 2026‑09‑23, antes de ejecutar.
