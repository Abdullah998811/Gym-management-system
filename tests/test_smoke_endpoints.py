import re
import os
import pytest
from tests.conftest import login_as

def test_every_role_dashboard(client):
    roles_credentials = [
        ('admin', 'Admin@12345'),
        ('manager', 'Admin@12345'),
        ('trainer', 'Admin@12345'),
        ('receptionist', 'Admin@12345'),
        ('member', 'Admin@12345')
    ]
    for un, pw in roles_credentials:
        login_as(client, un, pw)
        resp = client.get('/', follow_redirects=True)
        assert resp.status_code == 200, f"Dashboard failed for {un}"

        # Dedicated role dashboards
        resp_mem = client.get('/member-dashboard')
        assert resp_mem.status_code == 200, f"/member-dashboard failed for {un}"

        resp_trn = client.get('/trainer-dashboard')
        assert resp_trn.status_code == 200, f"/trainer-dashboard failed for {un}"

def test_smoke_every_get_route(client, app):
    """Smoke test: Log in as Admin and request EVERY GET route in app.url_map."""
    login_as(client, 'admin', 'Admin@12345')

    # Routes to skip (e.g. logout would end the session; delete endpoints)
    skip_endpoints = {
        'auth.logout',
        'auth.login',
        'static'
    }

    tested_count = 0
    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            if 'GET' not in rule.methods:
                continue
            if rule.endpoint in skip_endpoints:
                continue
            if 'delete' in rule.rule or 'cancel' in rule.rule:
                continue

            # Fill in route arguments with test ID 1
            url = rule.rule
            if '<int:id>' in url:
                url = url.replace('<int:id>', '1')
            elif '<int:member_id>' in url:
                url = url.replace('<int:member_id>', '1')

            # Skip unhandled parameter types if any
            if '<' in url:
                continue

            resp = client.get(url, follow_redirects=True)
            assert resp.status_code < 400, f"Endpoint {rule.endpoint} ({url}) returned {resp.status_code}"
            tested_count += 1

    print(f"\n[Smoke Test Verified {tested_count} GET endpoints with status < 400!]")

def test_all_url_for_endpoints_exist(app):
    """Scan all templates and python files for url_for('...') and assert each exists."""
    valid_endpoints = set(app.view_functions.keys())
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))

    url_for_pattern = re.compile(r"url_for\(\s*['\"]([a-zA-Z0-9_\.]+)['\"]")
    found_endpoints = set()

    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith(('.html', '.py')):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    matches = url_for_pattern.findall(content)
                    for m in matches:
                        found_endpoints.add((m, f))

    missing = []
    for ep, filename in found_endpoints:
        if ep not in valid_endpoints:
            missing.append(f"{ep} (referenced in {filename})")

    assert not missing, f"Missing url_for endpoints detected: {missing}"
    print(f"\n[Endpoint Test Verified all {len(found_endpoints)} url_for references exist in app.url_map!]")

def test_health_check_public(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.data == b"OK"
