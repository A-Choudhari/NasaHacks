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
from openai import OpenAI

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
    news = receiveNews(request)

    markers = locationMarkers(request, news)

    # add marker one by one on the map
    for i in range(0,len(markers)):
        folium.Marker(
            location=[markers.iloc[i]['latitude'], markers.iloc[i]['longitude']],
            popup=markers.iloc[i]['popup'],
        ).add_to(map_html)


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


def receiveNews(request):
    country = User.objects.get(user=request.user.id).country
    url = (f'https://newsapi.org/v2/everything?'
       'q=CO2 Emission in {country}&'
       'from=2024-10-01&'
       'sortBy=popularity&'
       'apiKey=020f247b2f7d4945b16501d01ab185e7')

    response = requests.get(url)
    result = response.json
    return result


def locationMarkers(request, news):
    country = User.objects.get(id=request.user.id)
    data = pd.DataFrame(columns=['latitude', 'longitude', 'popup'])
    for new in news:
        json_string = json.dumps(new)
        # API KEY for OPENAI
        client = OpenAI(api_key="")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are figuring out the longitude and latitude of where these major CO2 emission events are happening."},
                {
                    "role": "user",
                    "content": f"""
                    Process the information below and give me 3 things. Each value should be on a new line and the value itself, no other information.
                    The first piece of information is give the latitude of where this is happening in the {country}.
                    Second piece of information is the giv the longitude of where this is happening in {country}.
                    Third information is generate HTML code to showcase the news report as a popup. 
                    I want the very top of popup to have a urlToImage, then the title should have a hyperlink to the news article, and finally a quick 1-2 sentence summary of what happened in relation to CO2 emissions.
                    {json_string}
                    """
                }
            ]
        )
        response_lines = completion.choices[0].message.content
        print(response_lines)
        # Extract each value (assuming the format will always have three lines)
        latitude = response_lines[0].strip()   # First line is latitude
        longitude = response_lines[1].strip()  # Second line is longitude
        html_popup = "\n".join(response_lines[2:]).strip()  # Remaining lines form the HTML code
        # Add the extracted data to the dataframe
        data = data.append({
            'latitude': latitude,
            'longitude': longitude,
            'popup': html_popup
        }, ignore_index=True)

    return data
