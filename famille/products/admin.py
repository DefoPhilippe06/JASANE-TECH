from django.contrib import admin
from .models import Product, ProductImage, Category

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("category",)
    inlines = [ProductImageInline]

admin.site.register(Product, ProductAdmin)
admin.site.register(Category)
