import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ...db import get_db
from ...models import AuditLog, Order, OrderItem, Product, RiderLocation, Shop, User
from ...realtime import manager
from ...responses import success
from ...schemas import CreateOrderRequest, LocationUpdateRequest, LoginRequest, ProductCreateRequest, RegisterRequest
from ...security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)
from ...seed import seed_demo_data

router = APIRouter()


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@router.get('/health')
def health():
    return success({'ok': True}, 'healthy')


@router.get('/')
def root():
    return success({'service': 'LocalQuick', 'version': '4.0.0', 'docs': '/docs'})


@router.post('/auth/register')
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    email = str(data.email).lower().strip()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail='Email already registered')
    user = User(name=data.name.strip(), email=email, password_hash=hash_password(data.password), role='CUSTOMER')
    db.add(user)
    db.add(AuditLog(actor_user_id=None, action='AUTH_REGISTER', entity_type='USER', entity_id=email))
    db.commit()
    db.refresh(user)
    return success(
        {
            'token': create_access_token(user),
            'refresh_token': create_refresh_token(user),
            'user': {'id': user.id, 'name': user.name, 'role': user.role},
        },
        'registered',
        201,
    )


@router.post('/auth/login')
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=str(data.email).lower().strip()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    db.add(AuditLog(actor_user_id=user.id, action='AUTH_LOGIN', entity_type='USER', entity_id=str(user.id)))
    db.commit()
    return success(
        {
            'token': create_access_token(user),
            'refresh_token': create_refresh_token(user),
            'user': {'id': user.id, 'name': user.name, 'role': user.role},
        },
        'login successful',
    )


@router.post('/auth/refresh')
def refresh(payload: dict, db: Session = Depends(get_db)):
    token = payload.get('refresh_token', '')
    try:
        data = decode_token(token)
        if data.get('type') != 'refresh':
            raise ValueError('invalid type')
        user_id = int(data['sub'])
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid refresh token')
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail='Invalid user')
    return success({'token': create_access_token(user), 'refresh_token': create_refresh_token(user)}, 'token refreshed')


@router.post('/auth/logout')
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(AuditLog(actor_user_id=user.id, action='AUTH_LOGOUT', entity_type='USER', entity_id=str(user.id)))
    db.commit()
    return success({'logged_out': True}, 'logout successful')


@router.get('/shops')
def list_shops(lat: float | None = None, lng: float | None = None, db: Session = Depends(get_db)):
    shops = db.query(Shop).filter_by(open=True, status='APPROVED').all()
    result = []
    for shop in shops:
        d = None if lat is None or lng is None else haversine(lat, lng, shop.lat, shop.lng)
        if d is None or d <= shop.radius_km:
            result.append(
                {
                    'id': shop.id,
                    'name': shop.name,
                    'area': shop.area,
                    'delivery_fee': shop.delivery_fee,
                    'distance_km': round(d, 2) if d is not None else None,
                    'min_order': shop.min_order,
                }
            )
    return success(result)


@router.get('/shops/{shop_id}')
def get_shop(shop_id: int, db: Session = Depends(get_db)):
    shop = db.get(Shop, shop_id)
    if not shop or not shop.open:
        raise HTTPException(status_code=404, detail='Shop not found')
    products = db.query(Product).filter_by(shop_id=shop.id, active=True).all()
    return success(
        {
            'id': shop.id,
            'name': shop.name,
            'area': shop.area,
            'delivery_fee': shop.delivery_fee,
            'radius_km': shop.radius_km,
            'min_order': shop.min_order,
            'products': [
                {
                    'id': p.id,
                    'name': p.name,
                    'category': p.category,
                    'price': p.price,
                    'mrp': p.mrp,
                    'discount': p.discount,
                    'stock': p.stock,
                    'image': p.image,
                }
                for p in products
            ],
        }
    )


