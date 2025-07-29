import streamlit as st
import pandas as pd
import pickle
import json
import ast
from modules import jira_api, llm_get_data_for_search, llm_get_matrix, utils, octane_api,st_combox_logic
from modules.llm_matcher_gherkin import llm_match_gherkin_v2
from modules.llm_gen_gherkin import llm_gen_gherkin_v2
import docx
# cuando los modulos se importan, streamlit se queda en running hasta que terminan los testing que existen en los modulos


def obtener_torre_opciones():
    """Regresa una lista de tuplas (nombre, código) a partir del JSON"""
    with open("config/torres.json", "r", encoding="utf-8") as file:
        torres_codes = json.load(file)
    # Convertir el diccionario en lista de tuplas
    torres_items = list(torres_codes.items())
    return torres_items

def editar_componentes(data_for_search):
    df_componentes = pd.DataFrame(data_for_search, columns=["Componente Funcional"])
    st.markdown("### Componentes funcionales identificados:")
    #for comp in data_for_search:
    #    st.markdown(f"* {comp}")
    st.write("Tabla para editar los componentes")
    # Aseguramos la persistencia usando una key única
    edited_df = st.data_editor(df_componentes, num_rows="dynamic", key="editor_componentes", use_container_width=True)
    return edited_df["Componente Funcional"].tolist()

def editar_matriz(matriz):
    df_componentes = pd.DataFrame(matriz, columns=["Matriz de Pruebas"])
    st.markdown("### Pruebas identificados:")
    #for comp in data_for_search:
    #    st.markdown(f"* {comp}")
    st.write("Tabla para editar las pruebas")
    # Aseguramos la persistencia usando una key única
    edited_df_matriz = st.data_editor(df_componentes, num_rows="dynamic", key="editor_componentes_matriz", use_container_width=True)
    return edited_df_matriz["Matriz de Pruebas"].tolist()


def agregar_proceso_pendiente(matriz,get_issue,data_for_search):

    # se necesitan (matriz, get_issue,data_for_search)
    proceso_data = {"matriz":matriz,"get_issue":get_issue,"data_for_search":data_for_search}
    
    # añadir el proceso data a la lista de session_state
    st.session_state.procesos_pendientes.append(proceso_data)


def procesos_pendientes():
    """Verifica si existen procesos pendientes"""
    # esta funcion es para evitar la perdida relacionada a la arquitectura de streamlit
    # la idea es que en la re-ejecucion del programa continuara el proceso que se estaba haciendo antes.

    # si la lista no esta vacia , se imprime el titulo procesos pendientes y empieza ejecutandose
    if st.session_state.procesos_pendientes:
        st.markdown("### Procesos Pendientes:")
        for idx, proceso in enumerate(st.session_state.procesos_pendientes, start=1):
            st.write(f"Proceso {idx}:")
            st.write("Matriz:", proceso["matriz"])
            st.write("Issue:", proceso["get_issue"])
            st.write("Data for search:", proceso["data_for_search"])
            # Aquí podrías agregar lógica para reanudar el proceso
            # Por ejemplo, reejecutar la función que procesa esos datos
            # Una vez completado, puedes eliminar el proceso de la lista:
            # st.session_state.procesos_pendientes.pop(idx-1)

    pass

def ejecutar_proceso_pendiente():
    pass



def enviar_datos_jira(num_jira, matrix, torre_codigo):
    #TODO : Hacer pruebas con la matriz.
    # st.write(f"el nombre de test_matrix es {matrix.name}")
    matriz = llm_get_matrix.llm_get_matrix(matrix)

    #st.write(f"las pruebas indicadas son {matriz}")
    st.write(f"la torre elegida es {st.session_state.torre_codigo},verificando {torre_codigo}")

    #matriz = matriz[:2]
    # guardando num_jira en el session state
    st.session_state.num_jira = num_jira
    print("MATRIZ",matriz)
    st.session_state.matriz = ast.literal_eval(matriz)

    #Mostramos las pruebas de la matriz
    #df_matriz = pd.DataFrame(ast.literal_eval(st.session_state.matriz), columns=["Matriz de Prueba"],)
    #mostrar_df(df_matriz)

    try:
        st.session_state.current_get_issue = jira_api.get_fullissue(st.session_state.num_jira)

        #mostrar mas estilizado
        st.markdown(" ## La descripcion que obtuve desde Jira es : ")
        container_get_issue_jira = st.container(height=450,key= 'container_get_issue_jira')
        with container_get_issue_jira:
            st.code(st.session_state.current_get_issue["fields"]['description'])
        return True

    except KeyError as e:
        st.write(f'Error al obtener la historia de usuario, key error: {e}')
        return False
    except Exception as e:
        st.write(f'Error al obtener la historia de usuario: {e}')
        return False
    

    

    # st.write(f"El tipo de data for search es : {type(st.session_state.data_for_search)}")



