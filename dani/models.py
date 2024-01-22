###################################################################
## DANI - Desenvolvedor e Apresentador de Números e Indicadores ##
##################################################################

from dash import Dash, html, dash_table, dcc
import pandas as pd
import plotly.express as px

class Dani:
    data_frame = pd.DataFrame()
    app = Dash(__name__)

    def __init__(self, data_frame: pd.DataFrame) -> None:
        self.data_frame = data_frame

        self.app.layout = html.Div([
            html.Div(children="AGIR-UNB Dashboard", style={'textAlign': 'center', 'color': 'green', 'fontSize': 30}),
            dash_table.DataTable(
                data=self.data_frame, 
                page_size=10,
                style_header={ 'backgroundColor': 'blue', 'fontWeight': 'bold'},
                style_cell={'padding': '5px', 'textAlign': 'center'},
            ),
        ])