@router.post('/orders')
async def create_order(data: CreateOrderRequest, db: Session = Depends(get_db), user: User = Depends(require_roles('CUSTOMER'))):
    shop = db.get(Shop, data.shop_id)
    if not shop or not shop.open or shop.status != 'APPROVED':
        raise HTTPException(status_code=400, detail='Shop unavailable')

    if haversine(data.lat, data.lng, shop.lat, shop.lng) > shop.radius_km:
        raise HTTPException(status_code=400, detail="This shop doesn't deliver to your location yet.")

    subtotal = 0.0
    items = []
    for item in data.items:
        product = db.get(Product, item.product_id)
        if not product or product.shop_id != shop.id or not product.active:
            raise HTTPException(status_code=400, detail='Product unavailable')
        if product.stock < item.quantity:
            raise HTTPException(status_code=409, detail=f'Insufficient stock: {product.name}')
        product.stock -= item.quantity
        line = product.price * item.quantity
        subtotal += line
        items.append((product, item.quantity, line))

    if subtotal < shop.min_order:
        raise HTTPException(status_code=422, detail=f'Minimum order value is {shop.min_order}')

    order = Order(
        customer_id=user.id,
        shop_id=shop.id,
        address=data.address,
        lat=data.lat,
        lng=data.lng,
        subtotal=subtotal,
        delivery_fee=shop.delivery_fee,
        taxes=0.0,
        discounts=0.0,
        platform_fee=0.0,
        total=subtotal + shop.delivery_fee,
        payment_method=data.payment_method,
        payment_status='PENDING' if data.payment_method == 'ONLINE' else 'PENDING',
        status='PLACED',
    )
    db.add(order)
    db.flush()

    for product, qty, line in items:
        db.add(OrderItem(order_id=order.id, product_id=product.id, name=product.name, quantity=qty, unit_price=product.price, total_price=line))

    db.add(AuditLog(actor_user_id=user.id, action='ORDER_CREATED', entity_type='ORDER', entity_id=str(order.id)))
    db.commit()
    db.refresh(order)
    return success({'id': order.id, 'total': order.total, 'status': order.status, 'payment_status': order.payment_status}, 'order created', 201)


@router.get('/orders')
def customer_orders(db: Session = Depends(get_db), user: User = Depends(require_roles('CUSTOMER'))):
    orders = db.query(Order).filter_by(customer_id=user.id).order_by(Order.created_at.desc()).all()
    return success(
        [
            {
                'id': o.id,
                'total': o.total,
                'status': o.status,
                'payment_status': o.payment_status,
                'delivery_id': o.delivery_id,
                'created_at': o.created_at.isoformat(),
            }
            for o in orders
        ]
    )


@router.get('/orders/{order_id}')
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    if user.role == 'CUSTOMER' and order.customer_id != user.id:
        raise HTTPException(status_code=403, detail='Forbidden')

    order_items = db.query(OrderItem).filter_by(order_id=order.id).all()
    return success(
        {
            'id': order.id,
            'status': order.status,
            'payment_status': order.payment_status,
            'payment_method': order.payment_method,
            'address': order.address,
            'lat': order.lat,
            'lng': order.lng,
            'total': order.total,
            'subtotal': order.subtotal,
            'delivery_fee': order.delivery_fee,
            'delivery_id': order.delivery_id,
            'items': [
                {'product_id': x.product_id, 'name': x.name, 'price': x.unit_price, 'quantity': x.quantity}
                for x in order_items
            ],
        }
    )


@router.post('/payments/mock-success/{order_id}')
def mock_payment(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('CUSTOMER'))):
    order = db.get(Order, order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail='Order not found')
    order.payment_status = 'PAID'
    order.payment_method = 'ONLINE'
    order.payment_order_id = f'mock_{order.id}'
    db.add(AuditLog(actor_user_id=user.id, action='PAYMENT_MARKED_PAID', entity_type='ORDER', entity_id=str(order.id)))
    db.commit()
    return success({'payment_status': order.payment_status})


