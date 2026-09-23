# PLAN_PROTOTIPO — AREN.IA

Continúa a [PLAN_MULTIDOMINIO.md](PLAN_MULTIDOMINIO.md), que cerró 11 de 11 sesiones, y se ejecuta
**antes** de [PLAN_ASISTENTE.md](PLAN_ASISTENTE.md): un asistente que propone composiciones de APU
necesita primero que exista el flujo donde ponerlas, y ese flujo es lo que este plan construye.

**Diseño que lo fundamenta:**
[docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md](docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md).
Las secciones que se citan abajo (§3.1, §3.7…) son de ese documento.

**Cómo se audita:** `uv run python scripts/meta_prototipo.py [--hasta <fase>]`. Una fase se cruza
cuando su `--hasta` está en OK **y** la compuerta quedó anotada en `docs/bitacora/`.

**Qué es AREN.IA.** El prototipo que se entrega a ARENAZA después de la defensa. La «IA» del nombre
son las cuatro piezas de aprendizaje automático que el repositorio ya tiene probadas y que hoy no
están conectadas a ninguna pantalla (§3.7). No se entrena nada nuevo y la compuerta G2 no se
revierte.

---

## 0. Situación de partida

| Hecho | Estado al abrir el sprint |
|---|---|
| `main` | `471b3e2`, etiqueta **`p-base`**, los seis incrementos apilados fusionados |
| Suite | 558 pruebas en verde con `-W error`; ruff limpio; guardia del núcleo OK; `meta_datos.py` 3/3 |
| Worktree | `.claude/worktrees/prototipo`, rama `inc/PLAN-prototipo` |
| Motor | `calcular_apu` aplica FCAS y bono a **toda** línea de mano de obra: el destajo es inexpresable |
| Catálogo | `cargar_composicion()` es el único creador de partidas y **no** es reentrante |
| Interfaz | Ocho páginas, todas de consulta o cálculo; **ninguna compone un APU** |
| Pruebas de interfaz | **Ninguna.** Solo dos smoke tests de importación |
| Aprendizaje automático | Cuatro piezas construidas y **desconectadas** de toda pantalla de composición |
| Referencia de precios | 111 filas curadas de MaPreX en `data/precios/maprex_2026-07/`, en USD con tasa declarada |
| Fuentes normativas | Archivadas en `docs/fuentes/`: LOTTT, convención colectiva 2023, Ley del Seguro Social |

## 1. Principios del sprint

1. **El núcleo se toca una sola vez y con expediente.** El cambio de §3.1 va en su propio commit,
   sin tocar `adapters/` ni `ml/`, precedido por el hallazgo escrito y la decisión D9 al tutor.
2. **La línea base es intocable.** `tests/unit/test_costing.py` y `tests/fixtures/apu_linea_base.py`
   no se modifican en todo el sprint. Si algo los obliga a cambiar, el sprint se detiene.
3. **La lógica vive fuera de `render()`.** Todo lo que no sea pintar widgets va en `ui/composicion.py`,
   que se prueba sin Streamlit.
4. **Nada de la IA bloquea.** Las cuatro ayudas sugieren o avisan; quien hace el análisis decide.
5. **El rendimiento se exige, no se supone** (§3.3). No hay valor por defecto que pase en silencio.
6. **Los datos simulados se declaran.** El corpus de P4.3 nunca alimenta `ml/` ni cuenta para G2.

## 2. Compuertas y criterios de degradación

| Compuerta | Se cruza cuando | Degradación declarada |
|---|---|---|
| **GP0** (tras P0.2) | ERS y diseño aprobados; D9 planteada al tutor con su fundamento normativo | Si el tutor rechaza D9: el prototipo se entrega sin destajo, la imposibilidad queda como hallazgo y la modalidad pasa a trabajo futuro. El resto del alcance no depende de ella |
| **GP1** (tras P3.2) | Componiendo a mano las cinco partidas de la línea base sale **1 586,61 USD** y la auditoría detecta **7 de 7** | Si se mueve aunque sea 0,01, se revierte el cambio al núcleo y se pasa al sueldo sintético fuera del núcleo, con el precedente de `scripts/seed_telecom.py` |
| **GP2** (tras P4.3) | Pruebas de interfaz verdes en Linux y Windows dentro de la CI existente | Si `pytest -W error` las hace inviables: primero un `filterwarnings` acotado; si no alcanza, van detrás de marcador en un job aparte, con la pérdida de cobertura declarada y el guión manual de P4.2 absorbiéndola |

