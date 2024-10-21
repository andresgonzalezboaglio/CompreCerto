import requests
from .models import Producto, Producto_Hist, Supermercado
from django.utils import timezone
import re
from decimal import Decimal
from .search_terms import searchTerms
from .config import ASUN_BEARER_TOKEN


# Función para extraer cantidad y unidad de medida del nombre del producto
def extraer_peso_y_unidad(nombre_producto):
    match = re.search(r'(\d+)\s*(g|kg|ml|l|litro|unid|u)', nombre_producto.lower())
    if match:
        return float(match.group(1)), match.group(2)
    return None, None


# Función para obtener ofertas desde Asun con paginación
def obtener_ofertas_asun(searchTerm):
    base_url = f"https://services.vipcommerce.com.br/api-admin/v1/loja/buscas/produtos/filial/1/centro_distribuicao/30/termo/{searchTerm}?"
    headers = {
        'organizationid': '155',
        'domainkey': 'asunonline.com.br',
        'Authorization': f'Bearer {ASUN_BEARER_TOKEN}'
    }

    productos_extraidos = []
    pagina_actual = 1

    while True:
        url = f"{base_url}page={pagina_actual}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            productos = data.get('data', {}).get('produtos', [])
            paginator = data.get('paginator', {})

            for producto in productos:
                descripcion = producto.get('descricao')
                precio = Decimal(str(producto['preco']))
                id_origen = producto['sku']
                is_active = producto.get('disponivel', False)  # Obtener el estado de disponibilidad

                # Extraer cantidad y unidad de medida del nombre
                cantidad, unidad_medida = extraer_peso_y_unidad(descripcion)

                productos_extraidos.append({
                    'descripcion': descripcion,
                    'precio': precio,
                    'id_origen': id_origen,
                    'cantidad': cantidad,
                    'unidad_medida': unidad_medida,
                    'supermercado': 'Asun',
                    'is_active': is_active  # Asegúrate de incluir is_active
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
def guardar_productos_asun(productos, supermercado):
    productos_guardados = 0

    for producto in productos:
        nombre = producto.get('descripcion', '').strip().upper()
        precio = producto.get('precio')  # El precio ya está convertido a Decimal
        id_origen = producto['id_origen']
        cantidad = producto['cantidad']
        unidad_medida = producto.get('unidad_medida')  # Usamos get para evitar KeyError
        is_active = producto.get('is_active', False)  # Obtener estado de disponibilidad

        if unidad_medida is not None:
            unidad_medida = unidad_medida.upper()
        else:
            unidad_medida = None

        # Obtener el producto existente basándonos en id_origen y supermercado
        producto_existente = Producto.objects.filter(
            id_origen=id_origen,
            supermercado=supermercado
        ).first()

        # Verificar si el producto ya existe
        if producto_existente:
            # Actualizar is_active basado en la disponibilidad del producto
            is_active_changed = producto_existente.is_active != is_active
            producto_existente.is_active = is_active

            # Verificar si el precio ha cambiado
            if producto_existente.precio_actual != precio:
                precio_anterior = producto_existente.precio_actual

                # Actualizar el producto en la tabla Producto
                producto_existente.precio_actual = precio
                producto_existente.fecha_captura = timezone.now()
                producto_existente.save()

                # Guardar en el historial
                Producto_Hist.objects.create(
                    producto=producto_existente,
                    nombre=nombre,
                    precio_anterior=precio_anterior,
                    precio_actual=precio,
                    cantidad=cantidad,
                    unidad_medida=unidad_medida,
                    categoria=producto_existente.categoria,
                    supermercado=supermercado,
                    fecha_captura=timezone.now(),
                    fecha_variacion=timezone.now() if precio > precio_anterior else None
                )

            # Si solo cambió la disponibilidad, lo guardamos
            if is_active_changed:
                producto_existente.save()  # Guardar el cambio de is_active

        else:
            # Si el producto no existe, crearlo
            Producto.objects.create(
                id_origen=id_origen,
                supermercado=supermercado,
                nombre=nombre,
                precio_actual=precio,
                cantidad=cantidad,
                unidad_medida=unidad_medida,
                fecha_captura=timezone.now(),
                is_active=is_active  # Establecer como activo al crearlo
            )

        productos_guardados += 1

    return productos_guardados


# Función principal para obtener y guardar ofertas
def obtener_y_guardar_ofertas_asun():
    supermercado, _ = Supermercado.objects.get_or_create(
        nombre="Asun",
        direccion="Av. Castelo Branco, 1010 - Centro, Torres - RS, 95560-000"
    )

    resumen_guardados = {}

    for searchTerm in searchTerms:
        productos_extraidos = obtener_ofertas_asun(searchTerm)
        productos_guardados = guardar_productos_asun(productos_extraidos, supermercado)
        resumen_guardados[searchTerm] = productos_guardados

    # Mostrar resumen de productos guardados
    for term, count in resumen_guardados.items():
        print(f"ASUN: Se guardaron {count} productos para el término '{term}'.")
