from django.db import models

class Partner(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='partners/logos/')
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name
