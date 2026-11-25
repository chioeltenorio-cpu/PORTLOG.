# PORTLOG

## Sistema de Gestión de Logística Portuaria

## 1. Descripción del proyecto

PORTLOG es un sistema web de gestión de logística portuaria desarrollado
mediante una arquitectura de microservicios. Permite administrar
contenedores y registrar operaciones como entradas, salidas y
liberaciones aduanales. Contempla dos roles: agente aduanal y
transportista, con permisos específicos.

## 2. Objetivo

Desarrollar una aplicación web para gestionar operaciones de logística
portuaria de forma organizada y segura, separando responsabilidades en
servicios independientes.

## 3. Tecnologías

-   Backend: Python y Flask.
-   Frontend: HTML, CSS y JavaScript.
-   Bases de datos: SQLite.
-   Comunicación: API REST mediante HTTP.
-   Arquitectura: microservicios.

## 4. Arquitectura

  Componente             Puerto Responsabilidad
  -------------------- -------- ---------------------------------------------
  Frontend                 5500 Interfaz web
  API Gateway              5000 Punto de entrada, validación y enrutamiento
  Auth Service             5001 Registro, autenticación y sesiones
  Inventory Service        5002 Administración de contenedores
  Operations Service       5003 Movimientos y estado operativo

Cada microservicio utiliza una base SQLite independiente: `auth.db`,
`inventory.db` y `operations.db`. El frontend se comunica con el
Gateway. Operations consulta Inventory mediante HTTP.

Diagrama: `docs/arquitectura_portlog.png`

![Arquitectura de PORTLOG](docs/arquitectura_portlog.png)

## 5. Estructura del proyecto

``` text
PORTLOG/
├── api_gateway/
│   └── app.py
├── auth_service/
│   ├── data/
│   │   └── auth.db
│   └── app.py
├── inventory_service/
│   ├── data/
│   │   └── inventory.db
│   └── app.py
├── operations_service/
│   ├── data/
│   │   └── operations.db
│   └── app.py
├── database/
├── docs/
│   ├── API.md
│   ├── arquitectura_portlog.png
│   └── evidencias/
├── frontend/
│   ├── css/
│   ├── js/
│   └── index.html
├── requirements.txt
├── iniciar_portlog.sh
├── README.md
└── venv/  (solo entorno local; no subir a Git)
```

Actualiza este árbol si cambia la estructura o si alguno de los archivos
indicados no se incluye en la entrega.

## 6. Funcionalidades

**Autenticación** - Registro e inicio/cierre de sesión. - Validación de
usuarios y sesiones mediante tokens.

**Inventario** - Consulta, registro, búsqueda y actualización de
contenedores.

**Operaciones** - Registro de entradas, salidas y liberaciones
aduanales. - Consulta del historial y del estado operativo.

**Seguridad** - Validación de tokens en el Gateway. - Autorización
basada en roles y validación también en el backend.

## 7. Roles y permisos

  Funcionalidad                      Agente aduanal   Transportista
  ---------------------------------- ---------------- ---------------
  Consultar contenedores             Sí               Sí
  Registrar contenedores             Sí               No
  Editar contenedores                Sí               No
  Consultar movimientos              Sí               Sí
  Registrar entradas y salidas       No               Sí
  Registrar liberaciones aduanales   Sí               No

## 8. Requisitos previos

-   Python 3.
-   pip.
-   Navegador web.
-   Terminal.
-   Visual Studio Code u otro editor (opcional).

Los comandos de esta guía están orientados a macOS/Linux. El entorno de
desarrollo utilizado durante las pruebas fue Python 3.12.5.

## 9. Instalación y configuración

### 9.1 Obtener el proyecto

Clona el repositorio o descarga el código fuente. Después entra a la
carpeta del proyecto:

``` bash
cd PORTLOG
```

### 9.2 Crear y activar el entorno virtual

Para una instalación nueva:

``` bash
python3 -m venv venv
source venv/bin/activate
```

Si el entorno ya existe:

``` bash
source venv/bin/activate
```

### 9.3 Instalar dependencias

``` bash
pip install -r requirements.txt
```

El archivo `requirements.txt` registra las dependencias principales:
Flask, requests, Flask-Cors y python-dotenv.

### 9.4 Bases de datos

El proyecto utiliza estas bases SQLite:

