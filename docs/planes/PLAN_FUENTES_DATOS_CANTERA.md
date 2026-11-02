# Plan de fuentes: cifras y fórmulas de la arenera y de la auditoría visual

> **Fecha:** 2026-10-18 · **Pedido:** Eugenio («darle un plan fuente a la 5») · **Lo ejecuta:** sesión 4.0 de la
> [ruta](./RUTA_SESIONES.md) (orquestador + `silice-rev-hechos`); lo usan `silice-arenera` y quien escriba un dato
> en una skill, un plan o una prueba.
> **Regla madre:** `NORMAS.md` §1, naturaleza de los datos (real-confidencial, real autorizado, anonimizado,
> construido).

## 1. Por qué

El [plan del gestor](./PLAN_GESTOR_PRODUCCION_Y_AUDITORIA_VISUAL.md) y las skills, **en su texto anterior a la
sesión 0** (antes del commit `3efffdf`), traían cifras (18,50 $/m³, coeficientes 1,15/1,00/0,85, densidad 1,65 t/m³
por defecto, rescate 20 %, vida útil 10 000 h…) y fórmulas (costo horario «Caterpillar/USBR») **sin fuente**. La
columna «Texto anterior» de §3.2 conserva lo que decían; la columna «Acción» dice cómo quedó. En una tesis cada número tiene que poder decir de dónde salió; en un producto real, un número
inventado dentro de un cálculo es un error que el auditor no puede detectar porque es *consistente*.

## 2. Estados de un dato

| Estado | Qué significa | ¿Puede entrar en un cálculo del producto? |
|---|---|---|
| **VERIFICADO** | Cotejado contra la fuente primaria; se registra edición, sección y página | Sí |
| **DATO DE LA EMPRESA** | Lo aporta la empresa (ensayo, factura, ficha del equipo, registro); es real-confidencial y vive fuera del repositorio | Sí, desde la configuración de la instalación, nunca escrito en el código |
| **A COTEJAR** | Hay una fuente candidata, aún no leída en su original | **No** |
| **CONSTRUIDO** | Ficticio, declarado como tal; sirve para pruebas y ejemplos | Solo en `tests/fixtures/` y en ejemplos rotulados «ejemplo construido» |
| **A MEDIR** | Meta de rendimiento del propio sistema | No es un dato: se mide y se registra en `docs/plan_pruebas.md` |
| **SIN FUENTE** | Nadie sabe de dónde salió | **Se retira** del texto o se reemplaza |

## 3. Inventario de cifras y fórmulas

### 3.1 Fórmulas

| # | Fórmula | Dónde aparece | Estado | Fuente candidata | Observación |
|---|---|---|---|---|---|
| F-1 | Costo horario $C_H$ = posesión + operación | Plan gestor §3.2; skill `gestor-produccion-aridos` §1 | A COTEJAR | *Caterpillar Performance Handbook*, sección «Owning and Operating Costs» (fijar edición); USACE **EP 1110-1-8**, *Construction Equipment Ownership and Operating Expense Schedule*; Peurifoy et al., *Construction Planning, Equipment, and Methods* (McGraw-Hill) | El plan dice «USBR»; no se conoce un método de costo horario del USBR. Lo más probable es que se trate del **USACE EP 1110-1-8**: a confirmar |
| F-2 | Interés, seguro e impuestos = $V_a(i+s+t)/H_a$ | Plan gestor §3.2; skill §1 | A COTEJAR, **probable error** | Peurifoy et al. calculan esos cargos sobre la **inversión media anual** y no sobre $V_a$ | Si se confirma, sobre $V_a$ se sobrestima el cargo; se corrige al cotejar |
| F-3 | Rendimiento de planta = Σ coproductos despachados / alimentado × 100 | Plan gestor §3.1 | CONSTRUIDO (definición propia) | — | Válida como definición; declarar unidad (t o m³, no mezclar) |
| F-4 | Reparto del costo del turno entre coproductos | Skill §2 | A COTEJAR | Costos conjuntos: Horngren, Datar y Rajan, *Cost Accounting: A Managerial Emphasis* (medida física, valor de venta en el punto de separación, valor neto realizable) | Por defecto, reparto por **masa** (t); por valor de venta, solo con precios de la empresa |
| F-5 | Existencia = Σ entradas − Σ despachos ± ajustes | Ruta RT-7 | CONSTRUIDO (identidad contable) | — | No necesita fuente; los **datos** sí (§3.3) |

### 3.2 Cifras

