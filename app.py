import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests 
import hashlib 
from datetime import datetime

# --- 👑 CONFIGURACIÓN DE ADMINISTRADOR ---
ADMIN_TELEFONO = "2142595696"

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
def get_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
# ⚙️ LÓGICA DE AUTO-LOGIN (PERSISTENCIA)
# ==========================================
def intentar_autologin():
    # Verificamos si hay un usuario guardado en la URL (Query Params)
    query_params = st.query_params
    movil_guardado = query_params.get("movil", None)

    if movil_guardado and not st.session_state['logueado']:
        if hoja_usuarios:
            try:
                usuarios_db = hoja_usuarios.get_all_records()
                for i, u in enumerate(usuarios_db):
                    db_tel = str(u.get('Telefono', '')).strip()
                    db_estado = str(u.get('Estado', '')).strip().lower()
                    
                    if db_tel == movil_guardado:
                        es_admin = (db_tel == ADMIN_TELEFONO)
                        
                        if db_estado == "activo" or es_admin:
                            st.session_state['logueado'] = True
                            st.session_state['usuario_telefono'] = db_tel
                            st.session_state['fila_usuario'] = i + 2
                            st.session_state['user_nombre'] = str(u.get('Nombre', '')).strip()
                            st.session_state['user_apellido'] = str(u.get('Apellido', '')).strip()
                            st.session_state['user_correo'] = str(u.get('Correo', '')).strip()
                            st.session_state['usuario_nombre_completo'] = f"{st.session_state['user_nombre']} {st.session_state['user_apellido']}"
                            st.session_state['datos_completos'] = True
                            st.toast(f"Reconexión exitosa: {st.session_state['user_nombre']}")
                            return True
            except: pass
    return False

# Ejecutamos autologin al cargar
if not st.session_state['logueado']:
    intentar_autologin()

# ==========================================
# 1. SISTEMA DE ACCESO
# ==========================================
def mostrar_login():
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- VISTA REGISTRO ---
    if st.session_state['modo_registro']:
        st.title("📝 Registro Rápido")
        st.caption("Solo necesitas tu nombre y teléfono.")
        
        with st.form("registro_nuevo"):
            reg_tel = st.text_input("📱 Tu Teléfono (Será tu usuario):")
            reg_nombre = st.text_input("👤 Tu Nombre:")
            reg_apellido = st.text_input("👤 Tu Apellido:")
            
            if st.form_submit_button("Solicitar Acceso", use_container_width=True):
                if reg_nombre and reg_tel and reg_apellido:
                    if hoja_usuarios:
                        try:
                            usuarios_db = hoja_usuarios.get_all_records()
                            existe = False
                            for u in usuarios_db:
                                if str(u.get('Telefono', '')).strip() == reg_tel.strip():
                                    existe = True; break
                            
                            if existe:
                                st.error("⚠️ Este teléfono ya existe.")
                            else:
                                hoja_usuarios.append_row([
                                    reg_tel, "N/A", reg_nombre, reg_apellido, "", "Pendiente"
                                ])
                                enviar_telegram(f"🔔 <b>SOLICITUD</b>\n👤 {reg_nombre} {reg_apellido}\n📱 {reg_tel}\n⚠️ Estado: Pendiente")
                                st.success("✅ Enviado. Espera la aprobación.")
                                time.sleep(3)
                                st.session_state['modo_registro'] = False
                                st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                else: st.error("Todos los datos son obligatorios.")
        
        st.markdown("---")
        if st.button("⬅️ Volver", use_container_width=True):
            st.session_state['modo_registro'] = False
            st.rerun()

    # --- VISTA LOGIN ---
    else:
        st.title("👋 Bienvenido")
        st.write("Ingresa tu número para conectar.")
        
        with st.form("login_form"):
            tel_input = st.text_input("📱 Número de Teléfono")
            entrar = st.form_submit_button("Conectar", use_container_width=True)
            
            if entrar:
                if hoja_usuarios:
                    try:
                        usuarios_db = hoja_usuarios.get_all_records()
                        encontrado = False
                        for i, u in enumerate(usuarios_db):
                            db_tel = str(u.get('Telefono', '')).strip()
                            db_estado = str(u.get('Estado', '')).strip().lower()
                            
                            if db_tel == tel_input.strip():
                                encontrado = True
                                es_admin = (db_tel == ADMIN_TELEFONO)
                                
                                if db_estado == "activo" or es_admin:
                                    st.session_state['logueado'] = True
                                    st.session_state['usuario_telefono'] = db_tel
                                    st.session_state['fila_usuario'] = i + 2
                                    st.session_state['user_nombre'] = str(u.get('Nombre', '')).strip()
                                    st.session_state['user_apellido'] = str(u.get('Apellido', '')).strip()
                                    st.session_state['user_correo'] = str(u.get('Correo', '')).strip()
                                    st.session_state['usuario_nombre_completo'] = f"{st.session_state['user_nombre']} {st.session_state['user_apellido']}"
                                    st.session_state['datos_completos'] = True
                                    
                                    # --- AQUÍ GUARDAMOS EL USUARIO EN LA URL ---
                                    st.query_params["movil"] = db_tel
                                    
                                    st.success(f"¡Conectado como {st.session_state['user_nombre']}!")
                                    time.sleep(0.5)
                                    st.rerun()
                                
                                elif db_estado == "pendiente":
                                    st.warning("⏳ Pendiente de aprobación.")
                                elif db_estado == "desactivado":
                                    st.error("⛔ Usuario desactivado.")
                                break
                        
                        if not encontrado:
                            st.error("Número no encontrado.")
                    except Exception as e: st.error(f"Error: {e}")

        st.write("")
        if st.button("📝 Registrarse", use_container_width=True):
            st.session_state['modo_registro'] = True
            st.rerun()

