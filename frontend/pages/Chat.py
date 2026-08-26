import streamlit as st
import requests
from frontend.config import API_URL

st.header("💬 BookLoop Chat Messenger")

if not st.session_state.get("token"):
    st.error("🔒 Please log in on the main app screen to access your conversations.")
else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    
    try:
        channels = requests.get(f"{API_URL}/chat/channels", headers=headers).json()
    except Exception:
        channels = []

    if not channels:
        st.info("No open chats yet. Visit the Marketplace page and click 'Chat with Seller' on a book!")
    else:
        options = [f"📚 {c['book_title']} (Classmate: {c['partner_name']})" for c in channels]
        selected_idx = st.selectbox("Select an Active Conversation Stream:", range(len(options)), format_func=lambda x: options[x])
        
        active_channel = channels[selected_idx]
        
        history = requests.get(
            f"{API_URL}/chat/history/{active_channel['book_id']}/{active_channel['partner_id']}", 
            headers=headers
        ).json()
        
        st.write("---")
        for msg in history:
            label = "🤝 **You**" if msg["sender_id"] == st.session_state.user_id else f"👤 **{active_channel['partner_name']}**"
            st.markdown(f"{label}: {msg['message']}")
            
        st.write("---")
        with st.form("reply_form", clear_on_submit=True):
            reply_text = st.text_input("Type your response here (Arrange cash swap locations at school)...")
            if st.form_submit_button("Send Message") and reply_text.strip():
                res = requests.post(
                    f"{API_URL}/chat/send", 
                    headers=headers, 
                    params={"receiver_id": active_channel["partner_id"], "book_id": active_channel["book_id"], "message": reply_text}
                )
                if res.status_code == 200:
                    st.rerun()