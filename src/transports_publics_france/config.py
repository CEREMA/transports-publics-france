"""
Configuration and parameters for the GTFS France pipeline
"""

DAYS_EN = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Mapping route_type GTFS → catégorie
ROUTE_TYPE_MAP = {
    **{str(k): "bus" for k in [3, 11, *range(200, 210), *range(700, 717), 800]},
    **{str(k): "tramway" for k in [0, 5, *range(900, 907)]},
    **{str(k): "métro" for k in [1, *range(400, 406)]},
    **{str(k): "train" for k in [2, *range(100, 118)]},
    **{str(k): "autres" for k in [
        4, 6, 7, 12, 1000, 1100, 1200, *range(1300, 1308),
        1400, *range(1500, 1508), *range(1700, 1703)
    ]},
}
ROUTE_TYPE_PRIORITY = {"train": 1, "métro": 2, "tramway": 3, "bus": 4, "bus TAD": 4}
# TODO : traduire les modes ?

# Clean stop names
STOPWORDS_FR = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "au",
    "aux", "à", "par", "sur", "sous", "pour", "dans", "ce", "se", "sa",
    "son", "ses", "que", "qui", "ne", "pas", "plus", "ou", "y", "il",
    "elle", "ils", "elles", "je", "tu", "nous", "vous", "mon", "ton",
    "rer", "terminus", "hall", "depart", "arrivee",
    # "est" excluded on purpose
}

ABBREV_MAP = {
    "saint": "st", "sainte": "ste", "route": "rte",
    "chemin": "ch", "boulevard": "bd", "avenue": "av",
}


# Validation of the GTFS files
REQUIRED_FILES = ["stops", "routes", "trips", "stop_times"]

REQUIRED_COLS = {
    "stops": ["stop_id"],
    "routes": ["route_id"],
    "trips": ["trip_id", "route_id"],
    "stop_times": ["trip_id", "stop_id"],
}

ID_COLS = {
    "stops": ["stop_id"],
    "routes": ["route_id", "agency_id"],
    "trips": ["trip_id", "route_id", "service_id"],
    "stop_times": ["trip_id", "stop_id"],
    "agency": ["agency_id"],
    "calendar": ["service_id"],
    "calendar_dates": ["service_id"],
}

TABLES_GTFS = [
    "stops", "routes", "trips", "stop_times",
    "agency", "calendar", "calendar_dates",
]

GTFS_FILES_WANTED = [
    "stop_times.txt", "stops.txt", "routes.txt", "trips.txt",
    "agency.txt", "calendar.txt", "calendars.txt", "calendar_dates.txt",
]

MODE_PRIORITY = {"train": 1, "métro": 2, "tramway": 3, "bus": 4, "bus TAD": 4}
