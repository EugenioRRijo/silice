# Ficha de B2: «Auditar un libro» en un solo flujo (subir, ver qué se encontró, concluir)

- **Fecha:** 2026-11-27.
- **Árbol:** `.worktrees/s4`, rama `feature/front-b1`. Las rutas son relativas a `frontend-desktop/src/` salvo que digan
  otra cosa.
- **Método:** skills `disenar-desde-la-tarea` e `interfaz-silice`, con la forma de [`ficha-b1.md`](../b1/ficha-b1.md).
  La cara es la de [`README.md`](../README.md) y los fragmentos aprobados 15 (subir), 08 (problemas), 09 (dictamen) y 16
  (historial).
- **Límites:** `core/`, lo sellado por `reglas-congeladas-2026-11-24` (reglas, umbrales, `aplicacion/causas_raiz.py`, el
  plan no circular, la taxonomía de plantilla, `api/rutas/libros.py`), `aplicacion/manifiesto_corrida.py` y
  `aplicacion/hoja.py` **no cambian**. El «Qué hacer» y sus códigos van en una capa de presentación nueva
  (`aplicacion/que_hacer.py` y `api/rutas/libros_que_hacer.py`) y una prueba compara las huellas de los sellados con la
  etiqueta (§6).
- **Quién la usa en la medición:** la prueba de comprensión de las 6 alertas (A1 a A6) del
  [guion](../../../tesis/2026-11-23-guion-prueba-con-usuarios.md). Se hace en esta pantalla.

---

## 1. Ficha de la pantalla

### 1.1 Historia de trabajo
Cuando me llega el Excel de un presupuesto, quiero subirlo y saber de una vez si tiene algo mal, dónde está y qué
tengo que hacer, **para devolvérselo corregido a quien lo hizo o seguir adelante sin dudas**.

No quiero cambiar de pantalla para pasar de «lo subí» a «qué encontró» a «y ahora qué»: hoy son tres lugares
(Subir y auditar, Libro de la empresa, Historial).

### 1.2 De dónde viene y a dónde va
- **Viene de:**
  - el espacio «Auditar un presupuesto» (`marco/espacios.ts:116-122`, herramienta «Subir y auditar Excel»);
  - la Vista general, con el archivo soltado en su zona (`paginas/inicio/archivoPendiente.ts`);
  - el recorrido guiado «Auditar un libro de la empresa» (`shell/recorrido.ts:20`);
  - el Historial, con «Auditar un libro».
- **Va a** (un control visible por cada éxito):
  - con hallazgos: «Descargar el informe en PDF», para entregarlo a quien hizo el libro;
  - sin hallazgos: «Auditar otro libro» (el libro cumple y no queda nada que corregir);
  - en los dos casos, «Ver la hoja marcada» (el Visor, `paginas/libros`) y «Ver el historial».

### 1.3 Quién la usa y qué sabe
- **Economistas que presupuestan obras viales y viven en Excel** (3 de las 5 personas): entienden «referencia a otra
  celda», «fórmula» y «hoja»; esperan ver la celda exacta y el efecto en el total.
- **Personas que presupuestan pero no conocen Sílice** (2 de 5): no saben qué es una «causa raíz», un «componente
  fuera del total» ni un «umbral».
- **Cómo se sirve a los dos:** el nombre llano de la regla y su código entre paréntesis («Componente fuera del total
  (L4)»); la línea «Qué hacer», en llano y en trato de usted, **a pedido** (plegada); la ayuda larga en
  «¿Qué es esto?».

