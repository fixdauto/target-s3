#!/usr/bin/env python

from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(name="target-s3",
      version="1.0.0",
      description="Singer.io target for uploading files to S3 - Meltano compatible",
      long_description=long_description,
      long_description_content_type='text/markdown',
      author="mctrinkle",
      url='https://github.com/fixdauto/target-s3',
      classifiers=[
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3 :: Only'
      ],
      py_modules=["target_s3_csv"],
      install_requires=[
          'pytz==2018.4',
          'singer-python==5.1.1',
          'inflection==0.3.1',
          'fsspec==0.8.2',
          's3fs==0.5.1',
          'backoff==1.3.2',
          'jsonlines==1.2.0',
          'jsonschema==2.6.0',
          'numpy==1.19.2',
          'pandas==1.1.2',
          'pyarrow==1.0.1',
          'boto3==1.9.57',
          'botocore~=1.12.253',
      ],
      entry_points="""
          [console_scripts]
          target-s3=target_s3:main
       """,
      packages=["target_s3"],
      package_data = {},
      include_package_data=True,
)
