# Rediseño del front: marco de obras, bandeja de pendientes y ayuda

Fecha: 2026-10-26. Estado: APROBADO por Eugenio el 2026-10-26 («quiero este diseño»; alcance de esta tanda: hasta
F2). Maqueta de referencia: vista «dentro de la obra» con barra lateral marfil (copia local, fuera del repo).
Sustituye la pulida visual prevista en MOD-5b (impeccable + taste sobre el marco actual). No toca `core/`.

## 1. Intención y por qué

El front React quedó con la organización de Streamlit: una pantalla por herramienta (Componer, Elaborar, Similares,
Reajuste, Escenarios…; 27 páginas en `frontend-desktop/src/paginas/`) y un menú que obliga a saber de antemano a dónde
ir. Eugenio: «siento que el usuario se pierde cada vez que abre este programa». La empresa confirmó lo mismo
(reunión del 2026-10-25: «una sola vista de trabajo»).

El rediseño cambia el **eje de la navegación**: de herramientas a **obras** (organizadas como repositorios de GitHub)
y a **pendientes** (lo que a la persona le toca hacer). Cada botón y cada opción tiene que poder justificarse en una
frase por el beneficio que da a quien lo usa; lo que no pasa esa prueba se fusiona, se mueve o se quita.

Éxito, en palabras de Eugenio: que la persona sepa dónde está, qué puede hacer y qué sigue, sin ayuda externa; y un
código más pequeño y limpio que el actual.

## 2. Objetivos

1. **Marco nuevo** (decidido con maquetas, opción «C + D»):
   - **Barra superior** negro carbón con el logo de la empresa, línea amarilla inferior, migas
     (`Mis obras / <obra> / <sección>`), buscador global (Ctrl+K) y menú de la cuenta.
   - **Barra lateral marfil** en forma de árbol (estilo explorador de GitHub/VS Code), tres zonas:
     1. **Pendientes** con contador.
     2. **Obras**: árbol; cada obra se despliega en sus secciones (Resumen, Presupuesto, Archivos y planos, Versiones,
        Aprobaciones, Mercado, Control de obra) unidas por una línea guía; contador de pendientes por obra;
        «+ Nueva obra» al pie del árbol.
     3. **Empresa**: Precios y catálogo, Auditar un presupuesto, Empresa y personas, **Ayuda**.
   - Elemento activo: fondo crema y raya amarilla a la izquierda.
2. **Pendientes como pantalla de entrada** (bandeja tipo correo): lista ordenada por urgencia a la izquierda, detalle a
   la derecha con qué pasó, qué hacer y el botón para hacerlo. Cada pendiente dice de qué obra es.
3. **La obra como espacio de trabajo**: cabecera con nombre, moneda, versión, lista de precios y estado; pestañas por
   sección; franja amarilla «Te falta: …» / «Siguiente paso: …» que marca las filas afectadas.
4. **La carpeta desaparece del uso diario**: la obra es la carpeta; sus archivos viven en «Archivos y planos». La
   gestión de carpetas en disco queda solo en Empresa (administrador: instalar, respaldar, restaurar).
5. **Rework visual de todas las páginas y vistas** con un mismo lenguaje: tablas limpias con cifras alineadas
   (coma decimal, punto de miles), un solo botón principal por pantalla, textos que dicen para qué sirve cada cosa.
6. **Sección de Ayuda** (pedida por Eugenio: «a veces es poco intuitivo»):
   - **Ayuda en contexto**: cada sección y cada control no obvio lleva un «¿Qué es esto?» que abre un panel lateral
     con la explicación corta y un enlace a la guía.
   - **Guías por tarea** en la sección Ayuda: armar un presupuesto, enviarlo a aprobar, responder observaciones,
     auditar un Excel, actualizar precios, seguir una obra. Pasos numerados con capturas.
   - **Glosario** del oficio (APU, partida, rendimiento, FCAS, lista de precios, versión sellada…).
   - **Primera vez**: la bandeja vacía de una cuenta nueva muestra «Empieza aquí» con la guía de armar un presupuesto.
7. **Tema de la empresa configurable**: el repositorio lleva un tema neutro; logo y paleta de la empresa viven en un
   archivo local que no se versiona (regla de Eugenio: nombre y marca de la empresa nunca al repo).
