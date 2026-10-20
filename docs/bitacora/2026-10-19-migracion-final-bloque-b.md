# Migración final, bloque B (T4 a T8): registro de ciclos

Rama `inc/ruta-s2-mig-final-b`, árbol `.worktrees/s2m4`, desde `inc/ruta-s2-mig` (b2d1c2d). Orquesta `tesis-b9`; el
árbitro de cada entrega es un subagente nuevo que juzga con `docs/planes/MANUAL_ARBITRO.md`. Manual de los
implementadores: `docs/planes/MANUAL_SUBAGENTES_FINAL_B.md`. Sin push ni PR; la integra `tesis-8d`.

## Ciclos

| Tarea | Implementador | Ronda | Veredicto | SHA de la cabeza |
|---|---|---|---|---|
| T8 Reajuste y Control | Sonnet | 1 | APROBADO | f177106 (rojo ebf17b0) |
| T4 variaciones atípicas | Opus | 1 | DEVUELTO (MAYOR: el porcentaje exacto no estaba a la vista) | 14eb075 |
| T4 | Opus | 2 | APROBADO | 62ac906 (rojo b05b4e3) |
| T5 Empresas registradas | Opus | 1 | APROBADO | 6586683 |
| T6 Asistente de IA | Opus | 1 | APROBADO | edfb357 |
| T7 Revisar un paquete | Opus | 1 | DEVUELTO (2 MAYOR: 500 al dictaminar un alterado; desvíos sin es-VE) | 378f0ba |
| T7 | Opus | 2 | APROBADO | b2e97cb (rojo a46a815) |

| T8b alertas del núcleo con tilde | Sonnet | 1 | DEVUELTO (MAYOR: huecos `.+` encadenados, costo cúbico y recursión en el desglose «no aplica») | f5310e8 |
| T8b | Sonnet | 2 | APROBADO (MENOR: el tope de 2 000 caracteres dejaba sin corregir desgloses largos; cerrado y verificado por el orquestador) | d58e251; cierre 5a05957 (rojo 02d563e) |

| T9 calidad de pruebas | Sonnet | 1 | APROBADO (MENOR: piso de AppTest preventivo sin rojo real, declarado) | deec248 (a3b7d19, 680a3fe, cfd92b4) |

Compartidos aplicados por el orquestador: `30819c7` (routers, tabla de acceso, CHANGELOG, api.json) y `b49ccf0`
(api.json tras la ronda 1 de T7). Verificación tras `30819c7`: 268 pruebas verdes de acceso, OpenAPI, rutas del front y
arquitectura.

## Correcciones de la auditoría visual (VB‑2 a VB‑23), cuatro paquetes

Informe de la auditoría: `2026-10-19-auditoria-visual-bloque-b.md` (commit 9efba7d). Cada paquete trabajó en carpetas
disjuntas del mismo árbol, con su rojo en commit propio antes de cada corrección, y un árbitro nuevo por entrega.

| Paquete | Hallazgos | Ronda y veredicto | Cabeza |
|---|---|---|---|
| A Control y Reajuste | VB‑3, 4, 5, 10, 13, fechas de VB‑19 | R1 DEVUELTO (MAYOR: `fechasEsVe` reescribía fechas de datos del usuario); R2 DEVUELTO (MAYOR: el foco quedaba bajo la cabecera fija, medido en navegador; causa, una instrucción del orquestador); R3 APROBADO | a3fc664 (rojo b68344a) |
| B Elaborar, Historial, Tablero, Entregar | VB‑6, 7, 8, 16 (Entregar, Tablero), 19, 21 | R1 APROBADO | db2badf |
| C Marco, Inicio, Administración | VB‑2, 9, 12, 14, 15, 18, 20, 22, 23 | R1 DEVUELTO (MAYOR: la prueba de Esc no protegía la devolución del foco; mutante); R2 APROBADO | 5a563d6 (rojo 1f63ae8) |
| D Componer, Precios, Revisar | VB‑11, 16 (Precios, Revisar), 17, 19 (Revisar) | R1 DEVUELTO (3 MAYOR: regex cuadrática, sustituciones sobre datos del usuario, fechas por regex sobre texto armado); R2 APROBADO; cierre de MENOR verificado por el orquestador | 4ac64fd |

Lección repetida que conviene fijar: toda regla que reescribe texto con datos del usuario (regex, `strptime`, sustitución
de palabras) debe actuar solo sobre su ranura o su plantilla fija, con costo lineal, tope de longitud y una prueba
adversarial de 100 000 caracteres. Lo aprendieron T8b, el paquete D y el paquete A, en ese orden. Segunda lección: una
prueba de jsdom no ve la geometría ni el foco; VB‑2 y el foco bajo la cabecera de VB‑13 solo aparecieron al medir en
navegador.

