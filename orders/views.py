import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Order, OrderItem, Payment, Invoice
from bakery.models import CartItem, Coupon, Product
from notifications.models import Notification

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        return redirect('cart_detail')
        
    from bakery.models import BakerySettings
    settings_obj = BakerySettings.get_settings()

    total = sum(item.item_total for item in cart_items)
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
        except Coupon.DoesNotExist:
            request.session.pop('coupon_code', None)
            
    total_after_discount = total - discount
    gst = total_after_discount * 0.05 / 1.05
    delivery_charges = 0.0  # Set to 0 initially. Delivery fee will be determined by seller.
    grand_total = total_after_discount + delivery_charges
    advance_amount = grand_total * 0.40
    remaining_amount = grand_total * 0.60
    
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address', '')
        if not address:
            address = "Self Pickup from Sripad's Bakery Outlet"
        delivery_date = request.POST.get('delivery_date')
        delivery_time = request.POST.get('delivery_time')
        delivery_type = request.POST.get('delivery_type')
        special_instructions = request.POST.get('special_instructions', '')
        
        # Save delivery details to user profile for one-click reuse
        u = request.user
        if phone:
            u.phone = phone
        if address and delivery_type == 'delivery':
            u.address = address
        if name and not (u.first_name or u.last_name):
            parts = name.strip().split(' ', 1)
            if len(parts) == 2:
                u.first_name, u.last_name = parts[0], parts[1]
            else:
                u.first_name = parts[0]
        u.save()
        
        post_delivery_charges = 0.0  # Kept at 0.0 initially, seller updates it after reviewing address.
        post_grand_total = total_after_discount + float(post_delivery_charges)
        post_advance_amount = post_grand_total * 0.40
        post_remaining_amount = post_grand_total * 0.60
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=total,
            discount=discount,
            gst=gst,
            delivery_charges=post_delivery_charges,
            grand_total=post_grand_total,
            advance_amount=post_advance_amount,
            remaining_amount=post_remaining_amount,
            coupon_code=coupon_code,
            name=name,
            phone=phone,
            email=email,
            delivery_address=address,
            delivery_date=delivery_date,
            delivery_time=delivery_time,
            delivery_type=delivery_type,
            special_instructions=special_instructions,
            payment_status='pending',
            order_status='placed'
        )
        
        # Copy cart items to order items
        for item in cart_items:
            # Adjust price based on weight
            product_price = float(item.product.current_price)
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
            
            unit_price = product_price * multiplier

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                selected_weight=item.selected_weight,
                price=unit_price
            )
            # Update product stock
            if item.product.stock_quantity >= item.quantity:
                item.product.stock_quantity -= item.quantity
                item.product.save()
                
        # Clear cart and coupon from session
        cart_items.delete()
        request.session.pop('coupon_code', None)
        
        payment_method = request.POST.get('payment_method', 'online')
        
        if payment_method == 'cash':
            # Create a pending Cash payment log
            Payment.objects.create(
                order=order,
                transaction_id='CASH-' + uuid.uuid4().hex[:10].upper(),
                amount=order.advance_amount,
                status='pending',
                provider='Cash',
                is_verified=False
            )
            
            # Send notifications
            from accounts.models import CustomUser
            sellers = CustomUser.objects.filter(role='seller')
            for seller in sellers:
                Notification.objects.create(
                    user=seller,
                    title="New Cash Order (Unconfirmed)",
                    message=f"Order {order.order_number} has been placed via Cash. Advance payment of ₹{order.advance_amount:.2f} is pending.",
                    link=f"/orders/seller/manage/"
                )
                
            Notification.objects.create(
                user=request.user,
                title="Order Placed (Cash)",
                message=f"Your order {order.order_number} has been placed via Cash. Sripad's Bakery will review your order and contact you for confirmation.",
                link=f"/orders/track/{order.order_number}/"
            )
            
            return render(request, 'buyer/payment_success_landing.html', {
                'order': order,
                'is_advance': True,
                'is_cash': True
            })
            
        # Create notification for online order placed
        Notification.objects.create(
            user=request.user,
            title="Order Placed",
            message=f"Your order {order.order_number} has been placed. Please complete the advance payment.",
            link=f"/orders/payment/{order.order_number}/"
        )
        
        return redirect('payment_page', order_number=order.order_number)
        
    context = {
        'cart_items': cart_items,
        'total': total,
        'discount': discount,
        'gst': gst,
        'delivery_charges': delivery_charges,
        'grand_total': grand_total,
        'advance_amount': advance_amount,
        'remaining_amount': remaining_amount,
    }
    return render(request, 'buyer/checkout.html', context)