8. **Borrar por completo la herencia de Streamlit** (Eugenio: «todas las vistas me molestan porque se ven a
   Streamlit; quiero borrar eso de este proyecto por completo, la identidad y ese front feo»). Streamlit ya se
   retiró como dependencia; lo que queda es su identidad: una pantalla por herramienta, títulos tipo «Componer una
   partida» en un menú, formularios apilados de arriba abajo, nombres internos (`pagina`, `seccion`, `clasica`),
   textos y documentos que lo nombran. Al cierre no debe quedar ninguna pantalla con esa forma ni ningún rastro en
   código, estilos, textos o manual vigente (el histórico de bitácoras se conserva como historia). Guardia: una prueba
   que falla si reaparece el patrón o la palabra fuera del histórico.
   **Referencia de composición aprobada**: la vista «dentro de la obra» de la maqueta (cabecera de la obra, pestañas,
   franja «Te falta», tabla) es el molde de todas las secciones.
9. **Menos código**: el resultado debe tener menos líneas de producto que hoy (línea base abajo), sin perder pruebas
   de comportamiento.

## 3. No objetivos

- No se toca `core/` ni la lógica de negocio de `aplicacion/`; la API solo cambia si una pantalla nueva necesita una
  ruta que no existe (p. ej. la lista agregada de pendientes, ver §8).
- No se cambia de framework (React + Carbon se quedan: el código y las pruebas aprobadas por los árbitros valen).
- No se reescribe desde cero en otro proyecto.
- No se retiran funciones: se reubican. Retirar algo exige que Eugenio lo apruebe en el inventario (§6).
- No hay IA nueva en este trabajo.

## 4. Antiobjetivos (fracaso aunque funcione)

- Pintar las pantallas viejas de amarillo y llamarlo rediseño.
- Que el árbol de obras se vuelva otro menú de herramientas.
- Ayuda que repite el título del botón («Guardar: guarda»). Cada texto de ayuda dice para qué sirve y cuándo usarlo.
- Bajar líneas borrando pruebas o metiendo todo en archivos gigantes.
- Que el nombre o el logo de la empresa terminen en un commit.

## 5. Restricciones

- Pantalla de referencia 1366×768 (también 1056 y 1910, como en MOD-5a); escala de letra de presbicia vigente.
- Español de Venezuela; coma decimal y punto de miles en toda entrada y salida.
- Accesibilidad de lo ya aprobado (foco, Esc, regiones vivas, contraste AA) se conserva.
- Uso semanal: agentes de uno en uno, árbitro igual, menores agrupados, navegador una sola vez al final.
- TDD obligatorio en todo lo nuevo; suite completa en el cierre de cada fase.
- Antes de empezar a construir: cerrar o confirmar el trabajo sin confirmar de los agentes en pausa en
  `.worktrees/s2madm` (toca `shell/` y `paginas/`). Eugenio decide cuándo reanudarlos.

## 6. Método

### 6.1 Medir antes de borrar (línea base del 2026-10-26)

| Medida | Valor |
|---|---|
| Código de producto TS/TSX | 36.250 líneas |
| Pruebas TS/TSX | 40.255 líneas |
| SCSS | 4.608 líneas |
| Archivos sin uso (knip 5.66.1) | 0 |
| Exportaciones sin uso | 38 (casi todas constantes que solo usan las pruebas) |
| Tipos exportados sin uso | 57 |
| Duplicación (jscpd, bloques ≥ 8 líneas) | 0,79 % (27 clones) |

Conclusión honesta: **no hay mucho código muerto**. Lo que pesa es la **estructura**: 27 pantallas, cada una con su
cabecera, su estado vacío, su tabla y su forma de avisar, y componentes de 500-650 líneas (`Elaborar`, `Hoja`,
`Shell`, `GestionCarpetas`). El ahorro real sale de fusionar pantallas en secciones de la obra y de sacar los patrones
repetidos a piezas comunes. knip y jscpd se quedan como guardias en la CI para que no vuelva a crecer basura.

### 6.2 Inventario de pantallas, botones y opciones

Antes de rediseñar cada sección, una tabla con cada página, botón y opción visible: qué hace de verdad, qué
beneficio da a la persona, y el destino (**se queda / se fusiona / se mueve / se quita**). Eugenio aprueba el
inventario; las bajas solo con su visto bueno. El inventario es la fuente de los textos de ayuda (§2.6).

Reparto de partida (lo confirma el inventario):

