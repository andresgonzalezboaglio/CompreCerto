from .scraping_bistek import guardar_precios_bistek
from .scraping_stockcenter import guardar_productos_stock_center
from .scraping_baggio import guardar_precios_baggio
from .scraping_asun import obtener_y_guardar_ofertas_asun
from .scraping_bigjoia import guardar_precios_bigjoia()

def ejecutar_scraping_bistek():
    guardar_precios_bistek()


def ejecutar_scraping_stockcenter():
    guardar_productos_stock_center()


def ejecutar_scraping_baggio():
    guardar_precios_baggio()


def ejecutar_scraping_asun():
    obtener_y_guardar_ofertas_asun()


def ejecutar_scraping_bigjoia():
    guardar_precios_bigjoia()


def ejecutar_scraping():
    ejecutar_scraping_asun()
    ejecutar_scraping_bistek()
    ejecutar_scraping_stockcenter()
    ejecutar_scraping_bigjoia()
    ejecutar_scraping_baggio()