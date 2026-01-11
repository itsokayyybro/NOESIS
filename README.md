# NOESIS: Learn with Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://noesis-1kyo.onrender.com/)

An AI-powered learning platform that generates personalized learning modules tailored to your organization's tech stack and documentation. Built with Google's Gemini AI and advanced RAG (Retrieval-Augmented Generation) capabilities.

## 🌟 Overview

NOESIS transforms the way organizations approach technical training by creating adaptive learning paths grounded in real codebases, internal documentation, and industry best practices. Instead of generic tutorials, learners receive contextual, company-specific modules that accelerate onboarding and skill development.

**Live Demo:** [https://noesis-1kyo.onrender.com/](https://noesis-1kyo.onrender.com/)

## ✨ Key Features

### 🎯 Contextual Learning
- **Organization-Specific Content**: Upload internal docs, codebases, and technical specifications to ground learning modules in your actual tech stack
- **Multi-Format Support**: Accepts `.txt`, `.md`, `.pdf`, `.json`, and `.ipynb` files for maximum flexibility
- **Intelligent Document Processing**: Automatically chunks and indexes documentation for optimal retrieval

### 🧠 AI-Powered Generation
- **Gemini-Driven Modules**: Leverages Google's Gemini AI to create comprehensive learning checkpoints
- **Adaptive Complexity**: Generates content tailored to skill level and learning prerequisites
- **RAG Architecture**: Retrieval-Augmented Generation ensures responses are accurate and grounded in provided context

### 🔄 Dynamic Learning Paths
- **Adaptive Checkpoints**: AI analyzes topic complexity to create appropriate learning milestones
- **Prerequisite Mapping**: Intelligent sequencing based on concept dependencies
- **Multi-Domain Support**: Pre-configured for Microservices, Data Pipelines, Frontend, and DevOps tracks

### ✅ Live Code Validation
- **Real-Time Feedback**: Instant code checking with intelligent error detection
- **Interactive Learning**: Hands-on exercises validated against best practices
- **Progress Tracking**: Monitor learner advancement through checkpoints

### 🔐 Admin Dashboard
- **Content Management**: Centralized control over learning modules and resources
- **Analytics & Insights**: Track learner progress and module effectiveness
- **Curriculum Customization**: Fine-tune learning paths for specific teams or roles

## 🏗️ Architecture

NOESIS employs a sophisticated RAG (Retrieval-Augmented Generation) workflow:

### Context Processing
- Users can paste text or upload files directly in the interface
- Request-specific grounding for personalized learning experiences
- Documents are processed in real-time for immediate contextual learning
- Intelligent chunking and embedding pipeline for optimal information retrieval

## 🛠️ Tech Stack

- **Backend**: Python (Flask)
- **AI Engine**: Google Gemini API with RAG
- **Document Processing**: Custom chunking and embedding pipeline
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Render.com
- **Storage**: JSON-based context store

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Google Gemini API key
- pip package manager

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/itsokayyybro/NOESIS.git
cd NOESIS
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
export GEMINI_API_KEY=your_gemini_api_key_here
export FLASK_SECRET_KEY=your_secret_key_here  # Required for production
```

4. **Run the application**
```bash
python app.py
```

5. **Access the platform**
Open your browser to `http://localhost:5000`

## 📁 Project Structure

```
NOESIS/
├── app.py                      # Main Flask application
├── backend_logic.py            # Core RAG and AI logic
├── validator.py                # Code validation engine
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment config
├── static/                     # CSS, JS, images
├── templates/                  # HTML templates
└── backend_logic.ipynb         # Development notebook
```

## 🎓 Usage

### For Learners

1. **Navigate to the Platform**: Visit the homepage
2. **Select Learning Domain**: Choose from Microservices, Data Pipelines, Frontend, or DevOps
3. **Upload Context (Optional)**: Add company-specific docs or paste text for personalized modules
4. **Start Learning**: Receive AI-generated checkpoints tailored to your needs
5. **Validate Code**: Test your solutions with real-time feedback

### For Administrators

1. **Access Admin Panel**: Navigate to `/admin`
2. **Configure Domains**: Customize learning tracks for your tech stack
3. **Monitor Progress**: Track learner engagement and module completion

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Your Google Gemini API key | Yes |
| `FLASK_SECRET_KEY` | Flask session secret (production) | Yes (prod) |

### Document Processing

- **File Size Limits**: Large files are automatically trimmed before chunking
- **Supported Formats**: `.txt`, `.md`, `.ipynb`, `.json`, `.pdf`
- **Chunking Strategy**: Semantic chunking for optimal retrieval

## 🤝 Team

This project was developed by a talented team of developers:

- **Your Name** - Project Lead & Backend Development
- **OM** - AI Integration & RAG Implementation  
- **Jeet** - Frontend Development & UI/UX
- **Prince** - DevOps & Deployment

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini for powering our AI capabilities
- The open-source community for excellent libraries and tools
- Our beta testers for valuable feedback

## 📧 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/itsokayyybro/NOESIS/issues)
- **Discussions**: [GitHub Discussions](https://github.com/itsokayyybro/NOESIS/discussions)

## 🗺️ Roadmap

- [ ] Multi-language support
- [ ] Team collaboration features
- [ ] Advanced analytics dashboard
- [ ] Mobile application
- [ ] Integration with popular LMS platforms
- [ ] Video content generation
- [ ] Gamification elements

## 🔒 Security

- All API keys should be stored as environment variables
- Never commit sensitive credentials to version control
- Use `FLASK_SECRET_KEY` in production environments
- Regularly update dependencies to patch vulnerabilities

## 🚀 Deployment

The application is configured for deployment on Render.com via `render.yaml`. For other platforms:

1. Set environment variables in your hosting platform
2. Ensure all dependencies in `requirements.txt` are installed
3. Configure the appropriate Python version (3.8+)
4. Set the start command to `python app.py`

---

**Built with ❤️ by the NOESIS Team**

*Empowering organizations to learn smarter, not harder.*
