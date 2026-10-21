"""Los borradores vivos de la hoja del proyecto en la interfaz nueva (T10, 3b-1; diseno §3.1).

Es el equivalente de `st.session_state["hoja_borrador"]` de la pagina clasica: el `Borrador` que una
persona esta editando vive **en el servidor, en memoria del proceso, ligado a la huella de su
ficha de sesion** (nunca a la ficha misma), no en el navegador. Recargar la pagina o cambiar de
proyecto en la cabecera no lo pierde; reiniciar la API si (costo declarado, D-2). La API corre
como un solo proceso de `uvicorn` sin `--workers` (la prueba 3b-B26 lo vigila): un registro por
proceso basta.

Ciclo de vida y memoria acotada (valores SUPUESTOS a ratificar, D-9):

* como maximo `POR_FICHA` borradores por ficha: el `POR_FICHA + 1` descarta el menos usado;
* como maximo `GLOBALES` en el proceso, y `BYTES_MAXIMOS` estimados (`len(pickle.dumps(borrador))`)
  en total: se expulsa el menos usado hasta bajar (un borrador solo, por grande que sea, se queda);
* el tamano se estima al crear y se vuelve a estimar cada `RE_ESTIMAR_CADA` cambios aceptados
  (la edicion lo hace crecer); si el total pasa el tope se expulsa el menos usado, nunca el que se
  esta editando;
* vence a las `VIGENCIA` sin uso; no hay hilo de fondo, el barrido es perezoso en cada `crear` y en
  cada `obtener`;
* se olvidan al cambiar de caso, cerrar sesion o vencer la ficha (`api.caso_web` llama a
  `olvidar`, `heredar` y `olvidar_todo`).

Cada borrador que sale del registro, por cualquiera de esos caminos, se avisa una vez a cada funcion
de `al_quitar` (3e-2: la importacion de un plano borra asi su carpeta temporal). El aviso llega
FUERA del cerrojo del registro, para que quien lo recibe tome el suyo sin abrazo mortal; un aviso
que falla no deja a los demas sin el suyo ni hace fallar la operacion.

Un borrador de otra ficha **no existe** (`BorradorInexistente`, que la ruta traduce a 404 y no a
403, para no confirmar ids ajenos). Cada borrador lleva un cerrojo y un contador `rev` que sube con
cada cambio aceptado: quien escribe manda el `rev` que vio y, si no coincide, `RevDesactualizado`.
El `id` es `secrets.token_urlsafe(16)` y no se registra nunca.

Sin FastAPI ni Streamlit (RM-1). Nada del asistente entra aqui: el punto de acoplamiento futuro es
`obtener(huella, id)` y `reemplazar(huella, id, borrador, rev)` (diseno §2.10).
"""

from __future__ import annotations

import pickle
import secrets
import sys
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timedelta
from typing import Any

from aplicacion.hoja import Borrador, VersionAbierta

POR_FICHA = 4
GLOBALES = 64
BYTES_MAXIMOS = 256 * 1024 * 1024
VIGENCIA = timedelta(hours=8)
#: Cada cuantos cambios aceptados se vuelve a estimar el tamano de un borrador (diseno §3.1).
RE_ESTIMAR_CADA = 20


class BorradorInexistente(LookupError):  # noqa: N818
    """El borrador no existe para esta ficha: nunca se creo, es de otra, se descarto o vencio."""


class RevDesactualizado(Exception):  # noqa: N818
    """Quien escribe vio un `rev` que ya no es el del borrador (otra ventana lo cambio)."""


def _recorrido(objeto: Any, visto: set[int]) -> int:
    """Suma `sys.getsizeof` de lo que cuelga de `objeto` (cada objeto una vez)."""
    if id(objeto) in visto:
        return 0
    visto.add(id(objeto))
    total = sys.getsizeof(objeto)
    if isinstance(objeto, Mapping):
        total += sum(_recorrido(k, visto) + _recorrido(v, visto) for k, v in objeto.items())
    elif isinstance(objeto, list | tuple | set | frozenset):
        total += sum(_recorrido(v, visto) for v in objeto)
    elif is_dataclass(objeto) and not isinstance(objeto, type):
        total += sum(_recorrido(getattr(objeto, f.name), visto) for f in fields(objeto))
    return total


