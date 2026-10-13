"""Contexto de una devolución: qué hojas salen, qué APU se regeneran y cómo se reescriben las
referencias del libro recibido (spec 1.5, F-D4 y F-D5).

Reglas de referencias (`Contexto.rango`), para toda fórmula que se conserva:

- Vínculo a otro libro, `#REF!`, hoja que no sale (AUX, plantillas de APU sin partida) o nombre que
  no sale → la fórmula no se puede conservar: se sustituye por su valor (`None`).
- Celda de un APU regenerado → su nombre definido (`APU_01_PU`) si es un rótulo publicado, o la
  celda equivalente de la maqueta uniforme (líneas, subtotales, cabecera). Si no tiene equivalente,
  la fórmula se sustituye por su valor.
- Columna completa de un APU (`'APU-01'!$B:$B`) → se conserva: la hoja mantiene su nombre.
- Todo lo demás se conserva tal cual (las hojas copiadas conservan sus posiciones).

Nombres definidos del libro recibido: uno cuyo texto rechaza la lista negra de
`formulas.motivo_peligro` (DDE, WEBSERVICE, HYPERLINK, CALL, REGISTER, EXEC, FILTERXML, INFO, RTD,
otro libro) no sale y queda anotado en las transformaciones del calcado; las fórmulas que lo usan
pasan a su valor por la regla de "nombre que no sale".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from adapters.hoja_empresa.escritor.apu import PUBLICADOS, Maqueta
from adapters.hoja_empresa.escritor.estilos import LectorEstilos
from adapters.hoja_empresa.escritor.formulas import (
    MAX_FILA,
    Ref,
    analizar_ref,
    cita,
    dir_celda,
    motivo_peligro,
)
from adapters.hoja_empresa.escritor.hoja import LibroSalida
from adapters.hoja_empresa.modelo import ApuLeido, DatosDevolucion, PartidaLeida, Rotulo
from adapters.hoja_empresa.perfil import Perfil, normalizar

__all__ = ["Contexto", "ERRORES"]

ERRORES = frozenset({"#REF!", "#N/A", "#VALUE!", "#DIV/0!", "#NAME?", "#NUM!", "#NULL!"})
_NO_NOMBRE = re.compile(r"[^A-Za-z0-9_]")


@dataclass(slots=True)
class Contexto:
    datos: DatosDevolucion
    perfil: Perfil
    wb: Any
    estilos: LectorEstilos
    salida: LibroSalida = field(default_factory=LibroSalida)
    hoja_presupuesto: str = ""
    unidos: dict[str, PartidaLeida] = field(default_factory=dict)
    idents: dict[str, str] = field(default_factory=dict)
    quitadas: set[str] = field(default_factory=set)
    maqueta: Maqueta | None = None
    mapas: dict[str, dict[int, int]] = field(default_factory=dict)
    nombres: dict[str, str] = field(default_factory=dict)
    pendientes: list[tuple[str, int, int, str, str]] = field(default_factory=list)

    @property
    def libro(self):  # noqa: ANN201 - LibroLeido
        return self.datos.libro

    # -- hojas --

    def es(self, hoja: str, logica: str) -> bool:
        return normalizar(hoja) == normalizar(self.perfil.hojas.get(logica, logica))

    def preparar(self) -> None:
        """Decide qué hojas salen, qué APU se regeneran y sus identificadores."""
        libro = self.libro
        nombres_wb = list(self.wb.sheetnames)
        pres = next((h for h in nombres_wb if self.es(h, "PRESUPUESTO")), None)
        self.hoja_presupuesto = pres or self.perfil.hoja("PRESUPUESTO")
        prefijo = normalizar(self.perfil.prefijo_apu)
        for p in libro.partidas:
            if p.hoja_apu and p.hoja_apu in nombres_wb and p.hoja_apu not in self.unidos:
                self.unidos[p.hoja_apu] = p
        for h in nombres_wb:
            if self.es(h, "AUX"):
                self.quitadas.add(h)
            elif normalizar(h).startswith(prefijo) and h not in self.unidos:
                self.quitadas.add(h)
        # El orden de los APU unidos es el de las hojas del libro.
        self.unidos = {h: self.unidos[h] for h in nombres_wb if h in self.unidos}
        usados: set[str] = set()
        for h in self.unidos:
            a = libro.apu(h)
            base = _NO_NOMBRE.sub("_", a.ident if a is not None else h)
            ident, i = base, 2
            while ident.upper() in usados:
                ident, i = f"{base}_{i}", i + 1
            usados.add(ident.upper())
            self.idents[h] = ident

    def apu(self, hoja: str) -> ApuLeido | None:
        return self.libro.apu(hoja)

    def nombre_rotulo(self, hoja: str, r: Rotulo) -> str:
        return f"{self.idents[hoja]}_{r.value}"

    def partida(self, numero: int) -> PartidaLeida | None:
        """La partida con ese número; con números repetidos, la unida a un APU y con cantidad."""
        cands = [p for p in self.libro.partidas if p.numero == numero]
        if not cands:
            return None
        for criterio in (
            lambda p: p.hoja_apu in self.unidos and p.cantidad != 0,
            lambda p: p.hoja_apu in self.unidos,
            lambda p: True,
        ):
            elegidas = [p for p in cands if criterio(p)]
            if elegidas:
                return elegidas[0]
        return None

    # -- nombres --

    def preparar_nombres(self) -> None:
        """Nombres del libro que se conservan + los nombres publicados por cada APU."""
        assert self.maqueta is not None
        salen = set(self.wb.sheetnames) - self.quitadas
        for nombre, texto in self.libro.nombres.items():
            if nombre.startswith("_xlnm") or "!_xlnm" in nombre:
                continue
            t = (texto or "").strip().lstrip("=")
            if not t:
                continue
            motivo = motivo_peligro(t)
            if motivo is not None:
                self.salida.anotar(
                    "Nombre definido omitido",
                    None,
                    nombre,
                    f"no sale como fórmula, {motivo}: ={t[:255]}",
                )
                continue
            if "#REF!" in t.upper():
                continue
            hojas = {h for h in (_hojas_de(t)) if h is not None}
            if any(h not in salen for h in hojas):
                continue
            if any(h in self.unidos for h in hojas):
                continue
            if "!" in nombre:
                hoja, _, local = nombre.rpartition("!")
                if hoja not in salen:
                    continue
                self.nombres[f"{cita(hoja)}!{local}"] = "=" + t
            else:
                self.nombres[nombre] = "=" + t
        for hoja in self.unidos:
            for r in PUBLICADOS:
                fila, col = self.maqueta.celda(r)
                self.nombres[self.nombre_rotulo(hoja, r)] = f"={cita(hoja)}!{dir_celda(fila, col)}"

    def existe_nombre(self, nombre: str) -> bool:
        u = nombre.upper()
        return any(k.upper() == u or k.upper().endswith("!" + u) for k in self.nombres)

    def celda_nombre(self, nombre: str) -> tuple[str, int, int] | None:
        """Hoja y celda a la que apunta un nombre del libro de salida (si es una celda)."""
        texto = next((v for k, v in self.nombres.items() if k.upper() == nombre.upper()), None)
        if texto is None:
            return None
        r = analizar_ref(texto.lstrip("="))
        if isinstance(r, Ref) and r.es_celda and r.hoja:
            return r.hoja, r.f1, r.c1
        return None

    # -- referencias --

    def rango(self, texto: str, hoja_formula: str) -> str | None:
        r = analizar_ref(texto)
        if r is None:
            return texto
        if isinstance(r, str):
            local = r.rpartition("!")[2]
            return texto if self.existe_nombre(local) else None
        if r.externa or r.rota:
            return None
        hoja = r.hoja if r.hoja is not None else hoja_formula
        if hoja in self.unidos:
            return self._ref_apu(hoja, r, texto)
        if hoja in self.quitadas or hoja not in self.wb.sheetnames:
            return None
        return texto

    def _ref_apu(self, hoja: str, r: Ref, texto: str) -> str | None:
        if r.f1 == 1 and r.f2 == MAX_FILA:
            return texto
        mapa = self.mapas.get(hoja, {})
        if r.es_celda:
            nueva = mapa.get(r.f1)
            if nueva is None:
                return None
            assert self.maqueta is not None
            for rot in PUBLICADOS:
                if self.maqueta.celda(rot) == (nueva, r.c1):
                    return self.nombre_rotulo(hoja, rot)
            return f"{cita(hoja)}!{dir_celda(nueva, r.c1)}"
        f1, f2 = mapa.get(r.f1), mapa.get(r.f2)
        if f1 is None or f2 is None or f2 - f1 != r.f2 - r.f1:
            return None
        return f"{cita(hoja)}!{dir_celda(f1, r.c1)}:{dir_celda(f2, r.c2)}"


def _hojas_de(texto: str) -> list[str | None]:
    out: list[str | None] = []
    for parte in texto.split(","):
        r = analizar_ref(parte.strip())
        if isinstance(r, Ref):
            out.append(r.hoja)
    return out
