import requests
from .models import Producto, Producto_Hist, Supermercado
from urllib.parse import quote_plus
from django.utils import timezone
import re
from decimal import Decimal
from .search_terms import searchTerms
from .config import STOCK_CENTER_TOKEN


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
        'Authorization': f'Bearer {STOCK_CENTER_TOKEN}'
    }

    productos_extraidos = []
    pagina_actual = 1

    while True:
        url = f"{base_url}?page={pagina_actual}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            productos = data.get('data', {}).get('produtos', [])

            for producto in productos:
                descripcion = producto.get('descricao', 'Producto sin nombre')
                if descripcion == 'Producto sin nombre':
                    continue  # Ignoramos productos sin nombre

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

            total_pages = data.get('paginator', {}).get('total_pages', 1)
            if pagina_actual >= total_pages:
                break

            pagina_actual += 1
        else:
            print(f"Error en la solicitud: {response.status_code}")
            break

    return productos_extraidos


# Función para guardar productos en la base de datos y en el historial
def guardar_productos_stock_center():
    for searchTerm in searchTerms:
        productos = obtener_ofertas_stock_center(searchTerm)
        supermercado, _ = Supermercado.objects.get_or_create(
            nombre="Stock Center",
            direccion="Av. Castelo Branco, 2380 - Bairro São Jorge, Torres - RS, 95560-000"
        )

        productos_guardados = 0

        for producto in productos:
            nombre = producto['descripcion'].upper()
            precio = Decimal(str(producto['precio']))  # Convertimos el precio a Decimal
            id_origen = producto['id_origen']
            cantidad = producto['cantidad']
            unidad_medida = producto['unidad_medida']

            producto_existente = Producto.objects.filter(
                id_origen=id_origen,
                supermercado=supermercado
            ).first()

            precio_anterior = producto_existente.precio_actual if producto_existente else Decimal('0')

            if producto_existente and producto_existente.precio_actual == precio:
                continue

            producto_obj, created = Producto.objects.update_or_create(
                id_origen=id_origen,
                supermercado=supermercado,
                defaults={
                    'nombre': nombre.strip(),
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
                    precio_anterior=precio_anterior,
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    supermercado=supermercado,
                    fecha_captura=timezone.now(),
                    fecha_aumento=timezone.now() if precio > precio_anterior else None
                )

            productos_guardados += 1

        print(f"STOCK CENTER: Se guardaron {productos_guardados} productos para el término '{searchTerm}'.")
