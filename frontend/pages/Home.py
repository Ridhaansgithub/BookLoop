import os

import requests
import streamlit as st

from frontend.config import API_URL, CATEGORY_OPTIONS, GRADE_OPTIONS, book_category, book_image_url, grade_label


st.markdown('<div class="bookloop-kicker">A better way to find your next book</div>', unsafe_allow_html=True)
st.markdown('<h1>Find your <span style="color: #000000;">next chapter.</span></h1>', unsafe_allow_html=True)
st.markdown('<p class="bookloop-intro">Affordable school books, passed from one student to the next.</p>', unsafe_allow_html=True)

search_col, filter_col = st.columns([2.4, 1])
with search_col:
    search_term = st.text_input("Search books", placeholder="Search by title, author, or subject...", label_visibility="collapsed")
with filter_col:
    class_filter = st.selectbox(
        "Filter by class",
        ["All", *GRADE_OPTIONS],
        format_func=lambda grade: "All grades" if grade == "All" else grade_label(grade),
        label_visibility="collapsed",
    )

try:
    books = requests.get(f"{API_URL}/books", timeout=10).json()
except requests.exceptions.RequestException as error:
    books = []
    st.error(f"Could not reach backend server database feed: {error}")

if not books:
    st.write("No active books found right now. Be the first to list one!")
else:
    st.markdown('<div class="bookloop-section-title"><h2>Shop by category</h2><span class="bookloop-pill">SAT · ACT · AP · School</span></div>', unsafe_allow_html=True)
    categories = st.columns(4)
    for category_col, title in zip(categories, CATEGORY_OPTIONS):
        with category_col:
            if st.button(title, key=f"category_{title}", use_container_width=True):
                st.session_state.selected_book_category = title

    selected_category = st.session_state.get("selected_book_category")
    if selected_category:
        st.caption(f"Showing category: {selected_category}")
        if st.button("Show all categories", key="clear_category_filter"):
            st.session_state.selected_book_category = None
            st.rerun()

    st.markdown('<div class="bookloop-section-title"><h2>Latest listings</h2></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    visible_books = []

    for book in books:
        searchable_text = f'{book.get("title", "")} {book.get("author", "")} {book.get("target_class", "")}'.lower()
        if class_filter != "All" and book["target_class"] != class_filter:
            continue
        if selected_category and book_category(book) != selected_category:
            continue
        if search_term.strip().lower() not in searchable_text:
            continue
        visible_books.append(book)

    for index, book in enumerate(visible_books):
        image_url = book_image_url(book.get("image_url"))
        title = str(book.get("title", "Untitled"))
        author = str(book.get("author", "Unknown"))
        target_class = grade_label(book.get("target_class", "Class 1"))
        try:
            price = f"${float(book.get('price', 0)):.2f}"
        except (TypeError, ValueError):
            price = "Price unavailable"

        with cols[index % len(cols)]:
            with st.container(border=True):
                if image_url:
                    st.image(image_url, width="stretch")
                else:
                    st.markdown(
                        '<div aria-label="No book photo" style="display:grid;width:100%;'
                        'aspect-ratio:4/3;place-items:center;background:#e8f1f5;'
                        'font-size:3rem;">📖</div>',
                        unsafe_allow_html=True,
                    )
                st.subheader(title)
                st.write(f"{author} · {target_class}")
                st.markdown(f"**{price}**")
                if st.button(
                    "View book",
                    key=f"view_book_{book['id']}",
                    width="stretch",
                ):
                    st.session_state.selected_book_id = int(book["id"])
                    st.switch_page(
                        os.path.join(os.path.dirname(__file__), "ProductDetail.py")
                    )

    if not visible_books:
        st.info("No books match those filters yet. Try another search or list the first one.")
