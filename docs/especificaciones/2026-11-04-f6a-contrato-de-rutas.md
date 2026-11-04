# F6a: contrato de rutas (diseño técnico)

**Fecha:** 2026-11-04 · **Autor:** Claude (diseño técnico, según el reparto acordado con Antigravity) · **Plan:**
[PLAN_REDISENO_F6.md](../planes/PLAN_REDISENO_F6.md) · **Especificación:**
[2026-11-04-rediseno-f6-espacios-design.md](2026-11-04-rediseno-f6-espacios-design.md) · **Fuente de los permisos y
módulos:** `frontend-desktop/src/shell/rutas.ts` (`PAGINAS`) en `feature/f5-pulido`.

Este contrato es el oráculo de la Tarea 1 (cada pantalla, un solo lugar) y de las redirecciones de las Tareas 3, 5 y 6.
Ninguna pantalla cambia de permiso ni de módulo: F6 solo cambia dónde vive.

## 1. Familias de rutas (HashRouter)

| Patrón | Qué monta | Cabecera | Barra superior |
|---|---|---|---|
| `/inicio/:vista` (`general`, `pendientes`) | Inicio | «Inicio» | Dashboard empresarial · Bandeja de pendientes |
| `/obra/:carpeta/:obraId/:seccion` | La obra (sin cambios de forma; F4) | `CabeceraDeObra` | Secciones de la obra |
| `/:espacio/:herramienta` (`produccion`, `auditoria`, `precios`) | Un espacio de la empresa | Título del espacio | Sus herramientas |
| `/cuenta/:seccion` | La cuenta y la instalación | Persona, rol y «Salir de la sesión» | Secciones de la cuenta |

Reglas comunes:
- **Ruta índice** (`/`) → `/inicio/general`.
- **Espacio sin herramienta** (`/precios`) → su **primera herramienta usable** para la cuenta (no siempre la primera de la
  lista: «Precios de la empresa» exige `administrar_precios`, así que una cuenta que solo arma entra al Catálogo).
- **Herramienta desconocida** (`/precios/xyz`) → la primera usable del espacio, con `replace`.
- **Herramienta sin permiso o con su módulo apagado, escrita a mano:** el aviso de siempre de esa pantalla. Ni pantalla
  en blanco ni redirección silenciosa.
- **Espacio sin ninguna herramienta usable** (por ejemplo, Producción con el módulo apagado): el aviso «Su cuenta no
  tiene herramientas en este espacio» con un enlace al Inicio.
- Toda redirección **conserva la consulta** (`?proyecto=…`, `?envio=…`) y usa `replace`, para que «Atrás» no rebote.
- `document.title` sale de `ubicar`: «<herramienta o sección> · Sílice».

## 2. Las 31 pantallas

