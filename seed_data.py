import os
import django
from django.utils import timezone
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sripads_bakery.settings')
django.setup()

from accounts.models import CustomUser
from bakery.models import Category, Product, Coupon

def create_mock_image(filepath, bg_color):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    Image.new('RGB', (400, 300), color=bg_color).save(filepath)

def seed():
    print("Cleaning old data...")
    # Delete existing to prevent duplicate or conflicting categories/products
    Product.objects.all().delete()
    Category.objects.all().delete()
    Coupon.objects.all().delete()

    print("Seeding database...")
    
    # 1. Programmatic Mock Images Generation
    create_mock_image('static/images/hero_banner.jpg', '#3E2723')
    
    category_images = {
        'sweet': '#FFD1DC', 'salty': '#FFF9C4', 'crispy': '#D7CCC8',
        'snacks': '#FFE0B2'
    }
    for slug, color in category_images.items():
        create_mock_image(f'media/categories/{slug}.jpg', color)

    product_images = {
        'truffle': '#5D4037', 'cheesecake': '#FFECB3', 'sourdough': '#D7CCC8',
        'cookies': '#8D6E63', 'cupcake': '#D32F2F', 'butter_bun': '#FFF9C4',
        'rusk': '#FFE0B2', 'puff': '#FFAB91', 'patties': '#B0BEC5'
    }
    for name, color in product_images.items():
        create_mock_image(f'media/products/{name}.jpg', color)

    # 2. Seeding Categories (Simple Names)
    categories = {}
    for cat_data in [
        {'name': 'Sweet Items', 'slug': 'sweet', 'description': 'Sweet cakes, pastries, and sweet treats.'},
        {'name': 'Salty Items', 'slug': 'salty', 'description': 'Salted breads, salty buns, and namkeen products.'},
        {'name': 'Crispy Items', 'slug': 'crispy', 'description': 'Crispy cookies, biscuits, toasts, and rusks.'},
        {'name': 'Snacks', 'slug': 'snacks', 'description': 'Fresh samosas, puffs, patties, and savory bakery snacks.'},
    ]:
        cat, _ = Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults={
                'name': cat_data['name'],
                'image': f"categories/{cat_data['slug']}.jpg",
                'description': cat_data['description']
            }
        )
        categories[cat_data['slug']] = cat

    # 3. Seeding Products
    products = [
        {
            'name': 'Belgian Chocolate Truffle Cake', 'category': 'sweet',
            'description': 'Rich layers of dark chocolate sponge smothered in Belgian ganache.',
            'ingredients': 'Belgian cocoa, premium chocolate chips, butter, sugar.',
            'weight_options': '0.5 kg, 1 kg, 2 kg', 'default_weight': '1 kg',
            'price': 850.00, 'discount_price': 750.00, 'image': 'products/truffle.jpg',
            'is_veg': True, 'is_featured': True, 'is_best_seller': True, 'stock_quantity': 15
        },
        {
            'name': 'New York Strawberry Cheesecake', 'category': 'sweet',
            'description': 'Classic dense cream cheese bake topped with strawberry compote.',
            'ingredients': 'Cream cheese, fresh strawberries, graham crackers.',
            'weight_options': '1 kg, 2 kg', 'default_weight': '1 kg',
            'price': 1200.00, 'discount_price': None, 'image': 'products/cheesecake.jpg',
            'is_veg': True, 'is_featured': True, 'is_today_special': True, 'stock_quantity': 8
        },
        {
            'name': 'Sweet Mawa Cupcake', 'category': 'sweet',
            'description': 'Rich and soft traditional cupcake loaded with premium mawa/khoya and dry fruits.',
            'ingredients': 'Mawa, milk, flour, butter, almonds, sugar.',
            'weight_options': '0.5 kg', 'default_weight': '0.5 kg',
            'price': 120.00, 'discount_price': 99.00, 'image': 'products/cupcake.jpg',
            'is_veg': True, 'is_featured': True, 'stock_quantity': 25
        },
        {
            'name': 'Salty Butter Bun', 'category': 'salty',
            'description': 'Soft local bakery bun stuffed with lightly salted premium butter spread.',
            'ingredients': 'Wheat flour, yeast, salted butter, sugar glaze.',
            'weight_options': '0.5 kg', 'default_weight': '0.5 kg',
            'price': 60.00, 'discount_price': 50.00, 'image': 'products/butter_bun.jpg',
            'is_veg': True, 'is_today_special': True, 'stock_quantity': 40
        },
        {
            'name': 'San Francisco Sourdough Bread', 'category': 'salty',
            'description': 'Authentic naturally fermented bread with a thick crust and tangy crumb.',
            'ingredients': 'Flour, sourdough starter culture, sea salt.',
            'weight_options': '0.5 kg', 'default_weight': '0.5 kg',
            'price': 180.00, 'discount_price': 160.00, 'image': 'products/sourdough.jpg',
            'is_veg': True, 'is_best_seller': True, 'stock_quantity': 20
        },
        {
            'name': 'Double Chocolate Chip Cookies', 'category': 'crispy',
            'description': 'Soft-baked cookies stuffed with dark and milk chocolate chunks.',
            'ingredients': 'Chocolate chunks, brown sugar, organic butter, flour.',
            'weight_options': '0.5 kg', 'default_weight': '0.5 kg',
            'price': 250.00, 'discount_price': None, 'image': 'products/cookies.jpg',
            'is_veg': True, 'is_best_seller': True, 'is_today_special': True, 'stock_quantity': 30
        },
        {
            'name': 'Crispy Rusk Toast', 'category': 'crispy',
            'description': 'Super crispy, twice-baked classic sweet-salty toast biscuits perfect for tea-time dipping.',
            'ingredients': 'Wheat flour, sugar, cardamom, milk solids.',
            'weight_options': '0.5 kg, 1 kg', 'default_weight': '0.5 kg',
            'price': 90.00, 'discount_price': 80.00, 'image': 'products/rusk.jpg',
            'is_veg': True, 'is_featured': True, 'stock_quantity': 50
        },
        {
            'name': 'Veg Potato Puff Samosa', 'category': 'snacks',
            'description': 'Crispy, multi-layered baked pastry puff filled with local spiced mashed potato and green peas.',
            'ingredients': 'Potato, green peas, spices, refined flour, butter.',
            'weight_options': '0.5 kg', 'default_weight': '0.5 kg',
            'price': 40.00, 'discount_price': 30.00, 'image': 'products/puff.jpg',
            'is_veg': True, 'is_best_seller': True, 'stock_quantity': 35
        },
        {
            'name': 'Bakery Paneer Patties', 'category': 'snacks',
            'description': 'Deliciously flaky baked pastry filled with spicy cottage cheese stuffing.',
            'ingredients': 'Paneer, capsicum, onions, spices, flour, butter.',
            'weight_options': '0.5 kg', 'default_weight': '0.5 kg',
            'price': 60.00, 'discount_price': 50.00, 'image': 'products/patties.jpg',
            'is_veg': True, 'is_today_special': True, 'stock_quantity': 25
        }
    ]
    for p_data in products:
        category_slug = p_data.pop('category')
        Product.objects.get_or_create(
            name=p_data['name'],
            defaults={**p_data, 'category': categories[category_slug]}
        )

    # 4. Seeding Coupons
    for code, pct in [('SWEET10', 10), ('SRIPAD50', 50)]:
        Coupon.objects.get_or_create(
            code=code,
            defaults={
                'discount_percentage': pct,
                'active': True,
                'valid_from': timezone.now() - timezone.timedelta(days=1),
                'valid_to': timezone.now() + timezone.timedelta(days=30)
            }
        )

    # 5. Seeding User Accounts (preserves updated user credentials)
    if not CustomUser.objects.filter(username='admin').exists():
        CustomUser.objects.create_superuser('admin', 'nkbiswal301@gmail.com', 'adminpassword', role='seller', phone='+91 9876543210')
    if not CustomUser.objects.filter(username='customer').exists():
        CustomUser.objects.create_user('customer', 'customer@gmail.com', 'customerpassword', role='buyer', phone='+91 9123456780')

    print("Seeding completed successfully!")

if __name__ == '__main__':
    seed()
