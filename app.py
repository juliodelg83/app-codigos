import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse 
import requests 

# Configuración de página
st.set_page_config(page_title="Buscador", layout="centered")

# --- FUNCIONES DE TELEGRAM ---
def enviar_telegram(mensaje):
    try:
        token = st.secrets["general"]["telegram_token"]
        chat_id = st.secrets["general"]["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
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
                        
                        st.markdown("**Tus Datos:**")
                        col_rep_1, col_rep_2 = st.columns(2)
                        with col_rep_1:
                            rep_nombre = st.text_input("Nombre:", key=f"rep_nom_{item['_id']}")
                        with col_rep_2:
                            rep_tel = st.text_input("Teléfono:", key=f"rep_tel_{item['_id']}")

                        btn_reportar = st.form_submit_button("Registrar Reporte y Enviar 📩")
                        
                        if btn_reportar:
                            if rep_nombre and rep_tel:
                                usuario_completo = f"{rep_nombre} - {rep_tel}"
                                
                                if hoja_reportes:
                                    try:
                                        hoja_reportes.append_row([
                                            item.get('Direccion'), item.get('Ciudad'),
                                            item.get('Codigo'), nuevo_code_user, comentario_user, usuario_completo
                                        ])
                                        st.success("✅ Reporte guardado.")
                                        enviar_telegram(f"🚨 <b>REPORTE DE ERROR</b>\n📍 {item.get('Direccion')}\n🔑 Viejo: {item.get('Codigo')} -> Nuevo: {nuevo_code_user}\n💬 Nota: {comentario_user}\n👤 <b>Reporta:</b> {rep_nombre}\n📱 <b>Tel:</b> {rep_tel}")
                                    except:
                                        pass
                                
                                asunto = f"Correccion: {item.get('Direccion')}"
                                cuerpo = f"El código {item.get('Codigo')} NO funciona.\nNuevo: {nuevo_code_user}\nNota: {comentario_user}\nReportado por: {usuario_completo}"
                                link = f"mailto:juliodelg@gmail.com?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                                st.markdown(f'<a href="{link}" target="_blank" style="display:inline-block;background:#d93025;color:white;padding:8px 15px;text-decoration:none;border-radius:5px;">📤 Enviar Correo</a>', unsafe_allow_html=True)
                            else:
                                st.error("⚠️ Por favor escribe tu nombre y teléfono.")
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
            
            st.markdown("**Tus Datos:**")
            c_reg_1, c_reg_2 = st.columns(2)
            with c_reg_1:
                reg_nombre = st.text_input("Nombre:")
            with c_reg_2:
                reg_tel = st.text_input("Teléfono:")
            
            enviado = st.form_submit_button("Guardar", use_container_width=True)
            
            if enviado:
                if nuevo_cod and nueva_ciudad and nuevo_estado and reg_nombre and reg_tel:
                    try:
                        with st.spinner("Guardando..."):
                            usuario_completo = f"{reg_nombre} - {reg_tel}"
                            # Guardamos en Excel concatenado
                            hoja.append_row([busqueda, nueva_ciudad, nuevo_estado, nuevo_cod, usuario_completo])
                            
                            mensaje_aviso = f"🆕 <b>NUEVO REGISTRO</b>\n📍 {busqueda}\n🏙 {nueva_ciudad}, {nuevo_estado}\n🔑 Código: {nuevo_cod}\n👤 <b>Registra:</b> {reg_nombre}\n📱 <b>Tel:</b> {reg_tel}"
                            enviar_telegram(mensaje_aviso)
                            
                        st.success("¡Guardado exitosamente!")
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.error("⚠️ Completa todos los campos (incluyendo Nombre y Teléfono).")

# --- SECCIÓN DE SUGERENCIAS (ACTUALIZADA) ---
st.markdown("---")
with st.expander("💬 Enviar Comentario o Sugerencia"):
    with st.form("form_sugerencia"):
        st.write("¿Tienes alguna idea para mejorar la app o quieres decir algo?")
        texto_sugerencia = st.text_area("Escribe tu mensaje:", placeholder="Ej: Sería bueno agregar...")
        
        st.markdown("**Tus Datos (Obligatorios):**")
        c_sug_1, c_sug_2 = st.columns(2)
        with c_sug_1:
            sug_nombre = st.text_input("Nombre:")
        with c_sug_2:
            sug_tel = st.text_input("Teléfono:")
        
        enviar_sug = st.form_submit_button("Enviar Mensaje ✈️", use_container_width=True)
        
        if enviar_sug:
            if texto_sugerencia and sug_nombre and sug_tel:
                mensaje_telegram = f"💡 <b>NUEVA SUGERENCIA</b>\n💬 <b>Mensaje:</b> {texto_sugerencia}\n👤 <b>De:</b> {sug_nombre}\n📱 <b>Tel:</b> {sug_tel}"
                enviar_telegram(mensaje_telegram)
                st.success("¡Mensaje enviado! Gracias por tu opinión.")
            else:
                st.error("⚠️ Por favor completa el mensaje, tu nombre y tu teléfono.")

# --- FOOTER ---
st.markdown("---") 
st.markdown(
    """
    <div style='text-align: center; color: grey;'>
        <small>Creado por <b>Julio Delgado</b> | v3.5</small>
    </div>
    """, 
    unsafe_allow_html=True
)
