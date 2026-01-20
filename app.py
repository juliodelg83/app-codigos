import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests 
import hashlib 
from datetime import datetime

# ==========================================
# 👑 CONFIGURACIÓN GENERAL
# ==========================================
ADMIN_TELEFONO = "2142595696"
LINK_TELEGRAM = "https://t.me/BuscadordecodigosBot" 

# 👇 TU LOGO DE MAPA
LOGO_MAPA = "https://share.google/lYGxwInu3n38g4bI4"

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
            a { text-decoration: none; }
            /* Ajuste para centrar imagen en la columna */
            div[data-testid="stImage"] {
                display: flex;
                align-items: center;
                justify-content: center;
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
if 'memoria_direccion' not in st.session_state: st.session_state['memoria_direccion'] = ""
if 'vista_admin_login' not in st.session_state: st.session_state['vista_admin_login'] = False

# --- UTILS ---
def encriptar(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def capitalizar_palabras(texto):
    if not texto: return ""
    return ' '.join(word.capitalize() for word in texto.lower().split())

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
# ⚙️ AUTO-LOGIN
# ==========================================
def intentar_autologin():
    query_params = st.query_params
    movil_guardado = query_params.get("movil", None)

    if movil_guardado and not st.session_state['logueado']:
        if not movil_guardado.isdigit() or len(movil_guardado) != 10: return False
        
        if movil_guardado == ADMIN_TELEFONO: return False

        if hoja_usuarios:
            try:
                usuarios_db = hoja_usuarios.get_all_records()
                for i, u in enumerate(usuarios_db):
                    db_tel = str(u.get('Telefono', '')).strip()
                    db_estado = str(u.get('Estado', '')).strip().lower()
                    
                    if db_tel == movil_guardado:
                        if db_estado == "desactivado": return False
                        
                        st.session_state['logueado'] = True
                        st.session_state['usuario_telefono'] = db_tel
                        st.session_state['fila_usuario'] = i + 2
                        st.session_state['user_nombre'] = str(u.get('Nombre', '')).strip()
                        st.session_state['user_apellido'] = str(u.get('Apellido', '')).strip()
                        st.session_state['user_correo'] = str(u.get('Correo', '')).strip()
                        st.session_state['usuario_nombre_completo'] = f"{st.session_state['user_nombre']} {st.session_state['user_apellido']}"
                        st.session_state['datos_completos'] = True
                        st.toast(f"Hola {st.session_state['user_nombre']}")
                        return True
            except: pass
    return False

if not st.session_state['logueado']:
    intentar_autologin()

# ==========================================
# 1. PANTALLAS DE ACCESO
# ==========================================
def mostrar_acceso():
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- 👮 ADMIN ---
    if st.session_state['vista_admin_login']:
        st.title("👮 Acceso Administrador")
        with st.form("form_admin"):
            tel_admin = st.text_input("Usuario:", placeholder="Número de teléfono") 
            pass_admin = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if tel_admin == ADMIN_TELEFONO:
                    if hoja_usuarios:
                        try:
                            usuarios_db = hoja_usuarios.get_all_records()
                            encontrado_admin = False
                            for i, u in enumerate(usuarios_db):
                                if str(u.get('Telefono', '')).strip() == ADMIN_TELEFONO:
                                    db_pass = str(u.get('Password', '')).strip()
                                    if db_pass == encriptar(pass_admin) or db_pass == pass_admin:
                                        iniciar_sesion(ADMIN_TELEFONO, str(u.get('Nombre','Admin')), str(u.get('Apellido','')), "", i+2)
                                        encontrado_admin = True
                                        break
                            if not encontrado_admin: st.error("❌ Error de credenciales.")
                        except Exception as e: st.error(f"Error: {e}")
                else: st.error("⛔ Sin permisos.")
        
        st.write("")
        if st.button("⬅️ Volver", use_container_width=True):
            st.session_state['vista_admin_login'] = False
            st.rerun()

    # --- 📍 PANTALLA DE BIENVENIDA (LOGO + TEXTO) ---
    else:
        # ✅ CAMBIO: Logo al lado de Bienvenido
        col_logo, col_texto = st.columns([1, 4])
        with col_logo:
            # Usamos el link que proporcionaste
            st.image(LOGO_MAPA, width=80) 
        with col_texto:
            st.title("Bienvenido")

        st.write("Ingresa tus datos para acceder:")
        
        # 1. FORMULARIO WEB
        with st.form("form_acceso"):
            tel = st.text_input("📱 Teléfono (10 dígitos):", max_chars=10)
            c1, c2 = st.columns(2)
            with c1: nom = st.text_input("👤 Nombre:")
            with c2: ape = st.text_input("👤 Apellido:")
            
            entrar = st.form_submit_button("Ingresar", use_container_width=True)
            
            if entrar:
                if tel == ADMIN_TELEFONO: st.error("⛔ Número reservado.")
                elif not tel.isdigit() or len(tel) != 10: st.error("⚠️ Teléfono inválido.")
                elif not nom or not ape: st.error("⚠️ Faltan datos.")
                else:
                    if hoja_usuarios:
                        try:
                            usuarios_db = hoja_usuarios.get_all_records()
                            encontrado = False
                            for i, u in enumerate(usuarios_db):
                                if str(u.get('Telefono', '')).strip() == tel:
                                    encontrado = True
                                    if str(u.get('Estado', '')).strip().lower() == "desactivado":
                                        st.error("⛔ Acceso denegado.")
                                    else:
                                        fila = i + 2
                                        if str(u.get('Nombre','')) != nom:
                                            hoja_usuarios.update_cell(fila, 3, nom)
                                            hoja_usuarios.update_cell(fila, 4, ape)
                                        iniciar_sesion(tel, nom, ape, str(u.get('Correo','')), fila)
                                    break
                            
                            if not encontrado:
                                hoja_usuarios.append_row([tel, "N/A", nom, ape, "", "Activo", "Web"])
                                enviar_telegram(f"🆕 <b>NUEVO (Web)</b>\n👤 {nom} {ape}\n📱 {tel}")
                                iniciar_sesion(tel, nom, ape, "", len(usuarios_db) + 2)
                        except Exception as e: st.error(f"Error: {e}")

        # 2. BOTÓN DE TELEGRAM
        st.write("")
        st.markdown("---")
        st.link_button("✈️ Usar App en Telegram", LINK_TELEGRAM, use_container_width=True)

        st.write("")
        if st.button("👮 Acceso Admin", type="secondary", use_container_width=True):
            st.session_state['vista_admin_login'] = True
            st.rerun()

def iniciar_sesion(tel, nombre, apellido, correo, fila):
    st.session_state['logueado'] = True
    st.session_state['usuario_telefono'] = tel
    st.session_state['fila_usuario'] = fila
    st.session_state['user_nombre'] = nombre
    st.session_state['user_apellido'] = apellido
    st.session_state['user_correo'] = correo
    st.session_state['usuario_nombre_completo'] = f"{nombre} {apellido}"
    st.session_state['datos_completos'] = True
    if tel != ADMIN_TELEFONO: st.query_params["movil"] = tel
    st.success(f"¡Hola {nombre}!")
    time.sleep(0.5)
    st.rerun()

# ==========================================
# 2. APP PRINCIPAL
# ==========================================
def mostrar_app():
    es_admin = (st.session_state['usuario_telefono'] == ADMIN_TELEFONO)
    
    # Header
    c_head_1, c_head_2 = st.columns([3, 1])
    with c_head_1:
        st.markdown(f"### 👋 Hola, {st.session_state['user_nombre']}")
        if es_admin: st.caption("🛡️ Modo Admin")
    with c_head_2:
        st.link_button("📱 Bot", LINK_TELEGRAM)

    st.markdown("---")
    seccion = st.session_state['seccion_activa']

    # --- BUSCADOR ---
    if seccion == "Buscador":
        st.subheader("🔍 Buscar Dirección")
        registros = []
        error_carga = False
        
        if not hoja:
            st.error("❌ Sin conexión.")
            error_carga = True
        else:
            try: registros = hoja.get_all_records()
            except Exception as e: st.error(f"⚠️ Error: {e}"); error_carga = True

        if not error_carga:
            busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: 1234 Main St", key="search_box")
            if busqueda:
                busqueda_lower = busqueda.lower().strip()
                coincidencias = [r for r in registros if busqueda_lower in str(r.get('Direccion','')).lower()]
                if coincidencias:
                    st.success(f"✅ {len(coincidencias)} resultado(s):")
                    for item in coincidencias:
                        idx = next((i for i, r in enumerate(registros) if r == item), 0)
                        with st.container(border=True):
                            st.markdown(f"📍 **{item.get('Direccion')}**")
                            st.write(f"🏙 {item.get('Ciudad')}, {item.get('Estado')}")
                            st.markdown(f"## 🔑 {item.get('Codigo')}")
                            
                            origen = item.get('Origen', 'Desconocido')
                            if origen == 'Telegram': st.caption("📱 Telegram")
                            elif origen == 'Web': st.caption("🌐 Web")
                            else: st.caption(f"ℹ️ {origen}")
                            
                            with st.expander("Reportar Error"):
                                with st.form(f"rep_{idx}"):
                                    nc = st.text_input("Nuevo código:")
                                    nt = st.text_input("Nota:")
                                    if st.form_submit_button("Reportar"):
                                        quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                                        hoja_reportes.append_row([item.get('Direccion'), item.get('Ciudad'), item.get('Codigo'), nc, nt, quien, get_time(), "Web"])
                                        enviar_telegram(f"🚨 <b>REPORTE (Web)</b>\n👤 {quien}\n📍 {item.get('Direccion')}\n🔑 {nc}")
                                        st.success("Enviado")
                else:
                    st.warning("⚠️ No encontrada.")
                
                st.markdown("---")
                if st.button(f"➕ Registrar '{busqueda}'", use_container_width=True):
                    st.session_state['memoria_direccion'] = busqueda
                    st.session_state['seccion_activa'] = "Registrar"
                    st.rerun()

    # --- REGISTRAR ---
    elif seccion == "Registrar":
        st.subheader("➕ Nueva Dirección")
        val_ini = st.session_state.get('memoria_direccion', "")
        with st.form("reg_form"):
            nd = st.text_input("Dirección:", value=val_ini)
            c1, c2 = st.columns(2)
            with c1: ci = st.text_input("Ciudad:", value="Dallas")
            with c2: es = st.text_input("Estado:", value="TX")
            co = st.text_input("Código:")
            if st.form_submit_button("Guardar", use_container_width=True):
                if nd and co:
                    nd_fmt = capitalizar_palabras(nd)
                    ci_fmt = capitalizar_palabras(ci)
                    es_fmt = es.upper()
                    quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                    try:
                        hoja.append_row([nd_fmt, ci_fmt, es_fmt, co, quien, get_time(), "Web"])
                        enviar_telegram(f"🆕 <b>NUEVO (Web)</b>\n👤 {quien}\n📍 {nd_fmt}\n🔑 {co}")
                        st.session_state['memoria_direccion'] = ""
                        st.success(f"✅ {nd_fmt}")
                        time.sleep(1.5)
                        st.session_state['seccion_activa'] = "Buscador"
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                else: st.error("Faltan datos")

    # --- SUGERENCIAS ---
    elif seccion == "Sugerencias":
        st.subheader("💬 Sugerencias")
        with st.form("sug_form"):
            txt = st.text_area("Mensaje:")
            if st.form_submit_button("Enviar", use_container_width=True):
                if txt:
                    try:
                        enviar_telegram(f"💡 <b>IDEA (Web)</b>\n👤 {st.session_state['usuario_nombre_completo']}\n💬 {txt}")
                        st.success("Enviado")
                    except Exception as e: st.error(f"Error: {e}")

    # --- PERFIL ---
    elif seccion == "Perfil":
        st.subheader("⚙️ Mi Perfil")
        st.write(f"📱 **{st.session_state['usuario_telefono']}**")
        st.link_button("🤖 Abrir @BuscadordecodigosBot", LINK_TELEGRAM, use_container_width=True)
        st.markdown("---")
        with st.form("edit_perfil"):
            un = st.text_input("Nombre:", value=st.session_state['user_nombre'])
            ua = st.text_input("Apellido:", value=st.session_state['user_apellido'])
            if st.form_submit_button("Actualizar Datos"):
                try:
                    usuarios_db = hoja_usuarios.get_all_records()
                    for i, u in enumerate(usuarios_db):
                        if str(u.get('Telefono', '')).strip() == st.session_state['usuario_telefono']:
                            hoja_usuarios.update_cell(i+2, 3, un)
                            hoja_usuarios.update_cell(i+2, 4, ua)
                            st.session_state['user_nombre'] = un
                            st.session_state['user_apellido'] = ua
                            st.success("Actualizado"); time.sleep(1); st.rerun()
                except: st.error("Error al actualizar")

    # --- ADMIN ---
    elif seccion == "Admin" and es_admin:
        st.subheader("👮 Panel Admin")
        if not hoja_usuarios: st.error("Sin conexión Usuarios")
        else:
            try:
                todos_usuarios = hoja_usuarios.get_all_records()
                tab_act, tab_bloq, tab_todos = st.tabs(["✅ Activos", "⛔ Bloqueados", "👥 Todos"])
                with tab_act:
                    activos = [u for i,u in enumerate(todos_usuarios) if str(u.get('Estado','')).lower() == 'activo']
                    st.metric("Usuarios Activos", len(activos))
                    for a in activos:
                        idx = next((i for i, u in enumerate(todos_usuarios) if u['Telefono'] == a['Telefono']), -1) + 2
                        with st.expander(f"🟢 {a.get('Nombre')} {a.get('Apellido')}"):
                            st.caption(f"📱 {a.get('Telefono')} | 🌐 {a.get('Origen', 'N/A')}")
                            if st.button("Bloquear", key=f"d_{a['Telefono']}"):
                                hoja_usuarios.update_cell(idx, 6, "Desactivado")
                                st.rerun()
                with tab_bloq:
                    bloq = [u for i,u in enumerate(todos_usuarios) if str(u.get('Estado','')).lower() == 'desactivado']
                    if not bloq: st.info("Nadie bloqueado.")
                    for b in bloq:
                        idx = next((i for i, u in enumerate(todos_usuarios) if u['Telefono'] == b['Telefono']), -1) + 2
                        with st.container(border=True):
                            st.write(f"🔴 {b.get('Nombre')} {b.get('Apellido')}")
                            if st.button("Desbloquear", key=f"re_{b['Telefono']}"):
                                hoja_usuarios.update_cell(idx, 6, "Activo")
                                st.rerun()
                with tab_todos:
                    visibles = [{k: v for k, v in u.items() if k != 'Password'} for u in todos_usuarios]
                    st.dataframe(visibles)
            except Exception as e: st.error(f"Error: {e}")

    # --- MENU INFERIOR ---
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(5) if es_admin else st.columns(4)
    with cols[0]:
        if st.button("🔍 Buscar", use_container_width=True): 
            st.session_state['seccion_activa'] = "Buscador"; st.session_state['memoria_direccion'] = ""; st.rerun()
    with cols[1]:
        if st.button("➕ Nuevo", use_container_width=True): 
            st.session_state['seccion_activa'] = "Registrar"; st.session_state['memoria_direccion'] = ""; st.rerun()
    with cols[2]:
        if st.button("💬 Ideas", use_container_width=True): st.session_state['seccion_activa'] = "Sugerencias"; st.rerun()
    with cols[3]:
        if st.button("⚙️ Perfil", use_container_width=True): st.session_state['seccion_activa'] = "Perfil"; st.rerun()
    if es_admin:
        with cols[4]:
            if st.button("👮 Admin", use_container_width=True): st.session_state['seccion_activa'] = "Admin"; st.rerun()

    st.write("")
    if st.button("🚪 Salir", use_container_width=True):
        st.query_params.clear()
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

if not st.session_state['logueado']: mostrar_acceso()
else: mostrar_app()