@router.get('/shop/orders')
def shop_orders(db: Session = Depends(get_db), user: User = Depends(require_roles('SHOP_OWNER', 'SHOP'))):
    shop = db.query(Shop).filter_by(owner_id=user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail='No shop assigned')
    orders = db.query(Order).filter_by(shop_id=shop.id).order_by(Order.created_at.desc()).all()
    return success([{'id': o.id, 'total': o.total, 'status': o.status, 'customer_id': o.customer_id} for o in orders])


@router.post('/shop/products')
def add_product(data: ProductCreateRequest, db: Session = Depends(get_db), user: User = Depends(require_roles('SHOP_OWNER', 'SHOP'))):
    shop = db.query(Shop).filter_by(owner_id=user.id).first()
    if not shop:
        raise HTTPException(status_code=404, detail='No shop assigned')
    p = Product(shop_id=shop.id, **data.model_dump())
    db.add(p)
    db.add(AuditLog(actor_user_id=user.id, action='PRODUCT_CREATED', entity_type='PRODUCT', entity_id='new'))
    db.commit()
    db.refresh(p)
    return success({'id': p.id, 'name': p.name}, 'product created', 201)


@router.post('/shop/orders/{order_id}/status')
def shop_status(order_id: int, status: str, db: Session = Depends(get_db), user: User = Depends(require_roles('SHOP_OWNER', 'SHOP'))):
    shop = db.query(Shop).filter_by(owner_id=user.id).first()
    order = db.get(Order, order_id)
    if not shop or not order or order.shop_id != shop.id:
        raise HTTPException(status_code=404, detail='Order not found')

    valid = {
        'PLACED': {'ACCEPTED', 'CANCELLED'},
        'ACCEPTED': {'PACKING', 'CANCELLED'},
        'PACKING': {'READY_FOR_PICKUP', 'CANCELLED'},
        'READY_FOR_PICKUP': {'ASSIGNED', 'PICKED_UP'},
        'ASSIGNED': {'PICKED_UP'},
        'PICKED_UP': {'OUT_FOR_DELIVERY'},
        'OUT_FOR_DELIVERY': {'DELIVERED'},
    }
    if status not in valid.get(order.status, set()):
        raise HTTPException(status_code=422, detail='Invalid status transition')
    order.status = status
    db.add(AuditLog(actor_user_id=user.id, action='ORDER_STATUS_UPDATED', entity_type='ORDER', entity_id=str(order.id), details=status))
    db.commit()
    return success({'status': order.status})


@router.get('/delivery/orders')
def delivery_orders(db: Session = Depends(get_db), user: User = Depends(require_roles('DELIVERY_PARTNER', 'DELIVERY'))):
    orders = (
        db.query(Order)
        .filter((Order.status.in_(['READY_FOR_PICKUP', 'ASSIGNED', 'OUT_FOR_DELIVERY'])) | (Order.delivery_id == user.id))
        .order_by(Order.created_at.desc())
        .all()
    )
    return success(
        [
            {'id': o.id, 'shop_id': o.shop_id, 'address': o.address, 'status': o.status, 'total': o.total, 'delivery_id': o.delivery_id}
            for o in orders
        ]
    )


@router.post('/delivery/orders/{order_id}/accept')
def accept_delivery(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('DELIVERY_PARTNER', 'DELIVERY'))):
    order = db.get(Order, order_id)
    if not order or order.status not in {'READY_FOR_PICKUP', 'ASSIGNED'}:
        raise HTTPException(status_code=400, detail='Order is not available')
    if order.delivery_id and order.delivery_id != user.id:
        raise HTTPException(status_code=409, detail='Order already assigned')
    order.delivery_id = user.id
    order.status = 'OUT_FOR_DELIVERY'
    db.add(AuditLog(actor_user_id=user.id, action='DELIVERY_ACCEPTED', entity_type='ORDER', entity_id=str(order.id)))
    db.commit()
    return success({'ok': True})


