from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Notification

@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:10]
    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'link': n.link or '#',
            'created_at': n.created_at.strftime("%I:%M %p"),
        })
    return JsonResponse({
        'success': True,
        'notifications': data,
        'count': Notification.objects.filter(user=request.user, is_read=False).count()
    })

@login_required
@csrf_exempt
@require_POST
def mark_as_read(request):
    notification_id = request.POST.get('id')
    if notification_id:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
    else:
        # Mark all as read
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        
    return JsonResponse({'success': True})
