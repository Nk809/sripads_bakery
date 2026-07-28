from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    ingredients = models.TextField(blank=True, null=True)
    weight_options = models.CharField(max_length=200, default="0.5 kg, 1 kg, 2 kg", help_text="Comma-separated weight options")
    default_weight = models.CharField(max_length=50, default="1 kg")
    price = models.DecimalField(max_digits=10, decimal_places=2) # Standard price for default weight
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='products/')
    image_2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='products/', blank=True, null=True)
    availability = models.BooleanField(default=True)
    delivery_time = models.CharField(max_length=100, default="24 hours")
    is_veg = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=10)
    is_featured = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    is_today_special = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def current_price(self):
        if self.discount_price:
            return self.discount_price
        return self.price

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    selected_weight = models.CharField(max_length=50, default="1 kg")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.selected_weight})"

    @property
    def item_total(self):
        price = self.product.current_price
        # Adjust price roughly based on weight (standard price is for 1 kg)
        # e.g., if 0.5 kg -> price * 0.5, if 2 kg -> price * 2, if 1 kg -> price
        weight_str = self.selected_weight.lower()
        multiplier = 1.0
        if '0.5' in weight_str or 'half' in weight_str:
            multiplier = 0.5
        elif '2' in weight_str:
            multiplier = 2.0
        elif '3' in weight_str:
            multiplier = 3.0
        elif '5' in weight_str:
            multiplier = 5.0
            
        return float(price) * multiplier * self.quantity

class Coupon(models.Model):
    COUPON_TYPE_CHOICES = (
        ('percentage', 'Discount Percentage'),
        ('bogo', 'Buy One Get One (BOGO)'),
        ('festival', 'Festival Offer (% Discount)'),
    )
    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPE_CHOICES, default='percentage')
    discount_percentage = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        if self.coupon_type == 'bogo':
            return f"{self.code} (BOGO)"
        return f"{self.code} ({self.discount_percentage}%)"

class BakerySettings(models.Model):
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=50.0)
    free_delivery_threshold = models.DecimalField(max_digits=6, decimal_places=2, default=500.0)

    def __str__(self):
        return "Sripad's Bakery Global Settings"
    
    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj
