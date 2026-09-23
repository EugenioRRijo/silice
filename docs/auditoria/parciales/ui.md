# Auditoría parcial — capa `ui`

Commit auditado: `cc2243cd5a7efd3b20dc82fe586484a6ef01fea8`. Criterios: spec
`docs/superpowers/specs/2026-09-23-plan-cierre-tesis-design.md` §4. Las decisiones D1–D9 de
`docs/dossier_g0.md` se toman como riesgo ya rastreado y no se reportan. Foco de esta pasada: S
(¿una pantalla que pinta, calcula y persiste?), DRY, pureza de `ui/composicion.py`, dependencias
entre `ui` y `scripts`, `Decimal` sin `float`, manejo de errores sin trazas crudas.

## 1. Archivos revisados (14 de 14 de `git ls-files ui/`)

```
ui/__init__.py
ui/app.py
ui/composicion.py
ui/paginas/__init__.py
ui/paginas/actualizacion.py
ui/paginas/catalogo.py
ui/paginas/componer.py
ui/paginas/elaborar.py
ui/paginas/escenarios.py
ui/paginas/historico.py
ui/paginas/similares.py
ui/paginas/simulador.py
ui/paginas/visor.py
ui/visor3d.py
```

## 2. Hallazgos

| ID | capa | principio | severidad | evidencia archivo:línea (sobre el commit auditado) | hallazgo | corrección propuesta | fase destino |
|---|---|---|---|---|---|---|---|
| ui-01 | ui | S (responsabilidad única) | menor | `ui/paginas/componer.py:29,32,55` (importa a la vez `streamlit`, `sqlalchemy.orm.Session` y `core.costing.calcular_apu`); `:111-193` (`render`/`_pagina` orquestan cabecera, tres tablas, desglose en vivo, guardado UC-10/UC-11 y una segunda historia de usuario: cantidades de obra + elaborar presupuesto + exportar Excel, `:682-834`); persiste en `:639-665` (`sesion.commit()`, `Catalogo.cargar_composicion`/`reemplazar_composicion`) | Una sola pantalla (872 líneas) pinta, calcula (llama a `calcular_apu` para el desglose en vivo), persiste la composición (UC-10/UC-11) y además reimplementa un recorte de UC-01 (elaborar presupuesto y exportar Excel desde la misma página). Cumple los tres criterios de evidencia S de la spec §4 a la vez. La lógica de dominio ya está bien separada en `ui/composicion.py` (puro); lo que falta separar es la orquestación Streamlit de las dos historias de usuario. Hay pruebas sobre `_guardar` (`tests/unit/test_ui_componer.py`), así que no es un vacío de trazabilidad, solo de estructura | Partir la página en la composición (UC-10/UC-11: cabecera, tablas, desglose, guardar) y un módulo de orquestación aparte para "cantidades de obra → elaborar → exportar" (UC-01), o extraer este último bloque a su propia función/módulo reutilizable con `ui/paginas/elaborar.py` | C3 (spec §5: si el inventario propone dividir `componer.py` por el criterio S, la Tarea 11 de U1 lo hace) |
| ui-02 | ui | DRY | menor. Cruza: scripts | `ui/paginas/actualizacion.py:47`; `catalogo.py:24`; `componer.py:79`; `elaborar.py:38`; `escenarios.py:43`; `historico.py:25`; `similares.py:40`; `simulador.py:25` (las ocho declaran `RUTA_BASE_POR_DEFECTO = "data/apu.db"`); `scripts/simular_lista.py:86-87` (`default="data/apu.db"`, novena copia del mismo valor); reconocido en el propio `ui/app.py:18-23` | El valor por defecto de la ruta de la base SQLite está escrito nueve veces (ocho páginas más `scripts/simular_lista.py`) en vez de una sola. `ui/app.py` ya documenta la duplicación como deliberada por ahora (evita un import circular `ui.app`↔`ui.paginas.*`) | **Previsto en U1**: el plan `docs/superpowers/plans/2026-09-23-ui-recorrido-guiado-u0-u1.md` (Tarea 8) ya centraliza `RUTA_BASE_POR_DEFECTO` en `ui/caso.py` como única definición en `ui/`, y la Tarea 10 reescribe `ui/app.py` para que ninguna página salvo el Inicio la pida. No requiere corrección nueva | C3 (ya en el plan de U1, Tareas 8 y 10) |
| ui-03 | ui | DRY / coherencia de presentación | menor | `ui/paginas/componer.py:56-57` (importa `DECIMALES_PRESENTACION` y `formatear_decimal` pero solo los usa una vez, en `:848`); `:471-476` (desglose en vivo: `str(resultado.materiales)` … `str(resultado.precio_unitario)`, sin redondear); `:521-522,536-538,552-553` (bloque "Partidas similares del catalogo": `str(linea.cantidad)`, `str(linea.precio)`, `str(linea.depreciacion)`, `str(linea.sueldo)`); `:668-670` (mensaje de guardado: `f"...precio unitario {resultado.precio_unitario}."`) | `componer.py` muestra `Decimal` sin pasar por `formatear_decimal`/`DECIMALES_PRESENTACION` en tres lugares (desglose en vivo, mensaje de guardado y la lista de partidas similares), a diferencia de las demás pantallas y de su propio uso correcto en `:848`. El bloque de "Partidas similares" es casi idéntico al de `ui/paginas/similares.py:130-176`, que sí usa `formatear_decimal` para las mismas columnas — la única definición de presentación del sistema (CLAUDE.md §2, principio 1) queda aplicada de forma inconsistente dentro del mismo archivo | Pasar los seis valores del desglose en vivo, el precio unitario del mensaje de guardado y las cuatro columnas del bloque de partidas similares por `formatear_decimal(valor, DECIMALES_PRESENTACION)`, igual que el resto de las pantallas | C3 |
| ui-04 | ui | DRY | menor | `ui/composicion.py:68-81` (`_texto`) frente a `ui/paginas/componer.py:752-762` (`_celda_de_cantidad`), cuerpos idénticos (`fila.get(clave)`, `None`→`""`, `str(valor).strip()`, `"nan"`→`""`) | `_celda_de_cantidad` duplica literalmente `ui.composicion._texto`. El propio docstring de `_celda_de_cantidad` lo reconoce ("Mismo criterio que `ui.composicion._texto` (privada, no importable desde aquí)"), lo que documenta la duplicación sin eliminarla — contradice `docs/metodologia.md` §5.2.6 ("cuando dos módulos necesitan el mismo helper, el helper sube al paquete común más cercano, nunca se copia") | Quitar el guion bajo a `_texto` en `ui/composicion.py` (o exportar un alias público) e importarlo desde `componer.py` en vez de duplicarlo | C3 |

