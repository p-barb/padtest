'''
Package setup
'''

import setuptools


setuptools.setup(
    name="padtest",
    version="1.0.2",
    author="Pablo Barbieri",
    author_email="pbarbie2@uwo.ca",
    license='MIT',
    description="pad foundation test in Plaxis",
    long_description=("Load test axisymmetric or strip pad foundations subjected to static or dynamic vertical, horizontal or flexural loads in Plaxis 2D."),
    long_description_content_type="text/markdown",
    keywords = ['civil', 'engineering', 'geotechnical', 'pad', 'foundation'], 
    url="https://github.com/p-barb/padtest",
    download_url = 'https://github.com/p-barb/padtest/archive/v_101.tar.gz'
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7.16",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Windows",
    ],
    python_requires='==3.7.16',
    install_requires=['numpy', 'pandas', 'matplotlib', 'pycryptodome'],

)