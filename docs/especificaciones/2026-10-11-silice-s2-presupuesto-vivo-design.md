# Sílice S2 (0.7.0): presupuesto vivo — valuaciones, valor ganado, alertas y recuperación de retrasos

| Campo | Valor |
|---|---|
| Estado | **propuesta corregida** tras la revisión de los cinco encargos (requisitos, arquitectura, pruebas y calidad, verificador de hechos, seguridad) y sus rulings RV‑1…RV‑26 del 2026‑10‑11; pendiente de la aprobación de Eugenio. Los tres expedientes de `core/` (§5.4) necesitan además el visto bueno del tutor |
| Versión que entrega | **0.7.0** (spec maestro §5; RV‑1); condición: 0.6.0 fusionada (S5‑1 adelantado: Alembic, respaldo, `preparar_base`; y S1: moneda, tasa fechada, reajuste). La 0.8.0 (S3) se construye **sobre** la 0.7.0, porque el paquete lleva los anexos de S2 |
| Fecha | 2026‑10‑11 |
| Rama del spec | `inc/silice` (worktree `.worktrees/silice`). Construcción (RV‑2): una rama corta por **fase** desde el `main` del momento, PR contra `main` y fusión al cruzar la compuerta de la fase (§8); un solo carril de núcleo abierto a la vez: S1‑1 → S1‑3 → S1‑4 → **S2‑1 → S2‑2 → S2‑3** → S3‑2; la fase de interfaz S2‑4 con la guardia M9 |
| Se apoya en | [spec maestro](2026-10-11-silice-1.0.0-design.md) (§3, §5, §6); [horizonte](2026-10-08-horizonte-reorientacion-design.md) H‑D2, H‑D5, §4 y §6 (fase R2); [antecedentes](../tesis/antecedentes-reorientacion-2026-10-08.md) §2 y §3; [spec S1](2026-10-11-silice-s1-moneda-reajuste-design.md) §5.3, §8; [spec SF](2026-10-04-sprint-final-prototipo-design.md) SF‑E2, SF‑E3, SF‑E4, SF‑E6 |
| Documentos que enmienda | [ERS](../ERS.md), [modelo de datos](../modelo_datos.md) (§2.6 nueva), [arquitectura](../arquitectura.md), [plan de pruebas](../plan_pruebas.md), [NORMAS.md](../../NORMAS.md) §6 |
| Naturaleza de los datos | [NORMAS.md §1](../../NORMAS.md): la obra de ejemplo OB‑S2 (§7.1), sus valuaciones, sus costos reales y su inspector son **ficticios y declarados** |

**Lo que este spec no inventa.** Las fórmulas de valor ganado (PV, EV, AC, SV, CV, SPI, CPI, EAC) se usan como
**definiciones del sistema**: ninguna fuente que las contenga está verificada en el repositorio (ver §4.2 y la
tarea S2‑0). Las cifras de eficiencia por rendimientos decrecientes son **supuestos declarados**: Lee (2022) es la
base del método, no de los números. Los límites de horas extraordinarias sí están verificados, en la copia de la
LOTTT del repositorio (`docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt`).

---

## 1. Qué se quiere

1. **Valuaciones por cantidades ejecutadas** (H‑D5), por partida y período, con su fuente (número de valuación,
   inspector, fecha), escritas a mano o importadas de Excel, en dos estados (*presentada* y *conformada*), y
   **auditadas**: lo ejecutado no supera lo presupuestado sin una variación registrada, ninguna partida fuera del
   plan, ninguna fecha fuera de su período. Lo ejecutado de las conformadas alimenta el reajuste de S1.
2. **Valor ganado** en la moneda del proyecto (S1), con fórmulas declaradas, y la **separación del desvío de
   control** en tres componentes: **plazo** (cantidad a precios de la línea base), **precio** (lo que la obra ejecutada cuesta
   de más por los precios del corte) y **consumo** (el resto). Es el aporte central del horizonte (§5): separar
   plazo y precio con el reajuste del art. 134 y los índices del BCV (antecedentes §2).
3. **Alertas y reproyección siempre** (H‑D2): al registrar una valuación el sistema compara con el plan, alerta
   con umbrales declarados y reproyecta el término, el costo final y el punto de equilibrio al ritmo real.
4. **Opciones de recuperación bajo demanda** (H‑D2): más cuadrillas, horas extra, partidas en paralelo o aceptar
   el retraso con su costo indirecto, calculadas con el **rendimiento y la cuadrilla de cada APU** y un **factor
   de eficiencia declarado** por rendimientos decrecientes (horizonte §4; Lee, 2022). El usuario elige; la
   decisión rehace plan, curva y punto de equilibrio y queda en el registro.

**Criterio de éxito de la 0.7.0** (horizonte, fase R2): *una obra con retraso detectado, reproyectada y
recuperada con una opción elegida*. Se demuestra con OB‑S2 (§7.1): dos valuaciones, SPI 0,80, término
reproyectado tres días hábiles tarde, cuatro opciones con su costo y una decisión que crea una versión nueva con
su plan, su curva y su registro.

### 1.1 Lo que se encontró en el código (2026‑10‑11, rama `inc/silice`)

- **Rendimiento y cuadrilla.** `ComposicionAPU.rendimiento` (unidades por día) y `LineaManoObra` (cantidad de
  obreros, sueldo, modalidad jornal o destajo) están en el contrato `core/contracts/apu.py`; el costo por día de la
  cuadrilla se obtiene de esas líneas y de `ParametrosCosto` (FCAS, bono) sin tocar el contrato.
- **Plan y curva.** El plan es `PeriodoPlan = (etiqueta, [(código, fracción)])`; `generar_curva` cierra exacto
  en el total (el último período absorbe el residuo) y `plan_de_version` lo recupera de `PlanVersion` (SF‑E6).
  **El plan no tiene fechas ni dependencias** entre partidas.
- **Punto de equilibrio.** `punto_equilibrio(presupuesto, parametros)` (SF‑E3): CV = Σ cantidad × costo
  directo; CF = CV × administración; PE = CF × V / (V − CV); ubicación en la curva; estados tipados.
- **Versiones y registro.** `guardar_edicion` (SF‑E2) crea una versión con `RegistroCambio` por celda y fuente y
  responsable obligatorios, pero fija `motivo="edicion"`. `MOTIVOS_VERSION` admite edición, restauración,
  cotización, revaloración (y `conversion` desde S1). La versión vigente es la de mayor `id` no descartada.
- **Lo que falta y los precedentes.** No hay valuaciones, costos reales ni línea base de control (`Ejecucion`
  solo sirve a los rendimientos medidos de UC‑06). R8–R12 se construyen con su instantánea y entran por `reglas=`
  (SF‑E1), fuera de `REGLAS`: es el patrón de R13 y R14. `core/budget/importacion.py` ya lee XLSX con `openpyxl`
  (C6.4): la importación de valuaciones sigue ese precedente.

## 2. Alcance

**Incluye:** línea base de control y calendario; valuaciones con fuente, en dos estados (presentada y
conformada), anulación sin borrado e importación de Excel; entrega a S1 de lo ejecutado por período; costos
reales con moneda, fecha y fuente; reglas R13 y R14; valor ganado y separación del desvío de control; alertas;
reproyección del término, del costo final y del punto de equilibrio; cuatro opciones de recuperación; decisión
registrada como versión nueva; pantalla «Control de obra»; hojas de control en el Excel de la hoja.

**No incluye:** dependencias entre partidas (red de precedencias, ruta crítica); combinar dos opciones en una
misma partida; proyectar inflación futura (los precios se toman al corte) ni proyectar reajustes futuros (el PE
proyectado suma solo el reajuste ya reconocido, §4.7); deflactar cada costo real a la fecha del corte (§11,
pregunta 5); rutas nuevas de la API (S3 decide); el registro encadenado, el formato del paquete y su firma (S3);
multas contractuales con fuente normativa (no verificadas: la penalización es un dato del contrato).

**Coordinación con otros specs.**

| Con | Qué usa o entrega S2 |
|---|---|
| S1 | **Usa** `MONEDAS`, `moneda_del_proyecto`, `tasa_aplicable` y `convertir` (S1 §5.3) para los costos reales; el **precio del corte** de cada partida sale de S1 por comprobación directa (PU de la versión revalorada por UC‑02) o por escalatoria (`Kⱼ,m` por partida, S1 §8.3); el **reajuste reconocido** (la suma de los estudios de reajuste de S1 **guardados** hasta el corte, nunca uno proyectado; RV‑12) entra al PE proyectado (§4.7). **Entrega** a S1 lo ejecutado por período (RV‑11, criterio en RF‑72): solo las valuaciones **conformadas** no anuladas, cada una asignada al período mensual de la cláusula por su fecha *hasta*; lo ejecutado por encima de lo presupuestado se **guarda** con R13 ERROR (S1 UC‑18 3f se alinea: no rechaza) y el reajuste se calcula sobre `min(Q, q)` con aviso. Un cambio de moneda del proyecto (S1 RF‑64) después de declarar la línea base de control la **invalida**: hay que declararla de nuevo sobre la versión convertida |
| S3 | Las filas de línea base, valuación, conformación, anulación, costo real y decisión viajan en `anexos/control.json` del paquete formato v1 (RV‑8), cubiertas por `huella_anexos` del manifiesto firmado, **sin cadena propia**: las tablas de S2 ya son solo‑agregar, salvo los parámetros de control, que se cambian con su `RegistroCambio` (límite declarado). La reauditoría de S3 §9 recomputa R13–R14 desde ese anexo. La versión que crea una decisión (motivo `recuperacion`) se sella como cualquier otra en el embudo `persistencia.guardar_presupuesto` (RV‑7). S3 asigna rol a registrar, conformar y anular valuaciones, registrar costos y decidir una recuperación (REQ‑4). La «separación del desvío de control» de S2 y la «diferencia entre versiones» de S3 (SL‑E9) son descomposiciones **distintas** (§4.3; RV‑10) |
| S5 | S5‑1 (Alembic) se adelanta a la 0.6.0 (RV‑3): S2 agrega **su revisión** de Alembic con sus tablas aditivas; la prueba de deriva (RNF‑20) las recorre. La base de prueba de la 0.7.0 se genera en la compuerta GS2 con su ficha escrita con el código de esa etiqueta (total literal, huella del informe, filas por tabla) |

Sin S1 la 0.7.0 no se construye (spec maestro §5). Si los precios del corte de una partida no están disponibles,
la separación de esa partida queda **no disponible** (estado tipado), no se supone precio constante.

---

## 3. Requisitos (enmienda a la ERS, IEEE 830)

**Numeración** (spec maestro §9): UC‑19 y UC‑20; RF‑72 a RF‑79; RNF‑15; expedientes SL‑E4 a SL‑E6; reglas R13 y
R14. **Se usan todos; ninguno queda vacante.** Las decisiones de este spec se numeran S2‑R1…, como S1. La meta
comprueba la **presencia** de estos números en la ERS, no conteos absolutos (REQ‑19), para que el orden de fusión
con otros specs no la rompa.

