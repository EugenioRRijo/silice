# AREN.IA — prototipo de composición de APU · diseño

**Fecha:** 2026-09-16 · **Rama:** `inc/PLAN-prototipo` · **Base:** etiqueta `p-base` (`471b3e2`)
**Plan que lo ejecuta:** `PLAN_PROTOTIPO.md` (14 sesiones, tres compuertas)

**AREN.IA** es el nombre del prototipo que se entrega a ARENAZA después de la defensa. La «IA» del
nombre no es una promesa a futuro: son las piezas de aprendizaje automático que el repositorio ya
tiene construidas y probadas, y que hoy no están conectadas a ninguna pantalla (sección 3.7).

---

## 1. Por qué existe

El sistema sabe costear un APU, presupuestarlo, auditarlo y exportarlo, pero **no sabe componer
uno**. Las partidas nacen del `seed` o de la carga de composiciones; `Catalogo.cargar_composicion()`
es el único creador de partidas del sistema y solo lo llaman los scripts de siembra. Ninguna de las
ocho páginas de la interfaz permite armar una partida.

Es el hallazgo más recurrente del proyecto: apareció en I2 (RF‑16 no puede persistir la partida
nueva), en I6.2 (UC‑06 no tiene dónde proponer el rendimiento) y en F.2, y está escalado al tutor
como **D5** del dossier G0. Este trabajo lo cierra.

El segundo motivo es externo: el prototipo se entrega a una empresa después de la defensa, así que
tiene que ser usable por un tercero, no solo demostrable.

### Fuente de los requisitos

Una nota de campo de un profesional de presupuestos (comunicación personal, 2026‑09‑16) describe
cómo se arma un APU en la práctica venezolana: tres tablas de insumos, una unidad de cobro por
partida, rendimientos que **los declara quien hace el análisis**, y mano de obra que puede cobrarse
por jornal o por unidad instalada. Esa nota no es la prueba de nada por sí sola —es el testimonio de
que la práctica existe—; el respaldo normativo está en la sección 5.

---

## 2. Alcance

**Entra:** componer una partida desde la interfaz (tres tablas de insumos, unidad, rendimiento),
ver el precio unitario desglosarse en vivo, guardar y **editar** la partida, asignarle cantidades de
obra, generar el presupuesto con su curva, auditarlo con las siete reglas y exportarlo a Excel.
Más: conectar a esa pantalla las cuatro ayudas de aprendizaje automático que ya existen y están
desconectadas (§3.7), las primeras pruebas automatizadas de interfaz del repositorio, un juego de
datos de demostración y un corpus simulado para probar con volumen.

**No entra:** bimoneda real en el motor (se diseña, no se implementa — sección 3.5); endpoints de
API para crear partidas (la interfaz llama a `core` directo, como las ocho páginas existentes);
ETL de libros Excel de MAPREX (el material sucio que describe la nota no está en el repositorio y
el ETL de los PDF ya existe y funciona).

---

## 3. Decisiones de diseño

### 3.1 Modalidad de mano de obra — cambio al núcleo (decisión D9)

**Problema.** `calcular_apu` aplica `(1 + FCAS)` a **toda** línea de mano de obra, suma
`bono × total_obreros` y divide el bloque entero entre el rendimiento. Un destajo de 6 USD/m²
saldría 42 USD más bono. No hay bandera por línea, y `ParametrosCosto` se congela por presupuesto
entero, no por partida.

**Decisión.** `core/contracts/apu.py` gana:

```python
class ModalidadManoObra(StrEnum):
    JORNAL = "jornal"     # sueldo diario: recibe FCAS y bono, se divide entre el rendimiento
    DESTAJO = "destajo"   # precio por unidad de partida: entra completo, sin FCAS ni bono
```

y `LineaManoObra` gana `modalidad: ModalidadManoObra = ModalidadManoObra.JORNAL` como último campo
con valor por defecto, de modo que toda construcción posicional existente sigue siendo válida.

`core/costing/motor.py` parte la mano de obra en dos sumandos:

