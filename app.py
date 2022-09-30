import datetime
import io
import time
import os
import base64

from flask import Flask, send_from_directory
from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px

import numpy as np
import pandas as pd
from urllib.parse import quote as urlquote
from pdf2image import convert_from_bytes

from lib import o3d_h

# region pre-run and helper functions definition
def spacing():
    return html.Br()


# endregion

# region settings
# path to uploaded files:
upload_folder = (
    "C:\\Users\\eugeniobernard\\local_workspaces\\composite-repair-dashboard\\test_run"
)

if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

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


external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

# endregion

# region app layout
# Normally, Dash creates its own Flask server internally. By creating our own,
# we can create a route for downloading files directly:
server = Flask(__name__)
app = Dash(server=server, external_stylesheets=external_stylesheets)


@server.route("/download/<path:path>")
def download(path):
    """Serve a file from the upload directory."""
    return send_from_directory(upload_folder, path, as_attachment=True)


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
                    # value=[""],
                    placeholder="Select an OEM manufacture...",
                    options=[{"label": i, "value": i} for i in oems_list],
                    multi=False,
                    id="OEM-dropdown",
                ),
                spacing(),
                # Aircraft/product Selection
                dcc.Dropdown(
                    # value=[""],
                    placeholder="Select a product...",
                    options=[{"label": i, "value": i} for i in prod_list],
                    multi=False,
                    id="Product-dropdown",
                ),
                spacing(),
                # Repair Selection
                dcc.Dropdown(
                    # value=[""],
                    placeholder="Select a repair...",
                    options=[{"label": i, "value": i} for i in repairs_list],
                    multi=False,
                    id="Repair-dropdown",
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
                            # className="three.columns",
                            id="upload-image",
                            children=html.Div(
                                ["Drag and Drop or ", html.A("Select picture")]
                            ),
                            style=image_uplaod_style,
                            # Allow multiple files to be uploaded
                            multiple=True,
                            accept="image/*",
                        ),
                        dcc.Upload(
                            # className="three.columns",
                            id="upload-coa",
                            children=html.Div(
                                ["Drag and Drop or ", html.A("Select PDF")]
                            ),
                            style=pdf_uplaod_style,
                            # Allow multiple files to be uploaded
                            multiple=True,
                            accept="application/pdf",
                        ),
                        dcc.Upload(
                            id="upload-data",
                            children=html.Div(
                                ["Drag and drop or click to select a file to upload."]
                            ),
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
                            multiple=True,
                            accept=".ply, .pcd",
                        ),
                        # dcc.Upload(
                        #     # className="three.columns",
                        #     id="upload-data",
                        #     children=html.Div(
                        #         [
                        #             "Drag and Drop or ",
                        #             html.A("Select a pointcloud file"),
                        #         ]
                        #     ),
                        #     style=pdf_uplaod_style,
                        #     # Allow multiple files to be uploaded
                        #     multiple=False,
                        #     # accept=".ply, .pcd",
                        # ),
                    ],
                    style={"display": "flex"},
                    className="row",
                ),
            ],
        ),
        spacing(),
        html.H2("File List"),
        html.Ul(id="file-list"),
        spacing(),
        html.Button("Load pointcloud", id="load-pointcloud"),
        spacing(),
        html.Div(
            [
                html.Div(id="output-coa"),
                html.Div(id="output-image-upload"),
                dcc.Graph(id="pcd-render"),
            ],
            className="row",
        ),
    ]
)

# endregion

# region callbacks helper functions


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


def save_file(name, content):
    """Decode and store a file uploaded with Plotly Dash."""
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    data = content.encode("utf8").split(b";base64,")[1]
    with open(os.path.join(upload_folder, name), "wb") as fp:
        fp.write(base64.decodebytes(data))


def uploaded_files():
    """List the files in the upload directory."""
    files = []
    for filename in os.listdir(upload_folder):
        path = os.path.join(upload_folder, filename)
        if os.path.isfile(path):
            files.append(filename)
    return files


def file_download_link(filename):
    """Create a Plotly Dash 'A' element that downloads a file from the app."""
    location = "/download/{}".format(urlquote(filename))
    return html.A(filename, href=location)


# endregion

# region Callbacks
@app.callback(
    Output("picture-output-name", "children"),
    Input("picture-input-name", "value"),
)
def update_output_div(input_value):
    return f"Output: {input_value}"


@app.callback(
    Output("file-list", "children"),
    [Input("upload-data", "filename"), Input("upload-data", "contents")],
)
def update_output(uploaded_filenames, uploaded_file_contents):
    """Save uploaded files and regenerate the file list."""

    if uploaded_filenames is not None and uploaded_file_contents is not None:
        for name, data in zip(uploaded_filenames, uploaded_file_contents):
            save_file(name, data)

    files = uploaded_files()
    if len(files) == 0:
        return [html.Li("No files yet!")]
    else:
        return [html.Li(file_download_link(filename)) for filename in files]


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


@app.callback(
    Output("pcd-render", "figure"),
    Input("load-pointcloud", "n_clicks"),
)
def render_pcd(btn_click):
    filename = uploaded_files()
    if len(filename) == 0:
        return go.Figure()
    pcd = o3d_h.load_ply(os.path.join(upload_folder, filename[0]))

    if pcd.is_empty():
        exit()

    o3d_h.estimate_normals(pcd, 0.1)

    points = np.asarray(pcd.points)

    colors = None
    if pcd.has_colors():
        colors = np.asarray(pcd.colors)
    elif pcd.has_normals():
        colors = (0.5, 0.5, 0.5) + np.asarray(pcd.normals) * 0.5

    pcd.paint_uniform_color((1.0, 0.0, 0.0))
    colors = np.asarray(pcd.colors)

    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=points[:, 0],
                y=points[:, 1],
                z=points[:, 2],
                mode="markers",
                marker=dict(size=1, color=colors),
            )
        ],
        layout=dict(
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
            )
        ),
    )
    return fig


# endregion

if __name__ == "__main__":
    app.run_server(debug=True)
