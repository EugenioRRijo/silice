# AREN.IA — recorrido guiado de la interfaz · diseño

**Fecha:** 2026-09-23 · **Rama:** `inc/PLAN-ui` (worktree `.claude/worktrees/ui`) · **Base:**
`inc/PLAN-prototipo` (`a478cfc`), porque `main` todavía no tiene la pantalla de composición
**Plan que lo ejecuta:** `PLAN_UI.md` (fases U0 a U3, tres compuertas) — aún no escrito
**Depende de:** la fusión del PR #7 a `main`, previa auditoría (sección 8)
**Revisado por cuatro encargos de ingeniería de sistemas** el 2026-09-23 (requisitos, arquitectura,
pruebas y calidad, verificación factual). Los ocho hallazgos bloqueantes están aplicados; la
sección 10 deja constancia de qué cambió y por qué.

> **Enmienda de la spec de cierre (2026‑09‑23, anotada en la fase C4 del cierre, 2026‑09‑28).** La
> [spec de cierre §5](2026-09-23-plan-cierre-tesis-design.md) enmendó este diseño en dos puntos, y
> donde el texto de abajo diga otra cosa, manda la enmienda: (1) la compuerta **GU1** se partió en
> **GU1a** (U1 completa sin CP‑07; cruzada el 2026‑09‑28 con la CI en verde, PR #14) y **GU1b**
> (CP‑07 ejecutado y registrado, en la fase Med); (2) U1 se ejecutó dentro de la fase C3 del cierre,
> que autorizó **dos** commits de `core/` (INV‑080 e INV‑015 7a), de modo que «`core/` sin cambios»
> vale para todo U1 salvo esos dos. Detalle: [bitácora del cierre](../../bitacora/2026-09-23-cierre.md).

El prototipo sabe hacer su trabajo y no sabe explicarlo. Este diseño no agrega capacidades: agrega
**orientación**. La frase que lo origina es de Eugenio, 2026‑09‑22: «no sé qué hacer y no hay un
camino para llevar al usuario de la mano».

---

## 1. Por qué existe

Al cerrar el sprint del prototipo, la interfaz tiene nueve pantallas que funcionan y ninguna puerta
de entrada. El problema no es estético ni de interacción — nadie se pierde *dentro* de la pantalla
de composición; se pierde *antes de llegar a ella*. Son seis defectos de orientación, todos
verificados en el código:

| # | Defecto | Evidencia |
|---|---|---|
| D‑1 | **La pantalla inicial es la peor posible.** `default=indice == 0` sobre una tupla ordenada alfabéticamente abre la aplicación en *Actualización de precios*, una carga masiva de listas: lo último que hace un usuario nuevo | `ui/app.py:91-101`, `ui/app.py:127` |
| D‑2 | **El archivo de la base se pide en cada pantalla por separado.** El usuario debe saber qué es `data/apu.db` y repetirlo en **ocho de las nueve** pantallas (cinco en modo entrega); solo el visor 3D no lo pide. Nada garantiza que las ocho apunten al mismo sitio | `actualizacion.py:108`, `catalogo.py:32`, `componer.py:109`, `elaborar.py:99`, `escenarios.py:57`, `historico.py:37`, `similares.py:69`, `simulador.py:51`. La constante `RUTA_BASE_POR_DEFECTO` está definida **ocho** veces |
| D‑3 | **El estado vacío no existe, y la única siembra que hay está escondida.** *Actualización de precios* tiene un botón «Sembrar la linea base» en la barra lateral que no explica qué siembra; **ninguna pantalla ofrece el caso de demostración** (`scripts/seed_demo.py`), y ninguna reacciona a una base vacía diciendo qué pasa | `ui/paginas/actualizacion.py:44`, `:109-110`, `:133-142`; `scripts/seed_demo.py` sin llamador en `ui/` |
| D‑4 | **Los títulos son vocabulario de tesis.** «UC‑01», «UC‑02», «UC‑10 / UC‑11» gobiernan el menú. Fuera del tribunal, nadie sabe qué es UC‑10 | `ui/app.py:92-100` (los códigos, en 92, 94, 95, 96 y 98) |
| D‑5 | **Ninguna pantalla indica el paso siguiente.** Ni `st.page_link` ni `st.switch_page` aparecen en ningún módulo de `ui/paginas/` | las nueve `render()` |
| D‑6 | **El orden del menú es arbitrario.** Alfabético por nombre de módulo, no el del trabajo real: catálogo → componer → elaborar → auditar → exportar | `ui/app.py:91-101` |

### El defecto de fondo: el modo entrega está al revés

`ARENIA_MODO_ENTREGA=1` **oculta** escenarios, partidas similares, simulador y visor 3D
(`ui/app.py:25-31`, `:104-119`). Se diseñó pensando en la empresa que recibe el prototipo. Pero el
público objetivo declarado por Eugenio (2026‑09‑22) es **el tribunal y el tutor**, y para ellos esas
cuatro pantallas *son* la tesis: I2 (normalización), I6.1 (anomalías), UC‑08 (escenarios) y la
extracción IFC. Esconderlas esconde la investigación.

### Lo que este trabajo aporta a la tesis, y lo que no

`docs/calidad_iso25010.md` §4: la usabilidad es la **única característica de ISO/IEC 25010 sin
medición alguna** del proyecto (la compatibilidad, RNF‑09, queda *parcial* por una brecha declarada
en G1, y no es objeto de este trabajo).

**Lo que este sprint NO hace:** cerrar RNF‑04. `docs/ERS.md:469` lo define como «**el informe de
auditoría** se entiende sin formación previa», medido con «juicio de expertos (Likert)» sobre una
población de «3–5 profesionales de costos u obra» (`docs/dossier_g0.md:197-200`). Sus ocho ítems
preguntan por la severidad de los hallazgos, el impacto cuantificado, los `origen_id` y el orden del
informe. **Ninguno pregunta si la persona supo por dónde empezar**, y siete de los ocho son
incontestables por alguien que no llegó al informe — que es exactamente el resultado que este sprint
necesita poder registrar.

**Lo que este sprint SÍ hace:** declarar y medir un requisito nuevo, **RNF‑10 — capacidad de
aprendizaje de la interfaz**, con su propio instrumento (bloque B del anexo A, sección 5). RNF‑04
**sigue pendiente**, sin tocar, para la Fase 6 con el tutor. Decisión de Eugenio, 2026‑09‑23, sobre
la recomendación coincidente de tres revisores.

### Fuente de los requisitos

La queja de Eugenio (2026‑09‑22) y dos pendientes que el propio sprint del prototipo dejó escritos
en su bitácora de cierre (`docs/bitacora/2026-09-16-sprint-prototipo.md:183`, `:190-191`):
«ejecutar el guion manual con una persona» y «abrir la aplicación en modo entrega en un navegador:
la Tarea 5 lo probó con pruebas unitarias del filtro, no en pantalla».

---

## 2. Alcance

**Entra.** Una pantalla de Inicio; el caso abierto compartido; el estado vacío con siembra desde la
interfaz; el vocabulario de los títulos; la agrupación y el orden del menú; el paso siguiente y el
indicador de caso abierto, pintados por el marco; los recorridos guiados como estructura de datos;
la prueba con persona.

**No entra.** Ninguna modificación a `core/`, `adapters/`, `ml/` ni `api/` (enmendado: la fase C3
del cierre autorizó dos commits de `core/`, INV‑080 e INV‑015 7a; ver la nota del encabezado). Ningún cambio al cálculo,
a la auditoría ni al Excel. Ninguna capacidad nueva: no se agrega nada que la aplicación no sepa
hacer hoy. El asistente con IA (UC‑09) es otro plan (`PLAN_ASISTENTE.md`) y no se toca.

### 2.1 Numeración: ocho requisitos y un caso de uso

Hay **34 RF asignados** (RF‑01…RF‑31 y RF‑33…RF‑35, `docs/ERS.md:460`); **RF‑32 es el único
vacante** y está reservado a UC‑09. Los requisitos de este trabajo son **RF‑36 a RF‑43**, ocho, y el
caso de uso es **UC‑12**. Verificado: ningún documento del repositorio reclama hoy RF‑36 ni UC‑12.

| RF | Enunciado |
|---|---|
| RF‑36 | La interfaz abrirá en la pantalla de Inicio, cualquiera que sea el orden del resto del menú |
| RF‑37 | Los recorridos guiados se declararán una sola vez, en un módulo sin Streamlit ni base de datos, y el destino de cada paso será la ruta de una página registrada |
| RF‑38 | El archivo de la base se fijará una vez por sesión y todas las pantallas operarán sobre ese mismo caso; ninguna pantalla distinta del Inicio pedirá la ruta |
| RF‑39 | El sistema mostrará en toda pantalla, en solo lectura, el caso abierto y su estado: existencia del archivo, número de partidas, número de insumos y si hay lista de precios vigente |
| RF‑40 | Cuando el caso abierto no exista o no contenga partidas, el Inicio lo declarará y ofrecerá cargar el caso de demostración, sin exponer nunca la opción de reiniciar la base |
| RF‑41 | Cada pantalla del recorrido activo mostrará su paso siguiente, tomado de la declaración única de recorridos; una pantalla que no pertenezca a ningún recorrido no lo mostrará |
| RF‑42 | El menú presentará cada pantalla con el nombre de su oficio, agrupada en dos secciones —Trabajo e Investigación— en el orden del trabajo real; el código del caso de uso permanecerá visible como subtítulo |
| RF‑43 | Con el modo entrega activo, ninguna pantalla de Trabajo quedará inaccesible |

**Deuda que este sprint destapa y debe declarar, no heredar.** `PLAN_ASISTENTE.md:71-73` instruye
«numera sus requisitos desde RF‑32» y necesita **seis**. Pero RF‑33 a RF‑35 ya se los llevó
UC‑10/UC‑11 en el sprint del prototipo: **la reserva ya estaba rota antes de este trabajo**. U0
enmienda la nota de `docs/ERS.md:16-18` y `:395-398` para que la reserva sea de **RF‑32 solamente**,
y que los demás RF de UC‑09 continúen desde el número libre más alto al ejecutar la Sesión A0.1.

---

## 3. Decisiones de diseño

### 3.1 Los recorridos son datos, no texto repartido por las pantallas

Un recorrido es una secuencia de pasos con un propósito. Se declara **una vez**, en un módulo sin
Streamlit (`ui/recorridos.py`), como `Recorrido(nombre, proposito, pasos)` con
`Paso(titulo, pagina, que_hacer, senal_de_exito)`.

De esa única definición salen cuatro consumidores: el Inicio que los pinta, el paso siguiente del
marco, el indicador de «dónde estás» y el guion de prueba manual. Escribir el camino cuatro veces
sería lo que el principio DRY de `CLAUDE.md` §2 prohíbe.

La consecuencia comprobable: **todo `paso.pagina` debe ser el `url_path` de una página registrada**.
Lo exige una prueba de integridad de enlaces, que compara contra `paginas_visibles(False)` —las
diez—, no contra las visibles en modo entrega, o el modo entrega volvería roja la suite.

Los tres recorridos:

| Recorrido | Para quién | Termina en |
|---|---|---|
| **Ver la demostración auditada** | tribunal, tutor, primer contacto | el informe con los hallazgos y el Excel descargado |
| **Armar un presupuesto** | presupuestista | su propio Excel auditado |
| **Actualizar precios** | quien mantiene el catálogo | el comparativo aceptado |

### 3.2 El caso abierto se elige una vez, y lo pinta el marco

`ui/caso.py` guarda la ruta en `st.session_state` y la exponen `ruta_caso()` y `fijar_caso()`. Las
pantallas dejan de tener su caja de texto; el indicador de solo lectura lo pinta el marco (3.3), de
modo que en toda pantalla se sabe sobre qué base se trabaja.

Esto liquida una duplicación que hoy está documentada como mal menor: el docstring de
`ui/app.py:18-23` explica que cada pantalla repite su `RUTA_BASE_POR_DEFECTO` para evitar el ciclo
que **aparecería si** una página importara la constante desde `ui.app`. Hoy ese ciclo **no existe**
—ninguna página importa `ui.app`—; es una prevención, y como tal hay que leerla. `ui/caso.py` la
resuelve sin crear ciclo nuevo: el grafo queda `ui.app → ui.paginas.* → ui.caso → core.catalog`,
acíclico.

*(Corrección de un dato heredado: el docstring de `ui/app.py:20` dice que la constante está «ya
repetida igual en `scripts/simular_lista.py`». Ese script no define ninguna constante; usa el
literal como `default=` de argparse, `scripts/simular_lista.py:86-87`. U0 lo corrige de paso.)*

**Tres invariantes que no se dejan a la implementación:**

1. **La clave de `session_state` es propia, no de widget.** Streamlit descarta las entradas de
   widgets que no se vuelven a montar (`should_preserve`, `runtime/state/session_state.py:456-462`):
   si `fijar_caso()` se apoyara en la clave del `text_input` del Inicio, el caso abierto **se
   olvidaría al navegar a otra pantalla**, justo al hacer lo que el diseño quiere habilitar. Además,
   escribir sobre una clave de widget lanza `StreamlitAPIException`.
2. **`ruta_caso()` tiene respaldo declarado.** `st.navigation` permite entrar por URL directamente a
   `/componer` sin pasar por el Inicio: el estado «no hay caso abierto» existe de verdad y devuelve
   `RUTA_BASE_POR_DEFECTO`, que `ui/caso.py` define **una sola vez** y deja sobreescribible por
   variable de entorno (para el guion manual y para GU1).
3. **El motor de SQLAlchemy NO va a `session_state`.** Se sigue creando por pantalla con su
   `try/finally: motor.dispose()`, como hoy (`ui/paginas/catalogo.py:34-47`). En Windows no se puede
   borrar el archivo con un motor abierto (`tests/unit/test_ui_componer.py:38-41`): un `Engine`
   compartido sería imposible de cerrar.

**La trampa que esto obliga a resolver.** `crear_esquema(motor)` sobre una ruta con una errata crea
una base vacía en silencio, y hoy el resultado se ve como tablas vacías sin explicación. Por eso
`estado_caso` resuelve «si existe» con `Path.exists()` **antes** de llamar a `crear_esquema`, y el
estado vacío de 3.5 convierte un fallo mudo en un mensaje con salida.

### 3.3 El paso siguiente lo pinta el marco, no las páginas

**Esta decisión corrige el diseño original, que era irrealizable.** `st.switch_page` y
`st.page_link` aceptan `str | Path | Page`, y con páginas definidas por callable —como son las
nueve (`ui/app.py:125-131`)— **hace falta el objeto `Page`**. Esos objetos solo existen dentro de
`main()`, por diseño deliberado que `tests/unit/test_ui_importable.py` vigila. Para que
`ui/paginas/componer.py` pintara «siguiente: elaborar» tendría que importar `ui.app`: el ciclo real,
y uno que `ui/caso.py` **no** puede romper, porque no nace de la constante sino del registro de
páginas.

La solución la da el propio Streamlit: el archivo de entrada de `st.navigation` es un marco —*«acts
like a router or frame of common elements around each of your pages»*— y `st.navigation(...)`
devuelve la página actual, con su `url_path` accesible. Así `main()` tiene a la vez los `Page`
construidos y el paso actual:

```
pagina_actual = st.navigation(secciones)
_pintar_caso_abierto()            # barra lateral, solo lectura
pagina_actual.run()
_pintar_paso_siguiente(pagina_actual.url_path)
```

Cero imports nuevos en las páginas, cero ciclo. `ui/app.py` pasa a tener dos papeles: enrutador y
marco común.

### 3.4 El vocabulario de la pantalla es el del oficio; el de la tesis baja a subtítulo

«Componer una partida», no «Componer partida (UC‑10 / UC‑11)». El código del caso de uso no
desaparece — baja a un `caption` bajo el título, porque la trazabilidad a la ERS es un requisito de
la tesis (`CLAUDE.md` §2, principio 6). Lo que cambia es quién manda: el menú lo gobierna el oficio,
no la numeración. Afecta a las cinco pantallas que hoy llevan código en el título; las otras cuatro
no tienen ninguno que bajar.

### 3.5 Se agrupa en dos secciones; el modo entrega sigue omitiendo, no colapsando

`st.navigation` acepta un diccionario de secciones desde la versión 1.36. El menú queda en dos:
**Trabajo** (inicio, catálogo, componer, elaborar, actualizar, histórico) e **Investigación**
(escenarios, similares, simulador, visor 3D).

**Corrección a la propuesta original:** las secciones **no se pueden colapsar** en la barra lateral.
Solo son colapsables con `position="top"` (`streamlit/commands/navigation.py:129-131`), y el
parámetro `expanded` es global, no por sección, e inoperante con doce páginas o menos. Por tanto
`ARENIA_MODO_ENTREGA` conserva su comportamiento —**omite** la sección Investigación del
diccionario— y lo que este sprint cambia es la agrupación, el orden y los nombres. Adoptar
`position="top"` cambiaría la navegación de toda la aplicación y subiría el mínimo de Streamlit
bastante más: queda descartado.

**La agrupación es función pura.** El discriminante `investigacion: bool` (`ui/app.py:79`) da dos
grupos y ningún nombre; pasa a `seccion: str`. Junto a `paginas_visibles`, y **fuera de `main()`**,
vive `secciones_visibles(modo_entrega) -> Mapping[str, tuple[DefinicionPagina, ...]]`: el `dict`
preserva el orden de inserción, así que el orden de secciones y el de cada sección quedan probados
sin Streamlit, como hoy. Cuidado con `default=indice == 0` (`ui/app.py:127`): con secciones el
índice se reinicia por sección y `st.navigation` lanza excepción si hay más de un `default=True`.
El `default` se marca **por identidad** (la página inicio), no por posición.

### 3.6 El estado vacío siembra, y no puede destruir

Si la base abierta no tiene partidas, el Inicio lo dice y ofrece cargar el caso de demostración. La
siembra ya existe y está probada (`scripts/seed_demo.py`, corregida en `617861b` para heredar los
precios de la lista anterior).

**Restricción de diseño, no criterio de degradación.** `scripts/seed_demo.py:462-491` —`main(argv)`—
imprime a stdout y, con `--reiniciar`, ejecuta `models.Base.metadata.drop_all(motor)`: **borra la
base entera**. Por tanto:

- el botón invoca la siembra **sin `--reiniciar`**, y el flag **no se expone nunca** en la interfaz;
- el botón solo se pinta cuando `estado_caso(ruta)` informa **cero partidas**: no puede sembrar
  encima de trabajo existente;
- una prueba unitaria afirma que `"--reiniciar"` no aparece en ningún `argv` construido por `ui/`;
- la siembra completa es lenta (línea base + demostración + presupuesto auditado): `st.spinner`, y
  el `default_timeout` de `AppTest` se sube por encima de los 60 s del arnés actual.

*(Se retira el criterio de degradación de la versión anterior de este documento, que decía que
`scripts/` no era importable. Es falso: `scripts/__init__.py` existe y la propia interfaz ya lo
importa —`ui/paginas/actualizacion.py:44`, `ui/paginas/simulador.py:22`—, además de catorce módulos
de `tests/`. Un riesgo inventado es peor que ninguno.)*

### 3.7 A, luego B, luego C — y cada compuerta decide si sigue

El orden aprobado por Eugenio (2026‑09‑23) es A → B → C. **Es una secuencia, no un compromiso de
ejecutar las tres.** Criterio observable, declarado antes de medir: **si CP‑07 resulta PASA, U2 no
se ejecuta**; se ejecuta si resulta FALLA, y su alcance lo fijan los puntos de detención
registrados. U3 requiere decisión expresa de Eugenio en cualquier caso.

La razón de que A vaya primero no es su tamaño: A construye el estado compartido (`ui/caso.py`), el
marco (3.3) y la estructura de recorridos sobre los que B se apoya. Un asistente de cinco pasos
escrito antes que el caso abierto tendría que inventárselo.

---

## 4. Arquitectura

Cuatro piezas. Cada una responde a las tres preguntas: qué hace, cómo se usa, de qué depende.

| Pieza | Qué hace | Depende de | Se prueba |
|---|---|---|---|
| `ui/recorridos.py` | Los tres recorridos como dataclasses inmutables. Sin Streamlit, sin base de datos | nada | unitaria pura |
| `ui/caso.py` | `ruta_caso()`, `fijar_caso()` sobre una clave propia de `session_state`; `estado_caso(ruta) -> EstadoCaso`; la única `RUTA_BASE_POR_DEFECTO` | `core.catalog`, `streamlit` | unitaria sobre bases temporales |
| `ui/paginas/inicio.py` | Solo pinta: estado del caso, los tres recorridos, el estado vacío con su siembra | `ui.caso`, `ui.recorridos` | `AppTest` |
| `ui/app.py` | Enrutador **y marco común**: secciones, orden, inicio por defecto, indicador de caso abierto, dónde estás y paso siguiente alrededor de `.run()` | `ui.caso`, `ui.recorridos` | unitaria de `secciones_visibles` + integridad de enlaces |

Reglas que la arquitectura debe respetar:

1. **`ui/` no *modifica* `core/`.** `git diff --stat core/` vacío durante todo U1 y guardia del
   núcleo en código 0 (enmendado: salvo los dos commits de `core/` que autorizó la fase C3 del
   cierre, INV‑080 e INV‑015 7a; nota del encabezado). *Importar* de `core` es legítimo y ya es el caso: `docs/arquitectura.md` §C4
   declara `ui --> core` como arista válida, y `ui/paginas/catalogo.py:19` ya la usa.
2. **La lógica verificable vive fuera de las páginas.** Es el patrón que el sprint anterior
   estableció con `ui/composicion.py`: las páginas pintan, los módulos hermanos deciden.
3. **Ningún módulo de `ui/` construye objetos de Streamlit al importarse.** Lo comprueba
   `tests/unit/test_ui_importable.py`, cuya lista está escrita a mano (`:4-17`) y por tanto **no
   cubriría los módulos nuevos**: U1 la deriva de `ui.app.PAGINAS` y añade `ui.caso` y
   `ui.recorridos` explícitamente.
4. **Una sola definición de presentación.** Los dos decimales siguen saliendo de
   `core.verification.informe.DECIMALES_PRESENTACION`.
5. **`ui/composicion.py` no puede importar `ui/caso.py`.** Metería Streamlit en el grafo de
   importación de la prueba de integración del núcleo. La meta P7 de `scripts/meta_prototipo.py` ya
   vigila que `ui/composicion.py` no importe `streamlit` ni `pandas`; sigue vigente.
6. **`scripts/seed_demo.py` no se mueve ni se renombra.** Dos pruebas importan de esa ruta exacta
   (`tests/integration/test_composicion_extremo_a_extremo.py:47`,
   `tests/unit/test_ui_componer.py:58`), una de ellas la regresión intocable.

---

## 5. Fundamento normativo

| Fuente | Qué aporta |
|---|---|
| **ISO/IEC 25010**, usabilidad | Las subcaracterísticas atacadas: *reconocibilidad de la adecuación* (D‑1, D‑4), *capacidad de aprendizaje* (D‑5, D‑6), *protección contra errores del usuario* (D‑2, D‑3) |
| **IEEE 830** | RF‑36 a RF‑43 y UC‑12, con la plantilla de `docs/ERS.md:391-392`: afirmación comprobable, prioridad, UC de origen, incremento y criterio de aceptación con su prueba |
| **IEEE 829** | CP‑07 se redacta **antes** de ejecutarlo, en el formato narrativo de `docs/guion_prueba_arenia.md` §6 — `docs/plan_pruebas.md` §8 es una matriz RF→prueba y no admite un caso narrativo |
| **Anexo A del dossier G0** | Se conserva **intacto**: es el instrumento de RNF‑04 y se aplica con 3–5 expertos sobre el informe. U0 le agrega un **bloque B** de recorrido, con promedio propio, que **nunca se promedia con el bloque A** |

**Bloque B — siete ítems Likert (1–5), uno por defecto vigilado:**

| # | Afirmación | Vigila |
|---|---|---|
| B1 | Al abrir la aplicación entendí para qué sirve y por dónde empezar | D‑1, D‑4 |
| B2 | Los nombres del menú me dijeron qué hace cada pantalla sin abrirlas | D‑4 |
| B3 | En todo momento supe sobre qué archivo de datos estaba trabajando | D‑2 |
| B4 | Cuando no había datos, la aplicación me dijo qué pasaba y cómo salir | D‑3 |
| B5 | Al terminar una pantalla supe cuál era el paso siguiente | D‑5 |
| B6 | El orden de las pantallas se parece al orden en que se hace el trabajo | D‑6 |
| B7 | Volvería a recorrer esto solo, sin que nadie me acompañara | global |

Más el campo abierto ya previsto y dos campos de registro nuevos: **tiempo total** y **número de
preguntas al observador**.

---

## 6. Pruebas y criterios de aceptación

| Nivel | Qué cubre |
|---|---|
| Unitaria pura | `estado_caso` sobre base inexistente, vacía y sembrada; los recorridos; `secciones_visibles`; **integridad de enlaces**: todo `paso.pagina` está en `{p.ruta_url for p in paginas_visibles(False)}`; que `"--reiniciar"` no aparece en ningún `argv` de `ui/` |
| `AppTest` | El Inicio pinta los tres recorridos; el estado vacío aparece con base vacía; la siembra deja la base utilizable; el indicador de caso abierto aparece **al pintar cada pantalla con el caso fijado** |
| **Se reescriben a propósito** | `tests/unit/test_ui_app.py`: `TITULOS_NUEVE`/`TITULOS_ARENIA` (`:16-34`), el orden alfabético (`:44-46`), «exactamente cinco / oculta cuatro» (`:49-57`), «nueve rutas» (`:88-91`) y el punto de parcheo de `_aplicacion` (`:80-85`). Cambian porque 3.4, 3.5 y la página nueva cambian el comportamiento **especificado**, no porque fallen. `tests/unit/test_ui_componer.py:101-108` migra su parcheo a `ui.caso`. **Sobrevive intacta la afirmación de que todas las rutas URL son únicas**: nació de un fallo real (`a478cfc`) |
| Regresión intocable | `tests/integration/test_composicion_extremo_a_extremo.py` sigue verde **sin editarlo**: importa `ui.composicion` —la capa pura—, no `ui.app` ni `ui/paginas/`, y afirma el total contra `tests/fixtures/apu_linea_base.py` en vez de escribirlo. 1 586,61 USD y 7 de 7 |
| Portabilidad | Suite verde en `ubuntu-latest` y `windows-latest` con `-W error --strict-markers`, sin `filterwarnings` ni marcadores nuevos |

### Salvaguarda de aislamiento — exigible antes de la primera prueba de U1

El sprint anterior tuvo un defecto grave: tres pruebas de interfaz **escribieron en `data/apu.db`
del worktree** (hallazgo 5 de la bitácora de cierre). Este diseño **aumenta** ese riesgo por dos
vías: el botón de siembra ejecuta mucho más que una partida, y la costura que hoy permite desviar la
base —parchear `RUTA_BASE_POR_DEFECTO` en el objeto módulo de cada página— desaparece al
centralizarla. `tests/conftest.py` no protege hoy nada: la única defensa es una convención escrita
en docstrings, y una convención no detuvo el hallazgo 5.

Por tanto, **antes de escribir la primera prueba de U1**:

1. Fixture **autouse de alcance sesión** en `tests/conftest.py` que capture existencia y `mtime` de
   `data/apu.db` al empezar y **falle la sesión** si cambiaron al terminar.
2. `ui/caso.py` conserva `RUTA_BASE_POR_DEFECTO` como constante de módulo —sigue siendo parchable, y
   DRY se cumple igual: una definición, no ocho— y admite sobreescritura por variable de entorno.
3. Toda prueba `AppTest` hereda el arnés de `tests/unit/test_ui_componer.py:107-111`: parchea el
   **objeto módulo de `sys.modules`** (no una ruta de texto, por la copia huérfana que documenta
   `:20-30`) y afirma que la base temporal existe **antes de pulsar nada**.
4. Decidir y ejecutar la limpieza de `UI-01-TUB`, pendiente del sprint anterior, para que la
   comprobación 1 arranque desde un estado conocido.

### Límites conocidos de `AppTest`

- **No puede navegar entre las pantallas de esta aplicación**: `switch_page` exige una página basada
  en archivo relativa al script principal, y aquí son `st.Page(callable)`. Cada pantalla se prueba
  por separado sembrando `session_state`; la navegación real la cubre el guion manual.
- **`st.page_link` no está modelado** en su árbol de elementos: cae en `UnknownElement`, que no tiene
  `.label`, y el helper por rótulo del arnés actual reventaría con `AttributeError`. Es la misma
  sorpresa que dio `st.data_editor` en P4. **Decisión tomada de antemano: el paso siguiente se pinta
  con `st.button` + `st.switch_page()`**, comprobable por rótulo.

### Compuerta GU1 — CP‑07, la prueba con persona

Una persona que nunca ha visto la aplicación, sin explicación previa y sin que nadie la guíe, llega
desde el Inicio hasta un Excel cuyo libro incluye la hoja de auditoría. Es el único nivel que puede
verificar «no sé qué hacer», que es el defecto que origina el sprint.

El caso completo —consigna literal, guion del observador con qué cuenta como ayuda, cinco
condiciones de parada, estado final observable, hoja de registro y criterio— se redacta en U0 en
`docs/guion_prueba_arenia.md` como **CP‑07**, con fila de referencia en `docs/plan_pruebas.md`. Sus
piezas no negociables:

- **Dos escenarios con personas distintas:** A, base sembrada (mide el recorrido); B, base vacía
  (mide además el estado vacío y la siembra desde la interfaz).
- **Base exclusiva de la prueba**, nunca `data/apu.db`.
- **Tope de 20 minutos**; abandono a los 5 minutos sin acción nueva; el observador ofrece ayuda una
  sola vez tras 3 minutos sin avanzar, y si la persona acepta, la sesión queda **asistida** y el
  veredicto es FALLA.
- **Estado final observable:** existe `presupuesto_<codigo>.xlsx` con sus cuatro hojas
  (*Presupuesto*, *APU*, *Curva*, *Auditoria*) y la persona sabe decir cuántos hallazgos tiene la
  auditoría. En el escenario B, además, la base tiene partidas al terminar.

**Criterio de aceptación, declarado antes de ejecutar. PASA si y solo si:** alcanzó el estado final
sin ayuda; dentro de los 20 minutos; y el promedio del **bloque B** es ≥ 4,0 **sin ningún ítem por
debajo de 3**. **FALLA en cualquier otro caso**, sin negociar: un criterio que se ablanda después de
medir no mide nada. Una FALLA no cancela el sprint — es el dato de la tesis y la entrada de U2.

Los umbrales de 20, 5 y 3 minutos **son decisiones de este caso, no medidas**: se declaran para que
el veredicto no dependa del criterio del observador, y se revisan con evidencia tras la primera
ejecución, dejando constancia en `docs/bitacora/`.

---

## 7. Las fases

| Fase | Contenido | Compuerta |
|---|---|---|
| **U0** — Documentar | RF‑36 a RF‑43 y UC‑12 en la ERS (con el actor nuevo «usuario nuevo / evaluador» y los seis lugares que un UC obliga a tocar); enmienda de la reserva de RF‑32; RNF‑10 en ERS, `calidad_iso25010.md` y `plan_pruebas.md` §3/§8/§9; bloque B en el anexo A; CP‑07 en el guion manual; el menor de `streamlit` (sección 8) | **GU0**: requisitos escritos, CP‑07 redactado antes de ejecutarse, documentos sin contradicción interna |
| **U1** — Enfoque A | Inicio, caso abierto, marco, estado vacío sembrable, vocabulario, agrupación, paso siguiente | **GU1a** (enmienda de la spec de cierre §5): línea base en 1 586,61 y 7 de 7; suite verde en ambos sistemas; salvaguarda de aislamiento activa; **GU1b** (fase Med): **CP‑07** |
| **U2** — Enfoque B | El asistente de cinco pasos. **Solo si CP‑07 resulta FALLA**; su alcance lo fijan los puntos de detención registrados | **GU2**: ídem GU1, más `componer.py` sin cambios salvo extracción de fragmentos |
| **U3** — Enfoque C | Pulido de navegación y redacción. Requiere decisión expresa de Eugenio | — |

El detalle sesión por sesión es del `PLAN_UI.md`, no de este documento.

---

## 8. Riesgos y criterios de degradación

| Riesgo | Criterio |
|---|---|
| **El PR #7 no se fusiona o la auditoría obliga a cambios de fondo** | Dependencia dura: `main` no tiene `componer.py` (verificado con `git ls-tree`) y sin ella no hay recorrido que guiar. U1 no empieza hasta la fusión. Esta rama solo lleva documentos: se reasienta sobre `main` sin conflicto |
| **`AppTest` no alcanza algo del Inicio** | Ya pasó con `st.data_editor` en P4 y con `st.page_link` aquí. Lo que no alcance lo cubre CP‑07, declarado como tal — nunca se relaja la afirmación para que la prueba pase |
| **Una prueba de U1 escribe en `data/apu.db`** | La salvaguarda de §6 lo convierte en fallo ruidoso de la sesión completa, no en un descubrimiento a posteriori |
| **CP‑07 resulta FALLA** | No se relaja el criterio. Se registra, se cita con su n y su perfil, y se convierte en el alcance de U2 |
| **La agrupación del menú rompe la entrega a la empresa** | `ARENIA_MODO_ENTREGA` conserva su comportamiento de omitir la sección Investigación (3.5) |

**Menor que este sprint hereda y corrige en U0:** `pyproject.toml:17` declara `streamlit>=1.35`,
pero `st.navigation` —que `ui/app.py:131` ya usa— **apareció en 1.36.0** (20/06/2024), y el
diccionario de secciones existe **desde esa misma versión**; verificado contra las notas de versión
publicadas y contra la firma de `streamlit/commands/navigation.py:89-90` en la 1.62.0 instalada. El
`uv.lock` resuelve 1.62.0 y por eso nadie lo ha visto, pero la restricción declarada admite una
instalación que no arranca. El mínimo sube a 1.36.

**Desactualización documental que U0 debe resolver o fechar:** `docs/calidad_iso25010.md` está
fechado el 2026‑08‑31 con 395 pruebas y `docs/plan_pruebas.md` §10 registra 479 (2026‑09‑14),
mientras el cierre del prototipo declara **673**. Este documento cita §4 de calidad como estado
vigente.

---

## 9. Trabajo futuro declarado

- **Medir RNF‑10 con más de una persona.** CP‑07 con n = 1 es un dato, no una muestra, y así se cita.
- **RNF‑04 sigue pendiente**, con su población de 3–5 expertos sobre el informe, para la Fase 6.
- **El buscador MaPreX añade una fila nueva** en vez de rellenar una en blanco (pregunta cerrada «por
  ahora» el 2026‑09‑20). CP‑07 es la ocasión de resolverla con evidencia en vez de con criterio.
- **Un recorrido para los cuatro dominios.** Hoy los recorridos son civiles; telecom, industrial y
  sistemas tienen presupuestos sembrados y ninguna puerta de entrada propia.
- **Los tres sembradores con el patrón de herencia de precios latente** (`seed_telecom`,
  `seed_industrial`, `seed_sistemas`), pendientes desde el sprint anterior: si el Inicio llegara a
  ofrecer sembrar por dominio, dejan de ser latentes.

---

## 10. Qué cambió en la revisión del 2026-09-23

Cuatro encargos revisaron la primera versión de este documento. Los cuatro aprobaron con
correcciones; ocho hallazgos eran bloqueantes. Quedan aplicados:

| Hallazgo | Corrección aplicada |
|---|---|
| **GU1 no cierra RNF‑04** (tres revisores, por separado) | §1 y §5: se declara **RNF‑10** con instrumento propio (bloque B); RNF‑04 queda intacto y pendiente. Decisión de Eugenio |
| **El anexo A no se puede contestar si la persona no llega al informe** | §5: bloque B de siete ítems, promedio propio, nunca mezclado con el A |
| **El spec no redactaba ni un RF** | §2.1: ocho enunciados, RF‑36 a RF‑43, y UC‑12 |
| **El paso siguiente desde las páginas reintroduce el ciclo** | §3.3: lo pinta `ui/app.py` como marco alrededor de `.run()` |
| **`st.navigation` no colapsa secciones en la barra lateral** | §3.5: el modo entrega sigue omitiendo; se descarta `position="top"` |
| **GU1 no era ejecutable** | §6: CP‑07 con consigna literal, guion del observador, cinco paradas, tope de 20 min y criterio firmado antes de medir |
| **`scripts/` sí es importable** (falso el criterio de degradación) | §3.6: se retira; en su lugar, la restricción contra `--reiniciar`, que sí destruye la base |
| **Ninguna pantalla ofrecía sembrar: era falso** | D‑3: *Actualización de precios* ya tiene el botón; lo que falta es el caso de demostración y la reacción a una base vacía |

Correcciones menores también aplicadas: eran **ocho** copias de `RUTA_BASE_POR_DEFECTO`, no cinco;
`catalogo.py:32`, no `:33`; el ciclo de importación es **potencial**, no actual; `simular_lista.py`
no tiene constante; la regla 1 dice «no **modifica** `core/`», porque `ui → core` es arista legítima
del C4; la prueba de enlaces **no** va a `test_arquitectura.py`, que es puro análisis estático sin
importar módulos; `test_ui_app.py` se reescribe a propósito y se declara; `test_ui_importable.py`
debe ampliarse a los módulos nuevos; la usabilidad es la única **sin medición alguna** (la
compatibilidad es *parcial*, no pendiente).

Los cuatro revisores confirmaron, por separado, que **ningún cambio a `core/` es necesario**: el
estado del caso se construye entero con la API pública de `Catalogo`.
