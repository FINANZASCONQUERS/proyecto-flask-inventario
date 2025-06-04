import json
from datetime import datetime
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

def formatear_info_actualizacion(fecha_str_original, usuario_str, tipo_fecha="underscore"):
    """
    Formatea la fecha y el usuario para el mensaje de "Última actualización".
    tipo_fecha puede ser "underscore" (YYYY-MM-DD_HH-MM-SS) o "iso" (YYYY-MM-DDTHH:MM:SS).
    """
    if not fecha_str_original or fecha_str_original == "N/A":
        return "N/A" # O "Información de actualización no disponible."
    
    dt_obj = None
    try:
        if tipo_fecha == "underscore":
            dt_obj = datetime.strptime(fecha_str_original, "%Y-%m-%d_%H-%M-%S")
        elif tipo_fecha == "iso":
            if '.' in fecha_str_original: # Manejar microsegundos si están presentes
                fecha_str_original = fecha_str_original.split('.')[0]
            dt_obj = datetime.fromisoformat(fecha_str_original)
        else: # Formato desconocido
            return f"Fecha de registro: {fecha_str_original}"

        # Formato: 4 de Junio de 2025, 10:30 AM (Ejemplo)
        # Para español necesitarías configurar el locale o un mapeo de meses/días.
        # Usaremos un formato numérico para evitar problemas de locale por ahora:
        fecha_formateada = dt_obj.strftime("%Y-%m-%d, %I:%M:%S %p") 
        
        mensaje = f"Última actualización: {fecha_formateada}"
        if usuario_str and usuario_str != "N/A":
            mensaje += f" por {usuario_str}"
        return mensaje + "."
        
    except ValueError:
        # Si el parseo falla, devuelve la fecha original para no perder la info
        return f"Fecha de registro (error formato): {fecha_str_original}"

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_produccion_cambiar'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Decorador para verificar login (mejorado para AJAX)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            # Si la petición espera JSON (como fetch), devuelve un error JSON y un código 401
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               (request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'):
                return jsonify(success=False, message="Sesión expirada o no autenticado. Por favor, inicie sesión de nuevo.", error_code="SESSION_EXPIRED"), 401
            
            flash('Por favor inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def log_request():
    print(f"➞️  {request.method} {request.path}")

USUARIOS = {
    "quality.manager@conquerstrading.com": {
        "password": generate_password_hash("Conquers2025"),
        "area": "barcaza",
        "nombre": "Ricardo Congo",
        "rol": "manager"
    },
    "production@conquerstrading.com": {
        "password": generate_password_hash("Conquers2025"),
        "area": "planta",
        "nombre": "Ignacio Quimbayo",
        "rol": "production"
    },
    "ops@conquerstrading.com": {
        "password": generate_password_hash("Conquers2025"),
        "area": "transito",
        "nombre": "Juliana Torres",
        "rol": "operations"
    },
      "omar.morales@conquerstrading.com": {
        "password": generate_password_hash("Conquers2025"),
        "area": "reporte",
        "nombre": "Omar Morales",
        "rol": "admin"
    },
        "oci@conquerstrading.com": {
        "password": generate_password_hash("Conquers2025"),
        "area": "reporte",
        "nombre": "Carlos Barón",
        "rol": "admin"
    }
}
    


PLANILLA_PLANTA = [
    {"TK": "TK-109", "PRODUCTO": "CRUDO RF.", "MAX_CAP": 22000, "BLS_60": "", "API": "", "BSW": "", "S": ""},
    {"TK": "TK-110", "PRODUCTO": "FO4",       "MAX_CAP": 22000, "BLS_60": "", "API": "", "BSW": "", "S": ""},
    {"TK": "TK-01",  "PRODUCTO": "DILUYENTE", "MAX_CAP": 450,   "BLS_60": "", "API": "", "BSW": "", "S": ""},
    {"TK": "TK-02",  "PRODUCTO": "DILUYENTE", "MAX_CAP": 450,   "BLS_60": "", "API": "", "BSW": "", "S": ""},
    {"TK": "TK-102", "PRODUCTO": "FO6",       "MAX_CAP": 4100,  "BLS_60": "", "API": "", "BSW": "", "S": ""}
]

PLANILLA_BARCZA_OPS = [
    {"TK": "TK-105", "PRODUCTO": "MGO", "MAX_CAP": 5695, "BLS_60": "", "API": "", "BSW": "", "S": ""},
    {"TK": "MAN TK-1", "PRODUCTO": "MGO", "MAX_CAP": 709, "BLS_60": "", "API": "", "BSW": "", "S": ""},
    {"TK": "MAN TK-2", "PRODUCTO": "MGO", "MAX_CAP": 806, "BLS_60": "", "API": "", "BSW": "", "S": ""},
    {"TK": "MAN TK-3", "PRODUCTO": "MGO", "MAX_CAP": 694, "BLS_60": "", "API": "", "BSW": "", "S": ""}
]

from datos_barcaza_bita import PLANILLA_BARCZA_BITA

PLANILLA_TRANSITO_GENERAL = [
    {"ORIGEN": "", "FECHA": "", "GUIA": "", "PRODUCTO": "", "PLACA": "", "API": "", "BSW": "", "TOV": "", "GSV": "", "NSV": ""}
    for _ in range(10)  # O el número de filas que desees por defecto
]

PLANILLA_TRANSITO_REFINERIA = [
    {"ORIGEN": "", "FECHA": "", "GUIA": "", "PRODUCTO": "", "PLACA": "", "API": "", "BSW": "", "TOV": "", "GSV": "", "NSV": ""}
    for _ in range(10)  # O el número de filas que desees por defecto
]

def cargar_productos():
    ruta = "productos.json"
    try:
        if os.path.exists(ruta):
            with open(ruta, encoding='utf-8') as f:
                data = json.load(f)
                # Validar estructura
                if not all(isinstance(v, list) for v in data.values()):
                    raise ValueError("Estructura inválida en productos.json")
                return data
    except Exception as e:
        print(f"Error cargando productos: {e}")
    return {"REFINERIA": [], "EDSM": []}  # Estructura por defecto

@app.route('/transito')
@login_required
def transito():
    # Mantén tu lógica de permisos si es necesaria
    if session.get('email') != "ops@conquerstrading.com": # Ejemplo, ajusta según tus roles
        flash("No tienes permisos para acceder a esta sección.", "danger")
        return redirect(url_for('home'))

    transito_config_data = cargar_transito_config()

    return render_template("transito.html",
        nombre=session.get("nombre"),
        datos_general=PLANILLA_TRANSITO_GENERAL,
        datos_refineria=PLANILLA_TRANSITO_REFINERIA,
        tipo_inicial="general", # 'general' para EDSM, 'refineria' para Refinería
        transito_config=transito_config_data # Pasar la nueva configuración
        # Ya no pasamos 'productos=cargar_productos()' aquí para Tránsito,
        # ya que transito_config manejará los productos específicos.
    )

def cargar_transito_config():
    ruta_config = "transito_config.json"
    default_config = {
        "REFINERIA": {"campos": {}},
        "EDSM": {"campos": {}}
    }
    try:
        if os.path.exists(ruta_config):
            with open(ruta_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Validaciones básicas
                if not isinstance(config, dict) or \
                   "REFINERIA" not in config or "campos" not in config["REFINERIA"] or \
                   "EDSM" not in config or "campos" not in config["EDSM"]:
                    print(f"Advertencia: Estructura inválida en {ruta_config}. Usando configuración por defecto.")
                    return default_config
                return config
        else:
            print(f"Advertencia: {ruta_config} no encontrado. Usando configuración por defecto.")
            return default_config
    except Exception as e:
        print(f"Error crítico al cargar {ruta_config}: {e}. Usando configuración por defecto.")
        return default_config

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('home'))

    next_page = request.args.get('next')
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        user = USUARIOS.get(email)

        if user and check_password_hash(user['password'], password):
            session['email'] = email
            session['area'] = user['area']
            session['nombre'] = user['nombre']
            session['rol'] = user['rol']
            flash(f"Bienvenido {user['nombre']}", 'success')
            return redirect(next_page or url_for('home'))

        flash('Email o contraseña incorrectos', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('login'))

@app.route('/planta')
@login_required
def planta():
   return render_template("planta.html", planilla=PLANILLA_PLANTA)


@app.route('/barcaza')
@login_required
def barcaza():
    datos_cr = PLANILLA_BARCZA_BITA[:10]
    datos_margoth = PLANILLA_BARCZA_BITA[10:20]
    datos_odisea = PLANILLA_BARCZA_BITA[20:]

    print("🚀 datos_ops:", PLANILLA_BARCZA_OPS)  # Debug
    print("✅ datos_cr:", datos_cr)
    print("✅ datos_margoth:", datos_margoth)
    print("✅ datos_odisea:", datos_odisea)

    return render_template("barcazas.html",
        datos_ops=PLANILLA_BARCZA_OPS,
        datos_cr=datos_cr,
        datos_margoth=datos_margoth,
        datos_odisea=datos_odisea,
        tipo_inicial="ops",
        nombre=session.get("nombre"))

@app.route('/reporte_planta')
@login_required
def reporte_planta():
    carpeta = "registros"
    datos_planta_js = []
    # Usaremos una variable más descriptiva para la info completa
    fecha_actualizacion_info = "No hay registros guardados." 

    try:
        archivos_planta = sorted(
            [a for a in os.listdir(carpeta) if a.startswith("planta_") and a.endswith(".json")], 
            reverse=True
        )
        if archivos_planta:
            ruta_mas_reciente = os.path.join(carpeta, archivos_planta[0])
            with open(ruta_mas_reciente, encoding='utf-8') as f:
                planta_data_cargada = json.load(f)
            
            datos_planta_js = planta_data_cargada.get("datos", [])
            
            # Usar las claves correctas guardadas por guardar_registro_generico
            fecha_guardado = planta_data_cargada.get("fecha") 
            usuario_guardado = planta_data_cargada.get("usuario")
            
            fecha_actualizacion_info = formatear_info_actualizacion(fecha_guardado, usuario_guardado, tipo_fecha="underscore")

        else:
            datos_planta_js = PLANILLA_PLANTA 
            # fecha_actualizacion_info ya tiene "No hay registros guardados."
            
    except Exception as e:
        print(f"Error crítico al cargar datos para /reporte_planta: {e}")
        datos_planta_js = [] 
        fecha_actualizacion_info = "Error al cargar la información de actualización."
        flash(f"No se pudo cargar el reporte de planta: {str(e)}", "danger")

    return render_template("reporte_planta.html", 
                           datos_planta_para_js=datos_planta_js,
                           fecha_actualizacion_info=fecha_actualizacion_info) # N

@app.route('/reporte_barcaza')
@login_required
def reporte_barcaza():
    carpeta = "registros"
    fecha_actualizacion_info = "No hay registros de barcazas guardados."
    datos_ops = []
    datos_bita_crudos = [] # Cambiado para reflejar que son datos crudos del JSON

    try:
        os.makedirs(carpeta, exist_ok=True)

        latest_ops_file_content = None
        latest_bita_file_content = None

        archivos_ops_json = sorted([a for a in os.listdir(carpeta) if a.startswith("barcaza_ops_") and a.endswith(".json")], reverse=True)
        if archivos_ops_json:
            with open(os.path.join(carpeta, archivos_ops_json[0]), encoding='utf-8') as f:
                latest_ops_file_content = json.load(f)

        archivos_bita_json = sorted([a for a in os.listdir(carpeta) if a.startswith("barcaza_bita_") and a.endswith(".json")], reverse=True)
        if archivos_bita_json:
            with open(os.path.join(carpeta, archivos_bita_json[0]), encoding='utf-8') as f:
                latest_bita_file_content = json.load(f)

        fecha_ops_str = latest_ops_file_content.get("fecha") if latest_ops_file_content else None
        usuario_ops_str = latest_ops_file_content.get("usuario") if latest_ops_file_content else None
        fecha_bita_str = latest_bita_file_content.get("fecha") if latest_bita_file_content else None
        usuario_bita_str = latest_bita_file_content.get("usuario") if latest_bita_file_content else None

        final_fecha_str = None
        final_usuario_str = None

        if fecha_ops_str and fecha_bita_str:
            if fecha_ops_str >= fecha_bita_str:
                final_fecha_str = fecha_ops_str
                final_usuario_str = usuario_ops_str
            else:
                final_fecha_str = fecha_bita_str
                final_usuario_str = usuario_bita_str
        elif fecha_ops_str:
            final_fecha_str = fecha_ops_str
            final_usuario_str = usuario_ops_str
        elif fecha_bita_str:
            final_fecha_str = fecha_bita_str
            final_usuario_str = usuario_bita_str
        
        if final_fecha_str:
            fecha_actualizacion_info = formatear_info_actualizacion(final_fecha_str, final_usuario_str, tipo_fecha="underscore")

        datos_ops = latest_ops_file_content.get("datos", []) if latest_ops_file_content else []
        datos_bita_crudos = latest_bita_file_content.get("datos", []) if latest_bita_file_content else []
            
    except Exception as e:
        print("Error general en reporte_barcaza:", e)
        flash("Error al generar el reporte de barcazas.", "danger")
        fecha_actualizacion_info = "Error al cargar la información de actualización."

    return render_template("reporte_barcaza.html",
                           datos_ops=datos_ops,
                           datos_bita=datos_bita_crudos, # Pasa los datos crudos; el HTML debe manejarlos
                           nombre=session.get("nombre"),
                           fecha_actualizacion_info=fecha_actualizacion_info)

@app.route('/guardar-datos-barcaza', methods=['POST'])
@login_required
def guardar_datos_barcaza():
    if not request.is_json:
        return jsonify(success=False, message="Formato no válido"), 400

    data = request.get_json()
    tk = data.get("tk")
    field = data.get("field")
    value = data.get("value")
    tipo = data.get("tipo")

    if not all([tk, field, tipo]):
        return jsonify(success=False, message="Datos incompletos"), 400

    planilla = PLANILLA_BARCZA_OPS if tipo == "ops" else PLANILLA_BARCZA_BITA
    for fila in planilla:
        if fila["TK"] == tk and field in fila:
            fila[field] = value
            return jsonify(success=True)

    return jsonify(success=False, message="Tanque o campo no encontrado"), 404

@app.route('/guardar-registro-barcaza-ops', methods=['POST'])
@login_required
def guardar_registro_ops():
    print("Intentando guardar registro OPS...")  # Debug
    result = guardar_registro_generico(PLANILLA_BARCZA_OPS, "barcaza_ops")
    print("Resultado guardado OPS:", result)  # Debug
    return result

@app.route('/guardar-registro-barcaza-bita', methods=['POST'])
@login_required
def guardar_registro_bita():
    return guardar_registro_generico(PLANILLA_BARCZA_BITA, "barcaza_bita")

@app.route('/obtener-datos-barcazas')
@login_required
def obtener_datos_barcazas():
    try:
        # Obtener registros más recientes
        registros_ops = []
        registros_bita = []
        carpeta = "registros"
        
        for archivo in sorted(os.listdir(carpeta), reverse=True):
            if not archivo.endswith(".json"):
                continue
                
            ruta = os.path.join(carpeta, archivo)
            try:
                with open(ruta, encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if "barcaza_ops" in archivo and not registros_ops:
                        registros_ops = data["datos"]
                    elif "barcaza_bita" in archivo and not registros_bita:
                        registros_bita = data["datos"]
                        
                    if registros_ops and registros_bita:
                        break
            except:
                continue
        
        # Procesar BITA para agrupar por barcaza
        bita_procesada = []
        if registros_bita:
            # Agrupar por barcazas (primeros 10: CR, siguientes 10: Margoth, últimos 10: Odisea)
            grupos = {
                "Barcaza CR": registros_bita[:10],
                "Barcaza Margoth": registros_bita[10:20],
                "Barcaza Odisea": registros_bita[20:]
            }
            
            for nombre, tanques in grupos.items():
                total_bls = sum(float(t.get("BLS_60", 0) or 0) for t in tanques)
                max_cap = sum(float(t["MAX_CAP"]) for t in tanques)
                
                # Calcular promedios
                apis = [float(t.get("API", 0) or 0) for t in tanques if t.get("API")]
                bsws = [float(t.get("BSW", 0) or 0) for t in tanques if t.get("BSW")]
                ss = [float(t.get("S", 0) or 0) for t in tanques if t.get("S")]
                
                bita_procesada.append({
                    "TK": nombre,
                    "PRODUCTO": "VLSFO",
                    "MAX_CAP": max_cap,
                    "BLS_60": total_bls,
                    "API": round(sum(apis)/len(apis), 2) if apis else "",
                    "BSW": round(sum(bsws)/len(bsws), 2) if bsws else "",
                    "S": round(sum(ss)/len(ss), 2) if ss else "",
                    "TIPO": "bita"
                })
        
        return jsonify({
            "success": True,
            "datos_ops": registros_ops or [],
            "datos_bita": bita_procesada or []
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

def guardar_registro_generico(planilla, tipo):
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    carpeta = "registros"
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"{tipo}_{fecha}.json")
    data = {
        "fecha": fecha,
        "area": tipo,
        "usuario": session.get("nombre"),
        "datos": planilla
    }
    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500

@app.route('/guardar-registro-transito-<tipo_transito>', methods=['POST'])
@login_required
def guardar_transito(tipo_transito): # tipo_transito será 'general' o 'refineria'
    app.logger.info(f"Solicitud para guardar tránsito tipo: {tipo_transito}")
    
    # --- INICIO VERIFICACIÓN DE HORA PARA TRÁNSITO ---
    try:
        HORA_LIMITE = time(10, 0, 0) # Definición de la hora límite
        hora_actual_servidor = datetime.now().time()
        app.logger.info(f"Guardar Tránsito - Hora actual: {hora_actual_servidor}, Hora límite: {HORA_LIMITE}")

        if hora_actual_servidor >= HORA_LIMITE:
            mensaje = f"No se pueden registrar datos de tránsito ('{tipo_transito}') después de las {HORA_LIMITE.strftime('%I:%M %p').replace('AM','a.m.').replace('PM','p.m.')}."
            app.logger.warning(f"Intento de guardado denegado por hora límite: {mensaje} para usuario {session.get('nombre')}")
            return jsonify(success=False, message=mensaje), 403 # 403 Forbidden es apropiado
    except NameError as ne:
        app.logger.error(f"Error de programación en guardar_transito (verificación de hora): {ne}. ¿Falta importar 'time' de 'datetime'?")
        return jsonify(success=False, message="Error de configuración del servidor (verificación de hora)."), 500
    except Exception as e_time_check:
        app.logger.error(f"Error inesperado en verificación de hora para guardar_transito: {e_time_check}")
        return jsonify(success=False, message="Error del servidor al verificar la hora del registro."), 500
    # --- FIN VERIFICACIÓN DE HORA ---

    try:
        datos_recibidos = request.get_json()
        if not isinstance(datos_recibidos, list):
            app.logger.error(f"Guardar Tránsito: Los datos recibidos no son una lista. Tipo: {type(datos_recibidos)}")
            return jsonify(success=False, message="El formato de datos enviados es incorrecto (se esperaba una lista)."), 400
        app.logger.info(f"Guardar Tránsito: {len(datos_recibidos)} filas recibidas. Muestra de la primera fila (si existe): {json.dumps(datos_recibidos[0] if datos_recibidos else {}, indent=2)}")
    except Exception as e_json_load:
        app.logger.error(f"Guardar Tránsito: Error al obtener o parsear JSON de la solicitud: {e_json_load}")
        return jsonify(success=False, message="Error en los datos enviados (no es JSON válido o está vacío)."), 400

    # Validar que tipo_transito sea uno de los esperados
    if tipo_transito not in ["general", "refineria"]: # Asumiendo que estos son los valores que usa tu JS en la URL
        app.logger.error(f"Guardar Tránsito: tipo_transito inválido recibido en la URL: '{tipo_transito}'")
        return jsonify(success=False, message=f"Tipo de planilla de tránsito '{tipo_transito}' no es válido."), 400

    fecha_registro_dt = datetime.now() 
    fecha_str_para_nombre_archivo = fecha_registro_dt.strftime("%Y-%m-%d_%H-%M-%S") 

    # Usar BASE_DIR para asegurar la ruta correcta de la carpeta 'registros'
    carpeta_registros_path = os.path.join(BASE_DIR, "registros")
    try:
        os.makedirs(carpeta_registros_path, exist_ok=True)
    except OSError as e_mkdir:
        app.logger.error(f"Guardar Tránsito: Error crítico al crear directorio de registros '{carpeta_registros_path}': {e_mkdir}")
        return jsonify(success=False, message="Error del servidor al preparar el almacenamiento de registros."), 500

    nombre_archivo_final = f"transito_{tipo_transito}_{fecha_str_para_nombre_archivo}.json"
    ruta_archivo_final = os.path.join(carpeta_registros_path, nombre_archivo_final)
    app.logger.info(f"Guardar Tránsito: Se intentará guardar en: {ruta_archivo_final}")

    # Preparar los datos que se guardarán en el archivo JSON
    # La estructura debe coincidir con lo que la función reporte_transito espera leer.
    # Tu función guardar_registro_generico original guarda: fecha, area, usuario, datos.
    # Tu función guardar_transito original (la que me pegaste) guarda: timestamp_iso, fecha_guardado_str, tipo_transito, usuario, datos.
    # Vamos a usar la segunda estructura ya que es la que definiste para esta función.
    
    # Procesar fechas dentro de los datos recibidos si vienen como DD/MM/YYYY
    datos_procesados_para_guardar = []
    for fila_idx, fila_original in enumerate(datos_recibidos):
        if not isinstance(fila_original, dict):
            app.logger.warning(f"Guardar Tránsito: Fila {fila_idx} no es un diccionario, se omitirá. Contenido: {fila_original}")
            continue
        fila_procesada = {}
        for k, v_original in fila_original.items():
            if k == "FECHA" and v_original and isinstance(v_original, str) and "/" in v_original:
                try:
                    dt_obj = datetime.strptime(v_original, "%d/%m/%Y")
                    fila_procesada[k] = dt_obj.strftime("%Y-%m-%d") # Guardar en formato ISO YYYY-MM-DD
                except ValueError:
                    app.logger.warning(f"Guardar Tránsito: Formato de fecha inválido '{v_original}' en fila {fila_idx}, se guardará como texto.")
                    fila_procesada[k] = v_original 
            else:
                fila_procesada[k] = v_original
        datos_procesados_para_guardar.append(fila_procesada)


    data_to_save_in_file = {
        "timestamp_iso": fecha_registro_dt.isoformat(), 
        "fecha_guardado_str": fecha_str_para_nombre_archivo, 
        "tipo_transito": tipo_transito, # 'general' o 'refineria'
        "usuario": session.get("nombre"),
        "datos": datos_procesados_para_guardar # La lista de filas que vino del frontend (con fechas procesadas)
    }

    try:
        with open(ruta_archivo_final, 'w', encoding='utf-8') as f:
            json.dump(data_to_save_in_file, f, ensure_ascii=False, indent=2)
        app.logger.info(f"REGISTRO DE TRÁNSITO GUARDADO EXITOSAMENTE: {nombre_archivo_final}")
        
        # Actualizar las planillas globales en memoria (si tu vista de edición directa las usa)
        # Esto es opcional y depende de cómo cargues los datos en la vista de edición /transito
        if tipo_transito == "general":
            global PLANILLA_TRANSITO_GENERAL
            PLANILLA_TRANSITO_GENERAL = [dict(d) for d in datos_procesados_para_guardar] # Actualizar con los datos guardados
        elif tipo_transito == "refineria":
            global PLANILLA_TRANSITO_REFINERIA
            PLANILLA_TRANSITO_REFINERIA = [dict(d) for d in datos_procesados_para_guardar]

        return jsonify(success=True, message=f"Registro de tránsito '{tipo_transito}' guardado exitosamente.")
    except Exception as e_write_file:
        app.logger.error(f"Guardar Tránsito: Error crítico al escribir el archivo de registro '{ruta_archivo_final}': {e_write_file}")
        return jsonify(success=False, message=f"Error del servidor al guardar el archivo de registro: {str(e_write_file)}"), 500

@app.route('/agregar-producto', methods=['POST'])
@login_required
def agregar_producto():
    data = request.get_json()
    nuevo_producto = data.get("producto")
    grupo = data.get("grupo")  # "REFINERIA" o "EDSM"

    if not nuevo_producto or grupo not in ["REFINERIA", "EDSM"]:
        return jsonify(success=False, message="Datos incompletos")

    ruta = "productos.json"
    try:
        with open(ruta, encoding="utf-8") as f:
            productos = json.load(f)

        if nuevo_producto not in productos[grupo]:
            productos[grupo].append(nuevo_producto)
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(productos, f, ensure_ascii=False, indent=2)

        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))
       
@app.route('/reporte')
@login_required
def reporte():
    registros = []
    carpeta = "registros"
    os.makedirs(carpeta, exist_ok=True)

    # Verifica si hay archivos de planta guardados
    for archivo in sorted(os.listdir(carpeta), reverse=True):
        if archivo.endswith(".json") and "planta" in archivo:
            ruta = os.path.join(carpeta, archivo)
            try:
                with open(ruta, encoding='utf-8') as f:
                    data = json.load(f)
                    registros.append(data)
            except Exception as e:
                print(f"❌ Error leyendo {archivo}: {e}")

    if registros:
        # Mostrar solo el más reciente
        return render_template("reporte_planta.html", planilla=registros[0]["datos"])
    else:
        flash("⚠️ No hay datos registrados aún para planta", "warning")
        return redirect(url_for('planta'))


@app.route('/historial_registros') # CAMBIO AQUÍ
@login_required
def historial_registros():        # CAMBIO AQUÍ
    registros = []
    carpeta = "registros"
    os.makedirs(carpeta, exist_ok=True)

    for archivo in sorted(os.listdir(carpeta), reverse=True):
        if archivo.endswith(".json"):
            ruta = os.path.join(carpeta, archivo)
            try:
                with open(ruta, encoding='utf-8') as f:
                    registro = json.load(f)
                    if session.get("email") in ["omar.morales@conquerstrading.com", "oci@conquerstrading.com"]:
                        registros.append(registro)
                    else:
                        if registro.get("usuario") == session.get("nombre"):
                            registros.append(registro)
            except Exception as e:
                print(f"Error al cargar {archivo}: {e}")
    # Asegúrate que el nombre del template sigue siendo el correcto si quieres reutilizarlo
    return render_template("reporte_general.html", registros=registros, nombre=session.get("nombre"))

@app.route('/dashboard_reportes')
@login_required
def dashboard_reportes():
    # ----- INICIO DE VERIFICACIÓN DE PERMISOS -----
    if session.get('email') != "omar.morales@conquerstrading.com":
        flash("No tiene permisos para acceder a esta página.", "danger")
        return redirect(url_for('home')) # Redirige a home, que luego decidirá a dónde enviar al usuario
    # ----- FIN DE VERIFICACIÓN DE PERMISOS -----

    carpeta = "registros"
    os.makedirs(carpeta, exist_ok=True)
    
    # --- Resumen de Planta ---
    planta_summary = {"datos": [], "fecha": "N/A", "usuario": "N/A"} # Inicializar con valores por defecto
    try:
        archivos_planta = sorted([a for a in os.listdir(carpeta) if a.startswith("planta_") and a.endswith(".json")], reverse=True)
        if archivos_planta:
            with open(os.path.join(carpeta, archivos_planta[0]), encoding='utf-8') as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict):
                    planta_summary = loaded_data
                # Asegurar que las claves esperadas existan, usando valores por defecto si no.
                planta_summary.setdefault("datos", [])
                planta_summary.setdefault("fecha", "N/A") # 'fecha' ya debería estar por tu función guardar_registro_generico
                planta_summary.setdefault("usuario", "N/A")# 'usuario' ya debería estar por tu función guardar_registro_generico
        # Si no hay archivos, planta_summary ya tiene los valores por defecto.
    except Exception as e:
        print(f"Error cargando resumen planta para dashboard: {e}")
        # En caso de error, planta_summary ya tiene los valores por defecto.

    # --- Resumen de Operaciones de Barcaza (OPS) ---
    barcaza_ops_summary = {"datos": [], "fecha": "N/A", "usuario": "N/A"} # Inicializar con valores por defecto
    try:
        archivos_ops = sorted([a for a in os.listdir(carpeta) if a.startswith("barcaza_ops_") and a.endswith(".json")], reverse=True)
        if archivos_ops:
            with open(os.path.join(carpeta, archivos_ops[0]), encoding='utf-8') as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict):
                    barcaza_ops_summary = loaded_data # Usar los datos cargados
                # Asegurar que las claves esperadas existan
                barcaza_ops_summary.setdefault("datos", [])
                barcaza_ops_summary.setdefault("fecha", "N/A") # 'fecha' ya debería estar por tu función guardar_registro_generico
                barcaza_ops_summary.setdefault("usuario", "N/A")# 'usuario' ya debería estar por tu función guardar_registro_generico
        # Si no hay archivos, barcaza_ops_summary ya tiene los valores por defecto.
    except Exception as e:
        print(f"Error cargando resumen barcaza OPS para dashboard: {e}")
        # En caso de error, barcaza_ops_summary ya tiene los valores por defecto.

    # --- Resumen de Barcaza Bitácora (BITA) ---
    # Esta parte la dejas como la tenías, ya que barcaza_bita_summary es una lista procesada
    # y la fecha/usuario de la tarjeta "Reporte de Barcazas" vendrá de barcaza_ops_summary.
    barcaza_bita_summary = [] 
    try:
        archivos_bita = sorted([a for a in os.listdir(carpeta) if a.startswith("barcaza_bita_") and a.endswith(".json")], reverse=True)
        if archivos_bita:
            with open(os.path.join(carpeta, archivos_bita[0]), encoding='utf-8') as f:
                data_bita_cruda = json.load(f)
                if data_bita_cruda and "datos" in data_bita_cruda and isinstance(data_bita_cruda["datos"], list):
                    bita_cruda = data_bita_cruda["datos"]
                    datos_cr_recientes = bita_cruda[0:10] if len(bita_cruda) >= 10 else bita_cruda[0:len(bita_cruda)]
                    datos_margoth_recientes = bita_cruda[10:20] if len(bita_cruda) >= 20 else bita_cruda[10:len(bita_cruda)]
                    datos_odisea_recientes = bita_cruda[20:30] if len(bita_cruda) >= 30 else bita_cruda[20:len(bita_cruda)]
                    grupos = {
                        "Barcaza CR": datos_cr_recientes,
                        "Barcaza Margoth": datos_margoth_recientes,
                        "Barcaza Odisea": datos_odisea_recientes
                    }
                    temp_bita_procesada = []
                    for nombre_barc, tanques in grupos.items():
                        if not tanques: continue 
                        total_bls = sum(float(t.get("BLS_60", 0) or 0) for t in tanques)
                        max_cap = sum(float(t.get("MAX_CAP", 0) or 0) for t in tanques) # Corregido t.get("MAX_CAP", 0) por si no existe
                        producto_barcaza = tanques[0].get("PRODUCTO", "VLSFO") if tanques and tanques[0] else "VLSFO"
                        temp_bita_procesada.append({
                            "TK": nombre_barc, "MAX_CAP": max_cap, "BLS_60": total_bls,
                            "PRODUCTO": producto_barcaza
                        })
                    barcaza_bita_summary = temp_bita_procesada
    except Exception as e:
        print(f"Error cargando/procesando resumen barcaza BITA para dashboard: {e}")

    # --- Resumen de Tránsito ---
    transito_summary = {"datos_reporte": [], "total_nsv_general": 0, "fecha": "N/A", "usuario": "N/A"} # Inicializar
    try:
        registros_transito_archivos_para_datos = [] # Renombrado para claridad
        extracted_transito_metadata = False 
        
        archivos_transito_todos = sorted([a for a in os.listdir(carpeta) if a.startswith("transito_") and a.endswith(".json")], reverse=True)

        for archivo_nombre in archivos_transito_todos:
            with open(os.path.join(carpeta, archivo_nombre), encoding='utf-8') as f:
                contenido_archivo = json.load(f)
                
                # Extraer metadata (fecha, usuario) del archivo JSON de tránsito más reciente
                # Tu función guardar_transito guarda "timestamp_iso", "fecha_guardado_str", "tipo_transito", "usuario".
                # Usaremos "fecha_guardado_str" para la 'fecha' y "usuario" directamente.
                if not extracted_transito_metadata and isinstance(contenido_archivo, dict):
                    transito_summary["fecha"] = contenido_archivo.get("fecha_guardado_str", "N/A") # O "timestamp_iso" si prefieres formato ISO
                    transito_summary["usuario"] = contenido_archivo.get("usuario", "N/A")
                    extracted_transito_metadata = True

                # Procesar 'datos' para la consolidación del reporte
                if isinstance(contenido_archivo, dict) and "datos" in contenido_archivo and isinstance(contenido_archivo["datos"], list):
                    # 'tipo_transito' o 'tipo' dentro del archivo JSON guardado por guardar_transito()
                    tipo_transito_archivo = contenido_archivo.get("tipo_transito") or contenido_archivo.get("tipo", "general")
                    for reg in contenido_archivo["datos"]:
                        reg["TIPO_ARCHIVO"] = tipo_transito_archivo # Para la lógica de consolidación
                        registros_transito_archivos_para_datos.append(reg)
                elif not isinstance(contenido_archivo, dict):
                    print(f"Warning: Contenido del archivo transito_ {archivo_nombre} no es un diccionario y no se pudieron procesar sus 'datos'.")
        
        # Lógica de consolidación (como la tenías)
        consolidado = {}
        if registros_transito_archivos_para_datos:
            for registro in registros_transito_archivos_para_datos:
                if not registro.get("PRODUCTO") or registro.get("NSV") is None: continue
                producto = registro["PRODUCTO"]
                # Usamos TIPO_ARCHIVO que asignamos arriba, derivado de "tipo_transito" en el JSON
                tipo = "Refinería" if "refineria" in registro.get("TIPO_ARCHIVO", "").lower() else "EDSM"
                nsv_val = registro.get("NSV", "0") # Obtener como string o 0 por defecto
                try:
                    nsv = float(str(nsv_val).replace(',', '.')) # Convertir a float, manejando comas
                except ValueError:
                    nsv = 0.0 # Si la conversión falla, usar 0.0
                    
                if producto not in consolidado: consolidado[producto] = {"Refinería": 0, "EDSM": 0}
                consolidado[producto][tipo] += nsv
            
            datos_reporte_temp = []
            total_nsv_general_temp = 0
            for producto, valores in consolidado.items():
                total_producto = valores["Refinería"] + valores["EDSM"]
                datos_reporte_temp.append({
                    "PRODUCTO": producto, "REFINERIA": round(valores["Refinería"], 2),
                    "EDSM": round(valores["EDSM"], 2), "TOTAL": round(total_producto, 2)
                })
                total_nsv_general_temp += total_producto
            transito_summary["datos_reporte"] = datos_reporte_temp
            transito_summary["total_nsv_general"] = round(total_nsv_general_temp, 2)
            
    except Exception as e:
        print(f"Error procesando resumen tránsito para dashboard: {e}")
        # transito_summary ya tiene los valores por defecto para fecha/usuario

    return render_template("dashboard_reportes.html",
                           nombre=session.get("nombre"),
                           planta_summary=planta_summary,
                           barcaza_ops_summary=barcaza_ops_summary,
                           barcaza_bita_summary=barcaza_bita_summary,
                           transito_summary=transito_summary)
                           
