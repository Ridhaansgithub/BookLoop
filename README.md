# BookLoop
Sell your used books online here.

## Registration email settings

The Streamlit app sends and verifies registration OTPs through SMTP. Configure
these variables in the Streamlit deployment:

- `SMTP_HOST`
- `SMTP_PORT` (usually `587`)
- `SMTP_USERNAME`
- `APP_PASSWORD` (the Gmail app password; spaces are removed automatically)
- `OTP_SIGNING_SECRET` (a random secret shared with the API)

Configure the same `OTP_SIGNING_SECRET` in the Render API service. The API does
not send email; it only validates Streamlit's short-lived signed assertion
before creating the account.

Registration flow:

1. Submit the account details to request a code from Streamlit.
2. Enter the six-digit code sent by email.
3. Select **Verify and Register** to create the account.
