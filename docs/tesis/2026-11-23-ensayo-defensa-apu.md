# Guía de ensayo para la defensa: cálculo a mano de un APU vial en Sílice

> Borrador preparado por Gemini 4 Carbon (solo lectura) y revisado por Claude el 2026-11-23: las siete fórmulas de `calcular_apu` (`core/costing/motor.py`), los valores por omisión de `ParametrosCosto`, el FCAS (`aplicacion/fcas.py`), el IVA (`aplicacion/impuestos.py`), el desperdicio y las reglas citadas se comprobaron línea por línea contra el código. Ensayarlo en voz alta, sin mirar, cada semana.

> **Nota sobre los datos:** Todas las obras, empresas, insumos, rendimientos y precios de este documento son **100 % ficticios**, construidos con cifras redondas para explicar el cálculo en pizarra ([NORMAS.md](../../NORMAS.md#L21-L42)). En el repositorio existen tramos viales ficticios ([data/samples/vial/via_ficticia.csv](../../data/samples/vial/via_ficticia.csv)) y hojas viales ficticias de prueba ([tests/fixtures/libro_apu_por_hoja.py](../../tests/fixtures/libro_apu_por_hoja.py)), pero `seed_demo.py` siembra tuberías de agua potable; por eso aquí se arma desde cero una carpeta asfáltica ficticia siguiendo exactamente el catálogo vial de Sílice ([adapters/vial/constantes.py](../../adapters/vial/constantes.py#L94-L98)).

---

## 1. Cálculo paso a paso del APU vial (a mano y en el orden de Sílice)

**Caso ficticio:** Constructora Ficticia El Ensayo, C.A. · Obra: «Repavimentación Ficticia Tramo T1».
- **Partida:** `C-000.000.023` — Colocación de carpeta de concreto asfáltico, medida en masa (con suministro de mezcla).
- **Unidad de la partida:** tonelada (`t`). **Rendimiento:** `100,00 t/día` (lo que la cuadrilla coloca en una jornada).
- **Parámetros de costo** (los valores por defecto de `ParametrosCosto` en [core/contracts/apu.py](../../core/contracts/apu.py#L143-L155)):
  `fcas = 6,00` (`600 %`), `bono_alimentacion = 1,00 USD/obrero-día`, `administracion = 0,15` (`15 %`), `utilidad = 0,10` (`10 %`).

### Pasos previos fuera del núcleo (`adapters/` y `aplicacion/`)

**Paso 0a — Cantidad total de la partida desde el tramo vial**
- **Dónde vive:** [adapters/vial/modelo.py](../../adapters/vial/modelo.py#L275-L277) (`Tramo.longitud_m`) y [adapters/vial/derivacion.py](../../adapters/vial/derivacion.py#L59-L157) (`derivar_tramos`, regla `MASA`).
- **Fórmula en palabras:** Longitud = diferencia de progresivas en km por mil. Masa = longitud × ancho × espesor × densidad compactada.
- **Cuenta (tramo ficticio `T1`, de `0,00` a `1,00 km`, ancho `5,00 m`, espesor `0,05 m`, densidad `2,00 t/m³`):**
  `Longitud = (1,00 − 0,00) × 1.000 = 1.000 m` → `Masa = 1.000 × 5,00 × 0,05 × 2,00 =` **`500,00 t`**.

**Paso 0b — Desperdicio de materiales**
- **Dónde vive:** [aplicacion/regla_desperdicio.py](../../aplicacion/regla_desperdicio.py#L35-L37) (`cantidad_con_desperdicio`). *Nota:* en `core/` no existe un campo `desperdicio` dentro de `LineaMaterial` para no romper el contrato estable; Sílice incorpora la merma en la cantidad antes de llamar al motor y guarda la traza aparte.
- **Fórmula en palabras:** Cantidad con desperdicio = cantidad neta × (`1` + porcentaje ÷ `100`).
- **Cuenta:**
  - Mezcla asfáltica en caliente (ficticia): `1,00 t` neta con `5 %` de merma → `1,00 × (1 + 5 ÷ 100) =` **`1,05 t`**.
  - Gasoil de limpieza (ficticio): `2,00 l` netos con `0 %` de merma → `2,00 × (1 + 0 ÷ 100) =` **`2,00 l`**.

*(Nota sobre el FCAS: `calcular_apu` recibe `fcas` ya calculado, p. ej. `6,00`. Cuando la empresa lo deriva desde días feriados, vacaciones, utilidades y aportes patronales, usa `calcular_fcas` en [aplicacion/fcas.py](../../aplicacion/fcas.py#L173-L210): `fcas = (días_pagados ÷ días_trabajados) × (1 + Σ aportes) − 1`, sin incluir el bono de alimentación).*

---

### El motor puro del núcleo: `calcular_apu` ([core/costing/motor.py](../../core/costing/motor.py#L26-L70))

Todo ocurre en `Decimal` exacto, sin redondeos intermedios ([NORMAS.md §4](../../NORMAS.md#L102-L116)).

**Paso 1 — Materiales por unidad de partida (NO se dividen entre el rendimiento)**
- **Dónde vive:** [core/contracts/apu.py](../../core/contracts/apu.py#L43-L45) (`LineaMaterial.total`) y [core/costing/motor.py](../../core/costing/motor.py#L32) (`calcular_apu`).
- **Fórmula en palabras:** Se multiplica la cantidad por unidad de cada material por su precio y se suman las líneas.
- **Cuenta:**
  - Mezcla asfáltica (ficticia): `1,05 t × 80,00 USD/t = 84,00 USD/t`
  - Gasoil de limpieza (ficticio): `2,00 l × 0,50 USD/l = 1,00 USD/t`
  - `materiales = 84,00 + 1,00 =` **`85,00 USD/t`**.

**Paso 2 — Equipos por unidad de partida**
- **Dónde vive:** [core/contracts/apu.py](../../core/contracts/apu.py#L64-L66) (`LineaEquipo.total`) y [core/costing/motor.py](../../core/costing/motor.py#L34-L35) (`calcular_apu`).
- **Fórmula en palabras:** Para cada equipo se multiplica cantidad × precio de reposición × factor de depreciación diario; se suma el costo diario de todos los equipos y se divide entre el rendimiento diario.
- **Cuenta:**
  - Pavimentadora ficticia: `1 × 60.000,00 USD × 0,01 = 600,00 USD/día`
  - Rodillo compactador ficticio: `1 × 30.000,00 USD × 0,01 = 300,00 USD/día`
  - Herramientas menores ficticias: `1 × 1.000,00 USD × 0,10 = 100,00 USD/día`
  - Suma diaria `equipos_total = 600,00 + 300,00 + 100,00 = 1.000,00 USD/día`
  - `equipos = 1.000,00 ÷ 100,00 =` **`10,00 USD/t`**.

**Paso 3 — Mano de obra a jornal (`JORNAL`)**
- **Dónde vive:** [core/contracts/apu.py](../../core/contracts/apu.py#L101-L139) (`LineaManoObra.total`, `ComposicionAPU.total_obreros`) y [core/costing/motor.py](../../core/costing/motor.py#L37-L46) (`calcular_apu`).
- **Fórmula en palabras:** Se multiplica el jornal diario de cada categoría por (`1` + FCAS); aparte se multiplica el bono diario de alimentación por el total de obreros a jornal; se suman ambos montos diarios y el total se divide entre el rendimiento.
- **Cuenta (cuadrilla ficticia de 10 trabajadores a jornal):**
  - `2` Operadores de maquinaria × `15,00 USD/día = 30,00 USD/día`
  - `8` Obreros / rastrilleros × `5,00 USD/día = 40,00 USD/día`
  - `sueldos_con_fcas = 30,00 × (1 + 6,00) + 40,00 × (1 + 6,00) = 210,00 + 280,00 = 490,00 USD/día`
  - `total_obreros = 2 + 8 = 10` → `bono_total = 1,00 USD × 10 = 10,00 USD/día`
  - `mano_obra_jornal = (490,00 + 10,00) ÷ 100,00 = 500,00 ÷ 100,00 =` **`5,00 USD/t`**.

**Paso 4 — Mano de obra a destajo (`DESTAJO`) y total de mano de obra**
- **Dónde vive:** [core/costing/motor.py](../../core/costing/motor.py#L49-L57) (`calcular_apu`).
- **Fórmula en palabras:** Las líneas a destajo suman `cantidad × precio_por_unidad` directo (sin FCAS, sin bono y sin dividir entre rendimiento). Luego se suma jornal más destajo.
- **Cuenta:** `mano_obra_destajo = 0,00 USD/t` → `mano_obra = 5,00 + 0,00 =` **`5,00 USD/t`**.

**Paso 5 — Costo directo unitario**
- **Dónde vive:** [core/costing/motor.py](../../core/costing/motor.py#L59) (`calcular_apu`).
- **Fórmula en palabras:** Suma de materiales, equipos y mano de obra por unidad.
- **Cuenta:** `costo_directo = 85,00 + 10,00 + 5,00 =` **`100,00 USD/t`**.

**Paso 6 — Subtotal con administración**
- **Dónde vive:** [core/costing/motor.py](../../core/costing/motor.py#L60) (`calcular_apu`). *(Nota: `ResultadoAPU` guarda el acumulado `con_administracion`, no el recargo suelto de `15,00 USD/t`).*
- **Fórmula en palabras:** Costo directo multiplicado por (`1` + fracción de administración).
- **Cuenta:** `con_administracion = 100,00 × (1 + 0,15) = 100,00 × 1,15 =` **`115,00 USD/t`**.

**Paso 7 — Precio unitario (utilidad en cascada)**
- **Dónde vive:** [core/costing/motor.py](../../core/costing/motor.py#L61) (`calcular_apu`) y presentación a dos decimales con `ROUND_HALF_UP` en [core/verification/texto.py](../../core/verification/texto.py#L216-L225) (`formatear_decimal`).
- **Fórmula en palabras:** Subtotal con administración multiplicado por (`1` + fracción de utilidad), en cascada.
- **Cuenta:** `precio_unitario = 115,00 × (1 + 0,10) = 115,00 × 1,10 =` **`126,50 USD/t`**.

---

### Cierre del presupuesto e IVA (fuera de `calcular_apu`)

**Paso 8 — Total del renglón y subtotal del presupuesto**
- **Dónde vive:** [core/contracts/presupuesto.py](../../core/contracts/presupuesto.py#L28-L56) (`PartidaPresupuestada.total`, `Presupuesto.total`).
- **Fórmula en palabras:** Cantidad de obra de la partida multiplicada por su precio unitario.
- **Cuenta:** `500,00 t × 126,50 USD/t =` **`63.250,00 USD`**.

**Paso 9 — IVA sobre el total del presupuesto**
- **Dónde vive:** **No existe en `core/`** (en Sílice el APU nunca lleva IVA). Vive en [aplicacion/impuestos.py](../../aplicacion/impuestos.py#L39-L46) (`con_iva`, constante `ALICUOTA_IVA = 0,16`).
- **Fórmula en palabras:** Subtotal redondeado a centavos; IVA = subtotal × `0,16` redondeado a centavos; Total con IVA = subtotal + IVA.
- **Cuenta:** `iva = 63.250,00 × 0,16 =` **`10.120,00 USD`** → `total = 63.250,00 + 10.120,00 =` **`73.370,00 USD`**.

---

## 2. Tabla final del APU como la ve la empresa (datos ficticios)

**Partida:** `C-000.000.023` — Colocación de carpeta de concreto asfáltico, medida en masa (ficticia)
**Unidad:** `t` · **Cantidad del tramo T1:** `500,00 t` · **Rendimiento:** `100,00 t/día` · **Moneda:** `USD`

| Rubro / Insumo (ficticio) | Unidad | Cantidad / Obreros | Desp. / Deprec. / Mod. | Precio o Jornal (USD) | Subtotal línea (USD) | Costo por `1 t` (USD) |
|---|---|---:|---:|---:|---:|---:|
| **1. MATERIALES** *(no se divide ÷ rend.)* | | | | | | **85,00** |
| Mezcla asfáltica en caliente (neta `1,00 t`) | t | 1,05 | +5,00 % desp. | 80,00 | 84,00 | 84,00 |
| Gasoil de limpieza | l | 2,00 | 0,00 % desp. | 0,50 | 1,00 | 1,00 |
| **2. EQUIPOS** *(total diario ÷ `100,00 t/día`)* | | | | | **1.000,00 /día** | **10,00** |
| Pavimentadora de asfalto (ficticia) | día | 1,00 | 0,01 deprec. | 60.000,00 | 600,00 /día | 6,00 |
| Rodillo compactador vibratorio (ficticio) | día | 1,00 | 0,01 deprec. | 30.000,00 | 300,00 /día | 3,00 |
| Herramientas menores (ficticias) | día | 1,00 | 0,10 deprec. | 1.000,00 | 100,00 /día | 1,00 |
| **3. MANO DE OBRA** *(total diario ÷ `100,00 t/día`)* | | **10,00** | | | **500,00 /día** | **5,00** |
| Operadores de maquinaria | jornal | 2,00 | jornal | 15,00 | 30,00 /día | — |
| Obreros / rastrilleros viales | jornal | 8,00 | jornal | 5,00 | 40,00 /día | — |
| *Recargo FCAS (`600 %`, factor `× 6,00` sobre `70,00`)* | — | — | — | — | *420,00 /día* | — |
| *Bono de alimentación (`10` obreros × `1,00 USD`)* | — | — | — | — | *10,00 /día* | — |
| **COSTO DIRECTO UNITARIO (`1 + 2 + 3`)** | | | | | | **100,00** |
| Administración y gastos generales (`15,00 %`) | | | | | *implícito: 15,00* | |
| **SUBTOTAL CON ADMINISTRACIÓN (`× 1,15`)** | | | | | | **115,00** |
| Utilidad e imprevistos (`10,00 %` en cascada) | | | | | *implícito: 11,50* | |
| **PRECIO UNITARIO SIN IVA (`× 1,10`)** | | | | | | **126,50** |

**Resumen en el Presupuesto (para `500,00 t`):** Subtotal sin IVA = **`63.250,00 USD`** · IVA (`16,00 %`) = **`10.120,00 USD`** · **Total con IVA = `73.370,00 USD`**.

---

## 3. Las 15 preguntas más probables del jurado (y cómo responderlas)

1. **¿Qué es el rendimiento y cómo afecta el precio unitario?**
   Es la cantidad de obra que la cuadrilla y sus máquinas producen en un día de trabajo; en nuestro ejemplo, `100,00 t/día`. Mientras más alto es el rendimiento, entre más toneladas se reparte el día de equipos y obreros, así que el precio unitario baja.

2. **¿Por qué los equipos y la mano de obra se dividen entre el rendimiento, pero los materiales no?**
   Porque las máquinas y los trabajadores se pagan por día trabajado, y ese día rinde `100,00 t`. En cambio, los materiales ya están medidos para una sola tonelada de carpeta (`1,05 t` de mezcla por cada tonelada colocada); dividirlos entre `100` los cobraría cien veces más baratos.

3. **¿Por qué un equipo de `60.000,00 USD` aporta solo `600,00 USD` al día?**
   Porque la pavimentadora no se gasta entera en un día ni en una sola obra. El factor de depreciación (`0,01`) representa la fracción diaria de desgaste, reposición y mantenimiento que le toca pagar a esa jornada.

4. **¿Qué es el FCAS y por qué en el ejemplo multiplica los salarios por `7`?**
   Es el Factor de Costos Asociados al Salario: vacaciones, utilidades, prestaciones sociales de la LOTTT, convención colectiva de la construcción y aportes como IVSS, FAOV e INCES. Un `fcas` de `6,00` significa `600 %` adicional sobre el salario básico, por eso `sueldo × (1 + 6,00)` multiplica por `7`.

5. **¿Por qué el bono de alimentación va separado del porcentaje del FCAS?**
   Porque legalmente no tiene carácter salarial y es un monto fijo por jornada y por obrero (`1,00 USD × 10 obreros`), sin importar cuánto gane cada cargo. En Sílice, la calculadora de FCAS rechaza meter el cestaticket como componente para impedir que se cobre dos veces.

6. **¿Qué cambia en la fórmula si una cuadrilla trabaja a destajo y no a jornal?**
   A destajo (artículo 114 de la LOTTT) se pacta un pago directo por tonelada colocada y no por día. Por eso Sílice suma esa línea completa al precio unitario: no le aplica FCAS, no le suma bono diario y no la divide entre el rendimiento.

7. **¿Por qué administración (`15 %`) y utilidad (`10 %`) se multiplican en cascada y no se suma `25 %`?**
   Porque en la práctica venezolana la administración (`15,00 USD`) cubre la oficina central sobre el costo directo (`100,00 → 115,00`), y la utilidad es la ganancia sobre todo lo que la empresa arriesga, incluida esa administración (`115,00 × 1,10 = 126,50`). Sumar `25 %` daría `125,00 USD/t` y omitiría `1,50 USD/t`.

8. **¿Por qué el IVA (`16 %`) no está dentro del APU?**
   Porque los precios unitarios de obra se contratan y valúan sin impuestos, y el IVA se aplica una sola vez al pie del presupuesto o de la valuación (`aplicacion/impuestos.py`). Si un APU incluye impuesto adentro, la auditoría de Sílice (`AH4`) advierte que se estaría cobrando IVA dos veces.

9. **¿Cómo maneja Sílice el desperdicio de materiales sin tocar `core/`?**
   Multiplica antes la cantidad neta por `1 + desperdicio ÷ 100` (`1,00 t + 5 % = 1,05 t`) y guarda la neta y el porcentaje en una tabla aditiva fuera del núcleo. Así el cálculo es exacto y se respeta el principio arquitectónico de contratos estables en `core/`.

10. **¿Por qué usaste `Decimal` en lugar de `float` y en qué momento redondeas?**
    En coma flotante binaria (`float`), números como `0,1` tienen error de representación y acumulan descuadres de centavos entre hojas. Sílice calcula todo en `Decimal` exacto de 28 dígitos sin redondeos intermedios y solo redondea a dos decimales (`ROUND_HALF_UP`) al mostrar o exportar cifras.

11. **¿Qué pasa con este APU cuando hay inflación o se mueve la tasa del BCV?**
    La versión guardada queda congelada con su sello y sus fechas para no perder trazabilidad. Frente a la inflación, Sílice ofrece tres herramientas: **Actualizar precios** con una lista nueva, **Reajuste** por fórmula polinómica con índices del BCV, y **Riesgo**, que simula `2.000` trayectorias con series mensuales de asfalto, gasoil y tasa para estimar la reserva `P80`.

12. **¿Qué pasa en el reajuste si el contrato está en dólares pero le ponen el INPC en bolívares?**
    Sílice emite una advertencia explícita (`AVISO_USD_BS` en `core/budget/reajuste.py`), porque un índice en bolívares aplicado a precios en dólares cobraría dos veces la devaluación. Para esos casos Sílice permite expresar primero el índice en USD dividiéndolo entre la tasa mensual del BCV.

13. **¿De dónde sale el precio de `80,00 USD/t` de la mezcla si la contratista tiene planta propia?**
    Del módulo de **Producción**: registra los gastos del mes en cantera y planta, calcula el costo real por tonelada según la receta vigente y lo publica como insumo propio (`MZP-…`). Además, la regla `CV3` avisa si el APU quedó usando el precio de un cálculo viejo.

14. **¿Qué hace la Inteligencia Artificial en este cálculo y qué tiene prohibido hacer?**
    La IA y el ML **jamás calculan un precio unitario, ni una cantidad, ni un impuesto**: toda cuenta la hace código determinista. El ML local solo busca partidas parecidas y señala precios o rendimientos atípicos (*Isolation Forest*), y el asistente de IA solo puede proponer entradas en borrador que pasan cuatro validaciones antes de que una persona confirme.

15. **Si eres ingeniero de sistemas y no presupuestista, ¿qué demuestra este cálculo en tu TEG?**
    Demuestra la arquitectura de puertos y adaptadores: el motor `core/costing/motor.py` es una función pura de 45 líneas que no sabe qué es asfalto ni qué es una vía. Toda la geometría y las reglas viales (`VR1`–`VR8`) entraron en `adapters/vial/` sin modificar una sola línea de `core/`.

---

## 4. Tres errores típicos que la auditoría de Sílice detecta en este APU

1. **Cantidad de carpeta inflada frente a la geometría de la vía — Regla `VR1` ([adapters/vial/reglas.py](../../adapters/vial/reglas.py#L599-L609), `auditar_vial`) y `R1` ([core/verification/reglas.py](../../core/verification/reglas.py#L150-L242), `TrazabilidadGeometrica`)**
   - **Qué número cambia:** En vez de las **`500,00 t`** que dan los parámetros del tramo `T1` (`1.000 × 5,00 × 0,05 × 2,00`), alguien escribe a mano **`550,00 t`** en el presupuesto. El subtotal sin IVA sube de `63.250,00 USD` a **`69.575,00 USD`** (`+6.325,00 USD`).
   - **Por qué lo detecta:** `VR1` vuelve a multiplicar área × espesor × densidad del tramo enlazado (`tramo:T1:capa:1`) y, como el desvío de `10 %` supera la tolerancia de `0,5 %`, marca **ERROR**. *Si el jurado pregunta por qué 0,5 %: es un **supuesto declarado** (`TOLERANCIA_CARPETA`, V-3 en `adapters/vial/constantes.py`), uno de los umbrales viales que se calibran con los economistas en el diagnóstico o se declaran como límite.* con el valor observado (`550`) y el esperado (`500`).

2. **Sumar administración y utilidad (`25 %`) en vez de encadenarlas, o meter IVA en el APU — Reglas `CV1` ([aplicacion/conciliacion.py](../../aplicacion/conciliacion.py#L125-L153), `_cv1`) y `AH1` / `AH4` ([fusion/apu_por_hoja.py](../../fusion/apu_por_hoja.py#L300-L352), `_evaluar`)**
   - **Qué número cambia:** En un Excel externo suman `15 % + 10 % = 25 %` sobre el costo directo de `100,00 USD/t` e imprimen un precio unitario de **`125,00 USD/t`** en lugar de **`126,50 USD/t`**, perdiendo **`750,00 USD`** en las `500,00 t`. (O el caso opuesto: meten `16 %` de IVA dentro del APU dando **`146,74 USD/t`** y luego cobran otro `16 %` al final, inflando el total con IVA de `73.370,00 USD` a **`85.109,20 USD`**).
   - **Por qué lo detecta:** Sílice nunca confía en el precio unitario escrito: `CV1` y `AH1` recalculan el APU desde sus insumos con `calcular_apu` y marcan **ERROR** porque la diferencia (`1,50 USD/t`) supera la tolerancia de `0,01 USD`; y `AH4` marca **ADVERTENCIA** en cuanto ve un porcentaje de impuesto distinto de cero dentro de la hoja del APU.

3. **Factor de depreciación inconsistente del mismo equipo entre partidas — Regla `R6` ([core/verification/reglas.py](../../core/verification/reglas.py#L616-L655), `CriterioDepreciacion`)**
   - **Qué número cambia:** El «Rodillo compactador vibratorio» (`30.000,00 USD`) usa depreciación `0,01` en la base granular, pero en nuestra carpeta alguien corre la coma y escribe **`0,10`**. El costo diario del rodillo salta de `300,00` a **`3.000,00 USD/día`**, el rubro equipos pasa de `10,00` a **`37,00 USD/t`**, el costo directo sube a **`127,00 USD/t`** y el precio unitario sube de `126,50` a **`160,66 USD/t`** (`127,00 × 1,15 × 1,10 = 160,655`), encareciendo el renglón en **`17.077,50 USD`** sin IVA.
   - **Por qué lo detecta:** `R6` recorre todos los APU del presupuesto, normaliza el nombre de cada equipo y exige un único factor de depreciación por máquina; al hallar `0,01` en una partida y `0,10` en otra, emite **ERROR** citando ambos códigos de partida.
