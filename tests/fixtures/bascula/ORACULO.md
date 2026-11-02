# Oráculo de los fixtures de báscula (ejemplo construido)

**Todo lo de esta carpeta es un EJEMPLO CONSTRUIDO.** Ninguna placa, cliente, ticket ni peso es real ni sale de un
reporte de empresa alguna (B-4: no hay muestras reales; los reportes reales son confidenciales y nunca van al
repositorio). Los valores esperados de este archivo se calcularon **a mano, antes** que los generadores de
`construir.py` y que el lector de `produccion/conectores/bascula.py`; ninguna prueba los obtiene ejecutando el
código que verifica.

Convenciones: fecha de referencia de las pruebas de lectura = `2026-10-18` (la manda el cliente, no el reloj).
Los pesos del archivo están **todos en kg** (la unidad sale del encabezado «(kg)»); el lector los pasa a toneladas
con `kg / 1000`. La densidad `1,60 t/m³` de ARENA es **del fixture** (ejemplo construido), no un valor del
producto, y no se mezcla con el 1,65 de PLAN_FUENTES C-5/C-6. Los generadores escriben UTF-8 sin BOM, fin de
línea `\n` y delimitador `;` en el CSV; el xlsx lleva una sola hoja llamada `Reporte`.

## 1. Reporte básico: `csv_basico()` y `xlsx_basico()`

Encabezados (fila 1): `Ticket; Fecha; Placa; Cliente; Material; Bruto (kg); Tara (kg); Neto (kg)`.
Seis filas de datos. En el CSV los pesos son texto sin separador de miles (`42500`); en el xlsx son números
nativos enteros (`42500`); la fecha es texto ISO `YYYY-MM-DD` en ambos. Celda a celda, el xlsx y el CSV son
iguales (el xlsx con `str(entero)`).

| Fila | Ticket | Fecha | Placa | Cliente | Material | Bruto kg | Tara kg | Neto kg |
|---|---|---|---|---|---|---|---|---|
| 1 | TCK-001 | 2026-10-15 | EJ-001 | Cliente Ejemplo A | ARENA | 42500 | 14200 | 28300 |
| 2 | TCK-002 | 2026-10-15 | EJ-002 | Cliente Ejemplo B | PIEDRA34 | 38000 | 13500 | 24500 |
| 3 | TCK-003 | 2026-10-16 | EJ-003 | Cliente Ejemplo A | ARENA | 42000 | 45000 | -3000 |
| 4 | TCK-004 | 2026-10-16 | EJ-004 | Cliente Ejemplo C | ARENA | 40000 | 15000 | 20000 |
| 5 | TCK-005 | 2026-12-31 | EJ-005 | Cliente Ejemplo B | PIEDRA34 | 40000 | 15000 | 25000 |
| 6 | TCK-006 | 2026-10-17 | EJ-006 | Cliente Ejemplo C | GRAVA9 | 40000 | 15000 | 25000 |

### Resultado esperado por fila (con unidad kg, referencia 2026-10-18)

| Fila | Cuenta a mano | Resultado esperado |
|---|---|---|
| 1 | 42 500 − 14 200 = 28 300 kg; 28 300 / 1000 = **28,300 t**; neto del archivo 28 300 = bruto − tara (coincide). Con densidad 1,60 t/m³: 28,300 / 1,60 = **17,6875 m³** (comprobación: 17,6875 × 1,60 = 28,3000) | **leído**: bruto 42,5 t, tara 14,2 t, neto `Decimal("28.300")`; despacho de 28,300 t = 17,6875 m³ |
| 2 | 38 000 − 13 500 = 24 500 kg; 24 500 / 1000 = **24,5 t**; neto del archivo 24 500 = bruto − tara (coincide). Material en toneladas: no necesita densidad | **leído**: bruto 38,0 t, tara 13,5 t, neto `Decimal("24.5")`; despacho de **24,5 t** |
| 3 | tara 45 000 kg ≥ bruto 42 000 kg (45 000 − 42 000 = 3 000 de exceso). El neto del archivo es 42 000 − 45 000 = −3 000, coherente con bruto − tara, así que **solo** salta la regla de la tara | **dudoso**, motivo exacto «tara mayor o igual que el bruto» |
| 4 | bruto − tara = 40 000 − 15 000 = 25 000 kg; el archivo dice 20 000; diferencia 5 000 kg ≠ 0 (tolerancia 0) | **dudoso**, motivo exacto «neto distinto de bruto − tara» |
| 5 | 2026-12-31 es posterior a la referencia 2026-10-18 (74 días después: 13 días de octubre + 30 de noviembre + 31 de diciembre = 74); pesos coherentes (40 000 − 15 000 = 25 000) | **dudoso**, motivo exacto «fecha futura» |
| 6 | pesos coherentes (40 000 − 15 000 = 25 000); `GRAVA9` no está en el catálogo del caso de prueba | **leído** por el lector (no conoce el catálogo); la **importación** con catálogo (ARENA, PIEDRA34) lo manda a la bandeja con el motivo exacto «material desconocido» |

Totales del archivo: el **lector** da **3 leídos (filas 1, 2 y 6) y 3 dudosos (filas 3, 4 y 5)**; tras la **importación** con el catálogo de la prueba quedan **2 despachos y 4 en la bandeja** (6 filas de datos, sin ticket repetido). Los números de fila del
lector son los del archivo contando el encabezado como fila 1: las filas de datos van de la 2 a la 7 (fila de la
tabla + 1).

