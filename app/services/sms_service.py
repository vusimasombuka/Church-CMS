import requests
from flask import current_app
from app.extensions import db
from app.models.sms_log import SMSLog


def send_sms(phone, message):
    """
    Sends an SMS via Clickatell
    """

    url = "https://platform.clickatell.com/messages/http/send"

    headers = {
        "Authorization": current_app.config["CLICKATELL_API_KEY"],
        "Content-Type": "application/json",
    }

    payload = {
        "to": [phone],
        "content": message,
        "from": current_app.config.get("CLICKATELL_SENDER_ID"),
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()

    return response.json()


def log_sms(
    phone,
    message,
    message_type,
    branch_id,
    related_table=None,
    related_id=None,
    status="pending",
    error=None
):

    sms = SMSLog(
        phone=phone,
        message=message,
        message_type=message_type,
        related_table=related_table,
        related_id=related_id,
        status=status,
        error=error,
        branch_id=branch_id
    )

    db.session.add(sms)
    db.session.commit()

    return sms

def send_and_log_sms(
    phone,
    message,
    message_type,
    branch_id,
    related_table=None,
    related_id=None
):
    """
    Safely logs + sends SMS and updates status.
    """

    sms = SMSLog(
        phone=phone,
        message=message,
        message_type=message_type,
        related_table=related_table,
        related_id=related_id,
        status="pending",
        branch_id=branch_id
    )

    db.session.add(sms)
    db.session.commit()

    try:
        send_sms(phone, message)
        sms.status = "sent"
        sms.error = None
    except Exception as e:
        sms.status = "failed"
        sms.error = str(e)

    db.session.commit()
    return sms
