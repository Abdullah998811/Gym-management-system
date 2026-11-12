from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models.base import BaseModel

class ExpenseCategory(BaseModel):
    __tablename__ = 'expense_categories'

    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    expenses = db.relationship('Expense', back_populates='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ExpenseCategory {self.name}>"

class Expense(BaseModel):
    __tablename__ = 'expenses'

    category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    expense_date = db.Column(db.Date, default=date.today, nullable=False)
    paid_to = db.Column(db.String(100), nullable=False)
    receipt_url = db.Column(db.String(255), nullable=True)

    category = db.relationship('ExpenseCategory', back_populates='expenses')
    branch = db.relationship('Branch', back_populates='expenses')

    def __repr__(self):
        return f"<Expense {self.title} - PKR {self.amount}>"

class PaymentMethod(BaseModel):
    __tablename__ = 'payment_methods'

    name = db.Column(db.String(50), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # cash, card, online, bank

    payments = db.relationship('Payment', back_populates='payment_method')

    def __repr__(self):
        return f"<PaymentMethod {self.name}>"

class Discount(BaseModel):
    __tablename__ = 'discounts'

    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    amount_type = db.Column(db.String(20), default='percentage', nullable=False)  # percentage, fixed
    value = db.Column(db.Numeric(12, 2), nullable=False)

    invoices = db.relationship('Invoice', back_populates='discount')

    def __repr__(self):
        return f"<Discount {self.code} ({self.value})>"

class Invoice(BaseModel):
    __tablename__ = 'invoices'

    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id', ondelete='CASCADE'), nullable=False)
    membership_id = db.Column(db.Integer, db.ForeignKey('memberships.id'), nullable=True)
    discount_id = db.Column(db.Integer, db.ForeignKey('discounts.id'), nullable=True)

    issue_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    due_date = db.Column(db.Date, nullable=False, index=True)
    subtotal = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    payment_status = db.Column(db.String(20), default='Unpaid', nullable=False, index=True)  # Paid, Partial, Unpaid, Overdue

    member = db.relationship('Member', back_populates='invoices')
    membership = db.relationship('Membership', back_populates='invoices')
    discount = db.relationship('Discount', back_populates='invoices')
    items = db.relationship('InvoiceItem', back_populates='invoice', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='invoice', cascade='all, delete-orphan')

    @property
    def paid_amount(self):
        total = Decimal('0.00')
        for p in self.payments:
            if not p.is_deleted and p.amount is not None:
                total += Decimal(str(p.amount))
        return total

    @property
    def balance_due(self):
        tot = Decimal(str(self.total_amount)) if self.total_amount is not None else Decimal('0.00')
        bal = tot - self.paid_amount
        return max(Decimal('0.00'), bal)

    @property
    def is_overdue(self):
        return self.payment_status != 'Paid' and self.due_date < date.today()

    def update_status(self):
        paid = self.paid_amount
        tot = Decimal(str(self.total_amount)) if self.total_amount is not None else Decimal('0.00')
        if tot > Decimal('0.00') and paid >= tot:
            self.payment_status = 'Paid'
        elif paid > Decimal('0.00'):
            self.payment_status = 'Partial'
        elif self.due_date < date.today():
            self.payment_status = 'Overdue'
        else:
            self.payment_status = 'Unpaid'

    def __repr__(self):
        return f"<Invoice {self.invoice_number} - {self.payment_status}>"

class InvoiceItem(BaseModel):
    __tablename__ = 'invoice_items'

    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)

    invoice = db.relationship('Invoice', back_populates='items')

class Payment(BaseModel):
    __tablename__ = 'payments'

    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'), nullable=False)
    payment_date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_reference = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.String(255), nullable=True)

    invoice = db.relationship('Invoice', back_populates='payments')
    payment_method = db.relationship('PaymentMethod', back_populates='payments')

    def __repr__(self):
        return f"<Payment PKR {self.amount} for Inv #{self.invoice_id}>"
