from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from .models import Category, Product, CartItem, Coupon, BakerySettings, UploadedFile
from feedback.models import Feedback

def home(request):
    categories = Category.objects.all()[:6]
    featured_products = Product.objects.select_related('category').filter(is_featured=True, availability=True)[:4]
    best_sellers = Product.objects.select_related('category').filter(is_best_seller=True, availability=True)[:4]
    today_specials = Product.objects.select_related('category').filter(is_today_special=True, availability=True)[:4]
    new_arrivals = Product.objects.select_related('category').filter(is_new_arrival=True, availability=True).order_by('-created_at')[:4]
    
    # Get recent customer reviews (feedbacks with high rating)
    reviews = Feedback.objects.filter(rating__gte=4).order_by('-created_at')[:5]
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'best_sellers': best_sellers,
        'today_specials': today_specials,
        'new_arrivals': new_arrivals,
        'reviews': reviews,
    }
    return render(request, 'buyer/home.html', context)

def product_list(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    
    products = Product.objects.select_related('category').filter(availability=True)
    
    if query:
        products = products.filter(name__icontains=query) | products.filter(description__icontains=query)
        
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_slug,
    }
    return render(request, 'buyer/products.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category'), slug=slug)
    recommended = Product.objects.select_related('category').filter(category=product.category, availability=True).exclude(id=product.id)[:4]
    
    # Fetch reviews for this product
    reviews = Feedback.objects.filter(order_item__product=product).order_by('-created_at')
    
    # Parse weight options
    weights = [w.strip() for w in product.weight_options.split(',') if w.strip()]
    
    context = {
        'product': product,
        'recommended': recommended,
        'reviews': reviews,
        'weights': weights,
    }
    return render(request, 'buyer/product_detail.html', context)


@login_required
def cart_detail(request):
    from .models import BakerySettings
    settings_obj = BakerySettings.get_settings()
    delivery_rate = float(settings_obj.delivery_charge)
    threshold = float(settings_obj.free_delivery_threshold)
    
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.item_total for item in cart_items)
    
    # GST and Delivery Charges calculations
    gst = total * 0.05 / 1.05 # 5% GST inclusive for bakery products
    delivery_charges = delivery_rate if total < threshold and total > 0 else 0.0
    grand_total = total + delivery_charges
    
    # Calculate Advance and Remaining amounts (40% advance)
    advance_amount = grand_total * 0.40
    remaining_amount = grand_total * 0.60
    
    discount = 0.0
    coupon_code = request.session.get('coupon_code', None)
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now())
            if coupon.coupon_type == 'bogo':
                bogo_discount = 0.0
                for item in cart_items:
                    free_qty = item.quantity // 2
                    if free_qty > 0:
                        weight_str = item.selected_weight.lower()
                        multiplier = 1.0
                        if '0.5' in weight_str or 'half' in weight_str:
                            multiplier = 0.5
                        elif '2' in weight_str:
                            multiplier = 2.0
                        elif '3' in weight_str:
                            multiplier = 3.0
                        elif '5' in weight_str:
                            multiplier = 5.0
                        unit_price = float(item.product.current_price) * multiplier
                        bogo_discount += unit_price * free_qty
                discount = bogo_discount
            else:
                discount = total * (coupon.discount_percentage / 100.0)
            total_after_discount = total - discount
            gst = total_after_discount * 0.05 / 1.05
            delivery_charges = delivery_rate if total_after_discount < threshold and total_after_discount > 0 else 0.0
            grand_total = total_after_discount + delivery_charges
            advance_amount = grand_total * 0.40
            remaining_amount = grand_total * 0.60
        except Coupon.DoesNotExist:
            request.session.pop('coupon_code', None)
            
    context = {
        'cart_items': cart_items,
        'total': total,
        'discount': discount,
        'coupon_code': coupon_code,
        'gst': gst,
        'delivery_charges': delivery_charges,
        'grand_total': grand_total,
        'advance_amount': advance_amount,
        'remaining_amount': remaining_amount,
    }
    return render(request, 'buyer/cart.html', context)

