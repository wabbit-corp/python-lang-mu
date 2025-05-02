#!/usr/bin/env python
# TODO: Decide what to do with Python 3.10+ compatibility.

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="python-lang-mu",
    version="1.0.0",
    author="Sir Wabbit",
    author_email="wabbit@wabbit.one",
    description="Mu Configuration Language",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/python-lang-mu",  # or your repo
    packages=["mu"],
    python_requires=">=3.10",  # or lower, but code uses match/case
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)