from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
import uuid

from accounts.models import CustomUser
from bakery.models import Category, Product, CartItem, Coupon
from orders.models import Order, OrderItem, Payment, Invoice
from chat.models import ChatMessage
from feedback.models import Feedback
from notifications.models import Notification

from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer, ProductSerializer,
    CartItemSerializer, OrderSerializer, ChatMessageSerializer, FeedbackSerializer,
    NotificationSerializer
)

# --- AUTHENTICATION ---

class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)  # Log user in
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username_or_email = request.data.get('username')
        password = request.data.get('password')
        
        user = None
        if '@' in username_or_email:
            try:
                user_obj = CustomUser.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                pass
        else:
            user = authenticate(request, username=username_or_email, password=password)
            
        if user is not None:
            login(request, user)
            return Response(UserSerializer(user).data)
        return Response({'message': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class ProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

# --- PRODUCT CATALOG ---

class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Product.objects.filter(availability=True)
        q = self.request.query_params.get('q')
        category = self.request.query_params.get('category')
        if q:
            queryset = queryset.filter(name__icontains=q) | queryset.filter(description__icontains=q)
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset

class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

# --- CART MANAGEMENT ---

class CartAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart_items = CartItem.objects.filter(user=request.user)
        serializer = CartItemSerializer(cart_items, many=True)
        total = sum(item.item_total for item in cart_items)
        gst = total * 0.05 / 1.05
        delivery = 50.0 if total < 500 and total > 0 else 0.0
        
        # Apply coupon if in session
        discount = 0.0
        coupon_code = request.session.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now())
                discount = total * (coupon.discount_percentage / 100.0)
                total_after_discount = total - discount
                gst = total_after_discount * 0.05 / 1.05
            except Coupon.DoesNotExist:
                request.session.pop('coupon_code', None)

        grand_total = total - discount + delivery
        
        return Response({
            'cart_items': serializer.data,
            'total': total,
            'discount': discount,
            'coupon_code': coupon_code,
            'gst': gst,
            'delivery_charges': delivery,
            'grand_total': grand_total,
            'advance_amount': grand_total * 0.40,
            'remaining_amount': grand_total * 0.60
        })

class CartAddAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        weight = request.data.get('weight', '1 kg')
        
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
            
        return Response({'success': True, 'message': 'Added to cart.'})

class CartRemoveAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        item_id = request.data.get('item_id')
        cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
        cart_item.delete()
        return Response({'success': True, 'message': 'Removed from cart.'})

class CartUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        item_id = request.data.get('item_id')
        action = request.data.get('action') # 'increase' or 'decrease'
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
                return Response({'success': True, 'deleted': True})
                
        return Response({'success': True, 'quantity': cart_item.quantity})

class CartCouponAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').strip().upper()
        action = request.data.get('action', 'apply') # 'apply' or 'remove'
        
        if action == 'remove':
            request.session.pop('coupon_code', None)
            return Response({'success': True, 'message': 'Coupon removed.'})
            
        try:
            coupon = Coupon.objects.get(code=code, active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now())
            request.session['coupon_code'] = coupon.code
            return Response({'success': True, 'message': 'Coupon applied.', 'discount_percentage': coupon.discount_percentage})
        except Coupon.DoesNotExist:
            return Response({'success': False, 'message': 'Invalid coupon.'}, status=status.HTTP_400_BAD_REQUEST)

# --- ORDERS ---

class OrderListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Checkout logic
        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items.exists():
            return Response({'message': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Extract delivery info
        name = request.data.get('name')
        phone = request.data.get('phone')
        email = request.data.get('email')
        address = request.data.get('address')
        delivery_date = request.data.get('delivery_date')
        delivery_time = request.data.get('delivery_time')
        delivery_type = request.data.get('delivery_type', 'delivery')
        special_instructions = request.data.get('special_instructions', '')
        
        if not (name and phone and email and address and delivery_date and delivery_time):
            return Response({'message': 'Missing fields'}, status=status.HTTP_400_BAD_REQUEST)

        # Financial computations
        total = sum(item.item_total for item in cart_items)
        discount = 0.0
        coupon_code = request.session.get('coupon_code')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, active=True, valid_from__lte=timezone.now(), valid_to__gte=timezone.now())
                discount = total * (coupon.discount_percentage / 100.0)
            except Coupon.DoesNotExist:
                request.session.pop('coupon_code', None)
                
        total_after_discount = total - discount
        gst = total_after_discount * 0.05 / 1.05
        delivery_charges = 50.0 if total_after_discount < 500 and delivery_type == 'delivery' else 0.0
        grand_total = total_after_discount + delivery_charges
        advance_amount = grand_total * 0.40
        remaining_amount = grand_total * 0.60
        
        order = Order.objects.create(
            user=request.user, total_amount=total, discount=discount, gst=gst,
            delivery_charges=delivery_charges, grand_total=grand_total,
            advance_amount=advance_amount, remaining_amount=remaining_amount,
            coupon_code=coupon_code, name=name, phone=phone, email=email,
            delivery_address=address, delivery_date=delivery_date, delivery_time=delivery_time,
            delivery_type=delivery_type, special_instructions=special_instructions,
            payment_status='pending', order_status='placed'
        )
        
        for item in cart_items:
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
                order=order, product=item.product, quantity=item.quantity,
                selected_weight=item.selected_weight, price=unit_price
            )
            # Stock update
            if item.product.stock_quantity >= item.quantity:
                item.product.stock_quantity -= item.quantity
                item.product.save()
                
        cart_items.delete()
        request.session.pop('coupon_code', None)
        
        # Notify
        Notification.objects.create(
            user=request.user, title="Order Placed",
            message=f"Order {order.order_number} placed. Pay advance to start prep.",
            link=f"/orders/payment/{order.order_number}/"
        )
        
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

class OrderDetailAPIView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'

    def get_object(self):
        order = super().get_object()
        if not (self.request.user.is_seller or order.user == self.request.user):
            raise permissions.exceptions.PermissionDenied()
        return order

class OrderCancelAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.order_status not in ['placed', 'payment_received']:
            return Response({'success': False, 'message': 'Cannot cancel accepted order.'}, status=status.HTTP_400_BAD_REQUEST)
            
        reason = request.data.get('reason', 'Cancelled by customer')
        order.order_status = 'cancelled'
        order.cancellation_reason = reason
        order.save()
        
        # Stock return
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
                
        Notification.objects.create(
            user=order.user, title="Order Cancelled",
            message=f"You cancelled order {order.order_number}."
        )
        return Response({'success': True, 'message': 'Order cancelled.'})

# --- PAYMENTS ---

class PaymentWebhookAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        transaction_id = request.data.get('transaction_id', 'TXN-' + uuid.uuid4().hex[:10].upper())
        
        order.payment_status = 'advance_paid'
        order.order_status = 'payment_received'
        order.save()
        
        Payment.objects.create(
            order=order, transaction_id=transaction_id, amount=order.advance_amount,
            status='success', provider='Razorpay'
        )
        Invoice.objects.create(order=order)
        
        # Notifications
        for seller in CustomUser.objects.filter(role='seller'):
            Notification.objects.create(
                user=seller, title="New Order Received",
                message=f"Order {order.order_number} paid and received."
            )
        Notification.objects.create(
            user=order.user, title="Advance Paid",
            message=f"Advance payment for {order.order_number} is successful."
        )
        return Response({'success': True, 'message': 'Payment logged.'})

# --- CHAT ---

class ChatMessageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number)
        if not (request.user.is_seller or order.user == request.user):
            return Response({'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        last_id = request.query_params.get('last_id', 0)
        messages = ChatMessage.objects.filter(order=order)
        if last_id:
            messages = messages.filter(id__gt=last_id)
            
        # Mark as read
        ChatMessage.objects.filter(order=order, is_read=False).exclude(sender=request.user).update(is_read=True)
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number)
        if not (request.user.is_seller or order.user == request.user):
            return Response({'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        message_text = request.data.get('message', '').strip()
        image = request.FILES.get('image')
        
        if not message_text and not image:
            return Response({'message': 'Empty message.'}, status=status.HTTP_400_BAD_REQUEST)
            
        msg = ChatMessage.objects.create(order=order, sender=request.user, message=message_text, image=image)
        
        # Notify recipient
        recipient = order.user if request.user.is_seller else None
        if not recipient:
            for seller in CustomUser.objects.filter(role='seller'):
                Notification.objects.create(
                    user=seller, title="New Chat Message",
                    message=f"New message from {request.user.username} for order {order.order_number}."
                )
        else:
            Notification.objects.create(
                user=recipient, title="New Message from Bakery",
                message=f"The bakery sent a message for your order {order.order_number}."
            )
            
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

# --- FEEDBACK ---

class FeedbackSubmitAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.order_status != 'delivered':
            return Response({'message': 'Order must be delivered.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if Feedback.objects.filter(order=order, user=request.user).exists():
            return Response({'message': 'Feedback already submitted.'}, status=status.HTTP_400_BAD_REQUEST)
            
        rating = int(request.data.get('rating', 5))
        review = request.data.get('review', '').strip()
        photo = request.FILES.get('photo')
        
        feedback = Feedback.objects.create(order=order, user=request.user, rating=rating, review=review, photo=photo)
        
        for seller in CustomUser.objects.filter(role='seller'):
            Notification.objects.create(
                user=seller, title="New Customer Feedback",
                message=f"{request.user.username} left a {rating}-star review."
            )
        return Response(FeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)

class FeedbackReplyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_seller:
            return Response({'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        feedback = get_object_or_404(Feedback, id=pk)
        reply = request.data.get('reply', '').strip()
        if not reply:
            return Response({'message': 'Reply cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
            
        feedback.reply = reply
        feedback.save()
        
        Notification.objects.create(
            user=feedback.user, title="Bakery Replied to Feedback",
            message=f"The bakery replied to your feedback for {feedback.order.order_number}."
        )
        return Response(FeedbackSerializer(feedback).data)

# --- NOTIFICATIONS ---

class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user, is_read=False)[:15]

class NotificationMarkReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        nid = request.data.get('id')
        if nid:
            noti = get_object_or_404(Notification, id=nid, user=request.user)
            noti.is_read = True
            noti.save()
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'success': True})

# --- SELLER ANALYTICS ---

class SellerAnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_seller:
            return Response({'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        today = timezone.now().date()
        today_orders = Order.objects.filter(created_at__date=today).count()
        pending_orders = Order.objects.filter(order_status__in=['placed', 'payment_received', 'accepted', 'preparing', 'ready', 'out_for_delivery']).count()
        completed_orders = Order.objects.filter(order_status='delivered').count()
        revenue = Payment.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0.0
        
        return Response({
            'today_orders_count': today_orders,
            'pending_orders_count': pending_orders,
            'completed_orders_count': completed_orders,
            'total_revenue_collected': revenue
        })
