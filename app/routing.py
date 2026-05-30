import os
import json
import random

import numpy as np
import pandas as pd
import geopandas as gpd

import osmnx as ox                          # load/save graphml, nearest_nodes
import networkx as nx                       # shortest_path, graph traversal

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def route_total_cost(G, route, weight):
    return sum(G[u][v][0].get(weight, 0) for u, v in zip(route[:-1], route[1:]))

def route_to_gdf(G, route):
        geoms = []
        for u, v in zip(route[:-1], route[1:]):
            data = G[u][v][0]
            if "geometry" in data:
                geoms.append(data["geometry"])
            else:
                geoms.append(LineString([(G.nodes[u]["x"], G.nodes[u]["y"]),
                                         (G.nodes[v]["x"], G.nodes[v]["y"])]))
        return gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326")

def get_routes(start, end, G):
    orig = ox.nearest_nodes(G, X=start[1], Y=start[0])
    dest = ox.nearest_nodes(G, X=end[1],   Y=end[0])

    def balanced_weight(u, v, d):
        d = d[0]
        score  = d.get('safety_score', 0.5)
        length = d.get('length', 0)
        return length * (1 + 2 * (1 - score))

    route_fastest = nx.shortest_path(G, orig, dest, weight='length')
    total_length  = route_total_cost(G, route_fastest, 'length')

    length_type = ('short'  if total_length < 500  else
                   'medium' if total_length <= 2000 else
                   'long')

    calc_safety_scores(G, scores, length_type)

    # Bulk-set attributes — much faster than a Python for-loop over 684k edges
    nx.set_edge_attributes(G, scores['safety_score'].to_dict(), 'safety_score')
    nx.set_edge_attributes(G, scores['safety_cost'].to_dict(),  'safety_cost')

    return {
        'fastest':  route_fastest,
        'safest':   nx.shortest_path(G, orig, dest, weight='safety_cost'),
        'balanced': nx.shortest_path(G, orig, dest, weight=balanced_weight),
    }