### 1.4 Camino crítico (análisis jerárquico de tareas)
| Subtarea | Frecuencia | ¿Crítica? |
|---|---|---|
| Soltar o elegir el `.xlsx` | siempre | sí |
| Auditar | siempre | sí |
| Leer cuántos hallazgos hay y de qué gravedad | siempre | sí (A1 a A6) |
| Leer qué dice cada hallazgo y alerta (celda, regla, efecto) | siempre | sí (A1 a A6) |
| Saber qué hacer con cada uno | casi siempre | sí |
| Descargar el informe en PDF | a veces | no |
| Ver el hallazgo sobre la hoja del libro | a veces | no |
| Cambiar la fecha de la revisión | rara | no |
| Auditar con recorrido guiado | rara | no |
| Un libro con un APU por hoja | rara | no (otro perfil) |
| Abrir una auditoría anterior | ocasional | no (Historial) |

### 1.5 Tipo de vista y frase de respuesta
- **Tipo:** informe de resultado en una sola página, con secuencia: subir, qué se encontró, conclusión y entrega.
- **Pregunta que responde:** «¿Este libro tiene algo mal, dónde y qué hago?».
- **Frase de respuesta** (la escribe una función pura que **solo cuenta**; los montos vienen del servidor):
  - con hallazgos: «**6 hallazgos** en el libro» y debajo «3 errores · 3 advertencias». Los totales del libro frente a los
    de Sílice salen en «Conclusión y entrega», en la franja de indicadores que ya existe (`FranjaIndicadores`), con su
    valor exacto y sin recalcular nada;
  - sin hallazgos: «El libro **no tiene hallazgos**: Sílice revisó cada partida y no halló nada que corregir».
- Un hallazgo de regla «no aplicable» (R2 y R7 sin curva ni plan) **no cuenta**, igual que hoy
  (`aplicacion/causas_raiz.py`, `no_aplicables`).

### 1.6 Reparto de controles
**A la vista, antes de auditar (4 decisiones, en orden de tabulación):**
1. La zona «Suelte aquí el libro .xlsx, o haga clic para elegirlo».
2. **«Auditar el libro»**, el único principal. Inactivo hasta que haya un archivo, y dice por qué.
3. El pliegue «Más opciones» (resumen: «Se revisa con la fecha de hoy. Cambiar»).
4. El pliegue «Otro tipo de libro: un APU por hoja» (el flujo de `AuditarApuPorHoja`, que no cambia).

**A la vista, con el resultado (8 decisiones o menos):**
1. «Auditar otro libro» (secundario; vuelve al estado inicial).
2. Cada hallazgo y alerta lleva **un** botón «Qué hacer» (disclosure), cerrado. No cuenta como decisión de la
   página: es lectura a pedido.
3. «Descargar el informe en PDF» (el principal de la conclusión).
4. «Ver la hoja marcada».
5. «Ver el historial».
6. El pliegue «Reglas que no aplicaron a este libro (n)».

**En «Más opciones», cada una con su valor por omisión dicho:**
- **Fecha de la revisión.** Por omisión, hoy. Con la misma fecha, el mismo libro da siempre el mismo resultado
  (`api/rutas/libros.py`: la API no usa el reloj).
- **Auditar con recorrido guiado.** Por omisión, no: lleva el archivo al Visor con el recorrido de tres pasos de
  `shell/recorrido.ts` (flujo de hoy, sin cambios de comportamiento).

### 1.7 Punto de partida
- **Sin archivo:** la zona vacía y el principal inactivo. Si la persona soltó un archivo en la Vista general
  (`archivoPendiente`), se toma al montar y se audita solo (como hoy el Visor).
- **Con la lista de «Últimas auditorías guardadas»** debajo, tal como hoy (`paginas/inicio/UltimasAuditorias.tsx`), para
  la pregunta «¿dónde estaba el de ayer?».
- **Sin permiso** para auditar (`leer_proyecto`): se dice quién audita, como hoy (`paginas/auditoria/index.tsx:57-67`).

### 1.8 Tabla de estados
Cada estado lleva **un** control al paso siguiente.

