import csv
from django.db import connection
from precios.models import Producto


# Función para cargar las marcas desde un archivo externo
def cargar_marcas(brands):
    marcas = set()
    with open(brands, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            # Suponiendo que cada fila tiene una marca en la primera columna
            marcas.add(row[0].strip().upper())
    return marcas


# Función para actualizar las marcas en la base de datos
def actualizar_marcas(brands):
    marcas = cargar_marcas(brands)

    for marca in marcas:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE precios_producto 
                SET marca = %s 
                WHERE nombre ILIKE %s
            """, [marca, f'%{marca}%'])

        print(f"Actualizada la marca '{marca}' en productos que contienen el nombre.")


if __name__ == "__main__":
    brands = 'brands.csv'
    actualizar_marcas(brands)
