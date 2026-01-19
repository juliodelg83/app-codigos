import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 

# Configuración de página
st.set_page_config(page_title="Buscador", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        json_creds = json.loads(st.secrets["general"]["google_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
        client = gspread.authorize(creds)
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
try:
    registros = hoja.get_all_records()
except Exception as e:
    st.error(f"Error leyendo la base de datos: {e}")
    st.stop()

# --- LÓGICA DE BÚSQUEDA ---
busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: 17811 Vail St")

if busqueda:
    # Limpieza básica
    texto_buscar = busqueda.strip().lower()
    
    resultados_encontrados = []
    
    for fila in registros:
        # Buscamos coincidencias en la columna 'Direccion'
        direccion_db = str(fila.get('Direccion', '')).strip().lower()
        
        if texto_buscar in direccion_db:
            resultados_encontrados.append(fila)
    
    # --- MOSTRAR RESULTADOS ---
    if len(resultados_encontrados) > 0:
        st.success(f"✅ Se encontraron {len(resultados_encontrados)} registro(s):")
        
        for item in resultados_encontrados:
            with st.container():
                # Organizamos la info en columnas para que se vea limpio
                c1, c2, c3 = st.columns([3, 2, 1])
                
                with c1:
                    st.caption("Dirección")
                    st.write(f"**{item.get('Direccion')}**")
                
                with c2:
                    st.caption("Ubicación")
                    # Mostramos Ciudad y Estado juntos
                    st.write(f"{item.get('Ciudad')}, {item.get('Estado')}")
                
                with c3:
                    st.caption("Código")
                    st.markdown(f"### {item.get('Codigo')}")
                
                st.divider() # Linea separadora elegante
                
    else:
        # --- FORMULARIO DE REGISTRO ---
        st.warning(f"No existe registro para: '{busqueda}'")
        st.markdown("### 👇 Registrar nuevo:")
        
        with st.form("nuevo_form"):
            st.write(f"Vas a registrar: **{busqueda}**")
            
            # Fila 1: Ciudad y Estado
            col_a, col_b = st.columns(2)
            with col_a:
                nueva_ciudad = st.text_input("Ciudad:", placeholder="Ej: Dallas")
            with col_b:
                nuevo_estado = st.text_input("Estado:", placeholder="Ej: TX")
            
            # Fila 2: Código (ocupando todo el ancho para que destaque)
            nuevo_cod = st.text_input("Código de acceso:", placeholder="#1234")
            
            enviado = st.form_submit_button("Guardar en Nube ☁️", use_container_width=True)
            
            if enviado:
                # Validamos que no falte nada
                if nuevo_cod and nueva_ciudad and nuevo_estado:
                    try:
                        with st.spinner("Guardando..."):
                            # Guardamos las 4 columnas en orden
                            hoja.append_row([busqueda, nueva_ciudad, nuevo_estado, nuevo_cod])
                            
                        st.success("¡Guardado exitosamente!")
                        time.sleep(1) 
                        st.rerun() 
                        
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.error("⚠️ Por favor completa Ciudad, Estado y Código.")

# (Opcional) Tabla Admin
with st.expander("👮‍♂️ Admin: Ver todos los registros"):
    st.dataframe(registros)