Nota sobre quién decide qué (para no mezclar capas): las reglas de las filas 3, 4 y 5 son de forma y salen del
archivo y de la fecha de referencia; la de la fila 6 depende del catálogo de materiales y la decide la **importación** (decisión de la sesión 4:
el lector no conoce el catálogo); el motivo escrito es el de la tabla.
En la fila 3 el neto (−3000) es justo bruto − tara, por eso la regla del neto no salta y el motivo es único; si el
lector tuviera además una regla de «neto negativo», habría que registrar aquí su motivo (hoy el plan no la tiene).

### Si se importa el básico (despachos en m³, densidad de ARENA = 1,60 t/m³ del fixture)

| Material | Toneladas | Cuenta | Despacho |
|---|---|---|---|
| ARENA (fila 1) | 28,300 | 28,300 / 1,60 | **17,6875 m³** |
| PIEDRA34 (fila 2) | 24,5 | sin conversión | **24,5 t** |

Sin las filas 3 a 6 en los despachos: la bandeja de sospechosos recibe 4 filas y no se crea ningún despacho para
ellas. Reimportar el mismo archivo deja **2 despachos y 4 sospechosos** (no duplica; la clave es el ticket).

## 2. `xlsx_sin_unidad()`

Mismo contenido que el reporte básico (mismos tickets, mismos números nativos), pero los encabezados de peso
**no llevan unidad**: `Bruto`, `Tara`, `Neto` (los otros cinco encabezados no cambian).

Esperado (RT-S4-6): sin `unidad_peso` explícita, el archivo **no se importa**: ningún pesaje leído, ningún
dudoso, y el mensaje para el usuario es «Indique si los pesos están en kg o en t.». Con `unidad_peso="kg"` dado por
el usuario, el resultado es idéntico al del reporte básico (sección 1: el lector da 3 leídos y 3 dudosos). Con `unidad_peso="t"`
los mismos números serían toneladas (el mismo 42 500 sería 42 500 t, absurdo): esa es la razón de no adivinar.

## 3. `csv_coma_decimal()`

Mismos encabezados con unidad que el básico (`Bruto (kg)`, `Tara (kg)`, `Neto (kg)`), delimitador `;`, y tres filas
de datos (texto en las celdas de peso). Fecha 2026-10-15, material `ARENA`.

| Fila | Ticket | Bruto (texto) | Tara (texto) | Neto (texto) |
|---|---|---|---|---|
| 1 | TCK-101 | `1.234,56` | `234,56` | `1.000,00` |
| 2 | TCK-102 | `1,234.56` | `234.56` | `1,000.00` |
| 3 | TCK-103 | `42500` | `14200` | `28,300` |

Lectura a mano:

- Fila 1 (formato europeo, punto de miles y coma decimal): `1.234,56` kg = 1234,56; `234,56` = 234,56;
  `1.000,00` = 1000,00. Neto: 1234,56 − 234,56 = 1000,00 (coincide). En toneladas: 1,23456 / 0,23456 / 1,00000.
  **Leída exacta**: bruto `Decimal("1234.56")` kg.
- Fila 2 (formato anglosajón, coma de miles y punto decimal): `1,234.56` = 1234,56; `234.56` = 234,56; `1,000.00`
  = 1000,00. Igual que la fila 1 en valor. **Leída exacta**: bruto `Decimal("1234.56")` kg. Las filas 1 y 2 dan los
  mismos tres números.
- Fila 3: `28,300` tiene un solo separador y exactamente tres cifras después: puede ser 28,3 (coma decimal) o
  28 300 (coma de miles). Es **ambiguo**: no se adivina. Esperado: **dudoso**, motivo exacto «número ambiguo»
  (tendría sentido 28 300 por 42 500 − 14 200 = 28 300, pero esa coincidencia no la usa el lector para decidir).

Totales: **2 leídos (TCK-101, TCK-102) y 1 dudoso (TCK-103, «número ambiguo»)**.

## 4. `xlsx_con_macros_renombrado()`

Un libro `.xlsx` válido por fuera (el del reporte básico, un ZIP con `[Content_Types].xml`, `xl/workbook.xml`,
etc.) al que se le añade la pieza `xl/vbaProject.bin` (contenido de relleno rotulado «ejemplo construido»: no es una
macro ni código ejecutable). Se entrega con extensión `.xlsx` aunque su contenido sea de un libro con macros.

Esperado: **rechazo** por contener macros (la guardia `verificar_archivo` lo nombra «vbaProject.bin»); no se lee
ningún pesaje ni se toca la base. Mensaje comprobable por el nombre de la pieza: contiene «macros».

## 5. `csv_desmedido(filas)`

Mismos encabezados y delimitador que el básico; `filas` líneas de datos. Cada línea `i` (de 1 a `filas`):
`TCK-{i:06d}; 2026-10-01; EJ-{i:06d}; Cliente Ejemplo A; ARENA; 40000; 15000; 25000` (40 000 − 15 000 = 25 000, todas
coherentes, por lo que lo único anormal es el tamaño).

Total de líneas = 1 (encabezado) + `filas`. Con `filas=200000`: **200 001 líneas** (200 000 de datos). Como
`MAX_FILAS = 100000` (PLAN_SESION_4_ARENERA, constantes de `produccion/fuentes.py`, CONSTRUIDO) y 200 000 > 100 000, esperado: **rechazo con mensaje y sin
leer ni importar nada**. Un archivo con `filas = 100000` (100 001 líneas contando el encabezado) está justo en el
borde y no lo cubre este fixture: es una prueba de frontera de `test_conector_bascula.py`, con su propia cuenta.
