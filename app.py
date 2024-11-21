from flask import Flask, request, render_template, Response, json
import requests
import math

app = Flask(__name__)

# Base API URL
API_URL = "https://www.myanonamouse.net/tor/js/loadSearchJSONbasic.php"

# Initial session cookie (replace with your actual values)
session_cookies = {
    "mam_id": "_zXN0MpPPSXWWgMlJ0YLHvPUq9FRh56DRrciTUY908x85dl--29svP04D2mYQuAVDYj8IMWJMRF8ZUrHL9EWUHf5K96jotpO4Oirre13mhtWRS3iVJzXXp4AwgIuQ3r4uXIkNF56Rkffep9deKOGMMouNQqEaNGC_unaDHNj-utOM8uLPxVJtnXhNvIKdFoBaZuIPK-s9N_ZVwopt-dcRpdnhpQcxXx5K7zQVDq9PXuuU6kuXW8SDeLYkn2UvfgyYZwC4Hxgy1IcK8D6Ze1sYmgmkKSfVjCgwmEH",
    "uid": "221118",
}


def update_cookies(response):
    """Extract and update cookies from the API response."""
    global session_cookies
    if "set-cookie" in response.headers:
        # Parse and update the cookies
        cookies = response.cookies.get_dict()
        session_cookies.update(cookies)


@app.route("/", methods=["GET", "POST"])
def search():
    # Get search parameters from the form
    search_query = request.args.get("query", "")
    search_in_title = request.args.get("search_in_title", "off") == "on"
    search_in_author = request.args.get("search_in_author", "off") == "on"
    search_in_narrator = request.args.get("search_in_narrator", "off") == "on"
    media_type = request.args.get("media_type", "all")
    page = int(request.args.get("page", 1))
    per_page = 10
    start_number = (page - 1) * per_page

    # Prepare API parameters
    params = {
        "tor[text]": search_query,
        "tor[sortType]": "default",
        "tor[startNumber]": start_number,
        "perpage": per_page,
        "thumbnail": "true",  # Always include thumbnails
    }

    # Add search_in parameters
    params["tor[srchIn][title]"] = search_in_title
    params["tor[srchIn][author]"] = search_in_author
    params["tor[srchIn][narrator]"] = search_in_narrator

    # Add media type filter
    if media_type != "all":
        params["tor[main_cat][]"] = media_type

    # Prepare headers with cookies
    headers = {
        "Cookie": "; ".join([f"{k}={v}" for k, v in session_cookies.items()])
    }

    # Make API request
    if search_query:
        response = requests.get(API_URL, headers=headers, params=params)
        
        # Update cookies from the API response
        update_cookies(response)
        
        if response.status_code == 200:
            results = response.json()
            total_results = results.get("total", 0)
            total_pages = math.ceil(total_results / per_page)
            data = results.get("data", [])

            # Parse and clean author_info for each result
            for item in data:
                item["author_info"] = parse_author_info(item.get("author_info", ""))
        else:
            total_results = 0
            total_pages = 0
            data = []
    else:
        total_results = 0
        total_pages = 0
        data = []

    return render_template(
        "index.html",
        query=search_query,
        search_in_title=search_in_title,
        search_in_author=search_in_author,
        search_in_narrator=search_in_narrator,
        media_type=media_type,
        results=data,
        page=page,
        total_pages=total_pages,
    )

def parse_author_info(author_info):
    """Extract and return only the author's names from author_info."""
    try:
        # Convert the JSON string into a Python dictionary
        authors = json.loads(author_info)
        # Join all author names into a single string (e.g., "Author1, Author2")
        return ", ".join(authors.values())
    except (json.JSONDecodeError, TypeError):
        # If parsing fails or the field is empty, return "Unknown Author"
        return "Unknown Author"

@app.route("/proxy_thumbnail")
def proxy_thumbnail():
    """Proxy thumbnails to bypass cookie or CORS issues."""
    url = request.args.get("url")
    if not url:
        return "No URL provided", 400
    headers = {"Cookie": "; ".join([f"{k}={v}" for k, v in session_cookies.items()])}
    response = requests.get(url, headers=headers, stream=True)
    return Response(response.content, content_type=response.headers.get("Content-Type"))


if __name__ == "__main__":
    app.run(debug=True)