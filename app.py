import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests 

# Configuración de página
st.set_page_config(page_title="Acceso Seguro", layout="centered")

# --- VARIABLES DE SESIÓN ---
if 'logueado' not in st.session_state: st.session_state['logueado'] = False
if 'usuario_telefono' not in st.session_state: st.session_state['usuario_telefono'] = ""
if 'usuario_nombre' not in st.session_state: st.session_state['usuario_nombre'] = ""
if 'datos_completos' not in st.session_state: st.session_state['datos_completos'] = False

# --- FUNCIONES DE TELEGRAM ---
def enviar_telegram(mensaje):
    try:
        token = st.secrets["general"]["telegram_token"]
        chat_id = st.secrets["general"]["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
        requests.post(url, data=data)
    except:
        pass

# --- CONEXIÓN A GOOGLE SHEETS ---
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
# 1. PANTALLA DE LOGIN (Solo Teléfono y Clave)
# ==========================================
def mostrar_login():
    st.title("🔒 Ingreso Usuarios")
    st.markdown("Ingresa con tu número de teléfono.")
    
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
                        # Fila real en Excel = índice + 2 (por encabezado)
                        fila_excel = i + 2
                        
                        # Convertimos a string para comparar
                        db_tel = str(u.get('Telefono', '')).strip()
                        db_pass = str(u.get('Password', '')).strip()
                        
                        if db_tel == tel_input.strip() and db_pass == pass_input.strip():
                            st.session_state['logueado'] = True
                            st.session_state['usuario_telefono'] = db_tel
                            st.session_state['fila_usuario'] = fila_excel # Guardamos dónde está para editarlo luego
                            
                            # Verificamos si ya completó sus datos (Si tiene Nombre)
                            nombre_db = str(u.get('Nombre', '')).strip()
                            if nombre_db:
                                st.session_state['datos_completos'] = True
                                st.session_state['usuario_nombre'] = nombre_db
                            else:
                                st.session_state['datos_completos'] = False
                            
                            encontrado = True
                            st.success("¡Datos correctos!")
                            time.sleep(0.5)
                            st.rerun()
                            break
                    
                    if not encontrado:
                        st.error("Teléfono o contraseña incorrectos.")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")

# ==========================================
# 2. PANTALLA DE REGISTRO (Primer Ingreso)
# ==========================================
def mostrar_registro_inicial():
    st.title("👋 ¡Bienvenido!")
    st.warning("Para continuar, por favor completa tu información personal y asegura tu cuenta con una nueva contraseña.")
    
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1: nuevo_nombre = st.text_input("Nombre:")
        with col2: nuevo_apellido = st.text_input("Apellido:")
        
        nuevo_correo = st.text_input("Correo Electrónico:")
        st.markdown("---")
        nueva_clave = st.text_input("Crea tu NUEVA contraseña:", type="password")
        confirmar_clave = st.text_input("Repite la contraseña:", type="password")
        
        guardar_datos = st.form_submit_button("Guardar y Continuar ➡️", use_container_width=True)
        
        if guardar_datos:
            if nuevo_nombre and nuevo_apellido and nuevo_correo and nueva_clave:
                if nueva_clave == confirmar_clave:
                    try:
                        f = st.session_state['fila_usuario']
                        # Actualizamos Columnas: B(Pass), C(Nom), D(Ape), E(Correo)
                        # OJO: gspread usa (fila, columna)
                        hoja_usuarios.update_cell(f, 2, nueva_clave)     # Col B
                        hoja_usuarios.update_cell(f, 3, nuevo_nombre)    # Col C
                        hoja_usuarios.update_cell(f, 4, nuevo_apellido)  # Col D
                        hoja_usuarios.update_cell(f, 5, nuevo_correo)    # Col E
                        
                        st.session_state['datos_completos'] = True
                        st.session_state['usuario_nombre'] = nuevo_nombre
                        
                        st.success("¡Perfil actualizado con éxito!")
                        enviar_telegram(f"👤 <b>REGISTRO COMPLETADO</b>\nUsuario: {nuevo_nombre} {nuevo_apellido}\nTel: {st.session_state['usuario_telefono']}")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error guardando: {e}")
                else:
                    st.error("Las contraseñas no coinciden.")
            else:
                st.error("Por favor llena todos los campos.")

# ==========================================
# 3. APP PRINCIPAL (Buscador)
# ==========================================
def mostrar_app():
    # MENU LATERAL
    with st.sidebar:
        st.header(f"Hola, {st.session_state['usuario_nombre']}")
        st.caption(f"📱 {st.session_state['usuario_telefono']}")
        
        if st.button("Cerrar Sesión"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

    st.title("📍 Buscador de Direcciones")

    if not hoja: st.error("Error DB"); st.stop()

    try: registros = hoja.get_all_records()
    except: st.stop()

    # BUSQUEDA
    busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: 17811 Vail St")

    if busqueda:
        texto_buscar = busqueda.strip().lower()
        resultados_encontrados = []
        
        for i, fila in enumerate(registros):
            fila['_id'] = i 
            direccion_db = str(fila.get('Direccion', '')).strip().lower()
            if texto_buscar in direccion_db:
                resultados_encontrados.append(fila)
        
        if len(resultados_encontrados) > 0:
            st.success(f"✅ Encontrado ({len(resultados_encontrados)}):")
            for item in resultados_encontrados:
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
                    
                    with st.expander(f"🚨 Reportar fallo"):
                        with st.form(f"reporte_{item['_id']}"):
                            n_code = st.text_input("Código correcto:")
                            nota = st.text_input("Nota:")
                            if st.form_submit_button("Reportar"):
                                if hoja_reportes:
                                    hoja_reportes.append_row([item.get('Direccion'), item.get('Ciudad'), item.get('Codigo'), n_code, nota])
                                    enviar_telegram(f"🚨 <b>REPORTE</b>\n👤 {st.session_state['usuario_nombre']}\n📍 {item.get('Direccion')}\n🔑 Nuevo: {n_code}")
                                    st.success("Enviado.")
                    st.divider()
        else:
            st.warning("No encontrado.")
            st.markdown("### 👇 Registrar nuevo:")
            with st.form("nuevo_form"):
                st.write(f"Registrando: **{busqueda}**")
                c1, c2 = st.columns(2)
                with c1: ciu = st.text_input("Ciudad:")
                with c2: est = st.text_input("Estado:")
                cod = st.text_input("Código:")
                if st.form_submit_button("Guardar", use_container_width=True):
                    if cod and ciu and est:
                        hoja.append_row([busqueda, ciu, est, cod])
                        enviar_telegram(f"🆕 <b>NUEVO</b>\n👤 {st.session_state['usuario_nombre']}\n📍 {busqueda}\n🔑 {cod}")
                        st.success("Guardado.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Faltan datos.")
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: grey;'><small>v5.0 (Gestión de Usuarios)</small></div>", unsafe_allow_html=True)

# ==========================================
#        CONTROL DE FLUJO (Router)
# ==========================================
if not st.session_state['logueado']:
    mostrar_login()
else:
    # Si está logueado, verificamos si ya completó sus datos
    if st.session_state['datos_completos']:
        mostrar_app()
    else:
        mostrar_registro_inicial()
