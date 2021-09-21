import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="multiauthlib",
    version="0.0.1",
    author="Jerry Xiao",
    author_email="multiauthlib@mail.jerryxiao.cc",
    description="smart yggdrasil proxy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/isjerryxiao/multi-authlib",
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'multi-authlib=multiauthlib.multiauthlib:main'
        ]
    },
    install_requires=['aiohttp==3.7.4.post0', 'cchardet==2.1.7', 'aiodns==3.0.0']
)
