import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests # Necesario para Telegram

# Configuración de página
st.set_page_config(page_title="Buscador", layout="centered")

# --- FUNCIONES DE TELEGRAM ---
def enviar_telegram(mensaje):
    try:
        token = st.secrets["general"]["telegram_token"]
        chat_id = st.secrets["general"]["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": mensaje}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

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
        try:
            sheet_reportes = archivo.worksheet("Reportes")
        except:
            sheet_reportes = None
        return sheet_datos, sheet_reportes
    except Exception as e:
        return None, None

hoja, hoja_reportes = conectar_sheet()

st.title("📍 Buscador de Direcciones")

if not hoja:
    st.error("⚠️ Error de conexión: No pude conectar con Google Sheets.")
    st.stop()

# --- TRAER DATOS ---
try:
    registros = hoja.get_all_records()
except Exception as e:
    st.error(f"Error leyendo la base de datos: {e}")
    st.stop()

# --- LÓGICA DE BÚSQUEDA ---
busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: 17811 Vail St")

if busqueda:
    texto_buscar = busqueda.strip().lower()
    resultados_encontrados = []
    
    for i, fila in enumerate(registros):
        fila['_id'] = i 
        direccion_db = str(fila.get('Direccion', '')).strip().lower()
        if texto_buscar in direccion_db:
            resultados_encontrados.append(fila)
    
    # --- MOSTRAR RESULTADOS ---
    if len(resultados_encontrados) > 0:
        st.success(f"✅ Se encontraron {len(resultados_encontrados)} registro(s):")
        
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
                
                # Reportes
                with st.expander(f"🚨 ¿El código #{item.get('Codigo')} no funciona?"):
                    st.write("Envía la corrección al administrador:")
                    with st.form(f"reporte_form_{item['_id']}"):
                        nuevo_code_user = st.text_input("¿Cuál es el código correcto?", placeholder="Nuevo código")
                        comentario_user = st.text_input("Comentarios:", placeholder="Detalles extra...")
                        btn_reportar = st.form_submit_button("Registrar Reporte y Enviar 📩")
                        
                        if btn_reportar:
                            if hoja_reportes:
                                try:
                                    hoja_reportes.append_row([
                                        item.get('Direccion'), item.get('Ciudad'),
                                        item.get('Codigo'), nuevo_code_user, comentario_user
                                    ])
                                    st.success("✅ Reporte guardado.")
                                    # Notificación a Telegram por reporte
                                    enviar_telegram(f"🚨 REPORTE DE ERROR\nDirección: {item.get('Direccion')}\nCódigo Viejo: {item.get('Codigo')}\nSugerido: {nuevo_code_user}\nNota: {comentario_user}")
                                except:
                                    pass
                            
                            asunto = f"Correccion: {item.get('Direccion')}"
                            cuerpo = f"El código {item.get('Codigo')} NO funciona.\nNuevo: {nuevo_code_user}\nNota: {comentario_user}"
                            link = f"mailto:juliodelg@gmail.com?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                            st.markdown(f'<a href="{link}" target="_blank" style="display:inline-block;background:#d93025;color:white;padding:8px 15px;text-decoration:none;border-radius:5px;">📤 Enviar Correo</a>', unsafe_allow_html=True)
                st.divider()
                
    else:
        # --- REGISTRAR NUEVO ---
        st.warning(f"No existe registro para: '{busqueda}'")
        st.markdown("### 👇 Registrar nuevo:")
        
        with st.form("nuevo_form"):
            st.write(f"Vas a registrar: **{busqueda}**")
            c_a, c_b = st.columns(2)
            with c_a:
                nueva_ciudad = st.text_input("Ciudad:", placeholder="Ej: Dallas")
            with c_b:
                nuevo_estado = st.text_input("Estado:", placeholder="Ej: TX")
            
            nuevo_cod = st.text_input("Código de acceso:", placeholder="#1234")
            
            enviado = st.form_submit_button("Guardar en Nube ☁️", use_container_width=True)
            
            if enviado:
                if nuevo_cod and nueva_ciudad and nuevo_estado:
                    try:
                        with st.spinner("Guardando..."):
                            hoja.append_row([busqueda, nueva_ciudad, nuevo_estado, nuevo_cod])
                            
                            # --- ENVIAR NOTIFICACIÓN TELEGRAM ---
                            mensaje_aviso = f"🆕 NUEVO REGISTRO\n📍 {busqueda}\n🏙 {nueva_ciudad}, {nuevo_estado}\n🔑 Código: {nuevo_cod}"
                            enviar_telegram(mensaje_aviso)
                            
                        st.success("¡Guardado exitosamente!")
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.error("⚠️ Completa todos los campos.")

# --- FOOTER ---
st.markdown("---") 
st.markdown(
    """
    <div style='text-align: center; color: grey;'>
        <small>Creado por <b>Julio Delgado</b> | v3.0 (Con Notificaciones)</small>
    </div>
    """, 
    unsafe_allow_html=True
)
