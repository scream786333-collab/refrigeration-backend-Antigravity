#!/usr/bin/env python3
"""
Diagnostic script to check if the refrigeration simulator is ready to run.
"""

import os
import sys
import json

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_ok(text):
    print(f"  ✓ {text}")

def print_error(text):
    print(f"  ✗ {text}")

def print_warning(text):
    print(f"  ⚠ {text}")

def main():
    print_header("Virtual Refrigeration System - Diagnostic Check")
    
    all_ok = True
    
    # 1. Check Python version
    print("\n1. Python Version:")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        print_error(f"Python {version.major}.{version.minor} (need 3.8+)")
        all_ok = False
    
    # 2. Check required files
    print("\n2. Required Files:")
    required_files = [
        'app.py',
        'requirements.txt',
        'templates/index.html',
        'data/refrigerants.json'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print_ok(file)
        else:
            print_error(f"{file} (missing)")
            all_ok = False
    
    # 3. Check Python packages
    print("\n3. Python Packages:")
    packages = [
        'flask',
        'flask_cors',
        'numpy',
        'matplotlib',
        'pandas',
        'reportlab'
    ]
    
    missing_packages = []
    for package in packages:
        try:
            __import__(package)
            print_ok(package)
        except ImportError:
            print_error(f"{package} (not installed)")
            missing_packages.append(package)
            all_ok = False
    
    # 4. Check refrigerants data
    print("\n4. Refrigerants Database:")
    try:
        with open('data/refrigerants.json', 'r') as f:
            refrigerants = json.load(f)
            print_ok(f"Found {len(refrigerants)} refrigerants")
            for ref in refrigerants.keys():
                print(f"     - {ref}")
    except Exception as e:
        print_error(f"Could not load refrigerants: {e}")
        all_ok = False
    
    # 5. Check directories
    print("\n5. Required Directories:")
    directories = [
        'templates',
        'static',
        'static/exports',
        'data'
    ]
    
    for dir_path in directories:
        if os.path.exists(dir_path):
            print_ok(dir_path)
        else:
            print_warning(f"{dir_path} (will be created)")
    
    # Summary and recommendations
    print("\n" + "="*60)
    if all_ok and not missing_packages:
        print("  ✓ All checks passed!")
        print("\n  You can now run:")
        print("    python app.py")
        print("\n  Then open: http://localhost:5000/")
    else:
        print("  ✗ Some checks failed!")
        if missing_packages:
            print(f"\n  Install missing packages:")
            print(f"    pip install {' '.join(missing_packages)}")
            print(f"\n  Or install all dependencies:")
            print(f"    pip install -r requirements.txt")
    
    print("="*60 + "\n")
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
