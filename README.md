# UG Wi-Fi Support — Full Starter System

This package contains:
- Flask backend with SQLite
- Student authentication
- Admin authentication/authorization
- Password hashing
- JWT authentication
- Ticket creation and status updates
- Router/signal management
- Android Kotlin/Jetpack Compose client
- Student dashboard, tickets, reporting and signal screen

## Backend
1. Create a Python virtual environment.
2. Install: `pip install -r requirements.txt`
3. Run: `python app.py`
4. The API listens on `0.0.0.0:5000`.

Default demo accounts are created automatically:
- Student ID: `UG0001`
- Student password: `student123`
- Admin ID: `admin`
- Admin password: `admin123`

Change these immediately for real deployment.

## Android
Open `android` in Android Studio.
The emulator uses `http://10.0.2.2:5000/`.
For a physical phone, change `BASE_URL` in `MainActivity.kt` to your computer's LAN IP.

## Important
This is a project/demo baseline. For production, use HTTPS, a strong JWT secret stored outside source control, a production database, rate limiting, secure deployment, and proper admin account provisioning.