@app.route('/guardar-datos-planta', methods=['POST'])
@login_required
def guardar_datos_planta():
    if not request.is_json:
        return jsonify(success=False, message="Formato no válido"), 400

    data = request.get_json()
    tk = data.get("tk")
    field = data.get("field")
    value = data.get("value")

    if not all([tk, field]):
        return jsonify(success=False, message="Datos incompletos"), 400

    for fila in PLANILLA_PLANTA:
        if fila["TK"] == tk and field in fila:
            fila[field] = value
            return jsonify(success=True)

    return jsonify(success=False, message="Tanque o campo no encontrado"), 404

@app.route('/guardar-registro-planta', methods=['POST'])
@login_required
def guardar_registro_planta():
    return guardar_registro_generico(PLANILLA_PLANTA, "planta")

@app.route('/reporte_transito')
@login_required
def reporte_transito():
    app.logger.info("Accediendo a /reporte_transito")
    datos_consolidados = {"Refinería": {}, "EDSM": {}}
    datos_conteo_camiones = {"Refinería": {}, "EDSM": {}}
    fecha_actualizacion_info = "No hay registros de tránsito para generar el reporte."

    carpeta_registros_path = os.path.join(BASE_DIR, "registros")
    # ... (asegurar que la carpeta existe) ...

    archivos_en_directorio = []
    try:
        archivos_en_directorio = sorted(os.listdir(carpeta_registros_path), reverse=True)
        # ... (logging) ...
    except Exception as e_listdir:
        # ... (logging) ...
        pass # Continuar para que se muestre el mensaje por defecto

    metadata_extracted = False
    archivos_transito_json_validos = 0

    for archivo_nombre in archivos_en_directorio:
        if archivo_nombre.startswith("transito_") and archivo_nombre.endswith(".json"):
            ruta_completa = os.path.join(carpeta_registros_path, archivo_nombre)
            app.logger.info(f"Procesando archivo para reporte tránsito: {archivo_nombre}")
            try:
                with open(ruta_completa, 'r', encoding='utf-8') as f:
                    data_archivo = json.load(f)

                archivos_transito_json_validos +=1

                if not metadata_extracted and isinstance(data_archivo, dict):
                    # Usar 'fecha_guardado_str' o 'timestamp_iso' que guarda guardar_transito
                    fecha_guardado = data_archivo.get("fecha_guardado_str") or data_archivo.get("timestamp_iso")
                    usuario_guardado = data_archivo.get("usuario")
                    tipo_fecha_guardado = "underscore" if data_archivo.get("fecha_guardado_str") else "iso"
                    
                    fecha_actualizacion_info = formatear_info_actualizacion(fecha_guardado, usuario_guardado, tipo_fecha=tipo_fecha_guardado)
                    metadata_extracted = True
                
                # ... (TU LÓGICA ACTUAL PARA CONSOLIDAR datos_consolidados y datos_conteo_camiones)...
                # Esta parte es crucial y debe permanecer:
                tipo_archivo_guardado = data_archivo.get("tipo_transito") or data_archivo.get("tipo") 
                registros_individuales = data_archivo.get("datos", [])
                if not tipo_archivo_guardado or not isinstance(registros_individuales, list):
                    app.logger.warning(f"Archivo {archivo_nombre} con formato inesperado. Omitiendo para consolidación.")
                    continue
                tipo_destino_reporte = "Refinería" if tipo_archivo_guardado == "refineria" else "EDSM"
                for reg_idx, reg in enumerate(registros_individuales):
                    # ... (tu lógica interna para procesar 'reg' y sumar a datos_consolidados)...
                    origen = reg.get("ORIGEN", "Origen Desconocido") 
                    producto = reg.get("PRODUCTO")
                    nsv_str = reg.get("NSV")

                    if not producto or nsv_str is None:
                        app.logger.warning(f"Registro #{reg_idx} en {archivo_nombre} omitido (sin PRODUCTO o NSV). Origen: {origen}")
                        continue
                    try:
                        nsv = float(str(nsv_str).replace(',', '.')) 
                    except ValueError:
                        app.logger.warning(f"Valor NSV no numérico '{nsv_str}' para Origen '{origen}', Producto '{producto}' en {archivo_nombre}. Omitiendo.")
                        continue
                    if tipo_destino_reporte not in datos_consolidados: datos_consolidados[tipo_destino_reporte] = {}
                    if tipo_destino_reporte not in datos_conteo_camiones: datos_conteo_camiones[tipo_destino_reporte] = {}
                    if origen not in datos_consolidados[tipo_destino_reporte]: datos_consolidados[tipo_destino_reporte][origen] = {}
                    if origen not in datos_conteo_camiones[tipo_destino_reporte]: datos_conteo_camiones[tipo_destino_reporte][origen] = {}
                    if producto not in datos_consolidados[tipo_destino_reporte][origen]: datos_consolidados[tipo_destino_reporte][origen][producto] = 0
                    if producto not in datos_conteo_camiones[tipo_destino_reporte][origen]: datos_conteo_camiones[tipo_destino_reporte][origen][producto] = 0
                    datos_consolidados[tipo_destino_reporte][origen][producto] += nsv
                    datos_conteo_camiones[tipo_destino_reporte][origen][producto] += 1


            except Exception as e_process_file: # Más genérico para errores de lectura o JSON
                app.logger.error(f"Error procesando archivo {archivo_nombre} para reporte_transito: {e_process_file}")

    # ... (tu lógica de redondeo final y logging) ...
    if archivos_transito_json_validos == 0 : # Si no se procesó ningún archivo de tránsito válido
        fecha_actualizacion_info = "No hay registros de tránsito disponibles."

    return render_template("reporte_transito.html",
                           datos_consolidados=datos_consolidados,
                           datos_conteo_camiones=datos_conteo_camiones,
                           nombre=session.get("nombre"),
                           fecha_actualizacion_info=fecha_actualizacion_info) # Nueva variable
        

