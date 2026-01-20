import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests 
import hashlib 

# Configuración de página
st.set_page_config(page_title="Acceso Seguro", layout="wide")

# --- CSS: OCULTAR MENÚ STREAMLIT ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
# Inicializamos variables para guardar los datos individuales
if 'logueado' not in st.session_state: st.session_state['logueado'] = False
if 'usuario_telefono' not in st.session_state: st.session_state['usuario_telefono'] = ""
if 'usuario_nombre_completo' not in st.session_state: st.session_state['usuario_nombre_completo'] = ""
# Variables específicas para editar perfil
if 'user_nombre' not in st.session_state: st.session_state['user_nombre'] = ""
if 'user_apellido' not in st.session_state: st.session_state['user_apellido'] = ""
if 'user_correo' not in st.session_state: st.session_state['user_correo'] = ""
if 'datos_completos' not in st.session_state: st.session_state['datos_completos'] = False

# Variable para controlar el menú de navegación
if 'seccion_activa' not in st.session_state: st.session_state['seccion_activa'] = "🔍 Buscador"

# --- ENCRIPTACIÓN ---
def encriptar(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

# --- TELEGRAM ---
def enviar_telegram(mensaje):
    try:
        token = st.secrets["general"]["telegram_token"]
        chat_id = st.secrets["general"]["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
        requests.post(url, data=data)
    except:
        pass

# --- GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        json_creds = json.loads(st.secrets["general"]["google_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
        client = gspread.authorize(creds)
        
        archivo = client.open("BuscadorDB")
        sheet_datos = archivo.sheet1
        try: sheet_reportes = archivo.worksheet("Reportes")
        except: sheet_reportes = None
        try: sheet_usuarios = archivo.worksheet("Usuarios")
        except: sheet_usuarios = None
            
        return sheet_datos, sheet_reportes, sheet_usuarios
    except Exception as e:
        return None, None, None

hoja, hoja_reportes, hoja_usuarios = conectar_sheet()

# ==========================================
# 1. LOGIN (Ahora guarda datos individuales)
# ==========================================
def mostrar_login():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("🔒 Ingreso Usuarios")
        with st.form("login_form"):
            tel_input = st.text_input("📱 Número de Teléfono")
            pass_input = st.text_input("🔑 Contraseña", type="password")
            entrar = st.form_submit_button("Ingresar", use_container_width=True)
            
            if entrar:
                if hoja_usuarios:
                    try:
                        usuarios_db = hoja_usuarios.get_all_records()
                        encontrado = False
                        for i, u in enumerate(usuarios_db):
                            fila_excel = i + 2
                            db_tel = str(u.get('Telefono', '')).strip()
                            db_pass = str(u.get('Password', '')).strip()
                            
                            es_temporal = (db_pass == pass_input.strip())
                            es_encriptada = (db_pass == encriptar(pass_input.strip()))
                            
                            if db_tel == tel_input.strip() and (es_temporal or es_encriptada):
                                st.session_state['logueado'] = True
                                st.session_state['usuario_telefono'] = db_tel
                                st.session_state['fila_usuario'] = fila_excel 
                                
                                # Guardamos datos individuales para el perfil
                                nombre_db = str(u.get('Nombre', '')).strip()
                                apellido_db = str(u.get('Apellido', '')).strip()
                                correo_db = str(u.get('Correo', '')).strip()
                                
                                st.session_state['user_nombre'] = nombre_db
                                st.session_state['user_apellido'] = apellido_db
                                st.session_state['user_correo'] = correo_db
                                
                                if nombre_db:
                                    st.session_state['datos_completos'] = True
                                    st.session_state['usuario_nombre_completo'] = f"{nombre_db} {apellido_db}"
                                else:
                                    st.session_state['datos_completos'] = False
                                
                                encontrado = True
                                st.success("Correcto")
                                time.sleep(0.5)
                                st.rerun()
                                break
                        if not encontrado: st.error("Datos incorrectos.")
                    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 2. REGISTRO INICIAL
# ==========================================
def mostrar_registro_inicial():
    st.title("👋 Bienvenido")
    st.warning("Configura tu cuenta.")
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1: nuevo_nombre = st.text_input("Nombre:")
        with col2: nuevo_apellido = st.text_input("Apellido:")
        nuevo_correo = st.text_input("Correo:")
        st.markdown("---")
        nueva_clave = st.text_input("Nueva contraseña:", type="password")
        confirmar_clave = st.text_input("Repite contraseña:", type="password")
        
        if st.form_submit_button("Guardar"):
            if nuevo_nombre and nueva_clave == confirmar_clave:
                try:
                    f = st.session_state['fila_usuario']
                    hoja_usuarios.update_cell(f, 2, encriptar(nueva_clave))
                    hoja_usuarios.update_cell(f, 3, nuevo_nombre)
                    hoja_usuarios.update_cell(f, 4, nuevo_apellido)
                    hoja_usuarios.update_cell(f, 5, nuevo_correo)
                    
                    st.session_state['datos_completos'] = True
                    st.session_state['usuario_nombre_completo'] = f"{nuevo_nombre} {nuevo_apellido}"
                    st.session_state['user_nombre'] = nuevo_nombre
                    st.session_state['user_apellido'] = nuevo_apellido
                    st.session_state['user_correo'] = nuevo_correo
                    
                    st.rerun()
                except: st.error("Error guardando.")
            else: st.error("Verifica los datos.")

# ==========================================
# 3. APP PRINCIPAL
# ==========================================
def mostrar_app():
    
    # --- BARRA LATERAL (BOTONES) ---
    with st.sidebar:
        st.markdown("# 👤") 
        st.write(f"Hola, **{st.session_state['usuario_nombre_completo']}**")
        st.caption(f"📱 {st.session_state['usuario_telefono']}")
        st.markdown("---")
        
        # BOTONES DE NAVEGACIÓN
        if st.button("🔍 Buscador", use_container_width=True):
            st.session_state['seccion_activa'] = "🔍 Buscador"
            
        if st.button("➕ Registrar Nueva", use_container_width=True):
            st.session_state['seccion_activa'] = "➕ Registrar Nueva"
            
        if st.button("💬 Sugerencias", use_container_width=True):
            st.session_state['seccion_activa'] = "💬 Sugerencias"
            
        if st.button("⚙️ Mi Perfil", use_container_width=True):
            st.session_state['seccion_activa'] = "⚙️ Mi Perfil"
        
        st.markdown("---")
        if st.button("Cerrar Sesión", use_container_width=True):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()

    # Leemos la sección activa
    opcion = st.session_state['seccion_activa']

    # ----------------------------------------------------
    # PANTALLA 1: BUSCADOR
    # ----------------------------------------------------
    if opcion == "🔍 Buscador":
        st.title("🔍 Buscador de Direcciones")
        if not hoja: st.stop()
        try: registros = hoja.get_all_records()
        except: st.stop()

        lista_direcciones = []
        if registros:
            lista_direcciones = [str(r.get('Direccion', '')) for r in registros if r.get('Direccion')]

        busqueda_seleccion = st.selectbox(
            "Selecciona una dirección:", 
            options=lista_direcciones, 
            index=None, 
            placeholder="Escribe para buscar...",
        )

        if busqueda_seleccion:
            resultados = [r for i, r in enumerate(registros) if str(r.get('Direccion', '')) == busqueda_seleccion]
            for i, r in enumerate(registros):
                if str(r.get('Direccion', '')) == busqueda_seleccion: r['_id'] = i
            
            if resultados:
                for item in resultados:
                    st.success("✅ Dirección encontrada")
                    with st.container():
                        c1, c2, c3 = st.columns([3, 2, 1])
                        with c1:
                            st.caption("Dirección")
                            st.write(f"**{item.get('Direccion')}**")
                        with c2:
                            st.caption("Ubicación")
                            st.write(f"{item.get('Ciudad')}, {item.get('Estado')}")
                        with c3:
                            st.caption("Código")
                            st.markdown(f"### {item.get('Codigo')}")
                        
                        with st.expander(f"Reportar fallo"):
                            with st.form(f"rep_{item.get('_id', 0)}"):
                                nc = st.text_input("Nuevo código:")
                                nt = st.text_input("Nota:")
                                if st.form_submit_button("Enviar"):
                                    quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                                    hoja_reportes.append_row([item.get('Direccion'), item.get('Ciudad'), item.get('Codigo'), nc, nt, quien])
                                    enviar_telegram(f"🚨 <b>REPORTE</b>\n👤 {st.session_state['usuario_nombre_completo']}\n📍 {item.get('Direccion')}\n🔑 {nc}")
                                    st.success("Listo.")
                    st.divider()
        else:
            st.info("👈 Usa el menú de botones si necesitas registrar una nueva.")

    # ----------------------------------------------------
    # PANTALLA 2: REGISTRAR NUEVA
    # ----------------------------------------------------
    elif opcion == "➕ Registrar Nueva":
        st.title("➕ Registrar Nueva Dirección")
        st.warning("Asegúrate de que la dirección no exista ya en el Buscador.")
        
        with st.form("registro_direccion"):
            nueva_dir = st.text_input("Dirección Completa:", placeholder="Ej: 123 Main St")
            c1, c2 = st.columns(2)
            with c1: ciu = st.text_input("Ciudad:", placeholder="Dallas")
            with c2: est = st.text_input("Estado:", placeholder="TX")
            cod = st.text_input("Código de acceso:", placeholder="#1234")
            
            if st.form_submit_button("Guardar Dirección", use_container_width=True):
                if nueva_dir and cod and ciu and est:
                    quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                    hoja.append_row([nueva_dir, ciu, est, cod, quien])
                    enviar_telegram(f"🆕 <b>NUEVO</b>\n👤 {st.session_state['usuario_nombre_completo']}\n📍 {nueva_dir}\n🔑 {cod}")
                    st.success("¡Guardada exitosamente!")
                else:
                    st.error("Por favor completa todos los campos.")

    # ----------------------------------------------------
    # PANTALLA 3: SUGERENCIAS
    # ----------------------------------------------------
    elif opcion == "💬 Sugerencias":
        st.title("💬 Buzón de Sugerencias")
        st.write("Tu opinión nos ayuda a mejorar la aplicación.")
        
        with st.form("form_sug"):
            msg = st.text_area("Escribe tu mensaje o idea aquí:")
            if st.form_submit_button("Enviar Sugerencia", use_container_width=True):
                if msg:
                    enviar_telegram(f"💡 <b>SUGERENCIA</b>\n👤 {st.session_state['usuario_nombre_completo']}\n📱 {st.session_state['usuario_telefono']}\n💬 {msg}")
                    st.success("¡Mensaje enviado! Gracias.")
                else:
                    st.error("El mensaje no puede estar vacío.")

    # ----------------------------------------------------
    # PANTALLA 4: MI PERFIL (PRE-CARGADO)
    # ----------------------------------------------------
    elif opcion == "⚙️ Mi Perfil":
        st.title("⚙️ Configuración de Perfil")
        
        # Pestañas
        tab1, tab2 = st.tabs(["📝 Mis Datos", "🔑 Contraseña"])
        
        # --- PESTAÑA 1: MODIFICAR DATOS ---
        with tab1:
            st.write("Corrige o actualiza tu información.")
            with st.form("form_datos"):
                c1, c2 = st.columns(2)
                # AQUÍ ESTÁ EL CAMBIO: Usamos 'value=' para precargar los datos
                with c1: 
                    up_nombre = st.text_input("Nombre:", value=st.session_state['user_nombre'])
                with c2: 
                    up_apellido = st.text_input("Apellido:", value=st.session_state['user_apellido'])
                
                up_correo = st.text_input("Correo Electrónico:", value=st.session_state['user_correo'])
                
                if st.form_submit_button("Actualizar Datos"):
                    if up_nombre and up_apellido and up_correo:
                        try:
                            # Buscar usuario por teléfono
                            usuarios_db = hoja_usuarios.get_all_records()
                            fila_encontrada = -1
                            
                            for i, u in enumerate(usuarios_db):
                                if str(u.get('Telefono', '')).strip() == st.session_state['usuario_telefono']:
                                    fila_encontrada = i + 2
                                    break
                            
                            if fila_encontrada > 0:
                                # Actualizamos Datos en Excel
                                hoja_usuarios.update_cell(fila_encontrada, 3, up_nombre)
                                hoja_usuarios.update_cell(fila_encontrada, 4, up_apellido)
                                hoja_usuarios.update_cell(fila_encontrada, 5, up_correo)
                                
                                # Actualizamos Sesión en la App
                                st.session_state['usuario_nombre_completo'] = f"{up_nombre} {up_apellido}"
                                st.session_state['user_nombre'] = up_nombre
                                st.session_state['user_apellido'] = up_apellido
                                st.session_state['user_correo'] = up_correo
                                
                                st.success("¡Información actualizada! Recargando...")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Error al encontrar tu usuario.")
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")
                    else:
                        st.error("Por favor completa todos los campos.")

        # --- PESTAÑA 2: CAMBIAR CLAVE ---
        with tab2:
            st.write("Cambia tu contraseña de acceso.")
            with st.form("cambio_pass"):
                clave_actual = st.text_input("Contraseña Actual:", type="password")
                clave_nueva = st.text_input("Nueva Contraseña:", type="password")
                clave_confirm = st.text_input("Confirmar Nueva:", type="password")
                
                if st.form_submit_button("Actualizar Contraseña"):
                    if clave_nueva == clave_confirm:
                        try:
                            usuarios_db = hoja_usuarios.get_all_records()
                            fila_encontrada = -1
                            
                            for i, u in enumerate(usuarios_db):
                                if str(u.get('Telefono', '')).strip() == st.session_state['usuario_telefono']:
                                    if str(u.get('Password', '')).strip() == encriptar(clave_actual):
                                        fila_encontrada = i + 2
                                        break
                            
                            if fila_encontrada > 0:
                                hoja_usuarios.update_cell(fila_encontrada, 2, encriptar(clave_nueva))
                                st.success("¡Contraseña actualizada con éxito!")
                            else:
                                st.error("La contraseña actual es incorrecta.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Las contraseñas nuevas no coinciden.")

    # Footer invisible
    st.markdown("<div style='text-align: center; color: grey;'><small>v5.7.2</small></div>", unsafe_allow_html=True)

# ==========================================
# CONTROL
# ==========================================
if not st.session_state['logueado']: mostrar_login()
else:
    if st.session_state['datos_completos']: mostrar_app()
    else: mostrar_registro_inicial()
