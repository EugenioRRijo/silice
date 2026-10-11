# Nuevo horizonte de la tesis: la IA propone, un auditor verifica y el presupuesto se mantiene vivo

| Campo | Valor |
|---|---|
| Estado | **propuesta de horizonte, revisión 2** (fase R0). Pendiente de la aprobación de Eugenio y del visto bueno del tutor. Cada fase R1–R4 tendrá su propio spec detallado, revisado por los encargos, antes de construirse |
| Fecha | 2026‑10‑08; revisión 2 el 2026‑10‑09 (las dos personas y el paquete auditado, base de precios por empresa, auditoría de planos, indicador del administrador) |
| Rama | `inc/spec-horizonte`, desde `main` |
| Se apoya en | el sprint final del prototipo (SF), [spec del 2026‑10‑04](2026-10-04-sprint-final-prototipo-design.md), construido y revisado en la pila de PR #22–#29, aún sin fusionar |
| Antecedentes | [informe de antecedentes del 2026‑10‑08](../tesis/antecedentes-reorientacion-2026-10-08.md) (cada dato marcado VERIFICADO, INDICIO o NO ENCONTRADO) |
| Plazo de entrega de la tesis | aproximadamente un año desde esta fecha (según Eugenio) |
| Naturaleza de los datos | sin cambios: los casos son construidos; los precios son los listados MaPreX de julio de 2026, suficientes para la tesis |

---

## 1. Por qué reorientar

**Lo que motivó la decisión (2026‑10‑03 a 2026‑10‑08).** Eugenio conoció otra tesis que, a partir de un plano de
Revit o AutoCAD, calcula los metrajes y exporta el APU; está construida como un plugin de AutoCAD que optimiza
planos de redes. Con el sprint SF el sistema también importa planos (DXF e IFC) y trabaja con redes, así que **nos
parecemos en el dominio**. El informe de antecedentes encontró además que **OneEstimate ya vende en Venezuela «APU
generados con IA»**, sin describir cómo los verifica.

**Conclusión.** «Generar el APU», con plano o con IA, ya no es una contribución propia. Lo que nadie hace, según
la búsqueda, es **auditar con reglas deterministas lo que genera una IA** y **mantener el presupuesto cuadrado
durante la obra con la norma y los índices venezolanos**. El título vigente ya lo anuncia: *«…generación,
**trazabilidad de origen y auditoría** de análisis de precios unitarios…»*. La reorientación cambia el énfasis,
no el tema.

## 2. La nueva pregunta de investigación (propuesta para el tutor)

> ¿Cómo lograr que un presupuesto de obra de instalaciones en red, generado por una persona, por un plano o por
> una inteligencia artificial, sea verificable hasta el origen de cada número y se mantenga cuadrado en tiempo y
> en dinero durante la ejecución, en el contexto económico venezolano?

**Tesis en una frase:** *la IA propone el presupuesto, un auditor de reglas lo verifica, y el valor ganado lo
mantiene cuadrado con la norma y los índices venezolanos.*

**Por qué auditar si el sistema calcula.** Las cuentas del núcleo no fallan; lo que falla es lo que entra y lo que
pasa con el tiempo: una medida mal escrita, una partida o una unidad equivocada, un precio de la base vencido o con
un error de tipeo, una propuesta errada de la IA, un número cambiado después sin decir por qué, una obra que se
atrasa o unos precios que suben. La calculadora multiplica bien un dato malo; el auditor exige el origen de cada
número y lo vuelve a comprobar.

### 2.1 Objetivos específicos propuestos (a acordar con el tutor)

Los objetivos vigentes del capítulo I (OE1–OE6, y OE7 en la variante A, decisión D3 aún pendiente) se conservan en
lo construido. Se proponen como **nuevos o reformulados**:

| Propuesta | Objetivo |
|---|---|
| OE‑H1 | Diseñar un auditor de reglas deterministas que verifique la consistencia y la trazabilidad de un presupuesto de instalaciones, cualquiera que sea su generador (persona, plano o modelo de lenguaje) |
| OE‑H2 | Integrar un asistente con modelos de lenguaje, independiente del proveedor, cuyas propuestas pasen siempre por el auditor, y medir cuántos errores de cada modelo detecta el auditor |
| OE‑H3 | Implementar el control del presupuesto durante la obra con valor ganado, separando el desvío por plazo del desvío por precio, con valuaciones por cantidades ejecutadas |
| OE‑H4 | Implementar el reajuste de precios en la moneda elegida por el proyecto, por fórmula escalatoria con índices del BCV y por comprobación directa, conforme a la Ley de Contrataciones Públicas (a cotejar con la Gaceta) |
| OE‑H5 | Proponer opciones de recuperación de retrasos con su costo, calculadas con el rendimiento y la cuadrilla de los APU |
| OE‑H6 | Auditar los planos que alimentan el presupuesto (validaciones del plano y comparación entre dos fuentes) y entregar el presupuesto como un paquete auditado cuya integridad pueda comprobar quien lo recibe |