---

## Fase P0 — Documentar antes de tocar (2 sesiones)

*Definition of Ready:* `p-base` etiquetada y la suite en verde.

### Sesión P0.1 — ERS, casos de uso nuevos y las fuentes

**Lecturas.** spec §1, §3.3, §5; `docs/ERS.md` (RF‑16 y familia); `docs/dossier_g0.md` §D4 y §D5;
`docs/fuentes/`.

```
Agrega a docs/ERS.md los casos de uso UC-10 (componer una partida desde la interfaz) y UC-11
(editar una partida ya compuesta), con sus requisitos funcionales numerados a continuacion del
ultimo existente. Incluye el requisito de que el sistema NO persiste una composicion cuyo
rendimiento no haya sido declarado explicitamente junto con sus condiciones, y el de que la
modalidad de mano de obra es por linea. Marca RF-16 como satisfecho por UC-10.

Crea docs/fuentes/README.md: una ficha por documento archivado con su Gaceta, fecha, de donde se
descargo, y que articulo o clausula del spec lo cita. Anota las dos salvedades del spec: el PDF de
la convencion colectiva vino de un host privado y hay que cotejarlo con una copia oficial, y el
dominio leyes.io redirige hoy a un dominio de spam y no se cita.

Transcribe la nota de campo del profesional de presupuestos a
docs/fuentes/2026-09-16-nota-practica-apu.md: fecha, medio, rol del informante sin su nombre,
y el texto literal. Encabezala declarando que es una comunicacion personal, que en APA se cita en
el texto y no en la lista de referencias, y que su papel es testimoniar que la modalidad del
articulo 114 de la LOTTT se usa en obra, no probar su existencia.
```

**Cierre.** UC‑10 y UC‑11 en la ERS con sus RF; `docs/fuentes/README.md` con una ficha por documento;
la nota transcrita con su encabezado metodológico.
**Fuente única.** La ERS para los requisitos; `docs/fuentes/README.md` para la procedencia documental.
**Commit.** `docs(ers): casos de uso de composicion y edicion de partidas`

---

### Sesión P0.2 — Arquitectura, metas del sprint y la decisión D9

**Lecturas.** spec §3.1, §4, §5, §8; `docs/arquitectura.md`; `scripts/meta_asistente.py` (patrón de
meta con `--hasta`); `CLAUDE.md` §5 y §9.

```
Crea scripts/meta_prototipo.py copiando el patron de scripts/meta_asistente.py: metas P1 a P12 con
--hasta por fase, y su prueba en tests/unit/test_meta_prototipo.py. Las metas son las de la seccion
6 del spec mas una que falla si algo de ml/ referencia el corpus simulado de P4.3.

Agrega a docs/arquitectura.md la vista de la pagina de composicion: que ui/composicion.py es logica
pura probada sin Streamlit, que ui/paginas/componer.py solo pinta, y que las cuatro ayudas de
aprendizaje automatico se invocan desde ui/ con importacion perezosa, nunca desde core/.

Escribe docs/bitacora/2026-09-16-P0-hallazgo-destajo.md: el contrato LineaManoObra no puede
expresar el salario por unidad de obra que tipifica el articulo 114 de la LOTTT y que regula la
clausula 1 de la convencion colectiva de la construccion 2023. Cita ambos textos desde
docs/fuentes/. Explica por que la hipotesis central no se ve afectada: dice que el nucleo no cambia
al agregar un DOMINIO, y una modalidad salarial no es un dominio.

Agrega la decision D9 a docs/dossier_g0.md con ese fundamento y las cuatro opciones evaluadas, y
actualiza D4 con el hallazgo de que el FCAS de 600 por ciento no tiene fuente normativa publicada:
los valores publicados son 198 a 293 por ciento (Chacin 2008) y 78 a 2386 por ciento segun hipotesis
(Dodi y Salas 2019). Recomienda declararlo parametro configurable del caso de estudio.
```

