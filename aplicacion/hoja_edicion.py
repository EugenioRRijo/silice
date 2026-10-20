"""Editar el borrador vivo de la hoja del proyecto (T10, 3c-1; diseno §3.2 y §5.1).

Es `_pestana_espacio` + `_poner_borrador` de la pagina clasica (P:1213-1217, P:256-275) hechos
servicio: las cinco tablas del editor del espacio se validan con `hoja.espacio_desde_filas` (la
copia del Plan C, tal cual, sin reimplementarla), el borrador nuevo completa la composicion de las
partidas que el espacio acaba de derivar (`hoja.completar_composiciones`, con la lista de precios
de la version abierta) y reemplaza al vivo subiendo su `rev`.

Si algo falla (`rev` viejo, borrador ya guardado, una celda invalida, la base) el borrador queda
EXACTAMENTE como estaba y `rev` no sube: «la hoja sigue con el ultimo borrador valido» (P:1217).
Una edicion que deja el espacio igual tampoco sube `rev` (la clasica no hace nada si
`nuevo == borrador`). Aqui no se escribe nada en la base: solo se lee el catalogo del caso.

Sin FastAPI ni Streamlit (RM-1).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from sqlalchemy.orm import Session

from aplicacion import hoja, hoja_borradores
from aplicacion.hoja_borradores import BorradorVivo, RevDesactualizado
from core.catalog import Catalogo

__all__ = ["BorradorYaGuardado", "RevDesactualizado", "editar_espacio"]

#: Las cinco tablas del editor del espacio, como las envia el navegador: tabla -> filas de texto.
TablasDelEspacio = Mapping[str, Sequence[Mapping[str, str]]]


class BorradorYaGuardado(Exception):  # noqa: N818
    """El borrador ya se guardo como una version (3d): se abre esa version para seguir."""

    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo


def editar_espacio(
    sesion: Session, huella: str, id: str, rev: int, tablas: TablasDelEspacio
) -> BorradorVivo:
    """Aplica las tablas al espacio del borrador `id` de la ficha `huella` y lo devuelve.

    Lanza `BorradorInexistente` (no existe para la ficha), `BorradorYaGuardado`,
    `RevDesactualizado` (se comprueba antes que el contenido: una ventana rezagada debe recargar,
    no corregir datos) o `HojaInvalida` con el texto de la clasica. La comprobacion de `rev`, la
    validacion y el reemplazo ocurren dentro del cerrojo del borrador.
    """
    vivo = hoja_borradores.obtener(huella, id)
    with vivo.cerrojo:
        if vivo.guardado_como is not None:
            raise BorradorYaGuardado(vivo.guardado_como)
        if vivo.rev != rev:
            raise RevDesactualizado(id)
        espacio = hoja.espacio_desde_filas(tablas, base=vivo.borrador.espacio)
        nuevo = replace(vivo.borrador, espacio=espacio)
        if nuevo == vivo.borrador:
            return vivo
        lista = None
        if vivo.abierta is not None:
            lista = hoja.lista_de_version(sesion, vivo.abierta.proyecto, vivo.abierta.codigo)
        nuevo = hoja.completar_composiciones(Catalogo(sesion), nuevo, lista=lista)
        return hoja_borradores.reemplazar(huella, id, nuevo, rev)
