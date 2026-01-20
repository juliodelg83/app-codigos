import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests 
import hashlib 

# Configuración de página
st.set_page_config(page_title="Acceso Seguro", layout="centered")

# --- VARIABLES DE SESIÓN ---
if 'logueado' not in st.session_state: st.session_state['logueado'] = False
if 'usuario_telefono' not in st.session_state: st.session_state['usuario_telefono'] = ""
if 'usuario_nombre' not in st.session_state: st.session_state['usuario_nombre'] = ""
if 'datos_completos' not in st.session_state: st.session_state['datos_completos'] = False

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
                            
                            nombre_db = str(u.get('Nombre', '')).strip()
                            apellido_db = str(u.get('Apellido', '')).strip()
                            
                            if nombre_db:
                                st.session_state['datos_completos'] = True
                                st.session_state['usuario_nombre'] = f"{nombre_db} {apellido_db}"
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
# 2. REGISTRO USUARIO
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
                    st.session_state['usuario_nombre'] = f"{nuevo_nombre} {nuevo_apellido}"
                    st.rerun()
                except: st.error("Error guardando.")
            else: st.error("Verifica los datos.")

# ==========================================
# 3. APP PRINCIPAL (HÍBRIDA)
# ==========================================
def mostrar_app():
    with st.sidebar:
        st.write(f"👤 **{st.session_state['usuario_nombre']}**")
        if st.button("Salir"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()

    st.title("📍 Buscador")

    if not hoja: st.stop()
    try: registros = hoja.get_all_records()
    except: st.stop()

    # --- LISTA PARA AUTOCOMPLETAR ---
    # Creamos la lista de opciones para el buscador
    lista_direcciones = []
    if registros:
        lista_direcciones = [str(r.get('Direccion', '')) for r in registros if r.get('Direccion')]

    # 1. BUSCADOR CON AUTOCOMPLETADO
    busqueda_seleccion = st.selectbox(
        "🔍 Buscar dirección:", 
        options=lista_direcciones, 
        index=None, 
        placeholder="Escribe para buscar...",
    )

    # 2. LÓGICA
    if busqueda_seleccion:
        # --- CASO A: SI ENCONTRÓ ALGO ---
        resultados = [r for i, r in enumerate(registros) if str(r.get('Direccion', '')) == busqueda_seleccion]
        # (Asignamos ID manual para el reporte)
        for i, r in enumerate(registros):
            if str(r.get('Direccion', '')) == busqueda_seleccion:
                r['_id'] = i
                
        if resultados:
            st.success("✅ Dirección encontrada:")
            for item in resultados:
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
                    
                    with st.expander(f"Reportar"):
                        with st.form(f"rep_{item.get('_id', 0)}"):
                            nc = st.text_input("Nuevo código:")
                            nt = st.text_input("Nota:")
                            if st.form_submit_button("Enviar"):
                                quien = f"{st.session_state['usuario_nombre']} ({st.session_state['usuario_telefono']})"
                                hoja_reportes.append_row([item.get('Direccion'), item.get('Ciudad'), item.get('Codigo'), nc, nt, quien])
                                enviar_telegram(f"🚨 <b>REPORTE</b>\n👤 {st.session_state['usuario_nombre']}\n📍 {item.get('Direccion')}\n🔑 {nc}")
                                st.success("Listo.")
                st.divider()

    else:
        # --- CASO B: NO SELECCIONÓ NADA (REGISTRO) ---
        st.info("👆 Usa el buscador de arriba. Si no aparece, regístrala aquí abajo:")
        
        with st.form("auto_registro"):
            st.write(f"📍 **Registrar Nueva Dirección**")
            
            nueva_dir = st.text_input("Dirección Completa:")
            c1, c2 = st.columns(2)
            with c1: ciu = st.text_input("Ciudad:", placeholder="Dallas")
            with c2: est = st.text_input("Estado:", placeholder="TX")
            cod = st.text_input("Código de acceso:", placeholder="#1234")
            
            if st.form_submit_button("Guardar Nueva", use_container_width=True):
                if nueva_dir and cod and ciu and est:
                    if nueva_dir in lista_direcciones:
                        st.error("⚠️ Esa dirección YA existe, búscala arriba.")
                    else:
                        quien = f"{st.session_state['usuario_nombre']} ({st.session_state['usuario_telefono']})"
                        hoja.append_row([nueva_dir, ciu, est, cod, quien])
                        enviar_telegram(f"🆕 <b>NUEVO</b>\n👤 {st.session_state['usuario_nombre']}\n📍 {nueva_dir}\n🔑 {cod}")
                        st.success("¡Guardada!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Faltan datos.")

    # Footer
    st.markdown("---")
    with st.expander("💬 Sugerencias"):
        with st.form("sug"):
            msg = st.text_area("Mensaje:")
            if st.form_submit_button("Enviar"):
                enviar_telegram(f"💡 <b>SUGERENCIA</b>\n👤 {st.session_state['usuario_nombre']}\n💬 {msg}")
                st.success("Enviado.")

    st.markdown("<div style='text-align: center; color: grey;'><small>v5.5</small></div>", unsafe_allow_html=True)

# ==========================================
# CONTROL
# ==========================================
if not st.session_state['logueado']: mostrar_login()
else:
    if st.session_state['datos_completos']: mostrar_app()
    else: mostrar_registro_inicial()
