---
name: base-datos-migraciones
description: >-
  Gestión de persistencia con SQLite y Alembic multi-caso en Sílice: aislamiento de
  casos/*.db frente a produccion.db, respaldos atómicos y protocolos de migración.
---

# Skill: Persistencia SQLite y Migraciones con Alembic

Esta guía detalla el modelo de bases de datos de Sílice y cómo añadir migraciones seguras sin riesgo de pérdida de datos.

---

## 1. Topología de Bases de Datos en Sílice

Sílice no utiliza una base de datos única monolítica; utiliza un esquema particionado multi-base en SQLite:

```
SILICE_DATOS/
├── instalacion.db         # Usuarios, licencias, eventos perdidos y configuración global
├── produccion.db          # Catálogo de maquinaria, partes diarios, desgastes y canteras
└── casos/                 # Un archivo .db independiente por cada proyecto o presupuesto
    ├── silice.db          # Caso predeterminado
    ├── puente_rio.db      # Proyecto A
    └── edificio_alfa.db   # Proyecto B
```

### Principio de Aislamiento:
* `casos/*.db` almacena partidas, APUs, cómputos métricos e informes de auditoría del proyecto.
* `produccion.db` es de ámbito empresarial compartido: contiene los activos físicos de la cantera (trituradoras, cargadores frontales) y sus costos históricos de operación.

---

## 2. Protocolo de Migraciones Seguras (Alembic)

1. **Juego de Respaldo Previo Obligatorio:**
   Antes de ejecutar cualquier migración de esquema en `base_datos.py`, el sistema ejecuta una copia snapshot atómica (`respaldo.copiar_sqlite`). Si la migración falla a mitad de camino, se restablece el archivo original de inmediato.
2. **Revisión Head y Clasificación:**
   Toda nueva base de datos nace clasificada como `"nueva"` y se lleva directamente a `head` ejecutando las revisiones en orden secuencial.
3. **Manejo de Caso por Defecto en Instalación Limpia:**
   `migrar_todo()` debe garantizar que si la carpeta `casos/` está vacía, se inicialice automáticamente `config.ruta_caso_por_defecto()` (`casos/silice.db`) junto a `instalacion.db` y `produccion.db`.
