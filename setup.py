from setuptools import setup, find_packages

version = "0.0.0"  
name = "nales_alpha"
description = "Nalès"
long_description = " "
author = "Romain FERRU"
author_email = "Romain.ferru@gmail.com"
install_requires = (
    []
)  # 


setup(
    name=name,
    version=version,
    license="TBD",
    author=author,
    author_email=author_email,
    description=description,
    long_description=long_description,
    packages=find_packages(where="*"),
    install_requires=install_requires,
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    test_suite="tests",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX",
        "Operating System :: MacOS",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet",
        "Topic :: Scientific/Engineering",
    ],
)