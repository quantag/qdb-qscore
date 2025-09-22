from flask import Flask, redirect, request, session, jsonify
from flask_cors import CORS
from requests_oauthlib import OAuth2Session
import os
import jwt
import json

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.urandom(24)

# === Load CLIENT_ID and CLIENT_SECRET from Google JSON ===
with open("client_secret.json") as f:
    google_creds = json.load(f)["web"]

CLIENT_ID = google_creds["client_id"]
CLIENT_SECRET = google_creds["client_secret"]

# === REDIRECT_URI stays hardcoded ===
REDIRECT_URI = 'https://cryspprod3.quantag-it.com:444/api10/google-auth-callback'

AUTHORIZATION_BASE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SCOPE = ['openid', 'email', 'profile']

# === Memory store for issued tokens per session ===
issued_tokens = {}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": 0}), 200


@app.route('/google-auth-start')
def login():
    login_token = request.args.get('login_token')
    session['login_token'] = login_token

    print("DEBUG redirect_uri:", REDIRECT_URI)
    oauth = OAuth2Session(CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)
    authorization_url, state = oauth.authorization_url(
        AUTHORIZATION_BASE_URL,
        access_type="offline",
        prompt="select_account"
    )

    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/google-auth-callback')
def callback():
    login_token = session.get('login_token')
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=session.get('oauth_state'))
    token = oauth.fetch_token(
        TOKEN_URL,
        client_secret=CLIENT_SECRET,
        authorization_response=request.url
    )

    session['token_ready'] = True
    session_id = request.cookies.get('session')

    id_token = token.get('id_token')
    decoded = jwt.decode(id_token, options={"verify_signature": False})
    user_email = decoded.get("email")
    print("User email:", user_email)

    issued_tokens[login_token] = id_token

    return '''
    <html><head>
     <title>Quantag Studio</title>
     </head><body>
     <h2>Login successful.</h2>
     You can close this window and return to VS Code
     </body></html>
    '''

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route('/check_token_ready', methods=['GET'])
def check_token_ready():
    login_token = request.args.get('login_token')
    if login_token and login_token in issued_tokens:
        return jsonify({"token": issued_tokens[login_token]})
    else:
        return jsonify({"status": "pending"}), 404

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5020)
