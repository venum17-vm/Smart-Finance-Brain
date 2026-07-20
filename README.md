# Smart Finance Brain

A comprehensive personal finance management and document processing application built with Python, Flask, and SQLite. Track expenses, analyze spending patterns, extract financial data from documents, and manage recurring bills and obligations.

## 🎯 Features

- **Expense Tracking**: Record and categorize daily expenses with automatic category detection
- **Budget Management**: Set monthly budgets and receive alerts when approaching limits
- **Smart Document Processing**: 
  - Extract financial data from PDFs, images, and documents
  - OCR-powered text extraction with Tesseract
  - AI-assisted analysis with Groq API (optional)
- **Obligation Management**: Track recurring bills, subscriptions, insurance, and EMIs
- **Financial Analytics**: 
  - Monthly and category-wise spending analysis
  - Expense trends and forecasting
  - Multiple payment method tracking
- **Email Alerts**: Configure budget notifications via Gmail
- **Web Dashboard**: Modern, responsive HTML/CSS/JS interface
- **Multi-user Support**: Isolated per-user databases for privacy
- **Data Import**: Import expenses from Excel, CSV, and text files

## 📋 Project Structure

```
SmartFinanceBrain/
├── server.py                    # Flask web server
├── database.py                  # SQLite database setup & helpers
├── email_service.py             # Gmail-based email alerts
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── LICENSE                      # MIT License
├── README.md                    # This file
├── modules/
│   ├── finance_manager.py       # Expense analytics & forecasting
│   ├── document_manager.py      # Document extraction & OCR
│   ├── document_extractor.py    # Text extraction utilities
│   ├── file_processor.py        # Import from Excel/CSV/Text
│   ├── obligation_manager.py    # Bill & subscription tracking
│   └── automation_engine.py     # Groq AI integration
├── ui/
│   ├── index.html               # Login page
│   ├── dashboard.html           # Main dashboard
│   ├── css/
│   │   └── dashboard.css        # Styling
│   └── js/
│       └── dashboard.js         # Frontend logic
├── data/                        # SQLite databases (gitignored)
│   └── default/                 # Sample/default user data
├── uploads/                     # Imported files (gitignored)
├── reports/                     # Generated reports (gitignored)
└── tests/
    └── test_all.py              # System tests
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **Tesseract OCR** (optional but recommended for document processing)
  - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
  - **macOS**: `brew install tesseract`
  - **Linux**: `sudo apt-get install tesseract-ocr`

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/SmartFinanceEngine.git
cd SmartFinanceEngine
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your configuration
# Important: Set FLASK_SECRET_KEY to a random value for production:
python -c "import secrets; print(secrets.token_hex(32))"
```

**Key environment variables:**
- `FLASK_SECRET_KEY`: Session encryption key (required for production)
- `DEFAULT_USER_PIN`: Default 4-digit PIN for new users (default: 1234)
- `GROQ_API_KEY`: Optional API key for AI features (get from https://console.groq.com/keys)

#### 5. Run the Application
```bash
python server.py
```

Open your browser and navigate to:
```
http://localhost:5000
```

#### 6. Create Your First Account
- Enter a phone number (10 digits)
- Set a 4-digit PIN
- Provide your email for alerts (optional)

## 🔑 Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Flask server
FLASK_SECRET_KEY=<generate a random hex string>
FLASK_ENV=development
FLASK_DEBUG=False

# Database
DEFAULT_USER_PIN=1234

# Groq API (optional)
GROQ_API_KEY=<your groq api key>

# Email service
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TIMEOUT=15

# Application
PORT=5000
HOST=localhost
LOG_LEVEL=INFO
```

### Generating a Secure Flask Secret Key

For production, generate a cryptographically secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and set it as `FLASK_SECRET_KEY` in your `.env` file.

## 🔧 Configuration

### Email Alerts (Gmail)

To enable budget alerts via email:

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Search for "App passwords"
4. Select "Mail" and "Windows Computer" (or your device)
5. Generate a password (16 characters)
6. In the app: Settings → Email Configuration
7. Enter your Gmail address and the generated App Password

### Groq API (Optional AI Features)

For AI-powered document analysis:

1. Sign up at [console.groq.com](https://console.groq.com)
2. Create an API key
3. Add to `.env`: `GROQ_API_KEY=<your_key>`

Without Groq API, the app falls back to Tesseract OCR for document processing.

### Tesseract OCR

Ensure Tesseract is installed and in your PATH:

**Windows:**
- Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- The app will auto-detect common installation paths

**Verify installation:**
```bash
tesseract --version
```

## 💾 Database Structure

### Global Database (`data/users.db`)
- `users`: User accounts, PINs, emails, budget alerts
- `settings`: Global application settings

### Per-User Database (`data/{phone}/finance.db`)
- `expenses`: All expense records
- `budget`: Monthly budget settings
- `documents`: Imported financial documents
- `obligations`: Recurring bills and subscriptions
- `imported_files`: Tracking of imported data files
- `chat_history`: Chat interactions with AI
- `user_settings`: User-specific preferences

## 📊 Expense Categories

- Food & Dining
- Transportation
- Shopping
- Entertainment
- Bills & Utilities
- Health & Medical
- Education
- Travel
- Investment
- Other

## 🔐 Security & Privacy

- **Local-first**: All data stored locally in SQLite, no cloud sync
- **Per-user isolation**: Each user's data is completely separated
- **Environment variables**: Sensitive credentials loaded from `.env` (not committed to git)
- **Session management**: Secure Flask session handling
- **No tracking**: Zero analytics or external tracking

**Sensitive files to keep private (already in .gitignore):**
- `.env` - Contains API keys and secrets
- `data/` - Contains user databases
- `uploads/` - Contains user-uploaded files
- `reports/` - Contains generated reports

## 🧪 Testing

Run the system tests:
```bash
python tests/test_all.py
```

This tests:
- Authentication
- Expense management
- Document extraction
- Obligation tracking
- Email service integration

## 🐛 Troubleshooting

### Port Already in Use
If port 5000 is busy, change it in `.env`:
```env
PORT=5001
```

### Tesseract Not Found
```bash
# Windows - Update PATH or reinstall Tesseract

# macOS
brew install tesseract

# Linux
sudo apt-get install tesseract-ocr
```

### Module Import Errors
Ensure you're in the virtual environment and have installed all dependencies:
```bash
pip install -r requirements.txt
```

### Database Corruption
Delete the corrupted database file and it will be recreated on next run:
```bash
rm data/users.db
rm data/{phone_number}/finance.db
```

## 📦 Dependencies

Key packages included:
- **Flask**: Web framework
- **SQLite3**: Database (included with Python)
- **Pandas**: Data processing
- **PyMuPDF**: PDF extraction
- **Pillow**: Image processing
- **OpenCV**: Advanced image processing
- **Tesseract**: OCR (via pytesseract)
- **python-dotenv**: Environment variable management

See `requirements.txt` for complete list with versions.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Groq](https://groq.com) - For the free Llama AI API
- [Tesseract OCR](https://github.com/tesseract-ocr) - For text extraction
- [Flask](https://flask.palletsprojects.com/) - Web framework

## 📞 Support

For issues and questions:
- Open a GitHub issue
- Check existing documentation
- Review test files for usage examples

## 🚦 Development Status

- ✅ Core functionality stable
- ✅ Multi-user support
- ✅ Document processing
- ✅ AI integration (optional)
- 🔄 Future: Mobile app, Cloud sync (opt-in), Advanced forecasting

---

**Made with ❤️ for personal finance management**
## Contributors

- Venu Madhava M
- Pankaj Kumar
