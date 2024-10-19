import requests
from .models import Producto, Producto_Hist, Supermercado
from urllib.parse import quote_plus
from django.utils import timezone
import json
from bs4 import BeautifulSoup
import re
from .search_terms import searchTerms
from decimal import Decimal  # Asegurarnos de usar Decimal para precisión en comparaciones

# Función para extraer cantidad y unidad de medida del nombre del producto
def extraer_peso_y_unidad(nombre_producto):
    if nombre_producto:
        match = re.search(r'(\d+)\s*(g|kg|ml|l|litro|unid|u)', nombre_producto.lower())
        if match:
            return float(match.group(1)), match.group(2)
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
                            break

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
                                    'precio': Decimal(str(precio)),  # Convertir el precio a Decimal
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

        else:
            print(f"Error en la solicitud: {response.status_code}")
            break

    return productos_extraidos

# Función para guardar los productos en la base de datos y en el historial
def guardar_precios_bistek():
    supermercado, _ = Supermercado.objects.get_or_create(
        nombre="Bistek",
        direccion="R. Amazonas, 810 - Torres, RS, 95560-000"
    )

    for searchTerm in searchTerms:
        productos = obtener_precios_bistek(searchTerm)
        productos_guardados = 0

        for producto in productos:
            nombre = producto['nombre']
            marca = producto['marca']
            precio = producto['precio']
            id_origen = producto['id_origen']
            cantidad = producto['cantidad']
            unidad_medida = producto['unidad_medida']

            # Obtener el producto existente basándonos en id_origen y supermercado
            producto_existente = Producto.objects.filter(
                id_origen=id_origen,
                supermercado=supermercado
            ).first()

            # Si el producto ya existe
            if producto_existente:
                # Verificar si el precio es exactamente igual (compara como Decimal)
                if Decimal(producto_existente.precio_actual) == precio:
                    # Si el precio es el mismo, no hacer nada
                    continue

                # Si el precio ha cambiado, actualizar y registrar el historial
                precio_anterior = producto_existente.precio_actual

                # Actualizar el producto en la tabla Producto
                producto_existente.precio_actual = precio
                producto_existente.fecha_captura = timezone.now()
                producto_existente.save()

                # Guardar en el historial si el precio ha cambiado
                Producto_Hist.objects.create(
                    producto=producto_existente,
                    nombre=nombre.strip(),
                    marca=marca.strip() if marca else None,
                    precio_anterior=precio_anterior,
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    categoria=producto_existente.categoria,
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
                    marca=marca.strip() if marca else None,
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    fecha_captura=timezone.now(),
                    fecha_aumento=None
                )

            productos_guardados += 1

        print(f"BISTEK: Se guardaron {productos_guardados} productos para el término '{searchTerm}'.")
