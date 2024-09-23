import os
import streamlit as st

from src.backend.services.data_service import DataService
from src.frontend.controllers.generic_controller import GenericController
from src.frontend.views.main_view import MainView


class MainController(GenericController):
    def __init__(self):
        self.view = MainView()

    def start(self):
        self.view.view_data_loader(os.listdir('data'), on_change=self.on_change_data_file)

        data = DataService(f'data/{MainView.data_file.value}')
        data.load_data()
        st.write(data.cirurgy_repository.get_all())

    def on_change_data_file(self):
        pass