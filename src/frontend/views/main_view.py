import streamlit as st

from src.utils.borg import BorgObj


class MainView:
    data_file = BorgObj("data_file", str)

    def __init__(self, cntr=st):
        self.data_loader = cntr.container()

    def view_data_loader(self, files: list[str], on_change: callable):
        self.data_loader.selectbox("Selecione um arquivo JSON da pasta 'data/' para carregar os dados",
                                   files, index=None, key=MainView.data_file.key, on_change=on_change)
