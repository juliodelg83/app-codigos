import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time 
import urllib.parse # Para generar el link de correo

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
        
        # Abrimos el archivo
        archivo = client.open("BuscadorDB")
        
        # Hoja principal
        sheet_datos = archivo.sheet1
        
        # Intentamos conectar con la hoja de Reportes
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

if not hoja_reportes:
    st.warning("⚠️ OJO: No encontré la hoja llamada 'Reportes'. Crea una pestaña nueva en tu Excel con ese nombre para guardar los fallos.")

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
    
    # Buscamos coincidencias
    for i, fila in enumerate(registros):
        # Guardamos el índice 'i' para usarlo como ID único de los botones
        fila['_id'] = i 
        direccion_db = str(fila.get('Direccion', '')).strip().lower()
        
        if texto_buscar in direccion_db:
            resultados_encontrados.append(fila)
    
    # --- MOSTRAR RESULTADOS ---
    if len(resultados_encontrados) > 0:
        st.success(f"✅ Se encontraron {len(resultados_encontrados)} registro(s):")
        
        for item in resultados_encontrados:
            with st.container():
                # Columnas de información
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
                
                # --- SECCIÓN DE REPORTE DE ERROR ---
                with st.expander(f"🚨 ¿El código #{item.get('Codigo')} no funciona?"):
                    st.write("Envía la corrección al administrador:")
                    
                    # Formulario único para este item
                    with st.form(f"reporte_form_{item['_id']}"):
                        nuevo_code_user = st.text_input("¿Cuál es el código correcto? (Si lo tienes)", placeholder="Nuevo código")
                        comentario_user = st.text_input("Comentarios adicionales:", placeholder="El código cambió, la puerta está rota, etc.")
                        
                        btn_reportar = st.form_submit_button("Registrar Reporte y Enviar 📩")
                        
                        if btn_reportar:
                            # 1. Guardar en la hoja "Reportes" del Excel
                            if hoja_reportes:
                                try:
                                    hoja_reportes.append_row([
                                        item.get('Direccion'),
                                        item.get('Ciudad'),
                                        item.get('Codigo'),   # Código Viejo
                                        nuevo_code_user,      # Código Nuevo Sugerido
                                        comentario_user       # Comentarios
                                    ])
                                    st.success("✅ Reporte guardado en la base de datos.")
                                except Exception as e:
                                    st.error(f"No se pudo guardar en Excel: {e}")
                            
                            # 2. Generar link de correo (mailto)
                            asunto = f"Correccion de Codigo: {item.get('Direccion')}"
                            cuerpo = f"""Hola Julio,
                            
El código actual {item.get('Codigo')} NO funciona para la dirección:
{item.get('Direccion')}, {item.get('Ciudad')}.

El NUEVO código correcto es: {nuevo_code_user}

Comentarios: {comentario_user}
"""
                            # Codificamos el texto para que funcione en el link
                            link_correo = f"mailto:juliodelg@gmail.com?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                            
                            st.markdown(f"""
                            <a href="{link_correo}" target="_blank" style="
                                display: inline-block;
                                background-color: #d93025;
                                color: white;
                                padding: 10px 20px;
                                text-decoration: none;
                                border-radius: 5px;
                                font-weight: bold;
                                text-align: center;
                            ">📤 Click aquí para enviar Correo a Julio</a>
                            """, unsafe_allow_html=True)

                st.divider()
                
    else:
        # --- FORMULARIO DE REGISTRO NUEVO ---
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
                        st.success("¡Guardado exitosamente!")
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.error("⚠️ Completa todos los campos.")

# Admin
with st.expander("👮‍♂️ Admin: Ver todos los registros"):
    st.dataframe(registros)
