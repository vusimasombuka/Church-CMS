from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.decorators import role_required
from app.extensions import db
from app.models.sms_template import SMSTemplate
from app.models.lookup import Lookup  # make sure this import exists at top



sms_templates_bp = Blueprint(
    "sms_templates",
    __name__,
    url_prefix="/sms-templates"
)


# =========================
# LIST TEMPLATES
# =========================
from app.models.lookup import Lookup


@sms_templates_bp.route("/")
@login_required
@role_required("admin", "super_admin")
def list_templates():

    from sqlalchemy import func

    templates = SMSTemplate.query.order_by(SMSTemplate.id.desc()).all()

    # Count ACTIVE templates per message type
    template_counts_query = (
        db.session.query(
            SMSTemplate.message_type,
            func.count(SMSTemplate.id)
        )
        .filter(SMSTemplate.active == True)
        .group_by(SMSTemplate.message_type)
        .all()
    )

    template_counts = {t[0]: t[1] for t in template_counts_query}

    # Get ALL message types that exist in DB (active or inactive)
    all_types_query = (
        db.session.query(SMSTemplate.message_type)
        .distinct()
        .all()
    )

    all_message_types = [t[0] for t in all_types_query]

    # For dropdown
    offering_types = Lookup.query.filter_by(category="offering_type").all()
    sms_types = Lookup.query.filter_by(category="sms_type").all()
    message_types = offering_types + sms_types

    return render_template(
        "sms_templates.html",
        templates=templates,
        template_counts=template_counts,
        message_types=message_types,
        all_message_types=all_message_types
    )