@login_required
@require_POST
def add_to_cart(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    weight = request.POST.get('weight', '1 kg')
    
    product = get_object_or_404(Product, id=product_id)
    
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        selected_weight=weight,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
        
    return JsonResponse({
        'success': True,
        'message': f"Added {product.name} to cart.",
        'cart_count': CartItem.objects.filter(user=request.user).count()
    })

@login_required
@require_POST
def remove_from_cart(request):
    item_id = request.POST.get('item_id')
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    name = cart_item.product.name
    cart_item.delete()
    
    return JsonResponse({
        'success': True,
        'message': f"Removed {name} from cart."
    })

@login_required
@require_POST
def update_cart_quantity(request):
    item_id = request.POST.get('item_id')
    action = request.POST.get('action') # 'increase' or 'decrease'
    
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    
    if action == 'increase':
        cart_item.quantity += 1
        cart_item.save()
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            return JsonResponse({'success': True, 'deleted': True, 'message': "Item removed from cart."})
            
    return JsonResponse({
        'success': True,
        'quantity': cart_item.quantity,
        'item_total': cart_item.item_total,
        'message': "Cart updated."
    })

@login_required
@require_POST
def apply_coupon(request):
    code = request.POST.get('code', '').strip().upper()
    try:
        coupon = Coupon.objects.get(code=code, active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now())
        request.session['coupon_code'] = coupon.code
        return JsonResponse({
            'success': True,
            'message': f"Coupon '{code}' applied successfully!",
            'discount_percentage': coupon.discount_percentage
        })
    except Coupon.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': "Invalid or expired coupon code."
        })

@login_required
@require_POST
def remove_coupon(request):
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
    return JsonResponse({
        'success': True,
        'message': "Coupon removed."
    })

# --- SELLER PANEL VIEWS ---
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from orders.models import Order, OrderItem, Payment
from accounts.models import CustomUser
from chat.models import ChatMessage

def seller_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_seller:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@seller_required
def seller_dashboard(request):
    today = timezone.now().date()
    
    # Dashboard stats
    today_orders = Order.objects.filter(created_at__date=today).count()
    pending_orders = Order.objects.filter(order_status__in=['placed', 'payment_received', 'accepted', 'preparing', 'ready', 'out_for_delivery']).count()
    completed_orders = Order.objects.filter(order_status='delivered').count()
    cancelled_orders = Order.objects.filter(order_status='cancelled').count()
    
    # Revenue is sum of successful payments
    revenue = Payment.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0.0
    customers_count = CustomUser.objects.filter(role='buyer').count()
    products_count = Product.objects.all().count()
    
    # Unread messages from buyers
    unread_messages = ChatMessage.objects.filter(is_read=False).exclude(sender__role='seller').count()
    
    # Sales Chart Data (Last 7 days)
    seven_days_ago = today - timezone.timedelta(days=6)
    sales_over_time = (
        Payment.objects.filter(status='success', created_at__date__gte=seven_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(total=Sum('amount'))
        .order_by('date')
    )
    
    chart_dates = []
    chart_revenue = []
    # Fill in dates (even with 0 revenue)
    for i in range(7):
        d = seven_days_ago + timezone.timedelta(days=i)
        chart_dates.append(d.strftime('%b %d'))
        match = next((item for item in sales_over_time if item['date'] == d), None)
        chart_revenue.append(float(match['total']) if match else 0.0)
        
    # Top Products (by quantity ordered)
    top_items = (
        OrderItem.objects.values('product__name')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')[:5]
    )
    top_products_labels = [item['product__name'] or 'Deleted' for item in top_items]
    top_products_qty = [item['qty'] for item in top_items]

    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:5]
    
    context = {
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'revenue': revenue,
        'customers_count': customers_count,
        'products_count': products_count,
        'unread_messages': unread_messages,
        'chart_dates': json.dumps(chart_dates),
        'chart_revenue': json.dumps(chart_revenue),
        'top_products_labels': json.dumps(top_products_labels),
        'top_products_qty': json.dumps(top_products_qty),
        'recent_orders': recent_orders,
    }
    return render(request, 'seller/dashboard.html', context)

