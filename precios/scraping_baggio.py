import requests
from bs4 import BeautifulSoup
from .models import Producto, Producto_Hist, Supermercado
from django.utils import timezone
from .search_terms import searchTerms
from decimal import Decimal
import re


# Función para extraer cantidad y unidad de medida del nombre del producto
def extraer_peso_y_unidad(nombre_producto):
    match = re.search(r'(\d+)\s*(g|kg|ml|l|litro|unid|u)', nombre_producto.lower())
    if match:
        return float(match.group(1)), match.group(2)
    return None, None


# Función para obtener detalles del producto desde la página de detalles
def obtener_detalle_producto(url_producto):
    response = requests.get(url_producto)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraer el nombre del producto
        nombre = soup.find('h1', class_='tt-title').get_text(strip=True)

        # Extraer el precio actual y convertirlo a Decimal
        precio_actual = Decimal(soup.find('input', id='produto_valor')['value'].replace(',', '.'))

        # Extraer id_origen
        id_origen = soup.find('input', id='produto_id')['value']

        # Extraer cantidad y unidad de medida del nombre del producto
        cantidad, unidad_medida = extraer_peso_y_unidad(nombre)

        return {
            'nombre': nombre,
            'precio': precio_actual,
            'id_origen': id_origen,
            'cantidad': cantidad,
            'unidad_medida': unidad_medida,
        }

    print(f"Error al acceder a {url_producto}: {response.status_code}")
    return None


# Función para obtener productos desde la página de búsqueda
def obtener_precios_baggio(searchTerm):
    url_busqueda = f'https://www.baggiosupermercados.net.br/?q={searchTerm}'

    productos_extraidos = []

    try:
        response = requests.get(url_busqueda)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Encontrar todos los productos listados en la página de resultados
            items = soup.find_all('div', class_='tt-description')

            for item in items:
                link_producto = item.find('a')['href']  # Enlace al detalle del producto

                # Obtener el detalle de cada producto desde su página de detalle
                detalles_producto = obtener_detalle_producto(link_producto)
                if detalles_producto:
                    productos_extraidos.append(detalles_producto)

        else:
            print(f"Error al realizar la solicitud: {response.status_code}")

    except requests.RequestException as e:
        print(f"Error de solicitud: {e}")

    return productos_extraidos


# Función para guardar productos en la base de datos y en el historial
def guardar_precios_baggio():
    supermercado, _ = Supermercado.objects.get_or_create(
        nombre="Baggio Supermercados",
        direccion="Rua José Hespanhol, 755 Centro - Passo de Torres/SC"
    )

    for searchTerm in searchTerms:
        productos = obtener_precios_baggio(searchTerm)
        productos_guardados = 0

        for producto in productos:
            nombre = producto['nombre'].upper()
            precio = producto['precio']
            id_origen = producto['id_origen']
            cantidad = producto['cantidad']
            unidad_medida = producto.get('unidad_medida')

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
                producto_existente.is_active = True  # Siempre será True si está en el response

                # Verificar si el precio ha cambiado
                precio_anterior = producto_existente.precio_actual

                if precio_anterior == precio:
                    producto_existente.save()  # Asegúrate de guardar el cambio de is_active
                    continue  # Si el precio es el mismo, no hacer nada

                # Si el precio cambió, actualizar y guardar en el historial
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
                    supermercado=supermercado,
                    fecha_captura=timezone.now(),
                    fecha_variacion=timezone.now()  # Registrar siempre la fecha de variación
                )
            else:
                # Si el producto no existe, crearlo
                Producto.objects.create(
                    id_origen=id_origen,
                    nombre=nombre.strip(),
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    supermercado=supermercado,
                    fecha_captura=timezone.now(),
                    is_active=True  # Establecer como activo al crearlo
                )

            productos_guardados += 1

        print(f"BAGGIO: Se guardaron {productos_guardados} productos para el término '{searchTerm}'.")