```
mo_jornal  = ( Σ_jornal cantidad × sueldo × (1+FCAS) + bono × Σ_jornal cantidad ) / rendimiento
mo_destajo = Σ_destajo cantidad × sueldo
mano_obra  = mo_jornal + mo_destajo
```

**Dos invariantes que las pruebas vigilan.** `ComposicionAPU.total_obreros` **excluye** las líneas a
destajo: un subcontratista que cobra por metro no es un obrero que devengue bono de alimentación.
Y con todas las líneas en `JORNAL` el resultado es idéntico al actual hasta el último decimal.

**Verruga declarada.** Bajo `DESTAJO` el campo `sueldo` no significa sueldo sino precio por unidad
de partida. Se prefiere esa ambigüedad documentada a un segundo campo vacío en la inmensa mayoría de
las líneas. Va en el docstring del contrato y en la bitácora.

**Estatuto del cambio.** `CLAUDE.md` §5 declara los contratos estables y §9 ordena detenerse y
documentar antes de parchear el núcleo. Esto es lo segundo, no lo primero: el hallazgo se escribe,
sube al tutor como **D9** y solo entonces se implementa. La hipótesis central del proyecto no se ve
afectada — dice que el núcleo no cambia **al agregar un dominio**, y una modalidad salarial no es un
dominio. `scripts/guardia_nucleo.py` solo falla si un commit toca `core/` junto a `adapters/` o
`ml/`, así que el commit del motor pasa la integración continua.

### 3.2 El doble rendimiento se resuelve con vocabulario, no con lógica

La nota de campo llama «rendimiento» a dos cosas distintas: el consumo de material por unidad de
obra (7,5 sacos de cemento por m³) y la producción por día de una cuadrilla (50 m² instalados). En
el sistema ya son dos campos separados — `LineaMaterial.cantidad` y `ComposicionAPU.rendimiento` —
así que no hay nada que cambiar salvo los nombres en pantalla, que es justo donde se produciría el
error.

La columna de materiales se rotula **«Consumo por unidad»**. El campo de la partida se rotula
**«Rendimiento — unidades por día»**. Nunca la misma palabra para las dos cosas, ni en la interfaz
ni en la hoja de Excel.

### 3.3 El rendimiento se exige, no se supone

No existe ni existirá una tabla de rendimientos: MAPREX cotiza precios, no rendimientos, y el
rendimiento depende de quién ejecute el trabajo. La nota de campo lo dice y el contrato ya lo
modela: `TipoRendimiento.ESTIMADO`, campo `condiciones`, y `referencia_ejecucion` obligatoria para
los medidos.

**Requisito funcional nuevo:** el sistema **no persiste una composición cuyo rendimiento no haya
sido declarado explícitamente junto con sus condiciones.** No hay valor por defecto que pase en
silencio. Los dos caminos que persisten una composición —`cargar_composicion`, que crea la partida
(UC‑10), y `reemplazar_composicion`, que corrige la existente (UC‑11)— exigen las condiciones y
lanzan `ValueError` si vienen vacías; ningún ayudante del mapeo las suple con un valor por defecto.

`core/catalog/rendimientos.proponer_rendimiento()` —escrito en I6.2 y nunca conectado a una
pantalla— precarga la sugerencia, y `advertencia_rendimiento()` muestra la dispersión sin bloquear.
Con menos de dos observaciones la propuesta viene vacía: es el comportamiento correcto y mejora con
el uso. Se siembran los cinco rendimientos de la línea base como estimados con sus condiciones, para
que la pantalla no arranque muda.

### 3.4 MAPREX es referencia de mercado, no verdad

No hay datos de socios comerciales. Las 111 filas curadas de `data/precios/maprex_2026-07/` (tasa
declarada 633,3644 Bs/USD al 01/07/2026) sirven como **sugerencia**: un buscador rellena
descripción, unidad, `precio_usd` y `factor_depreciacion`, y el usuario puede sobrescribir el precio
con una cotización propia. La procedencia queda en `ListaPrecios.origen`.

El autocompletado del factor de depreciación no es comodidad: la regla **R6** compara ese factor
entre partidas, y dos usuarios tecleando 0,20 y 0,25 para la misma retroexcavadora producirían un
error de auditoría legítimo pero evitable.

