from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('review', 'order__order_number', 'user__username')
