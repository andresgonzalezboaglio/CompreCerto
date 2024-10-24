import os
import django
from CompreCerto import settings
from precios.models import Producto  # Ajusta esto si el modelo está en otra aplicación

# Configura Django si no lo has hecho aún
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CompreCerto.settings")  # Cambia esto por el nombre de tu proyecto
django.setup()


def realizar_query():
    # Ejemplo de consulta
    productos = Producto.objects.all()  # Obtiene todos los productos
    for producto in productos:
        print(f"Nombre: {producto.nombre}, Precio: {producto.precio_actual}")


if __name__ == "__main__":
    realizar_query()