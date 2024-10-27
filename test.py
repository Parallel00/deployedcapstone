import pytest
from app import app, db
from flask_login import FlaskLoginClient

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory SQLite for tests
    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Create the database tables
        yield client
        with app.app_context():
            db.drop_all()  # Clean up after tests

@pytest.fixture
def logged_in_client(client):
    # Simulates user login
    client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
    return client

def test_generate_qr_code_authenticated(logged_in_client):
    response = logged_in_client.post('/', data={'url': 'https://example.com'})
    assert response.status_code == 200  # Check for OK status

def test_generate_qr_code_unauthenticated(client):
    response = client.post('/', data={'url': 'https://example.com'})
    assert response.status_code == 200  # Should still be OK to render the page
    assert b'You must be logged in to generate QR codes.' in response.data  # Check for flash message

def test_generate_qr_code_invalid_url(logged_in_client):
    response = logged_in_client.post('/', data={'url': 'invalid-url'})
    assert response.status_code == 200  # Check for rendering of index page

