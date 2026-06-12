from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from access.models import Department


class Stock(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, unique=True, verbose_name='Name')
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='stocks')
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(1000000)])
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_stocks'
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
	    return self.name
