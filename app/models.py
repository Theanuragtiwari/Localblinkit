from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Role(Base, TimestampMixin):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)


class User(Base, TimestampMixin):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), index=True, default='CUSTOMER')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class Shop(Base, TimestampMixin):
    __tablename__ = 'shops'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(180), index=True)
    area: Mapped[str] = mapped_column(String(180), default='')
    address: Mapped[str] = mapped_column(String(400), default='')
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=5.0)
    delivery_fee: Mapped[float] = mapped_column(Float, default=20.0)
    min_order: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default='APPROVED')
    open: Mapped[bool] = mapped_column(Boolean, default=True)


class ShopDocument(Base, TimestampMixin):
    __tablename__ = 'shop_documents'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey('shops.id'), index=True)
    document_type: Mapped[str] = mapped_column(String(60))
    document_url: Mapped[str] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(String(20), default='PENDING')


class ShopHour(Base, TimestampMixin):
    __tablename__ = 'shop_hours'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey('shops.id'), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    open_time: Mapped[str] = mapped_column(String(10))
    close_time: Mapped[str] = mapped_column(String(10))
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)


class DeliveryZone(Base, TimestampMixin):
    __tablename__ = 'delivery_zones'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    center_lat: Mapped[float] = mapped_column(Float)
    center_lng: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default='ACTIVE')


class Category(Base, TimestampMixin):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Product(Base, TimestampMixin):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey('shops.id'), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey('categories.id'))
    name: Mapped[str] = mapped_column(String(180), index=True)
    category: Mapped[str] = mapped_column(String(80), default='General')
    brand: Mapped[str] = mapped_column(String(120), default='')
    price: Mapped[float] = mapped_column(Float)
    mrp: Mapped[float] = mapped_column(Float, default=0.0)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    image: Mapped[str] = mapped_column(String(500), default='')


class ProductImage(Base, TimestampMixin):
    __tablename__ = 'product_images'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), index=True)
    image_url: Mapped[str] = mapped_column(String(500))


class Inventory(Base, TimestampMixin):
    __tablename__ = 'inventory'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), unique=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10)


class Address(Base, TimestampMixin):
    __tablename__ = 'addresses'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    label: Mapped[str] = mapped_column(String(20), default='OTHER')
    line1: Mapped[str] = mapped_column(String(255))
    line2: Mapped[str] = mapped_column(String(255), default='')
    city: Mapped[str] = mapped_column(String(80), default='')
    pincode: Mapped[str] = mapped_column(String(12), default='')
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)


class Cart(Base, TimestampMixin):
    __tablename__ = 'carts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, index=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey('shops.id'))


class CartItem(Base, TimestampMixin):
    __tablename__ = 'cart_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey('carts.id'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (UniqueConstraint('cart_id', 'product_id', name='uq_cart_product'),)


class Order(Base, TimestampMixin):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey('shops.id'), index=True)
    delivery_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), index=True)
    address: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    subtotal: Mapped[float] = mapped_column(Float)
    delivery_fee: Mapped[float] = mapped_column(Float)
    taxes: Mapped[float] = mapped_column(Float, default=0.0)
    discounts: Mapped[float] = mapped_column(Float, default=0.0)
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default='PLACED', index=True)
    payment_status: Mapped[str] = mapped_column(String(30), default='PENDING')
    payment_method: Mapped[str] = mapped_column(String(20), default='COD')
    payment_order_id: Mapped[str | None] = mapped_column(String(150))


class OrderItem(Base, TimestampMixin):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    name: Mapped[str] = mapped_column(String(180))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float)


class Payment(Base, TimestampMixin):
    __tablename__ = 'payments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), index=True)
    provider: Mapped[str] = mapped_column(String(40), default='RAZORPAY')
    provider_order_id: Mapped[str] = mapped_column(String(180), default='')
    provider_payment_id: Mapped[str] = mapped_column(String(180), default='')
    status: Mapped[str] = mapped_column(String(30), default='PENDING')
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(5), default='INR')
    signature: Mapped[str] = mapped_column(String(255), default='')


class Refund(Base, TimestampMixin):
    __tablename__ = 'refunds'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey('payments.id'), index=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default='PENDING')
    reason: Mapped[str] = mapped_column(String(255), default='')


class Coupon(Base, TimestampMixin):
    __tablename__ = 'coupons'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    discount_type: Mapped[str] = mapped_column(String(20), default='PERCENTAGE')
    discount_value: Mapped[float] = mapped_column(Float, default=0.0)
    min_order: Mapped[float] = mapped_column(Float, default=0.0)
    max_discount: Mapped[float] = mapped_column(Float, default=0.0)
    usage_limit: Mapped[int] = mapped_column(Integer, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CouponUsage(Base, TimestampMixin):
    __tablename__ = 'coupon_usage'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey('coupons.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), index=True)


class DeliveryPartner(Base, TimestampMixin):
    __tablename__ = 'delivery_partners'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default='OFFLINE')
    vehicle_type: Mapped[str] = mapped_column(String(40), default='BIKE')
    vehicle_number: Mapped[str] = mapped_column(String(40), default='')


class DeliveryAssignment(Base, TimestampMixin):
    __tablename__ = 'delivery_assignments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), unique=True, index=True)
    delivery_partner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    status: Mapped[str] = mapped_column(String(30), default='ASSIGNED')


class RiderLocation(Base, TimestampMixin):
    __tablename__ = 'rider_locations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)


class Notification(Base, TimestampMixin):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20), default='IN_APP')
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class Review(Base, TimestampMixin):
    __tablename__ = 'reviews'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int] = mapped_column(Integer)
    rating: Mapped[int] = mapped_column(Integer)
    review_text: Mapped[str] = mapped_column(Text, default='')


class Rating(Base, TimestampMixin):
    __tablename__ = 'ratings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(Base, TimestampMixin):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60), default='')
    details: Mapped[str] = mapped_column(Text, default='')
