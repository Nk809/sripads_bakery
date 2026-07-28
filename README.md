# Sripad's Bakery - Bakery Management Web Application

> **Tagline**: Freshly Baked, Just a Click Away.

Sripad's Bakery is a modern, responsive, and secure full-stack commercial bakery ordering and management web application. It features a complete **Buyer Panel** for browsing items, managing shopping carts, and placing customized orders, coupled with a **Seller (Admin) Panel** for product configuration, order tracking, real-time client chat, and business analytics.

---

## 🌟 Key Features

1.  **Dual Dashboard Layout**: Completely isolated spaces for Buyers and Seller (Admin).
2.  **Order Splits (40% Advance)**: Automatically calculates a 40% advance requirement during checkout. Remaining 60% is collected on delivery/pickup.
3.  **Secure Simulation Payments**: Simulates a Razorpay gateway to easily test payment failure/success.
4.  **Real-Time Sync**: Chat message exchange, order status updates, and notification badges refresh instantly using optimized polling.
5.  **Interactive Analytics**: Chart.js lines and doughnut charts for sales statistics and bestseller counts on the seller dashboard.
6.  **RESTful APIs**: Django Rest Framework (DRF) serializers and views built-in for easy future integration with Flutter or React Native Android apps.
7.  **Luxury Theme Styling**: Tailored warm luxury color scheme (Dark Chocolate, Warm Honey, Soft Cream) using custom Poppins typography.

---

## 🛠️ Technology Stack

*   **Backend**: Django (Python 3)
*   **APIs**: Django Rest Framework (DRF)
*   **Database**: SQLite (default for development), support for PostgreSQL.
*   **Frontend**: HTML5, CSS3, JavaScript (ES6), Bootstrap 5, Font Awesome 6, Google Fonts.

---

## 📁 Folder Structure

```
sripads_bakery/
│
├── manage.py
├── create_mock_data.py  # Seeder script
├── db.sqlite3           # SQLite Database
│
├── sripads_bakery/      # Core settings and URL configs
│   ├── settings.py
│   ├── urls.py
│   ├── api_urls.py
│   └── api_views.py
│
├── accounts/            # Users, registration, login
├── bakery/              # Products, categories, shopping cart
├── orders/              # Checkout, tracking, payments, invoices
├── chat/                # Real-time message exchange
├── feedback/            # Star ratings and replies
├── notifications/       # User alert logs
│
├── static/              # CSS styling and assets
│   └── css/style.css
└── templates/           # HTML templates
    ├── base.html
    ├── accounts/
    ├── buyer/
    ├── seller/
    └── chat/
```

---

## 🚀 Installation & Running Guide

Follow these steps to run the application locally on your machine:

### 1. Set Up Environment
Make sure you have Python installed. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
Install Django and Django Rest Framework:
```bash
pip install django djangorestframework pillow
```
*(Pillow is required for image file upload fields)*

### 3. Run Database Migrations
Generate and execute database schema setup:
```bash
python manage.py makemigrations accounts bakery orders chat feedback notifications
python manage.py migrate
```

### 4. Seed Database (Mock Data)
Seed the database with pre-configured products, categories, coupons, and credentials:
```bash
python create_mock_data.py
```

This registers the following default users:
*   **Seller Admin account**:
    *   **Username**: `admin`
    *   **Password**: `admin123`
*   **Buyer / Customer account**:
    *   **Username**: `buyer`
    *   **Password**: `buyer123`

### 5. Launch Development Server
```bash
python manage.py runserver
```
Visit the application at `http://127.0.0.1:8000/` in your browser.

---

## 📡 REST API Documentation

All API views are protected where appropriate, and return clean JSON formatting.

*   `POST /api/auth/login/`: Authenticats credentials and starts session.
*   `POST /api/auth/register/`: Registers a new buyer profile.
*   `GET /api/categories/`: Returns all product categories.
*   `GET /api/products/`: Lists available bakery items. Optional query param `?category=slug` filters list.
*   `GET /api/cart/`: Fetch active user shopping cart details.
*   `POST /api/cart/`: Append product item to cart. (Requires `product_id`, `quantity`, `weight`).
*   `GET /api/orders/`: Lists active orders (filtered for buyer, or entire list for seller).
*   `GET /api/chat/<order_number>/`: Lists messages history for specified order.
*   `POST /api/chat/<order_number>/`: Post a message/image.
