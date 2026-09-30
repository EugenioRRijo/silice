# Auditoría parcial — capa `scripts`

Commit auditado: `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8` (worktree `cierre-C0`, HEAD
`3b7645ef3c45fc7f858f8b8502f1b4618dd71d60`; sin cambios locales sobre `scripts/`, los números de
línea valen igual sobre ambos). Criterios: spec
`2026-09-23-plan-cierre-tesis-design.md` §4. Las decisiones D1–D9 de
`docs/dossier_g0.md` se toman como riesgo ya rastreado y no se reportan. Por instrucción del
encargo, `scripts/meta_*.py` quedan fuera del criterio S (responsabilidad única); los demás
principios sí se les aplicaron.

## 1. Archivos revisados (25 de 25 de `git ls-files scripts/`)

```
scripts/README.md
scripts/__init__.py
scripts/derivar_listas_telecom.py
scripts/exportar_openapi.py
scripts/extraer_arenaza.py
scripts/extraer_maprex.py
scripts/generar_resultados_ml.py
scripts/generar_tanquilla_ifc.py
scripts/guardia_nucleo.py
scripts/lista_maprex_usd.py
scripts/medir_rnf03.py
scripts/meta_alpha.py
scripts/meta_asistente.py
scripts/meta_datos.py
scripts/meta_i6.py
scripts/meta_multidominio.py
scripts/meta_prototipo.py
scripts/meta_redaccion.py
scripts/seed.py
scripts/seed_demo.py
scripts/seed_industrial.py
scripts/seed_sistemas.py
scripts/seed_telecom.py
scripts/simular_corpus.py
scripts/simular_lista.py
scripts/verificar_omitidas.py
```

## 2. Hallazgos

