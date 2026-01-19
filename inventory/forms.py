from django import forms
from core.models import Outlet

class ExcelUploadForm(forms.Form):
    outlet = forms.ModelChoiceField(queryset=Outlet.objects.all())
    date = forms.DateField(widget=forms.SelectDateWidget)
    excel_file = forms.FileField()