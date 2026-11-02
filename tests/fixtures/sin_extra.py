"""Simular, dentro del mismo proceso, un entorno sin un extra opcional (INV-021).

Un solo gestor para los extras `civil` (`ifcopenshell`) y `ml`: limpia del cache de modulos todo
lo que pudiera haber importado el extra y bloquea `import <extra>` (y sus submodulos) con un
`ImportError`, para que un import a nivel de modulo mal hecho se delate de inmediato. Al salir
restaura el cache original **y** sincroniza los atributos de paquete.
"""

from __future__ import annotations

import builtins
import sys
from collections.abc import Sequence

import pytest


class SinExtra:
    """Gestor de contexto: `with SinExtra(monkeypatch, bloqueados, relacionados): ...`.

    Args:
        monkeypatch: el de la prueba; aplica el parche de `builtins.__import__`, que se deshace
            al salir del `with` (su teardown lo repone otra vez, sin efecto).
        bloqueados: nombres de paquete de primer nivel cuyo `import` lanza `ImportError`
            (tambien sus submodulos).
        relacionados: modulos que se sacan de `sys.modules` al entrar y se restauran al salir.
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        bloqueados: Sequence[str],
        relacionados: Sequence[str],
    ) -> None:
        self._monkeypatch = monkeypatch
        self._bloqueados = tuple(bloqueados)
        self._relacionados = tuple(relacionados)

    def _bloqueado(self, nombre: str) -> bool:
        return any(nombre == b or nombre.startswith(b + ".") for b in self._bloqueados)

    def __enter__(self) -> None:
        self._respaldo = {
            nombre: sys.modules[nombre] for nombre in self._relacionados if nombre in sys.modules
        }
        for nombre in self._relacionados:
            sys.modules.pop(nombre, None)

        import_original = builtins.__import__
        self._import_original = import_original

        def import_bloqueado(nombre, *args, **kwargs):
            if self._bloqueado(nombre):
                raise ImportError(f"simulado: extra no instalado ({nombre})")
            return import_original(nombre, *args, **kwargs)

        self._monkeypatch.setattr(builtins, "__import__", import_bloqueado)

    def __exit__(self, *excepcion: object) -> None:
        # El bloqueo termina con el `with`, no en el teardown del monkeypatch: se repone aqui el
        # `__import__` original (el teardown vuelve a poner el mismo valor, sin efecto).
        builtins.__import__ = self._import_original
        for nombre in self._relacionados:
            sys.modules.pop(nombre, None)
        sys.modules.update(self._respaldo)
        # `sys.modules.pop`/`.update` restauran la entrada del diccionario, pero NO el atributo del
        # paquete padre (p. ej. `ui.paginas.hoja`, el atributo). El import hecho dentro del `with`
        # lo deja apuntando a la copia fria sin el extra, y una prueba posterior que resuelva por
        # ruta de texto (`monkeypatch.setattr("ui.paginas.hoja.X", ...)`, que usa `getattr`)
        # parcharia la copia huerfana. Se sincroniza cada atributo con lo que quedo en
        # `sys.modules`, o se borra si el modulo no estaba cargado antes de `__enter__`.
        for nombre in self._relacionados:
            if "." not in nombre:
                continue  # modulo de nivel superior: no hay atributo de paquete padre que fijar
            nombre_paquete, atributo = nombre.rsplit(".", 1)
            paquete = sys.modules.get(nombre_paquete)
            if paquete is None:
                continue  # el paquete padre tampoco esta cargado: nada que sincronizar
            if nombre in sys.modules:
                setattr(paquete, atributo, sys.modules[nombre])
            elif hasattr(paquete, atributo):
                delattr(paquete, atributo)
