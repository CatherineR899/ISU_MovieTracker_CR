import tomllib 
import streamlit as st
import sqlite3
import re
import requests
import random

TMDB_BASE_URL = "https://api.themoviedb.org/3"
tmdb_key = st.secrets["TMDB_API_KEY"]
watchmode_key = st.secrets["WATCHMODE_API_KEY"]

def execute_query(query, params=(), fetchone=False, fetchall=False):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        conn.commit()
        return None

# =========================
# DATABASE LAYER
# =========================

    # =========================
    # USER FUNCTIONS
    # =========================

def get_user(username):
    return execute_query(
        "SELECT * FROM users WHERE username = ?",
        (username,),
        fetchone=True
    )

def username_exists(username):
    result = execute_query(
        "SELECT * FROM users WHERE username = ?",
        (username,),
        fetchone=True
    )
    return result is not None

def add_user(username, password):
    execute_query(
        """
        INSERT INTO users (username, password)
        VALUES (?, ?)
        """,
        (username, password)
    )

def update_username(user_id, new_username):
    execute_query(
        """
        UPDATE users
        SET username = ?
        WHERE id = ?
        """,
        (new_username, user_id)
    )

def update_password(user_id, new_password):
    execute_query(
        """
        UPDATE users
        SET password = ?
        WHERE id = ?
        """,
        (new_password, user_id)
    )

