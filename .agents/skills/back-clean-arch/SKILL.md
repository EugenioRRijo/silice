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

## 3. Transporte Local Seguro (ruta, RT-5)

Para cumplir con **RNF-08** (aislamiento total y cero exposición indebida de red):
* **Un solo backend:** el FastAPI de `api/` (RT-1), con su protección vigente (`api/proteccion.py`: clave por ruta, `TrustedHost`, filtro de red, tope de 20 MiB).
* **Transporte primario:** bucle local `127.0.0.1` con **puerto efímero** y **clave por sesión**; la interfaz nueva se sirve desde el mismo FastAPI en `/app` (RT-2). En la sesión 5, Tauri v2 envuelve esa interfaz y arranca el Python que ya instala Inno Setup (RT-3).
* **Named Pipes de Windows** (`\\.\pipe\silice-ipc-local`) quedan como **endurecimiento posterior**: uvicorn no sirve por Named Pipes sin un transporte propio. Solo se construyen si una prueba real muestra un antivirus bloqueando el bucle local.
