# Especificación de Requerimientos de Software (IEEE 830)

**Sistema de generación y auditoría de Análisis de Precios Unitarios multidominio**

> Estado: **completo, pendiente de revisión del tutor (compuerta G0, [docs/metodologia.md §2.2](metodologia.md#22-compuertas))**.
> Redactado en la Sesión 0.1 de [PLAN_DESARROLLO.md](../PLAN_DESARROLLO.md). Criterio de cierre exigido:
> al menos 23 RF numerados con prioridad y trazabilidad al caso de uso, y matriz de trazabilidad
> completa. Resultado original: **31 RF** (sección 3.2) y matriz de la sección 4.
> Este documento no reproduce datos que tienen fuente única: enlaza [CLAUDE.md](../CLAUDE.md),
> [docs/linea_base.md](linea_base.md) y [docs/metodologia.md](metodologia.md) (principio DRY,
> [metodologia.md §5](metodologia.md#5-dry)). Tras cruzar G0 quedan congelados los ocho casos de uso y
> sus requerimientos funcionales numerados.
> **Extensión posterior a G0 (Sesión P0.1, compuerta GP0, [PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)):**
> se agregan UC‑10 y UC‑11 y los RF‑33 a RF‑35, para un total de **34 RF**. El número **UC‑09** y el
> rango que arranca en **RF‑32** quedan vacantes/reservados: los reserva
> [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no ejecutada) para el asistente de
> presupuestos con IA; esta sesión continúa la numeración en UC‑10 y RF‑33 para no colisionar con esa
> reserva (enmendado en la Sesión U0.1, ver la nota siguiente).
> **Extensión del sprint de UI (Sesión U0.1, compuerta GU0, [PLAN_UI.md](../PLAN_UI.md)):** se
> agregan UC‑12, los RF‑36 a RF‑43 —para un total de **42 RF**— y el requisito no funcional
> RNF‑10. **La reserva de UC‑09 queda reducida a RF‑32 solamente:** RF‑33 a RF‑35 ya los tomó
> UC‑10/UC‑11, de modo que la reserva de un rango contiguo estaba rota antes de este sprint. Los
> demás requisitos de UC‑09 continuarán, al ejecutarse la Sesión A0.1 de
> [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md), a partir del siguiente al número más alto asignado (hoy
> RF‑44); esta enmienda prevalece sobre la instrucción «numera desde RF‑32» de
> PLAN_ASISTENTE.md:71‑73, que queda desactualizada hasta que A0.1 la corrija.

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026‑08‑29 |
| Autor | [tesista] |
| Revisor | [tutor académico] |

---

## 1. Introducción

### 1.1 Propósito
Definir los requerimientos funcionales y no funcionales del sistema para que el tutor, el jurado y el
equipo de desarrollo compartan una única descripción verificable de lo que se construye.

### 1.2 Alcance
Ver [CLAUDE.md §1](../CLAUDE.md#1-qué-es-este-proyecto). Incluye: derivación trazable de cantidades,
costeo con estructura venezolana, presupuesto y curva, verificación automática, normalización semántica,
detección de anomalías y predicción de precios. Excluye: gemelo digital en sentido estricto,
digitalización automática de planos, evaluación financiera del proyecto de inversión.

### 1.3 Definiciones, acrónimos y abreviaturas

| Término | Definición |
|---|---|
| APU | Análisis de Precios Unitarios: desglose de materiales, equipos y mano de obra por unidad de partida |
| FCAS | Factor de Costos Asociados al Salario (prestaciones); en la línea base, 600 % |
| Bono de alimentación | Cestaticket; monto diario por obrero |
| Rendimiento | Unidades de partida ejecutadas por día |
| BIM‑5D | Modelo paramétrico 3D con cómputo, costo y plan de trabajo asociados |
| IFC | Industry Foundation Classes, formato abierto de intercambio BIM |
| COVENIN 2000 | Codificación venezolana de partidas de construcción |
| ItemComputo | Cantidad de obra trazable (`core.contracts`) |
| Adaptador de dominio | Componente que lee la fuente propia de un dominio y devuelve ItemComputo |
| Línea base | Presupuesto auditado del caso de estudio, [docs/linea_base.md](linea_base.md) |
| LOD | *Level of Development*: grado de definición geométrica y de información de un elemento del modelo BIM (LOD 100 conceptual … LOD 500 verificado en obra). Determina si una cantidad puede extraerse del modelo o debe declararse por regla; es la pregunta que resuelve la compuerta G1 |
| AACE clase 3 | Clase de estimado de la *Association for the Advancement of Cost Engineering* (RP 18R‑97) para un proyecto definido entre el 10 % y el 40 %: exactitud esperada entre −20 % y +30 %. Marco de contraste del indicador 2 |
| MAPE | *Mean Absolute Percentage Error*: media de \|(real − estimado)/real\|, en porcentaje. Métrica principal del módulo predictivo por ser independiente de la escala del precio |
| RMSE | *Root Mean Squared Error*: raíz de la media de los errores al cuadrado, en la unidad monetaria; penaliza los errores grandes |
| R² | Coeficiente de determinación: proporción de la varianza del precio explicada por el modelo (1 = ajuste perfecto, 0 = equivale a predecir la media) |
| CBR | *Case‑Based Reasoning*, razonamiento basado en casos: se estima el precio de una partida nueva por analogía con las más parecidas del histórico, con validación dejando uno fuera. Alternativa prevista cuando hay entre 50 y 200 registros por dominio |
| Isolation Forest | Algoritmo de detección de anomalías no supervisado: aísla observaciones raras con árboles de particiones aleatorias. No requiere datos etiquetados; se usa sobre precios unitarios y rendimientos |
| sentence‑transformers | Biblioteca de modelos que convierten un texto en un vector semántico. Con el modelo multilingüe `paraphrase-multilingual-MiniLM-L12-v2` permite comparar descripciones de partidas por similitud del coseno sin entrenamiento previo |
| Sombra digital | Réplica digital que se alimenta del estado real de la obra pero no actúa sobre ella. El sistema es BIM‑5D y, a lo sumo, sombra digital: **no** es un gemelo digital, que exige realimentación bidireccional en tiempo real ([metodologia.md §9](metodologia.md#9-riesgos-que-gobiernan-las-compuertas)) |

### 1.4 Referencias
IEEE 830‑1998; ISO/IEC 25010; COVENIN 2000; AACE RP 18R‑97; Bases del anteproyecto
(`docs/fuentes/`); [CLAUDE.md](../CLAUDE.md); [docs/metodologia.md](metodologia.md).

### 1.5 Visión general del documento
La sección 2 describe el producto y sus casos de uso; la sección 3 enumera los requerimientos; la
sección 4 los traza a los casos de uso y a las pruebas.

---

## 2. Descripción general

### 2.1 Perspectiva del producto
Sistema de escritorio/servidor local: núcleo Python con base SQLite, interfaz Streamlit y API FastAPI.
Recibe cantidades de obra de adaptadores de dominio (IFC, CSV, tablas) y listas de precios (CSV/Excel);
produce presupuesto, curva de inversión, informe de auditoría y exportación a Excel. Ver
[docs/arquitectura.md](arquitectura.md).

### 2.2 Funciones del producto (casos de uso)

| UC | Nombre | Incremento |
|---|---|---|
| UC‑01 | Elaborar presupuesto nuevo desde una fuente de cantidades | I0.5, I3.1 |
| UC‑02 | Actualizar masivamente los precios de un presupuesto existente | I1 |
| UC‑03 | Reutilizar partidas y desgloses de proyectos anteriores | I2 |
| UC‑04 | Recalcular ante cambio de alcance o dimensiones | I3.2 |
| UC‑05 | Auditar un presupuesto elaborado por un tercero | I4 |
| UC‑06 | Registrar y consultar rendimientos reales de obra ejecutada | I6.2 |
| UC‑07 | Contrastar el precio construido con el precio de mercado | I6.3 |
| UC‑08 | Generar escenarios de sensibilidad | F.1 |
| UC‑10 | Componer una partida | P0.1 (declarado), P1–P2 |
| UC‑11 | Editar una partida compuesta | P0.1 (declarado), P1–P2 |
| UC‑12 | Recorrer la aplicación guiado desde el Inicio | U0.1 (declarado), U1 |

UC‑09 queda vacante en este documento: [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no
ejecutada) lo reserva para «Generar presupuesto asistido desde las necesidades del usuario». UC‑10 y
UC‑11 se declaran en la Sesión P0.1 del sprint del prototipo AREN.IA
([PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)); su implementación en `ui/composicion.py` y
`ui/paginas/componer.py` es de las Fases P1 y P2 de ese plan, aún no ejecutadas al cerrar esta sesión.

Los tipos citados en los flujos (`ItemComputo`, `ComposicionAPU`, `ResultadoAPU`, `Presupuesto`,
`Hallazgo`, `Rendimiento`) son los de [CLAUDE.md §5](../CLAUDE.md#5-contratos-de-interfaz-corecontracts),
implementados en `core/contracts/`.

#### UC‑01 — Elaborar presupuesto nuevo desde una fuente de cantidades

- **Actor principal:** proyectista / estimador. **Actor secundario:** administrador del catálogo.
- **Precondiciones:** el catálogo tiene partidas, insumos y una lista de precios vigente; existe una
  fuente de cantidades (IFC, CSV o tabla) de un dominio con adaptador registrado.
- **Flujo principal**
  1. El proyectista crea el proyecto y selecciona la fuente de cantidades y su dominio.
  2. El sistema invoca `AdaptadorDominio.extraer(fuente)` y obtiene una lista de `ItemComputo`, cada uno
     con `origen_id` y `origen_tipo`.
  3. El sistema asocia cada ítem a su partida del catálogo y recupera su `ComposicionAPU` y el
     rendimiento vigente.
  4. El motor de costos calcula el `ResultadoAPU` de cada partida con los `ParametrosCosto` del proyecto.
  5. El sistema arma el `Presupuesto`: una `PartidaPresupuestada` por ítem, con su total, y el total general.
  6. El proyectista distribuye las partidas en períodos; el sistema genera la curva de inversión y
     comprueba que el acumulado final iguale el total.
  7. El sistema ejecuta la verificación (UC‑05) y emite el informe de auditoría sin que se le solicite.
  8. El proyectista exporta presupuesto y curva a XLSX.
- **Flujos alternativos**
  - *2a. Fuente ilegible o de otro dominio:* el sistema rechaza la carga, no crea el presupuesto e indica
    el archivo y el elemento o fila que falló.
  - *3a. Ítem sin partida en el catálogo:* el sistema propone las tres partidas más similares (UC‑03); si
    no se acepta ninguna, el ítem queda pendiente, no suma al total y el informe lo declara.
  - *3b. Partida sin rendimiento vigente:* el sistema propone el del histórico con su dispersión (UC‑06) y
    exige declarar si es estimado o medido.
  - *6a. Sin plan de trabajo:* el presupuesto se emite sin curva y el informe registra que R2 no es aplicable.
  - *7a. Hallazgos de severidad `CRITICO`:* el presupuesto se emite igualmente, con esos hallazgos al frente
    del informe. La verificación audita, no bloquea.
- **Postcondiciones:** presupuesto persistido con referencia a la lista de precios que lo valoró; curva
  cerrada al 100 %; informe de auditoría persistido; toda cantidad conserva su origen.

#### UC‑02 — Actualizar masivamente los precios de un presupuesto existente

- **Actor principal:** administrador del catálogo. **Actor secundario:** proyectista.
- **Precondiciones:** existe un presupuesto valorado con una lista de precios; se dispone del archivo
  CSV/XLSX con la lista nueva.
- **Flujo principal**
  1. El administrador carga el archivo e indica su fecha de vigencia y su moneda.
  2. El sistema valida columnas, tipos y unidades, y convierte todo importe a `Decimal`.
  3. El sistema identifica los insumos cuyo precio difiere del vigente y las partidas donde participan.
  4. El sistema recalcula los APU afectados y produce una versión nueva del presupuesto, sin editar
     ninguna composición.
  5. El sistema persiste un registro de cambio por insumo: precio anterior, precio nuevo, variación e
     incidencia por partida.
  6. El sistema muestra el informe comparativo por partida y total, en valor absoluto y porcentual.
  7. El usuario acepta la versión nueva o la descarta.
- **Flujos alternativos**
  - *2a. Insumos desconocidos en el archivo:* el sistema los lista y ofrece darlos de alta o ignorarlos; los
    ignorados no intervienen en el recálculo.
  - *2b. Unidad no equivalente a la del catálogo* (`unidades_equivalentes`): la fila se rechaza y se
    reporta; las demás se procesan.
  - *3a. Ningún precio cambió:* no se crea versión nueva y se informa.
  - *7a. El usuario descarta la versión:* se marca como descartada, pero el registro de cambios se conserva
    porque alimenta el histórico del módulo predictivo.
- **Postcondiciones:** versión nueva asociada a su lista de precios; histórico de cambios persistido; el
  presupuesto anterior sigue siendo reconstruible a su fecha.

#### UC‑03 — Reutilizar partidas y desgloses de proyectos anteriores

- **Actor principal:** proyectista. **Actor secundario:** administrador del catálogo.
- **Precondiciones:** el catálogo contiene partidas de proyectos anteriores; el modelo de similitud está
  disponible localmente.
- **Flujo principal**
  1. El proyectista escribe la descripción de la partida en texto libre.
  2. El sistema calcula su vector semántico y devuelve las tres partidas del catálogo con mayor similitud
     del coseno, cada una con su puntaje.
  3. El proyectista selecciona una.
  4. El sistema precarga su `ComposicionAPU` y su rendimiento, conservando la referencia a la partida de
     origen y el puntaje que la propuso.
  5. El proyectista ajusta cantidades o insumos y el sistema recalcula el precio unitario.
- **Flujos alternativos**
  - *2a. Ningún candidato supera el umbral de similitud declarado:* el sistema no propone nada y ofrece
    crear la partida desde cero.
  - *2b. Catálogo vacío (primer proyecto):* la propuesta se omite sin error.
  - *4a. El desglose recuperado usa insumos sin precio en la lista vigente:* se señalan y la partida queda
    incompleta hasta que se coticen.
- **Postcondiciones:** partida creada con trazabilidad a la partida de origen; el puntaje de similitud
  queda registrado como justificación de la reutilización.

#### UC‑04 — Recalcular ante cambio de alcance o dimensiones

- **Actor principal:** proyectista.
- **Precondiciones:** existe un presupuesto cuyas cantidades provienen de reglas paramétricas
  (`origen_tipo = REGLA`) o de un modelo IFC.
- **Flujo principal**
  1. El proyectista modifica un parámetro dimensional (ancho, altura, espesor) o el conteo de elementos.
  2. El sistema vuelve a evaluar las reglas afectadas y produce `ItemComputo` nuevos con la expresión y
     los parámetros que los generaron.
  3. El sistema recalcula las partidas afectadas y el total.
  4. El sistema regenera la curva y vuelve a ejecutar la verificación.
  5. El sistema muestra el diferencial contra la versión anterior: cantidad, precio unitario y total por
     partida.
- **Flujos alternativos**
  - *1a. El parámetro no participa en ninguna regla:* no hay recálculo y se informa.
  - *2a. La fuente es un modelo IFC y no reglas:* el sistema exige reimportar el modelo (UC‑01, paso 2) y
    empareja por `origen_id` (GlobalId) para conservar la correspondencia de las partidas.
  - *2b. Una regla produce una cantidad negativa o nula* (por ejemplo, relleno negativo): la cantidad se
    rechaza, la partida conserva su valor anterior y se emite un hallazgo de R5.
- **Postcondiciones:** versión nueva trazable, con la expresión que produjo cada cantidad; el diferencial
  queda registrado.

#### UC‑05 — Auditar un presupuesto elaborado por un tercero

- **Actor principal:** auditor.
- **Precondiciones:** hay un presupuesto propio del sistema, o un archivo tabular de un tercero con
  cantidades, unidades, APU y plan de trabajo.
- **Flujo principal**
  1. El auditor selecciona el presupuesto o importa el archivo del tercero.
  2. El sistema construye el `Presupuesto` en memoria conservando las unidades escritas por el autor.
  3. El sistema ejecuta las siete reglas R1–R7
     ([CLAUDE.md §7](../CLAUDE.md#7-siete-reglas-de-verificación-coreverification-sesión-i4)).
  4. Cada regla devuelve `Hallazgo` con severidad, descripción, impacto cuantificado y los `origen_id`
     involucrados.
  5. El sistema ordena los hallazgos por severidad descendente y emite el informe de auditoría.
  6. El auditor exporta el informe.
- **Flujos alternativos**
  - *2a. El archivo no trae plan de trabajo:* R2 y R7 se declaran no aplicables en el informe; las demás
    reglas se ejecutan igual.
  - *2b. Las cantidades no declaran regla ni origen:* R1 emite un hallazgo de trazabilidad ausente en vez
    de comparar contra una expresión inexistente.
  - *3a. Una regla no puede evaluarse por falta de datos:* se registra como hallazgo INFO "regla no
    evaluable" y la ejecución continúa; ninguna regla aborta el informe.
  - *5a. No hay hallazgos:* el informe se emite igualmente, declarando las siete reglas evaluadas y sin
    hallazgos.
- **Postcondiciones:** informe persistido y asociado al presupuesto; el presupuesto auditado no se
  modifica en ningún caso.

#### UC‑06 — Registrar y consultar rendimientos reales de obra ejecutada

- **Actor principal:** residente de obra (registro). **Actor secundario:** proyectista (consulta).
- **Precondiciones:** la partida existe en el catálogo y la ejecución es identificable (obra, tramo, fecha).
- **Flujo principal**
  1. El residente registra el rendimiento observado: partida, valor, condiciones, fecha y referencia a la
     ejecución.
  2. El sistema lo persiste como `TipoRendimiento.MEDIDO`, exigiendo esa referencia.
  3. Al crear o revisar un APU, el sistema propone el rendimiento del histórico de la partida y muestra su
     dispersión: número de observaciones, media, mínimo y máximo.
  4. Si el proyectista introduce un valor que se aparta del comportamiento observado, el sistema lo
     advierte sin impedir el registro.
  5. El sistema nunca mezcla estimados con medidos: cada APU declara de cuál procede su rendimiento.
- **Flujos alternativos**
  - *1a. Falta la referencia a la ejecución:* el registro se rechaza; un rendimiento medido sin ejecución
    no es auditable.
  - *3a. No hay histórico para la partida:* el sistema propone el rendimiento estimado del catálogo y lo
    rotula como tal.
  - *4a. El proyectista acepta la advertencia:* se registra su justificación junto al APU.
- **Postcondiciones:** histórico de rendimientos ampliado; todo APU es trazable al tipo y a la fuente de
  su rendimiento.

#### UC‑07 — Contrastar el precio construido con el precio de mercado

- **Actor principal:** auditor. **Actor secundario:** proyectista.
- **Precondiciones:** hay histórico de precios y de APU acumulado, y el conteo de registros por dominio
  está hecho (compuerta G2, [CLAUDE.md §8.1](../CLAUDE.md#8-compuertas-y-criterios-de-degradación)).
- **Flujo principal**
  1. El usuario selecciona una partida o un presupuesto completo.
  2. El sistema determina la técnica que corresponde al conteo de registros del dominio.
  3. El sistema estima el precio de referencia y reporta MAPE, RMSE y R² de la técnica empleada.
  4. El sistema contrasta el precio construido con el estimado y expresa la desviación en porcentaje.
  5. El sistema marca como atípicos los precios que se apartan del histórico y los incorpora al informe
     de auditoría.
- **Flujos alternativos**
  - *2a. Menos de 50 registros:* se emplea el sistema de reglas con análisis de sensibilidad y el
    resultado se rotula como limitación declarada.
  - *3a. Partida nueva sin análogas en el histórico:* no se estima y se informa que el contraste no es
    posible.
  - *4a. La desviación excede el rango de la clase 3 de AACE:* se emite un hallazgo de severidad
    ADVERTENCIA.
- **Postcondiciones:** estimación, métricas y desviación quedan registradas junto al presupuesto, con la
  técnica empleada declarada.

#### UC‑08 — Generar escenarios de sensibilidad

- **Actor principal:** proyectista.
- **Precondiciones:** existe un presupuesto base calculado.
- **Flujo principal**
  1. El proyectista define un escenario variando `ParametrosCosto` (FCAS, bono, administración, utilidad)
     o un conjunto de precios de insumos.
  2. El sistema recalcula el presupuesto completo con esos valores, sin alterar el base.
  3. El sistema muestra el total del escenario y su variación respecto del base, por partida y en conjunto.
  4. El proyectista compara varios escenarios en una tabla y la exporta.
- **Flujos alternativos**
  - *1a. Parámetro fuera de rango* (negativo, o depreciación fuera de (0, 1]): se rechaza por las
    invariantes de los contratos y el escenario no se crea.
  - *2a. El escenario altera precios de insumos:* se usa el mecanismo de UC‑02, pero sin persistir la
    lista como vigente.
  - *4a. El proyectista promueve un escenario a presupuesto:* se crea una versión nueva que registra el
    escenario del que proviene.
- **Postcondiciones:** escenarios guardados con sus parámetros; el presupuesto base permanece inalterado.

#### UC‑10 — Componer una partida

- **Actor principal:** proyectista / estimador.
- **Precondiciones:** el catálogo tiene insumos disponibles; hay una referencia de precios de mercado
  cargada (p. ej. MaPreX) para el buscador de apoyo; la partida no tiene composición previa.
- **Flujo principal**
  1. El proyectista declara el código, la descripción y la unidad de la partida.
  2. El proyectista arma la tabla de materiales: insumo, unidad, cantidad de consumo por unidad de
     partida y precio.
  3. El proyectista arma la tabla de equipos: insumo, cantidad, precio y factor de depreciación.
  4. El proyectista arma la tabla de mano de obra: insumo, cantidad, sueldo o precio por unidad
     instalada, y la modalidad de cada línea (jornal o destajo).
  5. El proyectista declara el rendimiento de la partida (unidades de partida por día) junto con sus
     condiciones.
  6. El sistema calcula el `ResultadoAPU` con `calcular_apu` sobre la composición en memoria y muestra
     el desglose y el precio unitario en vivo, sin necesidad de guardar.
  7. El proyectista guarda la composición.
  8. El sistema la persiste asociada a su rendimiento declarado y a sus condiciones.
- **Flujos alternativos**
  - *2a/3a/4a. Fila vacía en alguna tabla:* se descarta sin error.
  - *2b/3b/4b. El proyectista usa el buscador de la referencia de mercado:* el sistema propone
    descripción, unidad, precio y, para equipos, el factor de depreciación; el precio sugerido queda
    editable por quien presupuesta, porque la referencia de mercado no es verdad.
  - *5a. El rendimiento no se declara, o se declara sin sus condiciones:* el sistema no persiste la
    composición; el paso 7 queda bloqueado.
  - *7a. La partida ya existe con composición:* el sistema no crea una segunda composición; ofrece
    editar la existente (UC‑11).
- **Postcondiciones:** la partida queda persistida con su composición, su rendimiento y sus
  condiciones declaradas; el precio unitario es reproducible evaluando `calcular_apu` sobre lo
  guardado.

#### UC‑11 — Editar una partida compuesta

- **Actor principal:** proyectista / estimador.
- **Precondiciones:** la partida existe en el catálogo y tiene una composición y un rendimiento
  vigente.
- **Flujo principal**
  1. El proyectista abre la partida existente; el sistema precarga sus tres tablas de insumos y su
     rendimiento vigente con sus condiciones.
  2. El proyectista modifica insumos, cantidades, precios o la modalidad de alguna línea de mano de
     obra.
  3. El proyectista declara un rendimiento nuevo con sus condiciones.
  4. El sistema recalcula el desglose y el precio unitario en vivo sobre la composición modificada.
  5. El proyectista guarda.
  6. El sistema reemplaza la composición vigente: borra las líneas anteriores, registra el
     rendimiento nuevo y conserva el rendimiento anterior en el histórico de la partida.
- **Flujos alternativos**
  - *3a. El proyectista no declara un rendimiento nuevo con sus condiciones:* el sistema no permite
    guardar (misma regla que UC‑10, paso 5).
  - *6a. La partida no existe en el catálogo:* el sistema rechaza el reemplazo; ese caso es UC‑10, no
    UC‑11.
- **Postcondiciones:** la composición vigente es la nueva; el rendimiento anterior queda en el
  histórico de la partida, distinguible del nuevo; ningún otro presupuesto ya emitido que reutilizó
  esta partida se altera retroactivamente.

#### UC‑12 — Recorrer la aplicación guiado desde el Inicio

- **Actor principal:** usuario nuevo / evaluador. **Actor secundario:** proyectista / estimador.
- **Precondiciones:** la aplicación está instalada y arrancada; el usuario no recibió explicación
  previa del sistema.
- **Flujo principal**
  1. El usuario abre la aplicación; el sistema muestra la pantalla de Inicio (RF‑36).
  2. El sistema muestra en la barra lateral, en solo lectura, el caso abierto y su estado (RF‑39).
  3. El usuario confirma el archivo del caso o abre otro; el sistema lo fija para toda la sesión y
     ninguna otra pantalla vuelve a pedirlo (RF‑38).
  4. El usuario elige uno de los tres recorridos declarados (RF‑37).
  5. En cada pantalla del recorrido, el sistema indica en qué paso está y ofrece el paso siguiente
     (RF‑41); el menú agrupa las pantallas por oficio y en el orden del trabajo (RF‑42).
  6. El usuario completa el último paso y obtiene el resultado del recorrido (por ejemplo, el
     presupuesto en Excel con su hoja de auditoría).
- **Flujos alternativos**
  - *1a. Modo entrega activo:* el menú omite la sección Investigación; ninguna pantalla de Trabajo
    queda inaccesible (RF‑43).
  - *3a. El caso no existe o no tiene partidas:* el sistema lo declara y ofrece cargar el caso de
    demostración; nunca ofrece reiniciar la base (RF‑40).
  - *3b. El archivo no se puede leer como base de datos:* el sistema lo informa con un mensaje, sin
    traza, y el usuario abre otro.
  - *5a. El usuario abre una pantalla que no pertenece al recorrido activo:* el sistema no muestra
    paso siguiente en ella (RF‑41).
- **Postcondiciones:** el usuario llegó al resultado del recorrido; la base solo cambió por las
  acciones que el propio usuario ejecutó (la siembra del paso 3a, guardar, elaborar).

### 2.3 Características de los usuarios

| Actor | Descripción | UC principales |
|---|---|---|
| Proyectista / estimador | elabora y actualiza presupuestos | UC‑01, 02, 03, 04, 08, 10, 11 |
| Auditor | revisa presupuestos de terceros | UC‑05, 07 |
| Residente de obra | registra rendimientos medidos | UC‑06 |
| Administrador del catálogo | mantiene partidas, insumos y listas de precios | UC‑02, 03 |
| Usuario nuevo / evaluador | abre la aplicación por primera vez —tribunal, tutor o presupuestista recién llegado— y necesita orientarse sin formación previa | UC‑12 |

### 2.4 Restricciones
- Todo monto y cantidad en `Decimal` (CLAUDE.md §2).
- El núcleo no depende de ningún dominio; los dominios entran por `AdaptadorDominio` (CLAUDE.md §5).
- Procesamiento sobre IFC 4, no sobre formatos nativos de modelado (independencia tecnológica).
- Codificación de partidas COVENIN 2000; estructura de costos según la Convención Colectiva vigente.
- Ejecución local en Windows/Linux con Python ≥ 3.12.

### 2.5 Suposiciones y dependencias
- Disponibilidad de la línea base auditada (existe) y de un modelo IFC de prueba (`tanquilla.ifc`, pendiente).
- Volumen de registros históricos suficiente para el módulo predictivo (compuerta G2, CLAUDE.md §8.1).
- Autorización de uso académico de una base de precios de referencia, o catálogo reducido propio.

### 2.6 Requisitos futuros
Sombra digital (avance real de obra vs curva planificada); multimoneda con factor de actualización;
reconocimiento de planos.

---

## 3. Requisitos específicos

### 3.1 Interfaces externas
- **Usuario:** interfaz web local (Streamlit) con los once casos de uso declarados en este documento
  (UC‑01 a UC‑08 y UC‑10 a UC‑12; UC‑09 vacante, ver sección 2.2), con una pantalla de Inicio que
  lleva al usuario por recorridos guiados (UC‑12).
- **Software:** API REST (FastAPI) con esquema OpenAPI en `docs/api.json`.
- **Archivos de entrada:** IFC 4 (dominio civil), CSV de topología (telecom), registro de activos
  (industrial), alcance funcional (sistemas), listas de precios CSV/XLSX.
- **Archivos de salida:** presupuesto y curva en XLSX, informe de auditoría.

### 3.2 Requisitos funcionales

Cada RF es una afirmación comprobable, con prioridad (Esencial / Deseable / Opcional), el UC que lo
origina, el incremento que lo implementa y un criterio de aceptación con la prueba que lo demuestra.
Numeración: RF‑01 a RF‑03 se conservan como se escribieron en el esqueleto (son los tres requisitos
transversales del núcleo); de RF‑04 en adelante los requisitos van agrupados por caso de uso en orden
ascendente de UC. Los números no se reutilizan: si un RF se retira, su número queda vacante.
**RF‑32 queda vacante**: [PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md) (Sesión A0.1, aún no ejecutada)
lo reserva para UC‑09. Los RF de UC‑10 y UC‑11 (Sesión P0.1 de
[PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)) continuaron en RF‑33, y los de UC‑12 (Sesión U0.1 de
[PLAN_UI.md](../PLAN_UI.md)) en RF‑36. La reserva es **de RF‑32 solamente**: los demás requisitos
de UC‑09 tomarán, al ejecutarse A0.1, la numeración a partir del siguiente al número más alto
asignado (hoy RF‑44). Esta enmienda prevalece sobre la instrucción «numera desde RF‑32» de
[PLAN_ASISTENTE.md](../PLAN_ASISTENTE.md):71‑73, que queda desactualizada hasta que la Sesión A0.1
la corrija.

| RF | Enunciado | Prioridad | UC | Incremento | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑01 | El sistema calculará el precio unitario de una partida a partir de su composición y los parámetros de costo según la fórmula de CLAUDE.md §4 | Esencial | UC‑01 | I0.3 | `test_costing.py` en verde (5 APU ± 0,01) |
| RF‑02 | El sistema generará siempre el informe de auditoría al producir o cargar un presupuesto | Esencial | UC‑05 | I4 | 7 de 7 inconsistencias detectadas |
| RF‑03 | Toda cantidad de obra conservará `origen_id`, `origen_tipo` y, si aplica, la regla que la produjo | Esencial | UC‑01, 04 | I0.1 | `tests/unit/test_contracts.py` y `tests/unit/test_linea_base.py`: ningún `ItemComputo` sin `origen_id`, y un ítem de origen REGLA sin expresión es rechazado |
| RF‑04 | El sistema obtendrá las cantidades de obra invocando `AdaptadorDominio.extraer(fuente)`, sin que el núcleo conozca el dominio ni el formato de la fuente | Esencial | UC‑01 | I0.1, I3.1 | `tests/unit/test_arquitectura.py` verde (ningún adaptador importa de `core` fuera de `core.contracts`) y `tests/unit/test_linea_base.py`: todo `ItemComputo` trae `origen_id` y `origen_tipo`; la extracción IFC con `origen_id` = GlobalId, pendiente (Sesión I3.1) |
| RF‑05 | El sistema persistirá partidas, insumos, composiciones y rendimientos en SQLite; `scripts/seed.py` cargará la línea base en la base de datos, de modo que el presupuesto se reproduzca completo desde ella | Esencial | UC‑01 | I0.4 | `tests/integration/test_persistencia.py`: los cinco APU recuperados de la base dan los mismos precios unitarios que el fixture |
| RF‑06 | El sistema construirá el presupuesto asociando cada `ItemComputo` a su `ComposicionAPU`, calculando su `ResultadoAPU` y emitiendo una `PartidaPresupuestada` por ítem, con total por partida y total general | Esencial | UC‑01 | I0.5 | `tests/unit/test_budget.py` y `tests/integration/test_presupuesto_linea_base.py`: el presupuesto de la línea base corregida se reproduce partida por partida desde el catálogo persistido |
| RF‑07 | El sistema generará la curva de inversión de modo que su acumulado final sea exactamente igual al total del presupuesto | Esencial | UC‑01 | I0.5 | `tests/unit/test_budget.py` y `tests/integration/test_presupuesto_linea_base.py`: `total_curva == total` sin tolerancia (el caso real cerraba en 99,30 %) |
| RF‑08 | El sistema exportará presupuesto y curva a XLSX, redondeando a dos decimales solo en la celda presentada y nunca en el cálculo | Deseable | UC‑01 | I0.5 | `tests/unit/test_budget.py::test_exportar_excel_escribe_cuatro_hojas`: el libro se escribe completo y sus totales coinciden con los del presupuesto en memoria |
| RF‑09 | El sistema admitirá un dominio nuevo agregando un adaptador bajo `adapters/` que solo importe `core.contracts`, sin modificar `core/` | Esencial | UC‑01 | I5 | `git diff --stat core/` vacío tras I5, `tests/unit/test_arquitectura.py` verde y `tests/unit/test_adapter_telecom.py`, `tests/unit/test_adapter_industrial.py` y `tests/unit/test_adapter_sistemas.py` en verde (indicador 4) |
| RF‑10 | El sistema cargará una lista de precios en CSV o XLSX, la validará (columnas, tipos y unidades) e identificará los insumos cuyo precio difiere del vigente y las partidas donde participan | Esencial | UC‑02 | I1 | `tests/integration/test_actualizacion_precios.py`: la lista de prueba identifica exactamente los insumos modificados |
| RF‑11 | El sistema recalculará todos los APU afectados por la lista nueva y producirá una versión nueva del presupuesto sin editar ninguna composición | Esencial | UC‑02 | I1 | `tests/integration/test_actualizacion_precios.py`: las composiciones quedan idénticas y los precios unitarios cambian solo en las partidas afectadas |
| RF‑12 | El sistema persistirá cada cambio de precio con insumo, precio anterior, precio nuevo, variación porcentual, incidencia por partida y fecha | Esencial | UC‑02 | I1 | `tests/integration/test_actualizacion_precios.py`: un registro por insumo modificado, recuperable tras cerrar la sesión |
| RF‑13 | El sistema emitirá un informe comparativo entre la versión anterior y la nueva, por partida y total, en variación absoluta y porcentual | Esencial | UC‑02 | I1 | `tests/integration/test_actualizacion_precios.py`: la suma de las variaciones por partida iguala la variación del total |
| RF‑14 | El sistema reconstruirá cualquier presupuesto con los precios vigentes en la fecha en que fue elaborado | Esencial | UC‑02 | I1 | `tests/integration/test_persistencia.py::test_precios_se_reconstruyen_a_fecha` y `tests/integration/test_actualizacion_precios.py`: la reconstrucción a la fecha original es idéntica al presupuesto emitido (RNF‑02) |
| RF‑15 | El sistema devolverá, para una descripción en texto libre, las tres partidas del catálogo más similares con su puntaje de similitud del coseno | Esencial | UC‑03 | I2 | `tests/unit/test_normalizacion.py::test_propuestas_ordenadas_por_puntaje_y_sobre_el_umbral`: a lo sumo tres, orden descendente, ninguna bajo `UMBRAL_POR_DEFECTO` |
| RF‑16 | Al aceptar una propuesta, el sistema precargará su composición y su rendimiento, conservando la referencia a la partida de origen y el puntaje que la propuso | Esencial | UC‑03 | I2 | precarga cubierta en `ui/paginas/similares.py` (desglose, rendimiento, origen y puntaje visibles); la **persistencia** de la partida nueva, antes bloqueada por la falta de un flujo de creación de partidas (hallazgo en `docs/bitacora/2026-08-31-I2-normalizacion.md` y decisión D5 de `docs/dossier_g0.md`), queda **satisfecha por UC‑10** (Sesión P0.1; implementación en las Fases P1–P2 de [PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)) |
| RF‑17 | El sistema reconocerá al menos el 80 % de las partidas de un presupuesto conocido al normalizar sus descripciones | Esencial | UC‑03 | I2 | `tests/unit/test_normalizacion.py::test_acepta_al_menos_80_por_ciento_del_presupuesto_conocido`: ≥ 80 % de la línea base parafraseada reconocida en el primer puesto |
| RF‑18 | El sistema derivará las cantidades del dominio civil de reglas paramétricas declaradas, registrando en cada `ItemComputo` la expresión evaluada y los parámetros usados | Esencial | UC‑04 | I3.2 | `tests/unit/test_reglas_civil.py`: con a = 0,80, h = 0,80, e = 0,10 el concreto da 0,224 m3 y el encofrado 4,48 m2, y ambos ítems traen `regla` y `parametros` |
| RF‑19 | Al modificar un parámetro dimensional o el conteo de elementos, el sistema reevaluará las reglas afectadas y recalculará cantidades, precios y curva sin intervención manual | Esencial | UC‑04 | I3.2 | `tests/unit/test_reglas_civil.py`: cambiar el ancho de la tanquilla altera las cantidades derivadas de esa dimensión y ninguna otra |
| RF‑20 | El sistema presentará el diferencial entre la versión anterior y la recalculada: cantidad, precio unitario y total por partida | Deseable | UC‑04 | I3.2 | `tests/unit/test_budget.py`: la suma de los diferenciales por partida iguala la diferencia de totales |
| RF‑21 | El sistema ejecutará las siete reglas R1–R7 sobre cualquier `Presupuesto` y devolverá `Hallazgo` con severidad, descripción, impacto cuantificado y los `origen_id` involucrados | Esencial | UC‑05 | I4 | `tests/unit/test_verification.py`: cada regla devuelve hallazgos completos y lista vacía cuando el presupuesto cumple |
| RF‑22 | El sistema detectará las siete inconsistencias de la línea base sobre el presupuesto de prueba que las reproduce | Esencial | UC‑05 | I4 | `tests/integration/test_auditoria_7_de_7.py`: 7 de 7 hallazgos sobre el presupuesto de prueba, uno por regla, con `tests/unit/test_verification.py` cubriendo cada regla por separado (indicador 1) |
| RF‑23 | El sistema ordenará el informe por severidad descendente y no modificará el presupuesto auditado; una regla que no pueda evaluarse se reportará como hallazgo INFO sin interrumpir a las demás | Esencial | UC‑05 | I4 | `tests/unit/test_verification.py`: el presupuesto de entrada es idéntico antes y después, y una regla sin datos no aborta el informe |
| RF‑24 | El sistema importará un presupuesto de un tercero en formato tabular, conservando las unidades originales escritas por su autor, para poder auditarlo | Esencial | UC‑05 | I4 | `tests/integration/test_auditoria_7_de_7.py`: la unidad "mts" del cómputo llega intacta a la regla R3 |
| RF‑25 | El sistema registrará rendimientos medidos con partida, valor, condiciones, fecha y referencia a la ejecución, y rechazará un rendimiento medido sin esa referencia | Esencial | UC‑06 | I6.2 | `tests/unit/test_contracts.py` cubre la invariante; registro y consulta cubiertos (I6.2): `tests/integration/test_rendimientos.py` (medido exige referencia a una `Ejecucion` real, trazada por clave foránea) y `tests/integration/test_api_rendimientos.py` |
| RF‑26 | Al componer un APU, el sistema propondrá el rendimiento del histórico de la partida con su dispersión (número de observaciones, media, mínimo y máximo) | Esencial | UC‑06 | I6.2 | cubierto (I6.2): `tests/integration/test_rendimientos.py` y `tests/integration/test_api_rendimientos.py` — dispersión con n, media, mínimo, máximo y desglose estimado‑medido; la propuesta prefiere el medido más reciente y declara siempre el tipo |
| RF‑27 | El sistema advertirá cuando el rendimiento introducido se aparte del comportamiento observado, sin impedir el registro | Esencial | UC‑06 | I6.1, I6.2 | detección cubierta: `tests/unit/test_anomalias.py` (`evaluar_rendimiento`: desviado → atípico, coherente → no, histórico corto → sin veredicto); advertencia en el flujo cubierta (I6.2): `tests/integration/test_api_rendimientos.py` — fuera del rango observado responde 201 con `advertencia` y el registro persiste igual |
| RF‑28 | El sistema estimará el precio de mercado de una partida con la técnica que corresponda al conteo de registros del dominio y reportará MAPE, RMSE y R² de la técnica empleada | Esencial | UC‑07 | I6.3 | cubierto (I6.3): `docs/resultados_ml.md` generado con MAPE, RMSE, R² y técnica según conteo (compuerta G2 cruzada); pruebas en `tests/unit/test_prediccion.py` y `tests/unit/test_resultados_ml.py` (indicador 5) |
| RF‑29 | El sistema contrastará el precio construido con el estimado, expresará la desviación en porcentaje y marcará como atípicos los precios que se aparten del histórico | Esencial | UC‑07 | I6.1, I6.3 | marcado de atípicos cubierto: `tests/unit/test_anomalias.py` (`precios_atipicos` sobre el histórico de variaciones); contraste cubierto (I6.3): `tests/unit/test_prediccion.py` — desviación en porcentaje y `Hallazgo` de severidad ADVERTENCIA fuera del rango declarado de la clase 3 de AACE |
| RF‑30 | El sistema generará escenarios variando `ParametrosCosto` o precios de insumos y recalculará el presupuesto completo sin alterar el presupuesto base | Deseable | UC‑08 | F.1 | cubierto (cierre UC‑08, 2026‑08‑31): `tests/unit/test_escenarios.py` — el presupuesto base y las composiciones quedan intactos, y cada partida del escenario se verifica contra `calcular_apu` (el motor como verdad de terreno); por HTTP, `tests/integration/test_api_escenarios.py` — `POST /presupuestos/{codigo}/escenarios` no persiste ninguna versión y responde 422 ante un parámetro fuera de rango (flujo 1a) |
| RF‑31 | El sistema comparará varios escenarios entre sí y con el presupuesto base en una tabla exportable | Opcional | UC‑08 | F.1 | cubierto (cierre UC‑08, 2026‑08‑31): `tests/unit/test_escenarios.py` — la tabla trae el base y una fila por escenario con total, variación absoluta y porcentual, y se exporta (`to_csv`); en la UI, la página «Escenarios (UC‑08)» presenta la tabla con detalle por partida y descarga CSV |
| RF‑33 | El sistema no persistirá una composición cuyo rendimiento no haya sido declarado explícitamente junto con sus condiciones | Esencial | UC‑10, 11 | P1.2, P2.2 | cumplido en los dos caminos del catálogo: `tests/integration/test_persistencia.py::test_cargar_composicion_sin_condiciones_lanza_valueerror` (P2.2, `Catalogo.cargar_composicion`) y `::test_reemplazar_composicion_exige_condiciones_no_vacias` (P1.2, `Catalogo.reemplazar_composicion`); pendiente en la pantalla: `tests/unit/test_ui_componer.py` (P4.1, botón de guardar deshabilitado sin condiciones) |
| RF‑34 | La modalidad de la mano de obra se declara por línea: jornal o destajo | Esencial | UC‑10, 11 | P1.1, P2.2 | cumplido en el núcleo y el catálogo: `tests/unit/test_costing_destajo.py` (P1.1, `ModalidadManoObra` en `core/contracts/apu.py`, columna Modalidad de `LineaManoObra`) y `tests/integration/test_persistencia.py::test_la_modalidad_a_destajo_sobrevive_el_viaje_por_el_catalogo` (persistencia y lectura); cumplido en la composición pura: `tests/unit/test_composicion.py` (P2.1, `ui/composicion.py` acepta y valida la modalidad por fila); pendiente la columna Modalidad de la tabla de mano de obra en `ui/paginas/componer.py` (P2.2) |
| RF‑35 | El precio sugerido desde la referencia de mercado es editable por quien presupuesta | Esencial | UC‑10 | P2.3 | pendiente: prueba del buscador `buscar_referencia` en `tests/unit/test_composicion.py` (P2.3); MaPreX es referencia, no verdad, y el campo de precio nunca queda de solo lectura; el archivo se nombra al abrir la sesión |
| RF‑36 | La interfaz abrirá en la pantalla de Inicio, cualquiera que sea el orden del resto del menú | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_app.py` — el Inicio es la página por defecto por identidad, no por posición, y la ruta vacía que Streamlit da a la página por defecto se traduce a `inicio` |
| RF‑37 | Los recorridos guiados se declararán una sola vez, en un módulo sin Streamlit ni base de datos, y el destino de cada paso será la ruta de una página registrada | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_recorridos.py` — integridad de enlaces: todo `paso.pagina` está en `{p.ruta_url for p in paginas_visibles(False)}` y en las visibles en modo entrega |
| RF‑38 | El archivo de la base se fijará una vez por sesión y todas las pantallas operarán sobre ese mismo caso; ninguna pantalla distinta del Inicio pedirá la ruta | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_caso.py` — resolución sesión → entorno → constante; `RUTA_BASE_POR_DEFECTO` definida una sola vez en `ui/`; `tests/unit/test_ui_app.py` — ninguna página salvo el Inicio pide la ruta |
| RF‑39 | El sistema mostrará en toda pantalla, en solo lectura, el caso abierto y su estado: existencia del archivo, número de partidas, número de insumos y si hay lista de precios vigente | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_caso.py` (estado sobre base inexistente, vacía, sembrada e ilegible, sin traza) y `tests/unit/test_ui_app.py` (`AppTest`: el marco pinta el estado en cada una de las diez pantallas) |
| RF‑40 | Cuando el caso abierto no exista o no contenga partidas, el Inicio lo declarará y ofrecerá cargar el caso de demostración, sin exponer nunca la opción de reiniciar la base | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_inicio.py` (estado vacío, siembra, botón ausente con partidas) y `tests/unit/test_ui_caso.py` (el literal del flag de reinicio no aparece en ningún archivo de `ui/`) |
| RF‑41 | Cada pantalla del recorrido activo mostrará su paso siguiente y la posición del usuario en el recorrido, tomados de la declaración única de recorridos; una pantalla que no pertenezca a ningún recorrido no mostrará ninguno de los dos | Deseable | UC‑12 | U1 | pendiente: `tests/unit/test_ui_recorridos.py` (`paso_siguiente`) y `tests/unit/test_ui_app.py` (`AppTest`: botón «Siguiente» y su destino) |
| RF‑42 | El menú presentará cada pantalla con el nombre de su oficio, agrupada en dos secciones —Trabajo e Investigación— en el orden del trabajo real; el código del caso de uso permanecerá visible como subtítulo | Deseable | UC‑12 | U1 | pendiente: `tests/unit/test_ui_app.py` — secciones y orden sin Streamlit; ningún título lleva código de UC; `AppTest`: el subtítulo «Caso de uso …» en las cinco pantallas que tienen uno |
| RF‑43 | Con el modo entrega activo, ninguna pantalla de Trabajo quedará inaccesible | Esencial | UC‑12 | U1 | pendiente: `tests/unit/test_ui_app.py` (la sección Trabajo es idéntica con y sin modo entrega) y `tests/unit/test_ui_recorridos.py` (ningún paso sale de Trabajo) |

Los archivos citados pertenecen al conjunto de pruebas acordado para el proyecto: en `tests/unit/`,
`test_costing.py`, `test_contracts.py`, `test_linea_base.py`, `test_arquitectura.py`, `test_budget.py`,
`test_reglas_civil.py`, `test_verification.py`, `test_adapter_telecom.py`, `test_adapter_industrial.py` y
`test_adapter_sistemas.py`; en `tests/integration/`, `test_persistencia.py`, `test_presupuesto_linea_base.py`,
`test_auditoria_7_de_7.py` y `test_actualizacion_precios.py`. Los cuatro primeros existen al cerrar la
Sesión 0.1; los demás los crea el incremento indicado en su fila. Los RF posteriores al núcleo (I2, I6.1,
I6.2, I6.3, F.1 y, ahora, RF‑33 a RF‑35 del sprint del prototipo) declaran su criterio medible y marcan la
prueba como pendiente: el archivo se nombra al abrir esa sesión, no antes. RF‑36 a RF‑43 (U0.1)
nombran ya su archivo de prueba, que crea U1.

Cobertura por caso de uso (mínimos exigidos por el criterio de cierre entre paréntesis):

| UC | RF | Cantidad |
|---|---|---|
| UC‑01 | RF‑01, RF‑03, RF‑04, RF‑05, RF‑06, RF‑07, RF‑08, RF‑09 | 8 (≥ 4) |
| UC‑02 | RF‑10, RF‑11, RF‑12, RF‑13, RF‑14 | 5 (≥ 4) |
| UC‑03 | RF‑15, RF‑16, RF‑17 | 3 (≥ 2) |
| UC‑04 | RF‑03, RF‑18, RF‑19, RF‑20 | 4 (≥ 3) |
| UC‑05 | RF‑02, RF‑21, RF‑22, RF‑23, RF‑24 | 5 (≥ 3) |
| UC‑06 | RF‑25, RF‑26, RF‑27 | 3 (≥ 3) |
| UC‑07 | RF‑28, RF‑29 | 2 (≥ 2) |
| UC‑08 | RF‑30, RF‑31 | 2 (≥ 2) |
| UC‑10 | RF‑33, RF‑34, RF‑35 | 3 (sin mínimo declarado; UC nuevo, Sesión P0.1) |
| UC‑11 | RF‑33, RF‑34 | 2 (sin mínimo declarado; UC nuevo, Sesión P0.1) |
| UC‑12 | RF‑36, RF‑37, RF‑38, RF‑39, RF‑40, RF‑41, RF‑42, RF‑43 | 8 (sin mínimo declarado; UC nuevo, Sesión U0.1) |
| **Total** | RF‑01 … RF‑31, RF‑33 … RF‑43 (RF‑32 vacante — reservado a UC‑09; RF‑03 traza a dos UC; RF‑33 y RF‑34 trazan a UC‑10 y UC‑11) | **42** |

### 3.3 Requisitos no funcionales (ISO/IEC 25010)

| Característica | RNF | Métrica | Meta |
|---|---|---|---|
| Adecuación funcional | RNF‑01 exactitud del presupuesto frente a la línea base corregida | desviación % | dentro de clase 3 AACE |
| Fiabilidad | RNF‑02 reproducibilidad: el mismo presupuesto se reconstruye a la fecha de su lista de precios | comparación exacta | 100 % |
| Eficiencia de desempeño | RNF‑03 tiempo de recálculo masivo tras cambiar la lista de precios, medido en el equipo de desarrollo con SQLite local y sin exportación | segundos para N partidas | < 5 s con N ≤ 100 partidas |
| Usabilidad | RNF‑04 el informe de auditoría se entiende sin formación previa | juicio de expertos (Likert) | ≥ 4/5 |
| Mantenibilidad | RNF‑05 agregar un dominio no modifica `core/` | `git diff --stat core/`, `test_arquitectura.py` | vacío / verde |
| Mantenibilidad | RNF‑06 cobertura de pruebas del núcleo | pytest‑cov | ≥ 80 % |
| Portabilidad | RNF‑07 instalación con `uv sync` en Windows y Linux | pasos manuales | 0 |
| Seguridad | RNF‑08 ejecución local: el sistema no requiere credenciales, no invoca servicios externos en tiempo de ejecución y los datos residen en un archivo SQLite del equipo del usuario | credenciales versionadas; llamadas de red durante la operación | 0 y 0; única excepción, la descarga inicial del modelo de `sentence-transformers` (I2), que se declara y se cachea localmente |
| Compatibilidad | RNF‑09 entrada IFC 4 de cualquier modelador | archivos de ≥ 2 herramientas (p. ej. Revit y Bonsai) | cantidades extraídas iguales al cálculo manual en ambos; pendiente de la compuerta G1 (I3.1), cuya alternativa es la entrada tabular documentada |
| Usabilidad | RNF‑10 capacidad de aprendizaje de la interfaz: una persona que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de auditoría | caso con persona CP‑07 ([guion_prueba_arenia.md](guion_prueba_arenia.md)) y bloque B del anexo A de [dossier_g0.md](dossier_g0.md) | en cada uno de los dos escenarios de CP‑07 (CP‑07 pasa solo si pasan ambos): sin ayuda, ≤ 20 min, bloque B ≥ 4,0 y ningún ítem < 3 |

### 3.4 Reglas de negocio
Fórmula de cálculo: [CLAUDE.md §4](../CLAUDE.md#4-especificación-del-cálculo-y-línea-base).
Reglas de verificación R1–R7: [CLAUDE.md §7](../CLAUDE.md#7-siete-reglas-de-verificación-coreverification-sesión-i4).
Criterios de degradación del módulo predictivo: [CLAUDE.md §8.1](../CLAUDE.md#8-compuertas-y-criterios-de-degradación).

---

## 4. Matriz de trazabilidad

| UC | RF | Prueba(s) | Incremento | Indicador de la tesis |
|---|---|---|---|---|
| UC‑01 | RF‑01, RF‑03, RF‑04, RF‑05, RF‑06, RF‑07, RF‑08 | `tests/unit/test_costing.py`, `tests/unit/test_contracts.py`, `tests/unit/test_linea_base.py`, `tests/unit/test_arquitectura.py`, `tests/unit/test_budget.py` (I0.5), `tests/integration/test_persistencia.py` (I0.4), `tests/integration/test_presupuesto_linea_base.py` (I0.5); extracción IFC pendiente (I3.1) | I0.1, I0.3, I0.4, I0.5, I3.1 | 2, 3 |
| UC‑01 (transversal) | RF‑09 | `tests/unit/test_arquitectura.py`, `tests/unit/test_adapter_telecom.py`, `tests/unit/test_adapter_industrial.py` y `tests/unit/test_adapter_sistemas.py` (I5), más `git diff --stat core/` | I0.1, I5 | 4 |
| UC‑02 | RF‑10, RF‑11, RF‑12, RF‑13, RF‑14 | `tests/integration/test_actualizacion_precios.py` (I1), `tests/integration/test_persistencia.py` (I0.4) | I0.4, I1 | 3 |
| UC‑03 | RF‑15, RF‑16, RF‑17 | `tests/unit/test_normalizacion.py` (I2); persistencia de RF‑16 pendiente del flujo de creación de partidas (hallazgo I2) | I2 | 3 |
| UC‑04 | RF‑03, RF‑18, RF‑19, RF‑20 | `tests/unit/test_contracts.py` (RF‑03, I0.1), `tests/unit/test_reglas_civil.py` (I3.2), `tests/unit/test_budget.py` (I0.5) | I0.1, I3.2 | 2 |
| UC‑05 | RF‑02, RF‑21, RF‑22, RF‑23, RF‑24 | `tests/unit/test_verification.py` (I4), `tests/integration/test_auditoria_7_de_7.py` (I4) | I4 | 1 |
| UC‑06 | RF‑25, RF‑26, RF‑27 | `tests/unit/test_contracts.py` (invariante de `Rendimiento`, I0.1); `tests/unit/test_anomalias.py` (detección de desviación, I6.1); `tests/integration/test_rendimientos.py` y `tests/integration/test_api_rendimientos.py` (registro, dispersión y advertencia, I6.2) | I0.1, I6.1, I6.2 | 2 |
| UC‑07 | RF‑28, RF‑29 | `tests/unit/test_anomalias.py` (precios atípicos, I6.1); `tests/unit/test_prediccion.py` y `tests/unit/test_resultados_ml.py` (estimación, métricas y contraste AACE, I6.3; `docs/resultados_ml.md`) | I6.1, I6.3 | 5 |
| UC‑08 | RF‑30, RF‑31 | `tests/unit/test_escenarios.py` y `tests/integration/test_api_escenarios.py` (`core/budget/escenarios.py`, `POST /presupuestos/{codigo}/escenarios`, página `ui/paginas/escenarios.py`; sin persistir: el mecanismo de UC‑02) | cierre UC‑08 (2026‑08‑31) | 2 (apoyo) |
| UC‑10 | RF‑16 (satisfecho), RF‑33, RF‑34, RF‑35 | pendientes: `tests/integration/test_persistencia.py` (P1.2), `tests/unit/test_costing_destajo.py` (P1.1), `tests/unit/test_composicion.py` (P2.1, P2.3), `tests/unit/test_ui_componer.py` (P4.1) — ninguna existe al cerrar la Sesión P0.1 | P0.1 (declarado), P1–P4 ([PLAN_PROTOTIPO.md](../PLAN_PROTOTIPO.md)) | prototipo de entrega AREN.IA, fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) |
| UC‑11 | RF‑33, RF‑34 | pendientes: `tests/integration/test_persistencia.py` (P1.2, `Catalogo.reemplazar_composicion`) — no existe al cerrar la Sesión P0.1 | P0.1 (declarado), P1.2, P2.2 | prototipo de entrega AREN.IA, fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) |
| UC‑12 | RF‑36, RF‑37, RF‑38, RF‑39, RF‑40, RF‑41, RF‑42, RF‑43 | pendientes: `tests/unit/test_ui_recorridos.py`, `tests/unit/test_ui_caso.py`, `tests/unit/test_ui_inicio.py`, `tests/unit/test_ui_app.py` (U1); CP‑07 para RNF‑10 | U0.1 (declarado), U1 ([PLAN_UI.md](../PLAN_UI.md)) | fuera de los cinco indicadores de [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis); aporta la medición de usabilidad de [calidad_iso25010.md §4](calidad_iso25010.md) |

Correspondencia RNF → verificación: RNF‑01 y RNF‑02 se comprueban en UC‑01 y UC‑02 (RF‑06, RF‑14);
RNF‑03 en UC‑02 (RF‑11); RNF‑04 con el juicio de expertos sobre el informe de UC‑05; RNF‑05 con RF‑09;
RNF‑06 y RNF‑07 en la Sesión F.2; RNF‑08 por inspección del repositorio y de las dependencias;
RNF‑09 en la compuerta G1 (RF‑04). RNF‑10 con el caso con persona CP‑07, en la compuerta GU1 de
[PLAN_UI.md](../PLAN_UI.md); RNF‑04 es un requisito distinto y sigue pendiente.

La columna "Indicador" enlaza con [docs/metodologia.md §8](metodologia.md#8-indicadores-de-la-tesis) y
con la matriz de [docs/tesis/esqueleto_tesis.md](tesis/esqueleto_tesis.md).

---

## Apéndices
- A. Caso de estudio y línea base: [docs/linea_base.md](linea_base.md).
- B. Modelo de datos: [docs/modelo_datos.md](modelo_datos.md).
- C. Arquitectura: [docs/arquitectura.md](arquitectura.md).
