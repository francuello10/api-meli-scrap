import dash
from dash import dcc, html, Input, Output, dash_table, ctx, exceptions
import pandas as pd
import requests
import io
import plotly.express as px
import logging

logging.basicConfig(level=logging.INFO)

app = dash.Dash(__name__)
app.title = "Scraping-MELI"
app._favicon = "meli-dev.png"

app.layout = html.Div([
    # Cuadros de recuento
    html.Div([
        html.Div(id="total-products", className="info-box cool-box", style={'color': 'white'}),
        html.Div(id="seller-count", className="info-box cool-box", style={'color': 'white'}),
        html.Div(id="catalog-items", className="info-box cool-box", style={'color': 'white'}),
        html.Div(id="average-price", className="info-box cool-box", style={'color': 'white'}),
    ], className="info-container", style={
        'display': 'flex',
        'justifyContent': 'space-around',
        'margin': '20px 0',
        'padding': '10px',
        'border-radius': '10px',
        'box-shadow': '0px 4px 6px rgba(0, 0, 0, 0.1)'
    }),

    # Barra de búsqueda centrada y ancha
    html.Div([
        dcc.Input(id="input-producto", type="text", placeholder="Ingrese un producto", className="search-bar",
                  style={'width': '60%', 'padding': '15px', 'fontSize': '18px', 'border-radius': '10px'}),
        dcc.Dropdown(id='estado-filter', placeholder='Estado',
                     options=[{'label': 'Nuevo', 'value': 'new'},
                              {'label': 'Usado', 'value': 'used'}],
                     style={'width': '15%', 'display': 'inline-block', 'border-radius': '10px'}),
        dcc.Dropdown(id='marca-filter', placeholder='Marca',
                     style={'width': '15%', 'display': 'inline-block', 'border-radius': '10px', 'disabled': True}),
        dcc.Dropdown(id='categoria-filter', placeholder='Categoría',
                     style={'width': '15%', 'display': 'inline-block', 'border-radius': '10px', 'disabled': True}),
        html.Button("Buscar", id="search-button", n_clicks=0, className="search-button",
                    style={'padding': '10px 20px', 'width': '10%', 'border-radius': '10px', 'backgroundColor': '#ff6f61'}),
    ], className="search-container", style={'textAlign': 'center', 'margin': '20px 0'}),

    # Mensaje de salida
    html.Div(id="output-message",
             style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif', 'fontSize': '20px'}),

    # Contenedor de la tabla de resultados
    html.Div(id="output-table-container", children=[
        html.H2("Resultados de la Búsqueda",
                style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif',
                       'fontSize': '28px'}),
        html.Div(id="output-table", style={'margin-top': '20px', 'padding': '20px'}),
        html.Button("Exportar a Excel", id="export-button", n_clicks=0, className="export-button"),
        dcc.Download(id="download-link")
    ], style={'display': 'none'}),

    # Contenedor de la tabla de recuento por vendedores
    html.Div(id="output-seller-container", children=[
        html.H2("Recuento de Publicaciones por Vendedor",
                style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif',
                       'marginTop': '50px', 'fontSize': '28px'}),
        html.Div(id="output-seller-table", style={'margin-top': '20px', 'padding': '20px'}),
    ], style={'display': 'none'}),
    
    # Contenedor del gráfico de distribución de precios
    html.Div(id="output-graph-container", children=[
        html.H2("Distribución de Precios",
                style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif',
                       'marginTop': '50px', 'fontSize': '28px'}),
        html.Div(id="output-graph", style={'margin-top': '20px'}),
    ], style={'display': 'none'}),
], style={'fontFamily': 'Roboto, sans-serif', 'backgroundColor': '#1e1e1e', 'padding': '40px'})


