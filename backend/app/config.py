from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "LifeQuest"
    DATABASE_URL: str = "sqlite:///./lifequest.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
