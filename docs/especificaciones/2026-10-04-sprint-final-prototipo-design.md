# Sprint final del prototipo (SF): hoja del proyecto con metrajes, edición trazable y barra superior

| Campo | Valor |
|---|---|
| Estado | **propuesta**, pendiente de la aprobación de Eugenio; los cambios en `core/` además necesitan el visto bueno del tutor (§12) |
| Fecha | 2026‑10‑04 |
| Rama | `inc/spec-sf`, desde `main` = `1a02530` (fusión del PR #19, caso TI‑001) |
| Sprint | SF, «sprint final del prototipo»; fases SF0 a SF5 (§13) |
| Documentos que enmienda | [ERS](../ERS.md) (UC, RF y RNF nuevos), [arquitectura](../arquitectura.md), [modelo de datos](../modelo_datos.md), [plan de pruebas](../plan_pruebas.md), [guion de prueba](../guion_prueba_arenia.md), [PLAN_CIERRE.md](../../PLAN_CIERRE.md) |
| Naturaleza de los datos | igual que [NORMAS.md §1](../../NORMAS.md): los casos son construidos para el proyecto; los precios, referencias publicadas MaPreX de julio de 2026 |

Este documento es la **fuente única** del diseño del sprint. El plan de sesiones (`PLAN_SF.md`) se
escribe después de aprobarlo y no repite este texto: lo enlaza.

---

## 1. Qué se quiere y por qué

### 1.1 Lo que pidió Eugenio (2026‑10‑03 y 2026‑10‑04)

1. Cerrar el prototipo funcional con un sprint final.
2. Que presupuestos, APU, curvas y punto de equilibrio sean **editables dentro del sistema**, como
   una hoja de cálculo: el usuario cambia una línea y el sistema recalcula, se audita y deja
   **trazabilidad de origen** del cambio. Esa misma hoja se exporta a Excel.
3. Que un presupuesto nuevo parta de **metrajes como dato de entrada**. En el caso TI‑001 las
   cantidades (metros de cable, de tubo, número de equipos HP) se dieron por hechas. El dato de
   entrada es el **espacio**: cuántos metros hacen falta para pasar los tubos por pared, techo o
   piso hasta cada punto, por ejemplo una toma de agua en una casa u oficina.
4. Cubrir tres especialidades con reglas propias: **agua, datos y electricidad**.
5. Poder **importar un plano** (DXF de AutoCAD e IFC de Revit) como dato de entrada, con la
   **hoja de metrajes** dentro del sistema como punto fuerte.
6. Saber **de dónde salen los precios**.
7. Una interfaz cómoda con una **barra superior** y las herramientas pertinentes.
8. Este spec, con las metodologías pertinentes, para aprobarlo.

### 1.2 Lo que se encontró en el repositorio (2026‑10‑04)

- **Los metrajes de TI‑001 son supuestos.** `data/samples/telecom/topologia_ti001.csv` declara
  longitudes por puesto (18 m, 19,5 m…) y 10 % de reserva sin plano ni levantamiento detrás
  ([bitácora del caso](../bitacora/2026-09-30-caso-ti001.md)). R1 comprueba que la cantidad
  coincide con su regla, no que la **medida de entrada** tenga origen: es el hueco que este sprint
  cierra.
- **El punto de equilibrio solo existe en un script del caso**
  (`scripts/analisis_ti001.py:305`), no en el sistema ni en la interfaz.
- **Hoy se edita poco:** la composición de un APU (UC‑10, UC‑11) y el plan de trabajo en Elaborar
  (`ui/paginas/elaborar.py`, `st.data_editor`). Las cantidades, la curva y el punto de equilibrio
  no se editan, y una edición no deja registro de cambio salvo la actualización de precios (UC‑02,
  `CambioPrecio`).
- **La interfaz** es Streamlit 1.62 con navegación lateral (`ui/app.py`, `st.navigation`) y diez
  pantallas. Esa versión admite la navegación en la parte superior (`position="top"`).
- **`elaborar` siempre audita con las siete reglas** (`core/budget/presupuesto.py:155`,
  `auditar(presupuesto)`): no admite reglas adicionales, aunque `auditar` sí las admite
  (`core/verification/informe.py:178`).
- **`Dominio` tiene cuatro valores** (`core/contracts/dominio.py`): civil, telecom, industrial y
  sistemas. No hay uno para electricidad.
- **Hallazgos sin corregir de la auditoría de TI‑001:** A‑1 (la interfaz guarda subidas sin limpiar
  el nombre), A‑2 (R4 compara por subcadena: no distingue «4 pulg» de «3/4 pulg»), M‑1 (inyección
  de fórmulas en el Excel), M‑2 (el TOTAL redondeado del Excel no cuadra con la suma de filas
  redondeadas) y M‑3 (el adaptador telecom emite 40 INFO de R4 por `origen` y `destino`).

### 1.3 De dónde salen los precios (respuesta al punto 6)

Ningún precio del sistema se busca en internet. Todos salen de los listados **MaPreX de julio de
2026** que aportó Eugenio (`data/precios/maprex_2026-07/`: materiales, equipos y mano de obra del
software MaPreX v26, base del 08/07/2026), en bolívares, convertidos con **633,3644 Bs/USD**, la
tasa que declara el propio listado al 01/07/2026. Las laptops y el servidor de TI‑001 se valoraron
con referencias de categoría (OFI058, OFI131), no con una cotización de HP (ruling T‑3 del caso).
Los listados son referencia, no lista vigente ([README de precios](../../data/precios/maprex_2026-07/README.md)).
Este sprint hace visible ese origen en la interfaz y permite registrar una cotización con su fuente
(RF‑56).

### 1.4 Criterio de éxito del sprint

Un usuario que no es el autor levanta el espacio de una oficina (o lo importa de un plano), obtiene
el presupuesto de agua, datos y electricidad con su auditoría, cambia una línea, ve el recálculo y
el registro de ese cambio, y exporta el Excel, sin ayuda y sin tocar un archivo fuera del sistema.
Se mide con los casos de prueba CP‑08 a CP‑11 (§11).

---

## 2. Relación con el plan de cierre

[PLAN_CIERRE.md](../../PLAN_CIERRE.md) congeló el alcance funcional hasta cumplir F1–F5. Este spec
es una **enmienda** a ese límite:

- El sprint SF se inserta **después de GC6 y antes de Med**. Med mide la interfaz con personas
  (CP‑07, indicador 3, juicio de expertos de RNF‑04); medir antes de cambiar la interfaz invalidaría
  la medición.
- Los protocolos de Med ([indicador 3](../protocolo_indicador3.md), [RNF‑04](../protocolo_rnf04.md))
  no se cambian en su método; en SF4 se actualizan sus pasos para la interfaz nueva, antes de la
  primera sesión medida.
- F1–F5 no cambian. La etiqueta `v1.0-tesis` (F3) se pone después de Med, como estaba.
- La redacción de la tesis sigue en pausa; la Red incluirá este sprint en los capítulos IV y V.

---

## 3. Alcance

**Incluye:** hoja de metrajes con modelo espacial (§6); reglas de cantidades de agua, datos y
electricidad (§7); auditoría espacial y corrección de A‑1, A‑2, M‑1, M‑2 y M‑3 (§8); edición con
versiones y registro de cambios (§9); punto de equilibrio en el sistema (§9.4); Excel con fórmulas
vivas y hoja de trazabilidad (§9.5); origen visible de cada precio (§9.6); barra superior (§10);
importación de DXF e IFC hacia la hoja (§6.5); caso de demostración OF‑001 (§11.1).

**No incluye:**

- Dibujar planos o editar geometría en un lienzo. La hoja es tabular.
- Planos en PDF o escaneados (reconocer símbolos es un problema de investigación aparte; el
  capítulo I ya lo excluye en 1.5.2).
- Volver a importar un Excel editado fuera del sistema: lo que se edita fuera no pasa por la
  auditoría (decisión DA‑SF‑4).
- Usuarios con contraseña. El «responsable» de un cambio es un nombre que el usuario declara.
- Nuevas rutas de la API para la hoja (la API conserva sus rutas actuales; YAGNI).
- Una interfaz web nueva (React): queda como trabajo futuro.
- Cálculo estructural, de caudales o de caídas de tensión: las reglas cuentan materiales, no
  dimensionan la instalación.

---

## 4. Requisitos (enmienda a la ERS, IEEE 830)

La numeración continúa la de la ERS vigente (último UC‑12, RF‑44, RNF‑10; UC‑09 sigue reservado).

### 4.1 Casos de uso nuevos

| UC | Nombre | Actor | Resumen |
|---|---|---|---|
| UC‑13 | Levantar el espacio y los metrajes de un proyecto | proyectista | Carga ambientes, fuentes, puntos y recorridos con el origen de cada medida; el sistema propone recorridos y deriva las cantidades por especialidad |
| UC‑14 | Importar un plano a la hoja de metrajes | proyectista | Sube un DXF o un IFC; el sistema crea filas en la hoja con su origen y un informe de lo que no reconoció |
| UC‑15 | Editar la hoja del proyecto | proyectista | Cambia una celda de entrada; ve el recálculo y la auditoría al momento; guarda una versión con el registro de cambios |
| UC‑16 | Analizar el punto de equilibrio del contrato | proyectista, gerente | Consulta el punto de equilibrio y su ubicación en la curva, y cómo se mueve al editar |

UC‑01 se extiende: «fuente de cantidades» incluye la hoja de metrajes (flujo alterno nuevo).

### 4.2 Requisitos funcionales nuevos

| RF | Requisito | UC |
|---|---|---|
| RF‑45 | La hoja de metrajes registra ambientes, fuentes, puntos y recorridos; toda medida lleva su origen (§6.3) | UC‑13 |
| RF‑46 | El sistema propone para cada punto un recorrido ortogonal desde su fuente, por superficie (pared, techo, piso), y el usuario puede reemplazarlo | UC‑13 |
| RF‑47 | Reglas de cantidades de **agua** (agua fría y drenaje) declaradas con su fuente (§7.1) | UC‑13 |
| RF‑48 | Reglas de cantidades de **datos** (§7.2) | UC‑13 |
| RF‑49 | Reglas de cantidades de **electricidad** (tomacorrientes e iluminación) (§7.3) | UC‑13 |
| RF‑50 | Importación de DXF con la convención de capas de §6.5.1 e informe de lo no reconocido | UC‑14 |
| RF‑51 | Importación de espacios y terminales desde IFC (§6.5.2) | UC‑14 |
| RF‑52 | Edición de las celdas de entrada de la hoja del proyecto con recálculo y auditoría inmediatos | UC‑15 |
| RF‑53 | Cada versión guardada registra sus cambios: qué, valor anterior, valor nuevo, cuándo, responsable y fuente | UC‑15 |
| RF‑54 | Punto de equilibrio calculado por el sistema y ubicado en la curva de inversión | UC‑16 |
| RF‑55 | Exportación a Excel con las hojas de la hoja del proyecto, fórmulas vivas y hoja de trazabilidad | UC‑15 |
| RF‑56 | Cada precio muestra su origen (lista, referencia, fecha, tasa); se puede registrar una cotización con su fuente | UC‑15 |
| RF‑57 | Barra superior con la navegación y las herramientas del proyecto (§10) | todos |
| RF‑58 | Reglas de auditoría espacial R8, R9 y R10 (§8.2) | UC‑13, UC‑15 |

### 4.3 Requisitos no funcionales nuevos (ISO/IEC 25010)

| RNF | Característica | Requisito | Medición |
|---|---|---|---|
| RNF‑11 | Eficiencia de desempeño | Recálculo y auditoría tras una edición en ≤ 2 s para un proyecto de hasta 500 filas de metrajes | prueba automatizada con el caso OF‑001 ampliado, en la CI de Windows |
| RNF‑12 | Seguridad | Ningún texto exportado a Excel se interpreta como fórmula; ningún archivo subido se guarda con un nombre que salga de su carpeta | pruebas de M‑1 y A‑1 |
| RNF‑13 | Usabilidad | Una persona nueva completa CP‑08 a CP‑11 sin ayuda | guion de prueba, en Med |

---

## 5. Arquitectura (vistas 4+1)

### 5.1 Principio que se conserva

[NORMAS.md §2](../../NORMAS.md): núcleo cerrado, adaptadores abiertos. Lo **propio de una
especialidad o de un formato de plano** va en `adapters/`. Lo **genérico de cualquier presupuesto**
(versionar una edición, registrar el cambio, punto de equilibrio, Excel) va en `core/` con
expediente, como en C5 y C6. La meta M9 sigue midiendo que agregar especialidades no toque `core/`.

### 5.2 Vista lógica: paquetes nuevos y cambiados

| Paquete | Qué contiene | Importa | Toca `core/` |
|---|---|---|---|
| `adapters/espacio/` (nuevo) | modelo espacial (ambiente, fuente, punto, recorrido, tramo, origen de medida), geometría de recorridos, persistencia propia de la hoja, emisión de `ItemComputo` y reglas R8–R10 | solo `core.contracts` | no |
| `adapters/espacio/especialidades/` (nuevo) | `agua.py`, `datos.py`, `electricidad.py`: reglas de cantidades y partidas derivadas, cada una con su fuente | solo `core.contracts` | no |
| `adapters/espacio/planos/` (nuevo) | `dxf.py` (ezdxf), `ifc.py` (ifcopenshell, reutiliza el extra `civil`) | solo `core.contracts` | no |
| `core/budget/presupuesto.py` | `elaborar(..., reglas=REGLAS)`: admite reglas adicionales | — | **sí** (expediente SF‑E1) |
| `core/budget/edicion.py` (nuevo) | versión nueva de un presupuesto a partir de una edición y su registro de cambios; reutiliza `descartar_version` | — | **sí** (SF‑E2) |
| `core/models/entidades.py` | entidad `RegistroCambio` | — | **sí** (SF‑E2) |
| `core/budget/equilibrio.py` (nuevo) | punto de equilibrio, función pura (§9.4) | — | **sí** (SF‑E3) |
| `core/budget/excel.py` | hojas nuevas, fórmulas vivas, escape de fórmulas (M‑1), cuadre del redondeo (M‑2) | — | **sí** (SF‑E4) |
| `core/verification/reglas.py` | R4 compara por especificación normalizada, no por subcadena (A‑2) | — | **sí** (SF‑E5) |
| `adapters/telecom/` | `origen` y `destino` dejan de ser especificaciones (M‑3) | `core.contracts` | no |
| `ui/hoja.py` (nuevo, sin Streamlit) | orquesta «editar → derivar → elaborar → auditar → previsualizar → guardar versión», como `ui/elaboracion.py` | `adapters.espacio`, `core` | no |
| `ui/app.py`, `ui/barra.py` (nuevo), `ui/paginas/hoja.py` (nueva) | barra superior, herramientas y la pantalla de la hoja | `ui.*` | no |
| `ui/paginas/*` con subidas | usan una sola función de guardado seguro (A‑1) | — | no |

### 5.3 Vista de procesos: una edición

```
usuario edita una celda de entrada
  -> ui.hoja aplica el cambio en memoria (borrador de la versión)
  -> adapters.espacio deriva los ItemComputo (si cambió el espacio)
  -> core.budget.elaborar(items, composiciones, parametros, plan, reglas = REGLAS + REGLAS_ESPACIO)
  -> core.budget.equilibrio.punto_equilibrio(presupuesto)
  -> la hoja se repinta con totales, curva, punto de equilibrio y estado de auditoría por fila
usuario pulsa «Guardar versión» (fuente y responsable obligatorios por cambio de medida o precio)
  -> core.budget.edicion guarda la versión nueva con su informe y un RegistroCambio por celda
```

El borrador no se persiste: cerrar sin guardar no deja rastro ni versión. Deshacer es volver a la
versión anterior con el mismo mecanismo que UC‑02 (`descartar_version`).

### 5.4 Vista de desarrollo y física

- Dependencia nueva: `ezdxf` (licencia MIT) en un extra `planos`. `ifcopenshell` ya está en el extra
  `civil`.
- Persistencia: el mismo archivo SQLite del caso abierto. Las tablas de la hoja de metrajes llevan el
  prefijo `esp_` y su propio `MetaData` dentro de `adapters/espacio/` (decisión DA‑SF‑2). Las tablas
  de `core/models` no cambian salvo `RegistroCambio`.
- Despliegue: sin cambios (Streamlit local y la API FastAPI).
- `tests/unit/test_arquitectura.py` se extiende: `adapters.espacio` solo importa `core.contracts`;
  `ui.hoja` no importa Streamlit.

### 5.5 Decisiones de diseño

| # | Decisión | Alternativa descartada | Costo si es errónea |
|---|---|---|---|
| DA‑SF‑1 | Interfaz en Streamlit con `st.data_editor`; si la prueba de SF0 falla, la hoja pasa a AG Grid (`streamlit-aggrid`) dentro de la misma fase | React sobre la API | rehacer la pantalla de la hoja (no el resto) |
| DA‑SF‑2 | La hoja de metrajes se persiste en tablas propias del adaptador (`esp_*`) | entidades nuevas en `core/models` | mover tablas a `core/` con expediente |
| DA‑SF‑3 | Agua y electricidad se emiten con `Dominio.CIVIL` («instalaciones de la edificación») y datos con `Dominio.TELECOM`; la especialidad viaja en `especificaciones["especialidad"]` | agregar `Dominio.ELECTRICO` | un valor nuevo en `core/contracts` con expediente y aval del tutor |
| DA‑SF‑4 | La edición oficial es la del sistema; el Excel exportado no se reimporta | importar el Excel editado | cambios hechos en Excel sin auditar |
| DA‑SF‑5 | Una cantidad derivada se puede sobrescribir a mano, con fuente obligatoria; R8 la marca como ADVERTENCIA | prohibir la sobrescritura | el usuario saca el cálculo del sistema |
| DA‑SF‑6 | El plano importado nunca salta la hoja: crea filas revisables con su origen | importar directo al presupuesto | errores del plano sin revisión |

---

## 6. La hoja de metrajes

### 6.1 Sistema de coordenadas

Un proyecto tiene un sistema de coordenadas en metros con el eje z hacia arriba desde el piso
terminado. Cada ambiente se describe como un rectángulo (origen `x0, y0`, `largo` en x, `ancho` en
y, `alto`). Los ambientes no rectangulares se descomponen en rectángulos; el DXF los aproxima por su
caja envolvente y lo declara en el informe de importación.

### 6.2 Tablas

| Tabla | Columnas | Notas |
|---|---|---|
| Ambientes | id, nombre, x0, y0, largo, ancho, alto, origen de medida | |
| Fuentes | id, especialidad, tipo (acometida o montante de agua, colector de drenaje, rack, tablero), ambiente, x, y, z, origen de medida | |
| Puntos | id, especialidad, tipo (toma de agua fría, drenaje, punto de datos, tomacorriente, salida de iluminación), ambiente, pared o techo, x, y, z, fuente, circuito (electricidad), especificaciones (diámetro, calibre, categoría), origen de medida | un punto pertenece a una fuente |
| Recorridos | id, punto, fuente, propuesto o declarado | uno por punto |
| Tramos | recorrido, orden, superficie (pared, techo, plafón, piso, bandeja), empotrado o expuesto, vértice inicial, vértice final, longitud (calculada), origen de medida | |
| Orígenes de medida | id, tipo (plano y lámina, DXF, IFC, levantamiento en sitio, supuesto), referencia, fecha, responsable | el tipo «supuesto» existe para declararlo, no para esconderlo |

### 6.3 Origen de la medida

Toda fila de las cinco primeras tablas cita un origen de medida. Los tipos y lo que exige cada uno:

| Tipo | Referencia obligatoria |
|---|---|
| Plano | número de plano y lámina, revisión |
| DXF | archivo, capa y *handle* de la entidad |
| IFC | archivo y `GlobalId` |
| Levantamiento en sitio | fecha y responsable |
| Supuesto | motivo; R8 lo marca como ADVERTENCIA |

### 6.4 Recorrido propuesto

Para cada punto sin recorrido declarado, el sistema propone uno ortogonal: sube desde la fuente hasta
el techo (o baja al piso si la especialidad es drenaje), recorre en x y luego en y por el techo, y
baja por la pared hasta la altura del punto. Cada tramo queda con su superficie y su longitud. El
usuario puede reemplazar el recorrido declarando sus vértices. La longitud de un tramo es la
distancia entre sus vértices; no se escribe a mano.

### 6.5 Importación de planos

El plano crea filas en la hoja con origen DXF o IFC y un **informe de importación**. Lo que no sigue
la convención se lista en el informe y no se adivina.

#### 6.5.1 DXF (convención de capas)

| Capa | Entidad | Se convierte en |
|---|---|---|
| `AMBIENTES` | polilínea cerrada con un texto adentro (nombre) | ambiente (caja envolvente si no es rectángulo) |
| `FTE-AGUA`, `FTE-DRENAJE`, `FTE-DATOS`, `FTE-ELEC` | bloque insertado | fuente |
| `PTO-AGUA`, `PTO-DRENAJE`, `PTO-DATOS`, `PTO-TOMA`, `PTO-LUZ` | bloque insertado, atributos `ALTURA` y opcionales `DIAMETRO`, `CALIBRE`, `CIRCUITO` | punto |
| `REC-<especialidad>` | polilínea abierta | recorrido declarado (opcional) |

Las unidades salen de la variable `$INSUNITS` del archivo; si falta, la importación se detiene y
pide la unidad. La altura de los ambientes no está en un plano 2D: queda pendiente en la hoja y R8
la marca hasta que se cargue.

#### 6.5.2 IFC

Se leen `IfcSpace` (ambientes), los terminales sanitarios, de datos, de tomacorriente y de
iluminación, y los tableros. Las clases exactas por esquema (IFC2x3 e IFC4) se fijan en SF0 con
archivos de prueba y se documentan en el manual técnico. Origen: archivo y `GlobalId`.

---

## 7. Reglas de cantidades por especialidad

Cada regla produce `ItemComputo` con `origen_tipo = REGLA`, la expresión en `regla` y sus valores en
`parametros` (lo verifica R1). Cada constante (desperdicio, holgura, límite) se declara en una tabla
de parámetros de la especialidad con su **fuente**. Las fuentes candidatas de abajo se verifican en
SF0 y se registran en [referencias.md](../tesis/referencias.md) con el mismo procedimiento de las
referencias de la tesis; una constante sin fuente verificada se declara como **supuesto** y queda
visible en la hoja.

**Cómo se mide cada material** (vale para las tres especialidades). Los recorridos de una misma
fuente forman un árbol: donde dos recorridos pasan por el mismo segmento, comparten tubería o
canalización. Por eso la geometría une los segmentos coincidentes antes de medir:

- **tubería y canalización** se miden sobre la unión de segmentos (cada metro cuenta una vez);
- **cable de datos** se mide por recorrido, porque cada punto lleva su propio cable hasta el rack;
- **conductor eléctrico** se mide por circuito, sobre la cadena tablero → punto 1 → punto 2 … en el
  orden que declare el usuario (el sistema propone el del vecino más cercano);
- el **diámetro de un segmento compartido** es el mayor de los puntos que sirve, salvo que el
  usuario lo declare. No se dimensiona la instalación (§3): esta regla solo asigna un material.

### 7.1 Agua (agua fría y drenaje)

| Partida derivada | Regla |
|---|---|
| Tubería por material y diámetro (m) | longitud de la unión de segmentos, por diámetro × (1 + desperdicio) |
| Codos | número de cambios de dirección en el árbol |
| Tees | número de derivaciones del árbol (nodos donde se separan dos recorridos) |
| Llave de paso | una por punto de agua fría que la declare |
| Picado y resane de pared o piso (m) | suma de tramos empotrados |
| Salida de agua o de drenaje (punto) | una por punto |

Comprobación propia (R10): pendiente mínima del drenaje. Fuente candidata: Normas Sanitarias para
proyecto, construcción, reparación y reforma de edificaciones (Gaceta Oficial N.º 4.044
Extraordinario, 1988), a verificar.

### 7.2 Datos

| Partida derivada | Regla |
|---|---|
| Cable UTP por categoría (m) | (longitud del recorrido + holgura en el rack + holgura en el punto) × (1 + reserva) |
| Canalización por tipo y diámetro (m) | longitud de la unión de segmentos |
| Cajas, *face plates* y *jacks* | uno por punto |
| Certificación (punto) | una por punto |

Comprobación propia (R10): longitud del enlace permanente ≤ 90 m. Fuente candidata: ANSI/TIA‑568, a
verificar.

### 7.3 Electricidad (tomacorrientes e iluminación)

| Partida derivada | Regla |
|---|---|
| Conductor por calibre (m) | longitud de la cadena del circuito × número de conductores (fase, neutro, tierra) × (1 + desperdicio) |
| Tubería por tipo y diámetro (m) | longitud de la unión de segmentos |
| Cajas (pieza) | una por punto y una por cambio de dirección que la declare |
| Salida de tomacorriente o de iluminación (punto) | una por punto |
| Protección por circuito (pieza) | una por circuito del tablero |

Comprobación propia (R10): puntos por circuito ≤ máximo declarado. Fuente candidata: Código Eléctrico
Nacional (FONDONORMA 200), a verificar.

---

## 8. Auditoría

### 8.1 Lo que no cambia

Las siete reglas R1–R7 siguen igual en su enunciado. `elaborar` las corre siempre (principio 7).

### 8.2 Reglas nuevas (en `adapters/espacio`, implementan `ReglaVerificacion`)

| Regla | Comprueba | Severidad |
|---|---|---|
| R8 Origen de la medida | toda cantidad derivada del espacio cita su origen de medida; supuestos y sobrescrituras a mano se marcan | ERROR sin origen; ADVERTENCIA si es supuesto o sobrescritura |
| R9 Coherencia espacial | cada punto y fuente cae dentro de su ambiente; ninguna altura supera la del ambiente; ningún recorrido es más corto que la distancia ortogonal mínima entre su fuente y su punto | ERROR |
| R10 Límites de la especialidad | pendiente del drenaje, 90 m por enlace de datos, puntos por circuito | ERROR o ADVERTENCIA según la fuente del límite |

R8–R10 trabajan sobre el `Presupuesto` igual que R1–R7: lo que necesitan viaja en `parametros` y
`especificaciones` de cada `ItemComputo`. Por eso no tocan `core/`.

### 8.3 Correcciones de hallazgos pendientes

| Hallazgo | Corrección | Fase |
|---|---|---|
| A‑2 | R4 normaliza cada especificación a un valor comparable por clave (diámetros como fracciones, «2» frente a «1/2», «6» frente a «16») y excluye del corpus la descripción del propio ítem; las pruebas incluyen los casos de la bitácora de TI‑001 | SF1 |
| M‑3 | el adaptador telecom deja `origen` y `destino` en `parametros`, no en `especificaciones` | SF2 |
| M‑1 | toda celda de texto que empiece por `=`, `+`, `-` o `@` se exporta como texto | SF3 |
| M‑2 | los totales del Excel se calculan con `ROUND` (REDONDEAR en Excel en español) por fila y la suma de lo redondeado, y la pantalla presenta el mismo criterio | SF3 |
| A‑1 | las tres pantallas con subida usan una sola función de guardado seguro, como `api/archivos.py:16` | SF4 |

Los cinco se registran como hallazgos nuevos del [inventario](../auditoria/2026-09-inventario.md)
al abrir SF0.

---

## 9. La hoja del proyecto: edición, trazabilidad y exportación

### 9.1 Pestañas

Una sola pantalla, «Hoja del proyecto», con pestañas: **Espacio y metrajes**, **APU**,
**Presupuesto**, **Plan y curva**, **Punto de equilibrio**, **Precios**, **Auditoría** y
**Trazabilidad**.

### 9.2 Qué se edita y qué no

| Pestaña | Celdas editables | Celdas calculadas (bloqueadas) |
|---|---|---|
| Espacio y metrajes | ambientes, fuentes, puntos, vértices de recorridos declarados, orígenes de medida | longitudes de tramos, cantidades derivadas |
| APU | cantidad y rendimiento de cada línea, insumo elegido | precios unitarios y totales |
| Presupuesto | sobrescritura de una cantidad (DA‑SF‑5) | precio unitario, total por partida y total general |
| Plan y curva | reparto de cada partida por período | montos, acumulados y porcentajes |
| Punto de equilibrio | nada propio; se mueve con las demás | todo |
| Precios | cotización nueva con su fuente (§9.6) | precio vigente de cada insumo |
| Parámetros del proyecto | FCAS, administración, utilidad, imprevistos, con fuente | — |

Cada fila lleva una columna **Estado** con el peor hallazgo de la auditoría que la toca y un enlace a
su detalle en la pestaña Auditoría.

### 9.3 Registro de cambios

`RegistroCambio`: proyecto, versión de origen, versión resultante, objeto (metraje, APU, precio,
plan, parámetro), clave de la fila, campo, valor anterior, valor nuevo, **fuente**, responsable,
fecha y hora. Guardar exige fuente y responsable en todo cambio de medida o de precio. La pestaña
Trazabilidad lista los cambios por versión y permite volver a cualquier versión anterior.

### 9.4 Punto de equilibrio

Se lleva al sistema la definición del caso TI‑001 (`scripts/analisis_ti001.py:305`):

- costo variable CV = costo directo de todas las partidas;
- costo fijo CF = administración (gastos generales) sobre el costo directo;
- V = total del contrato; margen de contribución m = (V − CV) / V; PE = CF / m;
- se ubica en la curva: el primer período cuyo acumulado alcanza el PE y la fracción de ese período.

La definición es un ruling (RS‑4 en §14): el tutor puede pedir otra clasificación de costos fijos.
`core/budget/equilibrio.py` la implementa como función pura con `Decimal`, y el script del caso pasa
a importarla (DRY).

### 9.5 Excel exportado

Una hoja por pestaña, con la misma disposición de columnas que en el sistema. Los totales de APU,
presupuesto, curva y punto de equilibrio se escriben como **fórmulas** que referencian las celdas de
cantidad y precio, de modo que el archivo se recalcula si alguien mueve un número. La hoja
Trazabilidad lleva el registro de cambios de la versión exportada y la hoja Auditoría, el informe.
Una prueba compara cada total calculado por el sistema con el valor que da la fórmula del Excel
(evaluada con la biblioteca de lectura) para el caso OF‑001.

### 9.6 Precios con su origen

La pestaña Precios muestra, por insumo: lista de precios, referencia (por ejemplo, el Ref de
MaPreX), fecha del precio, moneda original y tasa de conversión con su fecha. Una **cotización** se
registra como una lista de precios nueva con fuente (proveedor, número y fecha de la cotización)
por el mismo camino de UC‑02 y con la evidencia que pide el
[protocolo de levantamiento de precios](../protocolo_precios.md); nunca reemplaza el precio en
silencio. Un insumo sin fuente ni fecha se
marca en la columna Estado.

---

## 10. Interfaz: barra superior

- **Navegación arriba** (`st.navigation(position="top")`) con dos grupos, Trabajo e Investigación;
  el modo entrega (RF‑43) sigue ocultando Investigación.
- **Barra de herramientas** fija debajo de la navegación, pintada por el marco común de `ui/app.py`:

| Herramienta | Qué hace |
|---|---|
| Proyecto | nuevo, abrir, caso abierto y su versión |
| Importar plano | sube un DXF o un IFC hacia la hoja (UC‑14) |
| Precios | abre la pestaña Precios y registra una cotización |
| Auditar | muestra el resumen del informe vigente (se audita siempre; el botón solo lo enseña) |
| Guardar versión | persiste el borrador con su registro de cambios |
| Exportar Excel | descarga el Excel de la versión vigente |
| Recorrido guiado | abre o retoma los recorridos de UC‑12 |

- La barra lateral queda para el caso abierto y el paso del recorrido guiado.
- La revisión de SF4 añade un encargo de usabilidad (§12.2) que evalúa la barra con las heurísticas
  de Nielsen.

---

## 11. Pruebas y calidad (IEEE 829, ISO/IEC 25010)

### 11.1 Caso de demostración OF‑001

Una oficina construida para el proyecto, sobre la planta de TI‑001: cuarto técnico con rack y
tablero, zonas A y B de puestos, recepción, un baño y una cocineta. Lleva las tres especialidades en
el mismo espacio. Se entrega como hoja cargada a mano **y** como DXF que sigue la convención de
§6.5.1, para comprobar que las dos entradas dan las mismas cantidades. Precios MaPreX de julio de
2026. TI‑001 se conserva sin cambios como evidencia histórica.

### 11.2 Pruebas automatizadas (antes que el código, NORMAS principio 5)

- Oráculos de geometría: longitudes de recorridos propuestos calculadas a mano para OF‑001.
- Oráculos de cantidades por especialidad, con la expresión de R1.
- R8–R10: un error sembrado por regla, detectado; ninguna falsa alarma en OF‑001 limpio.
- A‑2: los cuatro pares de la bitácora de TI‑001 más el caso inverso de la línea base.
- Importación: el DXF de OF‑001 produce las mismas filas que la hoja manual; un DXF fuera de
  convención produce informe y no filas.
- Edición: una edición produce versión nueva, informe y un `RegistroCambio` por celda; descartar
  vuelve a la versión anterior sin pérdida.
- Excel: total del sistema = total de la fórmula; ninguna celda de texto se interpreta como fórmula.
- RNF‑11: tiempo de recálculo con 500 filas.
- Arquitectura: importaciones permitidas de `adapters.espacio` y `ui.hoja`.

### 11.3 Casos de prueba con personas (guion)

| CP | Tarea |
|---|---|
| CP‑08 | Levantar a mano el baño de OF‑001 (un ambiente, una fuente, dos puntos de agua) y obtener su presupuesto auditado |
| CP‑09 | Importar el DXF de OF‑001 y corregir en la hoja la fila que el informe marca |
| CP‑10 | Cambiar la cantidad de una línea de un APU, ver el recálculo y guardar la versión con su fuente |
| CP‑11 | Ver el origen del precio de un insumo, registrar una cotización y exportar el Excel |

Se ejecutan en Med junto con CP‑07.

### 11.4 Calidad

La evaluación de [calidad_iso25010.md](../calidad_iso25010.md) se amplía con RNF‑11 a RNF‑13. La
cobertura de `core/` sigue ≥ 80 % (RNF‑06) y la suite corre con `-W error` y 0 omitidas en Linux y
Windows.

---

## 12. Metodología y gobierno

### 12.1 Marco

- **Scrum‑Cascada** ([metodologia.md](../metodologia.md)): las fases SF0–SF5 van en orden, cada una
  con su compuerta (cascada); dentro de cada fase, las tareas son ítems de un sprint con su
  *Definition of Done* (Scrum).
- **DRY:** cada hecho en un lugar; la definición del punto de equilibrio y la del Excel salen del
  script del caso y pasan a `core/`, y el script las importa.
- **Pruebas antes que código** en `core/` y en las reglas de especialidad (TDD).
- **IEEE 830** para la enmienda de la ERS (SF0); **vistas 4+1** para la de arquitectura (SF0);
  **IEEE 829** para el plan de pruebas y el guion; **ISO/IEC 25010** para la calidad.
- **Expediente por cambio en `core/`** (SF‑E1 a SF‑E5), con la regla que lo motiva, la prueba que
  lo demuestra y el impacto; visto bueno del tutor antes de fusionar la fase que lo contiene.
- **Bitácora** `docs/bitacora/2026-10-sf.md` con rulings, expedientes y cruce de compuertas.

### 12.2 Compuertas y revisión

Cada fase se cruza cuando (a) `scripts/meta_sf.py --hasta SF<n>` está en OK, (b) la CI está verde en
Linux y Windows y (c) aprueban los encargos de revisión, despachados como subagentes:

| Encargo | Revisa con |
|---|---|
| Ingeniero de requisitos | IEEE 830 y la ERS enmendada |
| Arquitecto de software | vistas 4+1, NORMAS §2, §5 y §6, expedientes de `core/` |
| Ingeniero de pruebas y calidad | IEEE 829 e ISO/IEC 25010 |
| Verificador de hechos | cada cita archivo:línea del texto de la fase |
| Especialista en usabilidad (solo SF4) | heurísticas de Nielsen e ISO 9241‑110 |

Etiqueta base `sf-base` en `main` al abrir SF0, y una etiqueta por compuerta (`gsf0`…`gsf5`). Un PR
por fase contra `main`, con fusión por *merge commit*.

### 12.3 Lo que decide el tutor

Los expedientes SF‑E1 a SF‑E5 (cambios en `core/`) y, si se pide, DA‑SF‑3 (un `Dominio` propio para
electricidad). Si el tutor rechaza un expediente, la fase se entrega sin esa pieza y se declara.

---

## 13. Fases

| Fase | Contenido | Entregable que funciona al cerrar | Compuerta |
|---|---|---|---|
| **SF0** | Enmienda de ERS, arquitectura y modelo de datos; verificación de las fuentes de §7; inventario A‑1…M‑3; **prueba corta de `st.data_editor`** con 500 filas, columna Estado y recálculo (criterio: RNF‑11 y ninguna edición perdida; si falla, AG Grid) | documentos aprobados y decisión DA‑SF‑1 confirmada | GSF0 |
| **SF1** | `adapters/espacio` (modelo, geometría, persistencia `esp_*`, orígenes), especialidad **agua**, R8 y R9, SF‑E1 (`elaborar` con reglas), SF‑E5 (R4, A‑2), pestaña Espacio y metrajes | el baño de OF‑001 se levanta a mano y sale su presupuesto auditado | GSF1 |
| **SF2** | Especialidades **datos** y **electricidad**, R10, M‑3, OF‑001 completo | la oficina entera con tres especialidades | GSF2 |
| **SF3** | SF‑E2 (edición, versiones, `RegistroCambio`), SF‑E3 (punto de equilibrio), SF‑E4 (Excel con fórmulas, M‑1, M‑2), pestañas APU, Presupuesto, Plan y curva, Punto de equilibrio, Precios, Auditoría y Trazabilidad | editar una línea, ver el recálculo, guardar con su registro y exportar | GSF3 |
| **SF4** | Barra superior y herramientas, A‑1, actualización del guion (CP‑08 a CP‑11) y de los pasos de los protocolos de Med, manuales | la aplicación completa con la barra nueva | GSF4 |
| **SF5** | Importación DXF (convención de capas) e IFC hacia la hoja, informe de importación, DXF de OF‑001 | el DXF de OF‑001 da las mismas cantidades que la hoja manual | GSF5 |

**Si el tiempo aprieta**, se cae primero SF5 (la hoja manual sigue siendo la entrada completa y la
importación pasa a trabajo futuro), y después el IFC dentro de SF5 antes que el DXF. SF1 a SF4 no se
recortan: sin ellos no hay prototipo que medir en Med.

---

## 14. Rulings para ratificar

| # | Decisión | Costo si es errónea |
|---|---|---|
| RS‑1 | Streamlit con `st.data_editor` (DA‑SF‑1) | rehacer la pantalla de la hoja con AG Grid |
| RS‑2 | Agua y electricidad con `Dominio.CIVIL` (DA‑SF‑3) | expediente para un `Dominio` nuevo |
| RS‑3 | El Excel no se reimporta (DA‑SF‑4) | una fase extra de importación con auditoría |
| RS‑4 | Definición del punto de equilibrio de §9.4 | cambiar una función pura y sus pruebas |
| RS‑5 | Constantes de especialidad sin fuente verificada se usan como supuesto declarado | cifras de desperdicio u holgura discutibles hasta verificarlas |
| RS‑6 | SF se inserta antes de Med (§2) | Med mediría una interfaz que ya no existe |

---

## 15. Riesgos

| Riesgo | Mitigación |
|---|---|
| `st.data_editor` no aguanta la hoja (recargas, filas, estado por fila) | prueba de SF0 con criterio fijo y paso a AG Grid sin rehacer las demás fases |
| Los DXF reales no siguen la convención de capas | el informe de importación lista lo no reconocido; la hoja manual sigue siendo la entrada completa |
| Fuentes normativas de §7 no verificables | constantes como supuesto declarado (RS‑5), visibles en la hoja y marcadas por R8 |
| Cinco cambios en `core/` | un expediente por cambio, pruebas antes que código y guardia del núcleo en la CI |
| El sprint alarga el cierre | orden de caída de §13; SF5 es la primera en caer |
