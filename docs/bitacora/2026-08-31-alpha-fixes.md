# Bitácora — Oleada de correcciones de la revisión final del sprint alpha

**Fecha:** 2026‑08‑31 · **Rama:** `inc/alpha-fixes` · **Base:** `16f61e6` (sprint alpha fusionado,
12/12 metas, 295 pruebas) · **Compuertas cruzadas:** ninguna (G0, G1 y G2 siguen abiertas)

## Objetivo

Corregir los diez ítems que el revisor final dejó abiertos (3 *Important* y 7 *minors* promovidos)
antes de etiquetar `alpha-0.1`, sin tocar `core/contracts/` ni la línea base, y dejando la meta
`scripts/meta_alpha.py` en 12/12 con una evidencia de M9 más fuerte que la que tenía.

## Qué se corrigió, ítem por ítem

| # | Archivo:línea | Corrección |
|---|---|---|
| 1 | `adapters/civil/tabular.py:118-124` | El balance de relleno rechaza con `ValueError` una segunda zanja de diámetro distinto. El `factor_volumen_tuberia` que se escribe en la expresión de R5 es el de la **última** fila de zanja, mientras `volumen_tuberia_total` sí acumula fila por fila: con dos diámetros R5 comparaba la cantidad contra un volumen de tubería que no era el suyo (ERROR falso). Prueba nueva, más la del balance con dos zanjas del mismo diámetro y la del relleno sin zanja (el *minor* diferido de T4) |
| 2 | `core/catalog/mapeo.py:3`, `core/models/entidades.py:6`, `core/catalog/repositorio.py:7` | Los tres docstrings decían «único»/«ninguna conversión» donde el ADR 12 y `docs/modelo_datos.md §634` dicen «exactamente dos» (`mapeo.py` y `budget/persistencia.py`). `repositorio.py` precisa además que la única fila que construye por su cuenta, `models.PrecioInsumo` de `_fijar_precio`, no traduce ningún contrato |
| 3 | `scripts/meta_alpha.py` (`estado_nucleo_intacto`, `_ramas_adaptador`), `README.md:10` | M9 añade a la regla por commit el `git diff core/` del **rango completo** de cada rama que incorpora un dominio. Cierra el agujero señalado: un commit de una rama de adaptador que tocara **solo** `core/` no lo lista `git log -- adapters ml` y era invisible |
| 4 | `core/catalog/precios.py:238-247` | `_a_precio` valida `not precio.is_finite() or precio < 0`: `Decimal("nan") < 0` lanzaba `InvalidOperation` (un `ArithmeticError`) fuera del `except`, y `Decimal("Infinity")` entraba en silencio. El mensaje cita archivo y fila, como promete el docstring de `leer_lista_precios` |
| 5 | `ui/app.py:160` | La cláusula pasa a `(LookupError, ValueError, ArithmeticError, SQLAlchemyError)`: el `IntegrityError` del segundo clic con el mismo código de presupuesto y la `InvalidOperation` del ítem 4 salían como traza cruda en Streamlit |
| 6 | `tests/integration/test_auditoria_7_de_7.py:68-70` | Borrado el `pytest.importorskip("core.budget")` + `hasattr(budget, "generar_curva")`: hoy convertirían una regresión del núcleo en un *skip* silencioso justo en la prueba del indicador 1 |
| 7 | `core/catalog/mapeo.py:61` | Un material sin unidad es `CatalogoIncompleto` citando código y descripción, como sus ramas vecinas, en vez del `ValueError` anónimo de `normalizar_unidad("")` |
| 8 | `core/budget/actualizacion.py` (`_registrar_incidencias`, `_partidas_por_insumo`) | `_registrar_incidencias` es idempotente con el mismo patrón que `registrar_cambios`, y `_partidas_por_insumo` no repite una partida que lleve el mismo insumo en dos líneas de su composición |
| 9 | `docs/arquitectura.md §5` | La estación de modelado BIM, el IFC y `tanquilla.ifc` quedan marcados *PREVISTO* y con arista punteada (G1 abierta), con un párrafo que lo dice en prosa; y la regla de `.gitignore` es `*.db`, no `data/*.db` |
| 10 | `data/samples/telecom/README.md` | La procedencia «90/80 m de bobina» era falsa; ver *Hallazgos* |

## Decisiones

| Decisión | Motivo |
|---|---|
| El ítem 1 se resuelve **declarando el límite** (un solo diámetro por fuente cuando hay balance), no con un término por diámetro | Un término por diámetro exige un código de partida de tubería por diámetro, y el catálogo del alpha tiene uno solo. El límite se declara en el docstring de `AdaptadorCivilTabular` y en la prueba, como pide la revisión |
| M9 evalúa por rama solo las fusiones **de la línea principal** cuyo rango **agrega** archivos bajo `adapters/` o `ml/` | Es la formulación literal de la hipótesis de NORMAS.md §1 («el núcleo no cambia **cuando se agrega un dominio**») y produce exactamente las cuatro ramas de los cuatro adaptadores. Una fusión de `main` *hacia dentro* de una rama en curso tiene los papeles invertidos y su rango no es lo que la rama introdujo (`0aa7e60` lo demostró en la primera versión); una rama que solo *modifica* un adaptador ya existente no es la incorporación de un dominio y la cubre la regla por commit |
| **Dos commits** en vez de uno | Ver *Impedimentos* |
| El ítem 5 no lleva prueba | Es UI, y el proyecto no prueba la capa de presentación. Verificación manual registrada abajo |
| Se corrige `README.md:10` pero **no** `docs/bitacora/2026-08-29-sprint-alpha.md:47` | El cierre del sprint lo firma el integrador; la redacción de esa bitácora la ajusta él si quiere. `README.md` sí describe el sistema vigente |