**Cierre.** **Compuerta GP0**: `meta_prototipo.py --hasta P0` en OK; D9 y D4 en el dossier con sus
citas; bitácora del hallazgo escrita. **No se toca `core/` hasta que esto esté.**
**Fuente única.** `docs/dossier_g0.md` para las decisiones; `scripts/meta_prototipo.py` para el avance.
**Commit.** `docs(g0): decision d9 sobre la modalidad de mano de obra y meta del sprint`

---

## Fase P1 — Núcleo y catálogo (2 sesiones)

*Definition of Ready:* GP0 cruzada.

### Sesión P1.1 — Modalidad de mano de obra

**Lecturas.** spec §3.1; `core/contracts/apu.py`; `core/costing/motor.py`;
`tests/unit/test_costing.py` (**solo leer**); `tests/fixtures/apu_linea_base.py` (**solo leer**).

```
TDD, rojo antes que verde. Escribe primero en tests/unit/test_costing_destajo.py estas pruebas:
que una linea a destajo entra completa sin FCAS ni bono ni division entre el rendimiento; que
total_obreros excluye las lineas a destajo; que una composicion mixta suma ambos bloques; que
construir LineaManoObra sin modalidad da JORNAL; y una prueba de caracterizacion que recalcula las
cinco partidas de la linea base y exige el mismo precio unitario que antes, al ultimo decimal.
Corre y verifica que fallan por ImportError.

Despues agrega ModalidadManoObra a core/contracts/apu.py y la rama en core/costing/motor.py segun
el spec 3.1. El campo modalidad va ultimo y con valor por defecto JORNAL, para no romper ninguna
construccion posicional. Documenta en el docstring de LineaManoObra que bajo DESTAJO el campo
sueldo es el precio por unidad de partida, no un sueldo.

NO modifiques tests/unit/test_costing.py ni tests/fixtures/apu_linea_base.py. Este commit toca
solo core/: nada de adapters/ ni de ml/, para que la guardia del nucleo pase.
```

**Cierre.** Las pruebas nuevas en verde; `test_costing.py` verde **sin una sola modificación**;
`uv run python scripts/guardia_nucleo.py --base p-base` en OK.
**Fuente única.** `core/contracts/apu.py` para la enumeración; `core/costing/motor.py` para la fórmula.
**Commit.** `feat(core): modalidad de mano de obra por linea, jornal o destajo`

---

### Sesión P1.2 — Catálogo: reemplazo, lista MaPreX y rendimientos sembrados

**Lecturas.** spec §3.3, §3.4, §3.6; `core/catalog/repositorio.py`; `core/catalog/precios.py`;
`core/catalog/rendimientos.py`; `data/precios/maprex_2026-07/README.md`; `scripts/seed.py`.

```
TDD. Agrega Catalogo.reemplazar_composicion(composicion, lista, dominio, fecha_rendimiento) en
core/catalog/repositorio.py: misma resolucion de insumos que cargar_composicion, pero borra las
lineas anteriores de la partida y registra un rendimiento NUEVO en vez de pisar el anterior. Lanza
LookupError si la partida no existe. No hace commit: eso es de la interfaz. Pruebas en
tests/integration/test_persistencia.py: reemplazar dos veces funciona, el historico de rendimientos
conserva ambos, y reemplazar una partida inexistente lanza LookupError.

Crea scripts/lista_maprex_usd.py: lee los cuatro referencia_*.csv y escribe
data/precios/maprex_2026-07/lista_maprex_usd.csv en el formato canonico tipo,insumo,unidad,precio
con la columna precio_usd. Determinista y reejecutable. Su prueba verifica el numero de filas y que
todo precio es Decimal positivo leido desde texto.

Extiende scripts/seed.py para registrar los cinco rendimientos de la linea base como ESTIMADO con
sus condiciones declaradas, de modo que proponer_rendimiento tenga algo que proponer desde el
primer dia.
```

**Cierre.** `reemplazar_composicion` con sus tres pruebas en verde; la lista en USD generada y
verificada; los cinco rendimientos sembrados; `core/` sin cambios respecto a P1.1 salvo el
repositorio.
**Fuente única.** `scripts/lista_maprex_usd.py` deriva la lista; los precios no se transcriben nunca.
**Commit.** `feat(catalog): reemplazo de composicion y lista de precios maprex en usd`

