from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models.base import BaseModel

class MembershipPlan(BaseModel):
    __tablename__ = 'membership_plans'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    plan_type = db.Column(db.String(50), nullable=False)  # Monthly, Quarterly, Biannual, Annual
    duration_days = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    max_classes_per_week = db.Column(db.Integer, default=5, nullable=False)

    features = db.relationship('PlanFeature', back_populates='plan', cascade='all, delete-orphan')
    memberships = db.relationship('Membership', back_populates='plan', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<MembershipPlan {self.name} - PKR {self.price}>"

class PlanFeature(BaseModel):
    __tablename__ = 'plan_features'

    plan_id = db.Column(db.Integer, db.ForeignKey('membership_plans.id', ondelete='CASCADE'), nullable=False)
    feature_name = db.Column(db.String(100), nullable=False)
    is_included = db.Column(db.Boolean, default=True, nullable=False)

    plan = db.relationship('MembershipPlan', back_populates='features')

class Membership(BaseModel):
    __tablename__ = 'memberships'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('membership_plans.id'), nullable=False, index=True)
    start_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    price_paid = db.Column(db.Numeric(12, 2), nullable=False)
    auto_renew = db.Column(db.Boolean, default=False, nullable=False)

    member = db.relationship('Member', back_populates='memberships')
    plan = db.relationship('MembershipPlan', back_populates='memberships')
    freezes = db.relationship('MembershipFreeze', back_populates='membership', cascade='all, delete-orphan')
    renewals = db.relationship('MembershipRenewal', back_populates='membership', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', back_populates='membership')

    @property
    def is_expired(self):
        from app.utils.helpers import today_pk
        return self.end_date < today_pk()

    @property
    def is_frozen(self):
        from app.utils.helpers import today_pk
        today = today_pk()
        for f in self.freezes:
            if not f.is_deleted and f.status in ('active', 'approved', 'Active', 'Approved') and f.start_date <= today <= f.end_date:
                return True
        return self.status == 'frozen'

    @property
    def days_remaining(self):
        from app.utils.helpers import today_pk
        delta = (self.end_date - today_pk()).days
        return max(0, delta)

    def __repr__(self):
        return f"<Membership #{self.id} for Member {self.member_id}>"

class MembershipFreeze(BaseModel):
    __tablename__ = 'membership_freezes'

    membership_id = db.Column(db.Integer, db.ForeignKey('memberships.id', ondelete='CASCADE'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    membership = db.relationship('Membership', back_populates='freezes')
    approver = db.relationship('User')

class MembershipRenewal(BaseModel):
    __tablename__ = 'membership_renewals'

    membership_id = db.Column(db.Integer, db.ForeignKey('memberships.id', ondelete='CASCADE'), nullable=False)
    renewal_date = db.Column(db.Date, default=date.today, nullable=False)
    extended_until = db.Column(db.Date, nullable=False)
    amount_paid = db.Column(db.Numeric(12, 2), nullable=False)

    membership = db.relationship('Membership', back_populates='renewals')

class Promotion(BaseModel):
    __tablename__ = 'promotions'

    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    discount_pct = db.Column(db.Numeric(12, 2), default=Decimal('10.00'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    max_uses = db.Column(db.Integer, default=100, nullable=False)
    current_uses = db.Column(db.Integer, default=0, nullable=False)

    member_promotions = db.relationship('MemberPromotion', back_populates='promotion', cascade='all, delete-orphan')

    def is_valid(self):
        today = date.today()
        return (not self.is_deleted and 
                self.status == 'active' and 
                self.start_date <= today <= self.end_date and 
                self.current_uses < self.max_uses)

class MemberPromotion(BaseModel):
    __tablename__ = 'member_promotions'

    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    promotion_id = db.Column(db.Integer, db.ForeignKey('promotions.id', ondelete='CASCADE'), nullable=False)
    applied_date = db.Column(db.Date, default=date.today, nullable=False)

    member = db.relationship('Member', back_populates='member_promotions')
    promotion = db.relationship('Promotion', back_populates='member_promotions')
