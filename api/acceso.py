"""Acceso por ruta, no por router (RM-3, plan de la sesión 2b).

Cada ruta acepta la clave de API (`X-Silice-Clave`: las integraciones, como antes con `CON_CLAVE`)
o la cookie de sesión del navegador con el rol de la acción que exige la página Streamlit que hace
lo mismo (`ui_sesion.exigir(...)` en `ui/paginas/*.py`). Un router mezcla lectura y escritura,
así que la acción va en el decorador de cada ruta (`dependencies=LEER`, ...).

Ruta → acción (y la página Streamlit que lo justifica):

- `LEER_PROYECTO` (arma y revisa):
  - `GET /partidas`, `GET /insumos`: Catálogo.
  - `GET /listas-precios`, `GET /cambios-precio`: Histórico de precios.
  - `GET /presupuestos`, `GET /presupuestos/{codigo}`, `.../informe`, `.../excel`: Tablero, y el
    informe y el Excel de una versión.
  - `GET /ejecuciones`, `GET /partidas/{codigo}/rendimientos`: consulta de rendimientos.
  - `POST /v1/libros/auditoria`, `/devolucion`, `/pdf`, `/replica`: Libro de la empresa (RS2-5).
  - `GET /v1/proyectos`: la barra superior y el Tablero.
- `EDITAR_HOJA` (arma):
  - `POST /listas-precios`: Actualizar precios, que carga la lista con
    `crear_lista_desde_archivo` (`ui/paginas/actualizacion.py`). No es la lista de la empresa
    (Precios de la empresa, `ADMINISTRAR_PRECIOS`), que no tiene ruta todavía.
  - `POST /computos/{dominio}`, `POST /proyectos`, `POST /presupuestos`: Elaborar un presupuesto
    (y la barra, que crea proyectos).
  - `POST /presupuestos/importar`: sin página Streamlit; escribe APU y una lista vigente en el caso
    (UC-05), que es trabajo de quien arma.
  - `POST /presupuestos/{codigo}/actualizacion`: Actualizar precios.
  - `POST /presupuestos/{codigo}/escenarios`: Escenarios.
  - `POST /ejecuciones`, `POST /partidas/{codigo}/rendimientos`: Componer una partida.
- `REVISAR_PAQUETE` (revisa): `POST /v1/auditorias`, que reaudita como Revisar un paquete.
- `CAMBIAR_CASO` (arma y administrador): `POST /v1/casos/actual` («Cambiar de caso» del Inicio).
- Cualquier rol con sesión: `GET /v1/casos` (el caso abierto y la lista los ven todos).

Sin clave ni sesión: `GET /salud` y `POST /v1/sesion` (la entrada). `GET`/`DELETE /v1/sesion` y
`POST /v1/sesion/contrasena` exigen la ficha (aunque sea la de una contraseña temporal) con su
propia regla (`api.rutas.sesion`). `/app` es estático y público. Lo vigila
`tests/unit/test_api_acceso_por_ruta.py`, con su propia tabla escrita a mano.
"""

from __future__ import annotations

from fastapi import Depends

from api.sesion_web import exigir_clave_o_sesion
from seguridad.permisos import Accion

LEER = [Depends(exigir_clave_o_sesion(Accion.LEER_PROYECTO))]
EDITAR = [Depends(exigir_clave_o_sesion(Accion.EDITAR_HOJA))]
REVISAR = [Depends(exigir_clave_o_sesion(Accion.REVISAR_PAQUETE))]
CAMBIAR_CASO = [Depends(exigir_clave_o_sesion(Accion.CAMBIAR_CASO))]
CUALQUIER_ROL = [Depends(exigir_clave_o_sesion(None))]