@app.callback(
    # Output
    [
        Output("output-message", "children"),
        Output("output-table-container", "style"),
        Output("output-table", "children"),
        Output("output-seller-container", "style"),
        Output("output-seller-table", "children"),
        Output("output-graph-container", "style"),
        Output("output-graph", "children"),
        Output("download-link", "data"),
        Output("total-products", "children"),
        Output("seller-count", "children"),
        Output("catalog-items", "children"),
        Output("average-price", "children"),
        Output("marca-filter", "disabled"),
        Output("categoria-filter", "disabled")
    ],
    # Input
    [
        Input("search-button", "n_clicks"),
        Input("input-producto", "value"),
        Input("export-button", "n_clicks"),
        Input("estado-filter", "value"),
        Input("marca-filter", "value"),
        Input("categoria-filter", "value")
    ]
)
def update_table_and_graph(n_clicks, producto, export_clicks, estado, marca, categoria):
    if n_clicks > 0:
        try:
            # Código principal dentro de try
            logging.info(f"Buscando producto: {producto}")
            df, precio_promedio = fetch_data(producto, estado, marca, categoria)

            # Verificar la integridad del DataFrame y el cálculo de precios
            logging.info(f"Tipos de datos en DataFrame:\n{df.dtypes}")
            logging.info(f"DataFrame:\n{df.head()}")

            # Asegurarse de que el precio promedio es un número válido
            logging.info(f"Precio promedio: {precio_promedio}")

            # Agrega logs para revisar el contenido de 'df'
            logging.info(f"DataFrame:\n{df.head()}")
            logging.info(f"Precio promedio: {precio_promedio}")

            # Limitar resultados a 50 y añadir recuento de cuántos se están mostrando
            df = df.head(50)
            product_count_display = f"{len(df)}/50"

            # Preparar los datos de vendedores
            seller_df = prepare_seller_data(df)

            total_models = df["Modelo"].nunique()
            catalog_items = len([item for item in df['Publicación en Catálogo'] if item == "✔"])
            total_products = len(df)
            seller_count = seller_df["Vendedor"].nunique()

            # Habilitar los filtros de marca y categoría
            enable_filters = False if total_products == 0 else True

            # Tabla de recuento por vendedores
            seller_df['Porcentaje'] = (seller_df['Cantidad de Artículos'] / total_products) * 100
            seller_df['heatmap_color'] = seller_df['Porcentaje'].apply(lambda x: f"rgba(255,0,0,{x/100:.2f})")

            seller_table = dash_table.DataTable(
                data=seller_df.to_dict('records'),
                columns=[
                    {"name": "Vendedor", "id": "Vendedor"},
                    {"name": "Cantidad de Artículos", "id": "Cantidad de Artículos"},
                    {"name": "Porcentaje", "id": "Porcentaje"},
                    {"name": "Tipo de Vendedor", "id": "Tipo de Vendedor"}
                ],
                style_cell={
                    'padding': '10px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    'textAlign': 'left',
                    'fontFamily': 'Roboto, sans-serif',
                    'backgroundColor': '#1e1e1e',
                    'color': '#ffffff'
                },
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Porcentaje'},
                        'backgroundColor': seller_df['heatmap_color'],
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                ],
                style_header={
                    'backgroundColor': '#444',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_table={'overflowX': 'auto', 'minWidth': '100%', 'maxWidth': '100%'},
                row_deletable=False,
                editable=False,
                sort_action="native",
                filter_action="native",
                row_selectable="multi",
                selected_rows=[],
                page_size=10,
                style_as_list_view=True
            )

            # Tabla de productos
            table = dash_table.DataTable(
                data=df.to_dict("records"),
                columns=[
                    {"name": "Imagen", "id": "Imagen", "presentation": "markdown"},
                    {"name": "Artículo", "id": "Artículo"},
                    {"name": "Marca", "id": "Marca"},
                    {"name": "Modelo", "id": "Modelo"},
                    {"name": "SKU", "id": "SKU"},
                    {"name": "Precio", "id": "Precio", "type": "numeric"},
                    {"name": "Stock Disponible", "id": "Stock Disponible"},
                    {"name": "Cantidad Vendida", "id": "Cantidad Vendida"},
                    {"name": "Envío Gratis", "id": "Envío Gratis"},
                    {"name": "FULL", "id": "FULL"},
                    {"name": "Vendedor", "id": "Vendedor"},
                    {"name": "Calificación del Vendedor", "id": "Reputación del Vendedor"},
                    {"name": "Tipo de Publicación", "id": "Tipo de Publicación"},
                    {"name": "Publicación en Catálogo", "id": "Publicación en Catálogo"},
                    {"name": "Url", "id": "Ver en MercadoLibre", "presentation": "markdown"},
                    {"name": "Categoría", "id": "category_id"},
                ],
                style_cell={
                    'padding': '5px',
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    'textAlign': 'left',
                    'fontFamily': 'Roboto, sans-serif',
                    'backgroundColor': '#1e1e1e',
                    'color': '#ffffff',
                    'maxWidth': '150px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                },
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Imagen'},
                        'width': '45px',
                        'height': '45px',
                        'textAlign': 'center',
                        'padding': '2px',
                        'whiteSpace': 'normal',
                        'overflow': 'hidden',
                    },
                    {
                        'if': {'column_id': 'Precio'},
                        'color': '#00FF00',
                        'fontWeight': 'bold',
                        'fontSize': '16px',
                    },
                ],
                style_header={
                    'backgroundColor': '#444',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_table={'overflowX': 'auto', 'minWidth': '100%', 'maxWidth': '100%'},
                markdown_options={'link_target': '_blank'},
                row_deletable=False,
                editable=False,
                sort_action="native",
                filter_action="native",
                row_selectable="multi",
                selected_rows=[],
                page_size=10,
                style_as_list_view=True
            )

            # Gráfico de dispersión de precios
            fig = px.scatter(df, x="Modelo", y="Precio_num", title="Dispersión de Precios",
                             color="Marca", hover_name="Artículo",
                             size="Cantidad Vendida", size_max=15, template="plotly_dark")
            fig.add_shape(type="line", x0=-0.5, x1=len(df) - 0.5, y0=precio_promedio, y1=precio_promedio, line=dict(color="Orange", width=3))

            if ctx.triggered_id == "export-button":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="Resultados")
                    seller_df.to_excel(writer, index=False, sheet_name="Recuento de Vendedores")
                data_xlsx = output.getvalue()
                return ("Datos cargados correctamente.",
                        {'display': 'block'},
                        table,
                        {'display': 'block'},
                        seller_table,
                        {'display': 'block'},
                        dcc.Graph(figure=fig),
                        dcc.send_bytes(data_xlsx, "resultados.xlsx"),
                        f"Cantidad de publicaciones listadas: {total_products}",
                        f"Cantidad de vendedores: {seller_count}",
                        f"Cantidad de publicaciones de catálogo: {catalog_items}",
                        f"Precio promedio en AR$: {precio_promedio:,.2f}",
                        {'display': 'none'},  # Ocultar la línea de carga
                        not enable_filters,  # Habilitar/Deshabilitar filtro de marca
                        not enable_filters)  # Habilitar/Deshabilitar filtro de categoría

            # Este return es para el caso en que no se presione el botón de exportación
            return (
                "Datos cargados correctamente.",
                {'display': 'block'},
                table,
                {'display': 'block'},
                seller_table,
                {'display': 'block'},
                dcc.Graph(figure=fig),
                None,
                f"Cantidad de publicaciones listadas: {len(df)}",
                f"Cantidad de vendedores: {df['Vendedor'].nunique()}",
                f"Cantidad de publicaciones de catálogo: {catalog_items}",
                f"Precio promedio en AR$: {precio_promedio:,.2f}",
                not enable_filters,
                not enable_filters
            )

        except Exception as e:
            logging.error(f"Error durante la obtención de datos: {str(e)}")
            return [
                f"Error al obtener datos: {str(e)}",
                {'display': 'none'},
                None,
                {'display': 'none'},
                None,
                {'display': 'none'},
                None,
                None,
                None,
                None,
                None,
                None,
                {'display': 'none'},
                True
            ]  # categoria-filter

    raise exceptions.PreventUpdate



