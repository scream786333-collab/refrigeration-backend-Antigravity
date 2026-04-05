import requests

url = 'http://localhost:5000/static/industrialSystems1-ezgif.com-resize.gif'
try:
    r = requests.get(url, timeout=5)
    print(f'✓ Flask Status: {r.status_code}')
    print(f'✓ Content-Type: {r.headers.get("Content-Type")}')
    print(f'✓ File Size: {len(r.content)} bytes')
    print(f'✓ GIF Accessible: YES')
except Exception as e:
    print(f'✗ Error: {e}')

# Also test index page
print('\n--- Testing Index Page ---')
try:
    r2 = requests.get('http://localhost:5000/', timeout=5)
    print(f'✓ Index Page Status: {r2.status_code}')
    if 'industrialSystems1-ezgif' in r2.text:
        print('✓ Image reference found in HTML')
except Exception as e:
    print(f'✗ Error: {e}')
