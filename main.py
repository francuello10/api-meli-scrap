import requests
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import logging
import json

app = FastAPI()

logging.basicConfig(level=logging.INFO)

@app.get("/scrape", response_class=JSONResponse)
async def scrape(
        producto: str,
        estado: str = None,
        ano: int = None
):
    search_query = f"{producto}"
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={search_query}"

    if estado:
        url += f"&condition={estado}"

    if ano:
        url += f"&year={ano}"

    logging.info(f"Fetching data from URL: {url}")

    response = requests.get(url)
    logging.info(f"Status code: {response.status_code}")

    if response.status_code != 200:
        logging.error(f"Error al obtener datos de MercadoLibre: {response.text}")
        return JSONResponse({"error": "Error al obtener datos de MercadoLibre"}, status_code=500)

    try:
        # Obtener los productos desde 'results' en la respuesta de la API de Mercado Libre
        data = response.json()

        # Verifica la estructura de los datos antes de procesarlos
        logging.info(f"Estructura de los datos recibidos: {type(data)}")
        logging.info(f"Ejemplo de datos recibidos: {json.dumps(data, indent=2, ensure_ascii=False)}")

        products = data.get("results", [])
        if not isinstance(products, list):
            logging.error(f"'results' no es una lista: {type(products)}")
            return JSONResponse({"error": "'results' no es una lista"}, status_code=500)

        # Log de cada producto individualmente
        for index, product in enumerate(products):
            if not isinstance(product, dict):
                logging.error(f"El producto en la posición {index} no es un diccionario: {type(product)}")
                continue
            logging.info(f"Producto {index + 1}: {json.dumps(product, indent=2, ensure_ascii=False)}")

        # Asegúrate de devolver solo la lista de productos
        return JSONResponse({"results": products})

    except Exception as e:
        logging.error(f"Error procesando los datos: {str(e)}")
        return JSONResponse({"error": "Error procesando los datos"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
