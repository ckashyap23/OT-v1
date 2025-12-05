import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.kite_api_key = os.getenv("KITE_API_KEY", "")
        self.kite_api_secret = os.getenv("KITE_API_SECRET", "")

        # we don't store access token in env, we read it from file
        self.kite_access_token_path = Path(
            os.getenv("KITE_ACCESS_TOKEN_PATH", "kite_access_token.txt")
        )

        self.azure_sql_conn_str = os.getenv("AZURE_SQL_CONN_STR", "")
        self.target_underlyings = os.getenv(
            "TARGET_UNDERLYINGS", "NIFTY,BANKNIFTY"
        ).split(",")


def get_settings() -> Settings:
    return Settings()
