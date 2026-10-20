# Hoja 3c-3, frente: avance (APU editable, cambio de insumo, retomar y cambio de versión)

**Fecha:** 2026-10-20 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `651f771` · Solo `frontend-desktop/src/paginas/hoja/` (no se tocó
`src/comun/`, ni `rutas.ts`, ni `ui/`, `core/`, `asistente/`, `api/`, `aplicacion/`). El contrato es `2026-10-19-hoja-3c3-contrato-rutas.md`.
Más una línea de CHANGELOG por 3c-2 y otra por 3c-3 (commit de ese archivo solo con mis dos líneas).

## Parejas prueba -> implementación

| Pareja | Prueba (rojo visto) | Implementación |
|---|---|---|
| Lógica pura del APU (rutas E6/E7/E8, cuerpos, ubicar el error, texto del estado) | `8bc05ba` (módulo inexistente) | `a735584` |
| Lógica de retomar (E10/E11: ofertas, rótulo, `borrador_id` del 409) | `30ac486` (módulo inexistente) | `93d7471` |
| Rechazo sin frase (el cambio de insumo se muestra solo, como la clásica) | `40d801e` (1 en rojo) | `31d208c` |
| Pestaña APU editable, factores y cambio de insumo (28 pruebas) | `918196d` (28 en rojo) | `6718634` |
| Retomar, diálogo de versión, borde de la pausa (28 pruebas) | `02303bd` (22 en rojo, 6 ya pasaban: describen conducta que existía) | `dcf9cb9` |
| «período» con tilde en el botón del plan secuencial | `a06ce7f` (1 en rojo) | `f9823bb` |
| Deuda DRY del espacio (motor y aviso comunes) | (refactor: las 96 pruebas de 3c-1 sin tocar) | `3d7583f` |
| Lint de la hoja (`react-hooks/set-state-in-effect`, `no-useless-assignment`) | — | `d7e2d8a` |

SHAs completos: `git log --oneline 651f771..HEAD -- frontend-desktop` (los commits `feat(api)`/`test(api)` del medio son del agente de backend).

## Qué se hizo

- **APU editable (E6):** cada línea tiene su cantidad como `TextInput` con nombre «Cantidad, {Rubro} fila {n}» y el rendimiento su campo con
  etiqueta visible; todo viaja como texto con la pausa de 400 ms, una petición en vuelo, `rev`, 409 distinguidos y 422 con
  «{detalle}. La hoja sigue con el último APU válido.» (la celda o el rendimiento quedan `aria-invalid`). ↑/↓/Esc como en el Presupuesto.
  El código de partida va con `encodeURIComponent` (puede traer «/»; el backend lo admite con `{partida:path}`).
- **Factores de la versión:** los cuatro parámetros también se editan dentro de la pestaña (`FactoresDeLaVersion`, el mismo componente de
  Parámetros en modo compacto), y el cierre se vuelve a leer al aceptarse.
- **Cambio de insumo (E7, E8):** disclosure plegado («Cambiar el insumo de una línea (en la copia de esta versión)», `aria-expanded`);
  tipo, línea, búsqueda con pausa de 300 ms (sin ella no se piden candidatos hasta abrirlo), selector nativo de candidatos
  (código · descripción · unidad · precio) y «Usar este insumo», deshabilitado hasta elegir. Hasta 300 candidatos; con más (el servidor
  dice `hay_mas` o llega el 301) pide acotar con la frase de la clásica. Sin versión abierta (`solo_lectura_insumos`) dice por qué y no pide
  nada. «Usar este insumo» **espera lo escrito**: primero sale la edición en pausa, se espera la que vuela, y la acción lleva el `rev` que
  contestó el servidor (`accionarEnOrden`). Su 422/409 se muestra tal cual, sin la frase del APU.
- **Estado de la partida:** `textoDeEstado` quita el «Estado de {clave}: » que arma el servidor; se muestra solo el texto del estado.
- **Retomar (E10, E11):** al abrir la hoja se pide `GET /v1/hoja/borradores` ANTES de abrir; si hay borradores del proyecto con cambios
  se ofrece «Retomar borrador de {proyecto} ({n} cambios)» (con varios, cada botón dice su versión) y «Descartar y abrir de nuevo»;
  mientras la persona no decide no se abre otro. Retomar lee el borrador vivo (R3, sin POST) y rehidrata: el resumen, el selector de versión,
  `beforeunload` y las tablas (cada pestaña pide su vista al borrador). Si la lista falla o no es lista, la hoja se abre igual. Si al abrir
  el servidor contesta 409 con `borrador_id` (E11), se vuelve a leer la lista y se ofrece retomarlo en vez de mostrar un error. Salir de la
  página o cambiar de proyecto con cambios no manda DELETE; sin cambios sí.
- **Cambio de versión con borrador abierto (3c-F9, P23):** con cambios, elegir otra versión abre un diálogo (`alertdialog`, `aria-modal`, foco
  adentro, Tab atrapado, Esc = «Seguir editando», el resto de la página `inert`, el foco vuelve al selector): «Tiene {n} cambios sin
  guardar. Si abre otra versión se pierden: guarde primero o descarte.» Solo «Descartar y abrir» borra el borrador (una vez) y abre la otra
  versión; si el DELETE falla no se abre y se dice por qué. No usa el Modal de Carbon (su archivo trae una URL que `npm run dist` rechaza,
  RNF-22); sigue el patrón de la confirmación de Administración.
