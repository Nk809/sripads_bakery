from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
import random
from .models import CustomUser

def buyer_signup(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if not (username and email and password):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'accounts/signup.html')
            
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/signup.html')
            
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'accounts/signup.html')
            
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'accounts/signup.html')
            
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            phone=phone,
            password=password,
            role='buyer'
        )
        login(request, user)
        messages.success(request, "Registration successful! Welcome to Sripad's Bakery.")
        return redirect('home')
        
    return render(request, 'accounts/signup.html')

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_seller:
            return redirect('seller_dashboard')
        return redirect('home')
        
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if login with email
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
            if user.is_seller:
                # Seller login requires Gmail OTP Verification
                code = str(random.randint(100000, 999999))
                request.session['pending_seller_login_user_id'] = user.id
                request.session['seller_verification_code'] = code
                
                subject = "Verification Code - Sripad's Bakery Admin Login"
                message = f"Hello {user.username},\n\nYour 2-Factor authentication code for logging into Sripad's Bakery Admin Panel is: {code}\n\nThis code will expire shortly."
                from_email = 'no-reply@sripadsbakery.com'
                recipient_list = [user.email]
                
                try:
                    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                    messages.success(request, "A verification code has been sent to your registered Gmail.")
                except Exception as e:
                    messages.warning(request, "Failed to send email. Code printed to console/logs.")
                    print(f"SMTP Error: {e}. Verification Code is: {code}")
                    
                return redirect('verify_login')
            else:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('home')
        else:
            messages.error(request, "Invalid username/email or password.")
            
    return render(request, 'accounts/login.html')

def verify_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_seller:
            return redirect('seller_dashboard')
        return redirect('home')
        
    pending_user_id = request.session.get('pending_seller_login_user_id')
    if not pending_user_id:
        messages.error(request, "No pending login session found. Please log in.")
        return redirect('login')
        
    user = get_object_or_404(CustomUser, id=pending_user_id)
    
    # Check for resending the verification code
    if request.GET.get('resend') == '1':
        code = str(random.randint(100000, 999999))
        request.session['seller_verification_code'] = code
        
        subject = "New Verification Code - Sripad's Bakery Admin Login"
        message = f"Hello {user.username},\n\nYour new 2-Factor authentication code is: {code}\n\nThis code will expire shortly."
        from_email = 'no-reply@sripadsbakery.com'
        recipient_list = [user.email]
        
        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            messages.success(request, "A new verification code has been sent to your Gmail.")
        except Exception as e:
            messages.warning(request, "Failed to send email. Code printed to console/logs.")
            print(f"SMTP Error: {e}. Resent Verification Code is: {code}")
            
        return redirect('verify_login')
        
    if request.method == 'POST':
        entered_code = request.POST.get('verification_code')
        actual_code = request.session.get('seller_verification_code')
        
        if entered_code == actual_code:
            login(request, user)
            messages.success(request, f"Gmail Verification successful! Welcome, {user.username}.")
            
            # Clean session variables
            request.session.pop('pending_seller_login_user_id', None)
            request.session.pop('seller_verification_code', None)
            
            return redirect('seller_dashboard')
        else:
            messages.error(request, "Invalid verification code. Please check your Gmail.")
            
    return render(request, 'accounts/verify_login.html', {'email': user.email})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.phone = request.POST.get('phone', '')
        user.email = request.POST.get('email', '')
        user.address = request.POST.get('address', '')
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
            
        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('profile')
        
    return render(request, 'accounts/profile.html')
