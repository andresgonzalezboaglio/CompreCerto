from django.db import models
from django.utils import timezone


class Supermercado(models.Model):
    nombre = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id_origen = models.CharField(max_length=255, null=True, blank=True)
    nombre = models.CharField(max_length=255)
    marca = models.CharField(max_length=255)
    supermercado = models.ForeignKey(Supermercado, on_delete=models.CASCADE)
    precio_actual = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unidad_medida = models.CharField(max_length=50, null=True, blank=True)
    categoria = models.CharField(max_length=255, null=True, blank=True)
    fecha_captura = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.nombre} ({self.supermercado.nombre})'


class Producto_Hist(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=255)
    marca = models.CharField(max_length=255)
    precio_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    precio_actual = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_captura = models.DateTimeField(default=timezone.now)
    fecha_aumento = models.DateTimeField(null=True, blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unidad_medida = models.CharField(max_length=50, null=True, blank=True)
    categoria = models.CharField(max_length=255, null=True, blank=True)
    supermercado = models.ForeignKey(Supermercado, on_delete=models.CASCADE)

    def __str__(self):
        return f'Histórico de {self.producto.nombre} - {self.producto.supermercado.nombre}'