# =========================
# ADD TEMPLATE
# =========================
@sms_templates_bp.route("/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_template():

    message_type = request.form.get("message_type").lower()
    message = request.form.get("message")

    if not message_type or not message:
        flash("Message type and message are required.", "error")
        return redirect(url_for("sms_templates.list_templates"))

    template = SMSTemplate(
        message_type=message_type,
        message=message,
        active=True
    )

    db.session.add(template)
    db.session.commit()

    flash("SMS template added.", "success")
    return redirect(url_for("sms_templates.list_templates"))


# =========================
# TOGGLE ACTIVE
# =========================
@sms_templates_bp.route("/toggle/<int:template_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def toggle_template(template_id):

    template = SMSTemplate.query.get_or_404(template_id)
    template.active = not template.active
    db.session.commit()

    return redirect(url_for("sms_templates.list_templates"))



# =========================
# DELETE TEMPLATE
# =========================
@sms_templates_bp.route("/delete/<int:template_id>", methods=["POST"])
@login_required
@role_required("admin", "super_admin")
def delete_template(template_id):

    template = SMSTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()

    flash("Template deleted successfully.", "success")
    return redirect(url_for("sms_templates.list_templates"))



@sms_templates_bp.route("/edit/<int:template_id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "super_admin")
def edit_template(template_id):

    template = SMSTemplate.query.get_or_404(template_id)

    if request.method == "POST":
        template.message = request.form.get("message")
        db.session.commit()
        flash("Template updated successfully.", "success")
        return redirect(url_for("sms_templates.list_templates"))

    return render_template(
        "sms_templates_edit.html",
        template=template
    )


from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.decorators import role_required
from app.extensions import db
from app.models.sms_template import SMSTemplate
from app.models.lookup import Lookup

sms_templates_bp = Blueprint(
    "sms_templates",
    __name__,
    url_prefix="/sms-templates"
)


# Variable documentation for reference
TEMPLATE_VARIABLES = {
    "General (All Templates)": {
        "{name}": "Person's first name (e.g., 'John')",
    },
    "Event Reminders": {
        "{event_title}": "Name of the event (e.g., 'Youth Conference')",
        "{event_date}": "Date of event (e.g., '25 December 2026')",
        "{days_until}": "Number of days until event (e.g., '90')",
    },
    "Giving/Offerings": {
        "{name}": "Giver's first name",
        "Note": "Template type must match offering_type exactly (e.g., 'tithe', 'offering')",
    },
    "Check-In": {
        "{name}": "Visitor or member's first name",
    },
    "Visitor Follow-up": {
        "{services}": "List of service times (e.g., 'Sunday: 9am, Wednesday: 6pm')",
    },
}


# Example templates users can copy
EXAMPLE_TEMPLATES = {
    "event_reminder_90": "Hi {name}! Save the date: {event_title} is happening on {event_date} (in {days_until} days). Don't miss it! - Living Waters",
    
    "event_reminder_60": "Hi {name}! Reminder: {event_title} is coming up on {event_date} ({days_until} days away). Get ready! - Living Waters",
    
    "event_reminder_30": "Hi {name}! {event_title} is just {days_until} days away ({event_date}). We can't wait to see you! - Living Waters",
    
    "event_reminder_7": "Hi {name}! {event_title} is next week ({event_date}). Final preparations underway. See you there! - Living Waters",
    
    "visitor_thank_you": "Hi {name}, thank you for visiting Living Waters! We hope to see you again soon. Join us Sundays at 9am.",
    
    "visitor_returning": "Welcome back {name}! Great to see you again at Living Waters.",
    
    "member_returning": "Welcome {name}! So glad you're with us today.",
    
    "birthday": "Happy Birthday {name}! May God bless you with many more years. From all of us at Living Waters!",
    
    "visitor_followup": "Hi {name}, we missed you! Join us this week: {services}. We'd love to see you!",
    
    "absentees_follow_up": "Hi {name}, we noticed you haven't been with us for a while. We miss you! Join us this Sunday.",
    
    "tithe": "Hi {name}, thank you for your tithe. May God bless your generosity! - Living Waters",
    
    "offering": "Hi {name}, thank you for your offering. God sees your heart! - Living Waters",
}


@sms_templates_bp.route("/")
@login_required
@role_required("admin", "super_admin")
def list_templates():
    from sqlalchemy import func

    templates = SMSTemplate.query.order_by(SMSTemplate.id.desc()).all()

    # Count ACTIVE templates per message type
    template_counts_query = (
        db.session.query(
            SMSTemplate.message_type,
            func.count(SMSTemplate.id)
        )
        .filter(SMSTemplate.active == True)
        .group_by(SMSTemplate.message_type)
        .all()
    )

    template_counts = {t[0]: t[1] for t in template_counts_query}

    # Get ALL message types that exist in DB
    all_types_query = (
        db.session.query(SMSTemplate.message_type)
        .distinct()
        .all()
    )

    all_message_types = [t[0] for t in all_types_query]

    # For dropdown
    offering_types = Lookup.query.filter_by(category="offering_type").all()
    sms_types = Lookup.query.filter_by(category="sms_type").all()
    message_types = offering_types + sms_types

    return render_template(
        "sms_templates.html",
        templates=templates,
        template_counts=template_counts,
        message_types=message_types,
        all_message_types=all_message_types,
        template_variables=TEMPLATE_VARIABLES,  # NEW: Pass variables
        example_templates=EXAMPLE_TEMPLATES,     # NEW: Pass examples
    )


@sms_templates_bp.route("/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_template():

    message_type = request.form.get("message_type").lower()
    message = request.form.get("message")

    if not message_type or not message:
        flash("Message type and message are required.", "error")
        return redirect(url_for("sms_templates.list_templates"))

    template = SMSTemplate(
        message_type=message_type,
        message=message,
        active=True
    )

    db.session.add(template)
    db.session.commit()

    flash("SMS template added.", "success")
    return redirect(url_for("sms_templates.list_templates"))


@sms_templates_bp.route("/toggle/<int:template_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def toggle_template(template_id):

    template = SMSTemplate.query.get_or_404(template_id)
    template.active = not template.active
    db.session.commit()

    return redirect(url_for("sms_templates.list_templates"))


@sms_templates_bp.route("/delete/<int:template_id>", methods=["POST"])
@login_required
@role_required("admin", "super_admin")
def delete_template(template_id):

    template = SMSTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()

    flash("Template deleted successfully.", "success")
    return redirect(url_for("sms_templates.list_templates"))


@sms_templates_bp.route("/edit/<int:template_id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "super_admin")
def edit_template(template_id):

    template = SMSTemplate.query.get_or_404(template_id)

    if request.method == "POST":
        template.message = request.form.get("message")
        db.session.commit()
        flash("Template updated successfully.", "success")
        return redirect(url_for("sms_templates.list_templates"))

    return render_template(
        "sms_templates_edit.html",
        template=template,
        template_variables=TEMPLATE_VARIABLES,
        example_templates=EXAMPLE_TEMPLATES
    )