import json
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.core.paginator import Paginator
import folium.elements
from .models import User, Post, Follows, Like
import requests
import folium
from folium import Map, TileLayer
from pystac_client import Client
import pandas as pd
import google.generativeai as genai

# Provide the STAC and RASTER API endpoints
STAC_API_URL = "https://earth.gov/ghgcenter/api/stac"
RASTER_API_URL = "https://earth.gov/ghgcenter/api/raster"
collection_name = "odiac-ffco2-monthgrid-v2023"

def index(request):
    all_posts = Post.objects.all().order_by("-timestamp")
    p = Paginator(all_posts, 10)
    page_number = request.GET.get('page')
    page_obj = p.get_page(page_number)
    allikes = Like.objects.all()
    wholikedit = []
    try:
        for like in allikes:
            if like.user.id == request.user.id:
                wholikedit.append(like.post.id)
    except:
        wholikedit = []



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
    # news = receiveNews(request)

    # markers = locationMarkers(request, news)

    # # add marker one by one on the map
    # for i in range(0,len(markers)):
    #     #Setup the content of the popup
    #     iframe = folium.IFrame(html=markers.iloc[i]['popup'], width=300, height=200)
    #     #Initialise the popup using the iframe
    #     popup = folium.Popup(iframe, min_width=300, max_width=300)


    #     folium.Marker(
    #         location=[markers.iloc[i]['latitude'], markers.iloc[i]['longitude']],
    #         popup=popup,
    #         icon=folium.Icon(color='red', icon='')
    #     ).add_to(map_)


    # Save the map as an HTML string
    map_html = map_._repr_html_()

    return render(request, "network/index.html", {"posts": page_obj, "likes":wholikedit, "map_html":map_html})


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
    if request.user.is_authenticated:
        country = User.objects.get(id=request.user.id).country
        print(country)
        # print(country)
        url = (f'https://newsapi.org/v2/everything?'
        'q={country}s CO2 Emission&'
        'from=2024-10-01&'
        'sortBy=popularity&'
        'apiKey=020f247b2f7d4945b16501d01ab185e7')

        response = requests.get(url)
        result = response.json()
        # Check if 'articles' exist in the result
        if "articles" in result:
            articles = result["articles"]
            # Convert articles to a list of dictionaries or do whatever you need with them
            # article_dicts = [{'title': article['title'], 'author': article['author']} for article in articles]
            output = json.dumps(result.get('articles'), indent=4)  # Serialize the articles to JSON
            
            # Print the serialized articles
            # print("Articles:\n", output)
            return result.get('articles')
    else:
        return ''


