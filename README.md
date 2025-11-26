# Procure-to-Pay System

A comprehensive Django + React application for managing purchase requests with multi-level approval workflow, document processing, and receipt validation.

## Features

- **User Roles**: Staff, Approver Level 1, Approver Level 2, Finance
- **Purchase Request Management**: Create, view, update purchase requests
- **Multi-level Approval Workflow**: Sequential approval process with tracking
- **Document Processing**: 
  - Proforma invoice extraction
  - Automatic Purchase Order generation
  - Receipt validation against PO
- **RESTful API**: Complete API with JWT authentication
- **Modern Frontend**: React-based UI with role-based access
- **Docker Support**: Full containerization with docker-compose

## Tech Stack

### Backend
- Django 5.2.8
- Django REST Framework
- JWT Authentication
- PostgreSQL (production) / SQLite (development)
- Document processing: pdfplumber, PyPDF2, pytesseract

### Frontend
- React 18
- React Router
- Axios for API calls
- Modern CSS with responsive design

### Deployment
- Docker & Docker Compose
- Gunicorn (production server)
- Nginx (frontend serving)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (optional, recommended)
- PostgreSQL (for production, SQLite used in development)

### Local Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd procuretopay
```

2. **Backend Setup**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Make migrations 
python manage.py makemigrations 

# Run migrations
python manage.py migrate

# Show migrations
python manage.py showmigrations

# Create superuser (required for admin access)
python manage.py createsuperuser

# Create sample users (recommended for multiple testing users and used when building Docker images)
python manage.py create_sample_users

# Run development server
python manage.py runserver
```

3. **Frontend Setup**
```bash
cd frontend
npm install
npm start
```

The application will be available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/swagger/

### Docker Setup

1. **Build and run with Docker Compose**
```bash
docker compose up --build
```

This will start:
- PostgreSQL database
- Django backend (port 8000)
- React frontend (port 3000)

2. **Create superuser and sample users**
```bash
# Sample users for all roles are created automatically on container startup
# via `python manage.py create_sample_users` in the backend container command.
# You only need to create a Django superuser for admin access:
docker compose exec backend python manage.py createsuperuser
```

3. **Access the application**
- Frontend: http://localhost:3000/login/
- Backend API: http://localhost:8000/api/
- Swagger Docs: http://localhost:8000/swagger/

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login (get JWT tokens)
- `POST /api/auth/refresh/` - Refresh access token
- `GET /api/auth/profile/` - Get current user profile

### Purchase Requests
- `GET /api/requests/` - List all requests (filtered by role)
- `POST /api/requests/` - Create new request (Staff only)
- `GET /api/requests/{id}/` - Get request details
- `PUT /api/requests/{id}/` - Update request (Staff, if pending)
- `POST /api/requests/{id}/approve/` - Approve request (Approvers)
- `POST /api/requests/{id}/reject/` - Reject request (Approvers)
- `POST /api/requests/{id}/submit_proforma/` - Upload proforma (Staff)
- `POST /api/requests/{id}/submit_receipt/` - Upload receipt (Staff)

## User Roles & Permissions

### Staff
- Create purchase requests
- View own requests
- Update pending requests
- Upload proforma invoices
- Upload receipts for approved requests

### Approver Level 1
- View pending requests
- Approve/reject requests (first level)
- View approval history

### Approver Level 2
- View pending requests (after Level 1 approval)
- Approve/reject requests (second level)
- View approval history

### Finance
- View all requests
- Access all request details
- View financial data

## Approval Workflow

1. **Staff creates request** → Status: PENDING
2. **Approver Level 1 reviews** → Approves/Rejects
   - If approved → Level 1 approved
   - If rejected → Status: REJECTED (final)
3. **Approver Level 2 reviews** (if Level 1 approved) → Approves/Rejects
   - If approved → Status: APPROVED, PO generated automatically
   - If rejected → Status: REJECTED (final)
4. **Staff uploads receipt** → Validated against PO

## Document Processing

### Proforma Processing
- Upload PDF/image proforma
- Automatic extraction of:
  - Vendor information
  - Total amount
  - Items and quantities
  - Payment terms

### Purchase Order Generation
- Automatically generated on final approval
- Contains:
  - PO number
  - Vendor details
  - Items and pricing
  - Approval history

### Receipt Validation
- Upload receipt after purchase
- Automatic validation against PO:
  - Vendor match
  - Amount match
  - Item count verification
- Returns validation results with errors/warnings

## Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

## Testing

```bash
# Run backend tests
python manage.py test

# Run frontend tests
cd frontend
npm test
```

## Deployment

### Production Deployment (AWS EC2 / VPS)

1. **Server Setup**
```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv postgresql nginx
```

2. **Clone and Setup**
```bash
git clone <repository-url>
cd procuretopay
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
# Set production environment variables
export SECRET_KEY=your-production-secret-key
export DEBUG=False
export ALLOWED_HOSTS=your-domain.com
export DATABASE_URL=postgresql://...
```

4. **Database Setup**
```bash
python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
```

5. **Run with Gunicorn**
```bash
gunicorn procuretopay.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

6. **Configure Nginx** (for frontend and reverse proxy)

### Docker Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Run production containers
docker-compose -f docker-compose.prod.yml up -d

# Sample users for all roles are created automatically on container startup
# via `python manage.py create_sample_users` in the backend image CMD.
# You only need to create a Django superuser for admin access:
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

## Project Structure

```
procuretopay/
├── api/                    # Django app
│   ├── models.py          # Data models
│   ├── views.py           # API views
│   ├── serializers.py     # DRF serializers
│   ├── permissions.py     # Custom permissions
│   ├── document_processor.py  # Document processing logic
│   └── urls.py            # API URLs
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API services
│   │   └── context/       # React context
│   └── public/
├── procuretopay/          # Django project settings
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

## Notes

- The system uses JWT tokens for authentication
- File uploads are stored in the `media/` directory
- Static files are collected to `staticfiles/` for production
- Document processing uses regex and PDF parsing (can be enhanced with AI/LLM)
- The system handles concurrent requests safely with database transactions

