from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import time
import random
import logging
from django.conf import settings

from famille.users.models import User
from famille.products.models import Product  # Assurez-vous d'importer votre modèle Product

# Configuration du logger
logger = logging.getLogger(__name__)

# Vos vues utilisateur existantes...
class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"

user_detail_view = UserDetailView.as_view()

class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user

user_update_view = UserUpdateView.as_view()

class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})

user_redirect_view = UserRedirectView.as_view()

# Nouvelles vues pour le paiement
class InitiatePaymentView(LoginRequiredMixin, View):
    def get(self, request):
        # Vérifier que l'utilisateur est authentifié
        if not request.user.is_authenticated:
            logger.error("Utilisateur non authentifié tentant d'accéder au paiement")
            return redirect(f"{reverse('account_login')}?next={request.path}?{request.GET.urlencode()}")
        
        product_id = request.GET.get('product_id')
        method = request.GET.get('method')  # orange, mtn, card
        
        if not product_id:
            logger.error("Product ID manquant dans la requête de paiement")
            return redirect(f"{reverse('users:payment-error')}?message=Produit non spécifié")
        
        # Récupérer le produit
        product = get_object_or_404(Product, id=product_id)
        
        # Configuration CinetPay - NOUVEAU BUSINESS
        apikey = getattr(settings, 'CINETPAY_API_KEY', '57291868268684b617a2858.66115218')
        site_id = getattr(settings, 'CINETPAY_SITE_ID', '105905628')
        
        # URLs de callback
        return_url = request.build_absolute_uri(reverse('users:payment-confirm'))
        notify_url = request.build_absolute_uri(reverse('users:payment-notify'))
        
        # Générer un ID de transaction unique (max 20 caractères pour CinetPay)
        transaction_id = f"CMD{product_id}{random.randint(1000, 9999)}"
        
        # Convertir le prix en entier (CinetPay nécessite un integer)
        try:
            amount = int(float(product.price))
        except (ValueError, TypeError):
            amount = 1000  # Valeur par défaut en cas d'erreur
        
        # Préparer les informations client avec des valeurs par défaut sécurisées
        user = request.user
        
        # Récupérer les valeurs avec des fallbacks sécurisés
        customer_name = user.get_full_name() or getattr(user, 'username', 'Client')
        customer_surname = getattr(user, 'username', 'Client')
        customer_email = getattr(user, 'email', 'client@example.com')
        customer_phone = getattr(user, 'phone_number', '+225070000000')
        customer_address = getattr(user, 'address', 'Abidjan')
        customer_city = getattr(user, 'city', 'Abidjan')
        customer_zip = getattr(user, 'zip_code', '00225')
        customer_state = getattr(user, 'state', 'Abidjan')
        
        # S'assurer que les valeurs sont des strings avant de les slicer
        customer_name = str(customer_name)[:30] if customer_name else 'Client'
        customer_surname = str(customer_surname)[:20] if customer_surname else 'Client'
        customer_email = str(customer_email) if customer_email else 'client@example.com'
        customer_phone = str(customer_phone) if customer_phone else '+225070000000'
        customer_address = str(customer_address)[:50] if customer_address else 'Abidjan'
        customer_city = str(customer_city)[:30] if customer_city else 'Abidjan'
        customer_zip = str(customer_zip)[:10] if customer_zip else '00225'
        customer_state = str(customer_state)[:30] if customer_state else 'Abidjan'
        
        # Données à envoyer à CinetPay (format correct)
        payload = {
    "apikey": apikey,
    "site_id": site_id,
    "transaction_id": transaction_id,
    "amount": amount,
    "currency": "XAF",  # Devise obligatoire pour le Cameroun
    "description": f"Achat de {product.name}"[:50],
    "return_url": return_url,
    "notify_url": notify_url,
    "channels": "ALL",
    "customer_name": customer_name,
    "customer_surname": customer_surname,
    "customer_email": customer_email,
    "customer_phone_number": "677070707",  # Format camerounais
    "customer_country": "CM",  # Code pays Cameroun
    "customer_city": "Yaoundé",  # Ville par défaut
    "mode": "test"  # Mode test activé
}
        
        # Journalisation pour débogage
        logger.info(f"Envoi requête CinetPay: {payload}")
        
        try:
            # Envoyer la requête à CinetPay
            response = requests.post(
                "https://api-checkout.cinetpay.com/v2/payment",
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"Réponse CinetPay - Status: {response.status_code}, Contenu: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '201':
                    # Rediriger vers la page de paiement CinetPay
                    payment_url = data['data']['payment_url']
                    logger.info(f"Redirection vers: {payment_url}")
                    return redirect(payment_url)
                else:
                    error_message = data.get('message', 'Erreur inconnue de CinetPay')
                    error_code = data.get('code', 'N/A')
                    logger.error(f"Erreur CinetPay - Code: {error_code}, Message: {error_message}")
                    return redirect(f"{reverse('users:payment-error')}?message={error_message}&code={error_code}")
            else:
                # Erreur HTTP 400 - Afficher plus de détails
                error_details = response.text
                logger.error(f"Erreur HTTP {response.status_code} de CinetPay: {error_details}")
                return redirect(f"{reverse('users:payment-error')}?message=Erreur de configuration CinetPay (HTTP {response.status_code})&details={error_details}")
                
        except requests.exceptions.RequestException as e:
            error_message = f"Erreur de connexion: {str(e)}"
            logger.error(f"Exception lors de l'appel CinetPay: {error_message}")
            return redirect(f"{reverse('users:payment-error')}?message={error_message}")
        except Exception as e:
            error_message = f"Erreur inattendue: {str(e)}"
            logger.error(f"Exception inattendue: {error_message}")
            return redirect(f"{reverse('users:payment-error')}?message={error_message}")

initiate_payment_view = InitiatePaymentView.as_view()
# Ajoutez cette vue après InitiatePaymentView
class InitiateCartPaymentView(LoginRequiredMixin, View):
    def get(self, request):
        # Vérifier que l'utilisateur est authentifié
        if not request.user.is_authenticated:
            logger.error("Utilisateur non authentifié tentant d'accéder au paiement panier")
            return redirect(f"{reverse('account_login')}?next={request.path}?{request.GET.urlencode()}")
        
        method = request.GET.get('method')  # orange, mtn, card
        amount = request.GET.get('amount')
        description = request.GET.get('description', 'Panier complet')
        
        # Configuration CinetPay
        apikey = getattr(settings, 'CINETPAY_API_KEY', '57291868268684b617a2858.66115218')
        site_id = getattr(settings, 'CINETPAY_SITE_ID', '105905628')
        
        # URLs de callback
        return_url = request.build_absolute_uri(reverse('users:payment-confirm'))
        notify_url = request.build_absolute_uri(reverse('users:payment-notify'))
        
        # Générer un ID de transaction unique
        transaction_id = f"CART{int(time.time())}{random.randint(1000, 9999)}"
        
        # Convertir le montant en entier
        try:
            amount_int = int(float(amount))
        except (ValueError, TypeError):
            amount_int = 1000
        
        # Préparer les informations client
        user = request.user
        customer_name = user.get_full_name() or getattr(user, 'username', 'Client')
        customer_surname = getattr(user, 'username', 'Client')
        customer_email = getattr(user, 'email', 'client@example.com')
        customer_phone = getattr(user, 'phone_number', '+225070000000')
        
        # S'assurer que les valeurs sont des strings
        customer_name = str(customer_name)[:30] if customer_name else 'Client'
        customer_surname = str(customer_surname)[:20] if customer_surname else 'Client'
        customer_email = str(customer_email) if customer_email else 'client@example.com'
        customer_phone = str(customer_phone) if customer_phone else '+225070000000'
        
        # Données à envoyer à CinetPay
        payload = {
            "apikey": apikey,
            "site_id": site_id,
            "transaction_id": transaction_id,
            "amount": amount_int,
            "currency": "XAF",
            "description": description[:50],
            "return_url": return_url,
            "notify_url": notify_url,
            "channels": "ALL",
            "metadata": f"cart_user_{user.id}",
            "customer_name": customer_name,
            "customer_surname": customer_surname,
            "customer_email": customer_email,
            "customer_phone_number": customer_phone,
            "customer_address": getattr(user, 'address', 'Abidjan')[:50],
            "customer_city": getattr(user, 'city', 'Abidjan')[:30],
            "customer_country": "CM",
            "customer_zip_code": getattr(user, 'zip_code', '00225')[:10],
            "customer_state": getattr(user, 'state', 'Abidjan')[:30],
            "mode": "test"
        }
        
        logger.info(f"Envoi requête CinetPay pour panier: {payload}")
        
        try:
            response = requests.post(
                "https://api-checkout.cinetpay.com/v2/payment",
                json=payload,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                timeout=30
            )
            
            logger.info(f"Réponse CinetPay panier - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '201':
                    return redirect(data['data']['payment_url'])
                else:
                    error_message = data.get('message', 'Erreur inconnue')
                    return redirect(f"{reverse('users:payment-error')}?message={error_message}")
            else:
                error_details = response.text
                return redirect(f"{reverse('users:payment-error')}?message=Erreur HTTP {response.status_code}&details={error_details}")
                
        except Exception as e:
            error_message = f"Erreur: {str(e)}"
            return redirect(f"{reverse('users:payment-error')}?message={error_message}")

initiate_cart_payment_view = InitiateCartPaymentView.as_view()

@method_decorator(csrf_exempt, name='dispatch')
class PaymentConfirmView(View):
    def get(self, request):
        transaction_id = request.GET.get('transaction_id')
        return self.process_payment(request, transaction_id)
    
    def post(self, request):
        transaction_id = request.POST.get('transaction_id')
        return self.process_payment(request, transaction_id)
    
    def process_payment(self, request, transaction_id):
        if not transaction_id:
            logger.error("Transaction ID manquant dans la confirmation de paiement")
            return redirect(f"{reverse('users:payment-error')}?message=Transaction ID manquant")
        
        # Vérifier le statut de la transaction
        apikey = getattr(settings, 'CINETPAY_API_KEY', '57291868268684b617a2858.66115218')
        site_id = getattr(settings, 'CINETPAY_SITE_ID', '105905628')
        
        payload = {
            "apikey": apikey,
            "site_id": site_id,
            "transaction_id": transaction_id
        }
        
        logger.info(f"Vérification du statut de la transaction: {transaction_id}")
        
        try:
            response = requests.post(
                "https://api-checkout.cinetpay.com/v2/payment/check",
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=30
            )
            
            logger.info(f"Réponse vérification statut: {response.status_code}, {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                status = data['data'].get('status', 'UNKNOWN')
                
                if status == 'ACCEPTED':
                    logger.info(f"Paiement réussi pour la transaction: {transaction_id}")
                    # Paiement réussi, enregistrer la commande
                    # Order.objects.create(...)
                    return redirect(reverse('users:payment-success') + f'?transaction_id={transaction_id}')
                else:
                    error_message = f"Le paiement a échoué. Statut: {status}"
                    logger.warning(f"{error_message} pour la transaction: {transaction_id}")
                    return redirect(f"{reverse('users:payment-error')}?message={error_message}&transaction_id={transaction_id}")
            else:
                error_message = f"Impossible de vérifier le statut du paiement. HTTP {response.status_code}"
                logger.error(f"{error_message} pour la transaction: {transaction_id}")
                return redirect(f"{reverse('users:payment-error')}?message={error_message}&transaction_id={transaction_id}")
                
        except requests.exceptions.RequestException as e:
            error_message = f"Erreur technique lors de la vérification: {str(e)}"
            logger.error(f"{error_message} pour la transaction: {transaction_id}")
            return redirect(f"{reverse('users:payment-error')}?message={error_message}&transaction_id={transaction_id}")

payment_confirm_view = PaymentConfirmView.as_view()

@method_decorator(csrf_exempt, name='dispatch')
class PaymentNotifyView(View):
    def post(self, request):
        # Traiter les notifications de paiement (webhook)
        transaction_id = request.POST.get('transaction_id')
        status = request.POST.get('status')
        amount = request.POST.get('amount')
        currency = request.POST.get('currency')
        
        logger.info(f"Notification de paiement reçue - Transaction: {transaction_id}, Statut: {status}, Montant: {amount} {currency}")
        
        # Vérifier la signature pour sécurité (à implémenter)
        # ...
        
        if transaction_id and status == 'ACCEPTED':
            # Mettre à jour le statut de la transaction en base de données
            try:
                # transaction = Transaction.objects.get(transaction_id=transaction_id)
                # transaction.status = 'completed'
                # transaction.save()
                logger.info(f"Paiement confirmé via notification pour la transaction: {transaction_id}")
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour de la transaction {transaction_id}: {str(e)}")
            
        return HttpResponse(status=200)

payment_notify_view = PaymentNotifyView.as_view()

class PaymentSuccessView(View):
    def get(self, request):
        transaction_id = request.GET.get('transaction_id', '')
        logger.info(f"Affichage page de succès pour la transaction: {transaction_id}")
        # Afficher une page de succès
        return HttpResponse(f"""
        <html>
            <head>
                <title>Paiement Réussi</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f8f9fa;">
                <div style="max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="color: green; font-size: 48px; margin-bottom: 20px;">✅</div>
                    <h1 style="color: green; margin-bottom: 20px;">Paiement Réussi !</h1>
                    <p style="font-size: 16px; color: #555; margin-bottom: 15px;">Merci pour votre achat. Votre transaction a été traitée avec succès.</p>
                    {f'<p style="font-size: 14px; color: #777;"><strong>ID de transaction:</strong> {transaction_id}</p>' if transaction_id else ''}
                    <p style="font-size: 15px; color: #555; margin-top: 20px;">Vous recevrez un email de confirmation sous peu.</p>
                    <div style="margin-top: 30px;">
                        <a href="/" style="display: inline-block; margin: 10px; padding: 12px 25px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Retour à l'accueil
                        </a>
                    </div>
                </div>
            </body>
        </html>
        """)

payment_success_view = PaymentSuccessView.as_view()

class PaymentErrorView(View):
    def get(self, request):
        error_message = request.GET.get('message', 'Une erreur est survenue lors du paiement.')
        error_code = request.GET.get('code', '')
        transaction_id = request.GET.get('transaction_id', '')
        error_details = request.GET.get('details', '')
        
        logger.warning(f"Affichage page d'erreur: {error_message}, Code: {error_code}, Détails: {error_details}")
        
        # Afficher une page d'erreur avec plus de détails
        return HttpResponse(f"""
        <html>
            <head>
                <title>Erreur de Paiement</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f8f9fa;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="color: red; font-size: 48px; margin-bottom: 20px;">❌</div>
                    <h1 style="color: red; margin-bottom: 20px;">Erreur de Paiement</h1>
                    <p style="font-size: 16px; color: #555; margin-bottom: 15px;">{error_message}</p>
                    {f'<p style="font-size: 14px; color: #777;"><strong>Code d\'erreur:</strong> {error_code}</p>' if error_code else ''}
                    {f'<p style="font-size: 14px; color: #777;"><strong>ID de transaction:</strong> {transaction_id}</p>' if transaction_id else ''}
                    {f'<p style="font-size: 12px; color: #999; background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 15px;"><strong>Détails techniques:</strong> {error_details}</p>' if error_details else ''}
                    <p style="font-size: 15px; color: #555; margin-top: 20px;">Veuillez réessayer ou contacter le support si le problème persiste.</p>
                    <div style="margin-top: 30px;">
                        <a href="/" style="display: inline-block; margin: 10px; padding: 12px 25px; background: #dc3545; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Retour à l'accueil
                        </a>
                        <a href="javascript:history.back()" style="display: inline-block; margin: 10px; padding: 12px 25px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Retour au produit
                        </a>
                    </div>
                </div>
            </body>
        </html>
        """)

payment_error_view = PaymentErrorView.as_view()