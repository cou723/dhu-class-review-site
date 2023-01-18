from flask import Flask, redirect, render_template, jsonify, session, request, flash, url_for
import os
from collections import namedtuple
from datetime import timedelta
from werkzeug.utils import secure_filename
from db import DbWrapper

ICON_DIR = "icons"

app = Flask(__name__, instance_relative_config=True,
            static_folder='./templates/icons')
app.config['TEMPLATES_AUTO_RELOAD'] = True
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['SECRET_KEY'] = "seacret"
app.config['UPLOAD_FOLDER'] = '/templates/icons'
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
    return render_template("review/description.html", review=review, is_signin=True)


@app.route("/review/post", methods=['GET', 'POST'])
@login_required
def post_review():
    db = DbWrapper()
    if request.method == 'GET':
        classes = db.execute("SELECT * FROM classes")
        return render_template("review/post.html", classes=classes, is_signin=True)
    review_count = db.execute("SELECT count(*) FROM reviews")[0][0]
    db.execute(
        f"INSERT INTO reviews VALUES({review_count}, {session['user_id']}, {request.form['class_id']}, '{request.form['comment']}')")
    return redirect("/")


@app.route("/review/edit/<int:review_id>", methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    db = DbWrapper()
    current_review = db.get_review(review_id)
    # GET
    if request.method == "GET":
        return render_template("review/edit.html", comment=current_review["comment"], review_id=review_id, is_signin=True)
    # POST
    if session.get("user_id") != current_review["user_id"]:
        return redirect(url_for("/", error_message="他人のレビューは編集できません"))
    db.execute(
        f"UPDATE reviews SET comment='{request.form['comment']}' WHERE review_id={review_id}")
    return redirect("/")


@app.route("/review/delete/<int:review_id>", methods=['GET'])
@login_required
def delete_review(review_id):
    db = DbWrapper()
    target_data = db.get_review(review_id)
    if session['user_id'] != target_data["user_id"]:
        return redirect(url_for("/", error_message="他人のレビューは削除できません"), code=307)
    db.execute(f"DELETE FROM reviews WHERE review_id={review_id}")
    return redirect("/")


# @app.route("/review/my_list")
# @login_required
# def list_reviews():
#     db = DbWrapper()
#     review_list = db.execute(
#         f"SELECT * FROM review WHERE user_id = {session['user_id']}")
#     return jsonify(review_list)


@app.route("/login", methods=["GET", "POST"])
def login():
    # GET
    if request.method == 'GET':
        return render_template("login.html", is_signin=False, error_message=request.args.get("error_message"))
    # POST
    db = DbWrapper()
    name = request.form.get("username")
    password = request.form.get("password")
    user_id = db.execute(
        f"SELECT user_id FROM users WHERE name = '{name}' AND password_hash = '{password}'")
    if (not user_id):
        return jsonify("Login failed")
    session['user_id'] = user_id[0][0]
    return redirect("/")


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    # GET
    if request.method == 'GET':
        return render_template("sign_up.html")
    # POST
    db = DbWrapper()
    name = request.form.get("username")
    password = request.form.get("password")
    user_count = db.execute("SELECT count(*) FROM users")
    db.execute(
        f"INSERT INTO users VALUES({user_count[0]}, '{name}', '{password}')")
    return redirect("/login", is_login=False)


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
    # GET
    db = DbWrapper()
    if request.method == "GET":
        user = db.execute(
            f"SELECT * from users WHERE user_id={session['user_id']}")[0]
        icon_path = user[3]
        if icon_path == None:
            icon_path = ICON_DIR + "/default_icon.jpg"
        return render_template("profile.html", username=user[1], password=user[2], icon_path=icon_path, is_signin=True, error_message=request.args.get("error_message"))
    # POST
    if 'file' in request.files and request.files['file'].filename == '':
        file = request.files['file']
        flash('No selected file')
        if file and allowed_file(file.filename):
            filename = session["user_id"]
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if "username" in request.form:
        db.execute(
            f"UPDATE users SET name='{request.form['username']}' WHERE user_id={session['user_id']}")
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
    print(request.form["old_password"], password_hash)
    if request.form["old_password"] != password_hash:
        return redirect("/profile/change_password?error_message=パスワードが違います")
    if request.form["new_password"] != request.form["new_password_confirmation"]:
        return redirect("/profile/change_password?error_message=確認用のパスワードと新しいパスワードが一致しません")
    db.execute(
        f"UPDATE users SET password_hash='{request.form['new_password']}' WHERE user_id={session['user_id']}")
    return redirect("/profile")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
