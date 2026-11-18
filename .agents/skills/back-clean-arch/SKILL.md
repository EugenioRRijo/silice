---
name: back-clean-arch
description: >-
  Arquitectura de Backend FastAPI y Bounded Contexts en Sílice: principios SOLID, DRY,
  capa de aplicación (aplicacion/) con rutas delgadas, un solo proceso Uvicorn en el bucle
  local y preservación estricta de la inviolabilidad de core/.
---

# Skill: Backend Clean Architecture & Bounded Contexts

> **Vigente al 2026-11-17.** Un solo proceso Uvicorn (`api.main:app`) sirve la API y la interfaz React en `/app/`.
> La ventana de escritorio es `operacion/ventana.py` (pywebview con WebView2, extra `escritorio`). No existen Tauri,
> Named Pipes, `desktop/`, `ui/` ni Streamlit (retirados el 2026-10-21). Estado del proyecto:
> [docs/ESTADO.md](../../../docs/ESTADO.md).

Esta guía establece las directrices para el desarrollo del backend en Python dentro de la plataforma Sílice.

---

## 1. La Regla Inviolable del Núcleo (`core/`)

> [!CAUTION]
> **El directorio `core/` es el corazón matemático de la tesis y no cambia sin expediente y aval del tutor.**
> Ninguna nueva funcionalidad (ni producción de canteras, ni pantallas, ni conectores) modifica código dentro de
> `core/`. `git diff origin/main -- core/` debe ser vacío y `scripts/guardia_nucleo.py` lo vigila en la CI.

* Para agregar nuevas capacidades, se crean módulos en capas periféricas:
  * `aplicacion/` $\rightarrow$ La lógica de negocio: casos de uso, consultas y tablas `tablas_*.py` (registradas en
    `migraciones/metadatos.py`). Recibió lo que vivía en `ui/`.
  * `produccion/` $\rightarrow$ Bounded Context de la arenera (inventario, báscula, costo por tonelada).
  * `adapters/` $\rightarrow$ Lectura y escritura de formatos (Excel de la empresa, IFC, BCV, báscula).
  * `api/rutas/` $\rightarrow$ Controladores REST **delgados**: validan el esquema, llaman a `aplicacion/` y traducen
    errores a códigos HTTP.
  * `operacion/` $\rightarrow$ Arranque y entorno: `lanzador.py`, `ventana.py`, `primer_arranque.py`, `registro.py`,
    `eventos_perdidos.py`, `base_datos.py`.

---

## 2. Bounded Contexts y Principios SOLID

```
+--------------------------------------------------------------+
|              API (FastAPI, routers delgados en api/rutas/)   |
+------------------------------+-------------------------------+
                               |
                               v
+--------------------------------------------------------------+
|        Capa de aplicación (aplicacion/): casos de uso,       |
|        consultas a la base, tablas tablas_*.py               |
+---------------+------------------------------+---------------+
                |                              |
                v                              v
+-------------------------------+  +---------------------------+
|   Bounded Context Producción  |  |   Bounded Context Core    |
|         (produccion/)         |  |          (core/)          |
| - Inventario y báscula        |  | - Cálculo Puro de APUs    |
| - Costo por tonelada          |  | - Reglas de Auditoría     |
| - Recetas de planta           |  | - Modelos Matemáticos     |
+-------------------------------+  +---------------------------+
```

1. **Single Responsibility (SRP):** Un servicio de producción solo calcula m³ y costos de cantera; no audita partidas. El auditor solo evalúa discrepancias normativas; no sabe cómo funciona una chancadora.
2. **Open/Closed (OCP):** Producción y núcleo no se conocen: `produccion/` solo importa `core.contracts`
   (`tests/unit/test_arquitectura.py`, `test_produccion_respeta_su_regla`). El paso del costo propio a la lista de
   precios del caso lo hace `aplicacion/costo_propio.py` con la aritmética de `produccion/costo.py`.
3. **Dependency Inversion (DIP):** Las rutas de API dependen de funciones de `aplicacion/`, no de SQLite: ninguna
   ruta escribe `select()` (hoy quedan 9 archivos de `api/rutas/` con `select()` directo; no se suma ninguno).

### 2.1. DRY: una sola función por regla

* Antes de escribir una función, búscala: `git grep -n "def <nombre>"` y por lo que hace.
* Deuda conocida que no se repite: `decimal_desde_texto` existe dos veces (`api/esquemas.py`,
  `aplicacion/composicion.py`); formateadores de montos privados en rutas, cuando la presentación es
  `core/verification/texto.py` `formatear_decimal`.
* Números: cálculo con 28 dígitos y `ROUND_HALF_EVEN`; presentación a dos decimales con `ROUND_HALF_UP` (decisión de
  Eugenio del 2026-11-17, pendiente de ratificar por el tutor). Coma decimal y punto de miles en lo que ve el usuario.

---

## 3. Transporte Local Seguro (RNF-08)

* **Un solo backend:** el FastAPI de `api/`, con su protección vigente (`api/proteccion.py`: `TrustedHost`, filtro de
  red y tope de 20 MiB).
* **Acceso por ruta:** cada ruta declara `exigir_clave_o_sesion(<accion>)` (`api/sesion_web.py`) o un atajo de
  `api/acceso.py` (`LEER`, `EDITAR`, `REVISAR`, `CAMBIAR_CASO`, `CUALQUIER_ROL`): acepta la clave `X-Silice-Clave`
  de las integraciones o la cookie de sesión del navegador. El `CON_CLAVE` por router se retiró
  (`api/main.py:124-126`).
* **Transporte:** bucle local `127.0.0.1` en el puerto de la configuración (`operacion/config.py`,
  `PUERTO_POR_DEFECTO`); la red local solo si se activa explícitamente. `operacion/lanzador.py` arranca Uvicorn y
  espera `GET /salud`; `operacion/ventana.py` abre la interfaz en una ventana propia sin puente a Python ni puerto de
  depuración, y si no puede, el lanzador abre el navegador.
* **Instalador:** `instalador/silice.iss` (Inno Setup), `instalador/construir.py` y la prueba de humo
  `instalador/humo.ps1`.
