# Evaluación de calidad del producto (ISO/IEC 25010) — Sesión F.2

Evaluación del sistema contra el modelo de calidad de producto de ISO/IEC 25010, con las métricas
y metas declaradas en [ERS.md §3.3](ERS.md#33-requisitos-no-funcionales-isoiec-25010). La evidencia
numérica (corrida de la suite, cobertura, medición de desempeño) está registrada **una sola vez**
en [plan_pruebas.md](plan_pruebas.md) §9–§10; aquí se interpreta.

Fecha de la evaluación: 2026‑08‑31, sobre `main` en `02f961a` (cierre del sprint I6);
actualizada el mismo día tras el cierre de UC‑08 (`inc/UC08-escenarios`).

## 1. Adecuación funcional

**Completitud funcional.** 30 de los 31 RF tienen prueba automatizada en verde y **ningún RF
queda sin prueba**: la brecha de UC‑08 (RF‑30, RF‑31) se cerró el 2026‑08‑31 con
`core/budget/escenarios.py` y `tests/unit/test_escenarios.py`. El único RF parcial es RF‑16 (su
persistencia espera un flujo de creación de partidas que no existe en ningún UC implementado —
hallazgo recurrente de I2 e I6, elevado a G0). Los ocho casos de uso operan de extremo a
extremo: UC‑08 quedó cableado el mismo día en las tres capas (núcleo `core.budget`, ruta
`POST /presupuestos/{codigo}/escenarios` y página «Escenarios (UC‑08)» en la UI), con lo que la
interfaz cumple lo que la ERS §3.1 promete.

**Corrección funcional (RNF‑01).** El presupuesto de la línea base corregida se reproduce con
desviación 0,00 % — los cinco precios unitarios dentro de ± 0,01 y los totales exactos en
`Decimal` — muy dentro del rango de la clase 3 de AACE (−20 % / +30 %) que la meta exige. La
prueba de aceptación crítica del trabajo se cumple: **7 de 7 inconsistencias detectadas**
(indicador 1 de la tesis).

**Pertinencia funcional.** El informe de auditoría se genera siempre, sin pedirlo (principio 7 de
CLAUDE.md §2): `elaborar()` no tiene un modo sin auditoría.

**Veredicto: cumple**, con los tres RF no esenciales declarados arriba.

## 2. Fiabilidad

**Madurez.** 395 pruebas, 0 fallos, 0 omitidas, con `-W error` (ninguna advertencia tolerada) en
la corrida registrada. La suite creció de 88 (Sprint 0) a 395 sin retirar ninguna prueba de valor:
la línea base que validó el motor en I0.3 sigue vigilándolo intacta.

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
desarrollo, SQLite local, sin exportación): el ciclo completo de UC‑02 — revalorar 100 partidas
con 41 insumos cambiados, reelaborar con auditoría R1–R7, guardar la versión nueva y su histórico
de incidencias — tarda **1,17 s**, contra la meta de < 5 s: margen de 4×. La suite completa (395
pruebas, incluido el modelo de lenguaje de I2) corre en 100,9 s.

**Veredicto: cumple.**

## 4. Usabilidad (RNF‑04)

La meta (juicio de expertos ≥ 4/5 en Likert sobre el informe de auditoría) **no es automatizable y
está pendiente**: el instrumento ya está redactado ([dossier_g0.md, anexo A](dossier_g0.md)) y se
aplica con el tutor en la Fase 6. Lo que el producto ya
aporta a esa evaluación: hallazgos en español con severidad, impacto cuantificado y los
`origen_id` involucrados; UI multipágina con los flujos implementados y visor 3D del modelo; API
autodocumentada (OpenAPI en `docs/api.json`).

**Veredicto: pendiente de medición** (riesgo bajo: el informe se diseñó desde el caso real).

## 5. Mantenibilidad

**Modularidad (RNF‑05).** La hipótesis central de la tesis es una propiedad de mantenibilidad y
está probada empíricamente: `git diff --stat core/` vacío tras implementar los adaptadores
telecom, industrial y sistemas (indicador 4), y `test_arquitectura.py` (65 casos, generados por
parametrización sobre los módulos existentes) la vuelve a comprobar en cada corrida — un
adaptador que importe de `core` algo distinto de `core.contracts` rompe la suite.

