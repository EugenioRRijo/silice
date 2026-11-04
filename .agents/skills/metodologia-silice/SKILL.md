---
name: metodologia-silice
description: >-
  Metodologia de trabajo obligatoria en Silice para cualquier tarea de codigo, prueba, depuracion o
  auditoria: TDD con rojo visto, verificar antes de afirmar, depuracion por causa raiz, DRY con
  fuentes unicas y commits pequenos. Usar siempre antes de escribir codigo, proponer un arreglo,
  declarar algo "hecho" o reportar un hallazgo.
---

# Metodología de Sílice (la misma que sigue Claude, el orquestador)

La constitución es [NORMAS.md](../../../NORMAS.md); la metodología Scrum-Cascada y las fuentes únicas,
[docs/metodologia.md](../../../docs/metodologia.md). Esto es el resumen operativo.

## 1. Verificar antes de afirmar

- Ninguna frase del tipo «pasa», «está arreglado» o «falla» sin **el comando que corriste y su salida
  real**. Si no lo corriste, di «no verificado».
- Cita `archivo:línea` del **árbol actual** (`git rev-parse --short HEAD`), no de un worktree ni de un
  plan viejo. Lo vigente está en [docs/ESTADO.md](../../../docs/ESTADO.md).
- Antes de reportar una falla de prueba, descarta el entorno: carpetas locales ignoradas por git
  (`ui/__pycache__`, `demo_dist/`, `graphify-out/`), una consola cp1252 o un worktree viejo. Si la CI
  no la ve, probablemente es local: dilo así.

## 2. TDD con rojo visto

1. Escribe la prueba y **córrela: debe fallar por la razón esperada**, no por un error de importación.
2. Commit de la prueba sola: `test(<area>): <que> (rojo)`.
3. El mínimo código que la pone en verde; commit `feat|fix(<area>): ...`.
4. Oráculos independientes: el valor esperado sale de la fuente (cálculo a mano, ERS, norma), nunca
   del código bajo prueba. Sin `skip`, `xfail` ni filtros de warnings (`pytest -W error`).
5. Para probar que una prueba vale: introduce un mutante a mano (invierte una condición) y comprueba
   que cae. Después deshazlo.

## 3. Depuración por causa raíz

1. Reproduce el fallo con un comando exacto.
2. Lee el error completo y el código implicado; formula **una** hipótesis.
3. Pruébala con el cambio más pequeño posible. Si no se confirma, vuelve al paso 2; no apiles arreglos.
4. Tras tres hipótesis fallidas, para y reporta lo que sabes: puede ser un problema de diseño.

## 4. DRY y fuentes únicas

Cada hecho vive en un lugar y los demás documentos lo enlazan. Antes de escribir un dato (versión,
cifra, estado), busca su fuente única (`docs/metodologia.md` §5). No copies bloques de documentos:
enlázalos.

## 5. Reglas del dominio que no se negocian

- `core/` no cambia sin expediente y aval del tutor (`scripts/guardia_nucleo.py`).
- Dinero y cantidades con `Decimal` (Python) o texto exacto (front); la interfaz no calcula.
- Coma decimal y punto de miles en toda entrada y salida.
- Datos reales nunca en el repositorio ni en tus mensajes: NORMAS §1. Procesas en la nube de Google.

## 6. Comandos de comprobación

```powershell
uv run --active pytest <archivos> -q -W error -p no:cacheprovider
uv run --active ruff check <archivos>; uv run --active ruff format --check <archivos>
$env:PYTHONIOENCODING="utf-8"; uv run --active python scripts/meta_datos.py
cd frontend-desktop; npx vitest run <ruta>; npm run lint
```

No corras la suite completa salvo que te lo pidan: tarda y compite con otros agentes por la máquina.
