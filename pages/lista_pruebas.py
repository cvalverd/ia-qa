import streamlit as st
from modules import jira_api, llm_gen_gherkin , llm_get_data_for_search,st_combox_logic
import json




def procesar_json(uploaded_json):
    """
Procesa un archivo JSON subido y genera códigos Gherkin utilizando la función llm_gen_gherkin del módulo llm_gen_gherkin.
La función realiza los siguientes pasos:
  1. Intenta cargar el JSON desde el objeto 'uploaded_json' utilizando json.load().
  2. Llama a la función llm_gen_gherkin(llm_gen_gherkin.uploaded_json) para generar los códigos Gherkin a partir del contenido del JSON.
  3. Muestra los resultados utilizando st.write().

En caso de que ocurra un error:
  - Si se produce un KeyError, se muestra un mensaje indicando el error relacionado con la falta de una clave.
  - Para cualquier otro error, se muestra un mensaje genérico de error.
Args:
    uploaded_json: Objeto de archivo JSON subido que contiene la información necesaria para generar los códigos Gherkin.
Returns:
    None

Ejemplo:
    >>> # Suponiendo que 'uploaded_file' es un objeto subido a través de st.file_uploader()
    >>> procesar_json(uploaded_file)
    Resultados:
    { ... }  # Se muestra el resultado de la función llm_gen_gherkin
"""

    try:
        uploaded_json = json.load(uploaded_json)
        results = llm_gen_gherkin.llm_gen_gherkin(uploaded_json)
        st.write(f'Resultados: \n {results}')

    except KeyError as e:
        st.write(f'Error al obtener la historia de usuario, key error: {e}')
        return
    except Exception as e:
        st.write(f'Error al obtener la historia de usuario: {e}')
        return

def main():
    st_combox_logic.opcion_box()
    with st.form(key='user_description_form'):
        st.write('Subir archivo JSON con la descripcion del caso, lista de pruebas matcheadas y no matcheadas')
        uploaded_json = st.file_uploader("Subir archivo JSON", type=["json"])
        enviado = st.form_submit_button('Enviar', disabled=False)

    if enviado:
        procesar_json(uploaded_json)



if __name__ == '__main__':
    main()