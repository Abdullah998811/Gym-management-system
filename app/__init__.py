import os
import click
from datetime import date, datetime, timezone
from flask import Flask, render_template, request
from flask_login import login_required
from app.config import Config
from app.extensions import db, migrate, login_manager, csrf, limiter
from app.models.access import User, Role
from app.utils.decorators import check_inactivity_timeout

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload and instance directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'instance/uploads'), exist_ok=True)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.filter_by(id=int(user_id), is_deleted=False).first()

    # Session inactivity check before every request
    @app.before_request
    def before_request_inactivity():
        if request.endpoint and not request.endpoint.startswith('static'):
            timeout_response = check_inactivity_timeout()
            if timeout_response:
                return timeout_response

    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: data:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "script-src 'self' 'unsafe-inline' https:;"
        )
        return response

    # Health check route (public, no authentication)
    @app.route('/health')
    def health():
        return "OK", 200

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.members import members_bp
    from app.routes.plans import plans_bp
    from app.routes.trainers import trainers_bp
    from app.routes.classes import classes_bp
    from app.routes.nutrition import nutrition_bp
    from app.routes.equipment import equipment_bp
    from app.routes.finance import finance_bp
    from app.routes.operations import operations_bp
    from app.routes.notifications import notifications_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(plans_bp)
    app.register_blueprint(trainers_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(nutrition_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reports_bp)

    # Secure authenticated file upload serving
    @app.route('/uploads/<path:filename>')
    @login_required
    def uploaded_file(filename):
        from flask import send_from_directory
        upload_folder = app.config.get('UPLOAD_FOLDER', 'instance/uploads')
        return send_from_directory(upload_folder, filename)

    # Error handling pages
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return render_template('errors/413.html'), 413

    @app.errorhandler(429)
    def ratelimit_handler(error):
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Context processors and template filters
    from app.utils.helpers import to_localtime
    app.jinja_env.filters['localtime'] = to_localtime

    @app.context_processor
    def inject_global_data():
        return {
            'app_name': 'Titan Gym Management System',
            'current_year': datetime.now(timezone.utc).year
        }

    # Register CLI Commands
    @app.cli.command('seed')
    @click.option('--reset', is_flag=True, help='Reset/clear database before seeding')
    def seed_command(reset):
        """Seed initial data into database idempotently."""
        from seed import run_seed
        run_seed(reset=reset)

    @app.cli.command('create-admin')
    @click.option('--username', default='admin', help='Admin username')
    @click.option('--email', default='admin@titanfitness.pk', help='Admin email')
    @click.option('--password', default='Admin@12345', help='Admin password')
    def create_admin_command(username, email, password):
        """Create or update admin user."""
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin', description='Administrator')
            db.session.add(admin_role)
            db.session.flush()

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(
                username=username,
                email=email,
                full_name='System Administrator',
                role_id=admin_role.id
            )
            db.session.add(user)
        user.set_password(password)
        user.is_deleted = False
        user.status = 'active'
        db.session.commit()
        print(f"Admin user '{username}' configured successfully.")

    @app.cli.command('expire-freezes')
    def expire_freezes_command():
        """Restore membership status to active when freeze period ends and activate starting freezes."""
        from app.models.plan import Membership, MembershipFreeze
        today = date.today()

        # 1. Start freezes that have arrived
        starting_freezes = MembershipFreeze.active().filter(
            MembershipFreeze.start_date <= today,
            MembershipFreeze.end_date >= today
        ).all()
        started = 0
        for f in starting_freezes:
            if f.membership and f.membership.status != 'frozen':
                f.membership.status = 'frozen'
                started += 1

        # 2. End freezes that have expired
        frozen_memberships = Membership.active().filter_by(status='frozen').all()
        restored = 0
        for m in frozen_memberships:
            active_freeze = any(
                f.start_date <= today <= f.end_date
                for f in m.freezes if not f.is_deleted and f.status == 'active'
            )
            if not active_freeze:
                m.status = 'active'
                restored += 1

        db.session.commit()
        print(f"Freeze check complete: {started} memberships frozen, {restored} memberships restored to active.")

    @app.cli.command('update-overdue')
    def update_overdue_command():
        """Update unpaid or partially paid past-due invoices to Overdue."""
        from app.models.finance import Invoice
        today = date.today()
        invoices = Invoice.active().filter(
            Invoice.due_date < today,
            Invoice.payment_status.in_(['Unpaid', 'Partial'])
        ).all()
        count = 0
        for inv in invoices:
            inv.update_status()
            count += 1
        db.session.commit()
        print(f"Overdue check complete: {count} past-due invoices updated.")

    @app.cli.command('expire-memberships')
    def expire_memberships_command():
        """Handle expired memberships, ended freezes, overdue invoices, and release expired lockers."""
        from app.utils.helpers import today_pk
        from app.models.plan import Membership, MembershipFreeze
        from app.models.finance import Invoice
        from app.models.operations import Locker, LockerAssignment
        today = today_pk()

        # 1. Expire memberships past end_date
        expired_mems = Membership.active().filter(
            Membership.status.in_(['active', 'frozen']),
            Membership.end_date < today
        ).all()
        m_count = 0
        for m in expired_mems:
            m.status = 'expired'
            m_count += 1

        # 2. Release ended freezes
        frozen_memberships = Membership.active().filter_by(status='frozen').all()
        restored = 0
        for m in frozen_memberships:
            active_freeze = any(
                f.start_date <= today <= f.end_date
                for f in m.freezes if not f.is_deleted and f.status == 'active'
            )
            if not active_freeze:
                m.status = 'active'
                restored += 1

        # 3. Update overdue invoices
        invoices = Invoice.active().filter(
            Invoice.due_date < today,
            Invoice.payment_status.in_(['Unpaid', 'Partial'])
        ).all()
        inv_count = 0
        for inv in invoices:
            inv.update_status()
            inv_count += 1

        # 4. Release expired locker assignments
        expired_lockers = LockerAssignment.active().filter(
            LockerAssignment.assignment_status == 'Active',
            LockerAssignment.end_date < today
        ).all()
        l_count = 0
        for la in expired_lockers:
            la.assignment_status = 'Expired'
            if la.locker:
                la.locker.is_occupied = False
            l_count += 1

        db.session.commit()
        print(f"Maintenance complete: {m_count} memberships expired, {restored} freezes restored, {inv_count} invoices marked overdue, {l_count} lockers released.")

    return app
