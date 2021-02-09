database_url = 'sqlite:///C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/app/database.db'

class Config(object):
    DEBUG = False
    PROCESSED_REQUESTS_FOLDER = 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/processed_requests'
    MODELS_FOLDER = 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/models'
    UPLOAD_IMAGES_FOLDER = 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/images'
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    APPLICATION_ROOT = ''

    EMAIL_NOTIFICATION_ADDRESSES = ["example1@google.com", "example2@google.com"]
    MAX_EMAIL_FREQUENCY = 3600

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_USERNAME = ''
    MAIL_PASSWORD = ''
