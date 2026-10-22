# Retiro de Streamlit, F7: equivalencia de la logica del auditor

Commit de conmutacion: f2b3c5e5. Base congelada: `cd46732`. Solo cambian lineas de import de
`asistente/**` (`ui.hoja` a `aplicacion.hoja`); un comentario (`propuestas.py`, `COLUMNAS`) y un
docstring de `servicio.py` (fuera de la lista del auditor) citan ahora `aplicacion.hoja`.

## Criterio

Para cada archivo de `asistente/` que cambia: AST de `git show cd46732:<ruta>` contra el de HEAD,
tras normalizar los imports `ui` a `aplicacion` y quitar docstrings. Ademas (mas estricto que el
Apendice A del plan): los imports, ordenados, y el resto de sentencias, en orden, deben ser
identicos. `HojaInvalida` se importa de `aplicacion.hoja` (que la reexporta de `aplicacion.errores`)
para que la comparacion estricta se cumpla; es la misma clase.

## Salida

```
asistente/validacion.py
  solo en congelado: []
  solo en HEAD: []
  definiciones distintas: []
   EQUIVALENTE
asistente/orquestador.py
  solo en congelado: []
  solo en HEAD: []
  definiciones distintas: []
   EQUIVALENTE
asistente/privacidad.py
  solo en congelado: []
  solo en HEAD: []
  definiciones distintas: []
   EQUIVALENTE
asistente/propuestas.py
  solo en congelado: []
  solo en HEAD: []
  definiciones distintas: []
   EQUIVALENTE
asistente/servicio.py
  solo en congelado: []
  solo en HEAD: []
  definiciones distintas: []
   EQUIVALENTE
asistente/experimento/banco.py
  solo en congelado: []
  solo en HEAD: []
  definiciones distintas: []
   EQUIVALENTE
asistente/experimento/ejecucion.py
  solo en congelado: []
  solo en HEAD: []
  definiciones distintas: []
   EQUIVALENTE
TODOS: EQUIVALENTE
```

Mutante (sobre una copia fuera del repo): `return limpio[:limite]` de `asistente/privacidad.py`
cambiado a `limpio[:limite - 1]` hace que el mismo script imprima `TODOS: DIFERENTE`.

## Huellas

- `calcular()["banco"]` = `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2`, igual
  al de `congelado.json` (medido tras F7).
- `calcular()["protocolo"]` = `7de6b020d500b709c296f76fb166d0e440a9b232a537f408e3161190a2b37d04`,
  igual al de `congelado.json` (el protocolo aun no cambia).
- `auditor` difiere (los archivos cambiaron de import): se regenera en F11.
- Tras F8 (`ui/` borrada) `calcular()` falla con `FileNotFoundError: archivos del auditor que no
  existen: ['ui/composicion.py', 'ui/hoja.py']`, porque `protocolo.json` aun los lista. Queda roto
  hasta F11 (rutas definitivas en `protocolo.json` y `congelado.json` regenerado); por eso estan
  rojas las cinco pruebas de `test_experimento_congelado.py` que copian esos archivos y la ya
  conocida `test_experimento_congelado_vigente.py` (seis en total).
