# F6: contrato de rutas (diseño técnico)

**Fecha:** 2026-11-04 (versión 2, con las decisiones de Eugenio del mismo día) · **Autor:** Claude (diseño técnico, según el
reparto acordado con Antigravity) · **Plan:** [PLAN_REDISENO_F6.md](../planes/PLAN_REDISENO_F6.md) · **Fuente de permisos y
módulos:** `frontend-desktop/src/shell/rutas.ts` (`PAGINAS`) en `main` (`febf6673`).

Es el oráculo de las tareas T1 (ruta canónica), T2 (cada pantalla, un solo lugar), T4 a T6 (redirecciones) y T8 (Inicio).
**Ninguna pantalla cambia de permiso ni de módulo:** F6 solo cambia dónde vive cada una.

## 1. Familias de rutas (HashRouter)

| Patrón | Qué monta | Cabecera | Barra |
|---|---|---|---|
| `/inicio/:vista` (`general`, `pendientes`) | Inicio | «Vista general» | Vista general · Pendientes |
| `/obra/:carpeta/:obraId/:seccion` | La sección de la obra (su pantalla principal) | `CabeceraDeObra` | Secciones de la obra |
| `/obra/:carpeta/:obraId/:seccion/:subvista` | Una subvista de esa sección | `CabeceraDeObra` | Secciones de la obra; dentro de la sección, sus subvistas |
| `/:espacio/:herramienta` (`produccion`, `auditoria`, `precios`) | Un espacio de la empresa | Título del espacio | Sus herramientas |
| `/cuenta/:seccion` | La cuenta y la instalación | Persona, rol y «Salir de la sesión» | Secciones de la cuenta |

Reglas comunes:
- **Ruta índice** (`/`) → `/inicio/general` (la Vista general, que pone primero lo que bloquea; decisión de Eugenio).
- **Espacio sin herramienta** (`/precios`) → la **primera herramienta usable** para la cuenta.
- **Herramienta, sección o subvista desconocida** → la primera usable de su nivel, con `replace`. Si ninguna es usable, la
  primera definida, que muestra el aviso existente (`MENSAJE_SIN_PERMISO` o `MENSAJE_APAGADA`, `Marco.tsx:52-53`): sin
  texto nuevo y sin bucle.
- **Sin permiso o con el módulo apagado, escrita a mano:** el aviso de siempre de esa pantalla, nunca una pantalla en
  blanco.
- Toda redirección **conserva la consulta** (`?proyecto=…`, `?envio=…`) y usa `replace`.
- `document.title` sale de `ubicar`: «<pantalla> · Sílice».
- **Una sola ruta canónica por pantalla**, `rutaCanonica(paginaId, obra?)`. La usan el enrutador, el buscador, el
  recorrido guiado, los pendientes y todo enlace interno; ninguna ruta se escribe a mano.

## 2. Las 31 pantallas

**Enmienda 2026-11-05:** el registro tiene 32 pantallas. «inicio» (la Vista general, `/inicio/general`) es la 32.ª y vive fuera de las tablas de obra, Producción, Auditoría, Precios y Cuenta: se describe en §4. Las 31 de este apartado no cambian.

### 2.1. Obra: 9 secciones y 7 subvistas

| Pantalla (`id`) | Título | Ruta F6 | Acción | Módulo |
|---|---|---|---|---|
| `obras` | Resumen de la obra | `/obra/:c/:o/resumen` | — | — |
| `tablero` | Tablero del proyecto | `/obra/:c/:o/resumen/tablero` (subvista) | `leer_proyecto` | — |
| `hoja` | Presupuesto | `/obra/:c/:o/presupuesto` | `leer_proyecto` | — |
| `componer` | Componer una partida | `/obra/:c/:o/presupuesto/componer` (subvista; en la Hoja sigue también su panel) | `editar_hoja` | — |
| `tramos` | Tramos de la vía | `/obra/:c/:o/tramos` | `editar_hoja` | `vial` |
| `archivos` | Archivos y planos | `/obra/:c/:o/archivos` | `leer_proyecto` | — |
| `versiones` | Versiones | `/obra/:c/:o/versiones` | `leer_proyecto` | — |
| `aprobar` | Aprobar una versión | `/obra/:c/:o/aprobaciones` | `aprobar_version` | — |
| `revisar` | Revisar un paquete | `/obra/:c/:o/aprobaciones/revisar` (subvista) | `revisar_paquete` | — |
| `entregar` | Entregar paquete | `/obra/:c/:o/aprobaciones/entregar` (subvista) | `entregar_paquete` | — |
| `mercado` | Estudio de mercado | `/obra/:c/:o/mercado` | `leer_proyecto` | — |
| `actualizacion` | Actualizar precios | `/obra/:c/:o/mercado/actualizar` (subvista) | `editar_hoja` | — |
| `control` | Control de obra | `/obra/:c/:o/control` | `control_de_obra` | — |
| `reajuste` | Reajuste de precios | `/obra/:c/:o/control/reajuste` (subvista) | `convertir_y_reajustar` | — |
| `escenarios` | Escenarios de sensibilidad | `/obra/:c/:o/control/escenarios` (subvista) | `editar_hoja` | — |
| `riesgo` | Riesgo de la obra | `/obra/:c/:o/riesgo` | `ver_riesgo` | `riesgo` |

Eugenio no ubicó «Riesgo» en su respuesta: se deja como sección propia, como en el plan aprobado, y queda anotado como
pregunta (§5). Una sección cuya pantalla principal no es usable pero que tiene una subvista usable (por ejemplo,
Aprobaciones para quien solo puede revisar paquetes) se ofrece y abre en esa subvista.

### 2.2. Espacios de la empresa (barra lateral «Costos y producción»)

