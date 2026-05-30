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

def load_edges():
    G = ox.load_graphml('../data/processed/sd_walk_graph.graphml')
    scores = pd.read_csv(
        '../data/processed/edge_scores_infrastructure.csv',
        index_col=['u', 'v', 'key']
    )
    
    # Extract edge length into scores once so safety_cost can be computed as a DataFrame op
    scores['length'] = pd.Series({
        (u, v, k): data.get('length', 0)
        for u, v, k, data in G.edges(keys=True, data=True)
        if (u, v, k) in scores.index
    })
    
    for u, v, key, data in G.edges(keys=True, data=True):
    idx = (u, v, key)
    if idx in scores.index:
        data["crime_score_short_day"]    = scores.loc[idx, "crime_score_short_day"]
        data["crime_score_medium_day"]   = scores.loc[idx, "crime_score_medium_day"]
        data["crime_score_long_day"]     = scores.loc[idx, "crime_score_long_day"]
        data["crime_score_short_night"]  = scores.loc[idx, "crime_score_short_night"]
        data["crime_score_medium_night"] = scores.loc[idx, "crime_score_medium_night"]
        data["crime_score_long_night"]   = scores.loc[idx, "crime_score_long_night"]
        data["walk_score"]               = scores.loc[idx, "walk_score"]
        data["infrastructure_score"]     = scores.loc[idx, "infrastructure_score"]