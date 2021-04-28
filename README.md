# target-s3

# Notice: Unmaintained

This project is a fork of [Pipelinewise's `target-s3`](https://github.com/transferwise/pipelinewise-target-s3-csv) where we experimented with adding new features but ultimately are no longer maintaining this project and do not recommend it's use in prodcution. See more here: https://github.com/fixdauto/target-s3/issues/1#issuecomment-828087153

---

[![PyPI version](https://badge.fury.io/py/target-s3.svg)](https://badge.fury.io/py/target-s3)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/target-s3.svg)](https://pypi.org/project/target-s3/)
[![License: Apache2](https://img.shields.io/badge/License-Apache2-yellow.svg)](https://opensource.org/licenses/Apache-2.0)

[Singer](https://www.singer.io/) target that uploads loads data to S3
following the [Singer spec](https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md).

This is a [Meltano](https://meltano.com/) compatible target connector.

## How to use it

The recommended method of running this target is to use it from [Meltano](https://meltano.com/). 

If you want to run this [Singer Target](https://singer.io) independently please read further.

## Install

First, make sure Python 3 is installed on your system or follow these
installation instructions for [Mac](http://docs.python-guide.org/en/latest/starting/install3/osx/) or
[Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-local-programming-environment-on-ubuntu-16-04).

It's recommended to use a virtualenv:

```bash
  python3 -m venv venv
  pip install target-s3
```

or

```bash
  python3 -m venv venv
  . venv/bin/activate
  pip install --upgrade pip
  pip install .
```

### To run

Like any other target that's following the singer specificiation:

`some-singer-tap | target-s3 --config [config.json]`

It's reading incoming messages from STDIN and using the properites in `config.json` to upload data into Postgres.

**Note**: To avoid version conflicts run `tap` and `targets` in separate virtual environments.

### Configuration settings

Running the the target connector requires a `config.json` file. An example with the minimal settings:

   ```json
   {
     "s3_bucket": "my_bucket"
   }
   ```

### Profile based authentication

Profile based authentication used by default using the `default` profile. To use another profile set `aws_profile` parameter in `config.json` or set the `AWS_PROFILE` environment variable.

### Non-Profile based authentication

For non-profile based authentication set `aws_access_key_id` , `aws_secret_access_key` and optionally the `aws_session_token` parameter in the `config.json`. Alternatively you can define them out of `config.json` by setting `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` environment variables.


Full list of options in `config.json`:

| Property                            | Type    | Required?  | Description                                                   |
|-------------------------------------|---------|------------|---------------------------------------------------------------|
| aws_access_key_id                   | String  | No         | S3 Access Key Id. If not provided, `AWS_ACCESS_KEY_ID` environment variable will be used. |
| aws_secret_access_key               | String  | No         | S3 Secret Access Key. If not provided, `AWS_SECRET_ACCESS_KEY` environment variable will be used. |
| aws_session_token                   | String  | No         | AWS Session token. If not provided, `AWS_SESSION_TOKEN` environment variable will be used. |
| aws_profile                         | String  | No         | AWS profile name for profile based authentication. If not provided, `AWS_PROFILE` environment variable will be used. |
| s3_bucket                           | String  | Yes        | S3 Bucket name                                                |
| field_to_partition_by_time          | String  | Yes        | The timestamp or date field (key) that will be parsed into year/month/day to create partitions for large event datasets. 
| file_type                           | String  | No         | (Default: 'parquet') The type of file to upload to s3. Supported options are `parquet`. The file extension will automatically be updated based off the corresponding file type. |
| compression                         | String  | No         | The type of compression to apply before uploading. Supported options are `none`, `snappy` (default), `gzip`, and `brotli`. The file extension will automatically be updated based off the corresponding compression. |
| add_metadata_columns                | Boolean |            | (Default: False) Metadata columns add extra row level information about data ingestions, (i.e. when was the row read in source, when was inserted or deleted in snowflake etc.) Metadata columns are creating automatically by adding extra columns to the tables with a column prefix `_SDC_`. The column names are following the stitch naming conventions documented at https://www.stitchdata.com/docs/data-structure/integration-schemas#sdc-columns. Enabling metadata columns will flag the deleted rows by setting the `_SDC_DELETED_AT` metadata column. Without the `add_metadata_columns` option the deleted rows from singer taps will not be recongisable in Snowflake. |
| encryption_type                     | String  | No         | (Default: 'none') The type of encryption to use. Current supported options are: 'none' and 'KMS'. |
| encryption_key                      | String  | No         | A reference to the encryption key to use for data encryption. For KMS encryption, this should be the name of the KMS encryption key ID (e.g. '1234abcd-1234-1234-1234-1234abcd1234'). This field is ignored if 'encryption_type' is none or blank. |

## License

Apache License Version 2.0

See [LICENSE](LICENSE) to see the full text.
