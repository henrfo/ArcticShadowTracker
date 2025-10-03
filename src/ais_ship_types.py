# src/ais_ship_types.py

# AIS Ship Type Codes (ITU-R M.1371 standard)
# Source: NOAA Marine Cadastre 2018

SHIP_TYPE_MAP = {
    0: 'Not available',
    
    # 1-19: Reserved
    **{i: 'Reserved for future use' for i in range(1, 20)},
    
    # 20-29: Wing in ground (WIG)
    20: 'Wing in ground (WIG)',
    21: 'WIG, hazardous category A',
    22: 'WIG, hazardous category B',
    23: 'WIG, hazardous category C',
    24: 'WIG, hazardous category D',
    **{i: 'WIG, reserved for future use' for i in range(25, 30)},
    
    # 30: Fishing
    30: 'Fishing',
    
    # 31-32: Towing
    31: 'Towing',
    32: 'Towing (length > 200m or breadth > 25m)',
    
    # 33-39: Special operations
    33: 'Dredging or underwater ops',
    34: 'Diving ops',
    35: 'Military ops',
    36: 'Sailing',
    37: 'Pleasure craft',
    38: 'Reserved',
    39: 'Reserved',
    
    # 40-49: High speed craft (HSC)
    40: 'High speed craft (HSC)',
    41: 'HSC, hazardous category A',
    42: 'HSC, hazardous category B',
    43: 'HSC, hazardous category C',
    44: 'HSC, hazardous category D',
    **{i: 'HSC, reserved' for i in range(45, 49)},
    49: 'HSC, no additional info',
    
    # 50-59: Special vessels
    50: 'Pilot vessel',
    51: 'Search and rescue',
    52: 'Tug',
    53: 'Port tender',
    54: 'Anti-pollution equipment',
    55: 'Law enforcement',
    56: 'Spare - local vessel',
    57: 'Spare - local vessel',
    58: 'Medical transport',
    59: 'Ship (RR Resolution No. 18)',
    
    # 60-69: Passenger
    60: 'Passenger',
    61: 'Passenger, hazardous category A',
    62: 'Passenger, hazardous category B',
    63: 'Passenger, hazardous category C',
    64: 'Passenger, hazardous category D',
    **{i: 'Passenger, reserved' for i in range(65, 69)},
    69: 'Passenger, no additional info',
    
    # 70-79: Cargo
    70: 'Cargo',
    71: 'Cargo, hazardous category A',
    72: 'Cargo, hazardous category B',
    73: 'Cargo, hazardous category C',
    74: 'Cargo, hazardous category D',
    **{i: 'Cargo, reserved' for i in range(75, 79)},
    79: 'Cargo, no additional info',
    
    # 80-89: Tanker
    80: 'Tanker',
    81: 'Tanker, hazardous category A',
    82: 'Tanker, hazardous category B',
    83: 'Tanker, hazardous category C',
    84: 'Tanker, hazardous category D',
    **{i: 'Tanker, reserved' for i in range(85, 89)},
    89: 'Tanker, no additional info',
    
    # 90-99: Other
    90: 'Other type',
    91: 'Other, hazardous category A',
    92: 'Other, hazardous category B',
    93: 'Other, hazardous category C',
    94: 'Other, hazardous category D',
    **{i: 'Other, reserved' for i in range(95, 99)},
    99: 'Other, no additional info',
}

# Broad categories for filtering
SHIP_CATEGORIES = {
    'Fishing': [30],
    'Military': [35],
    'Cargo': list(range(70, 80)),
    'Tanker': list(range(80, 90)),
    'Passenger': list(range(60, 70)),
    'Towing': [31, 32, 52],
    'Pleasure': [36, 37],
}

def get_ship_type(code):
    """Returns ship type description for AIS code"""
    return SHIP_TYPE_MAP.get(code, 'Unknown')

def get_category(code):
    """Returns broad category for AIS code"""
    for category, codes in SHIP_CATEGORIES.items():
        if code in codes:
            return category
    return 'Other'