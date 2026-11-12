import pytest
from flask import session
from tests.conftest import login_as
from app.models.access import User

def test_login_success(client):
    response = login_as(client, 'admin', 'Admin@12345')
    assert response.status_code == 200
    assert b"Welcome back, Muhammad Asad" in response.data

def test_login_invalid_password(client):
    response = login_as(client, 'admin', 'WrongPassword!')
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

def test_account_lockout_after_five_failed_attempts(client):
    # Attempt 5 consecutive failed logins
    for _ in range(5):
        client.post('/auth/login', data={'username': 'manager', 'password': 'WrongPassword123'}, follow_redirects=True)

    # 6th attempt should be blocked with lockout warning
    response = client.post('/auth/login', data={'username': 'manager', 'password': 'WrongPassword123'}, follow_redirects=True)
    assert b"locked" in response.data.lower()

def test_logout(client):
    login_as(client, 'admin', 'Admin@12345')
    # GET /auth/logout must return 405 Method Not Allowed
    get_resp = client.get('/auth/logout')
    assert get_resp.status_code == 405

    # POST /auth/logout must successfully log out
    post_resp = client.post('/auth/logout', follow_redirects=True)
    assert post_resp.status_code == 200
    assert b"logged out successfully" in post_resp.data

def test_open_redirect_protection(client):
    # Attacker tries to supply external redirects
    evil_urls = ['//evil.com', '/\\evil.com', 'https://evil.com', 'http://attacker.com/steal']
    for evil in evil_urls:
        resp = client.post(f'/auth/login?next={evil}', data={'username': 'admin', 'password': 'Admin@12345'})
        assert resp.status_code == 302
        # Redirect location must NOT be the evil target, but the safe internal dashboard
        assert resp.headers['Location'] == '/' or resp.headers['Location'].endswith('/')

def test_role_access_403(client):
    # Log in as Member
    login_as(client, 'member', 'Admin@12345')

    # Try to access Admin-only audit logs page
    response = client.get('/reports/audit-logs')
    assert response.status_code == 403

    # Try to access Member creation page (receptionist/manager/admin only)
    response = client.get('/members/create')
    assert response.status_code == 403
