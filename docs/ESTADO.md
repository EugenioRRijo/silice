# Estado del proyecto

**Actualizado:** 2026-11-24 · lo mantiene el orquestador (Claude) al cerrar cada fase o al fusionar un PR.

Esta página es la **única fuente del estado actual**. Los planes de la raíz y de [planes/](planes/) y
la [bitácora](bitacora/) cuentan cómo se llegó aquí; si dicen otra cosa, manda esta página. Las cifras
de pruebas y de requisitos no se repiten aquí: viven en su fuente ([metodologia.md §5](metodologia.md)).

> **Congelamiento del consejo (2026-11-23):** tras #138 a #141 no entran funciones nuevas; se valida con personas y se
> mide la auditoría sin circularidad ([plan](planes/2026-11-23-plan-auditoria-no-circular.md)). #142 y #143 son lo
> último: la pantalla por causa raíz y los instrumentos de medición (§2).

## 1. Qué hay en `main`

`main` = **el programa completo** (PR #98, 2026-11-02) y, desde el 2026-11-04:
- **Rediseño F4** (PR #101, `fa47009d`): la obra por secciones y el Presupuesto en seis pestañas.
- **Tarea 16c, manual de usuario F4 y diseños F5** (PR #103, `7dcdc5c9`): el ligante en la receta de la planta, el
  manual nuevo y los diseños del presupuesto vial y de la ventana de escritorio (solo diseño).
- **Pulido F5, tandas 1 y 2** (PR #104, `febf6673`).
- **Contexto para agentes y puente con Antigravity** (PR #102, `076793b8`): `AGENTS.md`, esta página y las skills.
- **Pruebas R6 y R7 sin reloj** (PR #105, `693b74dd`) y **rediseño F6, espacios enrutados** (PR #106), fusionados el
  2026-11-13 por Claude con la autorización de Eugenio («hazlas tú, todo el pendiente, te doy permiso»).
- **Autocompletado, tanda del 12/11 y desperdicio en la Hoja** (PR #108, `ab867653`, 2026-11-13): lleva el PR #107
  (que queda fusionado), la tanda de detalles, F7, F8, F5 vial y ventana (V0 a V4), los topes del lector, la tanda del
  2026-11-12 y la prueba de punta a punta con sus correcciones (§3 y §4, punto 11).
- **Depuración y desenredo** (PR #110 a #122, fusionados el 2026-11-18 por Claude con la autorización de Eugenio:
  «te doy permiso de lo que queda pendiente de fusionar y ratificar»): la depuración unida, las olas 1 a 4 del
  [plan de desenredo](planes/2026-11-17-plan-desenredo.md), los anexos A.1 a A.9, C9, P7 y A.6. Cada PR se llevó a
  `main` antes de fusionarlo; el árbol de `main` (`e3419e40`) es idéntico al probado en la punta (13.169 pruebas de
  Python, el front, lint, ruff, metas y guardia en verde; CI verde en Ubuntu y Windows).
- **Arreglos de la prueba en vivo** (PR #123 a #127, fusionados el 2026-11-19 por Claude con la autorización de
  Eugenio: «te autorizo a fusionar #123 a #127»): el marco (#123), Producción (#124), el presupuesto (#125), Control y
  la demo (#126) y la documentación (#127: ratificación DS-1 a DS-58, acta DS-59 a DS-66 y la
  [bitácora de la prueba en vivo](bitacora/2026-11-18-prueba-en-vivo.md)). La suite de la unión de los cuatro dio
  13.333 pruebas de Python y 4.621 del front en verde (tras corregir dos pruebas viejas); CI verde en Ubuntu y Windows
  en cada PR. `main` queda en `7c6a3d6e`.
- **Estado y tanda técnica del 2026-11-19** (PR #128 a #132, fusionados por Claude con la autorización de Eugenio:
  «fusiona el #128 y sigue con lo que puedes hacer sin mí» y «cuando terminen abre los PR y fusionalos»): esta página
  (#128), la deuda de presentación DS-52 y DS-57 (#129), el pulido de la prueba en vivo (#130), anular el último conteo
  físico (#131) y las escrituras de la instalación con `BEGIN IMMEDIATE` por ruta, con el acta DS-67 a DS-76 (#132).
  CI verde en Ubuntu y Windows en cada PR. `main` queda en `e085ad64`.
- **Ola del 2026-11-19** (PR #133 a #135, fusionados por Claude con la misma autorización: «sigue con lo siguiente
  cuando terminen»): el PDF de hallazgos en el Visor (#133; el botón se llama «Descargar PDF» por pedido de
  Eugenio), Riesgo en la obra de la demo (#134) y la carga de las series viales en Índices del BCV, con la unión de la
  ola y el acta DS-77 a DS-89 (#135).
- **«Descargar PDF» y sprint 1120b** (PR #136 y #137, fusionados por Eugenio): el mapa de series de Riesgo guardado
  por versión, quién guardó el desperdicio y la depuración de la auditoría de Neon del 2026-11-20. `main` queda en
  `df91d176`.
- **Ola 1121 y entrega del consejo** (PR #138 a #141): la depuración de Neon (#138) y el rediseño con su claridad
  (#139), fusionados por Eugenio; la carga cognitiva con el rótulo congelado de la Hoja (#140, opción A de Eugenio) y
  la herramienta de medición de la auditoría, el respaldo local, el guion de la demo del plan B, el ensayo de la
  defensa y el esqueleto del capítulo de resultados (#141), fusionados el 2026-11-24 por Claude con la autorización
  de Eugenio («tu puedes cerrar 140 te doy permiso y lo demas tambien»). `main` queda en `b8cafe8b`.

Se probaron en vivo en Chromium con la siembra ficticia antes de fusionar. Contiene también la API FastAPI (`api/`) y
la interfaz React (`frontend-desktop/`) en un solo proceso Uvicorn (Streamlit y el Visor 3D se retiraron el 2026-10-21,
enmienda de [arquitectura.md](arquitectura.md)), los módulos Auditoría, Presupuestos y obras, y Producción, y el
instalador con huella SHA-256 firmada.

## 2. PR y ramas abiertas

| PR o rama | Qué trae | Estado |
|---|---|---|
| #100 `feature/nucleo-alias-ton-litro` | Alias «ton»→t y «lt»/«litro»→l en el núcleo (expediente NUC-E1) | **No fusionar** sin el aval del tutor |
| #142 `feature/causas-raiz-pantalla` | La pantalla de auditoría agrupa los hallazgos por causa raíz y pone aparte las reglas que no aplicaron (R2 y R7), en la misma pestaña; la respuesta vive en `api/rutas/libros_causas.py` | PR abierto contra `main`; Claude lo fusiona con CI verde (autorización del 2026-11-23) |
| #143 `feature/auditoria-no-circular` | Fase 1 del plan no circular: oráculo LibreOffice, manifiesto de corrida, inyector de fallas, trasplante de valores, medición una falla por vez (`scripts/medir_inyeccion.py --una-por-vez`), metamórficas, sensibilidad de umbrales, tasa de no interpretables y traza por causa. Primera medición: 5 de 12 fallas detectadas | Apilado sobre #142; se fusiona después |

Los `.worktrees/` son copias de ramas de trabajo y **no** describen el programa actual. F6 vive en `.worktrees/s2m3`, el
autocompletado en el checkout principal y la tanda en `.worktrees/tanda`; cada tarea de la tanda tuvo su árbol
`.worktrees/td-*` (autorización de Eugenio del 2026-11-06), que se quita al cerrar la fase.

## 3. Trabajo en curso

**Rediseño F6, espacios enrutados** (PR #106; [plan](planes/PLAN_REDISENO_F6.md),
[seguimiento](bitacora/2026-11-04-f6-construccion.md)). La app abre en la **Vista general**; barra lateral plana; cada
obra con su barra de secciones; la Cuenta reúne preferencias, cuentas, empresa, carpetas, sistema y ayuda. Árbitro final
de Claude xhigh: aprobado con condiciones, ya corregidas. Decisiones de Eugenio del 2026-11-05: «Presupuesto | Componer»,
cabecera compacta del Presupuesto, quien revisa ve y abre las obras de todas las carpetas (`abrir_carpeta`), y la
demostración nunca se mezcla con las carpetas de la empresa (fuera de ella no se lista).

**Autocompletado guiado** (PR #107; [plan](planes/PLAN_AUTOCOMPLETADO.md)): AC1–AC4 hechos (Componer con el precio de la
lista con que arma la carpeta, Control, Reajuste, Escenarios, Simulador, unidades, moneda, proveedor y versión de
comprobación); RF-167, RF-168 y RNF-29 en el ERS.

**Tanda de detalles D1–D17** ([plan](planes/PLAN_TANDA_DETALLES.md),
[arbitraje](bitacora/arbitrajes/tanda-detalles-claude-xhigh.md)). Construida el 2026-11-06 en cinco líneas en paralelo.
La ronda 1 del árbitro xhigh la devolvió con 2 MAYOR (D10 rompía la flecha izquierda de las pestañas; D16 seguía
mezclando la partida con Esc) y 13 MENOR; los dos MAYOR y los MENOR están corregidos con prueba en rojo primero (el 12 es
historia de commits y no se reescribe). La ronda 2 la **aprobó**, y la ronda 3, breve, sobre sus correcciones, también; sus MENOR (un presentador común y
robusto para las tres tablas de cambios, la cabecera de Componer al elegir otra partida, textos) y un defecto anterior a
la tanda (D17) están corregidos. `aplicacion/hoja.py`, archivo congelado del experimento de la tesis, cambió solo en
mensajes: el experimento se re-congeló con acta y autorización de Eugenio
([2026-11-06-recongelado-experimento.md](bitacora/2026-11-06-recongelado-experimento.md)).

**F7, F8 y F5 en paralelo** (2026-11-06, decisión de Eugenio: una fase por árbol, sin árbitro por fase y un solo
árbitro al final). F7 Ayuda: «¿Qué es esto?» en cada pantalla, guías, glosario y «Empieza aquí» (RF-185 a RF-189). F8:
redirecciones viejas retiradas, guion del recorrido rehecho, pasada en navegador ([bitácora](bitacora/2026-11-06-f8-cierre.md)),
front de 14,45 MB a 10,02 MB y «esta carpeta» en los mensajes. F5 vial: tareas 1 a 6 de su diseño (RF-170 a RF-178),
y, desde el 2026-11-13, el desperdicio también en la Hoja (§5.4). F5 ventana: V0 a V3 (RF-180 a RF-184;
[V0](bitacora/2026-11-06-ventana-v0.md)); V4 (humo en la CI) **hecha el 2026-11-12** (§3.3 a §3.5 de esa bitácora) y V5
(prueba en el equipo de Eugenio y en el de la empresa, con el diálogo «Guardar como») pendiente. **Las decisiones de F5 son provisionales**: recomendaciones del orquestador a las preguntas de sus
diseños, anotadas en cada especificación, que Eugenio debe ratificar; la de guardar el perfil de la ventana en la
carpeta de datos la decidió Eugenio el 2026-11-07.

**Árbitro único** ([veredicto](bitacora/arbitrajes/fases-f5-f7-f8-claude-xhigh.md),
[revisión](bitacora/arbitrajes/fases-f5-f7-f8-claude-xhigh-r2.md)): devolvió con 4 MAYOR (un xlsx hostil agotaba la
memoria, perfiles locales inalcanzables, la ventana borraba la letra y el zoom, manuales de la ventana falsos) y, en la
revisión, con 2 (el xlsx hostil por celdas reales lejanas y pruebas omitidas en la CI de Linux). La revisión final
([r3](bitacora/arbitrajes/fases-f5-f7-f8-claude-xhigh-r3.md)) aprobó todo salvo un MAYOR de minutos (una prueba nueva
violaba INV-052), corregido después junto con sus cuatro MENOR; todo con prueba en rojo primero; la pasada en navegador de la rama integrada (864 mediciones) no dejó defectos abiertos. El aviso de solo
lectura sale con tildes por `aplicacion/hoja_guardado.py`, la ruta del producto; el texto sin tildes de `hoja.py`
(congelado) no lo alcanza ningún llamador. Las pruebas intermitentes con la máquina cargada (`Retomar`,
`AutocompletadoDeInsumos` y `Edicion`) se corrigieron el 2026-11-12
([bitácora](bitacora/2026-11-12-pruebas-intermitentes.md)).

**Ola 2** (2026-11-13/14, `feature/ola2`; Eugenio ausente: «hazlas tú, todo el pendiente»). Cuatro líneas en paralelo,
una por árbol, cada decisión simulada ([árbitro](bitacora/arbitrajes/ola2-claude-xhigh.md)):
- **Re-congelado y plan** ([bitácora](bitacora/2026-11-13-ola2-recongelado-y-plan.md),
  [acta](bitacora/2026-11-13-recongelado-experimento-2.md); RF-196 a RF-199): lo que §5.6 dejaba para el próximo
  re-congelado de `aplicacion/hoja.py`, el plan por semanas y meses en su pestaña, los días por período de Control desde
  el plan y las valuaciones por renglón. La medición del experimento da la misma huella antes y después.
- **Front** ([bitácora](bitacora/2026-11-13-ola2-front.md); RF-200 y RF-201): la cantidad 0,001 entera en la pestaña
  APU, el precio redondeado en reposo y exacto al editar, `suministro` en el cliente, AH11 con nombre accesible, las
  pruebas intermitentes por causa raíz y los parámetros del precio editables en Componer (solo para el cálculo).
- **Libro por frentes** ([bitácora](bitacora/2026-11-13-ola2-libro-por-frentes.md); RF-205 a RF-212): varias hojas
  de presupuesto, segunda fila de impuesto, AH12, la hoja elegida aparte del perfil, el perfil local desde Cuenta ›
  Empresa (con defensa contra expresiones que se cuelgan), **llevar el libro auditado a la Hoja** y **el presupuesto
  por frente**. Probado en local con el libro real (solo en el equipo): todos los renglones entran con su frente.
- **PDF e índices** ([bitácora](bitacora/2026-11-13-ola2-pdf-e-indices.md); RF-213 y RF-214): «Descargar PDF» del
  presupuesto y sus APU (agrupado por frente cuando hay frentes) y un índice del BCV expresado en USD para el reajuste.
Incidente de datos (línea 2, [bitácora §8](bitacora/2026-11-13-ola2-front.md)): cuatro parámetros del presupuesto de la empresa (que vive solo en el equipo)
llegaron a commits locales y a una consulta a Gemini, sin nombres ni procedencia; la historia se reescribió antes de
subir nada.

## 4. Lo que espera a Eugenio

1. **Hecho el 2026-11-13:** #105, #106 y #108 (con #107) fusionados por Claude, con la CI en verde y la autorización
   de Eugenio; `feature/ola2` entró como #109. Diez ramas remotas viejas ya contenidas en `main` siguen en GitHub: el
   control de permisos no dejó borrarlas (lista en el informe del 2026-11-14).
2. Probar la tanda de detalles en el navegador, en especial la columna «Estado» del Presupuesto a 1366 px (D13) y la
   tabla apilada de la Vista general (D14), que jsdom no mide.
3. Decisiones ratificadas en bloque el 2026-11-04
   ([bitacora/2026-10-30-preguntas-para-eugenio.md](bitacora/2026-10-30-preguntas-para-eugenio.md)); quedan **a cotejar
   con el tutor** las que dependen de una fuente externa (IVSS, ligante, proxy de asfalto, tolerancia de receta,
   pintura, `t·km` y el IVA 16 %). Otra lista con datos de la empresa vive **solo en su equipo**.
4. Las preguntas de los diseños de F5 y las decisiones provisionales de F5 quedaron **ratificadas por delegación** el
   2026-11-13 («hazlas tú, todo el pendiente, te doy permiso»), igual que D-01 a D-36 del Word y las de la ola 2; todas
   siguen siendo reversibles (cada bitácora dice cómo).
5. El asistente de IA (T20): «luego» (2026-11-05), sin gasto por ahora.
6. Worktrees que quedan (28): con bases o respaldos ignorados (en `.claude/worktrees/prototipo` hay una `data/apu.db` que
   conviene mirar), con cambios sin guardar o con ramas que no están en `main`. Lista en «Limpieza de worktrees TESIS
   (2026-11-03).md» de su Escritorio, sección «No tocados».
7. Negar en el IDE de Antigravity la lectura de `docs/auditoria` y `data/confidencial` (en su línea de comandos ya está).
8. Revisar unas carpetas vacías que un agente dejó en `C:\c\Users\...`.
10. Topes del lector (2026-11-12): las tres decisiones del árbitro anterior están **resueltas**: (a) y (b) con código
   (`feature/tanda-2026-11-12`) y (c) en local: los libros reales pasan los topes y la réplica, muy lejos del límite. Las cuatro decisiones de
   esa rama se **simularon** y quedan como están
   ([acta](bitacora/2026-11-12-decisiones-topes-simulacion.md)): las combinadas cuentan; las valuaciones pasan por la
   guardia (el .xlsm se rechaza como en toda subida); se recorren todas las hojas; 20.000 filas por hoja también en las
   listas. Eugenio puede revertir cualquiera. Con Eugenio ausente se simularon y decidieron también
   ([acta §6](bitacora/2026-11-12-decisiones-topes-simulacion.md); registro completo en el Word «Decisiones arbitradas
   por Claude - Silice.docx» de su Escritorio): (d) la báscula lee del .xlsx `MAX_COLUMNAS + 1` columnas; (e) sin el
   permiso explícito `SILICE_PERMITIR_DEPURACION_VENTANA=1`, que solo pone la humo, algo que pide el puerto de
   depuración abre el navegador en vez de la ventana; (f) el instalador de WebView2 de la CI exige el firmante
   `O=Microsoft Corporation`. Todas son reversibles y esperan su ratificación.
   **Por ratificar con el tutor:** el runtime de WebView2 abre por su cuenta conexiones a servicios de Microsoft
   (medido en la CI y en local, aunque se apaguen SmartScreen, el actualizador de componentes o la red de fondo;
   [bitácora V0 §3.6](bitacora/2026-11-06-ventana-v0.md)). La humo ahora lo informa sin fallar. RNF-08 y RF-98
   dicen «0 conexiones salientes»: hay que declarar la excepción o sacar la ventana de lo que mide RF-98, como
   ya pasa con el navegador.
9. Tesis: aval del tutor para el PR #100, mediciones con personas (Med) y la respuesta de la Dirección de Investigación.
11. Prueba de punta a punta (2026-11-13, `feature/hoja-desperdicio`): con Eugenio ausente, cada decisión se **simuló**
   con datos ficticios y se eligió la mejor; todas son reversibles (cada bitácora dice cómo) y quedaron **ratificadas por
   delegación** el 2026-11-13.
   - **Vial** ([bitácora](bitacora/2026-11-13-e2e-vial.md)): D1, un renglón a mano y el mismo derivado de los tramos se
     advierten con VR8 en la auditoría (no se pregunta al llevar ni se reemplaza); D2, el tramo declara `suministro` y
     la demarcación `captafaros`, y llevar sigue siendo todo o nada; D3, VR4 lee la banda de la descripción del APU con
     el patrón ampliado del perfil, y Componer no pide la banda aparte.
   - **Plan y precios** ([bitácora](bitacora/2026-11-13-e2e-precios.md)): D-2, la primera versión arma el plan por
     días, semanas o meses (la primera unidad que cabe); D-7, una tercera vía para la lista para armar, copiar la de la
     empresa en su moneda; D-8, el archivo se revisa antes y el alta de los insumos nuevos se confirma (los de otra
     unidad nunca); D-11, una fila sin fecha o sin fuente toma las de la lista; §3.1, los precios convertidos se leen
     con dos decimales y la celda guarda el exacto.
   - **Front y textos** ([bitácora](bitacora/2026-11-13-e2e-front.md)): D1, el perfil del libro se elige de una lista
     del servidor; D2, AH11 avisa cuando casan menos de la mitad de dos o más renglones enlazados (ADVERTENCIA); D3, el
     «Motivo» de Versiones dice el tipo y la fuente; D4, la lista de sugerencias se abre arriba si abajo no cabe.
   - **Con el tutor**: los expedientes de `core/` que dejó la prueba (§5, punto 6).
12. Depuración unida (2026-11-17; Eugenio ausente, cola activa): cinco decisiones **simuladas** y elegidas, todas
   reversibles ([acta](bitacora/2026-11-17-decisiones-simuladas.md)). DS-3 cambia una conducta: si alguien edita en
   Componer **solo el reparto del desperdicio** y la cantidad queda igual, la edición se rechaza con un mensaje que lo
   explica, en vez de perderse sin aviso al cerrar. Guardar ese reparto sin crear versión queda como mejora en el
   plan de desenredo. Faltan revisar y fusionar los PR de `feature/depuracion-unida` y `docs/sincronizar-agentes`.
13. Redondeo de los libros (2026-11-17, `feature/desenredo-cifras`, tarea 2.3 del plan de desenredo): **RS2-12 pasa
   de redondear al par a redondear al alza** (`ROUND_HALF_UP`). Es la decisión de Eugenio del 2026-11-17 (dos
   decimales al alza al presentar) aplicada a la franja de indicadores de la auditoría de un libro: `actual`, `meta`,
   `delta` y `delta_pct` salen ahora de `api/presentacion.py`. Solo cambia la mitad exacta: un Δ% de 0,125 se ve
   0,13 (antes 0,12) y un total de 1.000,125 se ve 1.000,13 (antes 1.000,12). El cálculo y los exactos de
   `totales_libro` y `totales_silice` no cambian. Para probar en el navegador: la franja de indicadores de un libro.
   La ola 2 cambia también otras salidas (`feature/desenredo-presentacion`, acta DS-14 a DS-19):
   - `/v1/indices/en-usd/ver` pasa al alza (tasa a 4 decimales y valor a 6); se ve en Índices → En USD.
   - `total_texto` de `/v1/entregas/resumen` pasa al alza; la pantalla Entregar no lo muestra.
   - Las cifras de los hallazgos del PDF (`_fmt`) redondean la mitad al alza y no muestran «-0» ni «+0».
   - El aviso de porcentajes distintos (`_pct`) lleva punto de miles desde 1.000 %.
   - En toda la API, un monto que redondea a cero sale «0.00», no «-0.00». Uno de más de unas 26 cifras sale exacto
     en vez de dar 500 (revisión de la ola 2, hallazgo 1, fijado en `tests/unit/test_api_presentacion.py`).

   Para probar en el navegador: la franja de indicadores de un libro y Índices → En USD.
14. Decisiones de Eugenio del 2026-11-18 ([acta](bitacora/2026-11-17-decisiones-simuladas.md)):
   - **A.6 sí** (PR #121): deja sin efecto la DS-3. Guardar solo el desglose del desperdicio ya no se rechaza: escribe sus
     trazas sin crear versión.
   - **4.4 espera al experimento**: `aplicacion/hoja.py` sigue congelado (RS-9) y se parte en el próximo recongelado,
     junto con L5 y L7.
   - **P7 sí** (PR #120): cambiar de perfil reinicia las hojas marcadas.
   - **C9, descripción + unidad** (PR #119).

   **Ratificadas el 2026-11-18** por Eugenio («te doy permiso de lo que queda pendiente de fusionar y ratificar»):
   todas las decisiones simuladas DS-1 a DS-58 del acta, con la DS-48h (guardar solo el desglose, cuando otra persona
   guardó una versión más nueva, pide confirmar igual que una versión). La DS-3 quedó sustituida por A.6 y la DS-23
   (4.4) espera al experimento. La pila #110 a #122 está fusionada (§1).

   **Por ratificar:** las decisiones del árbitro DS-59 a DS-66 (prueba en vivo: el conteo físico cierra el pasado, ciclos de
   recetas con todas las versiones, valuación futura rechazada, CSV para Excel en español, partida pendiente con aviso en vez
   de 409, `calculo_de_regla` sobre `ast`, pendiente de otra carpeta, sección «Contraseña»), y las de la tanda técnica del
   2026-11-19, DS-67 a DS-76 (escrituras de la instalación con `BEGIN IMMEDIATE` solo en las rutas que deciden, cifras
   exactas sin notación científica, respuestas armadas antes del `commit`, índice de aprobaciones sin retener la carpeta,
   anular el último conteo físico, mezcla de mezclas en orden topológico, gráficos en el orden de su tabla, rótulo del
   desglose y fechas de las tablas), y las de la ola del 2026-11-19, DS-77 a DS-89 (PDF de hallazgos re-auditando el
   libro, sin fila en el historial, en el Visor y con el reloj del servidor; series de la demo corridas hasta el mes
   anterior y con poco asfalto y gasoil; carga de las series viales dentro de Índices, en un paso, una serie por
   archivo, con el módulo Riesgo y fuente y fecha obligatorias). El Word «Decisiones pendientes de Eugenio -
   2026-11-19.docx» de su Escritorio reúne todo lo que espera su respuesta. La P2 de ese Word partía de una premisa
   falsa: el PDF de hallazgos no existía y se construyó entero (acta DS-77).

   **Probado en vivo el 2026-11-18** ([bitácora](bitacora/2026-11-18-prueba-en-vivo.md)): A.6, C9 y P7 funcionan en el
   navegador. La prueba de todas las ventanas dejó hallazgos que se arreglan en las ramas `feature/vivo-*` (§2) y otros
   que esperan una decisión (bitácora, §4).
15. **Sprint 1120b (2026-11-20; Eugenio presente al arrancar y delegó «según nuestra metodología»)**: las decisiones
   DS-90 a DS-127 del [acta](bitacora/2026-11-17-decisiones-simuladas.md) quedan **por ratificar**. Cada una se revierte
   con el `git revert` de su verde. DS-75 (la opción A, solo en la lista de Guardar) y DS-117 (robustez de
   `elegir_opcion`, no el defecto de B1) se explican en las «Aclaraciones del orquestador» del acta. Además:
   - **Hook `block-libros-al-repo`:** dispara en falso con `sed` y `grep` de solo lectura. Hay que revisar la regla
     (`.claude/hookify.*.local.md`). Mientras, leer con Read o Grep en vez de rodear el bloqueo.
   - **Commit `534b382f`** (`feature/depurar-logica-1120`): el cuerpo del mensaje tiene una frase cortada («El resumen de
     la fusión pasa a ,»). Reescribir la historia espera decisión de Eugenio.

## 5. Trabajo técnico pendiente (orden recomendado)

Plan detallado, con el protocolo de trabajo con Gemini Flash por `agy` (Flash construye el parche, Claude lo aplica con
TDD y lo audita; árbitro de Claude xhigh en cada compuerta): [planes/PLAN_TANDA_DETALLES.md](planes/PLAN_TANDA_DETALLES.md).

1. **Tanda de detalles**: aprobada (§3); falta la prueba de Eugenio en el navegador. Los mensajes «no existe en este
   caso» ya dicen «esta carpeta» (F8 C5; guardia `tests/unit/test_mensajes_sin_caso.py`).
2. **Autocompletado**: completo (PR #107).
3. **Libros con celdas lejanas: hecho** (2026-11-07, rama `feature/lector-topes`; 2026-11-12, `feature/tanda-2026-11-12`).
   El lector del libro conocido, la réplica del visor (con fórmulas o sin ellas), el lector de un APU por hoja y, antes
   del núcleo, las listas, los presupuestos de terceros, el Excel externo, las valuaciones y los índices del BCV pasan por
   los topes del lector; un libro hostil se rechaza en décimas de segundo con 422. La báscula lee como mucho 61 columnas (§4, punto 10 d).
4. **F7, F8 y F5**: construidas y corregidas tras el árbitro único (§3); faltan la prueba de Eugenio, ratificar las
   decisiones provisionales de F5 y V5 (V4 hecha el 2026-11-12). **Hecho el 2026-11-13** (`feature/hoja-desperdicio`):
   el desperdicio en la Hoja, que se muestra y se edita ([decisión](bitacora/2026-11-13-desperdicio-en-la-hoja.md), por
   ratificar); las tildes de los dos avisos, con el experimento re-congelado
   ([acta](bitacora/2026-11-13-recongelado-experimento.md)); la licencia del SDK de WebView2, idéntica byte a byte a la
   del paquete de NuGet 1.0.3856.49, como los DLL que viajan; y la prueba local del libro vial real
   ([bitácora](bitacora/2026-11-13-libro-vial-real-local.md)), que encontró dos defectos ya corregidos.
5. **Hecho en la ola 2** (§3): de la prueba del libro vial real, bitácora §3: un perfil con varias hojas de presupuesto (una por
   frente), sumar una segunda fila de impuesto, avisar de una hoja que no sigue el prefijo del perfil, y poner un perfil
   local desde la interfaz. Las pruebas intermitentes del front con la máquina cargada `App.bienvenida` y
   `CostosDelPeriodo` (pasan solas). Las tildes que quedan en `aplicacion/hoja.py` (líneas del 422 de guardar) van en el
   próximo re-congelado.
6. **Lo que dejó la prueba de punta a punta** (2026-11-13; §4 y §5 de cada bitácora):
   - **Expedientes de `core/` propuestos, no aplicados** (necesitan el aval del tutor): `crear_lista_desde_archivo`
     (`core/catalog/precios.py`) pierde la fila de un equipo o una mano de obra que trae unidad, porque casa por la
     unidad de la fila y el catálogo los guarda sin ella, y no guarda la fecha ni la fuente de cada fila
     ([precios §5](bitacora/2026-11-13-e2e-precios.md)); `_num` de `core/verification/reglas.py` escribe R1 con punto
     decimal, y R6 y otros mensajes del núcleo van sin tildes ([front §4](bitacora/2026-11-13-e2e-front.md)).
   - **Hecho en la ola 2** (re-congelado del 2026-11-13, [acta](bitacora/2026-11-13-recongelado-experimento-2.md)). Era, para el próximo re-congelado de `aplicacion/hoja.py`: que `_estado_de_precio` mire la fuente declarada de
     cada precio (D-17, que no se pudo arreglar desde la vista) y `con_plan_por_rendimientos` use `plan_que_cabe`;
     «+ Administración» con tilde; y que `estado_de_items` no reparta por partida un hallazgo que ya cita su renglón.
   - **Hecho en la ola 2** (todo lo que era «Sin hacer»): la cantidad de 0,001 que se lee «0,00» en la pestaña APU (no se localizó: hace falta la celda
     exacta); la celda del precio redondeada en reposo y exacta al editarla (`TablaInsumos`); el selector de partida
     de las valuaciones de Control, que ofrece un solo renglón por código; elegir la hoja del presupuesto aparte del
     perfil; `suministro` en `frontend-desktop/src/api/vial.ts` (hoy no hace falta).
   - **Notas del árbitro (ronda 2), para Eugenio**: un plan armado por meses («Mes n») se muestra en la pestaña del
     plan como si fuera por días y Control pide a mano los días por período (5 por omisión; un mes son 20); y la salida
     del 422 de más de 10.000 días («cree el plan y asigne más cuadrillas») no se puede seguir desde la pantalla, que
     pide el plan antes que las cuadrillas. VR4 lee la banda con el `patron_banda` del perfil del libro de la
     instalación: un perfil local mal escrito apaga la lectura y deja un INFO. El verde `2b436af1` relajó, sin
     declararlo, el nombre accesible del aviso AH11 a su texto.
   - **Funciones que faltaban, hechas en la ola 2** (§3): llevar a la Hoja el libro auditado, el presupuesto por frente,
     el PDF, los índices del BCV en USD y los parámetros editables en Componer.
7. **Lo que dejó la ola 2** (bitácoras de cada línea, §4; [árbitro](bitacora/arbitrajes/ola2-claude-xhigh.md)):
   expedientes de `core/` propuestos, no aplicados (aval del tutor): `Catalogo.cargar_composicion` y la colección de
   precios de la lista en la misma sesión (línea 3, hoy esquivado en `aplicacion/libro_a_la_hoja.py`), y el saldo por
   renglón de las valuaciones (`origen_id` en `LineaValuacion` y `PartidaBase`, línea 1 §8). Mejora anotada: la
   defensa de `patron_banda` sigue siendo una heurística (lo peor que acepta es cúbico).
8. **Lo que dejaron los anexos, A.6 y A.9** (2026-11-18, actas DS-52, DS-57 y DS-48):
   - **Hecho el 2026-11-19** (tanda técnica, acta DS-67 a DS-76): DS-52 (los `Decimal` de `api/rutas/` pasan por
     `exacto`), DS-57 (las rutas arman su respuesta antes del `commit`; aprobaciones escribe su índice después, sin
     retener la carpeta), el botón «Guardar el desglose…» de la franja y de Versiones, el rótulo «AF-LLAVE, material
     n.º 1» y el manual. **Hecho en el sprint 1120b** (2026-11-20, `feature/desperdicio-responsable`): DS-48g, quién guardó el desglose
     (migración `caso_0024_desperdicio_responsable`), y DS-75 en su opción A, el insumo en el rótulo, solo en la lista de
     Guardar (DS-97). Queda como mejora: «Versiones» y «Revisar» siguen sin el insumo. El acta de 2026-11-19 había elegido
     la opción B para DS-75: por ratificar.
   - **4.4, L5 y L7:** entran en el próximo recongelado del experimento.
   - **Ola 5:** salir de los ciclos, con `Catalogo.rendimiento_vigente` en `core/`. Espera el aval del tutor.
9. **Ola del 2026-11-19** (acta DS-77 a DS-89): **hecho** el botón «Descargar PDF» del Visor, con una línea que dice qué
   baja (manual §12.2; Eugenio lo conservó y pidió ese nombre), la carga de las series viales en Índices del BCV (manual §9.4) con el enlace desde Riesgo, y la obra de la
   demostración con asfalto y gasoil, cuyas series se siembran corridas hasta el mes anterior (manual §10.6). **Hecho en el sprint 1120b**
   (2026-11-20, `feature/riesgo-mapa-guardado`, DS-90 a DS-94): el caso guarda por versión la serie que mueve cada insumo
   (migración `caso_0023_riesgo_mapa`). Queda como mejora, si Eugenio quiere ver más movimiento en Riesgo, una obra aparte para él (hoy la reserva de la demo es pequeña, unos 74 USD, para no
   desequilibrar Control).

### Declarado fuera de alcance (sprint 1120b, 2026-11-20)

- Tildes en `adapters/espacio/planos/`: el módulo entero va sin tildes.
- ~~JPEG del aviso de imágenes (B5)~~: resuelto en la ola 1121 (L3, `e5df9a3b`).
- Carrera estrecha entre `GET /insumos` y un guardado en vuelo de Riesgo.
- `aplicacion/revision.py` llega a 992 líneas tras la ola 1121 (L1); el tope de la guardia es 1000 y conviene partirlo
  antes del siguiente cambio.
- El patrón de DS-58 (A5) quedó copiado en `aplicacion/elaboracion.py`, `aplicacion/hoja_vial.py` y
  `aplicacion/libro_a_la_hoja.py` (nota 5 del árbitro): un ayudante común es una mejora opcional.
- Sin cambio de código por decisión: DS-100 (C4, cerrar el diálogo de anular conteo) y DS-109 (A13, prueba de guarda).
- Sin cambio por ser falso positivo: A10, B9 y C7 de la auditoría del 2026-11-20.

## 6. Auditorías en paralelo

Cuando otro agente (por ejemplo, Antigravity) audita a la vez, sus hallazgos van a
`bitacora/auditoria-agy-AAAA-MM-DD.md` y el orquestador escribe al lado el veredicto (confirmado,
falso positivo o ya resuelto en una rama). Lista abierta:
[bitacora/auditoria-agy-2026-11-04.md](bitacora/auditoria-agy-2026-11-04.md) y
[bitacora/auditoria-agy-2026-11-20.md](bitacora/auditoria-agy-2026-11-20.md) (Neon sobre el diff `5f910132..main`, con los
diez detalles del 2026-11-04 resueltos) y [bitacora/auditoria-agy-2026-11-21.md](bitacora/auditoria-agy-2026-11-21.md)
(la ola 1121, con veredicto por fila).

En la otra dirección, el orquestador le encarga trabajo a Antigravity con el subagente
`silice-antigravity` (`.claude/agents/silice-antigravity.md`), que llama a
`agy -p "…" --sandbox </dev/null`, siempre en modo de solo lectura, o directamente con el servidor MCP
`antigravity` (`scripts/mcp_antigravity.py`, registrado en `.mcp.json`: herramientas
`encargar_a_antigravity` y `arbitrar_rama`). Los permisos de `agy` viven fuera del repositorio, en
`~/.gemini/antigravity-cli/settings.json`: `proceed-in-sandbox`, comandos de lectura permitidos y
lectura de `docs/auditoria` y `data/confidencial` negada (comprobado con un archivo ficticio).
