# Guion de demostración — Sílice (Plan B: prototipo con límites declarados sobre datos ficticios)

> Borrador preparado por Gemini 4 Neon (solo lectura) y revisado por Claude el 2026-11-23: se comprobaron contra el código las órdenes de arranque (`start.py --reiniciar-demo`, `--puerto`) y los rótulos de pantalla que usa. Las cifras en vivo (totales, causas agrupadas, P50/P80) se anotan en el ensayo previo.

> **Propósito:** guion de **10 a 12 minutos** para la defensa del Trabajo Especial de Grado (Eugenio y Nicolaz) si no se dispone de libros reales ni evaluación con usuarios a tiempo. Todo lo mostrado usa **datos ficticios construidos** (`NORMAS.md` §1) y separa explícitamente lo **verificado** en el software de lo **pendiente de validación** con personas.
>
> **Notas de trazabilidad (lectura estática del repositorio, sin ejecutar comandos):**
> - Las rutas usan `HashRouter` bajo `http://127.0.0.1:8501/app/` (`start.py`, `frontend-desktop/src/App.tsx`). En las rutas de obra `#/obra/<carpeta>/<obraId>/...`, `<obraId>` es el entero asignado por SQLite; en vivo se entra haciendo clic en el nombre de la obra en la barra lateral, no tecleando la URL.
> - **Asistente de IA en la interfaz:** hoy **no existe** ventana ni botón de chat del asistente de IA en la interfaz de React (`docs/manual_usuario.md` §13). Solo existe su configuración para quien administra en `#/cuenta/sistema`, bloque «Asistente de IA» (apagado por defecto). No se simula ningún chat inexistente.
> - **Cifras exactas en ejecución:** como este guion se redactó sin ejecutar el sistema, los totales calculados en vivo de `OBRA-GENERADA` y el conteo exacto de causas agrupadas al exportar `libro_ficticio_con_errores.xlsx` se verifican durante el ensayo previo (ver lista de comprobación).

---

## 1. Guion por bloques (11 minutos objetivo · rango 10–12 min)

### Bloque 1 — Arranque y obra de demostración (0:00 – 2:00)

| Minuto | Pantalla (ruta) | Qué se hace (ratón / teclado) | Qué se dice (1–2 frases) | Límite declarado |
|---|---|---|---|---|
| 0:00 – 0:45 | Consola local → Navegador (`http://127.0.0.1:8501/app/#/inicio/general`, «Vista general») | Mostrar la consola donde ya arrancó `uv run start.py` (un solo proceso Uvicorn en `127.0.0.1:8501`, sirviendo API y React en `/app/`). En el navegador (sesión ya iniciada con cuenta `administrador + arma`), señalar en la barra superior la carpeta activa y la marca «Demostración». | «Sílice corre de forma local en un solo proceso, sin salir a internet y sin guardar datos en la nube. Para esta defensa usamos las carpetas didácticas sembradas por `start.py`: todos los nombres, cantidades y precios son ficticios.» | Ningún dato proviene de una obra real; la demostración valida funcionamiento técnico del prototipo, no adopción en empresa. |
| 0:45 – 1:30 | «Carpetas» (`#/cuenta/carpetas`) → «Vista general» (`#/inicio/general`) | Abrir Cuenta (arriba a la derecha) → «Carpetas» solo si hace falta conmutar a la carpeta de demostración (`demo.db` u `obra_control.db`); volver al logo «Sílice» (`#/inicio/general`). Recorrer con el cursor «Lo que requiere atención», «Cartera por moneda» (Bs y USD nunca se mezclan) y «Obras y avance contra el plan». | «La aplicación separa estrictamente la carpeta de la empresa de las carpetas de demostración y nunca mezcla bolívares con dólares. Desde la Vista general entramos a cualquier obra con un clic o con el buscador `Ctrl+K`.» | Las cifras de avance y cartera mostradas aquí corresponden a los casos sintéticos (`demo`, `of001`, `ti001`, `s1` y `obra_control`). |
| 1:30 – 2:00 | «Resumen de la obra» (`#/obra/demo.db/<obraId>/resumen`) | En la barra lateral, zona «Obras», hacer clic en la obra didáctica (`DEMO-001` / línea de agua potable, sembrada en `demo.db`). Mostrar la cabecera de la obra (estado, versión, moneda, lista para armar) y la barra de secciones horizontal. | «Cada obra concentra en una sola barra su Presupuesto, Versiones, Aprobaciones, Mercado, Control y Riesgo. Todo está versionado e inmutable: cada guardado crea una nueva versión sellada.» | La línea base civil y el caso `DEMO-001` son ejercicios académicos ficticios que reproducen la estructura venezolana de APU (`NORMAS.md` §1). |

