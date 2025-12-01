# Procure-to-Pay System

A Django + React application for managing purchase requests with multi-level approval workflow, document processing, and receipt validation.

## Features

- **Multi-level Approval Workflow**: Sequential approval process with role-based access
- **Document Processing**: Automatic proforma invoice extraction, PO generation, and receipt validation
- **Email Notifications**: Automated emails on approval/rejection
- **RESTful API**: Complete API with JWT authentication
- **Modern Frontend**: React-based UI with responsive design
- **Docker Support**: Full containerization with docker-compose

## Tech Stack

**Backend**: Django 5.2.8, Django REST Framework, JWT Authentication, PostgreSQL  
**Frontend**: React 18, TypeScript, Vite, Tailwind CSS  
**Deployment**: Docker, Docker Compose, Render (or any cloud platform)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone and setup backend:**
```bash
git clone https://github.com/wakaflorien/procureToPay.git
cd procuretopay

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate
python manage.py createsuperuser
python manage.py create_sample_users  # Optional: creates test users

# Run server
python manage.py runserver
```

2. **Setup frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/
- API Docs: http://localhost:8000/swagger/

### Docker Setup

```bash
# Build and start all services
docker compose up --build

# Create superuser
docker compose exec backend python manage.py createsuperuser

# Access the application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

## Deployment

### Render (Recommended)

1. **Push code to GitHub**
2. **Go to**: https://dashboard.render.com/new/blueprint
3. **Connect repository** (auto-detects `render.yaml`)
4. **Set environment variables**:
   - `ALLOWED_HOSTS`: Your backend URL
   - `CORS_ALLOWED_ORIGINS`: Your frontend URL
   - `VITE_API_URL`: Your backend API URL (for frontend)
5. **Deploy** and run migrations:
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

### Docker Compose (VPS)

1. **Create `.env` file:**
```env
POSTGRES_DB=procuretopay
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

2. **Deploy:**
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Login (get JWT tokens)
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/refresh/` - Refresh access token
- `GET /api/auth/profile/` - Get current user profile

### Purchase Requests
- `GET /api/requests/` - List requests (filtered by role)
- `POST /api/requests/` - Create request (Staff only)
- `GET /api/requests/{id}/` - Get request details
- `PUT /api/requests/{id}/` - Update request (Staff, if pending)
- `POST /api/requests/{id}/approve/` - Approve request (Approvers)
- `POST /api/requests/{id}/reject/` - Reject request (Approvers)
- `POST /api/requests/{id}/submit_proforma/` - Upload proforma invoice
- `POST /api/requests/{id}/submit_receipt/` - Upload receipt

## User Roles

- **Staff**: Create and manage own requests, upload documents 
- **Approver Level 1**: Review and approve/reject requests 
- **Approver Level 2**: Review and approve/reject requests 
- **Finance**: View all requests and financial data 

## Approval Workflow

1. Staff creates request → **PENDING**
2. Approver Level 1 reviews → Approves/Rejects
   - Approved → Level 1 approved
   - Rejected → **REJECTED** (final)
3. Approver Level 2 reviews (if Level 1 approved) → Approves/Rejects
   - Approved → **APPROVED**, PO generated automatically
   - Rejected → **REJECTED** (final)
4. Staff uploads receipt → Validated against PO

## Email Notifications

Email notifications are sent automatically on approval/rejection. Configure SMTP settings:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.ethereal.email  # or your SMTP provider
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-password
```

**For testing with Ethereal Email:**
```bash
python manage.py setup_ethereal_email --user YOUR_USERNAME --pass YOUR_PASSWORD --save-to-env
```

## Environment Variables

```env
# Required
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-password

# Frontend
VITE_API_URL=https://your-backend-url.com/api
```

## Project Structure

```
procuretopay/
├── api/                    # Django app
│   ├── models.py          # Data models
│   ├── views.py           # API views
│   ├── serializers.py     # DRF serializers
│   ├── notifications.py   # Email notifications
│   └── management/        # Management commands
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   └── services/      # API services
├── procuretopay/          # Django settings
├── docker-compose.yml     # Docker development
├── render.yaml            # Render deployment config
└── requirements.txt
```

## Additional Features

- **Pagination**: API endpoints paginated (20 items per page)
- **GitHub Actions**: Automated Docker builds (see `.github/workflows/`)
- **Email Templates**: HTML email templates for notifications

## Testing

```bash
# Backend tests
python manage.py test

# Frontend tests
cd frontend && npm test
```

## License

MIT
