from flask import Flask, redirect, render_template, jsonify, session, request
import sqlite3
import os
from collections import namedtuple
from datetime import timedelta

app = Flask(__name__, instance_relative_config=True)

app.config['SECRET_KEY'] = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=3)


def login_required(func):
    def wrapper(*args, **kwargs):
        print(session.get("user_id"))
        if "user_id" not in session:
            return redirect("/login")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def get_db_connection():
    return sqlite3.connect("Test.db")


def get_review_list(db):
    db.execute("SELECT * FROM reviews")
    reviews = []
    reviews_raw = db.fetchall()
    for review_raw in reviews_raw:
        review = {}
        review["review_id"] = review_raw[0]
        review["user_id"] = review_raw[1]
        review["class_id"] = review_raw[2]
        db.execute(f"SELECT name FROM users WHERE user_id={review['user_id']}")
        review["written_by"] = db.fetchone()[0]
        comment = review_raw[3]
        if len(comment) > 6:
            comment = comment[0:6]
            comment += "..."
        review["short_description"] = comment
        review["description"] = review_raw[3]
        reviews.append(review)
    return reviews


def get_review(db, review_id):
    db.execute(f"SELECT * FROM reviews WHERE review_id={review_id}")
    review_raw = db.fetchone()
    review = {}
    review["review_id"] = review_raw[0]
    db.execute(
        f"SELECT title,teacher FROM classes WHERE class_id={review_raw[2]}")
    class_info = db.fetchone()
    review["class_title"] = class_info[0]
    review["class_teacher"] = class_info[1]
    db.execute(f"SELECT name FROM users WHERE user_id={review_raw[1]}")
    review["written_by"] = db.fetchone()[0]
    review["comment"] = review_raw[3]
    return review


@app.route("/")
@login_required
def home():
    db_connection = get_db_connection()
    db = db_connection.cursor()
    db.execute("SELECT * FROM classes")
    classes_raw = db.fetchall()
    ClassTuple = namedtuple("ClassTuple", ["class_id", "title", "teacher"])
    classes = []
    for class_raw in classes_raw:
        classes.append(ClassTuple._make(class_raw)._asdict())
    reviews = get_review_list(db)
    return render_template(
        "index.html",
        classes=classes,
        reviews=reviews,
        user_id=session['user_id'])


@app.route("/review/<int:review_id>")
def get_review_page(review_id):
    db_connection = get_db_connection()
    db = db_connection.cursor()
    review = get_review(db, review_id)
    return render_template("review_description.html", review=review)


@app.route("/review/post", methods=['GET', 'POST'])
@login_required
def post_review():
    db_connection = get_db_connection()
    db = db_connection.cursor()
    if request.method == 'GET':
        db.execute("SELECT * FROM classes")
        classes = db.fetchall()
        return render_template("review_post.html", classes=classes)
    db.execute("SELECT count(*) FROM reviews")
    review_count = db.fetchone()[0]
    db.execute(
        f"INSERT INTO reviews VALUES({review_count}, {session['user_id']}, {request.form['class_id']}, '{request.form['comment']}')")
    db_connection.commit()
    db_connection.close()
    return jsonify("Post review")


@app.route("/review/delete/<int:review_id>", methods=['POST'])
@login_required
def delete_review(review_id):
    db_connection = get_db_connection()
    db = db_connection.cursor()
    target_data = get_review(db, review_id)
    if session["user_id"] != target_data["user_id"]:
        return jsonify(
            {'message': 'Deletion of reviews written by anyone other than you is not permitted'}), 400
    db.execute(f"DELETE FROM reviews WHERE review_id={review_id}")
    db_connection.commit()
    db_connection.close()


@app.route("/review/list")
@login_required
def list_reviews():
    db_connection = get_db_connection()
    db = db_connection.cursor()
    db.execute(f"SELECT * FROM review WHERE user_id = {session['user_id']}")
    review_list = db.fetchall()
    db_connection.close()
    return jsonify(review_list)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        db_connection = get_db_connection()
        db = db_connection.cursor()
        name = request.form.get("username")
        password = request.form.get("password")
        db.execute(
            f"SELECT user_id FROM users WHERE name = '{name}' AND password_hash = '{password}'")
        user_id = db.fetchone()
        db_connection.close()
        if (user_id is None):
            return jsonify("Login failed")
        else:
            session["user_id"] = user_id[0]
            return redirect("/")
    else:
        return render_template("login.html")


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if request.method == 'GET':
        return render_template("sign_up.html")
    db_connection = get_db_connection()
    db = db_connection.cursor()
    name = request.form.get("username")
    password = request.form.get("password")
    db.execute("SELECT count(*) FROM users")
    user_count = db.fetchone()
    db.execute(
        f"INSERT INTO users VALUES({user_count[0]}, '{name}', '{password}')")
    db_connection.commit()
    db_connection.close()
    return redirect("/login")


@app.route("/logout")
@login_required
def logout():
    session.pop('user_id', None)
    return redirect("/login")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
