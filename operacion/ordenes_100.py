"""Órdenes de la 1.0.0 de `python -m operacion` (spec S5 §5.4, §6.5, §8.2 y §10.4)."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Callable
from pathlib import Path

from cryptography.exceptions import InvalidTag

from operacion import base_datos, config, firma_sumas, lanzador, primer_arranque, red
from seguridad import cuentas


def _arrancar(argumentos: argparse.Namespace) -> int:
    return lanzador.arrancar(sin_navegador=argumentos.sin_navegador)


def _parar(_argumentos: argparse.Namespace) -> int:
    return lanzador.parar()


def _demostracion(_argumentos: argparse.Namespace) -> int:
    ruta = base_datos.resolver_caso("demostracion")
    base_datos.preparar_base(ruta)
    from scripts.seed_demo import main as sembrar  # diferido: scripts/ viaja solo por el manifiesto

    return int(sembrar(["--db", str(ruta)]))


def _restablecer_administrador(_argumentos: argparse.Namespace) -> int:
    """Devuelve el acceso de un administrador con acceso al equipo (S3 §5.4; BCP-1): un código de
    un solo uso que caduca a las 24 horas y cierra las sesiones de los administradores."""
    codigo, archivo = primer_arranque.restablecer_administrador()
    horas = int(cuentas.CADUCIDAD_RESTABLECIMIENTO.total_seconds() // 3600)
    print("Código de restablecimiento nuevo (de un solo uso):")
    print(f"  {cuentas.formato_codigo(codigo)}")
    print(f"También está en {archivo}. Sirve {horas} horas.")
    print("Las sesiones de los administradores quedaron cerradas.")
    print("Abra Sílice y escríbalo en «Perdí el acceso de administrador».")
    return 0


def _estado_red() -> int:
    ajustes = config.cargar_ajustes(config.ruta_ajustes())
    if ajustes.red_local:
        print(f"Red local: encendida en http://{ajustes.direccion}:{ajustes.puerto}/app/")
    else:
        print(f"Red local: apagada (solo http://127.0.0.1:{ajustes.puerto}/app/)")
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
    puertos = [ajustes.puerto]  # un solo proceso, un solo puerto
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


def _verificar_programa(_argumentos: argparse.Namespace) -> int:
    from operacion import programa

    try:
        diferencias = programa.verificar(config.RAIZ.parent)
    except FileNotFoundError:
        print("Esto no es una instalación de Sílice (falta manifiesto.json).", file=sys.stderr)
        return 1
    if diferencias:
        print("\n".join(diferencias), file=sys.stderr)
        return 1
    print("El programa coincide con su manifiesto.")
    return 0


def _eventos(argumentos: argparse.Namespace) -> int:
    from operacion import eventos_perdidos

    if argumentos.accion == "pendientes":
        for archivo in eventos_perdidos.pendientes():
            print(archivo.name)
        return 0
    eventos_perdidos.marcar_revisado(Path(argumentos.archivo), por="administrador")
    print(f"Revisado: {argumentos.archivo}")
    return 0


def _generar_clave(argumentos: argparse.Namespace) -> int:
    salida = Path(argumentos.salida).resolve()
    if salida.is_relative_to(config.RAIZ.resolve()):
        print("La clave privada no puede vivir dentro del repositorio.", file=sys.stderr)
        return 1
    if "onedrive" in str(salida).lower():
        print(
            "La clave privada no puede vivir en una carpeta de OneDrive (se sincroniza).",
            file=sys.stderr,
        )
        return 1
    if (salida / "clave_proyecto.enc").exists():
        print(f"Ya hay una clave en {salida}: no se pisa.", file=sys.stderr)
        return 1
    contrasena = getpass.getpass("Contraseña de la clave del proyecto (mínimo 12 caracteres): ")
    if contrasena != getpass.getpass("Repítala: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1
    privada = firma_sumas.generar_par()
    try:
        firma_sumas.guardar_privada(privada, contrasena, salida / "clave_proyecto.enc")
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    publica = firma_sumas.bytes_publicos(privada)
    (salida / "clave_proyecto.pub").write_text(publica.hex() + "\n", encoding="utf-8")
    print(f"Clave pública: {publica.hex()}")
    print(f"Huella SHA-256: {firma_sumas.huella(publica)}")
    print(
        f"Copie {salida / 'clave_proyecto.pub'} a operacion/clave_proyecto.pub y versione SOLO ese "
        f"archivo. Guarde {salida / 'clave_proyecto.enc'} y su contraseña en dos lugares fuera del "
        "repositorio."
    )
    return 0


def _firmar_sumas(argumentos: argparse.Namespace) -> int:
    sumas = Path(argumentos.sumas)
    clave = Path(argumentos.clave)
    clave = clave / "clave_proyecto.enc" if clave.is_dir() else clave
    try:
        privada = firma_sumas.cargar_privada(
            clave, getpass.getpass("Contraseña de la clave del proyecto: ")
        )
    except InvalidTag:
        print("Contraseña incorrecta (o la clave no es la que dice ser).", file=sys.stderr)
        return 1
    try:
        publica_del_programa = firma_sumas.leer_publica()
    except (FileNotFoundError, ValueError) as error:
        print(f"No hay clave del proyecto en este programa: {error}", file=sys.stderr)
        return 1
    if firma_sumas.bytes_publicos(privada) != publica_del_programa:
        print(
            "Esa clave no es la clave del proyecto (operacion/clave_proyecto.pub): no se firma "
            "nada.",
            file=sys.stderr,
        )
        return 1
    datos = sumas.read_bytes()
    firma = firma_sumas.firmar(datos, privada)
    assert firma_sumas.verificar(datos, firma, publica_del_programa)
    destino = sumas.with_name(sumas.name + ".ed25519")
    destino.write_bytes(firma)
    print(f"Firmado: {destino}")
    return 0


def _verificar_instalador(argumentos: argparse.Namespace) -> int:
    try:
        publica = (
            bytes.fromhex(argumentos.publica) if argumentos.publica else firma_sumas.leer_publica()
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"No hay clave del proyecto para comprobar: {error}", file=sys.stderr)
        return 1
    ok, mensaje = firma_sumas.verificar_instalador(
        Path(argumentos.exe),
        Path(argumentos.sumas).read_bytes(),
        Path(argumentos.firma).read_bytes(),
        publica,
    )
    print(mensaje, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def _huella(_argumentos: argparse.Namespace) -> int:
    publica = firma_sumas.leer_publica()
    print(firma_sumas.huella(publica))
    print(firma_sumas.huella_agrupada(publica))
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
    ordenes.add_parser(
        "restablecer-administrador",
        help="emite un código de un solo uso para recuperar el acceso de administrador",
    )
    local = ordenes.add_parser("red-local", help="activa, apaga o describe la red local")
    acciones = local.add_subparsers(dest="accion", required=True)
    activar = acciones.add_parser("activar", help="elegir una interfaz y abrir el cortafuegos")
    activar.add_argument("--ip")
    activar.add_argument("--si", action="store_true", help="no pedir confirmación")
    activar.add_argument("--elevado", action="store_true", help=argparse.SUPPRESS)
    acciones.add_parser("desactivar")
    acciones.add_parser("estado")
    ordenes.add_parser("verificar-programa", help="compara {app} con manifiesto.json")
    ordenes.add_parser("diagnostico-similitud", help="carga el modelo de similitud sin red")
    eventos = ordenes.add_parser("eventos", help="eventos de seguridad perdidos tras restaurar")
    sub = eventos.add_subparsers(dest="accion", required=True)
    sub.add_parser("pendientes")
    sub.add_parser("revisar").add_argument("archivo")
    generar = ordenes.add_parser(
        "generar-clave-proyecto", help="genera el par Ed25519 del proyecto"
    )
    generar.add_argument(
        "--salida", required=True, help="carpeta FUERA del repositorio y de OneDrive"
    )
    firmar = ordenes.add_parser("firmar-sumas", help="firma SHA256SUMS con la clave del proyecto")
    firmar.add_argument("sumas")
    firmar.add_argument("--clave", required=True, help="clave_proyecto.enc o su carpeta")
    verificar = ordenes.add_parser("verificar-instalador", help="huella y firma de un instalador")
    for nombre in ("exe", "sumas", "firma"):
        verificar.add_argument(nombre)
    verificar.add_argument(
        "--publica", help="clave pública en hexadecimal (por defecto, la del programa)"
    )
    ordenes.add_parser(
        "huella-clave-proyecto", help="huella SHA-256 de la clave pública del proyecto"
    )
    tabla.update(
        {
            "arrancar": _arrancar,
            "parar": _parar,
            "demostracion": _demostracion,
            "restablecer-administrador": _restablecer_administrador,
            "red-local": _red_local,
            "diagnostico-similitud": _diagnostico_similitud,
            "verificar-programa": _verificar_programa,
            "eventos": _eventos,
            "generar-clave-proyecto": _generar_clave,
            "firmar-sumas": _firmar_sumas,
            "verificar-instalador": _verificar_instalador,
            "huella-clave-proyecto": _huella,
        }
    )