## 3. Sin hallazgos

- **`Decimal` en todo lo monetario/dimensional, nunca `float` (principio 3).** No se encontró ningún
  `float` en cálculos de `ui/`. El único `float(...)` textual está en un comentario de docstring de
  `ui/composicion.py:73` explicando el comportamiento de `str(float("nan"))`, no en código ejecutable.
  `ui/visor3d.py` sí trabaja con floats crudos (`shape.geometry.verts`), pero son coordenadas de
  malla 3D para renderizar el IFC, no cantidades, precios, factores ni rendimientos del dominio APU;
  no aplica el principio.
- **`ui/composicion.py` sigue puro.** No importa `streamlit`, `pandas` ni `sqlalchemy`; solo
  `core.contracts`, `core.verification.texto` y, bajo `TYPE_CHECKING`, tipos de `ml/`. Los cuatro
  "ayudas de AREN.IA" cargan sus submódulos de `ml/` de forma perezosa e inyectable, degradando
  siempre a `None`/`[]`/`False` sin propagar la excepción.
- **Manejo de errores sin trazas.** No hay `except:` desnudo, `except Exception as e: raise`,
  `st.exception()` ni `traceback` en `ui/`. Las nueve páginas capturan tuplas de excepciones
  previsibles (`LookupError`, `ValueError`, `ArithmeticError`, `SQLAlchemyError`, y en `visor.py`
  además `OSError`/`ifcopenshell.Error`) y las muestran con `st.error(str(error))`, nunca una traza
  cruda. Los `except Exception` amplios de `ui/composicion.py` (ayudas de AREN.IA) son degradación
  declarada por diseño (spec §3.7, "todas sugerencia y ninguna bloqueante"), no hallazgo.
- **Dependencias entre `ui` y `scripts`.** Existen en los dos sentidos
  (`ui/paginas/actualizacion.py` → `scripts.seed`; `ui/paginas/simulador.py` →
  `scripts.simular_lista`; `scripts/simular_corpus.py` → `ui.composicion`), pero están declaradas
  explícitamente en `docs/arquitectura.md` §4 ("Vista de desarrollo"), líneas 846-854, que además
  verifica que no hay ciclo de módulos. Es diseño declarado, no violación (spec §4, criterio D: "toda
  dependencia entre capas externas se declara en `docs/arquitectura.md`"). La duplicación de valor
  que sí cruza esta frontera queda reportada aparte en ui-02.
- **O — abierto/cerrado, para dominios.** `ui/paginas/elaborar.py` (`_ADAPTADORES_SIN_CODIGOS`,
  `if dominio == Dominio.CIVIL`) y `ui/paginas/componer.py` (selector de `Dominio`) enumeran los
  cuatro dominios, pero la spec §4 nombra explícitamente a `ui/paginas/elaborar.py` como ejemplo de
  punto de composición fuera de `core/` que no es violación. No se reporta.
