---
name: back-clean-arch
description: >-
  Arquitectura de Backend FastAPI y Bounded Contexts en Sílice: principios SOLID, DRY,
  sidecar local desacoplado, IPC seguro sobre Named Pipes y preservación estricta de la
  inviolabilidad de core/.
---

# Skill: Backend Clean Architecture & Bounded Contexts

Esta guía establece las directrices para el desarrollo del backend en Python dentro de la plataforma Sílice.

---

## 1. La Regla Inviolable del Núcleo (`core/`)

> [!CAUTION]
> **El directorio `core/` es el corazón matemático de la tesis y es completamente INVIOLABLE.**
> Ninguna nueva funcionalidad (ni producción de canteras, ni visores de interfaz, ni conectores) puede modificar código dentro de `core/`. La verificación `git diff origin/main -- core/` debe ser siempre vacía.

* Para agregar nuevas capacidades, se crean módulos en capas periféricas:
  * `produccion/` $\rightarrow$ Para el Bounded Context de canteras y costos de extracción.
  * `adapters/` $\rightarrow$ Para parsers de entrada/salida (Excel, IFC, BCV, báscula).
  * `api/rutas/` $\rightarrow$ Para controladores REST que exponen servicios hacia la UI.

---

## 2. Bounded Contexts y Principios SOLID

```
+--------------------------------------------------------------+
|                        API / UI Gateway                      |
|                  (FastAPI Routers en api/rutas/)             |
+---------------+------------------------------+---------------+
                |                              |
                v                              v
+-------------------------------+  +---------------------------+
|   Bounded Context Producción   |  |   Bounded Context Core    |
|         (produccion/)         |  |          (core/)          |
| - Costo Horario Maquinaria    |  | - Cálculo Puro de APUs    |
| - Balance de Masa Trituración |  | - Reglas de Auditoría     |
| - Conectores de Báscula       |  | - Modelos Matemáticos     |
+---------------+---------------+  +-------------+-------------+
                |                                |
                +------------ DTOs --------------+
                      (Contratos Inmutables)
```

1. **Single Responsibility (SRP):** Un servicio de producción solo calcula m³ y costos de cantera; no audita partidas. El auditor solo evalúa discrepancias normativas; no sabe cómo funciona una chancadora.
2. **Open/Closed (OCP):** El core emite eventos y recibe DTOs (`InsumoCanteraDTO`). Nuevos tipos de insumos se agregan implementando el contrato sin modificar el motor de resolución de APUs.
3. **Dependency Inversion (DIP):** Las rutas de API dependen de abstracciones de servicios, no de implementaciones concretas de SQLite.

---

## 3. Transporte IPC Seguro (Windows Named Pipes & Localhost)

Para cumplir con **RNF-08** (aislamiento total y cero exposición indebida de red):
* El backend se levanta como proceso sidecar local administrado por Tauri.
* Para evitar falsos positivos de antivirus que bloquean puertos TCP `localhost`, la comunicación primaria utiliza **Named Pipes de Windows**:
  ```text
  \\.\pipe\silice-ipc-local
  ```
* En modo desarrollo o fallback, se habilita Uvicorn en `127.0.0.1:8000` con bandera `--no-access-log` y vinculado exclusivamente al loopback local.
