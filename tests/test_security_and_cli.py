import pytest
from datetime import date, timedelta
from decimal import Decimal
from flask import session
from app.extensions import db, limiter
from app.models import Member, Invoice, Membership, MembershipFreeze, User
from tests.conftest import login_as
from app.utils.pdf import generate_invoice_pdf, generate_revenue_report_pdf, generate_member_card_pdf

def test_security_headers_present(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert 'Content-Security-Policy' in resp.headers

def test_logout_get_returns_405(client):
    login_as(client, 'admin', 'Admin@12345')
    resp = client.get('/auth/logout')
    assert resp.status_code == 405

def test_logout_post_clears_session(client):
    login_as(client, 'admin', 'Admin@12345')
    resp = client.post('/auth/logout', follow_redirects=True)
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_session_cleared_before_login(client):
    with client.session_transaction() as sess:
        sess['stale_variable'] = 'attack_payload'

    resp = login_as(client, 'admin', 'Admin@12345')
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert 'stale_variable' not in sess

def test_rate_limiting_on_login():
    from app import create_app
    from tests.conftest import PytestConfig

    class RateLimitConfig(PytestConfig):
        RATELIMIT_ENABLED = True
        RATELIMIT_STORAGE_URI = 'memory://'

    test_app = create_app(RateLimitConfig)
    with test_app.app_context():
        db.create_all()
    client = test_app.test_client()

    try:
        # 10 attempts allowed
        for _ in range(10):
            r = client.post('/auth/login', data={'username': 'admin', 'password': 'WrongPassword123'}, follow_redirects=True)
            assert r.status_code == 200

        # 11th attempt should be blocked by limiter with 429
        r11 = client.post('/auth/login', data={'username': 'admin', 'password': 'WrongPassword123'}, follow_redirects=True)
        assert r11.status_code == 429
        assert b"429" in r11.data or b"Too Many Requests" in r11.data
    finally:
        limiter.enabled = False

def test_custom_error_handlers():
    from app import create_app
    from tests.conftest import PytestConfig
    from flask import abort

    test_app = create_app(PytestConfig)
    @test_app.route('/test-400')
    def trigger_400():
        abort(400)

    @test_app.route('/test-413')
    def trigger_413():
        abort(413)

    @test_app.route('/test-429')
    def trigger_429():
        abort(429)

    client = test_app.test_client()
    r400 = client.get('/test-400')
    assert r400.status_code == 400
    assert b"400" in r400.data

    r413 = client.get('/test-413')
    assert r413.status_code == 413
    assert b"413" in r413.data

    r429 = client.get('/test-429')
    assert r429.status_code == 429
    assert b"429" in r429.data

def test_production_secret_key_validation(monkeypatch):
    import importlib
    import app.config
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        importlib.reload(app.config)
    assert "SECRET_KEY must be set" in str(exc_info.value)
    # Restore clean testing state
    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-for-pytest-execution-only')
    importlib.reload(app.config)

def test_cli_seed_idempotent(app):
    runner = app.test_cli_runner()
    runner.invoke(args=['seed'])
    result = runner.invoke(args=['seed'])
    assert result.exit_code == 0
    assert "Database already seeded" in result.output

def test_cli_expire_freezes(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['expire-freezes'])
    assert result.exit_code == 0
    assert "Freeze check complete" in result.output

def test_cli_update_overdue(app):
    with app.app_context():
        # Create a past-due unpaid invoice
        inv = Invoice(
            invoice_number='INV-PAST-DUE-TEST',
            member_id=1,
            issue_date=date.today() - timedelta(days=20),
            due_date=date.today() - timedelta(days=5),
            subtotal=Decimal('1500.00'),
            total_amount=Decimal('1500.00'),
            payment_status='Unpaid'
        )
        db.session.add(inv)
        db.session.commit()
        inv_id = inv.id

    runner = app.test_cli_runner()
    result = runner.invoke(args=['update-overdue'])
    assert result.exit_code == 0
    assert "Overdue check complete" in result.output

    with app.app_context():
        inv_check = db.session.get(Invoice, inv_id)
        assert inv_check.payment_status == 'Overdue'

def test_reportlab_xml_special_characters_escaping(app):
    with app.app_context():
        mem = Member.active().first()
        mem.first_name = "Muhammad <script> & 'Test'"
        mem.last_name = "O'Connor & Sons >"
        pdf_bytes = generate_member_card_pdf(mem)
        assert len(pdf_bytes) > 0

def test_revenue_report_pdf_filters_by_month_and_year(client):
    login_as(client, 'admin', 'Admin@12345')
    resp = client.get('/finance/revenue-pdf?month=November&year=2026')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/pdf'
    assert resp.data.startswith(b'%PDF')

def test_csv_formula_injection_mitigation():
    from app.utils.helpers import sanitize_csv_cell, sanitize_csv_row
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd") == "'+cmd"
    assert sanitize_csv_cell("-2*3") == "'-2*3"
    assert sanitize_csv_cell("@SUM(A1:A5)") == "'@SUM(A1:A5)"
    assert sanitize_csv_cell("\tTab") == "'\tTab"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    assert sanitize_csv_row(["=SUM", "Normal", "@calc"]) == ["'=SUM", "Normal", "'@calc"]

def test_localtime_jinja_filter():
    from datetime import datetime, timezone
    from app.utils.helpers import to_localtime
    # 2026-11-12 10:00:00 UTC -> 2026-11-12 15:00:00 PKT (UTC+5)
    utc_dt = datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc)
    formatted = to_localtime(utc_dt, fmt="%Y-%m-%d %H:%M")
    assert formatted == "2026-11-12 15:00"

def test_cli_expire_memberships(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['expire-memberships'])
    assert result.exit_code == 0
    assert "Maintenance complete:" in result.output

def test_uploaded_file_auth_required(client):
    resp = client.get('/uploads/test.pdf')
    # Unauthenticated should redirect to login
    assert resp.status_code in (302, 401)
