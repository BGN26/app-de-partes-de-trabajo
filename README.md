# 🛠️ AI-Powered Work Order Management System

### *Gestión Inteligente de Partes de Trabajo con Visión Artificial Multimodal*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask_3.0-green.svg)](https://flask.palletsprojects.com/)
[![AI Model](https://img.shields.io/badge/AI_Model-Gemini_2.5_Flash-orange.svg)](https://aistudio.google.com/)
[![Docker](https://img.shields.io/badge/Deployment-Docker_Ready-blue.svg)](https://www.docker.com/)

---

## 🚀 La Visión del Proyecto

Este proyecto nace para resolver un cuello de botella crítico en empresas de servicios técnicos y mantenimiento: la digitalización de los albaranes de trabajo manuales. El proceso tradicional es lento, propenso a errores y genera una desconexión entre el trabajo de campo y la facturación administrativa.

Esta aplicación no es un simple CRUD. Es una solución de **IA Multimodal** que automatiza la entrada de datos. El operario simplemente toma una foto del parte de trabajo rellenado a mano, y el sistema utiliza modelos avanzados de Visión Artificial (Gemini 2.5 Flash) para entender el texto, estructurarlo y cruzalo inteligentemente con las bases de datos de la empresa, generando una factura en PDF al instante.

### 🌟 Características Clave

* **🔒 Autenticación Segura:** Sistema de login completo (Flask-Login).
* **📸 Entrada de Datos Híbrida (IA + Manual):** Permite creación manual o asistida por cámara.
* **🧠 IA Multimodal (Pipeline Senior):** Integración directa con Gemini 2.5 Flash. El modelo analiza la imagen directamente, obviando el OCR tradicional (Tesseract), lo que reduce la latencia e incrementa la precisión en documentos manuscritos o mal iluminados.
* **🔗 Inteligencia de Negocio (Fuzzy Matching):** Los datos extraídos por la IA (clientes, materiales) se cruzan contra la base de datos utilizando algoritmos de coincidencia difusa (`thefuzz`). Esto permite que el sistema preseleccione la opción correcta en los desplegables aunque la IA haya leído "cables" y en la BD ponga "Cable Coaxial".
* **🧾 Generación Automática de Facturas:** Generación dinámica de documentos PDF (con `fpdf2`) listos para imprimir o enviar al cliente.
* **📱 Diseño "Mobile First":** Interfaz totalmente adaptiva (Bootstrap 5) diseñada para ser usada desde teléfonos móviles en el campo.

---

## 🛠️ Stack Tecnológico

* **Backend:** Python 3.x, Flask (Microframework).
* **Base de Datos:** SQLAlchemy (ORM) con SQLite (múltiples bases de datos enlazadas para escalabilidad simulada).
* **Inteligencia Artificial:** Google GenAI (Gemini 2.5 Flash).
* **Procesamiento de Imagen:** OpenCV (normalización de contraste y reducción de ruido).
* **Algoritmia:** `thefuzz` (Levensthein distance) para Fuzzy Matching.
* **Frontend:** HTML5, Jinja2, JavaScript moderno, Bootstrap 5.
* **Documentación:** `fpdf2`.

---

## ⚙️ Arquitectura del Pipeline de IA

Este es el flujo que hace única a esta aplicación:

1.  **Captura (Móvil):** El usuario sube la foto vía HTTPS.
2.  **Preprocesamiento (OpenCV):** La imagen se normaliza (escala de grises, aumento de contraste adaptativo, binarización) para maximizar la legibilidad.
3.  **Análisis Multimodal (Gemini 2.5 Flash):** Se envía la imagen preprocesada a la API de Google con un prompt de ingeniería estructurada, forzando una respuesta en formato JSON nativo.
4.  **Estructuración de Datos (Backend Python):** Se parsea el JSON.
5.  **Correlación Inteligente (Fuzzy Matching):** Python cruza los textos crudos de la IA contra las tablas de `Cliente` y `Producto` usando distancias de Levenshtein. Si hay coincidencia (>80% seguridad), se asigna el ID exacto de la base de datos.
6.  **UX Reactiva (Formulario):** El formulario de Bootstrap se autorrellena y preselecciona los desplegables correctos, ahorrando un 90% del tiempo de escritura al operario.

---

## 🛠️ Instalación y Uso Local

### Prerrequisitos
* Python 3.10 o superior.
* Una API KEY de [Google AI Studio](https://aistudio.google.com/).

### Pasos

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/tuusuario/app-partes-trabajo.git](https://github.com/tuusuario/app-partes-trabajo.git)
    cd app-partes-trabajo
    ```

2.  **Crear y activar el entorno virtual:**
    ```bash
    python -m venv .venv
    # En Windows
    .venv\Scripts\activate
    # En Linux/macOS
    source .venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar variables de entorno:**
    Crea un archivo llamado `.env` en la raíz del proyecto y añade tu API KEY real:
    ```env
    SECRET_KEY=inventa_una_clave_larga_y_segura
    DATABASE_URL=sqlite:///principal.db
    BIND_CLIENTES=sqlite:///clientes.db
    BIND_MATERIALES=sqlite:///materiales.db
    GEMINI_API_KEY=tu_clave_real_de_google_aqui
    ```

5.  **Arrancar la aplicación:**
    ```bash
    python app.py
    ```
    La aplicación se iniciará por defecto en `http://127.0.0.1:5000`.

**Nota para pruebas con móvil:** Si quieres probar la cámara desde el móvil real, arranca `python app.py` y en otra terminal usa Ngrok (`ngrok http 5000`). Entra en la URL `https` que te genere Ngrok desde tu móvil.

