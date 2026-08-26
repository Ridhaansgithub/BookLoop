import streamlit as st
import requests
from frontend.config import API_URL, GRADE_OPTIONS, grade_label

st.header("🎒 School Books Marketplace")

# Pull existing list from SQLite
try:
    books = requests.get(f"{API_URL}/books").json()
except Exception:
    books = []
    st.error("Could not reach backend server database feed.")

if not books:
    st.write("No active books found right now. Be the first to list one!")
else:
    class_filter = st.selectbox(
        "Filter by Class/Year requirements:",
        ["All", *GRADE_OPTIONS],
        format_func=lambda grade: "All Grades" if grade == "All" else grade_label(grade),
    )
    
    cols = st.columns(3)
    idx = 0
    
    for book in books:
        if class_filter != "All" and book["target_class"] != class_filter:
            continue

        with cols[idx % 3]:
            st.write("---")
            if book["image_url"]:
                st.image(f"{API_URL}/uploads/books/{book['image_url']}", use_container_width=True)
            else:
                st.image("https://via.placeholder.com/150", caption="No Image Provided", use_container_width=True)
                
            st.subheader(book["title"])
            st.caption(f"By {book['author']} | Target: {book['target_class']}")
            st.markdown(f"### 🪙 Price: £{book['price']:.2f}")
            
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
        idx += 1