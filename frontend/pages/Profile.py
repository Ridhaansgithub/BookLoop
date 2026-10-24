from urllib.parse import quote

import streamlit as st
import requests
from frontend.config import API_URL

st.header("School Profiles & Trust Ratings")

if not st.session_state.get("token"):
    st.error("Please log in on the main screen to access profiles.")
else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    tab1, tab2, tab3 = st.tabs(["My Profile Card", "Leave a Swap Review", "Classmate Book Counts"])
    
    with tab1:
        try:
            profile = requests.get(
                f"{API_URL}/users/by-username/{quote(st.session_state.username, safe='')}/profile",
                timeout=10,
            ).json()
            st.subheader(f"Username: {profile['username']}")
            st.write(f"**Registered Class/Year:** {profile['school_class']}")
            st.markdown(f"### Classmate Trust Score: **{profile['average_rating']} / 5.0**")
            count_col1, count_col2, count_col3 = st.columns(3)
            count_col1.metric("Listed", profile["books_listed"])
            count_col2.metric("Sold", profile["books_sold"])
            count_col3.metric("Bought", profile["books_bought"])
            
            st.write("---")
            st.markdown("### Recent Feedback History")
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
        
        target_username = st.text_input("Enter their username:")
        score = st.slider("Select Rating:", min_value=1, max_value=5, value=5)
        notes = st.text_area("Add a comment (e.g., 'Book was in perfect condition, super nice transaction!'):")
        
        if st.button("Submit Feedback"):
            if not target_username.strip():
                st.error("Please enter a username.")
            else:
                res = requests.post(
                    f"{API_URL}/reviews", 
                    headers=headers, 
                    params={
                        "reviewed_username": target_username.strip(),
                        "rating": score,
                        "comment": notes,
                    },
                )
                if res.status_code == 200:
                    st.success("Thank you! Feedback submitted safely to their profile card.")
                else:
                    st.error(res.json().get("detail", "Failed to submit review."))

    with tab3:
        st.subheader("View a classmate's book activity")
        target_profile_username = st.text_input(
            "Username",
            key="count_profile_username",
        )
        if st.button("View book counts"):
            if not target_profile_username.strip():
                st.error("Please enter a username.")
                st.stop()
            response = requests.get(
                f"{API_URL}/users/by-username/{quote(target_profile_username.strip(), safe='')}/profile",
                timeout=10,
            )
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