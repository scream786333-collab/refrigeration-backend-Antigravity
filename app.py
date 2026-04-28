import os
import json
import io
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import numpy as np

# --- 1. SETUP PHYSICS ENGINE (CoolProp) ---
try:
    import CoolProp.CoolProp as CP
    HAS_COOLPROP = True
    print("[OK] High-Accuracy CoolProp Engine Loaded")
except ImportError:
    HAS_COOLPROP = False
    print("[WARN] CoolProp not found. Running in SIMULATION MODE (Approximate).")
    print("  To fix: pip install CoolProp")

# --- 2. SETUP CHARTING ENGINE (Matplotlib) ---
try:
    import matplotlib
    matplotlib.use('Agg') # Non-interactive backend for server
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Optional PDF export support (reportlab)
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

# --- FLASK APP SETUP ---
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, resources={r"/*": {"origins": "*"}})

# Ensure folders exist
os.makedirs('static/exports', exist_ok=True)
os.makedirs('data', exist_ok=True)

# --- REFRIGERANT DATABASE ---
DEFAULT_REFRIGERANTS = {
    "R134a": {"name": "R134a", "formula": "C2H2F4", "molar_mass": 102.03, "h_f_ref": 200.0, "cp_liquid": 1.43, "h_g_ref": 398.6, "cp_vapor": 0.94, "antoine_A": 14.41, "antoine_B": 2094, "antoine_C": -29.15},
    "R22": {"name": "R22", "formula": "CHClF2", "molar_mass": 86.47, "h_f_ref": 200.0, "cp_liquid": 1.26, "h_g_ref": 405.0, "cp_vapor": 0.76, "antoine_A": 14.55, "antoine_B": 2150, "antoine_C": -25.0},
    "R32": {"name": "R32", "formula": "CH2F2", "molar_mass": 52.02, "h_f_ref": 200.0, "cp_liquid": 1.94, "h_g_ref": 510.0, "cp_vapor": 0.85, "antoine_A": 14.70, "antoine_B": 2200, "antoine_C": -26.0},
    "R410A": {"name": "R410A", "formula": "Blend", "molar_mass": 72.58, "h_f_ref": 200.0, "cp_liquid": 1.52, "h_g_ref": 419.0, "cp_vapor": 0.84, "antoine_A": 14.60, "antoine_B": 2100, "antoine_C": -28.0},
    "R290": {"name": "R290", "formula": "C3H8", "molar_mass": 44.1, "h_f_ref": 200.0, "cp_liquid": 2.52, "h_g_ref": 550.0, "cp_vapor": 1.68, "antoine_A": 14.20, "antoine_B": 2050, "antoine_C": -30.0},
    "R600a": {"name": "R600a", "formula": "C4H10", "molar_mass": 58.12, "h_f_ref": 200.0, "cp_liquid": 2.38, "h_g_ref": 560.0, "cp_vapor": 1.68, "antoine_A": 14.10, "antoine_B": 2000, "antoine_C": -35.0}
}

