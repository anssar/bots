from django.contrib import admin
from django import forms

from .models import TaxifishkaClient, City, CityGroup, OrderHistory, JuridicalClientGroup, ClientFamily, Settings


class CityForm(forms.ModelForm):
    help_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}), required=False)

    class Meta:
        model = City
        fields = '__all__'


class CityAdmin(admin.ModelAdmin):
    form = CityForm


admin.site.register(TaxifishkaClient)
admin.site.register(City, CityAdmin)
admin.site.register(CityGroup)
# admin.site.register(OrderHistory)
admin.site.register(JuridicalClientGroup)
admin.site.register(ClientFamily)
admin.site.register(Settings)
