# Sidebar de módulos (MOD-2): decisiones de ingeniería (2026-10-25)

**Encargo:** Tarea MOD-2 de `docs/planes/PLAN_MODULOS.md` (diseño APROBADO `docs/especificaciones/2026-10-25-modulos-design.md`,
§4 y §12). Commits: `a556d9dc` (rojo), `a6ad5ebf` (implementación), `197e815d` (estilo de la guardia), `434875b4` y el siguiente
(menores del árbitro, rojo y corrección). Árbitro: APROBADA en ronda 1, con los menores que cierra el segundo par de commits.
Todo lo que sigue son decisiones de ingeniería; las marcadas **por ratificar** las decide Eugenio.

## 1. Nombre del botón «Sílice» con el sidebar fijado

El plan da dos nombres accesibles: «Sílice, abrir los módulos» (oculto) y «Sílice, cerrar los módulos» (visible). Con el sidebar
**fijado y a la vista**, pulsar «Sílice» no lo cierra: lleva el foco al módulo actual (decisión 4 de Eugenio; ocultarlo es
«Ocultar», al pie). Decir «cerrar» sería falso, así que en ese estado el nombre es **«Sílice, ir a los módulos»**
(`aria-expanded="true"`). Todos empiezan por «Sílice», el texto que se ve (WCAG 2.5.3).

## 2. Interfaz ampliada respecto del plan (sin quitar nada)

- `useClicSeguro(to, alNavegar?)` en `EnlaceSeguro.tsx`: el renglón de cada módulo del sidebar lleva al inicio del módulo pero
  marca `aria-current="page"` aunque la pantalla abierta sea otra del módulo; `NavLink` solo lo marca en su propia ruta, así que
  ese renglón es un `Link` con el mismo manejador de clic seguro.
- `ID_SIDEBAR` e `ID_BOTON_SILICE` en `sidebar.ts`: los usan el `aria-controls` de la barra, el regreso del foco y la regla de Esc
  («Sílice» abierto no cuenta como control de la barra desplegado).
- Prop opcional `paginas` en `SidebarModulos` (por omisión `PAGINAS`): el inicio de cada módulo sale del registro del armazón,
  que las pruebas cambian.
- Además: `cancelarSalida`, `responderSalida`, `useSalidaPendiente` y `unirConY` (`salida.ts`); `estadoSidebar` e
  `iniciarSidebar` (`sidebar.ts`); `leerFijadoPosible` (`useFijadoPosible.ts`); `useAtraparFoco` y `primerEnfocable`
  (`useAtraparFoco.ts`, un solo foco atrapado para el sidebar en capa y «Cambios sin guardar»).
- `hoja/useDialogo.ts` y `paginas/administracion/Cuentas.tsx` siguen con su propio foco atrapado: pasarlos a `useAtraparFoco`
  queda para después (no son archivos de MOD-2).

## 3. Esc y los tooltips de Carbon

Un solo oyente de Esc en `document`, en fase de burbuja: lo que tiene su propio Esc y detiene la propagación (panel de área,
cuenta, carpeta, la lista de `CampoConBusqueda`, el diálogo de salida, el propio sidebar) lo atiende antes. Esc abre el sidebar
solo si `esEscParaElSidebar` lo permite: no es sobre un campo, algo editable (`isContentEditable`, que el navegador calcula con
herencia y sin mayúsculas), una tabla editable (`role="grid"`), un control desplegable o un diálogo; no hay ningún diálogo modal
abierto ni ningún control de la barra desplegado salvo «Sílice».

El `Tooltip` de Carbon (indicadores Fiori, montos del historial) cierra con Esc desde **su propio oyente en `document`**, incluso
abierto solo con el ratón y el foco fuera; dos oyentes en el mismo nodo no se detienen entre sí. Por eso la regla también
devuelve `false` si hay un `.cds--popover--open` en el documento: ese Esc cierra el tooltip y no abre el sidebar (menor 1 del
árbitro).

## 4. Fijado sin ancho (**por ratificar con Eugenio**)

«Fijar» solo se ofrece cuando hay ancho para fijarlo (1366 px con letra Normal; 1708 y 2049 px con Grande y Muy grande). Si la
cuenta lo tiene fijado y la ventana es más angosta, se comporta como oculto: «Sílice» lo abre en capa y **esa capa no muestra
«Fijar» ni «Ocultar»**. Consecuencia: no se puede quitar el fijado hasta tener una ventana más ancha. Alternativa si Eugenio la
prefiere: mostrar «Dejar de fijar» en esa capa.

Si la capa está abierta con el fijado sin ancho y la ventana se ensancha, el sidebar pasa a franja y la capa se da por cerrada:
al estrecharse otra vez no reaparece sola ni le quita el foco a la página (menor 2 del árbitro).

## 5. «Pantallas del módulo» sigue con `Link`

`AccesosDelModulo.tsx` (MOD-1, en los inicios de los módulos) usa `Link`, no `EnlaceSeguro`: desde un inicio no se pregunta
antes de salir. Hoy ningún inicio tiene formularios que se ensucien. Si la mesa de control (MOD-4b) los tiene, su tarea lo
cambia. Tampoco hay todavía ninguna pantalla real que registre `useFormularioSucio`: hasta que Componer y los demás formularios
lo hagan, la pregunta «Cambios sin guardar» no aparece en el uso real.

## 6. Ventana sin compilar en la historia: `136f8647` a `5264483a`

El borrado de `MenuEnCapa.tsx`, `MenuEnCapa.scss` y `MenuEnCapa.test.tsx` quedó preparado en el índice compartido y entró en el
commit `136f8647` («chore: compartidos de MOD-4a»), antes del commit de la implementación (`a6ad5ebf`). En `136f8647`,
`92adbfb4` y `5264483a`, `Shell.tsx` aún importa `MenuEnCapa`: el front **no compila**. El orquestador asume la culpa: hizo
ese commit con el índice compartido sin revisar `git diff --cached`. El implementador tampoco debió dejar el borrado preparado
antes de su commit; desde entonces prepara y hace el commit en un solo paso, por ruta. No se reescribe la historia de una rama en la que trabajan varios
agentes. Un `git bisect` debe saltar esos tres commits (`git bisect skip 136f8647 92adbfb4 5264483a`).
