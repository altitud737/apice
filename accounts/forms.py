from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Company

class SignUpForm(UserCreationForm):
    company_name = forms.CharField(max_length=255, label="Nombre de la Empresa")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        company_name = self.cleaned_data.get('company_name')
        company = Company.objects.create(name=company_name)
        user.company = company
        if commit:
            user.save()
        return user
