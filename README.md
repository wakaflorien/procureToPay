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

This application consists of three main components:
- **Frontend**: React app (served via Nginx)
- **Backend**: Django REST API (Gunicorn)
- **Database**: PostgreSQL

### Deployment Options Comparison

| Option | Complexity | Cost | Best For |
|--------|-----------|------|----------|
| **Docker Compose (VPS)** | Low | $5-20/mo | Small teams, full control |
| **Railway/Render** | Very Low | $5-25/mo | Quick deployment, managed services |
| **AWS/GCP/Azure** | Medium-High | $20-100+/mo | Enterprise, scalability |
| **Kubernetes** | High | $50+/mo | Large scale, microservices |

---

### Option 1: Docker Compose on VPS (Recommended for Small-Medium Apps)

**Best for**: Full control, cost-effective, single server deployment

#### Prerequisites
- VPS (DigitalOcean, Linode, Hetzner, AWS EC2)
- Docker & Docker Compose installed
- Domain name (optional, for SSL)

#### Steps

1. **Create `.env` file** in project root:
```env
# Database
POSTGRES_DB=procuretopay
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-password-here

# Django
SECRET_KEY=your-django-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Optional: External database URL (if using managed PostgreSQL)
# DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

2. **Deploy**:
```bash
# Clone repository
git clone <repository-url>
cd procuretopay

# Build and start services
docker-compose -f docker-compose.prod.yml up -d --build

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Optional: Create sample users for testing
docker-compose -f docker-compose.prod.yml exec backend python manage.py create_sample_users
```

3. **SSL Setup** (using Let's Encrypt):
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (adjust domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

4. **Update Nginx config** for SSL (add to `frontend/nginx.conf`):
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # ... rest of config
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

5. **Monitoring & Maintenance**:
```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Update application
git pull
docker-compose -f docker-compose.prod.yml up -d --build
```

---

### Option 2: Railway / Render (Easiest - Managed Platform)

**Best for**: Quick deployment, zero DevOps overhead

#### Railway Deployment

1. **Connect GitHub** repository to Railway
2. **Add Services**:
   - **PostgreSQL**: Add from Railway's database template
   - **Backend**: Add service, set root directory to `/`, build command: `pip install -r requirements.txt`, start command: `gunicorn procuretopay.wsgi:application --bind 0.0.0.0:$PORT`
   - **Frontend**: Add service, set root directory to `/frontend`, build command: `npm install && npm run build`, start command: `npx serve -s dist -l $PORT`

3. **Environment Variables** (set in Railway dashboard):
   - `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL` (auto-provided by Railway)

#### Render Deployment

**📖 For detailed Render deployment instructions, see [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)**

**Quick Start:**
1. **Option 1 - Blueprint (Easiest)**: 
   - Push code to GitHub
   - Go to https://dashboard.render.com/new/blueprint
   - Connect repository (Render will auto-detect `render.yaml`)
   - Configure environment variables and deploy

2. **Option 2 - Manual Setup**:
   - Create PostgreSQL database
   - Deploy backend as Web Service
   - Deploy frontend as Static Site
   - See [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) for detailed steps

**Key Configuration:**
- **Backend Build**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Backend Start**: `gunicorn procuretopay.wsgi:application --bind 0.0.0.0:$PORT`
- **Frontend Build**: `cd frontend && npm install && npm run build`
- **Frontend Publish**: `frontend/dist`

---

### Option 3: AWS / GCP / Azure (Enterprise Scale)

**Best for**: High traffic, compliance requirements, enterprise features

#### AWS Architecture
- **Frontend**: S3 + CloudFront (CDN)
- **Backend**: ECS Fargate or EC2 with Auto Scaling
- **Database**: RDS PostgreSQL (Multi-AZ for HA)
- **Load Balancer**: Application Load Balancer
- **Storage**: S3 for media files

#### GCP Architecture
- **Frontend**: Cloud Storage + Cloud CDN
- **Backend**: Cloud Run or GKE
- **Database**: Cloud SQL PostgreSQL
- **Storage**: Cloud Storage for media

#### Azure Architecture
- **Frontend**: Azure Static Web Apps or Blob Storage + CDN
- **Backend**: Azure Container Instances or AKS
- **Database**: Azure Database for PostgreSQL
- **Storage**: Azure Blob Storage for media

---

### Option 4: Kubernetes (Large Scale)

**Best for**: Microservices, high availability, auto-scaling

#### Key Components:
- **Ingress**: Nginx Ingress Controller (SSL termination)
- **Backend**: Deployment with Horizontal Pod Autoscaler
- **Frontend**: Deployment or ConfigMap serving static files
- **Database**: Managed PostgreSQL (RDS, Cloud SQL) or StatefulSet
- **Secrets**: Kubernetes Secrets for sensitive data
- **ConfigMaps**: For non-sensitive configuration

#### Sample Kubernetes Manifests:
```yaml
# Example: Backend Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/backend:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

---

### Option 5: Traditional VPS (No Docker)

**Best for**: Maximum control, custom configurations

1. **Server Setup**:
```bash
sudo apt update
sudo apt install python3-pip python3-venv postgresql nginx nodejs npm
```

2. **Backend Setup**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic
```

3. **Run with Systemd** (`/etc/systemd/system/backend.service`):
```ini
[Unit]
Description=Gunicorn instance for ProcureToPay
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/procuretopay
Environment="PATH=/var/www/procuretopay/venv/bin"
ExecStart=/var/www/procuretopay/venv/bin/gunicorn procuretopay.wsgi:application --bind 127.0.0.1:8000 --workers 3

[Install]
WantedBy=multi-user.target
```

4. **Nginx Configuration** (`/etc/nginx/sites-available/procuretopay`):
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        root /var/www/procuretopay/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /media {
        alias /var/www/procuretopay/media;
    }

    location /static {
        alias /var/www/procuretopay/staticfiles;
    }
}
```

---

### Production Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY` (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up SSL/HTTPS (Let's Encrypt recommended)
- [ ] Use managed PostgreSQL or regular backups
- [ ] Configure media file storage (S3, Cloud Storage, or persistent volumes)
- [ ] Set up monitoring (Sentry, DataDog, or CloudWatch)
- [ ] Configure logging
- [ ] Set up CI/CD pipeline
- [ ] Enable database connection pooling
- [ ] Configure CORS properly for production domain
- [ ] Set up automated backups
- [ ] Configure rate limiting
- [ ] Review security headers (CSP, HSTS, etc.)

---

### Environment Variables Reference

```env
# Required
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Optional
POSTGRES_DB=procuretopay
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
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

