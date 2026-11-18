---
name: base-datos-migraciones
description: >-
  Gestión de persistencia con SQLite y Alembic en Sílice: instalacion.db (con las tablas
  de producción prod_*) y un casos/*.db por proyecto, respaldos atómicos y protocolos de migración.
---

# Skill: Persistencia SQLite y Migraciones con Alembic

> **Vigente al 2026-11-17.** Hay dos destinos de migración, `instalacion.db` y cada `casos/*.db`. No existe
> `produccion.db`: las tablas de producción (`prod_*`) viven en `instalacion.db` (decisión S4: la producción es de la
> empresa, no de un caso). Estado del proyecto: [docs/ESTADO.md](../../../docs/ESTADO.md).

Esta guía detalla el modelo de bases de datos de Sílice y cómo añadir migraciones seguras sin riesgo de pérdida de datos.

---

## 1. Topología de Bases de Datos en Sílice

Sílice no utiliza una base de datos única monolítica; usa SQLite en dos destinos (`operacion/config.py`):

```
SILICE_DATOS/              # en desarrollo, data/ del repositorio (en .gitignore)
├── instalacion.db         # Seguridad, auditorías de libros, módulos, índice de aprobaciones y producción (prod_*)
├── casos/                 # Un archivo .db independiente por cada proyecto o presupuesto
│   └── silice.db          # Caso predeterminado (config.ruta_caso_por_defecto())
├── paquetes/
└── respaldos/
```

### Principio de Aislamiento:
* `casos/*.db` almacena partidas, APU, cómputos, versiones e informes de auditoría del proyecto.
* `instalacion.db` es de ámbito empresarial compartido: cuentas, claves, módulos y los activos y costos de la arenera.

### Revisiones vigentes de `instalacion.db` (`migraciones/instalacion/versions/`)

| Revisión | Qué trae |
|---|---|
| `ins_0001_seguridad.py` | Tablas de `seguridad` (cuentas, claves) |
| `ins_0002_produccion.py` | Tablas de la arenera (`prod_*`) |
| `ins_0003_auditoria_libro.py` | Auditorías de «Libro de la empresa» |
| `ins_0004_mod_eleccion.py` | Elección y preferencias de módulos por cuenta |
| `ins_0005_mp_indice_aprobacion.py` | `mp_indice_aprobacion` |
| `ins_0006_prod_costo.py` | `prod_costo` |
| `ins_0007_prod_receta.py` | `prod_receta`, `prod_receta_componente` y el movimiento `consumo` |
| `ins_0008_prod_calculo.py` | `prod_calculo` |
| `ins_0009_prod_publicacion.py` | `prod_publicacion` |
| `ins_0010_modulo.py` | `modulo_cambio` |
| `ins_0011_receta_ligante.py` | `prod_receta_componente.es_ligante` (cabeza actual) |

Las del caso viven en `migraciones/caso/versions/` (`caso_0001` a `caso_0022` hoy). Antes de numerar una nueva, mira
la cabeza con `alembic heads` o en la carpeta: este cuadro puede quedarse atrás.

---

## 2. Protocolo de Migraciones Seguras (Alembic)

1. **Juego de Respaldo Previo Obligatorio:**
   Antes de migrar, `operacion/base_datos.py` hace una copia atómica (`operacion/respaldo.py`, `copiar_sqlite`). Si
   la migración falla a mitad de camino, se restablece el archivo original de inmediato.
2. **Revisión Head y Clasificación:**
   Toda base nueva nace clasificada como `"nueva"` y se lleva directamente a `head`. El único camino para abrir una
   base es `preparar_base(ruta, destino)`.
3. **Instalación limpia:** `migrar_todo()` lleva a `head` la instalación y todos los casos de la carpeta con un solo
   juego de respaldo.
4. **Tablas nuevas:** el modelo vive en su paquete (`aplicacion/tablas_*.py`, `produccion/modelo.py`…), su
   `METADATA_*` se registra en `migraciones/metadatos.py` y la revisión las crea. `tests/integration/test_migraciones.py`
   compara el esquema migrado con esas metadatas, y cada revisión tiene su `tests/integration/test_migracion_<tema>.py`
   con subida desde la revisión anterior con datos.
5. **DRY:** antes de crear una tabla o una consulta, busca si ya existe (`git grep -n "__tablename__"`). Las
   consultas van en `aplicacion/`, no en `api/rutas/`.
