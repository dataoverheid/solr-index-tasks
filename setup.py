# encoding: utf-8


from setuptools import setup
from os import path


repository_root = path.abspath(path.dirname(__file__))

with open(path.join(repository_root, 'README.md'), encoding='utf-8') as f:
    description = f.read()

with open(path.join(repository_root, 'VERSION')) as f:
    current_version = f.read()


setup(
    name='solr-index-tasks',
    version=current_version,
    description=description,
    url='https://github.com/dataoverheid/solr-index-tasks',
    author='Textinfo B.V.',
    author_email='support@textinfo.nl',
    license='CC0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: CC0',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    packages=[
        'solr_tasks',
        'solr_tasks.lib'
    ],
    package_dir={'solr_tasks': 'solr_tasks'},
    package_data={'solr_tasks': ['resources/*']},
    install_requires=[
        'python-dateutil>=2.8.0',
        'python-dotenv>=0.14.0',
        'bugsnag>=3.7.0',
        'urllib3>=1.25.0',
        'requests>=2.24.0'
    ]
)
