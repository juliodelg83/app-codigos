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

# Variable nueva para pasar la dirección de una pantalla a otra
if 'memoria_direccion' not in st.session_state: st.session_state['memoria_direccion'] = ""

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
# ⚙️ LÓGICA DE AUTO-LOGIN
# ==========================================
def intentar_autologin():
    query_params = st.query_params
    movil_guardado = query_params.get("movil", None)

    if movil_guardado and not st.session_state['logueado']:
        if not movil_guardado.isdigit() or len(movil_guardado) != 10: return False

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
                        st.toast(f"Reconexión rápida: {st.session_state['user_nombre']}")
                        return True
            except: pass
    return False

if not st.session_state['logueado']:
    intentar_autologin()

# ==========================================
# 1. PANTALLA ÚNICA DE ACCESO
# ==========================================
def mostrar_acceso():
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("📍 Bienvenido")
    st.write("Ingresa tus datos para acceder.")
    
    with st.form("form_acceso"):
        st.caption("Solo números sin el +1 (Ej: 2145550000)")
        tel = st.text_input("📱 Teléfono (10 dígitos):", max_chars=10)
        
        c1, c2 = st.columns(2)
        with c1: nom = st.text_input("👤 Nombre:")
        with c2: ape = st.text_input("👤 Apellido:")
        
        entrar = st.form_submit_button("Ingresar a la App", use_container_width=True)
        
        if entrar:
            if not tel.isdigit():
                st.error("⚠️ El teléfono solo debe contener números.")
                st.stop()
            if len(tel) != 10:
                st.error("⚠️ El teléfono debe tener 10 dígitos.")
                st.stop()
            if not nom or not ape:
                st.error("⚠️ Nombre y Apellido son obligatorios.")
                st.stop()
                
            if hoja_usuarios:
                try:
                    usuarios_db = hoja_usuarios.get_all_records()
                    encontrado = False
                    
                    for i, u in enumerate(usuarios_db):
                        db_tel = str(u.get('Telefono', '')).strip()
                        
                        if db_tel == tel:
                            encontrado = True
                            db_estado = str(u.get('Estado', '')).strip().lower()
                            
                            if db_estado == "desactivado":
                                st.error("⛔ Acceso denegado. Contacta al administrador.")
                                st.stop()
                            
                            fila = i + 2
                            if str(u.get('Nombre','')) != nom or str(u.get('Apellido','')) != ape:
                                hoja_usuarios.update_cell(fila, 3, nom)
                                hoja_usuarios.update_cell(fila, 4, ape)
                            
                            iniciar_sesion(tel, nom, ape, str(u.get('Correo','')), fila)
                            break
                    
                    if not encontrado:
                        hoja_usuarios.append_row([tel, "N/A", nom, ape, "", "Activo"])
                        enviar_telegram(f"🆕 <b>NUEVO USUARIO</b>\n👤 {nom} {ape}\n📱 {tel}")
                        iniciar_sesion(tel, nom, ape, "", len(usuarios_db) + 2)
                        
                except Exception as e: st.error(f"Error de conexión: {e}")

