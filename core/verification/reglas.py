"""Las siete reglas de verificación de consistencia (NORMAS.md §7).

Cada regla es una clase `ReglaVerificacion` que recibe un `Presupuesto` y devuelve una lista de
`Hallazgo`. Ninguna lanza excepciones por datos. A una regla que le falta un dato (un parámetro
ausente, una referencia de balance rota) la informa como INFO «regla no evaluable» (RF‑23, UC‑05
flujo 3a); un dato erróneo (sintaxis, valor que no es `Decimal`, desborde) es un ERROR; R2 y R7
sin plan de trabajo se declaran «no aplicables» (UC‑05 flujo 2a). Ningún hallazgo interrumpe a las
demás reglas.

Ninguna regla conoce un dominio. No hay aquí un nombre de partida, una unidad concreta ni un código
del caso de estudio: todo lo que una regla necesita saber del dominio se lo dice el propio
presupuesto (la expresión de `ItemComputo.regla`, las claves de `especificaciones`, las unidades que
normaliza `core.contracts.unidades`). Esa es la hipótesis central de la investigación: los
adaptadores cambian, el núcleo no.

**Convención del `impacto`.** Es siempre una magnitud no negativa, en la moneda del presupuesto
cuando la regla puede cuantificar dinero, y `None` cuando no tiene sentido cuantificarlo (R3, R4,
R6). El sentido de la desviación no va en el signo sino en `valor_observado` y `valor_esperado`, que
toda regla cuantitativa llena.

**Atribución a la partida (INV‑095, expediente C5.1).** `Hallazgo` no lleva código de partida y un
`origen_id` puede producir varias partidas (`OrigenTipo.REGLA`: el objeto paramétrico), así que el
informe no puede deducir la partida de un hallazgo por su origen. Las reglas cuyos hallazgos nacen
de una partida (R1, R3, R4, R5 y R7) la declaran con `atribuir` (`ReglaAtribuible`), y su `evaluar`
devuelve esos mismos hallazgos sin la partida. R2 (el presupuesto completo) y R6 (sus `origen_ids`
ya son códigos de partida) no la necesitan.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import ClassVar, Protocol, runtime_checkable

from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto, PuntoCurva
from core.contracts.unidades import unidades_equivalentes
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad
from core.verification.directivas import (
    CLAVE_BALANCE,
    CLAVE_TOLERANCIA,
    CLAVE_UNIDAD_ORIGINAL,
    codigos_en_etiqueta,
    es_directiva,
)
from core.verification.expresiones import (
    ExpresionInvalida,
    ParametroFaltante,
    codigos_de,
    evaluar,
    nombres_de,
    sustituir_codigos,
)
from core.verification.texto import (
    Componente,
    Magnitud,
    componentes,
    formatear_decimal,
    magnitudes_de,
    normalizar_texto,
)

__all__ = [
    "NO_APLICABLE",
    "REGLAS",
    "REGLA_NO_EVALUABLE",
    "Atribucion",
    "BalanceVolumetrico",
    "CierreCurvaInversion",
    "CoherenciaDimensional",
    "ConciliacionPresupuestoPlan",
    "CorrespondenciaEspecificaciones",
    "CriterioDepreciacion",
    "ReglaAtribuible",
    "TrazabilidadGeometrica",
]

_CERO = Decimal(0)

#: Prefijo de un hallazgo INFO de una regla a la que le falta un dato para evaluarse: un parámetro
#: ausente o una referencia no resuelta (RF‑23, UC‑05 flujo 3a). Un dato erróneo (sintaxis, valor
#: que no es `Decimal`, desborde) no es «no evaluable»: es un ERROR.
REGLA_NO_EVALUABLE = "regla no evaluable"
#: Con qué se declaran R2 y R7 cuando el presupuesto no trae plan de trabajo (UC‑05 flujo 2a).
NO_APLICABLE = "no aplicable"

#: Un hallazgo con el código de la partida que lo produjo, o `None` si no es de una partida.
Atribucion = tuple[Hallazgo, str | None]


@runtime_checkable
class ReglaAtribuible(Protocol):
    """Una regla que declara la partida de cada hallazgo que emite (INV‑095).

    No es un contrato de `core/contracts/`: lo implementan las reglas de este módulo y lo consulta
    `core.verification.informe.auditar`. Una regla que no lo implementa se atribuye por el índice
    de orígenes del informe.

    `auditar` usa `atribuir` en lugar de `evaluar`, así que los dos tienen que decir lo mismo: los
    hallazgos de `atribuir`, sin la partida, son exactamente los de `evaluar`, en el mismo orden.
    Quien redefina `evaluar` en una subclase redefine también `atribuir`.
    """

    def atribuir(self, presupuesto: Presupuesto) -> list[Atribucion]:
        """Los hallazgos de `evaluar`, en el mismo orden, cada uno con su partida."""
        ...


def _sin_partida(atribuciones: Iterable[Atribucion]) -> list[Hallazgo]:
    return [hallazgo for hallazgo, _ in atribuciones]


def _num(valor: Decimal) -> str:
    """Un número tal como se cita dentro de la descripción de un hallazgo (sin perder dígitos)."""
    return formatear_decimal(valor)


def _dentro_de_tolerancia(observado: Decimal, esperado: Decimal, relativa: Decimal) -> bool:
    diferencia = abs(observado - esperado)
    if esperado == _CERO:
        return diferencia == _CERO
    return diferencia <= abs(esperado) * relativa


def _cantidades_por_codigo(presupuesto: Presupuesto) -> dict[str, Decimal]:
    """Cantidad total de cada partida: una partida puede venir de varios ítems de cómputo."""
    totales: dict[str, Decimal] = defaultdict(lambda: _CERO)
    for partida in presupuesto.partidas:
        totales[partida.item.codigo_partida] += partida.item.cantidad
    return dict(totales)


def _origenes_por_codigo(presupuesto: Presupuesto) -> dict[str, tuple[str, ...]]:
    origenes: dict[str, list[str]] = defaultdict(list)
    for partida in presupuesto.partidas:
        origenes[partida.item.codigo_partida].append(partida.item.origen_id)
    return {codigo: tuple(ids) for codigo, ids in origenes.items()}


def _sin_repetir(valores: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(valores))


# ---------------------------------------------------------------------------------------------
# R1
# ---------------------------------------------------------------------------------------------


class TrazabilidadGeometrica(ReglaVerificacion):
    """R1. Toda cantidad deriva de una regla declarada y coincide con su evaluación.

    Una cantidad transcrita a mano (`OrigenTipo.MANUAL`) sin regla no es un error, pero tampoco es
    trazable: se advierte. Las demás procedencias (IFC, tabular, CSV) sí son trazables por su
    `origen_id`, aunque no declaren expresión.
    """

    codigo: ClassVar[str] = "R1"
    nombre: ClassVar[str] = "Trazabilidad geometrica"

    def __init__(self, tolerancia_relativa: Decimal = Decimal("0.001")) -> None:
        self.tolerancia_relativa = tolerancia_relativa

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _sin_partida(self.atribuir(presupuesto))

    def atribuir(self, presupuesto: Presupuesto) -> list[Atribucion]:
        hallazgos: list[Atribucion] = []
        for partida in presupuesto.partidas:
            item = partida.item
            if item.regla:
                hallazgos.extend(
                    (hallazgo, item.codigo_partida) for hallazgo in self._verificar_regla(partida)
                )
            elif item.origen_tipo is OrigenTipo.MANUAL:
                manual = Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.ADVERTENCIA,
                    descripcion=(
                        f"la cantidad de {item.codigo_partida} ({_num(item.cantidad)} "
                        f"{item.unidad}) es manual y no declara la regla que la produjo: "
                        "no es derivable ni reproducible"
                    ),
                    origen_ids=(item.origen_id,),
                    valor_observado=item.cantidad,
                )
                hallazgos.append((manual, item.codigo_partida))
        return hallazgos

    def _verificar_regla(self, partida: PartidaPresupuestada) -> list[Hallazgo]:
        item = partida.item
        try:
            esperado = evaluar(item.regla or "", item.parametros)
        except ParametroFaltante as error:
            # RF‑23, UC‑05 3a: falta un dato para evaluar la regla; se informa y no bloquea.
            return [
                Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.INFO,
                    descripcion=(
                        f"{REGLA_NO_EVALUABLE}: la regla declarada por {item.codigo_partida} "
                        f"({item.regla!r}) no se puede evaluar: falta el parametro {error}"
                    ),
                    origen_ids=(item.origen_id,),
                    valor_observado=item.cantidad,
                )
            ]
        except ExpresionInvalida as error:
            # Un dato erróneo (sintaxis, valor que no es `Decimal`, desborde): el cómputo no es
            # trazable y el presupuesto no cumple.
            return [
                Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"la regla declarada por {item.codigo_partida} no se puede evaluar "
                        f"({item.regla!r}): {error}"
                    ),
                    origen_ids=(item.origen_id,),
                    valor_observado=item.cantidad,
                )
            ]

        if _dentro_de_tolerancia(item.cantidad, esperado, self.tolerancia_relativa):
            return []

        diferencia = item.cantidad - esperado
        return [
            Hallazgo(
                regla=self.codigo,
                severidad=Severidad.ERROR,
                descripcion=(
                    f"la cantidad de {item.codigo_partida} es {_num(item.cantidad)} "
                    f"{item.unidad}, pero su regla {item.regla!r} evaluada con los parametros "
                    f"declarados da {_num(esperado)} {item.unidad}"
                ),
                impacto=abs(diferencia) * partida.resultado.precio_unitario,
                origen_ids=(item.origen_id,),
                valor_observado=item.cantidad,
                valor_esperado=esperado,
            )
        ]


# ---------------------------------------------------------------------------------------------
# R2
# ---------------------------------------------------------------------------------------------


class CierreCurvaInversion(ReglaVerificacion):
    """R2. El acumulado de la curva de inversión es exactamente el total del presupuesto."""

    codigo: ClassVar[str] = "R2"
    nombre: ClassVar[str] = "Cierre de la curva de inversion"

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        if not presupuesto.curva:
            return [
                Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.INFO,
                    descripcion=(
                        f"R2 {NO_APLICABLE}: el presupuesto no declara curva de inversion, "
                        "no hay cierre que verificar"
                    ),
                )
            ]

        hallazgos: list[Hallazgo] = []
        corrido = _CERO
        for punto in presupuesto.curva:
            corrido += punto.monto
            if punto.acumulado != corrido:
                hallazgos.append(
                    Hallazgo(
                        regla=self.codigo,
                        severidad=Severidad.ERROR,
                        descripcion=(
                            f"el acumulado del periodo {punto.periodo!r} es "
                            f"{_num(punto.acumulado)} y la suma corrida de los montos da "
                            f"{_num(corrido)}"
                        ),
                        impacto=abs(punto.acumulado - corrido),
                        valor_observado=punto.acumulado,
                        valor_esperado=corrido,
                    )
                )

        diferencia = presupuesto.total - presupuesto.total_curva
        if diferencia != _CERO:
            hallazgos.append(
                Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.CRITICO,
                    descripcion=(
                        f"la curva de inversion cierra en {_num(presupuesto.total_curva)} "
                        f"{presupuesto.moneda} y el presupuesto totaliza "
                        f"{_num(presupuesto.total)} {presupuesto.moneda}: quedan "
                        f"{_num(abs(diferencia))} {presupuesto.moneda} sin conciliar"
                    ),
                    impacto=abs(diferencia),
                    origen_ids=(),
                    valor_observado=presupuesto.total_curva,
                    valor_esperado=presupuesto.total,
                )
            )
        return hallazgos


# ---------------------------------------------------------------------------------------------
# R3
# ---------------------------------------------------------------------------------------------


class CoherenciaDimensional(ReglaVerificacion):
    """R3. La unidad del cómputo equivale a la unidad del APU que lo costea."""

    codigo: ClassVar[str] = "R3"
    nombre: ClassVar[str] = "Coherencia dimensional"

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _sin_partida(self.atribuir(presupuesto))

    def atribuir(self, presupuesto: Presupuesto) -> list[Atribucion]:
        hallazgos: list[Atribucion] = []
        for partida in presupuesto.partidas:
            item, apu = partida.item, partida.apu
            if unidades_equivalentes(item.unidad, apu.unidad):
                continue
            hallazgo = Hallazgo(
                regla=self.codigo,
                severidad=Severidad.ERROR,
                descripcion=(
                    f"la partida {item.codigo_partida} se computa en {self._citar(item)} y su "
                    f"APU esta definido en {apu.unidad!r}: no son la misma unidad, el precio "
                    "unitario no aplica a esa cantidad"
                ),
                origen_ids=(item.origen_id,),
            )
            hallazgos.append((hallazgo, item.codigo_partida))
        return hallazgos

    @staticmethod
    def _citar(item: ItemComputo) -> str:
        original = item.especificaciones.get(CLAVE_UNIDAD_ORIGINAL)
        if original and original != item.unidad:
            return f"{original!r} (normalizada {item.unidad!r})"
        return repr(item.unidad)


# ---------------------------------------------------------------------------------------------
# R4
# ---------------------------------------------------------------------------------------------


class CorrespondenciaEspecificaciones(ReglaVerificacion):
    """R4. Las especificaciones del cómputo se reconocen en el texto del APU.

    Una especificación que no aparece en el texto y que además contradice un valor del texto para
    la misma unidad (`3/4 pulg` frente a `4 pulg`) es un error; una que simplemente no aparece se
    informa como no contrastable, porque el texto del APU puede callar un atributo sin equivocarse.

    **Comparación normalizada (SF‑E5, hallazgo A‑2).** «Aparecer» es que la secuencia de palabras y
    cantidades de la especificación (`core.verification.texto.componentes`) esté, seguida y en
    orden, dentro de la de una descripción del APU, con las cantidades comparadas por su `Decimal`:
    `4 pulg` no aparece en `3/4 pulg`, ni `2` en `1/2`, ni `6` en `16`, ni `1/2` en `1 1/2`, y
    `0.5 pulg` sí aparece en `1/2 pulg`. El corpus es el APU (su descripción y la de cada línea),
    **no** la descripción del propio ítem: la escribe quien declaró la especificación y no puede
    confirmarla.
    """

    codigo: ClassVar[str] = "R4"
    nombre: ClassVar[str] = "Correspondencia de especificaciones"

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _sin_partida(self.atribuir(presupuesto))

    def atribuir(self, presupuesto: Presupuesto) -> list[Atribucion]:
        hallazgos: list[Atribucion] = []
        for partida in presupuesto.partidas:
            corpus = self._corpus(partida)
            magnitudes_corpus = [m for segmento in corpus for m in magnitudes_de(segmento)]
            for clave, valor in partida.item.especificaciones.items():
                if es_directiva(clave):
                    continue
                hallazgo = self._verificar(partida, clave, valor, corpus, magnitudes_corpus)
                if hallazgo is not None:
                    hallazgos.append((hallazgo, partida.item.codigo_partida))
        return hallazgos

    @staticmethod
    def _corpus(partida: PartidaPresupuestada) -> list[list[Componente]]:
        """Cada descripción del APU como secuencia comparable, por separado: una especificación
        no se reconoce, ni una cantidad toma su unidad, a caballo entre dos líneas."""
        apu = partida.apu
        descripciones = [
            apu.descripcion,
            *(linea.descripcion for linea in apu.materiales),
            *(linea.descripcion for linea in apu.equipos),
            *(linea.descripcion for linea in apu.mano_obra),
        ]
        return [componentes(descripcion) for descripcion in descripciones]

    def _verificar(
        self,
        partida: PartidaPresupuestada,
        clave: str,
        valor: str,
        corpus: Sequence[Sequence[Componente]],
        magnitudes_corpus: Sequence[Magnitud],
    ) -> Hallazgo | None:
        item = partida.item
        normalizado = normalizar_texto(valor)
        if not normalizado:
            return None
        declarado = componentes(normalizado)
        if declarado and any(_aparece(declarado, segmento) for segmento in corpus):
            return None

        contradicciones = [
            (magnitud.texto, en_texto.texto, magnitud.unidad)
            for magnitud in magnitudes_de(declarado)
            for en_texto in magnitudes_corpus
            if en_texto.unidad == magnitud.unidad and en_texto.valor != magnitud.valor
        ]
        if not contradicciones:
            return Hallazgo(
                regla=self.codigo,
                severidad=Severidad.INFO,
                descripcion=(
                    f"la especificacion {clave!r} = {normalizado!r} de {item.codigo_partida} no "
                    "aparece en el texto de su APU: no es contrastable"
                ),
                origen_ids=(item.origen_id,),
            )

        declarado, en_texto, unidad = contradicciones[0]
        return Hallazgo(
            regla=self.codigo,
            severidad=Severidad.ERROR,
            descripcion=(
                f"la especificacion {clave!r} de {item.codigo_partida} declara "
                f"{declarado} {unidad} y el texto de su APU dice {en_texto} {unidad}: "
                f"contradiccion entre el computo y la partida que lo costea"
            ),
            origen_ids=(item.origen_id,),
        )


def _aparece(buscada: Sequence[Componente], texto: Sequence[Componente]) -> bool:
    """True si `buscada` está, seguida y en orden, dentro de `texto` (comparando por `clave`)."""
    claves = [componente.clave for componente in buscada]
    del_texto = [componente.clave for componente in texto]
    largo = len(claves)
    return any(
        del_texto[inicio : inicio + largo] == claves for inicio in range(len(del_texto) - largo + 1)
    )


# ---------------------------------------------------------------------------------------------
# R5
# ---------------------------------------------------------------------------------------------


class BalanceVolumetrico(ReglaVerificacion):
    """R5. La cantidad de una partida cuadra con el balance que declara su directiva `_balance`.

    El balance se escribe en términos de códigos de partida entre llaves; el núcleo los sustituye
    por las cantidades del presupuesto y evalúa la expresión. Los nombres que queden (constantes
    del cómputo) se toman de `ItemComputo.parametros`.
    """

    codigo: ClassVar[str] = "R5"
    nombre: ClassVar[str] = "Balance volumetrico"

    def __init__(self, tolerancia_relativa: Decimal = Decimal("0.05")) -> None:
        self.tolerancia_relativa = tolerancia_relativa

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _sin_partida(self.atribuir(presupuesto))

    def atribuir(self, presupuesto: Presupuesto) -> list[Atribucion]:
        cantidades = _cantidades_por_codigo(presupuesto)
        origenes = _origenes_por_codigo(presupuesto)
        hallazgos: list[Atribucion] = []
        for partida in presupuesto.partidas:
            balance = partida.item.especificaciones.get(CLAVE_BALANCE)
            if balance:
                hallazgos.extend(
                    (hallazgo, partida.item.codigo_partida)
                    for hallazgo in self._verificar(partida, balance, cantidades, origenes)
                )
        return hallazgos

    def _verificar(
        self,
        partida: PartidaPresupuestada,
        balance: str,
        cantidades: Mapping[str, Decimal],
        origenes: Mapping[str, tuple[str, ...]],
    ) -> list[Hallazgo]:
        item = partida.item
        referenciados = codigos_de(balance)
        ids = _sin_repetir(
            (item.origen_id, *(o for codigo in referenciados for o in origenes.get(codigo, ())))
        )

        try:
            expandido = sustituir_codigos(balance, cantidades)
        except ParametroFaltante as error:
            return [
                self._inevaluable(
                    item,
                    ids,
                    f"referencia no resuelta: el balance {balance!r} cita la partida "
                    f"{error.args[0]!r}, que no esta en el presupuesto",
                    Severidad.INFO,
                )
            ]

        try:
            valores = {
                nombre: item.parametros[nombre]
                for nombre in nombres_de(expandido)
                if nombre in item.parametros
            }
            esperado = evaluar(expandido, valores)
        except ParametroFaltante as error:
            return [
                self._inevaluable(
                    item,
                    ids,
                    f"el balance {balance!r} no se puede evaluar: falta el parametro {error}",
                    Severidad.INFO,
                )
            ]
        except ExpresionInvalida as error:
            return [
                self._inevaluable(
                    item,
                    ids,
                    f"el balance {balance!r} no se puede evaluar: {error}",
                    Severidad.ERROR,
                )
            ]

        observado = cantidades[item.codigo_partida]
        tolerancia, aviso = self._tolerancia(item)
        hallazgos = list(aviso)
        if _dentro_de_tolerancia(observado, esperado, tolerancia):
            return hallazgos

        diferencia = observado - esperado
        hallazgos.append(
            Hallazgo(
                regla=self.codigo,
                severidad=Severidad.ERROR,
                descripcion=(
                    f"la partida {item.codigo_partida} declara {_num(observado)} {item.unidad} y "
                    f"su balance {balance!r} da {_num(esperado)} {item.unidad} con las cantidades "
                    f"del presupuesto (tolerancia {_num(tolerancia * 100)} %)"
                ),
                impacto=abs(diferencia) * partida.resultado.precio_unitario,
                origen_ids=ids,
                valor_observado=observado,
                valor_esperado=esperado,
            )
        )
        return hallazgos

    def _inevaluable(
        self, item: ItemComputo, ids: tuple[str, ...], detalle: str, severidad: Severidad
    ) -> Hallazgo:
        """RF‑23: un dato ausente es INFO «regla no evaluable»; uno erróneo, ERROR. Las demás
        reglas siguen en ambos casos."""
        prefijo = f"{REGLA_NO_EVALUABLE}: " if severidad is Severidad.INFO else ""
        return Hallazgo(
            regla=self.codigo,
            severidad=severidad,
            descripcion=f"{prefijo}{item.codigo_partida}: {detalle}",
            origen_ids=ids,
            valor_observado=item.cantidad,
        )

    def _tolerancia(self, item: ItemComputo) -> tuple[Decimal, list[Hallazgo]]:
        declarada = item.especificaciones.get(CLAVE_TOLERANCIA)
        if declarada is None:
            return self.tolerancia_relativa, []
        try:
            tolerancia = Decimal(declarada)
        except InvalidOperation:
            tolerancia = None
        # `Decimal("nan")` y `Decimal("Infinity")` no lanzan `InvalidOperation` al construirse:
        # fallan despues, al comparar. Una tolerancia negativa tampoco lanza, pero vuelve la
        # comparacion de `_dentro_de_tolerancia` siempre falsa. Las tres son datos invalidos y
        # caen al mismo aviso que la tolerancia no numerica.
        if tolerancia is None or not tolerancia.is_finite() or tolerancia < _CERO:
            aviso = Hallazgo(
                regla=self.codigo,
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"{item.codigo_partida} declara una tolerancia de balance no numerica "
                    f"({declarada!r}); se usa la del sistema ({_num(self.tolerancia_relativa)})"
                ),
                origen_ids=(item.origen_id,),
            )
            return self.tolerancia_relativa, [aviso]
        return tolerancia, []


# ---------------------------------------------------------------------------------------------
# R6
# ---------------------------------------------------------------------------------------------


class CriterioDepreciacion(ReglaVerificacion):
    """R6. Un mismo insumo lleva el mismo factor de depreciación en todos los APU.

    El contrato no tiene dónde declarar el criterio de amortización que justifica cada factor
    (insuficiencia registrada en la bitácora de la Sesión I4), así que la regla verifica lo que sí
    puede: que el factor sea único por insumo. Los `origen_ids` listan primero las partidas del
    factor minoritario, que son las candidatas a corregir.
    """

    codigo: ClassVar[str] = "R6"
    nombre: ClassVar[str] = "Criterio de depreciacion"

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        factores: dict[str, dict[Decimal, list[str]]] = defaultdict(lambda: defaultdict(list))
        for partida in presupuesto.partidas:
            for linea in partida.apu.equipos:
                insumo = normalizar_texto(linea.descripcion)
                factores[insumo][linea.depreciacion].append(partida.apu.codigo_partida)

        hallazgos: list[Hallazgo] = []
        for insumo, por_factor in factores.items():
            if len(por_factor) < 2:
                continue
            grupos = sorted(por_factor.items(), key=lambda par: (len(par[1]), par[0]))
            detalle = "; ".join(
                f"{factor} en {', '.join(_sin_repetir(codigos))}" for factor, codigos in grupos
            )
            hallazgos.append(
                Hallazgo(
                    regla=self.codigo,
                    severidad=Severidad.ERROR,
                    descripcion=(
                        f"el insumo {insumo!r} lleva {len(por_factor)} factores de depreciacion "
                        f"distintos: {detalle}. El criterio de amortizacion no esta declarado y "
                        "la imputacion no es reproducible"
                    ),
                    origen_ids=_sin_repetir(codigo for _, codigos in grupos for codigo in codigos),
                )
            )
        return hallazgos


# ---------------------------------------------------------------------------------------------
# R7
# ---------------------------------------------------------------------------------------------


class ConciliacionPresupuestoPlan(ReglaVerificacion):
    """R7. Cada monto del plan de trabajo coincide con el monto de las partidas que ejecuta.

    `PuntoCurva` no lleva código de partida (insuficiencia del contrato registrada en la bitácora),
    de modo que el enlace período-partida se establece por los códigos entre corchetes de la
    etiqueta y, si no los hay, por contención de la descripción de la partida en la del período.
    Como una partida puede repartirse en varios períodos y un período cubrir varias partidas, se
    concilian **componentes conexas** del grafo período-partida, no filas sueltas.

    R7 es decisión de diseño de este proyecto (las Bases del anteproyecto listan cinco reglas); se
    valida con el tutor en la Sesión I4.
    """

    codigo: ClassVar[str] = "R7"
    nombre: ClassVar[str] = "Conciliacion presupuesto-plan"

    def __init__(self, tolerancia: Decimal = Decimal("0.01")) -> None:
        self.tolerancia = tolerancia

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _sin_partida(self.atribuir(presupuesto))

    def atribuir(self, presupuesto: Presupuesto) -> list[Atribucion]:
        """Una partida sin período se atribuye a sí misma; una conciliación, a la primera partida
        de su componente en el orden del presupuesto (la descripción las nombra todas); un período
        sin partida y la declaración de «no aplicable», a ninguna."""
        if not presupuesto.curva:
            no_aplicable = Hallazgo(
                regla=self.codigo,
                severidad=Severidad.INFO,
                descripcion=(
                    f"R7 {NO_APLICABLE}: el presupuesto no declara plan de trabajo, no hay "
                    "montos que conciliar con sus partidas"
                ),
            )
            return [(no_aplicable, None)]

        componentes = _componentes_conexas(
            len(presupuesto.curva), len(presupuesto.partidas), self._enlazar(presupuesto)
        )

        hallazgos: list[Atribucion] = []
        for indices_periodo, indices_partida in componentes:
            puntos = [presupuesto.curva[i] for i in indices_periodo]
            partidas = [presupuesto.partidas[j] for j in indices_partida]
            if not partidas:
                hallazgos.extend((h, None) for h in self._periodos_sin_partida(puntos))
            elif not puntos:
                sin_periodo = self._partidas_sin_periodo(partidas)
                hallazgos.extend(
                    (h, partida.item.codigo_partida)
                    for h, partida in zip(sin_periodo, partidas, strict=True)
                )
            else:
                hallazgo = self._conciliar(puntos, partidas, presupuesto.moneda)
                if hallazgo is not None:
                    hallazgos.append((hallazgo, partidas[0].item.codigo_partida))
        return hallazgos

    @staticmethod
    def _enlazar(presupuesto: Presupuesto) -> list[tuple[int, int]]:
        descripciones = [
            (indice, normalizar_texto(partida.item.descripcion))
            for indice, partida in enumerate(presupuesto.partidas)
        ]
        enlaces: list[tuple[int, int]] = []
        for i, punto in enumerate(presupuesto.curva):
            codigos = codigos_en_etiqueta(punto.periodo)
            if codigos:
                enlaces.extend(
                    (i, j)
                    for j, partida in enumerate(presupuesto.partidas)
                    if partida.item.codigo_partida in codigos
                )
                continue
            etiqueta = normalizar_texto(punto.periodo)
            enlaces.extend(
                (i, j)
                for j, descripcion in descripciones
                if descripcion and descripcion in etiqueta
            )
        return enlaces

    def _conciliar(
        self,
        puntos: Sequence[PuntoCurva],
        partidas: Sequence[PartidaPresupuestada],
        moneda: str,
    ) -> Hallazgo | None:
        montos = sum((punto.monto for punto in puntos), _CERO)
        totales = sum((partida.total for partida in partidas), _CERO)
        diferencia = montos - totales
        if abs(diferencia) <= self.tolerancia:
            return None

        etiquetas = ", ".join(repr(punto.periodo) for punto in puntos)
        codigos = ", ".join(_sin_repetir(p.item.codigo_partida for p in partidas))
        return Hallazgo(
            regla=self.codigo,
            severidad=Severidad.ERROR,
            descripcion=(
                f"el plan de trabajo asigna {_num(montos)} {moneda} a {etiquetas} y el "
                f"presupuesto asigna {_num(totales)} {moneda} a {codigos}: difieren en "
                f"{_num(abs(diferencia))} {moneda}"
            ),
            impacto=abs(diferencia),
            origen_ids=_sin_repetir(partida.item.origen_id for partida in partidas),
            valor_observado=montos,
            valor_esperado=totales,
        )

    def _periodos_sin_partida(self, puntos: Sequence[PuntoCurva]) -> list[Hallazgo]:
        return [
            Hallazgo(
                regla=self.codigo,
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"el periodo {punto.periodo!r} del plan de trabajo no enlaza con ninguna "
                    "partida del presupuesto: su monto no es conciliable"
                ),
                impacto=abs(punto.monto),
                valor_observado=punto.monto,
            )
            for punto in puntos
        ]

    def _partidas_sin_periodo(self, partidas: Sequence[PartidaPresupuestada]) -> list[Hallazgo]:
        return [
            Hallazgo(
                regla=self.codigo,
                severidad=Severidad.ADVERTENCIA,
                descripcion=(
                    f"la partida {partida.item.codigo_partida} no aparece en ningun periodo del "
                    "plan de trabajo: su ejecucion no esta planificada"
                ),
                impacto=abs(partida.total),
                origen_ids=(partida.item.origen_id,),
                valor_observado=partida.total,
            )
            for partida in partidas
        ]


def _componentes_conexas(
    total_periodos: int, total_partidas: int, enlaces: Sequence[tuple[int, int]]
) -> list[tuple[list[int], list[int]]]:
    """Agrupa períodos y partidas que comparten al menos un enlace (conjuntos disjuntos)."""
    padre: dict[tuple[str, int], tuple[str, int]] = {
        **{("periodo", i): ("periodo", i) for i in range(total_periodos)},
        **{("partida", j): ("partida", j) for j in range(total_partidas)},
    }

    def buscar(nodo: tuple[str, int]) -> tuple[str, int]:
        while padre[nodo] != nodo:
            padre[nodo] = padre[padre[nodo]]
            nodo = padre[nodo]
        return nodo

    for i, j in enlaces:
        raiz_periodo, raiz_partida = buscar(("periodo", i)), buscar(("partida", j))
        if raiz_periodo != raiz_partida:
            padre[raiz_partida] = raiz_periodo

    componentes: dict[tuple[str, int], tuple[list[int], list[int]]] = {}
    for nodo in padre:
        raiz = buscar(nodo)
        periodos, partidas = componentes.setdefault(raiz, ([], []))
        (periodos if nodo[0] == "periodo" else partidas).append(nodo[1])
    return list(componentes.values())


REGLAS: tuple[ReglaVerificacion, ...] = (
    TrazabilidadGeometrica(),
    CierreCurvaInversion(),
    CoherenciaDimensional(),
    CorrespondenciaEspecificaciones(),
    BalanceVolumetrico(),
    CriterioDepreciacion(),
    ConciliacionPresupuestoPlan(),
)
