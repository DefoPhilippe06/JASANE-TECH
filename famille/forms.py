from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(label="Nom complet", max_length=100, widget=forms.TextInput(attrs={
        'class': 'w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
        'placeholder': 'Votre nom',
    }))
    email = forms.EmailField(label="Adresse email", widget=forms.EmailInput(attrs={
        'class': 'w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
        'placeholder': 'votre@email.com',
    }))
    subject = forms.CharField(label="Sujet", max_length=150, widget=forms.TextInput(attrs={
        'class': 'w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
        'placeholder': 'Sujet de votre message',
    }))
    message = forms.CharField(label="Message", widget=forms.Textarea(attrs={
        'class': 'w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
        'placeholder': 'Votre message...',
        'rows': 4,
    }))
