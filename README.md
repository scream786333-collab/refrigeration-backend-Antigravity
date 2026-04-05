# Virtual Refrigeration System Simulator

A complete web-based virtual laboratory for studying and analyzing refrigeration cycles.

## 📋 Quick Start Guide

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- A modern web browser (Chrome, Firefox, Edge, Safari)

### Installation & Running

#### Option 1: Windows Batch Script (Easiest)
1. Double-click `start_backend.bat`
2. Wait for the server to start (you should see "Running on http://localhost:5000")
3. Open your browser and go to: **http://localhost:5000/**

#### Option 2: Windows PowerShell
1. Open PowerShell in the `refrigeration-backend` folder
2. Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` (if needed)
3. Run: `.\start_backend.ps1`
4. Open your browser and go to: **http://localhost:5000/**

#### Option 3: Manual Setup
1. Open Command Prompt in the `refrigeration-backend` folder
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Start the Flask backend:
   ```
   python app.py
   ```
4. Optional (for PDF export):
   ```
   pip install reportlab
   ```
4. You should see:
   ```
   ============================================================
     Virtual Refrigeration System Simulator
     Backend running at: http://localhost:5000
     API available at: http://localhost:5000/api
   ============================================================
   ```
5. Open your browser and go to: **http://localhost:5000/**

## 🔧 Troubleshooting

### Error: "Failed to contact backend. Check that Flask is running."

This means the frontend cannot reach the backend. Here's how to fix it:

1. **Check if Flask is running:**
   - You should see "Running on http://localhost:5000" in the console
   - Try opening http://localhost:5000 in your browser directly
   - You should see the homepage

2. **Port 5000 might be in use:**
   ```
   # Find what's using port 5000:
   netstat -ano | findstr :5000
   
   # Kill the process (replace PID with the number shown):
   taskkill /PID <PID> /F
   ```

3. **Firewall might be blocking connections:**
   - Allow Python through Windows Firewall
   - Or use a different port by editing `app.py` (line with `app.run`)

4. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

### Error: "ModuleNotFoundError: No module named 'flask'"

Install the required packages:
```
pip install -r requirements.txt
```

### PDF export fails with "PDF export failed"

If the Export PDF feature returns an error, the server may be missing ReportLab. Install it with:

```
pip install reportlab
```

If you cannot install ReportLab, the backend will respond with a 503 error. The CSV/text export still works without this package.

### Port Already in Use

If port 5000 is already in use, you can change it:

1. Edit `app.py` (last line)
2. Change `app.run(host='0.0.0.0', port=5000, debug=True)`
   to `app.run(host='0.0.0.0', port=5001, debug=True)`
3. Update the frontend in `templates/index.html` (line 1071)
   Change `const API_BASE = 'http://localhost:5000';`
   to `const API_BASE = 'http://localhost:5001';`

## 📁 Project Structure

```
refrigeration-backend/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── thermo_calculations.py      # Thermodynamic calculations
├── utils.py                    # Utility functions
├── start_backend.bat          # Windows batch startup script
├── start_backend.ps1          # PowerShell startup script
├── data/
│   └── refrigerants.json      # Refrigerant properties database
├── static/
│   └── exports/               # Generated export files (CSV, PDF, Excel)
└── templates/
    └── index.html             # Web interface
```

## 🚀 Features

- **Interactive Simulation:** Real-time refrigeration cycle analysis
- **Multiple Refrigerants:** R134a, R22, R410A, R32, R600a, R290
- **Advanced Diagrams:** P-h and T-s cycle diagrams
- **Parametric Studies:** Pre-defined experiments and case studies
- **Data Export:** CSV, PDF, and Excel report generation
- **System Visualization:** Animated refrigeration system components
- **Performance Metrics:** COP, compressor power, capacity analysis

## 🔗 API Endpoints

Once running, you can access:

- **Main App:** http://localhost:5000/
- **API Documentation:** http://localhost:5000/api
- **Calculate Cycle:** POST http://localhost:5000/calculate
- **Get Refrigerants:** GET http://localhost:5000/refrigerants
- **Get Experiments:** GET http://localhost:5000/experiments
- **Export CSV:** POST http://localhost:5000/export/csv
- **Export PDF:** POST http://localhost:5000/export/pdf
- **Export Excel:** POST http://localhost:5000/export/excel

## 🛠️ Development

### To add a new refrigerant:
Edit `data/refrigerants.json` and add the properties.

### To modify calculation models:
Edit the `RefrigerationCycle` class in `app.py`.

### To change the UI:
Edit `templates/index.html`.

## 📊 Typical Workflow

1. **Start Backend:** Run `start_backend.bat`
2. **Open Browser:** Go to http://localhost:5000
3. **Configure Simulation:** 
   - Select refrigerant
   - Set evaporator/condenser temperatures
   - Adjust other parameters
4. **Calculate:** Click "Calculate Cycle"
5. **View Results:** See the diagrams, tables, and performance metrics
6. **Export Data:** Download as CSV, PDF, or Excel

## 🐛 Debugging

If something doesn't work:

1. **Check the console:**
   - Press F12 in your browser
   - Go to "Console" tab
   - Look for error messages

2. **Check the backend logs:**
   - Look at the command prompt/terminal where Flask is running
   - Red errors indicate problems

3. **Verify connectivity:**
   - Try accessing http://localhost:5000/api in your browser
   - You should see a JSON response

## 📝 System Requirements

- Windows 7 or later (or Linux/Mac)
- Python 3.8+
- 100MB free disk space
- Modern web browser

## 📧 Support

For issues or questions, check the error messages carefully. They usually indicate exactly what's wrong.

---

**Happy Simulating! 🧊❄️**
