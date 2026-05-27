from django import forms


class BadgePdfForm(forms.Form):
    file = forms.FileField(label="Badge PDF")
