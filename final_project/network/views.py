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
    #     iframe = folium.IFrame(html=markers.iloc[i]['popup'], width=500, height=250)
    #     #Initialise the popup using the iframe
    #     popup = folium.Popup(iframe, max_width=500)


    #     folium.Marker(
    #         location=[markers.iloc[i]['latitude'], markers.iloc[i]['longitude']],
    #         popup=popup,
    #         icon=folium.Icon(color='red', icon='')
    #     ).add_to(map_)

    popup_1 = """
    <style>
    body {
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
    }
    .popup-content {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .popup-content img {
        width: 100%;
        height: 40%;
        object-fit: cover;
        margin-bottom: 10px;
    }
    .popup-content h2 {
        margin: 0 0 10px 0;
        font-size: 14px;
        color: blue;
        text-decoration: underline;
    }
    .popup-content p {
        font-size: 12px;
        line-height: 1.3;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
    }
    </style>

    <div class="popup-content">
        <img src="data:image/jpeg;base64,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" alt="News Image">
        <h2><a href="https://www.cbsnews.com/news/gm-carbon-emissions-epa-climate-change/">Local Factory Under Investigation for Excessive CO2 Emissions</a></h2>
        <p>Authorities are investigating a factory after reports of thick smoke and strong odors,
          suspecting CO2 emissions far above legal limits.
        </p>
    </div>

    """
    #Setup the content of the popup
    iframe = folium.IFrame(html=popup_1, width=300, height=200)
    #Initialise the popup using the iframe
    popup = folium.Popup(iframe, max_width=300)


    folium.Marker(
        location=[37.141064, -121.888334],
        popup=popup,
        icon=folium.Icon(color='red', icon='')
    ).add_to(map_)

    popup_2 = """
    <style>
    body {
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
    }
    .popup-content {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .popup-content img {
        width: 100%;
        height: 40%;
        object-fit: cover;
        margin-bottom: 10px;
    }
    .popup-content h2 {
        margin: 0 0 10px 0;
        font-size: 14px;
        color: blue;
        text-decoration: underline;
    }
    .popup-content p {
        font-size: 12px;
        line-height: 1.3;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
    }
    </style>

    <div class="popup-content">
        <img src="https://www.euractiv.com/wp-content/uploads/sites/2/2024/10/shutterstock_1975421474-800x450.jpg" alt="News Image">
        <h2><a href="https://www.euractiv.com/section/economy-jobs/news/italys-largest-lobby-group-to-push-for-eu-policy-u-turn-on-co2-emission-trading-system/">Residents Alert Authorities to Unusual Emissions from Chemical Plant</a></h2>
        <p>Community members near a chemical plant reported seeing dense clouds of smoke and experiencing respiratory discomfort.
          Upon investigation, officials discovered a malfunction in the plant’s filtration system, which had led to an unregulated release of greenhouse gases into the atmosphere.
        </p>
    </div>
    """
    #Setup the content of the popup
    iframe = folium.IFrame(html=popup_2, width=300, height=200)
    #Initialise the popup using the iframe
    popup = folium.Popup(iframe, max_width=300)


    folium.Marker(
        location=[37.339561, -121.807379],
        popup=popup,
        icon=folium.Icon(color='red', icon='')
    ).add_to(map_)


    popup_3 = """
    <style>
    body {
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
    }
    .popup-content {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .popup-content img {
        width: 100%;
        height: 40%;
        object-fit: cover;
        margin-bottom: 10px;
    }
    .popup-content h2 {
        margin: 0 0 10px 0;
        font-size: 14px;
        color: blue;
        text-decoration: underline;
    }
    .popup-content p {
        font-size: 12px;
        line-height: 1.3;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
    }
    </style>

    <div class="popup-content">
        <img src="https://cnt.org/sites/default/files/styles/main_content_image/public/TCRP-cover-graphic-900px.png?itok=hytuZad3" alt="News Image">
        <h2><a href="https://cnt.org/blog/public-transportations-impacts-on-greenhouse-gas-emissions">City's Public Transportation Fleet Reports Record Drop in Emissions</a></h2>
        <p>The city’s newly upgraded electric bus fleet has reduced CO2 emissions by 30% over the past quarter, according to a report from the Department of Transportation.
          Officials credit the shift to electric vehicles as part of the city’s broader effort to curb its carbon footprint.
        </p>
    </div>
    """
    #Setup the content of the popup
    iframe = folium.IFrame(html=popup_3, width=300, height=200)
    #Initialise the popup using the iframe
    popup = folium.Popup(iframe, max_width=300)


    folium.Marker(
        location=[37.425800, -121.809924],
        popup=popup,
        icon=folium.Icon(color='red', icon='')
    ).add_to(map_)

    popup_4 = """
    <style>
    body {
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
    }
    .popup-content {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .popup-content img {
        width: 100%;
        height: 40%;
        object-fit: cover;
        margin-bottom: 10px;
    }
    .popup-content h2 {
        margin: 0 0 10px 0;
        font-size: 14px;
        color: blue;
        text-decoration: underline;
    }
    .popup-content p {
        font-size: 12px;
        line-height: 1.3;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
    }
    </style>

    <div class="popup-content">
        <img src="https://assets1.cbsnewsstatic.com/hub/i/r/2024/07/26/89bc4037-7196-4184-b51d-72c640d2d7f8/thumbnail/620x413/97ca0e9c016ea20e2f517d6d24782fc6/2024-07-26t205123z-1683988901-rc2839aq4qon-rtrmadp-3-usa-wildfires.jpg?v=0736ad3ef1e9ddfe1218648fe91d6c9b" alt="News Image">
        <h2><a href="https://www.cbsnews.com/news/park-fire-northern-california-explodes-hell-on-earth/">Wildfire in Northern Hills Causes Spike in Carbon Emissions</a></h2>
        <p>A wildfire that broke out in the Northern Hills region has burned through over 500 acres of forest, leading to a significant increase in CO2 emissions.
          Firefighters are working to contain the blaze, while local air quality monitors have reported elevated levels of greenhouse gases in nearby communities.
        </p>
    </div>
    """
    #Setup the content of the popup
    iframe = folium.IFrame(html=popup_4, width=300, height=200)
    #Initialise the popup using the iframe
    popup = folium.Popup(iframe, max_width=300)


    folium.Marker(
        location=[37.397600, -122.312485],
        popup=popup,
        icon=folium.Icon(color='red', icon='')
    ).add_to(map_)

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
            genai.configure(api_key='AIzaSyAKIuj0Kz-76o5Nl8zTxuG1nHpWDR5PKJQ')

            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"""
                        Process the information below and give me 3 things. Each value should be on a new line and the value itself, no other text.
                        The first piece of information is give the latitude of where this is happening in the {country}.
                        Second piece of information is the longitude of where this is happening in {country}.
                        Third information is generate HTML code to showcase the news report as a popup.
                        I want the very top of popup to have a urlToImage. The dimension of it should be 200x100 which is width x height. Then, the title should have a hyperlink to the news article,
                        and finally a quick 1-2 sentence summary of what happened in relation to CO2 emissions.
                        {json_string}
            
            """)
            response_lines = response.text.strip().split("\n")
            print(response_lines)
            # Extract each value (assuming the format will always have three lines)
            latitude_str = response_lines[0].strip()   # First line is latitude
            longitude_str = response_lines[1].strip() # Second line is longitude

            # Check if the first character is a hyphen for latitude
            if latitude_str.startswith('-'):
                latitude = (-1) * float(latitude_str[1:])  # Remove the hyphen and convert the rest to float, make it negative
            else:
                latitude = float(latitude_str)  # Convert to float as is for positive values

            # Check if the first character is a hyphen for longitude
            if longitude_str.startswith('-'):
                longitude = (-1) * float(longitude_str[1:])  # Remove the hyphen and convert the rest to float, make it negative
            else:
                longitude = float(longitude_str)  # Convert to float as is for positive values

            html_popup = "\n".join(response_lines[2:]).strip()  # Remaining lines form the HTML code
            # print(f"Latitude: {latitude}")
            # print(f"Longitude: {longitude}")
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


