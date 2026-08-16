from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _login(email: str, password: str):
    r = client.post('/auth/login', json={'email': email, 'password': password})
    assert r.status_code == 200
    body = r.json()
    assert body['success'] is True
    return body['data']['token']


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert data['success'] is True
    assert data['data']['ok'] is True


def test_seed_and_customer_order_flow():
    client.post('/seed')

    token = _login('customer@localquick.test', 'customer123')
    shops = client.get('/shops').json()['data']
    assert isinstance(shops, list)
    assert shops

    shop = shops[0]
    detail = client.get(f"/shops/{shop['id']}").json()['data']
    assert detail['products']

    product = detail['products'][0]
    create = client.post(
        '/orders',
        headers={'Authorization': token},
        json={
            'shop_id': shop['id'],
            'address': 'Test Address, Bhopal',
            'lat': 23.2599,
            'lng': 77.4126,
            'items': [{'product_id': product['id'], 'quantity': 1}],
            'payment_method': 'COD',
        },
    )
    assert create.status_code in (201, 200)
    payload = create.json()['data']
    oid = payload['id']

    me_orders = client.get('/orders', headers={'Authorization': token})
    assert me_orders.status_code == 200
    assert any(x['id'] == oid for x in me_orders.json()['data'])


def test_versioned_route_available():
    r = client.get('/api/v1/health')
    assert r.status_code == 200
    assert r.json()['success'] is True