| # | Cifra | Dónde aparece | Texto anterior (antes de `3efffdf`) | Estado | Acción |
|---|---|---|---|---|---|
| C-1 | Arena 18,50 $/m³; piedra 3/4" 16,20 $/m³; DTO 18,50 / 4,20 / 6,80 / 1,30 / 30,80 | Plan gestor §6.1; skill §2 | igual | CONSTRUIDO | Rotulado «ejemplo construido» en la skill |
| C-2 | «Cantera Las Mercedes»: 42 $/m³ declarado frente a 18 + 9 de flete | Plan gestor §4.1; skill `auditoria-forense` | «+55.5%» | CONSTRUIDO | (42 − 27)/27 = 0,5556 → **+55,6 %**; corregido en el plan del gestor y rotulado |
| C-3 | Coeficientes de valor 1,15 / 1,00 / 0,85 | Skill §2 | presentes | **SIN FUENTE** | Retirados; reemplazados por el método F-4 |
| C-4 | Valor de rescate; vida útil | Skill §1 | «típicamente 20 %», «ej. 10.000 h» | A COTEJAR | Retirados: **sin valor por defecto**; por equipo, DATO DE LA EMPRESA (ficha o factura); valores de referencia de F-1 al cotejar |
| C-5 | Densidad aparente de la arena 1,65 t/m³ | Plan gestor §6.1 (DTO) | `default=Decimal("1.65")` | A COTEJAR | Corregido: campo **obligatorio** (queda solo como `example`); DATO DE LA EMPRESA por material, por ensayo de peso unitario (ASTM C29/C29M; COVENIN 263, a cotejar) |
| C-6 | Ticket: 42,50 − 14,20 = 28,30 t → volumen | Plan gestor §6.3 (DTO) | `example=17.68` (28,30/17,68 = 1,60 t/m³, incoherente con el 1,65 del mismo plan) | CONSTRUIDO | Corregido a `example=17.15` (28,30 / 1,65) |
| C-7 | Fracciones: arena 0–4 mm; piedra 1/2" (12,5 mm), 3/4" (19 mm), 1" (25 mm) | Plan gestor §3.1 | igual | A COTEJAR | ASTM C33 / COVENIN 277 (requisitos de agregados); el corte de la arena suele ser el tamiz N.º 4 (4,75 mm), no 4 mm |
| C-8 | Formatos de báscula «Toledo, Cardinal» | Plan gestor SA5 | igual | DATO DE LA EMPRESA | Cada indicador exporta distinto: hacen falta **muestras reales** (B-4), que se anonimizan |
| C-9 | Tooltip de atípico | Skill `front-carbon-fiori-ibcs` §1.2 | «puntuación de anomalía > 0.65» (**falso** frente al código) | — | Corregido a la convención de `ml/anomaly/detector.py`: más negativo = más atípico, corte `UMBRAL_ATIPICO = -0.05` |
| C-10 | Tauri < 15 MB; 35–50 MB de RAM en reposo | Plan gestor §1 | igual | A MEDIR | Se mide en la sesión 5 |
| C-11 | 60 FPS con 50 000 filas | Plan gestor SA3 | igual | A MEDIR | Se mide en la sesión 2 con un libro construido de 50 000 filas |
| C-12 | Watchdog: relanza en < 1 s | Plan gestor §7 | igual | A MEDIR | Se mide en la sesión 5 |

| C-13 | Límites de lectura de reportes de báscula: 100 000 filas, 60 columnas, 30 filas de búsqueda del encabezado, tolerancia del neto 0 | Plan de la sesión 4 (`produccion/fuentes.py`), RNF-25 | — | CONSTRUIDO | Son decisiones de este sistema, no datos de la báscula; la ERS cita las mismas cifras y la prueba de `produccion/fuentes.py` las compara con la constante |
| C-14 | Tope de cuerpo de la API: 20 MiB | `api/proteccion.py:34` | igual | CONSTRUIDO | Constante existente de la 1.0.0 (RF-98) |
| C-15 | Densidad 1,60 t/m³ de los fixtures de báscula | `tests/fixtures/bascula/` | — | CONSTRUIDO | Ejemplo construido, distinto a propósito del 1,65 de C-5/C-6 |

### 3.3 Datos que debe aportar la empresa (bloqueo B-4)

| Dato | Para qué | Forma |
|---|---|---|
| Lista de materiales que produce y vende la arenera, con su unidad de venta (m³ o t) | Existencias | Tabla simple |
| Existencia inicial por material y cómo la miden (pila con cinta, topografía, dron) | Punto de partida y ajustes | Tabla + método |
| Densidad aparente por material (ensayo propio o del laboratorio) | Pasar de t (báscula) a m³ (venta) | Valor + fecha del ensayo |
| 2–3 reportes reales de la báscula de salida, en el formato en que los exporta | Importador y detector de columnas | `.xlsx`/`.csv`; se anonimizan antes de usarse en pruebas |
| Existencia mínima deseada por material | Alerta «queda poco» | Tabla |
| (Más adelante) fichas de la maquinaria: valor de compra, año, horas por año, consumo de diésel | Costo horario (tarea 4.6) | Tabla |

## 4. Procedimiento (sesión 4.0)

1. `silice-rev-hechos` recorre §3 y confirma que cada línea del plan del gestor y de las skills con un número
   tiene su estado aquí.
2. El orquestador coteja cada fuente A COTEJAR en su original (edición, sección, página) y la pasa a VERIFICADO o a
   SIN FUENTE. Lo que no se pueda leer en el original queda A COTEJAR y **no entra** a ningún cálculo.
3. `produccion/` carga las constantes desde la configuración de la instalación con su estado y fuente; una prueba
   recorre esa configuración y falla si una constante usada en un cálculo está A COTEJAR o SIN FUENTE.
4. La tarea 4.6 (costo horario) solo se abre si F-1 y F-2 quedan VERIFICADO.

## 5. Correcciones aplicadas en la sesión 0

- Skill `front-carbon-fiori-ibcs`: el tooltip usa la convención real del detector (C-9) y el ejemplo de tarjeta usa
  los tokens de Carbon en vez de colores sueltos de Tailwind.
- Skill `gestor-produccion-aridos`: retirados los coeficientes 1,15/1,00/0,85 (C-3); los costos se rotulan
  «ejemplo construido» (C-1); la fórmula queda «a cotejar» (F-1, F-2).
- Skill `auditoria-forense`: el ejemplo de parche queda rotulado «ejemplo construido» (C-2).
- Plan del gestor: las enmiendas de su §0 remiten aquí.