### 3.5 Moneda: USD, con la puerta abierta

El prototipo opera y muestra USD, como todo el sistema. La bimoneda se diseña y no se implementa:
el punto de entrada está identificado — `Presupuesto` ya congela cuatro parámetros de costo, y
`tasa_cambio` con `fecha_tasa` entrarían ahí el día que hagan falta, más una columna en el
exportador. Queda declarado como extensión prevista, no como omisión.

### 3.6 Guardar y editar

`cargar_composicion()` crea la partida si no existe, pero sigue rechazando con `ValueError` la
partida que ya tiene composición cargada, para no duplicar sus líneas: corregirla es la operación
distinta, `reemplazar_composicion()`. Ambos caminos exigen ahora `condiciones` (§3.3, RF‑33) y
lanzan `ValueError` si vienen vacías, antes de tocar la sesión.

`Catalogo.reemplazar_composicion()` existe en `core/catalog/repositorio.py`, con la misma
resolución de insumos y registrando un rendimiento nuevo en lugar de pisar el anterior.
`core/catalog/` no está entre los contratos congelados de `CLAUDE.md` §5: es trabajo ordinario.
El `commit` lo hace la interfaz, como en `ui/paginas/actualizacion.py`.

### 3.7 La «IA» de AREN.IA: cablear lo que ya existe

El repositorio tiene cuatro piezas de aprendizaje automático construidas, probadas y **desconectadas
de toda pantalla de composición**, porque cuando se escribieron esa pantalla no existía. La
composición manual es exactamente el lugar donde sirven:

| Pieza | Dónde vive | Qué hace al componer |
|---|---|---|
| Partidas similares (UC‑03) | `ml/normalization/` | Al escribir la descripción, propone composiciones de partidas parecidas del catálogo para partir de algo en vez de una tabla vacía |
| Precios atípicos | `ml/anomaly/` | Avisa si un precio tecleado se aparta del histórico del insumo. Nunca impide guardar |
| Propuesta de rendimiento | `core/catalog/rendimientos.py` | Precarga el rendimiento con su dispersión (§3.3) |
| Estimación por reglas | `ml/prediction/` | Contrasta el precio unitario recién compuesto contra la estimación, con el marco AACE |

Ninguna de las cuatro bloquea: todas sugieren o avisan. Esa es la condición de diseño — la persona
que hace el análisis decide, tal como exige §3.3. Y ninguna obliga a tocar `core/`: la pantalla las
invoca desde `ui/`, con importación perezosa para que la interfaz siga arrancando sin el extra `ml`,
como ya hace `ui/paginas/similares.py`.

La compuerta **G2 no se revierte**: la estimación sigue siendo el sistema de reglas con análisis de
sensibilidad declarado como limitación. Cablear no es reentrenar.

---

## 4. Arquitectura

| Archivo | Qué pasa |
|---|---|
| `core/contracts/apu.py` | `ModalidadManoObra`; campo en `LineaManoObra`; `total_obreros` excluye destajo |
| `core/costing/motor.py` | La mano de obra se parte en dos sumandos |
| `core/catalog/repositorio.py` | `reemplazar_composicion()`; `cargar_composicion()` exige las condiciones |
| `core/models/entidades.py` | La línea persistida gana `modalidad` (anulable, como `depreciacion`) |
| `core/catalog/mapeo.py` | La modalidad en la ida y la vuelta; `condiciones` sin valor por defecto |
| `ui/composicion.py` | **Nuevo.** Funciones puras: tablas → `ComposicionAPU`, validación, búsqueda MAPREX |
| `ui/paginas/componer.py` | **Nuevo.** Solo `render()`, delgado |
| `ui/app.py` | Registra la página; filtro de navegación para el modo entrega |
| `ui/paginas/elaborar.py` | Gana el botón de Excel que hoy no tiene |
| `core/budget/excel.py` | La hoja APU gana columna *Modalidad* |
| `scripts/lista_maprex_usd.py` | **Nuevo.** Deriva la lista canónica en USD desde las 111 filas |
| `scripts/simular_corpus.py` | **Nuevo.** Corpus simulado determinista, en cuarentena |
| `scripts/meta_prototipo.py` | **Nuevo.** Audita las metas del sprint |
| `core/verification/`, `core/budget/presupuesto.py`, `core/budget/curva.py` | **Intactos** |