### 3.1 Casos de uso

#### UC‑19 — Registrar una valuación de obra

- **Actor principal:** residente de obra (ERS §2.3; registra lo ejecutado). **Secundarios:** proyectista;
  administrador que revisa. El **inspector** no es usuario: su nombre es la fuente de la valuación.
- **Precondiciones:** versión del contrato guardada; **línea base de control** declarada (versión, perspectiva,
  calendario; RF‑72).
- **Flujo principal:** 1) el actor abre «Control de obra»; 2) escribe la valuación (número, período desde/hasta,
  fecha, inspector) y sus líneas (partida, cantidad del período, fecha de medición opcional), o la importa de
  Excel; 3) declara fuente y responsable; 4) el sistema la guarda **presentada**, **sin modificar ninguna
  anterior**, corre R13 y R14 y emite el informe de control (principio 7); 5) cuando el inspector la conforma, el
  actor registra la **conformación** (fecha, fuente, responsable; una fila aparte, la valuación no cambia); 6) el
  sistema calcula al corte (fecha *hasta*) el valor ganado, las alertas y la reproyección (UC‑20, pasos 1–3) con
  las valuaciones **conformadas** (RV‑18, valor por defecto a ratificar).
- **Flujos alternativos:** *2a* Excel malformado o columnas faltantes: se rechaza con mensaje y fila, sin
  *traceback*, sin escribir nada; *2b* cantidad negativa o no numérica: se rechaza la entrada (una corrección es
  una anulación, 4c); *4a* sin inspector o sin número: se guarda y R14 la marca ERROR; *4b* acumulado de una
  partida mayor que lo presupuestado o partida que el presupuesto no tiene: se guarda y R13 la marca ERROR, con el
  monto como impacto; el sistema ofrece registrar la **variación de obra** por la hoja (UC‑15, versión nueva con
  la cantidad cambiada) y declararla nueva línea base (RF‑72); *4c* anular una valuación: fila de anulación con
  fuente y responsable; la anulada se conserva y deja de contar; *4d* período solapado con otra valuación: R14
  ERROR; *5a* conformar una valuación anulada o ya conformada: se rechaza con mensaje; *5b* una valuación que
  nunca se conforma sigue en R13–R14 pero no entra al valor ganado ni a lo ejecutado que recibe S1.
- **Postcondiciones:** valuación inmutable con su fuente y su estado (presentada o conformada); informe de control
  emitido; ningún presupuesto cambia.

#### UC‑20 — Controlar el avance y recuperar un retraso

- **Actor principal:** proyectista (quien arma). **Secundarios:** gerente y administrador que revisa (consultan).
- **Precondiciones:** línea base de control vigente (no invalidada por un cambio de moneda, RF‑72) y al menos
  una valuación conformada no anulada.
- **Flujo principal:** 1) el sistema calcula al corte PV, EV, AC y sus índices (RF‑75) y separa el desvío
  (RF‑76); 2) evalúa las alertas (RF‑77); 3) reproyecta término, costo final y PE (RF‑77) — pasos 1 a 3
  **siempre**, sin que se pidan; 4) a pedido, calcula las opciones de recuperación con su costo (RF‑78); 5) el
  usuario elige una, declara fuente y responsable; 6) el sistema crea una versión nueva con el plan de la opción,
  su curva y su informe, guarda la decisión con la foto de los indicadores y reproyecta (RF‑79).
- **Flujos alternativos:** *1a* PV = 0 (corte antes de todo trabajo planificado): SPI «no aplica»; *1b* AC = 0:
  CPI «no aplica»; *1c* sin precios del corte (S1) para una partida: separación «no disponible» para ella;
  *1d* un costo real en otra moneda sin tasa aplicable (más de 7 días sin tasa, S1‑R2): el AC de ese costo queda
  «no disponible» y se declara con la lista de esos costos; AC y lo que depende de él (CV, CPI, consumo, EAC, VAC,
  PE proyectado) quedan «no disponible»; PV, EV, SV, SPI, precio y el término se calculan (REQ‑25); *3a* partida
  detenida (PV > 0, EV = 0): se reproyecta al ritmo global con ADVERTENCIA; *3b* SPI global = 0: término «no
  proyectable»; *4a* ninguna opción alcanza el término objetivo: se muestra la mejor y el retraso que queda; *4b*
  sin partidas por empezar: «partidas en paralelo» no aplica; *4c* partida sin mano de obra a jornal (solo destajo
  o sin mano de obra): «más cuadrillas» y «horas extra» dan «no aplica» tipado para ella (§4.6); *5a* el usuario
  no elige: nada cambia salvo lo de los pasos 1–3; *6a* sin fuente o responsable: se rechaza (como UC‑15a).
- **Postcondiciones:** la **línea base no cambia** (S2‑R3); la versión de la decisión es la vigente de la hoja.

**UC que se enmiendan.** UC‑15: una variación de obra es una edición de cantidad (objeto `cantidad`) con su
acta como fuente. UC‑16: el PE de la versión se complementa con el PE proyectado de UC‑20. UC‑18 (S1): desde la
0.7.0 lo ejecutado por período viene de las valuaciones conformadas (RF‑72; RV‑11); en la 0.6.0 se escribe a
mano; el paso 3f deja de rechazar el exceso sobre lo presupuestado y lo marca como R13.

### 3.2 Requisitos funcionales

Prioridad: E = esencial, D = deseable.

| RF | Requisito | UC | Pri. | Fase | Criterio de aceptación |
|---|---|---|---|---|---|
| RF‑72 | El sistema registrará la **línea base de control** (versión, perspectiva *costo* o *precio*, fecha desde, fuente, responsable) y su **calendario** (fecha de inicio, días hábiles por período, feriados), y valuaciones con número, período, fecha, inspector y líneas por partida, en estado *presentada* hasta que se registre su **conformación** (fecha, fuente, responsable; RV‑18); las valuaciones no se editan ni se borran: se anulan con fuente. Entregará a S1 **lo ejecutado por período** (`ejecutado_por_periodo`, RV‑11): solo valuaciones conformadas no anuladas, cada una asignada entera al período mensual de la cláusula que contiene su fecha *hasta*, con la cantidad del período y la **cantidad reajustable** `min(Q acumulado al cierre, q) − min(Q acumulado al cierre anterior, q)`, con aviso cuando difieren. Un cambio de moneda del proyecto posterior a la línea base de control la **invalida** | UC‑19 | E | S2‑1 | OB‑S2 se registra completa; editar o borrar una valuación no es posible por ninguna función de `core`; anular deja la anulada en la base y fuera del cálculo; cantidad negativa → `ValueError`; OB‑S2 entrega para noviembre de 2026 A 90 y B 60 (V‑01 y V‑02 conformadas) y la V‑S presentada no entra; con una valuación conformada más de B 150 en noviembre, B entrega cantidad 210, reajustable 200 y el aviso, y R13 da ERROR; una valuación del 2026‑11‑30 al 2026‑12‑04 va entera a diciembre; tras convertir la moneda del proyecto, `instantanea_control` rechaza con «línea base invalidada: declárela de nuevo» |
| RF‑73 | El sistema importará valuaciones (con su conformación, si la trae) y costos reales desde un XLSX con las hojas y columnas de §6.2, con informe de importación; un archivo malformado se rechaza entero | UC‑19 | E (decisión H‑D5; cae solo si Eugenio lo acepta, REQ‑21) | S2‑1 | el XLSX de OB‑S2 da las mismas valuaciones que la entrada a mano; cada malformación de §7.2 (fila RF‑73) da su mensaje sin *traceback* y sin escribir |
| RF‑74 | Al registrar, importar, conformar o anular, el sistema ejecutará **R13 y R14** (§3.4) sobre las valuaciones no anuladas (presentadas y conformadas) y emitirá el informe de control | UC‑19 | E | S2‑1 | la valuación sembrada V‑S de §7.1 da **exactamente** los seis hallazgos de §7.1 (regla, severidad, impacto); cada frontera de §7.3; R13 sobre una valuación de SIS‑001 (presupuesto de sistemas) da su conjunto exacto (ARQ‑H3) |
| RF‑75 | El sistema calculará al corte PV, EV, AC, SV, CV, SPI, CPI, BAC, EAC (dos métodos), VAC y la fecha estimada de término (dos métodos) con las fórmulas de §4.2, en la moneda del proyecto, solo con valuaciones conformadas; los costos reales se convierten con la tasa de su fecha (S1) y, sin tasa aplicable, su AC queda «no disponible» y se declara | UC‑20 | E | S2‑2 | OB‑S2 da los valores de §7.1 a ± 0,01 (montos) y ± 0,0001 (índices); las fechas, exactas; un costo real en Bs con más de 7 días sin tasa: AC, CV, CPI, consumo y EAC «no disponible» con ese costo listado, y PV, EV, SPI iguales a los de §7.1 (REQ‑25) |
| RF‑76 | El sistema hará la **separación del desvío de control** en **plazo** (SV), **precio** y **consumo** (§4.3; término cruzado en el consumo), con el método y la fuente del precio del corte (S1), y la identidad CV = precio + consumo será **exacta**. Es distinta de la «diferencia entre versiones» de S3 (RV‑10) | UC‑20 | E | S2‑2 | OB‑S2: precio −60,00, consumo −20,00, CV −80,00; la identidad con `Decimal` da diferencia cero en OB‑S2 y en el generador de RNF‑15 |
| RF‑77 | Al registrar o conformar una valuación, el sistema evaluará las **alertas** AL‑1 a AL‑6 con sus umbrales declarados (§4.5) y **reproyectará** plan, término, costo final y PE (§4.4, §4.7), sin que se pida | UC‑19, UC‑20 | E | S2‑2 | OB‑S2: las alertas exactas de §7.1 en sus dos escenarios (sin reajuste y con el reajuste reconocido); término reproyectado 2026‑12‑02; plan reproyectado de §7.1; cada frontera de umbral de §7.3 |
| RF‑78 | A pedido, el sistema calculará las opciones **más cuadrillas, horas extra, partidas en paralelo y aceptar el retraso** (§4.6) desde el rendimiento y la cuadrilla del APU de cada partida, con su término, costo directo adicional, costo indirecto, EAC y PE, y la lista de supuestos usados con su naturaleza (fuente o supuesto declarado) | UC‑20 | E | S2‑3 | OB‑S2: los cuatro resultados de §7.1 con el PE' de sus dos escenarios; horas extra nunca superan los límites de la LOTTT (§4.6.2); cada supuesto aparece en la salida; una partida de TI‑001 y una de SIS‑001 sin mano de obra a jornal (§4.6) dan «no aplica» tipado en cuadrillas y horas extra, sin división entre cero (ARQ‑H3) |
| RF‑79 | Elegir una opción creará una **versión nueva** (motivo `recuperacion`) con el plan de la opción, su curva y su informe, un `RegistroCambio` por fracción del plan que cambió y una `DecisionRecuperacion` con la foto de indicadores, opción y supuestos; fuente y responsable obligatorios; la línea base no cambia | UC‑20 | E | S2‑3 | tras elegir «más cuadrillas» en OB‑S2: R2 y R7 sin hallazgos, la curva cierra en el total, los registros de §7.1, la decisión recarga idéntica y el SPI al mismo corte sigue en 0,80 |

