import sqlite3
from sqlite3 import Cursor, Connection


DB_PATH = "Test.db"


class DbWrapper:
    db_connection: Connection
    db: Cursor

    def __init__(self):
        self.db_connection = sqlite3.connect(DB_PATH)
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
