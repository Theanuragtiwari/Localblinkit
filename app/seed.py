from sqlalchemy.orm import Session

from .config import settings
from .models import Product, Shop, User
from .security import hash_password


DEFAULT_USERS = [
    ('Admin', 'admin@localquick.test', 'admin123', 'ADMIN'),
    ('Shop Owner', 'shop@localquick.test', 'shop123', 'SHOP_OWNER'),
    ('Delivery Rider', 'rider@localquick.test', 'rider123', 'DELIVERY_PARTNER'),
    ('Customer', 'customer@localquick.test', 'customer123', 'CUSTOMER'),
]


def seed_demo_data(db: Session):
    if db.query(Shop).count() > 0:
        return False

    users = []
    for name, email, password, role in DEFAULT_USERS:
        user = User(name=name, email=email, password_hash=hash_password(password), role=role, email_verified=True)
        db.add(user)
        users.append(user)
    db.commit()
    for user in users:
        db.refresh(user)

    shop = Shop(
        owner_id=users[1].id,
        name='Sharma General Store',
        area='Main Market',
        address='Main Market, Bhopal',
        lat=23.2599,
        lng=77.4126,
        radius_km=settings.DELIVERY_RADIUS_KM,
        delivery_fee=20,
        min_order=50,
        status='APPROVED',
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)

    products = [
        Product(shop_id=shop.id, name='Milk 1L', category='Dairy', price=60, mrp=65, stock=50),
        Product(shop_id=shop.id, name='Bread', category='Bakery', price=40, mrp=45, stock=30),
        Product(shop_id=shop.id, name='Eggs 12 Pack', category='Dairy', price=90, mrp=95, stock=40),
        Product(shop_id=shop.id, name='Maggi', category='Snacks', price=15, mrp=20, stock=100),
        Product(shop_id=shop.id, name='Rice 5kg', category='Grocery', price=350, mrp=390, stock=20),
    ]
    db.add_all(products)
    db.commit()
    return True
