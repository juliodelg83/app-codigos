import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# Configuración de página
st.set_page_config(page_title="Buscador", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_sheet():
    try:
        # Definimos el alcance
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Leemos la llave secreta desde Streamlit Secrets
        json_creds = json.loads(st.secrets["general"]["google_json"])
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
        client = gspread.authorize(creds)
        
        # Abre la hoja por su nombre
        # IMPORTANTE: Asegúrate de que tu hoja en Google se llame EXACTAMENTE "BuscadorDB"
        sheet = client.open("BuscadorDB").sheet1
        return sheet
    except Exception as e:
        return None

# Intentamos conectar
hoja = conectar_sheet()

st.title("📍 Buscador de Direcciones")

if not hoja:
    st.error("⚠️ Error de conexión: No pude conectar con Google Sheets.")
    st.info("Verifica: 1. Que el JSON esté bien pegado en Secrets. 2. Que hayas compartido la hoja con el correo del robot. 3. Que la hoja se llame 'BuscadorDB'.")
    st.stop()

# --- LÓGICA DE BÚSQUEDA ---
busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: Av. Reforma 123")

if busqueda:
    try:
        # Obtenemos todos los registros de la nube
        registros = hoja.get_all_records()
        
        # Lógica para encontrar coincidencia
        encontrado = None
        for fila in registros:
            # Convierte a texto y minúsculas para comparar mejor
            if busqueda.lower() in str(fila.get('Dirección', '')).lower():
                encontrado = fila.get('Código', '')
                break
        
        if encontrado:
            st.success("✅ CÓDIGO ENCONTRADO:")
            st.header(f"{encontrado}")
        else:
            st.warning(f"No existe registro para: '{busqueda}'")
            st.markdown("---")
            st.write("👇 **Registrar nuevo:**")
            
            with st.form("nuevo_form"):
                nuevo_cod = st.text_input("Ingresa el código correcto:")
                # Botón de envío
                enviado = st.form_submit_button("Guardar en Nube ☁️")
                
                if enviado:
                    if nuevo_cod:
                        # Guardamos en la hoja de Google
                        hoja.append_row([busqueda, nuevo_cod])
                        st.success("¡Guardado exitosamente!")
                        st.balloons()
                        # Un pequeño truco para limpiar la pantalla
                        st.empty() 
                    else:
                        st.error("Por favor escribe un código.")

    except Exception as e:
        st.error(f"Ocurrió un error leyendo los datos: {e}")

# (Opcional) Ver la base de datos completa abajo
with st.expander("👮‍♂️ Admin: Ver todos los registros"):
    st.dataframe(hoja.get_all_records())
