# Preguntas para Eugenio: pantallas de los informes (2026-10-31)

Rama `inc/vial-pantallas-informes` (worktree `.worktrees/s2m3`, sale de 9e6bc3ab de `inc/vial-agregados`). Cierra lo que
la fila 112 de `2026-10-30-preguntas-para-eugenio.md` dejó sin pantalla: el reporte de costo de producción y la mejora
de la estimación (Tarea 15) con su informe. Decisiones tomadas con la opción más prudente y reversible mientras Eugenio
está ausente; archivo aparte para no chocar con el común (al fusionar, sus filas pueden pasar allí). Basta con
responder «sí» o corregir la que no guste. Todo con datos ficticios; `core/` intacto.

| # | Pregunta | Qué se hizo | Cómo cambiarlo |
|---|---|---|---|
| PI-1 | ¿Dónde vive el reporte de costo de producción? (fila 112, MENOR 1 del árbitro de la fase D) | Se mudó a `GET /v1/produccion/reportes/produccion?periodo=AAAA-MM`, en un router propio (`api/rutas/produccion_reportes.py`) con `registrar_costos_produccion` (arma y administrador; clave de API o sesión) y **después** `requiere_modulo("produccion")`: sin sesión 401, sin el rol 403, con el rol y producción apagada 404 con el texto de D-V-4. Solo lee la instalación, así el administrador lo baja sin abrir una carpeta. Router aparte (y no dentro de `produccion_planta`) para no sumarle la puerta de la arenera (`operar_arenera`), que no es la de los costos, y porque `produccion_planta.py` ya llega a 600 líneas | Pasarlo a `produccion_planta` si se prefiere un solo router de la planta |
| PI-2 | ¿Se deja la ruta vieja `/v1/vial/reportes/produccion`? | **Quitada.** Nada fuera de las pruebas la usaba: ni el front, ni scripts, ni la documentación de usuario (solo `test_api_reportes_viales.py` y `test_vial_extremo_a_extremo.py`, que pasan a la ruta nueva). `/v1/vial/reportes/{tipo}` queda con `computos`, `apu` y `resumen`; pedir `produccion` allí responde 404 «No existe el reporte «produccion».». La fila T21-4 de `2026-10-31-preguntas-t21-reportes.md` queda superada por ésta | Volver a ponerla como alias si una integración externa la llegara a usar |
| PI-3 | ¿Desde qué pantalla se baja el reporte de producción? | Desde **«Costo por tonelada»**, en la sección «Cálculos de {mes}» (`CalculosAnteriores`): «Descargar el reporte de costo de producción (Excel)» con el mes que se ve. Solo aparece si el mes tiene cálculos guardados (sin ellos el servidor responde 404 y el botón no serviría). El reporte trae **todos** los cálculos del mes, no solo el abierto. La pantalla solo la ve quien tiene `registrar_costos_produccion`, el mismo permiso de la ruta | Ponerlo al pie de `ResultadoDelCalculo` si se quiere por cálculo (la ruta tendría que filtrar por n.º) |
| PI-4 | ¿Dónde va «Mejora de la estimación»? | Como **sección al pie de «Riesgo de la obra»** (no una ruta nueva del menú): un `h2` y su texto. Se muestra **aunque no haya obra abierta**: la mejora no lee la obra ni la base (`POST /v1/riesgo/mejora` es cuenta pura). Sin ruta nueva, `shell/rutas.ts` y `scripts/recorrido_funcional.toml` no cambian (la fila «riesgo» sigue abriendo la pantalla) | Pasarla a una pestaña o a una ruta propia en `shell/rutas.ts` |
| PI-5 | ¿Cómo se precarga la estimación de Sílice? | Con el **P50 de la última proyección, redondeado a centésimas** como se lee en pantalla (159.666,1091212 → «159.666,11»), con la ayuda «Viene con el P50 de la proyección de V-002 (USD); puede cambiarla.». Si la persona la cambia, queda lo que escribió hasta que haya una proyección nueva, que vuelve a precargar. Sin proyección, el campo empieza vacío. El P50 exacto daría el mismo error en la mayoría de los casos; con centésimas lo que se ve es lo que se manda | Precargar el exacto con `textoParaEscribir` (campo con siete decimales) |
| PI-6 | Coma decimal y lo que viaja a la API | Las tres cifras se leen con `leerCifra` (coma decimal, punto de miles; «2.5» se rechaza junto al campo y no se envía) y viajan **con punto** (fila 90): «141.700,50» → `"141700.50"`. Los errores y la mejora llegan con punto y se escriben con `formatoEsVe`: «11,44 %», «0,21 %», «11,23 puntos» | — |
| PI-7 | Mejora negativa | Se muestra con su signo («-3,50 puntos») y una frase: «La estimación de Sílice se alejó más del costo real que el presupuesto original: la mejora es negativa.». Cero: «Las dos estimaciones se alejaron lo mismo del costo real.» | Cambiar el texto en `lecturaDeLaMejora` |
| PI-8 | ¿Qué pasa si se cambia una cifra después de calcular? | El resultado (y su botón de Excel) se retira: solo se muestra el que corresponde a las cifras que están en los campos, así el informe que se baja es siempre el de lo que se ve. El informe en Excel se pide con `GET /v1/riesgo/reportes/mejora` y las mismas tres cifras con punto | — |
| PI-9 | Monedas en la mejora | Como en T21-10: la pantalla dice que las tres cifras van en la misma moneda y a la misma fecha de precios, pero no lo comprueba (la API no recibe moneda). Con la precarga, la ayuda nombra la moneda de la proyección | Añadir `moneda` a la ruta y al informe |
| PI-10 | El error de la descarga del reporte de producción, ¿recibe el foco? | No: es el de `DescargaArchivo` (compartido), que devuelve el foco al botón y anuncia el error con `role="alert"` y el texto del servidor. El error de **calcular la mejora** sí recibe el foco (caja con `tabIndex=-1`, como en el resto de «Riesgo de la obra») | Llevar el foco al aviso en `DescargaArchivo` (afecta a todas las descargas) |
| PI-11 | MENOR 2 del árbitro de la fase D | `test_api_modulos.py`: con vial apagado, `GET /v1/vial/reportes/{computos,apu,resumen}` responde 404 con «El módulo vial está apagado en esta instalación.» y rita sigue con 403; con producción apagada, el reporte de producción responde 404 con el texto de producción (arma y administrador) aunque el período no tenga cálculos, y al encender vuelve su propio 404. La parte vial **entró en verde** (el módulo ya se exigía desde 8435b331); se comprobó que discrimina quitando `ModuloVial` de la ruta: falla con 200 en vez de 404 | — |
| PI-12 | El IVA del presupuesto en pantalla (T18-5) | **No se hace en esta rama.** Eugenio decidió mostrarlo en la sección Presupuesto del F4, y esa rama no está aquí. Queda para F4 | — |

