import sys
import os
os.environ['APP_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-for-pytest-execution-only'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app
from app.config import Config
from app.extensions import db
from seed import seed_database

class PytestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SERVER_NAME = 'localhost'

@pytest.fixture(scope='session')
def app():
    app = create_app(PytestConfig)
    with app.app_context():
        # Populate in-memory database using seed logic
        from app.models import (
            Role, Permission, RolePermission, User, LoginLog,
            Branch, Department, Facility, Area, OperatingHour, Holiday,
            Member, MemberProfile, EmergencyContact, MemberDocument,
            MemberMeasurement, MemberGoal, MemberNote,
            MembershipPlan, PlanFeature, Membership, MembershipFreeze,
            MembershipRenewal, Promotion, MemberPromotion,
            Trainer, TrainerSpecialization, TrainerCertification, Staff,
            StaffAttendance, Shift, ShiftAssignment, Payroll,
            ClassType, GymClass, ClassSchedule, ClassBooking, ClassWaitlist,
            ClassAttendance, PTSession, ExerciseCategory, Exercise, WorkoutPlan,
            WorkoutPlanExercise, MemberWorkoutPlan,
            Meal, DietPlan, DietPlanMeal, MemberDietPlan, Supplement, SupplementSale,
            Vendor, EquipmentCategory, Equipment, MaintenanceRecord,
            EquipmentIssue, PurchaseOrder, PurchaseOrderItem,
            ExpenseCategory, Expense, PaymentMethod, Discount, Invoice,
            InvoiceItem, Payment,
            Attendance, Locker, LockerAssignment, Visitor, Feedback,
            Complaint, Notification, AuditLog
        )
        db.create_all()

    # Seed the test in-memory database
    from seed import seed_database
    # Temporarily set app context
    with app.app_context():
        # Run seeding manually for memory db
        from datetime import date, datetime, timedelta, timezone
        from decimal import Decimal
        roles_data = [
            ('Admin', 'Admin'), ('Manager', 'Manager'), ('Trainer', 'Trainer'),
            ('Receptionist', 'Receptionist'), ('Member', 'Member')
        ]
        role_objs = {}
        for r_name, r_desc in roles_data:
            role = Role(name=r_name, description=r_desc)
            db.session.add(role)
            role_objs[r_name] = role

        perm = Permission(name='Manage', code='manage', description='Manage')
        db.session.add(perm)
        db.session.flush()

        rp = RolePermission(role_id=role_objs['Admin'].id, permission_id=perm.id)
        db.session.add(rp)

        br = Branch(name='Lahore Branch', code='LHR-01', address='Gulberg', city='Lahore', phone='042-111', email='lhr@gym.pk', capacity=200)
        db.session.add(br)
        db.session.flush()

        dept = Department(branch_id=br.id, name='Training', description='Fitness')
        fac = Facility(branch_id=br.id, name='Main Hall', description='Complex')
        db.session.add_all([dept, fac])
        db.session.flush()

        area = Area(branch_id=br.id, facility_id=fac.id, name='Weights Area', floor='Ground', max_capacity=50)
        oh = OperatingHour(branch_id=br.id, day_of_week='Monday', opening_time='06:00', closing_time='22:00')
        hol = Holiday(branch_id=br.id, title='Eid', start_date=date(2026, 6, 1), end_date=date(2026, 6, 2))
        db.session.add_all([area, oh, hol])

        demo_users = [
            ('admin', 'admin@gym.pk', 'Admin@12345', 'Muhammad Asad', '03001234567', 'Admin'),
            ('manager', 'manager@gym.pk', 'Admin@12345', 'Zaryab Farooq', '03011234567', 'Manager'),
            ('trainer', 'trainer@gym.pk', 'Admin@12345', 'Tariq Butt', '03021234567', 'Trainer'),
            ('receptionist', 'reception@gym.pk', 'Admin@12345', 'Sana Mir', '03031234567', 'Receptionist'),
            ('member', 'member@gym.pk', 'Admin@12345', 'Hamza Ali', '03041234567', 'Member')
        ]
        user_objs = {}
        for un, em, pw, fn, ph, rn in demo_users:
            u = User(username=un, email=em, full_name=fn, phone=ph, role_id=role_objs[rn].id, branch_id=br.id)
            u.set_password(pw)
            db.session.add(u)
            user_objs[un] = u

        db.session.flush()

        for u in user_objs.values():
            ll = LoginLog(user_id=u.id, ip_address='127.0.0.1', status='success')
            db.session.add(ll)

        st = Staff(user_id=user_objs['receptionist'].id, branch_id=br.id, department_id=dept.id, job_title='Desk', hire_date=date.today(), salary=40000.0)
        tr = Trainer(user_id=user_objs['trainer'].id, specialization='Strength', experience_years=5, hourly_rate=2000.0)
        db.session.add_all([st, tr])
        db.session.flush()

        ts = TrainerSpecialization(trainer_id=tr.id, skill_name='Lifting', proficiency_level='Master')
        tc = TrainerCertification(trainer_id=tr.id, title='CSCS', issuing_org='NSCA', issue_date=date(2022, 1, 1))
        sa_att = StaffAttendance(staff_id=st.id, date=date.today(), check_in_time='09:00', attendance_status='Present')
        sh = Shift(branch_id=br.id, name='Morning', start_time='06:00', end_time='14:00')
        db.session.add_all([ts, tc, sa_att, sh])
        db.session.flush()

        sa_asn = ShiftAssignment(staff_id=st.id, shift_id=sh.id, date=date.today())
        pr = Payroll(staff_id=st.id, month_year='2026-10', basic_salary=40000.0, net_salary=40000.0, payment_date=date.today(), payment_status='Paid')
        db.session.add_all([sa_asn, pr])

        plan = MembershipPlan(name='Gold Monthly', plan_type='Monthly', duration_days=30, price=5000.0, max_classes_per_week=5)
        db.session.add(plan)
        db.session.flush()

        pf = PlanFeature(plan_id=plan.id, feature_name='Sauna', is_included=True)
        promo = Promotion(code='PROMO1', title='Promo', discount_pct=10.0, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), max_uses=100)
        db.session.add_all([pf, promo])
        db.session.flush()

        mem = Member(
            membership_number='MEM-202611-1001',
            user_id=user_objs['member'].id,
            branch_id=br.id,
            first_name='Hamza',
            last_name='Ali',
            email='member@gym.pk',
            phone='03041234567',
            cnic='42101-1234567-1',
            dob=date(1996, 5, 14),
            gender='Male',
            join_date=date.today()
        )
        db.session.add(mem)
        db.session.flush()

        mp = MemberProfile(member_id=mem.id, address='Lahore', city='Lahore', fitness_level='Intermediate')
        ec = EmergencyContact(member_id=mem.id, name='Father', relationship='Parent', phone='03001112233')
        mdoc = MemberDocument(member_id=mem.id, title='ID', document_type='ID', file_path='doc.pdf')
        mm = MemberMeasurement(member_id=mem.id, measurement_date=date.today(), weight_kg=78.0, height_cm=178.0, bmi=24.6)
        mg = MemberGoal(member_id=mem.id, goal_type='Weight Loss', target_value='75 kg', target_date=date.today() + timedelta(days=60))
        mn = MemberNote(member_id=mem.id, author_id=user_objs['trainer'].id, note_text='Good form')
        ms = Membership(member_id=mem.id, plan_id=plan.id, start_date=date.today(), end_date=date.today() + timedelta(days=30), price_paid=5000.0)
        db.session.add_all([mp, ec, mdoc, mm, mg, mn, ms])
        db.session.flush()

        mf = MembershipFreeze(membership_id=ms.id, start_date=date.today() - timedelta(days=15), end_date=date.today() - timedelta(days=10), reason='Trip')
        mr = MembershipRenewal(membership_id=ms.id, renewal_date=date.today(), extended_until=date.today() + timedelta(days=30), amount_paid=5000.0)
        mprom = MemberPromotion(member_id=mem.id, promotion_id=promo.id, applied_date=date.today())
        db.session.add_all([mf, mr, mprom])

        ct = ClassType(name='CrossFit', description='HIIT', intensity_level='High')
        db.session.add(ct)
        db.session.flush()

        gc = GymClass(class_type_id=ct.id, trainer_id=tr.id, branch_id=br.id, title='CrossFit Blast', max_capacity=20, difficulty_level='All Levels')
        db.session.add(gc)
        db.session.flush()

        cs = ClassSchedule(class_id=gc.id, area_id=area.id, day_of_week='Monday', start_time='07:00', end_time='08:00')
        cb = ClassBooking(class_id=gc.id, member_id=mem.id, booking_date=date.today(), booking_status='Confirmed')
        cw = ClassWaitlist(class_id=gc.id, member_id=mem.id, booking_date=date.today(), request_date=date.today(), priority=1)
        ca = ClassAttendance(class_id=gc.id, member_id=mem.id, date=date.today(), attendance_status='Attended')
        pt_s = PTSession(trainer_id=tr.id, member_id=mem.id, session_date=date.today(), start_time='16:00', duration_minutes=60, focus_area='Squats')
        db.session.add_all([cs, cb, cw, ca, pt_s])

        ecat = ExerciseCategory(name='Legs', description='Lower Body')
        db.session.add(ecat)
        db.session.flush()

        ex = Exercise(category_id=ecat.id, name='Squat', target_muscle='Quads', difficulty='Intermediate')
        db.session.add(ex)
        db.session.flush()

        wp = WorkoutPlan(trainer_id=tr.id, title='Leg Day', goal='Hypertrophy', duration_weeks=4)
        db.session.add(wp)
        db.session.flush()

        wpe = WorkoutPlanExercise(plan_id=wp.id, exercise_id=ex.id, day_number=1, sets=4, reps='10', rest_seconds=60)
        mwp = MemberWorkoutPlan(member_id=mem.id, plan_id=wp.id, assigned_date=date.today(), is_current=True)
        meal = Meal(name='Chicken', meal_time='Lunch', calories=400, protein_g=40.0, carbs_g=30.0, fats_g=10.0)
        db.session.add_all([wpe, mwp, meal])
        db.session.flush()

        dp = DietPlan(title='Clean Diet', goal='Cut', daily_calories=2000)
        db.session.add(dp)
        db.session.flush()

        dpm = DietPlanMeal(diet_plan_id=dp.id, meal_id=meal.id, day_of_week='Monday')
        mdp = MemberDietPlan(member_id=mem.id, diet_plan_id=dp.id, assigned_date=date.today(), is_current=True)
        sup = Supplement(name='Whey', brand='ON', category='Protein', price=10000.0, stock_quantity=20, expiry_date=date(2028, 1, 1))
        db.session.add_all([dpm, mdp, sup])
        db.session.flush()

        ss = SupplementSale(supplement_id=sup.id, member_id=mem.id, quantity=1, unit_price=10000.0, total_amount=10000.0, sale_date=date.today())
        vend = Vendor(name='Techno', contact_person='Ali', phone='042-123', email='v@v.pk')
        db.session.add_all([ss, vend])
        db.session.flush()

        eq_cat = EquipmentCategory(name='Cardio', description='Treadmills')
        db.session.add(eq_cat)
        db.session.flush()

        eq = Equipment(category_id=eq_cat.id, vendor_id=vend.id, area_id=area.id, name='Treadmill', serial_number='TM-101', purchase_date=date.today(), purchase_price=500000.0, condition_status='Good')
        db.session.add(eq)
        db.session.flush()

        mr_log = MaintenanceRecord(equipment_id=eq.id, maintenance_date=date.today(), performed_by='Tech', cost=5000.0, next_due_date=date.today() + timedelta(days=90))
        eq_iss = EquipmentIssue(equipment_id=eq.id, reported_by=user_objs['trainer'].id, reported_date=date.today(), description='Belt sound', severity='Low')
        po = PurchaseOrder(vendor_id=vend.id, order_date=date.today(), expected_date=date.today(), total_amount=100000.0)
        db.session.add_all([mr_log, eq_iss, po])
        db.session.flush()

        poi = PurchaseOrderItem(purchase_order_id=po.id, category_id=eq_cat.id, item_name='Plates', quantity=2, unit_price=50000.0, line_total=100000.0)
        exp_c = ExpenseCategory(name='Rent', description='Facility Rent')
        db.session.add_all([poi, exp_c])
        db.session.flush()

        exp = Expense(category_id=exp_c.id, branch_id=br.id, title='Rent Oct', amount=200000.0, expense_date=date.today(), paid_to='Landlord')
        pm_c = PaymentMethod(name='Cash', code='cash')
        disc = Discount(code='DISC5', title='5% off', amount_type='percentage', value=5.0)
        db.session.add_all([exp, pm_c, disc])
        db.session.flush()

        inv = Invoice(
            invoice_number='INV-202611-1001',
            member_id=mem.id,
            membership_id=ms.id,
            discount_id=disc.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            subtotal=5000.0,
            tax_amount=0.0,
            discount_amount=250.0,
            total_amount=4750.0,
            payment_status='Paid'
        )
        db.session.add(inv)
        db.session.flush()

        ii = InvoiceItem(invoice_id=inv.id, description='Monthly Subscription', quantity=1, unit_price=4750.0, total_price=4750.0)
        pay = Payment(invoice_id=inv.id, payment_method_id=pm_c.id, payment_date=date.today(), amount=4750.0, transaction_reference='CASH-1')
        att = Attendance(member_id=mem.id, branch_id=br.id, check_in_time=datetime.now(timezone.utc), method='Manual')
        lck = Locker(branch_id=br.id, area_id=area.id, locker_number='L-101', locker_type='Standard', is_occupied=True)
        db.session.add_all([ii, pay, att, lck])
        db.session.flush()

        lck_a = LockerAssignment(locker_id=lck.id, member_id=mem.id, start_date=date.today(), end_date=date.today() + timedelta(days=30), assignment_status='Active')
        vis = Visitor(branch_id=br.id, name='Visitor 1', phone='03001239999', purpose='Tour', visit_date=date.today(), follow_up_status='Interested')
        fb = Feedback(member_id=mem.id, rating=5, comments='Great gym', feedback_date=date.today())
        comp = Complaint(member_id=mem.id, subject='AC', description='AC warm', priority='Low', resolution_status='Pending')
        notif = Notification(user_id=user_objs['admin'].id, title='Welcome', message='Welcome', notification_type='info')
        audit = AuditLog(user_id=user_objs['admin'].id, action='CREATE', table_name='init', record_id=1, timestamp=datetime.now(timezone.utc))
        db.session.add_all([lck_a, vis, fb, comp, notif, audit])

        db.session.commit()

    return app

@pytest.fixture
def client(app):
    return app.test_client()

def login_as(client, username='admin', password='Admin@12345'):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)
