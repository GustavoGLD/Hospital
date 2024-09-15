import random
import requests
import streamlit as st
import pandas as pd


@st.cache_data
def get_df() -> pd.DataFrame:
    tags = [str(n) for n in range(10)]
    tags_col = []
    for row_index in range(10):
        tags_col.append(random.sample(tags, random.randint(1, 5)))
    setup_col = []
    delivary_col = []
    for row_index in range(10):
        r = requests.get('https://v2.jokeapi.dev/joke/Any?type=twopart')
        setup_col.append(r.json()['setup'])
        delivary_col.append(r.json()['delivery'])
    return pd.DataFrame({'setup': setup_col, 'delivary': delivary_col, 'tags': tags_col})


if __name__ == '__main__':
    import ast

    # Define a lista de dicionários
    lista = [
        {'b': 1, 'bx': {'ba': 2, 'be': 3}},
        {'b': 2, 'bx': {'ba': 3, 'be': 4}},
        {'b': 3, 'bx': {'ba': 4, 'be': 5}},
    ]

    # Define a string com a condição de filtragem
    condicao = "d['b'] > 2 and d['bx']['be'] <= 5"

    # Faz a list comprehension usando ast.literal_eval
    resultado = [d for d in lista if eval(condicao)]
    print(resultado)

