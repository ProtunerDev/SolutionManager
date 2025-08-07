# SolutionManager

A professional web application for automotive ECU solution management, built with Flask and powered by AWS S3 storage.

## 🚀 Features

- **ECU Solution Management**: Upload, compare, and manage automotive ECU files
- **Binary File Comparison**: Advanced binary file analysis and difference detection
- **AWS S3 Integration**: Secure cloud storage for all files
- **User Authentication**: Supabase-powered authentication with role-based access
- **Admin Dashboard**: User management and solution administration
- **Responsive Design**: Modern Bootstrap-based UI
- **PostgreSQL Database**: Robust data storage and retrieval

## 🛠️ Technology Stack

- **Backend**: Flask 2.3.3, Python 3.12+
- **Database**: PostgreSQL with psycopg2
- **Authentication**: Supabase Auth
- **Storage**: AWS S3
- **Frontend**: Bootstrap 5, JavaScript
- **Forms**: Flask-WTF with CSRF protection

## 📋 Prerequisites

- Python 3.12 or higher
- PostgreSQL database
- AWS S3 account and bucket
- Supabase project

## ⚙️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ProtunerDev/SolutionManager.git
   cd SolutionManager
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   
   Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```
   
   Update the following variables in `.env`:
   ```env
   # Flask
   SECRET_KEY=your_secret_key_here
   APP_URL=http://localhost:5000
   
   # Database
   DB_HOST=localhost
   DB_NAME=SolutionManager
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_PORT=5432
   
   # Storage
   STORAGE_TYPE=s3
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_S3_BUCKET=your_bucket_name
   AWS_S3_REGION=us-east-1
   
   # Supabase
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   ```

5. **Database Setup**
   
   Create PostgreSQL database and run the schema:
   ```bash
   psql -U postgres -d SolutionManager -f app/database/schema.sql
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

   The application will be available at `http://localhost:5000`

## 🗂️ Project Structure

```
SolutionManager/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── auth/                 # Authentication module
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── routes.py
│   │   └── supabase_client.py
│   ├── main/                 # Main application routes
│   │   ├── forms.py
│   │   └── routes.py
│   ├── database/             # Database management
│   │   ├── db_manager.py
│   │   └── schema.sql
│   ├── utils/                # Utility modules
│   │   ├── binary_handler.py
│   │   ├── file_storage.py
│   │   ├── s3_storage.py
│   │   └── storage_factory.py
│   ├── static/               # Static assets
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/            # Jinja2 templates
│       ├── auth/
│       └── main/
├── tests/                    # Test suite
├── config.py                 # Application configuration
├── requirements.txt          # Python dependencies
├── run.py                   # Application entry point
└── README.md                # Project documentation
```

## 🔧 Configuration

### Storage Configuration

The application supports both local and S3 storage. Set `STORAGE_TYPE` in your environment:

- `local`: Files stored locally (development only)
- `s3`: Files stored in AWS S3 (recommended for production)

### User Roles

Configure admin users in Supabase by adding to user metadata:
```json
{
  "role": "admin"
}
```

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**: Ensure all production environment variables are set
2. **Database**: Use a production PostgreSQL instance
3. **Storage**: Configure AWS S3 with proper IAM permissions
4. **Security**: Update `SECRET_KEY` and enable HTTPS
5. **WSGI Server**: Use Gunicorn or similar for production deployment

### Docker Support (Optional)

A Dockerfile can be added for containerized deployment.

## 📝 API Documentation

The application provides RESTful endpoints for:

- `/api/dropdown/<field>`: Dynamic dropdown population
- `/auth/*`: Authentication endpoints
- `/delete_solution_from_home`: Solution deletion (admin only)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please open an issue on GitHub or contact the development team.

## 🔄 Version History

- **v1.0.0** - Initial release with core functionality
- ECU file management and comparison
- AWS S3 integration
- Supabase authentication
- Admin dashboard

---

**ProtunerDev** - Professional Automotive Software Solutions