## Para el CHANGELOG (no se escribió en `CHANGELOG.md`)

- Pantallas de los informes: «Costo por tonelada» baja el reporte de costo de producción del mes en Excel, ahora en `GET /v1/produccion/reportes/produccion` (con `registrar_costos_produccion` y el módulo producción; también lo baja el administrador; la ruta vieja bajo `/v1/vial` se quitó), y «Riesgo de la obra» suma «Mejora de la estimación»: tres cifras con coma decimal, la estimación de Sílice precargada con el P50, los dos errores y la mejora en puntos (negativa a la vista) y el informe en Excel. Decisiones en `docs/bitacora/2026-10-31-preguntas-pantallas-informes.md`.

## Lo que preocupa

- Un cliente externo que llamara `/v1/vial/reportes/produccion` recibiría 404 desde ahora (no se conoce ninguno).
- La precarga redondeada a centésimas puede mover el error de Sílice una centésima respecto del P50 exacto en casos de
  borde; se eligió que lo que se ve sea lo que se manda (PI-5).
- No se probó en el navegador (prohibido en esta tarea): el orquestador debería mirar la sección nueva al pie de
  «Riesgo de la obra» a 1366×768 y el botón en «Cálculos de {mes}».

## Commits y verificación

| Paso | Commit | Rojo / verde |
|---|---|---|
| Rutas (rojo) | e7f035bd | 12 fallan por aserción: `assert 404 == 200` (la ruta nueva no existía), `{'detail': 'Not Found'} == {'detalle': 'El módulo producción está apagado…'}`, la tabla de acceso con una ruta de más; las de vial apagado entran en verde (PI-11) |
| Rutas (verde) | 6aa5145c | 297 de 297 en reportes de producción y viales, módulos, acceso por ruta, punta a punta y OpenAPI; el oráculo de la prueba nueva sumó `AGR-34` a 5 (el cálculo del fixture lo trae) |
| Front (rojo) | 6d795da4 | 11 fallan con `expected null not to be null` (la sección y el botón aún no existían) |
| Front (verde) | 465c0296 | Vitest de `produccion`, `riesgo` y `shell`: 384 de 384 (30 archivos); `npm run lint` (eslint y `tsc -b`) limpio |

Verificación final, con `OPENPYXL_LXML=False`: las pruebas nuevas, `test_vial_extremo_a_extremo.py`,
`test_api_acceso_por_ruta.py`, `test_arquitectura*.py`, `test_api_modulos.py`, `test_api_reportes_*.py`,
`test_openapi.py` y `test_experimento_congelado_vigente.py`: **814 de 814** en 443 s. `ruff check .` limpio.
`docs/api.json` regenerado. `git diff --stat c1f436b2 -- core/` vacío. No se tocaron `aplicacion/hoja.py`,
`composicion.py` ni `asistente/experimento`.
