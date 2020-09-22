#!/usr/bin/env python3

import argparse
import csv
import gzip
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
import pandas as pd
import pyarrow as pa
import itertools
from io import StringIO
from sys import getsizeof

import singer
from jsonschema import Draft4Validator, FormatChecker

from target_s3 import s3
from target_s3 import utils

logger = singer.get_logger('target_s3')


# Upload created files to S3
def upload_to_s3(s3_client, s3_bucket, filename, s3_target,
                 compression=None, encryption_type=None, encryption_key=None):
    data = []
    df = None
    with open(filename, 'r') as f:
        data = f.read().splitlines()
    #     while True:
    #         lines = list(itertools.islice(f, 100))
    #
    #         if lines:
    #             lines_str = ''.join(lines)
    #             data.append(pd.read_json(StringIO(lines_str), lines=True))
    #         else:
    #             break

    # with open(filename, 'r') as f:
    #     df = pd.read_json(f, lines=True, chunksize=1000)

    # for x, l in enumerate(data[:2]):
    #     logger.info('line: {} of csv: {}'.format(x, l))

    df = pd.DataFrame(data)
    df.columns = ['json_element']
    df = df['json_element'].apply(json.loads)
    df = pd.json_normalize(df)

    if df is not None:
        compressed_file = filename.replace('jsonl', 'parquet')
        s3_target = s3_target + '.{}'.format('parquet')
        logger.info('df size: {}, compressed_file: {}'.format(df.shape, compressed_file))
        # df.to_csv(filename)
    filename_sufix_map = {'snappy': 'snappy', 'gzip': 'gz', 'brotli': 'br'}

    compressed_file = None
    if compression is None or compression.lower() == "none":
        df.to_parquet(compressed_file, index=False, compression=None)
    else:
        if compression in filename_sufix_map:
            compressed_file = "{}.{}".format(filename, filename_sufix_map[compression])
            df.to_parquet(compressed_file, index=False, compression=compression)
            s3_target = s3_target + '.{}'.format(filename_sufix_map[compression])
        else:
            raise NotImplementedError(
                """Compression type '{}' is not supported. Expected: {}""".format(compression, filename_sufix_map.keys())
            )
    s3.upload_file(compressed_file or filename,
                   s3_client,
                   s3_bucket,
                   s3_target,
                   encryption_type=encryption_type,
                   encryption_key=encryption_key)

    # Remove the local file(s)
    os.remove(filename)
    if compressed_file:
        os.remove(compressed_file)