### 3.3 Requisito no funcional (ISO/IEC 25010)

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑15 | Eficiencia de desempeño | En `ui.control`, sin Streamlit, desde registrar una valuación hasta tener informe de control, indicadores, alertas y reproyección: mediana ≤ 2 s; calcular las cuatro opciones: mediana ≤ 2 s; para una obra de 500 partidas, 52 períodos semanales y 26 valuaciones | `scripts/medir_rnf15.py` con un generador determinista versionado (`scripts/generar_obra_control.py`, en S2‑0); una corrida de calentamiento y la mediana de cinco. Veredicto en el equipo de desarrollo, como RNF‑03 y RNF‑11; la CI ejecuta el script en Linux y Windows y **registra** la cifra sin romper la corrida; la meta comprueba que el script corrió y dejó su cifra: sin cifra es FALLA, no OK (PRU‑H21) |

### 3.4 Reglas nuevas R13 y R14

En `core/verification/valuaciones.py`; implementan `ReglaVerificacion` (contrato sin cambios), se construyen con
la **instantánea de control** (línea base, calendario, plan de la línea base, valuaciones no anuladas hasta el
corte, presentadas y conformadas: el documento se audita aunque aún no cuente para el valor ganado) y entran por
`reglas=` como R8–R12; **no** entran en `REGLAS` (el 7 de 7 y las huellas de RNF‑04 no se mueven). Sus hallazgos
citan en `origen_ids` la clave de la línea (`valuacion:<número>:<código>`) **y** el `origen_id` del ítem de la
partida, para que el informe atribuya la partida (C5.1).

**Contextos** (tabla única de reglas externas del maestro, RV‑9). R13–R14, con la instantánea de control como
entrada, corren: en la hoja y en «Control de obra» (corte = el que el usuario elige, por defecto la fecha *hasta*
de la última valuación); en la reauditoría del paquete de S3 §9, desde `anexos/control.json` (corte = el
declarado en el anexo); en `POST /v1/auditorias` y en el experimento de S4, según lo que fije esa tabla. Toda
reevaluación es **en memoria** y nunca reescribe filas guardadas (no cambia `huella_contenido`).

| Regla | Condición | Severidad | Impacto |
|---|---|---|---|
| **R13 Valuación dentro del presupuesto** | (a) acumulado no anulado de una partida > cantidad de la línea base | ERROR | exceso × unitario base |
| | (b) partida valuada que la línea base no tiene | ERROR | sin unitario: no se cuantifica y se declara |
| | (c) partida presupuestada que el plan de la línea base no programa en ningún período | ADVERTENCIA | — |
| **R14 Fuente y fechas de la valuación** | (a) falta número, inspector o fecha | ERROR | — |
| | (b) *desde* > *hasta*; o fecha de la valuación anterior a *hasta*; o *hasta* posterior al corte; o *desde* anterior al inicio del calendario | ERROR | — |
| | (c) período solapado con otra valuación no anulada; o número repetido | ERROR | — |
| | (d) fecha de medición de una línea fuera de [*desde*, *hasta*] | ERROR | — |
| | (e) números no consecutivos cuando siguen el patrón prefijo + número (`V-01`, `V-03`) | ADVERTENCIA | — |
| | (f) hueco de días hábiles entre dos valuaciones consecutivas | INFO | — |

R13 compara con la **línea base vigente al corte**: una variación registrada (versión nueva con la cantidad y
declarada línea base) es lo que la hace pasar. La igualdad exacta pasa (`≤`); no hay tolerancia de medición
(§11, pregunta 6). R13 sirve igual a un presupuesto de cualquier dominio: se prueba también sobre SIS‑001
(ARQ‑H3). En R14(f), un hueco es al menos un día hábil sin cubrir entre el *hasta* de una valuación y el *desde*
de la siguiente: de viernes a lunes no hay hueco.

---

## 4. Definiciones de cálculo

### 4.1 Notación y precisión

Para cada partida *p* de la línea base: `q_p` cantidad; `u_p` **unitario base** según la perspectiva (*costo*:
costo directo unitario de su `ResultadoAPU`; *precio*: precio unitario); `f_p,n` fracción del plan en el período
*n*; `n_p` número de períodos con `f_p,n > 0`; `inicio_p` el primero. `L` = días hábiles por período; `N` =
períodos del plan; `D = N · L`. Al corte *t*: `Q_p` acumulado de las valuaciones **conformadas** no anuladas
(S2‑R14); `qe_p = min(Q_p, q_p)` (S2‑R8); `u'_p` **unitario del corte** (S1); `AC` costo real.

Todo en `Decimal`. Las divisiones van en un contexto local de 28 dígitos con `ROUND_HALF_EVEN`, fijado dentro de
cada función, como S1 §5.3 (DRY: una sola convención). **Se multiplica antes de dividir** y se divide una sola vez
cuando la fórmula lo permite (como SF‑E3), para que los oráculos exactos lo sean. Se redondea solo al presentar.

**Calendario.** Días hábiles = lunes a viernes menos los feriados declarados (SUPUESTO_DECLARADO; la LOTTT,
art. 173, limita la jornada a cinco días por semana para el trabajador, no para la obra). El período *n* abarca los
días hábiles `(n−1)·L + 1 … n·L` desde la fecha de inicio. Dentro de un período el trabajo planificado es
uniforme (S2‑R9).

### 4.2 Valor ganado (definiciones del sistema)

| Indicador | Definición | Si no aplica |
|---|---|---|
| BAC | `Σ q_p · u_p` | — |
| PV(t) | `Σ_p q_p · u_p · F_p(t)`, con `F_p(t)` = fracciones de los períodos terminados más la parte proporcional, por días hábiles, del período que contiene *t* | — |
| EV | `Σ qe_p · u_p` | — |
| AC | perspectiva *costo*: Σ costos reales declarados hasta *t*, cada uno convertido con `tasa_aplicable(fecha)` (S1); perspectiva *precio*: `Σ qe_p · u'_p` (lo que se paga con el precio del corte) | un costo sin tasa aplicable (S1‑R2): «no disponible», declarado con la lista de esos costos, y con él CV, CPI, EAC, VAC, consumo y PE proyectado (S2‑R17) |
| SV, CV | `EV − PV`, `EV − AC` | — |
| SPI, CPI | `EV / PV`, `EV / AC` | PV = 0 o AC = 0: «no aplica» |
| EAC (índice) | `BAC / CPI` | CPI no aplica |
| EAC (sistema) | `AC + Σ_p (q_p − qe_p) · u'_p / CPIc`, con `CPIc = Σ qe_p · u'_p / AC` (§4.3) | sin precio del corte: «no disponible» |
| VAC | `BAC − EAC (sistema)` | — |
| Término (índice) | día hábil número `⌈D / SPI⌉` desde el inicio | SPI no aplica o 0 |
| Término (plan) | día hábil del fin del plan reproyectado (§4.4) | «no proyectable» |

**Fuente.** Las definiciones de SV, CV, SPI, CPI, EAC = BAC/CPI y del término D/SPI son las de la práctica del
valor ganado, pero **ninguna fuente que las contenga está verificada** en el repositorio (antecedentes §2 verifica
trabajos que las usan, no su definición). La tarea S2‑0 encarga al verificador de hechos localizar y verificar una
(por ejemplo, la publicación de valor ganado del PMI o una práctica recomendada de AACE; **sin verificar**) antes
de citarlas en la tesis; si no se verifica ninguna, la tesis las presenta como definiciones del sistema (S2‑R11).
El **EAC del sistema** y la separación de §4.3 son propios de este trabajo y se declaran así.

**Perspectiva** (S2‑R2): *costo* es la de quien arma (contratista): `u_p` es costo directo, el mismo CV del punto
de equilibrio (SF‑E3), y AC lo que gastó. *Precio* es la de quien revisa: `u_p` es el PU del contrato y AC lo que
paga con el precio del corte; en esa perspectiva el consumo es cero por construcción y el PE no aplica (es del
contratista).

### 4.3 Separación del desvío de control: plazo, precio y consumo

Nombre propio (RV‑10): **separación del desvío de control**, con el término cruzado en el **consumo**. Es una
descomposición **distinta** de la «diferencia entre versiones» de S3 (SL‑E9: precio = `(PU₂ − PU₁)·q₂`, término
cruzado en el precio), que compara dos versiones de un presupuesto y no una obra contra su línea base. Ninguna
de las dos reutiliza a la otra: S2 no llama a SL‑E9 ni SL‑E9 calcula esta separación.

- **Plazo:** `SV = EV − PV`. Las dos cantidades están a precios de la línea base, así que SV es solo cantidad y
  tiempo, sin inflación.
- **Precio:** `ΔP = Σ qe_p · (u_p − u'_p)`. Es lo que la obra **ejecutada** cuesta de más (signo negativo) con los
  precios del corte; sobre la cantidad ejecutada, igual que la base del reajuste del art. 134 («solo lo ejecutado
  en el período», transcripción a cotejar; S1 §8.2).
- **Consumo:** `ΔC = Σ qe_p · u'_p − AC`. Lo que se gastó de más o de menos a precios del corte: rendimiento,
  desperdicio, cuadrillas.
- **Identidad:** `CV = ΔP + ΔC` exacta, porque `Σ qe_p·u_p − AC = Σ qe_p·(u_p − u'_p) + (Σ qe_p·u'_p − AC)`.
- **Al término:** `VAC = VAC_precio + VAC_consumo`, con `VAC_precio = −Σ q_p · (u'_p − u_p)` (toda la obra a
  precios del corte) y `VAC_consumo = VAC − VAC_precio`.

**Relación con la fuente.** La práctica que separa precio y cantidad (Humphreys & Associates, blog de
consultoría, VERIFICADO como tal en antecedentes §2) usa precio = (PU de BCWP − PU de ACWP) × cantidad de ACWP y
uso = (cantidad de BCWP − cantidad de ACWP) × PU de BCWP. Las dos descomposiciones suman lo mismo; **difieren en
dónde queda el término cruzado** (variación de precio × variación de cantidad): allí en el precio, aquí en el
consumo. Se elige así para que el componente de precio coincida con la base del reajuste reclamable (S2‑R1).

**Precio del corte** `u'_p` (S1): por **comprobación directa**, el unitario de la partida en la versión
revalorada por UC‑02 a la fecha del corte (costo directo o PU según la perspectiva); por **escalatoria**,
`u_p · (1 + (K_p,m − 1)·(1 − R))` con el coeficiente por partida de S1 §8.3 (INDICIO allí declarado). El
resultado cita el método, el estudio o la versión y la importación de índices; sin ninguno, «no disponible».

