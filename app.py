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
    html.Div(className="loading-line", id="loading-line"),

    html.H1("Scraping MELI - Francisco", style={'textAlign': 'center', 'color': '#ffffff'}),

    html.Div([
        html.Div(id="total-models", className="info-box"),
        html.Div(id="catalog-items", className="info-box"),
        html.Div(id="total-products", className="info-box"),
        html.Div(id="seller-count", className="info-box"),
        html.Div(id="blue-dollar", className="info-box"),
    ], className="info-container", style={'display': 'flex', 'justifyContent': 'space-around', 'margin': '20px 0'}),

    html.Div([
        dcc.Input(id="input-producto", type="text", placeholder="Ingrese un producto", className="search-bar",
                  style={'width': '60%', 'padding': '10px'}),
        html.Button("Buscar", id="search-button", n_clicks=0, className="search-button",
                    style={'padding': '10px 20px'}),
    ], className="search-container", style={'textAlign': 'center', 'margin': '20px 0'}),

    html.Div(id="output-message",
             style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif', 'fontSize': '20px'}),

    html.Div(id="output-table-container", children=[
        html.H2("Resultados de la Búsqueda",
                style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif',
                       'fontSize': '28px'}),
        html.Div(id="output-table", style={'margin-top': '20px', 'padding': '20px'}),
        html.Button("Exportar a Excel", id="export-button", n_clicks=0, className="export-button"),
        dcc.Download(id="download-link")
    ], style={'display': 'none'}),

    html.Div(id="output-seller-container", children=[
        html.H2("Recuento de Vendedores",
                style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif',
                       'marginTop': '50px', 'fontSize': '28px'}),
        html.Div(id="output-seller-table", style={'margin-top': '20px', 'padding': '20px'}),
    ], style={'display': 'none'}),

    # Selector para alternar entre gráficos, inicialmente oculto
    html.Div(id="graph-selector-container", children=[
        html.H2("Selecciona el gráfico que deseas ver",
                style={'textAlign': 'center', 'color': '#ffffff', 'fontFamily': 'Roboto, sans-serif', 'fontSize': '24px'}),
        dcc.RadioItems(
            id="graph-selector",
            options=[
                {"label": "Histograma de Precios", "value": "histogram"},
                {"label": "Box Plot de Precios", "value": "boxplot"},
                {"label": "Productos por Categoría", "value": "barchart"}
            ],
            value="histogram",  # Valor por defecto
            labelStyle={'display': 'inline-block', 'color': '#ffffff', 'marginRight': '10px'},
            style={'textAlign': 'center', 'color': '#ffffff'}
        ),
    ], style={'textAlign': 'center', 'margin': '20px 0', 'display': 'none'}),  # Inicialmente oculto

    # Contenedor del gráfico
    html.Div(id="output-graph-container", children=[
        html.Div(id="output-graph", style={'margin-top': '20px'}),
    ], style={'display': 'none'})

], style={'fontFamily': 'Roboto, sans-serif', 'backgroundColor': '#1e1e1e', 'padding': '40px'})

def get_current_blue_dollar():
    try:
        response = requests.get("https://dolarapi.com/v1/dolares/blue")
        data = response.json()
        blue_dollar_sale = data.get("venta", "N/A")  # Obtener el valor de venta
        return blue_dollar_sale
    except Exception as e:
        logging.error(f"Error al obtener la cotización del dólar blue: {e}")
        return "N/A"