| Pantalla (`id`) | Título | Lugar en F6 | Ruta F6 | Ruta vieja que redirige | Acción | Módulo |
|---|---|---|---|---|---|---|
| `obras` | Resumen de la obra | Obra | `/obra/:c/:o/resumen` | (sin cambio) | — | — |
| `hoja` | Presupuesto | Obra | `/obra/:c/:o/presupuesto` | `/hoja?…` (como hoy) | `leer_proyecto` | — |
| `tramos` | Tramos de la vía | Obra | `/obra/:c/:o/tramos` | `/tramos?…` (como hoy) | `editar_hoja` | `vial` |
| `archivos` | Archivos y planos | Obra | `/obra/:c/:o/archivos` | (como hoy) | `leer_proyecto` | — |
| `versiones` | Versiones | Obra | `/obra/:c/:o/versiones` | (como hoy) | `leer_proyecto` | — |
| `aprobar` | Aprobar una versión | Obra | `/obra/:c/:o/aprobaciones` | (como hoy) | `aprobar_version` | — |
| `mercado` | Estudio de mercado | Obra | `/obra/:c/:o/mercado` | (como hoy) | `leer_proyecto` | — |
| `control` | Control de obra | Obra | `/obra/:c/:o/control` | (como hoy) | `control_de_obra` | — |
| `tablero` | Tablero del proyecto | Obra (**nueva sección**) | `/obra/:c/:o/tablero` | `/tablero?…` → la obra de la sesión, como las demás secciones | `leer_proyecto` | — |
| `riesgo` | Riesgo de la obra | Obra (**nueva sección**) | `/obra/:c/:o/riesgo` | `/riesgo?…` → ídem | `ver_riesgo` | `riesgo` |
| `produccion` | Inicio de producción | Producción | `/produccion/resumen` | `/produccion` | `operar_arenera` | `produccion` |
| `existencias` | Existencias de la arenera | Producción | `/produccion/existencias` | `/existencias`, `/empresa/produccion` | `operar_arenera` | `produccion` |
| `costos` | Costos del período | Producción | `/produccion/costos` | `/costos` | `registrar_costos_produccion` | `produccion` |
| `costo_tonelada` | Costo por tonelada | Producción | `/produccion/costo-tonelada` | `/costo_tonelada` | `registrar_costos_produccion` | `produccion` |
| `receta_planta` | Receta de la planta | Producción | `/produccion/receta` | `/receta_planta` | `operar_arenera` | `produccion` |
| `producir_mezcla` | Producir mezcla | Producción | `/produccion/mezcla` | `/producir_mezcla` | `operar_arenera` | `produccion` |
| `auditoria` | Inicio de auditoría | Auditoría | `/auditoria/subir` | `/auditoria`, `/empresa/auditoria` | — | — |
| `libros` | Libro de la empresa | Auditoría | `/auditoria/libros` | `/libros` | `leer_proyecto` | — |
| `revisar` | Revisar un paquete | Auditoría | `/auditoria/revisar` | `/revisar` | `revisar_paquete` | — |
| `historial` | Historial de auditorías | Auditoría | `/auditoria/historial` | `/historial` | `leer_proyecto` | — |
| `precios_empresa` | Precios de la empresa | Precios | `/precios/listas` | `/precios_empresa` | `administrar_precios` | — |
| `catalogo` | Catálogo de partidas e insumos | Precios | `/precios/catalogo` | `/catalogo`, `/empresa/precios` | `leer_proyecto` | — |
| `componer` | Componer una partida | Precios | `/precios/componer` | `/componer` | `editar_hoja` | — |
| `actualizacion` | Actualizar precios | Precios | `/precios/actualizar` | `/actualizacion` (sin obra en la consulta; con obra, a su Mercado como hoy, `ABSORBIDAS`) | `editar_hoja` | — |
| `indices` | Índices del BCV | Precios | `/precios/indices` | `/indices` | `administrar_precios` | — |
| `simulador` | Simulador de listas | Precios | `/precios/simulador` | `/simulador` | `editar_hoja` | — |
| `reajuste` | Reajuste de precios | Precios | `/precios/reajuste` | `/reajuste` | `convertir_y_reajustar` | — |
| `administracion` | Administración | Cuenta (repartida) | `/cuenta/cuentas` y otras (§3) | `/administracion`, `/empresa/personas` → `/cuenta/cuentas` | `administrar_cuentas` | — |
| `acerca` | Acerca de Sílice | Cuenta | `/cuenta/ayuda` | `/acerca`, `/empresa/ayuda` | — | — |
| `entregar` | Entregar paquete | Solo buscador | `/entregar` (sin cambio) | — | `entregar_paquete` | — |
| `escenarios` | Escenarios de sensibilidad | Solo buscador | `/escenarios` (sin cambio) | — | `editar_hoja` | — |

Cuenta de control: obra 10 (8 de hoy + `tablero` + `riesgo`) + Producción 6 + Auditoría 4 + Precios 7 + Cuenta 2 + solo
buscador 2 = **31**.

## 3. La Cuenta (`/cuenta/:seccion`)

| Sección | Título de la pestaña | Contenido (lo existente) | Quién la ve |
|---|---|---|---|
| `preferencias` | Pantalla y tamaño de letra | `TamanoLetra` y los datos de la cuenta | Toda cuenta |
| `cuentas` | Cuentas y permisos | Pestañas «Cuentas» y «Accesos» de `paginas/administracion` | `administrar_cuentas` |
| `empresa` | Empresa y tema | «Empresa y clave de firma» y «Empresas registradas» | `administrar_cuentas` |
| `carpetas` | Carpetas de trabajo | `CarpetasDeTrabajo` | `administrar_cuentas` **y** `cambiar_caso` (como hoy: vive dentro de Administración; el plan decía solo `cambiar_caso`, lo que habría dado acceso a quien arma, y se corrige aquí) |
| `sistema` | Especialidades, IA e instalación | «Especialidades» (`activar_modulos`), «Asistente de IA», «Claves de API» e «Instalación» | `administrar_cuentas` (Especialidades, además, `activar_modulos`) |
| `ayuda` | Ayuda y acerca de Sílice | `paginas/acerca` y el inicio de los recorridos guiados | Toda cuenta |

`/cuenta` → `/cuenta/preferencias`. Tras cambiar de carpeta se vuelve a `/cuenta/carpetas` (sustituye a
`tomarVueltaACarpetas`).

## 4. Inicio (`/inicio/:vista`)

- `/inicio/general`: el panorama (F6b). **Mientras F6b no exista**, F6a monta aquí la `Bandeja` de hoy, para no dejar el
  Inicio vacío entre las dos entregas.
- `/inicio/pendientes`: la `Bandeja`. `/pendientes` → `/inicio/pendientes`.
- `usePendientes` recarga al entrar a cualquiera de las dos.

## 5. Lo que este contrato no cambia

Ningún permiso (`accion`) ni módulo de `PAGINAS`; ninguna ruta de la API; la ruta de la obra (F4). Una prueba lo vigila:
la tabla de §2 escrita a mano en `espacios.test.ts` contra `PAGINAS`, por `id`, `accion` y `modulo`.
