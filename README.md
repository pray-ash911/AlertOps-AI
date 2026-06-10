# AlertOps - AI Surveillance System

An intelligent surveillance system that uses computer vision and deep learning to detect security threats in real-time, including weapon detection and overcrowding alerts.

## Overview

AlertOps is a comprehensive AI-powered security monitoring platform that combines:
- **Weapon Detection**: Real-time identification of weapons in video feeds (Trained on 10k images dataset)
- **Overcrowding Detection**: Monitors designated areas for unsafe crowd densities
- **Event Management**: Centralized dashboard for reviewing and managing security alerts
- **Lift Monitoring**: Tracks lift/elevator usage patterns and occupancy

The system uses YOLOv8 deep learning models for object detection, Django REST Framework for API management, and Streamlit for interactive dashboards.

## Tech Stack

### Backend
- **Django** 4.x - Web framework and admin interface
- **Django REST Framework** - RESTful API development
- **PostgreSQL** - Database (psycopg2-binary)
- **PyTorch/Torchvision** - Deep learning framework (CUDA 12.1)
- **YOLOv8** (Ultralytics) - Object detection model
- **OpenCV** - Computer vision library
- **NumPy/Pandas** - Data processing

### Frontend & Dashboards
- **Streamlit** - Interactive analytics dashboards
- **Plotly** - Advanced visualization
- **Bootstrap/CSS** - Web interface styling

### Infrastructure
- **ngrok** - Public tunnel for local development
- **Python 3.8+** - Runtime environment

## Project Structure

```
AlertOps/
├── backend/                          # Django project root
│   ├── manage.py                     # Django management script
│   ├── core/                         # Django configuration
│   │   ├── settings.py               # Project settings
│   │   ├── urls.py                   # Main URL routing
│   │   ├── wsgi.py                   # WSGI application
│   │   └── asgi.py                   # ASGI application
│   ├── surveillance_app/             # Main application
│   │   ├── models.py                 # Data models (EventLog, Lift, etc.)
│   │   ├── views.py                  # API views and video processing
│   │   ├── serializers.py            # DRF serializers
│   │   ├── urls.py                   # App URL routing
│   │   ├── admin.py                  # Django admin configuration
│   │   ├── migrations/               # Database migrations
│   │   └── templates/                # HTML templates (auth, landing)
│   ├── snapshots/                    # Video processing storage
│   │   ├── lift_annotated/           # Annotated lift videos
│   │   └── lift_videos/              # Raw lift video frames
│   ├── static/                       # Static files
│   │   ├── css/                      # Stylesheets
│   │   └── images/                   # Image assets
│   └── tests/                        # Unit tests
├── dashboard/                        # Streamlit analytics dashboards
│   ├── dashboard.py                  # Main dashboard
│   └── pages/                        # Multi-page app
│       ├── analytics_dashboard.py    # Event analytics
│       └── lift_dashboard.py         # Lift usage analytics
├── models/                           # Pre-trained ML models
│   ├── best.pt                       # Weapon detection model (YOLOv8)
│   ├── best (1).pt                   # Alternative detection model
│   ├── yolov8m.pt                    # YOLOv8 medium model
│   └── yolov8n (1).pt                # YOLOv8 nano model
├── requirements.txt                  # Python dependencies
└── .venv/                            # Virtual environment

```

## Core Features

### Security Event Detection
- **Weapon Detection**: Identifies firearms and weapons in video feeds with confidence scores
- **Overcrowding Detection**: Monitors areas for excessive crowd density
- **Event Logging**: All security events are timestamped and logged with status tracking
- **Event Review**: Admin interface for reviewing and classifying alerts (Valid/False Alarm/Closed)

### Lift Monitoring
- **Occupancy Tracking**: Real-time monitoring of lift capacity
- **Usage Analytics**: Historical trends in lift usage patterns
- **Detection Models**: YOLOv8-based person detection for accurate occupancy counting
- **Video Analysis**: Frame-by-frame analysis and annotation of lift videos

### Event Management
- **Status Tracking**: Events can be marked as NEW, REVIEWED, FALSE ALARM, or CLOSED
- **Admin Review**: Staff can review and act on security alerts
- **Analytics**: Comprehensive dashboards for viewing event trends and statistics
- **User Management**: Role-based access control (staff, superuser, regular users)

### Data Models

#### EventLog
- Logs every security event (weapon or overcrowding incident)
- Stores event type, confidence values, timestamps
- Tracks review status and admin notes
- Links to surveillance areas and responsible staff

#### EventType
- Defines alert categories (WEAPON, OVERCROWDING)
- Customizable descriptions

#### SurveillanceArea
- Physical zones under monitoring
- Configurable overcrowding thresholds
- Activity status tracking

#### Lift
- Elevator/lift properties and capacity
- Warning threshold configuration

