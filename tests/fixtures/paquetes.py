"""Paquetes `.silice` armados a mano para las pruebas de verificación (S3-3; spec §13.3).

`paquete(...)` construye un paquete SIN pasar por la base: el `presupuesto.json` es el texto que se
le da (la verificación solo lo lee con el lector estricto y cuenta sus filas) y la cadena es
sintética pero consistente. Sus huellas se calculan AQUÍ, con `hashlib` y `json.dumps` según la
fórmula documentada en `core/budget/cadena.py` (spec S3 §6.2), y no con las funciones del núcleo:
si el núcleo cambiara la fórmula, el paquete «íntegro» dejaría de verificarse y la prueba lo diría
(oráculo independiente). `reempaquetar` cambia, quita o agrega archivos de un paquete ya hecho SIN
tocar su manifiesto ni su firma: así se fabrican las alteraciones de la tabla de S3 §13.3.

Todos los datos son ficticios (NORMAS.md §1): «Contratista Demo, C.A.» no existe.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from paquete.exportar import Emisor, construir_paquete
from paquete.verificar import armar_cadena_json
from seguridad import firma

GENESIS = "0" * 64
EMITIDO = datetime(2026, 11, 10, 9, 30, 0)
PRESUPUESTO = b'{"formato":"silice-presupuesto","version_formato":1,"nota":"de prueba"}'
INFORME = b'{"formato":"silice-informe","version_formato":1,"hallazgos":[]}'
ESPACIO = b'{"ambientes":[],"puntos":[]}'
CONTROL = b'{"formato":"silice-anexo","nombre":"control","entradas":[]}'
REAJUSTE = b'{"formato":"silice-anexo","nombre":"reajuste","entradas":[]}'
IA = b'{"formato":"silice-ia","pasos":[]}'
CUATRO_ANEXOS = {
    "anexos/espacio.json": ESPACIO,
    "anexos/reajuste.json": REAJUSTE,
    "anexos/control.json": CONTROL,
    "anexos/ia.json": IA,
}
EMPRESA = "Contratista Demo, C.A."
PAQUETE_ID = "11111111-1111-4111-8111-111111111111"


# --- huellas calculadas a mano (fórmula de S3 §6.2, sin importar core.budget.cadena) -----------


def sha(octetos: bytes) -> str:
    return hashlib.sha256(octetos).hexdigest()


def canonico(objeto: Any) -> bytes:
    """Claves ordenadas, sin espacios y UTF-8 sin escapar (SL-E8)."""
    return json.dumps(objeto, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def huella_anexos(anexos: Mapping[str, bytes]) -> str:
    return sha(canonico([[n, sha(anexos[n])] for n in sorted(anexos)]))


def huella_cambios(filas: Sequence[Sequence[str]]) -> str:
    return sha(canonico([list(f) for f in filas]))


def huella_eslabon(**campos: Any) -> str:
    return sha(canonico(campos))


def cadena_para(
    presupuesto: bytes, anexos: Mapping[str, bytes], codigos: Sequence[str] = ("004", "005")
) -> tuple[bytes, str]:
    """`(cadena.json, última huella)`: una cadena de `codigos`, la última atada a `presupuesto`
    y, si viene, a `anexos/espacio.json` (el único anexo que entra a la cadena)."""
    eslabones: list[dict[str, Any]] = []
    cambios: dict[str, list[list[str]]] = {}
    anterior = GENESIS
    for i, codigo in enumerate(codigos):
        ultima = i == len(codigos) - 1
        filas = [
            [
                "apu",
                "MIN-001|Arena",
                "cantidad",
                "1.00",
                "1.50",
                "memoria",
                "Ana <ana>",
                f"2026-11-0{i + 1}T08:00:00",
            ]
        ]
        contenido = sha(presupuesto) if ultima else sha(f"v{codigo}".encode())
        anexos_v = (
            {"anexos/espacio.json": anexos["anexos/espacio.json"]}
            if ultima and "anexos/espacio.json" in anexos
            else {}
        )
        cambios_h, anexos_h = huella_cambios(filas), huella_anexos(anexos_v)
        fecha = datetime(2026, 11, 1 + i, 8, 0, 0)
        h = huella_eslabon(
            anterior=anterior,
            codigo=codigo,
            contenido=contenido,
            cambios=cambios_h,
            anexos=anexos_h,
            usuario="Ana <ana>",
            fecha_hora=fecha.isoformat(),
            tipo="normal",
            version_formato=1,
        )
        eslabones.append(
            {
                "codigo": codigo,
                "anterior": anterior,
                "huella_contenido": contenido,
                "huella_cambios": cambios_h,
                "huella_anexos": anexos_h,
                "huella_eslabon": h,
                "usuario": "Ana <ana>",
                "fecha_hora": fecha.isoformat(),
                "tipo": "normal",
                "version_formato": 1,
            }
        )
        cambios[codigo] = filas
        anterior = h
    return canonico(armar_cadena_json(eslabones, cambios)), anterior


def paquete(
    *,
    par: firma.ParDeClaves | None = None,
    empresa: str | None = EMPRESA,
    anexos: Mapping[str, bytes] | None = None,
    destinatario: str | None = None,
    paquete_id: str = PAQUETE_ID,
    codigo: str = "005",
    presupuesto: bytes = PRESUPUESTO,
    codigos: Sequence[str] = ("004", "005"),
    declarar_clave: bool = True,
    emitido: datetime = EMITIDO,
) -> bytes:
    """Un paquete válido. Con `par` lo firma y declara su huella; sin él, queda sin firma."""
    anexos = dict(CUATRO_ANEXOS if anexos is None else anexos)
    cadena, ultima = cadena_para(presupuesto, anexos, codigos)
    huella_clave = firma.huella_completa(par.publica) if par and declarar_clave else None
    return construir_paquete(
        presupuesto=presupuesto,
        informe=INFORME,
        cadena=cadena,
        anexos=anexos,
        emisor=Emisor(empresa, huella_clave, "Ana <ana>"),
        destinatario=destinatario,
        proyecto="MIN-001",
        codigo=codigo,
        moneda="USD",
        total="836.79750000",
        ultima_huella=ultima,
        ahora=emitido,
        version_silice="0.8.0",
        privada=par.privada if par else None,
        paquete_id=paquete_id,
    )


def leer_zip(datos: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        return {i.filename: z.read(i) for i in z.infolist()}


def escribir_zip(archivos: Mapping[str, bytes]) -> bytes:
    flujo = io.BytesIO()
    with zipfile.ZipFile(flujo, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, octetos in archivos.items():
            z.writestr(nombre, octetos)
    return flujo.getvalue()


def reempaquetar(datos: bytes, cambios: Mapping[str, bytes | None]) -> bytes:
    """El mismo paquete con `cambios` (`None` quita el archivo); sin tocar manifiesto ni firma."""
    archivos = leer_zip(datos)
    for nombre, octetos in cambios.items():
        if octetos is None:
            archivos.pop(nombre, None)
        else:
            archivos[nombre] = octetos
    return escribir_zip(archivos)


def con_manifiesto(datos: bytes, **campos: Any) -> bytes:
    """El paquete con campos del manifiesto cambiados (la firma queda la vieja)."""
    archivos = leer_zip(datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    manifiesto.update(campos)
    archivos["manifiesto.json"] = canonico(manifiesto)
    return escribir_zip(archivos)


def con_archivo_rehecho(datos: bytes, nombre: str, nuevo: bytes) -> bytes:
    """Cambia `nombre` Y rehace su SHA-256 y tamaño en el manifiesto (la firma queda la vieja)."""
    archivos = leer_zip(datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    for entrada in manifiesto["archivos"]:
        if entrada["nombre"] == nombre:
            entrada["sha256"], entrada["tamano"] = sha(nuevo), len(nuevo)
    archivos[nombre], archivos["manifiesto.json"] = nuevo, canonico(manifiesto)
    return escribir_zip(archivos)


def refirmar(datos: bytes, par: firma.ParDeClaves, huella_declarada: str | None = None) -> bytes:
    """Rehace el manifiesto con una huella de clave (opcional) y lo firma con `par`."""
    archivos = leer_zip(datos)
    manifiesto = json.loads(archivos["manifiesto.json"])
    if huella_declarada is not None:
        manifiesto["huella_clave"] = huella_declarada
    archivos["manifiesto.json"] = canonico(manifiesto)
    archivos["firma.ed25519"] = firma.firmar(
        par.privada, firma.DOMINIO_PAQUETE, archivos["manifiesto.json"]
    )
    return escribir_zip(archivos)
