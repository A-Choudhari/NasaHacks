import json
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.core.paginator import Paginator
from .models import User
import requests
import folium
from folium import Map, TileLayer
from pystac_client import Client
import pandas as pd

# Provide the STAC and RASTER API endpoints
STAC_API_URL = "https://earth.gov/ghgcenter/api/stac"
RASTER_API_URL = "https://earth.gov/ghgcenter/api/raster"
collection_name = "odiac-ffco2-monthgrid-v2023"

def index(request):
    # Fetch the collection from the STAC API using the appropriate endpoint
    collection = requests.get(f"{STAC_API_URL}/collections/{collection_name}").json()
    number_of_items = get_item_count(collection_name)

    # Get the information about the number of granules found in the collection
    items = requests.get(f"{STAC_API_URL}/collections/{collection_name}/items?limit={number_of_items}").json()["features"]

    # Create a dictionary where the start datetime values for each granule is queried by year and month
    items = {item["properties"]["start_datetime"][:7]: item for item in items}

    # Specify the asset name
    asset_name = "co2-emissions"
    rescale_values = {
        "max": items[list(items.keys())[0]]["assets"][asset_name]["raster:bands"][0]["histogram"]["max"], 
        "min": items[list(items.keys())[0]]["assets"][asset_name]["raster:bands"][0]["histogram"]["min"]
    }

    # Fetch the tile for January 2000
    january_2000_tile = requests.get(
        f"{RASTER_API_URL}/collections/{items['2000-01']['collection']}/items/{items['2000-01']['id']}/tilejson.json?"
        f"&assets={asset_name}&color_formula=gamma+r+1.05&colormap_name=viridis"
        f"&rescale={rescale_values['min']},{rescale_values['max']}"
    ).json()

    # Create the Folium map (use Folium Map instead of DualMap)
    map_ = folium.Map(location=(34, -118), zoom_start=6)

    # Define the first map layer (January 2000)
    map_layer_2000 = TileLayer(
        tiles=january_2000_tile["tiles"][0],  # Path to retrieve the tile
        attr="GHG",  # Attribution
        opacity=0.8
    )
    map_layer_2000.add_to(map_)

    # Add any additional layers or markers as needed here

    # Save the map as an HTML string
    map_html = map_._repr_html_()

    # Pass the map HTML to the template
    return render(request, "network/index.html", {"map_html": map_html})

# Function to search for a data collection in the US GHG Center STAC API
def get_item_count(collection_id):
    count = 0
    items_url = f"{STAC_API_URL}/collections/{collection_id}/items"

    while True:
        response = requests.get(items_url)

        if not response.ok:
            print("Error getting items")
            exit()

        stac = response.json()
        count += int(stac["context"].get("returned", 0))

        next_link = [link for link in stac["links"] if link["rel"] == "next"]
        if not next_link:
            break
        
        items_url = next_link[0]["href"]

    return count
