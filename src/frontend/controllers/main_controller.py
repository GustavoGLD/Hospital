import os
import streamlit as st

from src.backend.services.data_service import DataService
from src.frontend.controllers.cirurgy_controller import CirurgyController
from src.frontend.controllers.generic_controller import GenericController
from src.frontend.views.main_view import MainView


class MainController(GenericController):
    def __init__(self):
        self.view = MainView()
        self.view.view_data_loader(os.listdir('data'), on_change=self.on_change_data_file)
        self.data = DataService(f'data/{MainView.data_file.value}')

    def start(self):
        self.data.load_data()
        st.write(self.data.cirurgy_repository.get_all())
        view_controller = CirurgyController(self.data)

        self.view.view_repositories_tabs()

    def on_change_data_file(self):
        pass

    def on_change_tab(self):
        pass