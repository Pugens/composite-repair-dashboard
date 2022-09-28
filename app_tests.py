from operator import concat
import dash
from dash import dcc, Input, Output, html, dash_table
import plotly.express as px
import pandas as pd
import os

# import plotly
import plotly.graph_objects as go


# ======================== Dash App
app = dash.Dash(__name__)

# ======================== Getting input of directory and Latest filename
PATH = str(
    "C:\\Users\\eugen\\local_workspaces\\composite-repair-dashboard\\tables\\"
)  # Use your path

# Fetch all files in path
fileNames = os.listdir(PATH)

# Filter file name list for files ending with .csv
fileNames = [file for file in fileNames if ".csv" in file]

print(fileNames)


# ======================== App Layout

app.layout = html.Div(
    [
        html.H1(
            "Table Content",
            style={"text-align": "center", "background-color": "#ede9e8"},
        ),
        html.Div(
            [
                dcc.Dropdown(
                    id="DropDown_FileName",
                    options=[{"label": i, "value": i} for i in fileNames],
                    # value=fileNames,
                    placeholder="Select a File",
                    multi=False,
                    clearable=False,
                ),
            ]
        ),
        html.Div(
            id="tblData",
        ),
    ]
)


@app.callback([Output("tblData", "children")], [Input("DropDown_FileName", "value")])
def update_figure(DropDown_FileName):
    # ======================== Reading Selected csv file

    print(concat(PATH + DropDown_FileName))
    analytics = pd.read_csv(PATH + DropDown_FileName)
    analytics["Comb_wgt"] = analytics.Samples * analytics.Average
    print(analytics)

    return dash_table.DataTable(
        data=analytics.to_dict("records"),
        columns=[{"name": i, "id": i} for i in (analytics.columns)],
    )


if __name__ == "__main__":
    app.run_server(debug=True)
