from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import ChatMessage
from orders.models import Order
from notifications.models import Notification

@login_required
def chat_room(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    
    # Check authorization
    if not (request.user.is_seller or order.user == request.user):
        return HttpResponse("Unauthorized", status=401)
        
    # Mark messages from the other user as read
    ChatMessage.objects.filter(order=order, is_read=False).exclude(sender=request.user).update(is_read=True)
    
    context = {
        'order': order,
    }
    return render(request, 'chat/room.html', context)

@login_required
def get_messages(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    
    if not (request.user.is_seller or order.user == request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
        
    last_id = request.GET.get('last_id', 0)
    messages_query = ChatMessage.objects.filter(order=order)
    if last_id:
        messages_query = messages_query.filter(id__gt=last_id)
        
    # Mark messages as read when fetched
    ChatMessage.objects.filter(order=order, is_read=False).exclude(sender=request.user).update(is_read=True)
    
    messages_list = []
    for msg in messages_query:
        messages_list.append({
            'id': msg.id,
            'sender_id': msg.sender.id,
            'sender_username': msg.sender.username,
            'sender_role': msg.sender.role,
            'is_me': msg.sender == request.user,
            'message': msg.message,
            'image_url': msg.image.url if msg.image else None,
            'created_at': msg.created_at.strftime("%I:%M %p"),
        })
        
    return JsonResponse({
        'success': True,
        'messages': messages_list
    })

@login_required
@csrf_exempt
@require_POST
def send_message(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    
    if not (request.user.is_seller or order.user == request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
        
    message_text = request.POST.get('message', '').strip()
    image = request.FILES.get('image', None)
    
    if not message_text and not image:
        return JsonResponse({'success': False, 'message': 'Empty message.'}, status=400)
        
    msg = ChatMessage.objects.create(
        order=order,
        sender=request.user,
        message=message_text,
        image=image
    )
    
    # Create notification for recipient
    recipient = order.user if request.user.is_seller else None
    if not recipient:
        # If buyer sent the message, notify the sellers
        from accounts.models import CustomUser
        sellers = CustomUser.objects.filter(role='seller')
        for seller in sellers:
            Notification.objects.create(
                user=seller,
                title="New Chat Message",
                message=f"New message from {request.user.username} for order {order.order_number}.",
                link=f"/chat/room/{order.order_number}/"
            )
    else:
        Notification.objects.create(
            user=recipient,
            title="New Message from Bakery",
            message=f"The bakery sent a message for your order {order.order_number}.",
            link=f"/chat/room/{order.order_number}/"
        )
        
    return JsonResponse({
        'success': True,
        'message_id': msg.id,
        'message_text': msg.message,
        'image_url': msg.image.url if msg.image else None,
        'created_at': msg.created_at.strftime("%I:%M %p"),
    })
