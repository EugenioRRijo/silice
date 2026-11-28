# Cara nueva del front: «Papel y resaltador» (aprobada 2026-11-26)

Eugenio aprobó esta cara para la reestructuración del front (B1 en adelante) el 2026-11-26, con modo claro y oscuro:
«esta bien ese modo oscuro afinemos el side bar con los widges y apruebo para adaptar el nuevo front de reestructiracion».
La reestructuración **no** sigue la cara de `frontend-desktop/DESIGN.md` (decisión del 2026-11-26); lo que sigue valiendo
de las NORMAS está en «Lo que no cambia», al final.

Las 21 vistas, en claro y oscuro, están en el lienzo del artifact <https://claude.ai/artifact/FkADvQaZ1BZJR8AQnt4LdV>
(tableros `S-*`). Esta carpeta es su fuente: `generar_vistas.py` + `estilos.css` + `fragmentos/` las vuelve a generar.

## De dónde sale

- **Disposición «HM»**: la tabla de la cara H (precio con la referencia de lista debajo, filtros por gravedad, columna
  Notas) dentro del marco de la cara M (notas numeradas al margen derecho, unidas a su fila).
- **Paleta «Papel y resaltador»**: elegida por Eugenio frente a «Verde de autopista» y «Cianotipo»; rechazó el morado de M.
- Pasada de **unslop** (skill `unslop-interfaz`) a pedido de Eugenio: una rampa neutra con tres roles de texto, un solo
  acento, pesos 400/500, serif solo en el título, espaciado en la retícula de 4, radios anidados, sin brillos.

## Marco

Decisión de Eugenio (2026-11-26): «el side bar se ven todas las obras disponibles» y la barra de arriba con herramientas va solo en la vista de cada obra (o de cada espacio). Él aprobó la recomendación: espacios y obras en la barra lateral; arriba, el lugar abierto en dos filas.

| Zona | Qué lleva |
|---|---|
| Franja global (48 px, tinta) | Sílice · **Nueva obra** (amarillo) · Buscar (Ctrl K) · cuenta. Los espacios de la empresa ya no van aquí (decisión de Eugenio del 2026-11-26) |
| Barra del lugar (52 px, hoja) | En una obra: nombre → Portada; pestañas **Presupuestar · Auditar · Anticipar** (Auditar con su cuenta de problemas); a la derecha, el menú de versión («V2 · en elaboración ▾»: versiones, pedir aprobación, entregar) y la acción principal. Fuera de una obra: nombre del espacio y su acción |
| Barra lateral (236 px, riel de 56 px) | Los LUGARES: grupo «Espacios de la empresa» (Inicio, Auditar un libro, Precios y catálogo, Producción) y grupo «Obras» con todas las obras (sus problemas abiertos; la abierta resaltada, con sus capítulos debajo); el bloque de cifras del lugar abierto; la carpeta al pie |
| Segunda fila del lugar (40 px, hoja) | Las opciones de la herramienta o del espacio abierto como pestañas (Partidas · Componer un APU · Tramos · …), la actual en resaltador |
| Contenido | `sobre` (contexto) → **h1 con la cifra o el hecho principal** → `datos` → la tabla o gráfica principal |
| Margen derecho (288 px) | Notas numeradas; la activa en resaltador, unida a su fila con una línea; al pie «datos ficticios» en las demos |

**Dónde quedó cada sección de la obra de hoy:** Resumen → Portada; Presupuesto → Presupuestar › Partidas; Componer →
Componer un APU; Tramos; Archivos y planos → Plano o cómputo; Mercado (Estudio y Actualizar) → Precios de mercado;
problemas y Aprobar → Auditar › Problemas, Dictamen, Revisar un paquete; Versiones y Entregar → menú de versión;
Control, Reajuste, Riesgo, Escenarios → Anticipar.

**Bloque de cifras de la barra lateral:** en una obra muestra las cifras de las *otras* herramientas (nunca repite el h1
de la que está abierta): presupuesto vigente, problemas abiertos con su palabra, avance frente a lo planificado. En la
portada no va (la portada ya las muestra). En cada espacio de la empresa, dos o tres cifras de ese espacio. Cada fila
es un enlace a su pantalla.

**Botón «Nueva obra»:** fijo en la barra de la empresa, amarillo #F6D55C con texto #1F1B16 (11,9:1; 13,1:1 contra la
barra) y borde #C9A227, el mismo amarillo de las notas. Abre la vista «Componer la obra» (no un diálogo), con los datos
que hoy pide `DialogoNuevaObra`: nombre, cliente y ubicación opcionales, tipo de obra, moneda (otra que la de la
carpeta se convierte con la tasa del BCV) y la carpeta donde se crea. **Por confirmar con Eugenio:** «Copiar de otra
obra» en «Cómo empezar» no existe hoy.

## Botones (elegidos por Eugenio el 2026-11-26: «contorno de papel»)

Referencias: Carbon (escala y un principal por zona), Primer (inactivo en vez de deshabilitado), Atlassian (verbos,
sin tooltip sobre un deshabilitado), Fluent 2 (botón dividido), Notion y el terciario de Carbon (contorno que se
rellena). Tablero «Botones» del lienzo.