### 4.4 Reproyección al ritmo real

Sea *c* el último período terminado al corte. Para cada partida con obra pendiente (`ρ_p = 1 − qe_p/q_p > 0`):

1. **Índice de la partida** `s_p`: `EV_p / PV_p` si `PV_p > 0` y `EV_p > 0`; el SPI global si `PV_p = 0` (sin
   evidencia propia) o si `EV_p = 0` con `PV_p > 0` (partida detenida, AL‑6); 1 si el SPI global no aplica;
   «no proyectable» si el que corresponde es 0 (S2‑R4).
2. **Ritmo** `r_p = s_p / n_p` (fracción por período: el ritmo medio planificado escalado por su índice).
3. **Inicio de lo pendiente:** el período *c*+1 si la partida ya empezó o su inicio planificado ya pasó; si no,
   su `inicio_p` (sin dependencias declaradas, las partidas son independientes: S2‑R4). Si el corte cae dentro
   del período *c*+1, ese período aporta solo `r_p` × (días hábiles que le quedan / `L`).
4. **Reparto:** cada período recibe `min(r_p, pendiente)`; la última fracción es el resto exacto (como
   `generar_curva`), así que la partida suma 1.
5. **Lo ejecutado** de cada valuación conformada entra como fracción `cantidad/q_p` en el período que contiene su *hasta*;
   fracciones de la misma partida en el mismo período se suman.
6. **Fin de la partida** en días hábiles: `(k − 1)·L + (x_k / r_p)·L`, con *k* su último período y `x_k` su
   última fracción. **Término (plan)** = día hábil `⌈máx_p fin_p⌉`; si nada queda pendiente, la fecha *hasta* de la
   última valuación.

El plan reproyectado (pasado ejecutado más futuro proyectado) es un `PeriodoPlan` válido: `generar_curva` lo
acepta y la curva cierra en el total. Los períodos que pasan de *N* toman la etiqueta del último con su número
siguiente si sigue el patrón «texto número» (`Semana 5`), o «Período *n*».

### 4.5 Alertas

`Alerta(codigo, severidad, descripcion, valor_observado, umbral, naturaleza_umbral)`, con `Severidad` del
contrato. Los umbrales viven en `ParametrosControl` (§6.1), son **SUPUESTO_DECLARADO** sin fuente, editables por
proyecto con fuente y su `RegistroCambio` (objeto `parametro`). Si el indicador de una alerta está «no
disponible» o «no aplica» (UC‑20 1a–1d), la alerta no se evalúa y la pantalla lo dice. AL‑4 se evalúa sobre la
reproyección (sin opción) con el reajuste reconocido al corte (§4.7).

| Código | Condición | Severidad (umbral por defecto) |
|---|---|---|
| AL‑1 Retraso | SPI < 1 | ADVERTENCIA si SPI ≥ 0,90; ERROR si SPI < 0,90 |
| AL‑2 Sobrecosto | CPI < 1 | ADVERTENCIA si CPI ≥ 0,90; ERROR si CPI < 0,90 |
| AL‑3 Término | término (plan) posterior al del plan base | ADVERTENCIA si el retraso ≤ 10 % de *D*; ERROR si mayor |
| AL‑4 Equilibrio | PE proyectado `NO_SE_ALCANZA` o `NO_EXISTE` | ERROR |
| | PE proyectado sube más de 10 puntos porcentuales sobre el de la línea base | ADVERTENCIA |
| AL‑5 Precio | `|ΔP| ≥ 5 %` de EV | INFO: «evaluar el reajuste (S1; LCP art. 133, a cotejar)» |
| AL‑6 Detenida | `PV_p > 0` y `EV_p = 0` | ADVERTENCIA por partida |

### 4.6 Opciones de recuperación (bajo demanda)

**Objetivo:** término objetivo `T*` = fin del plan base (`D`), o una fecha que el usuario declara. **Partidas que
determinan el término:** las de `fin_p > T*` en la reproyección. Cada opción se calcula sola (sin combinar) y
devuelve: plan reproyectado, término, días de retraso que quedan, costo directo adicional, costo indirecto
(`CF' − CF`, §4.7), penalización, EAC de la opción, PE proyectado y **supuestos usados** con su naturaleza.

**Componente dependiente del tiempo** del APU de cada partida (de la composición de la línea base, SF‑E6):
`C_d` = costo diario de la cuadrilla y el equipo = `Σ_jornal cantidad·sueldo·(1 + FCAS) + bono·obreros a jornal +
Σ cantidad·precio·depreciación`; `S` = `Σ_jornal cantidad·sueldo`; `R` = rendimiento. Las líneas a destajo se
pagan por unidad y los materiales no dependen del tiempo: ninguna opción los cambia. Con precios del corte
disponibles, `C_d` se toma de la composición revalorada (S1); si no, de la línea base, declarándolo.

**Partidas sin mano de obra a jornal** (ARQ‑H3): una partida solo a destajo o sin mano de obra tiene `S = 0`;
con rendimiento ausente o cero no hay ritmo que escalar. En
esos casos «más cuadrillas» y «horas extra» devuelven para esa partida el estado tipado **«no aplica»** con su
motivo (`sin mano de obra a jornal` o `sin rendimiento`), **sin dividir**: la función lo decide antes de
calcular `C_d/R`. Si todas las partidas que determinan el término están en ese caso, la opción entera es «no
aplica». «Aceptar el retraso» y «partidas en paralelo» no dependen de la cuadrilla y se calculan igual. Las
fronteras se toman de presupuestos de otro dominio, TI‑001 y SIS‑001: S2‑0 fija con su código una partida de
cada uno sin mano de obra a jornal; si ninguna lo es tal cual, siembra una variante declarada de ese caso (la
composición de esas partidas no se revisó al escribir este spec).

#### 4.6.1 Más cuadrillas

Con *k* cuadrillas iguales a la del APU, la *j*‑ésima rinde `η^(j−1)` de la primera (**rendimientos
decrecientes**): `E(k) = Σ_{j=1..k} η^(j−1)`. El ritmo pasa a `r_p · E(k)`. Para cada partida que determina el
término se toma el menor `k ∈ {2 … k_máx}` con `fin_p ≤ T*`, o `k_máx` si ninguno alcanza (y la salida da el
retraso que queda, flujo 4a). Costo adicional:

`ΔCD_p = q_rest,p · (C_d/R) · (k − E(k)) / E(k)`, calculado como `(q_rest·C_d·(k − E(k))) / (R·E(k))`.

Supuestos por defecto (SUPUESTO_DECLARADO, S2‑R5): `η = 0,80`, `k_máx = 3` (frentes de trabajo). **Base del
método:** Lee (2022), *Evaluating construction delays using productivity-based resource reallocation for economic
feasibility*, ECAM 30:1679‑1696, DOI 10.1108/ECAM-09-2019-0503 (VERIFICADO por Crossref en antecedentes §3:
productividad, precio unitario y carga de cada cuadrilla para la duración reducible y los trabajadores
necesarios). La forma geométrica de `E(k)` y los valores de `η` y `k_máx` **no** salen de Lee: son de este spec.

#### 4.6.2 Horas extra

`h` horas extra por día (`h ≤ h_máx`). Límites **verificados** en la LOTTT del repositorio (G.O. 6.076 Ext.,
07‑05‑2012): jornada diurna ≤ 8 h diarias y 40 semanales en cinco días (art. 173); duración efectiva con extras
≤ 10 h diarias, ≤ 10 h extra semanales y ≤ 100 h extra por año (art. 178); recargo **de por lo menos 50 %** sobre
el salario de la jornada ordinaria (art. 118); permiso de la Inspectoría del Trabajo (art. 182). De ahí
`h_máx = 2` con cinco días por semana, y el sistema rechaza una opción que lleve a un obrero a más de 100 h extra
en el año del contrato. El permiso del art. 182 aparece como requisito en la salida.

Ritmo: `r_p · (1 + (h/8)·η_he)`. Costo de un día de cuadrilla: `C_d + OT`, con `OT = (h/8)·(1 + recargo)·S·(1 +
FCAS·a)`, donde `a` = 1 si el FCAS se aplica a las horas extra (por defecto, S2‑R6). Costo adicional:

`ΔCD_p = q_rest,p · ( (C_d + OT) / (R·(1 + h·η_he/8)) − C_d/R )`.

Supuestos por defecto: `η_he = 0,80` (SUPUESTO_DECLARADO), `recargo = 0,50` (mínimo legal, art. 118), `a = 1`,
el bono de alimentación es por jornada y no cambia, el equipo se cobra por día y no cambia (SUPUESTO_DECLARADO).

#### 4.6.3 Partidas en paralelo

Partidas sin empezar con `inicio_p > c + 1`: su inicio se adelanta al período *c*+1. **Exige que el usuario declare
que no dependen** de las que están en curso (declaración con fuente, que queda en la decisión), porque el plan no
tiene dependencias (S2‑R4). Costo directo adicional 0 según el APU; la salida informa el máximo de cuadrillas
simultáneas por período. Sin partidas así: «no aplica».

#### 4.6.4 Aceptar el retraso

Plan = la reproyección. Costo = costo indirecto `CF' − CF` (§4.7) + `penalización diaria × días de retraso`
(dato del contrato, por defecto 0, con fuente; ninguna norma verificada la fija).

### 4.7 Punto de equilibrio proyectado (perspectiva *costo*)

`V' = V + reajuste reconocido`. El **reajuste reconocido** (RV‑12, S2‑R15) es la suma de los montos de los
estudios de reajuste de S1 **guardados** con fecha de cálculo ≤ corte, en la moneda del proyecto: cada uno es el
reajuste de lo ejecutado en sus períodos (art. 134, «solo lo ejecutado en el período», S1 §8.2), con lo
ejecutado que S2 le entrega (RF‑72), por el mecanismo de su cláusula (con `ambos`, §11 pregunta 10). **Nunca**
se suma un reajuste proyectado sobre la obra pendiente ni una comprobación de toda la obra, que S1 no produce;
sin estudio guardado, 0. La salida cita los estudios sumados. `equilibrio_proyectado` es pura y recibe el
reajuste reconocido como dato; `ui.control` lo arma desde los estudios guardados.

`CV' = EAC (sistema) + ΔCD` de la opción; `CF' = CF · D'/D`, con `D'` el término proyectado en días hábiles
(S2‑R7: el costo fijo se causa en el tiempo); PE' = `CF' · V' / (V' − CV')` con los estados de SF‑E3
(`V' − CV' ≤ 0`: `NO_EXISTE`; `PE' > V'`: `NO_SE_ALCANZA`; `PE' = V'` se alcanza). Ubicación: el período de la
curva reproyectada cuyo acumulado, como fracción del total, alcanza `PE'/V'`. Con una obra que va **exactamente según un plan de fracciones iguales por partida** (una
valuación por período con lo planificado, costos reales iguales al valor ganado, precios del corte iguales a los base, sin reajuste reconocido), EAC = BAC,
`D' = D`, la curva reproyectada es la del plan y **PE' = PE de SF‑E3** con su misma ubicación (prueba de
coherencia).

