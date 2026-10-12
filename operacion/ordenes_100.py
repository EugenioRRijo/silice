"""Órdenes de la 1.0.0 de `python -m operacion` (spec S5 §5.4, §6.5 y §8.2).

Aquí viven `arrancar`, `parar`, `demostracion`, `red-local` y `diagnostico-similitud`. Las
órdenes de la clave del proyecto y `verificar-instalador` (Tarea 3, que genera Eugenio) se agregan a
`registrar` cuando esa tarea se fusione. Solo `__main__` importa este módulo: `ui` y `api` no
(spec S5 §5.2).
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from operacion import base_datos, config, lanzador, red


def _arrancar(argumentos: argparse.Namespace) -> int:
    return lanzador.arrancar(sin_navegador=argumentos.sin_navegador)


def _parar(_argumentos: argparse.Namespace) -> int:
    return lanzador.parar()


def _demostracion(_argumentos: argparse.Namespace) -> int:
    ruta = base_datos.resolver_caso("demostracion")
    base_datos.preparar_base(ruta)
    from scripts.seed_demo import main as sembrar  # diferido: scripts/ viaja solo por el manifiesto

    return int(sembrar(["--db", str(ruta)]))


def _estado_red() -> int:
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    if ajustes.red_local:
        print(f"Red local: encendida en http://{ajustes.direccion}:{ajustes.puerto}")
    else:
        print(f"Red local: apagada (solo http://127.0.0.1:{ajustes.puerto})")
    print(f"API: {'activa' if ajustes.api_activa else 'apagada'} (puerto {ajustes.puerto_api})")
    return 0


def _elegir_interfaz(interfaces: list[red.Interfaz], ip: str | None) -> red.Interfaz | None:
    if ip is not None:
        return next((i for i in interfaces if i.ip == ip), red.Interfaz("(indicada)", ip))
    for numero, interfaz in enumerate(interfaces, start=1):
        print(f"  {numero}. {interfaz.nombre}  {interfaz.ip}")
    respuesta = input("Número de la interfaz de su red de confianza: ").strip()
    if respuesta.isdigit() and 1 <= int(respuesta) <= len(interfaces):
        return interfaces[int(respuesta) - 1]
    return None


def _red_local(argumentos: argparse.Namespace) -> int:
    ruta = config.ruta_ajustes()
    if argumentos.accion == "estado":
        return _estado_red()
    if argumentos.accion == "desactivar":
        resultado = red.desactivar(ruta_ajustes=ruta)
        print(resultado.mensaje, file=sys.stdout if resultado.ok else sys.stderr)
        return 0 if resultado.ok else 1
    interfaces = red.interfaces_privadas()
    if not interfaces:
        print("Este equipo no tiene ninguna interfaz con dirección privada.", file=sys.stderr)
        return 1
    if not red.es_administrador() and not argumentos.elevado:
        extra = ["--ip", argumentos.ip] if argumentos.ip else []
        return 0 if red.relanzar_elevado(["red-local", "activar", "--elevado", *extra]) else 1
    elegida = _elegir_interfaz(interfaces, argumentos.ip)
    if elegida is None:
        print("No se eligió ninguna interfaz.", file=sys.stderr)
        return 1
    print(red.AVISO_SIN_CIFRAR)
    if (
        not argumentos.si
        and input("¿Activar la red local en esa IP? (s/n): ").strip().lower() != "s"
    ):
        return 1
    ajustes = config.cargar_ajustes(ruta)
    puertos = [ajustes.puerto] + ([ajustes.puerto_api] if ajustes.api_activa else [])
    resultado = red.activar(
        elegida.ip,
        programa=Path(sys.executable),
        puertos=puertos,
        ruta_ajustes=ruta,
        interfaces=interfaces,
    )
    print(resultado.mensaje, file=sys.stdout if resultado.ok else sys.stderr)
    if argumentos.elevado:
        input("Pulse Entrar para cerrar esta ventana.")
    return 0 if resultado.ok else 1


def _diagnostico_similitud(_argumentos: argparse.Namespace) -> int:
    os.environ.update(lanzador.variables_de_similitud())
    import ml.normalization as normalizacion

    propuesta = normalizacion.proponedor({"EXC-1": "Excavación manual de zanja"})("excavar zanja")
    if propuesta.falla is not None:
        print(f"La función de similitud no está disponible: {propuesta.falla}", file=sys.stderr)
        return 1
    print("Similitud de partidas: el modelo cargó sin red.")
    return 0


def registrar(
    ordenes: argparse._SubParsersAction,  # type: ignore[type-arg]
    tabla: dict[str, Callable[[argparse.Namespace], int]],
) -> None:
    """Agrega los parsers y los manejadores de la 1.0.0 a `python -m operacion`."""
    arrancar = ordenes.add_parser("arrancar", help="prepara las bases y abre Sílice")
    arrancar.add_argument("--sin-navegador", action="store_true")
    ordenes.add_parser("parar", help="detiene la instancia en marcha")
    ordenes.add_parser("demostracion", help="crea el caso de demostración (datos construidos)")
    local = ordenes.add_parser("red-local", help="activa, apaga o describe la red local")
    acciones = local.add_subparsers(dest="accion", required=True)
    activar = acciones.add_parser("activar", help="elegir una interfaz y abrir el cortafuegos")
    activar.add_argument("--ip")
    activar.add_argument("--si", action="store_true", help="no pedir confirmación")
    activar.add_argument("--elevado", action="store_true", help=argparse.SUPPRESS)
    acciones.add_parser("desactivar")
    acciones.add_parser("estado")
    ordenes.add_parser("diagnostico-similitud", help="carga el modelo de similitud sin red")
    tabla.update(
        {
            "arrancar": _arrancar,
            "parar": _parar,
            "demostracion": _demostracion,
            "red-local": _red_local,
            "diagnostico-similitud": _diagnostico_similitud,
        }
    )
