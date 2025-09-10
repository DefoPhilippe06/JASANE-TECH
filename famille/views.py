from django.shortcuts import render
from famille.partners.models import Partner
from .forms import ContactForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test

def home(request):
    partners = Partner.objects.all()  # Récupère tous les partenaires
    message_sent = False
    error_message = None
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            full_message = f"De: {name} <{email}>\n\n{message}"
            try:
                send_mail(
                    subject,
                    full_message,
                    settings.DEFAULT_FROM_EMAIL,
                    ['dphilippejunior@gmail.com'],
                    fail_silently=False,
                )
                message_sent = True
            except Exception as e:
                import traceback
                print('Erreur lors de l\'envoi du mail :', e)
                traceback.print_exc()
                error_message = "Une erreur est survenue lors de l'envoi du message."
        else:
            error_message = "Veuillez remplir correctement tous les champs."
    else:
        form = ContactForm()
    return render(request, 'home.html', {
        'partners': partners,
        'form': form,
        'message_sent': message_sent,
        'error_message': error_message,
    })

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def settings_view(request):
    return render(request, 'settings.html')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def dashboard(request):
    return render(request, 'dashboard.html')
