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
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=Caveat:wght@400;500;600;700&display=swap');

        :root {
            --bookloop-ink: #0f172a;
            --bookloop-muted: #53657a;
            --bookloop-paper: #f7f9fc;
            --bookloop-line: #dfe7ec;
            --bookloop-teal: #6ca58a;
            --bookloop-coral: #6ca58a;
            --bookloop-blue: #0f172a;
            --bookloop-soft-green: #edf4ef;
        }

        .stApp {
            background: linear-gradient(145deg, #fbfcfe 0%, #f1f6fb 58%, #fdf8f4 100%);
            color: var(--bookloop-ink);
            font-family: 'DM Sans', sans-serif;
        }

        [data-testid='stHeader'] { background: transparent; }
        [data-testid='stAppViewContainer'] p, [data-testid='stAppViewContainer'] label,
        [data-testid='stAppViewContainer'] .stMarkdown, [data-testid='stAppViewContainer'] .stCaption {
            color: var(--bookloop-ink);
        }
        [data-testid='stAppViewContainer'] [data-testid='stCaptionContainer'] { color: #425467; }
        [data-testid='stSidebar'] {
            background: #51755A;
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
            background: #ffffff;
            color: var(--bookloop-ink);
            min-height: 2.3rem;
            height: 2.3rem;
            padding-top: 0.2rem;
            padding-bottom: 0.2rem;
            font-size: 0.96rem;
        }
        [data-testid='stTextInput'] input::placeholder, [data-testid='stTextArea'] textarea::placeholder { color: #596579; opacity: 1; }
        [data-testid='stCheckbox'] label p { color: var(--bookloop-ink) !important; }
        [data-testid='stTextInput'] input:focus, [data-testid='stTextArea'] textarea:focus,
        [data-testid='stSelectbox'] [role='combobox']:focus-visible {
            border-color: var(--bookloop-teal);
            box-shadow: 0 0 0 2px rgba(81, 117, 90, .2);
        }
        .stButton > button, [data-testid='stFormSubmitButton'] button {
            border: 0;
            border-radius: 999px;
            background: #51755A;
            color: white;
            font-family: 'DM Sans', sans-serif;
            font-weight: 700;
            min-height: 2.6rem;
            padding: 0 1.1rem;
            transition: transform .15s ease, background .15s ease;
        }
        .stButton > button:hover, [data-testid='stFormSubmitButton'] button:hover {
            background: #44664d;
            transform: translateY(-1px);
        }
        [data-baseweb='tab-list'] { gap: 1.5rem; border-bottom: 1px solid var(--bookloop-line); }
        [data-baseweb='tab'] { color: var(--bookloop-muted); font-weight: 700; }
        [aria-selected='true'] { color: var(--bookloop-teal) !important; }
        [data-testid='stAlert'] { border-radius: 8px; }
        [data-testid='stRadio'] [role='radiogroup'] { gap: .6rem; }
        [data-testid='stRadio'] label { font-weight: 700; }
        [data-testid='stSidebar'] [data-testid='stAlert'] p { color: #f7f8f4 !important; }
        .registration-success { text-align: center; padding: .8rem .3rem 1.2rem; }
        .success-checkmark {
            width: 4.5rem; height: 4.5rem; margin: 0 auto 1rem; border-radius: 50%;
            display: grid; place-items: center; background: #e4f5f3; color: #087f65;
            font-size: 2.8rem; font-weight: 700; animation: check-pop .55s cubic-bezier(.2, .8, .2, 1) both;
        }
        @keyframes check-pop {
            0% { transform: scale(.35) rotate(-25deg); opacity: 0; }
            65% { transform: scale(1.12) rotate(5deg); opacity: 1; }
            100% { transform: scale(1) rotate(0); opacity: 1; }
        }
        @media (prefers-reduced-motion: reduce) { .success-checkmark { animation: none; } }
        .bookloop-intro { color: var(--bookloop-muted); font-size: 1.05rem; max-width: 42rem; line-height: 1.6; }
        .bookloop-rule { height: 3px; width: 4.5rem; background: var(--bookloop-coral); margin: 1rem 0 1.6rem; }
        .bookloop-brand { display: flex; align-items: center; gap: .7rem; margin: .2rem 0 2.2rem; }
        .bookloop-mark { width: 2.35rem; height: 2rem; position: relative; display: inline-block; }
        .bookloop-mark:before, .bookloop-mark:after { content: ''; position: absolute; top: .12rem; width: 1rem; height: 1.75rem; background: var(--bookloop-blue); border-radius: .15rem .5rem .15rem .15rem; transform: skewY(-7deg); }
        .bookloop-mark:before { left: .1rem; border-right: .18rem solid #24a0a0; }
        .bookloop-mark:after { right: .1rem; transform: skewY(7deg); border-left: .18rem solid #24a0a0; }
        .bookloop-wordmark { color: var(--bookloop-blue); font-family: 'Space Grotesk', sans-serif; font-size: 1.45rem; font-weight: 700; letter-spacing: -.04em; line-height: 1; }
        .bookloop-wordmark span { color: var(--bookloop-teal); }
        .bookloop-tagline { color: var(--bookloop-muted); font-size: .62rem; letter-spacing: .08em; margin-top: .25rem; }
        .bookloop-hero {
            background: linear-gradient(105deg, #f8fbff 0%, #f4faf6 100%);
            border-radius: 0 0 26px 26px;
            padding: 1rem 2.3rem 1.8rem;
            border: 1px solid #edf2f5;
            margin-top: 0;
        }
        .bookloop-hero h1 { max-width: 40rem; font-size: clamp(2.6rem, 5vw, 4.7rem); margin: .5rem 0 1rem; }
        .bookloop-hero h1 span { color: var(--bookloop-teal); }
        .bookloop-card { background: rgba(255,255,255,.88); border: 1px solid var(--bookloop-line); border-radius: 14px; padding: .85rem; height: 100%; box-shadow: 0 8px 24px rgba(16,28,59,.05); }
        .bookloop-pill { display: inline-block; color: var(--bookloop-teal); background: #e4f5f3; border-radius: 999px; padding: .25rem .65rem; font-size: .72rem; font-weight: 700; }
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
    if "registration_success_pending" not in st.session_state:
        st.session_state.registration_success_pending = False
    if "registration_success_open" not in st.session_state:
        st.session_state.registration_success_open = False
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "Login"

    if st.session_state.registration_success_pending:
        for field_key in (
            "login_user", "login_pass", "reg_user", "reg_email", "reg_pass",
            "reg_under_18", "reg_class", "registration_otp_input",
        ):
            st.session_state[field_key] = "Class 7" if field_key == "reg_class" else False if field_key == "reg_under_18" else ""
        st.session_state.registration_challenge_id = None
        st.session_state.registration_code = None
        st.session_state.registration_otp_expires_at = None
        st.session_state.registration_otp_sent_to = None
        st.session_state.registration_success_pending = False
        st.session_state.registration_success_open = True
        st.session_state.auth_view = "Login"

    logo_path = os.path.join(APP_DIR, "assets", "bookloop-logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=False, width=520)
    else:
        st.markdown(
            '<div class="bookloop-brand">'
            '<span class="bookloop-mark"></span>'
            '<div><div class="bookloop-wordmark">Book<span>Loop</span></div>'
            '<div class="bookloop-tagline">BUY · SELL · SWAP · DONATE</div></div></div>',
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
        st.markdown('<div class="bookloop-hero">', unsafe_allow_html=True)
        st.markdown('<h1><span style="font-weight: 700;">Textbooks</span> find their <span>next chapter.</span></h1>', unsafe_allow_html=True)
        st.markdown('<div class="bookloop-intro">Buy, sell, swap, or donate academic books. Save money, support students, and keep good books moving.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Auth Interface (Only shows up if student is not logged in)
        st.radio(
            "Account access",
            ["Login", "Register Profile"],
            horizontal=True,
            key="auth_view",
            label_visibility="collapsed",
        )

        if st.session_state.auth_view == "Login":
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

        else:
            st.header("Create your account")
            st.caption("Use a verified email address to join your school book exchange.")
            is_under_18 = st.checkbox("I am under 18", key="reg_under_18")
            email_label = "Parent's Gmail Address" if is_under_18 else "Your Gmail Address"
            email_placeholder = "parent@gmail.com" if is_under_18 else "you@gmail.com"
            with st.form("register_form"):
                reg_user = st.text_input("Choose Username", key="reg_user")
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
                                st.session_state.registration_success_pending = True
                                st.rerun()
                            else:
                                st.error(register_res.json().get("detail", "Registration failed."))
                        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                            st.error("Cannot reach the registration service. Please try again shortly.")
                        except Exception as e:
                            st.error(f"Registration failed: {e}")

        if st.session_state.registration_success_open:
            @st.dialog("Registration complete")
            def show_registration_success() -> None:
                st.markdown(
                    '<div class="registration-success"><div class="success-checkmark">✓</div>'
                    '<p>Congratulations, you have signed up!</p></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Continue to sign in", type="primary", use_container_width=True):
                    st.session_state.registration_success_open = False
                    st.session_state.auth_view = "Login"
                    st.rerun()

            show_registration_success()


if __name__ == "__main__":
    main()