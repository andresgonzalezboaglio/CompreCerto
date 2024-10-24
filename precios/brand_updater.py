import csv
from django.utils import timezone
from precios.models import Producto


def actualizar_marcas_desde_csv(csv_file_path):
    # Cargar las marcas desde el archivo CSV
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        # Ignorar el encabezado
        next(reader)
        marcas = [row[0] for row in reader]

    # Iterar sobre los productos
    for producto in Producto.objects.all():
        nombre_producto = producto.nombre

        # Verificar si el campo marca es null
        if producto.marca is None:
            for marca in marcas:
                if marca in nombre_producto:
                    # Actualizar el campo marca
                    producto.marca = marca
                    producto.fecha_actualizacion = timezone.now()  # Si deseas registrar la fecha de actualización
                    producto.save()
                    print(f"Actualizado producto: {nombre_producto} con marca: {marca}")
                    break  # Salir del bucle después de la primera coincidencia


actualizar_marcas_desde_csv('brands.csv')
