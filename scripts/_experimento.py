"""Lo comun de los scripts del experimento del asistente (S4 §9, §10.2): contexto y proveedor real.

`contexto_del_experimento()` arma el banco, las composiciones y el catalogo; `proveedor_real()`
construye el proveedor con la clave del almacen de credenciales (nunca de un argumento ni de una
variable de entorno). Solo lo usan `evaluar_asistente.py` y `prueba_real_asistente.py`.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def contexto_del_experimento():
    from asistente.experimento.banco import cargar_banco, referencia_de
    from tests.fixtures import caso_of001, caso_ti001
    from tests.fixtures.asistente_banco import catalogo_del_experimento, codigos_y_unidades

    composiciones = {**caso_of001.COMPOSICIONES, **caso_ti001.COMPOSICIONES}
    return (
        cargar_banco(),
        composiciones,
        catalogo_del_experimento(),
        codigos_y_unidades(),
        referencia_de,
    )


def proveedor_real(nombre: str, protocolo: Mapping[str, object], empresa: str):
    if nombre == "claude":
        import getpass

        from asistente.clave import ClaveDeIA, almacen_del_sistema, es_bucle_local
        from asistente.proveedores.claude import ProveedorClaude
        from operacion.config import carpeta_datos
        from seguridad import secretos

        ruta = carpeta_datos() / "ia_clave.cifrada"
        clave = ClaveDeIA(
            almacen=almacen_del_sistema(),
            secretos=secretos,
            ruta_respaldo=ruta,
            es_local=es_bucle_local,
        )
        contrasena = getpass.getpass("Contrasena de la clave de IA: ") if ruta.exists() else None
        clave.activar(empresa, contrasena)
        # el respaldo del servidor se DESACTIVA en el experimento: un rechazo se cuenta como tal
        return ProveedorClaude(
            clave.vigente,
            modelo=str(protocolo["modelo_claude"]),
            esfuerzo=str(protocolo["esfuerzo"]),
            con_respaldo=False,
        )
    from asistente.proveedores.ollama_local import ProveedorOllama, version_a_tupla

    configuracion = json.loads((RAIZ / "asistente" / "config_ia.json").read_text(encoding="utf-8"))
    return ProveedorOllama(
        str(protocolo["modelo_local"]),
        version_minima=version_a_tupla(configuracion["version_minima_ollama"]),
        estructurado=bool(configuracion.get("estructurado", False)),
    )
