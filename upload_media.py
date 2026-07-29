import os
import django
import mimetypes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sripads_bakery.settings')
django.setup()

from bakery.models import UploadedFile
from django.conf import settings
import dj_database_url
from django.db import connections

def upload_local_media_to_db(db_alias='default'):
    print(f"Uploading files to database alias: {db_alias}...")
    media_dir = os.path.join(settings.BASE_DIR, 'media')
    if not os.path.exists(media_dir):
        print(f"Media directory {media_dir} does not exist.")
        return

    # Use the specified database connection
    from django.db import transaction
    try:
        with transaction.atomic(using=db_alias):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    # Get the relative path starting inside 'media/'
                    rel_path = os.path.relpath(filepath, media_dir)
                    
                    # Get content and type
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    
                    content_type, _ = mimetypes.guess_type(filepath)
                    if not content_type:
                        content_type = 'application/octet-stream'
                    
                    # Save to database
                    obj, created = UploadedFile.objects.using(db_alias).update_or_create(
                        name=rel_path,
                        defaults={
                            'content': content,
                            'content_type': content_type,
                        }
                    )
                    print(f"  {'Created' if created else 'Updated'} {rel_path} ({len(content)} bytes)")
    except Exception as e:
        print(f"Error writing to database {db_alias}: {e}")

# 1. Upload to the default database (local)
upload_local_media_to_db('default')

# 2. Upload to the Supabase Postgres database
try:
    supabase_url = "postgresql://postgres.yjkxaywybkndxxlppmhp:Tunu9348608677%40@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
    # Inject Supabase into Django's DATABASES settings dynamically
    settings.DATABASES['supabase'] = dj_database_url.parse(supabase_url)
    
    # Trigger connection initialization
    connections['supabase'].ensure_connection()
    
    upload_local_media_to_db('supabase')
except Exception as e:
    print(f"Could not connect to Supabase: {e}")
