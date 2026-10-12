"""Verificar un `.silice` ajeno (spec S3 §8.3, §6.5 y §13.3; maestro §4.5).

Pasos: abrir con límites -> formato -> integridad (huellas del manifiesto y `huella_anexos`) ->
autenticidad (la firma, con **la clave registrada** y nunca la que trae el paquete, y con el
prefijo de dominio) -> cadena -> anterioridad y destinatario. Cuatro estados:

* **verificado**: todo cuadra y la firma es de una empresa registrada y activa (o retirada, solo si
  el archivo se recibió antes de registrar el retiro);
* **no verificado**: sin firma, empresa no registrada, clave revocada o retirada y recibido
  después. Se audita igual; sin firma las huellas solo prueban que no se dañó por accidente;
* **alterado**: una huella, la firma o la cadena no cuadran. Se audita igual para mostrar qué
  contiene;
* **rechazado**: ZIP dañado o inseguro, fuera de límites o de un formato que no se conoce.

`verificar` no toca la base: recibe una función que busca la empresa por la huella completa de su
clave y la fecha en que se recibió el archivo.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.budget.cadena import (
    GENESIS,
    huella_de_anexos,
    huella_de_filas_de_cambios,
    huella_del_eslabon,
)
from core.budget.canonico import contar_filas
from paquete.formato import (
    ADMITIDOS,
    FORMATO_PAQUETE,
    LIMITE_FILAS,
    NOMBRE_FIRMA,
    NOMBRE_MANIFIESTO,
    OBLIGATORIOS,
    VERSION_FORMATO,
    JsonRechazado,
    PaqueteRechazado,
    abrir_zip,
    leer_json,
)
from seguridad import firma

__all__ = [
    "Anterioridad",
    "EmpresaConocida",
    "Verificacion",
    "armar_cadena_json",
    "banner",
    "evaluar_anterioridad",
    "verificar",
]

VERIFICADO, NO_VERIFICADO, ALTERADO, RECHAZADO = (
    "verificado",
    "no_verificado",
    "alterado",
    "rechazado",
)
FORMATO_CADENA = "silice-cadena"
ADMITE_ESPACIO = "anexos/espacio.json"


@dataclass(frozen=True, slots=True)
class EmpresaConocida:
    """Lo que la instalación sabe de una empresa registrada (`empresa_registrada`)."""

    empresa: str
    publica: bytes
    estado: str  # activa | retirada | revocada
    fecha_estado: datetime | None = None


BuscarEmpresa = Callable[[str], "EmpresaConocida | None"]


@dataclass(frozen=True, slots=True)
class Verificacion:
    estado: str
    motivo: str  # clave corta: ver MOTIVOS
    detalle: str  # qué archivo cambió, qué empresa dice ser...
    sha256: str
    archivos: Mapping[str, bytes] = field(default_factory=dict)
    manifiesto: Mapping[str, Any] | None = None
    cadena: Mapping[str, Any] | None = None
    empresa_declarada: str | None = None
    empresa_verificada: str | None = None
    retirada: bool = False
    avisos: tuple[str, ...] = ()

    @property
    def legible(self) -> bool:
        """Se puede reauditar: todo menos «rechazado» (en «alterado» se audita para mostrar)."""
        return self.estado != RECHAZADO and bool(self.archivos)


def _sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def _rechazo(sha: str, detalle: str) -> Verificacion:
    return Verificacion(RECHAZADO, "rechazado", detalle, sha)


# --- la cadena del paquete -------------------------------------------------------------------


def armar_cadena_json(
    eslabones: Sequence[Mapping[str, Any]], cambios: Mapping[str, Sequence[Sequence[str]]]
) -> dict[str, Any]:
    """El objeto de `cadena.json`: los eslabones hasta la versión entregada y, por código de
    versión, las filas de sus `RegistroCambio` (las mismas que entran a `huella_cambios`)."""
    return {
        "formato": FORMATO_CADENA,
        "version_formato": 1,
        "eslabones": list(eslabones),
        "cambios": {codigo: [list(f) for f in filas] for codigo, filas in cambios.items()},
    }


def _comprobar_cadena(
    cadena: Mapping[str, Any], manifiesto: Mapping[str, Any], archivos: Mapping[str, bytes]
) -> str | None:
    """Motivo si la cadena no cuadra; `None` si sí. Verifica los enlaces y que cada eslabón
    sea consistente consigo mismo y con sus cambios; del contenido de las versiones anteriores
    solo hay huellas (DA-S3-4), así que solo el último eslabón se ata al `presupuesto.json`."""
    eslabones = cadena.get("eslabones")
    if cadena.get("formato") != FORMATO_CADENA or not isinstance(eslabones, list) or not eslabones:
        return "cadena.json no tiene la forma esperada"
    anterior = GENESIS
    for e in eslabones:
        try:
            esperado = huella_del_eslabon(
                anterior=e["anterior"],
                codigo=e["codigo"],
                contenido=e["huella_contenido"],
                cambios=e["huella_cambios"],
                anexos=e["huella_anexos"],
                usuario=e["usuario"],
                fecha_hora=datetime.fromisoformat(e["fecha_hora"]),
                tipo=e["tipo"],
                version_formato=e["version_formato"],
            )
            cambios = huella_de_filas_de_cambios(cadena.get("cambios", {}).get(e["codigo"], []))
        except (KeyError, TypeError, ValueError):
            return "un eslabón de cadena.json está incompleto"
        if e["anterior"] != anterior or esperado != e["huella_eslabon"]:
            return f"el eslabón de la versión {e['codigo']} no cuadra"
        if cambios != e["huella_cambios"]:
            return f"los cambios de la versión {e['codigo']} no coinciden con su huella"
        anterior = e["huella_eslabon"]
    ultimo = eslabones[-1]
    if ultimo["huella_eslabon"] != manifiesto.get("ultima_huella_eslabon"):
        return "el último eslabón no es el que firma el manifiesto"
    if ultimo["codigo"] != manifiesto.get("codigo"):
        return "el último eslabón no es de la versión que declara el manifiesto"
    if ultimo["huella_contenido"] != _sha(archivos["presupuesto.json"]):
        return "el contenido de presupuesto.json no es el que selló el último eslabón"
    espacio = {n: archivos[n] for n in (ADMITE_ESPACIO,) if n in archivos}
    if ultimo["huella_anexos"] != huella_de_anexos(espacio):
        return "el anexo de espacio no es el que selló el último eslabón"
    return None


# --- verificar -------------------------------------------------------------------------------


def verificar(
    datos: bytes,
    *,
    buscar_empresa: BuscarEmpresa,
    recibido_en: datetime,
    mi_empresa: tuple[str | None, str | None] = (None, None),
) -> Verificacion:
    """El estado de `datos`. `mi_empresa` = (nombre, huella de clave) de la instalación que
    recibe, para avisar si el paquete se emitió para otra empresa (23g)."""
    sha = _sha(datos)
    try:
        archivos = abrir_zip(datos)
    except PaqueteRechazado as error:
        return _rechazo(sha, str(error))
    if NOMBRE_MANIFIESTO not in archivos:
        return _rechazo(sha, "El paquete no trae manifiesto.json: no se puede leer.")
    try:
        manifiesto = leer_json(archivos[NOMBRE_MANIFIESTO])
    except JsonRechazado as error:
        return _rechazo(sha, f"El manifiesto no es un JSON válido: {error}.")
    if not isinstance(manifiesto, dict) or manifiesto.get("formato") != FORMATO_PAQUETE:
        return _rechazo(sha, "El archivo no es un paquete de Silice (formato desconocido).")
    if manifiesto.get("version_formato") != VERSION_FORMATO:
        return _rechazo(
            sha,
            f"El paquete es de la versión de formato {manifiesto.get('version_formato')!r} "
            "y esta instalación solo lee la 1. Pida al emisor un paquete compatible.",
        )
    declarada = manifiesto.get("empresa")
    huella_clave = manifiesto.get("huella_clave")

    def resultado(estado: str, motivo: str, detalle: str = "", **mas) -> Verificacion:
        return Verificacion(
            estado,
            motivo,
            detalle,
            sha,
            archivos,
            manifiesto,
            mas.pop("cadena", None),
            declarada,
            mas.pop("verificada", None),
            **mas,
        )

    alterado = _integridad(manifiesto, archivos)
    if alterado is not None:
        return resultado(ALTERADO, "integridad", alterado)
    # Límites de lectura del documento (S3 §8.4): JSON estricto, 64 niveles y 200 000 filas.
    try:
        presupuesto = leer_json(archivos["presupuesto.json"])
    except JsonRechazado as error:
        return _rechazo(sha, f"presupuesto.json no es un JSON válido: {error}.")
    if isinstance(presupuesto, dict) and contar_filas(presupuesto) > LIMITE_FILAS:
        return _rechazo(
            sha, f"presupuesto.json trae más de {LIMITE_FILAS} renglones y líneas de composición."
        )
    firmado = archivos.get(NOMBRE_FIRMA)
    manifiesto_bytes = archivos[NOMBRE_MANIFIESTO]
    estado, motivo, detalle, verificada, retirada = NO_VERIFICADO, "sin_firma", "", None, False
    if firmado is not None:
        if len(firmado) != 64 or not huella_clave:
            return resultado(ALTERADO, "firma", "firma.ed25519 no es una firma válida")
        conocida = buscar_empresa(huella_clave)
        if conocida is None:
            estado, motivo = NO_VERIFICADO, "empresa_no_registrada"
        elif not firma.verificar(
            conocida.publica, firma.DOMINIO_PAQUETE, manifiesto_bytes, firmado
        ):
            return resultado(ALTERADO, "firma", "la firma no es válida con la clave registrada")
        elif conocida.estado == "revocada":
            estado, motivo = NO_VERIFICADO, "revocada"
        elif conocida.estado == "retirada":
            antes = conocida.fecha_estado is not None and recibido_en < conocida.fecha_estado
            estado, motivo = (
                (VERIFICADO, "retirada") if antes else (NO_VERIFICADO, "retirada_tarde")
            )
            verificada, retirada = (conocida.empresa if antes else None), antes
        else:
            estado, motivo, verificada = VERIFICADO, "firma_valida", conocida.empresa
    try:
        cadena = leer_json(archivos["cadena.json"])
    except JsonRechazado as error:
        return resultado(ALTERADO, "cadena", f"cadena.json no es un JSON válido: {error}")
    fallo = _comprobar_cadena(cadena, manifiesto, archivos)
    if fallo is not None:
        return resultado(ALTERADO, "cadena", fallo, cadena=cadena)
    avisos = []
    nombre_mio, huella_mia = mi_empresa
    destinatario = manifiesto.get("destinatario")
    if destinatario and destinatario not in {nombre_mio, huella_mia}:
        avisos.append(f"Este paquete se emitió para {destinatario}.")
    if retirada:
        avisos.append("La clave del emisor se retiró después de que usted recibió este paquete.")
    return resultado(
        estado,
        motivo,
        detalle,
        cadena=cadena,
        verificada=verificada,
        retirada=retirada,
        avisos=tuple(avisos),
    )


def _integridad(manifiesto: Mapping[str, Any], archivos: Mapping[str, bytes]) -> str | None:
    """Texto de lo que no cuadra, o `None`. Falta, sobra o cambió algún archivo."""
    try:
        listados = {a["nombre"]: a for a in manifiesto["archivos"]}
    except (KeyError, TypeError):
        return "el manifiesto no lista sus archivos"
    for nombre in OBLIGATORIOS:
        if nombre != NOMBRE_MANIFIESTO and nombre not in listados:
            return f"el manifiesto no lista {nombre}"
    for nombre, entrada in listados.items():
        if nombre not in ADMITIDOS or nombre in (NOMBRE_MANIFIESTO, NOMBRE_FIRMA):
            return f"el manifiesto lista un archivo que no es del formato: {nombre!r}"
        if nombre not in archivos:
            return f"falta {nombre}, que el manifiesto lista"
        if len(archivos[nombre]) != entrada.get("tamano") or _sha(archivos[nombre]) != entrada.get(
            "sha256"
        ):
            return f"{nombre} cambió después de firmarse"
    for nombre in archivos:
        if nombre not in listados and nombre not in (NOMBRE_MANIFIESTO, NOMBRE_FIRMA):
            return f"{nombre} está en el paquete y el manifiesto no lo lista"
    anexos = {n: b for n, b in archivos.items() if n.startswith("anexos/")}
    if huella_de_anexos(anexos) != manifiesto.get("huella_anexos"):
        return "los anexos no coinciden con la huella de anexos del manifiesto"
    return None


# --- anterioridad y banner -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Anterioridad:
    avisos: tuple[str, ...]
    ya_recibido: bool
    ultima_recibida: str  # «versión 004 del 2026-11-03» o «» si es la primera


def evaluar_anterioridad(
    manifiesto: Mapping[str, Any],
    cadena: Mapping[str, Any],
    huellas_de_anexos: Mapping[str, Sequence[str]],
    sha256: str,
    previos: Sequence[Mapping],
) -> Anterioridad:
    """§6.5. `previos`: lo ya recibido del mismo proyecto y emisor, del más viejo al más nuevo,
    con `huella_archivo`, `paquete_id`, `codigo`, `emitido`, `cadena` (JSON de `[[codigo,
    huella]...]`) y `huellas_anexos` (JSON `{anexo: [huella...]}`). Defensa PARCIAL: un revisor que
    nunca recibió un paquete más nuevo, otro revisor o una base restaurada no la tienen."""
    avisos: list[str] = []
    for p in previos:
        if p["huella_archivo"] == sha256 or p["paquete_id"] == manifiesto.get("paquete_id"):
            return Anterioridad(
                (f"Ya recibió este mismo paquete el {_dia(p['fecha'])}.",), True, _ultima(previos)
            )
    if not previos:
        return Anterioridad((), False, "")
    ultimo = previos[-1]
    hay = [[e["codigo"], e["huella_eslabon"]] for e in cadena["eslabones"]]
    vista = json.loads(ultimo["cadena"])
    comun = min(len(hay), len(vista))
    if hay[:comun] != vista[:comun]:
        donde = next(i for i in range(comun) if hay[i] != vista[i])
        avisos.append(
            f"Este paquete reescribe la historia: la versión {vista[donde][0]} que recibió el "
            f"{_dia(ultimo['fecha'])} tenía otra huella."
        )
    elif len(hay) <= len(vista):
        avisos.append(
            f"Este paquete es anterior a uno que ya recibió (versión {ultimo['codigo']} del "
            f"{_dia(ultimo['emitido'])})."
        )
    antes = json.loads(ultimo["huellas_anexos"])
    for anexo, huellas in sorted(antes.items()):
        faltan = set(huellas) - set(huellas_de_anexos.get(anexo, ()))
        if faltan:
            avisos.append(
                f"{len(faltan)} entrada(s) de {anexo} que recibió el {_dia(ultimo['fecha'])} "
                "ya no vienen."
            )
    return Anterioridad(tuple(avisos), False, _ultima(previos))


def _dia(valor: Any) -> str:
    return valor.date().isoformat() if isinstance(valor, datetime) else str(valor)[:10]


def _ultima(previos: Sequence[Mapping]) -> str:
    if not previos:
        return ""
    ultimo = previos[-1]
    return f"versión {ultimo['codigo']} del {_dia(ultimo['emitido'])}"


def banner(
    v: Verificacion, nombre_seguro: Callable[[str], str] = lambda texto: texto
) -> tuple[str, str]:
    """`(color, texto)` del banner de estado (S3 §8.3). `nombre_seguro` escapa lo que viene del
    paquete: la interfaz le pasa `texto_seguro`."""
    emitido = str((v.manifiesto or {}).get("emitido", ""))[:10]
    quien = nombre_seguro(v.empresa_declarada or "una empresa que no se indica")
    if v.estado == VERIFICADO:
        extra = " (clave retirada después)" if v.retirada else ""
        return "verde", (
            f"Verificado: emitido por {nombre_seguro(v.empresa_verificada or '')} el {emitido}. "
            f"No se alteró desde que se firmó.{extra}"
        )
    if v.estado == NO_VERIFICADO:
        razones = {
            "sin_firma": "El paquete no está firmado: las huellas solo prueban que no se dañó "
            "por accidente, no que nadie lo cambió.",
            "empresa_no_registrada": "Su clave no está registrada en esta instalación.",
            "revocada": "Su clave fue revocada.",
            "retirada_tarde": "Su clave se retiró antes de que usted recibiera el paquete.",
        }
        return "ambar", (
            f"No verificado: dice venir de {quien}, pero no se pudo comprobar. "
            f"{razones.get(v.motivo, '')} Se audita igual."
        )
    if v.estado == ALTERADO:
        return "rojo", (
            f"Alterado: {nombre_seguro(v.detalle)}. No confíe en este paquete; pida uno nuevo."
        )
    return "rojo", f"Rechazado: {nombre_seguro(v.detalle)}"