---

## 5. Arquitectura

### 5.1 Principio que se conserva

NORMAS §2 y spec SF §5.1: lo genérico de cualquier presupuesto va en `core/` con expediente; nada de S2 depende de
un dominio ni de una especialidad. **Ningún contrato de `core/contracts/` cambia**: las valuaciones, los costos
reales, las alertas y las opciones son tipos de `core/budget`, no de los contratos; R13 y R14 subclasifican
`ReglaVerificacion` tal como es. Si al construir apareciera la necesidad de tocar un contrato, la fase se detiene
y se registra (NORMAS §5).

### 5.2 Vista lógica

| Paquete | Qué contiene | Importa | Toca `core/` |
|---|---|---|---|
| `core/models/control.py` (nuevo) | tablas aditivas de §6.1, en módulo propio y reexportadas desde `core.models` (archivos calientes, RV‑2); su revisión de Alembic (RV‑3) | — | **SL‑E4, SL‑E6** |
| `core/models/entidades.py` | `MOTIVOS_VERSION` + `recuperacion` (una línea) | — | **SL‑E6** |
| `core/budget/valuaciones.py` (nuevo) | tipos `LineaBaseControl`, `Calendario`, `Valuacion`, `LineaValuacion`, `CostoReal`; `registrar_linea_base`, `registrar_valuacion`, `conformar_valuacion`, `anular_valuacion`, `registrar_costo`, `instantanea_control` (rechaza una línea base invalidada por cambio de moneda), `ejecutado_por_periodo` (para S1, RF‑72); `leer_valuaciones_excel` (fuente única del formato, §6.2); `tabla_valuaciones` (`TablaExportable`); `anexo_control` (las filas de §6.1 para `anexos/control.json` de S3) | `core.models`, `openpyxl`, `core.catalog.moneda` (S1) | **SL‑E4** |
| `core/verification/valuaciones.py` (nuevo) | `ValuacionDentroDelPresupuesto` (R13), `FuenteYFechasDeValuacion` (R14); fuera de `REGLAS` | `core.contracts` | **SL‑E4** |
| `core/budget/calendario.py` (nuevo) | `dias_habiles`, `dia_habil`, `periodo_de` (puras) | — | **SL‑E5** |
| `core/budget/valor_ganado.py` (nuevo) | `PreciosDelCorte`, `ParametrosControl`, `Indicadores`, `Separacion`, `Alerta`, `Reproyeccion`; `indicadores`, `separar_desvio`, `reproyectar`, `alertas`, `equilibrio_proyectado` (puras); `tabla_indicadores` | `core.budget.curva`, `core.budget.equilibrio`, `core.budget.calendario` | **SL‑E5** |
| `core/budget/equilibrio.py` | se extrae `equilibrio(venta, costo_variable, costo_fijo, curva)` (pura); `punto_equilibrio` la llama con los mismos argumentos que hoy | — | **SL‑E5** |
| `core/budget/recuperacion.py` (nuevo) | `costo_diario`, `opcion_cuadrillas`, `opcion_horas_extra`, `opcion_paralelo`, `opcion_aceptar`, `opciones` (puras); `aplicar_decision` (persistencia, una transacción) | `core.contracts.apu`, `core.budget.valor_ganado`, `core.budget.edicion` | **SL‑E6** |
| `core/budget/edicion.py` | `guardar_edicion(..., motivo="edicion")`: el motivo pasa a ser parámetro, validado contra `MOTIVOS_VERSION` | — | **SL‑E6** |
| `ui/control.py` (nuevo, sin Streamlit) | borrador de la valuación, llamada a `core`, armado de tablas y de `hojas_extra` del Excel | `core` | no |
| `ui/paginas/control.py` (nueva), `ui/barra.py` | pantalla «Control de obra» (sección Trabajo) y herramienta «Registrar valuación» | `ui.*` | no |

Reglas de arquitectura en su **propio archivo** `tests/unit/test_arquitectura_s2.py` (RV‑2): `ui/control.py` no
importa nada de `PROHIBIDOS_EN_UI` (`streamlit`, `pandas`, `ui.caso`; la lista se importa, no se copia);
`core/budget/valor_ganado.py`, `calendario.py` y las funciones de opción de `recuperacion.py` no importan
`sqlalchemy` (prueba nueva de pureza).

### 5.3 Vista de procesos

```
registrar valuación (UC-19)                         recuperar (UC-20, bajo demanda)
ui.control ──> core.budget.valuaciones.registrar     ui.control ──> recuperacion.opciones(instantánea,
  (o leer_valuaciones_excel ──> informe previo)          composiciones de la línea base, parámetros)
  ──> instantanea_control(corte = hasta)              ──> el usuario elige, fuente y responsable
  ──> auditar(presupuesto, reglas=(R13, R14))         ──> aplicar_decision: elaborar(plan de la opción)
  ──> valor_ganado.indicadores / separar_desvio           ──> guardar_edicion(motivo="recuperacion",
  ──> reproyectar ──> alertas ──> equilibrio_proyectado        cambios = fracciones del plan, gancho =
  (todo puro, recalculado; nada derivado se guarda)            DecisionRecuperacion) ──> reproyectar
```

**Qué se guarda y qué se recalcula** (S2‑R13): se guardan las **entradas** (línea base, calendario, valuaciones,
conformaciones, anulaciones, costos reales, parámetros) y la **decisión** con la foto de lo que el usuario vio;
los indicadores, las alertas, los hallazgos de R13–R14 y la reproyección se **recalculan** (deterministas, en
memoria, sin reescribir filas; RV‑9). Los hallazgos de R13 y R14 no entran al informe guardado de ninguna
versión, así que RF‑62 no se afecta.

**Persistencia de la decisión.** `aplicar_decision` crea la versión por `guardar_edicion(motivo="recuperacion")`,
que pasa por el embudo único `core/budget/persistencia.guardar_presupuesto` con `usuario` obligatorio; allí S3
sella toda versión de `MOTIVOS_VERSION` (RV‑7). S2 no agrega otro camino que cree versiones.

### 5.4 Expedientes de `core/` (resumen; el texto completo va en `docs/bitacora/2026-10-silice-s2-expedientes.md`, commiteado antes del código)

| Expediente | Regla que lo motiva | Por qué es genérico | Prueba que lo demuestra | Impacto | Costo si es erróneo |
|---|---|---|---|---|---|
| **SL‑E4** Valuaciones, línea base de control y su auditoría | H‑D5; RF‑72 a RF‑74; principio 7 | toda obra se valúa por cantidades de sus partidas, sea del dominio que sea | `test_valuaciones.py` (OB‑S2 a mano y por Excel; inmutabilidad; conformación; anulación), `test_ejecutado_por_periodo.py` (RF‑72: asignación por *hasta*, solo conformadas, reajustable con `min`, línea base invalidada por cambio de moneda), `test_r13_r14.py` (conjunto exacto de V‑S, SIS‑001 y fronteras), `test_base_anterior_abre_con_tablas_de_control` | 8 tablas aditivas en `core/models/control.py` y su revisión de Alembic; ninguna lectura anterior cambia; R13–R14 fuera de `REGLAS` | una revisión de Alembic más (RV‑3); severidades = parámetros |
| **SL‑E5** Valor ganado, separación del desvío de control y reproyección | H‑D2; RF‑75 a RF‑77; aporte central del horizonte §5 | se calcula sobre `Presupuesto`, plan y valuaciones, sin conocer dominios | `test_valor_ganado.py` (OB‑S2, §7.1), `test_identidad_separacion` (también con el generador), `test_equilibrio_extraido` (**TI‑001 sigue en 28 586,76 USD, Día 6**, literal sin editar), `test_pe_proyectado_coincide_con_sf_e3_segun_plan`, `test_pe_proyectado_dos_escenarios` (sin reajuste y con el reconocido de §7.1) | `equilibrio.py` se refactoriza sin cambiar su resultado; funciones puras nuevas | si el tutor prefiere otra separación u otro EAC, cambian dos funciones puras y su memoria (S2‑R1, S2‑R11) |
| **SL‑E6** Opciones de recuperación y decisión | H‑D2; RF‑78, RF‑79; horizonte §4 (Lee 2022) | el costo sale del rendimiento y la cuadrilla de cualquier APU | `test_recuperacion.py` (cuatro opciones de OB‑S2; límites de la LOTTT; monotonía: más *k* nunca alarga; «no aplica» sin jornal en TI‑001 y SIS‑001), `test_decision_crea_version.py` (registro, curva, línea base intacta), `test_guardar_edicion_motivo_por_defecto` (SF‑E2 sin cambios) | `guardar_edicion` gana un parámetro con valor por defecto; un motivo más; una tabla | cambiar `η`, `k_máx` o `a` es un parámetro; cambiar el modelo `E(k)` es una función pura (S2‑R5) |

### 5.5 Interfaz: pantalla «Control de obra»

Una pantalla de la sección Trabajo, con cinco pestañas: **Línea base** (versión, perspectiva, calendario,
parámetros de control con su naturaleza visible); **Valuaciones** (tabla editable para la nueva, importación de
Excel con informe previo, conformar y anular con fuente; las guardadas en solo lectura con su estado presentada
o conformada; columna Estado con el peor hallazgo de R13–R14, como RF‑55); **Valor ganado** (tabla de §4.2,
curva PV/EV/AC en el tiempo, separación del desvío de control en plazo, precio y consumo, cada monto en las dos
monedas con la tasa del corte, S1; los «no disponible» con su motivo); **Alertas y reproyección** (siempre
visibles al abrir: alertas AL‑1 a AL‑6, término por los dos métodos, EAC, PE proyectado con los estudios de
reajuste que suma, plan reproyectado); **Recuperación**
(botón «Calcular opciones», una fila por opción con término, costos, PE y supuestos; elegir pide fuente y
responsable). El Excel de la hoja (SF‑E4, `hojas_extra`) agrega «Valuaciones», «Valor ganado» y «Decisiones»;
`exportar_excel` conserva sus cuatro hojas. Los textos que vienen de fuera (inspector, observación y fuente de un
XLSX importado, o de un `anexos/control.json` recibido) se muestran con `ui/texto_seguro()` (RV‑14).

---

## 6. Modelo de datos

### 6.1 Tablas aditivas (ruling SF3‑E0; enmienda a `modelo_datos.md` §2.6)

En `core/models/control.py`, reexportadas desde `core.models`, y creadas por la revisión de Alembic de S2 (RV‑3);
viven en la base del caso (`casos\*.db`, RV‑4).

