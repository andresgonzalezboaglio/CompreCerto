from django.db import models
from django.utils import timezone


class Supermercado(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True, null=True)
    precio_actual = models.DecimalField(max_digits=10, decimal_places=2)
    supermercado = models.ForeignKey(Supermercado, on_delete=models.CASCADE)
    fecha_captura = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} - {self.supermercado.nombre}"

