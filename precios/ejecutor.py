from .scraping_bistek import guardar_precios_bistek
from .scraping_stockcenter import obtener_y_guardar_ofertas_stock_center


def ejecutar_scraping_bistek():
    guardar_precios_bistek()


def ejecutar_scraping_stockcenter():
    obtener_y_guardar_ofertas_stock_center()


def ejecutar_scraping():
    ejecutar_scraping_bistek()
    ejecutar_scraping_stockcenter()

