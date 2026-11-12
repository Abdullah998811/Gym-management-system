import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models import (
    Member, User, Role, Branch, Invoice, InvoiceItem,
    ClassBooking, GymClass, ClassType, Trainer, Attendance, Complaint, Feedback
)
from tests.conftest import login_as

@pytest.fixture
def member_b(app):
    with app.app_context():
        suffix = uuid.uuid4().hex[:6]
        br = Branch.active().first()
        role = Role.active().filter_by(name='Member').first()
        user_b = User(
            username=f'member_b_{suffix}',
            email=f'member_b_{suffix}@gym.pk',
            full_name='Member B Person',
            role_id=role.id,
            branch_id=br.id
        )
        user_b.set_password('MemberB@12345')
        db.session.add(user_b)
        db.session.flush()

        mem_b = Member(
            membership_number=f'MEM-B-{suffix}',
            user_id=user_b.id,
            branch_id=br.id,
            first_name='MemberB',
            last_name='User',
            email=f'member_b_{suffix}@gym.pk',
            phone=f'0309{suffix[:7]}',
            cnic=f'35202-{uuid.uuid4().int % 10000000:07d}-1',
            dob=date(1995, 1, 1),
            gender='Female',
            join_date=date.today()
        )
        db.session.add(mem_b)
        db.session.flush()

        inv = Invoice(
            invoice_number=f'INV-B-{suffix}',
            member_id=mem_b.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            subtotal=Decimal('3000.00'),
            total_amount=Decimal('3000.00'),
            payment_status='Unpaid'
        )
        db.session.add(inv)
        db.session.flush()

        gc = GymClass.active().first()
        cb = ClassBooking(
            class_id=gc.id,
            member_id=mem_b.id,
            booking_date=date.today() + timedelta(days=1),
            booking_status='Confirmed'
        )
        db.session.add(cb)

        comp = Complaint(
            member_id=mem_b.id,
            subject=f'Member B Complaint {suffix}',
            description='Private issue',
            priority='Low',
            resolution_status='Pending'
        )
        db.session.add(comp)

        db.session.commit()
        return {
            'user_id': user_b.id,
            'member_id': mem_b.id,
            'invoice_id': inv.id,
            'booking_id': cb.id,
            'class_id': gc.id,
            'complaint_id': comp.id,
            'complaint_subject': comp.subject
        }

def test_member_a_cannot_view_member_b_profile(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get(f'/members/{member_b["member_id"]}')
    assert resp.status_code == 403

def test_member_a_cannot_download_member_b_card_pdf(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get(f'/members/{member_b["member_id"]}/card-pdf')
    assert resp.status_code == 403

def test_member_a_cannot_add_measurement_to_member_b(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.post(f'/members/{member_b["member_id"]}/measurements', data={
        'measurement_date': str(date.today()),
        'weight_kg': 70.0,
        'height_cm': 175.0
    })
    assert resp.status_code == 403

def test_member_a_cannot_add_goal_to_member_b(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.post(f'/members/{member_b["member_id"]}/goals', data={
        'goal_type': 'Weight Loss',
        'target_value': '65 kg',
        'target_date': str(date.today() + timedelta(days=30))
    })
    assert resp.status_code == 403

def test_member_a_cannot_view_member_b_invoice(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get(f'/finance/{member_b["invoice_id"]}/view')
    assert resp.status_code == 403

def test_member_a_cannot_download_member_b_invoice_pdf(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get(f'/finance/{member_b["invoice_id"]}/pdf')
    assert resp.status_code == 403

def test_member_a_cannot_fetch_member_b_measurements_analytics(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get(f'/api/analytics/member-measurements/{member_b["member_id"]}')
    assert resp.status_code == 403

def test_member_a_cannot_cancel_member_b_booking(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.post(f'/classes/cancel-booking/{member_b["booking_id"]}')
    assert resp.status_code == 403

def test_member_a_cannot_book_class_for_member_b(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.post('/classes/book', data={
        'class_id': member_b["class_id"],
        'member_id': member_b["member_id"],
        'booking_date': str(date.today() + timedelta(days=2))
    })
    assert resp.status_code == 403

def test_member_only_sees_own_complaints(client, member_b):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/operations/complaints')
    assert resp.status_code == 200
    assert member_b["complaint_subject"].encode() not in resp.data

def test_staff_can_access_member_b_data(client, member_b):
    login_as(client, 'admin', 'Admin@12345')
    resp = client.get(f'/members/{member_b["member_id"]}')
    assert resp.status_code == 200
    resp_pdf = client.get(f'/members/{member_b["member_id"]}/card-pdf')
    assert resp_pdf.status_code == 200
    resp_inv = client.get(f'/finance/{member_b["invoice_id"]}/pdf')
    assert resp_inv.status_code == 200

def test_member_empty_payments_if_no_member_record(client, app):
    with app.app_context():
        br = Branch.active().first()
        role = Role.active().filter_by(name='Member').first()
        orphan_user = User(
            username='orphan_member',
            email='orphan@gym.pk',
            full_name='Orphan Member',
            role_id=role.id,
            branch_id=br.id
        )
        orphan_user.set_password('Admin@12345')
        db.session.add(orphan_user)
        db.session.commit()

    login_as(client, 'orphan_member', 'Admin@12345')
    resp = client.get('/finance/payments')
    assert resp.status_code == 200
    # Should not display any payments
    assert b"CASH-1" not in resp.data

def test_member_forbidden_on_exports_and_sales(client):
    login_as(client, 'member', 'Admin@12345')
    # Supplement sales forbidden for member
    assert client.get('/nutrition/sales').status_code == 403
    # CSV exports forbidden for member
    assert client.get('/nutrition/export-csv').status_code == 403
    assert client.get('/equipment/export-csv').status_code == 403
    assert client.get('/classes/export-csv').status_code == 403

def test_member_forbidden_on_dashboard_analytics_apis(client):
    login_as(client, 'member', 'Admin@12345')
    assert client.get('/api/analytics/revenue-monthly').status_code == 403
    assert client.get('/api/analytics/members-monthly').status_code == 403
    assert client.get('/api/analytics/plan-distribution').status_code == 403
    assert client.get('/api/analytics/attendance-weekly').status_code == 403