| Tipo | Aspecto | Encima | Presionado |
|---|---|---|---|
| Principal (uno por zona) | Relleno `acento` (tinta en claro, blanco roto en oscuro), radio 6 | `hover-tinta` (#3A342C / #FFFFFF) | baja 1 px |
| Secundario | Trazo interior de 1,5 px en `t1`, fondo transparente | se rellena de `t1` y el texto pasa a `hoja` | baja 1 px |
| Terciario | Texto subrayado (desfase 4 px), peso 500 | subrayado de 2 px | — |
| Destructivo | Trazo de 1,5 px en `error`, con su palabra; relleno rojo solo en el paso de confirmar | — | — |
| «Nueva obra» | Amarillo #F6D55C con borde #C9A227, solo en la barra de la empresa | #F9E07F | — |

Escala: compacto 28 px (filas y barras de herramientas), normal 32 px, grande 40 px; relleno 12/14/18 px; peso 500;
icono de 16 px a 6 px del texto; ancho mínimo 72 px. Foco: anillo de 2 px en `sel-borde` con desfase de 2 px.
Cargando: el botón conserva su ancho, muestra un giro de 16 px y `aria-busy`. Una acción que no se puede hacer
queda **inactiva** (`aria-disabled`, sigue en el orden de tabulación) y al pulsarla dice por qué.

## Barra lateral (elegida el 2026-11-26: «riel de iconos»)

Panel propio de altura completa, pegado al borde: fondo `lateral` (#EFE9DF / #12110F) con filete a la derecha.
Abierta mide 236 px; se reduce a un riel de 56 px solo con iconos (el nombre aparece al pasar y es el nombre
accesible). Cada opción lleva icono de 16 px, fila de 36 px, radio 6; la actual va con `aria-current="page"`, en
resaltador y en peso 500 (no solo color, guía navbar). Debajo, el índice de la vista; después el bloque de cifras
como tarjeta; al pie, la carpeta abierta. En el riel reducido las cifras pasan a números sobre el icono y la carpeta a
un icono con su nombre al pasar. Como mucho dos niveles (Carbon, Fluent). Iconos en `iconos.json`.

## Tokens

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| `fondo` | #F7F4EE | #161513 | Fondo de la página |
| `hoja` | #FDFBF7 | #1C1A18 | Tablas, tarjetas, barra del lugar |
| `alzado` | #EFE9DF | #262421 | Opción activa, controles |
| `linea` | rgba(31,27,22,.10) | rgba(239,233,222,.09) | Filetes |
| `t1` / `t2` / `t3` | #1F1B16 / #5E554A / #9A9184 | #EFE9DE / #AAA398 / #8A847A | Texto principal, secundario, apagado (t3 solo para filetes punteados) |
| `barra` | #1F1B16 | #12110F | Barra de la empresa |
| `lateral` | #EFE9DF | #12110F | Panel de la barra lateral |
| `acento` / `acento-t` | #1F1B16 / #FFFFFF | #EFE9DE / #1C1A18 | Botón principal (tinta en claro, blanco roto en oscuro) |
| `sel` / `sel-borde` | #FFF4C2 / #C9A227 | #2E2919 / #C9A227 | Resaltador: fila elegida, nota activa, lo que importa en una gráfica |
| `error` / `adv` / `ok` | #B42318 / #8A5A00 / #2F6B3F | #F0857C / #DDB25E / #7FBF8E | Severidad, **siempre con su palabra** |

Contrastes comprobados (WCAG AA ≥ 4,5:1 en texto): t2 sobre hoja 7,07 (claro) y 6,94 (oscuro); error sobre resaltador
5,94 y 5,77; advertencia sobre resaltador 5,35 y 7,33; t3 apagado 4,58 y 4,68.

## Tipografía

- **Instrument Sans** para toda la interfaz (400 y 500; 600 solo en la marca «Sílice»).
- **Newsreader** (400) solo en el h1 de cada vista.
- Cifras con `font-variant-numeric: tabular-nums`, coma decimal y punto de miles.
- Al implementar, las dos van **empaquetadas** con la aplicación (CSP y uso sin conexión); las maquetas las piden a
  Google Fonts solo porque son maquetas.

## Modo oscuro (guía `dark-mode` y `dark-mode-toggle` de modern-web-guidance)

- `color-scheme: light dark` en `:root` y `<meta name="color-scheme" content="light dark">` en el `<head>`; los tokens
  con `light-dark()` (y respaldo con `prefers-color-scheme` donde falte). Nada de una clase `.oscuro` que dependa de JS.
- Por defecto **sigue al sistema**. La elección vive en Cuenta › Empresa y tema, con tres estados (Claro, Oscuro,
  Como el sistema), y «Como el sistema» dice cuál es el modo actual. Se guarda en `localStorage` y se aplica con un
  script mínimo junto al `<meta>`, para que no parpadee.
- El modo oscuro solo cambia la pantalla; los PDF y el Excel que se entregan no cambian.

## Lo que no cambia

WCAG AA; la severidad nunca solo con color; coma decimal y punto de miles; trato de usted; la cifra la calcula el
servidor; fuentes empaquetadas; el tema de la empresa (`/v1/tema`) sigue mandando sobre el acento de la marca; las
decisiones D1-D8 de B1 y el movimiento funcional con movimiento reducido.

## Volver a generar las vistas

```powershell
python -I docs/especificaciones/2026-11-26-cara-papel-y-resaltador/generar_vistas.py <carpeta project del lienzo>
```

La carpeta destino debe tener el `canvas.json` del lienzo; el generador quita los tableros `S-*` viejos y pone los
nuevos. Cada fragmento lleva en su primera línea el JSON con su lugar (área, herramienta, opción, acción).
Todos los datos son ficticios.
