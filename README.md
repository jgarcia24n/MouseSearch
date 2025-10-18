# MouseSearch

MouseSearch is a web-based search utility for MyAnonamouse (MAM) that allows you to search for torrents and send them directly to your qBittorrent client.

## Features

-   **Advanced Search**: Search for audiobooks, e-books, and other media on MyAnonamouse with filters for title, author, narrator, media type, and language.
-   **qBittorrent Integration**: Add torrents directly to your qBittorrent client from the search results.
-   **Result Ranking**: Search results are intelligently ranked based on file type and the number of seeders to help you find the best torrents.
-   **Dynamic IP Updater**: Automatically checks and updates your dynamic seedbox IP address with the MyAnonamouse tracker.
-   **Status Dashboard**: View your MyAnonamouse user stats (ratio, upload, download, bonus points) and qBittorrent connection status at a glance.
-   **Easy Configuration**: All settings can be managed through a simple web interface.

## Getting Started

### Prerequisites

-   Docker
-   A MyAnonamouse account
-   A qBittorrent instance

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/mousesearch.git](https://github.com/your-username/mousesearch.git)
    cd mousesearch
    ```

2.  **Run with Docker:**
    The application is containerized for easy setup.
    ```bash
    docker build -t mousesearch .
    docker run -d -p 5000:5000 --name mousesearch mousesearch
    ```
    The application will be accessible at [http://localhost:5000](http://localhost:5000).

## Configuration

All configuration can be done through the web interface. Click the settings icon in the top right corner to open the configuration panel.

You will need to provide the following information:

-   **qBittorrent:**
    -   URL
    -   Username
    -   Password
    -   Default Category (optional)
-   **MyAnonamouse:**
    -   MAM ID (your `mam_id` cookie)

The application uses the following environment variables, which can be set in a `.env` file or directly in your Docker run command:

-   `FLASK_SECRET_KEY`: A secret key for the Flask application.
-   `MAM_API_URL`: The URL for the MyAnonamouse API (defaults to `https://www.myanonamouse.net`).
-   `QB_URL`: URL for your qBittorrent instance.
-   `QB_CATEGORY`: Default category for torrents added to qBittorrent.
-   `QB_USERNAME`: qBittorrent username.
-   `QB_PASSWORD`: qBittorrent password.
-   `MAM_ID`: Your `mam_id` cookie from MyAnonamouse.
-   `MAM_UID`: Your `uid` cookie from MyAnonamouse (this can be fetched automatically if `MAM_ID` is provided).
-   `CF_ACCESS_CLIENT_ID`: (Optional) Cloudflare Access Client ID.
-   `CF_ACCESS_CLIENT_SECRET`: (Optional) Cloudflare Access Client Secret.

## Usage

1.  Navigate to the application in your web browser.
2.  Open the settings panel and configure your qBittorrent and MyAnonamouse credentials.
3.  Use the main search form to find content.
4.  From the results list, click the download icon to send a torrent to qBittorrent.

## Project Structure

-   `app.py`: The main Flask application file containing all routes and logic.
-   `Dockerfile`: Defines the Docker container for the application.
-   `requirements.txt`: A list of Python dependencies for the project.
-   `templates/`: Contains the HTML templates for the web interface.
-   `static/`: Contains static assets like CSS and JavaScript.