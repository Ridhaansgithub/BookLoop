import streamlit as st
import requests
from frontend.config import API_URL


def expire_session() -> None:
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.auth_session_expired = True
    st.rerun()


st.header("Zuvyo Chat Messenger")

if not st.session_state.get("token"):
    st.error("Please log in on the main app screen to access your conversations.")
else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    book_id_param = st.query_params.get("book_id")
    partner_id_param = st.query_params.get("partner_id")
    if book_id_param is not None or partner_id_param is not None:
        if "book_id" in st.query_params:
            del st.query_params["book_id"]
        if "partner_id" in st.query_params:
            del st.query_params["partner_id"]

        try:
            book_id = int(book_id_param)
            partner_id = int(partner_id_param)
            if book_id < 1 or partner_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            st.error("This chat link is invalid. Return to the listing and try again.")
            st.stop()

        try:
            history_response = requests.get(
                f"{API_URL}/chat/history/{book_id}/{partner_id}",
                headers=headers,
                timeout=10,
            )
            if history_response.status_code == 401:
                expire_session()
            if not history_response.ok:
                raise requests.HTTPError(
                    f"Could not load the conversation ({history_response.status_code})."
                )
            history = history_response.json()
            if not history:
                start_response = requests.post(
                    f"{API_URL}/chat/send",
                    headers=headers,
                    params={
                        "receiver_id": partner_id,
                        "book_id": book_id,
                        "message": (
                            "Hi! I'm interested in this book. Is it still "
                            "available for a handoff at school?"
                        ),
                    },
                    timeout=10,
                )
                if start_response.status_code == 401:
                    expire_session()
                if not start_response.ok:
                    raise requests.HTTPError(
                        f"Could not start the conversation ({start_response.status_code})."
                    )
            st.session_state.chat_context = (book_id, partner_id)
        except (requests.RequestException, ValueError) as error:
            st.error(f"Could not open this conversation: {error}")
            st.stop()
    
    try:
        response = requests.get(f"{API_URL}/chat/channels", headers=headers, timeout=10)
        if response.status_code == 401:
            expire_session()
        if not response.ok:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {}
            detail = error_payload.get("detail", response.text) if isinstance(error_payload, dict) else response.text
            raise requests.HTTPError(f"Chat service error ({response.status_code}): {detail}")
        channels = response.json()
        if not isinstance(channels, list) or any(not isinstance(channel, dict) for channel in channels):
            raise ValueError("The chat service returned an invalid conversation list.")
    except (requests.RequestException, ValueError) as error:
        st.error(f"Could not load your conversations: {error}")
        st.stop()

    if not channels:
        st.info("No open chats yet. Open a book listing and select 'Chat with Seller' on its details page.")
    else:
        options = [f"{c['book_title']} (Classmate: {c['partner_name']})" for c in channels]
        chat_context = st.session_state.pop("chat_context", None)
        if chat_context:
            context_book_id, context_partner_id = chat_context
            preferred_index = next(
                (
                    index
                    for index, channel in enumerate(channels)
                    if channel.get("book_id") == context_book_id
                    and channel.get("partner_id") == context_partner_id
                ),
                0,
            )
            st.session_state.active_chat_index = preferred_index

        selected_idx = st.selectbox(
            "Select an Active Conversation Stream:",
            range(len(options)),
            index=st.session_state.get("active_chat_index", 0),
            format_func=lambda x: options[x],
            key="active_chat_index",
        )
        
        active_channel = channels[selected_idx]
        
        history_response = requests.get(
            f"{API_URL}/chat/history/{active_channel['book_id']}/{active_channel['partner_id']}", 
            headers=headers,
            timeout=10,
        )
        if history_response.status_code == 401:
            expire_session()
        if not history_response.ok:
            st.error(f"Could not load this conversation ({history_response.status_code}).")
            st.stop()
        history = history_response.json()
        
        st.write("---")
        for msg in history:
            label = "**You**" if msg["sender_id"] == st.session_state.user_id else f"**{active_channel['partner_name']}**"
            st.markdown(f"{label}: {msg['message']}")
            
        st.write("---")
        with st.form("reply_form", clear_on_submit=True):
            reply_text = st.text_input("Type your response here (Arrange cash swap locations at school)...")
            if st.form_submit_button("Send Message") and reply_text.strip():
                res = requests.post(
                    f"{API_URL}/chat/send", 
                    headers=headers, 
                    params={"receiver_id": active_channel["partner_id"], "book_id": active_channel["book_id"], "message": reply_text},
                    timeout=10,
                )
                if res.status_code == 401:
                    expire_session()
                if res.status_code == 200:
                    st.rerun()