---

## Fase P2 — La pantalla (4 sesiones)

*Definition of Ready:* P1 cerrada.

### Sesión P2.1 — Funciones puras de composición

**Lecturas.** spec §3.2, §3.3; `ui/paginas/escenarios.py` (el helper `_decimal` y el patrón de
`st.data_editor`); `core/contracts/apu.py`.

```
TDD. Crea ui/composicion.py con funciones puras, sin importar streamlit:
- composicion_desde_tablas(codigo, descripcion, unidad, rendimiento, filas_materiales,
  filas_equipos, filas_mano_obra) -> ComposicionAPU, convirtiendo texto a Decimal y descartando
  filas vacias.
- item_desde_cantidad(codigo, descripcion, unidad, cantidad, origen_id) -> ItemComputo con
  origen_tipo MANUAL.
- Un error de dominio propio, ComposicionInvalida(ValueError), con el campo culpable en el mensaje.
Reusa el helper _decimal de escenarios.py moviendolo aqui y dejando escenarios.py importandolo, para
no duplicar la conversion.

Pruebas en tests/unit/test_composicion.py: una tabla valida produce la composicion esperada; una
cantidad no numerica lanza ComposicionInvalida nombrando el campo; las filas vacias se descartan;
un rendimiento cero o negativo se rechaza; una unidad con alias se normaliza.

Agrega "ui" a los paquetes que tests/unit/test_arquitectura.py vigila, si no esta.
```

**Cierre.** `ui/composicion.py` con sus pruebas en verde y sin importar streamlit; `escenarios.py`
sigue funcionando con el helper compartido.
**Fuente única.** `ui/composicion.py` para la conversión tablas → contrato.
**Commit.** `feat(ui): funciones puras de composicion de apu`

---

### Sesión P2.2 — Las tres tablas y el desglose en vivo

**Lecturas.** spec §3.2, §3.3; `ui/paginas/escenarios.py`; `ui/paginas/catalogo.py`; `ui/app.py`.

```
Crea ui/paginas/componer.py con render() delgado: cabecera de la partida (codigo, descripcion,
unidad) y tres st.data_editor con num_rows dinamico para materiales, equipos y mano de obra. La
columna de materiales se rotula "Consumo por unidad" y el campo de la partida "Rendimiento -
unidades por dia": nunca la misma palabra para las dos cosas. La tabla de mano de obra lleva
columna Modalidad con jornal o destajo.

El rendimiento se precarga con core.catalog.rendimientos.proponer_rendimiento y se muestra
advertencia_rendimiento si la hay, pero el campo de condiciones es obligatorio: sin el, el boton de
guardar queda deshabilitado.

El desglose se recalcula en cada cambio llamando a calcular_apu sobre la composicion en memoria y
se muestra con st.metric: materiales, equipos, mano de obra, costo directo, con administracion y
precio unitario. No hace falta guardar nada para verlo.

Guardar llama a cargar_composicion o a reemplazar_composicion segun exista la partida, y hace el
commit de la sesion, como ui/paginas/actualizacion.py. Registra la pagina en ui/app.py y agrega
ui.paginas.componer a tests/unit/test_ui_importable.py.
```

**Cierre.** La página compone, calcula en vivo, guarda y edita; `test_ui_importable.py` la incluye;
no se puede guardar sin declarar rendimiento y condiciones.
**Fuente única.** `ui/paginas/componer.py` solo pinta; toda la lógica en `ui/composicion.py`.
**Commit.** `feat(ui): pagina de composicion de apu con desglose en vivo`

---

### Sesión P2.3 — Buscador MaPreX y autocompletado de depreciación

**Lecturas.** spec §3.4; `data/precios/maprex_2026-07/referencia_*.csv`;
`core/verification/` (la regla R6).

