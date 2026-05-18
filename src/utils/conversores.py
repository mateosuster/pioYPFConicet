"""
Unit converters for hydrocarbon quantities and prices.
Direct translation of functiones_hidrocarburos.R.

Convention: _q = quantity conversion, _p = price conversion
"""


# --- Crude oil ---

def m3_to_bbl_q(x):
    """m³ → barrels (quantity)"""
    return x * 6.2898

def m3_to_bbl_p(x):
    """m³ → barrels (price: USD/m³ → USD/bbl)"""
    return x / 6.2898

def kg_to_bbl_q(x):
    """kg → barrels (quantity)"""
    return x * 0.0062898107438466


# --- Gas: volume ---

def ft3_to_m3_q(x):
    """ft³ → m³ (quantity). 1 ft³ = 0.02831685 m³"""
    return x * 0.02831685

def ft3_to_m3_p(x):
    """ft³ → m³ (price: USD/ft³ → USD/m³)"""
    return x / 0.02831685

def kg_to_m3_q(x):
    """kg → m³ using gas density at 15°C (0.737 kg/m³)"""
    return x / 0.737


# --- Gas: energy ---

def ft3_to_mmbtu_q(x):
    """ft³ → MMBTU (quantity). 1 ft³ = 0.001028 MMBTU"""
    return x * 0.001028

def ft3_to_mmbtu_p(x):
    """ft³ → MMBTU (price)"""
    return x / 0.001028

def m3_to_mmbtu_q(x):
    """m³ → MMBTU (quantity). 1 m³ = 0.0353 MMBTU (Canada Energy Regulator)"""
    return x * 0.0353

def m3_to_mmbtu_p(x):
    """m³ → MMBTU (price: USD/m³ → USD/MMBTU)"""
    return x / 0.0353

def mmbtu_to_m3_p(x):
    """MMBTU → m³ (price: USD/MMBTU → USD/m³). 1 MMBTU = 28.32861 m³"""
    return x / 28.32861


# --- BEP (barrel of oil equivalent) ---

def m3_to_bep_q(x):
    """m³ → BEP (quantity)"""
    return x * 5883

def mmbtu_to_bep_q(x):
    """MMBTU → BEP (quantity). BP factor"""
    return x * 0.17245496

def mmbtu_to_bep_p(x):
    """MMBTU → BEP (price)"""
    return x / 0.17245496

def bep_to_mmbtu_p(x):
    """BEP → MMBTU (price)"""
    return x / 5.798615


# --- General wrapper matching R signature ---

def conversor_hidrocarburos(x, from_unit, to_unit, producto, tipo="cantidad"):
    """
    General converter matching R's conversor_hidrocarburos() signature.

    Parameters
    ----------
    x : numeric or array-like
    from_unit : str  e.g. "m3", "bbl", "MMBTU", "ft3"
    to_unit   : str
    producto  : str  "gas" | "crudo"
    tipo      : str  "cantidad" | "precio"
    """
    key = (producto, from_unit, to_unit, tipo)
    dispatch = {
        ("gas",   "MMBTU", "m3",    "cantidad"): lambda x: x * 28.32861,
        ("gas",   "MMBTU", "m3",    "precio"):   mmbtu_to_m3_p,
        ("gas",   "m3",    "MMBTU", "cantidad"): m3_to_mmbtu_q,
        ("gas",   "m3",    "MMBTU", "precio"):   m3_to_mmbtu_p,
        ("gas",   "ft3",   "m3",    "cantidad"): ft3_to_m3_q,
        ("gas",   "ft3",   "m3",    "precio"):   ft3_to_m3_p,
        ("gas",   "ft3",   "MMBTU", "cantidad"): ft3_to_mmbtu_q,
        ("gas",   "ft3",   "MMBTU", "precio"):   ft3_to_mmbtu_p,
        ("crudo", "m3",    "bbl",   "cantidad"): m3_to_bbl_q,
        ("crudo", "m3",    "bbl",   "precio"):   m3_to_bbl_p,
        ("crudo", "kg",    "bbl",   "cantidad"): kg_to_bbl_q,
    }
    fn = dispatch.get(key)
    if fn is None:
        raise ValueError(f"No converter for {key}")
    return fn(x)
