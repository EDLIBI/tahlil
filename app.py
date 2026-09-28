from flask import Flask, request, render_template, redirect, session
import pickle
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix
import matplotlib.pyplot as plt
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

app.config['UPLOAD_FOLDER'] = 'uploads'

analysis_log = []

# تحميل النموذج
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

data = pd.read_csv("dataset.csv")
X = vectorizer.transform(data["text"])
y = data["label"]
y_pred = model.predict(X)

accuracy = accuracy_score(y, y_pred)
cm = confusion_matrix(y, y_pred)


# ====== دوال قاعدة البيانات ======

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_user(username):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def create_user(username, password, role="user"):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        (username, password, role),
    )
    conn.commit()
    conn.close()


def update_password(username, new_password):
    conn = get_db()
    conn.execute(
        "UPDATE users SET password = ? WHERE username = ?",
        (new_password, username),
    )
    conn.commit()
    conn.close()


def update_user(user_id, username, password, role):
    conn = get_db()
    conn.execute(
        "UPDATE users SET username = ?, password = ?, role = ? WHERE id = ?",
        (username, password, role, user_id),
    )
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return users


# ====== صلاحيات ======

def require_login():
    return session.get("logged_in")


def require_admin():
    return session.get("role") == "admin"


# ====== تسجيل الدخول ======

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = get_user(username)

        if user and user["password"] == password:
            session["logged_in"] = True
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect("/")
        else:
            error = "❌ اسم المستخدم أو كلمة المرور غير صحيحة"

    return render_template("login.html", error=error)


# ====== إنشاء حساب جديد ======

@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""
    success = ""

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = get_user(username)

        if user:
            error = "❌ اسم المستخدم موجود مسبقًا"
        else:
            create_user(username, password, role="user")
            success = "✔️ تم إنشاء الحساب بنجاح، يمكنك تسجيل الدخول الآن"

    return render_template("register.html", error=error, success=success)


# ====== تغيير كلمة المرور ======

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if not require_login():
        return redirect("/login")

    error = ""
    success = ""

    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]

        user = get_user(session["username"])

        if user["password"] != old_password:
            error = "❌ كلمة المرور القديمة غير صحيحة"
        else:
            update_password(session["username"], new_password)
            success = "✔️ تم تغيير كلمة المرور بنجاح"

    return render_template("change_password.html", error=error, success=success)


# ====== تسجيل الخروج ======

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ====== الصفحة الرئيسية ======

@app.route("/", methods=["GET", "POST"])
def home():
    if not require_login():
        return redirect("/login")

    result = ""
    if request.method == "POST":
        text = request.form["news"]
        vec = vectorizer.transform([text])
        pred = model.predict(vec)[0]

        result = "✔️ الخبر صحيح" if pred == 1 else "❌ الخبر كاذب"

        analysis_log.append({"text": text, "result": result})

    return render_template("index.html", result=result)


# ====== الإحصائيات ======

@app.route("/dashboard")
def dashboard():
    if not require_login():
        return redirect("/login")

    plt.figure(figsize=(4, 4))
    plt.imshow(cm, cmap="Blues")
    plt.title("Confusion Matrix")
    plt.colorbar()

    if not os.path.exists("static"):
        os.makedirs("static")

    plt.savefig("static/cm.png")
    plt.close()

    return render_template("dashboard.html", accuracy=accuracy)


# ====== سجل التحليلات ======

@app.route("/log")
def log_page():
    if not require_login():
        return redirect("/login")

    return render_template("log.html", log=analysis_log)


# ====== رفع CSV ======

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not require_login():
        return redirect("/login")

    results = []

    if request.method == "POST":
        file = request.files["file"]

        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)

        df = pd.read_csv(filepath)

        for text in df["text"]:
            vec = vectorizer.transform([text])
            pred = model.predict(vec)[0]
            result = "✔️ صحيح" if pred == 1 else "❌ كاذب"
            results.append({"text": text, "result": result})

    return render_template("upload.html", results=results)


# ====== إدارة المستخدمين (مدير فقط) ======

@app.route("/manage_users")
def manage_users():
    if not require_admin():
        return redirect("/")

    users = get_all_users()
    return render_template("manage_users.html", users=users)


@app.route("/delete_user/<int:user_id>")
def delete_user_route(user_id):
    if not require_admin():
        return redirect("/")

    delete_user(user_id)
    return redirect("/manage_users")


@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if not require_admin():
        return redirect("/")

    user = get_user_by_id(user_id)

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        update_user(user_id, username, password, role)
        return redirect("/manage_users")

    return render_template("edit_user.html", user=user)


if __name__ == "__main__":
    app.run(debug=True)