# --- CALCULATION CLASS ---
class RefrigerationCycle:
    def __init__(self, refrigerant='R134a', evaporator_temp=-10, condenser_temp=40,
                 superheat=5, subcool=5, compressor_efficiency=0.85, cooling_load=10,
                 model_type='single-stage'):
        self.ref = refrigerant
        self.T_evap_C = evaporator_temp
        self.T_cond_C = condenser_temp
        self.superheat = superheat
        self.subcool = subcool
        self.eff_isen = compressor_efficiency 
        self.Q_load_kW = cooling_load
        self.model_type = model_type
        self.ref_props = DEFAULT_REFRIGERANTS.get(refrigerant, DEFAULT_REFRIGERANTS['R134a'])
        self.state_points = {}

    # MODE A: REAL PHYSICS (COOLPROP)
    def calculate_coolprop(self):
        T_evap_K = self.T_evap_C + 273.15
        T_cond_K = self.T_cond_C + 273.15
        
        # 1. Pressures
        try:
            P_evap = CP.PropsSI('P', 'T', T_evap_K, 'Q', 1.0, self.ref)
            P_cond = CP.PropsSI('P', 'T', T_cond_K, 'Q', 0.0, self.ref)
        except:
            # Fallback for blends with glide (R410A)
            P_evap = CP.PropsSI('P', 'T', T_evap_K, 'Q', 0.5, self.ref)
            P_cond = CP.PropsSI('P', 'T', T_cond_K, 'Q', 0.5, self.ref)

        # State 1: Comp In
        T1 = T_evap_K + self.superheat
        P1 = P_evap
        h1 = CP.PropsSI('H', 'T', T1, 'P', P1, self.ref)
        s1 = CP.PropsSI('S', 'T', T1, 'P', P1, self.ref)

        # State 2: Comp Out
        P2 = P_cond
        h2_ideal = CP.PropsSI('H', 'P', P2, 'S', s1, self.ref)
        h2 = h1 + (h2_ideal - h1) / self.eff_isen
        T2 = CP.PropsSI('T', 'P', P2, 'H', h2, self.ref)
        s2 = CP.PropsSI('S', 'P', P2, 'H', h2, self.ref)

        # State 3: Cond Out
        T3 = T_cond_K - self.subcool
        P3 = P_cond
        h3 = CP.PropsSI('H', 'T', T3, 'P', P3, self.ref)
        s3 = CP.PropsSI('S', 'T', T3, 'P', P3, self.ref)

        # State 4: Evap In
        P4 = P_evap
        h4 = h3 # Isenthalpic
        T4 = CP.PropsSI('T', 'P', P4, 'H', h4, self.ref)
        s4 = CP.PropsSI('S', 'P', P4, 'H', h4, self.ref)
        try: x4 = CP.PropsSI('Q', 'P', P4, 'H', h4, self.ref)
        except: x4 = 0.2

        # Store State Points (Units: kPa, C, kJ/kg)
        self.state_points = {
            '1': {'P': P1/1000, 'T': T1-273.15, 'h': h1/1000, 's': s1/1000, 'quality': None},
            '2': {'P': P2/1000, 'T': T2-273.15, 'h': h2/1000, 's': s2/1000, 'quality': None},
            '3': {'P': P3/1000, 'T': T3-273.15, 'h': h3/1000, 's': s3/1000, 'quality': None},
            '4': {'P': P4/1000, 'T': T4-273.15, 'h': h4/1000, 's': s4/1000, 'quality': x4}
        }
        
        # Performance
        q_evap = (h1 - h4) / 1000
        w_comp = (h2 - h1) / 1000
        q_cond = (h2 - h3) / 1000
        return self._format_results(q_evap, w_comp, q_cond)

    # MODE B: MANUAL SIMULATION (FALLBACK)
    def calculate_manual(self):
        props = self.ref_props
        # Antoine
        def get_P(T):
            try: return np.exp(props['antoine_A'] - props['antoine_B']/(T + 273.15 + props['antoine_C']))
            except: return 500.0
        
        P_evap = get_P(self.T_evap_C)
        P_cond = get_P(self.T_cond_C)

        T1 = self.T_evap_C + self.superheat
        h1 = props['h_g_ref'] + props['cp_vapor']*(T1-self.T_evap_C)
        
        T2_ideal = (T1+273.15)*(P_cond/P_evap)**0.2 - 273.15
        h2_ideal = props['h_g_ref'] + props['cp_vapor']*(T2_ideal-self.T_cond_C)
        h2 = h1 + (h2_ideal-h1)/self.eff_isen
        T2 = T2_ideal + 15
        
        T3 = self.T_cond_C - self.subcool
        h3 = props['h_f_ref'] - props['cp_liquid']*(self.T_cond_C-T3)
        h4 = h3
        
        self.state_points = {
            '1': {'P': P_evap, 'T': T1, 'h': h1, 's': 1.7, 'quality': None},
            '2': {'P': P_cond, 'T': T2, 'h': h2, 's': 1.8, 'quality': None},
            '3': {'P': P_cond, 'T': T3, 'h': h3, 's': 0.5, 'quality': None},
            '4': {'P': P_evap, 'T': self.T_evap_C, 'h': h4, 's': 0.6, 'quality': 0.3}
        }
        return self._format_results(h1-h4, h2-h1, h2-h3)

    def _format_results(self, q_evap, w_comp, q_cond):
        COP = q_evap/w_comp if w_comp > 0 else 0
        m_dot = self.Q_load_kW/q_evap if q_evap > 0 else 0
        return {
            'state_points': self.state_points,
            'performance': {
                'COP': round(COP, 3), 'refrigeration_effect': round(q_evap, 2),
                'compressor_work': round(w_comp, 2), 'heat_rejected': round(q_cond, 2),
                'mass_flow_rate': round(m_dot, 5), 'compressor_power': round(m_dot*w_comp, 3),
                'volumetric_efficiency': 85.0, 'cooling_capacity': self.Q_load_kW
            },
            'refrigerant': self.ref, 'model_type': self.model_type,
            'operating_conditions': {
                'evaporator_temp': self.T_evap_C, 'condenser_temp': self.T_cond_C,
                'superheat': self.superheat, 'subcool': self.subcool, 
                'compressor_efficiency': self.eff_isen*100
            }
        }

    def calculate(self):
        if HAS_COOLPROP:
            try: return self.calculate_coolprop()
            except Exception as e:
                print(f"CoolProp Error: {e}. Switching to Manual.")
                return self.calculate_manual()
        else:
            return self.calculate_manual()

    def get_points(self):
        return [self.state_points.get(i, {'P':0,'h':0,'s':0,'T':0}) for i in ['1','2','3','4']]

