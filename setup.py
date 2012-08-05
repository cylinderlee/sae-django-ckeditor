import os.path
from setuptools import setup, find_packages

def get_source_files():
    for dirname, _, files in os.walk('ckeditor/static/ckeditor/ckeditor/_source'):
        for filename in files:
            yield os.path.join('/'.join(dirname.split('/')[1:]), filename)

setup(
    name='sae-django-ckeditor',
    version='3.6.2.1',
    description='Django admin CKEditor integration for SAE.',
    long_description = open('README.rst', 'r').read() + open('AUTHORS.rst', 'r').read() + open('CHANGELOG.rst', 'r').read(),
    author='wangeek',
    author_email='nifabric@gmail.com',
    url='http://github.com/wangeek/sae-django-ckeditor',
    packages = find_packages(exclude=['project',]),
    install_requires = [
        'Pillow',
    ],
    include_package_data=True,
    exclude_package_data={
        'ckeditor': list(get_source_files()),
    },
    test_suite="setuptest.setuptest.SetupTestSuite",
    tests_require=[
        'django-setuptest>=0.1.1',
    ],
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    zip_safe=False,
)
