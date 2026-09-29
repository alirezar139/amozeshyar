from copy import copy
from datetime import timedelta

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

# How long past its expiry an access token still authenticates an upload.
UPLOAD_TOKEN_GRACE = timedelta(hours=6)


class _UploadAccessToken(AccessToken):
    """An access token whose expiry is extended by UPLOAD_TOKEN_GRACE.

    The signature, token type and user are all still verified; only the
    15-minute lifetime is relaxed."""

    def get_token_backend(self):
        backend = copy(super().get_token_backend())
        backend.leeway = UPLOAD_TOKEN_GRACE
        return backend

    def check_exp(self, claim="exp", current_time=None):
        super().check_exp(claim, (current_time or self.current_time) - UPLOAD_TOKEN_GRACE)


class UploadJWTAuthentication(JWTAuthentication):
    """For file-upload endpoints only.

    Django authenticates a request once its whole body has arrived, so a
    multi-gigabyte video that takes longer than the access token's 15
    minutes would be rejected right at the end — after the entire upload.
    This accepts a genuine access token that expired within the grace
    window instead.
    """

    def get_validated_token(self, raw_token):
        try:
            return _UploadAccessToken(raw_token)
        except TokenError as e:
            raise InvalidToken({"detail": e.args[0]}) from e
