import sqlite3


def main():
    con = sqlite3.connect('test.db')
    con.execute("DROP TABLE IF EXISTS USERS")
    con.execute("DROP TABLE IF EXISTS REVIEWS")
    con.execute("DROP TABLE IF EXISTS CLASSES")
    con.execute("CREATE TABLE USERS(\
        user_id INTEGER PRIMARY KEY AUTOINCREMENT, \
        username TEXT NOT NULL, \
        password TEXT NOT NULL) \
        ")
    con.execute("CREATE TABLE REVIEWS(\
        review_id INTEGER PRIMARY KEY AUTOINCREMENT, \
        class_id INTEGER NOT NULL, \
        user_id INTEGER NOT NULL, \
        comment TEXT NOT NULL, \
        ")
    con.execute("CREATE TABLE CLASSES(\
        class_id INTEGER PRIMARY KEY AUTOINCREMENT, \
        title TEXT NOT NULL, \
        description TEXT NOT NULL, \
        ")
    print('データベースを初期化しました')


if __name__ == '__main__':
    main()
