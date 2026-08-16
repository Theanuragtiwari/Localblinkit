from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    APP_NAME: str = 'LocalQuick API'
    APP_VERSION: str = '4.0.0'
    API_V1_PREFIX: str = '/api/v1'

    DATABASE_URL: str = 'sqlite:///./localquick.db'
    JWT_SECRET: str = 'change-me'
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_MINUTES: int = 60 * 24 * 14

    DELIVERY_RADIUS_KM: float = 5.0
    CORS_ORIGINS: str = '*'

    RAZORPAY_KEY_ID: str = ''
    RAZORPAY_KEY_SECRET: str = ''
    GOOGLE_MAPS_API_KEY: str = ''

    RATE_LIMIT_PER_MINUTE: int = 120


settings = Settings()
