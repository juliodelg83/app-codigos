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

# --- FUNCIÓN DE ENCRIPTACIÓN ---
def encriptar(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

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
# 1. PANTALLA DE LOGIN
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
                        fila_excel = i + 2
                        db_tel = str(u.get('Telefono', '')).strip()
                        db_pass = str(u.get('Password', '')).strip()
                        
                        # Comparamos: Texto plano (temporal) O Encriptada (personal)
                        es_temporal = (db_pass == pass_input.strip())
                        es_encriptada = (db_pass == encriptar(pass_input.strip()))
                        
                        if db_tel == tel_input.strip() and (es_temporal or es_encriptada):
                            st.session_state['logueado'] = True
                            st.session_state['usuario_telefono'] = db_tel
                            st.session_state['fila_usuario'] = fila_excel 
                            
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
# 2. PANTALLA DE REGISTRO
# ==========================================
def mostrar_registro_inicial():
    st.title("👋 ¡Bienvenido!")
    st.warning("Configura tu cuenta personal.")
    
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1: nuevo_nombre = st.text_input("Nombre:")
        with col2: nuevo_apellido = st.text_input("Apellido:")
        
        nuevo_correo = st.text_input("Correo Electrónico:")
        st.markdown("---")
        nueva_clave = st.text_input("Crea tu NUEVA contraseña:", type="password")
        confirmar_clave = st.text_input("Repite la contraseña:", type="password")
        
        guardar_datos = st.form_submit_button("Guardar y Encriptar 🔒", use_container_width=True)
        
        if guardar_datos:
            if nuevo_nombre and nuevo_apellido and nuevo_correo and nueva_clave:
                if nueva_clave == confirmar_clave:
                    try:
                        f = st.session_state['fila_usuario']
                        
                        # Guardamos ENCRIPTADO
                        clave_secreta = encriptar(nueva_clave)
                        
                        hoja_usuarios.update_cell(f, 2, clave_secreta)
                        hoja_usuarios.update_cell(f, 3, nuevo_nombre)
                        hoja_usuarios.update_cell(f, 4, nuevo_apellido)
                        hoja_usuarios.
