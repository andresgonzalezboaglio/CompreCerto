import requests
from .models import Producto, Producto_Hist, Supermercado
from urllib.parse import quote_plus
from django.utils import timezone
import json
from bs4 import BeautifulSoup
import re


# Función para extraer cantidad y unidad de medida del nombre del producto
def extraer_peso_y_unidad(nombre_producto):
    if nombre_producto:  # Verificar si el nombre del producto no es None
        # Buscar cantidad seguida o separada de la unidad de medida (g, kg, ml, l, litro, unid, etc.)
        match = re.search(r'(\d+)\s*(g|kg|ml|l|litro|unid|u)', nombre_producto.lower())
        if match:
            cantidad = match.group(1)  # Captura la cantidad
            unidad_medida = match.group(2)  # Captura la unidad de medida
            return float(cantidad), unidad_medida
    return None, None


# Función para obtener precios de Bistek desde el HTML
def obtener_precios_bistek(searchTerm):
    encoded_term = quote_plus(searchTerm)
    url = f'https://www.bistek.com.br/{encoded_term}?map=ft'

    productos_extraidos = []
    pagina_actual = 1

    while True:
        response = requests.get(f"{url}&page={pagina_actual}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            script_tags = soup.find_all('script')

            for i, script_tag in enumerate(script_tags):
                try:
                    data = json.loads(script_tag.string)

                    if 'itemListElement' in data:
                        productos = data.get('itemListElement', [])

                        if not productos:
                            print(f"No hay más productos en la página {pagina_actual} para {searchTerm}.")
                            break

                        for item in productos:
                            producto = item.get('item', {})
                            nombre = producto.get('name')
                            marca = producto.get('brand', {}).get('name')
                            precio = producto.get('offers', {}).get('lowPrice')
                            id_origen = producto.get('sku')

                            # Extraer cantidad y unidad de medida del nombre
                            cantidad, unidad_medida = extraer_peso_y_unidad(nombre)

                            if nombre and precio:
                                productos_extraidos.append({
                                    'nombre': nombre,
                                    'marca': marca or "Sin marca",
                                    'precio': float(precio),
                                    'id_origen': id_origen,
                                    'cantidad': cantidad,
                                    'unidad_medida': unidad_medida
                                })

                        next_link = soup.find('link', {'rel': 'next'})
                        if next_link:
                            pagina_actual += 1
                        else:
                            print(f"Alcanzada la última página ({pagina_actual}) para {searchTerm}.")
                            return productos_extraidos

                        break

                except (json.JSONDecodeError, TypeError):
                    continue

            if not productos_extraidos:
                print("No se encontraron productos en los scripts.")
                break

        else:
            print(f"Error en la solicitud: {response.status_code}")
            break

    return productos_extraidos


# Función para guardar los productos en la base de datos y en el historial
def guardar_precios_bistek():
    searchTerms = ["achocolatado", "leite", "creme", "mussarela"]

    resumen_guardados = {}

    for searchTerm in searchTerms:
        productos = obtener_precios_bistek(searchTerm)

        supermercado, _ = Supermercado.objects.get_or_create(
            nombre="Bistek",
            direccion="R. Amazonas, 810 - Torres, RS, 95560-000"
        )

        productos_guardados = 0

        for producto in productos:
            nombre = producto['nombre']
            marca = producto['marca']
            precio = producto['precio']
            id_origen = producto['id_origen']
            cantidad = producto['cantidad']
            unidad_medida = producto['unidad_medida']

            # Obtener el producto existente para obtener el precio anterior
            producto_existente = Producto.objects.filter(
                nombre=nombre.strip(),
                supermercado=supermercado
            ).first()

            precio_anterior = producto_existente.precio_actual if producto_existente else 0

            # Actualizar o crear el producto en la tabla Producto
            producto_obj, created = Producto.objects.update_or_create(
                nombre=nombre.strip(),
                supermercado=supermercado,
                defaults={
                    'id_origen': id_origen,
                    'marca': marca.strip(),
                    'precio_actual': precio,
                    'cantidad': cantidad,
                    'unidad_medida': unidad_medida,
                    'fecha_captura': timezone.now(),
                    'fecha_fin': None
                }
            )

            # Crear un registro en la tabla Producto_Hist para mantener el historial
            Producto_Hist.objects.create(
                producto=producto_obj,
                nombre=nombre.strip(),
                marca=marca.strip(),
                precio_anterior=precio_anterior,
                precio_actual=precio,
                cantidad=cantidad,
                unidad_medida=unidad_medida,
                categoria=producto_existente.categoria if producto_existente else None,
                supermercado=supermercado,
                fecha_captura=timezone.now()
            )

            productos_guardados += 1

        resumen_guardados[searchTerm] = productos_guardados

    print("Resumen final de productos guardados:")
    for term, count in resumen_guardados.items():
        print(f"Se han guardado/actualizado {count} productos para el término '{term}'.")


# Ejemplo de cómo llamarlo
# guardar_precios_bistek()