```
Agrega a ui/composicion.py la funcion buscar_referencia(texto, tipo) -> list[FilaReferencia], que
lee los cuatro referencia_*.csv y filtra por coincidencia en la descripcion normalizada.
FilaReferencia es un dataclass con descripcion, unidad, precio_usd, factor_depreciacion, bono_usd y
ref_maprex. Los precios se leen como Decimal desde texto, nunca como float. Pruebas: una busqueda
conocida devuelve la fila esperada con su ref_maprex; una busqueda sin resultados devuelve lista
vacia; el factor de depreciacion solo viene lleno en filas de equipos.

En ui/paginas/componer.py, un buscador junto a cada tabla rellena la fila elegida. Para equipos
rellena tambien el factor de depreciacion, que es lo que impide que R6 dispare por dos usuarios
tecleando 0,20 y 0,25 para el mismo equipo. El precio queda editable: MaPreX es referencia de
mercado, no verdad, y quien presupuesta puede sobreescribirlo con su cotizacion.

La lista de precios que se use al guardar declara en su campo origen la procedencia y la tasa
declarada de la referencia.
```

**Cierre.** El buscador rellena las tres tablas; la depreciación se autocompleta para equipos; una
prueba de integración compone dos partidas con el mismo equipo y verifica que R6 no emite hallazgo.
**Fuente única.** `referencia_*.csv`; ninguna descripción ni precio se transcribe al código.
**Commit.** `feat(ui): buscador de la referencia maprex con autocompletado de depreciacion`

---

### Sesión P2.4 — Las cuatro ayudas de AREN.IA

**Lecturas.** spec §3.7; `ui/paginas/similares.py` (el patrón de importación perezosa);
`ml/normalization/`; `ml/anomaly/`; `ml/prediction/`.

```
Conecta a ui/paginas/componer.py las cuatro ayudas, todas como sugerencia y ninguna bloqueante,
invocadas desde ui/ con importacion perezosa como hace ui/paginas/similares.py, para que la
interfaz siga arrancando sin el extra ml:

1. Al escribir la descripcion de la partida, ofrecer composiciones de partidas similares del
   catalogo para partir de algo en vez de una tabla vacia.
2. Al teclear un precio, avisar si es atipico respecto al historico del insumo.
3. El rendimiento propuesto con su dispersion, ya cableado en P2.2: aqui solo se le agrega la
   lectura de ml/anomaly cuando hay observaciones suficientes.
4. Al terminar la composicion, contrastar el precio unitario obtenido contra la estimacion por
   reglas, mostrando el marco AACE del resultado.

Ninguna de las cuatro modifica la composicion por su cuenta ni impide guardar. Ninguna toca core/.
Las pruebas van en tests/unit/test_composicion_ia.py y usan dobles, no el modelo real, para no
depender de la descarga de pesos.
```

**Cierre.** Las cuatro ayudas visibles y no bloqueantes; la página arranca sin el extra `ml`
instalado; `git diff p-base --stat -- core/` sin cambios desde P1.1.
**Fuente única.** `ml/` para los modelos; `ui/paginas/componer.py` solo los consulta.
**Commit.** `feat(ui): ayudas de aprendizaje automatico en la composicion de apu`

---

## Fase P3 — El flujo completo (2 sesiones)

*Definition of Ready:* P2 cerrada.

### Sesión P3.1 — Presupuesto, auditoría y Excel

**Lecturas.** spec §4; `core/budget/presupuesto.py`; `core/budget/curva.py`; `core/budget/excel.py`;
`ui/paginas/elaborar.py`; `ui/paginas/actualizacion.py` (el patrón de descarga).

```
En ui/paginas/componer.py, tras guardar partidas, permitir asignarles cantidades de obra y elaborar:
llamar a elaborar() con plan_secuencial para que la curva cierre y R2 y R7 queden limpias, mostrar
el informe de auditoria con a_markdown, y exportar con exportar_excel y st.download_button copiando
el patron de ui/paginas/actualizacion.py.

Agrega la columna Modalidad a la tabla de mano de obra de la hoja APU en core/budget/excel.py, y
actualiza la prueba que verifica las cuatro hojas. Agrega tambien el boton de Excel a
ui/paginas/elaborar.py, que hoy no lo tiene.
```

**Cierre.** De componer a Excel sin salir de la aplicación; la hoja APU muestra la modalidad; las
cuatro hojas verificadas por prueba.
**Fuente única.** `core/budget/excel.py` es el único sitio donde se redondea a dos decimales.
**Commit.** `feat(ui): presupuesto auditado y exportacion desde la composicion`

