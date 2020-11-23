database_url = 'sqlite:///C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/app/database.db'

class Config(object):
    DEBUG = False
    PROCESSED_REQUESTS_FOLDER = 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/processed_requests'
    MODELS_FOLDER = 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/models'
    UPLOAD_IMAGES_FOLDER = 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/images'
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    APPLICATION_ROOT = ''