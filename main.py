
import json, math
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, String, Integer, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker
from passlib.context import CryptContext
from jose import jwt, JWTError

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./localquick.db"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_MINUTES: int = 1440
    DELIVERY_RADIUS_KM: float = 5
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    class Config:
        env_file = ".env"

settings = Settings()
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="CUSTOMER")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Shop(Base):
    __tablename__ = "shops"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=5)
    delivery_fee: Mapped[float] = mapped_column(Float, default=20)
    open: Mapped[bool] = mapped_column(Boolean, default=True)
    products: Mapped[list["Product"]] = relationship(back_populates="shop")

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80), default="General")
    price: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    image: Mapped[str] = mapped_column(String(500), default="")
    shop: Mapped[Shop] = relationship(back_populates="products")

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    delivery_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    address: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    subtotal: Mapped[float] = mapped_column(Float)
    delivery_fee: Mapped[float] = mapped_column(Float)
    total: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="PLACED")
    payment_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    payment_method: Mapped[str] = mapped_column(String(20), default="COD")
    payment_order_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    items: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class RiderLocation(Base):
    __tablename__ = "rider_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI(title="LocalQuick V3 Complete API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.rooms = {}

    async def connect(self, order_id, ws):
        await ws.accept()
        self.rooms.setdefault(order_id, []).append(ws)

    def disconnect(self, order_id, ws):
        if order_id in self.rooms and ws in self.rooms[order_id]:
            self.rooms[order_id].remove(ws)

    async def broadcast(self, order_id, payload):
        for ws in list(self.rooms.get(order_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(order_id, ws)

manager = ConnectionManager()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def make_token(user):
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def get_user(auth, db):
    if not auth:
        return None
    try:
        raw = auth.removeprefix("Bearer ").strip()
        payload = jwt.decode(raw, settings.JWT_SECRET, algorithms=["HS256"])
        return db.get(User, int(payload["sub"]))
    except (JWTError, ValueError, TypeError):
        return None

def require_user(auth, db, roles=None):
    user = get_user(auth, db)
    if not user or not user.active:
        raise HTTPException(401, "Authentication required")
    if roles and user.role not in roles:
        raise HTTPException(403, "Forbidden")
    return user

def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

class Register(BaseModel):
    name: str
    email: EmailStr
    password: str

class Login(BaseModel):
    email: EmailStr
    password: str

class CartItem(BaseModel):
    product_id: int
    quantity: int

class CreateOrder(BaseModel):
    shop_id: int
    address: str
    lat: float
    lng: float
    items: list[CartItem]
    payment_method: str = "COD"

class LocationUpdate(BaseModel):
    order_id: int
    lat: float
    lng: float

class ProductCreate(BaseModel):
    name: str
    category: str = "General"
    price: float
    stock: int = 0
    image: str = ""

@app.get("/")
def root():
    return {"service": "LocalQuick", "version": "3.0.0", "docs": "/docs"}

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/auth/register")
def register(data: Register, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(400, "Email already registered")
    user = User(name=data.name, email=email, password=pwd.hash(data.password), role="CUSTOMER")
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": make_token(user), "user": {"id": user.id, "name": user.name, "role": user.role}}

@app.post("/auth/login")
def login(data: Login, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=str(data.email).lower()).first()
    if not user or not pwd.verify(data.password, user.password):
        raise HTTPException(401, "Invalid credentials")
    return {"token": make_token(user), "user": {"id": user.id, "name": user.name, "role": user.role}}

@app.get("/shops")
def list_shops(lat: Optional[float] = None, lng: Optional[float] = None, db: Session = Depends(get_db)):
    result = []
    for shop in db.query(Shop).filter_by(open=True).all():
        d = None if lat is None or lng is None else haversine(lat, lng, shop.lat, shop.lng)
        if d is None or d <= shop.radius_km:
            result.append({
                "id": shop.id, "name": shop.name, "area": shop.area,
                "delivery_fee": shop.delivery_fee,
                "distance_km": round(d, 2) if d is not None else None,
            })
    return result

@app.get("/shops/{shop_id}")
def get_shop(shop_id: int, db: Session = Depends(get_db)):
    shop = db.get(Shop, shop_id)
    if not shop:
        raise HTTPException(404, "Shop not found")
    return {
        "id": shop.id, "name": shop.name, "area": shop.area,
        "delivery_fee": shop.delivery_fee,
        "radius_km": shop.radius_km,
        "products": [
            {"id": p.id, "name": p.name, "category": p.category,
             "price": p.price, "stock": p.stock, "image": p.image}
            for p in shop.products if p.active
        ]
    }

@app.post("/orders")
async def create_order(data: CreateOrder, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    customer = require_user(auth, db, ["CUSTOMER"])
    shop = db.get(Shop, data.shop_id)
    if not shop or not shop.open:
        raise HTTPException(400, "Shop unavailable")
    if haversine(data.lat, data.lng, shop.lat, shop.lng) > shop.radius_km:
        raise HTTPException(400, "Delivery address is outside this shop's delivery radius")
    subtotal = 0.0
    items = []
    for item in data.items:
        product = db.get(Product, item.product_id)
        if not product or product.shop_id != shop.id or not product.active:
            raise HTTPException(400, "Product unavailable")
        if item.quantity < 1 or product.stock < item.quantity:
            raise HTTPException(400, f"Insufficient stock: {product.name}")
        product.stock -= item.quantity
        subtotal += product.price * item.quantity
        items.append({
            "product_id": product.id, "name": product.name,
            "price": product.price, "quantity": item.quantity
        })
    order = Order(
        customer_id=customer.id, shop_id=shop.id,
        address=data.address, lat=data.lat, lng=data.lng,
        subtotal=subtotal, delivery_fee=shop.delivery_fee,
        total=subtotal + shop.delivery_fee,
        payment_method=data.payment_method,
        payment_status="PAID" if data.payment_method == "COD" else "PENDING",
        items=json.dumps(items)
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"id": order.id, "total": order.total, "status": order.status, "payment_status": order.payment_status}

@app.get("/orders")
def customer_orders(auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["CUSTOMER"])
    orders = db.query(Order).filter_by(customer_id=user.id).order_by(Order.created_at.desc()).all()
    return [{"id": o.id, "total": o.total, "status": o.status,
             "payment_status": o.payment_status, "delivery_id": o.delivery_id,
             "created_at": o.created_at.isoformat()} for o in orders]

@app.get("/orders/{order_id}")
def get_order(order_id: int, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db)
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if user.role == "CUSTOMER" and order.customer_id != user.id:
        raise HTTPException(403, "Forbidden")
    return {
        "id": order.id, "status": order.status, "payment_status": order.payment_status,
        "payment_method": order.payment_method, "address": order.address,
        "lat": order.lat, "lng": order.lng, "total": order.total,
        "delivery_id": order.delivery_id, "items": json.loads(order.items)
    }

@app.post("/payments/mock-success/{order_id}")
def mock_payment(order_id: int, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["CUSTOMER"])
    order = db.get(Order, order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(404, "Order not found")
    order.payment_status = "PAID"
    order.payment_method = "ONLINE"
    order.payment_order_id = f"mock_{order.id}"
    db.commit()
    return {"ok": True, "payment_status": "PAID"}

@app.get("/shop/orders")
def shop_orders(auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["SHOP"])
    shop = db.query(Shop).filter_by(owner_id=user.id).first()
    if not shop:
        raise HTTPException(404, "No shop assigned")
    orders = db.query(Order).filter_by(shop_id=shop.id).order_by(Order.created_at.desc()).all()
    return [{"id": o.id, "total": o.total, "status": o.status, "customer_id": o.customer_id} for o in orders]

@app.post("/shop/products")
def add_product(data: ProductCreate, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["SHOP"])
    shop = db.query(Shop).filter_by(owner_id=user.id).first()
    if not shop:
        raise HTTPException(404, "No shop assigned")
    p = Product(shop_id=shop.id, **data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name}

@app.post("/shop/orders/{order_id}/status")
def shop_status(order_id: int, status: str, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["SHOP"])
    shop = db.query(Shop).filter_by(owner_id=user.id).first()
    order = db.get(Order, order_id)
    if not shop or not order or order.shop_id != shop.id:
        raise HTTPException(404, "Order not found")
    if status not in {"ACCEPTED", "PACKED", "CANCELLED"}:
        raise HTTPException(400, "Invalid status")
    order.status = status
    db.commit()
    return {"ok": True, "status": order.status}

@app.get("/delivery/orders")
def delivery_orders(auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["DELIVERY"])
    orders = db.query(Order).filter(
        (Order.status == "PACKED") | (Order.delivery_id == user.id)
    ).order_by(Order.created_at.desc()).all()
    return [{"id": o.id, "shop_id": o.shop_id, "address": o.address,
             "status": o.status, "total": o.total, "delivery_id": o.delivery_id} for o in orders]

@app.post("/delivery/orders/{order_id}/accept")
def accept_delivery(order_id: int, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["DELIVERY"])
    order = db.get(Order, order_id)
    if not order or order.status != "PACKED":
        raise HTTPException(400, "Order is not available")
    order.delivery_id = user.id
    order.status = "OUT_FOR_DELIVERY"
    db.commit()
    return {"ok": True}

@app.post("/delivery/orders/{order_id}/delivered")
def delivered(order_id: int, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["DELIVERY"])
    order = db.get(Order, order_id)
    if not order or order.delivery_id != user.id:
        raise HTTPException(403, "Forbidden")
    order.status = "DELIVERED"
    db.commit()
    return {"ok": True}

@app.post("/delivery/location")
async def rider_location(data: LocationUpdate, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = require_user(auth, db, ["DELIVERY"])
    order = db.get(Order, data.order_id)
    if not order or order.delivery_id != user.id:
        raise HTTPException(403, "Forbidden")
    loc = RiderLocation(
        delivery_id=user.id, order_id=order.id,
        lat=data.lat, lng=data.lng, updated_at=datetime.utcnow()
    )
    db.add(loc)
    db.commit()
    await manager.broadcast(order.id, {
        "type": "rider_location",
        "lat": data.lat, "lng": data.lng,
        "updated_at": loc.updated_at.isoformat()
    })
    return {"ok": True}

@app.websocket("/ws/orders/{order_id}")
async def order_socket(websocket: WebSocket, order_id: int):
    await manager.connect(order_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(order_id, websocket)

@app.get("/admin/summary")
def admin_summary(auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    require_user(auth, db, ["ADMIN"])
    delivered = db.query(Order).filter(Order.status == "DELIVERED").all()
    return {
        "users": db.query(User).count(),
        "shops": db.query(Shop).count(),
        "products": db.query(Product).count(),
        "orders": db.query(Order).count(),
        "revenue": round(sum(x.total for x in delivered), 2)
    }

@app.get("/admin/orders")
def admin_orders(auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    require_user(auth, db, ["ADMIN"])
    return [{"id": o.id, "status": o.status, "total": o.total,
             "shop_id": o.shop_id, "delivery_id": o.delivery_id,
             "payment_status": o.payment_status}
            for o in db.query(Order).order_by(Order.created_at.desc()).all()]

@app.post("/admin/orders/{order_id}/assign/{delivery_id}")
def assign_delivery(order_id: int, delivery_id: int, auth: Optional[str] = Header(None), db: Session = Depends(get_db)):
    require_user(auth, db, ["ADMIN"])
    order = db.get(Order, order_id)
    rider = db.get(User, delivery_id)
    if not order or not rider or rider.role != "DELIVERY":
        raise HTTPException(400, "Invalid assignment")
    order.delivery_id = rider.id
    if order.status in {"ACCEPTED", "PACKED"}:
        order.status = "OUT_FOR_DELIVERY"
    db.commit()
    return {"ok": True, "delivery_id": rider.id}

@app.post("/seed")
def seed(db: Session = Depends(get_db)):
    if db.query(Shop).count() > 0:
        return {"ok": True, "message": "Already seeded"}

    users = [
        User(name="Admin", email="admin@localquick.test", password=pwd.hash("admin123"), role="ADMIN"),
        User(name="Shop Owner", email="shop@localquick.test", password=pwd.hash("shop123"), role="SHOP"),
        User(name="Delivery Rider", email="rider@localquick.test", password=pwd.hash("rider123"), role="DELIVERY"),
        User(name="Customer", email="customer@localquick.test", password=pwd.hash("customer123"), role="CUSTOMER"),
    ]
    db.add_all(users)
    db.commit()
    for u in users: db.refresh(u)

    shop = Shop(
        owner_id=users[1].id, name="Sharma General Store",
        area="Main Market", lat=23.2599, lng=77.4126,
        radius_km=settings.DELIVERY_RADIUS_KM, delivery_fee=20
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)

    products = [
        Product(shop_id=shop.id, name="Milk 1L", category="Dairy", price=60, stock=50),
        Product(shop_id=shop.id, name="Bread", category="Bakery", price=40, stock=30),
        Product(shop_id=shop.id, name="Eggs 12 Pack", category="Dairy", price=90, stock=40),
        Product(shop_id=shop.id, name="Maggi", category="Snacks", price=15, stock=100),
        Product(shop_id=shop.id, name="Rice 5kg", category="Grocery", price=350, stock=20),
    ]
    db.add_all(products)
    db.commit()
    return {"ok": True, "demo_users": ["admin@localquick.test","shop@localquick.test","rider@localquick.test","customer@localquick.test"]}
