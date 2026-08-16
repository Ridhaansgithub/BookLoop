import streamlit as st
import requests
import os

# Allow configuring the backend URL via environment variable `API_URL`.
API_URL = os.getenv("BOOKLOOP_API_URL") or os.getenv("API_URL") or "http://127.0.0.1:8000"
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def page_path(name: str) -> str:
    """Build a stable file path regardless of how Streamlit launches the app."""
    return os.path.join(APP_DIR, "pages", name)


def main() -> None:
    st.set_page_config(page_title="BookLoop", page_icon="📚", layout="wide")

    # Initialize global session states if they don't exist
    if "token" not in st.session_state:
        st.session_state.token = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    st.title("🔄 BookLoop")
    st.subheader("Buy and sell your school books face-to-face for less!")

    # Sidebar login status dashboard
    if st.session_state.token:
        st.sidebar.success(f"Logged in as: {st.session_state.username} (ID: {st.session_state.user_id})")
        if st.sidebar.button("Log Out"):
            st.session_state.token = None
            st.session_state.username = None
            st.session_state.user_id = None
            st.rerun()
    else:
        st.sidebar.info("Please login or register to start swapping books!")

    # Unified app navigation once authenticated; this ensures the Home and My Listings pages share the same session state.
    if st.session_state.token:
        pages = [
            st.Page(page_path("Home.py"), title="Home", icon="🏠"),
            st.Page(page_path("MyListings.py"), title="My Listings", icon="📚"),
            st.Page(page_path("SellBook.py"), title="Sell Book", icon="💰"),
            st.Page(page_path("Chat.py"), title="Chat", icon="💬"),
            st.Page(page_path("Profile.py"), title="Profile", icon="👤"),
        ]
        pg = st.navigation(pages)
        pg.run()
    else:
        # Auth Interface (Only shows up if student is not logged in)
        tab1, tab2 = st.tabs(["🔒 Login", "📝 Register Profile"])

        with tab1:
            st.header("Login")
            with st.form("login_form"):
                login_user = st.text_input("Username", key="login_user")
                login_pass = st.text_input("Password", type="password", key="login_pass")
                submit_login = st.form_submit_button("Sign In")

            if submit_login:
                if not login_user or not login_pass:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        # 1. Authenticate credentials and request access token
                        res = requests.post(f"{API_URL}/login", data={"username": login_user, "password": login_pass}, timeout=5)
                        if res.status_code == 200:
                            try:
                                data = res.json()
                                token = data.get("access_token")
                            except Exception:
                                st.error("Invalid response from authentication endpoint.")
                                token = None

                            if token:
                                # 2. Use token immediately to safely pull the profile data
                                headers = {"Authorization": f"Bearer {token}"}
                                profile_res = requests.get(f"{API_URL}/users/me", headers=headers, timeout=5)

                                if profile_res.status_code == 200:
                                    try:
                                        profile_data = profile_res.json()
                                    except Exception:
                                        st.error("Failed to parse profile response.")
                                        profile_data = None

                                    if profile_data:
                                        # 3. Securely set session values from the official database record
                                        st.session_state.token = token
                                        st.session_state.username = profile_data.get("username")
                                        st.session_state.user_id = profile_data.get("id")

                                        st.success("Welcome back! Use the sidebar navigation to browse or list books.")
                                        st.rerun()
                                    else:
                                        st.error("Failed to retrieve your profile information.")
                                else:
                                    st.error("Failed to retrieve your profile information.")
                            else:
                                st.error("Invalid username or password.")
                    except requests.exceptions.Timeout:
                        st.error("Request timed out. Is the backend running and reachable?")
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to backend server. Is Uvicorn running?")
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        with tab2:
            st.header("Create School Account")
            with st.form("register_form"):
                reg_user = st.text_input("Choose Username", key="reg_user")
                reg_email = st.text_input("School Email Address", key="reg_email")
                reg_pass = st.text_input("Password", type="password", key="reg_pass")
                reg_class = st.selectbox("Your Current Class/Year group", ["Class 7", "Class 8", "Class 9", "Class 10", "Class 11"], key="reg_class")
                submit_reg = st.form_submit_button("Register Now")

            if submit_reg:
                if not reg_user or not reg_email or not reg_pass:
                    st.error("All registration fields are required.")
                else:
                    try:
                        # Pass fields explicitly as query string parameters matching backend rules
                        params = {
                            "username": reg_user,
                            "email": reg_email,
                            "password": reg_pass,
                            "school_class": reg_class
                        }
                        res = requests.post(f"{API_URL}/register", params=params, timeout=5)

                        # Check if the backend responded with a successful status code
                        if res.status_code == 201:
                            st.success("🎉 Registration successful! You can now log in using the 'Login' tab above.")
                        elif res.status_code == 400:
                            # Safely try parsing JSON only if it's a known error payload
                            try:
                                st.error(res.json().get("detail", "Registration failed."))
                            except Exception:
                                st.error(f"Registration failed with code 400: {res.text}")
                        else:
                            st.error(f"Backend returned error code {res.status_code}. Check your Uvicorn console logs!")

                    except requests.exceptions.Timeout:
                        st.error("Request timed out. Is the backend running and reachable?")
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to backend server. Is Uvicorn running?")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")


if __name__ == "__main__":
    main()