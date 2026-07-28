from django.core.files.storage import Storage
from django.core.files.base import ContentFile
from django.apps import apps
import mimetypes

class DatabaseStorage(Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_model(self):
        return apps.get_model('bakery', 'UploadedFile')

    def _open(self, name, mode='rb'):
        UploadedFile = self._get_model()
        try:
            obj = UploadedFile.objects.get(name=name)
            return ContentFile(obj.content, name=name)
        except UploadedFile.DoesNotExist:
            raise FileNotFoundError(f"File not found: {name}")

    def _save(self, name, content):
        UploadedFile = self._get_model()
        content.seek(0)
        data = content.read()
        
        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = 'application/octet-stream'
            
        # Standardize path name to match what is returned by url()
        obj, created = UploadedFile.objects.update_or_create(
            name=name,
            defaults={
                'content': data,
                'content_type': content_type
            }
        )
        return name

    def exists(self, name):
        UploadedFile = self._get_model()
        return UploadedFile.objects.filter(name=name).exists()

    def url(self, name):
        from django.conf import settings
        # Ensure we return a path beginning with MEDIA_URL
        # Remove any leading / if it's already in name, to prevent duplicates
        clean_name = name.lstrip('/')
        return f"{settings.MEDIA_URL}{clean_name}"

    def size(self, name):
        UploadedFile = self._get_model()
        try:
            return len(UploadedFile.objects.get(name=name).content)
        except UploadedFile.DoesNotExist:
            return 0
