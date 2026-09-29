"""Reglas paramétricas trazables del dominio civil (Sesión I3.2).

Cada regla es una expresión de texto (fuente única y trazable, principio DRY): el informe de
auditoría puede reproducirla y `evaluador.evaluar_regla` puede volver a evaluarla contra los
`parametros` guardados en el `ItemComputo` que produjo. Las funciones `computar_*` combinan estas
expresiones con la geometría de una fuente (fila tabular, elemento IFC, etc.) y devuelven
`ItemComputo` con `origen_tipo=OrigenTipo.REGLA`.

Los códigos de partida NO son constantes de este módulo: los recibe el llamador (`codigos`), porque
pertenecen al catálogo (I0.4), no al adaptador.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from adapters.civil.evaluador import evaluar_regla
from core.contracts import Dominio, ItemComputo, OrigenTipo

# ---------------------------------------------------------------------------------------------
# Expresiones. Única copia: reproducirlas en una prueba es un error (CLAUDE.md, principio DRY).
# ---------------------------------------------------------------------------------------------

REGLA_CONCRETO_TANQUILLA = "n * (a**2 - (a - 2*e)**2) * h"  # m3
REGLA_ENCOFRADO_TANQUILLA = "n * (4*a*h + 4*(a - 2*e)*h)"  # m2
REGLA_EXCAVACION_TANQUILLA = "n * (a + 2*sobreancho)**2 * (h + espesor_fondo)"  # m3
REGLA_EXCAVACION_ZANJA = "longitud * ancho * profundidad"  # m3
REGLA_TUBERIA = "longitud * (1 + desperdicio)"  # m
REGLA_VOLUMEN_TUBERIA = "longitud * 0.7854 * diametro**2"  # m3 (pi/4 ~= 0.7854, declarado)
REGLA_RELLENO = "excavacion - concreto - volumen_tuberia"  # m3

# Claves de `especificaciones` que son directivas para el núcleo (R5 las evalúa, R4 las ignora).
# El núcleo declarará las suyas propias; una prueba de la Sesión I4 verifica que coinciden.
CLAVE_BALANCE = "_balance"
CLAVE_TOLERANCIA = "_tolerancia"

_TOLERANCIA_BALANCE_DEFECTO = Decimal("0.05")


def computar_tanquillas(
    origen_id: str,
    codigos: Mapping[str, str],
    a: Decimal,
    h: Decimal,
    e: Decimal,
    n: Decimal,
    sobreancho: Decimal,
    espesor_fondo: Decimal,
    especificaciones: Mapping[str, str] | None = None,
) -> list[ItemComputo]:
    """Concreto, encofrado y excavación de `n` tanquillas idénticas, en ese orden.

    `a`, `h`, `e` son el ancho exterior, la altura y el espesor de pared (memoria de cálculo de la
    línea base). `sobreancho` y `espesor_fondo` son el margen de excavación alrededor del foso y el
    espesor de base bajo la tanquilla (supuestos declarados en `data/samples/civil/README.md`).

    `especificaciones` describe el elemento construido del objeto, las paredes de concreto de la
    tanquilla: solo el ítem de concreto las recibe. El encofrado (de madera) y la excavación no son
    de ese material, y si las llevaran R4 las marcaría como no contrastables contra un APU que no
    las menciona, ruido sobre partidas a las que no se refieren (INV‑096).
    """
    especificaciones = dict(especificaciones or {})

    parametros_concreto = {"n": n, "a": a, "e": e, "h": h}
    concreto = ItemComputo(
        codigo_partida=codigos["concreto"],
        descripcion="Concreto en paredes de tanquilla",
        unidad="m3",
        cantidad=evaluar_regla(REGLA_CONCRETO_TANQUILLA, parametros_concreto),
        origen_id=origen_id,
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=REGLA_CONCRETO_TANQUILLA,
        parametros=parametros_concreto,
        especificaciones=especificaciones,
    )

    parametros_encofrado = {"n": n, "a": a, "h": h, "e": e}
    encofrado = ItemComputo(
        codigo_partida=codigos["encofrado"],
        descripcion="Encofrado de madera para paredes de tanquilla",
        unidad="m2",
        cantidad=evaluar_regla(REGLA_ENCOFRADO_TANQUILLA, parametros_encofrado),
        origen_id=origen_id,
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=REGLA_ENCOFRADO_TANQUILLA,
        parametros=parametros_encofrado,
    )

    parametros_excavacion = {
        "n": n,
        "a": a,
        "sobreancho": sobreancho,
        "h": h,
        "espesor_fondo": espesor_fondo,
    }
    excavacion = ItemComputo(
        codigo_partida=codigos["excavacion"],
        descripcion="Excavacion para foso de tanquilla",
        unidad="m3",
        cantidad=evaluar_regla(REGLA_EXCAVACION_TANQUILLA, parametros_excavacion),
        origen_id=origen_id,
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=REGLA_EXCAVACION_TANQUILLA,
        parametros=parametros_excavacion,
    )

    return [concreto, encofrado, excavacion]


def computar_zanja(
    origen_id: str,
    codigos: Mapping[str, str],
    longitud: Decimal,
    ancho: Decimal,
    profundidad: Decimal,
    diametro: Decimal,
    desperdicio: Decimal,
    especificaciones: Mapping[str, str] | None = None,
) -> list[ItemComputo]:
    """Excavación de zanja (m3) y tubería con desperdicio (m), en ese orden.

    `diametro` (metros) no participa en ninguna de las dos reglas de este par ni se persiste en
    `especificaciones`: una clave como "diametro_m" no tiene contraparte en el texto del APU y R4
    (Sesión I4) la marcaría como un hallazgo falso. El llamador (el adaptador tabular) sigue
    teniendo `diametro` disponible para calcular el volumen de tubería (`REGLA_VOLUMEN_TUBERIA`) y
    construir el balance de `computar_relleno`.

    `especificaciones` (el diámetro en pulgadas, el material) describe la tubería: solo ese ítem
    las recibe. La excavación de la zanja no es de PVC ni tiene diámetro (INV‑096).
    """
    especificaciones = dict(especificaciones or {})

    parametros_excavacion = {"longitud": longitud, "ancho": ancho, "profundidad": profundidad}
    excavacion = ItemComputo(
        codigo_partida=codigos["excavacion"],
        descripcion="Excavacion en tierra para zanja de tuberia",
        unidad="m3",
        cantidad=evaluar_regla(REGLA_EXCAVACION_ZANJA, parametros_excavacion),
        origen_id=origen_id,
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=REGLA_EXCAVACION_ZANJA,
        parametros=parametros_excavacion,
    )

    parametros_tuberia = {"longitud": longitud, "desperdicio": desperdicio}
    tuberia = ItemComputo(
        codigo_partida=codigos["tuberia"],
        descripcion="Suministro e instalacion de tuberia",
        unidad="m",
        cantidad=evaluar_regla(REGLA_TUBERIA, parametros_tuberia),
        origen_id=origen_id,
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=REGLA_TUBERIA,
        parametros=parametros_tuberia,
        especificaciones=especificaciones,
    )

    return [excavacion, tuberia]


def computar_relleno(
    origen_id: str,
    codigos: Mapping[str, str],
    excavacion: Decimal,
    concreto: Decimal,
    volumen_tuberia: Decimal,
    balance: str | None = None,
    tolerancia: Decimal = _TOLERANCIA_BALANCE_DEFECTO,
) -> ItemComputo:
    """Relleno = excavacion - concreto - volumen_tuberia (m3), la regla de balance R5.

    Si se da `balance` (la expresión en términos de códigos de partida que el núcleo evaluará en la
    Sesión I4), se guarda en `especificaciones[CLAVE_BALANCE]` junto con `tolerancia` en
    `especificaciones[CLAVE_TOLERANCIA]`.
    """
    parametros = {
        "excavacion": excavacion,
        "concreto": concreto,
        "volumen_tuberia": volumen_tuberia,
    }
    especificaciones: dict[str, str] = {}
    if balance is not None:
        especificaciones[CLAVE_BALANCE] = balance
        especificaciones[CLAVE_TOLERANCIA] = str(tolerancia)

    return ItemComputo(
        codigo_partida=codigos["relleno"],
        descripcion="Relleno compactado con material granular",
        unidad="m3",
        cantidad=evaluar_regla(REGLA_RELLENO, parametros),
        origen_id=origen_id,
        origen_tipo=OrigenTipo.REGLA,
        dominio=Dominio.CIVIL,
        regla=REGLA_RELLENO,
        parametros=parametros,
        especificaciones=especificaciones,
    )
