from datetime import date, timedelta
from app.extensions import db
from tests.conftest import login_as
from app.models.member import Member, MemberMeasurement
from app.models.plan import MembershipPlan
from app.models.equipment import Equipment
from app.models.finance import Invoice
from app.models.operations import Attendance

def test_member_crud_and_soft_delete(client, app):
    login_as(client, 'admin', 'Admin@12345')

    # 1. Create Member
    resp = client.post('/members/create', data={
        'branch_id': 1,
        'first_name': 'Zubair',
        'last_name': 'Akram',
        'email': 'zubair.akram@example.pk',
        'phone': '03007654321',
        'cnic': '35202-7654321-9',
        'dob': '1995-04-10',
        'gender': 'Male',
        'blood_group': 'B+',
        'address': 'DHA Phase 5, Lahore',
        'city': 'Lahore',
        'fitness_level': 'Intermediate',
        'medical_conditions': 'None'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"registered successfully" in resp.data

    with app.app_context():
        m = Member.query.filter_by(email='zubair.akram@example.pk').first()
        assert m is not None
        assert m.is_deleted is False
        m_id = m.id

    # 2. View Member
    resp = client.get(f'/members/{m_id}')
    assert resp.status_code == 200
    assert b"Zubair Akram" in resp.data

    # 3. Edit Member
    resp = client.post(f'/members/{m_id}/edit', data={
        'branch_id': 1,
        'first_name': 'Zubair Updated',
        'last_name': 'Akram',
        'email': 'zubair.akram@example.pk',
        'phone': '03007654321',
        'cnic': '35202-7654321-9',
        'dob': '1995-04-10',
        'gender': 'Male',
        'blood_group': 'B+',
        'address': 'Gulberg 3',
        'city': 'Lahore',
        'fitness_level': 'Advanced',
        'medical_conditions': 'None'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"updated successfully" in resp.data

    # 4. Soft Delete Member
    resp = client.post(f'/members/{m_id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    assert b"soft-deleted" in resp.data

    # Verify soft delete in DB
    with app.app_context():
        m_check = db.session.get(Member, m_id)
        assert m_check.is_deleted is True
        assert Member.active().filter_by(id=m_id).first() is None

def test_membership_plan_crud_and_soft_delete(client, app):
    login_as(client, 'admin', 'Admin@12345')

    # 1. Create Plan
    resp = client.post('/plans/create', data={
        'name': 'Sprint 45 Days',
        'plan_type': 'Monthly',
        'duration_days': 45,
        'price': 8000.0,
        'max_classes_per_week': 4,
        'description': 'Rapid conditioning plan'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"created successfully" in resp.data

    with app.app_context():
        plan = MembershipPlan.query.filter_by(name='Sprint 45 Days').first()
        assert plan is not None
        p_id = plan.id

    # 2. Edit Plan
    resp = client.post(f'/plans/{p_id}/edit', data={
        'name': 'Sprint 45 Days Deluxe',
        'plan_type': 'Monthly',
        'duration_days': 45,
        'price': 8500.0,
        'max_classes_per_week': 5,
        'description': 'Updated plan'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"updated successfully" in resp.data

    # 3. Soft Delete Plan
    resp = client.post(f'/plans/{p_id}/delete', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        p_check = db.session.get(MembershipPlan, p_id)
        assert p_check.is_deleted is True
        assert MembershipPlan.active().filter_by(id=p_id).first() is None

def test_checkin_checkout_flow(client, app):
    login_as(client, 'receptionist', 'Admin@12345')

    # Perform check-in for member
    resp = client.post('/operations/checkin', data={
        'member_identifier': '03041234567',
        'branch_id': 1,
        'method': 'Manual'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        att = Attendance.active().filter_by(member_id=1, check_out_time=None).first()
        assert att is not None
        att_id = att.id

    # Perform check-out
    resp = client.post(f'/operations/checkout/{att_id}', follow_redirects=True)
    assert resp.status_code == 200
    assert b"checked out at" in resp.data

def test_form_validation_cnic_and_phone(client):
    login_as(client, 'admin', 'Admin@12345')

    # Test invalid CNIC format
    resp = client.post('/members/create', data={
        'branch_id': 1,
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'bad.cnic@example.pk',
        'phone': '03001234567',
        'cnic': '12345',  # Invalid CNIC
        'dob': '1998-01-01',
        'gender': 'Male'
    })
    assert b"CNIC must be 13 digits" in resp.data

    # Test invalid phone format
    resp = client.post('/members/create', data={
        'branch_id': 1,
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'bad.phone@example.pk',
        'phone': '123',  # Invalid phone
        'cnic': '42101-1234567-9',
        'dob': '1998-01-01',
        'gender': 'Male'
    })
    assert b"Please enter a valid phone number" in resp.data

def test_csv_exports(client):
    login_as(client, 'admin', 'Admin@12345')
    endpoints = [
        '/members/export-csv',
        '/plans/export-csv',
        '/trainers/export-csv',
        '/classes/export-csv',
        '/nutrition/export-csv',
        '/equipment/export-csv',
        '/finance/export-csv',
        '/operations/export-csv'
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

def test_reportlab_pdf_generation(client):
    login_as(client, 'admin', 'Admin@12345')

    # Member card PDF
    resp = client.get('/members/1/card-pdf')
    assert resp.status_code == 200
    assert resp.content_type == 'application/pdf'
    assert resp.data.startswith(b'%PDF')

    # Invoice PDF
    resp = client.get('/finance/1/pdf')
    assert resp.status_code == 200
    assert resp.content_type == 'application/pdf'
    assert resp.data.startswith(b'%PDF')

    # Revenue report PDF
    resp = client.get('/finance/revenue-pdf')
    assert resp.status_code == 200
    assert resp.content_type == 'application/pdf'
    assert resp.data.startswith(b'%PDF')