### 2.2 Alcance

**Dentro:** instalaciones de redes en edificaciones cuyas cantidades se derivan de recorridos y puntos (agua,
drenaje, datos y electricidad) y los cuatro dominios del núcleo (civil, telecomunicaciones, mantenimiento
industrial, sistemas) como prueba de extensibilidad.

**Fuera:** arquitectura, estructura y acabados (puertas, pisos, columnas…); dimensionar instalaciones (caudales,
caídas de tensión); entrenar una red neuronal propia; leer planos en PDF o escaneados; cubrir «toda la
construcción».

### 2.3 A quién le aporta (sector de la sociedad venezolana)

- **Pequeñas y medianas contratistas de instalaciones y mantenimiento de la zona industrial del Estado Miranda**
  (como dice el título): presupuestos auditados y evidencia trazable para justificar un reajuste ante el cliente o
  ante un ente público.
- **El administrador** que revisa presupuestos: el sistema cuadra y le señala dónde no cuadra.
- **Los entes contratantes**: pueden auditar el presupuesto que reciben, lo haya hecho quien lo haya hecho.

### 2.4 Dos personas unidas por el mismo auditor

El sistema sirve a quien **arma** el presupuesto y a quien lo **revisa**. Entre los dos viaja un **paquete
auditado**: el presupuesto, su informe de auditoría y su registro de cambios encadenado con huellas.

```
   LA CONTRATISTA (arma)                                  EL ADMINISTRADOR (revisa)
   hoja del proyecto: a mano / con plano / con IA         recibe el paquete
   precios de SU empresa                                  ├─ ¿alguien lo alteró después de auditarlo? (huellas)
   ├─ el auditor revisa EN VIVO (control de calidad)      ├─ el auditor lo vuelve a revisar (no confía en el informe ajeno)
   └─► entrega el PAQUETE AUDITADO ─────────────────────► ├─ ve en qué difiere y cuánto dinero representa
                                                          └─ durante la obra: valuaciones, reajuste en Bs, alertas
```

| Persona | Actor de la ERS | Lo que gana |
|---|---|---|
| **Quien arma** (contratista, proyectista) | proyectista / estimador | arma más rápido (hoja, IA, su base de precios) y entrega un presupuesto difícil de rechazar, porque cada número trae su origen |
| **Quien revisa** (administrador, cliente, ente contratante) | gerente, ampliado a «administrador que revisa» | no rehace el presupuesto: lo verifica; ve qué no cuadra, cuánto dinero representa y si lo tocaron después de auditado |

Si el presupuesto que recibe el administrador **no viene de este sistema** (otro programa, el plugin de la otra
tesis, OneEstimate), no hay paquete auditado: el sistema audita lo que puede y declara «no contrastable» lo que no
puede verificar, en vez de darlo por bueno.

## 3. Decisiones tomadas por Eugenio (2026‑10‑08)

| # | Tema | Decisión | Consecuencia de diseño |
|---|---|---|---|
| H‑D1 | Moneda | **El usuario elige la moneda de cada proyecto** (Bs o USD) y el sistema convierte | Cada precio guarda moneda original, fecha y tasa; el presupuesto se expresa en la moneda del proyecto; el reajuste y la erosión se muestran en las dos monedas; cambiar la moneda de un proyecto queda registrado |
| H‑D2 | Retrasos | **Alerta y reproyección siempre; opciones de recuperación bajo demanda** | Al registrar el avance, el sistema compara con el plan, alerta y reproyecta término, costo final y punto de equilibrio. A pedido calcula opciones (más cuadrillas, horas extra, partidas en paralelo, aceptar el retraso) con su costo; el usuario elige y la decisión queda registrada |
| H‑D3 | Reajuste | **Los dos mecanismos de la ley**: fórmula escalatoria con índices del BCV y comprobación directa; el proyecto elige y el sistema los muestra lado a lado | La comprobación directa ya existe (UC‑02); falta la escalatoria y la comparación |
| H‑D4 | IA | **Independiente del proveedor**: Claude como principal y un modelo local (Ollama) sin conexión, con el experimento de errores detectados por el auditor | La IA nunca escribe un número final: propone espacio y partidas mediante funciones del sistema; el núcleo calcula y el auditor verifica |
| H‑D5 | Avance real | **Por cantidades ejecutadas**, como una valuación de obra venezolana, a mano o importada de Excel, con su fuente | El auditor revisa las valuaciones (p. ej. lo ejecutado no supera lo presupuestado sin una variación registrada) |
| H‑D6 | Selección de mejoras | Valor ganado con separación plazo/precio; asistente con IA verificada; registro encadenado a prueba de manipulación; auditar el APU de otras herramientas; anomalías en variaciones de precio | Ver §5: el informe de antecedentes reordena cuáles son aporte y cuáles soporte |
| H‑D7 | Para quién (2026‑10‑09) | **Para las dos personas**: quien arma el presupuesto a mano (o con plano o IA) y el administrador que lo revisa | El auditor trabaja en vivo para quien arma y es el producto para quien revisa; el paquete auditado los une (§2.4) |
| H‑D8 | Base de precios por empresa (2026‑10‑09) | Cada empresa guarda **sus propios precios** («el m³ de piedra picada vale X»), con fecha, moneda y fuente | Es una lista de precios más, con su origen (el sistema ya maneja listas y cotizaciones por proyecto); el auditor la compara con el mercado (MaPreX) y con el tiempo («este precio está vencido» o «fuera de rango») |
| H‑D9 | Auditoría de planos (2026‑10‑09) | Auditar planos malos, erróneos o hechos con IA | Validaciones del plano al importar y comparación entre dos fuentes (§5.1). El auditor detecta inconsistencias, no «mentiras consistentes»: un plano coherente pero equivocado solo se descubre comparándolo con otra fuente |
| H‑D10 | Paquete auditado (2026‑10‑09) | Exportar e importar el presupuesto con su informe y sus huellas, y verificar que nadie lo alteró | El registro encadenado deja de ser solo un requisito de integridad: es el puente entre las dos personas |

## 4. Restricciones que salen de los antecedentes

Todas están en el [informe](../tesis/antecedentes-reorientacion-2026-10-08.md); las normativas están **pendientes
de cotejo con la Gaceta Oficial** antes de citarlas en la tesis.

- **Ley de Contrataciones Públicas** (Decreto 1.399, G.O. 6.154 Ext., 19‑11‑2014; transcripción no oficial):
  - art. 133: admite variaciones de precios por **fórmulas escalatorias** o por **comprobación directa** (H‑D3);
  - art. 134 (contratos de más de un año): el contrato declara estructura de costos, mecanismo de ajuste,
    periodicidad e índices con su órgano emisor; **precios fijos el primer año** salvo que se rompa el equilibrio
    económico; en cada período **solo se ajusta la obra ejecutada en ese período**.
  - El Reglamento (Decreto 6.708, G.O. 39.181, 2009) sigue vigente en lo que no contradiga, pero sus artículos sobre
    variaciones **no están verificados**.
- **BCV**: publica la tasa diaria (archivos .xls trimestrales, una hoja por día hábil), el INPC mensual (2026
  provisional) y un **índice de precios de insumos de la construcción** (mensual, trimestral, anual), que es el
  índice natural de la fórmula escalatoria. **No hay API oficial** y el certificado del sitio tiene la cadena
  incompleta: el sistema **importa archivos descargados**, con su fuente y fecha, y no depende de conectarse.
- **Compresión del cronograma**: suponer que el rendimiento crece en línea recta con la cuadrilla es falso
  (rendimientos decrecientes). Se declara como supuesto, con un factor de eficiencia visible, y se cita a Lee (2022)
  como base del método.
- **Separar desvío por precio y por cantidad** en valor ganado es práctica conocida (fuente de consultoría, no
  arbitrada): el aporte es su aplicación con bolívares, dólares, la escalatoria del art. 134 y los índices del BCV.

## 5. Qué es aporte y qué es soporte

