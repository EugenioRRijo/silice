---
name: pruebas-cobertura
description: >-
  Rigor de pruebas en Sílice: pytest con -W error, cero pruebas omitidas, cobertura medida
  como la mide la CI (core/, adapters/espacio/, seguridad/ y paquete/ >= 80 %), bases de
  prueba creadas por Alembic en tmp_path y Vitest en frontend-desktop/.
---

# Skill: Rigor de Pruebas y Cobertura (RNF-06)

> **Vigente al 2026-11-17.** Los umbrales y comandos de abajo son los de `.github/workflows/ci.yml`; si cambian allí,
> manda la CI. Estado del proyecto: [docs/ESTADO.md](../../../docs/ESTADO.md).

Esta guía define el protocolo estricto de pruebas automatizadas que debe cumplir todo código nuevo en Sílice.

---

## 1. Filosofía de Pruebas y Comandos Obligatorios

1. **Advertencias como Errores (`-W error`):** Ninguna prueba puede emitir warnings (deprecation, syntax, runtime). Todo warning debe resolverse en código, no filtrarse.
2. **Cero Pruebas Omitidas:** prohibidos `skip`, `skipif`, `xfail` e `importorskip`, sin excepciones. La CI lo comprueba
   con `scripts/verificar_omitidas.py` sobre el JUnit de la corrida.
3. **Comandos de comprobación (AGENTS.md):**
   ```powershell
   uv run pytest -W error -q -n auto --dist loadfile   # suite de Python, en paralelo (regla del 2026-11-24)
   uv run ruff check .                       # estilo
   uv run python scripts/meta_datos.py       # naturaleza de los datos (D1-D4)
   cd frontend-desktop; npm run lint; npx vitest run --maxWorkers=3
   ```
   Lo que corre la CI, por si hay que reproducirla:
   ```bash
   uv run pytest -W error -p no:cacheprovider --junitxml=reporte-pruebas.xml \
     --cov=core --cov=ml --cov=api --cov=adapters --cov=seguridad --cov=paquete --cov=asistente --cov=operacion
   uv run python scripts/verificar_omitidas.py reporte-pruebas.xml
   ```

---

## 2. Cobertura de Código (umbrales reales de la CI)

La CI mide con `--cov` los paquetes de arriba, pero **solo rompe** en tres umbrales:
* `core/`: $\ge 80\%$ (RNF-06, garantía de la tesis).
* `adapters/espacio/`: $\ge 80\%$ (meta S10).
* `seguridad/` y `paquete/`: $\ge 80\%$ (meta S3-M4).

```bash
uv run coverage report --include="core/*" --fail-under=80
uv run coverage report --include="adapters/espacio/*" --fail-under=80
uv run coverage report --include="seguridad/*,paquete/*" --fail-under=80
```

`produccion/`, `aplicacion/` y `api/` no tienen umbral propio en la CI: no se afirma una cifra de cobertura para ellos
sin medirla.

---

## 3. Reglas para Fixtures y Aislamiento

* **Uso exclusivo de `tmp_path`:** Nunca crear archivos temporales en carpetas fijas como `data/` o `C:\tmp`. Usar siempre el fixture `tmp_path: Path` de pytest.
* **Bases de prueba por Alembic, no con `create_all`:** una base se crea con el mismo camino que el programa, así la
  prueba también ejercita la migración. Ejemplo: `tests/fixtures/carpetas_trabajo.py`.
  ```python
  from operacion.base_datos import Destino, preparar_base

  @pytest.fixture
  def instalacion_temporal(tmp_path: Path) -> Path:
      ruta = tmp_path / "instalacion.db"
      preparar_base(ruta, Destino.INSTALACION)
      return ruta
  ```
* **Reutiliza las fixtures de `tests/fixtures/`** antes de escribir otra (los datos de la línea base viven solo en
  `tests/fixtures/apu_linea_base.py`).
* **Red:** `tests/conftest.py` tiene la guardia única de red; ninguna prueba sale a internet (proveedores de IA
  guionados, respuestas grabadas).
* **Mocking Limpio:** Usar `monkeypatch` para sustituir llamadas externas o de red; nunca parchar métodos dentro de `core/`.
