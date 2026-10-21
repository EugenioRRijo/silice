# Hoja 3d-2, frente: avance (restaurar, cotizar, retirar, convertir, cadena de sellos y menú activado)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `6a7f6af1` · Solo `frontend-desktop/src/paginas/hoja/`,
`src/shell/rutas.ts` y su prueba. No se tocó `src/comun/`, `ui/`, `core/`, `asistente/`, `api/`, `aplicacion/` ni `tests/`. El contrato es
`2026-10-20-hoja-3d2-contrato-rutas.md` (S2 a S6) y el diseño §4.5, §6.3 (fila 3d-2) y §7.

## Parejas prueba -> implementación

| Pareja | Prueba (rojo visto) | Implementación |
|---|---|---|
| MENOR de 3d-1: Cancelar y Esc no cierran el diálogo de guardar mientras se envía | `e05c9335` (1 en rojo) | `0769fcd7` |
| Extracción de `index.tsx` a `useVersiones.ts` y `useGuardadoDeLaPagina.ts` (sin cambio de conducta) | las pruebas existentes, verdes antes (516) y después | `d050fde7` |
| Lógica pura de S2 a S6 (rutas, cuerpos, textos de cambios pendientes, motivos, errores, insumos de precios) | `fa9f4325` (módulo inexistente) | `f7cb6a7e` |
| Diálogos, pestañas y cadena (30 pruebas de página) | `df7ec856` (30 en rojo) | `e494f6e7` |
| Menú: la Hoja migrada | `dc2f708c` (1 en rojo) | `f85f816c` |

## Qué se hizo

- **Cancelar y Esc** quedan deshabilitados/ignorados mientras `enviando` en `DialogoDeGuardar` (el error del servidor ya no se pierde).
- **Hooks extraídos de `index.tsx`** (577 -> 518 líneas): `useVersiones` (lista de versiones fresca y `recargarVersiones`) y
  `useGuardadoDeLaPagina` (modal, aviso de éxito, abrir la versión guardada o recién creada, devolver el foco). Salió además `alCrearVersion`, que
  reutilizan las cuatro operaciones nuevas.
- **Diálogos de operación** (`DialogoDeOperacion.tsx`, `role="dialog"`, `aria-modal`, `useDialogo`): foco al primer campo, Tab atrapado, Esc, el
  resto de la página `inert`, `Responsable: Nombre <login>` de solo lectura (sin campo `responsable`, RF-82), botón principal deshabilitado con el
  motivo visible y asociado por `aria-describedby`, `aria-live` «Guardando la versión…», una sola petición en vuelo (`useOperacion`), Cancelar/Esc
  ignorados mientras se envía, error del servidor tal cual (título según la operación: «No se guardó nada», «No se restauró nada», «No se convirtió
  nada») y el formulario como estaba. Se pintan por portal en un `anfitrion` hermano del contenido inerte (`ContextoDeDialogos`); al cancelar, el foco
  vuelve al botón DESPUÉS de quitar el `inert` (`useDialogoDeOperacion`, con prueba de espía de `HTMLElement.prototype.focus`).
- **Precios:** «Registrar una cotización…» (insumo, precio cotizado, proveedor, número, fecha por omisión hoy, evidencia opcional) y «Retirar una
  cotización…» (solo si hay insumos cotizados; motivo). El precio viaja como el texto escrito; la evidencia vacía como `null`.
- **Parámetros:** «Convertir la moneda…» (destino distinto de la actual, tasa venta/compra con venta por omisión, fuente); se ofrece solo si el
  servidor dice `puede_convertir`.
- **Trazabilidad:** «Restaurar una versión…» (versión, fuente) y la sección «Cadena de sellos» (S6: ícono + «Cadena íntegra» / «Cadena rota», el
  mensaje del servidor y la declaración de selladas si viene; una respuesta con forma ajena o un error se dicen sin romper la pestaña).
- **Con cambios sin guardar no se ofrece nada** (3d-F5): el aviso de P:1946, 2081 y 2201 con tildes y con el número de cambios (en singular con uno).
- **Éxito:** se muestra el `mensaje` del servidor (ya con tildes), se vuelve a leer la lista de versiones sin desmontar la página, se abre la versión
  nueva (R2) y el foco va al selector de versión.
- **Menú:** `rutas.ts` con `cargar: () => import("../paginas/hoja")`. La página ya tenía un único h1 `heading-04` dentro de `#contenido`
  (`<section class="silice-pagina silice-hoja">`; no usa `.silice-pagina-libro`, que es del visor de libros) y el marco le lleva el foco.

## Ajustes a pruebas (declarados)

Antes de implementar (rojo visto): ninguno. Después del rojo y antes del verde, al correr las pruebas contra la implementación parcial (`a8ca796b`):
(1) un `<input type="date">` no tiene rol `textbox`: la fecha se busca por su etiqueta; (2) el servidor simulado no contestaba `/vistas/espacio`
(pestaña por omisión): ahora usa `cuerpoDeVista`. Ambos son errores del arnés; la conducta esperada no cambió. Se agregaron 2 pruebas (respuesta de la
cadena vacía o sin `integra`) tras ver que una respuesta vacía rompía las pruebas de Trazabilidad de 3b-3 (que no simulan `/cadena`): `esCadena`
valida la forma. Un texto de la implementación se corrigió hacia la prueba (la descripción de convertir repite la de la clásica: «crea una versión
convertida; la actual no cambia»). Después del verde solo se añadieron esas 2 pruebas; ninguna existente cambió.

## Diferencias entre el contrato real y lo simulado

1. El contrato dice «extra prohibido» en S2, pero `api/esquemas_hoja.py` declara `RestaurarVersion` con `extra="ignore"` (los demás, `forbid`). No
   afecta al front, que no manda campos de más. Lo debe mirar el árbitro del backend.
2. El `mensaje` de las 200 lo compone el servidor con tildes; el front lo usa tal cual (en 3d-1 componía el suyo porque el del servidor decía «1
   cambios»). El texto de repuesto del cliente solo se usa si llegara vacío.
3. Los 422 de dominio de S3 y S4 llegan sin prefijo (el contrato lo deja al front): el front pone el título «No se guardó nada» y el `detalle`
   completo debajo, sin tocarlo. El de S5 ya trae su «No se convirtio nada: …» y se repite el sentido en el título (en español con tildes).
4. S2 a S5 no tienen `rev` ni 409 de concurrencia: el único 409 es el del núcleo («No se guardó nada: …», catálogo incompleto). Se muestra tal cual y
   el diálogo queda abierto; nada se sobrescribe en silencio.
5. `fecha` se manda del `<input type="date">` (AAAA-MM-DD). Por omisión es hoy con los componentes locales del navegador; el servidor juzga la fecha
   de la tasa de S5 con su propio «hoy».

## Límites y deudas

- **Sin medición de 1366x768 en navegador** (T11). Los diálogos son de una columna (32 rem) con desplazamiento propio; no se midió.
- Los diálogos viven dentro de la pestaña que los abre: si el `rev` del borrador cambia con un diálogo abierto en Precios o Trazabilidad (que se
  vuelven a montar con cada `rev`), el diálogo se cierra. Con el diálogo abierto la página está `inert`, así que solo ocurriría por un refresco desde
  otra ventana.
- La lista de «Versión a restaurar» es el historial de Trazabilidad en su orden (incluye descartadas); la clásica hacía lo mismo.
- `puede_convertir` falso (sin versión abierta o sin permiso) simplemente no ofrece el botón; no se explica por qué.