@app.callback(
    [Output("output-message", "children"),
     Output("output-table-container", "style"),
     Output("output-table", "children"),
     Output("output-seller-container", "style"),
     Output("output-seller-table", "children"),
     Output("output-graph-container", "style"),
     Output("output-graph", "children"),
     Output("download-link", "data"),
     Output("total-models", "children"),
     Output("catalog-items", "children"),
     Output("total-products", "children"),
     Output("seller-count", "children"),
     Output("loading-line", "style"),
     Output("blue-dollar", "children"),
     Output("graph-selector-container", "style")],  # Nuevo Output para controlar la visibilidad del selector de gráficos
    [Input("search-button", "n_clicks"),
     Input("input-producto", "value"),
     Input("export-button", "n_clicks"),
     Input("graph-selector", "value")]
)
def update_table_and_graph(n_clicks, producto, export_clicks, graph_type):
    if n_clicks > 0:
        try:
            logging.info(f"Buscando producto: {producto}")
            data = fetch_data(producto)

            # Ajuste para acceder correctamente a los resultados
            results = data.get('results', [])

            if isinstance(results, list) and len(results) > 0:
                logging.info(f"Datos válidos obtenidos: {len(results)} ítems")
                df, min_price, mid_price, max_price = prepare_data(results)
                seller_df = prepare_seller_data(results)

                # Contadores actualizados
                total_models = df["Modelo"].nunique()
                catalog_items = len([item for item in results if item.get("catalog_listing")])
                total_products = len(results)
                seller_count = seller_df["Vendedor"].nunique()

                # Obtener la cotización actual del dólar blue
                blue_dollar = get_current_blue_dollar()

                # Calcular estadísticas adicionales
                mean_price = df["Precio en ARS"].mean()
                median_price = df["Precio en ARS"].median()

                # Alternar gráficos basado en la selección
                if graph_type == "histogram":
                    fig = px.histogram(df, x="Precio en ARS", title="Distribución de Precios", template="plotly_dark", nbins=20)
                elif graph_type == "boxplot":
                    fig = px.box(df, y="Precio en ARS", title="Box Plot de Precios", template="plotly_dark")
                elif graph_type == "barchart":
                    # Asegurarse de que la columna "Categoría" esté presente
                    if "Categoría" in df.columns:
                        categoria_df = df.groupby("Categoría").size().reset_index(name="Cantidad")
                        fig = px.bar(categoria_df, x="Categoría", y="Cantidad", title="Productos por Categoría", template="plotly_dark")
                    else:
                        fig = None  # En caso de no tener datos, evitamos pasar un gráfico vacío

                # Si es histograma o boxplot, agregar líneas de referencia para promedio y mediana
                if fig and graph_type in ["histogram", "boxplot"]:
                    fig.add_vline(x=mean_price, line_dash="dash", line_color="green", annotation_text=f"Promedio: ARS {mean_price:,.2f}")
                    fig.add_vline(x=median_price, line_dash="dot", line_color="orange", annotation_text=f"Mediana: ARS {median_price:,.2f}")

                # Condiciones para colorear las filas de la tabla según precios
                style_data_conditional = [
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#3a3a3a',
                    },
                    {
                        'if': {'row_index': 'even'},
                        'backgroundColor': '#2e2e2e',
                    },
                    {
                        'if': {'column_id': 'Precio', 'filter_query': f'{{Precio en ARS}} <= {mid_price}'},
                        'backgroundColor': '#285d6b',
                        'color': '#ffffff',
                    },
                    {
                        'if': {'column_id': 'Precio', 'filter_query': f'{{Precio en ARS}} > {mid_price} && {{Precio en ARS}} < {max_price}'},
                        'backgroundColor': '#396f59',
                        'color': '#ffffff',
                    },
                    {
                        'if': {'column_id': 'Precio', 'filter_query': f'{{Precio en ARS}} >= {max_price}'},
                        'backgroundColor': '#995b50',
                        'color': '#ffffff',
                    },
                    {
                        'if': {'filter_query': '{Moneda} = USD', 'column_id': 'Precio'},
                        'color': '#A3E4D7',
                        'fontWeight': 'bold',
                    },
                    {
                        'if': {'filter_query': '{Moneda} = ARS', 'column_id': 'Precio'},
                        'color': '#AEDFF7',
                        'fontWeight': 'bold',
                    },
                ]

                # Tabla de datos de productos con categoría
                table = dash_table.DataTable(
                    data=df.to_dict("records"),
                    columns=[
                        {"name": "Imagen", "id": "Imagen", "presentation": "markdown"},
                        {"name": "Artículo", "id": "Artículo"},
                        {"name": "Categoría", "id": "Categoría"},  # Nueva columna de categoría
                        {"name": "Marca", "id": "Marca"},
                        {"name": "Modelo", "id": "Modelo"},
                        {"name": "Condición", "id": "Condición"},
                        {"name": "SKU", "id": "SKU"},
                        {"name": "Precio", "id": "Precio"},
                        {"name": "Stock Disponible", "id": "Stock Disponible"},
                        {"name": "Cantidad Vendida", "id": "Cantidad Vendida"},
                        {"name": "Envío Gratis", "id": "Envío Gratis", "presentation": "markdown"},
                        {"name": "FULL", "id": "FULL", "presentation": "markdown"},
                        {"name": "Vendedor", "id": "Vendedor"},
                        {"name": "Tipo de Publicación", "id": "Tipo de Publicación"},
                        {"name": "Publicación en Catálogo", "id": "Publicación en Catálogo"},
                        {"name": "Url", "id": "Ver en MercadoLibre", "presentation": "markdown"},
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
                    style_data_conditional=style_data_conditional,
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

                # MODIFICACIÓN DE RECUENTO DE VENDEDORES (gráfico + tabla)
                total_articulos = seller_df['Cantidad de Artículos'].sum()

                # Cálculo de porcentaje de artículos por vendedor
                seller_df['Porcentaje'] = (seller_df['Cantidad de Artículos'] / total_articulos) * 100

                # Gráfico de torta
                fig_pie = px.pie(seller_df, names="Vendedor", values="Cantidad de Artículos", title="Distribución por Vendedores",
                                 hole=0.3, template="plotly_dark")

                # Tabla de vendedores con porcentaje y heatmap
                style_data_conditional_seller = [
                    {
                        'if': {'filter_query': f'{{Porcentaje}} >= 50', 'column_id': 'Porcentaje'},
                        'backgroundColor': '#ff595e',
                        'color': 'white',
                    },
                    {
                        'if': {'filter_query': f'{{Porcentaje}} >= 25 && {{Porcentaje}} < 50', 'column_id': 'Porcentaje'},
                        'backgroundColor': '#ffca3a',
                        'color': 'white',
                    },
                    {
                        'if': {'filter_query': f'{{Porcentaje}} < 25', 'column_id': 'Porcentaje'},
                        'backgroundColor': '#1982c4',
                        'color': 'white',
                    },
                ]

                # Tabla de vendedores
                seller_table_with_percentage = dash_table.DataTable(
                    data=seller_df.to_dict("records"),
                    columns=[
                        {"name": "Vendedor", "id": "Vendedor"},
                        {"name": "Cantidad de Artículos", "id": "Cantidad de Artículos"},
                        {"name": "Porcentaje (%)", "id": "Porcentaje", "type": "numeric", "format": {'specifier': '.2f'}}
                    ],
                    style_data_conditional=style_data_conditional_seller,
                    style_cell={
                        'padding': '10px',
                        'textAlign': 'left',
                        'backgroundColor': '#1e1e1e',
                        'color': '#ffffff'
                    },
                    style_header={
                        'backgroundColor': '#444',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'textAlign': 'center'
                    },
                    style_table={'overflowX': 'auto', 'minWidth': '100%', 'maxWidth': '100%'},
                    page_size=10,
                )

                # Crear layout dividido: gráfico a la izquierda, tabla a la derecha
                seller_section = html.Div([
                    html.Div(dcc.Graph(figure=fig_pie),
                             style={'width': '45%', 'display': 'inline-block', 'paddingRight': '20px'}),
                    # Añadir paddingRight
                    html.Div(seller_table_with_percentage,
                             style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top',
                                    'paddingLeft': '20px'})  # Añadir paddingLeft
                ])

                # Mostrar el selector de gráficos solo si hay resultados
                return ("Datos cargados correctamente.",
                        {'display': 'block'},
                        table,
                        {'display': 'block'},
                        seller_section,  # Usar el nuevo layout con gráfico + tabla
                        {'display': 'block'},
                        dcc.Graph(figure=fig) if fig else "No se encontraron datos para el gráfico.",
                        None,
                        f"Cantidad de Modelos listados: {total_models}",
                        f"Modelos con publicación de catálogo existente: {catalog_items}",
                        f"Cantidad de productos publicados: {total_products}",
                        f"Vendedores: {seller_count}",
                        {'display': 'none'},  # Ocultar la línea de carga
                        f"Cotización Dólar Blue Venta: {blue_dollar} ARS",
                        {'display': 'block'})  # Mostrar el selector de gráficos

            else:
                logging.warning("No se encontraron resultados en la búsqueda.")
                logging.info(f"Resultados obtenidos: {results}")
                return ["No se encontraron resultados.",
                        {'display': 'none'}, None,
                        {'display': 'none'}, None,
                        {'display': 'none'}, None,
                        None, None, None, None, None, None, None, {'display': 'none'}]
        except Exception as e:
            logging.error(f"Error durante la obtención de datos: {str(e)}")
            return [f"Error al obtener datos: {str(e)}",
                    {'display': 'none'}, None,
                    {'display': 'none'}, None,
                    {'display': 'none'}, None,
                    None, None, None, None, None, None, None, {'display': 'none'}]
    raise exceptions.PreventUpdate



def fetch_data(producto):
    url = f"http://127.0.0.1:8000/scrape?producto={producto}"
    logging.info(f"Haciendo solicitud a la URL: {url}")
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    logging.info(f"Datos obtenidos: {data}")  # Verifica los datos obtenidos
    return data


def get_dolar_blue_cotizacion():
    try:
        response = requests.get("https://dolarapi.com/v1/dolares/blue")
        data = response.json()
        return data.get("venta", 0)  # Usamos el valor de venta del dólar blue
    except Exception as e:
        logging.error(f"Error al obtener la cotización del dólar blue: {e}")
        return 0  # Devolver 0 o algún valor por defecto en caso de error


def prepare_data(results):
    rows = []
    dolar_blue_cotizacion = get_dolar_blue_cotizacion()
    logging.info(f"Cotización del dólar blue obtenida: AR$ {dolar_blue_cotizacion}")

    for index, result in enumerate(results):
        logging.info(f"Procesando resultado #{index + 1}: {result}")

        if not isinstance(result, dict):
            logging.error(f"Se esperaba un diccionario en 'result', pero se recibió: {type(result)}")
            continue

        attributes = result.get("attributes", [])
        if not isinstance(attributes, list):
            logging.error(f"Esperaba una lista de atributos, pero obtuve: {type(attributes)} - {attributes}")
            continue

        title = result.get("title", "Título no disponible")
        brand = "Marca no disponible"
        model = "Modelo no disponible"
        sku = "SKU no disponible"

        # Extraer la categoría del producto del campo domain_id
        domain_id = result.get("domain_id", "")
        categoria = domain_id.split("-")[-1] if "-" in domain_id else "Categoría desconocida"

        for attr in attributes:
            if isinstance(attr, dict):
                if attr.get("id") == "BRAND":
                    brand = attr.get("value_name", "Marca no disponible")
                elif attr.get("id") in ["MODEL", "ALPHANUMERIC_MODEL"]:
                    model = attr.get("value_name", "Modelo no disponible")
                elif attr.get("id") == "ALPHANUMERIC_MODEL":
                    sku = attr.get("value_name", "SKU no disponible")
            else:
                logging.error(f"El atributo no es un diccionario: {attr}")

        shipping = result.get("shipping", {})
        if isinstance(shipping, dict):
            free_shipping = "🚚" if shipping.get("free_shipping") else "❌"
            full = "📦" if "fulfillment" in shipping.get("tags", []) else "❌"
        else:
            logging.error(f"'shipping' no es un diccionario: {type(shipping)} - {shipping}")
            free_shipping = "❌"
            full = "❌"

        seller = result.get("seller", {})
        if isinstance(seller, dict):
            seller_name = seller.get("nickname", "Desconocido")
        else:
            logging.error(f"'seller' no es un diccionario: {type(seller)} - {seller}")
            seller_name = "Desconocido"

        listing_type = result.get("listing_type_id", "Tipo no disponible")

        catalog_listing = "✅" if result.get("catalog_listing") else "❌"

        image_url = result.get("thumbnail", "https://via.placeholder.com/150")
        permalink = result.get("permalink", "#")

        image_md = f"![Image]({image_url})"

        currency = result.get("currency_id", "ARS")

        price_in_ars = result.get('price', 0)
        if currency == "USD":
            price_in_ars *= dolar_blue_cotizacion

        rows.append({
            "Imagen": image_md,
            "Artículo": title,
            "Categoría": categoria,  # Ahora se añade correctamente la categoría
            "Marca": brand,
            "Modelo": model,
            "Condición": "Nuevo" if result.get("condition", "new") == "new" else "Usado",
            "SKU": sku,
            "Precio": result.get('price', 0),
            "Moneda": currency,
            "Precio en ARS": price_in_ars,
            "Stock Disponible": result.get("available_quantity", "No disponible"),
            "Cantidad Vendida": result.get("sold_quantity", "No disponible"),
            "Envío Gratis": free_shipping,
            "FULL": full,
            "Vendedor": seller_name,
            "Tipo de Publicación": listing_type,
            "Publicación en Catálogo": catalog_listing,
            "Ver en MercadoLibre": f"[Link]({permalink})"
        })

    if not rows:
        logging.warning("No se pudieron preparar filas para los datos obtenidos.")

    df = pd.DataFrame(rows)
    df["Precio en ARS"] = pd.to_numeric(df["Precio en ARS"])

    min_price = df["Precio en ARS"].min()
    max_price = df["Precio en ARS"].max()
    mid_price = (min_price + max_price) / 2

    df = df.sort_values(by=["Precio en ARS"], ascending=True).reset_index(drop=True)
    df["Precio"] = df.apply(lambda x: f"{'AR$' if x['Moneda'] == 'ARS' else 'USD'} {x['Precio']:,.2f}", axis=1)

    return df, min_price, mid_price, max_price


def prepare_seller_data(results):
    seller_counts = {}

    for result in results:
        seller = result.get("seller", {}).get("nickname", "Desconocido")  # Obtener el nickname del vendedor
        seller_reputation = result.get("seller", {}).get("seller_reputation", {}).get("level_id", "Sin categoría")

        if seller in seller_counts:
            seller_counts[seller]['count'] += 1
        else:
            seller_counts[seller] = {
                'count': 1,
                'type': seller_reputation
            }

    seller_df = pd.DataFrame([
        {
            "Vendedor": seller,
            "Cantidad de Artículos": info['count'],
        }
        for seller, info in seller_counts.items()
    ])
    seller_df = seller_df.sort_values(by="Cantidad de Artículos", ascending=False).reset_index(drop=True)
    return seller_df


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
