"""Informe de auditoría: se genera siempre, sin que el usuario lo pida (CLAUDE.md §2.7).

`auditar` corre las siete reglas sobre un presupuesto y devuelve un `InformeAuditoria` inmutable con
los hallazgos ordenados y con lo necesario para atribuir cada hallazgo a su partida.

`Hallazgo` no lleva `codigo_partida` (insuficiencia del contrato registrada en la bitácora de la
Sesión I4): un hallazgo referencia `origen_ids`, y un mismo `origen_id` puede producir varias
partidas (el objeto paramétrico de `OrigenTipo.REGLA`). Por eso la atribución no se deduce del
origen: la declara la regla que emite el hallazgo (`ReglaAtribuible`, INV‑095) y el informe la
guarda en `partida_por_hallazgo`. Para las reglas que no la declaran (R2, R6, el `PENDIENTE` de
`core.budget` o una regla ajena al núcleo) queda el índice `origen_id -> codigo_partida`, que no
registra los orígenes compartidos por varias partidas. Todo sin tocar los contratos.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType

from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad
from core.verification.reglas import REGLAS, Atribucion, ReglaAtribuible
from core.verification.texto import formatear_decimal

__all__ = ["InformeAuditoria", "auditar"]

DECIMALES_PRESENTACION = 2

_SEVERIDADES = tuple(sorted(Severidad, reverse=True))
_GRAVES = frozenset({Severidad.ERROR, Severidad.CRITICO})


def _clave_orden(hallazgo: Hallazgo) -> tuple[int, str, str, str]:
    primer_origen = hallazgo.origen_ids[0] if hallazgo.origen_ids else ""
    return (-int(hallazgo.severidad), hallazgo.regla, primer_origen, hallazgo.descripcion)


def _celda(valor: Decimal | None) -> str:
    return "" if valor is None else formatear_decimal(valor, DECIMALES_PRESENTACION)


@dataclass(frozen=True, slots=True)
class InformeAuditoria:
    """Resultado de auditar un presupuesto. Los hallazgos se ordenan por gravedad descendente.

    `partida_por_hallazgo` guarda la partida que declaró la regla de cada hallazgo (`None` si la
    declaró para dos partidas distintas); `partida_por_origen` es el índice de respaldo para los
    hallazgos que ninguna regla atribuyó.
    """

    codigo_presupuesto: str
    hallazgos: tuple[Hallazgo, ...] = ()
    partida_por_origen: Mapping[str, str] = field(default_factory=dict)
    partida_por_hallazgo: Mapping[Hallazgo, str | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "hallazgos", tuple(sorted(self.hallazgos, key=_clave_orden)))
        object.__setattr__(
            self, "partida_por_origen", MappingProxyType(dict(self.partida_por_origen))
        )
        object.__setattr__(
            self, "partida_por_hallazgo", MappingProxyType(dict(self.partida_por_hallazgo))
        )

    @property
    def cumple(self) -> bool:
        """True si no hay ningún hallazgo de severidad ERROR o CRITICO."""
        return not any(hallazgo.severidad in _GRAVES for hallazgo in self.hallazgos)

    def por_severidad(self) -> dict[Severidad, int]:
        """Cuántos hallazgos hay de cada severidad, de la más grave a la más leve."""
        conteo = {severidad: 0 for severidad in _SEVERIDADES}
        for hallazgo in self.hallazgos:
            conteo[hallazgo.severidad] += 1
        return {severidad: total for severidad, total in conteo.items() if total}

    def por_regla(self) -> dict[str, list[Hallazgo]]:
        """Hallazgos agrupados por código de regla, en el orden en que aparecen en el informe."""
        agrupados: dict[str, list[Hallazgo]] = defaultdict(list)
        for hallazgo in self.hallazgos:
            agrupados[hallazgo.regla].append(hallazgo)
        return dict(agrupados)

    def partida_de(self, hallazgo: Hallazgo) -> str | None:
        """Código de la partida del hallazgo, o None si no se atribuye a ninguna.

        Primero, la partida que declaró la regla que lo emitió. Si ninguna la declaró, la del
        primer origen del hallazgo en el índice, que no registra un origen compartido por varias
        partidas: el informe no adivina. Un hallazgo que referencia el presupuesto completo (el
        cierre de la curva) no lleva orígenes y devuelve None.
        """
        if hallazgo in self.partida_por_hallazgo:
            return self.partida_por_hallazgo[hallazgo]
        if not hallazgo.origen_ids:
            return None
        return self.partida_por_origen.get(hallazgo.origen_ids[0])

    def a_markdown(self) -> str:
        """Informe legible: cabecera, resumen por severidad y tabla de hallazgos.

        Los montos y cantidades de la tabla se redondean a dos decimales, que es el único lugar
        donde se redondea (CLAUDE.md §2.3); la descripción de cada hallazgo conserva el valor
        exacto que lo motivó.
        """
        veredicto = "CUMPLE" if self.cumple else "NO CUMPLE"
        lineas = [
            f"# Informe de auditoria del presupuesto {self.codigo_presupuesto}",
            "",
            f"Hallazgos: {len(self.hallazgos)} · Resultado: {veredicto}",
            "",
            "## Resumen por severidad",
            "",
            "| Severidad | Hallazgos |",
            "|---|---|",
        ]
        lineas.extend(
            f"| {severidad.name} | {total} |" for severidad, total in self.por_severidad().items()
        )
        lineas.extend(
            [
                "",
                "## Hallazgos",
                "",
                "| # | Regla | Severidad | Partida | Descripcion | Impacto | Observado "
                "| Esperado |",
                "|---|---|---|---|---|---|---|---|",
            ]
        )
        for numero, hallazgo in enumerate(self.hallazgos, start=1):
            lineas.append(
                f"| {numero} | {hallazgo.regla} | {hallazgo.severidad.name} "
                f"| {self.partida_de(hallazgo) or '-'} | {hallazgo.descripcion} "
                f"| {_celda(hallazgo.impacto)} | {_celda(hallazgo.valor_observado)} "
                f"| {_celda(hallazgo.valor_esperado)} |"
            )
        lineas.append("")
        return "\n".join(lineas)


def auditar(
    presupuesto: Presupuesto, reglas: Sequence[ReglaVerificacion] = REGLAS
) -> InformeAuditoria:
    """Corre las reglas sobre el presupuesto y devuelve el informe.

    Nunca modifica el presupuesto: las reglas solo leen. Una regla atribuible (`ReglaAtribuible`)
    declara la partida de cada hallazgo; de las demás se toma `evaluar` y la atribución queda al
    índice de orígenes.
    """
    atribuciones: list[Atribucion] = []
    for regla in reglas:
        if isinstance(regla, ReglaAtribuible):
            atribuciones.extend(regla.atribuir(presupuesto))
        else:
            atribuciones.extend((hallazgo, None) for hallazgo in regla.evaluar(presupuesto))
    return InformeAuditoria(
        codigo_presupuesto=presupuesto.codigo,
        hallazgos=tuple(hallazgo for hallazgo, _ in atribuciones),
        partida_por_origen=_indice_de_partidas(presupuesto),
        partida_por_hallazgo=_partida_por_hallazgo(atribuciones),
    )


def _partida_por_hallazgo(atribuciones: Sequence[Atribucion]) -> dict[Hallazgo, str | None]:
    """La partida declarada de cada hallazgo; `None` si dos hallazgos iguales declaran partidas
    distintas, porque el informe no elige entre ellas."""
    declaradas: dict[Hallazgo, str | None] = {}
    for hallazgo, codigo in atribuciones:
        if codigo is None:
            continue
        declaradas[hallazgo] = codigo if declaradas.get(hallazgo, codigo) == codigo else None
    return declaradas


def _indice_de_partidas(presupuesto: Presupuesto) -> dict[str, str]:
    """`origen_id -> codigo_partida`, más la identidad de cada código: el respaldo de `partida_de`
    para los hallazgos que ninguna regla atribuyó.

    R6 compara APU entre sí y solo puede referenciar códigos de partida, y el `PENDIENTE` de
    `core.budget` cita primero el suyo: registrar también `codigo -> codigo` deja que `partida_de`
    los resuelva con la misma consulta. Un `origen_id` que citan partidas distintas no se registra
    (INV‑095): no hay forma de saber de cuál habla el hallazgo. Los demás `origen_id` tienen
    prioridad sobre la identidad: se registran primero.
    """
    partidas_del_origen: dict[str, set[str]] = defaultdict(set)
    for partida in presupuesto.partidas:
        partidas_del_origen[partida.item.origen_id].add(partida.item.codigo_partida)
    indice: dict[str, str] = {
        origen: next(iter(codigos))
        for origen, codigos in partidas_del_origen.items()
        if len(codigos) == 1
    }
    for partida in presupuesto.partidas:
        indice.setdefault(partida.item.codigo_partida, partida.item.codigo_partida)
    return indice
