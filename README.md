# Tecem - API Backend 

Este es el núcleo del sistema **Tecem**, un SaaS diseñado para la gestión y llenado de calificaciones académicas. Proporciona una API robusta construida con **Django** y **Django REST Framework (DRF)**.

## ✨ Características Técnicas
- **Autenticación:** Gestión de usuarios y sesiones mediante **JWT** (JSON Web Tokens).
- **Base de Datos:** Persistencia con **SQLite** (desarrollo) y soporte para PostgreSQL mediante Django ORM.
- **Estructura:** API unificada para el manejo de alumnos, docentes y actas de calificaciones.

---

## 🛠️ Instalación y Configuración

Sigue estos pasos para levantar el servidor localmente:

### 1. Preparar el entorno
Entra al directorio del proyecto y crea un entorno virtual:

$ cd tecem-back

# En Unix (Linux/Mac)
$python3 -m venv env$ source env/bin/activate

# En Windows
$python -m venv env$ .\env\Scripts\activate

### 2. Instalar dependencias
$ pip install -r requirements.txt

### 3. Configurar la Base de Datos
Ejecuta las migraciones para crear las tablas de calificaciones y usuarios:

$python manage.py makemigrations$ python manage.py migrate

### 4. Iniciar el servidor
$ python manage.py runserver 5000

El API de Tecem estará disponible en: http://localhost:5000

---

## 🐳 Ejecución con Docker
Si prefieres un entorno contenedorizado:

$cd api-server-django$ docker-compose up --build