| ID provisional | capa | principio | severidad | evidencia archivo:línea | hallazgo | corrección propuesta | fase destino |
|---|---|---|---|---|---|---|---|
| scripts-01 | scripts | DRY / encapsulación del helper compartido (metodologia.md §5.2 regla 6) | menor | `scripts/guardia_nucleo.py:25-31` (importa `_commits_nucleo_intacto`, `_git`, `_ramas_adaptador`); `scripts/verificar_omitidas.py:26` (importa `_resultado_de`, `_testcases`); `scripts/meta_prototipo.py:28`, `scripts/meta_datos.py:37`, `scripts/meta_redaccion.py:28`, `scripts/meta_i6.py:24-30`, `scripts/meta_multidominio.py:40-46`, `scripts/meta_asistente.py:31-37` (los seis importan `_evaluar` y/o `_filas_a_json`) | Ocho módulos (dos de ellos fuera de la familia `meta_*.py`) dependen de nombres con guion bajo de `scripts/meta_alpha.py`. El guion bajo declara "privado del módulo"; en la práctica `meta_alpha.py` es una biblioteca interna compartida por toda la capa, pero sus funciones nunca se promovieron a nombres públicos: no hay duplicación de código (el helper sube al paquete común, como pide la regla), pero su condición de interfaz estable no está declarada, así que cualquier refactor interno de `meta_alpha.py` puede romper ocho dependientes sin que el nombre lo advierta | Quitar el guion bajo a las funciones que ya cruzan módulos (`_git`, `_commits_nucleo_intacto`, `_ramas_adaptador`, `_resultado_de`, `_testcases`, `_evaluar`, `_filas_a_json`) y documentarlas como la API interna de `meta_alpha.py` para el resto de `scripts/`, o extraerlas a un módulo `scripts/_comun.py` sin ambigüedad de privacidad | C3 |
| scripts-02 | scripts | DRY (sembradores) | menor | `scripts/seed_telecom.py:451-463` (`sembrar_telecom` crea `models.ListaPrecios` sin copiar precios de ninguna lista previa); `scripts/seed_industrial.py:141-153` (`sembrar_industrial`, mismo patrón); `scripts/seed_sistemas.py:131-143` (`sembrar_sistemas`, mismo patrón); contraste: `scripts/seed_demo.py` (`sembrar_demo`, Tarea 2 de la Sesión P4.2) sí resuelve `Catalogo(sesion).lista_vigente(caso.fecha)` y copia sus precios antes de crear su propia lista | Los tres sembradores de dominio no aplican la protección contra "herencia de precios" que `seed_demo.py` sí implementa: si alguna vez se cargaran dos dominios en la misma base de datos, `Catalogo.composicion()` sin `lista=` explícito (`core/catalog/repositorio.py::lista_vigente`, que ordena por fecha sin distinguir dominio) podría resolver contra la lista de otro dominio. Hoy es **latente**: cada sembrador usa su propio archivo `--db` por defecto y sus propias funciones de reconstrucción siempre pasan `lista=` explícito, así que no se ha observado el defecto (mismo diagnóstico que `2026-09-23-ui-recorrido-guiado-design.md` §9, "trabajo futuro declarado") | Extraer el patrón "crear lista nueva copiando los precios de la vigente" de `seed_demo.py` a una función compartida (p. ej. en `scripts/_comun.py` o como utilidad de `core.catalog`) y que `sembrar_telecom`, `sembrar_industrial` y `sembrar_sistemas` la reutilicen antes de que un consumidor futuro (p. ej. "sembrar por dominio" desde la UI) cargue dos dominios en una sola base | C3 |
| scripts-03 | scripts | DRY (redondeo de presentación, `core.verification.informe.DECIMALES_PRESENTACION`) | menor | `scripts/seed_demo.py:544,546,549`; `scripts/seed_industrial.py:257,259`; `scripts/seed_sistemas.py:250,252`; `scripts/seed_telecom.py:572-573,577`; `scripts/simular_lista.py:59` (`Decimal("0.01")` de precisión monetaria escrito a mano) | Los resúmenes CLI de los cuatro sembradores de dominio (no `seed.py`, que no imprime precios) formatean `precio_unitario`/`total`/`monto` con `f"{...:.2f}"` en vez de importar `DECIMALES_PRESENTACION` (o `formatear_decimal`) de `core.verification.informe`, que ya es la fuente única declarada para "cuántos decimales de dinero se presentan" (`core/budget/excel.py` sí lo hace así). Si `DECIMALES_PRESENTACION` cambiara, seis puntos de estos cuatro archivos quedarían desalineados en silencio | Sustituir los `:.2f` de los resúmenes CLI por `formatear_decimal(valor, DECIMALES_PRESENTACION)` importado de `core.verification.informe`; en `simular_lista.py`, importar la misma constante en vez del literal `Decimal("0.01")` | C3 |
| scripts-04 | scripts | Gestión de datos / efectos destructivos | menor | `scripts/seed.py:41,118,125-126` (`RUTA_POR_DEFECTO = "data/apu.db"`; `--reiniciar` ejecuta `models.Base.metadata.drop_all(motor)` sin confirmación); `scripts/seed_demo.py:58,123` (mismo `RUTA_POR_DEFECTO = "data/apu.db"`, la misma base que usan todas las páginas de `ui/paginas/` por defecto, según su propio docstring); `scripts/seed_telecom.py:171,547-548`; `scripts/seed_industrial.py:91,231-232`; `scripts/seed_sistemas.py:92,221-222` (mismo patrón `--reiniciar` sin confirmación en los cinco) | `--reiniciar` borra el esquema completo (todas las tablas, no solo las del dominio que siembra ese script) sin ningún aviso interactivo ni respaldo, y en `seed.py`/`seed_demo.py` apunta por defecto a `data/apu.db`, el archivo que la UI usa como base de trabajo. `NORMAS.md` §6 declara que "las bases SQLite se regeneran con `scripts/seed.py`" (la regeneración en sí es diseño declarado), pero la ausencia de una guarda de confirmación sobre el archivo por defecto sigue abierta: `2026-09-23-ui-recorrido-guiado-design.md` §9 ya la registra como restricción pendiente ("la restricción contra `--reiniciar`, que sí destruye la base") | Añadir una confirmación explícita (o exigir `--confirmar`) cuando `--reiniciar` se combine con la ruta por defecto de cada script, o negarse como ya hace `simular_corpus.py` cuando detecta que el archivo de destino es el de trabajo compartido | C3 |
| scripts-05 | scripts | DRY (rutas repetidas) | menor | `scripts/seed.py:41` (`RUTA_POR_DEFECTO = "data/apu.db"`); `scripts/seed_demo.py:109,123` (ya hace `from scripts import seed` pero declara de nuevo el literal `"data/apu.db"` en vez de `seed.RUTA_POR_DEFECTO`); `scripts/simular_lista.py:86-87` (mismo literal `"data/apu.db"`, sin importarlo de ningún módulo hermano) | La ruta por defecto de la base de datos principal se escribe como literal en tres archivos; `seed_demo.py` ya importa `scripts.seed` para otra cosa (`seed.sembrar`) y pudo reusar su constante | Que `seed_demo.py` y `simular_lista.py` importen `RUTA_POR_DEFECTO` de `scripts.seed` en vez de redeclarar el literal | C3 |
| scripts-06 | scripts | Coherencia documental | menor | `scripts/README.md:1-6` (documenta solo `seed.py` y `meta_alpha.py`); `scripts/__init__.py:1` (docstring: "siembra de datos y meta del sprint alpha") | De los 24 scripts `.py` de la capa, el README solo describe 2. No mencionan `seed_telecom.py`, `seed_industrial.py`, `seed_sistemas.py`, `seed_demo.py`, `guardia_nucleo.py`, `verificar_omitidas.py`, `simular_corpus.py`, `simular_lista.py`, `exportar_openapi.py`, `medir_rnf03.py`, los extractores MaPreX/ARENAZA/telecom, `generar_resultados_ml.py`, `generar_tanquilla_ifc.py`, `lista_maprex_usd.py`, ni los cinco `meta_*.py` posteriores a `meta_alpha.py` | Ampliar la tabla de `scripts/README.md` con los 22 scripts faltantes (o, como mínimo, agruparlos por sesión/dominio) y actualizar el docstring de `scripts/__init__.py` | C3 |