### Verificación manual del ítem 5 (sin prueba, por diseño)

1. `import ui.app` con la cláusula nueva: la línea queda
   `except (LookupError, ValueError, ArithmeticError, SQLAlchemyError)`.
2. `issubclass(decimal.InvalidOperation, ArithmeticError)` → `True`;
   `issubclass(IntegrityError, SQLAlchemyError)` → `True`.
3. Reproducido el segundo clic: dos `actualizar_precios` seguidos con el mismo `codigo_nuevo` sobre
   una SQLite en memoria lanzan `IntegrityError`, que **no** era `(LookupError, ValueError)` y sí es
   `SQLAlchemyError`. Antes salía como traza; ahora es un `st.error`.

## Hallazgos

1. **La procedencia telecom «90/80 m de bobina» era falsa (ítem 10).** Leídos los dos PDF con el
   Python global (`python -c "import fitz; ..."`, reconstruyendo las filas por coordenada `y`): los
   90 y los 80 son **metros de «Tubo Corrugado Flexible 1 Pulgada»** —canalización, no cable—,
   renglón 3 de `Presupuesto_1_ARENAZA.pdf` y renglón 5 de `Presupuesto_2_ARENAZA.pdf`, la única
   partida medida en metros de los dos documentos. El cable UTP se compra **por bobina, en piezas**:
   cada presupuesto lleva «BOBINA CABLE UTP CAT 6 (300 M)» y «Bobina Cable Utp Cat6 305 m Int», del
   orden de 605 m disponibles. Corregido el README de la muestra; el supuesto de los 95 m repartidos
   entre los cinco enlaces se mantiene, ahora contrastado contra la canalización de 90 m.
2. **Inconsistencia en la fuente primaria de telecom.** Ese mismo renglón de tubo corrugado dice
   **80 m en los cómputos métricos y 90 m en el presupuesto** de `Presupuesto_2_ARENAZA.pdf`
   (99,75 × 3 tubos de 30 m = 299,25 USD). Es exactamente el tipo de desvío que persiguen las siete
   reglas: queda anotado en el README de la muestra, no corregido, y es candidato a caso de prueba
   de R7 cuando el dominio telecom llegue a presupuesto.
3. **`composicion_apu` no tiene clave única (partida, insumo).** Nada impide repetir un insumo en
   dos líneas de la misma partida; sin eso, `_partidas_por_insumo` registraba dos incidencias
   idénticas para el mismo cambio de precio (ítem 8). Se resolvió en el código, no en el esquema: una
   restricción única cerraría la puerta a un desglose legítimo (el mismo insumo en dos usos de la
   partida). Candidato a revisar en el modelo de datos si aparece un caso real.
4. **El agujero de M9 era estructural, no un descuido.** `git log -- adapters ml` filtra por ruta y
   por eso jamás puede ver un commit que solo toque `core/`. Ninguna regla por commit podía cerrarlo;
   hacía falta cambiar la unidad de análisis a la rama. Las cuatro ramas de adaptador del sprint
   (`inc/I3.2-civil`, `inc/I5-industrial`, `inc/I5-sistemas`, `inc/I5-telecom`) dan `git diff core/`
   vacío, que es la evidencia que NORMAS.md §1 le atribuye a la hipótesis central.
5. **Ninguna insuficiencia nueva de `core/contracts/`.** Los diez ítems se corrigieron sin tocar los
   contratos.

## Impedimentos

- **Un solo commit era incompatible con M9 en verde.** El despacho pedía un único commit
  `fix: correcciones de la revision final del sprint alpha`, pero el ítem 1 cambia
  `adapters/civil/tabular.py` y los ítems 2, 4, 7 y 8 cambian `core/`: un commit con ambas cosas es
  precisamente lo que M9 marca como conflictivo, y `meta_alpha.py` habría reportado 11/12 desde el
  primer momento posterior al commit (comprobado). Se separó en dos: `fix(civil): …` con el
  adaptador y sus pruebas, y `fix: correcciones de la revision final del sprint alpha` con todo lo
  demás. La historia queda diciendo la verdad —el arreglo del adaptador no necesitó tocar el
  núcleo— y M9 se mantiene en OK. Si el integrador prefiere aplastarlos, M9 pasará a FALLA.
- El README raíz está en la lista de archivos compartidos que edita el integrador, pero el ítem 3 de
  la revisión pide expresamente corregir `README.md:10`; se editó solo esa frase.
