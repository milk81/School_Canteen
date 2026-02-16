import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
MENU_FILE = os.path.join(DATA_DIR, 'menu.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')
PURCHASE_REQUESTS_FILE = os.path.join(DATA_DIR, 'purchase_requests.json')
REVIEWS_FILE = os.path.join(DATA_DIR, 'reviews.json')