def _tamano_estimado(borrador: Borrador) -> int:
    """`len(pickle.dumps(borrador))`; si algo del borrador no se serializa (TI-001 trae un
    `mappingproxy`), una estimacion por recorrido de objetos."""
    try:
        return len(pickle.dumps(borrador))
    except (TypeError, pickle.PicklingError, AttributeError):
        return _recorrido(borrador, set())


@dataclass(eq=False)
class BorradorVivo:
    """Un borrador en edicion, con lo que la hoja clasica guardaba en `st.session_state`.

    `caso` es la ruta del caso con que se abrio (la ruta opaca que la API compara con el caso de la
    ficha: un borrador jamas guarda en un caso ajeno). `abierta` es la `VersionAbierta` (o `None`:
    proyecto sin versiones, borrador en blanco); `calculo` es la cache `(rev, ResultadoHoja,
    cambios)` de la vista, que `reemplazar` invalida. `guardado_como` se llena al guardar (3d).
    """

    id: str
    huella: str
    caso: str
    proyecto: str
    version: str | None
    borrador: Borrador
    abierta: VersionAbierta | None
    creado: datetime
    tocado: datetime
    tamano: int
    rev: int = 0
    guardado_como: str | None = None
    calculo: tuple[int, Any, list] | None = None
    cerrojo: threading.RLock = field(default_factory=threading.RLock, repr=False)


