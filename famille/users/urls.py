from django.urls import path

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view
from .views import (
    initiate_payment_view, 
    payment_confirm_view, 
    payment_notify_view, 
    payment_success_view, 
    payment_error_view
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
    
    # URLs pour le paiement
    path("payment/initiate/", view=initiate_payment_view, name="initiate-payment"),
    path("payment/confirm/", view=payment_confirm_view, name="payment-confirm"),
    path("payment/notify/", view=payment_notify_view, name="payment-notify"),
    path("payment/success/", view=payment_success_view, name="payment-success"),
    path("payment/error/", view=payment_error_view, name="payment-error"),
]
from .views import (
    user_detail_view, user_redirect_view, user_update_view,
    initiate_payment_view, payment_confirm_view, payment_notify_view,
    payment_success_view, payment_error_view,
    initiate_cart_payment_view  # ← Ajoutez cette importation
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
    
    # URLs pour le paiement
    path("payment/initiate/", view=initiate_payment_view, name="initiate-payment"),
    path("payment/initiate/cart/", view=initiate_cart_payment_view, name="initiate-cart-payment"),  # ← Nouvelle URL
    path("payment/confirm/", view=payment_confirm_view, name="payment-confirm"),
    path("payment/notify/", view=payment_notify_view, name="payment-notify"),
    path("payment/success/", view=payment_success_view, name="payment-success"),
    path("payment/error/", view=payment_error_view, name="payment-error"),
]