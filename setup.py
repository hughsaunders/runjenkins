from setuptools import setup, find_packages

setup(
    name='runjenkins',
    description='Run jenkins jobs from the cli using yaml configs',
    url='https://github.com/hughsaunders/runjenkins',
    author='Hugh Saunders',
    author_email='hugh@wherenow.org',
    license='Apache',
    packages=find_packages(),
    install_requires=[
        'click==6.7',
        'python-jenkins==0.4.15',
        'pyyaml==3.12',
    ],
    entry_points={
        'console_scripts': [
            'runjenkins=runjenkins.cli'
        ]
    }
)
