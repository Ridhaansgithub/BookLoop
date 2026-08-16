import streamlit as st

st.header("🔑 Account Management")

if st.session_state.get("token"):
    st.success(f"🔒 Authenticated as: **{st.session_state.username}**")
    st.write(f"Your internal User ID is **{st.session_state.user_id}**.")
    st.info("If you want to view profiles, browse books, or access your chats, use the sidebar links to navigate.")
else:
    st.warning("⚠️ You are not logged in yet.")
    st.info("Please head over to the main **app.py** homepage using the sidebar link to securely sign in or register your student account.")
    
    