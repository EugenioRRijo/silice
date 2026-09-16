"""Carga el catálogo telecom (ARENAZA) en SQLite y reproduce sus dos presupuestos.

Hermano de `scripts/seed.py` (que hace lo mismo con la línea base civil) y, como aquel, el único
módulo fuera de `tests/` que importa su fixture: `tests/fixtures/presupuestos_arenaza.py` es la
única copia de los dos presupuestos ARENAZA en todo el sistema (CLAUDE.md §2, principio DRY). Aquí
**no se escribe ningún número del PDF**: todos se leen del fixture.

Uso::

    uv run python scripts/seed_telecom.py                 # crea data/apu_telecom.db
    uv run python scripts/seed_telecom.py --db /tmp/x.db  # otra ruta
    uv run python scripts/seed_telecom.py --reiniciar     # borra el esquema y lo vuelve a crear

Qué se construye y por qué
==========================

**Objetivo de la reproducción: el PDF tal como está impreso.** Igual que la línea base civil
conserva sus siete inconsistencias, este catálogo reproduce los totales impresos (1 109,29 y
5 410,73 USD) aunque cuatro renglones no cumplan ``cantidad x precio_unitario = total`` en la
fuente. Las contradicciones no se corrigen: se representan con un mecanismo declarado y quedan
registradas para la auditoría de la Sesión M1.3.

Mapeo renglón -> partida (regla general, 36 de los 40 renglones)
---------------------------------------------------------------

Un renglón del PDF es una partida ``TC-P<n>-<renglon>``:

===========================  ====================================================================
Elemento                     Valor
===========================  ====================================================================
``codigo_partida``           ``TC-P1-01``…``TC-P1-14``, ``TC-P2-01``…``TC-P2-26``
``unidad``                   la del renglón, normalizada ("Pieza" -> "pieza", "Metros" -> "m")
``rendimiento``              1 (supuesto: el PDF no declara rendimientos; ver "Supuestos")
``materiales``               una línea: 1 unidad al precio unitario impreso
``ItemComputo.cantidad``     la cantidad impresa en la tabla "Presupuesto" del PDF
===========================  ====================================================================

Con ello el motor puro devuelve ``precio_unitario`` = precio unitario impreso y el presupuesto
calcula ``cantidad x precio_unitario`` = total impreso, exactamente.

Los cuatro mecanismos de los renglones que el PDF no cierra
-----------------------------------------------------------

1. **Tubo corrugado** (P1 renglón 3 y P2 renglón 5; 90 m, 99,75 USD, total 299,25). El precio
   impreso está cotizado **por tubo de 30 m**, no por metro: el propio PDF anota "3*99,75". La
   partida conserva la unidad y la cantidad impresas (90 m) y su APU compra ``1/30`` de tubo por
   metro al precio impreso: ``(1/30) x 99,75 = 3,325 USD/m`` y ``90 x 3,325 = 299,25`` ✓. Así se
   conservan a la vez el precio impreso en la fuente (99,75 por tubo, que es lo que valdrá
   contrastar con MaPreX en M1.3) y el total impreso. El renglón del presupuesto 2 (donde
   "Presupuesto" imprime 90 m y "Computos metricos" imprime 80 m del mismo tubo) declara
   además `regla = REGLA_TUBO_CORRUGADO`, para que la Sesión M1.3 audite la discrepancia con
   la regla de verificación R1 (ver `item_de`).
2. **P2 renglones 14 y 18** (1 446,65 vs 5 x 289,00 = 1 445,00; 303,93 vs 7 x 42,99 = 300,93). El
   total impreso contradice la multiplicación **en la fuente**. Se reproduce el total impreso
   añadiendo al APU una segunda línea de material declarada, cuya descripción empieza por
   ``MARCA_AJUSTE`` y cita el importe impreso, el producto y el ``origen`` de la fila. El precio
   unitario impreso (289,00 y 42,99) queda intacto en la primera línea y en la lista de precios: la
   diferencia no se disuelve dentro del precio del insumo, se ve. La contradicción **no se corrige**
   y es material de la Sesión M1.3.

   **Obligación para la Sesión M1.3 (y para cualquier consumidor de la lista de precios):** las
   líneas cuya descripción empieza por ``MARCA_AJUSTE`` son **artefactos de reproducción**, no
   insumos de mercado. Deben **excluirse de todo contraste de precios** (con MaPreX o con cualquier
   otra lista) y de toda **normalización semántica** de descripciones de insumo
   (``ml/normalization``): sus importes (0,33 y 0,428571… USD) no son precios de nada. Para que no
   puedan confundirse con un material cotizado por pieza llevan además ``unidad = "sg"`` (suma
   global), no la unidad del renglón. Son exactamente dos en todo el catálogo telecom y
   ``tests/integration/test_presupuesto_arenaza.py`` lo fija con una prueba, de modo que ningún
   ajuste nuevo pueda colarse sin que alguien lo decida.
3. **P1 renglón 14, "Micelaneos"** (total 100,00, sin cantidad ni unidad ni precio unitario). Se
   representa como **1 suma global x 100,00** (``unidad = "sg"``, el alias canónico de "global" en
   ``core.contracts.unidades``). El fixture sigue declarando ``cantidad = precio_unitario = None``:
   el "1" es un mecanismo de esta capa, no un dato de la fuente.
4. **Guaya guía pasa cable** (P1 renglón 12 y P2 renglón 26). Único renglón que no es un insumo que
   quede instalado sino una **herramienta reutilizable**: entra como ``LineaEquipo`` con
   ``depreciacion = 1,00``, el factor que el PDF aplica de hecho al cargar la herramienta completa a
   un solo presupuesto. Con ``rendimiento = 1`` el importe es el impreso (90,00). Que la herramienta
   se impute al 100 % es una observación para M1.3 (regla de verificación **R6**,
   ``CriterioDepreciacion``, CLAUDE.md §7), no un ajuste de esta capa.

La política de mano de obra "50 % del presupuesto total"
--------------------------------------------------------

Ambos PDF anotan: *"El precio de la mano de obra será el equivalente al 50% del presupuesto
total"*. Se implementa con la **OPCIÓN 1** del hallazgo 1 de
``docs/bitacora/2026-08-29-I5-telecom.md``: ``con_mano_obra`` arma, **fuera del motor**, una
``LineaManoObra`` sintética de una "cuadrilla" cuyo sueldo se despeja para que la mano de obra del
APU sea la fracción pedida del costo directo. El motor de costos no cambia (sigue siendo la función
pura de CLAUDE.md §4) y `core/` queda intacto.

Lectura adoptada: "el presupuesto total" es la cifra impresa al pie del PDF (la suma de los
renglones, que son todos suministros), de modo que la mano de obra es 0,50 x total impreso y se
**añade** a él. La lectura alternativa —que el total impreso ya incluyera la mano de obra, es decir
mano de obra = 100 % de los suministros— no es compatible con la fuente: los 14 y 26 renglones son
todos materiales y equipos y suman exactamente el total impreso, sin ningún renglón de mano de obra.
Ninguna de las dos lecturas afecta al criterio de cierre de la sesión (± 0,01 sobre el total
impreso): la mano de obra queda fuera de esa cifra en ambas.

La línea sintética **no se persiste**: SQLite guarda el presupuesto impreso (suministros), y la
política se aplica al reconstruir, antes de llamar al motor.

Supuestos declarados
--------------------

- ``rendimiento = 1`` para las 40 partidas: el PDF no declara rendimientos. Es neutro para los
  materiales (que no se dividen entre el rendimiento) y, con una sola partida-día por renglón,
  también para el único equipo.
- ``PARAMETROS_ARENAZA`` pone en cero FCAS, bono de alimentación, administración y utilidad: el PDF
  no imprime ninguno de los cuatro. No es una afirmación sobre la empresa, es lo que la fuente
  permite verificar; la estructura venezolana completa vive en la línea base civil.
- Los códigos ``TC-*`` son de este trabajo: el PDF no numera partidas con código.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

# Igual que en scripts/seed.py: ejecutado como `python scripts/seed_telecom.py`, sys.path[0] es
# scripts/ y `core` no se resuelve (pyproject declara `package = false`).
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core import models  # noqa: E402
from core.budget import generar_presupuesto  # noqa: E402
from core.catalog import (  # noqa: E402
    Catalogo,
    CatalogoIncompleto,
    abrir_sesion,
    crear_esquema,
    crear_motor,
)
from core.contracts import (  # noqa: E402
    ComposicionAPU,
    Dominio,
    ItemComputo,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    OrigenTipo,
    ParametrosCosto,
    Presupuesto,
)
from core.costing import calcular_apu  # noqa: E402
from core.verification.directivas import CLAVE_UNIDAD_ORIGINAL  # noqa: E402
from tests.fixtures import presupuestos_arenaza as arenaza  # noqa: E402
from tests.fixtures.presupuestos_arenaza import RenglonPresupuesto  # noqa: E402

# ---------------------------------------------------------------------------------------------
# Constantes del caso ARENAZA (los importes viven en el fixture; aquí solo lo que no es del PDF)
# ---------------------------------------------------------------------------------------------

FECHA_ARENAZA = date(2026, 5, 18)
MONEDA = "USD"
NOMBRE_PROYECTO = "Red de datos y videovigilancia ARENAZA"
DESCRIPCION_PROYECTO = (
    "Cableado estructurado, red inalambrica y videovigilancia IP de ARENAZA: los dos "
    "presupuestos fechados 18/05/2026 (001 y 002)"
)
NOMBRE_LISTA = "Precios ARENAZA 18/05/2026"
ORIGEN_LISTA = "Presupuesto_1_ARENAZA.pdf, Presupuesto_2_ARENAZA.pdf"
RUTA_POR_DEFECTO = "data/apu_telecom.db"

#: Los dos presupuestos del fixture, por número de PDF. Única puerta a sus renglones.
PRESUPUESTOS: Mapping[int, tuple[RenglonPresupuesto, ...]] = {
    1: arenaza.PRESUPUESTO_1,
    2: arenaza.PRESUPUESTO_2,
}
#: El total impreso de cada uno, para el resumen del CLI (el fixture es la fuente).
TOTALES: Mapping[int, Decimal] = {1: arenaza.TOTAL_1, 2: arenaza.TOTAL_2}
#: Código del presupuesto en el sistema. El PDF los numera 001 y 002; el prefijo los distingue
#: del 001 civil, que vive en otro proyecto.
CODIGOS_PRESUPUESTO: Mapping[int, str] = {1: "TC-001", 2: "TC-002"}

#: Sin rendimientos en la fuente: 1 unidad de partida por día (supuesto declarado, ver módulo).
RENDIMIENTO = Decimal("1")
#: El PDF no imprime FCAS, bono, administración ni utilidad.
PARAMETROS_ARENAZA = ParametrosCosto(
    fcas=Decimal("0"),
    bono_alimentacion=Decimal("0"),
    administracion=Decimal("0"),
    utilidad=Decimal("0"),
)

#: "El precio de la mano de obra sera el equivalente al 50% del presupuesto total" (nota del PDF).
FRACCION_MANO_OBRA = Decimal("0.50")
DESCRIPCION_MANO_OBRA = "Cuadrilla ARENAZA (mano de obra = 50 % del presupuesto total)"

#: Unidad de la partida global "Micelaneos" (alias canónico de "global" en core.contracts.unidades).
UNIDAD_SUMA_GLOBAL = "sg"
#: El tubo corrugado se cotiza por tubo de 30 m, no por metro (el PDF anota "3*99,75").
METROS_POR_TUBO = Decimal("30")
#: (presupuesto, renglón) del tubo corrugado en cada PDF.
RENGLONES_TUBO: frozenset[tuple[int, int]] = frozenset({(1, 3), (2, 5)})
#: (presupuesto, renglón) de la guaya guía: la única herramienta reutilizable de los dos PDF.
RENGLONES_HERRAMIENTA: frozenset[tuple[int, int]] = frozenset({(1, 12), (2, 26)})
#: Factor con el que el PDF imputa esa herramienta: completa, a un solo presupuesto.
DEPRECIACION_HERRAMIENTA = Decimal("1.00")
#: Prefijo de la línea que reproduce un total impreso contradictorio (mecanismo 2 del módulo).
#: No contiene "R6" a propósito: en este repositorio "R6" es la regla de verificación
#: `CriterioDepreciacion` (CLAUDE.md §7) y esta marca se persiste como descripción de insumo, así
#: que un "R6" aquí se leería como esa regla en el informe de auditoría de la Sesión M1.3.
MARCA_AJUSTE = "Ajuste total impreso"
#: Regla trazable del tubo corrugado del presupuesto 2 (Sesión M1.3, ver `item_de`): una referencia
#: pura al parámetro `cantidad_computos` ya declarado en el ítem. No es una fórmula geométrica (R1
#: no exige que lo sea: solo compara `regla` evaluada contra `cantidad`), es la forma más directa de
#: declarar "esta cantidad debe coincidir con la de Computos metricos" sin inventar un mecanismo
#: nuevo en `core/`.
REGLA_TUBO_CORRUGADO = "cantidad_computos"


# ---------------------------------------------------------------------------------------------
# Del fixture a los contratos: composiciones e ítems de cómputo
# ---------------------------------------------------------------------------------------------


def codigo_partida(numero: int, renglon: int) -> str:
    """`(2, 5)` -> `"TC-P2-05"`. Los códigos son de este trabajo: el PDF no los trae."""
    return f"TC-P{numero}-{renglon:02d}"


def renglones(numero: int) -> tuple[RenglonPresupuesto, ...]:
    """Los renglones del presupuesto `numero` (1 o 2), tal como los transcribe el fixture."""
    try:
        return PRESUPUESTOS[numero]
    except KeyError:
        raise ValueError(
            f"no hay presupuesto ARENAZA numero {numero}; los transcritos son "
            f"{sorted(PRESUPUESTOS)}"
        ) from None


def codigos_arenaza(numero: int) -> list[str]:
    """Los códigos `TC-*` del presupuesto, en el orden del PDF."""
    return [codigo_partida(numero, fila.renglon) for fila in renglones(numero)]


def _unidad(renglon: RenglonPresupuesto) -> str:
    """La unidad impresa; suma global cuando el PDF no imprime ninguna (mecanismo 3)."""
    return renglon.unidad or UNIDAD_SUMA_GLOBAL


def _cantidad(renglon: RenglonPresupuesto) -> Decimal:
    """La cantidad impresa; 1 suma global cuando el PDF no la descompone (mecanismo 3)."""
    return renglon.cantidad if renglon.cantidad is not None else Decimal("1")


def _precio(renglon: RenglonPresupuesto) -> Decimal:
    """El precio unitario impreso; el total cuando el PDF no lo descompone (mecanismo 3)."""
    return renglon.precio_unitario if renglon.precio_unitario is not None else renglon.total


def _lineas_impresas(
    numero: int, renglon: RenglonPresupuesto
) -> tuple[tuple[LineaMaterial, ...], tuple[LineaEquipo, ...]]:
    """Las líneas del APU que salen directamente de lo impreso, sin ajuste todavía."""
    clave = (numero, renglon.renglon)
    if clave in RENGLONES_TUBO:  # mecanismo 1: precio por tubo de 30 m
        material = LineaMaterial(
            f"{renglon.descripcion} (tubo de {METROS_POR_TUBO:f} m)",
            "pieza",
            Decimal("1") / METROS_POR_TUBO,
            _precio(renglon),
        )
        return (material,), ()
    if clave in RENGLONES_HERRAMIENTA:  # mecanismo 4: herramienta reutilizable
        equipo = LineaEquipo(
            renglon.descripcion, Decimal("1"), _precio(renglon), DEPRECIACION_HERRAMIENTA
        )
        return (), (equipo,)
    material = LineaMaterial(
        renglon.descripcion, _unidad(renglon), Decimal("1"), _precio(renglon)
    )
    return (material,), ()


def _linea_ajuste(
    renglon: RenglonPresupuesto, composicion: ComposicionAPU
) -> LineaMaterial | None:
    """Mecanismo 2: la diferencia entre el total impreso y lo que da la composición, declarada.

    `None` cuando no hace falta (los 38 renglones que sí cierran). Si el total impreso fuera menor
    que la composición haría falta una línea negativa, que los contratos prohíben con razón
    (`cantidad` y `precio` no pueden ser negativos): se detiene con un error explícito en vez de
    inventar un mecanismo silencioso. Ningún renglón de los dos PDF está en ese caso.

    La línea lleva `unidad = "sg"` (suma global) y no la del renglón: es un artefacto de
    reproducción, no un insumo cotizado por pieza, y no debe entrar en ningún contraste de precios
    (ver el docstring del módulo, mecanismo 2). La unidad no interviene en el cálculo del motor.
    """
    objetivo = renglon.total / _cantidad(renglon)
    calculado = calcular_apu(composicion, PARAMETROS_ARENAZA).precio_unitario
    diferencia = objetivo - calculado
    if diferencia == 0:
        return None
    if diferencia < 0:
        raise ValueError(
            f"el renglon {renglon.origen} imprime un total ({renglon.total}) menor que el que da "
            f"su composicion ({calculado * _cantidad(renglon)}): haria falta una linea negativa, "
            "que los contratos prohiben. Declare un mecanismo para este renglon en seed_telecom.py"
        )
    return LineaMaterial(
        f"{MARCA_AJUSTE}: el PDF imprime {renglon.total} y cantidad x precio unitario da "
        f"{_cantidad(renglon) * _precio(renglon)} ({renglon.origen})",
        UNIDAD_SUMA_GLOBAL,
        Decimal("1"),
        diferencia,
    )


def composicion_de(numero: int, renglon: RenglonPresupuesto) -> ComposicionAPU:
    """El APU de un renglón: una unidad de partida al precio impreso, más su ajuste si lo lleva."""
    materiales, equipos = _lineas_impresas(numero, renglon)
    composicion = ComposicionAPU(
        codigo_partida=codigo_partida(numero, renglon.renglon),
        descripcion=renglon.descripcion,
        unidad=_unidad(renglon),
        rendimiento=RENDIMIENTO,
        materiales=materiales,
        equipos=equipos,
    )
    ajuste = _linea_ajuste(renglon, composicion)
    if ajuste is None:
        return composicion
    return replace(composicion, materiales=(*materiales, ajuste))


def composiciones_arenaza(numero: int) -> dict[str, ComposicionAPU]:
    """Los APU del presupuesto, armados desde el fixture. Sin mano de obra: ver `con_mano_obra`."""
    return {
        codigo_partida(numero, fila.renglon): composicion_de(numero, fila)
        for fila in renglones(numero)
    }


def item_de(numero: int, renglon: RenglonPresupuesto) -> ItemComputo:
    """La cantidad de obra del renglón, trazable a su fila del PDF (`<pdf>:<pagina>:<renglon>`).

    `origen_tipo` es TABULAR: la fuente es la tabla "Presupuesto" del PDF, no una regla ni un
    modelo. El tubo corrugado del presupuesto 2 declara además, en `parametros`, las dos cantidades
    que el PDF se contradice a sí mismo (80 m en "Computos metricos", 90 m en "Presupuesto").

    **Excepción declarada para la Sesión M1.3.** Los demás renglones no llevan `regla` porque su
    cantidad no se deriva de nada: se transcribe. Este renglón sí la lleva
    (`REGLA_TUBO_CORRUGADO = "cantidad_computos"`) para que la regla de verificación R1
    (`TrazabilidadGeometrica`) compare la cantidad impresa en "Presupuesto" (90, la que queda en
    `cantidad`) contra la de "Computos metricos" (80, en `parametros`) y emita el hallazgo con este
    `origen_id`. No se inventa un mecanismo nuevo en `core/`: R1 ya compara cualquier `regla`
    declarada contra su evaluación, sin exigir que sea una fórmula geométrica (CLAUDE.md §7, R1);
    aquí la "regla" es la referencia directa al parámetro que ya viaja con el ítem.
    """
    especificaciones = {CLAVE_UNIDAD_ORIGINAL: renglon.unidad} if renglon.unidad else {}
    parametros: dict[str, Decimal] = {}
    regla: str | None = None
    if renglon.origen == arenaza.TUBO_CORRUGADO["origen_presupuesto"]:
        parametros = {
            "cantidad_computos": arenaza.TUBO_CORRUGADO["cantidad_computos"],
            "cantidad_presupuesto": arenaza.TUBO_CORRUGADO["cantidad_presupuesto"],
        }
        regla = REGLA_TUBO_CORRUGADO
    return ItemComputo(
        codigo_partida=codigo_partida(numero, renglon.renglon),
        descripcion=renglon.descripcion,
        unidad=_unidad(renglon),
        cantidad=_cantidad(renglon),
        origen_id=renglon.origen,
        origen_tipo=OrigenTipo.TABULAR,
        dominio=Dominio.TELECOM,
        regla=regla,
        parametros=parametros,
        especificaciones=especificaciones,
    )


def items_arenaza(numero: int) -> list[ItemComputo]:
    """Las cantidades de obra del presupuesto, en el orden del PDF."""
    return [item_de(numero, fila) for fila in renglones(numero)]


# ---------------------------------------------------------------------------------------------
# La política de mano de obra del PDF: opción 1 del hallazgo 1 de la bitácora I5-telecom
# ---------------------------------------------------------------------------------------------


def con_mano_obra(
    composicion: ComposicionAPU,
    fraccion: Decimal = FRACCION_MANO_OBRA,
    parametros: ParametrosCosto = PARAMETROS_ARENAZA,
) -> ComposicionAPU:
    """Añade la `LineaManoObra` sintética que representa la política ARENAZA. **Fuera del motor.**

    El motor calcula ``mano_obra = (sum(cantidad x sueldo) x (1 + fcas) + bono x obreros) /
    rendimiento``. Con una sola cuadrilla de un obrero, el sueldo que hace que esa expresión valga
    ``fraccion x costo_directo`` se despeja::

        sueldo = (fraccion x costo_directo x rendimiento - bono) / (1 + fcas)

    El despeje usa los parámetros recibidos, así que la política se cumple también si algún día se
    costea este dominio con FCAS o bono distintos de cero. `core.costing` no cambia: la política se
    resuelve antes de llamarlo (CLAUDE.md §2, principio 4).
    """
    if composicion.mano_obra:
        raise ValueError(
            f"la composicion de {composicion.codigo_partida} ya declara mano de obra: aplicar la "
            "politica encima duplicaria el importe"
        )
    directo = calcular_apu(composicion, parametros).costo_directo
    sueldo = (
        fraccion * directo * composicion.rendimiento - parametros.bono_alimentacion
    ) / (1 + parametros.fcas)
    if sueldo < 0:
        raise ValueError(
            f"el bono de alimentacion ({parametros.bono_alimentacion}) ya supera la mano de obra "
            f"que pide la politica en {composicion.codigo_partida}: no hay sueldo que la cumpla"
        )
    return replace(
        composicion, mano_obra=(LineaManoObra(DESCRIPCION_MANO_OBRA, Decimal("1"), sueldo),)
    )


# ---------------------------------------------------------------------------------------------
# Persistencia: catálogo telecom en SQLite
# ---------------------------------------------------------------------------------------------


def sembrar_telecom(sesion: Session) -> models.Proyecto:
    """Carga proyecto, lista de precios ARENAZA y las 40 partidas TC-*. Idempotente.

    Se persiste el presupuesto **impreso** (materiales y el equipo): la mano de obra sintética es
    política de la capa de catálogo y se aplica al reconstruir, no se guarda.
    """
    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == NOMBRE_PROYECTO)
    ).one_or_none()
    if proyecto is not None:
        return proyecto

    proyecto = models.Proyecto(
        nombre=NOMBRE_PROYECTO,
        descripcion=DESCRIPCION_PROYECTO,
        dominio=str(Dominio.TELECOM),
    )
    lista = models.ListaPrecios(
        nombre=NOMBRE_LISTA,
        moneda=MONEDA,
        fecha_vigencia=FECHA_ARENAZA,
        origen=ORIGEN_LISTA,
    )
    sesion.add_all((proyecto, lista))
    sesion.flush()

    catalogo = Catalogo(sesion)
    for numero in sorted(PRESUPUESTOS):
        for composicion in composiciones_arenaza(numero).values():
            catalogo.cargar_composicion(composicion, lista, Dominio.TELECOM, FECHA_ARENAZA)

    sesion.commit()
    return proyecto


def lista_arenaza(sesion: Session) -> models.ListaPrecios:
    """La lista de precios ARENAZA. Se busca por nombre y no por fecha para no depender de qué
    otras listas (civil, MaPreX) convivan en la misma base."""
    lista = sesion.scalars(
        select(models.ListaPrecios).where(models.ListaPrecios.nombre == NOMBRE_LISTA)
    ).one_or_none()
    if lista is None:
        raise CatalogoIncompleto(
            f"no hay lista de precios {NOMBRE_LISTA!r} en la base: corra sembrar_telecom primero"
        )
    return lista


def composiciones_desde_catalogo(sesion: Session, numero: int) -> dict[str, ComposicionAPU]:
    """Reconstruye los APU del presupuesto desde SQLite, con los precios de la lista ARENAZA."""
    catalogo = Catalogo(sesion)
    lista = lista_arenaza(sesion)
    return {
        codigo: catalogo.composicion(codigo, fecha=FECHA_ARENAZA, lista=lista)
        for codigo in codigos_arenaza(numero)
    }


def presupuesto_arenaza(
    sesion: Session,
    numero: int,
    *,
    con_mano_obra_sintetica: bool = False,
    parametros: ParametrosCosto = PARAMETROS_ARENAZA,
) -> Presupuesto:
    """El presupuesto ARENAZA completo, reconstruido desde el catálogo y valorado por el motor.

    Con `con_mano_obra_sintetica` se aplica antes la política del PDF (50 % del total). Esta es la
    función que reutiliza la Sesión M1.3 para auditar el presupuesto telecom.
    """
    composiciones = composiciones_desde_catalogo(sesion, numero)
    if con_mano_obra_sintetica:
        composiciones = {
            codigo: con_mano_obra(composicion, parametros=parametros)
            for codigo, composicion in composiciones.items()
        }
    return generar_presupuesto(
        items_arenaza(numero),
        composiciones,
        parametros,
        codigo=CODIGOS_PRESUPUESTO[numero],
        fecha=FECHA_ARENAZA,
        moneda=MONEDA,
    )


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--db",
        default=RUTA_POR_DEFECTO,
        help=f"ruta del archivo SQLite (por defecto {RUTA_POR_DEFECTO})",
    )
    analizador.add_argument(
        "--reiniciar", action="store_true", help="borra el esquema antes de crearlo de nuevo"
    )
    argumentos = analizador.parse_args(argv)

    ruta = Path(argumentos.db)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        if argumentos.reiniciar:
            models.Base.metadata.drop_all(motor)
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar_telecom(sesion)
            _imprimir_resumen(sesion, ruta, proyecto)
    finally:
        motor.dispose()
    return 0


def _imprimir_resumen(sesion: Session, ruta: Path, proyecto: models.Proyecto) -> None:
    lista = lista_arenaza(sesion)
    print(f"Base de datos: {ruta}")
    print(f"Proyecto: {proyecto.nombre} ({proyecto.dominio})")
    print(
        f"Lista de precios: {lista.nombre} ({lista.moneda}, vigente desde {lista.fecha_vigencia})"
    )

    for numero in sorted(PRESUPUESTOS):
        presupuesto = presupuesto_arenaza(sesion, numero)
        con_mo = presupuesto_arenaza(sesion, numero, con_mano_obra_sintetica=True)
        impreso = TOTALES[numero]
        print(
            f"Presupuesto {presupuesto.codigo} ({len(presupuesto.partidas)} partidas): "
            f"reproducido {presupuesto.total:.2f} {MONEDA} | impreso en el PDF {impreso:.2f} "
            f"{MONEDA} | diferencia {presupuesto.total - impreso:.2f}"
        )
        print(
            f"  con la mano de obra del PDF ({FRACCION_MANO_OBRA:.0%} del total): "
            f"{con_mo.total:.2f} {MONEDA}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
