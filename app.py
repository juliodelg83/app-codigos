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

# --- 🎨 CSS ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            div.stButton > button {
                width: 100%;
                border-radius: 8px;
                padding: 10px 5px;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'logueado' not in st.session_state: st.session_state['logueado'] = False
if 'usuario_telefono' not in st.session_state: st.session_state['usuario_telefono'] = ""
if 'usuario_nombre_completo' not in st.session_state: st.session_state['usuario_nombre_completo'] = ""
if 'user_nombre' not in st.session_state: st.session_state['user_nombre'] = ""
if 'user_apellido' not in st.session_state: st.session_state['user_apellido'] = ""
if 'user_correo' not in st.session_state: st.session_state['user_correo'] = ""
if 'datos_completos' not in st.session_state: st.session_state['datos_completos'] = False

if 'seccion_activa' not in st.session_state: st.session_state['seccion_activa'] = "Buscador"
if 'modo_registro' not in st.session_state: st.session_state['modo_registro'] = False

# --- UTILS ---
def encriptar(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def enviar_telegram(mensaje):
    try:
        token = st.secrets["general"]["telegram_token"]
        chat_id = st.secrets["general"]["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
        requests.post(url, data=data)
    except: pass

@st.cache_resource
def conectar_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        json_creds = json.loads(st.secrets["general"]["google_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
        client = gspread.authorize(creds)
        archivo = client.open("BuscadorDB")
        return archivo.sheet1, archivo.worksheet("Reportes"), archivo.worksheet("Usuarios")
    except: return None, None, None

hoja, hoja_reportes, hoja_usuarios = conectar_sheet()

# ==========================================
# 1. SISTEMA DE ACCESO
# ==========================================
def mostrar_login():
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- VISTA REGISTRO ---
    if st.session_state['modo_registro']:
        st.title("📝 Solicitar Cuenta")
        st.caption("Llena tus datos. El administrador deberá aprobarte.")
        
        with st.form("registro_nuevo"):
            reg_nombre = st.text_input("Nombre:")
            reg_apellido = st.text_input("Apellido:")
            reg_tel = st.text_input("Teléfono:")
            reg_correo = st.text_input("Correo:")
            reg_pass = st.text_input("Contraseña:", type="password")
            
            if st.form_submit_button("Enviar Solicitud", use_container_width=True):
                if reg_nombre and reg_tel and reg_pass:
                    if hoja_usuarios:
                        try:
                            # Verificar duplicados
                            usuarios_db = hoja_usuarios.get_all_records()
                            existe = False
                            for u in usuarios_db:
                                if str(u.get('Telefono', '')).strip() == reg_tel.strip():
                                    existe = True; break
                            
                            if existe:
                                st.error("⚠️ Teléfono ya registrado.")
                            else:
                                # Guardar como Pendiente
                                hoja_usuarios.append_row([reg_tel, encriptar(reg_pass), reg_nombre, reg_apellido, reg_correo, "Pendiente"])
                                enviar_telegram(f"🔔 <b>NUEVO</b>\n👤 {reg_nombre} {reg_apellido}\n📱 {reg_tel}\n⚠️ Estado: Pendiente")
                                st.success("✅ Solicitud enviada.")
                                st.info("Espera aprobación del administrador.")
                                time.sleep(3)
                                st.session_state['modo_registro'] = False
                                st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                else: st.error("Faltan datos.")
        
        st.markdown("---")
        if st.button("⬅️ Volver", use_container_width=True):
            st.session_state['modo_registro'] = False
            st.rerun()

    # --- VISTA LOGIN ---
    else:
        st.title("🔒 Ingreso")
        with st.form("login_form"):
            tel_input = st.text_input("📱 Teléfono")
            pass_input = st.text_input("🔑 Contraseña", type="password")
            
            if st.form_submit_button("Entrar", use_container_width=True):
                if hoja_usuarios:
                    try:
                        usuarios_db = hoja_usuarios.get_all_records()
                        encontrado = False
                        for i, u in enumerate(usuarios_db):
                            db_tel = str(u.get('Telefono', '')).strip()
                            db_pass = str(u.get('Password', '')).strip()
                            db_estado = str(u.get('Estado', '')).strip().lower() # Leemos el estado
                            
                            if db_tel == tel_input.strip() and (db_pass == pass_input.strip() or db_pass == encriptar(pass_input.strip())):
                                encontrado = True
                                
                                # LÓGICA DE ESTADOS
                                if db_estado == "activo":
                                    st.session_state['logueado'] = True
                                    st.session_state['usuario_telefono'] = db_tel
                                    st.session_state['fila_usuario'] = i + 2
                                    st.session_state['user_nombre'] = str(u.get('Nombre', '')).strip()
                                    st.session_state['user_apellido'] = str(u.get('Apellido', '')).strip()
                                    st.session_state['user_correo'] = str(u.get('Correo', '')).strip()
                                    
                                    if st.session_state['user_nombre']:
                                        st.session_state['datos_completos'] = True
                                        st.session_state['usuario_nombre_completo'] = f"{st.session_state['user_nombre']} {st.session_state['user_apellido']}"
                                    else:
                                        st.session_state['datos_completos'] = False
                                        
                                    st.success(f"¡Hola {st.session_state['user_nombre']}!")
                                    time.sleep(0.5)
                                    st.rerun()
                                
                                elif db_estado == "pendiente":
                                    st.warning("⏳ Tu cuenta está **Pendiente**. El administrador aún no la ha aprobado.")
                                
                                elif db_estado == "desactivado":
                                    st.error("⛔ Tu cuenta ha sido **Desactivada**. Contacta al soporte.")
                                
                                else:
                                    st.error("⚠️ Estado de cuenta desconocido.")
                                break
                        
                        if not encontrado: st.error("Datos incorrectos.")
                    except Exception as e: st.error(f"Error: {e}")

        st.write("")
        st.markdown("¿No tienes cuenta?")
        if st.button("📝 Crear Cuenta Nueva", use_container_width=True):
            st.session_state['modo_registro'] = True
            st.rerun()

# ==========================================
# 2. PERFIL INICIAL
# ==========================================
def mostrar_registro_inicial():
    st.title("👋 Completar Perfil")
    with st.form("registro_form"):
        c1, c2 = st.columns(2)
        with c1: nuevo_nombre = st.text_input("Nombre:")
        with c2: nuevo_apellido = st.text_input("Apellido:")
        nuevo_correo = st.text_input("Correo:")
        
        if st.form_submit_button("Guardar Datos", use_container_width=True):
            if nuevo_nombre:
                try:
                    f = st.session_state['fila_usuario']
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

# ==========================================
# 3. APP PRINCIPAL
# ==========================================
def mostrar_app():
    st.markdown(f"### 👋 Hola, {st.session_state['user_nombre']}")
    st.markdown("---")
    seccion = st.session_state['seccion_activa']

    # 1. BUSCADOR
    if seccion == "Buscador":
        if not hoja: st.stop()
        try: registros = hoja.get_all_records()
        except: st.stop()
        
        lista_dirs = [str(r.get('Direccion', '')) for r in registros if r.get('Direccion')]
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
                                    enviar_telegram(f"🚨 <b>REPORTE</b>\n👤 {quien}\n📍 {item.get('Direccion')}\n🔑 {nc}")
                                    st.success("Enviado")
        else: st.info("Utiliza el botón '➕ Nuevo' abajo si la dirección no existe.")

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
                    enviar_telegram(f"🆕 <b>NUEVO</b>\n👤 {quien}\n📍 {nd}\n🔑 {co}")
                    st.success("Guardado")
                    time.sleep(1)
                    st.session_state['seccion_activa'] = "Buscador"
                    st.rerun()
                else: st.error("Faltan datos")

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

    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    c_nav1, c_nav2, c_nav3, c_nav4, c_nav5 = st.columns(5)
    with c_nav1:
        if st.button("🔍 Buscar", use_container_width=True): st.session_state['seccion_activa'] = "Buscador"; st.rerun()
    with c_nav2:
        if st.button("➕ Nuevo", use_container_width=True): st.session_state['seccion_activa'] = "Registrar"; st.rerun()
    with c_nav3:
        if st.button("💬 Ideas", use_container_width=True): st.session_state['seccion_activa'] = "Sugerencias"; st.rerun()
    with c_nav4:
        if st.button("⚙️ Perfil", use_container_width=True): st.session_state['seccion_activa'] = "Perfil"; st.rerun()
    with c_nav5:
        if st.button("🚪 Salir", use_container_width=True):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()

if not st.session_state['logueado']: mostrar_login()
else:
    if st.session_state['datos_completos']: mostrar_app()
    else: mostrar_registro_inicial()