| Estado | Qué ve la persona | Paso siguiente |
|---|---|---|
| Vacío | La zona, el principal inactivo y la nota «El archivo original no se modifica ni se guarda» | Soltar el libro |
| Archivo elegido | «Archivo elegido: Presupuesto cliente A.xlsx» y el principal activo | «Auditar el libro» |
| Cargando | Un esqueleto de la frase y de la lista, con «Auditando el libro…» (sin cifras inventadas y **sin región viva** con texto) | — (espera) |
| Error al auditar (422, 413, 415, 500) | `AvisoError` con el detalle del servidor y el archivo conservado | «Reintentar» (vuelve a pedir con el mismo archivo) |
| Sesión vencida (401) | El marco pide entrar de nuevo; el archivo elegido sigue en la página | Entrar y «Reintentar» |
| Con hallazgos | La frase, los datos, «Qué se encontró» y la conclusión «no cumple» | «Descargar el informe en PDF» |
| Sin hallazgos | La frase «no tiene hallazgos» y la conclusión «cumple» | «Auditar otro libro» |
| Parcial: no quedó en el historial | La auditoría vale; una nota dice «No se pudo guardar la auditoría en el historial» (texto del servidor, `aviso_historial`) | «Descargar el informe en PDF» |
| Parcial: alertas de precio sin tasa del BCV | Una sola línea agrupada: «No se pudieron contrastar 14 precios USD-Bs: la instalación no tiene la tasa del BCV de 2026-11-24» | «Qué hacer» de esa alerta |
| Éxito al preparar la hoja | Se abre «Libro de la empresa» con el mismo resultado, **sin auditar otra vez** | «Ver el historial» |
| Error al preparar la hoja | `AvisoError` al lado del botón y el resultado intacto | Reintentar «Ver la hoja marcada» |
| Éxito al auditar | El foco va al titular de la frase, y el anunciador dice **una vez** «Auditoría lista: 3 errores y 3 advertencias.» | «Descargar el informe en PDF» |

### 1.9 Supuestos de negocio (por confirmar)
Ninguno se presenta como regla.

| # | Supuesto | Lo confirma |
|---|---|---|
| S1 | El tercer paso se llama **«Conclusión y entrega»**, no «Dictamen». «Dictamen» es la pieza firmada y atada a una versión (`paq_dictamen`, Aprobar y Revisar), y una auditoría de libro no es de una obra ni se firma | Eugenio (D2) |
| S2 | «Cumple» es el `cumple` del servidor. La pantalla no lo recalcula | Eugenio |
| S3 | Una alerta USD-Bs «dentro del umbral» **no** es un aviso: no se muestra. «No contrastable» sí, agrupada | Eugenio (D6) |
| S4 | Una alerta de precio no tiene severidad: no se pinta con los colores de gravedad (dos semánticas separadas) | Eugenio |
| S5 | Los códigos estables del «Qué hacer» son el código de la regla («L4») y `alerta:<tipo>` para las alertas de precio | Eugenio (D4) |
| S6 | Hasta unos cientos de hallazgos por libro; la lista no se pagina. Se mide con el libro de demostración | Medición |

### 1.10 Pruebas que la fijan
Son pruebas de Testing Library, por rol y por nombre, con datos construidos (`datosDePrueba.ts`) y de pytest.
1. Antes de auditar hay 4 controles de decisión a la vista o menos (zona, principal, dos pliegues).
2. El principal es **uno** en cada estado, y dice por qué está inactivo cuando no hay archivo.
3. «Auditar el libro» manda **una** auditoría (`POST /v1/libros/auditoria`) y **ninguna** réplica; la réplica se pide
   solo al pulsar «Ver la hoja marcada» y nunca se audita dos veces (no se duplica el historial).
4. La frase de respuesta cuenta bien (0, 1 y N; el no aplicable no cuenta) y dice los totales con coma decimal.
5. Las **6 alertas** de la prueba de comprensión salen en la pantalla en el formato del guion (A1 a A6, §2).
6. Cada hallazgo y alerta tiene su botón «Qué hacer», cerrado por omisión, con `aria-expanded` y sin `title`.
7. La severidad se dice siempre con palabra e ícono; las alertas de precio no llevan color de gravedad.
8. Un error al auditar muestra el detalle del servidor y «Reintentar» conserva el archivo.
9. Sin hallazgos: «no tiene hallazgos» y la conclusión «cumple».
10. El recorrido guiado y el libro de un APU por hoja siguen funcionando como hoy.
11. Pytest: todo código de regla que un libro puede emitir tiene «Qué hacer» no genérico; el texto está en trato de
    usted; la ruta exige sesión o clave y no cambia `api/rutas/libros.py`.
