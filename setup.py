'''
Package setup
'''

import setuptools


setuptools.setup(
    name="ltest",
    version="0.0.1",
    author="Pablo Barbieri",
    author_email="pbarbie2@uwo.ca",
    description="centered load test shallow foundation in Plaxis",
    long_description=("centered load test shallow foundation in Plaxis"),
    long_description_content_type="text/markdown",
    url="https://github.com/p-barb/ltest",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7.16",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='==3.7.16',
)