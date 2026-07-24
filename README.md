# ApiFastApi

API RESTful completa y profesional para la gestión de usuarios, construida con **FastAPI**, **SQLAlchemy** (asíncrono), **PostgreSQL** y **PgBouncer**, diseñada para desplegarse en **Docker Swarm**.

## Características

- CRUD completo de usuarios (crear, leer, actualizar, eliminar)
- Conexión asíncrona a PostgreSQL vía asyncpg
- Pool de conexiones con PgBouncer (transaction mode)
- Migraciones de base de datos con Alembic
- Despliegue en Docker Swarm con secrets
- Multi-stage Docker build (imagen optimizada)
- Type checking estricto con mypy (CI/CD)

## Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x (asíncrono) |
| DB | PostgreSQL 18 |
| Pooler | PgBouncer |
| Migraciones | Alembic |
| ASGI Server | Uvicorn |
| Contenedor | Docker / Docker Swarm |
| CI/CD | GitHub Actions (mypy) |

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Saludo |
| GET | `/users` | Listar usuarios |
| GET | `/users/{id}` | Obtener usuario por ID |
| POST | `/users` | Crear usuario |
| PATCH | `/users/{id}` | Actualizar parcialmente |
| DELETE | `/users/{id}` | Eliminar usuario |

## Despliegue rápido

```bash
# 1. Configurar credenciales en .envi
# 2. Crear secrets y desplegar
./lunch.sh
```

## Autor

**Ing Yeison Ipia**
