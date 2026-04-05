try:
    import CoolProp.CoolProp as CP
    HAS_COOLPROP = True
except Exception:
    CP = None
    HAS_COOLPROP = False

import numpy as np
from dataclasses import dataclass

class RefrigerationCycle:
    """
    Standard Vapor Compression Cycle Calculator using CoolProp (Real Gas EOS).
    """
    
    def __init__(self, refrigerant='R134a', evaporator_temp=-10, condenser_temp=40,
                 superheat=5, subcool=5, compressor_efficiency=0.85,
                 cooling_load=10):
        
        self.ref = refrigerant
        # Inputs
        self.T_evap_C = evaporator_temp
        self.T_cond_C = condenser_temp
        self.superheat = superheat
        self.subcool = subcool
        self.eff_isen = compressor_efficiency
        self.Q_load_kW = cooling_load  # Cooling Capacity in kW

        # Internal State Storage
        self.states = {} 

    def _get_prop(self, output_key, input_pair_1, value_1, input_pair_2, value_2):
        """Helper to wrap CoolProp calls and handle units (SI internally)"""
        if not HAS_COOLPROP:
            raise ImportError(
                "CoolProp is not installed. Install it with `pip install CoolProp` "
                "or run the backend using the embedded fallback model."
            )

        try:
            val = CP.PropsSI(output_key, input_pair_1, value_1, input_pair_2, value_2, self.ref)
            return val
        except Exception as e:
            raise ValueError(f"CoolProp Error for {self.ref}: {e}")

    def calculate(self):
        """
        Calculates the Single-Stage Vapor Compression Cycle.
        """
        
        # --- PREPARATION (Units: Pa, K) ---
        T_evap_K = self.T_evap_C + 273.15
        T_cond_K = self.T_cond_C + 273.15
        
        # 1. Get Saturation Pressures (Bubble point for liquid, Dew point for vapor)
        # Q=1 is Saturated Vapor, Q=0 is Saturated Liquid
        P_evap = self._get_prop('P', 'T', T_evap_K, 'Q', 1.0)
        P_cond = self._get_prop('P', 'T', T_cond_K, 'Q', 0.0)

        # --- STATE 1: Compressor Inlet (Evaporator Outlet) ---
        # Condition: Pressure = P_evap, Temp = T_evap + Superheat
        T1 = T_evap_K + self.superheat
        P1 = P_evap
        
        h1 = self._get_prop('H', 'T', T1, 'P', P1)
        s1 = self._get_prop('S', 'T', T1, 'P', P1)

        # --- STATE 2: Compressor Outlet ---
        # Process: Compression from P1 to P_cond
        P2 = P_cond
        
        # Step A: Ideal Isentropic Compression (s2_ideal = s1)
        # We find the enthalpy if the compressor was perfect (100% efficient)
        h2_isen = self._get_prop('H', 'P', P2, 'S', s1)
        
        # Step B: Actual Compression using Isentropic Efficiency
        # h2_actual = h1 + (work_ideal / efficiency)
        h2 = h1 + (h2_isen - h1) / self.eff_isen
        
        # Find Actual T2 and s2 based on P2 and new h2
        T2 = self._get_prop('T', 'P', P2, 'H', h2)
        s2 = self._get_prop('S', 'P', P2, 'H', h2)

        # --- STATE 3: Condenser Outlet ---
        # Condition: Pressure = P_cond, Temp = T_cond - Subcool
        P3 = P_cond
        T3 = T_cond_K - self.subcool
        
        h3 = self._get_prop('H', 'T', T3, 'P', P3)
        s3 = self._get_prop('S', 'T', T3, 'P', P3)

        # --- STATE 4: Evaporator Inlet ---
        # Process: Isenthalpic Expansion (Throttling) -> h4 = h3
        P4 = P_evap
        h4 = h3
        
        # Determine Quality (x) and Temperature at inlet
        T4 = self._get_prop('T', 'P', P4, 'H', h4)
        s4 = self._get_prop('S', 'P', P4, 'H', h4)
        x4 = self._get_prop('Q', 'P', P4, 'H', h4) # Vapor quality

        # --- PERFORMANCE CALCULATIONS ---
        # Mass Flow Rate (m_dot) = Cooling Capacity / Refrigeration Effect
        # Units: kW / (kJ/kg) -> kW / (J/kg / 1000) -> kg/s
        refrig_effect_J = h1 - h4
        m_dot = (self.Q_load_kW * 1000) / refrig_effect_J
        
        # Compressor Work (Power)
        # W = m_dot * (h2 - h1)
        work_specific_J = h2 - h1
        power_kW = (m_dot * work_specific_J) / 1000
        
        # Heat Rejected (Condenser)
        q_rejected_J = h2 - h3
        heat_rejected_kW = (m_dot * q_rejected_J) / 1000
        
        # COP
        cop = self.Q_load_kW / power_kW

        # --- FORMATTING OUTPUT (match backend/frontend schema) ---
        # Use string keys for states to match expected API shape
        self.state_points = {
            '1': {
                'T': float(round(T1 - 273.15, 3)),
                'P': float(round(P1 / 1000.0, 3)),
                'h': float(round(h1 / 1000.0, 3)),
                's': float(round(s1 / 1000.0, 4)),
                'quality': 1.0
            },
            '2': {
                'T': float(round(T2 - 273.15, 3)),
                'P': float(round(P2 / 1000.0, 3)),
                'h': float(round(h2 / 1000.0, 3)),
                's': float(round(s2 / 1000.0, 4)),
                'quality': 1.0
            },
            '3': {
                'T': float(round(T3 - 273.15, 3)),
                'P': float(round(P3 / 1000.0, 3)),
                'h': float(round(h3 / 1000.0, 3)),
                's': float(round(s3 / 1000.0, 4)),
                'quality': 0.0
            },
            '4': {
                'T': float(round(T4 - 273.15, 3)),
                'P': float(round(P4 / 1000.0, 3)),
                'h': float(round(h4 / 1000.0, 3)),
                's': float(round(s4 / 1000.0, 4)),
                'quality': float(x4) if x4 is not None else None
            }
        }

        performance = {
            'COP': float(round(cop, 3)),
            'compressor_power': float(round(power_kW, 3)),
            'compressor_work': float(round(work_specific_J / 1000.0, 3)),
            'cooling_capacity': float(round(self.Q_load_kW, 3)),
            'heat_rejected': float(round(heat_rejected_kW, 3)),
            'mass_flow_rate': float(round(m_dot, 5)),
            'refrigeration_effect': float(round(refrig_effect_J / 1000.0, 3)),
            'volumetric_efficiency': None
        }

        return {
            'performance': performance,
            'state_points': self.state_points
        }

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Create cycle with the parameters from your original log
    cycle = RefrigerationCycle(
        refrigerant='R134a',
        evaporator_temp=-10,
        condenser_temp=40,
        superheat=5,
        subcool=5,
        compressor_efficiency=0.85,
        cooling_load=10
    )
    
    results = cycle.calculate()
    
    print("\n--- PERFORMANCE ---")
    for k, v in results['performance'].items():
        print(f"{k}: {v}")
        
    print("\n--- STATE POINTS (T: °C, P: kPa, h: kJ/kg) ---")
    print(f"{'Pt':<4} {'P (kPa)':<10} {'T (°C)':<10} {'h (kJ/kg)':<10} {'Quality':<8}")
    for pt, data in results['states'].items():
        x_str = f"{data['x']:.3f}" if 0 <= data['x'] <= 1 else "Super/Sub"
        print(f"{pt:<4} {data['P']:<10.2f} {data['T']:<10.2f} {data['h']:<10.2f} {x_str:<8}")