#### LiftDetection/LiftUsage
- Per-frame detection results from video analysis
- Usage statistics and patterns

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL (recommended) or SQLite
- 4GB+ GPU VRAM (for CUDA acceleration, optional but recommended)
- Windows/Linux/macOS

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AlertOps
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database**
   - Update `backend/core/settings.py` with your database credentials
   - Default: SQLite (no configuration needed for development)
   
   ```python
   # For PostgreSQL, update DATABASES in settings.py:
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'alertops_db',
           'USER': 'postgres',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

5. **Run migrations**
   ```bash
   cd backend
   python manage.py migrate
   ```

6. **Create superuser** (for admin access)
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files** (production)
   ```bash
   python manage.py collectstatic --noinput
   ```

## Running the Application

### 1. Start Django Backend Server
```bash
cd backend
python manage.py runserver
```
Server runs on: `http://localhost:8000`

### 2. Access Django Admin
```
http://localhost:8000/admin
```
Use your superuser credentials to manage events, areas, and users.

### 3. Start Streamlit Dashboards
```bash
streamlit run dashboard/dashboard.py
```
Dashboards available at: `http://localhost:8501`

### Optional: Public Access via ngrok
```bash
ngrok http 8000
```
Use the generated ngrok URL for public API access (already configured in `ALLOWED_HOSTS`).

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login and get token
- `POST /api/auth/logout/` - Logout

### Events
- `GET /api/events/` - List all security events
- `GET /api/events/<id>/` - Get event details
- `PATCH /api/events/<id>/` - Update event status/review
- `POST /api/events/` - Create new event
- `DELETE /api/events/<id>/` - Delete event

### Surveillance Areas
- `GET /api/areas/` - List monitored areas
- `POST /api/areas/` - Create new area
- `GET /api/areas/<id>/` - Get area details

### Event Types
- `GET /api/event-types/` - List event types
- `POST /api/event-types/` - Create event type

### Analytics
- `GET /api/events/statistics/` - Event statistics
- `GET /api/events/timeline/` - Event timeline data

### Video Processing
- `POST /api/process-video/` - Submit video for analysis
- `GET /api/video-status/<id>/` - Check processing status

## Dashboard Features

### Main Dashboard
- Real-time event feed with latest alerts
- Event type distribution (Weapon vs. Overcrowding)
- Geographic heat maps for areas with high alert activity
- Recent events table with status indicators

### Analytics Dashboard
- Event trends over time (daily, weekly, monthly)
- Staff performance metrics (events reviewed, resolution time)
- Event status breakdown (valid vs. false alarms)
- Top alert locations and areas
- Time-of-day incident patterns

### Lift Dashboard
- Current lift occupancy status
- Lift usage trends and patterns
- Peak usage times analysis
- Occupancy capacity alerts
- Historical usage analytics

## Model Information

### Weapon Detection Model
- **File**: `models/best (1).pt`
- **Architecture**: YOLOv8 (custom-trained)
- **Output**: Weapon bounding boxes with confidence scores
- **Threshold**: Configurable confidence threshold

### Overcrowding Detection Model
- **File**: `models/best.pt`
- **Architecture**: YOLOv8 (custom-trained for person detection)
- **Output**: Person bounding boxes and crowd density estimation
- **Threshold**: Configurable based on surveillance area

### Pre-trained Models (Optional)
- `models/yolov8m.pt` - YOLOv8 Medium (general purpose)
- `models/yolov8n (1).pt` - YOLOv8 Nano (lightweight)

## Configuration

### Key Settings (`backend/core/settings.py`)
```python
DEBUG = True                   # Set to False in production
ALLOWED_HOSTS = [...]          # Add your domain/IP
SECRET_KEY = '...'             # Change in production
INSTALLED_APPS = [...]         # Installed Django apps
```

### Environment Variables (Recommended)
Create `.env` file in project root:
```
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost/alertops_db
ALLOWED_HOSTS=example.com,www.example.com
```

## Testing

Run unit tests:
```bash
cd backend
python manage.py test surveillance_app.tests
```

## Troubleshooting

### Common Issues

**Issue**: Models not loading
- Ensure model files are in `models/` directory
- Check CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`

**Issue**: Database errors
- Run migrations: `python manage.py migrate`
- Check database connection in settings.py

**Issue**: Permission denied errors (Windows)
- Use PowerShell: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`
- Or use Command Prompt with admin privileges

**Issue**: ngrok tunnel not connecting
- Ensure ngrok is installed and authenticated
- Update ALLOWED_HOSTS with your ngrok URL

## Performance Optimization

- Use GPU acceleration (CUDA) for faster inference
- Batch process videos when possible
- Cache model inference results
- Implement video frame skipping for lower latency requirements

## Security Considerations

⚠️ **Development Only Settings**:
- `DEBUG = True` - Disable in production
- `SECRET_KEY` - Change to a secure random string
- `ALLOWED_HOSTS` - Restrict to your domain(s)
- CSRF protection enabled for all POST requests
- Implement proper authentication tokens for API access

## Future Enhancements

- Multi-camera support with distributed processing
- Real-time alerts via email/SMS/push notifications
- Advanced video analytics (object tracking, behavior analysis)
- Mobile app for monitoring on-the-go
- ML model retraining pipeline
- Integration with external security systems
- Geographic mapping with heat map visualization
- Archive and retention policies

## License

This project is proprietary. Unauthorized copying or modification is prohibited.