| Tabla | Columnas | Notas |
|---|---|---|
| `linea_base_control` | `id`, `proyecto_id`, `presupuesto_id` (versión), `desde` (fecha), `perspectiva` (`costo`/`precio`), `fuente`, `responsable`, `fecha_hora` | la vigente al corte es la de mayor `desde` ≤ corte; cambiarla es declarar una fila nueva; queda **invalidada** si la moneda de su versión ya no es la del proyecto (RV‑11): se calcula, no se escribe |
| `calendario_obra` | `linea_base_id` (PK), `fecha_inicio`, `dias_por_periodo` (≥ 1), `feriados` (texto JSON de fechas ISO) | — |
| `parametros_control` | `proyecto_id` (PK), umbrales de §4.5, `eta_cuadrilla`, `cuadrillas_max`, `eta_horas_extra`, `horas_extra_dia`, `recargo_horas_extra`, `fcas_en_horas_extra`, `penalizacion_diaria`, `fuente_penalizacion` | sin fila, los valores por defecto de §4.5 y §4.6 |
| `valuacion` | `id`, `proyecto_id`, `numero`, `desde`, `hasta`, `fecha`, `inspector`, `origen` (`manual` o `excel:<archivo>`), `fuente`, `responsable`, `fecha_hora` | sin `UPDATE` ni `DELETE` en `core`; número y campos pueden faltar (R14 los marca) |
| `linea_valuacion` | `id`, `valuacion_id`, `codigo_partida`, `cantidad` (≥ 0), `fecha_medicion` (anulable), `observacion` | cantidad **del período**, no acumulada |
| `conformacion_valuacion` | `valuacion_id` (PK), `fecha` (de la conformación), `fuente` (acta o firma del inspector), `responsable`, `fecha_hora` | sin fila, la valuación está *presentada*; con fila, *conformada* (RV‑18, a ratificar); la valuación no cambia |
| `anulacion_valuacion` | `valuacion_id` (PK), `motivo`, `responsable`, `fecha_hora` | la anulada se conserva |
| `costo_real` | `id`, `proyecto_id`, `valuacion_id` (anulable), `codigo_partida` (anulable = no asignado), `monto`, `moneda`, `fecha`, `fuente`, `responsable` | se convierte con `tasa_aplicable(fecha)` de S1; no se guarda el convertido |
| `decision_recuperacion` | `id`, `proyecto_id`, `linea_base_id`, `version_resultante_id`, `fecha_corte`, `opcion`, `detalle` (JSON: partidas, *k*, *h*, declaración de independencia), `costo_directo_adicional`, `costo_indirecto`, `penalizacion`, `termino` (fecha), `spi`, `cpi`, `eac`, `pe` (anulable), `supuestos` (JSON: nombre, valor, naturaleza), `fuente`, `responsable`, `fecha_hora` | la foto de lo que el usuario vio |

Todos los montos y cantidades en `DecimalExacto`. Una base anterior (clínica, TI‑001, importadas, y las de S1)
abre por `preparar_base` (`upgrade head`) y gana las tablas sin perder filas (prueba de SL‑E4). Ninguna función
de `core` emite `UPDATE` ni `DELETE` sobre estas tablas, salvo `parametros_control` (que se cambia con su
`RegistroCambio`): por eso sus filas viajan en `anexos/control.json` del paquete de S3 con huella y **sin cadena
propia** (RV‑8; límite declarado).

### 6.2 Formato del XLSX de valuaciones (fuente única en `core/budget/valuaciones.py`)

- `Valuaciones`: `numero`, `desde`, `hasta`, `fecha` (ISO), `inspector`, `conformada` (fecha ISO, opcional) y
  `fuente_conformacion` (obligatoria si hay `conformada`).
- `Lineas`: `numero`, `codigo_partida`, `cantidad`, `fecha_medicion` (opcional), `observacion` (opcional).
- `Costos` (opcional): `numero` (opcional), `codigo_partida` (opcional), `monto`, `moneda` (`Bs`/`USD`), `fecha`,
  `fuente`.

Todo número se lee como texto y se convierte a `Decimal` (como `importacion.py`); límite de 20 MB y guardado
seguro de la subida (RNF‑12). Una valuación del archivo con el mismo número que una guardada se rechaza: el
archivo no corrige, se anula y se vuelve a registrar.

---

## 7. Pruebas (IEEE 829)

TDD con **rojo observado**: el commit de la prueba va antes que el de la implementación en SL‑E4, SL‑E5 y SL‑E6.
**Cero pruebas omitidas** (sin `skipif` ni `xfail`); RNF‑15 registra, no rompe, como RNF‑11.

### 7.1 Oráculo a mano: la obra OB‑S2 (versionada antes del código)

`tests/fixtures/memorias/control_ob_s2.md`, escrita a mano con cada paso intermedio, y su XLSX
`tests/fixtures/control/ob_s2.xlsx`. Las pruebas comparan con la memoria, nunca con la salida de otra función del
sistema. Las cifras de abajo se comprobaron con aritmética `Decimal` independiente al escribir este spec.

**Datos.** Versión del contrato y línea base `OB-001`; perspectiva *costo*, moneda USD, administración 0,15 y utilidad 0,10 (PU = costo directo × 1,265).
Calendario: inicio lunes 2026‑11‑02, períodos semanales de 5 días hábiles, sin feriados; *D* = 20, término del
plan viernes 2026‑11‑27.

| Partida | Cantidad | Costo directo unitario `u` | De él, materiales | APU: `R`, `C_d`, `S` | Plan (fracción por semana) | Unitario del corte `u'` |
|---|---|---|---|---|---|---|
| A excavación | 100 m3 | 10,00 | 0,00 | 10 m3/d; `C_d` 100; `S` 12 | S1 0,5 · S2 0,5 | 10,00 |
| B tubería | 200 m | 5,00 | 3,00 | 20 m/d; `C_d` 40; `S` 5 | S2 0,5 · S3 0,5 | 6,00 (material 3,00 → 4,00) |
| C relleno | 100 m3 | 20,00 | 12,00 | 10 m3/d; `C_d` 80; `S` 10 | S3 0,5 · S4 0,5 | 22,10 (material 12,00 → 14,10) |

(`C_d` = `S` × (1 + FCAS 6,00) + bono 1,00 × obreros + equipo: A 84 + 4 + 12; B 35 + 2 + 3; C 70 + 4 + 6. Con un
plan de dos semanas por partida, cada `R` es el de una cuadrilla. La memoria desglosa las líneas.)
BAC = 4 000,00; V = 5 060,00; CF = 600,00; PE base = 2 864,15 USD (56,60 %), en S3.

**Valuaciones** (inspector «Ing. Ficticio», declarado): V‑01, 2026‑11‑02 a 11‑06, fecha 11‑09: A 40. V‑02,
2026‑11‑09 a 11‑13, fecha 11‑16: A 50, B 60. Las dos **conformadas** el día de su fecha (fuente: acta ficticia
declarada). Costos reales: 1 280,00 USD. **Corte:** 2026‑11‑13 (*c* = 2). Nada de lo que sigue en la tabla
depende del reajuste.

| Resultado | Valor | Resultado | Valor |
|---|---|---|---|
| PV | 1 500,00 | ΔP precio | −60,00 |
| EV | 1 200,00 | ΔC consumo | −20,00 |
| AC | 1 280,00 | CPIc | 0,984375 |
| SV / SPI | −300,00 / 0,8000 | EAC (sistema) | 4 480,00 |
| CV / CPI | −80,00 / 0,9375 | EAC (índice) | 4 266,67 |
| VAC = precio + consumo | −480,00 = −410,00 + −70,00 | Término (índice) | día 25: 2026‑12‑04 |
| Índices por partida | A 0,9 · B 0,6 · C sin evidencia → 0,8 | Término (plan) | día 23: **2026‑12‑02** |

**Plan reproyectado:** S1 A 0,4 · S2 A 0,5, B 0,3 · S3 A 0,1, B 0,3, C 0,4 · S4 B 0,3, C 0,4 · S5 B 0,1, C 0,2.
Fines: A 11,11; B 21,67; C 22,5 días hábiles.

**Lo ejecutado que S2 entrega a S1** (RF‑72). Cláusula ficticia de OB‑S2: periodicidad mensual, mecanismo
`comprobacion`. V‑01 (*hasta* 11‑06) y V‑02 (*hasta* 11‑13) caen en noviembre de 2026: A 40 + 50 = 90, B 60, C 0;
la cantidad reajustable es la misma (ningún acumulado supera lo presupuestado).

**Reajuste reconocido** (RV‑12; §4.7). Escenario *con reajuste*: un estudio de S1 guardado al corte (fecha de
cálculo 2026‑11‑13), período noviembre, comprobación directa (S1 §8.4) contra la versión revalorada al corte
(los `u'` de la tabla de datos), sobre lo ejecutado de ese período:

- PU del contrato = `u` × 1,265: A 12,65; B 6,325. PU comprobado = `u'` × 1,265: A 12,65; B 7,59.
- `Σ q_ejecutada · (PU_comprobado − PU_contrato)` = A 90 × 0,00 + B 60 × 1,265 = 0,00 + **75,90**
  (= 60 × 1,00 × 1,265).
- V' = 5 060,00 + 75,90 = **5 135,90**.

La comprobación de **toda** la obra a precio de venta (410 × 1,265, la cifra de la versión anterior de este spec)
no es un reajuste que S1 produzca: incluye obra no ejecutada y no entra en V'. Escenario *sin reajuste*: ningún
estudio guardado, V' = V = 5 060,00.

**PE' de la reproyección** (= «aceptar el retraso»: `CV'` = EAC = 4 480,00; *D'* = 23; `CF'` = 30 × 23 = 690,00):

- sin reajuste: `V' − CV'` = 580,00; PE' = 690,00 × 5 060,00 / 580,00 = 6 019,66 > 5 060,00 → `NO_SE_ALCANZA`;
- con reajuste: `V' − CV'` = 655,90; PE' = 690,00 × 5 135,90 / 655,90 = 5 402,91 > 5 135,90 → `NO_SE_ALCANZA`.

**Alertas** (iguales en los dos escenarios): AL‑1 ERROR (0,80); AL‑2 ADVERTENCIA (0,9375); AL‑3 ERROR (3 días =
15 % de *D*); **AL‑4 ERROR** (PE' de la reproyección `NO_SE_ALCANZA` con y sin el reajuste reconocido); AL‑5 INFO
(60/1 200 = 5 %, frontera exacta).

**Opciones** (`T*` = día 20; `CF/D` = 600,00 / 20 = 30 por día; `CV'` = 4 480,00 + ΔCD; PE' = `CF'·V'/(V' − CV')`):

| Opción | Detalle | Término | ΔCD | `CV'` | `CF'` | PE' sin reajuste (V' = 5 060,00) | PE' con reajuste reconocido (V' = 5 135,90) |
|---|---|---|---|---|---|---|---|
| Aceptar el retraso | — | día 23, 2026‑12‑02 | 0,00 | 4 480,00 | 690,00 | 6 019,66: `NO_SE_ALCANZA` | 5 402,91: `NO_SE_ALCANZA` |
| Más cuadrillas | B y C con *k* = 2, `E` = 1,8 | día 17, 2026‑11‑24 | 120,00 | 4 600,00 | 510,00 | 5 610,00: `NO_SE_ALCANZA` | **4 887,68 (95,17 %), se alcanza en S4** |
| Horas extra | `h` = 2 en B y C; B llega (19,72), C no (20,42) | día 21, 2026‑11‑30 | 115,3125 | 4 595,3125 | 630,00 | 6 860,09: `NO_SE_ALCANZA` | 5 985,37: `NO_SE_ALCANZA` |
| Partidas en paralelo | ninguna sin empezar con inicio > S3 | — | — | — | — | «no aplica» | «no aplica» |

