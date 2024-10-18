import requests
from .models import Producto, Producto_Hist, Supermercado
from urllib.parse import quote_plus
from django.utils import timezone
import json
from bs4 import BeautifulSoup
import re
from decimal import Decimal


# Función para extraer cantidad y unidad de medida del nombre del producto
def extraer_peso_y_unidad(nombre_producto):
    if nombre_producto:
        match = re.search(r'(\d+)\s*(g|kg|ml|l|litro|unid|u)', nombre_producto.lower())
        if match:
            return float(match.group(1)), match.group(2)
    return None, None


# Función para obtener precios de Bistek
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

            for script_tag in script_tags:
                try:
                    data = json.loads(script_tag.string)

                    if 'itemListElement' in data:
                        productos = data.get('itemListElement', [])
                        for item in productos:
                            producto = item.get('item', {})
                            nombre = producto.get('name')
                            marca = producto.get('brand', {}).get('name')
                            precio = producto.get('offers', {}).get('lowPrice')
                            id_origen = producto.get('sku')

                            if nombre:
                                cantidad, unidad_medida = extraer_peso_y_unidad(nombre)
                            else:
                                cantidad, unidad_medida = None, None

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
                            return productos_extraidos

                except (json.JSONDecodeError, TypeError):
                    continue

            if not productos_extraidos:
                break

        else:
            break

    return productos_extraidos


# Función para guardar los productos en la base de datos
def guardar_precios_bistek():
    searchTerms = ["canela"]  # Puedes cambiar los términos aquí

    for searchTerm in searchTerms:
        productos = obtener_precios_bistek(searchTerm)

        supermercado, _ = Supermercado.objects.get_or_create(
            nombre="Bistek",
            direccion="R. Amazonas, 810 - Torres, RS, 95560-000"
        )

        for producto in productos:
            nombre = producto['nombre']
            marca = producto['marca']
            precio = producto['precio']
            id_origen = producto['id_origen']
            cantidad = producto['cantidad']
            unidad_medida = producto['unidad_medida']

            producto_existente = Producto.objects.filter(
                nombre=nombre.strip(),
                supermercado=supermercado
            ).first()

            precio_anterior = producto_existente.precio_actual if producto_existente else 0

            if producto_existente and producto_existente.precio_actual == precio:
                continue

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
                    'fecha_aumento': None
                }
            )

            if not created and precio != precio_anterior:
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
                    fecha_captura=timezone.now(),
                    fecha_aumento=timezone.now() if precio > precio_anterior else None
                )

        print(f"BISTEK: Se han guardado productos para el término '{searchTerm}'.")