@router.post('/delivery/orders/{order_id}/delivered')
def delivered(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles('DELIVERY_PARTNER', 'DELIVERY'))):
    order = db.get(Order, order_id)
    if not order or order.delivery_id != user.id:
        raise HTTPException(status_code=403, detail='Forbidden')
    order.status = 'DELIVERED'
    order.payment_status = 'PAID' if order.payment_method == 'COD' else order.payment_status
    db.add(AuditLog(actor_user_id=user.id, action='ORDER_DELIVERED', entity_type='ORDER', entity_id=str(order.id)))
    db.commit()
    return success({'ok': True})


@router.post('/delivery/location')
async def rider_location(data: LocationUpdateRequest, db: Session = Depends(get_db), user: User = Depends(require_roles('DELIVERY_PARTNER', 'DELIVERY'))):
    order = db.get(Order, data.order_id)
    if not order or order.delivery_id != user.id:
        raise HTTPException(status_code=403, detail='Forbidden')
    loc = RiderLocation(delivery_id=user.id, order_id=order.id, lat=data.lat, lng=data.lng, updated_at=datetime.utcnow())
    db.add(loc)
    db.commit()

    await manager.broadcast(
        order.id,
        {
            'type': 'rider_location',
            'lat': data.lat,
            'lng': data.lng,
            'updated_at': loc.updated_at.isoformat(),
        },
    )
    return success({'ok': True})


@router.websocket('/ws/orders/{order_id}')
async def order_socket(websocket: WebSocket, order_id: int):
    await manager.connect(order_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(order_id, websocket)


@router.get('/admin/summary')
def admin_summary(db: Session = Depends(get_db), _: User = Depends(require_roles('ADMIN', 'SUPER_ADMIN'))):
    delivered = db.query(Order).filter(Order.status == 'DELIVERED').all()
    return success(
        {
            'users': db.query(User).count(),
            'shops': db.query(Shop).count(),
            'products': db.query(Product).count(),
            'orders': db.query(Order).count(),
            'revenue': round(sum(x.total for x in delivered), 2),
        }
    )


@router.get('/admin/orders')
def admin_orders(db: Session = Depends(get_db), _: User = Depends(require_roles('ADMIN', 'SUPER_ADMIN'))):
    return success(
        [
            {
                'id': o.id,
                'status': o.status,
                'total': o.total,
                'shop_id': o.shop_id,
                'delivery_id': o.delivery_id,
                'payment_status': o.payment_status,
            }
            for o in db.query(Order).order_by(Order.created_at.desc()).all()
        ]
    )


@router.post('/admin/orders/{order_id}/assign/{delivery_id}')
def assign_delivery(order_id: int, delivery_id: int, db: Session = Depends(get_db), admin: User = Depends(require_roles('ADMIN', 'SUPER_ADMIN'))):
    order = db.get(Order, order_id)
    rider = db.get(User, delivery_id)
    if not order or not rider or rider.role != 'DELIVERY_PARTNER':
        raise HTTPException(status_code=400, detail='Invalid assignment')
    if order.delivery_id and order.delivery_id != rider.id:
        raise HTTPException(status_code=409, detail='Order already assigned')
    order.delivery_id = rider.id
    if order.status in {'ACCEPTED', 'PACKING', 'READY_FOR_PICKUP', 'ASSIGNED'}:
        order.status = 'OUT_FOR_DELIVERY'
    db.add(AuditLog(actor_user_id=admin.id, action='DELIVERY_ASSIGNED', entity_type='ORDER', entity_id=str(order.id), details=str(rider.id)))
    db.commit()
    return success({'delivery_id': rider.id})


@router.post('/seed')
def seed(db: Session = Depends(get_db)):
    seeded = seed_demo_data(db)
    if not seeded:
        return success({'seeded': False}, 'Already seeded')
    return success(
        {
            'seeded': True,
            'demo_users': ['admin@localquick.test', 'shop@localquick.test', 'rider@localquick.test', 'customer@localquick.test'],
        },
        'Demo data seeded',
    )
