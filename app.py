import datetime
import io
import time
import base64

import dash
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc

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


def parse_coa_contents(contents, filename, date):
    content_type, content_string = contents.split(",")

    decoded = base64.b64decode(content_string)

    images = convert_from_bytes(
        decoded,
        poppler_path=r"C:\Users\eugeniobernard\Local_documents\dash\poppler-0.68.0\bin",
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

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    children=[
        html.Div(
            children=[
                # Title
                html.H1("KVE Composite Repair dashboard"),
                # OEM Selection
                dcc.Dropdown(
                    value=[""],
                    placeholder="Select an OEM manufacture...",
                    options=[
                        {"label": i, "value": i}
                        for i in [
                            "Airbus",
                            "Boeing",
                            "Fokker",
                            "New client...",
                        ]
                    ],
                    multi=False,
                    id="OEM-dropdown",
                ),
                # Aircraft/product Selection
                dcc.Dropdown(
                    value=[""],
                    placeholder="Select a product...",
                    options=[
                        {"label": i, "value": i}
                        for i in [
                            "A320",
                            "A330",
                            "New product...",
                        ]
                    ],
                    multi=True,
                    id="Product-dropdown",
                ),
                spacing(),
                html.Div(
                    [
                        "Picture name: ",
                        dcc.Input(id="my-input", value="", type="text"),
                    ]
                ),
                spacing(),
                html.Div(id="my-output"),
                dcc.Upload(
                    id="upload-image",
                    children=html.Div(["Drag and Drop or ", html.A("Select picture")]),
                    style={
                        "width": "100%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "margin": "10px",
                    },
                    # Allow multiple files to be uploaded
                    multiple=True,
                ),
                spacing(),
                dcc.Upload(
                    className="four columns",
                    id="upload-coa",
                    children=html.Div(["Drag and Drop or ", html.A("Select PDF")]),
                    style={
                        "width": "45%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "margin": "10px",
                    },
                    # Allow multiple files to be uploaded
                    multiple=False,
                ),
            ],
        ),
        html.Hr(),
        html.Div(id="output-coa"),
    ]
)

# region Callbacks
@app.callback(Output("output", "children"), [Input("OEM-dropdown", "value")])
def display_output(value):
    return str(value)


@app.callback(
    Output(component_id="my-output", component_property="children"),
    Input(component_id="my-input", component_property="value"),
)
def update_output_div(input_value):
    return f"Output: {input_value}"


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
        children = [parse_coa_contents(list_of_contents, list_of_names, list_of_dates)]
        return children


# endregion

if __name__ == "__main__":
    app.run_server(debug=True)
