---
name: pruebas-cobertura
description: >-
  Rigor de pruebas en Sílice: pytest con -W error, cobertura >= 80% (RNF-06), cero pruebas
  omitidas, fixtures reproducibles con tmp_path y validación en runners de CI.
---

# Skill: Rigor de Pruebas y Cobertura (RNF-06)

Esta guía define el protocolo estricto de pruebas automatizadas que debe cumplir todo código nuevo en Sílice.

---

## 1. Filosofía de Pruebas y Comandos Obligatorios

1. **Advertencias como Errores (`-W error`):** Ninguna prueba puede emitir warnings (deprecation, syntax, runtime). Todo warning debe resolverse en código.
2. **Cero Pruebas Omitidas:** No se permite `@pytest.mark.skip` salvo que esté justificado formalmente en bitácora por dependencia de hardware físico no presente en CI.
3. **Comando de Verificación de Suite:**
   ```bash
   uv run pytest tests/ -W error --junitxml=reporte-pruebas.xml
   uv run python scripts/verificar_omitidas.py reporte-pruebas.xml
   ```

---

## 2. Cobertura de Código ($\ge 80\%$)

La meta de calidad **RNF-06** exige cobertura estricta en las capas del sistema:
* `core/`: $\ge 80\%$ (Garantía de la tesis).
* `produccion/`: $\ge 85\%$ (Nuevas reglas de cálculo y costos).
* `seguridad/` y `paquete/`: $\ge 80\%$ (Meta S3-M4).

Comando de medición:
```bash
uv run coverage run -m pytest tests/ -W error
uv run coverage report --include="produccion/*,adapters/*" --fail-under=80
```

---

## 3. Reglas para Fixtures y Aislamiento

* **Uso exclusivo de `tmp_path`:** Nunca crear archivos temporales en carpetas fijas como `data/` o `C:\tmp`. Usar siempre el fixture `tmp_path: Path` de pytest.
* **Bases de datos SQLite en memoria o temporales:**
  ```python
  @pytest.fixture
  def sesion_produccion_temporal(tmp_path: Path):
      ruta_db = tmp_path / "produccion_test.db"
      motor = create_engine(f"sqlite:///{ruta_db.as_posix()}")
      Base.metadata.create_all(motor)
      with Session(motor) as sesion:
          yield sesion
  ```
* **Mocking Limpio:** Usar `monkeypatch` para sustituir llamadas externas o de red; nunca parchar métodos dentro de `core/`.