Cuentas con reajuste: más cuadrillas `V' − CV'` = 5 135,90 − 4 600,00 = 535,90 y PE' = 510,00 × 5 135,90 / 535,90
= 4 887,68, que es 95,17 % de V'; en la curva de `OB-002` el acumulado llega a 82 % en S3 y a 100 % en S4, así que
se ubica en S4. Horas extra: 540,5875 y 630,00 × 5 135,90 / 540,5875 = 5 985,37. Sin reajuste: 460,00 y 510,00 ×
5 060,00 / 460,00 = 5 610,00; 464,6875 y 630,00 × 5 060,00 / 464,6875 = 6 860,09. **Comprobación cruzada:**
PE' ≤ V' equivale a `V' ≥ CV' + CF'`, así que cada opción necesita un reajuste reconocido de al menos `CV' + CF' −
V`: aceptar 110,00; más cuadrillas 50,00; horas extra 165,3125. Con 75,90 solo «más cuadrillas» lo supera; sin
reajuste, ninguna.

**Decisión** «más cuadrillas» (la única que alcanza el equilibrio con el reajuste reconocido): versión `OB-002`
con motivo `recuperacion`, plan S1 A 0,4 · S2 A 0,5, B 0,3 · S3 A 0,1, B 0,54, C 0,72 · S4 B 0,16, C 0,28; un `RegistroCambio` (objeto `plan`) por cada (período, partida) que
cambió respecto del plan de la línea base; R2 y R7 sin hallazgos; la línea base sigue en `OB-001`.

**Valuación sembrada V‑S** (para R13–R14): número `V-03`, 2026‑11‑12 a 11‑20, fecha 11‑19, sin inspector; líneas
B 150 (acumulado 210 > 200), D 5 (no presupuestada), C 10 con fecha de medición 11‑23. Conjunto **exacto**: R13
ERROR B (impacto 50,00), R13 ERROR D, R14 ERROR sin inspector, R14 ERROR fecha anterior a *hasta*, R14 ERROR
solape con V‑02, R14 ERROR medición fuera del período. (El corte de esta prueba es 2026‑11‑20.)

### 7.2 Matriz

| RF / RNF | Prueba |
|---|---|
| RF‑72 | OB‑S2 a mano; inmutabilidad (ninguna función de `core` emite `UPDATE`/`DELETE` sobre `valuacion`, `linea_valuacion`, `conformacion_valuacion` ni `anulacion_valuacion`); conformación (una sola vez; nunca sobre una anulada); anulación; cantidad negativa; `ejecutado_por_periodo` con los casos del criterio de RF‑72 (solo conformadas, asignación por *hasta* incluso cruzando el mes, cantidad reajustable con `min` y aviso); línea base invalidada tras un cambio de moneda |
| RF‑73 | XLSX de OB‑S2 = entrada a mano (con su conformación); cada malformación (hoja o columna faltante, fecha ilegible, número repetido, `conformada` sin `fuente_conformacion`, más de 20 MB) da su mensaje y no escribe |
| RF‑74 | V‑S da el conjunto exacto; cada condición de R13 y R14 por separado; R13 sobre SIS‑001 |
| RF‑75, RF‑76 | tabla de §7.1; una valuación presentada sin conformar no cambia EV; perspectiva *precio* con los mismos datos (ΔC = 0); costo real en Bs convertido con la tasa de su fecha (S1); costo real sin tasa aplicable: AC y lo que depende de él «no disponible» y declarado, PV, EV y SPI intactos; identidad exacta con el generador |
| RF‑77 | plan reproyectado y alertas de §7.1 en los dos escenarios; reajuste reconocido = suma de los estudios guardados con fecha ≤ corte (un estudio guardado después del corte no cuenta); partida detenida (AL‑6); SPI global 0 («no proyectable»); corte a mitad de período |
| RF‑78 | las cuatro opciones de §7.1 con su PE' en los dos escenarios; monotonía en *k*; `h` = 3 rechazada; 100 h extra en el año pasa y 101 se rechaza; «no aplica» sin jornal (TI‑001, SIS‑001); los supuestos aparecen con su naturaleza |
| RF‑79 | decisión de §7.1; sin fuente o sin responsable se rechaza; la decisión recarga idéntica; SPI al mismo corte = 0,80 |
| RNF‑15 | `scripts/medir_rnf15.py`; la meta comprueba que dejó su cifra |
| Arquitectura | `tests/unit/test_arquitectura_s2.py`: pureza de `valor_ganado`, `calendario` y opciones; `ui/control.py` sin Streamlit; ningún archivo de `core/contracts/` cambia (`git diff` vacío en la meta) |

### 7.3 Fronteras

Cada frontera es una prueba explícita, con el valor que pasa y el primero que no (PRU‑H14).

- **R13:** acumulado = cantidad pasa; + 0,001 falla.
- **R14(a), (c), (d), (e):** fecha = *hasta* pasa, un día antes falla; períodos contiguos pasan, un día de solape
  falla; `V-01`, `V-02` pasa, `V-01`, `V-03` advierte.
- **R14(b):** *hasta* = corte pasa, corte + 1 día falla; *desde* = inicio del calendario pasa, inicio − 1 día
  falla.
- **R14(f):** V‑01 hasta el viernes 2026‑11‑06 y V‑02 desde el lunes 11‑09: sin hueco (sin hallazgo); V‑02 desde
  el martes 11‑10: hueco de un día hábil, INFO.