import hashlib
from django.conf import settings

def generate_payu_hash(txnid, amount, productinfo, firstname, email):
    """
    Generates request hash: sha512(key|txnid|amount|productinfo|firstname|email|||||||||||SALT)
    """
    key = settings.PAYU_MERCHANT_KEY
    salt = settings.PAYU_MERCHANT_SALT
    # Exactly 11 pipes between email and salt (for 10 UDF placeholders)
    hash_sequence = f"{key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{salt}"
    hash_obj = hashlib.sha512(hash_sequence.encode('utf-8'))
    return hash_obj.hexdigest().lower()

def verify_payu_response_hash(posted_hash, status, txnid, amount, productinfo, firstname, email):
    """
    Verifies response hash: sha512(SALT|status|||||||||||email|firstname|productinfo|amount|txnid|key)
    """
    key = settings.PAYU_MERCHANT_KEY
    salt = settings.PAYU_MERCHANT_SALT
    # Exactly 11 pipes between status and email (for 10 UDF placeholders)
    hash_sequence = f"{salt}|{status}|||||||||||{email}|{firstname}|{productinfo}|{amount}|{txnid}|{key}"
    hash_obj = hashlib.sha512(hash_sequence.encode('utf-8'))
    return hash_obj.hexdigest().lower() == posted_hash.lower()


