# BookLoop
Sell your used books online here.

## Registration email settings

The API sends registration OTPs through SMTP. Configure these environment variables before starting the backend:

- `SMTP_HOST`
- `SMTP_PORT` (usually `587`)
- `SMTP_USERNAME`
- `APP_PASSWORD` (the Gmail app password; spaces are removed automatically)

`SMTP_PASSWORD` is also supported for local development. On Render, set
`APP_PASSWORD` to the 16-character Gmail app password, then redeploy the API.

Registration flow:

1. Submit the account details to request a code.
2. Enter the six-digit code sent by email.
3. Select **Verify and Register** to create the account.
