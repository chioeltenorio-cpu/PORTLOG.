
// ==========================================
// PORTLOG - CONFIGURACION GENERAL
// ==========================================

const API_URL = "http://127.0.0.1:5000";

let tokenSesion = sessionStorage.getItem("portlog_token");
let usuarioActual = null;


// ==========================================
// FUNCIONES AUXILIARES
// ==========================================

function escapar(valor) {
    return String(valor ?? "").replace(/[&<>"']/g, caracter => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[caracter]);
}


async function leerRespuesta(respuesta) {
    try {
        return await respuesta.json();
    } catch {
        return {};
    }
}


// ==========================================
// MOSTRAR PANTALLAS
// ==========================================

function mostrarLogin() {

    document.getElementById("pantallaLogin").hidden = false;
    document.getElementById("aplicacion").hidden = true;

    usuarioActual = null;
}


function mostrarAplicacion() {

    document.getElementById("pantallaLogin").hidden = true;
    document.getElementById("aplicacion").hidden = false;
}


// ==========================================
// CONTROL DE PERMISOS VISUALES
// ==========================================

function aplicarPermisos() {

    if (!usuarioActual) return;

    const rol = usuarioActual.rol;

    document.querySelectorAll("[data-role]").forEach(elemento => {

        const rolesPermitidos = elemento.dataset.role
            .split(",")
            .map(valor => valor.trim());

        elemento.hidden = !rolesPermitidos.includes(rol);

    });

    const nombre = document.getElementById("nombreUsuario");
    const rolElemento = document.getElementById("rolUsuario");

    if (nombre) {
        nombre.textContent =
            usuarioActual.nombre || usuarioActual.correo || "Usuario";
    }

    if (rolElemento) {

        rolElemento.textContent =
            rol === "agente_aduanal"
                ? "Agente aduanal"
                : "Transportista";
    }
}


// ==========================================
// PETICIONES AUTENTICADAS AL GATEWAY
// ==========================================

async function apiFetch(ruta, opciones = {}) {

    const headers = {
        ...(opciones.headers || {})
    };

    if (tokenSesion) {
        headers["Authorization"] = `Bearer ${tokenSesion}`;
    }

    const respuesta = await fetch(
        `${API_URL}${ruta}`,
        {
            ...opciones,
            headers
        }
    );

    if (respuesta.status === 401 && tokenSesion) {

        cerrarSesionLocal();

        throw new Error(
            "Tu sesión ha expirado. Inicia sesión nuevamente."
        );
    }

    return respuesta;
}


// ==========================================
// CONSULTAR API
// ==========================================

async function consultarAPI(ruta) {

    const respuesta = await apiFetch(ruta);

    const datos = await leerRespuesta(respuesta);

    if (!respuesta.ok) {
        throw new Error(
            datos.error || `Error HTTP ${respuesta.status}`
        );
    }

    return datos;
}


// ==========================================
// INICIAR SESION
// ==========================================

async function iniciarSesion(evento) {

    evento.preventDefault();

    const correo = document.getElementById("correoLogin").value.trim();
    const password = document.getElementById("passwordLogin").value;

    const mensaje = document.getElementById("mensajeLogin");
    const boton = document.getElementById("btnLogin");

    mensaje.textContent = "";
    boton.disabled = true;
    boton.textContent = "Verificando...";

    try {

        // Solicitar autenticacion al microservicio Auth

        const respuesta = await fetch(
            `${API_URL}/api/auth/login`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    correo,
                    password
                })
            }
        );

        const datos = await leerRespuesta(respuesta);

        if (!respuesta.ok) {
            throw new Error(
                datos.error || "Correo o contraseña incorrectos"
            );
        }

        if (!datos.token) {
            throw new Error("Auth no devolvió un token de sesión");
        }

        // Guardar token temporalmente

        tokenSesion = datos.token;

        sessionStorage.setItem("portlog_token", tokenSesion);

        // Consultar identidad y rol del usuario

        const perfil = await consultarAPI("/api/auth/me");

        usuarioActual = perfil.usuario || perfil;

        if (
            !usuarioActual.rol ||
            !["agente_aduanal", "transportista"].includes(usuarioActual.rol)
        ) {
            throw new Error("El usuario tiene un rol no reconocido");
        }

        // Mostrar aplicación

        aplicarPermisos();
        mostrarAplicacion();

        document.getElementById("formLogin").reset();

        await actualizarDashboard();

    } catch (error) {

        mensaje.textContent = error.message;
        mensaje.style.color = "#dc2626";

        console.error("Error de inicio de sesión:", error);

        cerrarSesionLocal();

    } finally {

        boton.disabled = false;
        boton.textContent = "Iniciar sesión";
    }
}


