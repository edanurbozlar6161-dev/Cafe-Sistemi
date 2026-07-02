from django import forms

from .models import Kategori, Urun


class UrunForm(forms.ModelForm):
    """Yönetim panelinde ürün ekleme/düzenleme formu (görsel yükleme dahil)."""

    class Meta:
        model = Urun
        fields = [
            "category", "name", "description", "price", "image",
            "stock_count", "stock_status", "sira",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Örn: Sütlü Latte"}
            ),
            "description": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Kısa açıklama (opsiyonel)"}
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "stock_count": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "placeholder": "Örn: 25"}
            ),
            "stock_status": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sira": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class KategoriForm(forms.ModelForm):
    """Yönetim panelinde kategori ekleme/düzenleme formu."""

    class Meta:
        model = Kategori
        fields = ["name", "emoji", "sira"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Örn: Tatlılar"}
            ),
            "emoji": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "🍰", "maxlength": 8}
            ),
            "sira": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }
