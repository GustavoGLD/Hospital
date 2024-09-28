import os
import sys
import unittest
from inspect import getsourcefile

from loguru import logger

current_dir = os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))
sys.path.insert(0, current_dir[:current_dir.rfind(os.path.sep)])


from streamlit.testing.v1 import AppTest
from src.frontend.views.cirurgy_view import CirurgyView
from src.backend.entities.cirurgy_entity import CirurgyEntity
from src.frontend.views.main_view import MainView


import pytest


class TestViews(unittest.TestCase):
    def setUp(self) -> None:
        self.at = AppTest.from_file("streamlit_app.py")
        self.at.run()

        logger.info(f"{self.at.selectbox(key=MainView.data_file.key)}")
        self.at.selectbox(key=MainView.data_file.key).select("data.json").run()

    def test_cirurgy_view(self):
        logger.info(f"{self.at.selectbox(key=CirurgyView.selected_cirurgy_name.key)}")
        self.at.selectbox(key=CirurgyView.selected_cirurgy_name.key).select('Cirurgia de Exemplo 1 - 0').run()

        logger.info(f"{self.at.text_input(key=CirurgyView.change_cirugy_name.key)}")
        self.at.text_input(key=CirurgyView.change_cirugy_name.key).input("Cirurgia de Exemplo 2").run()

        logger.info(f"{self.at.text_input(key=CirurgyView.change_patient_name.key)}")
        self.at.text_input(key=CirurgyView.change_patient_name.key).input("Paciente de Exemplo 2").run()

        logger.info(f"{self.at.number_input(key=CirurgyView.change_priority.key)}")
        self.at.number_input(key=CirurgyView.change_priority.key).increment().run()

        logger.info(f"{self.at.number_input(key=CirurgyView.change_duration.key)}")
        self.at.number_input(key=CirurgyView.change_duration.key).increment().run()

        logger.info(f"{self.at.multiselect(key=CirurgyView.change_possible_teams.key)}")
        self.at.multiselect(key=CirurgyView.change_possible_teams.key).select("Team Delta - 3").run()

        logger.info(f"{self.at.multiselect(key=CirurgyView.change_possible_rooms.key)}")
        self.at.multiselect(key=CirurgyView.change_possible_rooms.key).select("Room B - 1").run()