def emit_state(state):
    if state is not None:
        line = json.dumps(state)
        logger.debug('Emitting state {}'.format(line))
        sys.stdout.write("{}\n".format(line))
        sys.stdout.flush()


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def persist_messages(messages, config, s3_client):
    state = None
    schemas = {}
    key_properties = {}
    headers = {}
    validators = {}

    filenames = []
    file_size_counters = dict()
    file_count_counters = dict()
    file_data = dict()
    filename = None
    s3_path, s3_filename = None, None
    now = datetime.now().strftime('%Y%m%dT%H%M%S')
    max_file_size_mb = 1000
    stream = None

    for message in messages:
        try:
            o = singer.parse_message(message).asdict()
        except json.decoder.JSONDecodeError:
            logger.error("Unable to parse:\n{}".format(message))
            raise
        message_type = o['type']
        # if message_type != 'RECORD':
        #     logger.info("singer message: {}".format(o))

        if message_type == 'RECORD':
            if o['stream'] not in schemas:
                raise Exception("A record for stream {}"
                                "was encountered before a corresponding schema".format(o['stream']))

            # Validate record
            try:
                validators[o['stream']].validate(utils.float_to_decimal(o['record']))
            except Exception as ex:
                if type(ex).__name__ == "InvalidOperation":
                    logger.error("""Data validation failed and cannot load to destination. RECORD: {}\n
                    'multipleOf' validations that allows long precisions are not supported 
                    (i.e. with 15 digits or more). Try removing 'multipleOf' methods from JSON schema.
                    """.format(o['record']))
                    raise ex

            record_to_load = o['record']
            if config.get('add_metadata_columns'):
                record_to_load = utils.add_metadata_values_to_record(o, {})
            else:
                record_to_load = utils.remove_metadata_values_from_record(o)

            flattened_record = utils.flatten_record(record_to_load)

            if filename is None:
                logger.info('first record: {}'.format(flattened_record))
                filename = utils.get_temp_file_path(o,
                                                    flattened_record,
                                                    key_properties[stream],
                                                    export_time=now,
                                                    path_specification=config.get('path_specification'))
                filename = os.path.join(tempfile.gettempdir(), filename)
                filename = os.path.expanduser(filename)
                file_size_counters[filename] = 0
                file_count_counters[filename] = file_count_counters.get(filename, 1)

                logger.info("Formatted temp filename: {}".format(filename))

                s3_path, s3_filename = utils.get_s3_target_path(o,
                                                                flattened_record,
                                                                key_properties[stream],
                                                                prefix=config.get('s3_filename_prefix'),
                                                                export_time=now,
                                                                path_specification=config.get('path_specification'))
                logger.info("Formatted s3 path: {}".format(s3_path + s3_filename))

            full_s3_target = s3_path + str(file_count_counters[filename]) + '_' + s3_filename

            if not (filename, full_s3_target) in filenames:
                filenames.append((filename, full_s3_target))

            file_size = os.path.getsize(filename) if os.path.isfile(filename) else 0
            if file_size >> 20 > file_size_counters[filename] and file_size >> 20 % 100 == 0:
                logger.info('file_size: {} MB, filename: {}'.format(round(file_size >> 20, 2), filename))
                file_size_counters[filename] = file_size_counters.get(filename, 0) + 10

            if file_size >> 20 > max_file_size_mb:
                logger.info('Max file size reached: {}, dumping to s3...'.format(max_file_size_mb))

                upload_to_s3(s3_client, config.get("s3_bucket"), filename, full_s3_target,
                             config.get("compression"),
                             config.get('encryption_type'),
                             config.get('encryption_key'))
                file_size = 0
                file_count_counters[filename] = file_count_counters.get(filename, 1) + 1
                if filename in headers:
                    del headers[filename]

            file_is_empty = file_size == 0
            if file_is_empty:
                logger.info('creating file: {}'.format(filename))

            with open(filename, 'a') as f:
                f.write(json.dumps(flattened_record))
                f.write('\n')
                # json.dump(flattened_record, f)

            # if filename not in headers and not file_is_empty:
            #     logger.info('(filename not in headers and not file_is_empty)')
            #     with open(filename, 'r') as csv_file:
            #         reader = csv.reader(csv_file,
            #                             delimiter=delimiter,
            #                             quotechar=quotechar)
            #         first_line = next(reader)
            #         headers[filename] = first_line if first_line else flattened_record.keys()
            # else:
            #     # logger.debug('setting headers: {}'.format(flattened_record.keys()))
            #     headers[filename] = flattened_record.keys()
            #
            # with open(filename, 'a') as csv_file:
            #     writer = csv.DictWriter(csv_file,
            #                             headers[filename],
            #                             extrasaction='raise',
            #                             delimiter=delimiter,
            #                             quotechar=quotechar)
            #     if file_is_empty:
            #         writer.writeheader()
            #
            #     writer.writerow(flattened_record)

            state = None
        elif message_type == 'STATE':
            logger.debug('Setting state to {}'.format(o['value']))
            state = o['value']
        elif message_type == 'SCHEMA':
            stream = o['stream']
            schemas[stream] = o['schema']
            if config.get('add_metadata_columns'):
                schemas[stream] = utils.add_metadata_columns_to_schema(o)

            schema = utils.float_to_decimal(o['schema'])
            validators[stream] = Draft4Validator(schema, format_checker=FormatChecker())
            key_properties[stream] = o['key_properties']
            filename = None
        elif message_type == 'ACTIVATE_VERSION':
            logger.debug('ACTIVATE_VERSION message')
        else:
            logger.warning("Unknown message type {} in message {}".format(o['type'], o))

    # Upload created CSV files to S3
    for filename, s3_target in filenames:
        upload_to_s3(s3_client, config.get("s3_bucket"), filename, s3_target,
                     config.get("compression"),
                     config.get('encryption_type'),
                     config.get('encryption_key'))

    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Config file')
    args = parser.parse_args()

    if args.config:
        with open(args.config) as input_json:
            config = json.load(input_json)
    else:
        config = {}

    config_errors = utils.validate_config(config)
    if len(config_errors) > 0:
        logger.error("Invalid configuration:\n   * {}".format('\n   * '.join(config_errors)))
        sys.exit(1)

    s3_client = s3.create_client(config)

    input_messages = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    state = persist_messages(input_messages, config, s3_client)

    emit_state(state)
    logger.debug("Exiting normally")


if __name__ == '__main__':
    main()