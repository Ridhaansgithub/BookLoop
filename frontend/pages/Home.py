from html import escape

import requests
import streamlit as st

from frontend.config import API_URL, CATEGORY_OPTIONS, GRADE_OPTIONS, book_category, grade_label

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
        image_url = book.get("image_url")
        image_markup = (
            f'<img src="{escape(API_URL)}/uploads/books/{escape(str(image_url))}" '
            'alt="Book cover" '
            'style="display:block;width:100%;height:100%;object-fit:cover;" />'
            if image_url
            else '<div aria-label="No book photo" style="display:grid;width:100%;'
            'height:100%;place-items:center;background:#e8f1f5;font-size:3rem;">📖</div>'
        )
        title = escape(str(book.get("title", "Untitled")))
        author = escape(str(book.get("author", "Unknown")))
        target_class = escape(grade_label(book.get("target_class", "Class 1")))
        try:
            price = f"${float(book.get('price', 0)):.2f}"
        except (TypeError, ValueError):
            price = "Price unavailable"

        with cols[index % len(cols)]:
            st.markdown(
                f'<a class="bookloop-listing-card" href="{escape(API_URL)}/book/{int(book["id"])}" '
                'style="display:block;height:100%;overflow:hidden;color:#0f172a;'
                'background:#fff;border:1px solid #dfe7ec;border-radius:14px;'
                'box-shadow:0 8px 24px rgba(16,28,59,.08);text-decoration:none;'
                'transition:transform .15s ease,box-shadow .15s ease;">'
                f'<div style="width:100%;aspect-ratio:4/3;max-height:260px;'
                f'overflow:hidden;background:#e8f1f5;">'
                f'{image_markup}</div>'
                '<div style="padding:1rem 1.1rem 1.1rem;">'
                f'<h3 style="margin:0 0 .4rem;font-size:1.15rem;line-height:1.3;'
                f'color:#0f172a;overflow-wrap:anywhere;">{title}</h3>'
                f'<p style="margin:0 0 .85rem;color:#53657a;font-size:.95rem;">'
                f'{author} · {target_class}</p>'
                f'<strong style="font-size:1.05rem;color:#0f172a;">{price}</strong>'
                '</div></a>',
                unsafe_allow_html=True,
            )

    if not visible_books:
        st.info("No books match those filters yet. Try another search or list the first one.")
