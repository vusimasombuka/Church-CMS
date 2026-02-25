from flask_login import current_user
from flask import abort, g
from app.extensions import db

def branch_query(model):
    """
    For routes with logged-in users.
    Returns query filtered by current user's branch unless super_admin.
    """
    if current_user.role == "super_admin":
        return model.query

    return model.query.filter_by(branch_id=current_user.branch_id)


def enforce_branch_access(obj):
    """
    Blocks access if object belongs to another branch.
    For routes with logged-in users only.
    """
    if current_user.role == "super_admin":
        return

    if hasattr(obj, "branch_id"):
        if obj.branch_id != current_user.branch_id:
            abort(403)


# ================= JOB-SPECIFIC FUNCTIONS (No current_user) =================

def get_query_for_branch(model, branch_id):
    """
    For background jobs. Explicitly filter by branch_id.
    Usage: get_query_for_branch(Member, 1).filter_by(phone=phone).first()
    """
    return model.query.filter_by(branch_id=branch_id)


def get_all_branches():
    """
    For background jobs. Get all branches to iterate through.
    Usage: for branch in get_all_branches():
    """
    from app.models.branch import Branch
    return Branch.query.all()


def branch_id_from_service(service_id):
    """
    Helper to get branch_id from a service record.
    Use this in check-in to ensure branch is derived from service selection.
    """
    from app.models.service import Service
    service = Service.query.get(service_id)
    if service:
        return service.branch_id
    return None