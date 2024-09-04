import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
import json

app = FastAPI()

logging.basicConfig(level=logging.INFO)

@app.get("/scrape", response_class=JSONResponse)
async def scrape(producto: str, estado: str = None, ano: int = None):
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={producto}"

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
