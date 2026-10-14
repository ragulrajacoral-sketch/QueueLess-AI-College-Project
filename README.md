# QueueLess AI — Smart Shopping and Billing System

A full-stack college project starter built with Python Flask and SQLite.

## Features
- Product catalogue with search and category filters
- Add products to cart and update quantities
- Add products using a product code (QR scanner integration can be added)
- Automatic bill calculation
- Checkout order storage using SQLite
- Order receipt with a generated QR code
- Order history
- Simple content-based product recommendations
- Responsive web interface

## Requirements
- Python 3.10 or newer
- pip

## Run on Windows
1. Extract the project ZIP.
2. Open Command Prompt in the `queueless_ai_project` folder.
3. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the application:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

## Important notes
- The app uses sample products and local demo data.
- The checkout creates an order and a QR receipt; it does **not** process real payments.
- The product-code form simulates scanning. To support camera-based scanning, add a browser QR library and print QR labels that contain the product code.
- Before deployment, set a strong `SECRET_KEY`, turn off Flask debug mode, add authentication/authorization, validate all inputs, and use HTTPS.
- This is a project starter, not a production-ready billing or payment system.

## Main files
- `app.py`: Flask routes, SQLite database, cart, checkout, QR creation
- `templates/`: HTML pages
- `static/style.css`: responsive styling
