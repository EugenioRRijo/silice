"""Adaptador tabular del dominio civil (Sesión I3.2).

Lee una tabla CSV de geometría (tanquillas y zanjas) y devuelve las cantidades de obra trazables
que producen las reglas paramétricas de `adapters/civil/reglas.py`. Es la entrada tabular prevista
por la compuerta G1 (NORMAS.md, sección 8.2) si el adaptador IFC no reproduce el cálculo manual;
aquí se implementa de forma independiente porque el brief de esta sesión la pide como entrega
propia.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.civil.evaluador import evaluar_regla
from adapters.civil.reglas import (
    REGLA_VOLUMEN_TUBERIA,
    computar_relleno,
    computar_tanquillas,
    computar_zanja,
)
from core.contracts import AdaptadorDominio, Dominio, ItemComputo

_TIPO_TANQUILLA = "tanquilla"
_TIPO_ZANJA = "zanja"
# Todas las columnas del formato (data/samples/civil/README.md): las que no aplican a la
# fila van vacias, pero la cabecera las trae. Exigirlas distingue una fuente de otro
# dominio que tambien tenga "id" y "tipo", como la topologia de telecom (T-4 de la
# revision de la pista P de C5).
_COLUMNAS = (
    "id",
    "tipo",
    "a",
    "h",
    "e",
    "n",
    "sobreancho",
    "espesor_fondo",
    "longitud",
    "ancho",
    "profundidad",
    "diametro",
    "desperdicio",
)


def _parsear_especificaciones(texto: str | None) -> dict[str, str]:
    """`"clave=valor;clave=valor"` -> `{"clave": "valor", ...}`. Cadena vacía -> diccionario vacío.

    Convierte el texto de la columna `especificaciones` del CSV en el diccionario que espera
    `ItemComputo.especificaciones` (regla R4).
    """
    resultado: dict[str, str] = {}
    for par in (texto or "").split(";"):
        par = par.strip()
        if not par:
            continue
        clave, _, valor = par.partition("=")
        resultado[clave.strip()] = valor.strip()
    return resultado


def _leer_filas(
    fuente: Path | str, columnas: tuple[str, ...], dominio: Dominio
) -> list[dict[str, str]]:
    """Las filas del CSV, o `ValueError` con el nombre del archivo si no es una fuente de `dominio`.

    UC-01, flujo 2a (INV-089): un archivo binario (no es texto UTF-8) o sin las columnas que este
    adaptador lee (la muestra de otro dominio) se rechaza nombrando el archivo, con el
    `ValueError` que la API traduce a 422, en vez de un `KeyError` de la primera columna que
    falte. Cada adaptador tiene su copia: ninguno importa de otro (NORMAS.md §2).
    """
    nombre = Path(fuente).name
    try:
        with open(fuente, newline="", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            presentes = lector.fieldnames or ()
            faltantes = [columna for columna in columnas if columna not in presentes]
            if faltantes:
                raise ValueError(
                    f"el archivo {nombre!r} no es una fuente del dominio {dominio.value}: "
                    f"faltan las columnas {faltantes}"
                )
            return list(lector)
    except UnicodeDecodeError as error:
        raise ValueError(
            f"el archivo {nombre!r} es ilegible: no es un CSV de texto en UTF-8"
        ) from error


def _decimal(fila: dict[str, str], columna: str, fuente: Path | str) -> Decimal:
    """`fila[columna]` como `Decimal`, o `ValueError` con el archivo, la fila y la columna.

    Una celda vacia o no numerica lanzaria `decimal.InvalidOperation` sin contexto, que la API no
    traduce a 422 (INV-089, UC-01 flujo 2a).
    """
    valor = (fila.get(columna) or "").strip()
    try:
        return Decimal(valor)
    except InvalidOperation as error:
        raise ValueError(
            f"el archivo {Path(fuente).name!r}, fila {fila.get('id')!r}: la columna "
            f"{columna!r} esta vacia o no es numerica: {valor!r}"
        ) from error


class AdaptadorCivilTabular(AdaptadorDominio):
    """Extrae cantidades de obra civiles de una tabla CSV de geometría.

    Cada fila es una tanquilla o una zanja (columna `tipo`); si `codigos` declara un código de
    partida para `relleno`, se emite además un ítem de relleno que balancea toda la excavación, el
    concreto y el volumen de tubería de la fuente completa (regla R5, Sesión I4).

    **Límite declarado del balance de relleno:** la expresión que evalúa R5 lleva un único término
    `{tuberia} * factor`, y ese factor es el área de la sección de un solo diámetro. Por eso el
    adaptador rechaza con `ValueError` una fuente con dos zanjas de diámetros distintos cuando hay
    que construir el balance: escribirlo con uno solo de los dos haría que R5 comparase la cantidad
    del cómputo contra un volumen de tubería que no es el suyo y reportase un ERROR falso sobre
    datos consistentes. Un término por diámetro exigiría un código de partida de tubería por
    diámetro, y el catálogo del alpha tiene uno solo; el límite se declara en vez de rodearse
    (hallazgo de la revisión final del sprint alpha, ítem 1).
    """

    dominio = Dominio.CIVIL

    def __init__(self, codigos: Mapping[str, str]) -> None:
        self._codigos = dict(codigos)

    def extraer(self, fuente: Path | str) -> list[ItemComputo]:
        items: list[ItemComputo] = []
        ids_procesadas: list[str] = []
        excavacion_total = Decimal("0")
        concreto_total = Decimal("0")
        volumen_tuberia_total = Decimal("0")
        factor_volumen_tuberia: Decimal | None = None
        diametro_balance: Decimal | None = None

        for fila in _leer_filas(fuente, _COLUMNAS, self.dominio):
            fila_id = fila["id"]
            ids_procesadas.append(fila_id)
            especificaciones = _parsear_especificaciones(fila.get("especificaciones"))
            # Una fila corta (menos celdas que la cabecera) trae `None` en las que faltan.
            tipo = (fila.get("tipo") or "").strip()

            if tipo == _TIPO_TANQUILLA:
                concreto, encofrado, excavacion = computar_tanquillas(
                    origen_id=fila_id,
                    codigos=self._codigos,
                    a=_decimal(fila, "a", fuente),
                    h=_decimal(fila, "h", fuente),
                    e=_decimal(fila, "e", fuente),
                    n=_decimal(fila, "n", fuente),
                    sobreancho=_decimal(fila, "sobreancho", fuente),
                    espesor_fondo=_decimal(fila, "espesor_fondo", fuente),
                    especificaciones=especificaciones,
                )
                items.extend([concreto, encofrado, excavacion])
                concreto_total += concreto.cantidad
                excavacion_total += excavacion.cantidad
            elif tipo == _TIPO_ZANJA:
                diametro_zanja = _decimal(fila, "diametro", fuente)
                excavacion, tuberia = computar_zanja(
                    origen_id=fila_id,
                    codigos=self._codigos,
                    longitud=_decimal(fila, "longitud", fuente),
                    ancho=_decimal(fila, "ancho", fuente),
                    profundidad=_decimal(fila, "profundidad", fuente),
                    diametro=diametro_zanja,
                    desperdicio=_decimal(fila, "desperdicio", fuente),
                    especificaciones=especificaciones,
                )
                items.extend([excavacion, tuberia])
                excavacion_total += excavacion.cantidad
                if diametro_balance is not None and diametro_zanja != diametro_balance:
                    raise ValueError(
                        f"el balance de relleno no admite dos diametros de tuberia: la fila "
                        f"{fila_id!r} declara {diametro_zanja} y una fila anterior declara "
                        f"{diametro_balance}"
                    )
                diametro_balance = diametro_zanja
                # Factor de conversión m -> m3 de la tubería (área de la sección): se deriva
                # de REGLA_VOLUMEN_TUBERIA con longitud=1 para no repetir el coeficiente 0.7854.
                factor_volumen_tuberia = evaluar_regla(
                    REGLA_VOLUMEN_TUBERIA,
                    {"longitud": Decimal("1"), "diametro": diametro_zanja},
                )
                volumen_tuberia_total += factor_volumen_tuberia * tuberia.cantidad
            else:
                raise ValueError(
                    f"el archivo {Path(fuente).name!r}, fila {fila_id!r}: tipo de fila no "
                    f"reconocido: {tipo!r} (se esperaba {_TIPO_TANQUILLA!r} o {_TIPO_ZANJA!r})"
                )

        if "relleno" in self._codigos:
            if factor_volumen_tuberia is None:
                raise ValueError(
                    "no se puede construir el balance de relleno sin una fila de zanja "
                    "(se necesita el diametro de tuberia)"
                )
            balance = (
                f"{{{self._codigos['excavacion']}}} - {{{self._codigos['concreto']}}} - "
                f"{{{self._codigos['tuberia']}}} * {factor_volumen_tuberia}"
            )
            items.append(
                computar_relleno(
                    origen_id="relleno:" + ",".join(ids_procesadas),
                    codigos=self._codigos,
                    excavacion=excavacion_total,
                    concreto=concreto_total,
                    volumen_tuberia=volumen_tuberia_total,
                    balance=balance,
                )
            )

        return items
