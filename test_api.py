#!/usr/bin/env python
"""Test the API to verify diagrams are working"""

import urllib.request
import json
import time

time.sleep(2)  # Give Flask time to restart

test_data = {
    "refrigerant": "R410A",
    "evaporator_temp": -5,
    "condenser_temp": 55,
    "superheat": 5,
    "subcool": 5,
    "compressor_efficiency": 80,
    "cooling_load": 10,
    "model_type": "ideal"
}

try:
    req = urllib.request.Request(
        'http://localhost:5000/calculate',
        data=json.dumps(test_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        
    print("✓ API Request Successful")
    print(f"  Success: {result.get('success')}")
    print(f"  Has charts: {'charts' in result}")
    
    if 'charts' in result:
        ph_diagram = result['charts'].get('ph_diagram', '')
        ts_diagram = result['charts'].get('ts_diagram', '')
        
        print(f"  P-h diagram starts with: {ph_diagram[:80]}")
        print(f"  T-s diagram starts with: {ts_diagram[:80]}")
        
        if ph_diagram and ts_diagram:
            print("\n✓ DIAGRAMS ARE BEING GENERATED CORRECTLY!")
        else:
            print("\n⚠ WARNING: Diagrams might be None or empty")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
