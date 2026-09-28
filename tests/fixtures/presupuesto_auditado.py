"""El presupuesto que reproduce las siete inconsistencias, y su versión corregida.

Prueba de aceptación crítica de la Sesión I4 (indicador 1 de la tesis): el sistema debe detectar
7 de 7. Esta fixture no repite ningún dato de la línea base: toma las cantidades, los APU, la curva
y la geometría de `apu_linea_base`, los precios del motor (`core.costing.calcular_apu`) y las
expresiones paramétricas del adaptador civil (`adapters.civil.reglas`).

Que una fixture de pruebas importe `adapters` es deliberado: demuestra que las reglas que escribe un
adaptador son evaluables por el núcleo sin que el núcleo conozca al adaptador (CLAUDE.md §2).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from adapters.civil.reglas import (
    CLAVE_BALANCE,
    CLAVE_TOLERANCIA,
    REGLA_CONCRETO_TANQUILLA,
    REGLA_ENCOFRADO_TANQUILLA,
    REGLA_TUBERIA,
)
from core.contracts import (
    ComposicionAPU,
    ItemComputo,
    OrigenTipo,
    PartidaPresupuestada,
    Presupuesto,
    PuntoCurva,
    normalizar_unidad,
)
from core.costing import calcular_apu
from core.verification.directivas import CLAVE_UNIDAD_ORIGINAL
from core.verification.expresiones import evaluar, sustituir_codigos
from core.verification.texto import normalizar_texto
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.computo_auditado import composiciones_linea_base, items_auditados
from tests.fixtures.computo_civil import FACTOR_VOLUMEN_TUBERIA

# Excavación de la zanja más los fosos de las cuatro tanquillas: la memoria del PDF suma ambos
# términos para llegar a los 9,74 m3 del presupuesto. No es ninguna de las reglas del adaptador
# civil (que separa zanja y tanquilla en dos ítems), por eso se declara aquí.
REGLA_EXCAVACION_TOTAL = "longitud * ancho * profundidad + n * foso"

TOLERANCIA_BALANCE = "0.05"

# Balance volumétrico del relleno en términos de códigos de partida (directiva `_balance`, R5).
# Los códigos van entre llaves: no son identificadores de Python y el núcleo los sustituye por las
# cantidades del presupuesto antes de evaluar la expresión.
BALANCE_RELLENO = (
    f"{{{linea_base.APU_EXCAVACION.codigo_partida}}}"
    f" - {{{linea_base.APU_CONCRETO.codigo_partida}}}"
    f" - {{{linea_base.APU_TUBERIA.codigo_partida}}} * {FACTOR_VOLUMEN_TUBERIA}"
)


def _parametros_excavacion() -> dict[str, Decimal]:
    return {
        "longitud": linea_base.LONGITUD_TUBERIA_M,
        "ancho": linea_base.ZANJA["ancho"],
        "profundidad": linea_base.ZANJA["profundidad"],
        "n": linea_base.N_TANQUILLAS,
        "foso": linea_base.VOLUMEN_FOSO_TANQUILLA,
    }


def _parametros_tanquilla() -> dict[str, Decimal]:
    return {**linea_base.GEOMETRIA_TANQUILLA, "n": linea_base.N_TANQUILLAS}


def _con_regla(item: ItemComputo, regla: str, parametros: dict[str, Decimal]) -> ItemComputo:
    return replace(item, origen_tipo=OrigenTipo.REGLA, regla=regla, parametros=parametros)


def _con_especificaciones(item: ItemComputo, extra: dict[str, str]) -> ItemComputo:
    return replace(item, especificaciones={**item.especificaciones, **extra})


def items_con_trazas() -> tuple[ItemComputo, ...]:
    """Los ítems auditados con las reglas y especificaciones que el proyectista sí documentó.

    Excavación y tubería declaran reglas que reproducen su cantidad (no generan hallazgo de R1);
    encofrado y concreto declaran las reglas de la memoria, que NO reproducen la cantidad usada
    (inconsistencias 1 y 2). El relleno no deriva de ninguna regla: declara el balance volumétrico
    que la regla R5 debe verificar (inconsistencia 6).
    """
    trazas = {
        linea_base.APU_EXCAVACION.codigo_partida: lambda item: _con_regla(
            item, REGLA_EXCAVACION_TOTAL, _parametros_excavacion()
        ),
        linea_base.APU_TUBERIA.codigo_partida: lambda item: _con_especificaciones(
            _con_regla(
                item,
                REGLA_TUBERIA,
                {"longitud": linea_base.LONGITUD_TUBERIA_M, "desperdicio": Decimal("0")},
            ),
            {"diametro": linea_base.DIAMETRO_TUBERIA_MEMORIA, "material": "PVC"},
        ),
        linea_base.APU_ENCOFRADO.codigo_partida: lambda item: _con_regla(
            item, REGLA_ENCOFRADO_TANQUILLA, _parametros_tanquilla()
        ),
        linea_base.APU_CONCRETO.codigo_partida: lambda item: _con_regla(
            item, REGLA_CONCRETO_TANQUILLA, _parametros_tanquilla()
        ),
        linea_base.APU_RELLENO.codigo_partida: lambda item: _con_especificaciones(
            item, {CLAVE_BALANCE: BALANCE_RELLENO, CLAVE_TOLERANCIA: TOLERANCIA_BALANCE}
        ),
    }
    return tuple(trazas[item.codigo_partida](item) for item in items_auditados())


def _presupuesto(
    items: tuple[ItemComputo, ...],
    composiciones: dict[str, ComposicionAPU],
    curva: tuple[PuntoCurva, ...] = (),
) -> Presupuesto:
    partidas = tuple(
        PartidaPresupuestada(
            item=item,
            apu=composiciones[item.codigo_partida],
            resultado=calcular_apu(
                composiciones[item.codigo_partida], linea_base.PARAMETROS_LINEA_BASE
            ),
        )
        for item in items
    )
    return Presupuesto(
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
        partidas=partidas,
        curva=curva,
    )


def presupuesto_con_siete_inconsistencias() -> Presupuesto:
    """El presupuesto tal como fue emitido: cinco partidas y la curva que cierra en 99,30 %."""
    return _presupuesto(items_con_trazas(), composiciones_linea_base(), linea_base.CURVA_AUDITADA)


# ---------------------------------------------------------------------------------------------
# Versión corregida: el mismo caso sin ninguna de las siete inconsistencias
# ---------------------------------------------------------------------------------------------


def _apu_tuberia_corregido() -> ComposicionAPU:
    """APU de tubería con la unidad del cómputo y el factor de depreciación unificado.

    El factor correcto no se escribe aquí: se toma del mismo insumo en otro APU de la línea base,
    que es exactamente lo que exige la regla R6 (un solo factor por insumo).
    """
    factores = {
        normalizar_texto(equipo.descripcion): equipo.depreciacion
        for equipo in linea_base.APU_EXCAVACION.equipos
    }
    equipos = tuple(
        replace(equipo, depreciacion=factores[normalizar_texto(equipo.descripcion)])
        if normalizar_texto(equipo.descripcion) in factores
        else equipo
        for equipo in linea_base.APU_TUBERIA.equipos
    )
    unidad_computo = next(
        linea.unidad_computo
        for linea in linea_base.PRESUPUESTO_AUDITADO
        if linea.codigo_partida == linea_base.APU_TUBERIA.codigo_partida
    )
    return replace(
        linea_base.APU_TUBERIA, unidad=normalizar_unidad(unidad_computo), equipos=equipos
    )


def _composiciones_corregidas() -> dict[str, ComposicionAPU]:
    composiciones = composiciones_linea_base()
    composiciones[linea_base.APU_TUBERIA.codigo_partida] = _apu_tuberia_corregido()
    return composiciones


def _items_corregidos(composiciones: dict[str, ComposicionAPU]) -> tuple[ItemComputo, ...]:
    corregidos: list[ItemComputo] = []
    for item in items_con_trazas():
        unidad = composiciones[item.codigo_partida].unidad
        cantidad = linea_base.COMPUTO_CORREGIDO.get(item.codigo_partida, item.cantidad)
        corregido = replace(
            item,
            unidad=unidad,
            cantidad=cantidad,
            especificaciones={**item.especificaciones, CLAVE_UNIDAD_ORIGINAL: unidad},
        )
        if "diametro" in corregido.especificaciones:
            corregido = _con_especificaciones(
                corregido, {"diametro": linea_base.DIAMETRO_TUBERIA_PROYECTO}
            )
        corregidos.append(corregido)

    cantidades = {item.codigo_partida: item.cantidad for item in corregidos}
    return tuple(
        replace(item, cantidad=evaluar(sustituir_codigos(BALANCE_RELLENO, cantidades), {}))
        if CLAVE_BALANCE in item.especificaciones
        else item
        for item in corregidos
    )


def presupuesto_corregido() -> Presupuesto:
    """El mismo caso con las siete inconsistencias resueltas: el informe no debe hallar errores.

    La curva la construye `core.budget` (`plan_secuencial` y `generar_curva`, Sesión I0.5), que
    cierra al 100 % por construcción. La consume
    `tests/integration/test_auditoria_7_de_7.py::test_el_presupuesto_corregido_no_tiene_errores`.
    """
    from core.budget import generar_curva, plan_secuencial

    composiciones = _composiciones_corregidas()
    sin_curva = _presupuesto(_items_corregidos(composiciones), composiciones)
    return replace(sin_curva, curva=tuple(generar_curva(sin_curva, plan_secuencial(sin_curva))))