Compartidos aplicados por el orquestador: `docs/api.json` regenerado (solo cambian `CalculoRespuesta.total_exacto` y
`TarjetaRespuesta.exacto`; 10 líneas) y el CHANGELOG. Verificación: 281 pruebas de OpenAPI, acceso, rutas del front y
arquitectura, con `-W error`.

### Decisiones nuevas para Eugenio

- Un administrador ya no ve la zona de soltar de Inicio: no tiene `leer_proyecto` (`seguridad/permisos.py`). Si quieres
  que pueda auditar hay que darle esa acción, que es un cambio de requisito.
- «Día 3» escrito a mano en Elaborar se guarda «Dia 3» (convención del núcleo, `core/budget/curva.py:30`); la tilde
  exigiría cambiar el núcleo y el aval del tutor.
- El texto «uv sync --extra ia» vive en dos lugares (`asistente/administracion.py` y el front del Asistente); la
  pantalla clásica lo sigue mostrando.
- Quedan sin tilde en `aplicacion/composicion.py` mensajes de paridad letra por letra con la clásica («codigo»,
  «descripcion», «composicion», «estimacion») y jerga en `api/rutas/precios_empresa.py` («UC‑17 4a»): acentuarlos
  obliga a cambiar pruebas de la clásica.
- Jerga del núcleo que solo recibió tildes y sigue a la vista: «(S1)», «(S1‑R2)», «(S1‑R10)», «(S1‑R21)», «(S2‑R4)»,
  «UC‑17», «UC‑18», «RNF‑14», `mecanismo_pagadero`, `por_partida`, `mano_obra`. Quitarla exige tocar `core/` o un
  catálogo de reescritura.
- Textos del núcleo sin tilde o con defecto de redacción solo registrados (no se tocan en `core/`):
  `core/verification/reglas.py:254, 263, 296, 335, 626, 648‑649`; `core/budget/equilibrio.py:123`;
  `core/verification/precios.py:174‑176` (paréntesis vacíos); `core/verification/informe.py:131` y
  `api/esquemas_informe.py:62` («CUMPLE / NO CUMPLE» en mayúsculas); `core/budget/reajuste.py:45` («INDICIO:»).
  «Sílice» sin tilde en `fusion/alertas.py:158`, `fusion/mapeo.py:214`, `fusion/proceso.py:328 y 574` y
  `adapters/hoja_empresa/` (reglas, plantilla, escritor).
- El corte `[:10]` de `aplicacion/control.py:165` pierde un segundo feriado separado por espacio; desde React ya no se
  alcanza, desde la API directa y la clásica sí.
- La hoja «Decisiones» del Excel pasó a texto dd/mm/aaaa; conviene celdas de fecha reales tomadas de `decisiones()`.

### Deuda nueva anotada por los árbitros (MENOR)

- Un componente común para el patrón «exacto en `title` más texto oculto» (4 copias) y reusar el estilo del indicador
  del Libro en el Tooltip del Historial.
- `aplicacion/reajuste.py` importa `Hueco` y `catalogo_de_frases` de `aplicacion/control.py`: llevarlos a un módulo
  neutro de frases del núcleo.
- `fechaEsVe` de `formatoEsVe.ts` reformatea fechas imposibles («2026‑13‑45»); `fechaDeRanura` de Control sí las
  rechaza: unificar.
