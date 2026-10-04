from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = BACKEND_DIR / "models"
SOIL_CSV = ROOT / "india_soil_data.csv"

SERVICE_DISTRICTS = [
    "Pune",
    "Nashik",
    "Ahmednagar",
    "Satara",
    "Solapur",
    "Sangli",
    "Kolhapur",
    "Latur",
]

# Union of the eight districts (Maharashtra).
SERVICE_BBOX = {
    "lat_min": 16.25,
    "lat_max": 20.65,
    "lon_min": 73.15,
    "lon_max": 77.05,
}

# Back-compat aliases used by older imports
PUNE_BBOX = SERVICE_BBOX
REGION_CENTER = {"lat": 18.5204, "lon": 73.8567}
PUNE_CENTER = REGION_CENTER

PUNE_CROPS = [
    "sugarcane",
    "grapes",
    "onion",
    "jowar",
    "bajra",
    "wheat",
    "maize",
    "soybean",
    "chickpea",
    "rice",
    "tomato",
    "groundnut",
    "cotton",
]

CROP_EMOJI = {
    "sugarcane": "🎋",
    "grapes": "🍇",
    "onion": "🧅",
    "jowar": "🌾",
    "bajra": "🌾",
    "wheat": "🌾",
    "maize": "🌽",
    "soybean": "🌱",
    "chickpea": "🫘",
    "rice": "🌾",
    "tomato": "🍅",
    "groundnut": "🥜",
    "cotton": "🌸",
}

CROP_INFO = {
    "sugarcane": "Long-duration cash crop; needs irrigation and warm months.",
    "grapes": "Pune specialty; well-drained soils and a dry ripening window.",
    "onion": "Major rabi/late-kharif crop around Pune; needs moderate N and drainage.",
    "jowar": "Sorghum — drought-hardy cereal for rainfed kharif.",
    "bajra": "Pearl millet — suited to lighter soils and lower rainfall.",
    "wheat": "Rabi cereal; cooler nights and irrigation help tillering.",
    "maize": "Flexible cereal for kharif if moisture is reliable.",
    "soybean": "Kharif oilseed/legume on medium-black soils.",
    "chickpea": "Rabi pulse (gram); residual moisture and neutral pH.",
    "rice": "Only where rainfall or irrigation can pond the field (west/ghat side).",
    "tomato": "Irrigated horticulture; sensitive to waterlogging.",
    "groundnut": "Needs sandy-loam and a dry harvest spell.",
    "cotton": "Kharif fibre crop on deeper soils with a long frost-free season.",
}

# Agronomic envelopes used for rule scoring (Pune / western Maharashtra).
CROP_PROFILES = {
    "sugarcane": {"ph": (6.0, 7.5), "n": (80, 160), "p": (40, 80), "k": (40, 120), "temp": (20, 35), "hum": (50, 85), "rain": (800, 1500), "season": "Annual"},
    "grapes": {"ph": (6.0, 7.5), "n": (40, 90), "p": (30, 70), "k": (50, 150), "temp": (15, 35), "hum": (40, 70), "rain": (500, 900), "season": "Annual"},
    "onion": {"ph": (6.0, 7.5), "n": (50, 100), "p": (40, 80), "k": (40, 90), "temp": (13, 28), "hum": (50, 75), "rain": (400, 800), "season": "Rabi"},
    "jowar": {"ph": (6.0, 8.0), "n": (40, 90), "p": (20, 50), "k": (20, 60), "temp": (22, 35), "hum": (40, 75), "rain": (400, 750), "season": "Kharif"},
    "bajra": {"ph": (6.5, 8.5), "n": (30, 80), "p": (15, 45), "k": (15, 50), "temp": (25, 38), "hum": (35, 70), "rain": (300, 650), "season": "Kharif"},
    "wheat": {"ph": (6.0, 7.5), "n": (60, 120), "p": (30, 60), "k": (30, 60), "temp": (12, 25), "hum": (40, 70), "rain": (400, 800), "season": "Rabi"},
    "maize": {"ph": (5.5, 7.5), "n": (60, 120), "p": (35, 70), "k": (30, 80), "temp": (18, 32), "hum": (50, 80), "rain": (500, 1000), "season": "Kharif"},
    "soybean": {"ph": (6.0, 7.5), "n": (40, 90), "p": (30, 70), "k": (30, 70), "temp": (20, 32), "hum": (55, 85), "rain": (600, 1100), "season": "Kharif"},
    "chickpea": {"ph": (6.0, 8.0), "n": (20, 70), "p": (20, 50), "k": (20, 50), "temp": (15, 28), "hum": (40, 70), "rain": (300, 650), "season": "Rabi"},
    "rice": {"ph": (5.0, 7.0), "n": (70, 130), "p": (35, 60), "k": (30, 50), "temp": (20, 32), "hum": (70, 95), "rain": (1000, 2000), "season": "Kharif"},
    "tomato": {"ph": (6.0, 7.5), "n": (70, 140), "p": (40, 90), "k": (50, 120), "temp": (18, 30), "hum": (50, 80), "rain": (500, 900), "season": "Rabi"},
    "groundnut": {"ph": (6.0, 7.5), "n": (20, 60), "p": (30, 70), "k": (30, 80), "temp": (22, 33), "hum": (45, 75), "rain": (450, 900), "season": "Kharif"},
    "cotton": {"ph": (6.0, 8.0), "n": (60, 120), "p": (30, 70), "k": (40, 90), "temp": (21, 34), "hum": (45, 80), "rain": (600, 1200), "season": "Kharif"},
}

SEASON_WINDOWS = {
    "Kharif": (6, 10),   # Jun–Oct
    "Rabi": (11, 3),     # Nov–Mar
    "Zaid": (3, 6),      # Mar–Jun
}

DISTRICT_CENTROIDS = {
    "Pune": (18.5204, 73.8567),
    "Ahmednagar": (19.0948, 74.7480),
    "Satara": (17.6805, 74.0183),
    "Solapur": (17.6599, 75.9064),
    "Nashik": (19.9975, 73.7898),
    "Sangli": (16.8524, 74.5815),
    "Kolhapur": (16.7050, 74.2433),
    "Latur": (18.4088, 76.5604),
}

MODEL_BLEND_RULE_WEIGHT = 0.30
MODEL_BLEND_ML_WEIGHT = 0.70
