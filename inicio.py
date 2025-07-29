import streamlit as st
from modules import jira_api, llm_gen_gherkin , llm_get_data_for_search, st_combox_logic

def enviar_datos():

    st.write('Enviando datos...')


def main():
    st.set_page_config(page_title='BCI Project', layout='centered', initial_sidebar_state='auto')

    
    st.title('BCI Project')
        


  
if __name__ == '__main__':
    main()