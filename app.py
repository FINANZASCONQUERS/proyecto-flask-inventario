import json
from datetime import datetime
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_produccion_cambiar'

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
    # os.makedirs(carpeta, exist_ok=True) # Asegurar que existe, aunque ya debería por el guardado

    datos_planta_js = []
    fecha_actualizacion_planta = "N/A"

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
            raw_timestamp = planta_data_cargada.get("timestamp_iso") or planta_data_cargada.get("fecha_guardado_str", "N/A")

            # Formatear el timestamp para visualización
            if "T" in raw_timestamp and "." in raw_timestamp: # Formato ISO probable
                try:
                    dt_obj = datetime.fromisoformat(raw_timestamp.split('.')[0]) # Ignorar microsegundos
                    fecha_actualizacion_planta = dt_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                except ValueError:
                    fecha_actualizacion_planta = raw_timestamp # Dejar como está si falla el parseo
            elif "_" in raw_timestamp and "-" in raw_timestamp : # Formato YYYY-MM-DD_HH-MM-SS
                 try:
                    dt_obj = datetime.strptime(raw_timestamp, "%Y-%m-%d_%H-%M-%S")
                    fecha_actualizacion_planta = dt_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                 except ValueError:
                    fecha_actualizacion_planta = raw_timestamp # Dejar como está
            else:
                fecha_actualizacion_planta = raw_timestamp

        else:
            # Si no hay archivos guardados, usamos la PLANILLA_PLANTA global para mostrar la estructura base
            # Los valores de BLS_60, API, etc., en PLANILLA_PLANTA son strings vacíos, así que los tanques aparecerán vacíos.
            datos_planta_js = PLANILLA_PLANTA 
            fecha_actualizacion_planta = "No hay registros guardados. Mostrando estructura por defecto."
            # flash("No hay datos de planta registrados para mostrar en el reporte.", "info") # Opcional

    except Exception as e:
        print(f"Error crítico al cargar datos para /reporte_planta: {e}")
        # En caso de un error grave al leer archivos, etc.
        datos_planta_js = [] # Mostrar reporte vacío
        fecha_actualizacion_planta = "Error al cargar los datos del reporte."
        flash(f"No se pudo cargar el reporte de planta: {str(e)}", "danger")

    return render_template("reporte_planta.html", 
                           datos_planta_para_js=datos_planta_js,
                           fecha_actualizacion_planta=fecha_actualizacion_planta)

@app.route('/reporte_barcaza')
@login_required
def reporte_barcaza():
    registros_ops = []
    registros_bita = []
    carpeta = "registros"
    
    try:
        os.makedirs(carpeta, exist_ok=True)
        print(f"Contenido de {carpeta}:", os.listdir(carpeta))  # Debug

        for archivo in sorted(os.listdir(carpeta), reverse=True):
            if not archivo.endswith(".json"):
                continue
                
            ruta = os.path.join(carpeta, archivo)
            try:
                with open(ruta, encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"Leyendo {archivo} - Tipo:", data.get("area"))  # Debug
                    
                    if "barcaza_ops" in archivo:
                        registros_ops.append(data)
                    elif "barcaza_bita" in archivo:
                        registros_bita.append(data)
            except Exception as e:
                print(f"Error leyendo {archivo}: {e}")
                continue

        print("Registros OPS encontrados:", len(registros_ops))  # Debug
        print("Registros BITA encontrados:", len(registros_bita))  # Debug

        # Tomar el más reciente de cada tipo
        datos_ops = registros_ops[0]["datos"] if registros_ops else []
        datos_bita = registros_bita[0]["datos"] if registros_bita else []

        return render_template("reporte_barcaza.html",
            datos_ops=datos_ops,
            datos_bita=datos_bita,
            nombre=session.get("nombre"))
            
    except Exception as e:
        print("Error general en reporte_barcaza:", e)
        flash("Error al generar el reporte", "danger")
        return redirect(url_for('barcaza'))

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

