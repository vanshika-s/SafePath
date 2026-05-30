import os
import json
import random

import numpy as np
import pandas as pd
import geopandas as gpd

import osmnx as ox                          # load/save graphml, nearest_nodes
import networkx as nx                       # shortest_path, graph traversal

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D         # custom legend entries for route maps
from shapely.geometry import LineString     # fallback edge geometry for plotting
from datetime import datetime               # system clock for day/night detection

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from datetime import datetime, date
from dateutil import tz
from astral import LocationInfo
from astral.sun import sun


def get_night_or_day():
    current_location = (32.8801, -117.234) # User's current location 
    local_tz = tz.tzlocal()
    
    location = LocationInfo(latitude=current_location[0], longitude=current_location[1])
    s = sun(location.observer, date=datetime.now(), tzinfo=local_tz)
    
    dawn_hour = s["dawn"].hour + (s["dawn"].minute / 60)
    dusk_hour  = s["dusk"].hour  + (s["dusk"].minute  / 60)
    
    now = datetime.now()
    exact_hour = now.hour + (now.minute / 60)
    IS_NIGHT = exact_hour >= dawn_hour or exact_hour <= dusk_hour
    
    print(f'Current hour: {exact_hour} → {"Night" if IS_NIGHT else "Day"} mode')

