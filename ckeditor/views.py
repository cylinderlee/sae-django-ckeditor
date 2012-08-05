import os
import re
from urlparse import urlparse, urlunparse
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from sae import storage
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from PIL import Image, ImageOps
except ImportError:
    import Image
    import ImageOps

try:
    from django.views.decorators.csrf import csrf_exempt
except ImportError:
    # monkey patch this with a dummy decorator which just returns the
    # same function (for compatability with pre-1.1 Djangos)
    def csrf_exempt(fn):
        return fn

THUMBNAIL_SIZE = (75, 75)
domain = getattr(settings, "CKEDITOR_UPLOAD_PATH", 'base')
storage_client = storage.Client()


def get_available_name(name):
    """
    Returns a filename that's free on the target storage system, and
    available for new content to be written to.
    """
    def exists(name):
        try:
            o = storage_client.stat(domain, name)
        #except storage.ObjectNotExistsError:
        except Exception:
            return False
    while exists(name):
        name += '_'
    return name


def get_thumb_filename(file_name):
    """
    Generate thumb filename by adding _thumb to end of
    filename before . (if present)
    """
    return '%s_thumb%s' % os.path.splitext(file_name)


def create_thumbnail(filename):
    saefile = StringIO(storage_client.get(domain,filename).data)
    image = Image.open(saefile)

    # Convert to RGB if necessary
    # Thanks to Limodou on DjangoSnippets.org
    # http://www.djangosnippets.org/snippets/20/
    if image.mode not in ('L', 'RGB'):
        image = image.convert('RGB')

    # scale and crop to thumbnail
    imagefit = ImageOps.fit(image, THUMBNAIL_SIZE, Image.ANTIALIAS)
    thumb_saefile = StringIO()
    upload_ext = os.path.splitext(filename)[1][1:]
    if upload_ext.upper() == 'JPG': upload_ext='JPEG'
    imagefit.save(thumb_saefile,format=upload_ext)
    storage_client.put(domain,get_thumb_filename(filename),storage.Object(thumb_saefile.getvalue()))


def get_upload_filename(upload_name, user):
    # If CKEDITOR_RESTRICT_BY_USER is True upload file to user specific path.
    if getattr(settings, 'CKEDITOR_RESTRICT_BY_USER', False):
        user_path = user.username
    else:
        user_path = ''

    # Generate date based path to put uploaded file.
    date_path = datetime.now().strftime('%Y_%m_%d')

    ## Complete upload path (upload_path + date_path).
    ## upload_path = os.path.join(settings.CKEDITOR_UPLOAD_PATH, user_path, \
    #         date_path)

    ## Make sure upload_path exists.
    #if not os.path.exists(upload_path):
    #    os.makedirs(upload_path)

    # Get available name and return.
    #return get_available_name(os.path.join(upload_path, upload_name))
    #only filename support, can't mkdir
    upload_path = user_path + date_path
    return get_available_name(upload_path+upload_name)


@csrf_exempt
def upload(request):
    """
    Uploads a file and send back its URL to CKEditor.

    TODO:
        Validate uploads
    """
    # Get the uploaded file from request.
    upload = request.FILES['upload']
    upload_ext = os.path.splitext(upload.name)[1]

    # Open output file in which to store upload.
    upload_filename = get_upload_filename(upload.name, request.user)
    #out = open(upload_filename, 'wb+')
    out = StringIO()

    # Iterate through chunks and write to destination.
    for chunk in upload.chunks():
        out.write(chunk)

    url = storage_client.put(domain,upload_filename,storage.Object(out.getvalue()))
    create_thumbnail(upload_filename)

    # Respond with Javascript sending ckeditor upload url.
    return HttpResponse("""
    <script type='text/javascript'>
        window.parent.CKEDITOR.tools.callFunction(%s, '%s');
    </script>""" % (request.GET['CKEditorFuncNum'], url))


def get_image_files(user=None):
    """
    Recursively walks all dirs under upload dir and generates a list of
    full paths for each file found.
    """
    # If a user is provided and CKEDITOR_RESTRICT_BY_USER is True,
    # limit images to user specific path, but not for superusers.
    if user and not user.is_superuser and getattr(settings, \
            'CKEDITOR_RESTRICT_BY_USER', False):
        user_path = user.username
    else:
        user_path = ''

    #browse_path = os.path.join(settings.CKEDITOR_UPLOAD_PATH, user_path)

    #TODO deal with user
    for item in storage_client.list(domain):
        # bypass for thumbs
        filename = item['name']
        if not filename.startswith(user_path) or os.path.splitext(filename)[0].endswith('_thumb'):
            continue
        yield filename


def get_image_browse_urls(user=None):
    """
    Recursively walks all dirs under upload dir and generates a list of
    thumbnail and full image URL's for each file found.
    """
    images = []
    for filename in get_image_files(user=user):
        images.append({
            'thumb': storage_client.url(domain,get_thumb_filename(filename)),
            'src': storage_client.url(domain,filename)
        })

    return images


def browse(request):
    context = RequestContext(request, {
        'images': get_image_browse_urls(request.user),
        'STATIC_URL':settings.STATIC_URL
    })
    return render_to_response('browse.html', context)
