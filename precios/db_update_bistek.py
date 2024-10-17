import requests
from .models import Producto, Supermercado
from urllib.parse import quote
from django.utils import timezone
import json


# Función para obtener datos de Bistek y actualizar la base de datos
def obtener_y_guardar_precios_bistek(searchTerm):
    encoded_term = quote(searchTerm)  # Codifica usando %20 para la URL

    # URL base simplificada
    url = f'https://www.bistek.com.br/{encoded_term}'

    response = requests.get(url)

    if response.status_code == 200:
        try:
            data = response.text

            # Extraemos el JSON de la plantilla HTML
            start = data.find('<template data-type="json" data-varname="__STATE__">')
            if start != -1:
                start = data.find('<script>', start) + len('<script>')
                end = data.find('</script>', start)
                json_text = data[start:end].strip()

                # Imprimir el JSON capturado
                print("Contenido del script JSON encontrado:")
                print(json_text)

                json_data = json.loads(json_text)

                # Buscamos productos dentro del JSON extraído
                for key, value in json_data.items():
                    if key.startswith('Product:sp') and isinstance(value, dict):
                        nombre = value.get('productName')
                        marca = value.get('brand', {}).get('name', 'Sin marca')
                        precio_bajo = value.get('priceRange', {}).get('sellingPrice', {}).get('lowPrice')
                        precio_alto = value.get('priceRange', {}).get('sellingPrice', {}).get('highPrice')
                        categoria = value.get('categories', {}).get('json', ['Sin categoría'])[-1]
                        id_origen = value.get('productId', 'Sin ID')

                        # Buscar unidad de medida y cantidad
                        especificaciones = value.get('specificationGroups', [])
                        unidad_medida = None
                        cantidad = None

                        for group in especificaciones:
                            for spec in group.get('specifications', []):
                                if spec.get('name') == 'Peso Produto':
                                    cantidad = float(spec.get('values', {}).get('json', [0])[0])
                                elif spec.get('name') == 'Unidade de Medida':
                                    unidad_medida = spec.get('values', {}).get('json', [''])[0]

                        # Solo procesar si los precios están disponibles
                        if precio_bajo is not None and precio_alto is not None:
                            precio = min(precio_bajo, precio_alto)

                            # Guardar o actualizar el producto en la base de datos
                            supermercado, _ = Supermercado.objects.get_or_create(
                                nombre="Bistek", direccion="R. Amazonas, 810 - Torres, RS"
                            )

                            Producto.objects.update_or_create(
                                descripcion=nombre.strip(),
                                supermercado=supermercado,
                                defaults={
                                    'marca': marca.strip(),
                                    'precio_actual': precio,
                                    'fecha_captura': timezone.now(),
                                    'fecha_fin': None,
                                    'id_origen': id_origen,
                                    'cantidad': cantidad,
                                    'unidad_medida': unidad_medida,
                                    'categoria': categoria
                                }
                            )

        except json.JSONDecodeError as e:
            print(f"Error al decodificar el JSON: {e}")
            print(response.text)

    else:
        print(f"Error en la solicitud: {response.status_code}")

# Llamada de prueba
# obtener_y_guardar_precios_bistek('kinder ovo roxo 1 uni 20g')
