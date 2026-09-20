import streamlit as st
import requests
import os
import re
import hmac
import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from frontend.config import API_URL

APP_DIR = os.path.dirname(os.path.abspath(__file__))
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OTP_EXPIRY_MINUTES = 10


def setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, KeyError):
        return default


def create_registration_assertion(email: str) -> str:
    signing_secret = setting("OTP_SIGNING_SECRET").strip()
    if not signing_secret:
        raise RuntimeError("OTP_SIGNING_SECRET is not configured in the Streamlit environment.")
    expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).timestamp())
    payload = f"{email.strip().lower()}:{expires_at}"
    signature = hmac.new(signing_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def send_registration_otp(recipient: str, otp: str) -> None:
    smtp_host = setting("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_username = setting("SMTP_USERNAME").strip()
    smtp_password = re.sub(r"\s+", "", setting("APP_PASSWORD") or setting("SMTP_PASSWORD"))
    try:
        smtp_port = int(setting("SMTP_PORT", "587").strip())
    except ValueError as error:
        raise RuntimeError("SMTP_PORT must be a valid number in the Streamlit environment.") from error
    if not smtp_username or not smtp_password:
        raise RuntimeError("SMTP_USERNAME and APP_PASSWORD must be configured in Streamlit.")

    message = EmailMessage()
    message["Subject"] = "Your BookLoop verification code"
    message["From"] = smtp_username
    message["To"] = recipient
    message.set_content(f"Your BookLoop verification code is {otp}. It expires in {OTP_EXPIRY_MINUTES} minutes.")
    smtp_connection = smtplib.SMTP_SSL if smtp_port == 465 else smtplib.SMTP
    with smtp_connection(smtp_host, smtp_port, timeout=15) as smtp:
        if smtp_port != 465:
            smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)


def page_path(name: str) -> str:
    """Build a stable file path regardless of how Streamlit launches the app."""
    return os.path.join(APP_DIR, "pages", name)


def main() -> None:
    st.set_page_config(page_title="BookLoop | School book exchange", page_icon="📖", layout="wide")

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --bookloop-ink: #17211f;
            --bookloop-muted: #61706c;
            --bookloop-paper: #f7f8f4;
            --bookloop-line: #dce4df;
            --bookloop-teal: #0b766e;
            --bookloop-coral: #d95f4f;
        }

        .stApp {
            background: linear-gradient(135deg, #f7f8f4 0%, #eef5f1 55%, #fdf8f3 100%);
            color: var(--bookloop-ink);
            font-family: 'DM Sans', sans-serif;
        }

        [data-testid='stHeader'] { background: transparent; }
        [data-testid='stAppViewContainer'] p, [data-testid='stAppViewContainer'] label,
        [data-testid='stAppViewContainer'] .stMarkdown, [data-testid='stAppViewContainer'] .stCaption {
            color: var(--bookloop-ink);
        }
        [data-testid='stAppViewContainer'] [data-testid='stCaptionContainer'] { color: var(--bookloop-muted); }
        [data-testid='stSidebar'] {
            background: #17211f;
            border-right: 0;
        }
        [data-testid='stSidebar'] * { color: #f7f8f4; }
        h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif; letter-spacing: 0; }
        h1 { color: var(--bookloop-ink); font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.05; }
        h2 { color: var(--bookloop-ink); }
        [data-testid='stTextInput'] input, [data-testid='stSelectbox'] > div,
        [data-testid='stNumberInput'] input, [data-testid='stTextArea'] textarea {
            border: 1px solid var(--bookloop-line);
            border-radius: 8px;
            background: rgba(255, 255, 255, .8);
            color: var(--bookloop-ink);
            min-height: 2.8rem;
        }
        [data-testid='stTextInput'] input::placeholder { color: #6b7774; opacity: 1; }
        [data-testid='stCheckbox'] label p { color: var(--bookloop-ink) !important; }
        [data-testid='stTextInput'] input:focus, [data-testid='stTextArea'] textarea:focus {
            border-color: var(--bookloop-teal);
            box-shadow: 0 0 0 2px rgba(11, 118, 110, .14);
        }
        .stButton > button, [data-testid='stFormSubmitButton'] button {
            border: 0;
            border-radius: 7px;
            background: var(--bookloop-teal);
            color: white;
            font-family: 'DM Sans', sans-serif;
            font-weight: 700;
            min-height: 2.8rem;
            padding: 0 1.15rem;
            transition: transform .15s ease, background .15s ease;
        }
        .stButton > button:hover, [data-testid='stFormSubmitButton'] button:hover {
            background: #095f59;
            transform: translateY(-1px);
        }
        [data-baseweb='tab-list'] { gap: 1.5rem; border-bottom: 1px solid var(--bookloop-line); }
        [data-baseweb='tab'] { color: var(--bookloop-muted); font-weight: 700; }
        [aria-selected='true'] { color: var(--bookloop-teal) !important; }
        [data-testid='stAlert'] { border-radius: 8px; }
        .bookloop-kicker { color: var(--bookloop-teal); font-size: .78rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
        .bookloop-intro { color: var(--bookloop-muted); font-size: 1.05rem; max-width: 42rem; line-height: 1.6; }
        .bookloop-rule { height: 3px; width: 4.5rem; background: var(--bookloop-coral); margin: 1rem 0 1.6rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize global session states if they don't exist
    if "token" not in st.session_state:
        st.session_state.token = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "registration_challenge_id" not in st.session_state:
        st.session_state.registration_challenge_id = None
    if "registration_code" not in st.session_state:
        st.session_state.registration_code = None
    if "registration_otp_expires_at" not in st.session_state:
        st.session_state.registration_otp_expires_at = None

    st.markdown('<div class="bookloop-kicker">A smarter school exchange</div>', unsafe_allow_html=True)
    st.title("BookLoop")
    st.markdown(
        '<div class="bookloop-intro">Pass on the books you have finished. Find the books you need next, at a fairer price.</div>'
        '<div class="bookloop-rule"></div>',
        unsafe_allow_html=True,
    )

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
            st.header("Welcome back")
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
            st.header("Create your account")
            st.caption("Use a verified email address to join your school book exchange.")
            with st.form("register_form"):
                reg_user = st.text_input("Choose Username", key="reg_user")
                is_under_18 = st.checkbox("I am under 18", key="reg_under_18")
                email_label = "Parent's Gmail Address" if is_under_18 else "Your Email Address"
                email_placeholder = "parent@gmail.com" if is_under_18 else "you@example.com"
                reg_email = st.text_input(email_label, placeholder=email_placeholder, key="reg_email")
                reg_pass = st.text_input("Password", type="password", key="reg_pass")
                reg_class = st.selectbox("Your Current Class/Year group", ["Class 7", "Class 8", "Class 9", "Class 10", "Class 11"], key="reg_class")
                request_otp = st.form_submit_button("Send Verification Code")

            if request_otp:
                if not reg_user or not reg_email or not reg_pass:
                    st.error("All registration fields are required.")
                elif not EMAIL_PATTERN.fullmatch(reg_email.strip()):
                    st.error("Please enter a valid email address.")
                elif is_under_18 and not reg_email.strip().lower().endswith("@gmail.com"):
                    st.error("Parental consent requires a Gmail address.")
                else:
                    try:
                        registration_otp = f"{secrets.randbelow(1_000_000):06d}"
                        send_registration_otp(reg_email.strip(), registration_otp)
                        st.session_state.registration_code = registration_otp
                        st.session_state.registration_otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
                        st.session_state.registration_challenge_id = "streamlit"
                        st.session_state.registration_otp_sent_to = reg_email.strip().lower()
                        st.success("Verification code sent. Check your inbox and spam folder.")
                    except (OSError, smtplib.SMTPException) as error:
                        st.error(f"Could not send the verification email: {error}")
                    except RuntimeError as error:
                        st.error(str(error))
                    except Exception as error:
                        st.error(f"Could not send the verification email: {error}")

            if st.session_state.get("registration_challenge_id"):
                st.info(
                    f"Enter the 6-digit code sent to {st.session_state.get('registration_otp_sent_to', reg_email.strip())}."
                )
                with st.form("verify_registration_form"):
                    registration_otp = st.text_input(
                        "Email verification code",
                        max_chars=6,
                        placeholder="Enter 6 digits",
                        key="registration_otp_input",
                    )
                    verify_otp = st.form_submit_button("Verify and Register")

                if verify_otp:
                    if not registration_otp.isdigit() or len(registration_otp) != 6:
                        st.error("Enter the 6-digit verification code from your email.")
                    elif datetime.now(timezone.utc) > st.session_state.registration_otp_expires_at:
                        st.error("This verification code has expired. Request a new code.")
                    elif not hmac.compare_digest(registration_otp, st.session_state.registration_code):
                        st.error("Incorrect verification code.")
                    else:
                        try:
                            register_res = requests.post(
                                f"{API_URL}/register",
                                params={
                                    "username": reg_user,
                                    "email": reg_email.strip(),
                                    "password": reg_pass,
                                    "school_class": reg_class,
                                    "verification_token": create_registration_assertion(reg_email),
                                },
                                timeout=10,
                            )
                            if register_res.status_code == 201:
                                st.session_state.registration_challenge_id = None
                                st.session_state.registration_code = None
                                st.session_state.registration_otp_sent_to = None
                                st.success("Registration successful. You can now sign in.")
                            else:
                                st.error(register_res.json().get("detail", "Registration failed."))
                        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                            st.error("Cannot reach the registration service. Please try again shortly.")
                        except Exception as e:
                            st.error(f"Registration failed: {e}")


if __name__ == "__main__":
    main()