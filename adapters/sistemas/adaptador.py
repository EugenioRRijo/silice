"""Adaptador del dominio sistemas: alcance funcional (Sesión I5).

Lee una tabla CSV de casos de uso y calcula, para cada uno, los puntos de función no ajustados
(PFNA) por el método de análisis de puntos de función de IFPUG, con los pesos medios de
complejidad de cada tipo de función (International Function Point Users Group, tabla estándar de
complejidad media):

| Tipo de función                          | Sigla | Peso medio | Columna del CSV |
|-------------------------------------------|-------|-----------:|------------------|
| Entrada externa (External Input)           | EI    |          4 | `entradas`       |
| Salida externa (External Output)           | EO    |          5 | `salidas`        |
| Consulta externa (External Inquiry)        | EQ    |          4 | `consultas`      |
| Archivo lógico interno (Internal Logical File) | ILF |         10 | `archivos`       |
| Archivo de interfaz externa (External Interface File) | EIF |   7 | `interfaces`     |

`REGLA_PUNTOS_FUNCION` es la expresión trazable que combina esos pesos: cada `ItemComputo` la
guarda en `regla` junto con las cinco cantidades en `parametros`, de modo que el informe de
auditoría puede reevaluarla (regla R1 de `core/verification/`, NORMAS.md §7).

Nota sobre la unidad ("pf"): `core.contracts.unidades._ALIAS` es la única tabla de alias del
sistema (NORMAS.md §2) y solo cubre unidades físicas de obra (m3, m2, m, pieza, kg, etc.); "punto
de función" no es una de ellas. `normalizar_unidad("pf")` la deja tal cual (minúsculas, sin
espacios), sin traducirla ni fallar, que es el comportamiento documentado para unidades
desconocidas. No se modifica `core/contracts/unidades.py` para agregarla (regla del contrato
congelado, NORMAS.md §5 y §9): se documenta como hallazgo en
`docs/bitacora/2026-08-29-I5-sistemas.md`.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from adapters.sistemas.evaluador import evaluar_regla
from core.contracts import AdaptadorDominio, Dominio, ItemComputo, OrigenTipo

REGLA_PUNTOS_FUNCION = "4*entradas + 5*salidas + 4*consultas + 10*archivos + 7*interfaces"

_COLUMNAS_CONTEO = ("entradas", "salidas", "consultas", "archivos", "interfaces")
_COLUMNAS = ("id", "modulo", "caso_de_uso", "codigo_partida", *_COLUMNAS_CONTEO)


def _parsear_especificaciones(texto: str | None) -> dict[str, str]:
    """`"clave=valor;clave=valor"` -> `{"clave": "valor", ...}`. Cadena vacía -> diccionario vacío.

    Mismo formato que `adapters/civil/tabular.py`, repetido aquí porque el evaluador de este
    dominio es deliberadamente independiente del de civil (docstring de `adapters/sistemas/
    evaluador.py`) y esta función no forma parte de ningún contrato compartido.
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


class AdaptadorSistemas(AdaptadorDominio):
    """Extrae puntos de función no ajustados (PFNA) de una tabla CSV de alcance funcional.

    Cada fila es un caso de uso, con su propio `codigo_partida`: a diferencia del adaptador civil
    tabular, este no recibe un mapeo externo de códigos porque la fuente ya los declara. La
    cantidad de cada `ItemComputo` es el PFNA evaluado con `REGLA_PUNTOS_FUNCION` sobre las cinco
    columnas de conteo de la fila.
    """

    dominio = Dominio.SISTEMAS

    def extraer(self, fuente: Path | str) -> list[ItemComputo]:
        items: list[ItemComputo] = []
        for fila in _leer_filas(fuente, _COLUMNAS, self.dominio):
            parametros = {columna: _decimal(fila, columna, fuente) for columna in _COLUMNAS_CONTEO}
            cantidad = evaluar_regla(REGLA_PUNTOS_FUNCION, parametros)
            items.append(
                ItemComputo(
                    codigo_partida=fila["codigo_partida"],
                    descripcion=f"{fila['modulo']}: {fila['caso_de_uso']}",
                    unidad="pf",
                    cantidad=cantidad,
                    origen_id=fila["id"],
                    origen_tipo=OrigenTipo.REGLA,
                    dominio=Dominio.SISTEMAS,
                    regla=REGLA_PUNTOS_FUNCION,
                    parametros=parametros,
                    especificaciones=_parsear_especificaciones(fila.get("especificaciones")),
                )
            )
        return items