| Espacio | Segmento → pantalla (en orden; abre la primera usable) | Acción | Módulo |
|---|---|---|---|
| Producción | `resumen`→`produccion`, `existencias`→`existencias`, `costos`→`costos`, `costo-tonelada`→`costo_tonelada`, `receta`→`receta_planta`, `mezcla`→`producir_mezcla` | `operar_arenera` o `registrar_costos_produccion` | `produccion` |
| Auditoría | `subir`→`auditoria`, `libros`→`libros`, `historial`→`historial` | —, `leer_proyecto`, `leer_proyecto` | — |
| Precios y catálogo | `listas`→`precios_empresa`, `catalogo`→`catalogo`, `indices`→`indices`, `simulador`→`simulador` | `administrar_precios`, `leer_proyecto`, `administrar_precios`, `editar_hoja` | — |

### 2.3. Cuenta

`administracion` (repartida en secciones, §3) y `acerca` (`/cuenta/ayuda`).

**Cuenta de control:** obra 16 (9 secciones + 7 subvistas) + Producción 6 + Auditoría 3 + Precios 4 + Cuenta 2 = **31**.
Ninguna pantalla queda solo en el buscador.

**Enmienda 2026-11-05:** «inicio» no entra en esta cuenta: es la 32.ª pantalla del registro (`shell/rutas.ts`) y vive en §4, fuera de las tablas de obra, Producción, Auditoría, Precios y Cuenta. Con ella, el registro suma 32.

### 2.4. Redirecciones desde rutas viejas (conservan la consulta)

| Ruta vieja | Destino |
|---|---|
| `/pendientes` | `/inicio/pendientes` |
| `/<seccion>?…` de una pantalla de obra (`/hoja`, `/tablero`, `/reajuste`, `/revisar`…) | su ruta de obra con la obra de la sesión, como hoy hace `Marco.tsx:437-442`; sin obra, a Pendientes (con una excepción, abajo) |
| `/produccion`, `/existencias`, `/costos`, `/costo_tonelada`, `/receta_planta`, `/producir_mezcla` | `/produccion/<segmento>` |
| `/auditoria`, `/libros`, `/historial` | `/auditoria/<segmento>` |
| `/precios_empresa`, `/catalogo`, `/indices`, `/simulador` | `/precios/<segmento>` |
| `/empresa/precios` | `/precios/catalogo` (abre lo mismo que abría en F4) |
| `/empresa/auditoria` | `/auditoria/subir` |
| `/empresa/produccion` | `/produccion/existencias` |
| `/administracion`, `/empresa/personas` | `/cuenta/cuentas` |
| `/acerca`, `/empresa/ayuda` | `/cuenta/ayuda` |

**Excepción (enmienda 2026-11-05, tal como la aplica `Marco.tsx`, `RutaVieja`):** una ruta vieja de una sección **o de una
subvista** de la obra (`/aprobar`, `/hoja`, `/reajuste`, `/entregar`…) que trae consulta (`?…`) y no encuentra obra en la
sesión **no** va a Pendientes: se abre donde estaba, con su consulta, para no perder lo que pide (por ejemplo
`/aprobar?envio=12` o `/reajuste?x=1`). Sin consulta y sin obra, sigue yendo a Pendientes.

Un pendiente de «actualizar precios» es de una obra: abre `/obra/:c/:o/mercado/actualizar`, lo que reemplaza a
`ABSORBIDAS` de `paginas/pendientes/logica.ts`.

## 3. La Cuenta (`/cuenta/:seccion`)

| Sección | Título de la pestaña | Contenido (lo existente) | Quién la ve |
|---|---|---|---|
| `preferencias` | Pantalla y tamaño de letra | `TamanoLetra` y los datos de la cuenta. **Es el único lugar del tamaño de letra** dentro del marco (decisión de Eugenio, 2026-11-04; enmienda R9 a DESIGN.md). Antes de entrar sigue en `CabeceraSinMarco` (`App.tsx`) | Toda cuenta |
| `cuentas` | Cuentas y permisos | «Cuentas» y «Accesos» de `paginas/administracion` | `administrar_cuentas` |
| `empresa` | Empresa y tema | «Empresa y clave de firma» y «Empresas registradas» | `administrar_cuentas` |
| `carpetas` | Carpetas | `CarpetasDeTrabajo` (la guardia de jerga prohíbe «carpeta de trabajo» en `src/marco/`) | `administrar_cuentas` **y** `cambiar_caso`, como hoy |
| `sistema` | Especialidades, IA e instalación | «Especialidades» (además `activar_modulos`), «Asistente de IA», «Claves de API» e «Instalación» | `administrar_cuentas` |
| `ayuda` | Ayuda y acerca de Sílice | `paginas/acerca` y el inicio de los recorridos guiados | Toda cuenta |

`/cuenta` → `/cuenta/preferencias`. Tras cambiar de carpeta se vuelve a `/cuenta/carpetas` (sustituye a
`tomarVueltaACarpetas`).

## 4. Inicio (`/inicio/:vista`)

- `/inicio/general`, la **Vista general**. Primero lo que bloquea; después los indicadores de la cartera **separados por
  moneda** (Bs y USD, sin sumar entre monedas), que salen de una ruta nueva del servidor (`GET /v1/obras/resumen/todas`,
  T7). Al final, las últimas auditorías y la arenera.
- `/inicio/pendientes`: la `Bandeja`.
- `usePendientes` recarga al entrar a cualquiera de las dos.

## 5. Preguntas abiertas para Eugenio

1. ¿«Riesgo de la obra» queda como sección propia de la obra o pasa a subvista de Control de obra?
2. ¿Quien revisa debe ver las obras de todas las carpetas? (Hoy solo ve la de la empresa.)
