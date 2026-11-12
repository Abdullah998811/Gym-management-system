import pytest
from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models import (
    Member, User, Role, Branch, MembershipPlan, Membership, MembershipFreeze,
    Invoice, InvoiceItem, Payment, PaymentMethod, GymClass, ClassBooking, ClassWaitlist,
    Attendance, AuditLog, ClassType, Trainer, Supplement, SupplementSale,
    Locker, LockerAssignment, Area, PTSession
)
from tests.conftest import login_as

def test_overpayment_rejection(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member.active().first()
        inv = Invoice(
            invoice_number='INV-TEST-OVERPAY',
            member_id=mem.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            subtotal=Decimal('2000.00'),
            total_amount=Decimal('2000.00'),
            payment_status='Unpaid'
        )
        db.session.add(inv)
        db.session.commit()
        inv_id = inv.id

    # Attempt to pay 2500 on a 2000 invoice
    resp = client.post(f'/finance/{inv_id}/view', data={
        'invoice_id': inv_id,
        'payment_method_id': 1,
        'payment_date': str(date.today()),
        'amount': 2500.00,
        'transaction_reference': 'REF-FAIL'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"cannot exceed remaining balance due" in resp.data

    with app.app_context():
        inv_check = db.session.get(Invoice, inv_id)
        assert inv_check.payment_status == 'Unpaid'
        assert inv_check.paid_amount == Decimal('0.00')

def test_payment_on_paid_invoice_rejected(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member.active().first()
        inv = Invoice(
            invoice_number='INV-TEST-PAID',
            member_id=mem.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('1000.00'),
            payment_status='Paid'
        )
        db.session.add(inv)
        db.session.commit()
        inv_id = inv.id

    resp = client.post(f'/finance/{inv_id}/view', data={
        'invoice_id': inv_id,
        'payment_method_id': 1,
        'payment_date': str(date.today()),
        'amount': 100.00
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"already fully paid" in resp.data

def test_decimal_totals_correctness(app):
    with app.app_context():
        inv = Invoice(
            invoice_number='INV-DECIMAL-TEST',
            member_id=1,
            issue_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal('100.55'),
            tax_amount=Decimal('5.25'),
            discount_amount=Decimal('10.00'),
            total_amount=Decimal('95.80'),
            payment_status='Unpaid'
        )
        db.session.add(inv)
        db.session.flush()

        p1 = Payment(invoice_id=inv.id, payment_method_id=1, payment_date=date.today(), amount=Decimal('50.30'))
        p2 = Payment(invoice_id=inv.id, payment_method_id=1, payment_date=date.today(), amount=Decimal('45.50'))
        db.session.add_all([p1, p2])
        db.session.flush()

        assert inv.paid_amount == Decimal('95.80')
        assert inv.balance_due == Decimal('0.00')
        inv.update_status()
        assert inv.payment_status == 'Paid'

def test_membership_future_freeze_does_not_set_status_frozen(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member.active().first()
        ms = mem.active_membership
        assert ms is not None
        mem_id = mem.id

    future_start = date.today() + timedelta(days=10)
    future_end = date.today() + timedelta(days=20)

    resp = client.post(f'/members/{mem_id}/freeze', data={
        'start_date': str(future_start),
        'end_date': str(future_end),
        'reason': 'Upcoming holiday vacation'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Membership freeze scheduled" in resp.data

    with app.app_context():
        mem_check = db.session.get(Member, mem_id)
        # Status should remain active because start_date is in future!
        assert mem_check.memberships[0].status == 'active'
        assert mem_check.memberships[0].is_frozen == False

def test_overlapping_freeze_rejected(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member.active().first()
        mem_id = mem.id

    # The previous test scheduled freeze for days 10 to 20
    # Try scheduling an overlapping freeze for days 15 to 25
    overlap_start = date.today() + timedelta(days=15)
    overlap_end = date.today() + timedelta(days=25)

    resp = client.post(f'/members/{mem_id}/freeze', data={
        'start_date': str(overlap_start),
        'end_date': str(overlap_end),
        'reason': 'Overlapping leave'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"overlaps with an existing freeze" in resp.data

def test_waitlist_promotion_per_date(client, app):
    login_as(client, 'admin', 'Admin@12345')
    test_date_1 = date.today() + timedelta(days=5)
    test_date_2 = date.today() + timedelta(days=6)

    with app.app_context():
        ct = ClassType.active().first()
        tr = Trainer.active().first()
        br = Branch.active().first()
        mem1 = Member.active().first()

        # Create class with capacity = 1
        gc = GymClass(
            class_type_id=ct.id,
            trainer_id=tr.id,
            branch_id=br.id,
            title='VIP Pilates 1-on-1',
            max_capacity=1,
            difficulty_level='Beginner'
        )
        db.session.add(gc)
        db.session.flush()

        # Confirmed booking on test_date_1
        b1 = ClassBooking(class_id=gc.id, member_id=mem1.id, booking_date=test_date_1, booking_status='Confirmed')
        db.session.add(b1)
        db.session.flush()
        b1_id = b1.id
        gc_id = gc.id

        # Member 2 waitlisted for test_date_1
        user2 = User(username='waitlist_mem_date1', email='w1@gym.pk', full_name='WL Date 1', role_id=5, branch_id=br.id)
        user2.set_password('Pass@123')
        db.session.add(user2)
        db.session.flush()
        m2 = Member(membership_number='MEM-WL-1', user_id=user2.id, branch_id=br.id, first_name='WL1', last_name='User', email='w1@gym.pk', phone='03011111111', cnic='35202-1111111-1', dob=date(1995, 1, 1), gender='Male')
        db.session.add(m2)
        db.session.flush()
        wl_date1 = ClassWaitlist(class_id=gc.id, member_id=m2.id, booking_date=test_date_1, priority=1)

        # Member 3 waitlisted for test_date_2
        user3 = User(username='waitlist_mem_date2', email='w2@gym.pk', full_name='WL Date 2', role_id=5, branch_id=br.id)
        user3.set_password('Pass@123')
        db.session.add(user3)
        db.session.flush()
        m3 = Member(membership_number='MEM-WL-2', user_id=user3.id, branch_id=br.id, first_name='WL2', last_name='User', email='w2@gym.pk', phone='03022222222', cnic='35202-2222222-1', dob=date(1995, 1, 1), gender='Male')
        db.session.add(m3)
        db.session.flush()
        wl_date2 = ClassWaitlist(class_id=gc.id, member_id=m3.id, booking_date=test_date_2, priority=1)

        db.session.add_all([wl_date1, wl_date2])
        db.session.commit()
        m2_id = m2.id
        m3_id = m3.id

    # Cancel b1 on test_date_1 -> only Member 2 (waitlisted for test_date_1) should be promoted!
    resp = client.post(f'/classes/cancel-booking/{b1_id}', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        # Member 2 should now have a Confirmed booking on test_date_1
        promoted = ClassBooking.active().filter_by(class_id=gc_id, member_id=m2_id, booking_date=test_date_1).first()
        assert promoted is not None
        assert promoted.booking_status == 'Confirmed'

        # Member 3 should STILL be on the waitlist for test_date_2!
        assert ClassWaitlist.active().filter_by(class_id=gc_id, member_id=m3_id, booking_date=test_date_2).first() is not None

def test_checkin_blocks_member_without_active_membership(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        br = Branch.active().first()
        # Member with expired membership
        m_expired = Member(
            membership_number='MEM-EXPIRED-99',
            branch_id=br.id,
            first_name='Expired',
            last_name='Member',
            email='expired@gym.pk',
            phone='03098765432',
            cnic='35202-9876543-2',
            dob=date(1990, 1, 1),
            gender='Male'
        )
        db.session.add(m_expired)
        db.session.flush()
        m_id = m_expired.id

        # Expired membership
        ms = Membership(
            member_id=m_id,
            plan_id=1,
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
            price_paid=Decimal('5000.00'),
            status='active'
        )
        db.session.add(ms)
        db.session.commit()

    # Attempt check-in without override -> blocked!
    resp = client.post('/operations/checkin', data={
        'member_identifier': 'MEM-EXPIRED-99',
        'branch_id': 1,
        'method': 'Manual'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Access Denied" in resp.data
    assert b"Staff override with reason is required" in resp.data

    with app.app_context():
        att = Attendance.active().filter_by(member_id=m_id).first()
        assert att is None

def test_checkin_allowed_with_staff_override_and_audit_logged(client, app):
    login_as(client, 'admin', 'Admin@12345')
    resp = client.post('/operations/checkin', data={
        'member_identifier': 'MEM-EXPIRED-99',
        'branch_id': 1,
        'method': 'Manual',
        'staff_override': '1',
        'override_reason': 'Manager special approval for single session trial'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Check-in SUCCESS" in resp.data

    with app.app_context():
        m = Member.active().filter_by(membership_number='MEM-EXPIRED-99').first()
        att = Attendance.active().filter_by(member_id=m.id).first()
        assert att is not None
        # Verify Audit Log
        audit = AuditLog.active().filter_by(action='OVERRIDE_CHECKIN', table_name='attendance').first()
        assert audit is not None
        assert 'Manager special approval' in audit.new_values

def test_soft_delete_uniqueness_allows_reuse_of_email(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        # Soft delete a member
        mem = Member(
            membership_number='MEM-TO-DELETE-1',
            branch_id=1,
            first_name='Deleted',
            last_name='User',
            email='deleted.user@example.pk',
            phone='03120000000',
            cnic='35202-0000000-1',
            dob=date(1992, 1, 1),
            gender='Male'
        )
        db.session.add(mem)
        db.session.commit()
        mem.soft_delete(user_id=1)
        db.session.commit()

    # Create new active member with the EXACT same email and CNIC
    resp = client.post('/members/create', data={
        'branch_id': 1,
        'first_name': 'NewActive',
        'last_name': 'Person',
        'email': 'deleted.user@example.pk',
        'phone': '03121111111',
        'cnic': '35202-0000000-1',
        'dob': '1996-05-10',
        'gender': 'Male'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"registered successfully" in resp.data

    with app.app_context():
        active_cnt = Member.active().filter_by(email='deleted.user@example.pk').count()
        assert active_cnt == 1

def test_duplicate_active_email_rejected(client, app):
    login_as(client, 'admin', 'Admin@12345')
    resp = client.post('/members/create', data={
        'branch_id': 1,
        'first_name': 'Duplicate',
        'last_name': 'Tester',
        'email': 'deleted.user@example.pk',  # Currently active from previous test
        'phone': '03122222222',
        'cnic': '35202-8888888-1',
        'dob': '1996-05-10',
        'gender': 'Male'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"An active member with this email address already exists" in resp.data

def test_membership_renewal_auto_creates_invoice_and_item(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member.active().first()
        mem_id = mem.id

    resp = client.post(f'/members/{mem_id}/renew', data={
        'plan_id': 1,
        'amount_paid': 4500.0,
        'discount_code': 'PROMO1'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Membership renewed" in resp.data

    with app.app_context():
        mem = db.session.get(Member, mem_id)
        latest_inv = Invoice.active().filter_by(member_id=mem.id).order_by(Invoice.id.desc()).first()
        assert latest_inv is not None
        assert latest_inv.items != []
        assert latest_inv.discount_amount > Decimal('0.00')

def test_renewal_rejects_overpayment(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member.active().first()
        mem_id = mem.id

    # Plan price is 5000 with promo discount total is 4500. Paying 6000 should be rejected!
    resp = client.post(f'/members/{mem_id}/renew', data={
        'plan_id': 1,
        'amount_paid': 6000.0,
        'discount_code': 'PROMO1'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"cannot exceed total payable amount" in resp.data

def test_member_creation_with_linked_user(client, app):
    login_as(client, 'admin', 'Admin@12345')
    resp = client.post('/members/create', data={
        'branch_id': 1,
        'first_name': 'Linked',
        'last_name': 'Account',
        'email': 'linked.member@gym.pk',
        'phone': '03005555555',
        'cnic': '35202-5555555-5',
        'dob': '1998-03-20',
        'gender': 'Male',
        'create_user': 'y',
        'temp_password': 'TempPassword@123'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"registered successfully" in resp.data

    with app.app_context():
        created_mem = Member.active().filter_by(email='linked.member@gym.pk').first()
        assert created_mem is not None
        assert created_mem.user_id is not None
        user = db.session.get(User, created_mem.user_id)
        assert user.role_name == 'Member'
        assert user.force_password_change == True
        assert user.check_password('TempPassword@123')

def test_supplement_sale_stock_reduction_and_expiry(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member.active().first()
        mem_id = mem.id
        sup_active = Supplement(
            name='Test Whey',
            brand='Optimum',
            category='Protein',
            price=Decimal('10000.00'),
            stock_quantity=5,
            expiry_date=date.today() + timedelta(days=90)
        )
        sup_expired = Supplement(
            name='Expired Creatine',
            brand='Optimum',
            category='Creatine',
            price=Decimal('4000.00'),
            stock_quantity=10,
            expiry_date=date.today() - timedelta(days=10)
        )
        db.session.add_all([sup_active, sup_expired])
        db.session.commit()
        act_id = sup_active.id
        exp_id = sup_expired.id

    # 1. Successful sale of 2 units
    resp = client.post('/nutrition/sales', data={
        'supplement_id': act_id,
        'member_id': mem_id,
        'quantity': 2,
        'unit_price': 10000.00
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sale of 2x" in resp.data

    with app.app_context():
        sup_check = db.session.get(Supplement, act_id)
        assert sup_check.stock_quantity == 3  # Reduced by 2

    # 2. Rejection of quantity > available stock (attempting 5 when 3 left)
    resp2 = client.post('/nutrition/sales', data={
        'supplement_id': act_id,
        'member_id': mem_id,
        'quantity': 5,
        'unit_price': 10000.00
    }, follow_redirects=True)
    assert resp2.status_code == 200
    assert b"Insufficient stock" in resp2.data

    # 3. Rejection of expired supplement
    resp3 = client.post('/nutrition/sales', data={
        'supplement_id': exp_id,
        'member_id': mem_id,
        'quantity': 1,
        'unit_price': 4000.00
    }, follow_redirects=True)
    assert resp3.status_code == 200
    assert b"Cannot sell expired supplement" in resp3.data

def test_locker_assignment_validations(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        br = Branch.active().first()
        area = Area.active().first()
        mem = Member.active().first()
        mem_id = mem.id
        locker = Locker(
            branch_id=br.id,
            area_id=area.id,
            locker_number='L-TEST-99',
            locker_type='Standard',
            is_occupied=False
        )
        db.session.add(locker)
        db.session.commit()
        locker_id = locker.id

    # 1. Invalid dates (end_date <= start_date)
    resp_invalid_date = client.post('/operations/lockers', data={
        'action': 'assign_locker',
        'locker_id': locker_id,
        'member_id': mem_id,
        'start_date': str(date.today()),
        'end_date': str(date.today())  # Same date -> rejected
    }, follow_redirects=True)
    assert resp_invalid_date.status_code == 200
    assert b"strictly after start date" in resp_invalid_date.data

    # 2. Valid assignment
    resp_valid = client.post('/operations/lockers', data={
        'action': 'assign_locker',
        'locker_id': locker_id,
        'member_id': mem_id,
        'start_date': str(date.today()),
        'end_date': str(date.today() + timedelta(days=30))
    }, follow_redirects=True)
    assert resp_valid.status_code == 200
    assert b"assigned to member" in resp_valid.data

    with app.app_context():
        loc_check = db.session.get(Locker, locker_id)
        assert loc_check.is_occupied == True

    # 3. Double assign occupied locker -> rejected
    resp_occupied = client.post('/operations/lockers', data={
        'action': 'assign_locker',
        'locker_id': locker_id,
        'member_id': mem_id,
        'start_date': str(date.today()),
        'end_date': str(date.today() + timedelta(days=30))
    }, follow_redirects=True)
    assert resp_occupied.status_code == 200
    assert b"already occupied" in resp_occupied.data

def test_member_restore_action(client, app):
    login_as(client, 'admin', 'Admin@12345')
    with app.app_context():
        mem = Member(
            membership_number='MEM-RESTORE-TEST',
            branch_id=1,
            first_name='RestoreMe',
            last_name='User',
            email='restore.me@gym.pk',
            phone='03009999999',
            cnic='35202-9999999-9',
            dob=date(1993, 7, 7),
            gender='Female'
        )
        db.session.add(mem)
        db.session.commit()
        mem.soft_delete(user_id=1)
        db.session.commit()
        mem_id = mem.id

    # Restore the member
    resp = client.post(f'/members/{mem_id}/restore', follow_redirects=True)
    assert resp.status_code == 200
    assert b"restored successfully" in resp.data

    with app.app_context():
        restored = db.session.get(Member, mem_id)
        assert restored.is_deleted == False
        assert restored.status == 'active'
