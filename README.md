# NGO Operations Platform

A comprehensive platform for NGO operations management, designed to help field agents, donors, child care providers, and mission managers coordinate their efforts.

## Features

- **Field Agent Dashboard**: GPS tracking, resource logs, QR code scanning, messaging, and emergency alerts
- **Donor Dashboard**: Donation statistics, currency tracing, and interactive map
- **Child Care Dashboard**: Child profiles management, health status tracking, and priority cases
- **Mission Manager Dashboard**: Project management, resource allocation, and team oversight
- **Unified Map**: Visualize fund routes, resource distributions, child locations, and field agent positions
- **Messaging System**: Real-time communication between different stakeholders

## Technology Stack

- Flask (Python web framework)
- SQLite (Database)
- SQLAlchemy (ORM)
- Socket.IO (Real-time communication)
- Leaflet (Interactive maps)
- Bootstrap 5 (Responsive UI)
- Font Awesome (Icons)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Jwessel2020/BDIT.git
   cd BDIT
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   flask --app app.py initdb
   ```

5. Run the application:
   ```
   flask --app app.py run
   ```

6. Open your browser and navigate to `http://127.0.0.1:5000`

## Usage

- Login with one of the predefined user accounts:
  - Field Agent: username `agent1`, password `test123`
  - Donor: username `donor1`, password `test123`
  - Child Care Provider: username `care1`, password `test123`
  - Mission Manager: username `manager1`, password `test123`

## Development

This project uses Flask's built-in development server. For production deployment, consider using a production WSGI server like Gunicorn or uWSGI. 