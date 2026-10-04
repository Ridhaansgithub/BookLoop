import streamlit as st
import requests
from frontend.config import API_URL

st.header("👤 School Profiles & Trust Ratings")

if not st.session_state.get("token"):
    st.error("🔒 Please log in on the main screen to access profiles.")
else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    tab1, tab2, tab3 = st.tabs(["My Profile Card", "⭐ Leave a Swap Review", "Classmate Book Counts"])
    
    with tab1:
        try:
            profile = requests.get(f"{API_URL}/users/{st.session_state.user_id}/profile").json()
            st.subheader(f"Username: {profile['username']} (User ID: {st.session_state.user_id})")
            st.write(f"🎒 **Registered Class/Year:** {profile['school_class']}")
            st.markdown(f"### ⭐ Classmate Trust Score: **{profile['average_rating']} / 5.0**")
            count_col1, count_col2, count_col3 = st.columns(3)
            count_col1.metric("Listed", profile["books_listed"])
            count_col2.metric("Sold", profile["books_sold"])
            count_col3.metric("Bought", profile["books_bought"])
            
            st.write("---")
            st.markdown("### 📝 Recent Feedback History")
            if not profile["reviews"]:
                st.info("No reviews received yet. Swap books face-to-face to build up your score!")
            else:
                for r in profile["reviews"]:
                    st.markdown(f"**{r['reviewer_name']}** rated you `{r['rating']} Stars`")
                    if r['comment']:
                        st.caption(f'"{r["comment"]}"')
                    st.write("")
        except Exception:
            st.error("Could not fetch profile details.")
            
    with tab2:
        st.subheader("Rate a Classmate")
        st.write("Successfully completed a face-to-face swap? Leave your classmate a review!")
        
        target_uid = st.number_input("Enter their User ID:", min_value=1, step=1)
        score = st.slider("Select Rating:", min_value=1, max_value=5, value=5)
        notes = st.text_area("Add a comment (e.g., 'Book was in perfect condition, super nice transaction!'):")
        
        if st.button("Submit Feedback"):
            if not target_uid:
                st.error("Please enter a valid User ID.")
            else:
                res = requests.post(
                    f"{API_URL}/reviews", 
                    headers=headers, 
                    params={"reviewed_user_id": target_uid, "rating": score, "comment": notes}
                )
                if res.status_code == 200:
                    st.success("Thank you! Feedback submitted safely to their profile card.")
                else:
                    st.error(res.json().get("detail", "Failed to submit review."))

    with tab3:
        st.subheader("View a classmate's book activity")
        target_profile_id = st.number_input("User ID", min_value=1, step=1, key="count_profile_id")
        if st.button("View book counts"):
            response = requests.get(f"{API_URL}/users/{int(target_profile_id)}/profile", timeout=10)
            if response.status_code == 200:
                viewed_profile = response.json()
                class_name = viewed_profile["school_class"] or "Class not provided"
                st.write(f"**{viewed_profile['username']}** · {class_name}")
                count_col1, count_col2, count_col3 = st.columns(3)
                count_col1.metric("Listed", viewed_profile["books_listed"])
                count_col2.metric("Sold", viewed_profile["books_sold"])
                count_col3.metric("Bought", viewed_profile["books_bought"])
            else:
                st.error(response.json().get("detail", "Could not load this profile."))