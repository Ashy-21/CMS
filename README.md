# 🎓 College Management System (CMS)

A complete **College Management System** built with **Django**, featuring multi-role access for **Admin (HOD)**, **Staff**, and **Students**.  
This system allows colleges to manage **students, staff, attendance, leave, results**, and more — all from a single web interface.

---

## 🚀 Features

### 👨‍💼 Admin / HOD
- Manage students, staff, courses, and departments  
- Approve or reject leave requests  
- View and manage attendance and results  
- Create new colleges and assign admins

### 👩‍🏫 Staff
- Mark attendance for students  
- Apply for leave  
- Upload results and grades  

### 🎓 Students
- View attendance history and grades  
- Apply for leave  
- Submit feedback  

### 🌐 General
- College selector and creation flow  
- Secure login system with CSRF protection  
- Responsive Bootstrap 5 UI  
- Role-based dashboard and access control  
- SQLite (default) with easy switch to PostgreSQL/MySQL

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-------------|
| **Frontend** | HTML, CSS, Bootstrap 5 |
| **Backend** | Django 5.x |
| **Database** | SQLite (default), PostgreSQL optional |
| **Language** | Python 3.12+ |
| **Template Engine** | Django Templates |
| **Authentication** | Django Auth System (Custom User Model) |

---

## ⚙️ Installation Guide

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/college-management-system.git
cd college-management-system