# --- DIAGRAMS ---
def get_chart(cycle, type_):
    if not HAS_MATPLOTLIB: return None
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        pts = cycle.get_points()
        x = [p['h'] if type_=='ph' else p['s'] for p in pts]
        y = [p['P'] if type_=='ph' else p['T'] for p in pts]
        
        # Plot Logic
        ax.plot(x, y, 'bo', markersize=8)
        ax.plot(x+[x[0]], y+[y[0]], 'b-', linewidth=2)
        
        title = "P-h Diagram" if type_ == 'ph' else "T-s Diagram"
        xlabel = "Enthalpy (kJ/kg)" if type_ == 'ph' else "Entropy (kJ/kg·K)"
        ylabel = "Pressure (kPa)" if type_ == 'ph' else "Temperature (°C)"
        
        ax.set_title(f"{title} ({cycle.ref})")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}"
    except Exception as e:
        print(f"Chart Error: {e}")
        return None

# --- ROUTES ---
@app.route('/')
def index():
    """Serve the main frontend template if it exists, otherwise return API info."""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Template not found: {e}. Serving API info page.")
        return (
            "<html><head><title>Refrigeration Backend</title></head>"
            "<body style='font-family:Arial,Helvetica,sans-serif;padding:20px;'>"
            "<h1>Refrigeration Backend Running</h1>"
            "<p>Frontend template not found. Use the API endpoints directly.</p>"
            "<p>Available endpoints:</p>"
            "<ul>"
            "<li><code>POST /calculate</code> - Calculate refrigeration cycle</li>"
            "<li><code>GET /refrigerants</code> - List refrigerants</li>"
            "</ul>"
            "</body></html>"
        )

