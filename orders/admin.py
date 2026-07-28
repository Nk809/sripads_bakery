from django.contrib import admin
from .models import Order, OrderItem, Payment, Invoice

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'grand_total', 'advance_amount', 'payment_status', 'order_status', 'created_at')
    list_filter = ('order_status', 'payment_status', 'delivery_type', 'created_at')
    search_fields = ('order_number', 'name', 'phone', 'email')
    inlines = [OrderItemInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'amount', 'status', 'provider', 'created_at')
    list_filter = ('status', 'provider', 'created_at')
    search_fields = ('transaction_id', 'order__order_number')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'order', 'created_at')
    search_fields = ('invoice_number', 'order__order_number')
