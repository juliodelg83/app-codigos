import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests 
import hashlib 

# Configuración de página
st.set_page_config(page_title="App Direcciones", layout="centered")

# --- 🎨 CSS: ESTILO MÓVIL ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* Ajuste botones inferiores */
            div.stButton > button {
                width: 100%;
                border-radius: 8px;
                height: auto;
                padding: 10px 5px;
                font-size: 14px;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'logueado' not in st.session_state: st.session_state['logueado'] = False
if 'usuario_telefono' not in st.session_state: st.session_state['usuario_telefono'] = ""
if 'usuario_nombre_completo' not in st.session_state: st.session_state['usuario_nombre_completo'] = ""
# Datos perfil
if 'user_nombre' not in st.session_state: st.session_state['user_nombre'] = ""
if 'user_apellido' not in st.session_state: st.session_state['user_apellido'] = ""
if 'user_correo' not in st.session_state: st.session_state['user_correo'] = ""
if 'datos_completos' not in st.session_state: st.session_state['datos_completos'] = False

# Control de navegación (Por defecto: Buscador)
if 'seccion_activa' not in st.session_state: st.session_state['seccion_activa'] = "Buscador"

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
# 1. LOGIN
# ==========================================
def mostrar_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.title("🔒 Ingreso")
    
    with st.form("login_form"):
        tel_input = st.text_input("📱 Teléfono")
        pass_input = st.text_input("🔑 Contraseña", type="password")
        entrar = st.form_submit_button("Entrar", use_container_width=True)
        
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
                            st.success("¡Bienvenido!")
                            time.sleep(0.5)
                            st.rerun()
                            break
                    if not encontrado: st.error("Datos incorrectos.")
                except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 2. REGISTRO INICIAL
# ==========================================
def mostrar_registro_inicial():
    st.title("👋 Configurar Cuenta")
    with st.form("registro_form"):
        c1, c2 = st.columns(2)
        with c1: nuevo_nombre = st.text_input("Nombre:")
        with c2: nuevo_apellido = st.text_input("Apellido:")
        nuevo_correo = st.text_input("Correo:")
        st.markdown("---")
        nueva_clave = st.text_input("Contraseña Nueva:", type="password")
        confirmar_clave = st.text_input("Repetir Contraseña:", type="password")
        
        if st.form_submit_button("Guardar Datos", use_container_width=True):
            if nuevo_nombre and nuevo_clave == confirmar_clave:
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
            else: st.error("Error en los datos.")

# ==========================================
# 3. APP PRINCIPAL (DISEÑO MÓVIL)
# ==========================================
def mostrar_app():
    
    # --- CABECERA ---
    # Solo el saludo, sin subtítulos extra
    st.markdown(f"### 👋 Hola, {st.session_state['user_nombre']}")
    st.markdown("---")

    # --- CONTENIDO SEGÚN SECCIÓN ---
    seccion = st.session_state['seccion_activa']

    # 1. BUSCADOR
    if seccion == "Buscador":
        if not hoja: st.stop()
        try: registros = hoja.get_all_records()
        except: st.stop()
        
        lista_dirs = [str(r.get('Direccion', '')) for r in registros if r.get('Direccion')]
        
        # CAMBIO AQUÍ: Título más claro
        st.subheader("🔍 Buscar Dirección")
        busqueda = st.selectbox("Escribe dirección:", options=lista_dirs, index=None, placeholder="Tocá aquí para buscar...")
        
        if busqueda:
            res = [r for i,r in enumerate(registros) if str(r.get('Direccion','')) == busqueda]
            for i,r in enumerate(registros):
                if str(r.get('Direccion','')) == busqueda: r['_id'] = i
            
            if res:
                for item in res:
                    st.success("✅ Encontrada")
                    with st.container(border=True):
                        st.markdown(f"📍 **{item.get('Direccion')}**")
                        st.write(f"🏙 {item.get('Ciudad')}, {item.get('Estado')}")
                        st.markdown(f"## 🔑 {item.get('Codigo')}")
                        
                        with st.expander("Reportar Error"):
                            with st.form(f"rep_{item.get('_id')}"):
                                nc = st.text_input("Nuevo código:")
                                nt = st.text_input("Nota:")
                                if st.form_submit_button("Reportar"):
                                    quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                                    hoja_reportes.append_row([item.get('Direccion'), item.get('Ciudad'), item.get('Codigo'), nc, nt, quien])
                                    enviar_telegram(f"🚨 <b>REPORTE</b>\n👤 {st.session_state['usuario_nombre_completo']}\n📍 {item.get('Direccion')}\n🔑 {nc}")
                                    st.success("Enviado")
        else:
            st.info("Utiliza el botón '➕ Nuevo' abajo si la dirección no existe.")

    # 2. REGISTRAR
    elif seccion == "Registrar":
        st.subheader("➕ Nueva Dirección")
        with st.form("reg_form"):
            nd = st.text_input("Dirección:")
            c1, c2 = st.columns(2)
            with c1: ci = st.text_input("Ciudad:", value="Dallas")
            with c2: es = st.text_input("Estado:", value="TX")
            co = st.text_input("Código:")
            
            if st.form_submit_button("Guardar", use_container_width=True):
                if nd and co:
                    quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                    hoja.append_row([nd, ci, es, co, quien])
                    enviar_telegram(f"🆕 <b>NUEVO</b>\n👤 {st.session_state['usuario_nombre_completo']}\n📍 {nd}\n🔑 {co}")
                    st.success("Guardado")
                    time.sleep(1)
                    st.session_state['seccion_activa'] = "Buscador"
                    st.rerun()
                else:
                    st.error("Faltan datos")

    # 3. SUGERENCIAS
    elif seccion == "Sugerencias":
        st.subheader("💬 Sugerencias")
        with st.form("sug_form"):
            txt = st.text_area("Mensaje:")
            if st.form_submit_button("Enviar", use_container_width=True):
                if txt:
                    enviar_telegram(f"💡 <b>SUGERENCIA</b>\n👤 {st.session_state['usuario_nombre_completo']}\n💬 {txt}")
                    st.success("Enviado")

    # 4. PERFIL
    elif seccion == "Perfil":
        st.subheader("⚙️ Mi Perfil")
        tab1, tab2 = st.tabs(["Mis Datos", "Contraseña"])
        
        with tab1:
            with st.form("edit_perfil"):
                un = st.text_input("Nombre:", value=st.session_state['user_nombre'])
                ua = st.text_input("Apellido:", value=st.session_state['user_apellido'])
                uc = st.text_input("Correo:", value=st.session_state['user_correo'])
                if st.form_submit_button("Actualizar Datos"):
                    usuarios_db = hoja_usuarios.get_all_records()
                    for i, u in enumerate(usuarios_db):
                        if str(u.get('Telefono', '')).strip() == st.session_state['usuario_telefono']:
                            hoja_usuarios.update_cell(i+2, 3, un)
                            hoja_usuarios.update_cell(i+2, 4, ua)
                            hoja_usuarios.update_cell(i+2, 5, uc)
                            st.session_state['user_nombre'] = un
                            st.session_state['user_apellido'] = ua
                            st.session_state['user_correo'] = uc
                            st.session_state['usuario_nombre_completo'] = f"{un} {ua}"
                            st.success("Actualizado")
                            time.sleep(1)
                            st.rerun()

        with tab2:
            with st.form("edit_pass"):
                ca = st.text_input("Actual:", type="password")
                cn = st.text_input("Nueva:", type="password")
                cc = st.text_input("Repetir:", type="password")
                if st.form_submit_button("Cambiar Clave"):
                    usuarios_db = hoja_usuarios.get_all_records()
                    for i, u in enumerate(usuarios_db):
                        if str(u.get('Telefono', '')).strip() == st.session_state['usuario_telefono']:
                            if str(u.get('Password','')).strip() == encriptar(ca):
                                if cn == cc:
                                    hoja_usuarios.update_cell(i+2, 2, encriptar(cn))
                                    st.success("Clave cambiada")
                                else: st.error("No coinciden")
                            else: st.error("Clave actual mal")

    # --- BARRA DE NAVEGACIÓN INFERIOR ---
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    
    c_nav1, c_nav2, c_nav3, c_nav4, c_nav5 = st.columns(5)
    
    with c_nav1:
        if st.button("🔍 Buscar", use_container_width=True):
            st.session_state['seccion_activa'] = "Buscador"
            st.rerun()
    with c_nav2:
        if st.button("➕ Nuevo", use_container_width=True):
            st.session_state['seccion_activa'] = "Registrar"
            st.rerun()
    with c_nav3:
        if st.button("💬 Ideas", use_container_width=True):
            st.session_state['seccion_activa'] = "Sugerencias"
            st.rerun()
    with c_nav4:
        if st.button("⚙️ Perfil", use_container_width=True):
            st.session_state['seccion_activa'] = "Perfil"
            st.rerun()
    with c_nav5:
        if st.button("🚪 Salir", use_container_width=True):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()

# ==========================================
# CONTROL
# ==========================================
if not st.session_state['logueado']: mostrar_login()
else:
    if st.session_state['datos_completos']: mostrar_app()
    else: mostrar_registro_inicial()