def fetch_data(producto, estado=None, marca=None, categoria=None):
    url = f"http://127.0.0.1:8000/scrape?producto={producto}"
    if estado:
        url += f"&estado={estado}"
    if marca:
        url += f"&marca={marca}"
    if categoria:
        url += f"&categoria={categoria}"

    logging.info(f"Haciendo solicitud a la URL: {url}")
    response = requests.get(url)
    response.raise_for_status()

    data = response.json()
    logging.info(f"Datos obtenidos: {data}")

    results = data.get('results')
    if not isinstance(results, list):
        logging.error("Los resultados no son una lista.")
        raise ValueError("Los resultados no son una lista.")

    df = prepare_data(results)
    precio_promedio = df['Precio_num'].mean()
    logging.info(f"Precio promedio calculado: {precio_promedio}")

    return df, precio_promedio


def prepare_data(results):
    rows = []
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            logging.error(f"El resultado en la posición {i} no es un diccionario: {result}")
            continue

        try:
            # Extracción de datos relevantes
            articulo = result.get("title", "Título no disponible")
            price = result.get("price", 0)
            currency_id = result.get("currency_id", "ARS")

            if currency_id == "USD":
                price_formatted = f"USD {price:,.2f}"
            else:
                price_formatted = f"AR$ {price:,.2f}"

            # Información del vendedor
            seller_info = result.get("seller", {})
            seller = seller_info.get("nickname", "Desconocido")
            reputacion_vendedor = seller_info.get("seller_reputation", {}).get("level_id", "Sin categoría")

            # Información del modelo, SKU, y marca
            attributes = result.get("attributes", [])
            model = "Modelo no disponible"
            sku = "SKU no disponible"
            marca = "Marca no disponible"

            for attr in attributes:
                if attr.get("id") == "MODEL":
                    model = attr.get("value_name", "Modelo no disponible")
                elif attr.get("id") == "ALPHANUMERIC_MODEL":
                    sku = attr.get("value_name", "SKU no disponible")
                elif attr.get("id") == "BRAND":
                    marca = attr.get("value_name", "Marca no disponible")

            # Publicación en Catálogo
            catalog_listing = result.get("catalog_listing", False)

            # Cantidad Vendida y Stock Disponible
            cantidad_vendida = result.get("sold_quantity", 0)
            stock_disponible = result.get("available_quantity", "No disponible")

            # Envío Gratis y FULL
            envio_gratis = "✔" if result.get("shipping", {}).get("free_shipping") else "✖"
            full = "✔" if "fulfillment" in result.get("shipping", {}).get("tags", []) else "✖"

            # Tipo de Publicación
            tipo_publicacion = result.get("listing_type_id", "Tipo no disponible")

            # Permalink y Categoría
            permalink = result.get("permalink", "#")
            category_id = result.get("category_id", "Sin categoría")

            # Imagen (Thumbnail)
            image_url = result.get("thumbnail", "https://via.placeholder.com/150")
            image_md = f"![Image]({image_url})"  # Markdown para previsualización

            # Agregando fila a la lista de filas
            rows.append({
                "Artículo": articulo,
                "Precio": price_formatted,
                "Precio_num": float(price),
                "Vendedor": seller,
                "Reputación del Vendedor": reputacion_vendedor,
                "Modelo": model,
                "SKU": sku,
                "Marca": marca,
                "Publicación en Catálogo": "✔" if catalog_listing else "✖",
                "Cantidad Vendida": cantidad_vendida,
                "Stock Disponible": stock_disponible,
                "Envío Gratis": envio_gratis,
                "FULL": full,
                "Tipo de Publicación": tipo_publicacion,
                "Ver en MercadoLibre": f"[Link]({permalink})",
                "Categoría": category_id,
                "Imagen": image_md  # Previsualización de la imagen
            })
        except Exception as e:
            logging.error(f"Error procesando el resultado en la posición {i}: {str(e)}")
            continue

    if not rows:
        logging.error("No se encontraron filas válidas para procesar.")
        raise ValueError("No se encontraron filas válidas para procesar.")

    # Crear el DataFrame
    df = pd.DataFrame(rows)

    # Convertir la columna 'Precio_num' a numérico y asegurarse de que sea del tipo adecuado
    df['Precio_num'] = pd.to_numeric(df['Precio_num'], errors='coerce').fillna(0)

    # Convertir la columna 'Cantidad Vendida' a numérico
    df['Cantidad Vendida'] = pd.to_numeric(df['Cantidad Vendida'], errors='coerce').fillna(0)

    # Verificación de tipo de dato
    if df['Precio_num'].dtype != 'float64' or df['Cantidad Vendida'].dtype != 'float64':
        logging.error("Una o más columnas no son numéricas después de la conversión.")
        logging.info(f"Contenido de 'Precio_num':\n{df['Precio_num'].head()}")
        logging.info(f"Contenido de 'Cantidad Vendida':\n{df['Cantidad Vendida'].head()}")

    df = df.sort_values(by=["Precio_num"], ascending=True).reset_index(drop=True)

    return df



def prepare_seller_data(df):
    seller_counts = df.groupby("Vendedor").size().reset_index(name='Cantidad de Artículos')
    seller_counts = seller_counts.sort_values(by="Cantidad de Artículos", ascending=False).reset_index(drop=True)
    seller_counts['Tipo de Vendedor'] = df.groupby("Vendedor")['Reputación del Vendedor'].first().reset_index(drop=True)
    return seller_counts


if __name__ == "__main__":
    app.run_server(debug=True)
