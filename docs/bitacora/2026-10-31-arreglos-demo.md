# Arreglos urgentes para la demostración del 1 de noviembre (rama inc/vial-arreglos-demo)

Origen: la pasada de navegador a 1366x768 del 31-10 (capturas en el directorio de trabajo de la sesión, `scratchpad/navegador/capturas/`).
Cada arreglo tiene su prueba, vista en rojo antes del arreglo. Todo en es-VE, solo tokens de Carbon (ningún color nuevo).

| # | Problema | Captura | Arreglo | Commit |
|---|----------|---------|---------|--------|
| 1 | Hoja › Presupuesto: cada fila medía ~10.000 px; el aviso largo del Estado quedaba a una letra por línea | 11_hoja, 11_hoja_completa | `.silice-hoja__estado-texto`: ancho mínimo 14 rem y a lo más 3 líneas (`line-clamp`); el texto completo sigue en el `title` de la fila. Se eligió porque no añade controles y no pierde información | e27c71c1 |
| 2 | «Tramos» no salía en la barra lateral hasta tener tramos; desde el buscador sin obra llevaba a Pendientes sin avisar | 08_buscador_tramos, 08b_obra_resumen, 09_tramos_vacio | «Tramos» es sección de toda obra mientras el módulo vial esté encendido (se retiran `soloVial` y `useObrasViales`). El buscador ya no ofrece la pantalla suelta «Tramos de la vía» sin obra: ofrece «Obra › Tramos» | 0319db18 |
| 3 | Auditoría: Impacto, Observado y Esperado con punto decimal; el código C-000.000.001 se partía | 11b_hoja_auditoria | `presentar: formatoEsVe` en las tres columnas; la partida va en un `span.silice-informe__codigo` con `white-space: nowrap` | 5dd18e85 |
| 4 | «fracción pintada 0.375» con punto | 09c_tramos_llevados | `adapters/vial/derivacion.py` formatea con la biblioteca estándar («0,375»). Ninguna prueba ni oráculo fijaba esa descripción; se añadió la prueba | d8a87f8a |
| 5 | Receta de la planta: «Producto (código)» buscaba en el catálogo de la carpeta y no hallaba las mezclas | 05_receta_escribiendo, 05c_receta_formulario | Los materiales de la arenera viven en la base de la instalación (no en la de la carpeta que lee `/v1/consulta`), así que no se añadió tabla en `aplicacion/consulta.py`: se usa `GET /v1/produccion/materiales`, que la pantalla ya pide, con filtro local (sin tildes, todas las palabras). Producto: `materiales_produccion`; componentes: materiales propios y, debajo, insumos del catálogo | 3d3efdfa, 04901688 |
| 6 | Diálogos «Registrar un costo» y «Registrar una receta nueva» cortados contra el pie sin señal de desplazamiento | 04b_costos_formulario, 05c_receta_formulario | El cuerpo de `MarcoDeDialogo` ya se desplazaba; ahora lleva sombras de desplazamiento (CSS puro, solo si hay más contenido). La fila del componente de la receta va en una línea (código, cantidad, unidad, tipo, Quitar) y «Quitar» queda alineado | d9bd1652 |
| 7 | Control › Valuaciones: «Total con IVA» cortada a la derecha | 21a_valuaciones | Relleno compacto (0,5 rem) en las celdas de las tablas de Control y cifras sin partir; si aun así no cupiera, `.silice-tabla` ya se desplaza dentro de su caja | 91f24249 |
| 8a | Unidades «m2»/«m3» en las tablas de Tramos | 10_tramos_llevados_ok | Se presentan «m²»/«m³» solo en la columna Unidad (`presentar`); el valor del servidor no cambia | commit de detalles |
| 8b | El foco del aviso verde se veía como una caja negra más ancha que el aviso | 09c_tramos_llevados | `AvisoConFoco` lleva `.silice-aviso-foco`: `fit-content` y anillo `--cds-focus` por dentro | commit de detalles |

## Notas

- No se tocó `core/`, `aplicacion/hoja.py`, `aplicacion/composicion.py` ni `asistente/experimento`, ni los archivos de «Llevar al presupuesto» (`aplicacion/hoja_vial.py`, `aplicacion/vial.py`, `api/rutas/vial.py`).
- No se verificó en navegador (no se abrió): las pruebas de CSS leen el fuente, como las demás del repositorio; conviene una mirada a 1366x768 en los ocho puntos antes de la demostración.
- Pendiente fuera de alcance: `#/tramos` escrito a mano sin obra sigue yendo a Pendientes (sin consulta en la dirección, `RutaVieja`); ya no se ofrece desde el buscador.
