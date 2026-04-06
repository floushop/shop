"""
Формы для приложения Catalog.
"""

from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Order

class OrderCreateForm(forms.ModelForm):
    """
    Форма для создания заказа (предзаказа).
    """
    delivery_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Дата доставки"
    )
    
    class Meta:
        model = Order
        fields = ['first_name', 'phone', 'email', 'address', 'delivery_date', 'comment']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите имя'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (999) 000-00-00'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Город, улица, дом, квартира'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Время доставки, пожелания к букету...'
            }),
        }
        labels = {
            'first_name': 'Имя *',
            'phone': 'Телефон *',
            'email': 'Email',
            'address': 'Адрес доставки *',
            'comment': 'Комментарий к заказу',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tomorrow = timezone.now().date() + timedelta(days=1)
        self.fields['delivery_date'].widget.attrs['min'] = tomorrow.isoformat()
    
    def clean_delivery_date(self):
        """
        Проверка, что дата доставки не сегодня и не в прошлом.
        """
        delivery_date = self.cleaned_data['delivery_date']
        today = timezone.now().date()
        
        if delivery_date <= today:
            raise forms.ValidationError(
                "Дата доставки должна быть не раньше завтрашнего дня."
            )
        
        return delivery_date
    
    def clean_phone(self):
        """
        Простая валидация телефона.
        """
        phone = self.cleaned_data['phone']
        digits = ''.join(filter(str.isdigit, phone))
        
        if len(digits) < 10:
            raise forms.ValidationError(
                "Введите корректный номер телефона."
            )
        
        return phone