| Pieza | Según los antecedentes | Papel en la tesis |
|---|---|---|
| IA que propone y auditor de reglas que verifica | sin antecedentes en presupuestos (el más cercano, SYNAPSE 2026, es de estructuras) | **aporte central** |
| Valor ganado que separa plazo y precio, con reajuste por la ley y los índices del BCV, en dos monedas | no encontrado en Venezuela ni Latinoamérica | **aporte central** |
| Recuperación de retrasos desde el rendimiento y la cuadrilla del APU | aplicación de Lee (2022) | aporte de aplicación |
| Registro encadenado con huellas SHA‑256 | técnica conocida (Hamledari y Fischer 2021) | **puente** entre quien arma y quien revisa (paquete auditado): su papel es nuevo, la técnica no |
| Auditar el APU de otras herramientas (Excel, API) | — | soporte del aporte central: muestra que el auditor es independiente del generador |
| Auditoría de planos (validaciones y comparación entre dos fuentes) | validación de IFC con IDS es estándar de buildingSMART; no hallado aplicado a presupuestos | soporte del aporte central: el auditor también verifica la entrada geométrica |
| Base de precios por empresa auditada contra el mercado y el tiempo | — | aplicación; da sentido práctico a la auditoría de precios |
| Anomalías en variaciones de precio | existe en compras públicas; no validable con precios ficticios | complemento menor |

### 5.1 Auditoría de planos: qué detecta y con qué herramientas

**Detecta hoy** (sprint SF): elementos fuera de la convención (informe de importación), plano sin unidades,
puntos fuera de su ambiente o sobre el techo y recorridos imposibles (R9), alturas pendientes, circuitos con valores
supuestos y elementos que desaparecieron al reimportar (R8), y límites de especialidad (R10).

**No puede detectar:** un plano coherente pero equivocado (salvo que se compare con otra fuente), si el diseño es
bueno (dimensionar está fuera del alcance) ni planos en PDF o escaneados.

**Se agrega en R3:**

| Para detectar | Herramienta | Estado |
|---|---|---|
| DXF dañado o mal construido | la auditoría de archivo de `ezdxf` | la biblioteca ya está, pero **hoy no se ejecuta ninguna auditoría** (`adapters/espacio/planos/dxf.py` solo lee el archivo); se agrega en S3 (RF‑89). Corregido el 2026‑10‑11 |
| IFC que no trae lo mínimo (espacio sin altura, aparato sin diámetro, tomacorriente sin circuito) | requisitos declarados en **IDS** (estándar de buildingSMART) y comprobados con **`ifctester`** (IfcOpenShell) | IfcOpenShell ya está; falta el IDS |
| Geometría absurda: ambientes superpuestos, puntos duplicados, escalas imposibles, puntos sin fuente | **`shapely`** con su índice espacial | ya instalada como dependencia de IfcOpenShell; se declara como dependencia directa |
| Diferencias entre dos fuentes (plano contra levantamiento; plano nuevo contra anterior), traducidas a dinero | `shapely` para emparejar con tolerancia y el núcleo para valorar la diferencia | parcial |
| Lo que propone la IA | salida estructurada validada con Pydantic, y luego las reglas del auditor | Pydantic ya está |
| Ver el error sobre el plano | dibujo de `ezdxf` con `matplotlib`, o plotly | parcial |
| Choques físicos en un IFC (tubo contra columna) | IfcClash (IfcOpenShell) | **opcional**: solo sirve si el IFC trae la estructura |

**Cómo se demuestra que funciona:** con **errores sembrados**, el método ya usado en TI‑001 (6 de 7 detectados):
se toman planos correctos (OF‑001) y planos o presupuestos generados por la IA, se les siembran errores conocidos y
se mide la **tasa de detección** y las **falsas alarmas**.

## 6. Fases

Cada fase se diseña en su propio spec (aprobado por Eugenio, revisado por los cuatro encargos) y se construye con
la metodología del sprint SF: Scrum‑Cascada con compuertas, DRY, pruebas antes que código con el rojo observado,
expediente por cada cambio en `core/`, cero pruebas omitidas, ramas de núcleo separadas de las de adaptadores e
interfaz, y fichas de rol de los subagentes (`sf-*`).

