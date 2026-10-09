# Nuevo horizonte de la tesis: la IA propone, un auditor verifica y el presupuesto se mantiene vivo

| Campo | Valor |
|---|---|
| Estado | **propuesta de horizonte** (fase R0). Pendiente de la aprobación de Eugenio y del visto bueno del tutor. Cada fase R1–R4 tendrá su propio spec detallado, revisado por los encargos, antes de construirse |
| Fecha | 2026‑10‑08 |
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

## 3. Decisiones tomadas por Eugenio (2026‑10‑08)

| # | Tema | Decisión | Consecuencia de diseño |
|---|---|---|---|
| H‑D1 | Moneda | **El usuario elige la moneda de cada proyecto** (Bs o USD) y el sistema convierte | Cada precio guarda moneda original, fecha y tasa; el presupuesto se expresa en la moneda del proyecto; el reajuste y la erosión se muestran en las dos monedas; cambiar la moneda de un proyecto queda registrado |
| H‑D2 | Retrasos | **Alerta y reproyección siempre; opciones de recuperación bajo demanda** | Al registrar el avance, el sistema compara con el plan, alerta y reproyecta término, costo final y punto de equilibrio. A pedido calcula opciones (más cuadrillas, horas extra, partidas en paralelo, aceptar el retraso) con su costo; el usuario elige y la decisión queda registrada |
| H‑D3 | Reajuste | **Los dos mecanismos de la ley**: fórmula escalatoria con índices del BCV y comprobación directa; el proyecto elige y el sistema los muestra lado a lado | La comprobación directa ya existe (UC‑02); falta la escalatoria y la comparación |
| H‑D4 | IA | **Independiente del proveedor**: Claude como principal y un modelo local (Ollama) sin conexión, con el experimento de errores detectados por el auditor | La IA nunca escribe un número final: propone espacio y partidas mediante funciones del sistema; el núcleo calcula y el auditor verifica |
| H‑D5 | Avance real | **Por cantidades ejecutadas**, como una valuación de obra venezolana, a mano o importada de Excel, con su fuente | El auditor revisa las valuaciones (p. ej. lo ejecutado no supera lo presupuestado sin una variación registrada) |
| H‑D6 | Selección de mejoras | Valor ganado con separación plazo/precio; asistente con IA verificada; registro encadenado a prueba de manipulación; auditar el APU de otras herramientas; anomalías en variaciones de precio | Ver §5: el informe de antecedentes reordena cuáles son aporte y cuáles soporte |

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
| Registro encadenado con huellas SHA‑256 | técnica conocida (Hamledari y Fischer 2021) | requisito de integridad, no aporte |
| Auditar el APU de otras herramientas (Excel, API) | — | soporte del aporte central: muestra que el auditor es independiente del generador |
| Anomalías en variaciones de precio | existe en compras públicas; no validable con precios ficticios | complemento menor |

## 6. Fases

Cada fase se diseña en su propio spec (aprobado por Eugenio, revisado por los cuatro encargos) y se construye con
la metodología del sprint SF: Scrum‑Cascada con compuertas, DRY, pruebas antes que código con el rojo observado,
expediente por cada cambio en `core/`, cero pruebas omitidas, ramas de núcleo separadas de las de adaptadores e
interfaz, y fichas de rol de los subagentes (`sf-*`).

| Fase | Contenido | Entrega que funciona | Depende de |
|---|---|---|---|
| **R0** | Propuesta para el tutor (este documento como base): pregunta, objetivos OE‑H1…H5, alcance, sector; **cotejo** de los arts. 133–134 con la Gaceta y de los artículos del Reglamento; decisión D3 pendiente; aval del sprint SF | aprobación del tutor | — |
| **R1** | Moneda por proyecto; precio con moneda, fecha y tasa; importación de los archivos del BCV (tasa, INPC, índice de insumos de la construcción) con fuente; reajuste por escalatoria y por comprobación directa, lado a lado, respetando el primer año y «solo lo ejecutado en el período» | un proyecto en Bs y otro en USD con su reajuste comparado | R0 |
| **R2** | Valuaciones por cantidades ejecutadas; valor ganado con desvío por plazo y por precio; alertas y reproyección; opciones de recuperación con su costo desde el rendimiento y la cuadrilla; registro de la decisión | una obra con retraso detectado, reproyectada y recuperada con una opción elegida | R1 |
| **R3** | Registro encadenado a prueba de manipulación; importar y auditar el APU de otras herramientas (Excel y una ruta de la API para plugins); anomalías en variaciones como complemento | un APU externo importado y auditado; una alteración en la base detectada | R0 (puede ir en paralelo a R2) |
| **R4** | Asistente independiente del proveedor (Claude y un modelo local); la IA solo propone mediante funciones del sistema; experimento: misma tarea a los dos modelos y conteo de errores detectados por el auditor | un presupuesto pedido en lenguaje natural, verificado, y el resultado del experimento | R1–R3 |

**Orden de caída si el tiempo aprieta:** primero las anomalías (R3), luego el modelo local de R4 (queda solo
Claude), luego el registro encadenado. R1 y R2 y el núcleo de R4 no se recortan: son la tesis.

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
2. ¿Variante A o B de los objetivos (D3), y cómo se integran OE‑H1…H5?
3. ¿Electricidad dentro del alcance (hoy no figura en el capítulo I)?
4. ¿Qué se hace con «zona industrial del Estado Miranda» del título: reflejarla en el sistema (precios zonificados,
   caso de una contratista de la zona) o ajustar el título?
5. ¿Aprueba los cambios en `core/` del sprint SF (expedientes SF‑E1…E9, PR #22 y #25)?