@login_required
def payment_page(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.payment_status != 'pending':
        return redirect('order_tracking', order_number=order.order_number)
        
    amount = f"{order.advance_amount:.2f}"
    txnid = f"TXN-{order.order_number}-ADV"
    productinfo = f"Sripads Bakery Advance Order {order.order_number}"
    
    payu_hash = generate_payu_hash(
        txnid=txnid,
        amount=amount,
        productinfo=productinfo,
        firstname=order.name,
        email=order.email
    )
    
    domain = request.build_absolute_uri('/')[:-1]
    surl = f"{domain}/orders/payu-success/{order.order_number}/"
    furl = f"{domain}/orders/payu-failure/{order.order_number}/"
    
    context = {
        'order': order,
        'payu_url': settings.PAYU_URL,
        'payu_merchant_key': settings.PAYU_MERCHANT_KEY,
        'txnid': txnid,
        'amount': amount,
        'productinfo': productinfo,
        'firstname': order.name,
        'email': order.email,
        'phone': order.phone,
        'surl': surl,
        'furl': furl,
        'payu_hash': payu_hash
    }
    return render(request, 'buyer/payment.html', context)

@login_required
def payment_cash(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.payment_status != 'pending':
        return redirect('order_tracking', order_number=order.order_number)
        
    if request.method == 'POST':
        # Create a pending Cash payment if not already existing
        payment, created = Payment.objects.get_or_create(
            order=order,
            provider='Cash',
            defaults={
                'transaction_id': 'CASH-' + uuid.uuid4().hex[:10].upper(),
                'amount': order.advance_amount,
                'status': 'pending',
                'is_verified': False
            }
        )
        
        # Create notifications for bakery owner (broadcast)
        from accounts.models import CustomUser
        sellers = CustomUser.objects.filter(role='seller')
        for seller in sellers:
            Notification.objects.create(
                user=seller,
                title="New Cash Order (Unconfirmed)",
                message=f"Order {order.order_number} has been placed via Cash. Advance payment of ₹{order.advance_amount:.2f} is pending.",
                link=f"/orders/seller/manage/"
            )
            
        Notification.objects.create(
            user=order.user,
            title="Order Placed (Cash)",
            message=f"Your order {order.order_number} has been placed via Cash. Sripad's Bakery will review your order and contact you for confirmation.",
            link=f"/orders/track/{order.order_number}/"
        )
        
        return render(request, 'buyer/payment_success_landing.html', {
            'order': order,
            'is_advance': True,
            'is_cash': True
        })
        
    return redirect('payment_page', order_number=order.order_number)

@login_required
def payment_remaining_page(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.payment_status == 'fully_paid' or order.order_status in ['delivered', 'cancelled']:
        return redirect('order_tracking', order_number=order.order_number)
        
    amount = f"{order.remaining_amount:.2f}"
    txnid = f"TXN-{order.order_number}-REM"
    productinfo = f"Sripads Bakery Remaining Order {order.order_number}"
    
    payu_hash = generate_payu_hash(
        txnid=txnid,
        amount=amount,
        productinfo=productinfo,
        firstname=order.name,
        email=order.email
    )
    
    domain = request.build_absolute_uri('/')[:-1]
    surl = f"{domain}/orders/payu-success/{order.order_number}/"
    furl = f"{domain}/orders/payu-failure/{order.order_number}/"
    
    context = {
        'order': order,
        'payu_url': settings.PAYU_URL,
        'payu_merchant_key': settings.PAYU_MERCHANT_KEY,
        'txnid': txnid,
        'amount': amount,
        'productinfo': productinfo,
        'firstname': order.name,
        'email': order.email,
        'phone': order.phone,
        'surl': surl,
        'furl': furl,
        'payu_hash': payu_hash
    }
    return render(request, 'buyer/payment_remaining.html', context)

@csrf_exempt
def payu_success_callback(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    
    if request.method == 'POST':
        posted_hash = request.POST.get('hash', '')
        status = request.POST.get('status', '')
        txnid = request.POST.get('txnid', '')
        amount = request.POST.get('amount', '')
        productinfo = request.POST.get('productinfo', '')
        firstname = request.POST.get('firstname', '')
        email = request.POST.get('email', '')
        
        if verify_payu_response_hash(posted_hash, status, txnid, amount, productinfo, firstname, email):
            if status == 'success':
                is_advance = txnid.endswith('-ADV')
                
                if is_advance:
                    order.payment_status = 'advance_paid'
                    order.order_status = 'payment_received'
                    order.save()
                    
                    Payment.objects.create(
                        order=order,
                        transaction_id=txnid,
                        amount=order.advance_amount,
                        status='success',
                        provider='PayU',
                        is_verified=True
                    )
                    Invoice.objects.get_or_create(order=order)
                    
                    # Notifications
                    from accounts.models import CustomUser
                    sellers = CustomUser.objects.filter(role='seller')
                    for seller in sellers:
                        Notification.objects.create(
                            user=seller,
                            title="New Order Received (PayU)",
                            message=f"Order {order.order_number} has been paid and received.",
                            link=f"/orders/seller/manage/"
                        )
                    Notification.objects.create(
                        user=order.user,
                        title="Advance Payment Received",
                        message=f"Advance payment for {order.order_number} is successful.",
                        link=f"/orders/track/{order.order_number}/"
                    )
                else:
                    # Remaining payment
                    if order.payment_status == 'advance_paid':
                        order.payment_status = 'fully_paid'
                    else:
                        order.payment_status = 'advance_paid'
                    order.save()
                    
                    Payment.objects.create(
                        order=order,
                        transaction_id=txnid,
                        amount=order.remaining_amount,
                        status='success',
                        provider='PayU',
                        is_verified=True
                    )
                    
                    # Notifications
                    from accounts.models import CustomUser
                    sellers = CustomUser.objects.filter(role='seller')
                    for seller in sellers:
                        Notification.objects.create(
                            user=seller,
                            title="Full Payment Received (PayU)",
                            message=f"Order {order.order_number} has been fully paid online.",
                            link=f"/orders/seller/manage/"
                        )
                    Notification.objects.create(
                        user=order.user,
                        title="Remaining Payment Received",
                        message=f"Remaining payment for {order.order_number} is successful.",
                        link=f"/orders/track/{order.order_number}/"
                    )
                
                return render(request, 'buyer/payment_success_landing.html', {'order': order, 'is_advance': is_advance})
        
    return render(request, 'buyer/payment_failed_landing.html', {'order': order, 'error': 'Hash verification failed or transaction was invalid.'})

@csrf_exempt
def payu_failure_callback(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    txnid = request.POST.get('txnid', 'TXN-FAILED')
    error_msg = request.POST.get('field9_with_cd', 'Payment rejected by bank or cancelled by user.')
    
    # Log failed payment attempt
    Payment.objects.create(
        order=order,
        transaction_id=txnid,
        amount=order.advance_amount if txnid.endswith('-ADV') else order.remaining_amount,
        status='failed',
        provider='PayU'
    )
    
    return render(request, 'buyer/payment_failed_landing.html', {'order': order, 'error': error_msg})


@login_required
@csrf_exempt
def payment_remaining_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.payment_status == 'fully_paid' or order.order_status in ['delivered', 'cancelled']:
        return JsonResponse({'success': False, 'message': 'Order is already fully paid or finalized.'}, status=400)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            transaction_id = data.get('transaction_id', 'TXN-REM-' + uuid.uuid4().hex[:10].upper())
        except Exception:
            transaction_id = 'TXN-REM-' + uuid.uuid4().hex[:10].upper()
            
        # Update order status
        if order.payment_status == 'advance_paid':
            order.payment_status = 'fully_paid'
        else:
            order.payment_status = 'advance_paid'
        order.save()
        
        # Log payment
        Payment.objects.create(
            order=order,
            transaction_id=transaction_id,
            amount=order.remaining_amount,
            status='success',
            provider='Razorpay'
        )
        
        # Create notifications
        from accounts.models import CustomUser
        sellers = CustomUser.objects.filter(role='seller')
        for seller in sellers:
            Notification.objects.create(
                user=seller,
                title="Full Payment Received",
                message=f"Order {order.order_number} has been fully paid online.",
                link=f"/orders/seller/manage/"
            )
            
        Notification.objects.create(
            user=order.user,
            title="Remaining Payment Received",
            message=f"Remaining payment for {order.order_number} is successful. Thank you for the full payment!",
            link=f"/orders/track/{order.order_number}/"
        )
        
        return JsonResponse({'success': True, 'message': 'Remaining payment logged and order fully paid.'})
        
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

@login_required
@csrf_exempt
def payment_success_webhook(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if request.method == 'POST':
        try:
            # In simulation, transaction ID is passed or generated
            data = json.loads(request.body) if request.body else {}
            transaction_id = data.get('transaction_id', 'TXN-' + uuid.uuid4().hex[:10].upper())
        except Exception:
            transaction_id = 'TXN-' + uuid.uuid4().hex[:10].upper()
            
        # Update order status
        order.payment_status = 'advance_paid'
        order.order_status = 'payment_received'
        order.save()
        
        # Log payment
        Payment.objects.create(
            order=order,
            transaction_id=transaction_id,
            amount=order.advance_amount,
            status='success',
            provider='Razorpay'
        )
        
        # Generate Invoice
        Invoice.objects.create(order=order)
        
        # Create notification for bakery owner (broadcast)
        # In this multi-user structure, seller panel notifications are sent to users who are sellers
        from accounts.models import CustomUser
        sellers = CustomUser.objects.filter(role='seller')
        for seller in sellers:
            Notification.objects.create(
                user=seller,
                title="New Order Received",
                message=f"Order {order.order_number} has been paid and received.",
                link=f"/orders/seller/manage/"
            )
            
        Notification.objects.create(
            user=order.user,
            title="Advance Payment Received",
            message=f"Advance payment for {order.order_number} is successful. Bakery is processing your order.",
            link=f"/orders/track/{order.order_number}/"
        )
        
        return JsonResponse({'success': True, 'message': 'Payment logged and order confirmed.'})
        
    return JsonResponse({'success': False, 'message': 'Invalid request.'})

@login_required
def order_tracking(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    
    # Secure check: only buyer who placed order or seller can view tracking
    if not (request.user.is_seller or order.user == request.user):
        return HttpResponse("Unauthorized", status=401)
        
    context = {
        'order': order,
    }
    return render(request, 'buyer/tracking.html', context)

@login_required
def order_history(request):
    if request.user.is_seller:
        return redirect('seller_orders')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'buyer/order_history.html', context)

@login_required
def download_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not (request.user.is_seller or order.user == request.user):
        return HttpResponse("Unauthorized", status=401)
        
    invoice = get_object_or_404(Invoice, order=order)
    context = {
        'order': order,
        'invoice': invoice,
    }
    return render(request, 'buyer/invoice.html', context)

@login_required
@csrf_exempt
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # A customer can cancel ONLY before the seller accepts the order
    if order.order_status in ['placed', 'payment_received']:
        reason = request.POST.get('reason', 'Customer cancelled')
        order.order_status = 'cancelled'
        order.cancellation_reason = reason
        order.save()
        
        # Return items to stock
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
                
        # Send notifications
        Notification.objects.create(
            user=order.user,
            title="Order Cancelled",
            message=f"You cancelled order {order.order_number}.",
            link="/orders/history/"
        )
        
        from accounts.models import CustomUser
        sellers = CustomUser.objects.filter(role='seller')
        for seller in sellers:
            Notification.objects.create(
                user=seller,
                title="Order Cancelled by Buyer",
                message=f"Order {order.order_number} has been cancelled by the buyer.",
                link="/orders/seller/manage/"
            )
            
        return JsonResponse({'success': True, 'message': 'Order cancelled successfully.'})
    else:
        return JsonResponse({'success': False, 'message': 'Cannot cancel order once it has been accepted by the bakery.'}, status=400)

@login_required
def reorder(request, order_number):
    old_order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Add items to cart again
    for item in old_order.items.all():
        if item.product and item.product.availability:
            CartItem.objects.create(
                user=request.user,
                product=item.product,
                quantity=item.quantity,
                selected_weight=item.selected_weight
            )
            
    return redirect('cart_detail')


# --- SELLER PANEL VIEWS ---
from django.views.decorators.http import require_POST
from accounts.models import CustomUser
from chat.models import ChatMessage

@login_required
def seller_dashboard(request):
    if not request.user.is_seller:
        return HttpResponse("Unauthorized", status=401)
        
    orders = Order.objects.all()
    products = Product.objects.all()
    
    # Calculate statistics
    today = timezone.now().date()
    today_orders = orders.filter(created_at__date=today).count()
    pending_orders = orders.exclude(order_status__in=['delivered', 'cancelled']).count()
    completed_orders = orders.filter(order_status='delivered').count()
    cancelled_orders = orders.filter(order_status='cancelled').count()
    
    total_revenue = sum(float(o.grand_total) for o in orders.filter(payment_status='fully_paid'))
    customers_count = CustomUser.objects.filter(role='buyer').count()
    products_count = products.count()
    unread_messages = ChatMessage.objects.filter(is_read=False).exclude(sender__role='seller').count()
    
    context = {
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'total_revenue': total_revenue,
        'customers_count': customers_count,
        'products_count': products_count,
        'unread_messages': unread_messages,
    }
    return render(request, 'seller/dashboard.html', context)


@login_required
def seller_orders(request):
    if not request.user.is_seller:
        return HttpResponse("Unauthorized", status=401)
        
    status_filter = request.GET.get('status', 'all')
    orders = Order.objects.all().order_by('-created_at')
    
    if status_filter == 'pending':
        orders = orders.filter(order_status__in=['placed', 'payment_received', 'accepted', 'preparing', 'ready', 'out_for_delivery'])
    elif status_filter == 'completed':
        orders = orders.filter(order_status='delivered')
    elif status_filter == 'cancelled':
        orders = orders.filter(order_status='cancelled')
    elif status_filter != 'all':
        orders = orders.filter(order_status=status_filter)
        
    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'seller/orders.html', context)

@login_required
@csrf_exempt
@require_POST
def seller_update_order_status(request, order_number):
    if not request.user.is_seller:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
        
    order = get_object_or_404(Order, order_number=order_number)
    new_status = request.POST.get('status')
    
    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'message': 'Invalid status.'}, status=400)
        
    order.order_status = new_status
    
    # If marked as delivered, complete the full payment
    if new_status == 'delivered':
        order.payment_status = 'fully_paid'
        # Mark any pending cash payments as success and verified
        pending_payments = Payment.objects.filter(order=order, status='pending')
        for p in pending_payments:
            p.status = 'success'
            p.is_verified = True
            p.save()
            
        # Log remaining payment if not already fully recorded
        total_recorded_success = sum(p.amount for p in Payment.objects.filter(order=order, status='success'))
        if total_recorded_success < order.grand_total:
            remaining_to_log = order.grand_total - total_recorded_success
            Payment.objects.create(
                order=order,
                transaction_id='TXN-REM-' + uuid.uuid4().hex[:10].upper(),
                amount=remaining_to_log,
                status='success',
                provider='Cash/Card on Delivery',
                is_verified=True
            )
            
    order.save()
    
    # Send notification to buyer
    Notification.objects.create(
        user=order.user,
        title="Order Status Updated",
        message=f"Your order {order.order_number} is now: {order.get_order_status_display()}.",
        link=f"/orders/track/{order.order_number}/"
    )
    
    return JsonResponse({
        'success': True,
        'message': f"Order status updated to {order.get_order_status_display()}.",
        'status': order.order_status,
        'status_display': order.get_order_status_display()
    })

@login_required
@csrf_exempt
@require_POST
def seller_cancel_order(request, order_number):
    if not request.user.is_seller:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
        
    order = get_object_or_404(Order, order_number=order_number)
    reason = request.POST.get('reason', 'Cancelled by bakery')
    
    order.order_status = 'cancelled'
    order.cancellation_reason = reason
    order.save()
    
    # Return items to stock
    for item in order.items.all():
        if item.product:
            item.product.stock_quantity += item.quantity
            item.product.save()
            
    # Send notification to buyer
    Notification.objects.create(
        user=order.user,
        title="Order Cancelled by Bakery",
        message=f"Your order {order.order_number} has been cancelled. Reason: {reason}.",
        link=f"/orders/track/{order.order_number}/"
    )
    
    return JsonResponse({'success': True, 'message': 'Order cancelled successfully.'})

@csrf_exempt
@require_POST
def seller_set_delivery_charge(request, order_number):
    if not request.user.is_seller:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
        
    order = get_object_or_404(Order, order_number=order_number)
    try:
        delivery_charges = float(request.POST.get('delivery_charges', 0.0))
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid delivery charge format.'}, status=400)
        
    order.delivery_charges = delivery_charges
    # Recalculate totals
    total_after_discount = float(order.total_amount) - float(order.discount)
    gst_val = total_after_discount * 0.05 / 1.05
    order.grand_total = total_after_discount + delivery_charges
    order.remaining_amount = float(order.grand_total) - float(order.advance_amount)
    order.save()
    
    # Notify Customer
    Notification.objects.create(
        user=order.user,
        title="Delivery Charges Updated",
        message=f"Sripad's Bakery has updated the delivery charge for order {order.order_number} to ₹{delivery_charges:.2f}.",
        link=f"/orders/track/{order.order_number}/"
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'Delivery charge updated to ₹{delivery_charges:.2f}.',
        'grand_total': f'{order.grand_total:.2f}',
        'remaining_amount': f'{order.remaining_amount:.2f}'
    })

@login_required
@csrf_exempt
@require_POST
def seller_verify_payment(request, payment_id):
    if not request.user.is_seller:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
        
    payment = get_object_or_404(Payment, id=payment_id)
    payment.is_verified = True
    payment.status = 'success'
    payment.save()
    
    order = payment.order
    # If verifying the advance payment, transition the order statuses
    if order.payment_status == 'pending':
        order.payment_status = 'advance_paid'
        order.order_status = 'payment_received'
        order.save()
        Invoice.objects.get_or_create(order=order)
        
        # Notify buyer
        Notification.objects.create(
            user=order.user,
            title="Advance Payment Verified",
            message=f"Your payment of ₹{payment.amount} (ID: {payment.transaction_id}) has been verified. Sripad's Bakery is now preparing your order.",
            link=f"/orders/track/{order.order_number}/"
        )
    # If verifying a remaining payment
    elif order.payment_status == 'advance_paid' and payment.amount >= order.remaining_amount:
        order.payment_status = 'fully_paid'
        order.save()
        
        # Notify buyer
        Notification.objects.create(
            user=order.user,
            title="Remaining Payment Verified",
            message=f"Your remaining payment of ₹{payment.amount} (ID: {payment.transaction_id}) has been verified as authentic.",
            link=f"/orders/track/{order.order_number}/"
        )
    else:
        # Generic notification
        Notification.objects.create(
            user=order.user,
            title="Payment Verified",
            message=f"Your payment of ₹{payment.amount} (ID: {payment.transaction_id}) has been verified as authentic by Sripad's Bakery.",
            link=f"/orders/track/{order.order_number}/"
        )
    
    return JsonResponse({
        'success': True,
        'message': f"Payment {payment.transaction_id} marked as verified."
    })
