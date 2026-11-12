import os
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
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

def run_seed(reset=False):
    seed_database(reset=reset)

def seed_database(reset=False):
    app = create_app()
    with app.app_context():
        if app.config.get('APP_ENV') == 'production':
            raise RuntimeError("CRITICAL: Database seeding is strictly disabled in production environments!")

        if reset:
            print("Reset flag provided. Dropping existing tables and recreating schema...")
            db.drop_all()
            db.create_all()
        else:
            db.create_all()
            # Idempotency check: if roles already exist, skip seeding
            if Role.query.first():
                print("Database already seeded (roles already exist). Skipping seed.")
                return

        print("1. Seeding Roles & Permissions...")
        roles_data = [
            ('Admin', 'Complete system administrator access'),
            ('Manager', 'Branch operations, financial and staff management'),
            ('Trainer', 'Class scheduling, personal training, and workout plans'),
            ('Receptionist', 'Front desk check-in, bookings, and customer billing'),
            ('Member', 'Gym member portal access')
        ]
        role_objs = {}
        for r_name, r_desc in roles_data:
            role = Role(name=r_name, description=r_desc)
            db.session.add(role)
            role_objs[r_name] = role

        perms_data = [
            ('Manage Members', 'manage_members', 'Add, edit, and delete members'),
            ('Manage Finances', 'manage_finances', 'Generate invoices and collect payments'),
            ('Manage Classes', 'manage_classes', 'Create classes and schedule training'),
            ('Manage Staff', 'manage_staff', 'Handle payroll, shifts and attendance'),
            ('View Reports', 'view_reports', 'Access audit logs and financial analytics')
        ]
        perm_objs = []
        for p_name, p_code, p_desc in perms_data:
            perm = Permission(name=p_name, code=p_code, description=p_desc)
            db.session.add(perm)
            perm_objs.append(perm)

        db.session.flush()

        # Link Role Permissions
        for perm in perm_objs:
            rp = RolePermission(role_id=role_objs['Admin'].id, permission_id=perm.id)
            db.session.add(rp)
        for perm in perm_objs[:3]:
            rp = RolePermission(role_id=role_objs['Manager'].id, permission_id=perm.id)
            db.session.add(rp)

        print("2. Seeding Branches & Gym Setup...")
        branches_data = [
            ('Lahore Gulberg Branch', 'LHR-01', 'Block M, Gulberg III, MM Alam Road', 'Lahore', '042-35712345', 'gulberg@titanfitness.pk', 350),
            ('Karachi Clifton Branch', 'KHI-01', 'Block 4, Marine Promenade, Clifton', 'Karachi', '021-35812345', 'clifton@titanfitness.pk', 400),
            ('Islamabad F-7 Branch', 'ISB-01', 'Jinnah Super Market, Sector F-7', 'Islamabad', '051-2651234', 'f7@titanfitness.pk', 250)
        ]
        branch_objs = []
        for b_name, b_code, b_addr, b_city, b_phone, b_email, b_cap in branches_data:
            br = Branch(name=b_name, code=b_code, address=b_addr, city=b_city, phone=b_phone, email=b_email, capacity=b_cap)
            db.session.add(br)
            branch_objs.append(br)

        db.session.flush()
        main_branch = branch_objs[0]

        # Departments
        depts_data = [
            ('Fitness & Training', 'Certified fitness coaches and class instructors'),
            ('Front Desk & Customer Care', 'Reception, customer inquiries, and locker management'),
            ('Maintenance & Hygiene', 'Gym cleanliness, machine repairs, and facility upkeep'),
            ('Accounts & Billing', 'Revenue, invoicing, and vendor payables')
        ]
        dept_objs = []
        for d_name, d_desc in depts_data:
            dept = Department(branch_id=main_branch.id, name=d_name, description=d_desc)
            db.session.add(dept)
            dept_objs.append(dept)

        db.session.flush()

        # Facilities & Areas
        fac = Facility(branch_id=main_branch.id, name='Main Fitness Complex', description='3-story fitness and athletic performance facility')
        db.session.add(fac)
        db.session.flush()

        areas_data = [
            ('Cardio Deck', 'Floor 1', 60),
            ('Free Weights & Squat Racks', 'Ground Floor', 80),
            ('Studio A - Aerobics & HIIT', 'Floor 2', 40),
            ('Male Locker Room', 'Basement', 50),
            ('Female Locker Room', 'Basement', 50)
        ]
        area_objs = []
        for a_name, a_floor, a_cap in areas_data:
            area = Area(branch_id=main_branch.id, facility_id=fac.id, name=a_name, floor=a_floor, max_capacity=a_cap)
            db.session.add(area)
            area_objs.append(area)

        # Operating Hours
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            oh = OperatingHour(branch_id=main_branch.id, day_of_week=day, opening_time='06:00', closing_time='23:00')
            db.session.add(oh)

        # Holidays
        hol = Holiday(
            branch_id=main_branch.id,
            title='Pakistan Independence Day',
            start_date=date(2026, 8, 14),
            end_date=date(2026, 8, 14),
            description='National Holiday - Gym open 08:00 to 14:00'
        )
        db.session.add(hol)
        db.session.flush()

        print("3. Seeding Demo Users for all roles...")
        default_dev_password = os.getenv('SEED_PASSWORD') or os.getenv('SEED_ADMIN_PASSWORD') or 'Admin@12345'
        demo_users = [
            ('admin', 'admin@titanfitness.pk', default_dev_password, 'Muhammad Asad (Admin)', '03001234567', 'Admin'),
            ('manager', 'manager@titanfitness.pk', default_dev_password, 'Zaryab Farooq (Manager)', '03011234567', 'Manager'),
            ('trainer', 'trainer@titanfitness.pk', default_dev_password, 'Captain Tariq Butt (Trainer)', '03021234567', 'Trainer'),
            ('receptionist', 'reception@titanfitness.pk', default_dev_password, 'Sana Mir (Receptionist)', '03031234567', 'Receptionist'),
            ('member', 'member@titanfitness.pk', default_dev_password, 'Hamza Ali (Member)', '03041234567', 'Member')
        ]
        user_objs = {}
        for u_name, u_email, u_pwd, u_full, u_phone, u_role in demo_users:
            u = User(
                username=u_name,
                email=u_email,
                full_name=u_full,
                phone=u_phone,
                role_id=role_objs[u_role].id,
                branch_id=main_branch.id,
                last_login_at=datetime.now(timezone.utc),
                last_login_ip='127.0.0.1'
            )
            u.set_password(u_pwd)
            db.session.add(u)
            user_objs[u_name] = u

        db.session.flush()

        # Login Logs
        for u in user_objs.values():
            ll = LoginLog(user_id=u.id, ip_address='127.0.0.1', status='success')
            db.session.add(ll)

        print("4. Seeding Staff, Trainers, Shifts & Payroll...")
        # Staff record for receptionist
        staff_rec = Staff(
            user_id=user_objs['receptionist'].id,
            branch_id=main_branch.id,
            department_id=dept_objs[1].id,
            job_title='Front Desk Lead',
            hire_date=date(2025, 1, 15),
            salary=45000.0
        )
        db.session.add(staff_rec)
        db.session.flush()

        staff_att = StaffAttendance(
            staff_id=staff_rec.id,
            date=date.today(),
            check_in_time='08:45',
            check_out_time='17:00',
            attendance_status='Present'
        )
        db.session.add(staff_att)

        shift1 = Shift(branch_id=main_branch.id, name='Morning Shift', start_time='06:00', end_time='14:00')
        shift2 = Shift(branch_id=main_branch.id, name='Evening Shift', start_time='14:00', end_time='22:00')
        db.session.add_all([shift1, shift2])
        db.session.flush()

        sa = ShiftAssignment(staff_id=staff_rec.id, shift_id=shift1.id, date=date.today(), notes='Front desk duty')
        db.session.add(sa)

        payroll1 = Payroll(
            staff_id=staff_rec.id,
            month_year='2026-10',
            basic_salary=45000.0,
            bonus=5000.0,
            deductions=0.0,
            net_salary=50000.0,
            payment_date=date(2026, 10, 31),
            payment_status='Paid'
        )
        db.session.add(payroll1)

        # Trainer Profile
        trainer_rec = Trainer(
            user_id=user_objs['trainer'].id,
            specialization='Strength & Conditioning & Olympic Weightlifting',
            experience_years=8,
            hourly_rate=2500.0,
            bio='Former national powerlifter and certified strength coach with over 8 years experience coaching athletes.'
        )
        db.session.add(trainer_rec)
        db.session.flush()

        ts = TrainerSpecialization(trainer_id=trainer_rec.id, skill_name='Olympic Lifting', proficiency_level='Master')
        tc = TrainerCertification(trainer_id=trainer_rec.id, title='CSCS Strength Specialist', issuing_org='NSCA', issue_date=date(2020, 5, 10))
        db.session.add_all([ts, tc])

        print("5. Seeding Membership Plans & Features...")
        plans_data = [
            ('Titan Monthly Basic', 'Monthly', 30, 6000.0, 3, 'Gym floor access, locker access, and 3 group classes weekly.'),
            ('Titan Quarterly Pro', 'Quarterly', 90, 16000.0, 5, 'Full gym access, unlimited group classes, sauna, and free towel service.'),
            ('Titan Biannual Beast', 'Biannual', 180, 28000.0, 7, 'Premium priority booking, sauna, 2 complimentary PT sessions per month.'),
            ('Titan Annual Elite VIP', 'Annual', 365, 50000.0, 10, 'All-inclusive VIP status across all branches nationwide with guest passes.')
        ]
        plan_objs = []
        for p_name, p_type, p_dur, p_prc, p_cls, p_desc in plans_data:
            plan = MembershipPlan(
                name=p_name,
                plan_type=p_type,
                duration_days=p_dur,
                price=p_prc,
                max_classes_per_week=p_cls,
                description=p_desc
            )
            db.session.add(plan)
            plan_objs.append(plan)

        db.session.flush()

        features_data = [
            'Cardio & Machine Floor Access',
            'Heavy Free Weight & Deadlift Platforms',
            'Steam Room & Dry Sauna',
            'Personal Locker & Showers',
            'Monthly Body Composition & BMI Analysis'
        ]
        for plan in plan_objs:
            for feat in features_data:
                pf = PlanFeature(plan_id=plan.id, feature_name=feat, is_included=True)
                db.session.add(pf)

        promo = Promotion(
            code='FIT2026',
            title='New Year Fitness Surge',
            discount_pct=15.0,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            max_uses=200,
            current_uses=5
        )
        db.session.add(promo)
        db.session.flush()

        print("6. Seeding Pakistani Members, Profiles & Measurements...")
        pakistani_members = [
            ('Hamza', 'Ali', 'member@titanfitness.pk', '03041234567', '42101-1234567-1', date(1996, 5, 14), 'Male', 'B+', user_objs['member'].id),
            ('Bilal', 'Khan', 'bilal.khan@example.pk', '03009876543', '35201-9876543-1', date(1992, 8, 20), 'Male', 'O+', None),
            ('Ayesha', 'Tariq', 'ayesha.t@example.pk', '03214567890', '35202-4567890-2', date(1998, 11, 3), 'Female', 'A+', None),
            ('Usman', 'Malik', 'usman.malik@example.pk', '03335551234', '37405-5551234-3', date(1989, 2, 18), 'Male', 'B-', None),
            ('Fatima', 'Noor', 'fatima.noor@example.pk', '03451112233', '42201-1112233-4', date(1995, 7, 29), 'Female', 'AB+', None),
            ('Zainab', 'Bibi', 'zainab.bibi@example.pk', '03058889900', '35201-8889900-6', date(2000, 4, 12), 'Female', 'O-', None),
            ('Saad', 'Rafiq', 'saad.rafiq@example.pk', '03127778899', '38403-7778899-7', date(1994, 9, 25), 'Male', 'A-', None),
            ('Omar', 'Farooq', 'omar.farooq@example.pk', '03023334455', '35202-3334455-9', date(1991, 12, 10), 'Male', 'B+', None)
        ]
        member_objs = []
        for idx, (fn, ln, em, ph, cnic, dob, gdr, bg, uid) in enumerate(pakistani_members):
            mem = Member(
                membership_number=f"MEM-202611-{1001 + idx}",
                user_id=uid,
                branch_id=main_branch.id,
                first_name=fn,
                last_name=ln,
                email=em,
                phone=ph,
                cnic=cnic,
                dob=dob,
                gender=gdr,
                blood_group=bg,
                join_date=date.today() - timedelta(days=60 + idx * 10),
                created_by=user_objs['admin'].id,
                updated_by=user_objs['admin'].id
            )
            db.session.add(mem)
            member_objs.append(mem)

        db.session.flush()

        # Profiles, Emergency Contacts, Measurements, Goals & Notes
        for i, m in enumerate(member_objs):
            prof = MemberProfile(
                member_id=m.id,
                address=f"House {12 + i}, Street {3 + i}, Sector Y",
                city='Lahore',
                fitness_level='Intermediate' if i % 2 == 0 else 'Advanced',
                medical_conditions='None' if i % 3 != 0 else 'Mild knee stiffness on heavy squats'
            )
            ec = EmergencyContact(
                member_id=m.id,
                name=f"{m.last_name} Senior",
                relationship='Parent / Next of Kin',
                phone=f"0300{i}112233",
                address='Lahore, Pakistan'
            )
            doc = MemberDocument(
                member_id=m.id,
                title='CNIC & Health Clearance Form',
                document_type='ID Card',
                file_path='documents/clearance.pdf'
            )
            db.session.add_all([prof, ec, doc])

            # Historical measurements
            w_base = 82.0 - (i * 2.0)
            h_base = 178.0
            for step in range(3, -1, -1):
                meas_date = date.today() - timedelta(days=step * 20)
                wt = w_base - ((3 - step) * 1.2)
                bmi = MemberMeasurement.calculate_bmi(wt, h_base)
                meas = MemberMeasurement(
                    member_id=m.id,
                    measurement_date=meas_date,
                    weight_kg=wt,
                    height_cm=h_base,
                    bmi=bmi,
                    chest_cm=102.0,
                    waist_cm=86.0 - (3 - step),
                    hips_cm=98.0,
                    bicep_cm=38.0 + (3 - step) * 0.3,
                    body_fat_pct=18.0 - (3 - step) * 0.8
                )
                db.session.add(meas)

            # Goals
            goal = MemberGoal(
                member_id=m.id,
                goal_type='Strength & Power',
                target_value='140 kg Bench Press',
                current_value='120 kg',
                target_date=date.today() + timedelta(days=90),
                achieved=False
            )
            note = MemberNote(
                member_id=m.id,
                author_id=user_objs['trainer'].id,
                note_text=f"Athlete {m.first_name} showed impressive form on compound lifts. Emphasize rotator cuff warmups.",
                note_type='Performance'
            )
            db.session.add_all([goal, note])

            # Membership Subscription
            selected_plan = plan_objs[i % len(plan_objs)]
            ms_start = date.today() - timedelta(days=30)
            ms_end = ms_start + timedelta(days=selected_plan.duration_days)
            ms = Membership(
                member_id=m.id,
                plan_id=selected_plan.id,
                start_date=ms_start,
                end_date=ms_end,
                price_paid=selected_plan.price,
                auto_renew=True
            )
            db.session.add(ms)

        db.session.flush()

        # Membership Freeze & Renewal samples
        first_ms = member_objs[0].memberships[0]
        mf = MembershipFreeze(
            membership_id=first_ms.id,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=3),
            reason='Travelled out of city for business trip',
            approved_by=user_objs['manager'].id
        )
        mr = MembershipRenewal(
            membership_id=first_ms.id,
            renewal_date=date.today() - timedelta(days=30),
            extended_until=first_ms.end_date,
            amount_paid=first_ms.price_paid
        )
        mp = MemberPromotion(member_id=member_objs[0].id, promotion_id=promo.id, applied_date=date.today())
        db.session.add_all([mf, mr, mp])

        print("7. Seeding Classes, Bookings, PT & Workouts...")
        class_types_data = [
            ('CrossFit & Functional Fitness', 'High-power metabolic conditioning and Olympic weightlifting', 'High'),
            ('HIIT Athletic Conditioning', 'Cardiovascular calorie incinerator with explosive bodyweight drills', 'High'),
            ('Heavy Iron Powerlifting', 'Low-rep squat, bench press, deadlift mechanics', 'Extreme'),
            ('Restorative Vinyasa Yoga', 'Flexibility, core stabilization and breath work', 'Low')
        ]
        ct_objs = []
        for ct_name, ct_desc, ct_int in class_types_data:
            ct = ClassType(name=ct_name, description=ct_desc, intensity_level=ct_int)
            db.session.add(ct)
            ct_objs.append(ct)

        db.session.flush()

        gym_classes_data = [
            (ct_objs[0].id, 'Spartan CrossFit WOD', 20, 'Advanced'),
            (ct_objs[1].id, 'Morning HIIT Blast', 25, 'All Levels'),
            (ct_objs[2].id, 'Deadlift & Squat Lab', 15, 'Intermediate'),
            (ct_objs[3].id, 'Sunset Flow Yoga', 20, 'All Levels')
        ]
        gc_objs = []
        for c_tid, c_title, c_cap, c_diff in gym_classes_data:
            gc = GymClass(
                class_type_id=c_tid,
                trainer_id=trainer_rec.id,
                branch_id=main_branch.id,
                title=c_title,
                max_capacity=c_cap,
                difficulty_level=c_diff,
                description='High-performance group conditioning class led by head coaches.'
            )
            db.session.add(gc)
            gc_objs.append(gc)

        db.session.flush()

        # Class Schedules
        for idx, gc in enumerate(gc_objs):
            cs = ClassSchedule(
                class_id=gc.id,
                area_id=area_objs[2].id,
                day_of_week=['Monday', 'Wednesday', 'Friday', 'Saturday'][idx % 4],
                start_time='07:00',
                end_time='08:00'
            )
            db.session.add(cs)

        # Class Bookings & Attendance
        for i in range(4):
            cb = ClassBooking(
                class_id=gc_objs[0].id,
                member_id=member_objs[i].id,
                booking_date=date.today(),
                booking_status='Confirmed'
            )
            ca = ClassAttendance(
                class_id=gc_objs[0].id,
                member_id=member_objs[i].id,
                date=date.today() - timedelta(days=2),
                attendance_status='Attended'
            )
            db.session.add_all([cb, ca])

        wl = ClassWaitlist(class_id=gc_objs[0].id, member_id=member_objs[4].id, request_date=date.today(), priority=1)
        db.session.add(wl)

        # PT Sessions
        pt1 = PTSession(
            trainer_id=trainer_rec.id,
            member_id=member_objs[0].id,
            session_date=date.today(),
            start_time='16:00',
            duration_minutes=60,
            focus_area='Deadlift Form Breakdown',
            notes='Focus on hip hinge and lat engagement.',
            session_status='Scheduled'
        )
        db.session.add(pt1)

        # Exercises & Workout Plans
        ecat = ExerciseCategory(name='Barbell Compound Lifts', description='Foundational heavy multi-joint movements')
        db.session.add(ecat)
        db.session.flush()

        ex1 = Exercise(category_id=ecat.id, name='Barbell Back Squat', description='Deep squat with barbell on traps', target_muscle='Quadriceps & Glutes', difficulty='Hard')
        ex2 = Exercise(category_id=ecat.id, name='Conventional Deadlift', description='Barbell lift off floor to lockout', target_muscle='Hamstrings, Glutes & Erector Spinae', difficulty='Hard')
        db.session.add_all([ex1, ex2])
        db.session.flush()

        wp = WorkoutPlan(
            trainer_id=trainer_rec.id,
            title='8-Week Hypertrophy & Strength Split',
            goal='Maximum Hypertrophy',
            duration_weeks=8,
            description='Heavy compound lifts paired with high volume accessory isolation movements.'
        )
        db.session.add(wp)
        db.session.flush()

        wpe1 = WorkoutPlanExercise(plan_id=wp.id, exercise_id=ex1.id, day_number=1, sets=4, reps='8-10', rest_seconds=90)
        wpe2 = WorkoutPlanExercise(plan_id=wp.id, exercise_id=ex2.id, day_number=2, sets=4, reps='6-8', rest_seconds=120)
        mwp = MemberWorkoutPlan(member_id=member_objs[0].id, plan_id=wp.id, assigned_date=date.today(), is_current=True)
        db.session.add_all([wpe1, wpe2, mwp])

        print("8. Seeding Meals, Diet Plans & Supplements...")
        meal1 = Meal(name='Grilled Chicken Breast with Quinoa', meal_time='Lunch', calories=520, protein_g=48.0, carbs_g=45.0, fats_g=10.0, description='Lean skinless chicken breast with steamed spiced quinoa and broccoli.')
        meal2 = Meal(name='Oatmeal with Whey & Peanut Butter', meal_time='Breakfast', calories=480, protein_g=35.0, carbs_g=55.0, fats_g=14.0, description='Rolled oats soaked in almond milk, mixed with whey isolate and organic peanut butter.')
        db.session.add_all([meal1, meal2])
        db.session.flush()

        dp = DietPlan(title='High Protein Clean Bulk 2600 kcal', goal='Hypertrophy & Clean Muscle', daily_calories=2600, description='High protein intake distributed over 4 meals daily.')
        db.session.add(dp)
        db.session.flush()

        dpm1 = DietPlanMeal(diet_plan_id=dp.id, meal_id=meal1.id, day_of_week='Monday')
        dpm2 = DietPlanMeal(diet_plan_id=dp.id, meal_id=meal2.id, day_of_week='Monday')
        mdp = MemberDietPlan(member_id=member_objs[0].id, diet_plan_id=dp.id, assigned_date=date.today(), is_current=True)
        db.session.add_all([dpm1, dpm2, mdp])

        supp1 = Supplement(name='Gold Standard 100% Whey', brand='Optimum Nutrition', category='Whey Protein', price=14500.0, stock_quantity=35, expiry_date=date(2027, 8, 30))
        supp2 = Supplement(name='Creapure Micronized Creatine', brand='Dymatize', category='Creatine', price=6500.0, stock_quantity=50, expiry_date=date(2028, 1, 15))
        db.session.add_all([supp1, supp2])
        db.session.flush()

        sale1 = SupplementSale(supplement_id=supp1.id, member_id=member_objs[0].id, quantity=1, unit_price=14500.0, total_amount=14500.0, sale_date=date.today())
        db.session.add(sale1)

        print("9. Seeding Equipment, Vendors & Maintenance...")
        vendor = Vendor(name='TechnoGym Pakistan Direct', contact_person='Tariq Mehmood', phone='042-35889900', email='sales@technogym.pk', address='Gulberg Industrial Area, Lahore')
        db.session.add(vendor)
        db.session.flush()

        eq_cat = EquipmentCategory(name='Commercial Cardio Machines', description='Treadmills, cross-trainers, assault bikes and stairmasters')
        db.session.add(eq_cat)
        db.session.flush()

        eq1 = Equipment(
            category_id=eq_cat.id,
            vendor_id=vendor.id,
            area_id=area_objs[0].id,
            name='TechnoGym Excite Live Treadmill',
            serial_number='TG-EX-2026-001',
            purchase_date=date(2025, 3, 10),
            purchase_price=850000.0,
            warranty_expiry=date(2028, 3, 10),
            condition_status='Good'
        )
        eq2 = Equipment(
            category_id=eq_cat.id,
            vendor_id=vendor.id,
            area_id=area_objs[1].id,
            name='Eleiko Olympic Power Rack & Barbell',
            serial_number='EL-PWR-2026-04',
            purchase_date=date(2025, 4, 15),
            purchase_price=450000.0,
            warranty_expiry=date(2030, 4, 15),
            condition_status='Excellent'
        )
        db.session.add_all([eq1, eq2])
        db.session.flush()

        maint = MaintenanceRecord(
            equipment_id=eq1.id,
            maintenance_date=date(2026, 9, 15),
            performed_by='TechnoGym Official Service',
            cost=12000.0,
            notes='Lubricated running deck and calibrated digital console.',
            next_due_date=date(2026, 12, 15)
        )
        issue = EquipmentIssue(
            equipment_id=eq1.id,
            reported_by=user_objs['trainer'].id,
            reported_date=date.today() - timedelta(days=5),
            description='Emergency stop clip sensor needs slight realignment.',
            severity='Low',
            resolution_status='Resolved'
        )
        po = PurchaseOrder(vendor_id=vendor.id, order_date=date.today() - timedelta(days=40), expected_date=date.today(), total_amount=1300000.0, order_status='Delivered')
        db.session.add_all([maint, issue, po])
        db.session.flush()

        poi = PurchaseOrderItem(purchase_order_id=po.id, category_id=eq_cat.id, item_name='Olympic Weight Plates 20kg Pair', quantity=10, unit_price=25000.0, line_total=250000.0)
        db.session.add(poi)

        print("10. Seeding Finance, Invoices, Payments & Expenses...")
        exp_cat = ExpenseCategory(name='Utilities & Maintenance', description='Electricity, water, AC and generator fuel')
        db.session.add(exp_cat)
        db.session.flush()

        exp1 = Expense(category_id=exp_cat.id, branch_id=main_branch.id, title='LESCO Commercial Electricity Bill', amount=185000.0, expense_date=date.today() - timedelta(days=5), paid_to='LESCO Power Authority')
        exp2 = Expense(category_id=exp_cat.id, branch_id=main_branch.id, title='Air Conditioning Servicing & Chemical Wash', amount=25000.0, expense_date=date.today() - timedelta(days=12), paid_to='CoolCare Tech')
        db.session.add_all([exp1, exp2])

        pm_cash = PaymentMethod(name='Cash Desk', code='cash')
        pm_card = PaymentMethod(name='Visa / MasterCard Credit Card', code='card')
        pm_bank = PaymentMethod(name='Online Bank Transfer', code='online')
        db.session.add_all([pm_cash, pm_card, pm_bank])
        db.session.flush()

        disc = Discount(code='PROFIT10', title='New Member Special Voucher', amount_type='percentage', value=10.0)
        db.session.add(disc)
        db.session.flush()

        # Generate Invoices for members
        for idx, m in enumerate(member_objs[:6]):
            inv_total = 16000.0 if idx % 2 == 0 else 6000.0
            paid_status = 'Paid' if idx < 4 else ('Partial' if idx == 4 else 'Unpaid')
            inv = Invoice(
                invoice_number=f"INV-202611-{2001 + idx}",
                member_id=m.id,
                membership_id=m.memberships[0].id if m.memberships else None,
                discount_id=disc.id if idx == 0 else None,
                issue_date=date.today() - timedelta(days=15),
                due_date=date.today() + timedelta(days=15),
                subtotal=inv_total,
                tax_amount=0.0,
                discount_amount=1600.0 if idx == 0 else 0.0,
                total_amount=inv_total - (1600.0 if idx == 0 else 0.0),
                payment_status=paid_status
            )
            db.session.add(inv)
            db.session.flush()

            ii = InvoiceItem(invoice_id=inv.id, description='Quarterly Membership Subscription', quantity=1, unit_price=inv.total_amount, total_price=inv.total_amount)
            db.session.add(ii)

            if paid_status == 'Paid':
                pay = Payment(
                    invoice_id=inv.id,
                    payment_method_id=pm_card.id,
                    payment_date=date.today() - timedelta(days=14),
                    amount=inv.total_amount,
                    transaction_reference=f"TXN-{random.randint(100000, 999999)}"
                )
                db.session.add(pay)
            elif paid_status == 'Partial':
                pay = Payment(
                    invoice_id=inv.id,
                    payment_method_id=pm_cash.id,
                    payment_date=date.today() - timedelta(days=10),
                    amount=inv.total_amount / 2,
                    transaction_reference='CASH-DESK-PARTIAL'
                )
                db.session.add(pay)

        print("11. Seeding Operations, Attendance, Lockers, Visitors & Complaints...")
        # Member Attendance Logs
        for idx, m in enumerate(member_objs):
            now_utc = datetime.now(timezone.utc)
            # Check-in today
            att_today = Attendance(
                member_id=m.id,
                branch_id=main_branch.id,
                check_in_time=now_utc - timedelta(hours=1 + idx),
                check_out_time=now_utc - timedelta(minutes=15) if idx % 2 == 0 else None,
                method='Manual' if idx % 2 == 0 else 'QR'
            )
            # Check-in yesterday
            att_yest = Attendance(
                member_id=m.id,
                branch_id=main_branch.id,
                check_in_time=now_utc - timedelta(days=1, hours=2 + idx),
                check_out_time=now_utc - timedelta(days=1, hours=1),
                method='QR'
            )
            db.session.add_all([att_today, att_yest])

        # Lockers
        locker1 = Locker(branch_id=main_branch.id, area_id=area_objs[3].id, locker_number='L-101', locker_type='Standard', is_occupied=True)
        locker2 = Locker(branch_id=main_branch.id, area_id=area_objs[3].id, locker_number='L-102', locker_type='Standard', is_occupied=False)
        locker3 = Locker(branch_id=main_branch.id, area_id=area_objs[3].id, locker_number='VIP-01', locker_type='VIP', is_occupied=False)
        db.session.add_all([locker1, locker2, locker3])
        db.session.flush()

        la = LockerAssignment(
            locker_id=locker1.id,
            member_id=member_objs[0].id,
            start_date=date.today() - timedelta(days=15),
            end_date=date.today() + timedelta(days=45),
            assignment_status='Active'
        )
        db.session.add(la)

        # Visitors
        vis1 = Visitor(branch_id=main_branch.id, name='Kamran Akmal', phone='03221234567', purpose='Gym tour & quarterly inquiry', visit_date=date.today(), follow_up_status='Interested')
        vis2 = Visitor(branch_id=main_branch.id, name='Shahid Afridi Jr.', phone='03019876543', purpose='CrossFit program inquiry', visit_date=date.today() - timedelta(days=1), follow_up_status='Joined')
        db.session.add_all([vis1, vis2])

        # Feedback & Complaints
        fb = Feedback(member_id=member_objs[0].id, rating=5, comments='Outstanding training atmosphere, world-class equipment and friendly staff!')
        comp = Complaint(member_id=member_objs[1].id, subject='Water cooler temperature on Floor 1', description='The water cooler on the cardio deck was not chilling properly yesterday afternoon.', priority='Low', resolution_status='In Progress')
        db.session.add_all([fb, comp])

        # Notifications
        for u in user_objs.values():
            notif1 = Notification(user_id=u.id, title='Welcome to Titan Fitness', message='Your account is ready. Explore modules and fitness schedules.', notification_type='success', is_read=False)
            notif2 = Notification(user_id=u.id, title='Gym Timings Update', message='Operating hours on Saturday extended till 23:00.', notification_type='info', is_read=False)
            db.session.add_all([notif1, notif2])

        # Initial Audit Log
        audit = AuditLog(
            user_id=user_objs['admin'].id,
            action='CREATE',
            table_name='system_seed',
            record_id=1,
            new_values='{"status": "Database successfully populated with 73 related models"}',
            ip_address='127.0.0.1'
        )
        db.session.add(audit)

        db.session.commit()
        print("\n=======================================================")
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("ALL 73 TABLES ARE POPULATED WITH REALISTIC PAKISTANI DATA!")
        print("=======================================================")
        print("DEMO USER ACCOUNTS CONFIGURED FOR DEVELOPMENT TESTING:")
        print("  Usernames: admin, manager, trainer, receptionist, member")
        print("  (Passwords read from SEED_PASSWORD or SEED_ADMIN_PASSWORD environment variables)")
        print("=======================================================\n")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Seed Gym Management System Database")
    parser.add_argument('--reset', action='store_true', help='Drop all tables and recreate schema (local use only)')
    args = parser.parse_args()
    seed_database(reset=args.reset)
