import os

import requests
import streamlit as st

from frontend.config import API_URL, book_image_url, grade_label


def response_error(response: requests.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return fallback
    if isinstance(payload, dict):
        return str(payload.get("detail", fallback))
    return fallback


st.page_link(
    os.path.join(os.path.dirname(__file__), "Home.py"),
    label="← Back to Listings",
)

book_id = st.session_state.get("selected_book_id")
try:
    book_id = int(book_id)
    if book_id < 1:
        raise ValueError
except (TypeError, ValueError):
    st.error("This book link is invalid. Return to listings and choose a book.")
    st.stop()

try:
    book_response = requests.get(f"{API_URL}/books/{book_id}", timeout=10)
except requests.RequestException as error:
    st.error(f"Could not load this listing: {error}")
    st.stop()

if not book_response.ok:
    st.error(response_error(book_response, "This listing is no longer available."))
    st.stop()

try:
    book = book_response.json()
    seller_id = int(book["seller_id"])
except (ValueError, KeyError, TypeError) as error:
    st.error(f"The listing returned invalid book details: {error}")
    st.stop()

try:
    seller_response = requests.get(
        f"{API_URL}/users/{seller_id}/profile",
        timeout=10,
    )
except requests.RequestException as error:
    st.error(f"Could not load seller details: {error}")
    st.stop()

if not seller_response.ok:
    st.error(response_error(seller_response, "Could not load seller details."))
    st.stop()

seller = seller_response.json()
image_url = book_image_url(book.get("image_url"))
image_column, details_column = st.columns([1, 1])

with image_column:
    if image_url:
        st.image(image_url, width="stretch")
    else:
        st.markdown(
            '<div aria-label="No book photo" style="display:grid;width:100%;'
            'aspect-ratio:1;place-items:center;background:#e8f1f5;'
            'font-size:1rem;">No photo</div>',
            unsafe_allow_html=True,
        )

with details_column:
    title = str(book.get("title", "Untitled"))
    st.title(title)
    st.write(f"**Author:** {book.get('author', 'Unknown')}")
    st.write(
        f"**Class / Course:** "
        f"{grade_label(str(book.get('target_class', 'Class 1')))}"
    )
    try:
        price = f"${float(book.get('price', 0)):.2f}"
    except (TypeError, ValueError):
        price = "Price unavailable"
    st.markdown(f"### {price}")
    st.write(f"**Seller:** {seller.get('username', 'Unknown')}")
    average_rating = seller.get("average_rating", 0)
    try:
        rating = f"{float(average_rating):.1f}"
    except (TypeError, ValueError):
        rating = "0.0"
    st.write(f"**Seller rating:** {rating} / 5")

    if st.session_state.get("user_id") == seller_id:
        st.info("This is your listing.")
    else:
        st.page_link(
            os.path.join(os.path.dirname(__file__), "Chat.py"),
            label="Chat with Seller",
            query_params={
                "book_id": str(book_id),
                "partner_id": str(seller_id),
            },
        )

st.divider()
st.subheader("Seller reviews")
reviews = seller.get("reviews", [])
if not reviews:
    st.info("This seller hasn't received any reviews yet.")
else:
    for review in reviews:
        st.markdown(
            f"**{review.get('reviewer_name', 'Zuvyo user')}** · "
            f"{review.get('rating', 0)} / 5 stars"
        )
        if review.get("comment"):
            st.write(review["comment"])
        st.divider()
