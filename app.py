import datetime
import io
import time
import os
import base64

from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.express as px

import pandas as pd
from pdf2image import convert_from_bytes

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

# region Helper functions
def spacing():
    return html.Br()


def parse_contents(contents, filename, date):
    return html.Div(
        [
            html.H5(filename),
            html.H6(datetime.datetime.fromtimestamp(date)),
            # HTML images accept base64 encoded strings in the same format
            # that is supplied by the upload
            html.Img(src=contents),
            html.Hr(),
            html.Div("Raw Content"),
            html.Pre(
                contents[0:200] + "...",
                style={"whiteSpace": "pre-wrap", "wordBreak": "break-all"},
            ),
        ]
    )


def pil_to_b64_dash(im):
    buffered = io.BytesIO()
    im.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue())
    return bytes("data:image/jpeg;base64,", encoding="utf-8") + img_str


def parse_pdf_contents(contents, filename, date):
    content_type, content_string = contents.split(",")

    decoded = base64.b64decode(content_string)
    images = convert_from_bytes(
        decoded,
        poppler_path=poppler_path,
    )

    encoded = pil_to_b64_dash(images[0])

    return html.Div(
        [
            # HTML images accept base64 encoded strings in the same format
            # that is supplied by the upload
            html.Img(src=encoded.decode("utf-8")),
            html.Hr(),
        ]
    )


# endregion

# region settings
app = Dash(__name__, external_stylesheets=external_stylesheets)

# path to pdf decoding library:
poppler_path = os.path.join(os.getcwd(), "lib\\poppler-0.68.0\\bin")

# path to .csv files:
oems_table_path = os.path.join(os.getcwd(), "tables", "oems_table.csv")
products_table_path = os.path.join(os.getcwd(), "tables", "products_table.csv")
repairs_table_path = os.path.join(os.getcwd(), "tables", "repairs_table.csv")

# read .csv files and list first column:
oems_table = pd.read_csv(oems_table_path)
oems_list = oems_table["OEM"]
prod_table = pd.read_csv(products_table_path)
prod_list = prod_table["Product"]
repairs_table = pd.read_csv(repairs_table_path)
repairs_list = repairs_table["Repair"]

# file uploads style:
image_uplaod_style = {
    "width": "100%",
    "height": "60px",
    "lineHeight": "60px",
    "borderWidth": "1px",
    "borderStyle": "dashed",
    "borderRadius": "5px",
    "textAlign": "center",
    "margin": "10px",
}
pdf_uplaod_style = {
    "width": "100%",
    "height": "60px",
    "lineHeight": "60px",
    "borderWidth": "1px",
    "borderStyle": "dashed",
    "borderRadius": "5px",
    "textAlign": "center",
    "margin": "10px",
}
# endregion

# region app layout
app.layout = html.Div(
    children=[
        html.Div(
            children=[
                # Title
                html.H1(
                    "KVE Composite Repair dashboard",
                    style={"text-align": "center", "background-color": "#ede9e8"},
                ),
                # OEM Selection
                dcc.Dropdown(
                    value=[""],
                    placeholder="Select an OEM manufacture...",
                    options=[{"label": i, "value": i} for i in oems_list],
                    multi=False,
                    id="OEM-dropdown",
                ),
                spacing(),
                # Aircraft/product Selection
                dcc.Dropdown(
                    value=[""],
                    placeholder="Select a product...",
                    options=[{"label": i, "value": i} for i in prod_list],
                    multi=False,
                    id="Product-dropdown",
                ),
                spacing(),
                # Repair Selection
                dcc.Dropdown(
                    value=[""],
                    placeholder="Select a repair...",
                    options=[{"label": i, "value": i} for i in repairs_list],
                    multi=False,
                    id="Repair-dropdown",
                    # onrelease="console.log('hello')",
                ),
                spacing(),
                # Upload pictures of repair
                html.Div(
                    [
                        "Picture name: ",
                        dcc.Input(id="picture-input-name", value="", type="text"),
                    ]
                ),
                spacing(),
                html.Div(id="picture-output-name"),
                spacing(),
                html.Div(
                    [
                        dcc.Upload(
                            className="three columns",
                            id="upload-image",
                            children=html.Div(
                                ["Drag and Drop or ", html.A("Select picture")]
                            ),
                            style=image_uplaod_style,
                            # Allow multiple files to be uploaded
                            multiple=True,
                        ),
                        dcc.Upload(
                            className="three columns",
                            id="upload-coa",
                            children=html.Div(
                                ["Drag and Drop or ", html.A("Select PDF")]
                            ),
                            style=pdf_uplaod_style,
                            # Allow multiple files to be uploaded
                            multiple=False,
                        ),
                        dcc.Upload(
                            className="three columns",
                            id="upload-pcd",
                            children=html.Div(
                                [
                                    "Drag and Drop or ",
                                    html.A("Select a pointcloud file"),
                                ]
                            ),
                            style=pdf_uplaod_style,
                            # Allow multiple files to be uploaded
                            multiple=False,
                            accept=".ply, .pcd",
                        ),
                    ],
                    style={"display": "flex"},
                    className="row",
                ),
            ],
        ),
        html.Hr(),
        html.Div(
            [
                html.Div(id="output-coa", className="three columns"),
                html.Div(id="output-image-upload", className="three columns"),
                html.Div(id="pcd-render", className="three columns"),
            ],
            style={"display": "flex"},
            className="row",
        ),
    ]
)

# endregion

# region Callbacks
@app.callback(
    Output(component_id="picture-output-name", component_property="children"),
    Input(component_id="picture-input-name", component_property="value"),
)
def update_output_div(input_value):
    return f"Output: {input_value}"


# @app.callback(
#     Output(component_id="upload-pcd", component_property="children"),
#     Input(component_id="pcd-render", component_property="contents"),
# )
# def load_pcd_file(list_of_contents):
#     if list_of_contents is not None:
#         children = [parse_contents(c, n, d) for c, n, d in zip(list_of_contents)]
#         return children


@app.callback(
    Output("output-image-upload", "children"),
    Input("upload-image", "contents"),
    State("upload-image", "filename"),
    State("upload-image", "last_modified"),
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d)
            for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)
        ]
        return children


@app.callback(
    Output("output-coa", "children"),
    [Input("upload-coa", "contents")],
    [State("upload-coa", "filename"), State("upload-coa", "last_modified")],
)
def show_coa(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [parse_pdf_contents(list_of_contents, list_of_names, list_of_dates)]
        return children


# endregion

if __name__ == "__main__":
    app.run_server(debug=True)
