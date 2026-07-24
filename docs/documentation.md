# Documentación Técnica — ApiFastApi

ApiFastApi es una API RESTful asíncrona para la gestión de usuarios, construida con **FastAPI**, **SQLAlchemy 2.x**, **PostgreSQL 18** y **PgBouncer**, diseñada para entornos productivos orquestados con **Docker Swarm**.

---

## Tabla de Contenidos

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Modelo de Datos](#3-modelo-de-datos)
4. [Referencia de la API](#4-referencia-de-la-api)
5. [Configuración y Desarrollo Local](#5-configuración-y-desarrollo-local)
6. [Despliegue en Producción](#6-despliegue-en-producción)
7. [Infraestructura Docker Swarm](#7-infraestructura-docker-swarm)
8. [Migraciones con Alembic](#8-migraciones-con-alembic)
9. [Integración Continua (CI/CD)](#9-integración-continua-cicd)
10. [Seguridad](#10-seguridad)
11. [Troubleshooting](#11-troubleshooting)
12. [Roadmap / Trabajo Futuro](#12-roadmap--trabajo-futuro)

---

## 1. Arquitectura del Sistema

### 1.1 Diagrama de Arquitectura

```
  ┌──────────────┐
  │   Cliente    │  (cURL, httpx, navegador, etc.)
  └──────┬───────┘
         │  HTTP :8000
         ▼
  ┌─────────────────────────────────────────────┐
  │           FastAPI / Uvicorn                 │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
  │  │  main.py │  │schemas.py│  │repository│  │
  │  │  (rutas) │  │(Pydantic)│  │  (DAO)   │  │
  │  └──────────┘  └──────────┘  └──────────┘  │
  │              ┌────────────┐                 │
  │              │dbconexion.py│                 │
  │              │ (engine)   │                 │
  │              └────────────┘                 │
  └──────────────────────┬──────────────────────┘
                         │  asyncpg :6432
                         ▼
  ┌─────────────────────────────────────────────┐
  │               PgBouncer                     │
  │  pool_mode = transaction                    │
  │  default_pool_size = 20                     │
  │  max_client_conn = 1000                     │
  └──────────────────────┬──────────────────────┘
                         │  libpq :5432
                         ▼
  ┌─────────────────────────────────────────────┐
  │            PostgreSQL 18                    │
  │  ┌──────────────────────────────────────┐   │
  │  │           users                      │   │
  │  │  id (PK) | name | cedula (UNIQUE)   │   │
  │  └──────────────────────────────────────┘   │
  └─────────────────────────────────────────────┘
```

### 1.2 Flujo de una Petición (Ejemplo: Crear Usuario)

```
Cliente                     FastAPI                UserRepository          PgBouncer          PostgreSQL
   │                          │                        │                     │                   │
   │  POST /users             │                        │                     │                   │
   │  {"name":"Juan",         │                        │                     │                   │
   │   "cedula":"123"}        │                        │                     │                   │
   │ ───────────────────────► │                        │                     │                   │
   │                          │  Valida con            │                     │                   │
   │                          │  UserCreate (Pydantic) │                     │                   │
   │                          │                        │                     │                   │
   │                          │  repo.create(usuario)  │                     │                   │
   │                          │ ─────────────────────► │                     │                   │
   │                          │                        │  SELECT ... WHERE   │                   │
   │                          │                        │  cedula='123'       │                   │
   │                          │                        │ ──────────────────► │ ────────────────► │
   │                          │                        │ ◄────────────────── │ ◄──────────────── │
   │                          │                        │                     │                   │
   │                          │                        │  INSERT INTO users  │                   │
   │                          │                        │ ──────────────────► │ ────────────────► │
   │                          │                        │ ◄────────────────── │ ◄──────────────── │
   │                          │                        │                     │                   │
   │                          │  ◄───────────────────── │                     │                   │
   │ 201 Created              │                        │                     │                   │
   │  {"id":1,"name":"Juan",  │                        │                     │                   │
   │   "cedula":"123"}        │                        │                     │                   │
   │ ◄─────────────────────── │                        │                     │                   │
```

### 1.3 Patrón Arquitectónico

El proyecto sigue una **arquitectura en capas** con inyección de dependencias:

```
Capa de Rutas (main.py)
        │  Depende de →
Capa de Repositorio (repository.py)
        │  Depende de →
Capa de Acceso a Datos (dbconexion.py)
        │  Depende de →
Infraestructura (PostgreSQL + PgBouncer)
```

- **FastAPI `Depends()`** inyecta `UserRepository` en los handlers.
- **UserRepository** recibe una `AsyncSession` via `Depends(get_conexion)`.
- **get_conexion()** es un async generator que provee sesiones desde el pool de SQLAlchemy.
- **Conexion** es un singleton (caché via `@lru_cache`) que mantiene el engine asíncrono.

### 1.4 Decisiones Técnicas

| Decisión | Justificación |
|----------|---------------|
| **Async IO (asyncio)** | Máximo rendimiento para I/O bound (consultas a BD, red) |
| **PgBouncer transaction mode** | Pooling eficiente de conexiones TCP a PostgreSQL |
| **statement_cache_size=0** | Necesario para compatibilidad con PgBouncer (no soporta prepared statements entre transacciones) |
| **expire_on_commit=False** | Permite acceder a atributos de objetos ORM después del commit |
| **Secrets de Docker** | Las credenciales nunca se versionan ni quedan en la imagen |
| **Multi-stage Docker build** | Imagen final ~80% más pequeña al separar build de runtime |

---

## 2. Estructura del Proyecto

```
FastAPI/
│
├── main.py                        # Punto de entrada: app FastAPI, rutas, exception handler
├── schemas.py                     # Modelos Pydantic (Usuarios, UserCreate, UserUpdate)
├── repository.py                  # UserRepository (DAO), conexion singleton, get_conexion()
├── dbconexion.py                  # Clase Conexion: engine async + session factory
│
├── requirements.txt               # Dependencias Python (uvicorn, fastapi, sqlalchemy, asyncpg, alembic)
├── pyproject.toml                 # Configuración mypy (strict mode)
│
├── Dockerfile                     # Multi-stage build (builder → runtime)
├── stack.yaml                     # Stack de Docker Swarm (3 servicios)
├── pgbouncer.ini                  # Configuración de PgBouncer
├── userlist.txt                   # Usuarios PgBouncer (SCRAM-SHA-256)
├── lunch.sh                       # Script automatizado de despliegue
├── .dockerignore                  # Archivos excluidos del build Docker
│
├── alembicApi/                    # Migraciones de base de datos
│   ├── alembic.ini                # Configuración de Alembic
│   ├── models.py                  # Modelos SQLAlchemy (Base, User)
│   └── appapi/
│       ├── env.py                 # Entorno Alembic asíncrono
│       ├── script.py.mako         # Template para revisiones
│       └── versions/              # Revisiones de migración (vacío inicialmente)
│
├── docs/
│   └── documentation.md           # Esta documentación
│
└── .github/workflows/
    └── mypy.yml                   # CI: type checking con mypy
```

### 2.1 Descripción de Componentes Clave

| Archivo | Responsabilidad |
|---------|-----------------|
| `main.py` | Define la app FastAPI, configura el lifespan, registra el exception handler global y declara los 6 endpoints REST |
| `schemas.py` | Define los contratos de entrada/salida con Pydantic v2 |
| `repository.py` | Implementa el patrón Repository: encapsula la lógica de acceso a datos y expone métodos de negocio |
| `dbconexion.py` | Gestiona la conexión a PostgreSQL vía asyncpg con configuración específica para PgBouncer |
| `alembicApi/models.py` | Define el modelo ORM `User` que mapea a la tabla `users` |

---

## 3. Modelo de Datos

### 3.1 Tabla `users`

```sql
CREATE TABLE users (
    id      SERIAL       PRIMARY KEY,
    name    VARCHAR(70)  NOT NULL,
    cedula  VARCHAR(12)  NOT NULL UNIQUE
);
```

### 3.2 Modelo ORM (`alembicApi/models.py`)

```python
class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(70), nullable=False)
    cedula: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
```

### 3.3 Esquemas Pydantic (`schemas.py`)

| Clase | Ámbito | Campos | Validaciones |
|-------|--------|--------|-------------|
| `Usuarios` | Response | `id: int`, `name: str`, `cedula: str` | `from_attributes=True` (ORM mapping) |
| `UserCreate` | Request (POST) | `name: str`, `cedula: str` | Ambos requeridos |
| `UserUpdate` | Request (PATCH) | `name: str \| None`, `cedula: str \| None` | Todos opcionales (patch parcial) |

### 3.4 Reglas de Negocio

- La cédula es **unique** — no pueden existir dos usuarios con la misma cédula.
- El nombre tiene un máximo de **70 caracteres**.
- La cédula tiene un máximo de **12 caracteres**.
- Las actualizaciones son **parciales** (PATCH): solo se actualizan los campos enviados.

---

## 4. Referencia de la API

**Base URL (local):** `http://localhost:8000`
**Base URL (Swarm):** `http://<node-ip>:8000`

Formato de respuesta de error:

```json
{
  "detail": "Mensaje descriptivo del error"
}
```

---

### 4.1 `GET /` — Saludo

Devuelve un mensaje de bienvenida.

**Response `200`**

```
Hola Ing Yeison Ipia, mucho gusto
```

**Ejemplo:**
```bash
curl http://localhost:8000/
```

---

### 4.2 `GET /users` — Listar Usuarios

Devuelve el listado completo de usuarios registrados.

**Response `200`**
```json
[
  {
    "id": 1,
    "name": "Juan Pérez",
    "cedula": "1234567890"
  },
  {
    "id": 2,
    "name": "María Gómez",
    "cedula": "0987654321"
  }
]
```

**Ejemplo:**
```bash
curl http://localhost:8000/users
```

---

### 4.3 `GET /users/{id}` — Obtener Usuario por ID

**Parámetros**

| Nombre | Tipo | Ubicación | Obligatorio | Descripción |
|--------|------|-----------|-------------|-------------|
| `id` | `int` | Path | Sí | ID del usuario |

**Response `200`**
```json
{
  "id": 1,
  "name": "Juan Pérez",
  "cedula": "1234567890"
}
```

**Error `404`**
```json
{
  "detail": "Usuario no encontrado."
}
```

**Ejemplo:**
```bash
curl http://localhost:8000/users/1
```

---

### 4.4 `POST /users` — Crear Usuario

**Request Body**
```json
{
  "name": "Juan Pérez",
  "cedula": "1234567890"
}
```

**Response `201`**
```json
{
  "id": 1,
  "name": "Juan Pérez",
  "cedula": "1234567890"
}
```

**Error `400`** (cédula duplicada)
```json
{
  "detail": "La cedula ya esta registrada en la base de datos."
}
```

**Ejemplo:**
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Juan Pérez","cedula":"1234567890"}'
```

**Validaciones:**
- `name`: string, obligatorio, máximo 70 caracteres
- `cedula`: string, obligatorio, máximo 12 caracteres, debe ser único en el sistema

---

### 4.5 `PATCH /users/{id}` — Actualizar Usuario Parcialmente

**Parámetros**

| Nombre | Tipo | Ubicación | Obligatorio | Descripción |
|--------|------|-----------|-------------|-------------|
| `id` | `int` | Path | Sí | ID del usuario |

**Request Body** (ambos campos opcionales)
```json
{
  "name": "Juan Carlos Pérez"
}
```

**Response `200`**
```json
{
  "id": 1,
  "name": "Juan Carlos Pérez",
  "cedula": "1234567890"
}
```

**Error `404`**
```json
{
  "detail": "Usuario no encontrado."
}
```

**Ejemplo:**
```bash
curl -X PATCH http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Juan Carlos Pérez"}'
```

**Comportamiento:** Solo los campos presentes en el body son actualizados. Si no se envía ningún campo, la operación es un no-op (no hay cambios).

---

### 4.6 `DELETE /users/{id}` — Eliminar Usuario

**Parámetros**

| Nombre | Tipo | Ubicación | Obligatorio | Descripción |
|--------|------|-----------|-------------|-------------|
| `id` | `int` | Path | Sí | ID del usuario |

**Response `200`**
```json
null
```

**Error `404`**
```json
{
  "detail": "Usuario no encontrado."
}
```

**Ejemplo:**
```bash
curl -X DELETE http://localhost:8000/users/1
```

---

### 4.7 Manejador Global de Errores

Cualquier excepción no controlada en la aplicación es capturada por un handler global que retorna:

**Response `500`**
```json
{
  "detail": "Error interno del servidor"
}
```

Esto evita que se filtren detalles internos de la implementación al cliente.

---

## 5. Configuración y Desarrollo Local

### 5.1 Requisitos

- Python 3.12+
- PostgreSQL 16+ (accesible desde tu máquina)
- Docker (opcional, para despliegue en contenedores)
- Docker Swarm (opcional, para orquestación)

### 5.2 Desarrollo Local (sin Docker)

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd FastAPI

# 2. Crear y activar entorno virtual
python -m venv .env
source .env/bin/activate  # Linux/Mac
# .env\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar PostgreSQL local
#    Crea una base de datos llamada 'api' y un usuario con acceso

# 5. Configurar variables de entorno
#    Opción A: Crear archivo .envi (NO versionarlo)
cat > .envi << EOF
postgres_user=tu_usuario
postgres_password=tu_contraseña
postgres_host=localhost
postgres_db=api
EOF

#    Opción B: Crear secrets de Docker (si usas Docker local)
echo "tu_usuario" | docker secret create postgres_user -
echo "tu_contraseña" | docker secret create postgres_password -
echo "localhost" | docker secret create postgres_host -
echo "api" | docker secret create postgres_db -

# 6. Configurar PgBouncer local (opcional)
#    Si no tienes PgBouncer, modifica dbconexion.py para conectar
#    directamente a PostgreSQL en puerto 5432:
#    f'postgresql+asyncpg://{user}:{password}@{host}:5432/{db}'

# 7. Ejecutar migraciones
alembic -c alembicApi/alembic.ini upgrade head

# 8. Iniciar servidor de desarrollo
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 9. Verificar
curl http://localhost:8000/
```

### 5.3 Desarrollo con Docker (standalone)

```bash
# Construir imagen
docker build -t api-fast:v1 .

# Ejecutar contenedor (requiere secrets y BD accesible)
docker run -d \
  --name api-fast \
  -p 8000:8000 \
  --secret postgres_user \
  --secret postgres_password \
  --secret postgres_host \
  --secret postgres_db \
  api-fast:v1
```

### 5.4 Documentación Interactiva (Swagger UI)

FastAPI genera automáticamente documentación OpenAPI:

| Herramienta | URL |
|-------------|-----|
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |

Puedes probar todos los endpoints directamente desde el navegador.

### 5.5 Type Checking Local

```bash
# Instalar mypy si no está
pip install mypy

# Ejecutar análisis
mypy . --explicit-package-bases
```

---

## 6. Despliegue en Producción

### 6.1 Prerrequisitos

- Docker Engine 24+ con swarm mode inicializado
- Acceso a un registro de imágenes (o build local en cada nodo)
- 4 secrets de Docker creados (ver sección 6.3)
- Red overlay para la comunicación entre servicios

### 6.2 Inicializar Docker Swarm

```bash
# En el nodo manager
docker swarm init --advertise-addr <ip-manager>

# En cada nodo worker (unir al swarm)
docker swarm join --token <token> <ip-manager>:2377
```

### 6.3 Crear Secrets

```bash
echo "postgres_user_valor" | docker secret create postgres_user -
echo "postgres_password_valor" | docker secret create postgres_password -
echo "postgres_host_valor" | docker secret create postgres_host -
echo "postgres_db_valor" | docker secret create postgres_db -
```

Los secrets deben crearse **antes** de desplegar el stack. Docker Swarm los distribuye de forma segura solo a los servicios que los declaran.

### 6.4 Script de Despliegue (`lunch.sh`)

```bash
#!/usr/bin/env bash
set -e
set -a
source .envi          # 1. Carga credenciales desde archivo local
set +a

# 2. Crea secrets solo si no existen (idempotente)
docker secret inspect postgres_host >/dev/null 2>&1 || \
  echo "$postgres_host" | docker secret create postgres_host -
docker secret inspect postgres_user >/dev/null 2>&1 || \
  echo "$postgres_user" | docker secret create postgres_user -
docker secret inspect postgres_password >/dev/null 2>&1 || \
  echo "$postgres_password" | docker secret create postgres_password -
docker secret inspect postgres_db >/dev/null 2>&1 || \
  echo "$postgres_db" | docker secret create postgres_db -

docker build -t api-fast:v1 .   # 3. Construye imagen

sleep 5                         # 4. Espera a que build termine

docker stack deploy -c stack.yaml app   # 5. Despliega stack
```

**Uso:**
```bash
./lunch.sh
```

### 6.5 Verificar el Despliegue

```bash
# Estado del stack
docker stack services app

# Logs de la API
docker service logs app_api

# Verificar endpoint
curl http://<node-ip>:8000/users

# Escalar el servicio API
docker service scale app_api=3

# Actualizar imagen sin downtime
docker build -t api-fast:v2 .
docker service update --image api-fast:v2 app_api
```

---

## 7. Infraestructura Docker Swarm

### 7.1 Stack de Servicios (`stack.yaml`)

```yaml
services:
  data:
    image: postgres:18
    ports: [5432:5432]
    secrets: [postgres_user, postgres_password]
    environment:
      POSTGRES_USER_FILE: /run/secrets/postgres_user
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    volumes:
      - postgres:/var/lib/postgresql
    deploy:
      replicas: 1
      update_config:
        parallelism: 1
        delay: 5s
        order: start-first
        failure_action: rollback

  pgbouncer:
    image: edoburu/pgbouncer:latest
    ports: [6432:6432]
    volumes:
      - ./pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini
      - ./userlist.txt:/etc/pgbouncer/userlist.txt

  api:
    image: api-fast:v1
    ports: [8000:8000]
    secrets:
      - postgres_user
      - postgres_password
      - postgres_host
      - postgres_db
    deploy:
      replicas: 1
      update_config:
        parallelism: 1
        delay: 5s
        order: start-first
        failure_action: rollback
```

### 7.2 Servicios

| Servicio | Imagen | Puerto Expuesto | Propósito |
|----------|--------|----------------|-----------|
| `app_data` | postgres:18 | 5432 | Almacenamiento persistente de datos |
| `app_pgbouncer` | edoburu/pgbouncer | 6432 | Pool de conexiones, reduce overhead TCP |
| `app_api` | api-fast:v1 | 8000 | API FastAPI (escalable horizontalmente) |

### 7.3 Red

```yaml
networks:
  net_api:
    driver: overlay
    ipam:
      config:
        - subnet: 10.10.10.0/28
```

Todos los servicios comparten la red overlay `net_api` (subred `10.10.10.0/28`), lo que permite comunicación interna por nombre de servicio.

### 7.4 Estrategia de Actualización

```yaml
update_config:
  parallelism: 1       # Actualizar 1 réplica a la vez
  delay: 5s            # Esperar 5s entre réplicas
  order: start-first   # Iniciar nueva antes de detener vieja (zero-downtime)
  failure_action: rollback  # Revertir si falla
```

### 7.5 Configuración de PgBouncer

```ini
[databases]
api = host=app_data port=5432 dbname=api

[pgbouncer]
listen_addr = *
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
min_pool_size = 5
max_prepared_statements = 100
```

| Parámetro | Valor | Explicación |
|-----------|-------|-------------|
| `pool_mode = transaction` | Mantiene la conexión durante una transacción, luego la devuelve al pool |
| `default_pool_size = 20` | Conexiones por pool de base de datos |
| `min_pool_size = 5` | Conexiones mantenidas abiertas incluso sin carga |
| `max_client_conn = 1000` | Máximo de conexiones cliente simultáneas |
| `max_prepared_statements = 100` | Crítico para asyncpg: permite prepared statements |

### 7.6 Volumen Persistente

```yaml
volumes:
  postgres:
    name: postgres
```

Los datos de PostgreSQL persisten en un volumen Docker nombrado, independiente del ciclo de vida del contenedor.

---

## 8. Migraciones con Alembic

### 8.1 Configuración

Las migraciones están configuradas para ejecutarse en **modo asíncrono** con `asyncpg`. La configuración (`alembicApi/appapi/env.py`) lee las credenciales desde Docker secrets.

### 8.2 Comandos Útiles

```bash
# Generar una nueva migración (autogenerate)
alembic -c alembicApi/alembic.ini revision --autogenerate -m "crear_tabla_usuarios"

# Aplicar migraciones pendientes
alembic -c alembicApi/alembic.ini upgrade head

# Revertir la última migración
alembic -c alembicApi/alembic.ini downgrade -1

# Ver historial de migraciones
alembic -c alembicApi/alembic.ini history

# Ver estado actual
alembic -c alembicApi/alembic.ini current

# SQL sin ejecutar (modo offline)
alembic -c alembicApi/alembic.ini upgrade head --sql
```

### 8.3 Notas Importantes

- El directorio `alembicApi/appapi/versions/` está actualmente vacío. La primera migración debe generarse antes del despliegue.
- Los comandos deben ejecutarse en un entorno donde los secrets de Docker estén disponibles, o modificando `env.py` para leer de variables de entorno en desarrollo.

---

## 9. Integración Continua (CI/CD)

### 9.1 Workflow: Type Checking

```yaml
# .github/workflows/mypy.yml
name: Type Checking
on: [push, pull_request]

jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          pip install mypy fastapi pydantic sqlalchemy psycopg2-binary
      - run: mypy . --explicit-package-bases
```

### 9.2 Cobertura

- **Evento:** Se ejecuta en cada `push` y `pull request` hacia cualquier rama.
- **Python:** 3.12
- **Herramienta:** mypy con `strict = true` (configurado en `pyproject.toml`)
- **Comando:** `mypy . --explicit-package-bases`

### 9.3 Mejoras Sugeridas para CI/CD

- Agregar job de pruebas unitarias (cuando existan)
- Agregar job de linting (ruff o flake8)
- Agregar build y push automático de imagen Docker a un registro
- Agregar deploy automático al swarm al hacer merge a `main`

---

## 10. Seguridad

### 10.1 Docker Secrets

Todas las credenciales de base de datos se manejan mediante **Docker secrets**:
- Los secrets se montan como archivos en `/run/secrets/` dentro del contenedor
- Nunca quedan hardcodeados en el código ni en la imagen Docker
- Solo los servicios que declaran un secret pueden acceder a él
- Los secrets se cifran durante el almacenamiento y la transmisión en el swarm

```python
# Lectura de secret en repository.py
with open('/run/secrets/postgres_user') as f:
    db_user = f.read().strip()
```

### 10.2 Usuario no Privilegiado

El contenedor runtime ejecuta la aplicación con un usuario sin privilegios:

```dockerfile
RUN useradd -m appuser
USER appuser
```

### 10.3 Autenticación PgBouncer

PgBouncer utiliza `scram-sha-256` como método de autenticación, el estándar más seguro de PostgreSQL para almacenamiento y transmisión de contraseñas.

### 10.4 Manejador Global de Excepciones

Todas las excepciones no controladas son capturadas y devuelven un mensaje genérico, evitando la fuga de información interna.

### 10.5 Recomendaciones Adicionales

- Agregar HTTPS con un reverse proxy (Traefik, Nginx) y Let's Encrypt
- Implementar rate limiting para prevenir abusos
- Agregar autenticación/autorización (JWT, OAuth2) para proteger los endpoints
- Configurar firewalls para restringir acceso a los puertos de BD y PgBouncer
- Rotar los secrets periódicamente
- Agregar logging estructurado para auditoría

---

## 11. Troubleshooting

### 11.1 Error: Conexión a BD rechazada

**Síntoma:** `Can't connect to PostgreSQL server` o `Connection refused`

**Causas y soluciones:**

| Causa | Solución |
|-------|----------|
| PgBouncer no está corriendo | `docker service logs app_pgbouncer` |
| PostgreSQL no está listo | Esperar a que termine init, verificar con `docker service logs app_data` |
| Host incorrecto en secret | Verificar `postgres_host`: debe ser `app_data` dentro del stack |
| Puerto incorrecto | La API conecta a `:6432` (PgBouncer), no `:5432` directamente |

### 11.2 Error: "La cedula ya esta registrada"

**Causa:** Se intenta crear un usuario con una cédula que ya existe en la BD. La columna `cedula` tiene restricción `UNIQUE`.

**Solución:** Verificar que la cédula no exista previamente:

```bash
curl http://localhost:8000/users | jq '.[] | select(.cedula=="VALOR")'
```

### 11.3 Error: 404 "Usuario no encontrado"

**Causa:** El ID proporcionado no corresponde a ningún usuario en la BD.

**Solución:** Listar usuarios para verificar IDs disponibles:

```bash
curl http://localhost:8000/users
```

### 11.4 Error: mypy falla en CI

**Solución:** Ejecutar localmente para ver errores:

```bash
mypy . --explicit-package-bases
```

Los errores más comunes incluyen:
- Falta de anotaciones de tipo
- Importaciones sin stub
- Incompatibilidad de tipos entre Pydantic y SQLAlchemy

### 11.5 Error: "No running migrations to apply"

**Causa:** No hay migraciones pendientes o el directorio `versions/` está vacío.

**Solución:** Generar la primera migración:

```bash
alembic -c alembicApi/alembic.ini revision --autogenerate -m "initial"
alembic -c alembicApi/alembic.ini upgrade head
```

### 11.6 Logs Útiles

```bash
# API
docker service logs app_api

# PgBouncer
docker service logs app_pgbouncer

# PostgreSQL
docker service logs app_data

# Seguir logs en tiempo real
docker service logs -f app_api
```

---

## 12. Roadmap / Trabajo Futuro

| Área | Mejora Propuesta |
|------|------------------|
| **Pruebas** | Agregar tests unitarios (pytest + httpx.AsyncClient) y tests de integración con BD de prueba |
| **Autenticación** | Implementar JWT o OAuth2 para proteger endpoints |
| **Documentación interactiva** | Personalizar OpenAPI con descripciones, tags y ejemplos |
| **CI/CD** | Agregar jobs de pruebas, linting, build y push de imagen |
| **Migraciones** | Generar la migración inicial y versionar la BD |
| **Logging** | Implementar logging estructurado (structlog, loguru) con niveles y trazabilidad |
| **Health Check** | Agregar endpoint `/health` para readiness/liveness probes |
| **Rate Limiting** | Proteger contra abusos con slowapi o similar |
| **Múltiples recursos** | Extender el CRUD a otras entidades (ej. productos, órdenes) |
| **docker-compose** | Agregar docker-compose.yml para desarrollo local simplificado |

---

## Apéndice A: Variables de Entorno y Secrets

| Variable / Secret | Descripción | ¿Secreta? | Lectura |
|-------------------|-------------|-----------|---------|
| `postgres_user` | Usuario de BD | Sí | Docker secret |
| `postgres_password` | Contraseña de BD | Sí | Docker secret |
| `postgres_host` | Host de BD (nombre del servicio Docker) | Sí | Docker secret |
| `postgres_db` | Nombre de la base de datos | Sí | Docker secret |

## Apéndice B: Dependencias (`requirements.txt`)

| Paquete | Versión Mínima | Propósito |
|---------|---------------|-----------|
| `uvicorn` | — | Servidor ASGI para servir FastAPI |
| `fastapi` | — | Framework web |
| `sqlalchemy` | 2.x | ORM y core SQL asíncrono |
| `asyncpg` | — | Driver PostgreSQL asíncrono |
| `alembic` | — | Migraciones de base de datos |
| `psycopg2-binary` | — | Driver sync (disponible, no usado directamente) |
| `python-multipart` | — | Soporte para formularios (no usado actualmente) |

---

*Documentación generada para ApiFastApi — © Ing Yeison Ipia*
+