## 3. Sin hallazgos

- **`Decimal` y nunca `float`** — sin hallazgos. Único uso de `float` encontrado en toda la capa:
  `scripts/generar_tanquilla_ifc.py:118,152`, convirtiendo `Decimal` a `float` **solo** en la
  llamada a la API de `ifcopenshell` (IFC no admite otra magnitud) y declarado explícitamente en el
  docstring del módulo ("IFC solo admite `float` en sus magnitudes: se convierte al final, no
  antes, y el valor sobrevive el viaje de ida y vuelta"). Es diseño declarado, no violación. El
  resto de la capa (extractores MaPreX/ARENAZA, sembradores, simuladores, medición de RNF‑03) usa
  `Decimal` de punta a punta, incluidas las conversiones Bs→USD y las cuantizaciones de tolerancia.
- **El motor de costos es una función pura (principio 4)** — sin hallazgos. Ningún script
  reimplementa la fórmula de costeo: todos llaman a `core.costing.calcular_apu` o
  `core.budget.generar_presupuesto`/`elaborar`. La única lógica de costeo fuera del motor
  (`scripts/seed_telecom.py::con_mano_obra`, que despeja un sueldo sintético para la política "50 %
  del presupuesto total") está documentada como deliberadamente externa al motor y no lo modifica.
- **El informe de auditoría se genera siempre (principio 7)** — sin hallazgos en lo que a `scripts/`
  corresponde: `seed_industrial.py` y `seed_sistemas.py` llaman a `core.verification.auditar` antes
  de imprimir su resumen; ningún script construye un presupuesto y omite la auditoría donde el flujo
  la exige.
- **Cuarentena del corpus simulado** — sin hallazgos. `scripts/simular_corpus.py` implementa las
  dos capas que anuncia su docstring: por archivo (`main` se niega si `--db` ya existe) y por código
  (`scripts/meta_prototipo.py::_referencias_ml_a_corpus`, meta P11, falla si algún módulo de `ml/`
  menciona el generador o el corpus). Verificado leyendo ambos mecanismos.
- **Trazabilidad (`origen_id`, `origen_tipo`, `regla`)** — sin hallazgos. Los `ItemComputo` que
  arman `seed_telecom.py::item_de`, `seed_industrial.py` (vía `AdaptadorIndustrial`) y
  `seed_sistemas.py` (vía `AdaptadorSistemas`) declaran `origen_id` y `origen_tipo` trazables al PDF
  o al CSV de origen; el mecanismo del tubo corrugado declara además `regla` para que R1 lo audite.
- **Contratos inmutables / invariantes de `core.contracts`** — no aplica como hallazgo de esta capa:
  los scripts solo construyen contratos (`LineaMaterial`, `LineaEquipo`, `ComposicionAPU`, etc.), no
  los redefinen ni los eluden; no se encontró ninguna construcción que sortee un `__post_init__`.
