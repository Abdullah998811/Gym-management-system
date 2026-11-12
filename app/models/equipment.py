from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models.base import BaseModel

class Vendor(BaseModel):
    __tablename__ = 'vendors'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    contact_person = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=True)

    equipment = db.relationship('Equipment', back_populates='vendor')
    purchase_orders = db.relationship('PurchaseOrder', back_populates='vendor')

    def __repr__(self):
        return f"<Vendor {self.name}>"

class EquipmentCategory(BaseModel):
    __tablename__ = 'equipment_categories'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    equipment = db.relationship('Equipment', back_populates='category', cascade='all, delete-orphan')
    po_items = db.relationship('PurchaseOrderItem', back_populates='category')

    def __repr__(self):
        return f"<EquipmentCategory {self.name}>"

class Equipment(BaseModel):
    __tablename__ = 'equipment'

    category_id = db.Column(db.Integer, db.ForeignKey('equipment_categories.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    purchase_date = db.Column(db.Date, nullable=False)
    purchase_price = db.Column(db.Numeric(12, 2), nullable=False)
    warranty_expiry = db.Column(db.Date, nullable=True)
    condition_status = db.Column(db.String(50), default='Good', nullable=False)  # Excellent, Good, Maintenance Due, Out of Order

    category = db.relationship('EquipmentCategory', back_populates='equipment')
    vendor = db.relationship('Vendor', back_populates='equipment')
    area = db.relationship('Area', back_populates='equipment')
    maintenance_records = db.relationship('MaintenanceRecord', back_populates='equipment', cascade='all, delete-orphan')
    issues = db.relationship('EquipmentIssue', back_populates='equipment', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Equipment {self.name} ({self.serial_number})>"

class MaintenanceRecord(BaseModel):
    __tablename__ = 'maintenance_records'

    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id', ondelete='CASCADE'), nullable=False)
    maintenance_date = db.Column(db.Date, default=date.today, nullable=False)
    performed_by = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    next_due_date = db.Column(db.Date, nullable=False)

    equipment = db.relationship('Equipment', back_populates='maintenance_records')

class EquipmentIssue(BaseModel):
    __tablename__ = 'equipment_issues'

    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id', ondelete='CASCADE'), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_date = db.Column(db.Date, default=date.today, nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='Medium', nullable=False)  # Low, Medium, High, Critical
    resolution_status = db.Column(db.String(20), default='Open', nullable=False)  # Open, In Progress, Resolved

    equipment = db.relationship('Equipment', back_populates='issues')
    reporter = db.relationship('User')

class PurchaseOrder(BaseModel):
    __tablename__ = 'purchase_orders'

    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    order_date = db.Column(db.Date, default=date.today, nullable=False)
    expected_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    order_status = db.Column(db.String(20), default='Pending', nullable=False)  # Pending, Approved, Delivered, Cancelled

    vendor = db.relationship('Vendor', back_populates='purchase_orders')
    items = db.relationship('PurchaseOrderItem', back_populates='purchase_order', cascade='all, delete-orphan')

class PurchaseOrderItem(BaseModel):
    __tablename__ = 'purchase_order_items'

    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('equipment_categories.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    line_total = db.Column(db.Numeric(12, 2), nullable=False)

    purchase_order = db.relationship('PurchaseOrder', back_populates='items')
    category = db.relationship('EquipmentCategory', back_populates='po_items')
