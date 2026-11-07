"""Reglas de auditoría de la especialidad vial, VR1 a VR7 (plan vial, Tarea 9).

`auditar_vial(tramos, presupuesto, formula_asfalto_pct=...)` compara lo que dice el presupuesto con
lo que dicen los tramos. Una partida del presupuesto se casa con su capa o su línea por el
`origen_id` del ítem («tramo:T1:capa:1», «tramo:T1:demarcacion:1») y por el código de
`PARTIDAS_VIALES`: lo esperado sale de `derivar_tramos`, la misma derivación que produjo las
cantidades. Una partida sin ese origen no se evalúa aquí (que falte una partida es de la
conciliación, Tarea 10).

- **VR1** toneladas de carpeta del presupuesto ≠ área × espesor × densidad (tolerancia relativa),
  en la mezcla y, si la capa se mide en masa (F5 vial), también en su colocación.
- **VR2** porcentaje de asfalto declarado en la partida de mezcla (`especificaciones
  ["_porcentaje_asfalto"]`, que pone `derivar_tramos` desde `Capa.asfalto_pct`) a más de ±0,5
  puntos de la fórmula de trabajo. Sin fórmula no se evalúa; si quien arma la regla dice por qué
  (`sin_formula`, Tarea 16b), lo declara como INFO. La fórmula es un número plano por código de
  partida: este adaptador no importa de `produccion/` (`tests/unit/test_arquitectura.py`);
  `aplicacion/vial.py` la saca de la receta vigente de la mezcla propia.
- **VR3** ligante residual de imprimación y riego de adherencia fuera de su mínimo (y del máximo de
  la imprimación). El residual sale de la dosis en l/m² con la densidad del producto y la fracción
  residual de la emulsión (supuestos declarados).
- **VR4** t·km de transporte ≠ toneladas × distancia declarada.
- **VR5** litros de pintura (partida en `l` con origen de una línea) por km de línea de 10 cm fuera
  de su rango; el ancho sale de `especificaciones["_ancho_linea_cm"]` o, sin él, del supuesto. Los
  km pintados son los de la partida de la línea en m; la pintura que `derivar_tramos` pone a cada
  línea (`pintura_demarcacion`, Tarea 16b) es una partida en `l` más, la que llega a la Hoja.
- **VR6** progresivas solapadas (ERROR) o con huecos (ADVERTENCIA) entre los tramos de la obra,
  que son los de una misma vía. Cita `tramo:<id>` de los dos.
- **VR7** unidad de la partida incompatible con su capa o su línea, o código de partida que esa
  capa no produce (ERROR).

Severidad: VR1, VR4, VR6 (solape) y VR7 son aritmética o coherencia interna: ERROR. VR2, VR3, VR5 y
el hueco de VR6 dependen de rangos «a cotejar» o de un tramo que puede dejarse sin intervenir:
ADVERTENCIA. Los mensajes llevan coma decimal y punto de miles.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

from adapters.vial.constantes import (
    ADHERENCIA_RESIDUAL_MIN_G_M2,
    ANCHO_LINEA_REFERENCIA_CM,
    ANCHO_LINEA_SUPUESTO_CM,
    DENSIDAD_LIGANTE_KG_L,
    FRACCION_RESIDUAL_EMULSION,
    IMPRIMACION_RESIDUAL_MAX_G_M2,
    IMPRIMACION_RESIDUAL_MIN_G_M2,
    PARTIDAS_VIALES,
    PINTURA_MAX_L_KM,
    PINTURA_MIN_L_KM,
    TOLERANCIA_ASFALTO_PUNTOS,
    TOLERANCIA_CARPETA,
    TOLERANCIA_TRANSPORTE,
)
from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Tramo
from core.contracts import ItemComputo, Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "CODIGO_VR",
    "ESPEC_ANCHO_LINEA_CM",
    "ESPEC_PORCENTAJE_ASFALTO",
    "ReglasViales",
    "auditar_vial",
]

CODIGO_VR = "VR"
#: Directivas (DA-SF-3: empiezan con «_»): R4 no las contrasta con el texto del APU.
ESPEC_PORCENTAJE_ASFALTO = "_porcentaje_asfalto"
ESPEC_ANCHO_LINEA_CM = "_ancho_linea_cm"

_CERO = Decimal(0)
_MIL = Decimal(1000)
_DIEZ = Decimal(10)
_CIEN = Decimal(100)


def _n(valor: Decimal, decimales: int | None = None) -> str:
    """Un número con coma decimal y punto de miles; sin ceros de más."""
    if decimales is not None:
        valor = round(valor, decimales)
    texto = format(valor.normalize(), ",f")
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _hallazgo(
    regla: str,
    severidad: Severidad,
    origen: str | tuple[str, ...],
    descripcion: str,
    observado: Decimal | None = None,
    esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        severidad=severidad,
        descripcion=descripcion,
        origen_ids=(origen,) if isinstance(origen, str) else tuple(origen),
        valor_observado=observado,
        valor_esperado=esperado,
    )


def _numero(texto: str) -> Decimal | None:
    """El número escrito en una especificación (coma o punto decimal); `None` si no lo es."""
    try:
        valor = Decimal(texto.strip().replace(",", "."))
    except InvalidOperation:
        return None
    return valor if valor.is_finite() and valor > 0 else None


def _por_origen(presupuesto: Presupuesto) -> dict[str, list[ItemComputo]]:
    indice: dict[str, list[ItemComputo]] = defaultdict(list)
    for partida in presupuesto.partidas:
        indice[partida.item.origen_id].append(partida.item)
    return indice


def _suma(items: Sequence[ItemComputo], codigo: str) -> Decimal | None:
    cantidades = [i.cantidad for i in items if i.codigo_partida == codigo]
    return sum(cantidades, _CERO) if cantidades else None


def _codigo(clave: str) -> str:
    return PARTIDAS_VIALES[clave][0]


def _contra_derivado(
    regla: str,
    clave: str,
    derivados: Sequence[ItemComputo],
    indice: dict[str, list[ItemComputo]],
    tolerancia: Decimal,
    que: str,
) -> list[Hallazgo]:
    """Compara la suma del presupuesto con la cantidad derivada de cada capa para una partida."""
    codigo, hallazgos = _codigo(clave), []
    for derivado in derivados:
        if derivado.codigo_partida != codigo:
            continue
        observado = _suma(indice.get(derivado.origen_id, ()), codigo)
        esperado = derivado.cantidad
        if observado is None or abs(observado - esperado) <= esperado * tolerancia:
            continue
        hallazgos.append(
            _hallazgo(
                regla,
                Severidad.ERROR,
                derivado.origen_id,
                f"{que} de {derivado.origen_id}: {_n(observado)} {derivado.unidad} en el "
                f"presupuesto y {_n(esperado)} {derivado.unidad} por {derivado.regla} "
                f"(tolerancia {_n(tolerancia * _CIEN)} %)",
                observado,
                esperado,
            )
        )
    return hallazgos


def _vr2(
    derivados: Sequence[ItemComputo],
    indice: dict[str, list[ItemComputo]],
    formula_comun: Decimal | None,
    formulas: Mapping[str, Decimal],
    sin_formula: Mapping[str, str],
) -> list[Hallazgo]:
    tolerancia = Decimal(TOLERANCIA_ASFALTO_PUNTOS.valor)
    claves = {_codigo("carpeta_mezcla"), _codigo("bacheo_mezcla")}
    hallazgos = []
    for derivado in derivados:
        if derivado.codigo_partida not in claves:
            continue
        formula = formulas.get(derivado.codigo_partida, formula_comun)
        motivo = sin_formula.get(derivado.codigo_partida)
        if formula is None and motivo is None:
            continue
        for item in indice.get(derivado.origen_id, ()):
            texto = item.especificaciones.get(ESPEC_PORCENTAJE_ASFALTO)
            if item.codigo_partida != derivado.codigo_partida or texto is None:
                continue
            declarado = _numero(texto)
            if formula is None:
                escrito = texto if declarado is None else _n(declarado)
                hallazgos.append(
                    _hallazgo(
                        "VR2",
                        Severidad.INFO,
                        derivado.origen_id,
                        f"{derivado.origen_id}: asfalto de {escrito} % sin comparar con la "
                        f"fórmula de trabajo: {motivo}",
                        declarado,
                    )
                )
            elif declarado is None:
                hallazgos.append(
                    _hallazgo(
                        "VR2",
                        Severidad.ADVERTENCIA,
                        derivado.origen_id,
                        f"{derivado.origen_id}: el porcentaje de asfalto {texto!r} no es un número "
                        "mayor que cero",
                    )
                )
            elif abs(declarado - formula) > tolerancia:
                hallazgos.append(
                    _hallazgo(
                        "VR2",
                        Severidad.ADVERTENCIA,
                        derivado.origen_id,
                        f"{derivado.origen_id}: asfalto de {_n(declarado)} % y la fórmula de "
                        f"trabajo dice {_n(formula)} % (tolerancia ±{_n(tolerancia)} puntos: "
                        f"{TOLERANCIA_ASFALTO_PUNTOS.fuente})",
                        declarado,
                        formula,
                    )
                )
    return hallazgos


def _residual_g_m2(dosis_l_m2: Decimal) -> Decimal:
    return (
        dosis_l_m2
        * _MIL
        * Decimal(DENSIDAD_LIGANTE_KG_L.valor)
        * Decimal(FRACCION_RESIDUAL_EMULSION.valor)
    )


def _vr3(tramos: Sequence[Tramo]) -> list[Hallazgo]:
    minimos = {
        "imprimacion": (
            Decimal(IMPRIMACION_RESIDUAL_MIN_G_M2.valor),
            IMPRIMACION_RESIDUAL_MIN_G_M2,
        ),
        "riego_adherencia": (
            Decimal(ADHERENCIA_RESIDUAL_MIN_G_M2.valor),
            ADHERENCIA_RESIDUAL_MIN_G_M2,
        ),
    }
    maximo = Decimal(IMPRIMACION_RESIDUAL_MAX_G_M2.valor)
    hallazgos = []
    for tramo in tramos:
        for n, capa in enumerate(tramo.capas, start=1):
            if capa.tipo not in minimos or capa.dosis_l_m2 is None:
                continue
            origen = f"tramo:{tramo.id}:capa:{n}"
            residual = _residual_g_m2(capa.dosis_l_m2)
            minimo, constante = minimos[capa.tipo]
            limite, fuente, lado = None, constante.fuente, ""
            if residual < minimo:
                limite, lado = minimo, "el mínimo"
            elif capa.tipo == "imprimacion" and residual > maximo:
                limite, lado = maximo, "el máximo"
                fuente = IMPRIMACION_RESIDUAL_MAX_G_M2.fuente
            if limite is not None:
                hallazgos.append(
                    _hallazgo(
                        "VR3",
                        Severidad.ADVERTENCIA,
                        origen,
                        f"{origen}: {_n(capa.dosis_l_m2)} l/m² dejan {_n(residual, 2)} g/m² de "
                        f"ligante residual y {lado} de {capa.tipo} es {_n(limite)} g/m² "
                        f"({fuente})",
                        residual,
                        limite,
                    )
                )
    return hallazgos


def _vr5(derivados: Sequence[ItemComputo], indice: dict[str, list[ItemComputo]]) -> list[Hallazgo]:
    minimo, maximo = Decimal(PINTURA_MIN_L_KM.valor), Decimal(PINTURA_MAX_L_KM.valor)
    referencia = Decimal(ANCHO_LINEA_REFERENCIA_CM.valor)
    hallazgos = []
    for derivado in derivados:
        # el largo pintado de la línea (en m); la pintura que también deriva es lo que se mide
        if ":demarcacion:" not in derivado.origen_id or derivado.unidad != "m":
            continue
        km_pintados = derivado.cantidad / _MIL
        for item in indice.get(derivado.origen_id, ()):
            if item.unidad != "l":
                continue
            texto = item.especificaciones.get(ESPEC_ANCHO_LINEA_CM)
            ancho = Decimal(ANCHO_LINEA_SUPUESTO_CM.valor) if texto is None else _numero(texto)
            if ancho is None:
                hallazgos.append(
                    _hallazgo(
                        "VR5",
                        Severidad.ADVERTENCIA,
                        derivado.origen_id,
                        f"{derivado.origen_id}: el ancho de línea {texto!r} no es un número "
                        "mayor que cero",
                    )
                )
                continue
            tasa = item.cantidad / km_pintados / (ancho / referencia)
            limite = minimo if tasa < minimo else maximo if tasa > maximo else None
            if limite is not None:
                hallazgos.append(
                    _hallazgo(
                        "VR5",
                        Severidad.ADVERTENCIA,
                        derivado.origen_id,
                        f"{derivado.origen_id}: {_n(item.cantidad)} l de pintura en "
                        f"{_n(km_pintados)} km de línea de {_n(ancho)} cm son {_n(tasa, 2)} l por "
                        f"km de línea de {_n(referencia)} cm y el rango es de {_n(minimo)} a "
                        f"{_n(maximo)} ({PINTURA_MIN_L_KM.fuente})",
                        tasa,
                        limite,
                    )
                )
    return hallazgos


def _vr6(tramos: Sequence[Tramo]) -> list[Hallazgo]:
    hallazgos = []
    ordenados = sorted(tramos, key=lambda t: (t.progresiva_ini_km, t.progresiva_fin_km, t.id))
    previo: Tramo | None = None  # el que llega más lejos hasta ahora
    for tramo in ordenados:
        if previo is not None:
            origenes = (f"tramo:{previo.id}", f"tramo:{tramo.id}")
            if tramo.progresiva_ini_km < previo.progresiva_fin_km:
                solape = (
                    min(tramo.progresiva_fin_km, previo.progresiva_fin_km) - tramo.progresiva_ini_km
                )
                hallazgos.append(
                    _hallazgo(
                        "VR6",
                        Severidad.ERROR,
                        origenes,
                        f"solape de {_n(solape)} km entre {previo.id} y {tramo.id}: las mismas "
                        "progresivas se medirían dos veces",
                        solape,
                        _CERO,
                    )
                )
            elif tramo.progresiva_ini_km > previo.progresiva_fin_km:
                hueco = tramo.progresiva_ini_km - previo.progresiva_fin_km
                hallazgos.append(
                    _hallazgo(
                        "VR6",
                        Severidad.ADVERTENCIA,
                        origenes,
                        f"hueco de {_n(hueco)} km entre {previo.id} y {tramo.id}: progresivas "
                        "sin tramo",
                        hueco,
                        _CERO,
                    )
                )
        if previo is None or tramo.progresiva_fin_km > previo.progresiva_fin_km:
            previo = tramo
    return hallazgos


def _vr7(derivados: Sequence[ItemComputo], indice: dict[str, list[ItemComputo]]) -> list[Hallazgo]:
    por_codigo = {codigo: (clave, unidad) for clave, (codigo, _, unidad) in PARTIDAS_VIALES.items()}
    producidos: dict[str, dict[str, str]] = defaultdict(dict)
    for derivado in derivados:
        producidos[derivado.origen_id][derivado.codigo_partida] = derivado.unidad
    hallazgos = []
    for origen, unidades in producidos.items():
        for item in indice.get(origen, ()):
            if item.codigo_partida not in por_codigo:
                continue
            clave = por_codigo[item.codigo_partida][0]
            if item.codigo_partida not in unidades:
                motivo = f"la partida «{clave}» no la produce esa capa o línea"
            elif item.unidad != unidades[item.codigo_partida]:
                motivo = (
                    f"la partida «{clave}» va en {unidades[item.codigo_partida]} y el "
                    f"presupuesto la pone en {item.unidad}"
                )
            else:
                continue
            hallazgos.append(
                _hallazgo(
                    "VR7",
                    Severidad.ERROR,
                    origen,
                    f"{origen}: {motivo} (partida {item.codigo_partida})",
                )
            )
    return hallazgos


def auditar_vial(
    tramos: Sequence[Tramo],
    presupuesto: Presupuesto,
    *,
    formula_asfalto_pct: Decimal | None = None,
    formulas: Mapping[str, Decimal] | None = None,
    sin_formula: Mapping[str, str] | None = None,
) -> list[Hallazgo]:
    """Los hallazgos VR1 a VR7 de `presupuesto` frente a `tramos`, en orden de regla y de tramo.

    `formula_asfalto_pct` es el porcentaje de asfalto de la fórmula de trabajo, en puntos
    (5,5 es 5,5 %); `None` si no hay receta, y VR2 no se evalúa. `formulas` da la fórmula de cada
    partida de mezcla por su código (gana a `formula_asfalto_pct`) y `sin_formula`, por código, el
    motivo de que una partida no la tenga: VR2 lo declara (INFO) en cada mezcla que dice su
    porcentaje.
    """
    derivados = derivar_tramos(tramos)
    indice = _por_origen(presupuesto)
    return [
        *_contra_derivado(
            "VR1", "carpeta_mezcla", derivados, indice, Decimal(TOLERANCIA_CARPETA.valor), "carpeta"
        ),
        *_contra_derivado(
            "VR1",
            "carpeta_colocacion_masa",
            derivados,
            indice,
            Decimal(TOLERANCIA_CARPETA.valor),
            "colocación de la carpeta",
        ),
        *_vr2(derivados, indice, formula_asfalto_pct, formulas or {}, sin_formula or {}),
        *_vr3(tramos),
        *_contra_derivado(
            "VR4",
            "transporte_mezcla",
            derivados,
            indice,
            Decimal(TOLERANCIA_TRANSPORTE.valor),
            "transporte",
        ),
        *_vr5(derivados, indice),
        *_vr6(tramos),
        *_vr7(derivados, indice),
    ]


class ReglasViales(ReglaVerificacion):
    """VR1 a VR7 como regla de la auditoría: `elaborar(reglas=(*REGLAS, ReglasViales(...)))`.

    Sus hallazgos llevan `regla` «VR1»…«VR7», que no está entre las de `REGLAS`: al recargar o
    simular, `hallazgos_externos` los distingue y los vuelve a declarar (SF-E1), como a los de
    `Espacio`.
    """

    codigo = CODIGO_VR
    nombre = "Reglas viales"

    def __init__(
        self,
        tramos: Sequence[Tramo],
        formula_asfalto_pct: Decimal | None = None,
        *,
        formulas: Mapping[str, Decimal] | None = None,
        sin_formula: Mapping[str, str] | None = None,
    ) -> None:
        self.tramos = tuple(tramos)
        self.formula_asfalto_pct = formula_asfalto_pct
        self.formulas = dict(formulas or {})
        self.sin_formula = dict(sin_formula or {})

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return auditar_vial(
            self.tramos,
            presupuesto,
            formula_asfalto_pct=self.formula_asfalto_pct,
            formulas=self.formulas,
            sin_formula=self.sin_formula,
        )
