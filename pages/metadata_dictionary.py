import streamlit as st
import sys, os
sys.path.append(".")
from dotenv import load_dotenv
from modules.llm_gen_descripcion import generar_descripcion_funcional, ejemplo_gherkin_diccionario
from modules.jira_api import get_issue, get_fullissue
from PIL import Image
import pytesseract

load_dotenv()

st.json(ejemplo_gherkin_diccionario)
st.write("## Generar Descripción Funcional")

# Seleccionar el escenario (basado en el campo 'prueba')
scenario_names = [item["prueba"] for item in ejemplo_gherkin_diccionario]
selected_scenario = st.selectbox("Selecciona un escenario", scenario_names)

# Elegir la fuente de contexto: Jira o Imagen SDM
context_source = st.radio("Selecciona la fuente de contexto", options=["Jira", "Imagen SDM"])

# Si el usuario elige "Imagen SDM", mostramos el file uploader y guardamos el resultado
uploaded_file = None
if context_source == "Imagen SDM":
    uploaded_file = st.file_uploader("Carga una imagen SDM (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])

if st.button("Generar Descripción"):
    # Buscar el escenario seleccionado
    selected_dict = next((d for d in ejemplo_gherkin_diccionario if d["prueba"] == selected_scenario), None)
    
    if selected_dict:
        st.subheader("Código Gherkin Seleccionado")
        st.code(selected_dict["codigo_gherkin"])
        
        context_output = ""
        if context_source == "Jira":
            jira_code = selected_dict.get("codigo_historia_de_usuario", "")
            st.write("Código de historia de usuario:", jira_code)
            context_output = get_fullissue('ESB-3539')
            st.subheader("Contexto obtenido de Jira")
            st.write(context_output)
        else:
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, caption="Imagen cargada", use_column_width=True)
                context_output = pytesseract.image_to_string(image)
                st.subheader("Texto extraído de la imagen")
                st.write(context_output)
            else:
                st.error("Por favor, carga una imagen SDM para extraer el contexto.")
        
        # Si se obtuvo el contexto, generar la descripción funcional
        if context_output:
            generated_desc = generar_descripcion_funcional(selected_dict["codigo_gherkin"], context_output)
            st.subheader("Descripción Funcional Generada")
            st.code(generated_desc)
        else:
            st.error("No se obtuvo contexto. Verifica la fuente elegida.")
    else:
        st.error("No se encontró el escenario seleccionado.")