**Capacidad de prueba (RNF‑06).** Cobertura de `core/` **98,05 %** (meta ≥ 80 %); `ml/` 99,29 %,
`api/` 94,56 %, `adapters/` 88,78 %; total medido 96,11 %.

**Analizabilidad.** Cada hecho vive en un solo lugar (DRY: constantes en `ParametrosCosto`, alias
de unidades en `contracts.unidades`, línea base en el fixture); toda cantidad lleva su origen
(RF‑03); `ruff` (reglas E, F, W, I, B, UP, N) corre limpio.

**Modificabilidad.** Agregar un dominio = un paquete nuevo bajo `adapters/` que subclasifica
`AdaptadorDominio`; la guía para terceros queda en el manual técnico (Sesión F.3).

**Veredicto: cumple.**

## 6. Portabilidad (RNF‑07)

Instalación con `uv sync --locked` (+ extras) sin pasos manuales. Se verificó primero en Windows 11
(equipo de desarrollo) y, desde 2026‑09‑15, la integración continua lo verifica en cada PR en
runners de GitHub con Linux (`ubuntu-latest`) y Windows (`windows-latest`, Windows Server 2025):
suite completa de 490 pruebas con `-W error` y 0 omitidas en ambos sistemas
([run 34969162933](https://github.com/EugenioRRijo/tesis-apu-multidominio/actions/runs/34969162933)).
Portar no exigió ningún cambio de código ni de pruebas: no hay rutas codificadas ni dependencias
del sistema operativo en el código propio.

**Veredicto: cumple** (las dos plataformas declaradas, con evidencia automatizada en cada cambio).

## 7. Seguridad (RNF‑08)

Por inspección del repositorio y de las dependencias: 0 credenciales versionadas; ejecución
enteramente local (SQLite en el equipo del usuario, API y UI en localhost); 0 llamadas de red en
operación — la única excepción, declarada y cacheada, es la descarga inicial del modelo de
`sentence-transformers` (I2). La corrida de la suite pasa sin red disponible una vez poblada la
caché.

**Veredicto: cumple** para el perfil declarado (herramienta local de tesis, sin autenticación).

## 8. Compatibilidad (RNF‑09)

La compuerta G1 se cruzó **con salvedad**: el adaptador civil extrae de `tanquilla.ifc` cantidades
exactas al cálculo manual (0,224 m³ de concreto), pero el modelo fue generado programáticamente
con ifcopenshell, no exportado por un modelador BIM real. La meta (archivos de ≥ 2 herramientas,
p. ej. Revit y Bonsai) sigue abierta; la alternativa tabular documentada existe desde el diseño.

**Veredicto: parcial**, brecha declarada en la bitácora de F.1.

## 9. Resumen

| Característica | Meta de la ERS | Resultado | Veredicto |
|---|---|---|---|
| Adecuación funcional | clase 3 AACE; RF cubiertos | desviación 0,00 %; 30/31 RF en verde (26/26 esenciales); 7 de 7 | cumple |
| Fiabilidad | reproducibilidad 100 % | comparación exacta en verde; 395/395 | cumple |
| Eficiencia de desempeño | < 5 s con ≤ 100 partidas | **1,17 s** con 100 partidas | cumple |
| Usabilidad | Likert ≥ 4/5 | instrumento por aplicar (Fase 6) | pendiente |
| Mantenibilidad | `core/` intacto; cobertura ≥ 80 % | diff vacío + 65 pruebas; **98,05 %** | cumple |
| Portabilidad | 0 pasos manuales, Windows y Linux | Windows ✔ (local y CI); Linux ✔ (CI) | cumple |
| Seguridad | 0 credenciales, 0 red | 0 y 0 (excepción declarada) | cumple |
| Compatibilidad | IFC de ≥ 2 modeladores | exacto contra modelo programático | parcial |

Seis características cumplen su meta con evidencia automatizada o medida; una espera una medición
humana (usabilidad) y una queda parcial por una brecha declarada desde su compuerta (IFC real).
Ninguna brecha es silenciosa: todas tienen dueño, causa y bitácora.