// ==========================================
// RESTAURAR SESION EXISTENTE
// ==========================================

async function restaurarSesion() {

    if (!tokenSesion) {
        mostrarLogin();
        return;
    }

    try {

        const perfil = await consultarAPI("/api/auth/me");

        usuarioActual = perfil.usuario || perfil;

        if (
            !usuarioActual.rol ||
            !["agente_aduanal", "transportista"].includes(usuarioActual.rol)
        ) {
            throw new Error("Rol de usuario no válido");
        }

        aplicarPermisos();
        mostrarAplicacion();

        await actualizarDashboard();

    } catch (error) {

        console.error("No se pudo restaurar la sesión:", error);

        cerrarSesionLocal();
    }
}


// ==========================================
// CERRAR SESION
// ==========================================

async function cerrarSesion() {

    if (tokenSesion) {

        try {

            await fetch(
                `${API_URL}/api/auth/logout`,
                {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${tokenSesion}`
                    }
                }
            );

        } catch (error) {

            console.error("Error al cerrar sesión:", error);
        }
    }

    cerrarSesionLocal();
}


function cerrarSesionLocal() {

    sessionStorage.removeItem("portlog_token");

    tokenSesion = null;
    usuarioActual = null;

    mostrarLogin();

    const mensaje = document.getElementById("mensajeLogin");

    if (mensaje) {
        mensaje.textContent = "";
    }
}


// ==========================================
// VERIFICAR ESTADO DE MICROSERVICIOS
// ==========================================

async function verificarServicios() {

    const servicios = [
        {
            ruta: "/api/auth/health",
            elemento: "estadoAuth"
        },
        {
            ruta: "/api/inventory/containers",
            elemento: "estadoInventario"
        },
        {
            ruta: "/api/operations/movements",
            elemento: "estadoOperaciones"
        }
    ];

    for (const servicio of servicios) {

        const elemento = document.getElementById(servicio.elemento);

        if (!elemento) continue;

        try {

            await consultarAPI(servicio.ruta);

            elemento.textContent = "Disponible";
            elemento.className = "disponible";

        } catch (error) {

            elemento.textContent = "No disponible";
            elemento.className = "no-disponible";
        }
    }
}


// ==========================================
// CARGAR INVENTARIO
// ==========================================

async function cargarContenedores() {

    const tabla = document.getElementById("tablaContenedores");

    if (!tabla) return;

    try {

        const datos = await consultarAPI("/api/inventory/containers");

        const contenedores = datos.contenedores || [];

        const total = document.getElementById("totalContenedores");

        if (total) {
            total.textContent = datos.total ?? contenedores.length;
        }

        tabla.innerHTML = "";

        if (contenedores.length === 0) {

            tabla.innerHTML = `
                <tr>
                    <td colspan="7">No hay contenedores registrados</td>
                </tr>
            `;

            return;
        }

        contenedores.forEach(contenedor => {

            const fila = document.createElement("tr");

            const botonEditar =
                usuarioActual?.rol === "agente_aduanal"
                    ? `
                        <button
                            type="button"
                            class="btn-editar"
                            data-numero="${escapar(contenedor.numero)}">
                            Editar
                        </button>
                    `
                    : "Sin permisos";

            fila.innerHTML = `
                <td>${escapar(contenedor.numero)}</td>
                <td>${escapar(contenedor.origen)}</td>
                <td>${escapar(contenedor.destino)}</td>
                <td>${escapar(contenedor.tipo)}</td>
                <td>${escapar(contenedor.transportista)}</td>
                <td>${escapar(contenedor.estado)}</td>
                <td>${botonEditar}</td>
            `;

            tabla.appendChild(fila);
        });

    } catch (error) {

        tabla.innerHTML = `
            <tr>
                <td colspan="7">No se pudo cargar el inventario</td>
            </tr>
        `;

        console.error("Error de inventario:", error);
    }
}


// ==========================================
// CARGAR MOVIMIENTOS
// ==========================================

async function cargarMovimientos() {

    const tabla = document.getElementById("tablaMovimientos");

    if (!tabla) return;

    try {

        const datos = await consultarAPI("/api/operations/movements");

        const movimientos = datos.movimientos || [];

        const totalMovimientos =
            document.getElementById("totalMovimientos");

        const totalEntradas =
            document.getElementById("totalEntradas");

        const totalSalidas =
            document.getElementById("totalSalidas");

        if (totalMovimientos) {
            totalMovimientos.textContent =
                datos.total ?? movimientos.length;
        }

        const entradas = movimientos.filter(
            movimiento => movimiento.tipo_operacion === "entrada"
        ).length;

        const salidas = movimientos.filter(
            movimiento => movimiento.tipo_operacion === "salida"
        ).length;

        if (totalEntradas) totalEntradas.textContent = entradas;
        if (totalSalidas) totalSalidas.textContent = salidas;

        tabla.innerHTML = "";

        if (movimientos.length === 0) {

            tabla.innerHTML = `
                <tr>
                    <td colspan="4">No hay movimientos registrados</td>
                </tr>
            `;

            return;
        }

        movimientos.forEach(movimiento => {

            const fila = document.createElement("tr");
            const fecha = new Date(movimiento.fecha);

            fila.innerHTML = `
                <td>${escapar(movimiento.numero_contenedor)}</td>
                <td>${escapar(movimiento.tipo_operacion)}</td>
                <td>${escapar(movimiento.observaciones)}</td>
                <td>
                    ${
                        Number.isNaN(fecha.getTime())
                            ? "Fecha no válida"
                            : escapar(fecha.toLocaleString("es-MX"))
                    }
                </td>
            `;

            tabla.appendChild(fila);
        });

    } catch (error) {

        tabla.innerHTML = `
            <tr>
                <td colspan="4">No se pudo cargar el historial</td>
            </tr>
        `;

        console.error("Error de operaciones:", error);
    }
}


// ==========================================
// ACTUALIZAR DASHBOARD
// ==========================================

async function actualizarDashboard() {

    if (!usuarioActual || !tokenSesion) return;

    const gateway = document.getElementById("estadoGateway");
    const mensaje = document.getElementById("mensajeGeneral");

    if (gateway) {
        gateway.textContent = "Verificando...";
    }

    try {

        await consultarAPI("/health");

        if (gateway) {
            gateway.textContent = "API Gateway conectado";
            gateway.className = "estado-badge conectado";
        }

    } catch (error) {

        if (gateway) {
            gateway.textContent = "API Gateway desconectado";
            gateway.className = "estado-badge desconectado";
        }

        if (mensaje) {
            mensaje.textContent = "No se pudo conectar con el API Gateway.";
        }

        console.error("Error del API Gateway:", error);

        return;
    }

    await verificarServicios();

    await Promise.all([
        cargarContenedores(),
        cargarMovimientos()
    ]);

    if (mensaje) {
        mensaje.textContent = "Información actualizada correctamente.";
    }
}


// ==========================================
// REGISTRAR NUEVO CONTENEDOR
// ==========================================

async function registrarContenedor(evento) {

    evento.preventDefault();

    if (usuarioActual?.rol !== "agente_aduanal") {
        alert("No tienes permisos para registrar contenedores.");
        return;
    }

    const mensaje = document.getElementById("mensajeRegistro");

    const datos = {
        numero: document.getElementById("numero").value.trim(),
        descripcion: document.getElementById("descripcion").value.trim(),
        tipo: document.getElementById("tipo").value,
        peso_kg: Number(document.getElementById("peso_kg").value),
        transportista: document.getElementById("transportista").value.trim(),
        origen: document.getElementById("origen").value.trim(),
        destino: document.getElementById("destino").value.trim()
    };

    try {

        const respuesta = await apiFetch(
            "/api/inventory/containers",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(datos)
            }
        );

        const resultado = await leerRespuesta(respuesta);

        if (!respuesta.ok) {
            throw new Error(resultado.error || "Error al registrar");
        }

        mensaje.textContent = resultado.mensaje;
        mensaje.style.color = "green";

        document.getElementById("formContenedor").reset();

        await actualizarDashboard();

    } catch (error) {

        mensaje.textContent = error.message;
        mensaje.style.color = "red";

        console.error("Error al registrar contenedor:", error);
    }
}


// ==========================================
// BUSCAR CONTENEDOR
// ==========================================

async function buscarContenedor() {

    const numero = document.getElementById("buscarNumero").value.trim();

    const resultado = document.getElementById("resultadoBusqueda");

    if (!numero) {

        resultado.textContent = "Escribe un número de contenedor.";

        return;
    }

    try {

        const datos = await consultarAPI(
            `/api/inventory/containers/${encodeURIComponent(numero)}`
        );

        const contenedor = datos.contenedor;

        resultado.innerHTML = `
            <div class="tarjeta" style="margin-top:20px">

                <h3>${escapar(contenedor.numero)}</h3>

                <p>Descripción: ${escapar(contenedor.descripcion)}</p>
                <p>Origen: ${escapar(contenedor.origen)}</p>
                <p>Destino: ${escapar(contenedor.destino)}</p>
                <p>Tipo: ${escapar(contenedor.tipo)}</p>
                <p>Peso: ${escapar(contenedor.peso_kg)} kg</p>
                <p>Transportista: ${escapar(contenedor.transportista)}</p>
                <p>Estado: ${escapar(contenedor.estado)}</p>

            </div>
        `;

    } catch (error) {

        resultado.textContent = error.message;
    }
}


// ==========================================
// EDITAR CONTENEDOR
// ==========================================

async function editarContenedor(numero) {

    if (usuarioActual?.rol !== "agente_aduanal") {
        alert("No tienes permisos para editar contenedores.");
        return;
    }

    try {

        const datos = await consultarAPI(
            `/api/inventory/containers/${encodeURIComponent(numero)}`
        );

        const contenedor = datos.contenedor;

        const descripcion = prompt("Descripción:", contenedor.descripcion);

        if (descripcion === null) return;

        const origen = prompt("Origen:", contenedor.origen);

        if (origen === null) return;

        const destino = prompt("Destino:", contenedor.destino);

        if (destino === null) return;

        const tipo = prompt("Tipo:", contenedor.tipo);

        if (tipo === null) return;

        const peso = prompt("Peso en kg:", contenedor.peso_kg);

        if (peso === null) return;

        const transportista = prompt(
            "Transportista:",
            contenedor.transportista
        );

        if (transportista === null) return;

        const pesoNumerico = Number(peso);

        if (!Number.isFinite(pesoNumerico) || pesoNumerico <= 0) {
            throw new Error("El peso debe ser mayor que cero.");
        }

        const respuesta = await apiFetch(
            `/api/inventory/containers/${encodeURIComponent(numero)}`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    descripcion: descripcion.trim(),
                    origen: origen.trim(),
                    destino: destino.trim(),
                    tipo: tipo.trim(),
                    peso_kg: pesoNumerico,
                    transportista: transportista.trim()
                })
            }
        );

        const resultado = await leerRespuesta(respuesta);

        if (!respuesta.ok) {
            throw new Error(resultado.error || "No se pudo actualizar");
        }

        alert("Contenedor actualizado correctamente.");

        await actualizarDashboard();

    } catch (error) {

        alert("Error: " + error.message);

        console.error("Error al editar contenedor:", error);
    }
}


// ==========================================
// REGISTRAR MOVIMIENTO PORTUARIO
// ==========================================

async function registrarMovimiento(evento) {

    evento.preventDefault();

    const mensaje = document.getElementById("mensajeMovimiento");

    const tipo = document.getElementById("tipoOperacion").value;

    const rol = usuarioActual?.rol;

    const permisoValido =
        (rol === "transportista" &&
            ["entrada", "salida"].includes(tipo)) ||
        (rol === "agente_aduanal" &&
            tipo === "liberacion_aduanal");

    if (!permisoValido) {

        mensaje.textContent =
            "No tienes permisos para realizar esta operación.";

        mensaje.style.color = "red";

        return;
    }

    const datos = {
        numero: document.getElementById("numeroMovimiento").value.trim(),
        tipo_operacion: tipo,
        observaciones: document.getElementById(
            "observacionesMovimiento"
        ).value.trim()
    };

    if (!datos.numero || !datos.tipo_operacion) {

        mensaje.textContent = "Completa los campos obligatorios.";
        mensaje.style.color = "red";

        return;
    }

    try {

        const respuesta = await apiFetch(
            "/api/operations/movements",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(datos)
            }
        );

        const resultado = await leerRespuesta(respuesta);

        if (!respuesta.ok) {
            throw new Error(
                resultado.error || "Error al registrar movimiento"
            );
        }

        mensaje.textContent = resultado.mensaje;
        mensaje.style.color = "green";

        document.getElementById("formMovimiento").reset();

        await actualizarDashboard();

    } catch (error) {

        mensaje.textContent = error.message;
        mensaje.style.color = "red";

        console.error("Error de operaciones:", error);
    }
}


// ==========================================
// INICIAR APLICACION
// ==========================================

document.addEventListener("DOMContentLoaded", () => {

    const formLogin = document.getElementById("formLogin");

    const btnCerrarSesion =
        document.getElementById("btnCerrarSesion");

    const btnActualizar =
        document.getElementById("btnActualizar");

    const formContenedor =
        document.getElementById("formContenedor");

    const btnBuscar =
        document.getElementById("btnBuscar");

    const formMovimiento =
        document.getElementById("formMovimiento");

    const tablaContenedores =
        document.getElementById("tablaContenedores");


    // Inicio de sesión

    if (formLogin) {
        formLogin.addEventListener("submit", iniciarSesion);
    }

    // Cerrar sesión

    if (btnCerrarSesion) {
        btnCerrarSesion.addEventListener("click", cerrarSesion);
    }

    // Actualizar dashboard

    if (btnActualizar) {
        btnActualizar.addEventListener("click", actualizarDashboard);
    }

    // Registrar contenedor

    if (formContenedor) {
        formContenedor.addEventListener("submit", registrarContenedor);
    }

    // Buscar contenedor

    if (btnBuscar) {
        btnBuscar.addEventListener("click", buscarContenedor);
    }

    // Registrar movimiento

    if (formMovimiento) {
        formMovimiento.addEventListener("submit", registrarMovimiento);
    }

    // Editar contenedores

    if (tablaContenedores) {

        tablaContenedores.addEventListener("click", evento => {

            const boton = evento.target.closest(".btn-editar");

            if (boton) {
                editarContenedor(boton.dataset.numero);
            }

        });
    }

    // Recuperar sesión o mostrar login

    restaurarSesion();

});