- La regex de miles de `formatoEsVe` es cuadrática con más de 30 000 dígitos (anterior y no realista con `Decimal(28)`).
- `InformeAuditoria.tsx`: las columnas Impacto, Observado y Esperado se ven con punto decimal.
- VB‑18 en Reajuste: 11 `TextInput` con regiones vivas vacías; usar `CampoTexto` de `comun/`.
- `titulos.test.tsx` («inicio: un solo h1», hasta 21 s en frío) y `App.test` («#/libros», `findBy` de 5 s) son frágiles
  bajo carga desde antes: cargar la página en un `beforeAll`.
- Las cabeceras ordenables de Carbon leen en inglés «Click to sort rows by…» a lectores de pantalla.
- `estilos.test.ts` y `ZonaDeSoltar.test.ts` leen el `.scss` en vez de medir: la medición en navegador es lo que da fe.

## Correcciones del delta de la auditoría visual (VD‑1 a VD‑11), tres paquetes

Informe: `2026-10-20-auditoria-visual-delta-integrada.md` (commit f896fd7, sobre la rama integrada 647c67e). Mismo
método que antes: carpetas disjuntas, rojo en commit propio antes de cada corrección, un árbitro nuevo por entrega y
medición en navegador sobre una copia aislada de cada implementador y de cada árbitro.

| Paquete | Hallazgos | Ronda y veredicto | Cabeza |
|---|---|---|---|
| 1 Control, Tablero, Reajuste, Precios | VD‑1, 5, 8, 11 | R1 DEVUELTO (MAYOR: `inline-size: 1%` en la papelera de VD‑11 hacía salir el tooltip de la tabla a 1366 px; causa, la propia corrección de VD‑11); R2 APROBADO (16 casos medidos en navegador) | 9f9ee57 (rojo 2bf05ee) |
| 2 Foco, marco, Inicio, Administración | VD‑2, 3, 4, 7, 10 | R1 DEVUELTO (MAYOR: el efecto del foco tomaba la redirección de la carga inicial por un cambio de página); R2 DEVUELTO (MAYOR: el anillo hacia afuera no se veía en el Libro, causa una decisión del orquestador); R3 APROBADO | b364c22 (rojo 83fc6f8) |
| 3 Componer | VD‑6 | R1 APROBADO | 1148925 (rojo b27d1f6) |

Lecciones nuevas: (1) un arreglo de geometría o de foco se mide en navegador con el elemento en su estado
interactivo (tooltip abierto, foco, hover) y con píxeles, no solo con la caja en reposo; los dos MAYOR de este tramo
(tooltip y anillo) solo los vio una medición así. (2) Una guarda de «primera carga» no basta con la ruta previa: hay
que contar las redirecciones del enrutador (`REPLACE`). (3) La corrección de un hallazgo puede ser la causa del
siguiente: cada ronda se juzga contra el estado anterior y no solo contra el hallazgo.

Compartidos aplicados por el orquestador: `docs/api.json` regenerado (campo aditivo `OpcionRespuesta.supuestos` y
esquema nuevo `SupuestoRespuesta`, 31 líneas) y el CHANGELOG. Verificación en el árbol integrado: front completo 90
archivos / 1212 pruebas verdes, `npm run lint` limpio, `npm run build` compilado, `ruff check .` limpio y 440 pruebas
de backend con `-W error` (OpenAPI, acceso, rutas del front, arquitectura, Control y tildes).

### Decisiones nuevas para Eugenio (delta)

- La Nota de las opciones de recuperación de la interfaz nueva dice «eficiencia de la cuadrilla adicional» y
  «recargo de las horas extra»; la clásica sigue con «eta de cuadrillas: 0.80 (SUPUESTO_DECLARADO)». ¿Se lleva el
  texto nuevo a la clásica?
- Se quitó del `title` de rótulos y naturalezas el código original que V‑22 había dejado «para trazabilidad». Si se
  quiere conservar, hace falta otro medio (texto oculto o ayuda aparte).
- Inicio omite ahora «Caso abierto» y «Recorrido en curso» para las cuentas sin `leer_proyecto` (el administrador): el
  caso sigue en la cabecera y esas cuentas no pueden iniciar el recorrido de auditar.
- El foco al `h1` en un cambio de página se aplica a toda navegación en la que el foco se pierde, no solo a
  «Auditar por mi cuenta»; no actúa en la carga inicial ni cuando otro control ya tiene el foco.

### Deuda nueva anotada por los árbitros (delta)

- `AreaTexto.tsx` (Componer) duplica unas 15 líneas de `CampoTexto`: subirla a `src/comun/` o parametrizar
  `CampoTexto`; la prueba de la página no cubre los campos de las filas de la tabla de insumos ni el área de
  «Condiciones del rendimiento».
- VD‑6 sigue en Escenarios, Precios, Actualizar, Elaborar, Histórico, Simulador, Índices, Historial, Libro, Existencias
  y Similares (regiones `role=alert` vacías que monta Carbon): migrarlos a `CampoTexto`; Reajuste (10) ya estaba anotado.
- `TablaDensa` (`src/comun/TablaDensa.tsx:86-88`) pone `title` en toda celda de columna numérica con `presentar`, también
  en textos que no son cifras («día 46», «no aplica», «sí»).
- La regla del anillo del Libro depende de `.silice-pagina-libro`: cuando se migre la Hoja, que comparte el visor,
  debe reutilizar esa clase o la regla debe generalizarse al h1 con relleno del visor.
- La búsqueda del h1 espera hasta 240 cuadros (unos 4 s): puede mover el foco tarde si la página carga muy lenta y la
  persona no interactuó; inocuo.
- La papelera de las tablas editables de Reajuste queda unos 14 px más arriba que los campos de su fila (anterior).
- Quedan sin corregir, por ser texto de `core/`: «se alcanza en Dia N» en Control (Opciones y punto de equilibrio
  proyectado) y los motivos «no aplica» de `LimiteLegal` con cifras con punto y palabras sin tilde.

## Incidente

El implementador de T8 ejecutó `git checkout -q HEAD -- .` en el árbol compartido y descartó cambios sin commitear de
archivos versionados. Los implementadores de T4, T5, T6 y T7 comprobaron sus archivos y ninguno perdió trabajo (sus
cambios ya estaban en commits o en archivos sin seguimiento). Regla recordada: nada de `checkout`, `reset`, `stash`
ni `clean` en el árbol compartido.

## Decisiones tomadas por el orquestador (ratificables por Eugenio)

1. Un paquete «alterado» no admite dictamen (`SIN_DICTAMEN`): es lo conservador y reversible.
2. En la tabla de variaciones atípicas, el ícono de «Advertencia» usa el token `--silice-atipico` (morado), con texto
   e ícono: DESIGN.md asigna ese color a los atípicos (RF-100).

## Decisiones para Eugenio

- ¿Se pone freno de intentos a reactivar la clave de IA? Hoy no lo tiene, igual que en la clásica; su respaldo usa
  Argon2, que ya es lento.
- `seguridad/json_estricto.py` repite el nombre completo de una clave duplicada en su mensaje, sin tope de longitud
  (módulo compartido, fuera de T5).
- El Excel externo de «Revisar un paquete» pasa ahora por la guardia de `.xlsx`; la clásica no lo hacía.
- La clásica sigue ofreciendo el formulario de dictamen para un paquete alterado y responde con `st.error` al enviarlo.

## Límite conocido de `con_tildes` (T8b, hallazgo 2 del árbitro)

El núcleo arma el desglose de partidas sin motivo con `"; ".join(f"{c}: {m}" ...)` (`core/budget/recuperacion.py`,
intocable). Un código de partida que contenga «; » y «: » es ambiguo con dos ítems; solo se corrige lo que calce con
un motivo del conjunto cerrado (sin composicion de APU, sin rendimiento, sin mano de obra a jornal) a la derecha del
último «: » de cada ítem, y todo lo demás queda intacto. El tope de 2 000 caracteres vale solo para el catálogo de
plantillas por regex; el desglose es lineal y no lo necesita. Sin corregir por ser texto propio de `aplicacion/` y de
la ruta, con claves que usan las pruebas y el front: «Desvio de precio», «Fin (dia habil)», «Retraso (dias)»,
«mas de 7 dias» en `api/rutas/control.py`. El cambio «Mas»→«Más» de dos pruebas quedó en el commit de implementación
`f5310e8` y no en uno de pruebas en rojo (reescribir historia sería peor).

## Deuda anotada (MENOR de los árbitros)

- `fechaDeHoy` está copiada seis veces en el front (`administracion`, `actualizacion`, `indices`, `precios_empresa`,
  `elaborar`, `componer`): unificar en `src/comun`.
- `_contenido` (T5) y `_leer` (T7) hacen casi lo mismo: helper común de subida con tope.
- T7: un `IntegrityError` distinto de la carrera deja el archivo escrito en `datos/paquetes/` sin fila; conviene
  `ruta.unlink(missing_ok=True)` antes de relanzar.
- T6: el 403 por rol de ana y rita solo se prueba en el GET, no en los tres POST de la clave.
- Resto de la ranura de cabecera en `src/visor` y `libros` (sin alimentar); «Periodo» sin tilde en `elaborar` y
  `tablero`; textos sin tilde en módulos previos («clave publica», «contrasena», «Agregar linea»).
- Una cifra con `%` pegado («15.00%») no pasa a es-VE en `formatoEsVe`.

## Pendiente

- Verificación manual pendiente (T9): correr en un equipo con `xlrd` (`uv sync --extra bcv`) las 3 pruebas con
  archivo `.xls` real del BCV: `tests/unit/adapters/test_bcv_libro.py::test_el_libro_real_abre_con_su_huella`,
  `tests/unit/adapters/test_bcv_tasa.py::test_el_archivo_real_da_n_hojas_y_coincide_con_la_transcripcion_a_mano` y
  `tests/unit/adapters/test_bcv_inpc.py::test_el_archivo_real_coincide_con_la_transcripcion_a_mano`. En este equipo no
  hay `xlrd` y fallan con `ModuleNotFoundError` (sin skip a propósito); la lógica del lector queda cubierta con el
  `xlrd` falso. La CI (`uv sync --locked --all-extras`, `ci.yml:105`) debe correrlas.
- Decisión para Eugenio: esas 3 pruebas dejan la suite roja en un equipo local sin el extra `bcv`, por la regla de
  cero omitidas (`scripts/verificar_omitidas.py` rechaza cualquier omisión). La alternativa de fondo es hacer
  obligatorio el extra `bcv` en el entorno de desarrollo.
- El piso de 60 s para `default_timeout` de AppTest es preventivo: en la sesión de T9 no se reprodujo el
  agotamiento de 3 s. Si reaparece, medir con la máquina cargada antes de subirlo más.
- Formato: `ruff format --check .` seguirá listando 41 archivos (5 de `tests/fixtures`, que no se formatearon por
  precaución ante huellas, y 36 ajenos de producción) hasta que alguien decida formatearlos.
