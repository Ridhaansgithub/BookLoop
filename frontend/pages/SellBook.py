import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.title("📚 Sell a Book")

if not st.session_state.get("token"):
    st.error("Please log in first.")
    st.stop()

with st.form("sell_book_form"):

    title = st.text_input("Book Title")
    author = st.text_input("Author")
    target_class = st.text_input("Class / Course")
    price = st.number_input("Price (£)", min_value=0.0)

    uploaded_file = st.file_uploader(
        "Upload Book Image (Optional)",
        type=["jpg", "jpeg", "png"]
    )

    submit = st.form_submit_button("📤 List Book")

if submit:

    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    data = {
        "title": title,
        "author": author,
        "target_class": target_class,
        "price": price
    }

    files = {}

    if uploaded_file is not None:
        files["image"] = (
            uploaded_file.name,
            uploaded_file,
            uploaded_file.type
        )

    response = requests.post(
        f"{API_URL}/books",
        headers=headers,
        data=data,
        files=files
    )

    if response.status_code in [200, 201]:
        st.success("✅ Book listed successfully!")
    else:
        st.error(response.text)