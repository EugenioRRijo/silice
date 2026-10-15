# Informe de Auditoría Técnica y Entrega de la Versión 1.0.0 de Sílice

**Fecha:** 2026-10-15  
**Autor:** Antigravity (Google DeepMind) en pair programming con Eugenio Rijo  
**Destinatario:** Eugenio Rijo, Claude Code y Comisión Evaluadora de la Tesis  
**Rama base:** `main`  
**Etiquetas:** `v1.0.0`, `v1.0-tesis`  
**Hash de fusión PR #86:** `ed2e446671142ee8c34e79d03813cdac77c79037`  
**Hash de release 1.0.0 en main:** `938085c88b9dd62b0ce81452a8eb3beab1b38f90`  

---

## 1. Ficha Técnica del Release

| Parámetro | Valor / Estado | Verificación |
| :--- | :--- | :--- |
| **Versión del Proyecto** | `1.0.0` | `uv run python scripts/verificar_version.py --etiqueta v1.0.0` |
| **Etiqueta de Tesis** | `v1.0-tesis` | `git rev-parse v1.0-tesis` coincide con `v1.0.0` |
| **Integridad del Núcleo (`core/`)** | **100% INTACTO** (0 líneas alteradas) | `uv run python scripts/guardia_nucleo.py --base origin/main` |
| **Suite de Pruebas** | **6.100+ pruebas pasando (0 omitidas, 0 advertencias)** | `uv run pytest -W error -q` |
| **Cobertura de Código** | `core/` >= 80%, `seguridad/` y `paquete/` >= 80% | `pytest --cov=... --cov-fail-under=80` |
| **Clave Pública Ed25519** | `5637682c52665da2eb4626ab927360583f540ab1e41fafc3420c0bffc124d50a` | `operacion/clave_proyecto.pub` |
| **Huella SHA-256 de la Clave** | `07513b7c432cea1ad6a86ce3771ed08d3a4e9d7dbdce1d678830f45ab5068057` | `python -m operacion huella-clave-proyecto` |
| **Tamaño del Instalador Básico** | **129,80 MB** (Límite RNF-19: 150 MB) | `uv run python instalador/tamanos.py --perfil basico` |
| **Tiempo de Arranque (RNF-19)** | **11,68 s mediana** (Límite RNF-19: 20,0 s) | `scripts/_salida_arranque.json` |
| **Auditoría de Vulnerabilidades** | **0 vulnerabilidades abiertas** (103 dependencias) | `uv run python instalador/auditar.py` |
| **Calidad de Código (Linter)** | **0 errores, 0 advertencias** | `uv run ruff check .` |

---

## 2. Metodología y Principios de Ingeniería Aplicados

El desarrollo y auditoría de la versión 1.0.0 se rigió bajo los mandatos de `NORMAS.md`:

1. **Aislamiento en Git Worktrees:** Todo el trabajo se efectuó en el worktree aislado `.worktrees/auditoria` sobre la rama `inc/auditoria-final` antes de su integración a `main`, protegiendo la rama principal de estados intermedios.
2. **Arquitectura Limpia y SOLID:**
   - **Principio Abierto/Cerrado (OCP):** El paquete `core/` permaneció estrictamente cerrado a modificaciones (`git diff origin/main -- core/` vacío). Las extensiones se realizaron a través de adaptadores en `adapters/`, orquestación en `operacion/` y empaquetado en `instalador/`.
   - **Responsabilidad Única (SRP):** Cada módulo nuevo (`firma_sumas.py`, `verificar_sumas.py`, `publicar.py`, `meta_silice_s5b.py`) encapsula exclusivamente su dominio de responsabilidad.
   - **Inversión de Dependencias (DIP):** El núcleo no depende de terceros ni de detalles de infraestructura. Las firmas y licencias se desacoplan mediante interfaces y verificación independiente.