12. Pytest: las huellas de los archivos sellados coinciden con las de la etiqueta (§6).

---

## 2. Recorrido cognitivo
P1 ¿intentará esto? P2 ¿verá el control? P3 ¿lo asociará con lo que quiere? P4 ¿entenderá la respuesta?
✔ = pasa; ✖ = falla, con su arreglo ya incluido.

### Tarea de la prueba: subir el libro de demostración y decir qué hallazgos tiene
| Paso | P1 | P2 | P3 | P4 | Veredicto y arreglo |
|---|---|---|---|---|---|
| 1. Soltar el libro | ✔ | ✔ La zona es lo primero | ✔ | ✔ | — |
| 2. Pulsar «Auditar el libro» | ✔ | ✖ Hoy hay dos botones («recorrido guiado» y «por mi cuenta») y la persona duda | ✔ | — | Un solo principal; el guiado va en «Más opciones» |
| 3. Esperar | ✔ | ✔ | ✔ | ✖ Hoy se abre otra pantalla con un esqueleto | La misma página, con «Auditando el libro…» |
| 4. Leer cuántos hay | ✔ | ✔ La frase es el titular | ✔ | ✔ | — |
| 5. Leer cada uno | ✔ | ✔ | ✔ | ✖ Una alerta de precio (A1 a A3) no se ve hoy en ninguna pantalla | Sección «Alertas de precio» con el mensaje del servidor |
| 6. Decir qué haría | ✔ | ✔ «Qué hacer» está en cada uno | ✔ | ✔ | Plegado, para no contaminar la medición (§5, D3) |

### Prueba de comprensión de las 6 alertas
| Alerta | Dónde sale | Formato en pantalla (copiado del guion) |
|---|---|---|
| A1 Sin fuente | Alertas de precio | **Sin fuente** · `MT-04`, «la FUENTE de MT-04 dice «POR COTIZAR»: …» |
| A2 Base de la empresa | Alertas de precio | **Base de la empresa** · `MT-08`, «el libro usa 18,00 USD; precio propio …: +20,00 %, pasa del umbral de 5,00 %» |
| A3 USD-Bs | Alertas de precio | **USD-Bs** · `MT-08`, «900,00 Bs al 2026-10-01 … y 990,00 Bs al 2026-11-24 …: +10,00 %, pasa del umbral …» |
| A4 L4 | Qué se encontró, uno por uno | **APU-02!G36 · Error · Componente fuera del total (L4) · 1.265,00** y su descripción |
| A5 L5 | Qué se encontró, uno por uno | **RESUMEN!B4 · Error · Referencia rota o externa (L5)** y su descripción |
| A6 Causa raíz | Qué se encontró, por causa raíz | **Error · 6 casos · Referencia desalineada (L1)** y «Encontrado 0 · esperado 120» |

Las tarjetas impresas se copian de esta pantalla **sin** la línea «Qué hacer» (§5, D3).

---

## 3. Lo que se reutiliza y lo que se retira

### 3.1 Se reutiliza tal cual
- **`visor/Visor.tsx`** y `paginas/libros/index.tsx`: el Visor sigue siendo «Ver la hoja marcada». Lo abre con el
  resultado ya listo por el almacén (`visor/almacen.ts`, `almacenDelLibro` del contexto), así que no audita otra vez.
- **`comun/SubidaArchivo.tsx`, `comun/BotonInactivo.tsx`, `comun/DescargaArchivo.tsx`, `comun/AvisoError.tsx`, `comun/Severidad.tsx`,
  `comun/Anunciador.tsx` (`useAnunciar`), `comun/useCarga.ts`.**