@app.route('/')
def home():
    if 'email' in session:
        email = session.get('email')
        area = session.get('area') # Asegúrate que 'area' siempre esté en la sesión para usuarios logueados

        # ----- LÓGICA DE REDIRECCIÓN ACTUALIZADA -----
        if email == "omar.morales@conquerstrading.com":
            return redirect(url_for("dashboard_reportes"))
        elif email == "oci@conquerstrading.com": # Ejemplo: Carlos Barón (admin)
            return redirect(url_for("historial_registros")) # O cualquier otra página admin por defecto
        
        # Redirección basada en área para otros usuarios
        if area == "barcaza":
            return redirect(url_for("barcaza"))
        elif area == "planta":
            return redirect(url_for("planta"))
        elif area == "transito":
            return redirect(url_for("transito"))
        else:
            # Fallback para usuarios logueados sin una ruta de área específica o no cubiertos arriba
            flash('No tiene una página de inicio configurada. Contacte al administrador.', 'warning')
            return redirect(url_for('logout')) # O a una página de perfil genérica si existiera
        # ----- FIN DE LÓGICA DE REDIRECCIÓN -----

    return redirect(url_for('login')) # Si no hay email en sesión, va al login

@app.route('/test')
def test():
    return "✅ El servidor Flask está funcionando"
@app.route('/debug/productos')

def debug_productos():
    productos = cargar_productos()
    return jsonify({
        "productos": productos,
        "exists": os.path.exists("productos.json"),
        "file_content": open("productos.json").read() if os.path.exists("productos.json") else None
    })

if __name__ == '__main__':
    app.run(debug=True)