"""Deriva las dos listas de precios canónicas de UC‑02 del dominio telecom (Sesión M1.3).

Escribe en `data/telecom/fuentes/`:

- `lista_arenaza.csv` — **lista 1**: los precios de mercado de los dos presupuestos ARENAZA
  (vigencia 18/05/2026, la fecha impresa en los PDF) en el formato canónico de UC‑02
  (`tipo,insumo,unidad,precio`, `core.catalog.precios.COLUMNAS_ARCHIVO`).
- `lista_maprex_2026-07.csv` — **lista 2**: el precio MaPreX de julio 2026 (vigencia 09/07/2026)
  de cada insumo ARENAZA con equivalencia defendible, derivado fila a fila de
  `data/precios/maprex_2026-07/referencia_telecom.csv` (Sesión M0.2).

Uso::

    uv run python scripts/derivar_listas_telecom.py              # escribe los dos CSV
    uv run python scripts/derivar_listas_telecom.py --verificar  # compara con los CSV en disco

Como en `scripts/extraer_arenaza.py`, regenerar es un no‑op: las dos listas se derivan
íntegramente de datos que ya viven en otro sitio —el fixture ARENAZA, a través de las composiciones
de `scripts/seed_telecom.py`, y el CSV de referencia MaPreX— y **aquí no se escribe ningún
precio** (NORMAS.md §2, principio DRY). `tests/unit/test_listas_telecom.py` comprueba que los CSV en
disco son exactamente los que este script deriva.

Lista 1: qué insumo entra y cuál no
-----------------------------------
Entra todo insumo del catálogo telecom al que la fuente le da **un único precio unitario no
contradicho**. Quedan fuera —y lo decide este script a partir de los datos, no de una lista de
nombres— cuatro casos:

1. Las **líneas de ajuste** (descripción que empieza por ``MARCA_AJUSTE``): obligación de la
   Sesión M1.2; son artefactos de reproducción del total impreso, no insumos de mercado.
2. Las **sumas globales** (``unidad = "sg"``): "Micelaneos" es un importe sin cantidad ni precio
   unitario, no un insumo con precio.
3. Los renglones cuyo **total impreso contradice** ``cantidad x precio_unitario`` en la fuente
   (los que llevan línea de ajuste: presupuesto 2, renglones 14 y 18). El PDF les da dos precios
   unitarios incompatibles —el impreso y el implícito en el total— y una lista canónica no elige
   uno en silencio.
4. Los insumos con **dos precios distintos en la fuente** para la misma descripción y unidad
   ("Organizador De Cables Individuales 20cm 100 Und": 18,00 en el presupuesto 1 y 19,00 en el 2).
   UC‑02 aplica una fila del archivo a todas las variantes de esa descripción
   (`core.catalog.precios`, "Homónimos"): incluir cualquiera de los dos precios sobrescribiría el
   otro y fabricaría un cambio de precio dentro de la misma fuente.

El tubo corrugado **sí entra** (99,75 USD por tubo de 30 m, bajo la descripción con la que lo
persiste el catálogo): su precio no está contradicho; el propio PDF declara la unidad de venta.

Lista 2: correspondencia ARENAZA <-> MaPreX
-------------------------------------------
``CORRESPONDENCIA`` es la **única** tabla de equivalencias del proyecto: descripción impresa en el
PDF ARENAZA -> ``ref_maprex`` de `referencia_telecom.csv` y factor de conversión de la unidad de
venta. Criterio de admisión, en este orden:

- La nota de la Sesión M0.2 declara la fila MaPreX **equivalente de ese insumo ARENAZA sin
  salvedad de atributo** (no "cubre", no "referencia de categoría", no "MaPreX no distingue…").
- La unidad de venta es la misma (pieza), **o** el factor de conversión lo imprime la propia
  fuente ARENAZA. Única conversión admitida: el tubo corrugado, cotizado por tubo de 30 m en
  ARENAZA ("30 MTS", "3*99,75") y por metro en MaPreX (``ELE906``). Es el insumo del hallazgo
  80/90 y el que la Sesión M1.2 dejó explícitamente para este contraste; el "30" viene del PDF, no
  es un supuesto de este script.

El precio MaPreX se convierte desde bolívares con la misma tasa y el mismo redondeo de la Sesión
M0.2: ``precio_usd = (precio_bs x factor / TASA)`` cuantizado a 0,0001 (`_verificar_tasa`
comprueba, para cada fila usada, que esa tasa es la que produjo el CSV de referencia).

Quedan fuera y anotadas en `data/telecom/fuentes/README.md`: las presentaciones en bobina o bolsa
(cable UTP, conectores RJ45, tirrap: MaPreX cotiza por metro o por pieza y M0.2 anotó la diferencia
como salvedad), los equivalentes genéricos (cinta aislante, guaya sin longitud, cajetín de red sin
"4x2"), las referencias de categoría (canaleta, rack, switch, patch panel, fibra, fusionadora) y
los insumos sin equivalente en MaPreX (cámaras IP, NVR, punto de acceso, UPS, protector de
voltaje). También el jack coupler (``ELC065``) y el organizador (``ELF449``): su insumo ARENAZA
no está en la lista 1 (casos 3 y 4), así que no hay precio anterior que contrastar.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# Igual que en scripts/seed_telecom.py: ejecutado como `python scripts/...`, sys.path[0] es
# scripts/ y `core` no se resuelve (pyproject declara `package = false`).
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.catalog.precios import COLUMNAS_ARCHIVO  # noqa: E402
from core.contracts import ComposicionAPU  # noqa: E402
from scripts.seed_telecom import (  # noqa: E402
    MARCA_AJUSTE,
    METROS_POR_TUBO,
    PRESUPUESTOS,
    UNIDAD_SUMA_GLOBAL,
    composicion_de,
)

CARPETA_FUENTES = RAIZ / "data" / "telecom" / "fuentes"
RUTA_LISTA_ARENAZA = CARPETA_FUENTES / "lista_arenaza.csv"
RUTA_LISTA_MAPREX = CARPETA_FUENTES / "lista_maprex_2026-07.csv"
RUTA_REFERENCIA_MAPREX = RAIZ / "data" / "precios" / "maprex_2026-07" / "referencia_telecom.csv"
#: Vigencia de la lista 2: la `fecha_vigencia` de las filas de `materiales.pdf` en
#: `referencia_telecom.csv` (09/07/2026), de donde salen sus cinco filas.
FECHA_LISTA_MAPREX = date(2026, 7, 9)

#: Tasa declarada en el listado de mano de obra de MaPreX (01/07/2026): la misma de
#: `scripts/extraer_maprex.py` y del README de `data/precios/maprex_2026-07/`. No se importa de
#: aquel script porque exige PyMuPDF al importarse; `_verificar_tasa` comprueba en cada corrida que
#: sigue siendo la que produjo `referencia_telecom.csv`.
TASA = Decimal("633.3644")
CUANTO_USD = Decimal("0.0001")

TIPO_MATERIAL = "material"
TIPO_EQUIPO = "equipo"
#: `LineaEquipo` no lleva unidad (core.contracts.apu); en la lista va la celda vacía.
UNIDAD_EQUIPO = ""

MOTIVO_AJUSTE = "linea de ajuste del total impreso (obligacion de la Sesion M1.2): no es un insumo"
MOTIVO_SUMA_GLOBAL = "suma global sin cantidad ni precio unitario en el PDF: no es un insumo"
MOTIVO_CONTRADICHO = (
    "el total impreso contradice cantidad x precio_unitario en la fuente ({origen}): "
    "dos precios unitarios incompatibles"
)
MOTIVO_DOS_PRECIOS = (
    "dos precios distintos en la fuente para la misma descripcion y unidad: {precios}"
)


@dataclass(frozen=True)
class Fila:
    """Una fila del formato canónico de UC‑02."""

    tipo: str
    insumo: str
    unidad: str
    precio: Decimal

    @property
    def clave(self) -> tuple[str, str, str]:
        return (self.tipo, self.insumo, self.unidad)


@dataclass(frozen=True)
class Correspondencia:
    """Un insumo ARENAZA y su fila MaPreX: Ref, factor de unidad de venta y por qué vale."""

    ref_maprex: str
    factor: Decimal
    nota: str


@dataclass(frozen=True)
class FilaMaprex:
    """Una fila de la lista 2 junto con la correspondencia que la produjo."""

    fila: Fila
    correspondencia: Correspondencia
    precio_bs: Decimal


_NOTA_TUBO = (
    'tubo PVC electricidad corrugado flexible D=1" (equivalente exacto, M0.2); MaPreX cotiza por '
    "metro y ARENAZA por tubo de 30 m (el PDF imprime '30 MTS' y '3*99,75'): factor 30"
)

#: Descripción impresa en el PDF ARENAZA (clave del fixture) -> fila MaPreX. Ver el módulo.
CORRESPONDENCIA: dict[str, Correspondencia] = {
    "Anillo E.m.t. 2": Correspondencia(
        "ELE033", Decimal("1"), 'anillo EMT D=2" (equivalente exacto, M0.2); misma unidad: pieza'
    ),
    "Toma Doble Con Tierra 270 20a Con Placa Blanca": Correspondencia(
        "ELA190", Decimal("1"), "tomacorriente doble 1 fase 20/30 A (equivalente, M0.2); pieza"
    ),
    "Cajetin Plástico 4x2 Pvc Con Grapa Metálica.": Correspondencia(
        "ELE654",
        Decimal("1"),
        'cajetin rectangular PVC 2"x4" (misma medida, orden invertido, M0.2); pieza',
    ),
    "Tubo Corrugado Flexible 1 Pulgada": Correspondencia("ELE906", METROS_POR_TUBO, _NOTA_TUBO),
    "Tubo Corrugado Flexible 1 Pulgada 30 MTS": Correspondencia(
        "ELE906", METROS_POR_TUBO, _NOTA_TUBO
    ),
}


# ---------------------------------------------------------------------------------------------
# Lista 1: los precios ARENAZA
# ---------------------------------------------------------------------------------------------


def _composiciones() -> list[tuple[str, ComposicionAPU]]:
    """Las 40 composiciones en el orden del PDF, con el `origen` de su renglón."""
    return [
        (renglon.origen, composicion_de(numero, renglon))
        for numero, renglones in sorted(PRESUPUESTOS.items())
        for renglon in renglones
    ]


def derivar_lista_arenaza() -> tuple[list[Fila], dict[str, str]]:
    """Las filas de la lista 1 y, aparte, cada descripción excluida con su motivo."""
    precios: dict[tuple[str, str, str], list[Decimal]] = {}
    orden: list[tuple[str, str, str]] = []
    excluidos: dict[str, str] = {}

    def registrar(clave: tuple[str, str, str], precio: Decimal) -> None:
        if clave not in precios:
            precios[clave] = []
            orden.append(clave)
        if precio not in precios[clave]:
            precios[clave].append(precio)

    for origen, composicion in _composiciones():
        contradicho = any(m.descripcion.startswith(MARCA_AJUSTE) for m in composicion.materiales)
        for material in composicion.materiales:
            if material.descripcion.startswith(MARCA_AJUSTE):
                excluidos[material.descripcion] = MOTIVO_AJUSTE
            elif material.unidad == UNIDAD_SUMA_GLOBAL:
                excluidos[material.descripcion] = MOTIVO_SUMA_GLOBAL
            elif contradicho:
                excluidos[material.descripcion] = MOTIVO_CONTRADICHO.format(origen=origen)
            else:
                registrar((TIPO_MATERIAL, material.descripcion, material.unidad), material.precio)
        for equipo in composicion.equipos:
            registrar((TIPO_EQUIPO, equipo.descripcion, UNIDAD_EQUIPO), equipo.precio)

    filas: list[Fila] = []
    for clave in orden:
        vistos = precios[clave]
        if len(vistos) > 1:
            excluidos[clave[1]] = MOTIVO_DOS_PRECIOS.format(
                precios=" y ".join(f"{p:f}" for p in vistos)
            )
            continue
        filas.append(Fila(*clave, vistos[0]))
    return filas, excluidos


# ---------------------------------------------------------------------------------------------
# Lista 2: la referencia MaPreX de los insumos con equivalencia defendible
# ---------------------------------------------------------------------------------------------


def _referencia_por_ref() -> dict[str, list[dict[str, str]]]:
    """Filas de `referencia_telecom.csv` por Ref.

    Una Ref puede repetirse entre listados de MaPreX (`EFO001` es fibra en `materiales.pdf` y
    fusionadora en `equipos.pdf`); la ambigüedad se resuelve al usarla (`_fila_referencia`).
    """
    with open(RUTA_REFERENCIA_MAPREX, newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    indice: dict[str, list[dict[str, str]]] = {}
    for fila in filas:
        indice.setdefault(fila["ref_maprex"], []).append(fila)
    return indice


def _fila_referencia(indice: dict[str, list[dict[str, str]]], ref: str) -> dict[str, str]:
    """La única fila de la Ref; error explícito si no está o si es ambigua entre listados."""
    filas = indice.get(ref, [])
    if len(filas) != 1:
        raise ValueError(
            f"{RUTA_REFERENCIA_MAPREX.name}: la Ref {ref} aparece {len(filas)} veces; "
            "CORRESPONDENCIA exige exactamente una fila por Ref"
        )
    return filas[0]


def a_usd(precio_bs: Decimal, factor: Decimal = Decimal("1")) -> Decimal:
    """Bolívares x factor de unidad de venta -> USD, con la tasa y el redondeo de la Sesión M0.2."""
    return (precio_bs * factor / TASA).quantize(CUANTO_USD, rounding=ROUND_HALF_UP)


def _verificar_tasa(fila: dict[str, str]) -> None:
    """La tasa de este script debe reproducir el `precio_usd` que M0.2 escribió para esa fila."""
    esperado = Decimal(fila["precio_usd"])
    if a_usd(Decimal(fila["precio_bs"])) != esperado:
        raise ValueError(
            f"la tasa {TASA} no reproduce el precio_usd de {fila['ref_maprex']} en "
            f"{RUTA_REFERENCIA_MAPREX.name} ({esperado}): las dos sesiones usan tasas distintas"
        )


def derivar_lista_maprex() -> list[FilaMaprex]:
    """Las filas de la lista 2, cada una con la correspondencia y el precio en Bs que la produjo."""
    referencia = _referencia_por_ref()
    filas: list[FilaMaprex] = []
    vistas: set[tuple[str, str, str]] = set()
    usadas: set[str] = set()
    for origen, composicion in _composiciones():
        correspondencia = CORRESPONDENCIA.get(composicion.descripcion)
        if correspondencia is None:
            continue
        usadas.add(composicion.descripcion)
        if len(composicion.materiales) != 1 or composicion.equipos:
            raise ValueError(
                f"{origen}: la correspondencia MaPreX exige un renglon de una sola linea de "
                "material sin ajuste (casos 3 y 4 del modulo); revise CORRESPONDENCIA"
            )
        (material,) = composicion.materiales
        clave = (TIPO_MATERIAL, material.descripcion, material.unidad)
        if clave in vistas:
            continue
        vistas.add(clave)
        fila_referencia = _fila_referencia(referencia, correspondencia.ref_maprex)
        _verificar_tasa(fila_referencia)
        precio_bs = Decimal(fila_referencia["precio_bs"])
        filas.append(
            FilaMaprex(
                Fila(*clave, a_usd(precio_bs, correspondencia.factor)),
                correspondencia,
                precio_bs,
            )
        )
    sin_uso = set(CORRESPONDENCIA) - usadas
    if sin_uso:
        raise ValueError(
            "CORRESPONDENCIA cita descripciones que no estan en ningun presupuesto ARENAZA: "
            + ", ".join(sorted(sin_uso))
        )
    return filas


def derivar_listas() -> tuple[list[Fila], dict[str, str], list[FilaMaprex]]:
    """Las dos listas juntas, verificando que toda fila de la lista 2 tiene su par en la lista 1."""
    lista_1, excluidos = derivar_lista_arenaza()
    lista_2 = derivar_lista_maprex()
    claves_1 = {fila.clave for fila in lista_1}
    sin_par = [fila.fila.insumo for fila in lista_2 if fila.fila.clave not in claves_1]
    if sin_par:
        raise ValueError(
            "estas filas de la lista MaPreX no tienen precio ARENAZA que contrastar: "
            + ", ".join(sin_par)
        )
    return lista_1, excluidos, lista_2


# ---------------------------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------------------------


def fila_csv(fila: Fila) -> dict[str, str]:
    """La fila como la escribe el CSV: texto exacto, sin pasar por `float`."""
    return {
        "tipo": fila.tipo,
        "insumo": fila.insumo,
        "unidad": fila.unidad,
        "precio": f"{fila.precio:f}",
    }


def leer_csv(ruta: Path) -> list[dict[str, str]]:
    with open(ruta, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames != list(COLUMNAS_ARCHIVO):
            raise ValueError(
                f"{ruta.name}: cabecera {lector.fieldnames}, se esperaba {COLUMNAS_ARCHIVO}"
            )
        return list(lector)


def escribir_csv(ruta: Path, filas: Sequence[Fila]) -> None:
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(COLUMNAS_ARCHIVO))
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila_csv(fila))


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def _imprimir_contraste(lista_1: Sequence[Fila], lista_2: Sequence[FilaMaprex]) -> None:
    arenaza = {fila.clave: fila.precio for fila in lista_1}
    print("Contraste ARENAZA 18/05/2026 -> MaPreX 09/07/2026 (USD):")
    for fila in lista_2:
        anterior = arenaza[fila.fila.clave]
        variacion = (fila.fila.precio - anterior) / anterior
        print(
            f"  {fila.correspondencia.ref_maprex} x{fila.correspondencia.factor:f} | "
            f"{anterior:f} -> {fila.fila.precio:f} ({variacion:+.1%}) | {fila.fila.insumo}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--verificar",
        action="store_true",
        help="no escribe: compara los CSV en disco con lo derivado y sale con 1 si difieren",
    )
    argumentos = analizador.parse_args(argv)

    lista_1, excluidos, lista_2 = derivar_listas()
    esperado = {
        RUTA_LISTA_ARENAZA: [fila_csv(fila) for fila in lista_1],
        RUTA_LISTA_MAPREX: [fila_csv(fila.fila) for fila in lista_2],
    }
    if argumentos.verificar:
        distintos = [ruta.name for ruta, filas in esperado.items() if leer_csv(ruta) != filas]
        if distintos:
            print("Difieren de lo derivado: " + ", ".join(distintos))
            return 1
        print("Los dos CSV coinciden con lo derivado.")
    else:
        escribir_csv(RUTA_LISTA_ARENAZA, lista_1)
        escribir_csv(RUTA_LISTA_MAPREX, [fila.fila for fila in lista_2])
        print(f"{RUTA_LISTA_ARENAZA.name}: {len(lista_1)} insumos")
        print(f"{RUTA_LISTA_MAPREX.name}: {len(lista_2)} insumos")

    print(f"Excluidos de la lista 1 ({len(excluidos)}):")
    for descripcion, motivo in excluidos.items():
        print(f"  - {descripcion[:60]}: {motivo}")
    _imprimir_contraste(lista_1, lista_2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
