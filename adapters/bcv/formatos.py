"""Los formatos del BCV que S1-0 verifico abriendo los archivos reales (spec S1 §7.1): la letra de
cada trimestre en el nombre del archivo de la tasa y la hoja, los encabezados, la marca y la base
del INPC. `formatos.json` (junto a este modulo) es copia literal de la tabla «Formatos para
`adapters/bcv/formatos.json`» de `docs/fuentes/bcv_formatos.md`; lo comprueba
`tests/unit/adapters/test_bcv_inpc.py::test_formatos_json_copia_bcv_formatos_md`. Si el BCV cambia
un formato, se corrige la tabla, se regenera el JSON y se vuelve a transcribir `FUENTE.md`.

`FormatoMensual` vive aqui (y `inpc` lo importa) para que este modulo entre con el lector de la tasa
sin arrastrar el del INPC, que llega despues de su prueba (C3 de la meta)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from adapters.bcv.informe import FormatoNoReconocido

RUTA_FORMATOS = Path(__file__).with_name("formatos.json")


@dataclass(frozen=True, slots=True)
class FormatoMensual:
    """Donde estan, en el archivo mensual, el periodo y el valor (`bcv_formatos.md`)."""

    hoja: str
    etiqueta_periodo: str
    etiqueta_valor: str
    marca_provisional: str = "(*)"
    base: str = ""
    #: `periodo_en_celda`: cada fila trae su mes («Ene-2026»). `anio_en_filas`: el ano va en una
    #: fila propia y debajo los nombres de mes (`4_5_7.xls`, ver `docs/fuentes/bcv_formatos.md`).
    disposicion: str = "periodo_en_celda"


@dataclass(frozen=True, slots=True)
class Formatos:
    trimestre_por_letra: dict[str, int]
    inpc: FormatoMensual


def cargar_formatos() -> Formatos:
    datos = json.loads(RUTA_FORMATOS.read_text(encoding="utf-8"))
    letras = {
        str(letra).lower(): int(n) for letra, n in datos["tasa"]["trimestre_por_letra"].items()
    }
    if sorted(letras.values()) != [1, 2, 3, 4]:
        raise FormatoNoReconocido(f"{RUTA_FORMATOS.name}: cada trimestre 1 a 4 necesita su letra")
    inpc = datos["inpc"]
    return Formatos(
        letras,
        FormatoMensual(
            inpc["hoja"],
            inpc["etiqueta_periodo"],
            inpc["etiqueta_valor"],
            inpc["marca_provisional"],
            inpc["base"],
            inpc.get("disposicion", "periodo_en_celda"),
        ),
    )