- **MENOR (a), salir dentro de los 400 ms:** `envioPendiente.ts` anota lo que sale al desmontar (o lo que va en vuelo) a nombre del borrador;
  el descarte de la página espera esos envíos y borra solo si ninguno dejó cambios. Pruebas: el PUT sale, no hay DELETE si dejó cambios, y si
  no los dejó (valor igual o 422) el DELETE sale DESPUÉS del PUT, incluso si el PUT sigue en vuelo.
- **MENOR (b):** dos líneas de CHANGELOG (3c-2 y 3c-3 del front). La de 3c-1 del front no existe y no se agregó (no es de este encargo).
- **MENOR (c):** «período» con tilde. La clásica lo escribe sin tilde (`ui/paginas/hoja.py:1805`) pero la paridad de los textos de la interfaz se
  compara sin tildes (diseño §9.1, DV-12) y D1 exige español con tildes; la prueba cambió de expectativa a propósito (commit en rojo aparte).
- **MENOR (d), DRY:** hecho. `PestanaEspacio` usa `useEdicionDeSeccion` y `AvisoDeEdicion`; `useEdicionDelEspacio.ts` se eliminó (−222/+41
  líneas) y las 96 pruebas de 3c-1 (`Edicion`, `Vistas`, `Vistas3b3`) pasan sin tocar una línea.

## Ajustes a pruebas (declarados)

Antes de implementar (sin verde de por medio): `logicaApu.test.ts` ganó dos casos del rechazo sin frase (visto en rojo, `40d801e`).

Después de ver verde (errores de MI arnés o cambio deliberado de expectativa; los valores esperados de comportamiento no cambiaron):
- `4ed01d4` (`EdicionApu.test.tsx`): mi servidor simulado no contestaba `/vistas/espacio` (la pestaña por defecto); el buscador de escrituras
  usaba un regex que no admitía el código con «/» ya decodificado; el subtotal se busca por `title` (la cifra lleva la unidad).
- `4ed01d4` (`Vistas.test.tsx`, de 3b-2): la expectativa «Estado de AF-LLAVE|x: ADVERTENCIA: algo» pasó a «ADVERTENCIA: algo» **por encargo**:
  fijaba el código crudo que ahora se oculta. Es un cambio deliberado de expectativa, no un ajuste a la implementación.
- `3b6f812` (`Retomar.test.tsx`): (1) el aviso de verdad se distingue de los `role="alert"` vacíos de Carbon (primera corrida: 2 fallos solo en la
  corrida completa); (2) la pestaña Parámetros se abre antes de simular temporizadores (con `setTimeout` simulado `userEvent` y `findBy*` se cuelgan).
- `a06ce7f` (`Edicion3c2.test.tsx`): «periodo» -> «período» (rojo visto antes de la implementación).

## Diferencias entre el contrato real y lo simulado

Escribí las pruebas con el diseño §4.4 antes de existir el contrato; luego lo leí (`…3c3-contrato-rutas.md`) y ajusté lo siguiente:
1. **E10** responde `{ "borradores": [ {id, proyecto, version, cambios, rev, tocado} ] }` (el diseño decía una lista sola). La lógica acepta las dos
   formas; las pruebas de la página usan la real.
2. **E8** trata `limite=301` como 300 y dice `hay_mas`; la interfaz pide 301 y entiende ambas cosas (301 elementos o `hay_mas`).
3. **E6/E7** devuelven además `apu` (la vista); no se usa: se vuelve a pedir la vista (como en 3c-1/3c-2).
4. **E11 (`reemplazar`)** no se usa: «Descartar y abrir de nuevo» borra el borrador ofrecido (R4) y abre con R2. Queda disponible para 3d.
5. **E9 (`/cambios`)** no se usa: es del modal de guardar (3d).
6. Sin diferencias en los textos de los 422/409 de E6/E7 respecto de lo simulado.

## Límites y deudas

- **Dos editores a la vez en la pestaña APU** (cantidades y factores) tienen cada uno su `rev` local; si ambos mandan al mismo tiempo, el segundo
  recibe 409 de `rev` y se ofrece «Recargar el borrador». Se mitiga porque el `rev` de la página sincroniza a ambos al aceptarse el primero.
- **Cambiar de partida con una edición en la pausa** la manda en seguida (flush), pero el editor nuevo parte del `rev` de la página; si el flush
  tarda más que los 400 ms del siguiente cambio, hay un 409 recuperable.
- «Retomar» ofrece solo los borradores del proyecto abierto (la cabecera es el único selector de proyecto, DV-5).
- `Cuentas.tsx` y `DialogoDeVersion.tsx` repiten el patrón de diálogo; extraerlo a `src/comun` queda como deuda (fuera de la carpeta del encargo).
- Sin medición de 1366x768 en navegador (T11); el APU a ≥1200 px usa tres paneles y los de la derecha ganaron los factores (más altos).
- La Hoja sigue sin activarse en el menú (`rutas.ts` no se tocó). No se guarda nada (3d).
