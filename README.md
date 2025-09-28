# pylitemongo

[English](#english) | [فارسی](#فارسی)

---

## English

### 📌 Overview
**pylitemongo** is a lightweight, MongoDB-like document store built on top of SQLite.  
It provides a simple API for storing, querying, and managing JSON-like documents without the need for a separate database server.  
Perfect for small projects, prototyping, or embedding into applications where MongoDB would be too heavy.

---

### ✨ Features
- MongoDB-like API with familiar operations (`insert`, `find`, `update`, `delete`)
- Uses **SQLite** as the backend (no external dependencies)
- Lightweight and fast
- Pure Python implementation
- Easy to integrate into existing projects

---

### 📦 Installation
```bash
pip install pylitemongo
```
🚀 Quick Start
```python
from pylitemongo import Database

# Create or connect to a database
db = Database("mydata.db")

# Create a collection
users = db["users"]

# Insert documents
users.insert({"name": "Alice", "age": 25})
users.insert({"name": "Bob", "age": 30})

# Query documents
for user in users.find({"age": 25}):
    print(user)

# Update documents
users.update({"name": "Alice"}, {"$set": {"age": 26}})

# Delete documents
users.delete({"name": "Bob"})

📚 Documentation

Database: Represents a SQLite-backed database.

Collection: Provides MongoDB-like methods (insert, find, update, delete).

Queries support simple operators like $eq, $gt, $lt, $set.

🛠 Requirements

Python 3.6+

SQLite (built-in with Python)

🧪 Testing

Clone the repository and run tests with pytest:

git clone https://github.com/yourusername/pylitemongo.git
cd pylitemongo
pip install -r requirements-dev.txt
pytest

🤝 Contributing

Contributions are welcome!

Fork the repository

Create a new branch (git checkout -b feature-name)

Commit your changes (git commit -m "Add feature")

Push to the branch (git push origin feature-name)

Open a Pull Request

📜 License

This project is licensed under the MIT License.

فارسی

📌 معرفی

pylitemongo یک کتابخانه سبک و ساده است که امکان ذخیره و مدیریت داده‌ها را به صورت سندمحور (Document-Oriented) شبیه MongoDB فراهم می‌کند، اما بر پایه SQLite ساخته شده است.این ابزار برای پروژه‌های کوچک، نمونه‌سازی سریع (Prototyping) یا زمانی که استفاده از MongoDB سنگین است، بسیار مناسب می‌باشد.

✨ ویژگی‌ها

رابط کاربری شبیه MongoDB با متدهای آشنا (insert، find، update، delete)

استفاده از SQLite به عنوان پایگاه داده داخلی (بدون نیاز به نصب جداگانه)

سبک و سریع

پیاده‌سازی کامل با پایتون

قابل استفاده در پروژه‌های موجود

📦 نصب

pip install pylitemongo

🚀 شروع سریع

from pylitemongo import Database

# ایجاد یا اتصال به دیتابیس
db = Database("mydata.db")

# ایجاد کالکشن
users = db["users"]

# درج داده
users.insert({"name": "Ali", "age": 25})
users.insert({"name": "Sara", "age": 30})

# جستجو
for user in users.find({"age": 25}):
    print(user)

# بروزرسانی
users.update({"name": "Ali"}, {"$set": {"age": 26}})

# حذف
users.delete({"name": "Sara"})

📚 مستندات

Database: مدیریت دیتابیس SQLite

Collection: متدهای شبیه MongoDB (insert، find، update، delete)

پشتیبانی از عملگرهای ساده مانند $eq، $gt، $lt، $set

🛠 پیش‌نیازها

پایتون 3.6 یا بالاتر

SQLite (به صورت پیش‌فرض همراه پایتون نصب است)

🧪 تست

برای اجرای تست‌ها:

git clone https://github.com/yourusername/pylitemongo.git
cd pylitemongo
pip install -r requirements-dev.txt
pytest

🤝 مشارکت

مشارکت شما ارزشمند است!

ریپازیتوری را Fork کنید

یک Branch جدید بسازید (git checkout -b feature-name)

تغییرات خود را Commit کنید (git commit -m "افزودن ویژگی جدید")

Branch را Push کنید (git push origin feature-name)

یک Pull Request باز کنید

📜 مجوز

این پروژه تحت مجوز MIT منتشر شده است.