def iniciar_sesion(tel, nombre, apellido, correo, fila):
    st.session_state['logueado'] = True
    st.session_state['usuario_telefono'] = tel
    st.session_state['fila_usuario'] = fila
    st.session_state['user_nombre'] = nombre
    st.session_state['user_apellido'] = apellido
    st.session_state['user_correo'] = correo
    st.session_state['usuario_nombre_completo'] = f"{nombre} {apellido}"
    st.session_state['datos_completos'] = True
    st.query_params["movil"] = tel
    st.success(f"¡Hola {nombre}!")
    time.sleep(0.5)
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

    # --- BUSCADOR INTELIGENTE (TEXTO) ---
    if seccion == "Buscador":
        if not hoja: st.stop()
        try: registros = hoja.get_all_records()
        except: st.stop()
        
        # Usamos Text Input para capturar lo que escriben, exista o no
        st.subheader("🔍 Buscar Dirección")
        busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: 1234 Main St", key="search_box")
        
        if busqueda:
            # 1. Buscamos coincidencias (Exactas o Parciales)
            busqueda_lower = busqueda.lower().strip()
            coincidencias = [r for r in registros if busqueda_lower in str(r.get('Direccion','')).lower()]
            
            # A) Si encontramos algo
            if coincidencias:
                st.success(f"✅ Se encontraron {len(coincidencias)} resultado(s):")
                for item in coincidencias:
                    # Asignamos ID temporal para reporte
                    idx = next((i for i, r in enumerate(registros) if r == item), 0)
                    
                    with st.container(border=True):
                        st.markdown(f"📍 **{item.get('Direccion')}**")
                        st.write(f"🏙 {item.get('Ciudad')}, {item.get('Estado')}")
                        st.markdown(f"## 🔑 {item.get('Codigo')}")
                        
                        with st.expander("Reportar Error"):
                            with st.form(f"rep_{idx}"):
                                nc = st.text_input("Nuevo código:")
                                nt = st.text_input("Nota:")
                                if st.form_submit_button("Reportar"):
                                    quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                                    hoja_reportes.append_row([item.get('Direccion'), item.get('Ciudad'), item.get('Codigo'), nc, nt, quien, get_time()])
                                    enviar_telegram(f"🚨 <b>REPORTE</b>\n👤 {quien}\n📍 {item.get('Direccion')}\n🔑 {nc}")
                                    st.success("Enviado")
            
            # B) Si no es lo que buscaban o no hay nada
            else:
                st.warning("⚠️ No encontramos esa dirección.")

            # BOTÓN MÁGICO: Registrar lo que escribiste
            st.markdown("---")
            st.write("¿Es una dirección nueva?")
            if st.button(f"➕ Registrar '{busqueda}' ahora", use_container_width=True):
                # Guardamos lo que escribió en memoria
                st.session_state['memoria_direccion'] = busqueda
                # Cambiamos de pantalla
                st.session_state['seccion_activa'] = "Registrar"
                st.rerun()

    # --- REGISTRAR (Con Memoria) ---
    elif seccion == "Registrar":
        st.subheader("➕ Nueva Dirección")
        
        # Recuperamos la memoria (si viene del buscador)
        valor_inicial = st.session_state.get('memoria_direccion', "")
        
        with st.form("reg_form"):
            # Usamos value=valor_inicial para que aparezca escrito
            nd = st.text_input("Dirección:", value=valor_inicial)
            c1, c2 = st.columns(2)
            with c1: ci = st.text_input("Ciudad:", value="Dallas")
            with c2: es = st.text_input("Estado:", value="TX")
            co = st.text_input("Código:")
            
            if st.form_submit_button("Guardar", use_container_width=True):
                if nd and co:
                    quien = f"{st.session_state['usuario_nombre_completo']} ({st.session_state['usuario_telefono']})"
                    hoja.append_row([nd, ci, es, co, quien, get_time()])
                    enviar_telegram(f"🆕 <b>NUEVO</b>\n👤 {quien}\n📍 {nd}\n🔑 {co}")
                    
                    # Limpiamos memoria y volvemos
                    st.session_state['memoria_direccion'] = ""
                    st.success("Guardado")
                    time.sleep(1)
                    st.session_state['seccion_activa'] = "Buscador"
                    st.rerun()
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
            tab_act, tab_bloq, tab_todos = st.tabs(["✅ Activos", "⛔ Bloqueados", "👥 Todos"])
            
            with tab_act:
                activos = [u for i,u in enumerate(todos_usuarios) if str(u.get('Estado','')).lower() == 'activo']
                st.metric("Usuarios Activos", len(activos))
                for a in activos:
                    idx = next((i for i, u in enumerate(todos_usuarios) if u['Telefono'] == a['Telefono']), -1) + 2
                    with st.expander(f"🟢 {a.get('Nombre')} {a.get('Apellido')}"):
                        st.caption(f"📱 {a.get('Telefono')}")
                        if st.button("Bloquear Acceso", key=f"d_{a['Telefono']}"):
                            hoja_usuarios.update_cell(idx, 6, "Desactivado")
                            st.rerun()
            
            with tab_bloq:
                bloq = [u for i,u in enumerate(todos_usuarios) if str(u.get('Estado','')).lower() == 'desactivado']
                if not bloq: st.info("Nadie bloqueado.")
                for b in bloq:
                    idx = next((i for i, u in enumerate(todos_usuarios) if u['Telefono'] == b['Telefono']), -1) + 2
                    with st.container(border=True):
                        st.write(f"🔴 {b.get('Nombre')} {b.get('Apellido')}")
                        if st.button("Desbloquear (Permitir)", key=f"re_{b['Telefono']}"):
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
            st.session_state['seccion_activa'] = "Buscador"
            # Importante: Limpiar memoria al volver manualmente al buscador
            st.session_state['memoria_direccion'] = ""
            st.rerun()
    with cols[1]:
        if st.button("➕ Nuevo", use_container_width=True): 
            st.session_state['seccion_activa'] = "Registrar"
            st.session_state['memoria_direccion'] = "" # Limpiar si entran directo
            st.rerun()
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
