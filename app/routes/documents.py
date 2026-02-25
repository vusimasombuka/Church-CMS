import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, abort, current_app
import os
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.document import Document
from app.decorators import role_required
from flask_login import current_user
from app.models.document_category import DocumentCategory


documents_bp = Blueprint("documents", __name__, url_prefix="/documents")

UPLOAD_FOLDER = os.path.join("instance", "uploads")



# LIST + SEARCH
@documents_bp.route("/", methods=["GET", "POST"])
@login_required
def documents_list():

    from app.utils.branching import branch_query, enforce_branch_access

    # CREATE CATEGORY
    if request.method == "POST" and "new_category" in request.form:
        name = request.form.get("new_category").strip()

        if name:
            category = DocumentCategory(
                name=name,
                branch_id=current_user.branch_id
            )
            db.session.add(category)
            db.session.commit()

        return redirect(url_for("documents.documents_list"))

    search = request.args.get("search")
    selected_category = request.args.get("category", type=int)

    # Categories
    if current_user.role == "super_admin":
        categories = DocumentCategory.query.order_by(DocumentCategory.name).all()
    else:
        categories = DocumentCategory.query.filter_by(
            branch_id=current_user.branch_id
        ).order_by(DocumentCategory.name).all()

    # Documents
    query = branch_query(Document)

    if selected_category:
        query = query.filter_by(category_id=selected_category)

    if search:
        query = query.filter(Document.name.ilike(f"%{search}%"))

    documents = query.order_by(Document.created_at.desc()).all()

    return render_template(
        "documents.html",
        documents=documents,
        categories=categories,
        selected_category=selected_category,
        search=search
    )



# UPLOAD (ADMIN ONLY)
@documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
@role_required("super_admin", "admin")
def upload_document():

    from app.utils.branching import enforce_branch_access

    if request.method == "POST":

        file = request.files.get("file")
        name = request.form.get("name")
        category_id = request.form.get("category_id", type=int)

        if not file or not name or not category_id:
            return "Missing required fields", 400

        category = DocumentCategory.query.get_or_404(category_id)
        enforce_branch_access(category)

        filename = secure_filename(file.filename)

        upload_folder = os.path.join(current_app.instance_path, "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        file.save(os.path.join(upload_folder, filename))

        doc = Document(
            name=name,
            filename=filename,
            uploaded_by=current_user.username,
            branch_id=category.branch_id,
            category_id=category.id
        )

        db.session.add(doc)
        db.session.commit()

        return redirect(url_for("documents.documents_list"))

    # CATEGORY LIST
    if current_user.role == "super_admin":
        categories = DocumentCategory.query.order_by(DocumentCategory.name).all()
    else:
        categories = DocumentCategory.query.filter_by(
            branch_id=current_user.branch_id
        ).order_by(DocumentCategory.name).all()

    return render_template(
        "upload_document.html",
        categories=categories
    )




# PREVIEW (VIEW IN BROWSER)
@documents_bp.route("/preview/<filename>")
@login_required
def preview_document(filename):
    upload_folder = os.path.join(current_app.instance_path, "uploads")

    if not os.path.exists(os.path.join(upload_folder, filename)):
        abort(404)

    # Opens in browser
    return send_from_directory(upload_folder, filename)


from flask import send_from_directory
import os


# ✅ DOWNLOAD DOCUMENT
@documents_bp.route("/download/<int:doc_id>")
@login_required
def download_document(doc_id):

    from app.utils.branching import enforce_branch_access

    doc = Document.query.get_or_404(doc_id)
    enforce_branch_access(doc)

    upload_folder = os.path.join(current_app.instance_path, "uploads")

    return send_from_directory(
        upload_folder,
        doc.filename,
        as_attachment=True
    )




# ✅ DELETE DOCUMENT
@documents_bp.route("/delete/<int:doc_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def delete_document(doc_id):

    from app.utils.branching import enforce_branch_access

    doc = Document.query.get_or_404(doc_id)
    enforce_branch_access(doc)

    upload_folder = os.path.join(current_app.instance_path, "uploads")
    file_path = os.path.join(upload_folder, doc.filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(doc)
    db.session.commit()

    return redirect(url_for("documents.documents_list"))

# ✅ DELETE CATEGORY
@documents_bp.route("/delete-category/<int:category_id>", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def delete_category(category_id):

    from app.utils.branching import enforce_branch_access

    category = DocumentCategory.query.get_or_404(category_id)
    enforce_branch_access(category)

    if category.documents:
        flash("Cannot delete category with documents inside.", "error")
        return redirect(url_for("documents.documents_list"))

    db.session.delete(category)
    db.session.commit()

    flash("Category deleted.", "success")
    return redirect(url_for("documents.documents_list"))


# ✅ ADD CATEGORY
@documents_bp.route("/category/add", methods=["POST"])
@login_required
@role_required("super_admin", "admin")
def add_category():

    name = request.form.get("name")

    if not name:
        return redirect(url_for("documents.documents_list"))

    category = DocumentCategory(
        name=name.strip(),
        branch_id=current_user.branch_id
    )

    db.session.add(category)
    db.session.commit()

    return redirect(url_for("documents.documents_list"))
