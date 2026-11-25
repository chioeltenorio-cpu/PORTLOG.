# PORTLOG – Documentación de API REST

## 1. Introducción

PORTLOG utiliza una arquitectura de microservicios comunicados mediante API REST. El API Gateway funciona como punto central de acceso entre el frontend y los servicios internos.

**Dirección del Gateway:** `http://127.0.0.1:5000`

## 2. Microservicios

| Servicio | Dirección | Puerto |
|---|---|---:|
| API Gateway | http://127.0.0.1:5000 | 5000 |
| Auth | http://127.0.0.1:5001 | 5001 |
| Inventory | http://127.0.0.1:5002 | 5002 |
| Operations | http://127.0.0.1:5003 | 5003 |

## 3. Autenticación

Las rutas de inventario y operaciones requieren autenticación mediante un token Bearer.

Cabecera HTTP:

```http
Authorization: Bearer TOKEN
```

El token se obtiene mediante el inicio de sesión en Auth Service.

## 4. Endpoints del API Gateway

### 4.1 Autenticación

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/auth/health` | Verificar Auth |
| POST | `/api/auth/register` | Registrar usuario |
| POST | `/api/auth/login` | Iniciar sesión |
| GET | `/api/auth/me` | Consultar sesión |
| POST | `/api/auth/logout` | Cerrar sesión |

### 4.2 Inventario

| Método | Endpoint | Permiso |
|---|---|---|
| GET | `/api/inventory/health` | Requiere token |
| GET | `/api/inventory/containers` | Ambos roles |
| POST | `/api/inventory/containers` | Agente aduanal |
| GET | `/api/inventory/containers/<numero>` | Ambos roles |
| PUT | `/api/inventory/containers/<numero>` | Agente aduanal |

### 4.3 Operaciones

| Método | Endpoint | Permiso |
|---|---|---|
| GET | `/api/operations/health` | Requiere token |
| GET | `/api/operations/movements` | Ambos roles |
| POST | `/api/operations/movements` | Según tipo de operación |
| GET | `/api/operations/containers/<numero>/status` | Ambos roles |

Los permisos para registrar movimientos son:

- Agente aduanal: liberación aduanal.
- Transportista: entrada y salida.

## 5. Ejemplos de solicitudes

### Inicio de sesión

**POST** `/api/auth/login`

```json
{
  "correo": "usuario@portlog.com",
  "password": "contraseña"
}
```

### Registrar contenedor

**POST** `/api/inventory/containers`

Requiere token de agente aduanal.

### Registrar movimiento

**POST** `/api/operations/movements`

```json
{
  "numero": "MSCU1234567",
  "tipo_operacion": "entrada",
  "observaciones": "Ingreso de contenedor"
}
```

El tipo de operación debe corresponder al rol autorizado.

## 6. Códigos de respuesta HTTP

| Código | Descripción |
|---|---|
| 200 | Solicitud procesada correctamente |
| 201 | Recurso creado correctamente |
| 204 | Solicitud OPTIONS procesada |
| 400 | Datos incorrectos |
| 401 | No autenticado |
| 403 | Permisos insuficientes |
| 404 | Recurso o servicio no encontrado |
| 409 | Conflicto de datos u operación |
| 502 | Error de comunicación |
| 503 | Microservicio no disponible |
| 504 | Tiempo de espera agotado |

## 7. Comunicación entre servicios

El frontend se comunica exclusivamente con el API Gateway. Este valida las sesiones y permisos, y posteriormente distribuye las solicitudes al microservicio correspondiente.

Operations Service también consulta Inventory Service mediante HTTP para verificar la existencia de los contenedores.

## 8. Seguridad

PORTLOG implementa autenticación mediante tokens, validación de sesiones y autorización basada en roles. El API Gateway verifica los permisos antes de reenviar las solicitudes protegidas.