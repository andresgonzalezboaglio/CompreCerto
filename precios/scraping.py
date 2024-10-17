import requests
from .models import Producto, Supermercado
from urllib.parse import quote_plus
from urllib.parse import quote
from django.utils import timezone
import json
from bs4 import BeautifulSoup


# Token para autenticación (Bearer token)
BEARER_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJ2aXBjb21tZXJjZSIsImF1ZCI6ImFwaS1hZG1pbiIsInN1YiI6IjZiYzQ4NjdlLWRjYTktMTFlOS04NzQyLTAyMGQ3OTM1OWNhMCIsInZpcGNvbW1lcmNlQ2xpZW50ZUlkIjpudWxsLCJpYXQiOjE3Mjg5NDk4MDQsInZlciI6MSwiY2xpZW50IjpudWxsLCJvcGVyYXRvciI6bnVsbCwib3JnIjoiMTMwIn0.PLi7L_TQlx-qZSbY5OfTDB_zpzwXMKTjqZ4DlVVKPbkeYLQ9aYj9k-Lsg1HM4Sdg8vjcLH7GITI6Th-aBMQkSQ'


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
        # Llamamos a la URL con la página actual
        url = f"{base_url}?page={pagina_actual}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Procesar los productos
            productos = data.get('data', {}).get('produtos', [])
            paginator = data.get('paginator', {})

            # Agregar los productos extraídos a la lista
            for producto in productos:
                descripcion = producto.get('descricao', 'Producto sin nombre')
                precio = producto.get('preco', 0)

                productos_extraidos.append({
                    'descripcion': descripcion,
                    'precio': precio,
                    'supermercado': 'Stock Center'
                })

            # Comprobar si hay más páginas
            total_pages = paginator.get('total_pages', 1)
            if pagina_actual >= total_pages:
                break

            # Aumentar el contador de páginas
            pagina_actual += 1
        else:
            print(f"Error en la solicitud: {response.status_code}")
            break

    return productos_extraidos


# Función para guardar productos en la base de datos
def guardar_productos_stock_center(productos, supermercado):
    productos_guardados = 0

    for producto in productos:
        nombre = producto.get('descripcion', '').strip()
        if not nombre:
            print("Producto sin nombre, omitiendo...")
            continue

        precio = producto['precio']
        # Guardar o actualizar el producto en la base de datos
        Producto.objects.update_or_create(
            nombre=nombre,
            supermercado=supermercado,
            defaults={
                'precio_actual': precio,
                'fecha_captura': timezone.now(),
                'fecha_fin': None  # Mantener fecha_fin como None hasta que se actualice
            }
        )
        productos_guardados += 1

    return productos_guardados


# Función principal para obtener y guardar ofertas
def obtener_y_guardar_ofertas_stock_center(searchTerms):
    supermercado, _ = Supermercado.objects.get_or_create(nombre="Stock Center", direccion="Av. Castelo Branco, 2380 - Bairro São Jorge, Torres - RS, 95560-000")
    resumen_guardados = {}

    for searchTerm in searchTerms:
        productos_extraidos = obtener_ofertas_stock_center(searchTerm)
        productos_guardados = guardar_productos_stock_center(productos_extraidos, supermercado)
        resumen_guardados[searchTerm] = productos_guardados

    print("Resumen final de productos guardados:")
    for term, count in resumen_guardados.items():
        print(f"Se han guardado/actualizado {count} productos para el término '{term}'.")


# Ejemplo de cómo llamarlo
# searchTerms = ["yogurt"]
# obtener_y_guardar_ofertas_stock_center(searchTerms)

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

            # Recorremos todos los <script> para ver cuál contiene datos útiles
            script_tags = soup.find_all('script')

            for i, script_tag in enumerate(script_tags):
                try:
                    # Intentar cargar el contenido de cada script como JSON
                    data = json.loads(script_tag.string)

                    # Verificamos si el JSON tiene una estructura que pueda contener productos
                    if 'itemListElement' in data:
                        print(f"Productos encontrados en el script #{i}:")
                        print(json.dumps(data, indent=4))

                        # Obtener los productos de la lista
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

                            if nombre and precio:
                                productos_extraidos.append({
                                    'nombre': nombre,
                                    'marca': marca or "Sin marca",
                                    'precio': float(precio),
                                    'id_origen': id_origen
                                })

                        # Verificar si existe un enlace "next" en el HTML
                        next_link = soup.find('link', {'rel': 'next'})
                        if next_link:
                            pagina_actual += 1
                        else:
                            # No hay más páginas, romper el bucle
                            print(f"Alcanzada la última página ({pagina_actual}) para {searchTerm}.")
                            return productos_extraidos

                        break

                except (json.JSONDecodeError, TypeError):
                    # Algunos <script> no contienen JSON válido, así que los ignoramos
                    continue

            if not productos_extraidos:
                print("No se encontraron productos en los scripts.")
                break

        else:
            print(f"Error en la solicitud: {response.status_code}")
            break

    return productos_extraidos


# Función para guardar los productos en la base de datos
def guardar_precios_bistek():
    searchTerms = ["alfajor"]

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

            Producto.objects.update_or_create(
                nombre=nombre.strip(),
                supermercado=supermercado,
                defaults={
                    'id_origen': id_origen,
                    'marca': marca.strip(),
                    'precio_actual': precio,
                    'fecha_captura': timezone.now(),
                    'fecha_fin': None
                }
            )
            productos_guardados += 1

        resumen_guardados[searchTerm] = productos_guardados

    print("Resumen final de productos guardados:")
    for term, count in resumen_guardados.items():
        print(f"Se han guardado/actualizado {count} productos para el término '{term}'.")

# Ejemplo de cómo llamarlo
# guardar_precios_bistek()

