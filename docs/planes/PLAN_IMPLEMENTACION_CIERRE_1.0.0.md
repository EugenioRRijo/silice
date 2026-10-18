# Plan de Implementación: Cierre y Puesta en Marcha de Sílice 1.0.0

Este plan establece la ruta de ingeniería para completar, verificar y congelar la versión **1.0.0 de Sílice**. Su ejecución garantiza que el software funcione de manera autónoma, segura y verificable, cumpliendo con la hipótesis y arquitectura de la tesis.

---

## 1. Fundamentos Metodológicos y Principios de Diseño

El proyecto se rige por la constitución establecida en [NORMAS.md](file:///c:/Users/euger/OneDrive/Escritorio/TESIS/NORMAS.md) mediante cuatro pilares:

### A. Cascada (Macro-estructura de Gobierno)
El proyecto avanza por fases secuenciales separadas por **Compuertas de Calidad (Quality Gates)**. Ninguna fase se considera cerrada ni se pasa a la siguiente sin satisfacer al 100% sus criterios automatizados de compuerta (`meta_silice.py`).
```
[Fase 1: Integración] ──▶ Gate G1 ──▶ [Fase 2: Clave & Cripto] ──▶ Gate G2
       │
       ▼
[Fase 3: Instalador & Binario] ──▶ Gate G3 ──▶ [Fase 4: Humo & Red] ──▶ Gate G4
       │
       ▼
[Fase 5: Experimento & Informes] ──▶ Gate G5 ──▶ [Fase 6: Tagging & Release] ──▶ v1.0-tesis
```

### B. Scrum (Micro-ejecución Ágil)
Cada fase se descompone en tareas atómicas ejecutables por subagentes especializados (`sf-ingeniero-*`):
- **Ciclo TDD**: Prueba unitaria/integración antes de implementación (observando el fallo previo).
- **Definition of Done (DoD)**:
  1. Suite de pruebas verde (`pytest -W error`).
  2. Cobertura respetada según la capa ($\ge 80\%$).
  3. Formato y linter sin advertencias (`ruff check .` limpio).
  4. Guardia de arquitectura intacta (`git diff --stat origin/main -- core/` estrictamente vacío).
  5. Commit convencional en español sin tildes en el asunto (`feat(...)`, `fix(...)`, `test(...)`).

### C. Principios SOLID
- **S (Single Responsibility)**: Cada módulo y script tiene una única responsabilidad bien acotada (ej. `operacion/firma_sumas.py` gestiona exclusivamente firmas Ed25519; `instalador/construir.py` solo orquesta el empaquetado).
- **O (Open/Closed)**: El núcleo matemático y de contratos (`core/`) permanece cerrado e inalterable; la extensibilidad se logra agregando adaptadores o módulos periféricos sin tocar el motor de costos.
- **L (Liskov Substitution)**: Todos los adaptadores de especialidad (`civil`, `telecom`, `industrial`, `sistemas`) derivan de `AdaptadorDominio` y satisfacen sus invariantes sin efectos secundarios.
- **I (Interface Segregation)**: Contratos pequeños, inmutables (`frozen=True`) y segregados en `core.contracts` (`apu.py`, `presupuesto.py`, `verificacion.py`, `unidades.py`).
- **D (Dependency Inversion)**: Los módulos de alto nivel dependen de abstracciones (`core.contracts`); los detalles de bajo nivel (archivos, SQLite, red, Streamlit) quedan confinados a los bordes de la arquitectura (`adapters/`, `operacion/`, `ui/`, `api/`).

### D. DRY (Don't Repeat Yourself)
- **Fuentes únicas de verdad**:
  - Parámetros y constantes monetarias en `core.contracts.apu.ParametrosCosto`.
  - Normalización de unidades exclusivamente en `core.contracts.unidades`.
  - Línea base de cálculo solo en `tests/fixtures/apu_linea_base.py`.
  - Versión del sistema originada en `pyproject.toml` y consumida por API y UI vía `operacion.version`.
  - Validaciones de seguridad de archivos concentradas en `adapters.hoja_empresa.guardia`.

---

## 2. Inventario de Tareas por Fase

### Fase 1: Integración y Consolidación de Código Base
**Objetivo**: Integrar en `main` todas las pruebas de auditoría y correcciones pendientes.

| ID | Tarea | Componentes Afectados | Responsable | DoD |
|---|---|---|---|---|
| **T1.1** | Desmarcar Draft y fusionar [PR #86](https://github.com/EugenioRRijo/silice/pull/86) | Repositorio completo (27.500+ líneas, 6.100+ tests) | Eugenio / GitHub | PR #86 fusionado a `main` con merge commit |
| **T1.2** | Fusionar [PR #79](https://github.com/EugenioRRijo/silice/pull/79) (`instalador.yml`) | `.github/workflows/instalador.yml` | Eugenio / GitHub | Workflow activo en GitHub Actions |
| **T1.3** | Sincronizar ramas locales y worktrees con `origin/main` | Git worktrees (`.worktrees/`) | Agente | `main` al día con `origin/main` |

> **Gate G1**: `origin/main` verde en CI Linux y Windows; `git diff --stat origin/main -- core/` vacío.

---

### Fase 2: Ceremonia de la Clave del Proyecto (S5-CLAVE / T3)
**Objetivo**: Proveer la identidad criptográfica verificable del software sin comprometer secretos.

| ID | Tarea | Componentes Afectados | Responsable | DoD |
|---|---|---|---|---|
| **T2.1** | Generar par de claves Ed25519 fuera del repo | Consola local / carpeta segura | Eugenio | Archivos `clave_proyecto.enc` y `clave_proyecto.pub` generados |
| **T2.2** | Versionar clave pública | `operacion/clave_proyecto.pub` | Agente / Eugenio | Clave pública de 32 bytes hex guardada en el repo |
| **T2.3** | Actualizar huella SHA-256 en documentación | `docs/manual_instalacion.md` | Agente | Huella SHA-256 exacta registrada en el manual |

> **Gate G2**: `uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-5` evalúa `S5-CLAVE` en **OK**.

---

### Fase 3: Tooling de Instalación y Empaquetado Windows (S5-3 / T15)
**Objetivo**: Compilar el paquete instalador autónomo para Windows (`.exe`).

| ID | Tarea | Componentes Afectados | Responsable | DoD |
|---|---|---|---|---|
| **T3.1** | Instalar Inno Setup 6.7.x en la máquina | Sistema operativo Windows | Eugenio (`winget`) | `iscc` disponible en el `PATH` |
| **T3.2** | Compilación de prueba de `silice.iss` | `instalador/silice.iss`, `instalador/construir.py` | Agente | Generación de `Silice-0.6.0.exe` en `build/salida/` |
| **T3.3** | Verificación estática y de caracteres especiales | `tests/unit/test_iss.py` | Agente | Pruebas de compatibilidad con UTF-8 BOM y espacios pasando |

> **Gate G3**: Binario generado en local sin errores de ISPP ni macros faltantes; tamaño básico $\le 150\text{ MB}$.

---

### Fase 4: Prueba de Humo y Red Local (S5-4 / T16)
**Objetivo**: Validar que el ejecutable instalado arranca, responde y migra bases sin internet.

| ID | Tarea | Componentes Afectados | Responsable | DoD |
|---|---|---|---|---|
| **T4.1** | Ejecución de prueba de humo local | `instalador/humo.ps1` | Agente / Eugenio | 8 pasos de humo en verde (instalación, servicio, parada, persistencia) |
| **T4.2** | Verificación de aislamiento de red | `operacion/red.py`, `proxy_testigo.py` | Agente | Escucha únicamente en 127.0.0.1 salvo activación explícita de red local |
| **T4.3** | Auditoría de integridad tras instalación | `operacion/programa.py` | Agente | `python -m operacion verificar-programa` retorna 0 diferencias |

> **Gate G4**: `humo.ps1` ejecutado con éxito; servidor levantado en $\le 20\text{ s}$ y cerrado limpiamente.

---

### Fase 5: Experimento del Asistente y Cierre Documental S4 (S4-RESULTADOS)
**Objetivo**: Generar los resultados empíricos auditados del asistente de IA para el Capítulo V de la tesis.

| ID | Tarea | Componentes Afectados | Responsable | DoD |
|---|---|---|---|---|
| **T5.1** | Verificación de protocolo congelado | `asistente/experimento/congelado.json` | Agente | `congelado.verificar()` retorna lista vacía |
| **T5.2** | Generación de informe de resultados | `scripts/evaluar_asistente.py informe` | Agente | Archivo `docs/resultados_asistente.md` generado sin edición manual |
| **T5.3** | Auditoría meta S4 | `scripts/meta_silice_s4.py` | Agente | `S4-RESULTADOS` evaluado en **OK** |

> **Gate G5**: `scripts/meta_silice.py --version 0.9.0 --hasta S4-4` en **OK** al 100%.

---

### Fase 6: Cierre de Versión, Tagging y Congelamiento (GS5 / T20)
**Objetivo**: Incrementar la versión a `1.0.0`, firmar el paquete y crear las etiquetas inmutables.

| ID | Tarea | Componentes Afectados | Responsable | DoD |
|---|---|---|---|---|
| **T6.1** | Incremento de versión SemVer | `pyproject.toml`, `uv.lock`, `CHANGELOG.md` | Agente | Versión fijada en `1.0.0` y lockfile sincronizado |
| **T6.2** | Construcción del release final | `instalador/construir.py --perfil basico` | Agente | Generación de `Silice-1.0.0.exe` y `manifiesto.json` |
| **T6.3** | Firma de `SHA256SUMS` del release | `python -m operacion firmar-sumas` | Eugenio / Clave privada | Archivo `SHA256SUMS.ed25519` generado y verificado |
| **T6.4** | Verificación independiente con script | `instalador/verificar_sumas.py` | Agente | `VERIFICADO` reportado contra la clave pública del proyecto |
| **T6.5** | Creación de etiquetas Git finales | Git repository | Eugenio / Agente | Tags `v1.0.0-rc.1`, `v1.0.0` y `v1.0-tesis` creados y empujados |

> **Gate G6 (Final)**: Meta única en **OK** total: `uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-5` con salida 0.

---

## 3. Matriz de Responsabilidades (RACI)

| Actividad | Eugenio (Líder / Autor) | Agente (Pair Programmer / Subagentes) | CI / Entorno Autónomo |
|---|:---:|:---:|:---:|
| Fusión de PR #86 y PR #79 en GitHub | **A / R** | C | I |
| Generación de clave privada Ed25519 (H1) | **A / R** | C | - |
| Instalación de Inno Setup 6.7 (`winget`) | **A / R** | I | - |
| Ejecución de scripts de construcción y humo | I | **A / R** | **R** |
| Generación de informe del experimento | I | **A / R** | I |
| Firma de `SHA256SUMS` | **A / R** | C | - |
| Etiquetado `v1.0.0` y `v1.0-tesis` | **A** | **R** | I |

*R = Responsable de ejecutar; A = Aprueba / Autoriza; C = Consultado; I = Informado.*

---

## 4. Criterios de Aprobación para Iniciar la Ejecución

Para iniciar la secuencia de trabajo, confirma:
1. **Aprobación de la estructura de fases y compuertas** (Cascada G1–G6).
2. **Autorización para guiarte en el Paso 1 (Fusión de PR #86 y PR #79 en GitHub)** y en la **generación de la clave del proyecto (H1)**.
