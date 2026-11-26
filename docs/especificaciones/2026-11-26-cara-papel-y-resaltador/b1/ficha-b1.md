# Ficha de B1: superficie «Presupuesto» (T1, T2 y T3)

- **Fecha:** 2026-11-25.
- **Árbol:** `.worktrees/s4`, rama `feature/front-b0`. Las rutas son relativas a `frontend-desktop/src/` salvo que digan
  otra cosa.
- **Método:** skills `disenar-desde-la-tarea` e `interfaz-silice`, más `reglas-b1.md` (guía de Google, ui-ux-pro-max y
  ub-mode).
- **Límites:** `core/`, lo sellado por `reglas-congeladas-2026-11-24` y `aplicacion/hoja.py` no cambian. **B1 no necesita
  cambiar el back**: todas las rutas existen (§3.3).

---

## 1. Ficha de la pantalla

### 1.1 Historia de trabajo
Cuando abro una obra, quiero ver de una vez cuánto cuesta, qué partidas tiene y qué está mal, **para poder corregirla,
agregarle lo que falta y dejarla lista para guardar la versión**.

Necesito el total y los problemas a la vista sin cambiar de pestaña, para no tener que recordar una cifra de otra
pantalla (UX-01).

### 1.2 De dónde viene y a dónde va
- **Viene de:**
  - la Vista general o la barra lateral, al abrir la obra (hoy abre en Resumen: `marco/BarraLateral.tsx:99`,
    `marco/busqueda.ts:45`; ver la decisión D1);
  - Componer, con «Agregar X al presupuesto» (`paginas/componer/index.tsx:48`);
  - Versiones y Mercado, con `?version=` (`paginas/versiones/index.tsx:84`,
    `paginas/mercado/CotizacionesDeLaObra.tsx:150`);
  - los Pendientes con `pagina: "hoja"` (`paginas/pendientes/logica.test.ts:51`).
- **Va a** (control visible en cada éxito):
  - tras agregar o editar: «Guardar versión…», el principal que ya calcula `paginas/hoja/pasoDelPresupuesto.ts:47-65`;
  - tras guardar: «Envíe V a aprobación», de la misma regla;
  - desde un problema: la partida que lo causa, con su inspector abierto.

### 1.3 Quién la usa y qué sabe
- **Economistas que presupuestan obras viales y viven en Excel** (3 de las 5 personas). Esperan:
  - densidad y teclado de Excel: flechas, Enter, F2 y Esc;
  - el total siempre a la vista;
  - nada de ayudas que tengan que leer cada vez.
- **Personas que presupuestan pero no conocen Sílice** (2 de 5). No saben:
  - que «componer» es crear el análisis de precio unitario (APU);
  - qué es un rendimiento;
  - dónde se dice si algo está mal.
- **Cómo se sirve a los dos** (inversión por pericia):
  - una línea con un ejemplo en cada campo con jerga, y la ayuda larga en «¿Qué es esto?»;
  - los rótulos usan las palabras de la consigna: «Crear la partida», «Problemas».

### 1.4 Camino crítico (análisis jerárquico de tareas)
| Subtarea | Frecuencia | ¿Crítica? |
|---|---|---|
| Leer el total de la obra | siempre | sí (T1) |
| Ver qué partidas tienen problemas y por qué | siempre | sí (T3) |
| Cambiar una cantidad en su celda | siempre | sí |
| Agregar una partida del catálogo con su cantidad | casi siempre | sí (T2) |
| Crear una partida que no existe (componer su APU) | a veces | sí en T2 |
| Abrir el APU de una partida y ajustarlo | a veces | no |
| Guardar la versión | al cerrar la sesión de trabajo | sí (paso siguiente) |
| Quitar una partida, ver cómo se midió, volver a la calculada, objetivo de mercado | ocasional | no |
| Descargar Excel o PDF, subtotales por frente, traer un plano o un cómputo, descartar cambios | ocasional | no |
| Espacio y metrajes, plan, precios de insumos, ajustes de costo | ocasional | no (vista «Espacio, plan y ajustes») |

### 1.5 Tipo de vista y frase de respuesta
- **Tipo:** editor de hoja con un inspector lateral no modal (UX-19, UX-23).
- **Pregunta que responde:** «¿Cuánto cuesta esta obra y qué tiene que revisar?».
- **Frase de respuesta**, encima de la grilla. La escribe una función pura que **solo cuenta** filas y hallazgos; los
  montos vienen del servidor:
  - «El presupuesto suma **1.234.567,89 Bs** sin IVA en **12 partidas**. **3 partidas tienen problemas**: 1 error y
    2 advertencias. Ver los problemas»;
  - sin hallazgos: «… Sílice revisó 18 reglas y no halló problemas.», con el texto `sin_hallazgos` del servidor
    (`api/tipos.ts:257`).

### 1.6 Reparto de controles
**A la vista (8 decisiones, en el orden de tabulación = orden visual):**
1. «Problemas (3)», en la cabecera fija: abre el inspector en «Problemas».
2. El **único principal**, en la cabecera fija: el paso que toca (`pasoDelPresupuesto`): «Agregar la primera partida»,
   «Guardar versión…» o «Envíe V a aprobación».
3. «Más acciones del presupuesto»: un menú con `popover` (guía `dialog`, sección de menús).
4. La grilla de partidas: **una sola parada de Tab** (guía `spatial-navigation`). Columnas:
   - Partida, Descripción, Unidad;
   - Cantidad (editable);
   - Precio unitario y Total;
   - Problemas: ícono, palabra y texto corto.
5. «Partida», en la fila de alta: búsqueda por código o descripción, con el ejemplo «por ejemplo, bloque».
6. «Cantidad», en la fila de alta: `CampoDeCifra` con `inputmode="decimal"` y la ayuda «Con coma decimal: 50 o 12,5».
7. «Agregar al presupuesto», terciario. No se deshabilita para validar (guía `forms`).
8. El pliegue «Cálculo y nota (opcional)».

