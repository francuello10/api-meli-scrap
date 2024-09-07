import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
import json
from datetime import datetime, timedelta

app = FastAPI()

logging.basicConfig(level=logging.INFO)

# Manejar la solicitud de favicon para evitar el error 404
@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(status_code=204)

# Variables globales para almacenar el valor del dólar blue y la última actualización
dollar_blue_value = None
last_updated = None

# URL de la API de DólarAPI para obtener el valor del dólar blue
DOLLAR_API_URL = "https://dolarapi.com/v1/dolares/blue"


# Función para obtener el valor "venta" del dólar blue desde la API de DólarAPI
def fetch_dollar_blue():
    global dollar_blue_value, last_updated

    # Actualizar solo si ha pasado más de 1 hora desde la última actualización
    if last_updated is None or datetime.now() - last_updated > timedelta(hours=1):
        try:
            response = requests.get(DOLLAR_API_URL)
            data = response.json()

            # Asignamos el valor de venta del dólar blue
            dollar_blue_value = data['venta']
            last_updated = datetime.now()
            logging.info(f"Dólar Blue actualizado: {dollar_blue_value}")

        except Exception as e:
            logging.error(f"Error al obtener el valor del dólar blue: {e}")
            dollar_blue_value = None

    return dollar_blue_value


# Ruta para obtener el valor "venta" del dólar blue
@app.get("/dolar/blue", response_class=JSONResponse)
async def get_dollar_blue():
    dollar_value = fetch_dollar_blue()
    if dollar_value:
        return {"dollar_blue_sale_value": dollar_value}
    else:
        return JSONResponse({"error": "No se pudo obtener el valor del dólar blue"}, status_code=500)

@app.get("/scrape", response_class=JSONResponse)
async def scrape(producto: str, estado: str = None, ano: int = None, precio_min: float = None, precio_max: float = None, envio_gratis: bool = False):
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={producto}"

    # Filtro por estado del producto
    if estado:
        if estado in ["new", "used", "not_specified"]:  # Verificamos que el estado sea válido
            url += f"&condition={estado}"
        else:
            logging.warning(f"Estado no válido: {estado}")

    # Filtro por año (posiblemente en categorías específicas como autos)
    if ano:
        # Aquí el año es más complicado de aplicar, podrías buscar un atributo dentro del producto
        url += f"&year={ano}"

    # Filtros por precio mínimo y máximo
    if precio_min is not None:
        url += f"&price={precio_min}-"  # Precio mínimo
    if precio_max is not None:
        url += f"&price=-{precio_max}"  # Precio máximo

    # Filtro de envío gratis
    if envio_gratis:
        url += "&shipping_cost=free"

    logging.info(f"Fetching data from URL: {url}")

    # Realizamos la solicitud a la API de Mercado Libre
    response = requests.get(url)
    logging.info(f"Status code: {response.status_code}")

    if response.status_code != 200:
        logging.error(f"Error al obtener datos de MercadoLibre: {response.text}")
        return JSONResponse({"error": "Error al obtener datos de MercadoLibre"}, status_code=500)

    try:
        data = response.json()

        logging.info(f"Estructura de los datos recibidos: {type(data)}")
        logging.info(f"Ejemplo de datos recibidos: {json.dumps(data, indent=2, ensure_ascii=False)}")

        products = data.get("results", [])
        if not isinstance(products, list):
            logging.error(f"'results' no es una lista: {type(products)}")
            return JSONResponse({"error": "'results' no es una lista"}, status_code=500)

        for index, product in enumerate(products):
            logging.info(f"Producto {index + 1}: {json.dumps(product, indent=2, ensure_ascii=False)}")

        return JSONResponse({"results": products})

    except Exception as e:
        logging.error(f"Error procesando los datos: {str(e)}")
        return JSONResponse({"error": "Error procesando los datos"}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