def delete_account(user_id):
    execute_query(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    # =========================
    # MOVIE LIST FUNCTIONS
    # =========================

def get_watched_movies(user_id):
    movies = execute_query(
        "SELECT movie_id FROM watched_movies WHERE user_id = ?",
        (user_id,),
        fetchall=True
    )
    return [m[0] for m in movies]

def get_watchlist_movies(user_id):
    movies = execute_query(
        "SELECT movie_id FROM watchlist_movies WHERE user_id = ?",
        (user_id,),
        fetchall=True
    )
    return [m[0] for m in movies] if movies else []

    # =========================
    # CHECK FUNCTIONS
    # =========================

def movie_in_watched(user_id, movie_id):
    result = execute_query(
        """
        SELECT *
        FROM watched_movies
        WHERE user_id = ?
        AND movie_id = ?
        """,
        (user_id, movie_id),
        fetchone=True
    )
    return result is not None

def movie_in_watchlist(user_id, movie_id):
    result = execute_query(
        """
        SELECT 1
        FROM watchlist_movies
        WHERE user_id = ?
        AND movie_id = ?
        """,
        (user_id, movie_id),
        fetchone=True
    )
    return result is not None

    # =========================
    # REVIEW FUNCTIONS
    # =========================

def save_review(user_id, movie_id, rating, comment):
    execute_query(
        """
        DELETE FROM movie_reviews
        WHERE user_id = ?
        AND movie_id = ?
        """,
        (user_id, movie_id)
    )
    execute_query(
        """
        INSERT INTO movie_reviews
        (user_id, movie_id, rating, comment)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, movie_id, rating, comment)
    )


def get_review(user_id, movie_id):
    return execute_query(
        "SELECT rating, comment FROM movie_reviews WHERE user_id = ? AND movie_id = ?",
        (user_id, movie_id),
        fetchone=True
    )

# =========================
# API LAYER
# =========================

    # =========================
    # TMDB FUNCTIONS
    # =========================

@st.cache_data
def get_movie_details(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": tmdb_key
    }
    response = requests.get(url, params=params)
    return response.json()

@st.cache_data
def get_genres():
    url = f"{TMDB_BASE_URL}/genre/movie/list"
    return requests.get(url, params={"api_key": tmdb_key}).json()["genres"]

@st.cache_data(ttl=3600)
def discover_movies_by_genre(genre_id):
    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        "api_key": tmdb_key,
        "with_genres": genre_id,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 1000
    }
    response = requests.get(
        url,
        params=params
    )
    return response.json().get("results", [])

    # =========================
    # SEARCH & FILTER FUNCTIONS
    # =========================

def search_movies(query):
    url = f"{TMDB_BASE_URL}/search/movie"
    return requests.get(url, params={
        "api_key": tmdb_key,
        "query": query
    }).json().get("results", [])


def discover_by_genres(genre_ids):
    url = f"{TMDB_BASE_URL}/discover/movie"
    return requests.get(url, params={
        "api_key": tmdb_key,
        "with_genres": ",".join(map(str, genre_ids))
    }).json().get("results", [])

# =========================
# UI HELPERS
# =========================

def valid_password(password):
    if len(password) < 12 or len(password) > 20:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

def add_watched_movie(user_id, movie_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO watched_movies
        (user_id, movie_id)
        VALUES (?, ?)
        """,
        (user_id, movie_id)
    )
    cursor.execute(
        """
        DELETE FROM watchlist_movies
        WHERE user_id = ?
        AND movie_id = ?
        """,
        (user_id, movie_id)
    )
    conn.commit()
    conn.close()

def add_watchlist_movie(user_id, movie_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO watchlist_movies
        (user_id, movie_id)
        VALUES (?, ?)
        """,
        (user_id, movie_id)
    )
    conn.commit()
    conn.close()

@st.cache_data
def get_streaming_services(tmdb_movie_id):
    search_url = "https://api.watchmode.com/v1/search/"
    search_params = {
        "apiKey": watchmode_key,
        "search_field": "tmdb_movie_id",
        "search_value": tmdb_movie_id
    }
    search_response = requests.get(
        search_url,
        params=search_params
    )
    search_data = search_response.json()
    if not search_data.get("title_results"):
        return []
    watchmode_id = search_data["title_results"][0]["id"]
    details_url = f"https://api.watchmode.com/v1/title/{watchmode_id}/details/"
    details_params = {
        "apiKey": watchmode_key,
        "append_to_response": "sources"
    }
    details_response = requests.get(
        details_url,
        params=details_params
    )
    details_data = details_response.json()
    services = []
    for source in details_data.get("sources", []):
        name = source.get("name")
        if name and name not in services:
            services.append(name)
    return services

def display_movie_poster(movie, button_key):
    poster_url = (
        f"https://image.tmdb.org/t/p/w300"
        f"{movie['poster_path']}"
    )
    st.image(
        poster_url,
        use_container_width=True
    )
    if st.button(
        movie["title"],
        key=button_key
    ):
        st.session_state.selected_movie = movie["id"]
        st.rerun()

def display_movie_grid(
    movies,
    key_prefix
):
    cols = st.columns(5)
    for i, movie in enumerate(movies):
        with cols[i % 5]:
            display_movie_poster(
                movie,
                f"{key_prefix}_{movie['id']}"
            )

def remove_watched_movie(user_id, movie_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM watched_movies
        WHERE user_id = ?
        AND movie_id = ?
        """,
        (user_id, movie_id)
    )
    conn.commit()
    conn.close()

def remove_watchlist_movie(user_id, movie_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM watchlist_movies
        WHERE user_id = ?
        AND movie_id = ?
        """,
        (user_id, movie_id)
    )
    conn.commit()
    conn.close()

def get_favorite_genres(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT movie_id, rating
        FROM movie_reviews
        WHERE user_id = ?
    """, (user_id,))
    reviews = cursor.fetchall()
    conn.close()
    genre_scores = {}
    for movie_id, rating in reviews:
        movie = get_movie_details(movie_id)
        for genre in movie.get("genres", []):
            genre_name = genre["name"]
            if genre_name not in genre_scores:
                genre_scores[genre_name] = []
            genre_scores[genre_name].append(rating)
    if not genre_scores:
        return []
    averages = []
    for genre, ratings in genre_scores.items():
        avg = sum(ratings) / len(ratings)
        averages.append((genre, avg))
    averages.sort(
        key=lambda x: x[1],
        reverse=True
    )
    return [g[0] for g in averages[:3]]

def get_recommended_movies(user_id):
    favorite_genres = get_favorite_genres(user_id)
    if not favorite_genres:
        return []
    genres = get_genres()
    genre_map = {
        g["name"]: g["id"]
        for g in genres
    }
    watched = set(
        get_watched_movies(user_id)
    )
    watchlist = set(
        get_watchlist_movies(user_id)
    )
    excluded = watched.union(watchlist)
    recommendations = []
    for genre in favorite_genres:
        genre_id = genre_map.get(genre)
        if not genre_id:
            continue
        results = discover_movies_by_genre(genre_id)
        for movie in results:
            if movie["id"] not in excluded:
                recommendations.append(movie)
    unique_movies = {}
    for movie in recommendations:
        unique_movies[movie["id"]] = movie
    recommendations = list(
        unique_movies.values()
    )
    return recommendations[:10]

# =====================================
# SESSION STATE
# =====================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "screen" not in st.session_state:
    st.session_state.screen = "login"

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

if "previous_page" not in st.session_state:
    st.session_state.previous_page = "Home"

# =====================================
# LOGIN
# =====================================

PASSWORD_REQUIREMENTS = """
Password Requirements:

    • 12-20 characters

    • At least 1 uppercase letter

    • At least 1 lowercase letter

    • At least 1 number

    • At least 1 special character

"""

if not st.session_state.logged_in and st.session_state.screen == "login":
    st.title("Movie Tracker Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "" or password == "":
            st.error("Enter username and password")
        else:
            user = get_user(username)
            if user is None:
                st.error("Username does not exist")
            else:
                if password != user[2]:
                    st.error("Incorrect password")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.password = user[2]
                    st.rerun()
    if st.button("Create Account"):
        st.session_state.screen = "create_account"
        st.rerun()

# =====================================
# CREATE ACCOUNT
# =====================================

elif not st.session_state.logged_in and st.session_state.screen == "create_account":
    st.title("Create Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    st.caption(PASSWORD_REQUIREMENTS)
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Create Account"):
        if username == "" or password == "" or confirm_password == "":
            st.error("Fill all fields")
        elif username_exists(username):
            st.error("Username already exists")
        elif not valid_password(password):
            st.error("Password does not meet requirements")
        elif password != confirm_password:
            st.error("Passwords do not match")
        else:
            add_user(username, password)
            st.success("Account created")
            st.session_state.screen = "login"
            st.rerun()
    if st.button("Back to Login"):
        st.session_state.screen = "login"
        st.rerun()

# =====================================
# LOGGED IN APP
# =====================================

else:
    page = st.sidebar.radio(
        "Navigation",
        [
            "Home",
            "Search",
            "Have Watched",
            "Need To Watch",
            "Settings"
        ]
    )
    st.session_state.previous_page = page
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    if st.session_state.get("selected_movie") is not None:
        movie_id = st.session_state.selected_movie
        movie = get_movie_details(movie_id)
        poster_url = (
            f"https://image.tmdb.org/t/p/w500"
            f"{movie['poster_path']}"
        )
        st.title(movie["title"])
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(
                poster_url,
                use_container_width=True
            )
        with col2:
            st.subheader("Synopsis")
            st.write(movie["overview"])
            st.subheader("Rating")
            st.write(movie["vote_average"])
            st.subheader("Genres")
            genres = [
                g["name"]
                for g in movie["genres"]
            ]
            st.write(", ".join(genres))
            st.subheader("Streaming Services")
            services = get_streaming_services(movie_id)
            if services:
                st.write(", ".join(services))
            else:
                st.write("No streaming information available")
        watched = movie_in_watched(
            st.session_state.user_id,
            movie_id
        )
        watchlist = movie_in_watchlist(
            st.session_state.user_id,
            movie_id
        )
        if not watched:
            if st.button("Add To Have Watched"):
                add_watched_movie(
                    st.session_state.user_id,
                    movie_id
                )
                st.success("Added to Have Watched")
                st.rerun()
        if watched:
            if st.button("Remove From Have Watched"):
                remove_watched_movie(
                    st.session_state.user_id,
                    movie_id
                )
                st.success("Movie removed")
                st.rerun()
        if not watchlist:
            if st.button("Add To Need To Watch"):
                add_watchlist_movie(
                    st.session_state.user_id,
                    movie_id
                )
                st.success("Added to Need To Watch")
                st.rerun()
        if watchlist:
            if st.button("Remove From Need To Watch"):
                remove_watchlist_movie(
                    st.session_state.user_id,
                    movie_id
                )
                st.success("Movie removed")
                st.rerun()
        if watched:
            st.divider()
            st.subheader("Your Review")
            existing_review = get_review(
                st.session_state.user_id,
                movie_id
            )
            if existing_review:
                st.write(
                    f"Rating: {existing_review[0]}/5"
                )
                st.write(
                    existing_review[1]
                )
            with st.expander("Write Review"):
                rating = st.slider(
                    "Rating",
                    1,
                    5,
                    3
                )
                comment = st.text_area(
                    "Comment"
                )
                if st.button("Save Review"):
                    save_review(
                        st.session_state.user_id,
                        movie_id,
                        rating,
                        comment
                    )
                    st.success("Review Saved")
                    st.rerun()
        if st.button("Back To Previous Page"):
            st.session_state.selected_movie = None
            st.rerun()
        st.stop()

    # =========================
    # HOME
    # =========================

    if page == "Home":
        st.title("Home")
        st.write(
            f"Welcome {st.session_state.username}"
        )

        # ==================================
        # NEED TO WATCH REMINDERS
        # ==================================

        st.subheader(
            "Movies You Should Watch Next"
        )
        watchlist_movies = get_watchlist_movies(
            st.session_state.user_id
        )
        if watchlist_movies:
            selected_movies = random.sample(
                watchlist_movies,
                min(5, len(watchlist_movies))
            )
            cols = st.columns(5)
            for i, movie_id in enumerate(
                selected_movies
            ):
                movie = get_movie_details(movie_id)
                with cols[i % 5]:
                    display_movie_poster(
                        movie,
                        f"movie_{movie['id']}"
                    )
        else:
            st.write(
                "You currently have no movies in your Need To Watch list."
            )
        st.divider()

        # ==================================
        # RECOMMENDED MOVIES
        # ==================================

        st.subheader(
            "Recommended For You"
        )
        recommendations = get_recommended_movies(
            st.session_state.user_id
        )
        if recommendations:
            cols = st.columns(5)
            for i, movie in enumerate(
                recommendations[:10]
            ):
                if movie.get("poster_path"):
                    with cols[i % 5]:
                        display_movie_poster(
                            movie,
                            f"movie_{movie['id']}"
                        )
        else:
            st.write(
                """
                Rate some movies you've watched
                to receive personalized recommendations.
                """
            )

    # =========================
    # SEARCH
    # =========================

    elif page == "Search":
        st.title("Search Movies")
        # =========================
        # SESSION STATE
        # =========================
        if "show_filters" not in st.session_state:
            st.session_state.show_filters = False
        if "selected_genres" not in st.session_state:
            st.session_state.selected_genres = []
        if "search_results" not in st.session_state:
            st.session_state.search_results = None
        if "filter_results" not in st.session_state:
            st.session_state.filter_results = None

        # =========================
        # TMDB GENRES (cached)
        # =========================

        genres = get_genres()
        genre_names = [g["name"] for g in genres]
        genre_map = {g["name"]: g["id"] for g in genres}

        # =========================
        # SEARCH INPUT (INDEPENDENT)
        # =========================
        query = st.text_input("Search movies by name")
        if st.button("Search") and query:
            st.session_state.search_results = search_movies(query)
            st.session_state.filter_results = None  # reset filters

        # =========================
        # FILTER BUTTON
        # =========================
        if st.button("Filters"):
            st.session_state.show_filters = True

        # =========================
        # FILTER POPUP
        # =========================
        if st.session_state.show_filters:
            st.subheader("Filter Movies")
            selected = st.multiselect(
                "Select up to 3 genres",
                genre_names,
                max_selections=3
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Apply Filters"):
                    genre_ids = [genre_map[g] for g in selected]
                    st.session_state.filter_results = discover_by_genres(genre_ids)
                    st.session_state.search_results = None  # reset search
                    st.session_state.show_filters = False
                    st.rerun()
            with col2:
                if st.button("Close"):
                    st.session_state.show_filters = False
                    st.rerun()

        # =========================
        # CHOOSE WHAT TO DISPLAY
        # =========================
        if st.session_state.search_results is not None:
            results = st.session_state.search_results
        elif st.session_state.filter_results is not None:
            results = st.session_state.filter_results
        else:
            results = []

        # =========================
        # DISPLAY RESULTS
        # =========================
        if not results:
            st.write("No movies found")
        else:
            cols = st.columns(5)
            for i, movie in enumerate(results[:20]):
                if movie.get("poster_path"):
                    poster = f"https://image.tmdb.org/t/p/w300{movie['poster_path']}"
                    with cols[i % 5]:
                        st.image(poster, use_container_width=True)
                        if st.button(
                            movie["title"],
                            key=f"movie_{movie['id']}"
                        ):
                            st.session_state.previous_page = "Search"
                            st.session_state.selected_movie = movie["id"]
                            st.rerun()

    # =========================
    # WATCHED
    # =========================

    elif page == "Have Watched":
        st.title("Have Watched")
        movie_ids = get_watched_movies(
            st.session_state.user_id
        )
        movies = [
            get_movie_details(movie_id)
            for movie_id in movie_ids
        ]
        display_movie_grid(
            movies,
            "watched"
        )

    # =========================
    # WATCHLIST
    # =========================

    elif page == "Need To Watch":
        st.title("Need To Watch")
        movie_ids = get_watchlist_movies(
            st.session_state.user_id
        )
        movies = [
            get_movie_details(movie_id)
            for movie_id in movie_ids
        ]
        display_movie_grid(
            movies,
            "watchlist"
        )

    # =========================
    # SETTINGS
    # =========================

    elif page == "Settings":
        st.title("Settings")
        st.subheader("Account Information")
        st.write(f"Username: {st.session_state.username}")

        # -------------------------
        # EDIT USERNAME
        # -------------------------

        new_username = st.text_input("New Username")
        if st.button("Update Username"):
            if username_exists(new_username):
                st.error("Username already exists")
            else:
                update_username(
                    st.session_state.user_id,
                    new_username
                )
                st.session_state.username = new_username
                st.success("Username updated")
                st.rerun()
        st.divider()

        # -------------------------
        # PASSWORD VIEW + EDIT
        # -------------------------

        show_password = st.checkbox("Show Password")
        if show_password:
            st.write(f"Password: {st.session_state.password}")
        else:
            st.write("Password: ************")
        new_password = st.text_input("New Password", type="password")
        st.caption(PASSWORD_REQUIREMENTS)
        confirm_new_password = st.text_input("Confirm New Password", type="password")
        if st.button("Update Password"):
            if not valid_password(new_password):
                st.error("Password does not meet requirements")
            elif new_password != confirm_new_password:
                st.error("Passwords do not match")
            else:
                update_password(
                    st.session_state.user_id,
                    new_password
                )
                st.session_state.password = new_password
                st.success("Password updated")
                st.rerun()
        st.divider()

        # -------------------------
        # DELETE ACCOUNT
        # -------------------------

        if st.button("Delete Account"):
            delete_account(st.session_state.user_id)
            st.session_state.clear()
            st.success("Account deleted")
            st.rerun()