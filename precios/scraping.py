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
                            print(f"BISTECK: Alcanzada la última página ({pagina_actual}) para {searchTerm}.")
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
    searchTerms = ["canela"]

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
        print(f"BISTECK: Se han guardado/actualizado {count} productos para el término '{term}'.")


# Ejemplo de cómo llamarlo
guardar_precios_bistek()

"""
-------------------------------------------STOCK CENTER
"""


# Token para autenticación (Bearer token)
BEARER_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJ2aXBjb21tZXJjZSIsImF1ZCI6ImFwaS1hZG1pbiIsInN1YiI6IjZiYzQ4NjdlLWRjYTktMTFlOS04NzQyLTAyMGQ3OTM1OWNhMCIsInZpcGNvbW1lcmNlQ2xpZW50ZUlkIjpudWxsLCJpYXQiOjE3Mjg5NDk4MDQsInZlciI6MSwiY2xpZW50IjpudWxsLCJvcGVyYXRvciI6bnVsbCwib3JnIjoiMTMwIn0.PLi7L_TQlx-qZSbY5OfTDB_zpzwXMKTjqZ4DlVVKPbkeYLQ9aYj9k-Lsg1HM4Sdg8vjcLH7GITI6Th-aBMQkSQ'


# Función para extraer cantidad y unidad de medida del nombre del producto
def extraer_peso_y_unidad(nombre_producto):
    match = re.search(r'(\d+)\s*(g|kg|ml|l|litro|unid|u)', nombre_producto.lower())
    if match:
        return float(match.group(1)), match.group(2)
    return None, None


# Función para obtener ofertas desde Stock Center con paginación
def obtener_ofertas_stock_center(searchTerm):
    encoded_term = quote_plus(searchTerm)
    base_url = f"https://api-loja.stokonline.com.br/v1/loja/buscas/produtos/filial/1/centro_distribuicao/16/termo/{encoded_term}"
    headers = {
        'Authorization': f'Bearer {BEARER_TOKEN}'
    }

    productos_extraidos = []
    pagina_actual = 1

    while True:
        url = f"{base_url}?page={pagina_actual}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            productos = data.get('data', {}).get('produtos', [])
            paginator = data.get('paginator', {})

            for producto in productos:
                descripcion = producto.get('descricao', 'Producto sin nombre')
                precio = producto.get('preco', 0)
                id_origen = producto.get('sku')

                # Extraer cantidad y unidad de medida del nombre
                cantidad, unidad_medida = extraer_peso_y_unidad(descripcion)

                productos_extraidos.append({
                    'descripcion': descripcion,
                    'precio': precio,
                    'id_origen': id_origen,
                    'cantidad': cantidad,
                    'unidad_medida': unidad_medida,
                    'supermercado': 'Stock Center'
                })

            total_pages = paginator.get('total_pages', 1)
            if pagina_actual >= total_pages:
                break

            pagina_actual += 1
        else:
            print(f"Error en la solicitud: {response.status_code}")
            break

    return productos_extraidos


# Función para guardar productos en la base de datos y en el historial
def guardar_productos_stock_center(productos, supermercado):
    productos_guardados = 0

    for producto in productos:
        nombre = producto.get('descripcion', '').strip()
        if not nombre:
            print("Producto sin nombre, omitiendo...")
            continue

        precio = producto['precio']
        id_origen = producto['id_origen']
        cantidad = producto['cantidad']
        unidad_medida = producto['unidad_medida']

        # Obtener el producto existente para obtener el precio anterior
        producto_existente = Producto.objects.filter(
            nombre=nombre,
            supermercado=supermercado
        ).first()

        precio_anterior = producto_existente.precio_actual if producto_existente else 0

        # Actualizar o crear el producto en la tabla Producto
        producto_obj, created = Producto.objects.update_or_create(
            nombre=nombre,
            supermercado=supermercado,
            defaults={
                'id_origen': id_origen,
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
            nombre=nombre,
            precio_anterior=precio_anterior,
            precio_actual=precio,
            cantidad=cantidad,
            unidad_medida=unidad_medida,
            supermercado=supermercado,
            fecha_captura=timezone.now()
        )

        productos_guardados += 1

    return productos_guardados


# Función principal para obtener y guardar ofertas
def obtener_y_guardar_ofertas_stock_center(searchTerms):
    supermercado, _ = Supermercado.objects.get_or_create(
        nombre="Stock Center",
        direccion="Av. Castelo Branco, 2380 - Bairro São Jorge, Torres - RS, 95560-000"
    )
    resumen_guardados = {}

    for searchTerm in searchTerms:
        productos_extraidos = obtener_ofertas_stock_center(searchTerm)
        productos_guardados = guardar_productos_stock_center(productos_extraidos, supermercado)
        resumen_guardados[searchTerm] = productos_guardados

    print("Resumen final de productos guardados:")
    for term, count in resumen_guardados.items():
        print(f"STOCK CENTER: Se han guardado/actualizado {count} productos para el término '{term}'.")


# Ejemplo de cómo llamarlo
searchTerms = ["canela"]
obtener_y_guardar_ofertas_stock_center(searchTerms)