def locationMarkers(request, news):
    if request.user.is_authenticated:
        country = User.objects.get(id=request.user.id).country
        data = pd.DataFrame(columns=['latitude', 'longitude', 'popup'])
        rows = []
        for new in news:
            json_string = json.dumps(new)
            # print(json_string)
            genai.configure(api_key='AIzaSyDsh0GZOVerHIn5dwRV-yP4gUGG2Jk28yE')

            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"""
                        Process the information below and give me 3 things. Each value should be on a new line and the value itself, no other text.
                        The first piece of information is give the latitude of where this is happening in the {country}.
                        Second piece of information is the longitude of where this is happening in {country}.
                        Third information is generate HTML code to showcase the news report as a popup. The image's dimensions should be 200x100 which is width x height 
                        I want the very top of popup to have a urlToImage, then the title should have a hyperlink to the news article, and finally a quick 1-2 sentence summary of what happened in relation to CO2 emissions.
                        {json_string}
            
            """)
            response_lines = response.text.strip().split("\n")
            print(response_lines)
            # Extract each value (assuming the format will always have three lines)
            latitude = response_lines[0].strip()   # First line is latitude
            longitude = response_lines[1].strip()  # Second line is longitude
            html_popup = "\n".join(response_lines[3:len(response_lines) - 1]).strip()  # Remaining lines form the HTML code
            print(f"Latitude: {latitude}")
            print(f"Longitude: {longitude}")
            print(f"HTML: {html_popup}")
            # Add the extracted data to the dataframe
            rows.append({
                'latitude': latitude,
                'longitude': longitude,
                'popup': html_popup
            })
        data = pd.concat([data, pd.DataFrame(rows)], ignore_index=True)
        return data
    else:
        return ''


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        country = request.POST["country"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.country = country
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html", {'user': User})


def profile(request, profile_id):
    profile_info = User.objects.get(pk=profile_id)
    post_info = Post.objects.filter(user=profile_info).order_by("-timestamp")
    p = Paginator(post_info, 10)
    page_number = request.GET.get('page')
    page_obj = p.get_page(page_number)

    follows = len(Follows.objects.filter(following=profile_info))
    followed = Follows.objects.filter(followed=profile_info)

    allikes = Like.objects.all()
    post_liked = []
    try:
        for like in allikes:
            if like.user.id == request.user.id:
                post_liked.append(like.post.id)
    except:
        post_liked = []
    check_follow = followed.filter(following=User.objects.get(pk=request.user.id))
    if len(check_follow) != 0:
        user_follow = True
    else:
        user_follow = False
    return render(request, "network/profile.html", {"profile": profile_info, "posts": page_obj,
                                                    "following": follows, "followed": followed,
                                                    "user_follow": user_follow, "likes":post_liked})


def following(request):
    user = User.objects.get(pk=request.user.id)
    data = Follows.objects.filter(following=user)
    posts = Post.objects.all().order_by("-timestamp")
    following_posts = []
    for post in posts:
        for dat in data:
            if dat.followed == post.user:
                following_posts.append(post)

    p = Paginator(following_posts, 10)
    page_number = request.GET.get('page')
    page_obj = p.get_page(page_number)

    allikes = Like.objects.all()
    post_liked = []
    try:
        for like in allikes:
            if like.user.id == request.user.id:
                post_liked.append(like.post.id)
    except:
        post_liked = []

    return render(request, "network/follow.html", {"posts": page_obj, "likes":post_liked})


def like(request, post_id):
    if request.method == "PUT":
        post = Post.objects.get(pk=post_id)
        number_likes = post.likes
        user = User.objects.get(pk=request.user.id)
        data = json.loads(request.body)
        try:
            if data.get("like") is not None:
                islike = data["like"]
                if islike:
                    new_like = Like(user=user, post=post)
                    new_like.save()
                    post.likes = number_likes + 1
                    post.save()
                else:
                    specific_post = Like.objects.get(user=user, post=post)
                    post.likes = post.likes - 1
                    post.save()
                    specific_post.delete()

                return JsonResponse({"message":"Success"})
        except:
            return JsonResponse({"message":"Issue in liking/unliking post"})



def newpost(request):
    if request.method == "POST":
        new_post = request.POST["new_post"]
        user = User.objects.get(pk=request.user.id)
        data = Post(text=new_post, user=user)
        data.save()
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/newpost.html")


def follow_user(request):
    if request.method == "POST":
        profile_id = request.POST["followed"]
        x = Follows(following=request.user, followed=User.objects.get(pk=profile_id))
        x.save()
    return HttpResponseRedirect(reverse(profile, kwargs={"profile_id": profile_id}))


def unfollow_user(request):
    if request.method == "POST":
        profile_id = request.POST["unfollowed"]
        x = Follows.objects.get(following=request.user, followed=User.objects.get(pk=profile_id))
        x.delete()
    return HttpResponseRedirect(reverse(profile, kwargs={"profile_id": profile_id}))


def edit(request, edit_id):
    if request.method == "POST":
        post_data = Post.objects.get(pk=edit_id)
        data = json.loads(request.body)
        if data.get("text") is not None:
            post_data.text = data["text"]
            post_data.save()
            return JsonResponse({"message": "Success"})


