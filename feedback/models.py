from django.db import models
from django.conf import settings
from orders.models import Order, OrderItem

class Feedback(models.Model):
    RATING_CHOICES = (
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    )
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='feedbacks')
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=RATING_CHOICES, default=5)
    review = models.TextField()
    photo = models.ImageField(upload_to='feedbacks/', blank=True, null=True)
    reply = models.TextField(blank=True, null=True) # Owner reply
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback by {self.user.username} (Rating: {self.rating})"
