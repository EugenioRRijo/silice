# Plan del autocompletado guiado (AC1–AC4)

**Origen:** pedido de Eugenio del 2026-10-21. Eugenio no es experto: pedirle un «código» a secas es ambiguo, y quiere que
los campos de datos propongan lo que ya existe, como MaPreX. Diseño aprobado:
[2026-10-21-autocompletado-de-campos-design.md](../especificaciones/2026-10-21-autocompletado-de-campos-design.md),
con su sección «Enmiendas 2026-11-05».
**Rama:** `feature/autocompletado`, desde `main` (076793b8). **Estado del proyecto:** [ESTADO.md](../ESTADO.md).

## Auditoría de partida (2026-11-05, solo lectura)

- Componente base: `comun/CampoConBusqueda.tsx`, combobox ARIA 1.2 con pausa de 300 ms, mínimo 2 letras, grupos, «Ver
  más», `valorPropio` y `enCelda`. Con adaptadores en `comun/CampoDeConsulta.tsx` y `comun/consulta.ts` sobre
  `GET /v1/consulta/{tabla}`.
- Ya guiados: Agregar partida, línea del APU, el código de Componer, Mercado (estudio e histórico) y los códigos de
  Producción.
- Sin guiar, prioridad ALTA (7): descripción del insumo en Componer; «Partida» en Control (valuación y costo real) y en
  Reajuste (ejecutado); «Serie» en Reajuste; insumo en Escenarios; insumos del Simulador.
- Prioridad MEDIA: unidades (Componer y APU), moneda de Actualizar precios, versión de comprobación de Reajuste y
  proveedor al cotizar. El resto es texto libre o un identificador nuevo (BAJA).

## Tareas y criterios de aceptación

| Tarea | Qué | Se acepta si | Estado |
|---|---|---|---|
| AC1 | Descripción del insumo en Componer (insumos y oficios) | Se elige del catálogo, se puede escribir una propia (queda avisada) y el teclado de la tabla sigue igual | ✔ |
| AC1b | El precio que se llena | Sale de la lista con que arma la carpeta a la «Fecha» de la composición; en otra moneda no se copia y se avisa; sin fecha o sin lista, solo descripción y unidad | ✔ |
| AC2 | Partida del contrato y serie de índices | Control y Reajuste sugieren solo las partidas de la versión del contrato; la valuación no admite una fuera de él (salvo lista recortada); las series salen de una ruta de solo lectura | ✔ |
| AC2c | Campos en celda | Sin etiqueta a la vista ni botón «Borrar» en celda; fuera de celda, sin cambios | ✔ |
| AC3 | Escenarios y Simulador | Insumo con la descripción exacta; selección múltiple con etiquetas quitables y anuncios; Escenarios dice qué precios no cambiaron nada y el Simulador envía una lista (el texto con comas se sigue aceptando; `null` son todos, una lista vacía o un texto de solo comas, ninguno; hasta 200 nombres y 20.000 caracteres) | ✔ |
| AC4 | Unidad, moneda, versión y proveedor | Unidades del catálogo agrupadas con el normalizador del núcleo; moneda y versión como `Select`; proveedores de cotizaciones activas, admitiendo uno nuevo | ✔ |

Reglas comunes: TDD (rojo en un commit aparte), `core/` intacto, toda ruta nueva de solo lectura con su fila en
`tests/unit/test_api_acceso_por_ruta.py` y `docs/api.json` al día, cifras como texto con coma decimal y nada calculado
en el cliente.

## Arbitraje

[Árbitro final de Claude, esfuerzo xhigh](../bitacora/arbitrajes/autocompletado-claude-xhigh.md) (2026-11-05):
**DEVUELTO** por dos bloqueantes de dinero en Componer (precio de la lista de otra fecha; filas con el precio de otro
insumo) y dos mayores (Esc en el panel; la sugerencia no mostraba precio, moneda ni fecha). Corregidos con su prueba en
rojo primero, junto con los menores. [Ronda 2](../bitacora/arbitrajes/autocompletado-claude-xhigh-r2.md): DEVUELTO por
un MAYOR nuevo (una fila precargada o de MaPreX se mezclaba al elegir del catálogo); en corrección. ERS: RF-163, RF-164
y RNF-30.
