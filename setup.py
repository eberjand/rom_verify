#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='romverify',
    version='0.1',
    description='Tool for verifying and organizing ROM dumps with No-Intro DATs',
    url='https://github.com/eberjand/rom_verify',
    license='MIT',
    entry_points={
        'console_scripts': [
            'romverify = romverify.main:main'
        ]
    },
    packages=find_packages()
)