La lógica vive en funciones puras fuera de `render()`, porque hoy el repositorio no tiene ninguna
prueba de interfaz y lo único verificable es lo que se puede llamar sin Streamlit.

### Comportamiento de las siete reglas ante una composición manual

Seis de las siete no producen hallazgos falsos. **R1** emite una advertencia por partida («la
cantidad es manual y no declara la regla que la produjo») que es deliberada y no invalida el
presupuesto. **R4** y **R5** se saltan por completo si no se declaran especificaciones ni balance.
**R2** y **R7** quedan limpias si se pasa `plan=plan_secuencial(borrador)`, como ya hace
`ui/paginas/elaborar.py`. **R6** es el único riesgo real y se mitiga con el autocompletado de §3.4.

---

## 5. Fundamento normativo

Verificado en fuente primaria el 2026‑09‑16.

**El destajo es una modalidad salarial tipificada.** LOTTT, artículo 114 (Gaceta Oficial N.º 6.076
Extraordinario, 7 de mayo de 2012, PDF publicado por el Ministerio del Poder Popular para el Proceso
Social de Trabajo):

> **Salario por unidad de obra, por pieza o a destajo.** Artículo 114. Se entenderá que el salario
> ha sido estipulado por unidad de obra, por pieza o a destajo, cuando se toma en cuenta la obra
> realizada por el trabajador o trabajadora, sin usar como medida el tiempo empleado para
> ejecutarla.

El artículo 112 la enumera entre las formas de estipular el salario; el 116 obliga a hacer constar
el modo de calcularlo; el 121 y el 122 fijan cómo promediarlo para vacaciones y prestaciones.

**La convención colectiva del sector la regula.** Convención Colectiva de Trabajo para la Rama de la
Industria de la Construcción (Gaceta Oficial N.º 6.752 Extraordinario, 6 de julio de 2023),
Cláusula 1: el trabajador por unidad de obra, por pieza o a destajo *«es aquel que ejecuta su
trabajo por metro, por unidad de obra, por pieza o por tarea, cuyo salario o pago no podrá ser
inferior al previsto en el Tabulador de Oficios y Salarios que forma parte de esta Convención»*.

Eso reformula D9. El hallazgo no es «un informante mencionó el destajo», sino: **el contrato del
sistema no puede expresar una modalidad salarial que la ley tipifica y que la convención colectiva
del sector regula.**

**El bono de alimentación no es salario, y eso valida la fórmula vigente.** La Cláusula 20 de la
convención dice que el beneficio *«no tiene carácter salarial, a ningún efecto legal o
contractual»*. El motor ya suma el bono aparte y **no** lo multiplica por el FCAS. La decisión de
diseño resulta estar normativamente respaldada.

**El FCAS de 600 % no tiene fuente normativa (decisión D4).** No lo publican el Colegio de
Ingenieros de Venezuela, la Cámara Venezolana de la Construcción, COVENIN ni MAPREX. Los valores
publicados que sí se encontraron son 198 %–293 % (Chacín, 2008, Universidad Rafael Urdaneta) y
78 %–2 386 % según qué cláusulas se incluyan (Dodi y Salas, 2019, Universidad José Antonio Páez,
cálculo dominado por la hiperinflación de 2018). El CIV sí calcula el FCAS en sus Guías
Referenciales de Costos, pero su página anuncia edición de febrero de 2011 y las guías se compran.
**Resolución propuesta para D4:** el 6,00 se presenta como parámetro configurable de la línea base
del caso de estudio, nunca como valor normativo, citando el rango publicado.

**Salvedades.** El PDF de la convención colectiva provino de un host comercial privado; hay que
cotejarlo contra una copia oficial antes de citarlo en la defensa. El dominio `leyes.io`, primer
resultado de buscador para el artículo 114, hoy redirige a un dominio de spam: no se cita.

---

## 6. Pruebas y criterios de aceptación

