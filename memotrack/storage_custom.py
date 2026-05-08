import cloudinary
import cloudinary.uploader
from django.core.files.storage import Storage
from django.conf import settings
import os

class UnsignedCloudinaryStorage(Storage):
    def __init__(self):
        cloudinary.config(
            cloud_name='docpntslt',
            api_key='459548338583816',
            secure=True
        )

    def _save(self, name, content):
        # This forces the "Unsigned" upload using your 'skedit' preset
        response = cloudinary.uploader.upload(
            content,
            upload_preset='skedit',
            unsigned=True,
            folder='media/' + os.path.dirname(name)
        )
        return response['public_id']

    def url(self, name):
        # This generates the FULL web address (https://res.cloudinary.com/...)
        url, options = cloudinary.utils.cloudinary_url(name, secure=True)
        return url

    def exists(self, name):
        return False

    def get_available_name(self, name, max_length=None):
        return name