**Lo que no cuenta como decisión y no entra en la prueba de conteo:**
- el botón «Ver el valor exacto» del total (`MontoExacto`): es una ayuda de lectura;
- el «¿Qué es esto?» del marco.

**En «Más opciones» (un solo nivel), cada una con su valor por omisión dicho:**
- **Pliegue de la fila de alta.** Su resumen: «Sin cálculo ni nota. Cambiar». Tiene dos campos:
  - Cálculo (opcional), con el ejemplo `6*3-2`;
  - Nota de medición (opcional).
- **Menú «Más acciones del presupuesto»:**
  - Descargar Excel y Descargar PDF: hoy van a la vista en `paginas/hoja/FranjaDelPresupuesto.tsx:146`;
  - Subtotales por frente (`PresupuestoPorFrentes`), en el inspector;
  - Traer un plano o un cómputo, que lleva a Archivos y planos;
  - «Espacio, plan y ajustes», la vista por pestañas;
  - Descartar los cambios, que pide confirmar. Hoy está a la vista en `paginas/hoja/EstadoDelBorrador.tsx:34-38`.
- **Inspector de la partida** (al abrir una fila). Su resumen: «Medida sin cálculo; cantidad escrita a mano». Contiene:
  - cómo se midió;
  - la cantidad calculada y «Volver a la calculada»;
  - el precio unitario y el total exactos (`MontoExacto` en línea);
  - el objetivo de mercado;
  - el APU (`EditorDeApu`);
  - «Quitar del presupuesto».

### 1.7 Punto de partida
- **La obra abre en el borrador de la versión vigente**, con su total y sus problemas ya leídos (`ProveedorDeLaHoja`,
  que no cambia).
- **Si queda un borrador con cambios**, se ofrece retomarlo (`paginas/hoja/OfertaDeRetomar.tsx`, que se reutiliza).
- **Al buscar una partida en la fila de alta:**
  - si no aparece, la última sugerencia dice «Crear la partida «friso de pared»» y debajo salen las «Parecidas»
    (`paginas/hoja/Parecidas.tsx`);
  - el inspector de creación arranca con la descripción escrita y ofrece «Similares», con «Empezar desde esta»
    (lote 2 de la ficha de Componer, ya construido).
- **Al llegar desde la subvista Componer**, la fila de alta abre con la partida elegida y el foco en «Cantidad».

### 1.8 Tabla de estados
Cada estado lleva **un** control al paso siguiente.

