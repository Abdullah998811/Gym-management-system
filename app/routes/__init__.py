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

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'members_bp',
    'plans_bp',
    'trainers_bp',
    'classes_bp',
    'nutrition_bp',
    'equipment_bp',
    'finance_bp',
    'operations_bp',
    'notifications_bp',
    'reports_bp'
]
