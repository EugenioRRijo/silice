---
name: asistente-ia
description: >-
  Arquitectura del Asistente de IA en Sílice: integración dual Cloud/Offline (Claude y Ollama),
  almacenamiento seguro de claves con keyring, embeddings multilingües y detección de anomalías ML.
---

# Skill: Asistente de IA y Modelos de Aprendizaje Automático

Esta guía define cómo operar y extender el componente de inteligencia artificial y machine learning de Sílice (`asistente/` y `ml/`).

---

## 1. Arquitectura Dual de Proveedores (Cloud vs. Offline)

Para cumplir con **RNF-08** (operación sin conexión forzada y sin fugas de datos comerciales confidenciales):

1. **Modo Cloud (Claude API):**
   - Utilizado cuando el usuario configura voluntariamente una clave de Anthropic.
   - Ideal para síntesis complejas de memoria descriptiva y auditorías forenses profundas.
2. **Modo Offline / Local (Ollama):**
   - Para instalaciones aisladas o en obra sin internet.
   - Conecta a un daemon de Ollama local (`http://127.0.0.1:11434`, bucle local comprobado por **IP resuelta**; versión mínima en `asistente/config_ia.json`). El modelo lo fija el administrador (`asistente/configuracion.py`, campo `modelo_local`); el experimento usa el de `asistente/experimento/protocolo.json`.
   - **Invariante:** la IA nunca escribe un número final; solo propone datos de entrada por las herramientas del sistema y el usuario confirma (spec S4 §1).
3. **Almacenamiento Seguro de Credenciales:**
   - **NUNCA** almacenar claves API en archivos de texto, `.env` o bases de datos SQLite.
   - Utilizar el módulo `keyring` del sistema operativo (Windows Credential Manager / DPAPI) mediante `seguridad.secretos`.

---

## 2. Embeddings Locales y Detección de Anomalías

### 2.1. Similitud Semántica de Partidas
* Modelo oficial: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
* Opera 100% offline tras su descarga inicial (`HF_HUB_OFFLINE="1"`).
* Permite comparar descripciones libres de partidas contra el catálogo oficial de la empresa o normas COVENIN.

### 2.2. Detección de Valores Atípicos (Outliers)
* Módulo: `ml/anomaly/detector.py`, funciones `precios_atipicos` (variaciones de precio, RF-29/RF-100) y `evaluar_rendimiento` (RF-27).
* Algoritmo: **Isolation Forest** ajustado sobre el histórico cada vez, `SEMILLA = 42`, `UMBRAL_ATIPICO = -0.05` (más negativo = más atípico), se abstiene con menos de `MINIMO_OBSERVACIONES = 8`. Sin datos reales no se valida la tasa de detección: se prueba con series sembradas.
* Integración con UI: el hallazgo es ADVERTENCIA con código `CODIGO_ATIPICO` (nunca ERROR); la interfaz lo traduce al **halo morado Carbon `#8a3ffc`**.