---

### Bloque 2 — Componer un APU y verlo en el presupuesto (2:00 – 4:30)

| Minuto | Pantalla (ruta) | Qué se hace (ratón / teclado) | Qué se dice (1–2 frases) | Límite declarado |
|---|---|---|---|---|
| 2:00 – 3:15 | «Presupuesto» → vista «Componer» (`#/obra/demo.db/<obraId>/presupuesto/componer`) | Hacer clic en «Presupuesto» en la barra de la obra y cambiar el conmutador superior de «Presupuesto» a «Componer». Escribir un código nuevo (p. ej. `ENSAYO-01`), descripción, unidad (`m`), rendimiento (`50`) y «Condiciones del rendimiento» (obligatorio). Mostrar «Partidas similares del catálogo» y buscar un insumo en referencia MaPreX o pulsar «Agregar fila»: poner un material con «Consumo por unidad» y «Desperdicio (%)» (p. ej. `5`), un equipo con depreciación y mano de obra (señalar opción «Modalidad» a jornal o a destajo). Observar «Desglose en vivo» y pulsar «Guardar composición». | «El principio central es separar propuesta de cálculo: las referencias, las partidas similares y el módulo de IA solo proponen entradas; el precio unitario lo calcula exclusivamente el núcleo determinista en aritmética `Decimal` exacta, aplicando administración y utilidad en cascada y nunca dividiendo materiales entre el rendimiento.» | **Límite de interfaz IA:** el panel conversacional del asistente de IA aún no está implementado en React (`manual_usuario.md` §13; solo existe su configuración en `#/cuenta/sistema`, apagado por defecto). Además, la modalidad a destajo (decisión D9) está pendiente de ratificación formal del tutor. |
| 3:15 – 4:00 | «Presupuesto» → pestaña «Partidas» (`#/obra/demo.db/<obraId>/presupuesto`) | Cambiar el conmutador a «Presupuesto». Pulsar «Agregar partida», buscar `ENSAYO-01` en «Partida», escribir «Cantidad» con coma decimal (p. ej. `25,5`) y «Cálculo (opcional)» (`5,1*5`), pulsar «Agregar al presupuesto». Hacer clic en el código de la partida recién agregada para abrir el panel lateral del APU y señalar al pie «Subtotal», «IVA (16 %)» y «Total con IVA». | «Al agregar la partida, el total y el IVA al 16 % —siempre fuera del APU— se recalculan desde el servidor con coma decimal y punto de miles. La interfaz jamás calcula dinero por su cuenta.» | El IVA al 16 % está fijado como alícuota general (a cotejar/parametrizar si cambia el régimen fiscal). |
| 4:00 – 4:30 | «Presupuesto» → pestaña «Revisión» (`#/obra/demo.db/<obraId>/presupuesto`) | Hacer clic en la pestaña «Revisión» (y señalar el botón «Guardar versión…» en la franja superior sin necesidad de guardar, o guardando con una fuente breve). | «El informe de auditoría interna (reglas R1–R7 y las reglas del dominio) se genera siempre de forma automática, sin que el usuario lo pida, y bloquea el envío a aprobación si hay hallazgos críticos o de error.» | La verificación interna prueba coherencia matemática y documental; no reemplaza el juicio ingenieril sobre precios de mercado. |

---

### Bloque 3 — Auditar el libro ficticio con errores y medición por causa raíz (4:30 – 7:30)