---

### Sesión P3.2 — Caso de demostración y regresión de la línea base

**Lecturas.** spec §6; `tests/fixtures/apu_linea_base.py` (**solo leer**); `docs/linea_base.md`.

```
Escribe tests/integration/test_composicion_extremo_a_extremo.py con dos pruebas:

1. Regresion. Componiendo las cinco partidas de la linea base a traves de
   ui.composicion.composicion_desde_tablas y elaborando el presupuesto, el total es 1 586,61 USD y
   la auditoria devuelve los 7 hallazgos esperados. Los datos de entrada se leen del fixture: no se
   transcribe ni un numero.

2. Demostracion. Un presupuesto construido para la demostracion, que no proviene de obra ejecutada,
   que ejercita jornal y destajo en la misma partida, materiales con desperdicio, equipos con
   depreciacion, curva y las cuatro hojas de Excel.

Crea scripts/seed_demo.py que deje esa misma demostracion cargada en la base para poder abrirla en
la interfaz. Declara en su docstring que es un caso didactico, no una obra ejecutada.
```

**Cierre.** **Compuerta GP1**: la regresión da 1 586,61 USD y 7 de 7; la demostración ejercita las
dos modalidades; `meta_prototipo.py --hasta P3` en OK.
**Fuente única.** `tests/fixtures/apu_linea_base.py`, que no se modifica.
**Commit.** `test(integration): composicion de extremo a extremo y regresion de la linea base`

---

## Fase P4 — Pruebas (3 sesiones)

*Definition of Ready:* GP1 cruzada.

### Sesión P4.1 — Las primeras pruebas de interfaz del repositorio

**Lecturas.** spec §6, §8; `tests/unit/test_ui_importable.py`; `.github/workflows/ci.yml`;
`pyproject.toml` (marcadores de pytest).

```
Crea tests/unit/test_ui_componer.py usando streamlit.testing.v1.AppTest (Streamlit 1.62.0, ya
verificado): abrir la pagina, llenar las tres tablas, disparar el calculo y verificar el precio
unitario mostrado; y una segunda prueba de que sin rendimiento declarado el boton de guardar esta
deshabilitado.

La suite corre con -W error. Si Streamlit emite avisos propios, agregar entradas acotadas de
filterwarnings en pyproject.toml, una por aviso, con un comentario que diga cual es y por que se
silencia. Si resultara inmanejable, marcar las pruebas con un marcador nuevo y correrlas en un job
aparte de la CI, documentando la perdida de cobertura en docs/plan_pruebas.md.

Actualiza docs/plan_pruebas.md con la fila de UC-10 y UC-11 en la matriz.
```

**Cierre.** Pruebas de interfaz en verde localmente y en la CI, en Linux y Windows; la matriz IEEE
829 cubre los dos casos de uso nuevos.
**Fuente única.** `docs/plan_pruebas.md` para la matriz requisito → prueba → resultado.
**Commit.** `test(ui): primeras pruebas automatizadas de la interfaz con apptest`

---

### Sesión P4.2 — Siembra de demostración y guión de prueba manual

**Lecturas.** `docs/plan_pruebas.md`; `docs/manual_usuario.md`; `scripts/seed_demo.py` de P3.2.

```
Extiende scripts/seed_demo.py para dejar la base lista de punta a punta: catalogo con insumos de la
referencia MaPreX en USD, varias partidas ya compuestas, los rendimientos sembrados y un presupuesto
de ejemplo. Un solo comando y la aplicacion esta lista para abrirse.

Escribe docs/guion_prueba_arenia.md al estilo IEEE 829: casos de prueba manuales numerados, con
precondicion, pasos, resultado esperado y espacio para el resultado obtenido. Cubre componer una
partida desde cero, editarla, un destajo, un rendimiento fuera de rango que dispara la advertencia,
exportar a Excel y leer el informe de auditoria. Es el guion que se le entrega a quien pruebe
AREN.IA.
```

**Cierre.** `uv run python scripts/seed_demo.py` deja la aplicación lista; el guión cubre los seis
recorridos con resultado esperado explícito.
**Fuente única.** `docs/guion_prueba_arenia.md` para el protocolo manual.
**Commit.** `docs(pruebas): siembra de demostracion y guion de prueba manual de arenia`

