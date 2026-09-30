# Bitácora — Sprint alpha (versión alpha 0.1)

**Fechas:** 2026‑08‑29 → 2026‑08‑31 · **Rama:** `main` (un incremento por rama `inc/…`, fusionado con
`--no-ff`) · **Compuertas cruzadas:** G‑núcleo (motor en verde sin tocar la línea base, etiqueta
`g-nucleo`) · **Pendientes:** G0 (tutor), G1 (IFC), G2 (datos para ML).

## Objetivo del sprint

Construir la **versión alpha**: el flujo completo de la tesis sobre el caso de estudio — cantidades
trazables → APU → presupuesto → curva de inversión (cierre al 100 %) → auditoría 7 de 7 —, la prueba
empírica de la hipótesis central (tres adaptadores nuevos sin tocar `core/`), el primer caso de uso de
valor percibido (UC‑02, actualización masiva de precios) y la documentación de Fase 0 completa (ERS,
modelo de datos, arquitectura). Todo medido por un solo comando, `uv run python scripts/meta_alpha.py`,
con doce metas `OK`/`FALLA`/`PENDIENTE`.

Fuera del alpha, por *Definition of Ready* incumplida: I3.1 (no existe `data/samples/tanquilla.ifc`),
I2 e I6.x (sin datos ni modelos de ML), I6.2, F.1 completa, F.2 y F.3.

## Cómo se trabajó

Trece tareas (más una corrección, T14) en cinco oleadas, cada una con un implementador en su propio
worktree y rama `inc/…`, una revisión independiente por tarea (cumplimiento del brief + calidad),
rondas de corrección acotadas y fusión a `main` por el integrador, que corría la meta tras cada fusión.
Los briefs, reportes, paquetes de revisión y el ledger del sprint viven fuera de git
(`.superpowers/sdd/`); lo que sobrevive es esta bitácora, las bitácoras de sesión y el historial.

## Qué se hizo, por tarea

| Tarea | Sesión del PLAN | Rama | Commits | Fusión | Bitácora de sesión |
|---|---|---|---|---|---|
| T1 Meta del alpha | — | `inc/alpha-meta` | `f75d850`, `21b13c6` | `be70863` | [alpha-meta](2026-08-29-alpha-meta.md) |
| T2 Motor de costos | I0.3 | `inc/I0.3-motor` | `6487910` | `a1be0e6` (etiqueta `g-nucleo`) | [I0.3-motor](2026-08-29-I0.3-motor.md) |
| T3 ERS IEEE 830 | 0.1 | `inc/0.1-ers` | `c852530`, `000067b` | `6ccd7be` | [0.1-ers](2026-08-29-0.1-ers.md) |
| T4 Reglas paramétricas civil y adaptador tabular | I3.2 | `inc/I3.2-civil` | `c34a81d`, `4ec5f80`, `2ef3c0b` | `5342ebd` | [I3.2-civil](2026-08-29-I3.2-civil.md) |
| T5 Modelo de datos, persistencia y catálogo | 0.2, I0.4 | `inc/0.2-modelo-datos-I0.4` | `d64e6bc`, `56c8ae0`, `e0ebf7d` | `90e075f` | [0.2-I0.4-persistencia](2026-08-29-0.2-I0.4-persistencia.md) |
| T7 Siete reglas de verificación e informe | I4 | `inc/I4-verificacion` | `dbaaf50`, `968804d` | `25a36ab` | [I4-verificacion](2026-08-29-I4-verificacion.md) |
| T8 Adaptador telecom | I5 | `inc/I5-telecom` | `1183e0c`, `09dc8c4`, `649935d` | `96bdbf5` | [I5-telecom](2026-08-29-I5-telecom.md) |
| T9 Adaptador industrial | I5 | `inc/I5-industrial` | `2e0e85f` | `eee2d7b` | [I5-industrial](2026-08-29-I5-industrial.md) |
| T10 Adaptador sistemas | I5 | `inc/I5-sistemas` | `7c20bf6` | `7e4ca35` | [I5-sistemas](2026-08-29-I5-sistemas.md) |
| T14 Corrección 4b: balance civil con llaves | I3.2 | `inc/I3.2-civil-balance` | `9c54669` | `b0d12a0` | [I3.2-civil](2026-08-29-I3.2-civil.md) §Corrección 4b |
| T6 Presupuesto, curva, Excel y persistencia | I0.5 | `inc/I0.5-presupuesto` | `4ae50ef`, `3e02242` | `da3d951` | [I0.5-presupuesto](2026-08-29-I0.5-presupuesto.md) |
| T11 UC‑02 actualización de precios y UI mínima | I1 | `inc/I1-actualizacion-precios` | `b83171e`, `c97185a` | `4a9d636` | [I1-actualizacion-precios](2026-08-29-I1-actualizacion-precios.md) |
| T12 Arquitectura 4+1 | 0.3 | `inc/0.3-arquitectura` | `f4951b3`, `ab9a2a7` | `047d0bb` | [0.3-arquitectura](2026-08-29-0.3-arquitectura.md) |
| T13 Integración final | — | `main` | (este cierre) | — | esta bitácora |

