from .scraping_bistek import guardar_precios_bistek
from .scraping_stockcenter import guardar_productos_stock_center
from .scraping_baggio import guardar_precios_baggio
from .scraping_asun import obtener_y_guardar_ofertas_asun
from .scraping_bigjoia import guardar_precios_bigjoia


# Primera parte: Stock Center y Asun
def ejecutar_scraping_parte1():
    ejecutar_scraping_stockcenter()
    ejecutar_scraping_asun()


# Segunda parte: Big Joia
def ejecutar_scraping_parte2():
    ejecutar_scraping_bigjoia()


# Tercera parte: Baggio
def ejecutar_scraping_parte3():
    ejecutar_scraping_baggio()


# Cuarta parte: Bistek
def ejecutar_scraping_parte4():
    ejecutar_scraping_bistek()


# Funciones para cada supermercado individual
def ejecutar_scraping_stockcenter():
    guardar_productos_stock_center()


def ejecutar_scraping_asun():
    obtener_y_guardar_ofertas_asun()


def ejecutar_scraping_bigjoia():
    guardar_precios_bigjoia()


def ejecutar_scraping_baggio():
    guardar_precios_baggio()


def ejecutar_scraping_bistek():
    guardar_precios_bistek()


# Si deseas ejecutar todas las partes juntas, puedes hacerlo llamando a cada una por separado
def ejecutar_scraping():
    ejecutar_scraping_parte1()  # Ejecutar Stock Center y Asun
    ejecutar_scraping_parte2()  # Ejecutar Big Joia
    ejecutar_scraping_parte3()  # Ejecutar Baggio
    ejecutar_scraping_parte4()  # Ejecutar Bistek
