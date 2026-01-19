import streamlit as st
import sqlite3

st.set_page_config(page_title="Buscador", layout="centered")

# Conexión a Base de Datos Local
def init_db():
    conn = sqlite3.connect('codigos.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direccion TEXT UNIQUE,
            codigo TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

st.title("📍 Buscador de Direcciones")

# Buscador
busqueda = st.text_input("Escribe la dirección:", placeholder="Ej: Av. Reforma 123")

if busqueda:
    c.execute("SELECT codigo FROM registros WHERE direccion LIKE ?", ('%' + busqueda + '%',))
    resultado = c.fetchone()
    
    if resultado:
        st.success(f"✅ CÓDIGO: {resultado[0]}")
    else:
        st.warning("No encontrado.")
        with st.form("nuevo"):
            nuevo_cod = st.text_input("Ingresa el código nuevo:")
            if st.form_submit_button("Guardar"):
                if nuevo_cod:
                    try:
                        c.execute("INSERT INTO registros (direccion, codigo) VALUES (?, ?)", (busqueda, nuevo_cod))
                        conn.commit()
                        st.success("¡Guardado!")
                        st.experimental_rerun()
                    except:
                        st.error("Error o dirección duplicada.")
