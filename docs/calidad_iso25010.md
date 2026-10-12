# Evaluación de calidad del producto (ISO/IEC 25010) — Sesión F.2

Evaluación del sistema contra el modelo de calidad de producto de ISO/IEC 25010, con las métricas
y metas declaradas en [ERS.md §3.3](ERS.md#33-requisitos-no-funcionales-isoiec-25010). Este
documento **interpreta**; no registra cifras ni estados que tienen fuente única
([metodologia.md §5.1](metodologia.md#5-dry)):

- el estado de cada RF y la prueba que lo demuestra: [plan_pruebas.md §8](plan_pruebas.md)
  (INV‑032);
- la suite, la cobertura y la corrida de CI que las mide: [plan_pruebas.md §10](plan_pruebas.md)
  (INV‑031);
- la verificación de cada RNF: [plan_pruebas.md §9](plan_pruebas.md).

Fecha de la evaluación: 2026‑08‑31, sobre `main` en `02f961a` (cierre del sprint I6).
**Actualizada el 2026‑09‑28 en la fase C4 del cierre** ([PLAN_CIERRE.md](../PLAN_CIERRE.md)) sobre
`main` = `ceb6b8e`, cuyo contenido es el del commit `308eca5` que probó la corrida de CI
[36427904452](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/36427904452)
(Linux y Windows, en verde). Esa actualización reemplaza la nota de vigencia del 2026‑09‑23, que
remitía las cifras a la bitácora hasta cerrar la compuerta de la interfaz.

## 1. Adecuación funcional

**Completitud funcional.** La ERS declara 42 RF (RF‑32 vacante). Su estado vive en un solo
lugar, [plan_pruebas.md §8](plan_pruebas.md), cuyo resumen enumera los RF que no están en verde y
la causa de cada uno; aquí no se repite esa lista, para que no vuelva a desincronizarse (INV‑027,
INV‑032). Lo que se interpreta es su efecto: §8 declara **un RF esencial en estado parcial** y un RF
deseable (RF‑20, diferencial de UC‑04) **no implementado**, en limitaciones (INV‑011). Desde C6, el
único RF esencial parcial es RF‑16 (plan_pruebas §8): la persistencia de la partida creada desde
una propuesta depende de la decisión D5 del
[dossier G0](dossier_g0.md#d5-flujo-de-creación-de-partidas-rf16-y-familia), pendiente del tutor,
y no se cierra dentro del cierre. RF‑24, la importación del presupuesto de un tercero, pasó a verde
en la fase C6 (INV‑076).

**Qué capa realiza cada caso de uso.** No todos los casos de uso tienen pantalla; la
correspondencia la declara la [ERS §3.1](ERS.md) (INV‑030) y el
[manual de usuario §3](manual_usuario.md) dice por dónde se opera cada uno. UC‑04 vive solo en el
adaptador civil (`adapters/civil/recalculo.py`), sin pantalla ni ruta; los rendimientos medidos de
UC‑06 se registran solo por la API, y las métricas de UC‑07, con un script (la pantalla «Componer
una partida» ofrece parte de los dos como ayudas); la importación de UC‑05 (RF‑24) solo existe por la
API, `POST /presupuestos/importar`, desde C6. UC‑08 está cableado en las tres capas: `core.budget.generar_escenario`, la ruta
`POST /presupuestos/{codigo}/escenarios` y la página «Escenarios de sensibilidad» (INV‑085).

**Corrección funcional (RNF‑01).** El presupuesto de la línea base corregida se reproduce con
desviación 0,00 % — los cinco precios unitarios dentro de ± 0,01 y los totales exactos en
`Decimal` — muy dentro del rango de la clase 3 de AACE (−20 % / +30 %) que la meta exige. La
prueba de aceptación crítica del trabajo se cumple: **7 de 7 inconsistencias detectadas**
(indicador 1 de la tesis). Las dos cosas las vuelven a comprobar `tests/unit/test_costing.py` y
`tests/integration/test_auditoria_7_de_7.py` en cada corrida de CI, entre ellas la citada arriba.

**Pertinencia funcional.** El informe de auditoría se genera siempre, sin pedirlo (principio 7 de
NORMAS.md §2): `elaborar()` no tiene un modo sin auditoría.

**Veredicto: parcial.** La corrección y la pertinencia cumplen; la completitud no, porque
[plan_pruebas.md §8](plan_pruebas.md) declara un RF esencial parcial (RF‑16) y un deseable sin
implementar. La versión
anterior de este párrafo decía «cumple, con los tres RF no esenciales declarados arriba», pero
arriba solo se declaraba RF‑16, que es esencial (INV‑067).

## 2. Fiabilidad

**Madurez.** La suite completa corre en verde con `-W error` (ninguna advertencia tolerada) y
**0 omitidas**, en Linux y en Windows, en cada PR: la CI exige las dos condiciones
(`scripts/verificar_omitidas.py`). La cifra de pruebas y su corrida están en
[plan_pruebas.md §10](plan_pruebas.md). La línea base que validó el motor en I0.3 sigue siendo la
única copia de sus datos (`tests/fixtures/apu_linea_base.py`) y `tests/unit/test_costing.py` la
sigue vigilando.

**Reproducibilidad (RNF‑02).** Cualquier presupuesto se reconstruye con los precios vigentes a su
fecha y el resultado es idéntico al emitido (100 %, comparación exacta). Todo lo estocástico fija
semilla: la misma entrada produce el mismo resultado en ML y en el simulador.

**Tolerancia a fallos.** Una regla de verificación que no puede evaluarse se reporta como hallazgo
INFO sin interrumpir a las demás (RF‑23); una lista de precios malformada se rechaza citando
archivo y fila antes de valorar nada; un rendimiento atípico advierte pero no impide el registro
(RF‑27).

**Veredicto: cumple.**

## 3. Eficiencia de desempeño (RNF‑03)

Medición reproducible con `uv run python scripts/medir_rnf03.py` (2026‑08‑31, equipo de
desarrollo, SQLite local, sin exportación; registro en [plan_pruebas.md §9](plan_pruebas.md)): el
ciclo completo de UC‑02 — revalorar 100 partidas con 41 insumos cambiados, reelaborar con
auditoría R1–R7, guardar la versión nueva y su histórico de incidencias — tarda **1,17 s**, contra
la meta de < 5 s: margen de 4×. La medición depende del equipo y se repite al congelar
([plan_redaccion.md §5](tesis/plan_redaccion.md#5-cifras-citables-y-cómo-regenerarlas)).

**Veredicto: cumple.**

## 4. Usabilidad (RNF‑04 y RNF‑10)

**RNF‑04 — el informe de auditoría se entiende sin formación previa.** La meta (juicio de
expertos ≥ 4/5 en Likert) **no es automatizable y está pendiente**. Se mide en la fase **Med**
([PLAN_CIERRE.md](../PLAN_CIERRE.md)) con el protocolo [protocolo_rnf04.md](protocolo_rnf04.md):
al menos tres expertos sin relación personal con el autor, el bloque A del
[anexo A del dossier](dossier_g0.md) y un informe identificado por su commit y por las huellas
SHA‑256 de sus dos formas, la pantalla y la hoja *Auditoria* ([protocolo](protocolo_rnf04.md) §1).
El material se regeneró en la compuerta GC5 sobre `e5a8209`: 14 hallazgos (1 CRITICO, 12 ERROR y
1 ADVERTENCIA) y huella de la pantalla `1d7ba8d6…9077a840` (protocolo §1, con la huella completa y
la del libro). En GC6 se volvió a regenerar sobre `5b33e5f`, el código de C6: las huellas de la pantalla y del
contenido del libro no cambian (protocolo §1). Lo que el producto ya aporta a esa evaluación: hallazgos en español con severidad,
impacto cuantificado y los `origen_id` involucrados (columna *Orígenes* de la hoja *Auditoria* del
Excel); desde C5, las siete reglas evaluadas en las dos formas y, en la pantalla, la partida de
cada hallazgo atribuida por regla (INV‑095, protocolo §1); UI multipágina y API autodocumentada (OpenAPI en `docs/api.json`).

**Veredicto: pendiente de medición.** No se anticipa el resultado.

**RNF‑10 — capacidad de aprendizaje de la interfaz** (sprint de UI, [PLAN_UI.md](../PLAN_UI.md)).
RNF‑04 pregunta por el **informe**; nada en él mide si la persona supo por dónde empezar, y siete de
sus ocho ítems no los puede contestar quien no llegó al informe. RNF‑10 mide ese tramo: una persona
que nunca vio la aplicación llega sola del Inicio a un presupuesto en Excel con su hoja de
auditoría. Instrumento: el caso con persona CP‑07 de [guion_prueba_arenia.md](guion_prueba_arenia.md)
y el **bloque B** del [anexo A del dossier](dossier_g0.md), con promedio propio que nunca se
mezcla con el del bloque A. Subcaracterísticas de ISO/IEC 25010 atacadas: reconocibilidad de la
adecuación, capacidad de aprendizaje y protección contra errores del usuario.

**Veredicto: pendiente de medición.** La spec de cierre (§5) partió la compuerta GU1 en dos:
**GU1a** (la interfaz de U1 completa, sin CP‑07) se cruzó el 2026‑09‑28 con la CI en verde (PR #14);
**GU1b** es CP‑07 ejecutado y registrado, en la fase Med. Con n = 1 por escenario, el resultado es
un dato, no una muestra, y así se cita.

## 5. Mantenibilidad

**Modularidad (RNF‑05).** La hipótesis central de la tesis es una propiedad de mantenibilidad y
está probada empíricamente: `git diff --stat core/` vacío tras implementar los adaptadores
telecom, industrial y sistemas (indicador 4), y `tests/unit/test_arquitectura.py` (parametrizada
sobre los módulos existentes: un módulo nuevo genera su caso solo) la vuelve a comprobar en cada
corrida — un adaptador que importe de `core` algo distinto de `core.contracts` rompe la suite.
La meta es que `core/` no cambie **al agregar un dominio**; `core/` sí cambió después por
decisiones registradas que no son dominios: la modalidad a destajo (D9, sprint del prototipo), las
correcciones de la fase C1 y los dos commits que la spec de cierre §5 autorizó en C3 (INV‑080 e
INV‑015 7a). Ninguno de esos commits tocó `adapters/` ni `ml/`: es la condición que
`scripts/guardia_nucleo.py` vigila en la CI.

**Capacidad de prueba (RNF‑06).** La meta es cobertura de `core/` ≥ 80 %. La CI la exige en cada
cambio: el paso «Cobertura de core >= 80 %» de `.github/workflows/ci.yml` corre
`coverage report --include="core/*" --fail-under=80` en Linux y falla por debajo. La cifra medida
y su corrida están en [plan_pruebas.md §10](plan_pruebas.md).

**Analizabilidad.** Cada hecho vive en un solo lugar (DRY: constantes en `ParametrosCosto`, alias
de unidades en `contracts.unidades`, línea base en el fixture), con una excepción declarada: el
evaluador de expresiones trazables existe en cinco copias, la del núcleo y una por adaptador
(INV‑006, aceptado por decisión de arquitectura registrada y pendiente del aval del tutor;
[expediente §A.3](bitacora/2026-09-23-C1-expedientes.md)). Toda cantidad lleva su origen (RF‑03);
`ruff` (reglas E, F, W, I, B, UP, N) corre limpio.

**Modificabilidad.** Agregar un dominio = un paquete nuevo bajo `adapters/` que subclasifica
`AdaptadorDominio`; la guía para terceros está en el [manual técnico §4](manual_tecnico.md).

**Veredicto: cumple.**

## 6. Portabilidad (RNF‑07 y RNF‑19)

Instalación con `uv sync --locked` (+ extras) sin pasos manuales. Se verificó primero en Windows 11
(equipo de desarrollo) y, desde 2026‑09‑15
([primera corrida en verde, 34969162933](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/34969162933)),
la integración continua lo verifica en cada PR en runners de GitHub con Linux (`ubuntu-latest`) y
Windows (`windows-latest`): suite completa con `-W error` y 0 omitidas en ambos sistemas (la
corrida vigente, en [plan_pruebas.md §10](plan_pruebas.md)). Portar no exigió ningún cambio de
código ni de pruebas: no hay rutas codificadas ni dependencias del sistema operativo en el código
propio.

**RNF‑19 (1.0.0).** El camino de usuario pasa a ser el instalador de Windows: sin administrador ni internet, con Python propio, ≤ 150 MB el básico y ≤ 650 MB el completo, arranque a la salud 200 en ≤ 60 s en la CI y ≤ 20 s en el equipo de desarrollo, y actualización que conserva el 100 % de las dos bases. La evidencia la dan el flujo `instalador.yml` (tamaño y prueba de humo en cada versión) y la medición de [plan_pruebas.md §10](plan_pruebas.md); hasta que esa medición exista, este punto está **por medir**.

**Veredicto: cumple** (las dos plataformas declaradas, con evidencia automatizada en cada cambio).

## 7. Seguridad (RNF‑08)

Por inspección del repositorio y de las dependencias: 0 credenciales versionadas; ejecución
enteramente local (SQLite en el equipo del usuario, API y UI en localhost). En operación hay **dos
llamadas de red, ambas declaradas**: la descarga inicial del modelo de `sentence-transformers`
(I2), que queda en caché, y three.js, que el Visor 3D carga desde `cdnjs.cloudflare.com` con
versión fija cada vez que se pinta (`ui/paginas/visor.py`, `URL_THREE_JS`; INV‑077, declarada en
C4). Sin red, el navegador no obtiene three.js y el visor no puede dibujar el modelo. Que la suite
pase sin red una vez poblada la caché **no se ha verificado con la red cortada**. Hay solo un
indicio: con `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`, `tests/unit/test_normalizacion.py` pasa
(revisión de pruebas de GC4). La corrida sin red se mide en Med.

**Veredicto: cumple** para el perfil declarado (herramienta local de tesis, sin autenticación),
con las dos excepciones de red declaradas.

## 8. Compatibilidad (RNF‑09)

La compuerta G1 se cruzó **con salvedad**: el adaptador civil extrae de `tanquilla.ifc` cantidades
exactas al cálculo manual (0,224 m³ de concreto), pero el modelo fue generado programáticamente
con ifcopenshell, no exportado por un modelador BIM real. La meta (archivos de ≥ 2 herramientas,
p. ej. Revit y Bonsai) sigue abierta; la alternativa tabular documentada existe desde el diseño.

**Veredicto: parcial**, brecha declarada en la bitácora de F.1.

## 9. Resumen

| Característica | Meta de la ERS | Resultado | Veredicto |
|---|---|---|---|
| Adecuación funcional | clase 3 AACE; RF cubiertos | desviación 0,00 %; 7 de 7; RF‑16 parcial y RF‑20 no implementado (cuáles y por qué: [plan_pruebas.md §8](plan_pruebas.md)) | parcial |
| Fiabilidad | reproducibilidad 100 % | comparación exacta en verde; suite en verde, 0 omitidas ([plan_pruebas.md §10](plan_pruebas.md)) | cumple |
| Eficiencia de desempeño | < 5 s con ≤ 100 partidas | **1,17 s** con 100 partidas | cumple |
| Usabilidad | RNF‑04 Likert ≥ 4/5 sobre el informe; RNF‑10 CP‑07 sin ayuda en ≤ 20 min, bloque B ≥ 4,0 y ningún ítem < 3 | RNF‑04: por medir en Med ([protocolo_rnf04.md](protocolo_rnf04.md)); RNF‑10: CP‑07 por ejecutar (GU1b, Med) | pendiente |
| Mantenibilidad | `core/` intacto al agregar un dominio; cobertura de `core/` ≥ 80 % | diff vacío tras I5 + `test_arquitectura.py`; la CI exige ≥ 80 % (cifra en [plan_pruebas.md §10](plan_pruebas.md)) | cumple |
| Portabilidad | 0 pasos manuales, Windows y Linux | Windows ✔ (local y CI); Linux ✔ (CI) | cumple |
| Seguridad | 0 y 0 (credenciales versionadas; llamadas de red durante la operación), con dos excepciones declaradas | 0 credenciales; dos llamadas de red declaradas (modelo de ML en caché, three.js del visor) | cumple |
| Compatibilidad | IFC de ≥ 2 modeladores | exacto contra modelo programático | parcial |

Cinco características cumplen su meta con evidencia automatizada o medida; una espera una medición
humana (usabilidad, en Med) y dos quedan parciales por brechas declaradas: la adecuación funcional
(los RF que [plan_pruebas.md §8](plan_pruebas.md) no da en verde) y la compatibilidad (IFC real). Ninguna brecha es silenciosa: todas tienen dueño,
causa y registro.