- **`visor/halos.ts`** (`estiloDeHallazgo`) y **`severidad/severidad.ts`**: el color y el ícono de cada gravedad.
- **`paginas/auditoria/AuditarApuPorHoja.tsx`**: sin cambios.
- **`paginas/inicio/UltimasAuditorias.tsx`, `paginas/inicio/archivoPendiente.ts`** y **`shell/recorrido.ts`**.
- **Del servidor:** `POST /v1/libros/auditoria`, `POST /v1/libros/replica` y `POST /v1/libros/auditoria/pdf`, sin
  cambios.

### 3.2 Se cambia o se retira
| Hoy | Qué pasa | Por qué |
|---|---|---|
| `paginas/auditoria/index.tsx`: dos botones («Auditar con recorrido guiado» primario y «Auditar por mi cuenta») y la navegación a `libros` | Un principal, «Auditar el libro», que audita en la página. El recorrido guiado pasa a «Más opciones». «Auditar por mi cuenta» se retira: su papel lo cumple el principal, y «Ver la hoja marcada» lleva al Visor | Un solo principal (UX-01); sin saltos |
| El Visor audita al montarse con el archivo pendiente | Sigue haciéndolo solo en el camino guiado. En el camino nuevo recibe el resultado por el almacén | Sin duplicar filas del historial |
| `visor/ListaHallazgos.tsx`: «Acción: …» solo del hallazgo elegido | Sin cambio. La página nueva tiene su propia lista, con «Qué hacer» por hallazgo | La lista del Visor responde otra pregunta (¿qué celda?) |
| `alertas` de precio: la API las manda y **ninguna pantalla las muestra** | Sección «Alertas de precio» en la página nueva | La prueba de comprensión las necesita (A1 a A3) |
| `paginas/historial/Detalle.tsx`: «Qué revisó Sílice» sin guía | Una columna «Qué hacer» con la línea del catálogo | La misma guía donde la persona revisa una auditoría anterior |

### 3.3 Rutas del servidor
- **Se reutilizan:** `POST /v1/libros/auditoria`, `/replica`, `/auditoria/pdf` y `GET /v1/auditorias-libro[/{id}]`.
- **Nueva, de solo lectura:** `GET /v1/libros/que-hacer` (`api/rutas/libros_que_hacer.py`). Responde el catálogo de
  `aplicacion/que_hacer.py`: por código de regla y por tipo de alerta, con `titulo`, `significa`, `que_hacer`,
  `generico` y, para las alertas, `sin_aviso_si` (frases con que el servidor declara que no hay nada que avisar).
  Mismo acceso que las demás rutas de libros (`ACCESO_LIBROS`). No recibe el libro ni lo guarda.
- **No cambia:** `api/rutas/libros.py` (sellado). El catálogo no se mezcla en su respuesta: el front junta los dos por
  `codigo`.

### 3.4 Rutas viejas: cuáles se redirigen
| Entrada de hoy | Después de B2 |
|---|---|
| `#/auditoria` (página `auditoria`) | La misma URL y el mismo id: monta el flujo nuevo |
| `#/auditoria/libros` (página `libros`) | Sin cambio. Es «Ver la hoja marcada» y el destino del recorrido guiado |
| `#/auditoria/historial` | Sin cambio de ruta; el detalle gana «Qué hacer» |

---

## 4. Plan de lotes
Reglas de todos los lotes: prueba en rojo vista fallar por la razón esperada antes del código; una mutación a mano por
comportamiento; `npm run lint` y las pruebas del lote; commit lo hace Claude.