# ==========================================
# 2. APP PRINCIPAL
# ==========================================
def mostrar_app():
    es_admin = (st.session_state['usuario_telefono'] == ADMIN_TELEFONO)

    st.markdown(f"### 👋 Hola, {st.session_state['user_nombre']}")
    if es_admin: st.caption("🛡️ Modo Admin")
    st.markdown("---")

    seccion = st.session_state['seccion_activa']

    # --- BUSCADOR ---
    if seccion == "Buscador":
        if not hoja: st.stop()
        try: registros = hoja.get_all_records()
        except: st.stop()
        
        lista_dirs = [str(r.get('Direccion', '')) for r in registros if r.get('Direccion')]
        st.subheader("🔍 Buscar Dirección")
        busqueda = st.selectbox("Escribe dirección:", options=lista_dirs, index=None, placeholder="Toca para buscar...")
        
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
                                    hoja_reportes.append_row([item.get('Direccion'), item.get('Ciudad'), item.get('Codigo'), nc, nt, quien, get_time()])
                                    enviar_telegram(f"🚨 <b>REPORTE</b>\n👤 {quien}\n📍 {item.get('Direccion')}\n🔑 {nc}")
                                    st.success("Enviado")
        else: st.info("Usa el botón '➕ Nuevo' si no existe.")

    # --- REGISTRAR ---
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
                    hoja.append_row([nd, ci, es, co, quien, get_time()])
                    enviar_telegram(f"🆕 <b>NUEVO</b>\n👤 {quien}\n📍 {nd}\n🔑 {co}")
                    st.success("Guardado"); time.sleep(1); st.session_state['seccion_activa'] = "Buscador"; st.rerun()
                else: st.error("Faltan datos")

    # --- SUGERENCIAS ---
    elif seccion == "Sugerencias":
        st.subheader("💬 Sugerencias")
        with st.form("sug_form"):
            txt = st.text_area("Mensaje:")
            if st.form_submit_button("Enviar", use_container_width=True):
                if txt:
                    enviar_telegram(f"💡 <b>IDEA</b>\n👤 {st.session_state['usuario_nombre_completo']}\n💬 {txt}")
                    st.success("Enviado")

    # --- PERFIL ---
    elif seccion == "Perfil":
        st.subheader("⚙️ Mi Perfil")
        st.write(f"📱 **{st.session_state['usuario_telefono']}**")
        with st.form("edit_perfil"):
            un = st.text_input("Nombre:", value=st.session_state['user_nombre'])
            ua = st.text_input("Apellido:", value=st.session_state['user_apellido'])
            if st.form_submit_button("Actualizar Datos"):
                usuarios_db = hoja_usuarios.get_all_records()
                for i, u in enumerate(usuarios_db):
                    if str(u.get('Telefono', '')).strip() == st.session_state['usuario_telefono']:
                        hoja_usuarios.update_cell(i+2, 3, un)
                        hoja_usuarios.update_cell(i+2, 4, ua)
                        st.session_state['user_nombre'] = un
                        st.session_state['user_apellido'] = ua
                        st.success("Actualizado"); time.sleep(1); st.rerun()

    # --- ADMIN ---
    elif seccion == "Admin" and es_admin:
        st.subheader("👮 Admin")
        if not hoja_usuarios: st.stop()
        try:
            todos_usuarios = hoja_usuarios.get_all_records()
            tab_pend, tab_act, tab_todos = st.tabs(["⏳ Pendientes", "✅ Activos", "👥 Todos"])
            
            with tab_pend:
                pendientes = [u for i,u in enumerate(todos_usuarios) if str(u.get('Estado','')).lower() == 'pendiente']
                if not pendientes: st.info("Sin solicitudes.")
                else:
                    for p in pendientes:
                        idx = next((i for i, u in enumerate(todos_usuarios) if u['Telefono'] == p['Telefono']), -1) + 2
                        with st.container(border=True):
                            st.write(f"**{p.get('Nombre')} {p.get('Apellido')}**")
                            st.caption(f"📱 {p.get('Telefono')}")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("Aprobar", key=f"a_{p['Telefono']}", type="primary"):
                                    hoja_usuarios.update_cell(idx, 6, "Activo")
                                    st.toast("Aprobado"); time.sleep(1); st.rerun()
                            with c2:
                                if st.button("Bloquear", key=f"b_{p['Telefono']}"):
                                    hoja_usuarios.update_cell(idx, 6, "Desactivado")
                                    st.toast("Bloqueado"); time.sleep(1); st.rerun()
            with tab_act:
                activos = [u for i,u in enumerate(todos_usuarios) if str(u.get('Estado','')).lower() == 'activo']
                st.metric("Activos", len(activos))
                for a in activos:
                    idx = next((i for i, u in enumerate(todos_usuarios) if u['Telefono'] == a['Telefono']), -1) + 2
                    with st.expander(f"🟢 {a.get('Nombre')} {a.get('Apellido')}"):
                        st.caption(f"📱 {a.get('Telefono')}")
                        if st.button("Desactivar", key=f"d_{a['Telefono']}"):
                            hoja_usuarios.update_cell(idx, 6, "Desactivado")
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
        if st.button("🔍 Buscar", use_container_width=True): st.session_state['seccion_activa'] = "Buscador"; st.rerun()
    with cols[1]:
        if st.button("➕ Nuevo", use_container_width=True): st.session_state['seccion_activa'] = "Registrar"; st.rerun()
    with cols[2]:
        if st.button("💬 Ideas", use_container_width=True): st.session_state['seccion_activa'] = "Sugerencias"; st.rerun()
    with cols[3]:
        if st.button("⚙️ Perfil", use_container_width=True): st.session_state['seccion_activa'] = "Perfil"; st.rerun()
    if es_admin:
        with cols[4]:
            if st.button("👮 Admin", use_container_width=True): st.session_state['seccion_activa'] = "Admin"; st.rerun()

    st.write("")
    if st.button("🚪 Salir (Desconectar)", use_container_width=True):
        st.query_params.clear() # Borramos la memoria de la URL
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

if not st.session_state['logueado']: mostrar_login()
else: mostrar_app()
