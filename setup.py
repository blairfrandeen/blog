from app import __version__
from setuptools import setup

setup(
    name="blog_admin",
    version=__version__,
    py_modules=["blog_admin"],
    install_requires=[
        "Click",
    ],
    entry_points={
        "console_scripts": [
            "blog = blog_admin:cli",
        ],
    },
)