class Registro:
    """El registro de borradores de un proceso. Reloj y medida inyectables para las pruebas."""

    def __init__(
        self,
        reloj: Callable[[], datetime] = datetime.now,
        *,
        por_ficha: int = POR_FICHA,
        globales: int = GLOBALES,
        bytes_maximos: int = BYTES_MAXIMOS,
        vigencia: timedelta = VIGENCIA,
        medir: Callable[[Borrador], int] = _tamano_estimado,
        re_estimar_cada: int = RE_ESTIMAR_CADA,
    ) -> None:
        self._reloj = reloj
        self._por_ficha = por_ficha
        self._globales = globales
        self._bytes_maximos = bytes_maximos
        self._vigencia = vigencia
        self._medir = medir
        self._re_estimar_cada = re_estimar_cada
        self._vivos: dict[str, BorradorVivo] = {}
        self._cerrojo = threading.RLock()
        #: A quien se avisa de cada borrador que sale del registro (fuera del cerrojo).
        self.al_quitar: list[Callable[[BorradorVivo], None]] = []
        self._quitados: list[BorradorVivo] = []

    # --- barrido y topes (siempre con el cerrojo tomado) ---------------------------------------

    @contextmanager
    def _exclusivo(self) -> Iterator[None]:
        """El cerrojo del registro y, ya soltado, el aviso de los borradores que salieron."""
        try:
            with self._cerrojo:
                yield
        finally:
            self._avisar()

    def _quitar(self, vivo: BorradorVivo) -> None:
        del self._vivos[vivo.id]
        self._quitados.append(vivo)

    def _avisar(self) -> None:
        with self._cerrojo:
            quitados, self._quitados = self._quitados, []
        for vivo in quitados:
            for aviso in list(self.al_quitar):
                try:
                    aviso(vivo)
                except Exception:  # noqa: BLE001 - un aviso que falla no frena a los demas
                    pass

    def _barrer(self, ahora: datetime) -> None:
        for vivo in [v for v in self._vivos.values() if ahora - v.tocado >= self._vigencia]:
            self._quitar(vivo)

    def _expulsar_al_menos_usado(self, entre: list[BorradorVivo]) -> None:
        self._quitar(min(entre, key=lambda v: v.tocado))

    def _expulsar_hasta_caber(self, quedarse: BorradorVivo) -> None:
        """Expulsa el menos usado (menos `quedarse`) hasta que el total de bytes estimados quepa."""
        while len(self._vivos) > 1 and (
            sum(v.tamano for v in self._vivos.values()) > self._bytes_maximos
        ):
            self._expulsar_al_menos_usado([v for v in self._vivos.values() if v is not quedarse])

    def _de(self, huella: str) -> list[BorradorVivo]:
        return [v for v in self._vivos.values() if v.huella == huella]

    # --- la capa ---------------------------------------------------------------------------------

    def crear(
        self,
        huella: str,
        caso: str,
        proyecto: str,
        version: str | None,
        borrador: Borrador,
        abierta: VersionAbierta | None,
    ) -> BorradorVivo:
        """Registra un borrador nuevo de la ficha `huella`; respeta topes y barre los vencidos."""
        with self._exclusivo():
            ahora = self._reloj()
            self._barrer(ahora)
            vivo = BorradorVivo(
                id=secrets.token_urlsafe(16),
                huella=huella,
                caso=caso,
                proyecto=proyecto,
                version=version,
                borrador=borrador,
                abierta=abierta,
                creado=ahora,
                tocado=ahora,
                tamano=self._medir(borrador),
            )
            while len(propios := self._de(huella)) >= self._por_ficha:
                self._expulsar_al_menos_usado(propios)
            while len(self._vivos) >= self._globales:
                self._expulsar_al_menos_usado(list(self._vivos.values()))
            self._vivos[vivo.id] = vivo
            self._expulsar_hasta_caber(vivo)
            return vivo

    def obtener(self, huella: str, id: str) -> BorradorVivo:
        """El borrador `id` de la ficha `huella` (y renueva su plazo); `BorradorInexistente`."""
        with self._exclusivo():
            ahora = self._reloj()
            self._barrer(ahora)
            vivo = self._vivos.get(id)
            if vivo is None or vivo.huella != huella:
                raise BorradorInexistente(id)
            vivo.tocado = ahora
            return vivo

    def reemplazar(self, huella: str, id: str, borrador: Borrador, rev: int) -> BorradorVivo:
        """Fija el borrador nuevo si `rev` es el vigente: sube `rev` e invalida la cache. Cada
        `re_estimar_cada` cambios vuelve a estimar el tamano y, si el total ya no cabe, expulsa
        el menos usado (nunca este)."""
        vivo = self.obtener(huella, id)
        with vivo.cerrojo:
            if vivo.rev != rev:
                raise RevDesactualizado(id)
            vivo.borrador = borrador
            vivo.rev += 1
            vivo.calculo = None
            if vivo.rev % self._re_estimar_cada == 0:
                vivo.tamano = self._medir(borrador)
                with self._exclusivo():  # primero el del borrador y luego el del registro
                    if self._vivos.get(vivo.id) is vivo:
                        self._expulsar_hasta_caber(vivo)
            return vivo

    def descartar(self, huella: str, id: str) -> None:
        """Idempotente: un id desconocido, vencido o ajeno no falla ni borra nada ajeno."""
        with self._exclusivo():
            vivo = self._vivos.get(id)
            if vivo is not None and vivo.huella == huella:
                self._quitar(vivo)

    def listar(self, huella: str) -> list[BorradorVivo]:
        """Los borradores de la ficha, el mas reciente (por uso) primero."""
        with self._exclusivo():
            self._barrer(self._reloj())
            return sorted(self._de(huella), key=lambda v: v.tocado, reverse=True)

    def olvidar(self, huella: str) -> None:
        with self._exclusivo():
            for vivo in self._de(huella):
                self._quitar(vivo)

    def heredar(self, anterior: str, nueva: str) -> None:
        """La ficha `nueva` sigue con los borradores de `anterior` (cambio de contrasena)."""
        with self._cerrojo:
            for vivo in self._de(anterior):
                vivo.huella = nueva

    def olvidar_todo(self) -> None:
        """Solo para las pruebas: ninguna hereda los borradores de otra."""
        with self._exclusivo():
            for vivo in list(self._vivos.values()):
                self._quitar(vivo)


REGISTRO = Registro()
crear = REGISTRO.crear
obtener = REGISTRO.obtener
reemplazar = REGISTRO.reemplazar
descartar = REGISTRO.descartar
listar = REGISTRO.listar
olvidar = REGISTRO.olvidar
heredar = REGISTRO.heredar
olvidar_todo = REGISTRO.olvidar_todo
al_quitar = REGISTRO.al_quitar
