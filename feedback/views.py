from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Feedback
from orders.models import Order, OrderItem
from notifications.models import Notification

@login_required
@csrf_exempt
@require_POST
def submit_feedback(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Check if order is delivered
    if order.order_status != 'delivered':
        return JsonResponse({'success': False, 'message': 'You can only leave feedback after the order has been delivered.'}, status=400)
        
    rating = int(request.POST.get('rating', 5))
    review_text = request.POST.get('review', '').strip()
    photo = request.FILES.get('photo', None)
    
    if not review_text:
        return JsonResponse({'success': False, 'message': 'Please write a review.'}, status=400)
        
    # Check if feedback already exists for this order
    if Feedback.objects.filter(order=order, user=request.user).exists():
        return JsonResponse({'success': False, 'message': 'Feedback already submitted for this order.'}, status=400)
        
    feedback = Feedback.objects.create(
        order=order,
        user=request.user,
        rating=rating,
        review=review_text,
        photo=photo
    )
    
    # Notify sellers
    from accounts.models import CustomUser
    sellers = CustomUser.objects.filter(role='seller')
    for seller in sellers:
        Notification.objects.create(
            user=seller,
            title="New Customer Feedback",
            message=f"{request.user.username} left a {rating}-star review for order {order.order_number}.",
            link=f"/orders/seller/feedback/"
        )
        
    return JsonResponse({'success': True, 'message': 'Thank you for your feedback!'})

@login_required
@csrf_exempt
@require_POST
def seller_reply_feedback(request, feedback_id):
    if not request.user.is_seller:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)
        
    feedback = get_object_or_404(Feedback, id=feedback_id)
    reply_text = request.POST.get('reply', '').strip()
    
    if not reply_text:
        return JsonResponse({'success': False, 'message': 'Please enter a reply.'}, status=400)
        
    feedback.reply = reply_text
    feedback.save()
    
    # Notify buyer
    Notification.objects.create(
        user=feedback.user,
        title="Bakery Replied to Your Feedback",
        message=f"The bakery owner replied to your feedback for order {feedback.order.order_number}.",
        link=f"/orders/track/{feedback.order.order_number}/"
    )
    
    return JsonResponse({'success': True, 'message': 'Reply submitted successfully.'})

@login_required
def seller_feedback_list(request):
    if not request.user.is_seller:
        return HttpResponse("Unauthorized", status=401)
    
    feedbacks = Feedback.objects.all().order_by('-created_at')
    context = {
        'feedbacks': feedbacks
    }
    return render(request, 'seller/feedback.html', context)
