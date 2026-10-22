"""Validacion de cada llamada de propuesta en cuatro capas (S4 §7).

1. esquema (Pydantic, `extra="forbid"`); 2. semantica (ids, referencias, catalogo, unidades);
3. citas y supuestos: la guarda contra el numero inventado; 4. construccion del modelo espacial por
la misma puerta que una edicion a mano. El catalogo de causas de rechazo es CERRADO (`Causa`): cada
una tiene su prueba. Los errores GEOMETRICOS que el modelo admite (un punto fuera de su ambiente)
no se rechazan aqui: son de R9 y se dejan al auditor, porque eso es lo que mide el experimento.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ValidationError

from aplicacion.hoja import Borrador, HojaInvalida
from asistente.catalogo import CatalogoVista
from asistente.herramientas import (
    POR_NOMBRE,
    DeclararSinPartida,
    ProponerAmbiente,
    ProponerFuente,
    ProponerPartida,
    ProponerPunto,
    ProponerRecorrido,
    Terminar,
    a_decimal,
)
from asistente.propuestas import EstadoPropuesta, OrigenIA, Propuesta, TipoPropuesta, aplicar
from core.contracts.unidades import unidades_equivalentes


class Causa(StrEnum):
    CAMPO_EXTRA = "campo_extra"
    CAMPO_FALTANTE = "campo_faltante"
    TIPO_INVALIDO = "tipo_invalido"
    NUMERO_INVALIDO = "numero_invalido"
    ID_REPETIDO = "id_repetido"
    REFERENCIA_INEXISTENTE = "referencia_inexistente"
    PARTIDA_INEXISTENTE = "partida_inexistente"
    UNIDAD_NO_EQUIVALENTE = "unidad_no_equivalente"
    SIN_CITA_NI_SUPUESTO = "sin_cita_ni_supuesto"
    CITA_NO_LITERAL = "cita_no_literal"
    NUMERO_AUSENTE_DE_LA_CITA = "numero_ausente_de_la_cita"
    FILA_NO_CONSTRUIBLE = "fila_no_construible"
    NOTAS_CON_MONTOS = "notas_con_montos"


@dataclass(frozen=True, slots=True)
class Rechazo:
    causa: Causa
    motivo: str


@dataclass(frozen=True, slots=True)
class Contexto:
    """Lo que la validacion necesita: el texto de la persona, el borrador y lo ya pendiente."""

    textos_de_la_persona: tuple[str, ...]
    borrador: Borrador
    pendientes: Sequence[Propuesta]
    catalogo: CatalogoVista
    origen: OrigenIA
    siguiente_id: str


#: Campos numericos de cada herramienta de propuesta: cada uno exige cita o supuesto (§7.3).
NUMERICOS: dict[str, tuple[str, ...]] = {
    "proponer_ambiente": ("x0", "y0", "largo", "ancho", "alto"),
    "proponer_fuente": ("x", "y", "z"),
    "proponer_punto": ("x", "y", "z"),
    "proponer_partida": ("cantidad",),
}
#: Dimensiones que deben ser positivas (la hoja las rechaza igual, pero el motivo es mas claro).
POSITIVOS = frozenset({"largo", "ancho", "alto", "cantidad"})
_NUMERO = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?(?![\w])", re.IGNORECASE)
_MONTO = re.compile(
    r"(\d[\d.,]*\s*(\$|us\$|usd|bs\.?|bolivares|dolares))|((\$|us\$|usd|bs\.?)\s*\d)",
    re.IGNORECASE,
)
_A_METROS = {"mm": Decimal("0.001"), "cm": Decimal("0.01"), "m": Decimal(1)}


def normalizar(texto: str) -> str:
    """Espacios colapsados y coma decimal como punto: lo unico que la cita literal tolera."""
    return re.sub(r"(?<=\d),(?=\d)", ".", " ".join(texto.split()))


def numeros_de(texto: str) -> set[Decimal]:
    """Los numeros de un texto, tal cual y convertidos a metros (cm -> m, mm -> m)."""
    encontrados: set[Decimal] = set()
    for crudo, unidad in _NUMERO.findall(normalizar(texto)):
        valor = Decimal(crudo)
        encontrados.add(valor)
        if unidad:
            encontrados.add(valor * _A_METROS[unidad.lower()])
    return encontrados


def _rechazar_pydantic(error: ValidationError) -> Rechazo:
    detalle = error.errors()[0]
    donde = ".".join(str(p) for p in detalle["loc"])
    causa = {
        "extra_forbidden": Causa.CAMPO_EXTRA,
        "missing": Causa.CAMPO_FALTANTE,
        "string_pattern_mismatch": Causa.NUMERO_INVALIDO,
    }.get(detalle["type"], Causa.TIPO_INVALIDO)
    return Rechazo(causa, f"{donde}: {detalle['msg']}")


def validar_esquema(nombre: str, argumentos: Mapping[str, object]) -> BaseModel | Rechazo:
    """Capa 1. Una herramienta desconocida es un tipo invalido."""
    herramienta = POR_NOMBRE.get(nombre)
    if herramienta is None:
        return Rechazo(Causa.TIPO_INVALIDO, f"herramienta desconocida: {nombre!r}")
    try:
        return herramienta.modelo.model_validate(argumentos)
    except ValidationError as error:
        return _rechazar_pydantic(error)


def _ids(contexto: Contexto, tipo: TipoPropuesta) -> set[str]:
    existentes = {
        TipoPropuesta.AMBIENTE: {a.id for a in contexto.borrador.espacio.ambientes},
        TipoPropuesta.FUENTE: {f.id for f in contexto.borrador.espacio.fuentes},
        TipoPropuesta.PUNTO: {p.id for p in contexto.borrador.espacio.puntos},
    }.get(tipo, set())
    return existentes | {
        p.filas[0]["id"]
        for p in contexto.pendientes
        if p.tipo is tipo and "id" in p.filas[0] and p.estado.value != "rechazada"
    }


def _referencias(modelo: BaseModel, contexto: Contexto) -> Rechazo | None:
    """Capa 2, referencias: cada id citado existe en el borrador o en las pendientes."""
    ambientes = _ids(contexto, TipoPropuesta.AMBIENTE)
    fuentes = _ids(contexto, TipoPropuesta.FUENTE)
    puntos = _ids(contexto, TipoPropuesta.PUNTO)
    circuitos = {c.id for c in contexto.borrador.espacio.circuitos}
    pedidas = [
        ("ambiente_id", getattr(modelo, "ambiente_id", None), ambientes),
        ("fuente_id", getattr(modelo, "fuente_id", None), fuentes),
        ("circuito_id", getattr(modelo, "circuito_id", None), circuitos),
        ("punto_id", getattr(modelo, "punto_id", None), puntos),
    ]
    for campo, valor, existentes in pedidas:
        if valor is not None and valor not in existentes:
            return Rechazo(Causa.REFERENCIA_INEXISTENTE, f"{campo}: {valor!r} no existe")
    return None


def validar_semantica(nombre: str, modelo: BaseModel, contexto: Contexto) -> Rechazo | None:
    """Capa 2: ids nuevos, referencias, catalogo, unidades y especialidad del punto."""
    tipo = {
        "proponer_ambiente": TipoPropuesta.AMBIENTE,
        "proponer_fuente": TipoPropuesta.FUENTE,
        "proponer_punto": TipoPropuesta.PUNTO,
    }.get(nombre)
    if tipo is not None and modelo.id in _ids(contexto, tipo):
        return Rechazo(Causa.ID_REPETIDO, f"id: {modelo.id!r} ya existe")
    rechazo = _referencias(modelo, contexto)
    if rechazo is not None:
        return rechazo
    if isinstance(modelo, ProponerPartida):
        partida = contexto.catalogo.partida(modelo.codigo)
        if partida is None:
            return Rechazo(Causa.PARTIDA_INEXISTENTE, f"codigo: {modelo.codigo!r} no esta")
        if not unidades_equivalentes(modelo.unidad, partida.unidad):
            return Rechazo(
                Causa.UNIDAD_NO_EQUIVALENTE,
                f"unidad: {modelo.unidad!r} no equivale a {partida.unidad!r} de {modelo.codigo}",
            )
    if isinstance(modelo, ProponerPunto) and modelo.fuente_id is not None:
        fuente = next(
            (f for f in contexto.borrador.espacio.fuentes if f.id == modelo.fuente_id), None
        )
        pendiente = next(
            (
                p
                for p in contexto.pendientes
                if p.tipo is TipoPropuesta.FUENTE and p.filas[0]["id"] == modelo.fuente_id
            ),
            None,
        )
        especialidad = fuente.especialidad.value if fuente else pendiente.filas[0]["especialidad"]
        if especialidad != modelo.especialidad.value:
            return Rechazo(
                Causa.REFERENCIA_INEXISTENTE,
                f"fuente_id: {modelo.fuente_id!r} es de {especialidad}, no de "
                f"{modelo.especialidad.value}",
            )
    return None


def validar_citas(nombre: str, modelo: BaseModel, contexto: Contexto) -> Rechazo | None:
    """Capa 3: cada campo numerico trae una cita literal con su numero, o un supuesto."""
    texto_de_la_persona = normalizar(" ".join(contexto.textos_de_la_persona))
    for campo in NUMERICOS.get(nombre, ()):
        valor = a_decimal(getattr(modelo, campo))
        if campo in POSITIVOS and valor <= 0:
            return Rechazo(Causa.FILA_NO_CONSTRUIBLE, f"{campo}: debe ser positivo, no {valor}")
        if any(s.campo == campo for s in modelo.supuestos):  # type: ignore[attr-defined]
            continue
        citas = [c for c in modelo.citas if c.campo == campo]  # type: ignore[attr-defined]
        if not citas:
            return Rechazo(Causa.SIN_CITA_NI_SUPUESTO, f"{campo}: sin cita ni supuesto")
        literales = [c for c in citas if normalizar(c.texto) in texto_de_la_persona]
        if not literales:
            return Rechazo(
                Causa.CITA_NO_LITERAL, f"{campo}: la cita {citas[0].texto!r} no esta en el pedido"
            )
        if not any(abs(valor) in numeros_de(c.texto) for c in literales):
            return Rechazo(
                Causa.NUMERO_AUSENTE_DE_LA_CITA,
                f"{campo}: {valor} no aparece en la cita {literales[0].texto!r}",
            )
    return None


def _fila(nombre: str, modelo: BaseModel, id_propuesta: str) -> Propuesta:
    """Convierte la llamada en filas de texto del editor (numeros con punto decimal)."""
    citas = tuple((c.campo, c.texto) for c in modelo.citas)  # type: ignore[attr-defined]
    supuestos = tuple((s.campo, s.motivo) for s in modelo.supuestos)  # type: ignore[attr-defined]

    def n(texto: str) -> str:
        return str(a_decimal(texto))

    if isinstance(modelo, ProponerAmbiente):
        fila = {
            "id": modelo.id,
            "nombre": modelo.nombre,
            "x0": n(modelo.x0),
            "y0": n(modelo.y0),
            "largo": n(modelo.largo),
            "ancho": n(modelo.ancho),
            "alto": n(modelo.alto),
        }
        tipo = TipoPropuesta.AMBIENTE
    elif isinstance(modelo, ProponerFuente):
        fila = {
            "id": modelo.id,
            "especialidad": modelo.especialidad.value,
            "tipo": modelo.tipo.value,
            "ambiente_id": modelo.ambiente_id,
            "x": n(modelo.x),
            "y": n(modelo.y),
            "z": n(modelo.z),
        }
        tipo = TipoPropuesta.FUENTE
    elif isinstance(modelo, ProponerPunto):
        fila = {
            "id": modelo.id,
            "nombre": modelo.nombre,
            "especialidad": modelo.especialidad.value,
            "tipo": modelo.tipo.value,
            "ambiente_id": modelo.ambiente_id,
            "superficie": modelo.superficie.value,
            "x": n(modelo.x),
            "y": n(modelo.y),
            "z": n(modelo.z),
            "fuente_id": modelo.fuente_id or "",
            "circuito_id": modelo.circuito_id or "",
            "especificaciones": "; ".join(f"{p.clave}={p.valor}" for p in modelo.especificaciones),
        }
        tipo = TipoPropuesta.PUNTO
    elif isinstance(modelo, ProponerPartida):
        fila = {"codigo": modelo.codigo, "unidad": modelo.unidad, "cantidad": n(modelo.cantidad)}
        tipo = TipoPropuesta.PARTIDA
    else:
        raise AssertionError(nombre)
    return Propuesta(id_propuesta, tipo, (fila,), citas, supuestos)


def _recorrido(modelo: ProponerRecorrido, id_propuesta: str) -> Propuesta:
    citas = tuple((c.campo, c.texto) for c in modelo.citas)
    supuestos = tuple((s.campo, s.motivo) for s in modelo.supuestos)
    if modelo.modo == "propuesto":
        fila = {"punto_id": modelo.punto_id or "", "circuito_id": modelo.circuito_id or ""}
        return Propuesta(id_propuesta, TipoPropuesta.RECORRIDO, (fila,), citas, supuestos)
    recorrido = f"R-{modelo.punto_id or modelo.circuito_id}"
    filas = tuple(
        {
            "recorrido_id": recorrido,
            "punto_id": modelo.punto_id or "",
            "circuito_id": modelo.circuito_id or "",
            "orden": str(t.orden),
            "superficie": t.superficie.value,
            "empotrado": "",
            "pendiente": "",
            "vertices": "; ".join(
                f"{a_decimal(v.x)},{a_decimal(v.y)},{a_decimal(v.z)}" for v in t.vertices
            ),
        }
        for t in modelo.tramos or []
    )
    return Propuesta(id_propuesta, TipoPropuesta.RECORRIDO, filas, citas, supuestos, declarado=True)


def validar_recorrido(modelo: ProponerRecorrido, contexto: Contexto) -> Rechazo | None:
    """Un recorrido pertenece a un punto o a un circuito; el declarado trae tramos."""
    if (modelo.punto_id is None) == (modelo.circuito_id is None):
        return Rechazo(Causa.FILA_NO_CONSTRUIBLE, "un recorrido es de un punto o de un circuito")
    if modelo.modo == "declarado" and not modelo.tramos:
        return Rechazo(Causa.CAMPO_FALTANTE, "tramos: un recorrido declarado los necesita")
    if modelo.modo == "propuesto" and modelo.tramos:
        return Rechazo(Causa.FILA_NO_CONSTRUIBLE, "tramos: solo un recorrido declarado los trae")
    if modelo.modo == "declarado" and not (modelo.citas or modelo.supuestos):
        return Rechazo(Causa.SIN_CITA_NI_SUPUESTO, "vertices: sin cita ni supuesto")
    return None


def validar_notas(modelo: Terminar) -> Rechazo | None:
    if any(_MONTO.search(nota) for nota in modelo.notas):
        return Rechazo(Causa.NOTAS_CON_MONTOS, "notas: no pueden llevar montos de dinero")
    return None


PROPONER = frozenset(NUMERICOS) | {"proponer_recorrido"}


def validar_llamada(
    nombre: str, argumentos: Mapping[str, object], contexto: Contexto
) -> BaseModel | Propuesta | Rechazo:
    """Las cuatro capas, en orden.

    Una herramienta de propuesta valida devuelve su `Propuesta` PENDIENTE; `declarar_sin_partida`,
    tambien; una de lectura o de control (y `retirar_propuesta`) devuelve su modelo validado, para
    que lo ejecute el orquestador. El primer rechazo gana.
    """
    modelo = validar_esquema(nombre, argumentos)
    if isinstance(modelo, Rechazo):
        return modelo
    if isinstance(modelo, Terminar):
        return validar_notas(modelo) or modelo
    if isinstance(modelo, DeclararSinPartida):
        return Propuesta(
            contexto.siguiente_id, TipoPropuesta.SIN_PARTIDA, ({"necesidad": modelo.necesidad},)
        )
    if nombre not in PROPONER:
        return modelo
    rechazo = validar_semantica(nombre, modelo, contexto)
    if rechazo is None and isinstance(modelo, ProponerRecorrido):
        rechazo = validar_recorrido(modelo, contexto)
    if rechazo is None:
        rechazo = validar_citas(nombre, modelo, contexto)
    if rechazo is not None:
        return rechazo
    propuesta = (
        _recorrido(modelo, contexto.siguiente_id)
        if isinstance(modelo, ProponerRecorrido)
        else _fila(nombre, modelo, contexto.siguiente_id)
    )
    vigentes = [p for p in contexto.pendientes if p.estado is EstadoPropuesta.PENDIENTE]
    try:  # capa 4: la hoja debe poder construirla junto con lo ya pendiente
        aplicar(contexto.borrador, [*vigentes, propuesta], contexto.origen, contexto.catalogo)
    except HojaInvalida as error:
        return Rechazo(Causa.FILA_NO_CONSTRUIBLE, str(error))
    return propuesta
