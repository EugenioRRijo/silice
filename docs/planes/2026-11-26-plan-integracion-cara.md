# Plan: integrar la cara «Papel y resaltador» en el front (B1)

**Fecha:** 2026-11-26 · **Rama:** `feature/front-b1` · **Tope:** 2026-12-16 (etiqueta `medicion-v1`)
**Pedido de Eugenio:** «cuando termines en el artifact del reformulacion de fornt, empieza a integrar a la rama el
nuevo front y ui ux».
**Fuente del diseño:** [especificación](../especificaciones/2026-11-26-cara-papel-y-resaltador/README.md) y el lienzo
del artifact (tableros `S-*`, «Botones», «Barra lateral» y «Tablero de inicio»).

## Límites (los del acta, sin cambio)

`core/`, los archivos sellados por `reglas-congeladas-2026-11-24` y `aplicacion/hoja.py` no cambian. Las rutas del
contrato de 2026-11-04 no cambian: la cara nueva cambia dónde y cómo se muestran las secciones, no sus direcciones.
TDD (prueba en rojo primero), ub-mode, la guía *modern-web-guidance* consultada en cada lote, la skill
`interfaz-silice` antes de tocar una pantalla, y `sinJergaInterna` en verde. Coma decimal, trato de usted, la cifra la
calcula el servidor, la gravedad siempre con su palabra.

## Lotes, en orden

| Lote | Qué | Archivos principales | Quién construye |
|---|---|---|---|
| **C0** Fundamentos | Tokens claro y oscuro de la especificación como `--silice-*`, con `color-scheme: light dark` y `light-dark()` (respaldo con `prefers-color-scheme`); los tokens de Carbon (`--cds-background`, `--cds-layer-*`, `--cds-text-*`, `--cds-border-*`, `--cds-interactive`, `--cds-focus`, `--cds-button-*`) apuntan a ellos; Instrument Sans y Newsreader empaquetadas desde `@fontsource/instrument-sans@5.3.0` y `@fontsource/newsreader@5.3.0`; `/v1/tema` sigue mandando sobre el acento | `estilos/tokens.scss`, `estilos/fuentes.scss`, `package.json`, `marco/tema.ts` | Carbon, con Neon de revisor |
| **C1** Modo oscuro elegible | Cuenta › Empresa y tema con tres estados (Claro, Oscuro, Como el sistema, que dice cuál rige); `localStorage`; un script propio pequeño (`public/modo-inicial.js`, `script-src 'self'`) junto al `<meta name="color-scheme">` para que no parpadee; el evento `storage` sincroniza pestañas | `index.html`, `public/modo-inicial.js`, la sección de la Cuenta | Hydrogen |
| **C2** Botones | «Contorno de papel» sobre los botones de Carbon: principal en tinta, secundario con trazo de 1,5 px que se rellena al pasar, terciario subrayado, destructivo con trazo rojo; escala 28/32/40; foco dorado; patrón «inactivo que explica por qué» (`aria-disabled`) | `estilos/app.scss` (capa de botones), un componente `comun/BotonInactivo` | Hydrogen |
| **C3** Barra de la empresa | Espacios + «Nueva obra» amarilla fija + Buscar + cuenta | `marco/BarraSuperior.tsx` | Carbon |
| **C4** Barra de la obra | Nombre → Portada; pestañas Presupuestar · Auditar · Anticipar, cada una a la primera sección de su grupo; menú de versión (versiones, pedir aprobación, entregar); la acción principal de la herramienta | `marco/CabeceraDeObra.tsx`, `marco/BarraDeEspacio.tsx`, `marco/secciones.ts` (solo la agrupación, no las rutas) | Carbon |
| **C5** Riel lateral | Panel propio con iconos, reducible a 56 px (se recuerda), bloque de cifras de las otras herramientas (solo lo que la API ya da), carpeta abierta al pie | `marco/BarraLateral.tsx`, `marco/marco.scss` | Carbon |
| **C6** Notas al margen | Componente de notas numeradas unidas a su fila, sobre la lógica pura de B1-1 (`gruposDeProblemas`, `filaDelHallazgo`); Presupuestar › Partidas con la tabla HM (precio con referencia de lista) | `paginas/hoja/superficie/*` | Carbon (con B1-2b, la grilla) |
| **C7** Gráficos | Series validadas (azul, aguamarina, naranja) en los gráficos de Carbon Charts y en los propios; capa de detalle al pasar; «Ver como tabla» | gráficos de Control, Riesgo, Mercado, Escenarios y Producción | Hydrogen |
| **C8** Inicio | Inicio › Resumen con gráficos y la vista «Nueva obra» en lugar del diálogo (mismos datos que `DialogoNuevaObra`) | `paginas/inicio/*`, `shell/obras/*` | Carbon |

