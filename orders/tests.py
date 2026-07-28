from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from orders.models import Order, Payment
import datetime

User = get_user_model()

class RemainingPaymentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testbuyer',
            email='testbuyer@example.com',
            password='password123',
            role='buyer'
        )
        self.client.login(username='testbuyer', password='password123')
        
        self.order = Order.objects.create(
            user=self.user,
            total_amount=100.00,
            discount=0.00,
            gst=5.00,
            delivery_charges=0.00,
            grand_total=100.00,
            advance_amount=40.00,
            remaining_amount=60.00,
            name='Test Buyer',
            phone='1234567890',
            email='testbuyer@example.com',
            delivery_address='123 Test St',
            delivery_date=datetime.date.today(),
            delivery_time='12:00 PM',
            payment_status='advance_paid',
            order_status='payment_received'
        )

    def test_payment_remaining_page_access(self):
        url = reverse('payment_remaining_page', kwargs={'order_number': self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'buyer/payment_remaining.html')

    def test_payment_remaining_page_redirect_if_not_advance_paid(self):
        self.order.payment_status = 'fully_paid'
        self.order.save()
        url = reverse('payment_remaining_page', kwargs={'order_number': self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_payment_remaining_success_api(self):
        url = reverse('payment_remaining_success', kwargs={'order_number': self.order.order_number})
        response = self.client.post(url, data='{"transaction_id": "TXN-TEST-123"}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'fully_paid')
        
        # Verify Payment record
        payment = Payment.objects.filter(order=self.order, transaction_id='TXN-TEST-123').first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, 60.00)

    def test_seller_verify_payment_success(self):
        seller = User.objects.create_user(
            username='testseller',
            email='testseller@example.com',
            password='password123',
            role='seller'
        )
        payment = Payment.objects.create(
            order=self.order,
            transaction_id='TXN-MOCK-1',
            amount=40.00,
            status='success',
            provider='Razorpay'
        )
        self.assertFalse(payment.is_verified)
        
        self.client.login(username='testseller', password='password123')
        url = reverse('seller_verify_payment', kwargs={'payment_id': payment.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        payment.refresh_from_db()
        self.assertTrue(payment.is_verified)

    def test_seller_verify_payment_unauthorized(self):
        payment = Payment.objects.create(
            order=self.order,
            transaction_id='TXN-MOCK-2',
            amount=40.00,
            status='success',
            provider='Razorpay'
        )
        
        # User is testbuyer (buyer role)
        url = reverse('seller_verify_payment', kwargs={'payment_id': payment.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        
        payment.refresh_from_db()
        self.assertFalse(payment.is_verified)

    def test_seller_delete_customer_success(self):
        seller = User.objects.create_user(
            username='testseller_del',
            email='testseller_del@example.com',
            password='password123',
            role='seller'
        )
        fake_buyer = User.objects.create_user(
            username='fake_buyer',
            email='fake@example.com',
            password='password123',
            role='buyer'
        )
        
        self.client.login(username='testseller_del', password='password123')
        url = reverse('seller_delete_customer', kwargs={'customer_id': fake_buyer.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(id=fake_buyer.id).exists())

    def test_seller_delete_customer_unauthorized(self):
        fake_buyer = User.objects.create_user(
            username='fake_buyer_2',
            email='fake2@example.com',
            password='password123',
            role='buyer'
        )
        
        url = reverse('seller_delete_customer', kwargs={'customer_id': fake_buyer.id})
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(id=fake_buyer.id).exists())

    def test_seller_login_requires_verification(self):
        self.client.logout()
        seller = User.objects.create_user(
            username='seller_2fa',
            email='seller_2fa@example.com',
            password='password123',
            role='seller'
        )
        url = reverse('login')
        response = self.client.post(url, {'username': 'seller_2fa', 'password': 'password123'})
        self.assertRedirects(response, reverse('verify_login'))
        self.assertEqual(self.client.session.get('pending_seller_login_user_id'), seller.id)
        self.assertIsNotNone(self.client.session.get('seller_verification_code'))

    def test_seller_login_verification_success(self):
        self.client.logout()
        seller = User.objects.create_user(
            username='seller_2fa_success',
            email='seller_2fa_success@example.com',
            password='password123',
            role='seller'
        )
        self.client.post(reverse('login'), {'username': 'seller_2fa_success', 'password': 'password123'})
        session = self.client.session
        code = session.get('seller_verification_code')
        response = self.client.post(reverse('verify_login'), {'verification_code': code})
        self.assertRedirects(response, reverse('seller_dashboard'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_seller_login_verification_failure(self):
        self.client.logout()
        User.objects.create_user(
            username='seller_2fa_fail',
            email='seller_2fa_fail@example.com',
            password='password123',
            role='seller'
        )
        self.client.post(reverse('login'), {'username': 'seller_2fa_fail', 'password': 'password123'})
        response = self.client.post(reverse('verify_login'), {'verification_code': '000000'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_order_has_unread_messages(self):
        from chat.models import ChatMessage
        self.assertFalse(self.order.has_unread_messages)
        ChatMessage.objects.create(
            order=self.order,
            sender=self.user,
            message='Hello, is my cake ready?'
        )
        self.assertTrue(self.order.has_unread_messages)
        
        seller = User.objects.create_user(
            username='seller_msg',
            email='seller_msg@example.com',
            password='password123',
            role='seller'
        )
        ChatMessage.objects.create(
            order=self.order,
            sender=seller,
            message='Almost ready!',
            is_read=False
        )
        self.assertTrue(self.order.has_unread_messages)
        
        ChatMessage.objects.filter(order=self.order, sender=self.user).update(is_read=True)
        self.assertFalse(self.order.has_unread_messages)

    def test_checkout_with_cash_payment(self):
        from bakery.models import CartItem, Product, Category
        category = Category.objects.create(name='Cakes', slug='cakes')
        product = Product.objects.create(
            name='Test Cake',
            slug='test-cake',
            category=category,
            price=10.00,
            stock_quantity=10,
            availability=True
        )
        CartItem.objects.create(
            user=self.user,
            product=product,
            quantity=2,
            selected_weight='1 kg'
        )
        url = reverse('checkout')
        post_data = {
            'name': 'Test Buyer',
            'phone': '1234567890',
            'email': 'testbuyer@example.com',
            'delivery_type': 'pickup',
            'address': 'Self Pickup',
            'delivery_date': str(datetime.date.today()),
            'delivery_time': '10:00 AM - 1:00 PM',
            'payment_method': 'cash'
        }
        response = self.client.post(url, data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'buyer/payment_success_landing.html')
        
        # Verify order and payment created
        order = Order.objects.filter(user=self.user, total_amount=20.00).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.order_status, 'placed')
        
        payment = Payment.objects.filter(order=order).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.provider, 'Cash')
        self.assertEqual(payment.status, 'pending')
        self.assertFalse(payment.is_verified)

    def test_payment_cash_page_post(self):
        self.order.payment_status = 'pending'
        self.order.save()
        url = reverse('payment_cash', kwargs={'order_number': self.order.order_number})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'buyer/payment_success_landing.html')
        
        payment = Payment.objects.filter(order=self.order, provider='Cash').first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, 'pending')
        self.assertFalse(payment.is_verified)

    def test_seller_verify_cash_payment(self):
        seller = User.objects.create_user(
            username='testseller_cash',
            email='testseller_cash@example.com',
            password='password123',
            role='seller'
        )
        self.order.payment_status = 'pending'
        self.order.save()
        payment = Payment.objects.create(
            order=self.order,
            transaction_id='CASH-MOCK-1',
            amount=40.00,
            status='pending',
            provider='Cash'
        )
        
        self.client.login(username='testseller_cash', password='password123')
        url = reverse('seller_verify_payment', kwargs={'payment_id': payment.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        payment.refresh_from_db()
        self.assertTrue(payment.is_verified)
        self.assertEqual(payment.status, 'success')
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'advance_paid')
        self.assertEqual(self.order.order_status, 'payment_received')

    def test_payment_remaining_allowed_for_pending_status(self):
        self.order.payment_status = 'pending'
        self.order.save()
        
        # Should be allowed to access remaining payment page
        url_page = reverse('payment_remaining_page', kwargs={'order_number': self.order.order_number})
        response = self.client.get(url_page)
        self.assertEqual(response.status_code, 200)
        
        # Should be allowed to complete remaining payment via API
        url_success = reverse('payment_remaining_success', kwargs={'order_number': self.order.order_number})
        response = self.client.post(url_success, data='{"transaction_id": "TXN-TEST-999"}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'advance_paid')
