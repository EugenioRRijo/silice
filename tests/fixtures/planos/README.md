# Planos de prueba de la importación (SF5)

Aquí viven los archivos de plano que usan las pruebas de `adapters/espacio/planos` (RF‑50, RF‑51).
Todos son **casos construidos para el proyecto** (NORMAS.md §1), no planos de una obra ejecutada ni de un
estudio real: sus coordenadas son los supuestos declarados de las memorias de cálculo de OF‑001.

## `of001.dxf`: procedencia

* **Qué es.** La oficina OF‑001 (baño, cocineta, recepción, cuarto técnico y zonas A y B) con la
  convención de capas del spec §6.6.1: 6 ambientes (polilínea cerrada con su identificador adentro),
  6 fuentes y 21 puntos, con sus atributos de bloque (`ID`, `ALTURA`, `DIAMETRO`, `CALIBRE`, `CIRCUITO`,
  y las extensiones opcionales `CATEGORIA`, `LLAVE`, `AMBIENTE`; ver la bitácora SF, SF5).
* **Cómo se dibujó.** Entidad por entidad con `ezdxf`, por `scripts/dibujar_of001_dxf.py`, que lee las
  **tablas markdown** de `tests/fixtures/memorias/of001.md` (§1.1 a §1.4), `bano_of001.md` y
  `bano_drenaje_of001.md`. **No se generó desde la hoja** `tests/fixtures/espacio_of001.py` ni importa
  código de `adapters/`: una prueba lo vigila (la equivalencia con la hoja sería circular si lo hiciera).
* **Naturaleza.** Programático (no hecho en un programa de CAD): hereda la salvedad que RNF‑09 declara
  para los archivos de prueba generados por programa. El formato lo verifica `ezdxf` al releerlo; no está
  comprobado en AutoCAD ni en otro visor de CAD.
* **Unidades.** Metros (`$INSUNITS` = 6). `ALTURA` es la cota z del punto en las unidades del dibujo.
* **Altura de los ambientes.** No se dibuja: queda pendiente (spec §6.6.1) y se carga al importar. Es 2,500 m
  en todos los ambientes (memoria `of001.md`).
* **Regenerar.** `uv run python scripts/dibujar_of001_dxf.py` (necesita `uv sync --extra planos`).
  Escribe con metadatos fijos, así que el archivo es reproducible.