@app.route('/calculate', methods=['POST'])
def calculate_route():
    try:
        d = request.json or {}
        cycle = RefrigerationCycle(
            refrigerant=d.get('refrigerant', 'R134a'),
            evaporator_temp=float(d.get('evaporator_temp', -10)),
            condenser_temp=float(d.get('condenser_temp', 40)),
            superheat=float(d.get('superheat', 5)),
            subcool=float(d.get('subcool', 5)),
            compressor_efficiency=float(d.get('compressor_efficiency', 85))/100.0,
            cooling_load=float(d.get('cooling_load', 10))
        )
        res = cycle.calculate()
        return jsonify({
            "success": True, 
            "results": res, 
            "charts": {
                "ph_diagram": get_chart(cycle, 'ph'), 
                "ts_diagram": get_chart(cycle, 'ts')
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/refrigerants', methods=['GET'])
def get_refs():
    return jsonify(DEFAULT_REFRIGERANTS)

# Pre-defined Experiments Database
EXPERIMENTS = {
    "1": {
        "id": "1",
        "title": "Experiment 1: Effect of Evaporator Temperature on COP",
        "description": "Investigate how changing evaporator temperature affects COP and compressor power.",
        "objectives": [
            "Understand the relationship between evaporator temperature and COP",
            "Analyze how evaporator temperature affects refrigeration effect",
            "Observe compressor power variation with temperature changes"
        ],
        "procedure": [
            "Set refrigerant to R134a, condenser temperature to 40°C, superheat to 5°C, subcool to 5°C",
            "Set evaporator temperature to -15°C and record COP and compressor power",
            "Increase evaporator temperature to -10°C and record values",
            "Increase to -5°C and record",
            "Increase to 0°C and record",
            "Compare results and identify trends"
        ],
        "results": {
            "data_points": [
                {"Evaporator Temp (°C)": -15, "COP": "2.85", "Compressor Power (kW)": "3.51", "Cooling Capacity (kW)": 10},
                {"Evaporator Temp (°C)": -10, "COP": "3.42", "Compressor Power (kW)": "2.92", "Cooling Capacity (kW)": 10},
                {"Evaporator Temp (°C)": -5, "COP": "4.12", "Compressor Power (kW)": "2.43", "Cooling Capacity (kW)": 10},
                {"Evaporator Temp (°C)": 0, "COP": "5.08", "Compressor Power (kW)": "1.97", "Cooling Capacity (kW)": 10}
            ],
            "conclusion": "As evaporator temperature increases, COP improves significantly and compressor power requirement decreases. This shows the benefit of maintaining higher evaporator temperatures for efficiency."
        }
    },
    "2": {
        "id": "2",
        "title": "Experiment 2: Effect of Condenser Temperature on Compressor Work",
        "description": "Analyze the influence of condenser temperature on compressor energy consumption.",
        "objectives": [
            "Determine how condenser temperature affects compressor work",
            "Understand pressure ratio effects on compression",
            "Analyze COP variation with condenser temperature"
        ],
        "procedure": [
            "Set refrigerant to R134a, evaporator temperature to -10°C, superheat to 5°C, subcool to 5°C",
            "Set condenser temperature to 35°C and record compressor work and COP",
            "Increase condenser temperature to 40°C and record values",
            "Increase to 45°C and record",
            "Increase to 50°C and record",
            "Analyze the relationship between condenser temperature and compressor work"
        ],
        "results": {
            "data_points": [
                {"Condenser Temp (°C)": 35, "Compressor Work (kJ/kg)": "35.2", "COP": "4.10", "Cooling Capacity (kW)": 10},
                {"Condenser Temp (°C)": 40, "Compressor Work (kJ/kg)": "39.8", "COP": "3.42", "Cooling Capacity (kW)": 10},
                {"Condenser Temp (°C)": 45, "Compressor Work (kJ/kg)": "45.1", "COP": "2.98", "Cooling Capacity (kW)": 10},
                {"Condenser Temp (°C)": 50, "Compressor Work (kJ/kg)": "51.3", "COP": "2.58", "Cooling Capacity (kW)": 10}
            ],
            "conclusion": "Higher condenser temperatures significantly increase compressor work requirement and reduce COP. This demonstrates the importance of effective condenser cooling in efficient refrigeration systems."
        }
    },
    "3": {
        "id": "3",
        "title": "Experiment 3: Comparison of Refrigerants",
        "description": "Compare performance of R22, R134a, R410A, R32, R600a, and R290 under identical conditions.",
        "objectives": [
            "Compare COP of different refrigerants",
            "Analyze compressor work for each refrigerant",
            "Evaluate refrigeration effects across refrigerants"
        ],
        "procedure": [
            "Set operating conditions: evaporator temp -10°C, condenser temp 40°C, superheat 5°C, subcool 5°C",
            "Calculate cycle for R22 and record COP and compressor power",
            "Repeat for R134a, R410A, R32, R600a, and R290",
            "Tabulate and compare results",
            "Note any safety classifications and environmental impacts"
        ],
        "results": {
            "data_points": [
                {"Refrigerant": "R22", "COP": "3.45", "Compressor Power (kW)": "2.90", "Mass Flow (kg/s)": "0.1379"},
                {"Refrigerant": "R134a", "COP": "3.42", "Compressor Power (kW)": "2.92", "Mass Flow (kg/s)": "0.1205"},
                {"Refrigerant": "R410A", "COP": "3.38", "Compressor Power (kW)": "2.96", "Mass Flow (kg/s)": "0.0834"},
                {"Refrigerant": "R32", "COP": "3.52", "Compressor Power (kW)": "2.84", "Mass Flow (kg/s)": "0.1147"},
                {"Refrigerant": "R600a", "COP": "3.89", "Compressor Power (kW)": "2.57", "Mass Flow (kg/s)": "0.0714"},
                {"Refrigerant": "R290", "COP": "4.15", "Compressor Power (kW)": "2.41", "Mass Flow (kg/s)": "0.0682"}
            ],
            "conclusion": "R290 and R600a show superior COP values but have safety concerns (flammable). R32 offers good performance with lower GWP than R410A. Selection depends on balancing efficiency, environmental impact, and safety requirements."
        }
    },
    "4": {
        "id": "4",
        "title": "Experiment 4: Effect of Superheating on Cycle Efficiency",
        "description": "Study how superheating degree impacts efficiency and compressor work.",
        "objectives": [
            "Analyze effect of superheat on compressor inlet conditions",
            "Determine optimal superheat for efficiency",
            "Observe COP and power variations with superheat"
        ],
        "procedure": [
            "Set refrigerant to R134a, evaporator temp -10°C, condenser temp 40°C, subcool 5°C",
            "Set superheat to 0°C and record COP and compressor work",
            "Increase superheat to 5°C and record",
            "Increase to 10°C and record",
            "Increase to 15°C and record",
            "Identify optimal superheat degree"
        ],
        "results": {
            "data_points": [
                {"Superheat (°C)": 0, "COP": "3.48", "Compressor Work (kJ/kg)": "38.8"},
                {"Superheat (°C)": 5, "COP": "3.42", "Compressor Work (kJ/kg)": "39.8"},
                {"Superheat (°C)": 10, "COP": "3.35", "Compressor Work (kJ/kg)": "41.2"},
                {"Superheat (°C)": 15, "COP": "3.28", "Compressor Work (kJ/kg)": "42.8"}
            ],
            "conclusion": "Excessive superheat reduces cycle efficiency. Lower superheat improves COP, but minimum superheat is needed to ensure no liquid slugging into the compressor. Optimal superheat is typically 5-10°C."
        }
    },
    "5": {
        "id": "5",
        "title": "Experiment 5: Two-Stage vs Single-Stage Performance",
        "description": "Compare performance of single-stage and two-stage compression systems.",
        "objectives": [
            "Compare COP of single-stage and two-stage systems",
            "Analyze compressor work for each configuration",
            "Evaluate benefits of two-stage compression"
        ],
        "procedure": [
            "Calculate single-stage cycle: evaporator -20°C, condenser 40°C",
            "Record COP and compressor work",
            "For two-stage: set intercooler at 5°C, measure pressure ratio across each stage",
            "Record total COP and total compressor work",
            "Compare pressure ratios and work distribution"
        ],
        "results": {
            "data_points": [
                {"Configuration": "Single-Stage", "COP": "2.78", "Compressor Work (kJ/kg)": "45.3", "Pressure Ratio": "8.95"},
                {"Configuration": "Two-Stage (Intercooled)", "COP": "3.65", "Compressor Work (kJ/kg)": "32.1", "Pressure Ratio": "2.99 each"}
            ],
            "conclusion": "Two-stage compression with intercooling significantly improves COP (31% higher) and reduces compressor work by distributing the pressure ratio more evenly. Beneficial for wide temperature differences."
        }
    },
    "6": {
        "id": "6",
        "title": "Experiment 6: Effect of Subcooling on Refrigeration Effect",
        "description": "Investigate how subcooling increases refrigeration effect and COP.",
        "objectives": [
            "Understand subcooling effect on refrigeration effect",
            "Analyze COP variation with subcool degree",
            "Determine optimal subcooling level"
        ],
        "procedure": [
            "Set refrigerant to R134a, evaporator temp -10°C, condenser temp 40°C, superheat 5°C",
            "Set subcool to 0°C and record COP and refrigeration effect",
            "Increase subcool to 5°C and record",
            "Increase to 10°C and record",
            "Increase to 15°C and record",
            "Analyze trends and identify optimal subcooling"
        ],
        "results": {
            "data_points": [
                {"Subcool (°C)": 0, "COP": "3.32", "Refrigeration Effect (kJ/kg)": "126.5"},
                {"Subcool (°C)": 5, "COP": "3.42", "Refrigeration Effect (kJ/kg)": "131.2"},
                {"Subcool (°C)": 10, "COP": "3.52", "Refrigeration Effect (kJ/kg)": "135.8"},
                {"Subcool (°C)": 15, "COP": "3.58", "Refrigeration Effect (kJ/kg)": "139.2"}
            ],
            "conclusion": "Subcooling the liquid refrigerant increases the refrigeration effect and improves COP. Every 5°C of additional subcooling improves COP by ~3%. Practical limit is around 10-15°C."
        }
    }
}

@app.route('/experiments', methods=['GET'])
def get_exps():
    """Return list of all experiments"""
    return jsonify([
        {
            "id": "1",
            "title": "Experiment 1: Effect of Evaporator Temperature on COP",
            "description": "Investigate how changing evaporator temperature affects COP and compressor power."
        },
        {
            "id": "2",
            "title": "Experiment 2: Effect of Condenser Temperature on Compressor Work",
            "description": "Analyze the influence of condenser temperature on compressor energy consumption."
        },
        {
            "id": "3",
            "title": "Experiment 3: Comparison of Refrigerants",
            "description": "Compare performance of R22, R134a, R410A, R32, R600a, and R290 under identical conditions."
        },
        {
            "id": "4",
            "title": "Experiment 4: Effect of Superheating on Cycle Efficiency",
            "description": "Study how superheating degree impacts efficiency and compressor work."
        },
        {
            "id": "5",
            "title": "Experiment 5: Two-Stage vs Single-Stage Performance",
            "description": "Compare performance of single-stage and two-stage compression systems."
        },
        {
            "id": "6",
            "title": "Experiment 6: Effect of Subcooling on Refrigeration Effect",
            "description": "Investigate how subcooling increases refrigeration effect and COP."
        }
    ])

@app.route('/experiment/<experiment_id>', methods=['GET'])
def get_experiment(experiment_id):
    """Return detailed experiment data"""
    experiment = EXPERIMENTS.get(experiment_id)
    if not experiment:
        return jsonify({"error": "Experiment not found"}), 404
    return jsonify(experiment)

def generate_csv_export(data):
    """Generate formatted text/CSV export from results."""
    # Handle both formats: wrapped {results: {...}} or direct results
    if 'results' in data and isinstance(data['results'], dict):
        results = data['results']
    else:
        results = data
    
    lines = []
    lines.append("=" * 70)
    lines.append("REFRIGERATION CYCLE ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append("")
    
    # Refrigerant and model info
    lines.append(f"Refrigerant: {results.get('refrigerant', 'N/A')}")
    lines.append(f"Model Type: {results.get('model_type', 'N/A')}")
    lines.append("")
    
    # Operating Conditions
    lines.append("OPERATING CONDITIONS")
    lines.append("-" * 70)
    op = results.get('operating_conditions', {})
    for key, value in op.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    
    # Performance Metrics
    lines.append("PERFORMANCE METRICS")
    lines.append("-" * 70)
    perf = results.get('performance', {})
    for key, value in perf.items():
        if value is not None:
            lines.append(f"  {key}: {value}")
    lines.append("")
    
    # State Points
    lines.append("STATE POINTS")
    lines.append("-" * 70)
    states = results.get('state_points', {})
    if states:
        # Header
        lines.append(f"{'Point':<8} {'P (kPa)':<12} {'T (°C)':<12} {'h (kJ/kg)':<14} {'s (kJ/kg·K)':<14} {'Quality':<10}")
        lines.append("-" * 70)
        # Data rows
        for pid in ['1', '2', '3', '4']:
            s = states.get(pid, {})
            P = s.get('P', '')
            T = s.get('T', '')
            h = s.get('h', '')
            s_val = s.get('s', '')
            x = s.get('quality', '')
            lines.append(f"{pid:<8} {str(P):<12} {str(T):<12} {str(h):<14} {str(s_val):<14} {str(x):<10}")
    lines.append("")
    lines.append("=" * 70)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    
    return "\n".join(lines)


@app.route('/export/csv', methods=['POST'])
def export_csv():
    d = request.json or {}
    fn = f"refrigeration_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    fp = os.path.join('static/exports', fn)
    try:
        text_content = generate_csv_export(d)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(text_content)
        return send_file(fp, as_attachment=True, download_name=fn, mimetype='text/plain')
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def generate_pdf_report(data, filepath):
    """Create a simple PDF report from results dict using ReportLab."""
    if not HAS_REPORTLAB:
        raise RuntimeError('ReportLab not installed. Install with: pip install reportlab')

    # Handle two possible payload formats:
    # 1. Frontend sends: {state_points, performance, operating_conditions, ...}
    # 2. Or wrapped: {results: {...}}
    if 'results' in data and isinstance(data['results'], dict):
        results = data['results']
    else:
        results = data

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph('Refrigeration Simulation Report', styles['Title']))
    elements.append(Spacer(1, 12))

    # Operating conditions
    op = results.get('operating_conditions', {})
    elements.append(Paragraph('Operating Conditions', styles['Heading2']))
    op_rows = [[Paragraph('Parameter', styles['Heading4']), Paragraph('Value', styles['Heading4'])]]
    for k, v in op.items():
        op_rows.append([Paragraph(str(k), styles['BodyText']), Paragraph(str(v), styles['BodyText'])])
    t = Table(op_rows, colWidths=[180, 330], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Performance
    perf = results.get('performance', {})
    elements.append(Paragraph('Performance', styles['Heading2']))
    perf_rows = [[Paragraph('Metric', styles['Heading4']), Paragraph('Value', styles['Heading4'])]]
    for k, v in perf.items():
        perf_rows.append([Paragraph(str(k), styles['BodyText']), Paragraph(str(v), styles['BodyText'])])
    t2 = Table(perf_rows, colWidths=[180, 330], hAlign='LEFT')
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 12))

    # State points (if any)
    states = results.get('state_points', {})
    if states:
        elements.append(Paragraph('State Points', styles['Heading2']))
        sp_rows = [[Paragraph('Point', styles['Heading4']), Paragraph('P (kPa)', styles['Heading4']), Paragraph('T (°C)', styles['Heading4']), Paragraph('h (kJ/kg)', styles['Heading4']), Paragraph('s', styles['Heading4']), Paragraph('quality', styles['Heading4'])]]
        for pid in ['1','2','3','4']:
            s = states.get(pid, {})
            P_val = f"{s.get('P'):.2f}" if s.get('P') is not None and s.get('P') != '' else ''
            T_val = f"{s.get('T'):.1f}" if s.get('T') is not None and s.get('T') != '' else ''
            h_val = f"{s.get('h'):.2f}" if s.get('h') is not None and s.get('h') != '' else ''
            s_val = f"{s.get('s'):.3f}" if s.get('s') is not None and s.get('s') != '' else ''
            q_val = f"{s.get('quality'):.3f}" if s.get('quality') is not None and s.get('quality') != '' else 'N/A'
            sp_rows.append([
                Paragraph(str(pid), styles['BodyText']),
                Paragraph(P_val, styles['BodyText']),
                Paragraph(T_val, styles['BodyText']),
                Paragraph(h_val, styles['BodyText']),
                Paragraph(s_val, styles['BodyText']),
                Paragraph(q_val, styles['BodyText'])
            ])
        t3 = Table(sp_rows, colWidths=[40, 90, 80, 110, 70, 80], hAlign='LEFT')
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        elements.append(t3)
        elements.append(Spacer(1, 12))

    # Add charts to PDF if present
    charts = data.get('charts', {})
    import base64
    import io

    # P-h Diagram
    if 'ph_diagram' in charts and charts['ph_diagram']:
        try:
            elements.append(Paragraph('P-h Diagram', styles['Heading2']))
            img_data = charts['ph_diagram'].split('base64,')[-1]
            img_bytes = base64.b64decode(img_data)
            img = Image(io.BytesIO(img_bytes), width=400, height=250)
            elements.append(img)
            elements.append(Spacer(1, 12))
        except Exception as e:
            print(f"Error embedding P-h diagram: {e}")

    # T-s Diagram
    if 'ts_diagram' in charts and charts['ts_diagram']:
        try:
            elements.append(Paragraph('T-s Diagram', styles['Heading2']))
            img_data = charts['ts_diagram'].split('base64,')[-1]
            img_bytes = base64.b64decode(img_data)
            img = Image(io.BytesIO(img_bytes), width=400, height=250)
            elements.append(img)
            elements.append(Spacer(1, 12))
        except Exception as e:
            print(f"Error embedding T-s diagram: {e}")

    doc.build(elements)


@app.route('/export/pdf', methods=['POST'])
def export_pdf():
    if not HAS_REPORTLAB:
        return jsonify({"success": False, "error": "PDF export requires reportlab. Install with: pip install reportlab"}), 503

    d = request.json or {}
    print(f"DEBUG: /export/pdf received payload keys: {d.keys()}")
    print(f"DEBUG: Payload structure: {json.dumps(d, indent=2, default=str)[:500]}")
    
    fn = f"refrigeration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    fp = os.path.join('static/exports', fn)
    try:
        generate_pdf_report(d, fp)
        return send_file(fp, as_attachment=True, download_name=fn, mimetype='application/pdf')
    except Exception as e:
        print(f"ERROR in /export/pdf: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("=========================================")
    print("  Backend Started: http://localhost:5000")
    print("=========================================")
    app.run(host='0.0.0.0', port=5000, debug=True)