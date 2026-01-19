import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time # Importamos time para dar un respiro antes de recargar

# Configuración de página
st.set_page_config(page_title="Buscador", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Usamos cache_resource para no reconectar a Google cada vez que tocas un botón (hace la app más rápida)
@st.cache_resource
def conectar_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        json_creds = json.loads(st.secrets["general"]["google_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
        client = gspread.authorize(creds)
        # Asegúrate de que tu hoja se llame "BuscadorDB"
        sheet = client.open("BuscadorDB").sheet1
        return sheet
    except Exception as e:
        return None

hoja = conectar_sheet()

st.title("📍 Buscador de Direcciones")

if not hoja:
    st.error("⚠️ Error de conexión: No pude conectar con Google Sheets.")
    st.stop()

# --- TRAER DATOS ---
# Traemos los datos una vez al principio
try:
    registros = hoja.get_all_records()
except Exception as e:
    st.error(f"Error leyendo la base de datos: {e}")
    st.stop()

# --- LÓGICA DE BÚSQUEDA ---
busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: Av. Reforma 123 o solo 123")

if busqueda:
    # Limpiamos lo que escribe el usuario (quitamos espacios extra)
    texto_buscar = busqueda.strip().lower()
    
    # Buscamos TODAS las coincidencias, no solo la primera
    # NOTA: Usamos 'Direccion' sin acento basándonos en tu captura de pantalla
    resultados_encontrados = []
    
    for fila in registros:
        # Obtenemos el valor de la dirección de la base de datos
        # .get('Direccion') debe coincidir EXACTO con la cabecera de tu Excel/Sheet
        direccion_db = str(fila.get('Direccion', '')).strip().lower()
        
        if texto_buscar in direccion_db:
            resultados_encontrados.append(fila)
    
    # --- MOSTRAR RESULTADOS ---
    if len(resultados_encontrados) > 0:
        st.success(f"✅ Se encontraron {len(resultados_encontrados)} registro(s):")
        
        # Mostramos cada resultado encontrado
        for item in resultados_encontrados:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Dirección:** {item.get('Direccion')}")
                with col2:
                    st.write(f"**Código:** {item.get('Codigo')}")
                st.markdown("---")
                
    else:
        # --- SI NO ENCUENTRA NADA, MUESTRA EL FORMULARIO ---
        st.warning(f"No existe registro que contenga: '{busqueda}'")
        st.markdown("### 👇 Registrar nuevo:")
        
        with st.form("nuevo_form"):
            # Mostramos la dirección que no se encontró para no tener que escribirla de nuevo
            st.write(f"Vas a registrar: **{busqueda}**")
            nuevo_cod = st.text_input("Ingresa el código correcto:")
            
            enviado = st.form_submit_button("Guardar en Nube ☁️")
            
            if enviado:
                if nuevo_cod:
                    # INCIO DEL BLOQUE TRY
                    try:
                        with st.spinner("Guardando..."):
                            # Guardamos en la hoja de Google
                            hoja.append_row([busqueda, nuevo_cod])
                            
                        st.success("¡Guardado exitosamente!")
                        
                        # Esperamos 1 segundo y recargamos
                        time.sleep(1) 
                        st.rerun() 
                        
                    # ESTA ES LA PARTE QUE TE FALTABA O ESTABA DESALINEADA:
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                    # FIN DEL BLOQUE
                else:
                    st.error("Por favor escribe un código.")