@app.route('/guardar-registro-transito-<tipo_transito>', methods=['POST']) # Asegúrate que el nombre del parámetro es tipo_transito
@login_required
def guardar_transito(tipo_transito): # tipo_transito será 'general' o 'refineria'
    # --- INICIO VERIFICACIÓN DE HORA PARA TRÁNSITO ---
    HORA_LIMITE = time(10, 0, 0)
    hora_actual_servidor = datetime.now().time()

    if hora_actual_servidor >= HORA_LIMITE:
        mensaje = f"No se pueden registrar datos de tránsito ('{tipo_transito}') después de las {HORA_LIMITE.strftime('%I:%M %p')}."
        return jsonify(success=False, message=mensaje), 403
    # --- FIN VERIFICACIÓN DE HORA ---

    datos = request.get_json() # Estos son los datos de la tabla (lista de filas)
    fecha_registro = datetime.now() # Usar el objeto datetime completo
    fecha_str_archivo = fecha_registro.strftime("%Y-%m-%d_%H-%M-%S") # Para el nombre del archivo

    carpeta = "registros"
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"transito_{tipo_transito}_{fecha_str_archivo}.json")

    data_to_save = {
        "timestamp_iso": fecha_registro.isoformat(), # Fecha/hora del guardado en formato ISO
        "fecha_guardado_str": fecha_str_archivo, # Para compatibilidad o visualización simple
        "tipo_transito": tipo_transito, # 'general' o 'refineria'
        "usuario": session.get("nombre"),
        "datos": datos # La lista de filas que viene del frontend
    }

    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        return jsonify(success=True, message=f"Registro de tránsito '{tipo_transito}' guardado.")
    except Exception as e:
        print(f"Error al guardar registro de transito '{tipo_transito}': {e}")
        return jsonify(success=False, message=str(e)), 500

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

    # El resto de tu lógica para cargar datos del dashboard sigue aquí...
    carpeta = "registros"
    os.makedirs(carpeta, exist_ok=True)
    
    planta_summary = None
    try:
        archivos_planta = sorted([a for a in os.listdir(carpeta) if a.startswith("planta_") and a.endswith(".json")], reverse=True)
        if archivos_planta:
            with open(os.path.join(carpeta, archivos_planta[0]), encoding='utf-8') as f:
                planta_summary = json.load(f)
    except Exception as e:
        print(f"Error cargando resumen planta para dashboard: {e}")
        planta_summary = {"datos": [], "fecha": "N/A", "usuario": "N/A"} 

    barcaza_ops_summary = None
    try:
        archivos_ops = sorted([a for a in os.listdir(carpeta) if a.startswith("barcaza_ops_") and a.endswith(".json")], reverse=True)
        if archivos_ops:
            with open(os.path.join(carpeta, archivos_ops[0]), encoding='utf-8') as f:
                barcaza_ops_summary = json.load(f) 
    except Exception as e:
        print(f"Error cargando resumen barcaza OPS para dashboard: {e}")
        barcaza_ops_summary = {"datos": []} 

    barcaza_bita_summary = [] 
    try:
        archivos_bita = sorted([a for a in os.listdir(carpeta) if a.startswith("barcaza_bita_") and a.endswith(".json")], reverse=True)
        if archivos_bita:
            with open(os.path.join(carpeta, archivos_bita[0]), encoding='utf-8') as f:
                data_bita_cruda = json.load(f)
                if data_bita_cruda and "datos" in data_bita_cruda and isinstance(data_bita_cruda["datos"], list):
                    bita_cruda = data_bita_cruda["datos"]
                    datos_cr_recientes = bita_cruda[0:10] if len(bita_cruda) >= 10 else []
                    datos_margoth_recientes = bita_cruda[10:20] if len(bita_cruda) >= 20 else []
                    datos_odisea_recientes = bita_cruda[20:30] if len(bita_cruda) >= 30 else []
                    grupos = {
                        "Barcaza CR": datos_cr_recientes,
                        "Barcaza Margoth": datos_margoth_recientes,
                        "Barcaza Odisea": datos_odisea_recientes
                    }
                    temp_bita_procesada = []
                    for nombre_barc, tanques in grupos.items():
                        if not tanques: continue 
                        total_bls = sum(float(t.get("BLS_60", 0) or 0) for t in tanques)
                        max_cap = sum(float(t.get("MAX_CAP", 0) or 0) for t in tanques)
                        producto_barcaza = tanques[0].get("PRODUCTO", "VLSFO") if tanques and tanques[0] else "VLSFO"
                        temp_bita_procesada.append({
                            "TK": nombre_barc, "MAX_CAP": max_cap, "BLS_60": total_bls,
                            "PRODUCTO": producto_barcaza
                        })
                    barcaza_bita_summary = temp_bita_procesada
    except Exception as e:
        print(f"Error cargando/procesando resumen barcaza BITA para dashboard: {e}")

    transito_summary = {"datos_reporte": [], "total_nsv_general": 0}
    try:
        registros_transito_archivos = []
        for archivo in sorted(os.listdir(carpeta), reverse=True):
            if archivo.startswith("transito_") and archivo.endswith(".json"):
                with open(os.path.join(carpeta, archivo), encoding='utf-8') as f:
                    contenido_archivo = json.load(f)
                    if "datos" in contenido_archivo and isinstance(contenido_archivo["datos"], list):
                        tipo_transito_archivo = contenido_archivo.get("tipo", "general") 
                        for reg in contenido_archivo["datos"]:
                            reg["TIPO_ARCHIVO"] = tipo_transito_archivo 
                            registros_transito_archivos.append(reg)
        consolidado = {}
        if registros_transito_archivos:
            for registro in registros_transito_archivos:
                if not registro.get("PRODUCTO") or registro.get("NSV") is None: continue
                producto = registro["PRODUCTO"]
                tipo = "Refinería" if "refineria" in registro.get("TIPO_ARCHIVO", "").lower() else "EDSM"
                nsv = float(registro["NSV"]) if registro["NSV"] else 0
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
            transito_summary["total_nsv_general"] = total_nsv_general_temp
    except Exception as e:
        print(f"Error procesando resumen tránsito para dashboard: {e}")

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
    # Estructura: { "Refinería": { "ORIGEN_A": { "PRODUCTO_1": NSV_SUM, ... }, ... }, "EDSM": { ... } }
    datos_consolidados = {"Refinería": {}, "EDSM": {}}
    # Estructura: { "Refinería": { "ORIGEN_A": { "PRODUCTO_1": COUNT, ... }, ... }, "EDSM": { ... } }
    datos_conteo_camiones = {"Refinería": {}, "EDSM": {}}
    
    carpeta = "registros"
    os.makedirs(carpeta, exist_ok=True) 

    archivos_procesados = 0
    registros_totales_leidos = 0

    for archivo_nombre in sorted(os.listdir(carpeta), reverse=True):
        if archivo_nombre.startswith("transito_") and archivo_nombre.endswith(".json"):
            ruta_completa = os.path.join(carpeta, archivo_nombre)
            try:
                with open(ruta_completa, 'r', encoding='utf-8') as f:
                    data_archivo = json.load(f)
                
                # Usar 'tipo_transito' si existe (de guardados nuevos), sino 'tipo' (para compatibilidad)
                tipo_archivo_guardado = data_archivo.get("tipo_transito") or data_archivo.get("tipo") 
                registros_individuales = data_archivo.get("datos", [])
                
                if not tipo_archivo_guardado or not isinstance(registros_individuales, list):
                    print(f"Advertencia: Archivo {archivo_nombre} con formato inesperado. Omitiendo.")
                    continue

                tipo_destino_reporte = "Refinería" if tipo_archivo_guardado == "refineria" else "EDSM"
                
                archivos_procesados += 1
                for reg in registros_individuales:
                    registros_totales_leidos += 1
                    
                    # ---- MODIFICACIÓN PARA INCLUIR ORIGEN ----
                    origen = reg.get("ORIGEN", "Origen Desconocido") # Obtener ORIGEN, con un valor por defecto
                    producto = reg.get("PRODUCTO")
                    nsv_str = reg.get("NSV")

                    if not producto or nsv_str is None:
                        continue
                    
                    try:
                        nsv = float(str(nsv_str).replace(',', '.')) 
                    except ValueError:
                        print(f"Advertencia: Valor NSV no numérico '{nsv_str}' para Origen '{origen}', Producto '{producto}' en {archivo_nombre}. Omitiendo.")
                        continue

                    # Inicializar diccionarios para el origen si no existen
                    if origen not in datos_consolidados[tipo_destino_reporte]:
                        datos_consolidados[tipo_destino_reporte][origen] = {}
                        datos_conteo_camiones[tipo_destino_reporte][origen] = {}
                    
                    # Inicializar contadores/sumadores para el producto dentro del origen si no existen
                    if producto not in datos_consolidados[tipo_destino_reporte][origen]:
                        datos_consolidados[tipo_destino_reporte][origen][producto] = 0
                        datos_conteo_camiones[tipo_destino_reporte][origen][producto] = 0
                    
                    datos_consolidados[tipo_destino_reporte][origen][producto] += nsv
                    datos_conteo_camiones[tipo_destino_reporte][origen][producto] += 1
                    # ---- FIN MODIFICACIÓN ----
            
            except json.JSONDecodeError:
                print(f"Error: Archivo JSON corrupto - {archivo_nombre}. Omitiendo.")
            except Exception as e:
                print(f"Error procesando archivo {archivo_nombre} para reporte_transito: {e}")
    
    # Redondear los valores NSV antes de pasar a la plantilla
    for tipo_dest, origenes_data in datos_consolidados.items():
        for origen_key, productos_data in origenes_data.items():
            for prod_key, nsv_sum in productos_data.items():
                datos_consolidados[tipo_dest][origen_key][prod_key] = round(nsv_sum, 2)

    print(f"Reporte Tránsito - Datos Consolidados: {json.dumps(datos_consolidados, indent=2)}") # Para depuración
    print(f"Reporte Tránsito - Conteo Camiones: {json.dumps(datos_conteo_camiones, indent=2)}") # Para depuración

    return render_template("reporte_transito.html",
                           datos_consolidados=datos_consolidados,
                           datos_conteo_camiones=datos_conteo_camiones,
                           nombre=session.get("nombre"))
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