def procesar_datos_jira():
    # Obtenemos los resultados de la API (Gherkin y descripciones de Jira)
    get_resultados = octane_api.get_bsc_gherkin_by_filters(
        shared_space_id=1008,
        workspace_id=st.session_state.torre_codigo,
        functional_components=st.session_state.data_for_search
    )

    with open('logs/check_gherkins.log', "a") as log_file:
        log_file.write(f"{get_resultados}%\n")
    
    # Guardamos los resultados en un archivo (opcional)
    #with open(f"{st.session_state.num_jira}.txt", "w") as file:
    #    json.dump(get_resultados, file, indent=4)
    
    # Inicializamos el historial de Gherkin en session_state si aún no existe
    if "gherkin_history" not in st.session_state:
        st.session_state.gherkin_history = []
    
    # Contador para casos sin user story
    missing_jira_count = 0
    
    # Procesamos cada resultado y almacenamos los scripts (evitando duplicados)
    for idx, resultado in enumerate(get_resultados, start=1):
        # Procesamos el bloque de Gherkin si existe
        if "Gherkin" in resultado:
            gherkin_data = resultado.get("Gherkin", {}).get("data", [])
            for script in gherkin_data:
                script_value = script.get("script", {}).get("value", "")
                if script_value:
                    # Agregamos al historial si aún no está registrado
                    if script_value not in [item["script"] for item in st.session_state.gherkin_history]:
                        st.session_state.gherkin_history.append({
                            "index": idx,
                            "script": script_value
                        })
        # Para la descripción de Jira, contamos los casos sin contenido
        jira_desc = resultado.get("jira_us_description", "")
        if not jira_desc:
            missing_jira_count += 1
        else:
            st.markdown("#### Descripción desde user story")
            st.markdown(jira_desc)
    

    if missing_jira_count > 0:
        st.markdown(f"#### {missing_jira_count} caso(s) no tienen user story de Jira Asociado.")
    
    # Insertamos el CSS para un contenedor de altura fija con scroll vertical
    st.markdown("### Historial de Gherkin:")
    # Creamos un contenedor HTML con clase 'container-550'
    # st.markdown('<div class="container-550">', unsafe_allow_html=True)
    # for item in st.session_state.gherkin_history:
    #     with st.expander(f"Gherkin Script {item['index']}"):
    #         st.code(item["script"], language="gherkin")
    # st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
        /* Estilos solo para elementos dentro de .mi-contenedor */
        .mi-contenedor {
            max-height: 550px;
            overflow-y: auto;
        }
    </style>
    """, unsafe_allow_html=True)

    #with st.container():
    #    st.markdown('<div class="mi-contenedor">', unsafe_allow_html=True)
    #    for item in st.session_state.gherkin_history:
    #        with st.expander(f"Gherkin Script {item['index']}"):
    #            st.code(item["script"], language="gherkin")
    #    st.markdown('</div>', unsafe_allow_html=True)

    # Calcular el índice de corte para dividir la lista
    half = len(st.session_state.gherkin_history) // 2

    # Si el número de ítems es impar, la primera columna obtiene un ítem más
    if len(st.session_state.gherkin_history) % 2 != 0:
        half += 1  # Aumentamos 'half' para que la primera columna tenga un ítem más

    col1, col2 = st.columns(2)  # Dividir el layout en dos columnas

    with col1:
        # Contenido para la primera columna
        st.markdown('<div class="mi-contenedor">', unsafe_allow_html=True)
        # Poner la primera mitad (más el ítem extra si es impar) en la primera columna
        for item in st.session_state.gherkin_history[:half]:
            with st.expander(f"Gherkin Script {item['index']}"):
                st.code(item["script"], language="gherkin")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # Contenido para la segunda columna
        st.markdown('<div class="mi-contenedor">', unsafe_allow_html=True)
        # Poner la segunda mitad en la segunda columna
        for item in st.session_state.gherkin_history[half:]:
            with st.expander(f"Gherkin Script {item['index']}"):
                st.code(item["script"], language="gherkin")
        st.markdown('</div>', unsafe_allow_html=True)


def post_gherkin():
        # Luego, continuamos con el match y la visualización de la tabla
    llm_matcher_result, llm_matcher_result_df = llm_match_gherkin_v2({
        "descripcion_caso": st.session_state.current_get_issue["fields"]['description'] if not st.session_state.state_m01 else st.session_state.current_story_sdm ,
        "matriz_de_prueba": st.session_state.matriz,
        "gherkin_encontrados": [item["script"] for item in st.session_state.gherkin_history]
    }, st.session_state.num_jira)
    
    st.markdown("### Tabla :")
    mostrar_df(llm_matcher_result_df)
    
    st.download_button(
        label="Download Table",
        data=st.session_state.final_table,
        file_name='tabla.csv',
        mime='text/csv'
    )
    
    llm_gen_resul, llm_gen_resul_df = llm_gen_gherkin_v2(llm_matcher_result,st.session_state.current_get_issue ,st.session_state.num_jira,source_of_story=st.session_state.state_m01)
    mostrar_df(llm_gen_resul_df)


def enviar_datos_sdm_2(archivo_m01,matrix,torre_codigo):
 
    matriz = llm_get_matrix.llm_get_matrix(matrix)

    #st.write(f"las pruebas indicadas son {matriz}")
    st.write(f"la torre elegida es {st.session_state.torre_codigo},verificando {torre_codigo}")

    #matriz = matriz[:2]
    # guardando num_jira en el session state
    # leer documentos docx
    doc = docx.Document(archivo_m01)
    texto = [parrafo.text for parrafo in doc.paragraphs]
    m01_file = "\n".join(texto)
    st.session_state.current_story_sdm = m01_file

    st.session_state.matriz = ast.literal_eval(matriz)

    #Mostramos las pruebas de la matriz
    #df_matriz = pd.DataFrame(ast.literal_eval(st.session_state.matriz), columns=["Matriz de Prueba"],)
    #mostrar_df(df_matriz)

    try:
        #st.session_state.current_get_issue = jira_api.get_fullissue(st.session_state.num_jira)

        #mostrar mas estilizado
        st.markdown(" ## La descripcion que obtuve desde Jira es : ")
        container_get_issue_jira = st.container(height=450,key= 'container_get_issue_jira')
        with container_get_issue_jira:
            st.code(st.session_state.current_story_sdm)
        return True

    except Exception as e:
        st.write(f'Error al obtener descripcion desde archivo D01 o M01: {e}')
        return False


def enviar_datos_sdm(option , num_jira,m01_file,d01_file,matrix, torre_Codigo):
    # Las opciones pueden ser num_jira y matrix ó m01, d01 y matrix

    if option == 'jira_story_form':
    
        st.write(f"el nombre de test_matrix es {matrix.name}")
        matriz = llm_get_matrix.llm_get_matrix(matrix)
        st.write(f"las pruebas indicadas son {matriz}")
        st.write(f"la torre elegida es {torre_Codigo}")
        #matriz = matriz[:2]
        try:
            get_issue = jira_api.get_fullissue(num_jira)
            st.markdown("## la descripcion FULL de jira es ")
            st.code(get_issue)
            #mostrar mas estilizado
            st.markdown(" ## La descripcion que obtuve desde Jira es : ")
            st.code(get_issue["fields"]['description'])
            

        except KeyError as e:
            st.write(f'Error al obtener la historia de usuario, key error: {e}')
            return
        except Exception as e:
            st.write(f'Error al obtener la historia de usuario: {e}')
            return

        
        data_for_search = llm_get_data_for_search.llm_get_data_for_search_v2_sdm(m01_file=m01_file,d01_file=d01_file,matrix=matriz,workspace_id=torre_Codigo)
        # result ess lista de componentes funcionales mostrar en streamlit
        # añadir get bsc gherkin by filters
        #data_for_search = ["ms-serviciosclientes-neg"]
        st.markdown("### los componentes funcionales identificados son :")
        for component_name in data_for_search:
            st.markdown(f"* {component_name}")
        
            
        get_resultados = octane_api.get_bsc_gherkin_by_filters(shared_space_id=1008,workspace_id=torre_Codigo,functional_components=data_for_search)
        with open("gherkins_jira-nrd-116.txt", "w") as file:
            json.dump(get_resultados,file,indent = 4)
        # Filtrando y extrayendo los scripts Gherkin
        list_gherkin = []
        for idx, resultado in enumerate(get_resultados, start=1):
            if "Gherkin" in resultado:
                gherkin_data = resultado["Gherkin"]['data']
                for script in gherkin_data:
                    #st.code(script)
                    script_value = script["script"]['value']
                    if script_value:
                        st.write(f"### Gherkin Script {idx}")
                        st.code(script_value, language="gherkin")
                        list_gherkin.append(script_value)
            if "jira_us_description" in resultado:
                if resultado['jira_us_description'] == "":
                    st.markdown("### No tiene user story de Jira Asociado . . .")
                else:
                    st.markdown(f"### Descripcion desde user story")
                    st.markdown(resultado['jira_us_description'])

        # ----- Realiza un match con los gherkin encontrados y las pruebas: -----
        llm_matcher_result, llm_matcher_result_df = llm_match_gherkin_v2({
            "descripcion_caso": get_issue["fields"]['description'],
            "matriz_de_prueba": matriz,
            "gherkin_encontrados": list_gherkin
            
            }, num_jira)
        
        #----- mostrar tabla en el front
        st.markdown(f"### Gherkin Relacionados por Prueba")
        mostrar_df(llm_matcher_result_df)


        # ----- Genera gherkin sugeridos para los no macheados ----
        llm_gen_resul, llm_gen_resul_df = llm_gen_gherkin_v2(llm_matcher_result, get_issue, num_jira)
        st.markdown(f"### Gherkin Nuevos Generados")

        #----- mostrar tabla en el front
        mostrar_df(llm_gen_resul_df)

    elif option == 'SDM':

        matriz = llm_get_matrix.llm_get_matrix(matrix)
    
        # try:
        #     get_issue = jira_api.get_fullissue(num_jira)
        #     #mostrar mas estilizado
        #     st.markdown(" ## La descripcion que obtuve desde Jira es : ")
        #     st.code(get_issue["fields"]['description'])

        # except KeyError as e:
        #     st.write(f'Error al obtener la historia de usuario, key error: {e}')
        #     return
        # except Exception as e:
        #     st.write(f'Error al obtener la historia de usuario: {e}')
        #     return
        
        data_for_search = llm_get_data_for_search.llm_get_data_for_search_v2_sdm(m01_file=m01_file,d01_file=d01_file,matrix=matriz,workspace_id=torre_Codigo)
        # result ess lista de componentes funcionales mostrar en streamlit
        # añadir get bsc gherkin by filters
        
        st.markdown("### los componentes funcionales identificados son :")
        for component_name in data_for_search:
            st.markdown(f"* {component_name}")
        
            
        get_resultados = octane_api.get_bsc_gherkin_by_filters(shared_space_id=1008,workspace_id=torre_Codigo,functional_components=data_for_search)

        with open("gherkins_jira-nrd-116.txt", "w") as file:
            json.dump(get_resultados,file,indent = 4)
        # Filtrando y extrayendo los scripts Gherkin
        for idx, resultado in enumerate(get_resultados, start=1):
            if "Gherkin" in resultado:
                for script in gherkin_data:
                    st.code(script)
                    script_value = script["script"]['value']
                    if script_value:
                        st.write(f"### Gherkin Script {idx}")
                        st.code(script_value, language="gherkin")
            if "jira_us_description" in resultado:
                if resultado['jira_us_description'] == "":
                    st.markdown("### No tiene user story de Jira Asociado . . .")
                else:
                    st.markdown(f"### Descripcion desde user story")
                    st.markdown(resultado['jira_us_description'])

    else:
        pass
    

def mostrar_df (data_df):
    # muestra los datos como una tabla en el front
    st.dataframe(data_df, use_container_width=True, hide_index=True)
    #st.session_state['final_table'] = data_df
    try:
        csv = data_df.to_csv(index=False).encode('utf-8')
        st.session_state['final_table'] = csv
    except Exception as e:
        print(f"error {e}")
    
    
            


def main():
    # st.set_page_config(page_title='BCI Project', layout='centered', initial_sidebar_state='auto')
    st.title('BCI Project')
    
    if "procesos_pendientes" not in st.session_state:
        st.session_state.procesos_pendientes = []

    if "final_table" not in st.session_state:
        st.session_state.final_table = ''

    if "selected_option_qa_motor" not in st.session_state:
        st.session_state.selected_option_qa_motor = ''
    
    if 'torre_codigo' not in st.session_state:
        st.session_state.torre_codigo = "opcion"
    
    if 'current_get_issue' not in st.session_state:
        st.session_state.current_get_issue = ""

    if 'current_story_sdm' not in st.session_state:
        st.session_state.current_story_sdm = ""
    
    if 'state_m01' not in st.session_state:
        st.session_state.state_m01=""
    
    if 'data_for_search' not in st.session_state:
        st.session_state.data_for_search = ""
    
    if 'num_jira' not in st.session_state:
        st.session_state.num_jira = ''

    if 'matriz' not in st.session_state:
        st.session_state.matriz = ''
    
    if "step" not in st.session_state:
        # las fases son inicial , editar , procesar
        st.session_state.step = "inicial"

    
    
    st.session_state.selected_option_qa_motor = st_combox_logic.opcion_box()
    st.write(f"Fase Actual : {st.session_state.step}")
    st.write(f"HDU: {st.session_state.num_jira}")
    st.write(f"Torre: {st.session_state.torre_codigo}")

    if st.session_state.step == 'inicial':
        st.write (f"La opcion seleccionada es {st.session_state.selected_option_qa_motor}")
        torres_items = obtener_torre_opciones()
        torre_seleccionada = st.selectbox(
            'Selecciona una opción:',
            torres_items,
            format_func=lambda x: f"{x[0]} ({x[1]})"
        )
        st.session_state.torre_codigo = torre_seleccionada[1]
        if st.session_state.selected_option_qa_motor == 'JIRA':
            with st.form(key='jira_story_form'):
                #caja input para recibir codigo de jira
                input_num = st.text_input('Ingrese el código de Historia de Usuario JIRA:')
                #file upload box para subir la matriz de prueba
                uploaded_file = st.file_uploader("Subir matriz de prueba JIRA", type=["xlsx","doc","docx","txt","csv"], key='jira_matrix')
                    # mostrar en un recuadro la vista previa del archivo subido
                    # enviado se habilitara cuando ambos campos esten ocupados.
                    # requeridos_bool = input_num_jira is None or uploaded_file is None
                enviado = st.form_submit_button('Enviar')

            if enviado:
                resul = enviar_datos_jira(input_num, uploaded_file, torre_codigo=st.session_state.torre_codigo)
                # Aqui se pasa a la siguente Fase
                if resul:
                    st.session_state.step = "editar_matriz"
                    st.rerun()

                
        elif st.session_state.selected_option_qa_motor =='SDM':
            option = st.radio("¿Opcion para la consulta?", ["Historia de Usuario","Subir M01 o D01"])
            with st.form(key='sdm_story_form'):
                
                input_num = ''
                d01_file = ''
                # Opciones de SDM para elegir las opciones
                #OPCION 1 : ING USER STORY SDM
                #OPCION 2 : SUBIR ARCHIVO M01 Y D01
                
                if option == "Historia de Usuario":
                    #caja input para recibir codigo de sdm
                    input_num = st.text_input(f'Ingrese el código de Historia de Usuario SDM:')
                elif option == "Subir M01 o D01":
                    # Caja para Subir M01
                    m01_file = st.file_uploader("Subir Archivo m01 o d01", type=["xlsx","xlsm","doc","docx"] , key='sdm_m01')
                    # Caja para Subir D01
                    #d01_file = st.file_uploader("Subir Archivo d01", type=["xlsx","xlsm","doc","docx"] , key='sdm_d01')


                #file upload box para subir la matriz de prueba
                uploaded_file = st.file_uploader("Subir matriz de prueba SDM", type=["xlsx","doc","docx","txt","csv"], key='sdm_matrix')
                    # mostrar en un recuadro la vista previa del archivo subido
                    # enviado se habilitara cuando ambos campos esten ocupados.
                    # requeridos_bool = input_num_jira is None or uploaded_file is None
                enviado = st.form_submit_button('Enviar')
####
                if enviado:
                    if option == "Historia de Usuario":
                        result = enviar_datos_jira(input_num, uploaded_file, torre_codigo=st.session_state.torre_codigo)
                        if result:
                            st.session_state.step = "editar_matriz"
                            st.rerun()
                    if option == "Subir M01 o D01":
                        #enviar_datos_sdm(st.session_state.selected_option_qa_motor,input_num, m01_file=m01_file,d01_file=d01_file,matrix=uploaded_file,torre_Codigo=st.session_state.torre_codigo)
                        st.session_state.state_m01 = True
                        result = enviar_datos_sdm_2(archivo_m01=m01_file,matrix=uploaded_file,torre_codigo=st.session_state.torre_codigo)
                        if result:
                            st.session_state.step = "editar_matriz"
                            st.rerun()

    
    elif st.session_state.step == "editar_matriz":
        #Muestra la descripcion del HDU
        st.markdown(" ## La descripcion que obtuve desde Jira es : ")
        container_get_issue = st.container(height=400,key='container_get_issue')
        with container_get_issue:
            # mostrar el curret get issue para dar apoyo en lo que hay que editar
            if st.session_state.state_m01:
                st.code(st.session_state.current_story_sdm)
            else:
                st.code(st.session_state.current_get_issue["fields"]['description'])
            
##
        #Mostramos las pruebas de la matriz para editar
        matriz = editar_matriz(st.session_state.matriz)

        if st.button("Continuar",  key="btn_continuar_editar"):

            st.session_state.matriz = list(filter(None, matriz))

            if st.session_state.state_m01:

                st.session_state.data_for_search = llm_get_data_for_search.llm_get_data_for_search_v3({
                    "descripcion_caso": st.session_state.current_story_sdm,
                    "matriz_de_prueba": matriz
                },
                workspace_id=st.session_state.torre_codigo,story_used='sdm')
            else:
                st.session_state.data_for_search = llm_get_data_for_search.llm_get_data_for_search_v3({
                    "descripcion_caso": st.session_state.current_get_issue,
                    "matriz_de_prueba": matriz
                },workspace_id=st.session_state.torre_codigo,story_used='jira')
            st.write(f"data for search : [{st.session_state.data_for_search}]")

            st.session_state.step = "editar_componente"
            st.rerun()


    
    elif st.session_state.step == "editar_componente":

        #Muestra la descripcion del HDU
        st.markdown(" ## La descripcion que obtuve desde Jira es : ")
        container_get_issue = st.container(height=400,key='container_get_issue')
        with container_get_issue:
            # mostrar el curret get issue para dar apoyo en lo que hay que editar
            if st.session_state.state_m01:
                st.code(st.session_state.current_story_sdm)
            else:
                st.code(st.session_state.current_get_issue["fields"]['description'])
        
        #Mostramos las pruebas de la matriz
        st.markdown("### Pruebas identificadas:")
        mostrar_df(st.session_state.matriz)
        
        # Permite al usuario editar los datos
        data_for_search = editar_componentes(st.session_state.data_for_search)
        with open('logs/check_data_for_search.log', "a") as log_file:
                log_file.write(f"{data_for_search}\n")

        # Botón para continuar
        if st.button("Continuar", key="btn_continuar_editar"):

            # Guarda el resultado editado en session_state
            st.session_state.data_for_search = list(filter(None, data_for_search))
            with open('logs/check_data_for_search.log', "a") as log_file:
                log_file.write(f"{data_for_search}\n")
            st.session_state.final_table = list(filter(None, data_for_search))

            #pasamos al siguiente paso
            st.session_state.step = "procesar"

            st.rerun()  # Fuerza la recarga y re-evaluación del script

        if st.button("Volver"):
            #pasamos al siguiente paso
            st.session_state.step = "inicial"
            st.rerun() 

    elif st.session_state.step == "procesar":

        #Muestra la descripcion del HDU
        st.markdown(" ## La descripcion que obtuve desde Jira es : ")
        container_get_issue = st.container(height=400,key='container_get_issue')
        with container_get_issue:
            # mostrar el curret get issue para dar apoyo en lo que hay que editar
            if st.session_state.state_m01:
                st.code(st.session_state.current_story_sdm)
            else:
                st.code(st.session_state.current_get_issue["fields"]['description'])

        #Mostramos las pruebas de la matriz
        st.markdown("### Pruebas identificadas:")
        mostrar_df(st.session_state.matriz)

        #Mostramos las pruebas de la matriz
        st.markdown("### Componentes Funcionales:")
        mostrar_df(st.session_state.data_for_search)
        
        procesar_datos_jira()
        post_gherkin()

        if st.button("Finalizar y volver al inicio"):
            #se limpia variables
            uploaded_file = None
            enviado = None
            option = None
            st.session_state.procesos_pendientes = []
            st.session_state.final_table = ''
            st.session_state.selected_option_qa_motor = ''
            st.session_state.torre_codigo = "opcion"
            st.session_state.current_get_issue = ""
            st.session_state.current_story_sdm = ""
            st.session_state.state_m01=""
            st.session_state.data_for_search = ""
            st.session_state.num_jira = ''
            st.session_state.matriz = ''
            st.session_state.step = "inicial"
        
            #se recarga pagina
            st.rerun()
        
    


  
if __name__ == '__main__':
    main()