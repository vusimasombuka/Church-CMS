from datetime import date, timedelta
from app.extensions import db
from app.models.sms_log import SMSLog
from app.models.service import Service
from app.models.check_in import CheckIn
from app.models.sms_template import SMSTemplate
from app.services.sms_rotation_service import get_rotated_template


def visitor_followup_job():
    """
    Sends one follow-up SMS per visitor per week using SMS Templates
    """

    today = date.today()

    # Only run on Mondays
    if today.weekday() != 0:
        return

    # =========================
    # TEMPLATE ROTATION CHECK
    # =========================
    active_templates_count = SMSTemplate.query.filter_by(
        message_type="visitor_followup",
        active=True
    ).count()

    if active_templates_count < 3:
        print(
            f'Rotation Warning: "visitor_followup" has only '
            f'{active_templates_count} active template(s). '
            f'Minimum 3 required for proper rotation.'
        )

    # =========================
    # GET SERVICES
    # =========================
    services = Service.query.filter_by(active=True).all()
    if not services:
        return

    services_text = "; ".join(
        f"{s.name}: {s.day_of_week} {s.time}" for s in services
    )

    # =========================
    # FIND RECENT VISITORS
    # =========================
    recent_checkins = CheckIn.query.filter(
        CheckIn.visitor_id.isnot(None),
        CheckIn.phone.isnot(None),
        CheckIn.created_at >= today - timedelta(days=7)
    ).all()

    for checkin in recent_checkins:

        # Prevent duplicate weekly SMS
        already_sent = SMSLog.query.filter(
            SMSLog.phone == checkin.phone,
            SMSLog.message_type == "visitor_followup",
            SMSLog.created_at >= today - timedelta(days=7)
        ).first()

        if already_sent:
            continue

        # =========================
        # TEMPLATE ROTATION
        # =========================
        template = get_rotated_template(checkin.phone, "visitor_followup")
        if not template:
            continue

        message = template.message.replace("{services}", services_text)

        sms = SMSLog(
            phone=checkin.phone,
            message=message,
            message_type="visitor_followup",
            related_table="check_in",
            related_id=checkin.id,
            status="pending",
            branch_id=getattr(checkin, "branch_id", 1),
            template_id=template.id
        )

        db.session.add(sms)

    db.session.commit()