| Sección de la obra | Pantallas de hoy que absorbe |
|---|---|
| Presupuesto | Hoja, Elaborar, Componer una partida, Partidas similares |
| Archivos y planos | carpeta de trabajo, libro, planos, subidas |
| Versiones | versiones selladas, Histórico de cambios |
| Aprobaciones | Aprobar, Revisar un paquete, Entregar paquete |
| Mercado | Estudio de mercado, Actualizar precios |
| Control de obra | Control, Tablero, Reajuste, Escenarios |
| Empresa (fuera de la obra) | Catálogo, Precios de la empresa, Índices del BCV, Simulador, Auditoría, Producción, Administración, Acerca de |

### 6.3 Migración en el mismo proyecto (patrón «estrangulador», Fowler)

El marco nuevo se monta junto al actual. Cada sección se migra entera (pantalla + pruebas) y la ruta vieja redirige a
la nueva cuando su sección queda aprobada. Nada se borra hasta que su reemplazo está aprobado por el árbitro. Así la
app funciona en todo momento y cada paso se puede revertir.

### 6.4 Código limpio (Robert C. Martin, *Clean Code*, 2008) aplicado con medida

Reglas que se aplican y cómo se verifican:

- **Nombres que dicen la intención**, en el vocabulario del usuario (obra, partida, pendiente), sin restos de
  Streamlit (`pagina`, `seccion`, `carpeta` donde ya no aplica). Guardia: la prueba `sinJergaInterna` se amplía.
- **Una responsabilidad por componente**: la pantalla compone; la lógica pura vive en `logica.ts` probada aparte;
  las llamadas a la API en el cliente. Tope orientativo de 250 líneas por componente; superarlo exige razón escrita.
- **DRY** sobre patrones repetidos: cabecera de sección, franja «Te falta», estado vacío, tabla de cifras,
  «¿Qué es esto?». Se crean una vez en `comun/` y se reutilizan; se crean cuando aparecen la segunda vez, no antes.
- **YAGNI**: nada de opciones «por si acaso»; lo que el inventario no justifica no se construye.
- **Regla del boy scout**: cada sección migrada deja su código más limpio de lo que lo encontró (exportaciones sin uso,
  tipos huérfanos, comentarios que repiten el código).
- **Comentarios solo para el porqué** (decisión, norma, ruling), nunca para repetir el qué.
- **Textos como datos**: títulos, explicaciones y ayudas en un catálogo único por sección, no regados en el JSX. Ahorra
  líneas, alimenta la Ayuda y facilita revisar el tono.
- Tensión conocida: funciones pequeñas a veces suman líneas. Cuando choquen «menos líneas» y «más claro», gana claro;
  la meta de líneas se mide por sección, no por función.

### 6.5 Herramientas y por qué

- **knip** (código y dependencias sin uso) y **jscpd** (duplicación): medir y vigilar en CI; son de desarrollo, no
  entran al paquete.
- **taste-skill** y **ui-ux-pro-max**: dirección visual y revisión por pantalla con las referencias aprobadas
  (Fiori Object Page, Linear, Procore/Autodesk Build, Airtable, Carbon for IBM Products, Stripe, Ramp).
- **Carbon** se queda como base de componentes; el aspecto de la empresa sale de sus tokens de tema, no de
  sobrescribir componentes uno por uno.
- Ninguna dependencia nueva de ejecución salvo que una pieza lo justifique por escrito.

## 7. Orden de trabajo (por fases, cada una con árbitro)

1. **F0 Preparación**: cerrar el trabajo en pausa (decisión de Eugenio), línea base medida, knip/jscpd en la CI,
   tema de empresa (neutro en repo + archivo local), DESIGN.md del marco.
2. **F1 Inventario** (§6.2) aprobado por Eugenio.
3. **F2 Marco**: barra superior, barra lateral marfil en árbol, migas, Ctrl+K, ruteo `obra/<id>/<sección>`.
4. **F3 Pendientes**: bandeja + detalle, con la lista agregada de pendientes.
5. **F4 La obra**: Resumen y Presupuesto primero (es el flujo de «montar un presupuesto», prioridad vigente); luego
   Archivos, Versiones, Aprobaciones, Mercado, Control.
6. **F5 Empresa**: Precios y catálogo, Auditar, Empresa y personas, Producción.
7. **F6 Ayuda**: «¿Qué es esto?» en cada sección, guías por tarea, glosario, «Empieza aquí».
8. **F7 Cierre**: retiro de rutas y pantallas viejas, recorrido único en navegador (1056/1366/1910), suite completa,
   comparación de líneas contra la línea base.