| Lote | Archivos | Pruebas en rojo | Criterio de aceptación |
|---|---|---|---|
| **B2-0** Sellos | `tests/unit/test_sellos_de_reglas.py` | Las huellas SHA-256 de los sellados (los 10 de la etiqueta más `libros.py`, `hoja.py` y el conjunto de `core/`) coinciden con las de la etiqueta | Verde; una mutación en un sellado la rompe |
| **B2-1** Catálogo del «Qué hacer» | `aplicacion/que_hacer.py`, `tests/unit/test_que_hacer.py` | Cada código que un libro puede emitir (L1 a L9, L10, L11, F1, R1 a R7) y cada tipo de alerta tiene texto propio; los textos están en usted y sin jerga; un código desconocido da el genérico, marcado | Sin importar `fusion/` ni `core/` desde `aplicacion/` (`test_arquitectura.py`) |
| **B2-2** Ruta | `api/rutas/libros_que_hacer.py`, `api/main.py`, `tests/integration/test_api_libros_que_hacer.py`, `docs/api.json` | Sin sesión ni clave, 401; con clave, el catálogo; los tipos de alerta coinciden con `fusion/alertas.py` | `api/rutas/libros.py` intacto |
| **B2-3** Lógica pura del front | `paginas/auditoria/logicaDelLibro.ts` (+ test), `comun/catalogoQueHacer.ts` (+ test; en `comun/` porque lo usan Auditoría e Historial), `paginas/auditoria/datosDePrueba.ts` | Frases con 0, 1 y N; el no aplicable no cuenta; agrupar alertas; separar las que no son aviso; analizador del catálogo | Funciones puras, una mutación por cada una |
| **B2-4** Piezas | `paginas/auditoria/ProblemasDelLibro.tsx`, `AlertasDePrecio.tsx`, `ConclusionDelLibro.tsx`, `auditoria.scss` y `comun/QueHacer.tsx` (+ tests) | Pruebas 5, 6, 7 y 9 de §1.10 | Solo tokens `--silice-*`, rem y sin `title` |
| **B2-5** Flujo | `AuditarUnLibro.tsx`, `useAuditoriaDelLibro.ts`, `index.tsx` (+ tests); el título de la ruta en `shell/rutas.ts` y los textos de ayuda de «Auditar un libro» en `comun/ayuda/textos.ts` | Pruebas 1, 2, 3, 4, 8 y 10 de §1.10 | El flujo de hoy (recorrido y APU por hoja) sigue en verde |
| **B2-6** Historial | `paginas/historial/Detalle.tsx` (+ test): usa `comun/QueHacer.tsx` y `comun/catalogoQueHacer.ts` | La tabla de hallazgos guardados lleva su «Qué hacer» | Sin cambiar la lista ni los filtros |
| **B2-7** Cierre | Sin código nuevo | Las comprobaciones del encargo | Acta de cierre con la salida literal |

---

## 5. Decisiones: «Decisión de Claude, a ratificar por Eugenio»
Se resolvieron con la recomendación más fundada (estándares y sistemas parecidos). Eugenio las ratifica o las cambia.

