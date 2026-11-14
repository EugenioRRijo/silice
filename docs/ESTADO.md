# Estado del proyecto

**Actualizado:** 2026-11-13 · lo mantiene el orquestador (Claude) al cerrar cada fase o al fusionar un PR.

Esta página es la **única fuente del estado actual**. Los planes de la raíz y de [planes/](planes/) y
la [bitácora](bitacora/) cuentan cómo se llegó aquí; si dicen otra cosa, manda esta página. Las cifras
de pruebas y de requisitos no se repiten aquí: viven en su fuente ([metodologia.md §5](metodologia.md)).

## 1. Qué hay en `main`

`main` = **el programa completo** (PR #98, 2026-11-02) y, desde el 2026-11-04:
- **Rediseño F4** (PR #101, `fa47009d`): la obra por secciones y el Presupuesto en seis pestañas.
- **Tarea 16c, manual de usuario F4 y diseños F5** (PR #103, `7dcdc5c9`): el ligante en la receta de la planta, el
  manual nuevo y los diseños del presupuesto vial y de la ventana de escritorio (solo diseño).
- **Pulido F5, tandas 1 y 2** (PR #104, `febf6673`).
- **Contexto para agentes y puente con Antigravity** (PR #102, `076793b8`): `AGENTS.md`, esta página y las skills.

Se probaron en vivo en Chromium con la siembra ficticia antes de fusionar. Contiene también la API FastAPI (`api/`) y
la interfaz React (`frontend-desktop/`) en un solo proceso Uvicorn (Streamlit y el Visor 3D se retiraron el 2026-10-21,
enmienda de [arquitectura.md](arquitectura.md)), los módulos Auditoría, Presupuestos y obras, y Producción, y el
instalador con huella SHA-256 firmada.

## 2. PR y ramas abiertas

| PR o rama | Qué trae | Estado |
|---|---|---|
| #105 `fix/reloj-pruebas-hoja` | Dos pruebas de la Hoja (R6, R7) que desde el 2026-11-05 caían por el reloj del equipo | CI en verde: Eugenio lo fusiona; sin él, la CI de cualquier PR contra `main` cae |
| #106 `feature/f6-espacios` | Rediseño F6 completo (§3) | Arbitrado y corregido; espera la prueba de Eugenio en el navegador y la fusión |
| #107 `feature/autocompletado` | Autocompletado guiado AC1–AC4 (§3) | Árbitro xhigh: aprobado en la ronda 4; espera #105 (r6/r7) y la prueba de Eugenio |
| `feature/tanda-detalles` | Tanda de detalles D1–D17 (§3), sobre F6 y el autocompletado unidos | Aprobada (rondas 2 y 3 del árbitro); sin PR hasta que se fusionen #106 y #107 |
| `feature/integracion-fases` | F7 Ayuda, F8 Cierre, F5 vial y F5 ventana, sobre la tanda (§3) | Construidas en paralelo el 2026-11-06, una por árbol; espera el árbitro único y la prueba de Eugenio |
| `feature/lector-topes` | Topes de la guardia en el lector del libro conocido y en la réplica del visor (§5.3), sobre la integración | Árbitro xhigh: aprobado con condiciones, ya corregidas ([acta](bitacora/arbitrajes/lector-topes-claude-xhigh.md)); sin PR, como la integración |
| `feature/tanda-2026-11-12` | V4 (humo de la ventana en la CI de Windows), topes del lector en todas las subidas de .xlsx, aviso del puerto de depuración por política, pruebas intermitentes y metas en UTF-8, sobre `feature/lector-topes` | Árbitro xhigh: aprobado con cambios, ya corregidos; humo verde en windows-2025 (corridas 43358266674 y, con las decisiones (e) y (f), 43371689578); Argon y Hydrogen: aprobado (con un cambio de Argon, aplicado); decisiones (d), (e) y (f) simuladas y aplicadas (§4, punto 10); sin PR, como la integración |
| `feature/hoja-desperdicio` | El desperdicio en la Hoja (mostrar y editar la neta y el %), tildes de dos avisos con el experimento re-congelado con acta, y el lector del libro con un APU por hoja probado en local con el libro vial real (`lado_de_los_porcentajes`, cifras con la precisión de Excel), sobre `feature/tanda-2026-11-12`. Desde el 2026-11-13, también la **prueba de punta a punta** con un presupuesto vial real, corregida en tres líneas unidas a la rama: vial (VR8, `suministro` y `captafaros`, VR4 por la descripción; [bitácora](bitacora/2026-11-13-e2e-vial.md)), plan y precios (primera versión en semanas o meses, lista para armar desde la de la empresa, revisión y alta; [bitácora](bitacora/2026-11-13-e2e-precios.md)) y front y textos (envío a aprobación, perfil del libro y AH11, textos, Componer; [bitácora](bitacora/2026-11-13-e2e-front.md)), y el ciclo de importación de `aplicacion/` | Árbitro xhigh, ronda 1: aprobado con cambios (0 MAYOR, 9 MENOR), corregidos en `fix/arbitro-1113`; Argon y Hydrogen medium: sus dos hallazgos verdaderos ya estaban corregidos. **Ronda 2** (con las tres líneas): sus hallazgos se corrigen con prueba en rojo primero (la historia, reescrita sin subir, ya no trae una cifra real; «Usarla como lista para armar» solo para quien arma, la tabla de insumos nuevos sin claves y «Recuperación», `bba7bca7`; este registro al día). **Ronda 3: aprobado con cambios (0 MAYOR, 5 MENOR de registro y de datos), corregidos.** Suite completa de Python verde (12.534) y front 4.426/4.426 con la rama integrada. Decisiones del desperdicio y de las tres líneas simuladas (por ratificar, §4 punto 11); sin PR |
| #100 `feature/nucleo-alias-ton-litro` | Alias «ton»→t y «lt»/«litro»→l en el núcleo (expediente NUC-E1) | **No fusionar** sin el aval del tutor. Ya tiene `main` unido y el experimento recongelado con acta (`docs/bitacora/2026-11-04-recongelado-experimento.md` en su rama) |

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

## 4. Lo que espera a Eugenio

1. Fusionar en GitHub, en este orden y con merge commit: #105 (CI verde), #106 (F6) y #107 (autocompletado), cada
   uno después de probarlo en el navegador. Claude no puede fusionar: el control de permisos de Claude Code lo bloquea.
2. Probar la tanda de detalles en el navegador, en especial la columna «Estado» del Presupuesto a 1366 px (D13) y la
   tabla apilada de la Vista general (D14), que jsdom no mide.
3. Decisiones ratificadas en bloque el 2026-11-04
   ([bitacora/2026-10-30-preguntas-para-eugenio.md](bitacora/2026-10-30-preguntas-para-eugenio.md)); quedan **a cotejar
   con el tutor** las que dependen de una fuente externa (IVSS, ligante, proxy de asfalto, tolerancia de receta,
   pintura, `t·km` y el IVA 16 %). Otra lista con datos de la empresa vive **solo en su equipo**.
4. Responder las preguntas de los diseños de F5 (presupuesto vial, §10 de su especificación; ventana de escritorio) para
   poder construirlos.
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
   con datos ficticios y se eligió la mejor; todas son reversibles (cada bitácora dice cómo) y esperan su ratificación.
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
5. **Siguiente** (de la prueba del libro vial real, bitácora §3): un perfil con varias hojas de presupuesto (una por
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
   - **Para el próximo re-congelado de `aplicacion/hoja.py`**: que `_estado_de_precio` mire la fuente declarada de
     cada precio (D-17, que no se pudo arreglar desde la vista) y `con_plan_por_rendimientos` use `plan_que_cabe`;
     «+ Administración» con tilde; y que `estado_de_items` no reparta por partida un hallazgo que ya cita su renglón.
   - **Sin hacer**: la cantidad de 0,001 que se lee «0,00» en la pestaña APU (no se localizó: hace falta la celda
     exacta); la celda del precio redondeada en reposo y exacta al editarla (`TablaInsumos`); el selector de partida
     de las valuaciones de Control, que ofrece un solo renglón por código; elegir la hoja del presupuesto aparte del
     perfil; `suministro` en `frontend-desktop/src/api/vial.ts` (hoy no hace falta).
   - **Notas del árbitro (ronda 2), para Eugenio**: un plan armado por meses («Mes n») se muestra en la pestaña del
     plan como si fuera por días y Control pide a mano los días por período (5 por omisión; un mes son 20); y la salida
     del 422 de más de 10.000 días («cree el plan y asigne más cuadrillas») no se puede seguir desde la pantalla, que
     pide el plan antes que las cuadrillas. VR4 lee la banda con el `patron_banda` del perfil del libro de la
     instalación: un perfil local mal escrito apaga la lectura y deja un INFO. El verde `2b436af1` relajó, sin
     declararlo, el nombre accesible del aviso AH11 a su texto.
   - **Funciones que faltan** (la prueba las pidió y Sílice no las tiene): importar a la Hoja el libro auditado,
     agrupar el presupuesto por frente, sacarlo en PDF, índices del BCV en USD y parámetros editables en Componer.

## 6. Auditorías en paralelo

Cuando otro agente (por ejemplo, Antigravity) audita a la vez, sus hallazgos van a
`bitacora/auditoria-agy-AAAA-MM-DD.md` y el orquestador escribe al lado el veredicto (confirmado,
falso positivo o ya resuelto en una rama). Lista abierta:
[bitacora/auditoria-agy-2026-11-04.md](bitacora/auditoria-agy-2026-11-04.md).

En la otra dirección, el orquestador le encarga trabajo a Antigravity con el subagente
`silice-antigravity` (`.claude/agents/silice-antigravity.md`), que llama a
`agy -p "…" --sandbox </dev/null`, siempre en modo de solo lectura, o directamente con el servidor MCP
`antigravity` (`scripts/mcp_antigravity.py`, registrado en `.mcp.json`: herramientas
`encargar_a_antigravity` y `arbitrar_rama`). Los permisos de `agy` viven fuera del repositorio, en
`~/.gemini/antigravity-cli/settings.json`: `proceed-in-sandbox`, comandos de lectura permitidos y
lectura de `docs/auditoria` y `data/confidencial` negada (comprobado con un archivo ficticio).
