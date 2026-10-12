import streamlit as st
import requests
from frontend.config import API_URL, book_image_url

st.header("📋 Manage My Book Listings")

if not st.session_state.get("token"):
    st.error("🔒 Please log in first.")
    st.stop()

headers = {
    "Authorization": f"Bearer {st.session_state.token}"
}

try:
    response = requests.get(f"{API_URL}/books/me", headers=headers, timeout=10)

    if response.status_code != 200:
        st.error(
            f"Backend error ({response.status_code}): {response.text}"
        )
        st.stop()

    my_books = response.json()

    if not isinstance(my_books, list):
        st.error(f"Unexpected response: {my_books}")
        st.stop()

except requests.exceptions.Timeout:
    st.error("Request timed out while loading your listings. Please check that the backend is online.")
    st.stop()
except requests.exceptions.RequestException as e:
    st.error(f"Could not connect to backend: {e}")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error loading your listings: {e}")
    st.stop()

if len(my_books) == 0:
    st.info("You haven't listed any books yet.")
else:
    for book in my_books:
        with st.container():

            col1, col2, col3 = st.columns([1, 2, 1.5])

            with col1:
                image_url = book_image_url(book.get("image_url"))

                if image_url:
                    st.image(
                        image_url,
                        width=120,
                    )
                else:
                    st.markdown(
                        '<div style="width:120px; aspect-ratio:1; border-radius:10px; '
                        'background:#e8f1f5; display:flex; align-items:center; '
                        'justify-content:center; font-size:2rem;">📖</div>',
                        unsafe_allow_html=True,
                    )

                with st.expander("Replace book photo"):
                    replacement_image = st.file_uploader(
                        "Upload a replacement photo",
                        type=["jpg", "jpeg", "png"],
                        key=f"replacement_image_{book['id']}",
                    )
                    if st.button(
                        "Save photo",
                        key=f"save_photo_{book['id']}",
                        disabled=replacement_image is None,
                    ):
                        replacement_response = requests.put(
                            f"{API_URL}/books/{book['id']}/image",
                            headers=headers,
                            files={
                                "image": (
                                    replacement_image.name,
                                    replacement_image,
                                    replacement_image.type,
                                )
                            },
                            timeout=30,
                        )
                        if replacement_response.status_code == 200:
                            st.success("Book photo updated.")
                            st.rerun()
                        else:
                            st.error(replacement_response.text)

            with col2:
                st.subheader(book.get("title", "Untitled"))
                st.write(
                    f"**Author:** {book.get('author', 'Unknown')}"
                )
                st.write(
                    f"**Class:** {book.get('target_class', 'N/A')}"
                )
                st.write(
                    f"**Price:** ${float(book.get('price', 0)):.2f}"
                )
                st.write(
                    f"**Status:** {book.get('status', 'unknown').upper()}"
                )

            with col3:
                st.write("### Actions")

                if book.get("status") == "available":
                    buyer_username = st.text_input(
                        "Buyer username (optional)",
                        key=f"buyer_username_{book['id']}",
                    )
                    if st.button(
                        "🤝 Mark as Sold",
                        key=f"sold_{book['id']}",
                        use_container_width=True
                    ):
                        res = requests.put(
                            f"{API_URL}/books/{book['id']}/sold",
                            headers=headers,
                            params={"buyer_username": buyer_username.strip()}
                            if buyer_username.strip()
                            else None,
                        )

                        if res.status_code == 200:
                            st.success("Status updated.")
                            st.rerun()
                        else:
                            st.error(res.text)

                if st.button(
                    "🗑️ Delete Listing",
                    key=f"delete_{book['id']}",
                    use_container_width=True
                ):
                    res = requests.delete(
                        f"{API_URL}/books/{book['id']}",
                        headers=headers
                    )

                    if res.status_code == 200:
                        st.success("Listing deleted.")
                        st.rerun()
                    else:
                        st.error(res.text)

        st.divider()