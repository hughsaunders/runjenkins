import datetime
import os

from setuptools import setup


def get_version():
    now = datetime.datetime.now()
    start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    secs_since_midnight = (now - start_of_day).seconds
    date = now.strftime("%Y.%m.%d")
    return "{date}.{ssm}".format(date=date, ssm=secs_since_midnight)


setup(
    name='runjenkins',
    description='Run jenkins jobs from the cli using yaml configs',
    long_description=open(os.path.join(os.path.dirname(__file__),
                          "README.rst")).read(),
    url='https://github.com/hughsaunders/runjenkins',
    author='Hugh Saunders',
    author_email='hugh@wherenow.org',
    license='Apache',
    py_modules=['runjenkins'],
    python_requires='>=3',
    version=get_version(),
    install_requires=[
        'click==6.7',
        'python-jenkins==0.4.15',
        'pyyaml==3.12',
    ],
    entry_points={
        'console_scripts': [
            'runjenkins=runjenkins:cli'
        ]
    }
)
