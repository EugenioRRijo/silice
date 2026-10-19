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
   - Conecta a un daemon de Ollama local (`http://127.0.0.1:11434`) ejecutando modelos ligeros cuantizados (ej. `llama3.2:3b` o `qwen2.5:3b`).
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
* Módulo: `ml.anomaly.detector.DetectorAnomalias`.
* Algoritmo: **Isolation Forest** entrenado con rendimientos y precios históricos.
* Integración con UI: Cuando el detector marca una fila con anomalía, emite la etiqueta de severidad que el frontend traduce al **halo morado Carbon `#8a3ffc`**.
