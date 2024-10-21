import json
import requests
from bs4 import BeautifulSoup
from .models import Producto, Producto_Hist, Supermercado
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote
from .search_terms import searchTerms
import time
import random
import re

# Lista de User-Agents para rotar entre las solicitudes
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.198 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.124 Safari/537.36',
]


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


# Función para obtener precios de Bistek desde el HTML
def obtener_precios_bistek(searchTerm):
    encoded_term = quote(searchTerm)
    url = f'https://www.bistek.com.br/{encoded_term}?map=ft'
    productos_extraidos = []
    pagina_actual = 1

    while True:
        headers = {
            'User-Agent': random.choice(USER_AGENTS)  # Rotar entre User-Agents
        }

        try:
            response = requests.get(f"{url}&page={pagina_actual}", headers=headers, timeout=10)

            # Verificar si la solicitud fue exitosa
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                script_tags = soup.find_all('script')

                for i, script_tag in enumerate(script_tags):
                    try:
                        data = json.loads(script_tag.string)
                        if 'itemListElement' in data:
                            productos = data.get('itemListElement', [])

                            if not productos:  # Manejo del array vacío
                                print(f"No se encontraron productos para el término '{searchTerm}' en la página {pagina_actual}.")
                                return productos_extraidos  # Retorna la lista vacía

                            for item in productos:
                                producto = item.get('item', {})
                                nombre = producto.get('name')
                                marca = producto.get('brand', {}).get('name')
                                precio = producto.get('offers', {}).get('lowPrice')
                                id_origen = producto.get('sku')

                                # Extraer cantidad y unidad de medida del nombre del producto
                                cantidad, unidad_medida = extraer_peso_y_unidad(nombre)

                                if nombre and precio:
                                    productos_extraidos.append({
                                        'nombre': nombre,
                                        'marca': marca or "Sin marca",
                                        'precio': convertir_precio(precio),
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

        except requests.RequestException as e:
            print(f"Error en la solicitud: {e}")
            break

        # Tiempo de espera aleatorio entre solicitudes (anti-DDOS)
        time.sleep(random.uniform(1, 3))

    return productos_extraidos


# Función para guardar los productos en la base de datos y en el historial
def guardar_precios_bistek():
    supermercado, _ = Supermercado.objects.get_or_create(
        nombre="Bistek",
        direccion="R. Amazonas, 810 - Torres, RS, 95560-000"
    )

    # Obtener productos existentes con is_active=True
    productos_existentes = Producto.objects.filter(supermercado=supermercado, is_active=True)
    productos_activos_ids = {producto.id_origen for producto in productos_existentes}

    for searchTerm in searchTerms:
        productos = obtener_precios_bistek(searchTerm)
        productos_guardados = 0

        # Crear un conjunto de IDs de productos que están actualmente disponibles
        productos_nuevos_ids = {producto['id_origen'] for producto in productos}

        # Actualizar is_active a False para productos que ya no están disponibles
        for id_origen in productos_activos_ids:
            if id_origen not in productos_nuevos_ids:
                Producto.objects.filter(id_origen=id_origen, supermercado=supermercado).update(is_active=False)

        # Actualizar is_active a True para productos que están de nuevo disponibles
        for id_origen in productos_nuevos_ids:
            Producto.objects.filter(id_origen=id_origen, supermercado=supermercado).update(is_active=True)

        for producto in productos:
            nombre = producto['nombre'].upper()
            marca = producto['marca'].upper()
            precio = producto['precio']
            id_origen = producto['id_origen']
            cantidad = producto['cantidad']
            unidad_medida = producto.get('unidad_medida')  # Usamos get para evitar KeyError
            if unidad_medida is not None:
                unidad_medida = unidad_medida.upper()
            else:
                unidad_medida = None

            # Obtener el producto existente basándonos en id_origen y supermercado
            producto_existente = Producto.objects.filter(
                id_origen=id_origen,
                supermercado=supermercado
            ).first()

            # Verificar si el producto ya existe y si el precio cambió
            if producto_existente:
                precio_anterior = convertir_precio(producto_existente.precio_actual)

                if precio_anterior == precio:
                    continue  # Si el precio es el mismo, no hacer nada

                # Actualizar y guardar en el historial si el precio cambió
                producto_existente.precio_actual = precio
                producto_existente.fecha_captura = timezone.now()
                producto_existente.save()

                # Guardar en el historial
                Producto_Hist.objects.create(
                    producto=producto_existente,
                    nombre=nombre.strip(),
                    marca=marca.strip(),
                    precio_anterior=precio_anterior,
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    supermercado=supermercado,
                    fecha_captura=timezone.now(),
                    fecha_variacion=timezone.now() if precio > precio_anterior else None
                )

            else:
                # Crear el producto si no existe
                Producto.objects.create(
                    id_origen=id_origen,
                    supermercado=supermercado,
                    nombre=nombre.strip(),
                    marca=marca.strip(),
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    fecha_captura=timezone.now(),
                    is_active=True  # Asegúrate de establecerlo como activo al crearlo
                )

            productos_guardados += 1

        print(f"BISTEK: Se guardaron {productos_guardados} productos para el término '{searchTerm}'.")
