import os

import requests
import streamlit as st

from frontend.config import API_URL, grade_label


def error_detail(response: requests.Response, fallback: str) -> str:
    try:
        return str(response.json().get("detail", fallback))
    except (ValueError, AttributeError):
        return fallback


st.page_link(
    os.path.join(os.path.dirname(__file__), "Home.py"),
    label="← Back to Home",
)
st.title("Book details")

book_id_text = st.query_params.get("book_id", "")
try:
    book_id = int(book_id_text)
    if book_id < 1:
        raise ValueError
except (TypeError, ValueError):
    st.error("This book link is invalid. Return to Home and choose a listing.")
    st.stop()

try:
    book_response = requests.get(f"{API_URL}/books/{book_id}", timeout=10)
except requests.exceptions.RequestException as error:
    st.error(f"Could not load this listing: {error}")
    st.stop()

if book_response.status_code != 200:
    st.error(error_detail(book_response, "This listing is no longer available."))
    st.stop()

book = book_response.json()
try:
    seller_response = requests.get(
        f"{API_URL}/users/{int(book['seller_id'])}/profile",
        timeout=10,
    )
except (requests.exceptions.RequestException, KeyError, TypeError, ValueError) as error:
    st.error(f"Could not load seller details: {error}")
    st.stop()

if seller_response.status_code != 200:
    st.error(error_detail(seller_response, "Could not load seller details."))
    st.stop()

seller = seller_response.json()
image_column, details_column = st.columns([1, 1])
with image_column:
    if book.get("image_url"):
        st.image(
            f"{API_URL}/uploads/books/{book['image_url']}",
            use_container_width=True,
        )
    else:
        st.markdown(
            '<div class="bookloop-product-placeholder" aria-label="No book photo">📖</div>',
            unsafe_allow_html=True,
        )

with details_column:
    st.subheader(book.get("title", "Untitled"))
    st.write(f"**Author:** {book.get('author', 'Unknown')}")
    st.write(f"**Class / Course:** {grade_label(book.get('target_class', 'Class 1'))}")
    st.markdown(f"### ${float(book.get('price', 0)):.2f}")
    st.write(f"**Seller:** {seller.get('username', 'Unknown')}")

    if st.button("💬 Chat with Seller", key=f"pdp_chat_{book_id}"):
        token = st.session_state.get("token")
        if not token:
            st.error("Please log in to message the seller.")
        else:
            try:
                chat_response = requests.post(
                    f"{API_URL}/chat/send",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "receiver_id": book["seller_id"],
                        "book_id": book_id,
                        "message": (
                            f"Hi! Is your book '{book.get('title', 'book')}' still "
                            "available for a face-to-face handoff at school?"
                        ),
                    },
                    timeout=10,
                )
            except requests.exceptions.RequestException as error:
                st.error(f"Could not start a conversation: {error}")
            else:
                if chat_response.status_code == 200:
                    st.success("Chat started. Open Chat in the sidebar to continue.")
                else:
                    st.error(error_detail(chat_response, "Failed to start conversation."))

st.divider()
st.subheader("Seller reviews")
reviews = seller.get("reviews", [])
if not reviews:
    st.info("This seller hasn't received any reviews yet.")
else:
    for review in reviews:
        st.markdown(
            f"**{review.get('reviewer_name', 'BookLoop user')}** · "
            f"{review.get('rating', 0)} / 5 stars"
        )
        if review.get("comment"):
            st.write(review["comment"])
        st.divider()
