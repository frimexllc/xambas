LAUNCH_CATEGORY_DEFINITIONS = [
    {
        "name": "Limpieza del Hogar",
        "parent_id": None,
        "pricing_mode": "fixed",
        "risk_level": "standard",
        "attributes_schema": {
            "property_type": {
                "type": "string",
                "enum": ["departamento", "casa", "oficina_pequena"],
                "required": True,
            },
            "service_type": {
                "type": "string",
                "enum": ["basica", "profunda", "mudanza"],
                "required": True,
            },
            "bedrooms": {"type": "integer", "minimum": 0, "required": True},
            "bathrooms": {"type": "integer", "minimum": 1, "required": True},
            "area_m2": {"type": "number", "minimum": 20, "required": False},
            "supplies_included": {"type": "boolean", "required": False},
            "pets_present": {"type": "boolean", "required": False},
        },
        "children": [
            "Limpieza Basica",
            "Limpieza Profunda",
            "Limpieza de Mudanza",
        ],
    },
    {
        "name": "Plomeria",
        "parent_id": None,
        "pricing_mode": "quote",
        "risk_level": "standard",
        "attributes_schema": {
            "urgency": {
                "type": "string",
                "enum": ["programable", "urgente", "emergencia"],
                "required": True,
            },
            "issue_type": {
                "type": "string",
                "enum": ["fuga", "destape", "instalacion", "reparacion"],
                "required": True,
            },
            "property_type": {
                "type": "string",
                "enum": ["departamento", "casa", "local"],
                "required": True,
            },
            "water_supply_closed": {"type": "boolean", "required": False},
            "photos_count": {"type": "integer", "minimum": 0, "required": False},
        },
        "children": [
            "Fugas",
            "Destapes",
            "Instalaciones",
            "Reparaciones Generales",
        ],
    },
    {
        "name": "Electricidad",
        "parent_id": None,
        "pricing_mode": "quote",
        "risk_level": "regulated",
        "attributes_schema": {
            "urgency": {
                "type": "string",
                "enum": ["programable", "urgente", "emergencia"],
                "required": True,
            },
            "work_type": {
                "type": "string",
                "enum": ["apagones", "instalacion", "iluminacion", "tablero"],
                "required": True,
            },
            "property_type": {
                "type": "string",
                "enum": ["departamento", "casa", "local"],
                "required": True,
            },
            "power_cutoff_available": {"type": "boolean", "required": False},
            "licensed_work_required": {"type": "boolean", "required": False},
        },
        "children": [
            "Reparaciones Electricas",
            "Instalaciones Electricas",
            "Iluminacion",
            "Tablero Electrico",
        ],
    },
    {
        "name": "Montaje de Muebles",
        "parent_id": None,
        "pricing_mode": "fixed",
        "risk_level": "standard",
        "attributes_schema": {
            "furniture_type": {
                "type": "string",
                "enum": ["ropero", "cama", "escritorio", "centro_entretenimiento"],
                "required": True,
            },
            "pieces_count": {"type": "integer", "minimum": 1, "required": True},
            "wall_mount_required": {"type": "boolean", "required": False},
            "brand_or_model": {"type": "string", "required": False},
        },
        "children": [
            "Ropero",
            "Cama",
            "Escritorio",
            "Centro de Entretenimiento",
        ],
    },
]