| Minuto | Pantalla (ruta) | Qué se hace (ratón / teclado) | Qué se dice (1–2 frases) | Límite declarado |
|---|---|---|---|---|
| 4:30 – 5:15 | «Inicio de auditoría» (`#/auditoria/subir`) | En la barra lateral, grupo «Costos y producción», hacer clic en «Auditar un presupuesto». Soltar el archivo `libro_ficticio_con_errores.xlsx` (generado antes fuera del repositorio) en «Suelte aquí el libro .xlsx del presupuesto, o haga clic para elegirlo» y pulsar «Auditar por mi cuenta». | «Para demostrar la auditoría sin exponer datos confidenciales de ninguna empresa, usamos un libro ficticio generado por `libro_ficticio_con_errores.py` con 12 errores sembrados que cubren las reglas F1, L1, L3 a L7 y L9. El archivo Excel no se guarda en la base de datos: solo se registran su huella SHA-256, el resumen y los hallazgos.» | Son errores sintéticos sembrados sobre una plantilla controlada; no miden todavía la variabilidad de libros reales de múltiples empresas. |
| 5:15 – 6:30 | «Libro de la empresa» (`#/auditoria/libros`) | En el visor: (1) señalar los tres indicadores superiores («Subtotal sin IVA», «IVA», «Total general») con semántica IBCS favorable/desfavorable y nota «Libro menor» si aplica; (2) filtrar en «Hallazgos (n)» por «Crítico» / «Error» y hacer clic en 3 hallazgos representativos para saltar directo a sus celdas en la réplica visual (Univer): `PRESUPUESTO!P5` (F1, P.U. en `999,99`), `CRONOGRAMA!D4` (L1, fila fija equivocada) y `APU-02!G36` (L4, costo directo sin equipos) o `RESUMEN!B13` (L5, `#REF!`); (3) señalar «Descargar PDF» (informe de devolución con SHA-256). | «Sílice recalcula el libro completo con el mismo motor determinista y marca sobre la réplica visual exactamente qué celda falla y cuánto impacta. Un error de fila fija en el cronograma o un costo directo que omite equipos queda señalado con su regla y su severidad.» | La lectura del libro aplica topes de seguridad (20.000 filas, 100 columnas y 4.000.000 de celdas por libro) y rechaza libros con macros (`.xlsm`). |
| 6:30 – 7:30 | Terminal / planilla de medición (`scripts/medir_auditoria_libro.py`) | Cambiar a la terminal (o abrir la planilla `planilla.xlsx` y la salida de `calcular` generadas en la carpeta externa de ensayo). Mostrar: (1) cómo `exportar` agrupa los hallazgos por **causa raíz** (misma regla y primera cláusula, con columna «Ocurrencias» y todas las celdas afectadas); (2) la tabla Markdown agregada que imprime `calcular` (Precisión, Detección de lo sembrado, Exhaustividad aproximada y Kappa de Cohen) sin filtrar celdas ni descripciones. | «Para la metodología de la tesis medimos por causa raíz y no por síntoma repetido, evitando inflar artificialmente la precisión cuando una misma fórmula se copia en muchas filas. El script produce únicamente métricas agregadas aptas para el informe, manteniendo los libros y planillas fuera del repositorio.» | **Límites del protocolo (`2026-11-23-protocolo-medicion-auditoria.md`):** la exhaustividad es aproximada (nadie conoce todos los errores ocultos), la detección depende del catálogo de siembra, y el **kappa de Cohen** requiere dos evaluadores humanos independientes aún no ejecutados. |

---

### Bloque 4 — Riesgo de precios (P50 / P80) en la obra de demostración (7:30 – 9:30)

| Minuto | Pantalla (ruta) | Qué se hace (ratón / teclado) | Qué se dice (1–2 frases) | Límite declarado |
|---|---|---|---|---|
| 7:30 – 8:15 | «Riesgo de la obra» (`#/obra/obra_control.db/<obraId>/riesgo`) | En la barra lateral, hacer clic en `OBRA-GENERADA` (carpeta `obra_control.db`, en USD) y luego en la sección «Riesgo» de la barra de la obra. Verificar «Versión» (`GEN-001`) y «Parámetros comunes» (`Meses del plazo`: `6`, `Semilla`: `1`, `Meses de historia`: `36`; `Trayectorias`: `2.000`). En «Serie que mueve cada insumo», elegir «PPI de asfalto de EE. UU. WPU05810212…» para «Cemento asfáltico CA-30 (ficticio)» y «Gasoil, precio administrado…» para «Gasoil para equipos (ficticio)». | «El módulo de Riesgo estima cuánto puede subir el presupuesto si los insumos se mueven como en su historia mensual reciente, usando simulación determinista con semilla fija para que el cálculo sea reproducible.» | **Carácter exploratorio:** sin series históricas reales y completas, los montos no son predictivos. En la demo la tasa y las dos series viales son **ficticias** (corridas hasta el mes anterior); además, no existe serie pública venezolana de asfalto (se usa el PPI de EE. UU. solo por su variación mensual) y el gasoil es una serie en escalones a cotejar en Gaceta. |
| 8:15 – 9:30 | «Riesgo de la obra» (`#/obra/obra_control.db/<obraId>/riesgo`) | Pulsar «Proyectar». Leer «Total base», «P50», «P80», «Reserva para cubrir el P80» y la tabla «Los tres insumos que más empujan». Desplegar «Supuestos de la proyección» y señalar el botón «Descargar el informe de riesgo» y la sección «Comprobar hacia atrás» (explicar sin esperar 30 s en vivo, o mostrar captura previa). | «Aquí vemos el P50, el P80, la reserva sugerida y los tres insumos que más empujan el riesgo; los supuestos quedan visibles junto al resultado. En una obra en USD, todo insumo sin serie asignada queda fijo, y la comprobación hacia atrás reporta cobertura como indicador histórico, nunca como probabilidad garantizada.» | En la obra de demo la reserva es deliberadamente pequeña (~74 USD, `docs/ESTADO.md` §5.9) para no desequilibrar Control de obra. Sin series reales de todos los insumos críticos, el módulo se presenta como **prototipo exploratorio**. |