@seller_required
def seller_product_list(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'seller/products.html', context)

@seller_required
def seller_product_add(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        category = get_object_or_404(Category, id=category_id)
        description = request.POST.get('description', '')
        ingredients = request.POST.get('ingredients', '')
        weight_options = request.POST.get('weight_options', '0.5 kg, 1 kg, 2 kg')
        default_weight = request.POST.get('default_weight', '1 kg')
        price = request.POST.get('price')
        discount_price = request.POST.get('discount_price') or None
        stock_quantity = request.POST.get('stock_quantity', 10)
        availability = request.POST.get('availability') == 'on'
        
        is_featured = request.POST.get('is_featured') == 'on'
        is_best_seller = request.POST.get('is_best_seller') == 'on'
        is_today_special = request.POST.get('is_today_special') == 'on'
        is_new_arrival = request.POST.get('is_new_arrival') == 'on'
        is_veg = request.POST.get('is_veg') == 'on'
        
        image = request.FILES.get('image')
        image_2 = request.FILES.get('image_2')
        image_3 = request.FILES.get('image_3')
        
        Product.objects.create(
            name=name,
            category=category,
            description=description,
            ingredients=ingredients,
            weight_options=weight_options,
            default_weight=default_weight,
            price=price,
            discount_price=discount_price,
            stock_quantity=stock_quantity,
            availability=availability,
            is_featured=is_featured,
            is_best_seller=is_best_seller,
            is_today_special=is_today_special,
            is_new_arrival=is_new_arrival,
            is_veg=is_veg,
            image=image,
            image_2=image_2,
            image_3=image_3
        )
        return redirect('seller_product_list')
        
    context = {
        'categories': categories,
        'action': 'Add'
    }
    return render(request, 'seller/product_form.html', context)

@seller_required
def seller_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        category_id = request.POST.get('category')
        product.category = get_object_or_404(Category, id=category_id)
        product.description = request.POST.get('description', '')
        product.ingredients = request.POST.get('ingredients', '')
        product.weight_options = request.POST.get('weight_options', '0.5 kg, 1 kg, 2 kg')
        product.default_weight = request.POST.get('default_weight', '1 kg')
        product.price = request.POST.get('price')
        
        disc_price = request.POST.get('discount_price')
        product.discount_price = disc_price if disc_price else None
        
        product.stock_quantity = request.POST.get('stock_quantity', 10)
        product.availability = request.POST.get('availability') == 'on'
        product.is_featured = request.POST.get('is_featured') == 'on'
        product.is_best_seller = request.POST.get('is_best_seller') == 'on'
        product.is_today_special = request.POST.get('is_today_special') == 'on'
        product.is_new_arrival = request.POST.get('is_new_arrival') == 'on'
        product.is_veg = request.POST.get('is_veg') == 'on'
        
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'image_2' in request.FILES:
            product.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            product.image_3 = request.FILES['image_3']
            
        product.save()
        return redirect('seller_product_list')
        
    # Split weights
    weights = [w.strip() for w in product.weight_options.split(',') if w.strip()]
    
    context = {
        'product': product,
        'categories': categories,
        'weights': weights,
        'action': 'Edit'
    }
    return render(request, 'seller/product_form.html', context)

@seller_required
def seller_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    # Instead of deleting, we can toggle availability or hard delete. Let's do a hard delete as requested
    product.delete()
    return redirect('seller_product_list')

@seller_required
def seller_customers(request):
    # Retrieve all buyers and calculate their lifetime stats
    customers = CustomUser.objects.filter(role='buyer').annotate(
        order_count=Count('orders'),
        total_spend=Sum('orders__payments__amount', filter=Q(orders__payments__status='success'))
    )
    context = {
        'customers': customers
    }
    return render(request, 'seller/customers.html', context)

@seller_required
def seller_delete_customer(request, customer_id):
    customer = get_object_or_404(CustomUser, id=customer_id, role='buyer')
    customer.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.method == 'POST':
        return JsonResponse({'success': True, 'message': f'Customer {customer.username} deleted successfully.'})
    return redirect('seller_customers')

@seller_required
def seller_settings(request):
    settings_obj = BakerySettings.get_settings()
    if request.method == 'POST':
        settings_obj.delivery_charge = request.POST.get('delivery_charge')
        settings_obj.free_delivery_threshold = request.POST.get('free_delivery_threshold')
        settings_obj.save()
        messages.success(request, "Global bakery settings updated successfully.")
        return redirect('seller_settings')
        
    context = {
        'settings': settings_obj
    }
    return render(request, 'seller/settings.html', context)

@seller_required
def seller_coupon_list(request):
    coupons = Coupon.objects.all().order_by('-valid_to')
    context = {
        'coupons': coupons
    }
    return render(request, 'seller/coupon_list.html', context)

@seller_required
def seller_coupon_add(request):
    if request.method == 'POST':
        code = request.POST.get('code').strip().upper()
        coupon_type = request.POST.get('coupon_type')
        discount_percentage = request.POST.get('discount_percentage')
        if not discount_percentage:
            discount_percentage = 0
        if coupon_type == 'bogo':
            discount_percentage = 0
        active = request.POST.get('active') == 'on'
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')
        description = request.POST.get('description', '')

        if Coupon.objects.filter(code=code).exists():
            messages.error(request, f"Coupon code '{code}' already exists.")
            return render(request, 'seller/coupon_form.html', {'action': 'Add'})

        Coupon.objects.create(
            code=code,
            coupon_type=coupon_type,
            discount_percentage=discount_percentage,
            active=active,
            valid_from=valid_from,
            valid_to=valid_to,
            description=description
        )
        messages.success(request, f"Coupon code '{code}' created successfully.")
        return redirect('seller_coupon_list')

    return render(request, 'seller/coupon_form.html', {'action': 'Add'})

@seller_required
def seller_coupon_edit(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        coupon.coupon_type = request.POST.get('coupon_type')
        discount_percentage = request.POST.get('discount_percentage')
        if not discount_percentage:
            discount_percentage = 0
        if coupon.coupon_type == 'bogo':
            discount_percentage = 0
        coupon.discount_percentage = discount_percentage
        coupon.active = request.POST.get('active') == 'on'
        coupon.valid_from = request.POST.get('valid_from')
        coupon.valid_to = request.POST.get('valid_to')
        coupon.description = request.POST.get('description', '')
        coupon.save()
        messages.success(request, f"Coupon code '{coupon.code}' updated successfully.")
        return redirect('seller_coupon_list')

    valid_from_str = coupon.valid_from.strftime('%Y-%m-%dT%H:%M') if coupon.valid_from else ''
    valid_to_str = coupon.valid_to.strftime('%Y-%m-%dT%H:%M') if coupon.valid_to else ''

    context = {
        'coupon': coupon,
        'valid_from_str': valid_from_str,
        'valid_to_str': valid_to_str,
        'action': 'Edit'
    }
    return render(request, 'seller/coupon_form.html', context)

@seller_required
def seller_coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    code = coupon.code
    coupon.delete()
    messages.success(request, f"Coupon code '{code}' deleted successfully.")
    return redirect('seller_coupon_list')

from django.http import HttpResponse, Http404
from django.views.static import serve as django_serve
import os

def serve_db_media(request, path):
    clean_path = path.lstrip('/')
    try:
        obj = UploadedFile.objects.get(name=clean_path)
        response = HttpResponse(obj.content, content_type=obj.content_type)
        response['Content-Length'] = len(obj.content)
        response['Cache-Control'] = 'public, max-age=86400'
        return response
    except UploadedFile.DoesNotExist:
        from django.conf import settings
        local_path = os.path.join(settings.MEDIA_ROOT, clean_path)
        if os.path.exists(local_path):
            return django_serve(request, clean_path, document_root=settings.MEDIA_ROOT)
        raise Http404("File not found")