| Fase | Contenido | Entrega que funciona | Depende de |
|---|---|---|---|
| **R0** | Propuesta para el tutor (este documento como base): pregunta, objetivos OE‑H1…H6, alcance, sector; **cotejo** de los arts. 133–134 con la Gaceta y de los artículos del Reglamento; decisión D3 pendiente; aval del sprint SF | aprobación del tutor | — |
| **R1** | Moneda por proyecto; precio con moneda, fecha y tasa; **base de precios por empresa** (lista propia con fecha, moneda y fuente, auditada contra MaPreX y contra el tiempo); importación de los archivos del BCV (tasa, INPC, índice de insumos de la construcción) con fuente; reajuste por escalatoria y por comprobación directa, lado a lado, respetando el primer año y «solo lo ejecutado en el período» | un proyecto en Bs y otro en USD con su reajuste comparado; una empresa con su lista propia y sus precios vencidos o fuera de rango marcados | R0 |
| **R2** | Valuaciones por cantidades ejecutadas; valor ganado con desvío por plazo y por precio; alertas y reproyección; opciones de recuperación con su costo desde el rendimiento y la cuadrilla; registro de la decisión | una obra con retraso detectado, reproyectada y recuperada con una opción elegida | R1 |
| **R3** | Registro encadenado a prueba de manipulación; **paquete auditado** (exportar e importar el presupuesto con su informe y sus huellas, y verificar que nadie lo alteró); vista del **administrador que revisa**; importar y auditar el APU de otras herramientas (Excel y una ruta de la API para plugins); **auditoría de planos** (§5.1); anomalías en variaciones como complemento | un paquete armado por la contratista, recibido y verificado por el administrador; una alteración detectada; un APU externo auditado; errores sembrados en planos con su tasa de detección | R0 (puede ir en paralelo a R2) |
| **R4** | Asistente independiente del proveedor (Claude y un modelo local); la IA solo propone mediante funciones del sistema; experimento: misma tarea a los dos modelos y conteo de errores detectados por el auditor | un presupuesto pedido en lenguaje natural, verificado, y el resultado del experimento | R1–R3 |

**Orden de caída si el tiempo aprieta:** primero las anomalías (R3), luego IfcClash, luego el modelo local de R4
(queda solo Claude). R1, R2, el paquete auditado de R3 y el núcleo de R4 no se recortan: son la tesis.

### 6.1 Evaluación: un indicador por persona

| Persona | Qué se mide | Cómo |
|---|---|---|
| Quien arma | tiempo para armar el presupuesto y errores atrapados mientras lo arma | el indicador 3 vigente (tiempo de elaboración frente al método manual), con el auditor en vivo |
| Quien revisa | **tiempo para revisar un presupuesto y errores detectados** frente a los sembrados | **indicador nuevo**: el mismo presupuesto con errores sembrados, revisado a mano y con el sistema, por personas que no son el autor; tasa de detección y falsas alarmas |
| El auditor sobre la IA | errores de cada modelo atrapados por el auditor | experimento de R4 |
| El auditor sobre planos | tasa de detección de errores sembrados en planos | §5.1 |

Los protocolos se escriben antes de medir, como los vigentes del indicador 3 y de RNF‑04.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| El tutor no aprueba la reorientación | R0 va primero; la propuesta se apoya en el título vigente («trazabilidad de origen y auditoría») |
| La norma citada no coincide con la Gaceta | cotejo en R0; hasta entonces todo dato normativo queda «a cotejar» |
| El BCV cambia el formato o el acceso | importación de archivos descargados, con fuente y fecha; el formato se fija con archivos reales en R1 |
| Evaluar la IA con datos ficticios | el experimento mide errores detectados por el auditor sobre tareas definidas (casos de referencia construidos y declarados), no la exactitud de precios reales |
| Costo y privacidad del modelo en la nube | modelo local como alternativa; el borrador que viaja se limita a lo necesario y se declara |
| Recuperación de retrasos poco realista | factor de eficiencia declarado; Lee (2022) como base; la decisión siempre es del usuario |
| Que algo de esto se publique mientras tanto | repetir la búsqueda de antecedentes antes de redactar el capítulo II |

## 8. Lo que no cambia

- El núcleo cerrado y los adaptadores abiertos (NORMAS §2); todo lo de una especialidad en `adapters/`.
- Los datos siguen siendo ficticios y declarados; MaPreX de julio de 2026 es la referencia de precios.
- El sprint SF (hoja, auditoría R1–R10, versiones, Excel, planos, barra) es la base sobre la que se construye.
- La redacción de la tesis sigue en pausa hasta que el tutor apruebe el nuevo horizonte.

## 9. Preguntas abiertas para el tutor

1. ¿Acepta la reorientación del énfasis hacia la auditoría y el presupuesto vivo, con el mismo título?
2. ¿Variante A o B de los objetivos (D3), y cómo se integran OE‑H1…H6?
3. ¿Electricidad dentro del alcance (hoy no figura en el capítulo I)?
4. ¿Qué se hace con «zona industrial del Estado Miranda» del título: reflejarla en el sistema (precios zonificados,
   caso de una contratista de la zona) o ajustar el título?
5. ¿Aprueba los cambios en `core/` del sprint SF (expedientes SF‑E1…E9, PR #22 y #25)?
6. ¿Acepta que la tesis sirva a dos personas (quien arma y quien revisa) con un indicador para cada una, o prefiere
   una sola como protagonista?
