# Plan de cierre de la rama `feature/front-b1` (2026-11-28)

**Pedido de Eugenio (2026-11-28):** «haz unna lista de todas las tareas pendientes de tu lado, y genera un plan de
implementacion ayudandote con gemini para llegar al cierre de la rama de reestructuracion porfavor».

**Estado de partida:**
- El PR [#163](https://github.com/EugenioRRijo/silice/pull/163) está abierto en borrador y **sin fusionar**, con la CI
  de GitHub toda en verde.
- La rama va en `a384507c`.
- El detalle de lo hecho está en [ESTADO.md](../ESTADO.md).

**«Cierre de la rama»:**
- Todas las tareas de §1 están hechas y verificadas.
- El PR pasa de borrador a «listo para revisar», con la CI en verde.
- Eugenio lo fusiona cuando decida, y después se pone la etiqueta `medicion-v1`, con tope el 2026-12-16.

## 1. Tareas pendientes de Claude (no esperan decisiones de Eugenio)

| # | Tarea | Por qué | Quién la construye | Cómo se verifica |
|---|---|---|---|---|
| T1 | **«Quitar» del inspector de la partida** se encola con las escrituras de cantidades y se cancela si el último cambio dio 422 | Defecto real de B1-6, que señaló Gemini al intentar B1-11 | Claude (agente) | Prueba en rojo de la carrera 422 → «Quitar»; mutante a mano |
| T2 | **Recorrido UX en modo medición:** sin `--funcional`, a los 3 anchos y los 3 tamaños de letra, como cada rol. Mide un solo h1, que no haya desplazamiento horizontal, errores de consola y red, botones sin nombre, axe y la carga de decisiones | Desde la reestructuración solo se corrió el modo funcional. Este modo ve lo que el funcional no ve | Claude | El informe del recorrido sin regresiones frente a la referencia de `AXE_DE_REFERENCIA` |
| T3 | **Revisión visual en claro y oscuro** de las pantallas nuevas: Presupuesto, Auditar un libro, registro y código, Solicitudes, notificaciones y panel, Actividad, Inicio y gráficos | El recorrido comprueba que funcionan, no cómo se ven. El modo oscuro nunca se miró a ojo | Claude toma las capturas; **Gemini (neon) las revisa** con la cara aprobada y la skill unslop-interfaz | Lista de defectos visuales con captura; cada arreglo con su prueba de estilos |
| T4 | **Mutantes a mano** en los lotes que no los tuvieron: C7b (gráficos), C9 front (registro), C10b (filtro por persona), C11 (componentes de notificaciones), G2, G3 y G5 front (fecha de entrega) | ub-mode: «Kill the survivors» | Claude (agente) | Cada mutante muere; los sobrevivientes ganan una prueba |
| T5 | **Revisión de seguridad independiente** de las rutas nuevas que no la tuvieron: `/v1/notificaciones*` y preferencias, `/v1/obras/{codigo}/entrega` y `/v1/libros/que-hacer` | Solo C9a tuvo revisión de seguridad | Revisor `silice-rev-seguridad` (Claude); **segunda opinión de Gemini (neon)** | Veredicto con tabla; los cambios que pida, con su prueba en rojo |
| T6 | **«No se pudo leer 1 carpeta»** en el Inicio de la demostración: averiguar qué carpeta es y por qué | Puede ser un defecto del servidor (`carpetas_omitidas`, `api/rutas/obras.py:345`, `:425`) o solo de la siembra | Claude | Causa con evidencia; si es defecto, arreglo con prueba |
| T7 | **«Últimas auditorías» no se refresca** después de auditar un libro (B2) | La persona no ve su auditoría recién hecha sin recargar | **Gemini (hydrogen)** | Prueba: auditar y ver la fila nueva |
| T8 | **Tarjetas de la prueba de comprensión de las 6 alertas** (A1 a A6), generadas desde la pantalla nueva y **sin** la línea «Qué hacer» (decisión D3 de B2) | El agente de B2 las dejó pendientes; la prueba con personas las necesita | **Gemini (carbon)** redacta; Claude verifica contra la pantalla | Cada tarjeta coincide con lo que muestra Sílice (cifras en es-VE) |
| T9 | **Lectura en frío del manual de usuario:** las secciones que reescribió Gemini (739 líneas) | Solo se comprobaron 15 nombres de botones | **Gemini (argon)**, como lector «goldfish» que no ha visto el código | Hallazgos con línea; Claude corrige contra el código |
| T10 | **ERS, arquitectura y modelo de datos al día:** los requisitos de registro con código, notificaciones, actividad y fecha de entrega; los módulos nuevos (`seguridad/solicitudes.py`, `aplicacion/notificaciones.py`, `avisos_por_evento.py`, `que_hacer.py`, `entrega_de_obra.py`) | Las pruebas de documentos exigen trazabilidad, y el jurado lee la ERS | **Gemini (neon)** redacta; Claude verifica | `tests/unit/test_documentos_*` y la guardia de requisitos en verde |
| T11 | **Guardar el intento de B1-11** en una rama aparte, sin fusionar (`archivo/b1-11-intento`) | Hoy es un parche en una carpeta temporal que se puede borrar | Claude | La rama existe en GitHub |
| T12 | **Cierre:** suites completas (Python, front, `npm run muerto`, `duplicado`, `build`, `dist`), recorrido funcional 33 de 33, `ESTADO.md` y CHANGELOG, el PR pasa a «listo para revisar» y la CI en verde | — | Claude | Salida literal de cada suite y la CI |

**Ya no está pendiente:** la ayuda de «Espacio, plan y ajustes» existe (`paginas/hoja/textos.ts`).

## 2. Decisiones de Eugenio (no las hace Claude)

| # | Decisión | Qué recomienda Claude |
|---|---|---|
| E1 | Ratificar D1-D12 de B2 ([ficha](../especificaciones/2026-11-26-cara-papel-y-resaltador/b2/ficha-b2.md)) | Ratificarlas como están |
| E2 | La cifra de detección del ensayo: 3 de 12 frente al umbral del 50 % ([enmienda](../bitacora/2026-11-25-cifra-oficial-de-deteccion.md)) | Llevarla al tutor antes de abrir los libros nuevos |
| E3 | Dónde se ve el cliente de la obra | En la cabecera de la obra, bajo el nombre, junto a la ubicación |
| E4 | Avisos de 3 minutos que se apilan y tapan la tabla | Mostrar a la vista solo los 2 más recientes y un «+N en la campanita»; todos siguen en el panel |
| E5 | Fusionar el PR #163 | Después de T12 |

Si Eugenio elige en E3 y E4, el arreglo entra como T13 y T14 antes de T12.

## 3. Orden y reparto

Hay como máximo **2 agentes de Claude y 3 de Gemini a la vez**: el equipo se satura y hookify falla bajo carga. Las
corridas pesadas (suites completas y recorrido) van **de una en una**.

| Fase | Claude | Gemini en paralelo | Compuerta |
|---|---|---|---|
| **F1** (sin tocar la misma zona) | T11 (minutos) y T1 (agente) | T7 (hydrogen), T8 (carbon), T9 (argon, solo lectura) | T1 en verde con su mutante; T7 y T8 verificados por Claude |
| **F2** | T6 (diagnóstico) y T2 (recorrido de medición) | T10 (neon); segunda opinión de seguridad para T5 (neon, solo lectura) | Informe del recorrido sin regresiones; causa de T6 |
| **F3** | T5 (revisor de seguridad) y T4 (agente de mutantes) | T3, la revisión de las capturas (neon), con las capturas de T2 en claro y oscuro | Veredicto de seguridad cerrado; mutantes muertos; defectos visuales corregidos |
| **F4** | T12 | — | Suites y CI en verde; el PR «listo para revisar» |

**Reglas de siempre:**
- Gemini no corre nada ni hace commits. Escribe solo los archivos de su lote, y Claude prueba, corrige y confirma cada
  lote por separado.
- Prueba en rojo antes del código.
- No se tocan `core/`, `aplicacion/hoja.py` ni lo sellado por `reglas-congeladas-2026-11-24`.
- Ningún libro de la empresa ni nada derivado de él entra al repositorio (NORMAS §1); las pruebas usan casos construidos.
- Un gancho de hookify que bloquea se reintenta una vez y, si vuelve, se para.
- No se corre prettier.
- Antes de cerrar, `npm run muerto` en local, porque la CI lo pide.

## 4. Estimación

| Fase | Duración |
|---|---|
| F1 | medio día |
| F2 | medio día |
| F3 | un día |
| F4 | medio día, más los ~20 minutos de la CI |

Son **dos días y medio** de trabajo, con margen hasta el 2026-12-16. El riesgo mayor es T3: si la revisión visual
encuentra muchos defectos en modo oscuro, F3 se alarga. Si eso pasa, se arreglan primero los de las pantallas de la
prueba con personas (T1 a T3 del guion de uso y la prueba de las 6 alertas).
