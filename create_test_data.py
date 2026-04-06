#!/usr/bin/env python

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Product, ProductVariant

def create_test_products():
    
    products_data = [
        {
            'name': 'Нежные пионы',
            'description': 'Воздушный букет из розовых и белых пионов. Идеален для романтического подарка.',
            'variants': [
                {'size': 'S', 'price': 2500, 'is_available': True},
                {'size': 'M', 'price': 3500, 'is_available': True},
                {'size': 'L', 'price': 5000, 'is_available': True},
            ]
        },
        {
            'name': 'Страсть и розы',
            'description': 'Классический букет из красных роз с эвкалиптом. Для тех, кто ценит классику.',
            'variants': [
                {'size': 'S', 'price': 2000, 'is_available': True},
                {'size': 'M', 'price': 3000, 'is_available': True},
                {'size': 'L', 'price': 4500, 'is_available': False},
            ]
        },
        {
            'name': 'Летнее утро',
            'description': 'Нежный букет из лилий и ромашек. Скандинавский минимализм и свежесть.',
            'variants': [
                {'size': 'S', 'price': 1800, 'is_available': True},
                {'size': 'M', 'price': 2800, 'is_available': True},
                {'size': 'L', 'price': 3800, 'is_available': True},
            ]
        },
        {
            'name': 'Осенняя сказка',
            'description': 'Яркий букет с подсолнухами и георгинами. Тепло осени в каждом цветке.',
            'variants': [
                {'size': 'S', 'price': 2200, 'is_available': True},
                {'size': 'M', 'price': 3200, 'is_available': True},
                {'size': 'L', 'price': 4800, 'is_available': True},
            ]
        },
        {
            'name': 'Лавандовые мечты',
            'description': 'Ароматный букет из лаванды и полевых цветов. Прованс в вашем доме.',
            'variants': [
                {'size': 'S', 'price': 1900, 'is_available': True},
                {'size': 'M', 'price': 2900, 'is_available': False},
                {'size': 'L', 'price': 3900, 'is_available': True},
            ]
        },
        {
            'name': 'Белоснежная классика',
            'description': 'Элегантный букет из белых роз с гипсофилой. Идеален для свадьбы.',
            'variants': [
                {'size': 'S', 'price': 3000, 'is_available': True},
                {'size': 'M', 'price': 4500, 'is_available': True},
                {'size': 'L', 'price': 6500, 'is_available': True},
            ]
        },
    ]
    
    created_count = 0
    
    for product_data in products_data:
        if not Product.objects.filter(name=product_data['name']).exists():
            product = Product.objects.create(
                name=product_data['name'],
                description=product_data['description'],
                is_active=True
            )
            
            for variant_data in product_data['variants']:
                ProductVariant.objects.create(
                    product=product,
                    size=variant_data['size'],
                    price=variant_data['price'],
                    is_available=variant_data['is_available']
                )
            
            print(f'✅ Создан товар: {product.name}')
            created_count += 1
        else:
            print(f'⚠️  Товар уже существует: {product_data["name"]}')
    
    print(f'\n📊 Итого создано товаров: {created_count}')
    print('Теперь вы можете запустить сервер: python manage.py runserver')

if __name__ == '__main__':
    print('🌸 Создание тестовых данных для Bloom & Petal...\n')
    create_test_products()
