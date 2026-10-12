"""Seguridad de Sílice (S3, 0.8.0): cuentas, sesiones, secretos, firma y empresas.

Todo lo de este paquete vive en la base de la instalación (`instalacion.db`), nunca en la de un
caso (maestro §4.2, RV-4). No importa `core`, `ui`, `api` ni `adapters`: solo la biblioteca
estándar, `sqlalchemy`, `argon2` y `cryptography` (`tests/unit/test_arquitectura_s3.py`). Las
funciones reciben la `Session` de la instalación y el reloj (`ahora`) que usan, para que las
pruebas no dependan del tiempo real.
"""
