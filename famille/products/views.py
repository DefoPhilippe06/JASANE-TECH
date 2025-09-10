from django.http import HttpResponseRedirect
from django.urls import reverse
# Panier : ajouter un produit
def add_to_cart(request, pk):
    cart = request.session.get('cart', {})
    cart[str(pk)] = cart.get(str(pk), 0) + 1
    request.session['cart'] = cart
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('products:product_list')))

# Panier : retirer un produit
def remove_from_cart(request, pk):
    cart = request.session.get('cart', {})
    if str(pk) in cart:
        del cart[str(pk)]
        request.session['cart'] = cart
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('products:cart')))

# Panier : afficher le panier
def cart(request):
    cart = request.session.get('cart', {})
    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    cart_items = []
    for product in products:
        cart_items.append({
            'product': product,
            'quantity': cart[str(product.id)],
            'total': product.price * cart[str(product.id)]
        })
    total_price = sum(item['total'] for item in cart_items)
    return render(request, 'products/cart.html', {'cart_items': cart_items, 'total_price': total_price})
from django.shortcuts import render, get_object_or_404
from .models import Product, Category
from django.core.paginator import Paginator
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'products/category_list.html', {'categories': categories})

def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    products = category.products.prefetch_related('images').all()
    return render(request, 'products/category_detail.html', {'category': category, 'products': products})

def product_list(request):
    category_id = request.GET.get('category')
    search = request.GET.get('search')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    page_number = request.GET.get('page', 1)
    products = Product.objects.prefetch_related('images').all()
    categories = Category.objects.all()
    if category_id:
        products = products.filter(category_id=category_id)
    if search:
        products = products.filter(name__icontains=search)
    if price_min:
        products = products.filter(price__gte=price_min)
    if price_max:
        products = products.filter(price__lte=price_max)
    paginator = Paginator(products, 60)  # 6 produits par page
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        'products/product_list.html',
        {
            'products': page_obj.object_list,
            'page_obj': page_obj,
            'product_count': products.count(),
            'categories': categories,
            'selected_category': int(category_id) if category_id else None,
            'search': search or '',
            'price_min': price_min or '',
            'price_max': price_max or '',
        }
    )

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/product_detail.html', {'product': product})

# Créer une commande à partir du panier ou d'un produit unique
from .models import Commande, CommandeItem
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction

def create_order(request, pk=None):
    user = request.user if request.user.is_authenticated else None
    try:
        with transaction.atomic():
            commande = Commande.objects.create(user=user)
            if pk:
                # Commander un seul produit
                product = get_object_or_404(Product, pk=pk)
                quantity = 1
                CommandeItem.objects.create(
                    commande=commande,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
                commande.total = product.price * quantity
            else:
                # Commander tout le panier
                cart = request.session.get('cart', {})
                product_ids = [int(pid) for pid in cart.keys()]
                products = Product.objects.filter(id__in=product_ids)
                total = 0
                for product in products:
                    quantity = cart[str(product.id)]
                    CommandeItem.objects.create(
                        commande=commande,
                        product=product,
                        quantity=quantity,
                        price=product.price
                    )
                    total += product.price * quantity
                commande.total = total
                # Vider le panier
                request.session['cart'] = {}
            commande.save()
        messages.success(request, "Commande créée avec succès !")
    except Exception as e:
        messages.error(request, f"Erreur lors de la création de la commande : {e}")
    return redirect('products:product_list')