| # | Decisión | Fundamento |
|---|---|---|
| D1 | **Una sola página con tres secciones** (subir, qué se encontró, conclusión y entrega), no un asistente de pantallas. El foco va al titular del resultado | Un resultado que cabe en una lectura vertical no necesita pasos que se pierdan; Carbon recomienda un indicador de progreso solo para flujos de varias pantallas; la guía de Google pide mover el foco al contenido nuevo |
| D2 | El tercer paso se llama **«Conclusión y entrega»**. El «Dictamen» firmado queda en Aprobar y Revisar (otros lotes) | «Dictamen» ya significa una pieza firmada y atada a una versión; llamar igual a un resultado automático confunde a quien revisa paquetes (UX-04, una palabra, un significado) |
| D3 | El «Qué hacer» va **plegado** por hallazgo, y las tarjetas de la prueba de comprensión se imprimen **sin** él | Si la tarjeta lo trae, «¿qué haría ahora?» mide lectura y no comprensión. Plegado, la pantalla queda tranquila y el conductor lo puede abrir después |
| D4 | Los códigos estables son el código de la regla («L4») y `alerta:<tipo>` (`alerta:sin fuente`, `alerta:usd-bs`…). Una ruta nueva de solo lectura entrega el catálogo | No se toca la respuesta sellada de `libros.py`; el código de regla ya es estable y lo usan el PDF y el historial |
| D5 | «Ver la hoja marcada» pide la réplica **al pulsar** y reutiliza la auditoría por el almacén; no audita otra vez | Evita una segunda fila en el historial (RF-144) y no baja la réplica pesada a quien no la quiere |
| D6 | Una alerta USD-Bs «dentro del umbral» no se muestra; las «no contrastables» van en una línea agrupada con su cuenta | El servidor genera una fila por insumo; mostrarlas todas ahogaría las 3 o 4 que importan |
| D7 | «Auditar por mi cuenta» se retira; «Auditar con recorrido guiado» pasa a «Más opciones» | Un solo principal; el recorrido es para quien lo pida |
| D8 | La fecha de la revisión pasa a «Más opciones», con «hoy» por omisión | Ocasional; con valor por omisión dicho (interfaz-silice) |
| D9 | El Historial solo gana «Qué hacer» en su detalle. Los estados «Dictamen emitido», «En revisión» y «Archivada» del fragmento 16 **no** se construyen | Esos estados no existen en los datos; mostrarlos sería inventarlos |
| D10 | La cara se aplica con los tokens y clases que ya existen (`--silice-*`, Carbon); no se rehace el marco | El marco y la barra de espacios son de otros lotes |
| D11 | `QueHacer` y su catálogo viven en `comun/`, no en `paginas/auditoria/` | Los usan Auditoría e Historial y una página no importa de otra (`comun/arquitectura.test.ts`) |
| D12 | El título del documento y el h1 pasan de «Inicio de auditoría» a «Auditar un libro» | Es el nombre de la historia de trabajo y el que usa el acta; «Inicio» no decía qué se hace aquí |

---

## 6. Riesgos y qué se recorta primero
| Riesgo | Señal | Qué se hace |
|---|---|---|
| R1. Las tarjetas impresas de la prueba difieren de lo que sale en pantalla | La conductora ve otra cosa que la tarjeta | Copiar las tarjetas de esta pantalla con `medicion-v1` (el guion ya lo pide) |
| R2. El texto de un «Qué hacer» promete algo que la regla no garantiza | Un economista lo corrige en el piloto | Los textos dicen qué revisar, no qué decidir: el auditor no decide la intención (`adapters/hoja_empresa/reglas.py`, F-D7) |
| R3. Se toca un archivo sellado sin querer | Falla `test_sellos_de_reglas.py` | Revertir; una regla solo cambia con acta |
| R4. Un libro grande trae cientos de hallazgos | La página se alarga | Las causas raíz van primero (corregir una arregla todas); se mide en el piloto |
| R5. Otro lote cambia `shell/rutas.ts` o `marco/espacios.ts` | Conflicto al integrar | B2 no los toca: la página conserva su id `auditoria` |

**Orden de recorte**, si no alcanza:
1. B2-6 (el historial queda como hoy).
2. La agrupación de las alertas «no contrastables» (se muestra cada una).
3. El anunciador y el foco al titular (queda el foco por el orden natural).

**No se recorta:** B2-0 a B2-5.

## 7. Qué queda fuera, y por qué
- **Firma y emisión de un dictamen** de libro: pertenece a Aprobar y Revisar (otros lotes) y exige una versión.
- **Estados y filtros del historial** del fragmento 16: no hay estado en los datos.
- **«Usar el precio de la lista» y «Anotar la fuente»** (acciones de 1 clic del fragmento 15): escriben sobre el libro;
  el original nunca se modifica y la capa Delta es otro lote.
- **Barra del lugar, margen de notas y bloque de cifras de la barra lateral:** son del marco.
- **El resumen de la obra y «Problemas de la obra»** (fragmento 08): usan el borrador de la obra y son de B1 y de Aprobar.
