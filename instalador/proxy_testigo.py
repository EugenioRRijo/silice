"""Proxy testigo de la prueba de humo (spec S5 §11.2 paso 1): anota toda petición que le llega y
no deja pasar ninguna. Con `HTTP_PROXY` apuntando aquí, lo que Sílice pida respetando proxies queda
en el registro; se espera **cero** líneas."""

from __future__ import annotations

import argparse
import http.server
from pathlib import Path


def crear_manejador(registro: Path) -> type[http.server.BaseHTTPRequestHandler]:
    class Testigo(http.server.BaseHTTPRequestHandler):
        def _responder(self) -> None:
            with registro.open("a", encoding="utf-8") as archivo:
                archivo.write(f"{self.command} {self.path}\n")
            self.send_error(502, "proxy testigo: sin salida")

        # los nombres do_<MÉTODO> los fija http.server
        do_GET = do_POST = do_PUT = _responder  # noqa: N815
        do_DELETE = do_HEAD = do_OPTIONS = do_PATCH = _responder  # noqa: N815
        do_CONNECT = _responder  # noqa: N815

        def log_message(self, *argumentos) -> None:  # silencio: el registro es el archivo
            return

    return Testigo


def crear_servidor(puerto: int, registro: Path) -> http.server.ThreadingHTTPServer:
    return http.server.ThreadingHTTPServer(("127.0.0.1", puerto), crear_manejador(registro))


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--puerto", type=int, required=True)
    analizador.add_argument("--registro", type=Path, required=True)
    argumentos = analizador.parse_args(argv)
    crear_servidor(argumentos.puerto, argumentos.registro).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
