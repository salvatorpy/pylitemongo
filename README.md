# pylitemongo

English | فارسی

---

## English

### 📌 Overview

**pylitemongo** is a lightweight, MongoDB-like document store built on top of SQLite. It offers a familiar API for managing JSON-like documents without requiring a separate database server. Ideal for small-scale applications, rapid prototyping, or embedded use cases.

---

### ✨ Features

* MongoDB-style operations (`insert`, `find`, `update`, `delete`)
* Powered by **SQLite** (no external dependencies)
* Fast and minimal footprint
* Written entirely in Python
* Seamless integration with existing Python projects

---

### 📦 Installation

```bash
pip install pylitemongo
```

---

### 🚀 Quick Start

```python
from pylitemongo import Database

db = Database("mydata.db")
users = db["users"]

users.insert({"name": "Alice", "age": 25})
users.insert({"name": "Bob", "age": 30})

for user in users.find({"age": 25}):
    print(user)

users.update({"name": "Alice"}, {"$set": {"age": 26}})
users.delete({"name": "Bob"})
```

---

### 📚 Documentation

* **Database**: SQLite-backed document store
* **Collection**: MongoDB-like methods (`insert`, `find`, `update`, `delete`)
* Supports basic query operators: `$eq`, `$gt`, `$lt`, `$set`

---

### 🛠 Requirements

* Python 3.6+
* SQLite (included with Python)

---

### 🧪 Testing

```bash
git clone https://github.com/yourusername/pylitemongo.git
cd pylitemongo
pip install -r requirements-dev.txt
pytest
```

---

### 🤝 Contributing

We welcome contributions!

* Fork the repo
* Create a branch (`git checkout -b feature-name`)
* Commit your changes (`git commit -m "Add feature"`)
* Push the branch (`git push origin feature-name`)
* Open a Pull Request

---

### 📜 License

MIT License

---

## فارسی

### 📌 معرفی

**pylitemongo** یک کتابخانه سبک برای ذخیره‌سازی داده‌ها به صورت سندمحور است که بر پایه **SQLite** ساخته شده. این ابزار برای پروژه‌های کوچک، نمونه‌سازی سریع یا استفاده در برنامه‌هایی که نیاز به پایگاه‌داده سنگین ندارند، مناسب است.

---

### ✨ ویژگی‌ها

* عملیات مشابه MongoDB (`insert`، `find`، `update`، `delete`)
* استفاده از **SQLite** به عنوان پایگاه‌داده داخلی
* سبک، سریع و بدون وابستگی خارجی
* پیاده‌سازی کامل با پایتون
* قابل استفاده در پروژه‌های پایتونی موجود

---

### 📦 نصب

```bash
pip install pylitemongo
```

---

### 🚀 شروع سریع

```python
from pylitemongo import Database

db = Database("mydata.db")
users = db["users"]

users.insert({"name": "Ali", "age": 25})
users.insert({"name": "Sara", "age": 30})

for user in users.find({"age": 25}):
    print(user)

users.update({"name": "Ali"}, {"$set": {"age": 26}})
users.delete({"name": "Sara"})
```

---

### 📚 مستندات

* **Database**: مدیریت پایگاه‌داده SQLite
* **Collection**: متدهای مشابه MongoDB (`insert`، `find`، `update`، `delete`)
* پشتیبانی از عملگرهای ساده مانند `$eq`، `$gt`، `$lt`، `$set`

---

### 🛠 پیش‌نیازها

* پایتون 3.6 یا بالاتر
* SQLite (به صورت پیش‌فرض همراه پایتون)

---

### 🧪 تست

```bash
git clone https://github.com/yourusername/pylitemongo.git
cd pylitemongo
pip install -r requirements-dev.txt
pytest
```

---

### 🤝 مشارکت

خوشحال می‌شویم اگر مشارکت کنید!

* ریپازیتوری را Fork کنید
* یک Branch جدید بسازید (`git checkout -b feature-name`)
* تغییرات خود را Commit کنید (`git commit -m "افزودن ویژگی جدید"`)
* Branch را Push کنید (`git push origin feature-name`)
* یک Pull Request باز کنید

---

### 📜 مجوز

این پروژه تحت مجوز MIT منتشر شده است.