---

### Bloque 5 — Cierre: verificación lograda vs. validación pendiente (9:30 – 11:00)

| Minuto | Pantalla (ruta) | Qué se hace (ratón / teclado) | Qué se dice (1–2 frases) | Límite declarado |
|---|---|---|---|---|
| 9:30 – 10:15 | «Ayuda y acerca de Sílice» (`#/cuenta/ayuda`) o lámina de cierre | Abrir Cuenta → «Ayuda y acerca de Sílice» (muestra versión, estado de bases de datos y módulos) o proyectar una sola tabla resumen de verificación vs. validación. | «Lo que está **verificado** de forma automatizada y reproducible en Linux y Windows (con `-W error` y 0 pruebas omitidas) es la arquitectura y el cálculo: núcleo cerrado intacto al agregar dominios (`git diff --stat core/` vacío y guardia en CI), exactitud `Decimal` en los 5 APU de línea base (± 0,01), detección 7 de 7 en auditoría base, cobertura de `core/` ≥ 80 % y desempeño medido (1,17 s para 100 partidas en RNF-03; 0,125 s de mediana en 500 puntos en RNF-11).» | Las cifras de la suite (tomarlas de la última corrida de CI antes de la defensa; la de #140, el 2026-11-23, dio 13.745 pruebas de Python en verde; cobertura en `docs/plan_pruebas.md` §10) verifican el software contra oráculos construidos, no la validez externa en campo. |
| 10:15 – 11:00 | Misma lámina de cierre | Cerrar enumerando explícitamente lo que **no** está validado aún y queda como límite declarado del Plan B. | «Lo que **no está validado** y declaramos abiertamente: la usabilidad con expertos y usuarios reales (RNF-04 en escala Likert y casos CP-07 a CP-11 de RNF-10/RNF-13), la medición de precisión y kappa de Cohen con dos evaluadores sobre libros reales, la calibración de Riesgo con series históricas reales completas y la compatibilidad IFC con modeladores BIM comerciales (RNF-09).» | También se declaran pendientes de decisión del tutor: el PR #100 (alias de unidades en `core/`), expedientes menores de `core/`, y la excepción de red del runtime WebView2 en RNF-08/RF-98 (`docs/ESTADO.md` §4). |

---

## 2. Lista de comprobación previa (preparar 30–60 min antes)

1. **Carpeta externa de ensayo (fuera del repositorio, `NORMAS.md` §1):** crear p. ej. `D:\defensa_ensayo\` para archivos generados, descargas y capturas; nunca guardar nada de esto dentro del repo.
2. **Interfaz compilada y demo limpia:**
   - Verificar que `frontend-desktop/dist/` esté compilado (`npm run build` si hubo cambios previos).
   - Reiniciar y arrancar la demo con `uv run start.py --reiniciar-demo` (siembra `demo`, `of001`, `ti001`, `s1` y `obra_control` con sus series viales ficticias corridas al mes anterior; escucha en `http://127.0.0.1:8501/app/`).
3. **Sesión y permisos listos:**
   - Si la instalación local no tenía cuentas, completar «Bienvenida a Sílice» con el código de instalación (`%LOCALAPPDATA%\Silice\datos\codigo_instalacion.txt`) marcando «Usaré esta cuenta también para armar presupuestos» (rol `administrador + arma`, que permite ver todas las pantallas de la demo).
   - Verificar en `#/cuenta/sistema` que el módulo «Riesgo» esté en «Encendida» (vienen encendidos por defecto).
   - En `#/cuenta/preferencias`, probar si en el proyector conviene «Grande» (125 %) para legibilidad del jurado.
4. **Libro ficticio y planilla de medición ya generados fuera del repo:**
   ```powershell
   uv run python scripts/libro_ficticio_con_errores.py --salida D:\defensa_ensayo
   uv run python scripts/medir_auditoria_libro.py exportar D:\defensa_ensayo\libro_ficticio_con_errores.xlsx --salida D:\defensa_ensayo\planilla.xlsx
   ```
   - Hacer una copia de `planilla.xlsx` con marcas de ensayo (o dejarla lista para mostrar la columna «Ocurrencias» y «Veredicto») y probar `medir_auditoria_libro.py calcular --planilla <marcada> --clave D:\defensa_ensayo\clave_ficticia.xlsx` para anotar la compactación exacta (hallazgos → causas) antes de entrar.
5. **Ensayo cronometrado completo (sin red):**
   - Cortar Wi-Fi durante el ensayo para comprobar operación 100 % local (recuerda: si el modelo de similitud no está cacheado con `scripts/descargar_modelo.py`, «Buscar parecidas» avisará «Las propuestas no están disponibles» sin romper la demo).
   - Verificar en `OBRA-GENERADA` → «Riesgo» que «Proyectar» devuelve P50, P80 y la tabla de insumos; opcionalmente correr «Comprobar hacia atrás» una vez para guardar captura (tarda ~30 s y no conviene esperarlo en vivo).
   - Confirmar que el navegador no muestre pestañas, rutas ni archivos con nombres de empresas reales.

---

## 3. Plan de respaldo si algo falla en vivo

**Regla de oro en defensa:** no depurar código ni reiniciar bases frente al jurado más de **20 segundos**. Si un paso se traba, pasar de inmediato a la captura de respaldo correspondiente y seguir el guion sin perder ritmo.

### Qué capturas y artefactos llevar preparados en `D:\defensa_ensayo\respaldo\`

| ID | Contenido de la captura / artefacto (100 % datos ficticios) | Bloque que cubre |
|---|---|---|
| `01_vista_general.png` | `#/inicio/general` con marca «Demostración», cartera por moneda y lista de obras en la barra lateral. | Bloque 1 |
| `02_componer_desglose.png` | `#/obra/demo.db/<id>/presupuesto/componer` con `ENSAYO-01`, desperdicio (`5 %`), modalidad y «Desglose en vivo». | Bloque 2 |
| `03_presupuesto_y_revision.png` | Pestaña «Partidas» con `ENSAYO-01`, panel lateral APU, IVA (16 %) y captura de pestaña «Revisión». | Bloque 2 |
| `04_visor_hallazgos.png` | `#/auditoria/libros` con `libro_ficticio_con_errores.xlsx` abierto, indicadores Fiori/IBCS y hallazgo seleccionado en Univer (`PRESUPUESTO!P5` / `APU-02!G36`). | Bloque 3 |
| `05_informe_devolucion.pdf` | PDF descargado con el botón «Descargar PDF» del Visor (con huella SHA-256). | Bloque 3 |
| `06_medicion_causa_raiz.png` | Planilla `planilla.xlsx` mostrando columna «Ocurrencias» + terminal con la tabla Markdown de `medir_auditoria_libro.py calcular`. | Bloque 3 |
| `07_riesgo_p50_p80.png` | `#/obra/obra_control.db/<id>/riesgo` tras «Proyectar» (Total base, P50, P80, Reserva, tres insumos y «Supuestos de la proyección»). | Bloque 4 |
| `08_riesgo_comprobacion.png` | Resultado de «Comprobar hacia atrás» (Cobertura y Cortes dentro del P80) para explicar sin esperar 30 s en vivo. | Bloque 4 |

### Contingencias rápidas

| Fallo en vivo | Acción inmediata |
|---|---|
| `start.py` no arranca o puerto 8501 ocupado | Reintentar una sola vez con `uv run start.py --puerto 8600`; si falla en 15 s, presentar con las capturas `01` a `08`. |
| Sesión vencida o pantalla congelada / error de carga | Pulsar `F5`; si pide login, entrar con la cuenta de ensayo. Si la obra avisa «Esta obra se abrió en otra pestaña», cerrar la otra pestaña y pulsar «Retomar». |
| Componer falla por falta de lista para armar | Verificar que se está en `demo.db` (ya trae lista); si no, pulsar «Crear la lista a partir de MaPreX» o pasar a `02_componer_desglose.png`. |
| El visor Univer tarda o no dibuja en el proyector | Mostrar `04_visor_hallazgos.png` y abrir `05_informe_devolucion.pdf`, y continuar en vivo con la terminal de `medir_auditoria_libro.py`. |
| Riesgo devuelve aviso de falta de historia o queda plano | Confirmar que se eligió `OBRA-GENERADA` (`obra_control.db`) y que se asignaron las dos series (asfalto y gasoil); si falla, pasar a `07_riesgo_p50_p80.png` y `08_riesgo_comprobacion.png`. |