| **C9** Registro con código por correo | Decisión de Eugenio (2026-11-26): «creo que sera mejor que se registrara con su nombre y contraseña y al correo le llegue un codigo de 20 letras para que se convierta en constructor o revisor». La persona se registra (nombre, correo, usuario, contraseña) y su cuenta queda pendiente sin papel; el administrador elige el papel (arma o revisa) y Sílice genera un código de 20 caracteres (5 grupos de 4, un solo uso, vence en 7 días, guardado solo su hash) que envía por correo con el SMTP de la empresa (Cuenta › Empresa); sin correo configurado o sin conexión, el administrador lo ve en pantalla para entregarlo en mano; la persona escribe el código y toma el papel; el administrador asciende después como hoy. Toca API, migración de `instalacion.db`, pantalla de entrada y Cuentas; revisión de seguridad obligatoria | `api/rutas/cuentas.py`, `aplicacion/`, migración, `sesion/`, `marco/EspacioDeCuenta.tsx` | Claude con revisor de seguridad |

| **C10** Actividad por persona | Decisión de Eugenio (2026-11-26): «el reporte puede ser como lo hace github en su pagina web». Una página por persona (desde Cuentas y permisos y desde el nombre de quien guardó o auditó): un calendario de actividad del último año (una celda por día, una sola tinta de menos a más, con su leyenda y el detalle del día al pasar), las cifras del período (versiones guardadas y enviadas, auditorías, dictámenes), y debajo la actividad reciente en orden de fecha («guardó la V2 de Vialidad Tramo 3», «auditó Presupuesto cliente A.xlsx: 3 errores»), con filtro por tipo; además un filtro «Por persona» en Versiones y en el Historial de auditorías. Solo lectura de datos que ya existen (versiones, rastro de aprobaciones, historial); «Ver como tabla» en el calendario | `api/rutas/` (una ruta de solo lectura), `paginas/` (página nueva), Versiones e Historial | Claude |

| **C11** Notificaciones | Decisión de Eugenio (2026-11-26), con la guía `persistent-toast-notifications`: las confirmaciones se ven 3 minutos (pausa con el cursor o el foco), los avisos se quedan hasta cerrarse, y lo que bloquea va en un aviso de la pantalla o un diálogo; se apilan abajo a la derecha en la región «Notificaciones nuevas», sin robar el foco, anunciadas con el anunciador de B0 y nunca con un diálogo abierto; barra de estado fina abajo (carpeta, «Guardado hace …» y la campanita con las no leídas); la campanita abre un panel a la derecha, no modal (Hoy/Ayer, gravedad con palabra, enlace al lugar, «Marcar todas como leídas», filtro Sin leer, Esc devuelve el foco); se guardan 30 días por persona y se puede elegir cuáles recibir | `comun/notificaciones/*` (nuevo), `marco/Marco.tsx`, `marco/BarraDeEstado.tsx` (nuevo), una ruta de la API para guardarlas por persona | Claude |

Después siguen los lotes de comportamiento de la [ficha de B1](../bitacora/2026-11-25-acta-reestructuracion-front.md)
(B1-2b en adelante), que ya se escriben con la cara nueva.

## Cómo se cierra cada lote

1. Prueba en rojo por cada comportamiento visible (rol, nombre accesible, `aria-current`, `aria-pressed`, el modo).
2. Verde; `npm run lint`, `tsc`, `npx vitest run --maxWorkers=3`, y para estilos las pruebas de `estilos/*.test.ts`.
3. Mutaciones a mano en lo nuevo (ub-mode: matar sobrevivientes).
4. Una mirada en el navegador en claro y oscuro contra el tablero del lienzo.
5. Commit en `feature/front-b1`; revisión de Neon o de Opus al cerrar cada dos lotes.

## Después de C10: auditoría de la app completa (pedido de Eugenio, 2026-11-26)

«ok enfoquemos la reestructuracion hasta c10 y luego auditemos la app para que ningun boton este roto y herramienta se
rompa, validemos tambien la logica de la auditoria y de la aplicacion en general».

1. **Nada roto (recorrido de clics):** un recorrido automático (Playwright, sobre `scripts/recorrido_ux_playwright.py`)
   por cada ruta del contrato, en claro y oscuro, con la obra de demostración: pulsa cada botón y enlace visible, y
   falla ante un error en la consola, un 4xx/5xx inesperado, una pantalla en blanco, un botón sin efecto o un foco
   perdido. Cada hallazgo, con su captura, va a una bitácora fechada.
2. **Lógica de la auditoría:** el inyector de fallas, las metamórficas, el oráculo de LibreOffice, la sensibilidad de
   umbrales y la traza por causa (Fase 1 del plan no circular) corren contra las reglas selladas; cada regla detecta
   lo que debe y no inventa hallazgos; las reglas no cambian sin acta (sello `reglas-congeladas-2026-11-24`).
3. **Lógica general:** la suite completa de Python (`uv run pytest -W error -q -n auto --dist loadfile`) y del front,
   ruff, lint, tsc, `meta_datos`, la guardia del núcleo, y mutantes en cálculo, reglas y cuentas; un auditor
   independiente (Opus) revisa sin recibir las conclusiones del orquestador, y cada hallazgo se verifica contra el
   código antes de corregirse con prueba en rojo.
