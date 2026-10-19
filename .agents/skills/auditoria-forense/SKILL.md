---
name: auditoria-forense
description: >-
  Motor de Auditoría Forense y Parches Delta: detección de sobreprecios, análisis de
  fórmulas rotas, popovers contextuales de 1 clic y preservación probatoria del archivo original.
---

# Skill: Auditoría Forense de Presupuestos y Capa Delta

Esta guía especifica las reglas de auditoría y el mecanismo de parches no destructivos en Sílice.

---

## 1. Principio Probatorio y Preservación del Archivo Fuente

> [!IMPORTANT]
> En auditoría forense, el archivo entregado por el contratista o ente emisor constituye una **prueba documental inalterable**. Bajo ninguna circunstancia el sistema debe sobrescribir o modificar el archivo `.xlsx` o `.pdf` original.

### El Mecanismo de Capa Delta (Delta Patch):
* El archivo original se almacena con su huella `SHA256` inmutable.
* Cada corrección efectuada en la UI (ej. *"Adoptar costo real de cantera \$18.50/m³"*) se almacena como una entrada de parche:
  ```json
  {
    "id": "patch-550e8400",
    "archivo_sha256": "3a7b...",
    "coordenada": { "hoja": "Presupuesto", "fila": 12, "columna": 5 },
    "valor_anterior": 45.00,
    "valor_nuevo": 30.50,
    "motivo": "Ajuste por costo auditado en Cantera Las Mercedes + Flete 34km",
    "auditor": "Ing. Eugenio Rijo",
    "fecha": "2026-10-18T14:30:00Z"
  }
  ```
* Al exportar el dictamen final, Sílice genera:
  1. El informe forense en PDF con la trazabilidad completa de cambios.
  2. El nuevo presupuesto corregido derivado (`presupuesto_auditado.xlsx`).

---

## 2. Popovers de Micro-Auditoría Contextual (1 Clic)

Al hacer clic sobre una celda resaltada en el visor:
1. **Tarjeta de Diagnóstico:** Explica claramente el hallazgo técnico con desglose de costos.
2. **Acciones Rápidas Disponibles:**
   - `[Adoptar Costo de Cantera]`: Sustituye el precio unitario del árido por el costo derivado de la planta.
   - `[Ajustar a Tabulador CIV/BCV]`: Ajusta la tarifa al tope legal oficial.
   - `[Justificar Hallazgo]`: Permite ingresar un descargo técnico que valida la excepción sin romper el presupuesto.
