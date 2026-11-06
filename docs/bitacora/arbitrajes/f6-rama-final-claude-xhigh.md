# F6 · Rama entera · Árbitro final de Claude, esfuerzo xhigh (2026-11-05): APROBADO CON CONDICIONES

> Sustituye a Argon (sin cuota hasta ~2026-11-11), por decisión de Eugenio del 2026-11-05. Agente nuevo, sin las
> conclusiones del orquestador y sin leer los arbitrajes previos antes de juzgar. Diff `origin/main...HEAD` (base
> 076793b8, cabeza 59bdcd7f). Respuesta literal, salvo rutas absolutas del equipo; guardada por Claude.

**VEREDICTO: APROBADO CON CONDICIONES.** No hay nada bloqueante: `core/` está intacto, la división de permisos es correcta en `seguridad/`, `api/` y el front, y no encontré fugas entre carpetas. Antes de fusionar hay que corregir los dos hallazgos MAYOR, cada uno con su prueba en rojo primero, y poner al día ESTADO.md y el manual (MENOR 4). El resto puede ir después de la fusión.

**Verificado por mí**
- `git diff origin/main...HEAD -- core/`: salida vacía.
- `uv run --no-sync pytest -q -W error` sobre `test_api_obras_resumen_todas`, `test_permisos`, `test_api_acceso_por_ruta`, `test_api_casos`, `test_api_casos_empresa`, `test_api_obras_todas`, `test_api_eleccion`, `test_api_obras_pendientes_todas` y `test_api_proyectos_crear`: 472 puntos, «[100%] … [exited with code 0]». `test_openapi.py` también en verde.
- `npx vitest run --maxWorkers=1` sobre CabeceraCompacta, VistaGeneral, espacios, oferta, EspacioDeCuenta, salirConBorrador, sinRutasAMano, BarraLateral y MarcaDemostracion: «Test Files 9 passed (9) · Tests 252 passed (252)».
- Leí el diff completo de `seguridad/`, `api/` y `aplicacion/`, y del front: marco, hoja, inicio, pendientes, administración y shell.
- Revisé los pares rojo→verde de los 68 commits y conté los casos de prueba por archivo contra `main`: ningún archivo perdió casos.
- Calculé a mano el contraste del token nuevo `yellow-50` (#b28600): 3,03:1 sobre gris 10 y 3,33:1 sobre blanco, como dice DESIGN.md.
- No corrí el navegador: playwright no está en el venv y `dist` es de las 14:03, anterior a la cabecera compacta (16:40).

## Hallazgos

**[MAYOR] 1. Los enlaces de la Vista general a una obra de otra carpeta pierden sin preguntar el borrador de la Hoja.**
- **Dónde:** `frontend-desktop/src/paginas/inicio/CarteraYAvance.tsx:58` y `LoQueBloquea.tsx:84`.
- **Qué pasa:** son `<Link>` simples dentro de `#contenido`. `Marco.tsx:263` no intercepta los enlaces del contenido, y nada pasa por `irSeguro` (`Marco.tsx:242-254`), que es quien pregunta por las Hojas con cambios. La Bandeja sí pasa por ahí (`Marco.tsx:369`).
- **La cadena:** (1) al salir de la Hoja con cambios, el diálogo promete «Sus cambios quedan guardados para retomarlos al volver.» (`shell/DialogoSalida.tsx:16`); (2) ya en la Vista general, un clic en una obra de otra carpeta hace que `useObraDeLaRuta.ts:68-70` llame a `POST /v1/casos/actual`; (3) eso llega a `caso_web.fijar`, que ejecuta `hoja_borradores.olvidar(huella)` (`api/caso_web.py:37-40`); (4) el trabajo sin guardar se pierde en silencio.
- **Por qué importa:** viola DESIGN.md «Salir sin perder trabajo». Es una regresión de T8: en `main` se entraba por la Bandeja, que sí pregunta.
- **Corrección:** en `alClicAntes`, interceptar también los enlaces del contenido cuando `carpetaDelDestino(destino)` es distinta de `carpetaActual`, o dar `irSeguro` a la Vista general. **Prueba:** en `Marco.test`, «con un borrador con cambios, el enlace de la Vista general a una obra de otra carpeta pregunta y "Quedarme" no cambia de carpeta».
- **Cómo lo comprobé:** leyendo el código de punta a punta. No lo reproduje en el navegador.

**[MAYOR] 2. La cartera de la Vista general suma las obras inventadas de la demostración.**
- **Dónde:** `api/rutas/obras.py:311` lista todo `listar_casos()`, sin filtro, y `aplicacion/resumen_todas.py:94-122` no excluye `demostracion.db`. `aplicacion/casos.py:225` ya trae `es_demostracion()`.
- **Qué pasa:** en cuanto se estrena la demostración, «Total vigente», «Obras» y «En ejecución» mezclan las obras de la empresa con datos inventados, y la tabla de avance las muestra sin marca.
- **Por qué importa:** es una cifra de portada inventada y contradice la regla de marcar siempre la demostración.
- **Corrección:** excluir la demostración de la cartera, salvo que la sesión esté en ella, o mostrarla aparte con su marca. **Decisión de Eugenio.** **Prueba:** un caso con `demostracion.db` en `test_api_obras_resumen_todas.py`.

**[MENOR] 3. «Total vigente» no siempre es el total de la versión vigente.** `ObraEnMesa.total` es el de la línea base cuando existe (`aplicacion/mesa.py:357-359,374`); `api/rutas/obras.py:425`, `textos.ts:24` y `api/tipos.ts` dicen «vigente». Corrección: rotular «de la línea base o, sin ella, de la vigente» y añadir ese caso a la prueba.

**[MENOR] 4. Documentos que contradicen el código.** `docs/ESTADO.md:27` («Diseño en curso») y `:52-54` (pregunta ya respondida); `PLAN_REDISENO_F6.md:280` («Quien revisa sigue viendo solo la carpeta abierta»); el CHANGELOG no menciona `abrir_carpeta` ni la cabecera compacta; `docs/manual_usuario.md:456-462`, `DESIGN.md:286` y el comentario de `paginas/hoja/index.tsx:30` describen el orden viejo de la cabecera.

**[MENOR] 5. Tres oráculos se cambiaron en el commit verde.** `4951c8e1` (`within(franja)` → `franja.parentElement`), `9ef3ddd3` (texto esperado de VistaGeneral) y `dbff51ac` (la prueba de foco pasó de Presupuesto→Resumen a Mercado→Control; esconde que al entrar o salir de una sección con Hoja se vuelven a montar la cabecera y la barra, `EspacioDeObra.tsx:207-217`, y el foco salta al h1).

**[MENOR] 6. La regla de redondear cada obra antes de sumar no tiene prueba** (`resumen_todas.py:11-13`, `:74-88`). Falta un caso como 1,005 + 1,005 = 2,02.

**[MENOR] 7. Dos enlaces dentro de la obra usan la dirección corta**: `paginas/aprobar/EntregaDeLaObra.tsx:22` («/entregar») y `paginas/vial/Tramos.tsx:152` («/hoja»); redirigen y vuelven a montar `EspacioDeObra` dos veces. Sospecha sin probar: el foco queda en el cuerpo.

**[MENOR] 8. Cuatro redirecciones pierden la consulta**: `Marco.tsx:361` (índice), `:423` (`*`), `:441` (`PantallaDeRuta` sin pantalla) y `:467` (entrada de Empresa desconocida).

**[MENOR] 9. Código repetido y restos.** `resumen_todas.py:94-117` copia el bucle de `pendientes_todas.py:85-104`; `_EN_CURSO` (`resumen_todas.py:45`) repite `mesa.py:93`; `oferta.sueltas` siempre va vacío y `busqueda.ts:60` aún lo lee; `scripts/recorrido_ux_playwright.py:1735` decide con `cambiar_caso`; su modo `--umbrales` usa `#silice-sidebar` y `MODULOS`; comentarios viejos en `tests/unit/test_api_proyectos_crear.py:484` y `CarpetasDeTrabajo.tsx:5`.

**[MENOR] 10.** El h1 de los avisos «Sin permiso» y «Apagada» usa `cds--type-heading-compact-01` (`comun/EstadoVacio.tsx:17`), no el `heading-04` de los demás h1.

## Lo que pidió mirar el orquestador (sospechas, sin navegador)
- **Columna cortada «E…» a 1366 px:** es «Estado», la penúltima, cortada en el borde de la caja que se desplaza (`hoja.scss:144-170`); la barra de desplazamiento queda al pie, fuera de la primera vista. Probablemente ya pasaba en `main`. Propuesta: poner «Estado» junto a «Partida» o fijar la última columna.
- **Primera partida a ~1.242 px con Muy grande:** no rompe ninguna regla escrita; la medición con Muy grande que pide T5 (`PLAN_REDISENO_F6.md:189`) sigue pendiente.

## Áreas que están bien
Permisos (`abrir_carpeta` en `POST`/`DELETE /v1/casos/actual`, crear y subir en `cambiar_caso`); seguridad (CSRF y `Origin`, carpeta por sesión, la clave de API solo ve la del proceso); cifras (Bs y USD nunca se suman); rutas (sin bucles ni pantallas en blanco); código muerto retirado (ZonaEmpresa, Migas, ABSORBIDAS, `rutaDeEmpresa`, `tomarVueltaACarpetas`); accesibilidad; 14 afirmaciones de documentos comprobadas, correctas salvo las del MENOR 4.

## Comparación con los arbitrajes anteriores
La miró al final: los arbitrajes de T7 y T8 no mencionan ninguno de los dos MAYOR.
