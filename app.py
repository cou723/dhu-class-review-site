from flask import Flask, redirect, render_template, jsonify, session, request, flash, url_for
import os
from collections import namedtuple
from datetime import timedelta
from db import DbWrapper
import hashlib

ICON_DIR = "icons"
DEFAULT_ICON_PATH = "default_icon.jpg"

app = Flask(__name__, instance_relative_config=True,
            static_folder='./templates/icons')
app.config['TEMPLATES_AUTO_RELOAD'] = True
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['SECRET_KEY'] = "seacret"
app.config['UPLOAD_FOLDER'] = 'templates/icons/'
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024
app.permanent_session_lifetime = timedelta(minutes=3)


def login_required(func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/", methods=["GET"])
@login_required
def home():
    db = DbWrapper()
    classes_raw = db.execute("SELECT * FROM classes")
    ClassTuple = namedtuple("ClassTuple", ["class_id", "title", "teacher"])
    classes = []
    for class_raw in classes_raw:
        classes.append(ClassTuple._make(class_raw)._asdict())
    reviews = db.get_review_list()
    return render_template(
        "index.html", classes=classes, reviews=reviews, user_id=session['user_id'], is_signin=True, error_message=request.args.get("error_message")
    )


@app.route("/review/<int:review_id>")
def get_review_page(review_id):
    db = DbWrapper()
    review = db.get_review(review_id)
    return render_template("review/description.html", review=review, is_signin=True, error_message=request.args.get("error_message"))


@app.route("/review/post", methods=['GET', 'POST'])
@login_required
def post_review():
    db = DbWrapper()
    # GET
    if request.method == 'GET':
        classes = db.execute("SELECT * FROM classes")
        return render_template("review/post.html", classes=classes, is_signin=True, error_message=request.args.get("error_message"))
    # POST
    review_count = db.execute("SELECT count(*) FROM reviews")[0][0]
    comment = request.form['comment'].strip()
    if ('"' in comment or "'" in comment):
        return jsonify({'message': '" or \' are not aviable'}), 400
    db.execute(
        f"INSERT INTO reviews VALUES({review_count}, {session['user_id']}, {request.form['class_id'].strip()}, '{comment}')")
    return redirect("/")


@app.route("/review/edit/<int:review_id>", methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    db = DbWrapper()
    current_review = db.get_review(review_id)
    # GET
    if request.method == "GET":
        return render_template("review/edit.html", comment=current_review["comment"], review_id=review_id, is_signin=True, error_message=request.args.get("error_message"))
    # POST
    if session.get("user_id") != current_review["user_id"]:
        return jsonify({"message": "Editing other people's reviews is not permitted"})
    comment = request.form['comment'].strip()
    if ('"' in comment or "'" in comment):
        return jsonify({'message': '" or \' are not aviable'}), 400
    db.execute(
        f"UPDATE reviews SET comment='{comment}' WHERE review_id={review_id}")
    return redirect("/")


@app.route("/review/delete/<int:review_id>", methods=['GET'])
@login_required
def delete_review(review_id):
    db = DbWrapper()
    target_data = db.get_review(review_id)
    if session['user_id'] != target_data["user_id"]:
        return jsonify({"message": "Deletion of other people's reviews is not permitted"})
    db.execute(f"DELETE FROM reviews WHERE review_id={review_id}")
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    # GET
    if request.method == 'GET':
        return render_template("login.html", is_signin=False, error_message=request.args.get("error_message"))
    # POST
    db = DbWrapper()
    name = request.form.get("username").strip()
    password_hash = hashlib.sha256(
        request.form.get("password").encode()).hexdigest()
    user_id = db.execute(
        f"SELECT user_id FROM users WHERE name='{name}' AND password_hash='{password_hash}'")
    if (not user_id):
        return redirect("/login?error_message=ユーザー名またはパスワードが違います")
    session['user_id'] = user_id[0][0]
    return redirect("/")


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    # GET
    if request.method == 'GET':
        return render_template("sign_up.html", error_message=request.args.get("error_message"))
    # POST
    db = DbWrapper()
    name = request.form.get("username").strip()
    already_used_name_list = db.execute(
        f"SELECT name FROM users WHERE name='{name}'")
    print(already_used_name_list)
    if len(already_used_name_list):
        return render_template("sign_up.html", error_message="その名前はもう使われています")
    password_hash = hashlib.sha256(
        request.form.get("password").encode()).hexdigest()
    user_count = db.execute("SELECT count(*) FROM users")[0][0]
    db.execute(
        f"INSERT INTO users VALUES({user_count}, '{name}', '{password_hash}', '{DEFAULT_ICON_PATH}')")
    return redirect("/login")


@app.route("/logout")
@login_required
def logout():
    session.pop('user_id', None)
    return redirect("/login")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = DbWrapper()
    # GET
    if request.method == "GET":
        user = db.execute(
            f"SELECT * from users WHERE user_id={session['user_id']}")[0]
        icon_path = user[3]
        if icon_path == None:
            icon_path = "default_icon.jpg"
        return render_template("profile.html", username=user[1], password=user[2], icon_path=icon_path, is_signin=True, error_message=request.args.get("error_message"))
    # POST
    if 'icon' in request.files and request.files['icon'].filename != '':
        if not allowed_file(request.files['icon'].filename):
            return jsonify({'message': 'Icon file must be jpeg, jpg, png.'}), 400
        file = request.files['icon']
        filename = str(session["user_id"]) + ".jpg"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.execute(
            f"UPDATE users SET img_path='{str(session['user_id'])}.jpg' WHERE user_id={session['user_id']}")
    if "username" in request.form:
        db.execute(
            f"UPDATE users SET name='{request.form['username'].strip()}' WHERE user_id={session['user_id']}")
    return redirect("/")


@app.route("/profile/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    db = DbWrapper()
    # GET
    if request.method == "GET":
        return render_template("change_password.html", error_message=request.args.get("error_message"))
    # POST
    password_hash = db.execute(
        f"SELECT password_hash FROM users WHERE user_id={session['user_id']}")[0][0]
    if hashlib.sha256(request.form["old_password"].encode()).hexdigest() != password_hash:
        return redirect("/profile/change_password?error_message=パスワードが違います")
    if request.form["new_password"] != request.form["new_password_confirmation"]:
        return jsonify({'message': 'The new password confirmation new password entered does not match.'}), 400
    db.execute(
        f"UPDATE users SET password_hash='{hashlib.sha256(request.form['new_password'].encode()).hexdigest()}' WHERE user_id={session['user_id']}")
    return redirect("/profile")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
