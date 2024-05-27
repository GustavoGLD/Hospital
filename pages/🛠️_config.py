import streamlit as st

st.set_page_config(
    page_title="Configurações",
    page_icon="🏥",
)

with st.container(border=True):
    st.write("Distribuição das Cirurgias")

    num_generations = st.slider("1. Número de gerações", min_value=1, max_value=500, value=50, step=1)
    sol_per_pop = st.slider("1. Solução por população", min_value=1, max_value=500, value=30, step=1)
    num_parents_mating = st.slider("1. Número de pais para cruzamento", min_value=1, max_value=sol_per_pop, value=15, step=1)

    st.session_state['dist_config'] = {
        "num_generations": num_generations,
        "sol_per_pop": sol_per_pop,
        "num_parents_mating": num_parents_mating
    }

    with st.expander("1. Configurações avançadas"):
        crossover_type = st.selectbox("1. Tipo de cruzamento", ["uniform", "single_point", "two_points", "scattered"])
        mutation_type = st.selectbox("1. Tipo de mutação", ["adaptive", "random"])
        mutation_percent_genes = st.slider("1. Porcentagem de genes mutados", min_value=1, max_value=100, value=[10, 25], step=1)
        parent_selection_type = st.selectbox("1. Tipo de seleção de pais", ["sss", "tournament", "rank"])
        keep_parents = st.slider("1. Número de pais mantidos", min_value=1, max_value=sol_per_pop, value=5, step=1)

    st.session_state['dist_config'] = {
        "num_generations": num_generations,
        "sol_per_pop": sol_per_pop,
        "num_parents_mating": num_parents_mating,
        "crossover_type": crossover_type,
        "mutation_type": mutation_type,
        "mutation_percent_genes": mutation_percent_genes,
        "parent_selection_type": parent_selection_type,
        "keep_parents": keep_parents
    }

with st.container(border=True):
    st.write("Ordenação das Cirurgias")

    num_generations = st.slider("2. Número de gerações", min_value=1, max_value=500, value=10, step=1)
    sol_per_pop = st.slider("2. Solução por população", min_value=1, max_value=500, value=30, step=1)
    num_parents_mating = st.slider("2. Número de pais para cruzamento", min_value=1, max_value=sol_per_pop, value=15, step=1)

    with st.expander("2. Configurações avançadas"):
        crossover_type = st.selectbox("2. Tipo de cruzamento", ["uniform", "single_point", "two_points", "scattered"])
        mutation_type = st.selectbox("2. Tipo de mutação", ["adaptive", "random"])
        mutation_percent_genes = st.slider("2. Porcentagem de genes mutados", min_value=1, max_value=100, value=[5, 15], step=1)
        parent_selection_type = st.selectbox("2. Tipo de seleção de pais", ["sss", "tournament", "rank"])
        keep_parents = st.slider("2. Número de pais mantidos", min_value=1, max_value=sol_per_pop, value=5, step=1)

    st.session_state['ord_config'] = {
        "num_generations": num_generations,
        "sol_per_pop": sol_per_pop,
        "num_parents_mating": num_parents_mating,
        "crossover_type": crossover_type,
        "mutation_type": mutation_type,
        "mutation_percent_genes": mutation_percent_genes,
        "parent_selection_type": parent_selection_type,
        "keep_parents": keep_parents
    }
