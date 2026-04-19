"""Google OAuth 공개 엔드포인트 상수.

이 URL들은 Google이 공개한 상수이며 환경별로 달라지지 않는다.
env로 관리할 이유가 없고, env 표면만 넓혀 오설정 가능성을 만든다.
"""

from __future__ import annotations

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_OAUTH_SCOPE = "openid email profile"