Momentos del trabajo (NORMAS.md §1) alcanzados: las cinco pruebas del motor en verde (`g-nucleo`);
`git diff --stat core/` vacío para los cuatro adaptadores (meta M9, verificada por `meta_alpha.py` commit a
commit y por el rango completo de cada rama de adaptador). La compuerta G1 (IFC) sigue abierta: el adaptador civil del alpha es tabular
(NORMAS.md §8.2).

## Decisiones del sprint (rulings del integrador)

| Decisión | Motivo | Costo si es errónea |
|---|---|---|
| Implementadores en paralelo por oleadas, cada uno en su worktree con rutas exclusivas | petición del usuario; las rutas disjuntas eliminan conflictos | fusiones manuales |
| Contratos congelados; toda insuficiencia se documenta, no se parchea | NORMAS.md §5 y §9 | rodeos en el código (ver hallazgos) |
| Directivas `_balance`, `_tolerancia`, `_unidad_original` en `ItemComputo.especificaciones` (claves con `_` = directivas para el núcleo) | R5 y R3 necesitan datos que el contrato no tiene; la convención vive en `core/verification/directivas.py` y una prueba comprueba que el adaptador civil usa las mismas claves | dos declaraciones de la misma convención |
| Evaluador de expresiones duplicado entre `core/verification` y cada adaptador, atado por una prueba de equivalencia | `adapters/` solo importa `core.contracts`; un adaptador no importa otro | divergencia detectada solo por esa prueba |
| `DecimalExacto` (texto) en SQLite en vez de `Numeric` | exactitud y cero advertencias; en PostgreSQL sería `Numeric(18,6)` | sin ordenación numérica en SQL (no se necesita) |
| Modelos SQLAlchemy con los nombres del ER, importados siempre cualificados (`models.Presupuesto`) | siete nombres coinciden con contratos | confusión si alguien importa sin cualificar |
| Insumos homónimos con precio distinto → variantes en el catálogo (`EQU-007-B`) | la línea base los tiene (Agua, Pala, Cinta métrica, Nivel de mano); candidata a regla R8 | catálogo con duplicados aparentes |
| El presupuesto referencia su lista de precios **y** congela el `ResultadoAPU` por renglón (versionado híbrido); `cargar_presupuesto` verifica la reconstrucción | reconstrucción a fecha (UC‑02) y detección de composiciones editadas después | divergencia detectada como `ValueError` |
| La curva cierra por construcción: el último período es `total − Σ anteriores` y su acumulado es `total` literal; períodos etiquetados con los códigos entre corchetes (`"Dia 1 [LB-01-EXC]"`) | el hallazgo 3 de la línea base debe ser imposible; R7 concilia por códigos | ninguno |
| R6 con severidad ERROR; R7 devuelve `[]` si el presupuesto no declara curva | el 7/7 cuenta hallazgos ≥ ERROR; R2 ya señala la ausencia de curva | un presupuesto sin plan pasa R7 en silencio |
| `elaborar` audita siempre | principio 7 de NORMAS.md | ninguno |
| Incrementos fusionados a `main` sin preguntar por cada uno, con `--no-ff`; sin push | plan aprobado; no hay remoto | revertir fusiones |
| G0 (tutor) no cruzable desde aquí | requiere revisión humana | ninguno funcional |

## Hallazgos de la investigación

**Insuficiencias de los contratos** (todas rodeadas sin tocar `core/contracts/`; entrada del capítulo
de resultados y del manual técnico):

1. `Hallazgo` no lleva `codigo_partida` → `InformeAuditoria.partida_por_origen` lo resuelve desde los
   `origen_ids` (I4).
2. `PuntoCurva` no lleva `codigo_partida` → códigos entre corchetes en la etiqueta del período (I4, I0.5).
3. El criterio de amortización de R6 no es declarable en `LineaEquipo` → R6 verifica uniformidad del
   factor, no el criterio (I4).
4. `Presupuesto` no guarda los `ParametrosCosto` → viajan por las columnas de `models.Presupuesto` (I0.5).
5. `ItemComputo` no distingue la unidad original del cómputo → directiva `_unidad_original` (I4);
   `models.ItemComputo.unidad_original` sí existe (I0.5).
6. `core.contracts.unidades` no conoce `"pf"` (punto de función) ni canoniza `pulg`; la segunda
   canonización vive en `core/verification/texto.py` (I5 sistemas, I4).
7. No existe contrato para el informe de auditoría (`InformeAuditoria` es de `core.verification`) (0.1).
8. `Rendimiento` no representa dispersión (media, mínimo, máximo) para RF‑26 (0.1).

