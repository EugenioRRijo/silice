"""Esquemas del primer arranque (BCP-1; `api.rutas.primer_arranque`).

Ninguno lleva rutas, nombres de usuario ni el código. `ReclamoDeInstalacion` limita cada campo
(la contraseña a lo que admite `seguridad.cuentas`) y es estricto con los tipos: un número no
se convierte en texto ni un «si» en booleano.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, StrictBool, StrictStr

from seguridad import cuentas


class PoliticaDeContrasena(BaseModel):
    minimo: int = Field(description="Caracteres mínimos de una contraseña")
    maximo: int = Field(description="Caracteres máximos de una contraseña")


class PrimerArranqueRespuesta(BaseModel):
    sin_cuentas: bool = Field(description="La instalación no tiene ninguna cuenta")
    archivo_presente: bool = Field(
        description="Existe `codigo_instalacion.txt` en la carpeta de datos"
    )
    modo: Literal["producto", "desarrollo"] = Field(
        description="`producto` si la instalación es la del instalador"
    )
    politica: PoliticaDeContrasena


class ReclamoDeInstalacion(BaseModel):
    codigo: StrictStr = Field(
        max_length=64, description="El código de instalación o de restablecimiento"
    )
    usuario: StrictStr = Field(max_length=120)
    nombre: StrictStr = Field(max_length=120)
    contrasena: StrictStr = Field(max_length=cuentas.MAXIMO_CONTRASENA)
    tambien_arma: StrictBool = Field(
        default=False,
        description="La cuenta nueva también arma presupuestos (solo vale para una cuenta nueva)",
    )
