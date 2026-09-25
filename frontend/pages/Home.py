import streamlit as st
import requests
from frontend.config import API_URL, GRADE_OPTIONS, grade_label

st.markdown('<div class="bookloop-kicker">A better way to find your next book</div>', unsafe_allow_html=True)
st.markdown('<h1>Find your <span style="color: #087f89;">next chapter.</span></h1>', unsafe_allow_html=True)
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

# Pull existing list from SQLite
try:
    books = requests.get(f"{API_URL}/books").json()
except Exception:
    books = []
    st.error("Could not reach backend server database feed.")

if not books:
    st.write("No active books found right now. Be the first to list one!")
else:
    st.markdown('<div class="bookloop-section-title"><h2>Shop by category</h2><span class="bookloop-pill">SAT · ACT · AP · School</span></div>', unsafe_allow_html=True)
    categories = st.columns(4)
    for category_col, title, subtitle in zip(categories, ["SAT Prep", "ACT Prep", "AP Books", "College Textbooks"], ["Practice smarter", "Reach your score", "Study with confidence", "Keep learning"]):
        with category_col:
            st.markdown(f'<div class="bookloop-card"><span class="bookloop-pill">{title}</span><h3>{subtitle}</h3><p style="color:#657083;">Browse available listings</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="bookloop-section-title"><h2>Latest listings</h2></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    idx = 0
    
    for book in books:
        searchable_text = f'{book.get("title", "")} {book.get("author", "")} {book.get("target_class", "")}'.lower()
        if class_filter != "All" and book["target_class"] != class_filter:
            continue
        if search_term.strip().lower() not in searchable_text:
            continue

        with cols[idx % 3]:
            st.markdown('<div class="bookloop-card">', unsafe_allow_html=True)
            if book["image_url"]:
                st.image(f"{API_URL}/uploads/books/{book['image_url']}", use_container_width=True)
            else:
                st.markdown('<div style="height:180px; border-radius:10px; background:#e8f1f5; display:flex; align-items:center; justify-content:center; font-size:3rem;">📖</div>', unsafe_allow_html=True)
                
            st.subheader(book["title"])
            st.caption(f"{book['author']} · {grade_label(book['target_class'])}")
            st.markdown(f"**£{book['price']:.2f}**")
            
            if st.button("💬 Chat with Seller", key=f"chat_btn_{book['id']}"):
                if not st.session_state.get("token"):
                    st.warning("Please log in on the main Home application page to message this student.")
                else:
                    # Send a standardized initial greeting message to open up a chat connection channel
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    init_msg = f"Hi! Is your book '{book['title']}' still available for a face-to-face handoff at school?"
                    
                    res = requests.post(
                        f"{API_URL}/chat/send", 
                        headers=headers, 
                        params={"receiver_id": book["seller_id"], "book_id": book["id"], "message": init_msg}
                    )
                    
                    if res.status_code == 200:
                        st.success("✅ Chat stream opened! Head over to the Chat page in the sidebar to talk.")
                    else:
                        st.error("Failed to start conversation thread.")
            st.markdown('</div>', unsafe_allow_html=True)
        idx += 1

    if idx == 0:
        st.info("No books match those filters yet. Try another search or list the first one.")