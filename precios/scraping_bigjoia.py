import requests
from .models import Producto, Producto_Hist, Supermercado
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from .search_terms import searchTerms
import re


# Función para extraer cantidad y unidad de medida del nombre del producto
def extraer_peso_y_unidad(nombre_producto):
    if nombre_producto:
        match = re.search(r'(\d+\.?\d*)\s*(g|kg|ml|l|litro|unid|u|un)', nombre_producto.lower())
        if match:
            return float(match.group(1)), match.group(2)
    return None, None


# Función para convertir precio a Decimal y redondear
def convertir_precio(precio):
    return Decimal(precio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# Configuración de Big Joia
url_base = "https://search.osuper.com.br/ecommerce_products_production/_search"
headers = {
    "Content-Type": "application/json"
}


# Función para procesar cada página de productos y manejar la paginación
def obtener_precios_bigjoia(searchTerm):
    productos_extraidos = []
    has_next_page = True
    after_cursor = None

    while has_next_page:
        payload = {
            "accountId": 101,
            "storeId": 581,
            "categoryName": None,
            "first": 12,
            "after": after_cursor,
            "search": searchTerm,
            "sort": {
                "field": "_score",
                "order": "desc"
            },
            "highlightEnabled": False,
            "promotion": None,
            "brands": [],
            "categories": [],
            "tags": [],
            "personas": [],
            "pricingRange": {}
        }

        # Realizar la solicitud POST
        response = requests.post(url_base, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Iterar sobre los productos en la respuesta
            for edge in data['edges']:
                producto = edge['node']
                nombre = producto.get('name')
                precio = convertir_precio(producto['pricing'][0]['price'])  # Convertimos a Decimal y redondeamos
                id_origen = producto.get('objectID')

                # Obtener el valor de inStock
                in_stock = producto.get('stock', {}).get('inStock', 0)

                # Verificar si hay categorías
                categoria = producto.get('category', {}).get('name', 'Sin categoría')

                # Extraer cantidad y unidad_medida del nombre
                cantidad, unidad_medida = extraer_peso_y_unidad(nombre)

                productos_extraidos.append({
                    'nombre': nombre,
                    'precio': precio,
                    'id_origen': id_origen,
                    'cantidad': cantidad,
                    'unidad_medida': unidad_medida,
                    'categoria': categoria,
                    'is_active': in_stock > 0  # Establecer is_active según el stock
                })

            # Paginación
            has_next_page = data['pageInfo']['hasNextPage']
            after_cursor = data['pageInfo']['endCursor'] if has_next_page else None

        else:
            print(f"Error en la solicitud: {response.status_code}")
            break

    return productos_extraidos


# Función para guardar los productos de Big Joia en la base de datos
def guardar_precios_bigjoia():
    supermercado, _ = Supermercado.objects.get_or_create(
        nombre="Big Joia",
        direccion="Av. Carlos Barbosa, 240 - Torres, RS, 95560-000"
    )

    for searchTerm in searchTerms:
        productos = obtener_precios_bigjoia(searchTerm)
        productos_guardados = 0

        for producto in productos:
            nombre = producto['nombre'].upper()
            precio = producto['precio']
            id_origen = producto['id_origen']
            cantidad = producto['cantidad']
            unidad_medida = producto.get('unidad_medida')
            categoria = producto['categoria'].upper()

            if unidad_medida is not None:
                unidad_medida = unidad_medida.upper()
            else:
                unidad_medida = None

            # Obtener el producto existente basándonos en id_origen y supermercado
            producto_existente = Producto.objects.filter(
                id_origen=id_origen,
                supermercado=supermercado
            ).first()

            if producto_existente:
                # Actualizar is_active basado en la disponibilidad del producto
                producto_existente.is_active = True  # Siempre se establecerá a True al encontrarlo

                # Verificar si el precio ha cambiado
                precio_anterior = convertir_precio(producto_existente.precio_actual)

                if precio_anterior == precio:
                    producto_existente.save()  # Asegúrate de guardar el cambio de is_active
                    continue  # Si el precio es el mismo, no hacer nada

                # Actualizar y guardar en el historial si el precio cambió
                producto_existente.precio_actual = precio
                producto_existente.fecha_captura = timezone.now()
                producto_existente.save()

                # Guardar en el historial
                Producto_Hist.objects.create(
                    producto=producto_existente,
                    nombre=nombre.strip(),
                    precio_anterior=precio_anterior,
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    categoria=categoria,
                    supermercado=supermercado,
                    fecha_captura=timezone.now(),
                    fecha_aumento=timezone.now() if precio > precio_anterior else None
                )
            else:
                # Si el producto no existe, crearlo
                Producto.objects.create(
                    id_origen=id_origen,
                    supermercado=supermercado,
                    nombre=nombre.strip(),
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    categoria=categoria,
                    fecha_captura=timezone.now(),
                    fecha_aumento=None,
                    is_active=True  # Establecer como activo al crearlo
                )

            productos_guardados += 1

        print(f"BIG JOIA: Se guardaron {productos_guardados} productos para el término '{searchTerm}'.")
