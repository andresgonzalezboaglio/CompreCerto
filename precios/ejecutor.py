from .scraping_bistek import guardar_precios_bistek
from .scraping_stockcenter import guardar_productos_stock_center


def ejecutar_scraping_bistek():
    guardar_precios_bistek()


def ejecutar_scraping_stockcenter():
    guardar_productos_stock_center()


def ejecutar_scraping():
    ejecutar_scraping_bistek()
    ejecutar_scraping_stockcenter()

