# Social Media Platform with AI-Powered Content Tagging

A modern, real-time social media platform built with FastAPI and React. Features AI-powered automatic content tagging, real-time messaging, and interactive social features.

## Features

### Core Functionality
- **User Authentication**: Secure JWT-based login/registration system
- **Posts & Content**: Share text, images, and media content
- **Social Interactions**: Like posts, leave comments, follow users
- **Stories**: Share temporary content with friends
- **Real-time Notifications**: Live notification system for user activities

### AI Integration
- **Smart Tagging**: Automatic topic detection and tagging using OpenAI GPT
- **Content Analysis**: Intelligent categorization of post content

### Real-time Features
- **WebSocket Communication**: Live messaging and notifications
- **Push Notifications**: Browser-based push notifications
- **Live Chat**: Real-time messaging between users

### User Interface
- **Responsive Design**: Mobile and desktop compatible
- **Modern UI**: Clean, intuitive user interface
- **Accessibility**: WCAG compliant design

## Tech Stack

### Backend
- **Python 3.8+**
- **FastAPI**: High-performance REST API framework
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migration management
- **WebSocket**: Real-time communication
- **OpenAI API**: AI-powered content tagging

### Frontend
- **React 19.2.4**: Modern JavaScript framework
- **TypeScript 5.9.3**: Type-safe development
- **Vite**: Fast build tool and development server
- **Zustand**: Lightweight state management
- **Axios**: HTTP client for API calls
- **React Router**: Client-side routing

### Database
- **SQLite**: Development environment
- **PostgreSQL**: Production-ready database support

## Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 18 or higher
- Git

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/DenizDogrul/Social-Media-Platform-With-AI.git
cd Social-Media-Platform-With-AI

# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env file with your API keys and database settings
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Database Setup

```bash
# In backend directory
cd backend

# Run database migrations
alembic upgrade head

# Optional: Load demo data
python scripts/seed_demo.py
```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=sqlite:///./app.db

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Application
APP_ENV=development
DEBUG=true
```

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Usage

### Development Environment

```bash
# Start backend server
cd backend
uvicorn app.main:app --reload

# Start frontend server
cd frontend
npm run dev
```

Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Production Deployment

```bash
# Backend deployment
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend build
cd frontend
npm run build
npm run preview
```

## API Documentation

### Main Endpoints

#### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Token refresh
- `POST /auth/logout` - User logout

#### Posts
- `GET /posts` - List posts
- `POST /posts` - Create new post
- `GET /posts/{id}` - Get post details
- `PUT /posts/{id}` - Update post
- `DELETE /posts/{id}` - Delete post

#### Interactions
- `POST /posts/{id}/like` - Like a post
- `DELETE /posts/{id}/like` - Unlike a post
- `POST /posts/{id}/comments` - Add comment
- `GET /posts/{id}/comments` - List comments

#### Real-time
- `WebSocket /ws/notifications` - Notification stream
- `WebSocket /ws/messages` - Message stream

For detailed API documentation, visit: http://localhost:8000/docs

## Testing

```bash
# Run backend tests
cd backend
pytest tests/ -v

# Run frontend linting
cd frontend
npm run lint
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

**Deniz Doğru** - [GitHub](https://github.com/DenizDogrul)</content>
<parameter name="filePath">c:\Users\Deniz\OneDrive\Masaüstü\tez\README.md