| Estado | Qué ve la persona | Paso siguiente |
|---|---|---|
| Cargando | La cabecera de la grilla con sus columnas reales y filas de esqueleto, sin cifras inventadas. El total dice «Calculando…» **sin región viva** (guías `spinner` y `accessibility`: «Don't use live regions for interstitial states») | — (espera) |
| Vacío | «Esta obra aún no tiene partidas» (`EstadoVacio`). El principal de la cabecera es «Agregar la primera partida» y lleva el foco a «Partida». El secundario es «Traer un cómputo (.csv)» | «Agregar la primera partida» |
| Error al leer | `AvisoError` con el detalle del servidor | «Reintentar» (`recargar` de `useRecurso`) |
| Error al escribir (422 o 409) | La celda o el campo marcado, con el texto del servidor al lado (`AvisoDeEdicion`). **Lo escrito no se borra**. Un 409 por `rev` vuelve a leer el borrador | Corregir; «Recargar el borrador» si es 409 |
| Borrador ausente (404) | «El borrador ya no está» (`paginas/hoja/index.tsx:274-281`) | «Abrir de nuevo» |
| Parcial | Las partidas sin precio dicen «Pendiente» **en texto**, y «Problemas» las cuenta. Si falla la revisión pero la tabla carga, la frase dice «No se pudo revisar el presupuesto» | «Reintentar la revisión» |
| Éxito al agregar | La fila nueva queda en la grilla, con el foco en su celda Cantidad. El total de la cabecera cambia. El anunciador dice **una vez** «Se agregó FRI-01 al presupuesto. Total: …» | «Guardar versión…» (principal) |
| Éxito al guardar | `AvisoDeGuardado` (`comun/AvisoDeGuardado.tsx:11`), que **se queda** hasta que se cierra. El principal pasa a «Envíe V a aprobación» | «Envíe V a aprobación» |
| Sin permiso (quien revisa) | La nota «Está viendo este presupuesto en solo lectura» (`paginas/hoja/index.tsx:136`). Cambia lo siguiente: no hay fila de alta; las cantidades son texto; los problemas y el total se ven igual | «Problemas» |
| Sin `leer_proyecto` | La sección dice «Sin permiso» (`marco/EspacioDeObra.tsx:160, 189`, sin cambio) | — |

### 1.9 Supuestos de negocio (por confirmar)
Ninguno se presenta como regla.

| # | Supuesto | Lo confirma |
|---|---|---|
| S1 | El total de la cabecera es el **sin IVA** (`resumen.total`, `paginas/hoja/logica.ts:208`). El total con IVA va en la línea de abajo, y para T1 vale cualquiera de los dos si la persona dice cuál lee | Eugenio (D2) |
| S2 | «Problemas» cuenta CRÍTICO, ERROR y ADVERTENCIA. INFO no cuenta, igual que `esFilaAfectada` (`paginas/hoja/pasoDelPresupuesto.ts:74, 82-84`) | Eugenio |
| S3 | «Agrupados por causa» se hace por la regla que revisó Sílice (`reglas_evaluadas[].nombre`). `aplicacion/causas_raiz.py` es de los libros y está sellado | Eugenio |
| S4 | La obra de la prueba es civil o vial, sin espacio, con al menos un hallazgo, sin «friso de pared» en el catálogo y **restaurada antes de cada sesión** | Eugenio (D5) |
| S5 | Hasta 500 filas, sin paginar, con una respuesta al editar de menos de 200 ms. Se **mide** antes de optimizar (RNF-11) | Medición del lote B1-12 |
| S6 | La pantalla de referencia mide 1366 × 768. El panel ancho no cabe junto a la tabla y pasa por encima (`comun/PanelLateral.tsx:21-23`) | Eugenio |
| S7 | Quitar una partida pide confirmación, porque no existe una ruta para deshacer | Eugenio (D7) |

### 1.10 Pruebas que la fijan
Son pruebas de Testing Library, por rol y por nombre, sobre `datosDePrueba.ts`, con datos ficticios.
1. Hay 8 controles de decisión a la vista por omisión, o menos. Se cuentan `button`, `link`, `textbox`, `combobox`,
   `grid` y `summary` dentro de la superficie, sin «Ver el valor exacto».
2. La frase de respuesta precede a la grilla en el DOM, y la cabecera tiene un solo botón principal.
3. El total sale en es-VE, con su valor exacto en el `Toggletip` y **sin atributo `title`** (guía `accessibility`).
4. Al agregar, la fila nueva existe, el foco queda en su celda Cantidad y hay **un** anuncio.
5. Un 422, en la fila de alta o en una celda, deja lo escrito tal cual y marca el campo con texto, no solo con color.
6. La grilla:
   - tiene una sola parada de Tab;
   - las flechas mueven la celda activa;
   - en el borde no se llama a `preventDefault`;
   - con Ctrl, Alt o Meta no se intercepta nada;
   - F2 o Enter editan y Esc restaura.
7. El inspector:
   - el foco entra a su `h2`;
   - Tab puede salir, porque no atrapa el foco cuando va acoplado;
   - «Cerrar» está a la vista;
   - Esc devuelve el foco a la celda que lo abrió.
8. Elegir un problema lleva el foco a la fila que lo causa, y la severidad se dice con una palabra.
9. Sin permiso no hay fila de alta ni celdas editables.
10. Mientras carga, el esqueleto tiene las cabeceras de la grilla, ninguna cifra y ninguna región viva con texto.

---

## 2. Recorrido cognitivo
Las cuatro preguntas son:
- **P1:** ¿la persona intentará esto?
- **P2:** ¿verá el control?
- **P3:** ¿lo asociará con lo que quiere?
- **P4:** ¿entenderá la respuesta?

Se recorre sobre el diseño de §1. ✔ = pasa; ✖ = falla, con su arreglo ya incluido en la ficha.

### T1: «Abra la obra de demostración y vea cuánto cuesta su presupuesto» (5 min)
| Paso | P1 | P2 | P3 | P4 | Veredicto y arreglo |
|---|---|---|---|---|---|
| 1. En la Vista general, abrir la obra | ✔ | ✔ La obra está en la barra lateral y en la lista | ✔ | ✔ La obra se abre | Hoy abre en Resumen (`marco/BarraLateral.tsx:99`). Con D1 abre en Presupuesto |
| 2. Leer el total | ✔ | ✔ El total está en la cabecera fija, arriba y a la izquierda del principal. Hoy también está, pero con `title` y `aria-live` (`paginas/hoja/EstadoDelBorrador.tsx:30-33`) | ✔ Dice «Total sin IVA» | ✖ Hay dos cifras (sin y con IVA): ¿cuál es «cuánto cuesta»? | Las dos llevan su rótulo; la hoja de observación acepta cualquiera (S1, D2) |
| 3. Leerlo en voz alta | ✔ | ✔ | ✔ | ✔ Con coma decimal y la moneda | Una lectora de pantalla oye «Total sin IVA 1.234.567,89 Bs», sin los dígitos exactos repetidos (hoy los repite: `paginas/hoja/Cifra.tsx:8-11`) |
| **Más allá:** ¿y ahora qué? | ✔ | ✔ El principal dice el paso que toca | ✔ | ✔ | La frase de respuesta ya dice «3 partidas tienen problemas»: da pie a T3 |

### T2: «Cree una partida nueva (friso de pared) con un material y la mano de obra, y déjela con cantidad 50» (15 min)
| Paso | P1 | P2 | P3 | P4 | Veredicto y arreglo |
|---|---|---|---|---|---|
| 1. Buscar dónde agregar | ✔ | ✖ Con muchas filas, una fila de alta al pie queda bajo el pliegue | ✔ | — | La grilla se desplaza dentro de su región, con su altura acotada, y la fila de alta va debajo, **siempre en la primera pantalla** (UX-20; guía `responsive-table`, encabezados fijos) |
| 2. Escribir «friso de pared» en «Partida» | ✔ | ✔ | ✔ Por el ejemplo de la ayuda | ✔ Sin resultados se ve «¿No la encuentra?» | — |
| 3. Elegir la opción para crearla | ✔ | ✔ Es la última sugerencia | ✖ Hoy dice «Componer una partida nueva con la descripción…» (`paginas/hoja/AgregarPartida.tsx:269`), y la consigna dice «Cree» | — | Rótulo «Crear la partida «friso de pared»» (D4) |
| 4. Llenar código, unidad, un material, la mano de obra y el rendimiento en el inspector | ✔ | ✔ Lote 3 de Componer: lo ocasional va plegado | ✖ La persona nueva no sabe qué es el rendimiento | ✔ El precio unitario se ve en vivo | Ayudas con ejemplo y «Similares» (lote 2 de Componer, hecho). Si aun así falla, la prueba lo mostrará: no se rediseña Componer en B1 |
| 5. «Guardar la partida en el catálogo» | ✔ | ✔ | ✔ | ✖ Hoy vuelve con el foco en «Partida» (`paginas/hoja/AgregarPartida.tsx:173-176`) y no en Cantidad | El inspector se cierra, la fila de alta queda con «FRI-01 · Friso de pared (m2)» elegida, **el foco va a Cantidad** y se anuncia una vez «La partida quedó en el catálogo. Escriba su cantidad.» |
| 6. Escribir 50 y pulsar Enter | ✔ | ✔ | ✔ | ✔ La fila aparece con el foco en su cantidad y el total cambia | La tarea termina |
| **Más allá:** ¿quedó guardado? | ✔ | ✔ El principal pasa a «Guardar versión…» y la línea de estado dice «1 cambio sin guardar» | ✔ | ✔ | — |
| Error: escribe «50.5» | ✔ | ✔ | ✔ | ✔ El error sale al salir del campo y dice «Use la coma…» | Guía `validate-input-after-interaction`. Lo escrito se conserva |

### T3: «Diga si el presupuesto tiene algún problema que conviene revisar, y cuál» (5 min)
| Paso | P1 | P2 | P3 | P4 | Veredicto y arreglo |
|---|---|---|---|---|---|
| 1. Buscar si hay problemas | ✔ | ✔ En tres lugares: «Problemas (3)» en la cabecera, la frase sobre la grilla y la columna Problemas. Hoy hay que ir a la pestaña «Revisión» (`paginas/hoja/logica.ts:27`) | ✔ La misma palabra de la consigna (riesgo de validez: D6) | ✔ | — |
| 2. Abrir la lista | ✔ | ✔ | ✔ | ✔ «3 problemas en 2 partidas», agrupados por regla, cada uno con su severidad en palabra, la partida y la descripción del servidor | — |
| 3. Decir uno en voz alta | ✔ | ✔ | ✔ | ✔ | La tarea termina |
| Sin hallazgos | ✔ | ✔ | ✔ | ✔ «Sílice revisó 18 reglas y no halló problemas» | La persona puede decir que no hay, con su razón |
| **Más allá:** corregirlo | ✔ | ✔ «Ir a la partida» | ✔ | ✔ La fila queda activa y su inspector muestra el APU | — |

---

## 3. Lo que se reutiliza y lo que se retira

### 3.1 Se reutiliza tal cual
- **`paginas/hoja/ProveedorDeLaHoja.tsx`:** el borrador, las versiones, guardar y retomar (`HojaDeLaObra`, líneas 43-83).
  Lo monta `marco/EspacioDeObra.tsx:220-224`.
- **`paginas/hoja/pasoDelPresupuesto.ts:47-65`:** la regla pura del paso, que da el único principal.
- **`paginas/hoja/AprobacionDeVersion.tsx`, `paginas/hoja/useAprobacionDeVersion.ts` y `comun/FranjaDelPaso.tsx`.**
- **`paginas/hoja/useEdicionDeSeccion.ts`:** el motor de la pausa, el `rev`, el 409 y el 422. Junto con
  `paginas/hoja/logicaSecciones.ts:9` (`rutaDeCantidades`) y las funciones `sembrarCantidades`, `resembrarCantidades` y
  `cambiarCantidad`.
- **De `paginas/hoja/logica.ts`:**
  - `clavesDeAuditoria` (406) y `hallazgosDeOrigen` (419);
  - `campoDelErrorDePartida` y `cuerpoDeAgregarPartida` (612-650);
  - `comoSeMidio`.
- **Piezas de edición y búsqueda:**
  - `paginas/hoja/EditorDeApu.tsx`, dentro del inspector;
  - `paginas/hoja/Parecidas.tsx`;
  - `comun/CampoConBusqueda.tsx` y `comun/logicaBusqueda.ts` (`buscadorDePartidas`).
- **Componer:** `paginas/componer/ComponerPartida.tsx`, sin cambios.
- **Piezas de estado y de interfaz:**
  - `paginas/hoja/OfertaDeRetomar.tsx`, `paginas/hoja/AvisoDeEdicion.tsx` y `comun/AvisoDeGuardado.tsx`;
  - `comun/PanelLateral.tsx`, como inspector: `aside` no modal, foco al `h2`, Esc y devolución del foco;
  - `comun/Severidad.tsx`, `comun/EstadoVacio.tsx` y `comun/AvisoError.tsx`.
- **De B0:**
  - `comun/MontoExacto.tsx`, `comun/CampoDeCifra.tsx` y `comun/useFocoEnPrimerError.ts`;
  - `comun/recurso.ts` (`useRecurso` e `invalidarRecursos`) y `api/cliente.ts` (`pedir` con `leer`);
  - `comun/Dialogo.tsx`, para confirmar «Quitar» y «Descartar».
- **`comun/Anunciador.tsx`: hoy no está montado.** `ProveedorDeAnuncios` no aparece en `App.tsx:76-90`, así que
  `useAnunciar` cae en `sinProveedor` (`comun/Anunciador.tsx:36-38`) y no anuncia nada. El lote B1-0 lo monta.

### 3.2 Se cambia o se retira del camino de T1 a T3
| Hoy | Qué pasa | Por qué |
|---|---|---|
| Seis o siete pestañas en `paginas/hoja/index.tsx:330-365` (`PESTANAS`, `paginas/hoja/logica.ts:21-29`) | «Partidas» y «Revisión» pasan a la superficie. Las otras (Espacio y metrajes, APU, Plan y equilibrio, Precios y Ajustes de costo) quedan en la subvista nueva «Espacio, plan y ajustes» | T1 a T3 en una superficie, sin pestañas (B.3) |
| `paginas/hoja/PestanaPresupuesto.tsx:186-336`: `TablaPaginada` con un `TextInput` por celda (una parada de Tab por fila) | Se reemplaza por la `Grilla` (`role="grid"` y tabindex itinerante) | Guía `spatial-navigation`: «single tab stop» |
| `PestanaPresupuesto.tsx:338-340`: el total al pie de la tabla | Va a la cabecera fija y al pie de la tabla (`tfoot`, con el IVA) | T1 sin desplazarse. Guía `state-aware-sticky-headers` |
| `PestanaPresupuesto.tsx:260-265, 273, 294-313`: «Cómo se midió», objetivo de mercado y «Quitar» como columnas | Pasan al inspector de la partida | Columnas que no responden la pregunta (UX-24) |
| `paginas/hoja/AgregarPartida.tsx:109-360`: diálogo propio con trampa de foco más un panel «en capa» encima (`paginas/hoja/ComponerEnPanel.tsx:117`) | Fila de alta bajo la grilla, más el inspector de creación **no modal** | B.4, pantalla 2. Termina la capa doble (DESIGN.md:380) |
| `paginas/hoja/Cifra.tsx:6-12`: el exacto en `title` y oculto a la vista | `MontoExacto` en la cabecera y en el inspector. En la celda, solo el texto | Guía `accessibility`: «Don't use `title`…». Guía `single-line-overflow`: «DO NOT rely on `title` alone» |
| `paginas/hoja/EstadoDelBorrador.tsx:30-33`: el total con `title` y `aria-live="polite"` | `MontoExacto`, sin región viva propia. El anuncio único lo da `useAnunciar` | Guía `accessibility`: «Centralize live regions» |
| `paginas/hoja/EstadoDeFila.tsx:26, 35` (`title`) y «Ver en Revisión» (`:40-46`) | La columna Problemas y «Ir a la partida». Sin `title`, y el texto completo está en el inspector | Igual que arriba |
| `paginas/hoja/PestanaAuditoria.tsx` y `comun/InformeAuditoria.tsx` (tabla de 9 columnas) | `InspectorDeProblemas` agrupado por regla. `InformeAuditoria` sigue en Auditoría e Historial | T3 a la vista |
| «Descargar Excel» y «PDF» a la vista (`paginas/hoja/FranjaDelPresupuesto.tsx:146`) y «Descartar cambios» (`paginas/hoja/EstadoDelBorrador.tsx:34-38`) | Pasan a «Más acciones del presupuesto» | Tope de 8 controles a la vista |

**Se borra al final de B1, en el lote B1-11, recortable:**
- de `PestanaPresupuesto.tsx`: `PanelDeApu`, `DialogoAgregarPartida`, `ConfirmarQuitar` y `ContextoAuditoria`;
- `PestanaAuditoria.tsx`;
- su lógica viva se pasa a la superficie antes de borrar, con una mutación por comportamiento.

Cada borrado se hace después de que sus pruebas pasen a la superficie.

### 3.3 Rutas del back que se reutilizan (sin cambios)
- **Prefijo `/v1/hoja`.** En `api/rutas/hoja.py`:
  - `GET /versiones` (333);
  - `GET /borradores` (397) y `POST /borradores` (407);
  - `GET /borradores/{id}` (501) y `DELETE /borradores/{id}` (513);
  - `POST /borradores/{id}/guardar` (570);
  - `POST /borradores/{id}/partidas` (622) y `POST /borradores/{id}/partidas/quitar` (662);
  - `PUT /borradores/{id}/cantidades` (714);
  - `PUT /borradores/{id}/apu/{partida}` (862) y siguientes.
- **Prefijo `/v1/hoja`.** En `api/rutas/hoja_lecturas.py`:
  - `GET /borradores/{id}/vistas/presupuesto` (164);
  - `GET /borradores/{id}/vistas/apu` (172);
  - `GET /borradores/{id}/vistas/auditoria` (223);
  - `GET /borradores/{id}/cambios` (148).
- **Frentes** (`api/rutas/hoja_frentes.py:105, 114`) y **Excel y PDF** (`api/rutas/hoja_exportar.py:51, 77`).
- **`/v1/composicion/*`** (`api/rutas/composicion.py:366-500`) y **`/v1/buscar/partidas`** (`api/rutas/busqueda.py:67`).

**Necesidad del back, opcional y no bloqueante:** «Qué hacer» por hallazgo, con un código estable. El informe de hoy trae
`descripcion`, `impacto`, `observado`, `esperado` y `origen` (`api/tipos.ts:236-246`), sin «qué hacer». Si se quiere,
iría en una capa de presentación nueva, por ejemplo junto a `api/esquemas_informe.py`, fuera de los archivos sellados y de
`aplicacion/hoja.py`. Se recomienda dejarlo para B2 (D8).

### 3.4 Rutas viejas: cuáles se redirigen
| Entrada de hoy | Después de B1 |
|---|---|
| `#/obra/:c/:o/presupuesto`, con la página `hoja` (`marco/secciones.ts:23`, `marco/espacios.ts:143`, `shell/rutas.ts:85-92`) | La misma URL y el mismo id `hoja`: monta la superficie. El id lo usan los Pendientes del servidor (`paginas/pendientes/logica.test.ts:51`), así que no se toca |
| Las pestañas internas (estado del proveedor, sin URL: `paginas/hoja/usePestanaDeLaHoja.ts:29`) | Página nueva `hoja_pestanas`, en la subvista `#/obra/:c/:o/presupuesto/pestanas` («Espacio, plan y ajustes»). Es el `CuerpoDeLaHoja` de hoy, movido sin cambios a `paginas/hoja/pestanas.tsx` |
| `hoja.irAPestana("espacio")` desde Archivos (`paginas/archivos/index.tsx:104-107`) | Lleva a `…/presupuesto/pestanas` con «Espacio y metrajes» |
| `hoja.irAPestana("partidas")` desde Cargar cómputo (`paginas/archivos/CargarComputo.tsx:255`) | Lleva a `…/presupuesto`, con el foco en la grilla |
| «Ver en Revisión» y el paso `ver_revision` (`paginas/hoja/FranjaDelPresupuesto.tsx:91`) | Abren el inspector en «Problemas» |
| El estado `agregarPartida` de Componer (`paginas/hoja/index.tsx:152-162`) | Lo mismo, pero lo atiende la fila de alta |
| `?version=…` | Sin cambio: lo lee el proveedor |
| La obra abierta en `…/resumen` (`marco/BarraLateral.tsx:99, 262`, `marco/busqueda.ts:45`) | Pasa a `…/presupuesto` si Eugenio decide D1. El Resumen sigue como sección |

---

## 4. Plan de lotes para Sonnet
Reglas de todos los lotes:
- prueba en rojo, vista fallar por la razón esperada, antes del código;
- al cerrar: `npm run lint`, `npx vitest run --maxWorkers=3` y `npm run dist` si el lote importa algo nuevo de Carbon
  (`paginas/hoja/DialogoDeVersion.tsx:16`: el Modal de Carbon ya se rechazó por una URL);
- una mutación a mano por comportamiento;
- commit con el porqué, qué cambió y cómo se probó.

Hasta el lote B1-10 la superficie se construye **sin montarla en la ruta**: se prueba aislada. Así no queda nada a medias
en pantalla y la app de hoy sigue igual.

| Lote | Archivos | Pruebas en rojo | Guía de Google (id) | Criterio de aceptación |
|---|---|---|---|---|
| **B1-0** Anunciador y analizadores | `App.tsx` (envolver el `Marco` con `ProveedorDeAnuncios`), `App.test.tsx`; nuevo `paginas/hoja/analizadores.ts` (+ test): `leerVistaPresupuesto`, `leerInforme`, `leerResumen` | Un componente bajo `App` que llama a `useAnunciar` escribe en la región `polite`. `leerVistaPresupuesto` rechaza una fila sin `clave` y acepta `datosDePrueba` | `accessibility` («Centralize live regions») | La suite está verde, `regionesVivasVacias.test.tsx` sigue verde y hay un solo anunciador en el DOM |
| **B1-1** Lógica pura de la superficie | Nuevo `paginas/hoja/superficie/logica.ts` (+ test): `filasDeLaGrilla(vista, informe)`, `fraseDeRespuesta`, `gruposDeProblemas`, `filaDelHallazgo` y `cuentaDeProblemas` (sobre `clavesDeAuditoria` y `hallazgosDeOrigen`) | Frases con 0, 1 y N problemas. INFO no cuenta. Un hallazgo sin fila queda solo en la lista. Las cifras se copian del servidor, nunca se calculan | `content-first-noise-reduction` (lo secundario, a pedido) | Las funciones son puras, sin React, y cada una tiene una mutación que la prueba mata |
| **B1-2a** Máquina de la grilla | Nuevo `comun/logicaGrilla.ts` (+ test): `siguiente(estado, evento)`, con los estados `navegar` y `editar` y los eventos flecha, Inicio, Fin, F2, Enter, Esc, carácter (empieza a editar, como Excel) y Tab | En el borde no hay movimiento y la máquina dice «no consumir». F2 pasa a editar. Esc en edición devuelve el original. Enter confirma y baja | `spatial-navigation` | Es una unión discriminada: un estado ilegal no compila |
| **B1-2b** Componente `Grilla` | Nuevo `comun/Grilla.tsx`, `comun/Grilla.scss` (+ test) | `<table role="grid">` con `th scope`. Una sola parada de Tab y tabindex itinerante. Sin `preventDefault` en el borde. Con un modificador o `defaultPrevented`, no se intercepta. En edición, el campo interno se queda las flechas. Se llama a `scrollIntoView({block:'nearest',inline:'nearest'})` | `spatial-navigation`, `responsive-table` (`position: sticky` en las dos cabeceras, `@container`), `single-line-overflow` (`overflow: hidden`, no `clip`) | No importa de `paginas/` (`comun/arquitectura.test.ts:91`). Hay una escala de `z-index` en tokens (celda fija, cabecera de la grilla, cabecera de la obra, panel) |
| **B1-3** Cabecera fija | `paginas/hoja/EstadoDelBorrador.tsx` (`MontoExacto`, sin `title` ni `aria-live`; `alDescartar` opcional), `paginas/hoja/FranjaDelPresupuesto.tsx` (lugares para «Problemas (n)» y «Más acciones»), nuevo `paginas/hoja/superficie/MasAcciones.tsx` (menú con `popover`), `paginas/hoja/hoja.scss`; ajustar `CabeceraCompacta.test.tsx` y `Franja.test.tsx` | El total no tiene `title` y su exacto está en el `Toggletip`. El total no está en una región viva. Hay un solo principal. «Más acciones» abre, Esc cierra y el foco vuelve. «Descartar» pide confirmar con el foco en «Cancelar» | `state-aware-sticky-headers` (`container-type: scroll-state`, `scroll-padding-top`), `accessibility`, `dialog` (menús con `popover`) | La vista por pestañas también mejora sin perder pruebas. El aspecto se mira en el navegador |
| **B1-4** Superficie de solo lectura (sin ruta) | Nuevo `paginas/hoja/superficie/SuperficiePresupuesto.tsx`, `paginas/hoja/superficie/columnas.tsx` (+ test): `useRecurso` con la clave `ruta@rev` para la vista y para la revisión; `tfoot` con el total y el IVA; los estados de §1.8 | La frase va antes de la grilla. El esqueleto tiene cabeceras y ninguna cifra. Un error muestra «Reintentar» y lo pide de nuevo. «Pendiente» va en texto. Sin permiso no hay nada editable | `responsive-table`, `spinner`, `accessibility` («Don't use live regions for interstitial states») | Las pruebas 1, 2, 9 y 10 de §1.10 en verde |
| **B1-5** Editar cantidades en la grilla | Nuevo `paginas/hoja/superficie/CeldaDeCantidad.tsx` (`CampoDeCifra` `sm` con la etiqueta oculta); conexión de `useEdicionDeSeccion` en `SuperficiePresupuesto.tsx` | Escribir «12,5» y esperar la pausa manda un PUT con su `rev`. Esc restaura. Un 422 marca la celda con texto y no borra. Un 409 vuelve a leer. Enter confirma y baja | `forms` (`inputmode`), `validate-input-after-interaction`, `accessible-error-announcement`, `interactions-in-complex-layouts` | Las pruebas 5 y 6 de §1.10. Lo de `Edicion3c2.test.tsx` que toca cantidades queda cubierto en la superficie |
| **B1-6** Inspector de la partida | Nuevo `paginas/hoja/superficie/InspectorDePartida.tsx` (+ test): `PanelLateral` acoplado, con cómo se midió, calculada y «Volver a la calculada», `MontoExacto` en línea, objetivo de mercado, `EditorDeApu` y «Quitar» (`Dialogo` destructivo) | El foco va al `h2`. No hay trampa de foco. «Cerrar» está a la vista. Esc devuelve el foco a la celda. Al quitar, el foco inicial está en «Cancelar» y al confirmar se manda el POST a `/partidas/quitar` | `dialog` («Use for … inspectors…», «DO include a visible close button in every non-modal dialog»), `html` | La prueba 7 de §1.10 |
| **B1-7** Problemas | Nuevo `paginas/hoja/superficie/InspectorDeProblemas.tsx` y la celda de la columna Problemas (+ test) | Muestra «3 problemas en 2 partidas», agrupados por regla, con la severidad en palabra. Elegir uno activa su fila en la grilla. Sin hallazgos usa `sin_hallazgos` | `accessibility`, `content-first-noise-reduction` («don't open popovers the user didn't ask for») | La prueba 8 de §1.10 |
| **B1-8** Fila de alta | Nuevo `paginas/hoja/superficie/altaDePartida.ts` (máquina `siguiente`) y `paginas/hoja/superficie/FilaDeAlta.tsx` (+ test): `CampoConBusqueda`, `CampoDeCifra`, `Parecidas`, `useFocoEnPrimerError` y el pliegue «Cálculo y nota» | La máquina, pura. Sin partida, error y foco en «Partida». Un 422 no borra. Con éxito, la fila nueva tiene el foco en su Cantidad y hay un anuncio. Un segundo clic no manda dos POST | `forms` («DON'T disable submit buttons…»), `accessible-error-announcement` («move focus to the first invalid field»), `validate-input-after-interaction` | Las pruebas 4 y 5 de §1.10. Lo esencial de `AgregarPartida.test.tsx` (44 casos) queda cubierto |
| **B1-9** Crear la partida en el inspector | Nuevo `paginas/hoja/superficie/InspectorDeCreacion.tsx`; sacar el Esc de `paginas/hoja/ComponerEnPanel.tsx:78-96` a `paginas/hoja/useEscDeComposicion.ts`, que usan los dos; atender el estado `agregarPartida` de Componer | «Crear la partida «…»» abre el inspector no modal con la descripción. Guardar cierra el inspector, deja la partida elegida y pone el foco en Cantidad. Se portan las reglas de Esc de `ComponerEnPanel.test.tsx`. Llegar desde la subvista Componer deja la partida elegida | `dialog` (no modal, con «Cerrar»), `content-first-noise-reduction` | El recorrido de T2 completo pasa en la prueba |
| **B1-10** Cambio de ruta | `paginas/hoja/index.tsx` (monta la superficie con su `h1`), nuevo `paginas/hoja/pestanas.tsx` (el `CuerpoDeLaHoja` de hoy), `shell/rutas.ts` (la página `hoja_pestanas`), `marco/espacios.ts:142-145` (la subvista), `paginas/archivos/index.tsx:104-107`, `paginas/archivos/CargarComputo.tsx:255`, los textos de ayuda (`comun/ayuda/textos.ts:436-439`); D1 en `marco/BarraLateral.tsx:99, 262` y `marco/busqueda.ts:45`. En las pruebas viejas cambia el `import` de `./index` a `./pestanas`, sin tocar lo que prueban | `…/presupuesto` muestra la grilla. `…/presupuesto/pestanas` muestra las pestañas viejas. «Describir el espacio» lleva a su pestaña. La obra abre en Presupuesto (con D1) | `accessibility` («Update … SPA titles…», ya en el marco) | `comun/arquitectura.test.ts`, `guardiaInterfaz.test.ts`, `pestanasConFondo.test.ts` y `sinJergaInterna.test.ts` en verde. Primera pasada en el navegador (Chromium) de T1 a T3 |
| **B1-11** Retirar lo duplicado (recortable) | `paginas/hoja/logica.ts` (`PESTANAS` sin «Partidas» ni «Revisión»); se borran `PestanaPresupuesto.tsx`, `PanelDeApu.tsx`, `PestanaAuditoria.tsx`, `ContextoAuditoria.ts` y el diálogo de `AgregarPartida.tsx`, con sus pruebas ya portadas | Una prueba de que la subvista no tiene esas dos pestañas. Una mutación sobre lo portado, que debe fallar | — | «Kill the survivors. Delete dead code.» Sin dos caminos para lo mismo durante la medición |
| **B1-12** Medir y contener (recortable) | `comun/Grilla.scss` y un banco de 500 filas en `datosDePrueba` | Medir en Chromium el tiempo al editar una celda con 500 filas. Si pasa de 200 ms: `content-visibility: auto` con `contain-intrinsic-size` **solo bajo el pliegue** | `interactions-in-complex-layouts`, `defer-rendering-heavy-content` | El número medido queda en la bitácora. Sin cambio si no hace falta |
| **B1-13** Cierre | Sin código: suite completa de Python y del front, recorrido cognitivo sobre lo construido, árbitro Opus, piloto cronometrado de T1 a T3 con una persona ajena | — | Las 15 guías citadas | El acta de cierre, con la salida literal de las pruebas |

**Qué puede ir en paralelo** (máximo 2 o 3 agentes, por el gancho de Hookify bajo carga):
- **B1-0 ∥ B1-1 ∥ B1-2a:** no comparten archivos.
- **B1-2b ∥ B1-3:** `comun/Grilla.*` frente a `EstadoDelBorrador`, `FranjaDelPresupuesto`, `MasAcciones` y
  `hoja.scss`.
- **B1-4** necesita B1-1, B1-2b y B1-3.
- **B1-5 ∥ B1-6 ∥ B1-7:**
  - cada uno trae su componente en un archivo propio;
  - **la línea que lo conecta en `SuperficiePresupuesto.tsx` la hace Claude, en serie**, al cerrar cada lote.
- **B1-8** necesita B1-4. **B1-9** necesita B1-8.
- **B1-10** necesita todos los anteriores.
- **B1-11 y B1-12** van en paralelo después de B1-10.

---

## 5. Riesgos para el 2026-12-16 y qué se recorta primero
| Riesgo | Señal | Qué se hace |
|---|---|---|
| R1. Crear la partida en un inspector no modal: el Esc y el foco de Componer son delicados (DESIGN.md:380-384, `paginas/hoja/ComponerEnPanel.tsx:52-96`) | B1-9 pasa de dos sesiones | **Plan B:** «Crear la partida» de la fila de alta abre el `DialogoAgregarPartida` y el `ComponerEnPanel` de hoy, con la partida ya escrita. T2 sigue funcionando |
| R2. La grilla en jsdom no es la del navegador (foco, `scrollIntoView`, `sticky`) | Diferencias en la pasada de B1-10 | Una pasada en el navegador al cerrar B1-2b, con una página de prueba local, sin montarla en la app |
| R3. El volumen de pruebas por portar (`AgregarPartida.test.tsx` 44, `Edicion3c2.test.tsx` 34, `Guardar.test.tsx` 37) | B1-8 y B1-11 se alargan | Se porta el comportamiento, no la implementación. Las viejas siguen vivas sobre `pestanas.tsx` hasta B1-11 |
| R4. B4 (Inicio) y B2 (auditar un libro) también entran antes de medir, más el piloto y la prueba de instalación | El 2026-12-09 sin B1-10 cerrado | Se congela lo que haya en B1-10 y se pasa a B4 y B2 |
| R5. Contaminación entre sesiones: el servidor conserva los borradores con cambios (E10) y la partida creada queda en el catálogo de la empresa (`paginas/hoja/ComponerEnPanel.tsx:8`) | La segunda persona ve «Quedó un borrador…» o encuentra «friso de pared» | D5: restaurar la carpeta antes de cada sesión |
| R6. `npm run dist` rechaza un componente de Carbon con una URL | Falla `dist` | Nada de `OverflowMenu` ni `Modal`. Para el menú, `popover` nativo. Se corre `dist` en cada lote |

**Orden de recorte**, si no alcanza:
1. B1-12 (solo se aplica si la medición lo pide).
2. B1-11: la vista por pestañas queda intacta y se declara el doble camino.
3. Dentro de B1-6, el objetivo de mercado y los subtotales por frente: quedan solo en la vista por pestañas.
4. B1-9, con el plan B de R1.

**No se recorta:** B1-0 a B1-5, B1-7, B1-8 y B1-10.

---

## 6. Decisiones que solo puede tomar Eugenio
| # | Decisión | Recomendación (una) y fundamento |
|---|---|---|
| D1 | ¿La obra abre en Presupuesto en vez de Resumen? | **Sí.** B.3 hace de Presupuesto la superficie 1 de la obra. T1 a T3 pasan ahí, y una persona nueva no tiene que adivinar la sección. Cuesta tres líneas (`marco/BarraLateral.tsx:99, 262`, `marco/busqueda.ts:45`). El Resumen sigue en la barra de secciones |
| D2 | ¿Qué cifra vale como respuesta de T1? | **La cabecera muestra «Total sin IVA», y debajo «Con IVA (16 %)»; la hoja de observación acepta cualquiera de las dos si la persona dice cuál lee.** Así es el libro de la empresa (el costo sin IVA es `resumen.total`). Se fija antes de medir, como pide el acta |
| D3 | ¿Qué pasa con la vista por pestañas? | **Queda como subvista «Espacio, plan y ajustes», sin «Partidas» ni «Revisión» (B1-11).** Dos caminos para lo mismo en la medición mezclan los resultados. Si no alcanza el tiempo, queda intacta y se declara como límite |
| D4 | El rótulo para crear la partida en T2 | **«Crear la partida «friso de pared»»** en vez de «Componer una partida nueva con la descripción…». Usa el verbo de la consigna y del oficio (UX-03, UX-04). «Componer» sigue como nombre de la subvista |
| D5 | Restaurar la obra de demostración antes de cada sesión | **Sí, con el respaldo local de #141**: copiar la carpeta de demostración limpia antes de cada persona y anotarlo en el guion. Sin eso, la segunda persona encuentra la partida de la primera (R5) y T2 no se compara |
| D6 | T3 usa la palabra «problema», igual que el rótulo | **Mantener «Problemas»** (lenguaje llano, UX-04) **y declararlo como límite** en el capítulo IV: T3 mide si se encuentra y se lee, no si se adivina el vocabulario. Cambiar la consigna ahora rompería el guion ya enviado al tutor |
| D7 | Quitar una partida: ¿confirmar o deshacer? | **Confirmar**, con `Dialogo` destructivo y el foco en «Cancelar». No hay ruta para deshacer, `aplicacion/hoja.py` está congelado y el cambio se puede descartar antes de guardar (UX-16, rama «si no se puede deshacer») |
| D8 | ¿«Qué hacer» por hallazgo, escrito por el servidor? | **No en B1. Se lleva a B2**, junto con los códigos estables. La descripción del servidor basta para T3, y la capa nueva de presentación cuesta un lote de back que B1 no necesita |