| Criterio | Qué mide |
|---|---|
| **Demostración** | Un presupuesto construido para la demostración que ejercite jornal **y** destajo, materiales con desperdicio, equipos con depreciación, curva y las cuatro hojas de Excel |
| **Regresión** | Componiendo a mano las cinco partidas de la línea base desde la pantalla nueva sale **1 586,61 USD** y la auditoría sigue detectando **7 de 7** inconsistencias |
| **Núcleo** | `tests/unit/test_costing.py` verde sin una sola modificación, más una prueba nueva de que jornal‑por‑defecto reproduce el comportamiento anterior |
| **Interfaz** | Pruebas con `streamlit.testing.v1.AppTest` (Streamlit 1.62.0, verificado) verdes en Linux y Windows dentro de la integración continua existente |
| **Arquitectura** | `scripts/guardia_nucleo.py --base p-base` en verde |
| **Datos** | `scripts/meta_datos.py` 3/3; el corpus simulado no es referenciado por `ml/` ni cuenta para la compuerta G2 |

El corpus simulado se genera con semilla determinista, al modo de `scripts/simular_lista.py`, y una
meta del sprint falla si algo de `ml/` lo referencia. G2 sigue cruzada con degradación a reglas.

---

## 7. Las trece sesiones

| Fase | Sesiones | Compuerta |
|---|---|---|
| **P0** documentar | `P0.1` ERS (UC‑10 componer, UC‑11 editar, RF nuevos); transcripción de la nota de campo y archivo de las fuentes primarias de la sección 5 —LOTTT, convención colectiva, Ley del Seguro Social— en `docs/fuentes/` · `P0.2` arquitectura y **D9 al tutor** | **GP0** |
| **P1** núcleo | `P1.1` modalidad de mano de obra y motor, con pruebas antes que implementación · `P1.2` `reemplazar_composicion` y lista MAPREX en USD, más la siembra de rendimientos de la línea base | |
| **P2** pantalla | `P2.1` funciones puras de composición · `P2.2` las tres tablas y el desglose en vivo · `P2.3` buscador MAPREX y autocompletado de depreciación · `P2.4` las cuatro ayudas de aprendizaje automático, todas como sugerencia y ninguna bloqueante (§3.7) | |
| **P3** flujo | `P3.1` presupuesto, auditoría y Excel · `P3.2` caso de demostración y regresión de la línea base | **GP1** |
| **P4** pruebas | `P4.1` primeras pruebas de interfaz del repositorio · `P4.2` siembra de demostración y guión IEEE 829 · `P4.3` corpus simulado y su cuarentena | **GP2** |
| **P5** cerrar | `P5.1` navegación curada para la entrega, bitácora y manuales | |

**GP0** — ERS y este diseño aprobados, D9 planteada al tutor. Sin esto no se toca el núcleo.
**GP1** — la línea base reproduce 1 586,61 USD y la auditoría detecta 7 de 7.
**GP2** — pruebas de interfaz verdes en Linux y Windows.

---

## 8. Riesgos y criterios de degradación

**Si la línea base se mueve al introducir la modalidad**, aunque sea 0,01: se revierte el cambio al
núcleo y se pasa al sueldo sintético fuera del núcleo, por el que ya hay precedente en
`scripts/seed_telecom.py`. Un cambio retrocompatible que no es retrocompatible no se negocia.

**Si `pytest -W error` hace inviables las pruebas de interfaz** —Streamlit emite avisos propios y la
suite trata todo aviso como fallo—: primero un `filterwarnings` acotado y documentado; si resulta
inmanejable, las pruebas de interfaz van detrás de un marcador y corren en un trabajo aparte de la
integración continua, con la pérdida de cobertura declarada y el guión manual absorbiendo la
diferencia.

**Si el tutor rechaza D9**: el prototipo se entrega sin destajo, la imposibilidad queda documentada
como hallazgo de investigación y la modalidad pasa a trabajo futuro. El resto del alcance no
depende de ella.

---

## 9. Trabajo futuro declarado

Bimoneda real en el motor (§3.5) · endpoints de API para crear y editar composiciones · ETL de
libros Excel si aparece el material · validación con presupuestos de obra ejecutada, que sigue
siendo la limitación declarada del proyecto.
