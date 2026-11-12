import os
import csv
import io
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from flask import Response, stream_with_context, current_app, flash
from werkzeug.utils import secure_filename
from app.extensions import db

def today_pk():
    """Return the current date in Asia/Karachi (PKT, UTC+5) timezone."""
    try:
        return datetime.now(ZoneInfo("Asia/Karachi")).date()
    except Exception:
        return datetime.now(timezone(timedelta(hours=5))).date()

def to_localtime(dt, fmt="%d %b %Y, %I:%M %p"):
    """Convert UTC datetime to Asia/Karachi (PKT, UTC+5) timezone formatted string."""
    if not dt:
        return ""
    if not isinstance(dt, datetime):
        return str(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        pk_tz = ZoneInfo("Asia/Karachi")
    except Exception:
        pk_tz = timezone(timedelta(hours=5))
    local_dt = dt.astimezone(pk_tz)
    if fmt:
        return local_dt.strftime(fmt)
    return local_dt

def is_safe_url(target):
    """Ensure a target redirect URL is internal and safe against open redirects."""
    if not target or not isinstance(target, str):
        return False
    # Must start with a single '/' and reject '//evil.com' or '/\evil.com'
    if not target.startswith('/') or target.startswith('//') or target.startswith('/\\'):
        return False
    parsed = urlparse(target)
    return parsed.netloc == '' and parsed.scheme == ''

def commit_or_flash(success_msg=None, error_msg="An unexpected error occurred. Please try again."):
    """
    Attempt to commit the current SQLAlchemy session.
    If successful and success_msg is provided, flashes success_msg with 'success' category and returns True.
    If an exception occurs, rolls back the session, logs the exception with current_app.logger.exception,
    flashes error_msg with 'danger' category and returns False.
    """
    try:
        db.session.commit()
        if success_msg:
            flash(success_msg, "success")
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Database commit failed: %s", e)
        flash(error_msg, "danger")
        return False

def sanitize_csv_cell(cell):
    """Sanitize a cell against CSV injection (CWE-1236)."""
    if cell is None:
        return ""
    val = str(cell)
    if val and val[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{val}"
    return val

def sanitize_csv_row(row):
    return [sanitize_csv_cell(c) for c in row]

def stream_csv_response(row_generator, headers, filename="export.csv"):
    """Generate a streamed CSV HTTP response using a generator with CSV formula injection mitigation."""
    clean_filename = secure_filename(filename) or "export.csv"
    if not clean_filename.endswith(".csv"):
        clean_filename += ".csv"

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(sanitize_csv_row(headers))
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in row_generator():
            writer.writerow(sanitize_csv_row(row))
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )

def export_to_csv(rows, headers, filename="export.csv"):
    """Generate a CSV HTTP response with CSV formula injection mitigation."""
    clean_filename = secure_filename(filename) or "export.csv"
    if not clean_filename.endswith(".csv"):
        clean_filename += ".csv"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(sanitize_csv_row(headers))
    for row in rows:
        writer.writerow(sanitize_csv_row(row))
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def validate_file_content(file_storage, ext):
    """Validate uploaded file content using magic bytes and Pillow if available."""
    header = file_storage.read(16)
    file_storage.seek(0)
    if ext == 'pdf':
        if not header.startswith(b'%PDF-'):
            raise ValueError("Invalid PDF file: invalid or corrupted file header.")
    elif ext in ('jpg', 'jpeg'):
        if not header.startswith(b'\xff\xd8\xff'):
            raise ValueError("Invalid JPEG file: invalid file signature.")
    elif ext == 'png':
        if not header.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError("Invalid PNG file: invalid file signature.")
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

    if ext in ('jpg', 'jpeg', 'png'):
        try:
            from PIL import Image
            img = Image.open(file_storage)
            img.verify()
            file_storage.seek(0)
        except Exception:
            file_storage.seek(0)
            raise ValueError("Corrupted image file.")

def save_uploaded_file(file_storage, subfolder=''):
    """Save an uploaded file safely after verifying extension and magic bytes."""
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("File type not permitted. Allowed: PNG, JPG, JPEG, PDF")

    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    validate_file_content(file_storage, ext)

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, unique_name)
    file_storage.save(file_path)
    return os.path.join(subfolder, unique_name).replace('\\', '/')

def generate_membership_number(session=None):
    """Generate collision-safe sequence membership number: MEM-YYYYMM-XXXXX."""
    from app.models.member import Member
    now = datetime.now(timezone.utc)
    ym = now.strftime("%Y%m")
    prefix = f"MEM-{ym}-"
    s = session or db.session
    # Count existing in this month to get sequential base
    count = s.query(Member).filter(Member.membership_number.like(f"{prefix}%")).count()
    seq = count + 1
    # Add 4 hex characters to guarantee collision safety even in concurrent environments
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{prefix}{seq:04d}-{suffix}"

def generate_invoice_number(session=None):
    """Generate collision-safe sequence invoice number: INV-YYYYMM-XXXXX."""
    from app.models.finance import Invoice
    now = datetime.now(timezone.utc)
    ym = now.strftime("%Y%m")
    prefix = f"INV-{ym}-"
    s = session or db.session
    count = s.query(Invoice).filter(Invoice.invoice_number.like(f"{prefix}%")).count()
    seq = count + 1
    suffix = uuid.uuid4().hex[:4].upper()
    return f"{prefix}{seq:04d}-{suffix}"
