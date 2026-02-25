from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.decorators import role_required
from app.extensions import db
from app.models.visitor import Visitor
from app.models.check_in import CheckIn
from app.models.giving import Giving
from app.models.member import Member
from app.utils.branching import branch_query, enforce_branch_access

visitors_bp = Blueprint("visitors", __name__, url_prefix="/visitors")

# ================= VISITORS LIST =================
@visitors_bp.route("/")
@login_required
@role_required("super_admin", "admin", "usher")
def visitors_list():

    from app.utils.branching import branch_query
    from app.models.check_in import CheckIn

    page = request.args.get("page", 1, type=int)

    base_query = branch_query(Visitor)

    query = (
        base_query
        .outerjoin(CheckIn, CheckIn.visitor_id == Visitor.id)
        .group_by(Visitor.id)
        .order_by(db.func.max(CheckIn.check_in_date).desc())
    )

    visitors = query.paginate(page=page, per_page=25)

    return render_template("visitors.html", visitors=visitors)



# ================= CONVERT VISITOR TO MEMBER =================
@visitors_bp.route("/convert/<int:visitor_id>", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def convert_to_member(visitor_id):

    visitor = Visitor.query.get_or_404(visitor_id)
    enforce_branch_access(visitor)

    # 🔒 Branch-aware duplicate check
    existing_member = branch_query(Member).filter_by(
        phone=visitor.phone
    ).first()

    if existing_member:
        flash(
            f"A member with this phone number already exists: "
            f"{existing_member.first_name} {existing_member.last_name}. "
            f"Cannot convert - would create duplicate.",
            "error"
        )
        return redirect(url_for("visitors.visitors_list"))

    # ================= CREATE MEMBER =================
    member = Member(
        first_name=visitor.first_name,
        last_name=visitor.last_name,
        phone=visitor.phone,
        email=None,
        branch_id=visitor.branch_id
    )

    db.session.add(member)
    db.session.flush()

    # 🔒 Relink Giving (branch isolated)
    branch_query(Giving).filter_by(visitor_id=visitor.id).update({
        Giving.member_id: member.id,
        Giving.visitor_id: None
    })

    # 🔒 Relink CheckIns (branch isolated)
    branch_query(CheckIn).filter_by(visitor_id=visitor.id).update({
        CheckIn.member_id: member.id,
        CheckIn.visitor_id: None
    })

    db.session.delete(visitor)
    db.session.commit()

    flash("Visitor successfully converted to member.", "success")
    return redirect(url_for("visitors.visitors_list"))