## 8. Lo que queda al constructor

- La forma exacta de la lista agregada de pendientes (ruta nueva o composición en el front de las rutas que ya dan
  pendientes por obra), siempre que no toque `core/`.
- Los tokens de tema y su nombre; los valores de la empresa van en el archivo local.
- La técnica de redirección de rutas viejas.
- El formato del catálogo de textos y de las guías.

## 8 bis. Decisiones del orquestador tras la revisión del constructor (Eugenio puede cambiarlas)

- **Módulos del 2026-10-25**: el diseño de módulos (Auditoría / Presupuestos y obras / Producción y su selector) queda
  sustituido por las tres zonas de la barra lateral. Auditoría (Auditar un presupuesto, paquetes recibidos, historial
  de auditorías) y Producción (existencias) van en la zona Empresa, cada una como entrada propia. La regla de
  «módulo de entrada por rol» se convierte en el orden y el filtro de Pendientes.
- **Pendientes**: une `/v1/obras/pendientes` y `/v1/aprobaciones/pendientes`, filtrado por los permisos de la cuenta
  (quien arma ve lo suyo por hacer y lo devuelto; quien revisa, lo que espera su dictamen; el administrador, todo lo
  de su alcance). Orden: primero lo que bloquea (devuelto, atrasado, por aprobar), después avisos (cambios de
  precio); dentro de cada grupo, lo más antiguo arriba. Si unirlas en el front resulta frágil, se añade una ruta de
  lectura en `api/` que componga las dos, sin tocar `core/`.
- **Ctrl+K, primera entrega**: busca obras, secciones y entradas de la zona Empresa, en el front. Buscar partidas e
  insumos entre obras queda para después.
- **Guardia anti-Streamlit**: cubre `frontend-desktop/` (código, estilos, textos) y el manual o la ayuda vigentes.
  Histórico que se conserva: `docs/bitacora/`, `CHANGELOG.md`, especificaciones y planes anteriores a esta fecha.
  Los comentarios de `api/` y `aplicacion/` que lo nombran se limpian por la regla del boy scout cuando se toquen.
  `scripts/recorrido_ux_playwright.py` se ajusta al ruteo nuevo en F7.
- **Ayuda y manual son una sola cosa**: las guías por tarea de la sección Ayuda son el manual; los borradores de
  `docs/manual_nuevo/` se aprovechan como material. Las capturas del repositorio salen con tema neutro y obras
  ficticias; las de la empresa, solo en local.
- **Dependencias entre fases**: aprobada esta especificación, F2 (marco) puede empezar sin esperar el inventario,
  porque no depende de los botones de cada pantalla. F4, F5 y F6 sí esperan el inventario de su sección.

## 8 ter. Carpeta y obra (Eugenio, 2026-10-26: «C+B»)

Lectura del orquestador, por confirmar al verla funcionando: el árbol muestra **todas las obras de todas las
carpetas** a las que la cuenta tiene acceso (opción b), y Sílice abre la carpeta de la obra elegida sin que la persona
lo note. Consecuencias:
- Hace falta una ruta de lectura que liste obras de todas las carpetas (`api/` + `aplicacion/`, sin `core/`); esto
  amplía el no objetivo de §3, que solo admitía rutas para pendientes.
- `obra/<id>/<sección>` manda: al entrar por esa ruta, el front fija carpeta y obra en la sesión del servidor antes de
  pintar; la sesión del servidor solo refleja la ruta.
- Dos pestañas en obras de carpetas distintas: la segunda en tomar la sesión gana y la primera, al volver a hacer una
  petición, ve un aviso «Esta obra se abrió en otra pestaña» con botón para retomarla (no hay escritura silenciosa en
  la obra equivocada).
- Si la palabra «B» se refería al camino por etapas en la cabecera de la obra, se añade en F4 sin cambiar este marco.

Detalles visuales tomados de la maqueta aprobada: los contadores son píldoras pequeñas (no bloques), la franja
«Te falta» lleva un solo botón amarillo, las filas afectadas se marcan con fondo ámbar claro.

## 9. Por decidir con Eugenio

- Momento de reanudar y cerrar los agentes en pausa (bloquea F2 en adelante).
- Logo completo de la empresa en buena resolución (solo local).
- Eugenio respondió que le molestan todas las vistas por igual; el orden de F4 (Resumen y Presupuesto primero) queda
  como decisión del orquestador por ser el flujo prioritario de «montar un presupuesto».
