
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100, verbose_name='Имя')),
                ('phone', models.CharField(max_length=20, verbose_name='Телефон')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('address', models.TextField(verbose_name='Адрес доставки')),
                ('delivery_date', models.DateField(verbose_name='Дата доставки')),
                ('comment', models.TextField(blank=True, verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('status', models.CharField(choices=[('new', 'Новый'), ('confirmed', 'Подтверждён'), ('in_progress', 'В работе'), ('completed', 'Выполнен'), ('cancelled', 'Отменён')], default='new', max_length=20, verbose_name='Статус')),
                ('total_cost', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма заказа')),
                ('delivery_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Стоимость доставки')),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Заказы',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название букета')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/', verbose_name='Изображение')),
                ('is_active', models.BooleanField(default=True, help_text='Снимите галочку, чтобы скрыть товар из каталога полностью.', verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товары',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.CharField(choices=[('S', 'Малый (Small)'), ('M', 'Средний (Medium)'), ('L', 'Большой (Large)')], max_length=1, verbose_name='Размер')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('is_available', models.BooleanField(default=True, help_text='Снимите галочку, если цветы для данного размера временно недоступны.', verbose_name='Доступен для предзаказа')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='catalog.product', verbose_name='Товар')),
            ],
            options={
                'verbose_name': 'Вариант товара',
                'verbose_name_plural': 'Варианты товаров',
                'ordering': ['product', 'size'],
                'unique_together': {('product', 'size')},
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=255, verbose_name='Название товара')),
                ('size', models.CharField(max_length=10, verbose_name='Размер')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Количество')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='catalog.order', verbose_name='Заказ')),
                ('product_variant', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='catalog.productvariant', verbose_name='Вариант товара')),
            ],
            options={
                'verbose_name': 'Элемент заказа',
                'verbose_name_plural': 'Элементы заказа',
            },
        ),
    ]