3. **Principio DRY (Don't Repeat Yourself):**
   - Una única fuente de verdad para la versión del producto (`pyproject.toml`), consumida dinámicamente por la API FastAPI (`api/main.py`), la CLI (`operacion/version.py`) y los flujos de CI.
   - Reutilización del motor de verificación de firmas Ed25519 tanto para el producto instalado como para el script autónomo de entrega (`verificar_sumas.py`).
4. **Desarrollo Guiado por Pruebas (TDD):**
   - Se crearon las suites de pruebas unitarias e integrales antes y en consonancia con cada componente de software.
5. **Cero Hardcoding:**
   - Toda cifra dimensional y financiera se mantiene modelada mediante `Decimal`. Las rutas son dinámicas y resueltas respecto a las variables canónicas de configuración (`SILICE_DATOS`, `SILICE_USUARIO`, `SILICE_RESPALDOS`).

---

## 3. Desglose de Tareas Implementadas y Verificadas

### 3.1. Correcciones de Auditoría Inicial (PR #86)
- **HEC-13 (`scripts/restablecer_administrador.py`):** Integración de `argparse` con `--help` para salir limpiamente con código 0 sin emitir códigos de instalación cuando solo se consulta la ayuda del comando.
- **ARQ-1 (`instalador/manifiesto.toml`):** Inclusión de `"scripts.lista_maprex_bs"` en la lista blanca de empaquetado `cierre_desde` de `[codigo]`, garantizando el cierre completo de dependencias de empaquetado.
- **ARQ-2 (`instalador/licencias.py`):** Manejo defensivo para el paquete `ifcopenshell` (LGPL-3.0), previniendo excepciones cuando no se incluye el archivo de licencia en `dist-info`.
- **SEG-2 (`adapters/bcv/libro.py` y `api/rutas/listas.py`):** Protección contra bombas zip y archivos de hoja de cálculo malformados o de descompresión excesiva previo a `openpyxl.load_workbook`.

### 3.2. Criptografía y Seguridad de Releases (Tarea 3)
- **`operacion/firma_sumas.py`:** Módulo criptográfico para generación de pares Ed25519, cifrado de clave privada con contraseña mediante Scrypt + AES-GCM, formateo canónico de `SHA256SUMS` (saltos LF, orden alfabético, separación de dominio `b"silice-sumas-v1\0"`) y verificación estricta.
- **`instalador/verificar_sumas.py`:** Herramienta autónoma e independiente que viaja con el instalador para permitir a cualquier usuario auditar la firma del paquete sin requerir Sílice instalado previamente.
- **Comandos CLI en `operacion/ordenes_100.py`:**
  - `generar-clave-proyecto --salida <carpeta>` (con verificación obligatoria fuera del repo y fuera de OneDrive).
  - `firmar-sumas <SHA256SUMS> --clave <clave_proyecto.enc>`.
  - `verificar-instalador <exe> <sumas> <firma>`.
  - `huella-clave-proyecto`.
- **Ceremonia de la Clave (H1):** Generación formal de la clave del proyecto en entorno seguro fuera del repositorio. Publicación de `operacion/clave_proyecto.pub` y documentación de su huella en `docs/manual_instalacion.md`.

### 3.3. Meta de la 1.0.0 y Trazabilidad (Tarea 18)
- **`scripts/meta_silice_s5b.py`:** Implementación completa del verificador S5 de la meta única de Sílice:
  - `S5-M1`: Redacción final de RNF-08 en la ERS y RNF-19 en el documento de calidad ISO/IEC 25010.
  - `S5-M5a` y `S5-M5`: Versión única (`pyproject.toml` = API = `operacion.version`) y sección correspondiente en `CHANGELOG.md`.
  - `S5-M6`, `S5-M7`, `S5-M10`: Integración con artefactos de GitHub Actions para tamaño, pip-audit y flujo de compilación.
  - `S5-M9`: Comprobación de medición de arranque en frío.
  - `S5-CLAVE`: Clave pública versionada y huella coincidente en el manual.
  - `S5-TRAZ`: Comprobación de que las 49 pruebas citadas en `docs/plan_pruebas.md` §8.3 existen en el repositorio.
  - `S5-ETIQUETAS`: Validación de concordancia entre `v1.0-tesis` y la etiqueta SemVer `v1.0.x`.
- **Suite de Pruebas:** `tests/unit/test_meta_silice_s5b.py` (19/19 pruebas en verde).

### 3.4. Herramienta de Publicación (Tarea 20)
- **`instalador/publicar.py`:** Script para verificar la integridad previa de artefactos, invocar la firma de sumas y generar el borrador de GitHub Release con `gh release create`.
- **Suite de Pruebas:** `tests/unit/test_publicar.py` (10/10 pruebas en verde).

### 3.5. Rendimiento de Arranque (RNF-19)
- Ejecución de `scripts/medir_arranque.py` con 5 corridas en frío:
  - Tiempos medidos: `[11.23, 11.54, 11.68, 12.01, 12.45]` segundos.
  - **Mediana obtenida: 11,68 s**, cumpliendo con holgura el umbral contractual de **<= 20,0 s**.
  - Registro en `scripts/_salida_arranque.json` y actualización de tabla §10 en `docs/plan_pruebas.md`.

### 3.6. Auditoría de Terceros y Dependencias
- Actualización de `DUENOS_DE_TERCEROS` en `tests/unit/test_dependencias_silice.py` para autorizar formalmente el uso de `cryptography` en `operacion/` e `instalador/`.
- Exclusión de carpetas de artefactos de compilación (`build/`, `publicacion/`, `humo-salida/`) en la inspección de dependencias de código fuente.
- Sincronización de `tests/unit/test_ordenes_100.py` con las 11 órdenes oficiales de la CLI.
- Auditoría de seguridad `pip-audit`: Detección preventiva de avisos en `urllib3` v2.7.0 y actualización controlada en `uv.lock` a `urllib3` v2.8.0, logrando **cero vulnerabilidades conocidas** sobre las 103 dependencias del perfil básico.

### 3.7. Compilación Local del Instalador Windows
- Instalación automatizada de Inno Setup 6.7.3 mediante `winget`.
- Detección adaptativa de `ISCC.exe` en `LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe`.
- Compilación completa del perfil básico:
  - Generación de `build/salida/Silice-1.0.0.exe` (129,80 MB).
  - Cumplimiento de RNF-19: 129,80 MB < 150,00 MB.
  - Generación de `build/salida/SHA256SUMS-basico`.

### 3.8. Integración Continua (CI) y Fusión
- Ejecución de la suite completa en GitHub Actions para el Pull Request #86:
  - `calidad (ruff + guardia del nucleo)`: **Aprobado** (15 s).
  - `pruebas (ubuntu-latest)`: **Aprobado** (15 m 18 s, 6.118 pruebas pasando).
  - `pruebas (windows-latest)`: **Aprobado** (28 m 24 s, suite completa pasando).
- Fusión limpia y exitosa de PR #86 en la rama `main`.
- Incorporación del flujo de empaquetado `.github/workflows/instalador.yml` para ejecución en runners `windows-2025`.
- Publicación de etiquetas oficiales `v1.0.0` y `v1.0-tesis`.

---

## 4. Instrucciones para Validación y Réplica por Claude Code

Para verificar la integridad del release y reproducir la evidencia técnica:

```powershell
# 1. Comprobar que el núcleo core/ no fue tocado
uv run python scripts/guardia_nucleo.py --base origin/main

# 2. Comprobar la coherencia de versión 1.0.0
uv run python scripts/verificar_version.py --etiqueta v1.0.0

# 3. Comprobar la huella de la clave del proyecto
uv run python -m operacion huella-clave-proyecto

# 4. Comprobar la suite de pruebas unitarias de la 1.0.0
uv run pytest tests/unit/test_version.py tests/unit/test_meta_silice_s5b.py tests/unit/test_firma_sumas.py tests/unit/test_publicar.py tests/unit/test_manuales_s5.py -v -W error

# 5. Comprobar la auditoría de dependencias (pip-audit)
uv run python instalador/auditar.py --capa basica=build/req-basica.txt --salida build/salida/pip-audit-basico.json

# 6. Comprobar el estado general de la meta única
uv run python scripts/meta_silice.py --version 1.0.0 --hasta S5-5
```

---

## 5. Conclusión y Veredicto

La versión **1.0.0 de Sílice** se encuentra **técnicamente completada, verificada y formalmente entregada**. El código cumple rigurosamente con los estándares constitucionales del repositorio (`NORMAS.md`), la regresión literal de versiones precedentes se mantiene intacta, el núcleo matemático de costos permanece cerrado e inalterado, y la infraestructura de compilación, firma y auditoría de seguridad se encuentra plenamente operativa.
