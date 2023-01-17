from typing import Union
from flask import Flask, redirect, render_template, jsonify, session, request, flash, url_for
import sqlite3
from sqlite3 import Cursor, Connection
import os
from collections import namedtuple
from datetime import timedelta
from werkzeug.utils import secure_filename

ICON_DIR = "icons"

app = Flask(__name__, instance_relative_config=True,
            static_folder='./templates/icons')
app.config['TEMPLATES_AUTO_RELOAD'] = True
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['SECRET_KEY'] = "seacret"
app.config['UPLOAD_FOLDER'] = '/templates/icons'
app.permanent_session_lifetime = timedelta(minutes=3)


def get_db_connection():
    return sqlite3.connect("Test.db")


class DbWrapper:
    db_connection: Connection
    db: Cursor

    def __init__(self):
        self.db_connection = get_db_connection()
        self.db = self.db_connection.cursor()

    def __del__(self):
        self.db_connection.close()

    def execute(self, sql: str):
        print("execute:" + sql)
        if sql.startswith("SELECT"):
            self.db.execute(sql)
            return self.db.fetchall()
        if sql.startswith("INSERT") or sql.startswith("DELETE") or sql.startswith("UPDATE"):
            self.db.execute(sql)
            self.db_connection.commit()

    def get_review_list(self):
        reviews_raw = self.execute("SELECT * FROM reviews")
        reviews = []
        for review_raw in reviews_raw:
            review = {}
            review["review_id"] = review_raw[0]
            review["user_id"] = review_raw[1]
            review["class_id"] = review_raw[2]
            review["written_by"] = self.execute(
                f"SELECT name FROM users WHERE user_id={review['user_id']}")[0][0]
            comment = review_raw[3]
            if len(comment) > 6:
                comment = comment[0:6]
                comment += "..."
            review["short_description"] = comment
            review["description"] = review_raw[3]
            reviews.append(review)
        return reviews

    def get_review(self, review_id):
        review_raw = self.execute(
            f"SELECT * FROM reviews WHERE review_id={review_id}")[0]
        review = {}
        review["review_id"] = review_raw[0]
        class_info = self.execute(
            f"SELECT title,teacher FROM classes WHERE class_id={review_raw[2]}")[0]
        review["user_id"] = review_raw[1]
        review["class_title"] = class_info[0]
        review["class_teacher"] = class_info[1]
        review["written_by"] = self.execute(
            f"SELECT name FROM users WHERE user_id={review_raw[1]}")[0][0]
        review["comment"] = review_raw[3]
        return review


def login_required(func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/")
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
        "index.html", classes=classes, reviews=reviews, user_id=session['user_id'], is_signin=True
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
    if request.method == "GET":
        return render_template("review/edit.html", comment=current_review["comment"], review_id=review_id, is_signin=True)
    if session.get("user_id") != current_review["user_id"]:
        return jsonify({"message": "failed"})
    db.execute(
        f"UPDATE reviews SET comment='{request.form['comment']}' WHERE review_id={review_id}")
    return redirect("/")


@app.route("/review/delete/<int:review_id>", methods=['GET'])
@login_required
def delete_review(review_id):
    db = DbWrapper()
    target_data = db.get_review(review_id)
    if session['user_id'] != target_data["user_id"]:
        return jsonify(
            {'message': 'Deletion of reviews written by anyone other than you is not permitted'}), 400
    db.execute(f"DELETE FROM reviews WHERE review_id={review_id}")
    return redirect("/")


@app.route("/review/list")
@login_required
def list_reviews():
    db = DbWrapper()
    review_list = db.execute(
        f"SELECT * FROM review WHERE user_id = {session['user_id']}")
    return jsonify(review_list)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template("login.html", is_signin=False)
    db = DbWrapper()
    name = request.form.get("username")
    password = request.form.get("password")
    user_id = db.execute(
        f"SELECT user_id FROM users WHERE name = '{name}' AND password_hash = '{password}'")[0]
    if (user_id is None):
        return jsonify("Login failed")
    else:
        session['user_id'] = user_id[0]
        return redirect("/")


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if request.method == 'GET':
        return render_template("sign_up.html")
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
    db = DbWrapper()
    if request.method == "GET":
        user = db.execute(
            f"SELECT * from users WHERE user_id={session['user_id']}")[0]
        icon_path = user[3]
        if icon_path == None:
            icon_path = ICON_DIR + "/default_icon.jpg"
        return render_template("profile.html", username=user[1], password=user[2], icon_path=icon_path, is_signin=True)
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('download_file', name=filename))
    return redirect("/profile", is_login=True)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