-   `auth_service/data/auth.db`
-   `inventory_service/data/inventory.db`
-   `operations_service/data/operations.db`

Conserva la estructura de carpetas y los archivos de base de datos de la
versión local. Antes de distribuir una instalación limpia, verifica en
cada microservicio cómo se inicializan las tablas y si las bases se
crean automáticamente al arrancar. No publiques bases con información
personal, credenciales reales, tokens o datos privados; utiliza datos de
prueba.

### 9.5 Configuración

En el Gateway revisado, las direcciones de los servicios están definidas
en el diccionario `SERVICIOS`:

``` python
SERVICIOS = {
    "auth": "http://127.0.0.1:5001",
    "inventory": "http://127.0.0.1:5002",
    "operations": "http://127.0.0.1:5003"
}
```

En los fragmentos revisados no se identificaron variables de entorno
obligatorias para estas direcciones. Si se agregan variables o secretos
en otra versión, documenta sus nombres en `.env.example` y no publiques
el `.env` real.

## 10. Ejecución automática

Desde la carpeta principal, activa el entorno virtual y concede permiso
de ejecución al script:

``` bash
source venv/bin/activate
chmod +x iniciar_portlog.sh
```

Inicia los servicios:

``` bash
./iniciar_portlog.sh
```

El script inicia Auth, Inventory, Operations, API Gateway y el servidor
del frontend. Abre:

`http://127.0.0.1:5500`

Para detener el conjunto, presiona `Ctrl + C` en la terminal donde
ejecutaste el script. No lo ejecutes si ya hay procesos ocupando los
puertos 5000, 5001, 5002, 5003 o 5500.

## 11. Ejecución manual

Como alternativa, inicia cada componente en una terminal independiente
desde la raíz del proyecto, con el entorno virtual activado.

**Terminal 1 -- Auth**

``` bash
python auth_service/app.py
```

**Terminal 2 -- Inventory**

``` bash
python inventory_service/app.py
```

**Terminal 3 -- Operations**

``` bash
python operations_service/app.py
```

**Terminal 4 -- API Gateway**

``` bash
python api_gateway/app.py
```

**Terminal 5 -- Frontend**

``` bash
cd frontend
python -m http.server 5500
```

Abre `http://127.0.0.1:5500` y mantén las terminales abiertas mientras
utilizas el sistema.

## 12. Verificación

Gateway: `http://127.0.0.1:5000/health`

Rutas de salud a través del Gateway: - `/api/auth/health` -
`/api/inventory/health` - `/api/operations/health`

Las rutas de Inventory y Operations pasan por la validación de token del
Gateway en la implementación actual.

## 13. Documentación de API

La documentación de rutas, métodos, autenticación y respuestas se
encuentra en [`docs/API.md`](docs/API.md).

Rutas generales del Gateway: - `/api/auth/...` - `/api/inventory/...` -
`/api/operations/...`

Mantén `docs/API.md` sincronizado con las rutas reales del código.

## 14. Seguridad y pruebas

El Gateway valida los tokens consultando Auth y verifica los permisos
antes de reenviar solicitudes protegidas a Inventory u Operations.

Durante las pruebas se comprobó: - Inicio de sesión de agente aduanal y
transportista. - Consulta de contenedores y movimientos. - Registro de
liberación aduanal por el agente. - Registro de entradas y salidas por
el transportista. - Restricciones de registro y edición de contenedores
según el rol. - Rechazo de una liberación aduanal solicitada por un
transportista, con HTTP 403.

## 15. Evidencias

Organiza las capturas reales en `docs/evidencias/`. Se sugieren estos
nombres:

-   `01_login_agente.png`
-   `02_login_transportista.png`
-   `03_inventario.png`
-   `04_liberacion_aduanal.png`
-   `05_entrada_transportista.png`
-   `06_salida_transportista.png`
-   `07_bloqueo_http_403.png`
-   `08_servicios_activos.png`

No incluyas contraseñas ni tokens en las capturas.

## 16. Conclusión

PORTLOG demuestra una aplicación web basada en microservicios para la
gestión de logística portuaria. La separación de autenticación,
inventario y operaciones distribuye las responsabilidades, mientras que
el API Gateway centraliza las solicitudes y aplica controles de acceso
por roles. La aplicación integra una interfaz web, servicios REST
independientes y bases de datos SQLite separadas, además de
instrucciones de ejecución manual y automatizada para el entorno local.