**Otros hallazgos:** la política de mano de obra "50 % del total" de los presupuestos ARENAZA es de
costeo, no de cómputo, y no le corresponde al adaptador telecom; se analizaron tres opciones y se
recomienda una `LineaManoObra` sintética calculada fuera del motor (I5 telecom). La unidad
"intervención" (industrial) y "pf" (sistemas) no tienen rendimiento natural en el motor por
rendimiento diario (I5). El adaptador civil emitía el balance sin llaves, incompatible con R5: lo
detectó la verificación y se corrigió en 4b con una prueba de integración civil → R5. La verificación
detecta, además de las siete inconsistencias, dos hallazgos adicionales (8: encofrado computado en m3
contra un APU en m2; 9: la brecha de 11,11 USD de la curva se explica día a día con R7). La consola de
Windows es cp1252: la meta imprime tablas ASCII.

## Impedimentos

- **G0:** ERS, modelo de datos y arquitectura completos pero pendientes de revisión del tutor;
  R7 sigue siendo decisión de diseño de este proyecto (validar en la misma revisión).
- **G1:** sin `tanquilla.ifc`, la Sesión I3.1 no tiene *Definition of Ready*; el adaptador tabular
  cubre el dominio civil del alpha.
- **G2:** sin registros de APU suficientes por dominio, `ml/` queda para el siguiente sprint
  (contar registros y aplicar NORMAS.md §8.1).
- **FCAS 600 %:** sin fuente primaria confirmada (convención colectiva vigente); cerrar antes de
  defender el capítulo IV.
- Operativos: la creación simultánea de cuatro worktrees falló en el harness (carrera); se limitó a dos
  por despacho. La rama de T7 nació antes de la fusión de I0.4, así que T6 tuvo que recibir `main` a
  mitad de tarea (el segundo commit de T6 es la persistencia). Una revisión despachada el día 29 se
  perdió con un reinicio de sesión y se repitió el día 30.

## Evidencia de la meta

Sobre `main` = `4a9d636` (2026‑08‑30): **12/12 metas OK** — 295 pruebas, 0 fallidas, 0 errores;
cobertura de `core/` 97,82 % (umbral 80 %); M9 «núcleo intacto» verificado sobre los 7 commits de
adaptadores; ruff check y ruff format limpios. La tabla completa la imprime
`uv run python scripts/meta_alpha.py`.

Tras la oleada de corrección de la revisión final (fusión `b31e899`): **12/12** con 308 pruebas,
cobertura de `core/` 97,96 % y M9 reforzado (8 commits evaluados y las 4 ramas de adaptador con
`git diff core/` vacío por rango).

## Revisión final de la rama

Revisor independiente sobre todo el sprint (`e783f0c..16f61e6`): **0 Critical, 3 Important y 9
minors promovidos** — un defecto reproducible del adaptador civil (el balance de R5 con dos zanjas
de diámetro distinto usaba solo el último factor), dos docstrings del núcleo que contradecían el
«exactamente dos» de los documentos normativos, y M9 midiendo menos de lo que el README afirmaba.
Fortalezas verificadas por el propio revisor: contratos congelados de verdad (`git diff` vacío en
`core/contracts/` y en las pruebas del motor a lo largo de los 41 commits), la hipótesis central
comprobada rama por rama, la curva que cierra por construcción y la disciplina `Decimal` sin fisuras.

La oleada única de corrección (`inc/alpha-fixes`, commits `6ba145b` y `f440e47`, fusión `b31e899`)
corrigió los diez ítems con trece pruebas nuevas; la re‑revisión los dio todos por atendidos sin
roturas. Fueron dos commits a propósito — uno civil y uno del resto — porque un commit único que
mezcle `core/` y `adapters/` hace caer M9. Hallazgo adicional al verificar procedencias contra los
PDF: la propia fuente primaria ARENAZA es inconsistente (el tubo corrugado mide 80 m en los cómputos
y 90 m en el presupuesto del mismo documento) — candidata a caso de estudio de R7 en telecom. El
alcance de M9 («rama de adaptador» = la que agrega archivos bajo `adapters/` o `ml/`) se valida con
el tutor en G0.

La etiqueta `alpha-0.1` queda en el commit de este cierre.

## Próximos pasos

1. Presentar ERS, modelo de datos y arquitectura al tutor (G0) y validar R7 y la regla candidata R8.
2. Modelar `tanquilla.ifc` y ejecutar la Sesión I3.1 (G1).
3. Contar registros de APU por dominio y decidir la técnica de `ml/prediction/` (G2); Sesiones I2 y I6.
4. Atender los hallazgos menores diferidos por las revisiones (consolidados en la revisión final).
5. Fase F: API, plan de pruebas IEEE 829, calidad ISO/IEC 25010, manuales.
