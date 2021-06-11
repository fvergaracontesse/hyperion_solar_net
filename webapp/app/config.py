import os


class Config(object):
    TESTING = False
    SECRET_KEY = 'super secret key'


class ProductionConfig(Config):
    GOOGLE_API_KEY = os.environ.get("GOOGLE_MAP_API_KEY")


class DevelopmentConfig(Config):
    GOOGLE_API_KEY = os.environ.get("GOOGLE_MAP_API_KEY")


class TestingConfig(Config):
    GOOGLE_API_KEY = os.environ.get("GOOGLE_MAP_API_KEY")
    TESTING = True