---

### Sesión P4.3 — Corpus simulado y su cuarentena

**Lecturas.** spec §6; `scripts/simular_lista.py` (el patrón determinista);
`scripts/meta_datos.py`; `docs/resultados_ml.md`.

```
Crea scripts/simular_corpus.py: genera N composiciones de APU con semilla determinista, al modo de
scripts/simular_lista.py, para probar la interfaz con volumen. Su docstring declara que el corpus es
simulado, que no proviene de obra ejecutada y que no cuenta para ninguna compuerta.

Agrega a scripts/meta_prototipo.py una meta que FALLA si algun modulo de ml/ referencia el corpus o
el script que lo genera, y su prueba. La compuerta G2 sigue cruzada con degradacion a reglas: el
corpus no la revierte ni la toca.

Verifica que scripts/meta_datos.py sigue en 3 de 3 con la documentacion nueva del sprint.
```

**Cierre.** **Compuerta GP2**: pruebas de interfaz verdes en los dos sistemas; la meta de cuarentena
falla si alguien cablea el corpus a `ml/`; `meta_datos.py` 3/3.
**Fuente única.** `scripts/simular_corpus.py`, declarado sintético en su propio docstring.
**Commit.** `feat(scripts): corpus simulado para pruebas de volumen, en cuarentena`

---

## Fase P5 — Cerrar (1 sesión)

### Sesión P5.1 — Modo entrega, bitácora y manuales

**Lecturas.** `ui/app.py`; `docs/manual_usuario.md`; `docs/manual_tecnico.md`;
`docs/bitacora/2026-09-02-sprint-multidominio.md` (formato de cierre de sprint).

```
Agrega a ui/app.py un modo de entrega: una constante o variable de entorno que filtra la navegacion
para mostrar solo lo que AREN.IA necesita (composicion, elaborar, catalogo, actualizacion de precios,
historico) y ocultar las pantallas de investigacion (visor 3D, similares, simulador, escenarios).
Por defecto se muestran todas; el modo entrega es opcional.

Actualiza docs/manual_usuario.md con el recorrido de composicion y docs/manual_tecnico.md con la
modalidad de mano de obra y el contrato nuevo.

Escribe docs/bitacora/2026-09-16-sprint-prototipo.md con el cierre del sprint: las tres compuertas
con su evidencia, el cambio al nucleo y su expediente, los hallazgos, y que queda pendiente del
tutor. Regenera docs/api.json si cambio.
```

**Cierre.** `meta_prototipo.py` en 12/12; suite completa verde; ruff limpio;
`guardia_nucleo.py --base p-base` en OK; bitácora escrita.
**Fuente única.** La bitácora del sprint para el registro; los manuales para el uso.
**Commit.** `docs: cierre del sprint del prototipo arenia`

---

## Resumen del recorrido

| Fase | Sesiones | Producto | Depende de |
|---|---|---|---|
| **P0** | 2 | ERS con UC‑10 y UC‑11, fuentes archivadas, D9 y D4 al tutor, meta del sprint | `p-base` |
| **P1** | 2 | Modalidad de mano de obra en el núcleo; reemplazo de composición; lista MaPreX en USD | GP0 |
| **P2** | 4 | La pantalla de composición, con buscador de referencia y las cuatro ayudas de AREN.IA | P1 |
| **P3** | 2 | De componer a Excel, auditado; regresión de la línea base | P2 |
| **P4** | 3 | Primeras pruebas de interfaz, siembra de demostración, guión manual, corpus en cuarentena | GP1 |
| **P5** | 1 | Modo entrega, manuales y bitácora | P4 |

## Los tres momentos que definen el sprint

1. **GP0**: la decisión D9 sale hacia el tutor con el artículo 114 de la LOTTT detrás. Es el momento
   en que una nota de campo se convierte en un hallazgo de investigación.
2. **GP1**: componiendo a mano sale 1 586,61 USD. Es la prueba de que la pantalla nueva no le cambió
   una coma al motor.
3. **GP2**: el repositorio tiene, por primera vez, pruebas que ejercitan su interfaz.