- **Alertas:** SPI 1,0000 sin alerta; 0,9999 ADVERTENCIA; 0,9000 ADVERTENCIA; 0,8999 ERROR (igual CPI); retraso
  2 días (10 %) ADVERTENCIA, 3 días ERROR; `|ΔP|` en 5 % exacto INFO, 4,99 % nada; **AL‑4:** PE' sube 10,00
  puntos porcentuales sobre el de la línea base, sin alerta; 10,01, ADVERTENCIA; PE' = V' exacto se alcanza (con
  OB‑S2, «más cuadrillas» y un reajuste reconocido de 50,00: `V'` = 5 110,00 = `CV' + CF'` y PE' = 5 110,00).
- **Horas extra:** `h` = 2 (10 h extra en la semana de cinco días) pasa; `h` = 2,2 (11 h) se rechaza; 100 h extra
  en el año pasan, 101 se rechazan.
- **Opciones:** `fin = T*` exacto cuenta como recuperado; con un `T*` declarado tal que ni `k_máx` alcanza, la
  opción usa `k_máx` y devuelve el retraso que queda (flujo 4a); partida sin mano de obra a jornal, «no aplica»
  sin división.
- **Ejecutado para S1:** valuación con *hasta* el último día del mes va a ese mes; con *hasta* el primero del
  siguiente, al siguiente.

### 7.4 Regresión (no se edita ninguna)

**Regresión en cada compuerta (no se editan):** cinco APU ± 0,01; 7 de 7; R4 3/4 pulg y
`test_r4_marca_3_4_pulg_y_no_marca_pvc`; TI‑001 total, PU y PE 28 586,76 USD Día 6; dos huellas de RNF‑04; cuatro
hojas. Además, las memorias de S1. La meta comprueba `git diff v0.5.0..HEAD` vacío sobre los archivos de estas
pruebas (RV‑17). Si alguna se moviera, ruling de reanclaje, nunca editar la prueba.

---

## 8. Tareas por fase

| Fase | Contenido | Rama | Compuerta |
|---|---|---|---|
Cada fase es una rama corta desde el `main` del momento, con PR contra `main` y fusión al cruzar su compuerta, no
al final de la versión (RV‑2). Las fases de núcleo S2‑1…S2‑3 forman el carril único de núcleo después de S1‑4
(S1‑1 → S1‑3 → S1‑4 → S2‑1 → S2‑2 → S2‑3 → S3‑2): ninguna empieza mientras otra rama de núcleo siga abierta.
`CHANGELOG.md` lleva `[Sin publicar]` con una línea por PR.

| Fase | Contenido | Rama | Compuerta |
|---|---|---|---|
| **S2‑0** | ERS (UC‑19, UC‑20, RF‑72…79, RNF‑15, R13–R14), modelo de datos §2.6, arquitectura, plan de pruebas; **memoria OB‑S2 a mano** (con los dos escenarios de PE') y su XLSX; partidas frontera de TI‑001 y SIS‑001 fijadas; expedientes SL‑E4…E6 escritos; verificación de fuentes por el verificador de hechos (definiciones de valor ganado; texto completo de Lee 2022 si es accesible; arts. 104, 118, 173, 178 y 182 de la LOTTT contra la Gaceta); generador de RNF‑15; comprobaciones de la 0.7.0 en `scripts/meta_silice.py` | `inc/silice-s2-0` (docs) | GS2‑0: documentos aprobados |
| **S2‑1** | SL‑E4: tablas y revisión de Alembic, valuaciones, conformación, anulación, costos reales, `ejecutado_por_periodo`, importación XLSX, R13, R14, informe de control | `inc/silice-s2-1` (núcleo; empieza con S1‑4 fusionada) | pruebas de RF‑72 a RF‑74 en verde; fusión |
| **S2‑2** | SL‑E5: calendario, valor ganado, separación del desvío de control, reproyección, alertas, extracción de `equilibrio`, PE proyectado con el reajuste reconocido | `inc/silice-s2-2` (núcleo) | OB‑S2 = memoria en los dos escenarios; TI‑001 intacto; fusión |
| **S2‑3** | SL‑E6: opciones, `motivo` en `guardar_edicion`, `aplicar_decision` | `inc/silice-s2-3` (núcleo) | RF‑78, RF‑79; fusión (libera el carril de núcleo para S3‑2) |
| **S2‑4** | `ui/control.py`, pantalla, herramienta de la barra, hojas extra del Excel, AppTest; RNF‑15 | `inc/silice-s2-4` (interfaz, guardia M9) | GS2: meta en OK, CI verde Linux y Windows, encargos de revisión; fusión |
| **S2‑5** | `CHANGELOG.md` (`[Sin publicar]` → `[0.7.0]`), versión 0.7.0 en `pyproject.toml`, base de prueba de la 0.7.0 con su ficha (RV‑3), etiqueta `v0.7.0` en `main` | `inc/silice-s2-5` | fusión y etiqueta |

`uv run python scripts/meta_silice.py --version 0.7.0 --hasta FASE` (RV‑17) comprueba, además de lo común a todas
las versiones: la **presencia** en la ERS de UC‑19, UC‑20, RF‑72…79, RNF‑15, R13, R14 y SL‑E4…E6 (no conteos
absolutos, REQ‑19); cada RF‑72…79 con su prueba; cero omitidas; el commit de la memoria OB‑S2 anterior al primer
commit de `core/budget/valor_ganado.py`; el rojo antes del verde en cada expediente; `git diff` vacío en
`core/contracts/`; `git diff v0.5.0..HEAD` vacío sobre los archivos de las pruebas de regresión de §7.4; que
`medir_rnf15.py` dejó su cifra; la guardia de red de `tests/conftest.py` activa; ninguna rama de núcleo toca
`adapters/` ni `ui/` (M9).

**Orden de caída** si el tiempo aprieta: primero la importación XLSX (RF‑73 es esencial: cae solo si Eugenio lo
acepta), luego
«partidas en paralelo», luego la curva PV/EV/AC de la pantalla. Valuaciones a mano, R13–R14, valor ganado con
separación, alertas, reproyección, cuadrillas, horas extra, aceptar el retraso y la decisión no se recortan: son la
fase R2 del horizonte.

---

## 9. Decisiones y rulings para ratificar

| # | Decisión | Alternativa descartada | Costo si es errónea |
|---|---|---|---|
| S2‑R1 | Precio = `Σ qe·(u − u')` sobre la cantidad ejecutada; el término cruzado queda en el consumo. Nombre propio: «separación del desvío de control», distinta de la «diferencia entre versiones» de S3 (RV‑10) | el orden de Humphreys & Associates (cruzado en el precio) | cambiar dos líneas de `separar_desvio` y la memoria; la identidad no cambia |
| S2‑R2 | Dos perspectivas por línea base: *costo* (contratista, costo directo; con PE) y *precio* (contratante, PU; consumo 0, sin PE) | una sola perspectiva | un CPI engañoso: el costo real comparado con un valor ganado que incluye la utilidad |
| S2‑R3 | Línea base explícita: una decisión de recuperación **no** la cambia; una variación de obra la cambia solo si el usuario la declara | la versión vigente como línea base | el retraso desaparecería del SPI después de cada decisión |
| S2‑R4 | Reproyección por partida con su índice; sin evidencia, el SPI global; sin dependencias (independientes); paralelo exige declaración | SPI global para todas; pedir una red de precedencias | un término optimista si las partidas sí dependen; la red queda para después de 1.0.0 |
| S2‑R5 | `E(k)` geométrica con `η` = 0,80 y `k_máx` = 3; `η_he` = 0,80; SUPUESTO_DECLARADO, editables y visibles | crecimiento lineal (falso según el horizonte §4); cifras de una fuente no verificada | costos y términos de las opciones mal estimados; se corrige un parámetro o una función pura |
| S2‑R6 | FCAS aplicado a las horas extra por defecto (`a` = 1): el art. 104 de la LOTTT incluye los recargos por horas extraordinarias en el salario; el mismo artículo excluye del salario normal lo accidental y el art. 178 llama eventuales a las horas extra | `a` = 0 | sobrestimar (o subestimar) la opción de horas extra; decide el tutor (§11, pregunta 1) |
| S2‑R7 | En la proyección, `CF' = CF·D'/D` (el costo fijo se causa en el tiempo); SF‑E3 no cambia | `CF' = CV'·administración` como SF‑E3 | un PE proyectado que no ve el costo del retraso |
| S2‑R8 | `EV` usa `min(Q, q)`: la obra no presupuestada no gana valor hasta que se registra la variación (R13 la marca con su monto) | contar el exceso | EV inflado por obra no aprobada |
| S2‑R9 | Trabajo uniforme dentro del período; término en días hábiles con techo; lunes a viernes menos feriados declarados | granularidad de período | hasta un día de diferencia en el término |
| S2‑R10 | Valuaciones inmutables; corrección por anulación | editar en el sitio | se pierde la evidencia que viaja en `anexos/control.json` del paquete de S3 (con huella, sin cadena propia: RV‑8) |
| S2‑R11 | Las fórmulas de valor ganado son definiciones del sistema hasta verificar una fuente; EAC del sistema propio y declarado | citar una fuente sin verificar | una cita falsa en la tesis |
| S2‑R12 | Precios del corte sin proyectar inflación futura; cada costo real convertido con la tasa de su fecha | proyectar con el INPC | un EAC optimista con inflación alta; se declara en la pantalla |
| S2‑R13 | Se guardan entradas y decisiones; indicadores, alertas y hallazgos de R13–R14 se recalculan | guardar los indicadores de cada corte | si una fórmula cambia, los cortes pasados se ven distintos; la decisión conserva su foto |
| S2‑R14 | Dos estados de la valuación, *presentada* y *conformada* (fila de conformación aparte); el valor ganado y lo ejecutado que recibe S1 usan solo las conformadas; R13–R14 auditan todas las no anuladas (RV‑18; **valor por defecto, a ratificar por Eugenio, pregunta P3 del maestro §10**) | contar toda valuación registrada | un EV y un reajuste sobre obra que el inspector aún no aceptó; si Eugenio prefiere un solo estado, la conformación se vuelve automática y la tabla queda sin uso |
| S2‑R15 | V' del PE proyectado = V + reajuste **ya reconocido** (suma de los estudios de S1 guardados con fecha ≤ corte); nunca uno proyectado (RV‑12) | proyectar el reajuste de la obra pendiente, o tomar una comprobación de toda la obra | un PE proyectado que cuenta como ingreso un reajuste que nadie reconoció; si se quisiera proyectar, haría falta una función nueva de S1 y su memoria |
| S2‑R16 | Puente a S1 (RV‑11): conformadas asignadas enteras al período mensual de la cláusula por su *hasta*; el exceso sobre lo presupuestado se guarda con R13 ERROR y el reajuste usa `min(Q, q)` con aviso; un cambio de moneda posterior invalida la línea base de control | prorratear por días; rechazar el exceso (S1 3f anterior); convertir la línea base | hasta un período de desfase en el reajuste de una valuación que cruza el mes; se cambia una función pura |
| S2‑R17 | Un costo real sin tasa aplicable (S1‑R2) deja AC «no disponible», declarado, con lo que depende de él; nada se estima (REQ‑25) | omitir ese costo o usar la última tasa conocida | un AC parcial que mejora el CPI sin que nadie lo vea |

---

## 10. Riesgos

| Riesgo | Mitigación |
|---|---|
| S1 no entrega a tiempo los precios del corte o la conversión | las funciones de S2 reciben `PreciosDelCorte` como dato; sin él, la separación es «no disponible» y lo demás funciona; la 0.7.0 espera a la 0.6.0 (spec maestro §5) |
| Ninguna fuente de las fórmulas de valor ganado se verifica | S2‑R11: se presentan como definiciones del sistema |
| Reproyección sin dependencias engaña | S2‑R4 visible en la pantalla; «paralelo» exige declaración; la red de precedencias queda declarada como trabajo futuro |
| El usuario toma `η` como dato | cada opción lista sus supuestos con su naturaleza; AL y opciones dicen «supuesto declarado» |
| Tres expedientes más en `core/` | TDD con rojo visto, tablas aditivas, contratos intactos, aval del tutor |
| Refactor de `equilibrio.py` mueve el PE de TI‑001 | prueba literal de TI‑001 sin editar como regresión; la extracción es mecánica |
| El PE proyectado se lee como pronóstico del reajuste | S2‑R15: solo el reajuste reconocido, con los estudios citados en la pantalla; sin estudio, V' = V y se dice |
| S1 y S2 tocan los mismos archivos de núcleo | carril único de núcleo (RV‑2): S2‑1 empieza con S1‑4 fusionada; tablas en `core/models/control.py` |

---

## 11. Preguntas abiertas

Las que decide Eugenio o el tutor se reúnen, deduplicadas, en el maestro §10; aquí se remite a esa lista. Las que
cerró la revisión dicen con qué ruling.

1. **FCAS en horas extra** (S2‑R6): ¿se aplica? Es una interpretación de los arts. 104 y 178 de la LOTTT; decide el
   tutor o un experto laboral (maestro §10).
2. **Perspectiva por defecto** de una línea base nueva: ¿*costo* (quien arma) o *precio* (quien revisa)? Depende de
   cuál de las dos personas sea la protagonista (horizonte §9, pregunta 6; maestro §10).
3. **Separación** (S2‑R1): los nombres y la distinción con la «diferencia entre versiones» de S3 quedan **cerrados
   por RV‑10**. Sigue abierto para el tutor si se acepta poner el término cruzado en el consumo para alinear el
   precio con el reajuste, o se prefiere el orden de Humphreys & Associates (maestro §10).
4. **Valores de `η`, `η_he` y `k_máx`**: ¿Eugenio o el tutor conocen una fuente verificable para la caída de
   productividad por cuadrilla adicional y por horas extra? Hasta entonces son supuestos (maestro §10).
5. **Deflactar los costos reales** a la fecha del corte con el índice de S1, en lugar de convertir solo la moneda:
   con inflación alta, un costo pagado al inicio del período queda a precios más bajos y el consumo sale favorable.
   ¿Se agrega en 0.7.0 o queda declarado? (maestro §10)
6. **Tolerancia de medición en R13**: ¿la igualdad exacta es la regla, o se admite una tolerancia declarada por
   unidad? (maestro §10)
7. **Valuación presentada o conformada**: valor por defecto fijado por **RV‑18** (dos estados; el valor ganado y el
   reajuste usan solo las conformadas; S2‑R14), **a ratificar por Eugenio: pregunta P3 del maestro §10**.
8. **Penalización por retraso**: ¿la LCP o su Reglamento fijan una? No está verificado; hoy es un dato del contrato
   (maestro §10).
9. **S1, pregunta 6** (que el estudio de reajuste cite las valuaciones): **cerrada por RV‑11**. El estudio de la
   0.7.0 cita las conformadas por `ejecutado_por_periodo`, asignadas por su *hasta* al período mensual de la
   cláusula (RF‑72); en la 0.6.0 lo ejecutado se escribe a mano.
10. **Monto reconocido de un estudio de S1** (coordinación con S1, no es pregunta para Eugenio): con mecanismo
    `ambos`, ¿qué monto da el estudio como reconocido, la escalatoria o la comprobación? Y ¿S1 admite guardar el
    estudio de un mes que aún no cierra, como el de noviembre al corte 2026‑11‑13 del escenario con reajuste de
    §7.1? Si S1 lo prohíbe, las cifras de §7.1 no cambian: `equilibrio_proyectado` es pura y recibe el reajuste
    reconocido como dato (75,90); solo la prueba que lo lee de la base fecha el estudio al cierre del mes y usa un
    corte posterior.
