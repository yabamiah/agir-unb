###################################################################
## DANI - Desenvolvedor e Apresentador de Números e Indicadores ##
##################################################################

from dash import Dash, html, dash_table, dcc
import pandas as pd
import plotly.express as px

class Dani:
    data_frame = pd.DataFrame()
    app = Dash(__name__)
    data_frame_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.csv"

    def __init__(self) -> None:
        print("init")
        # self.data_frame = data_frame

        # self.app.layout = html.Div([
        #     html.Div(children="AGIR-UNB Dashboard", style={'textAlign': 'center', 'color': 'green', 'fontSize': 30}),
        #     dash_table.DataTable(
        #         data=self.data_frame, 
        #         page_size=10,
        #         style_header={ 'backgroundColor': 'blue', 'fontWeight': 'bold'},
        #         style_cell={'padding': '5px', 'textAlign': 'center'},
        #     ),
        # ])

    def compliance_dashboard(self):
        print("Compliance Dashboard")

    def display_programa_integridade(self):
        print("Display Programa Integridade")