from sys import stdout

import streamlit as st
import pandas as pd
import random

from loguru import logger
import time

logger.remove()
logger.add(stdout, level="DEBUG")

st.set_page_config(
    page_title="Agenda Inteligente de Cirurgias",
    page_icon="🏥",
)

if "random_df" not in st.session_state:
    ns = [random.randint(1, 100) for _ in range(120)]
    st.session_state.random_df = pd.DataFrame(
        {
            "duration": ns,
            "punishment": [100-n for n in ns]
        }
    )

if st.checkbox("Gerar dados aleatórios"):
    q = st.number_input("Número de cirurgias", min_value=1, max_value=500, value=120, step=1)
    if st.button("Gerar"):
        ns = [random.randint(1, 100) for _ in range(q)]
        st.session_state.random_df = pd.DataFrame(
            {
                "duration": ns,
                "punishment": [100-n for n in ns]
            }
        )

edited_df = st.data_editor(
    st.session_state.random_df,
    column_config={
        "duration": st.column_config.NumberColumn(
            "Duração (minutos)", min_value=0, max_value=100, step=1
        ),
        "punishment": st.column_config.NumberColumn(
            "Punição por atraso", min_value=0, max_value=100, step=1
        )
    },
    num_rows="dynamic",
    use_container_width=True,
)

num_rooms = st.number_input("Número de salas", min_value=1, max_value=150, value=40, step=1)

if st.button("Organizar salas"):
    from main import Cirurgy, Room, RoomList, suppress_stdout

    Cirurgy.reset_cirurgies()
    for index, row in edited_df.iterrows():
        Cirurgy(duration=int(row["duration"]), punishment=int(row["punishment"]))

    #st.json(Cirurgy.get_all_cirurgies())

    roomlist = RoomList([Room() for _ in range(num_rooms)])

    inicio = time.time()
    with st.spinner("Organizando salas..."):
        with suppress_stdout():
            roomlist.best_rooms_organization()

    st.write(f"Tempo de execução: {time.time() - inicio:.2f}s")
    logger.critical(f"Tempo de execução: {time.time() - inicio:.2f}s")

    st.write("Organização das salas:")
    for room in roomlist:
        st.write(f"Sala {room.id}: {room.best_order}")