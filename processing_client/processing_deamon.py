import time
import json
import requests
import argparse
import configparser

from helper import join_url


def get_args():
    """
    method for parsing of arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", help="Config path.")
    parser.add_argument("-a", "--api-key", help="API key.")

    args = parser.parse_args()

    return args


if __name__ == '__main__':
    args = get_args()

    config = configparser.ConfigParser()
    if args.config is not None:
        config.read(args.config)
    else:
        config.read('config.ini')

    if args.api_key is not None:
        config["SETTINGS"]['api_key'] = args.api_key

    headers = {'api-key': config['SETTINGS']['api_key']}

    previous = dict()
    while True:
        r = requests.get(join_url(config['SERVER']['base_url'],
                                  config['SERVER']['get_page_statistics']),
                         headers=headers)
        if r.status_code == 200:
            stats_dict = json.loads(r.text)
        else:
            time.sleep(10)
            continue

        engine_stats = stats_dict['engine_stats']
        for engine_id in engine_stats:
            try:
                previous_left = previous[engine_id]
            except KeyError:
                previous_left = 0

            if engine_stats[engine_id] > 10000:  # lot of pages in queue
                # run client for time
                pass
            elif previous_left == engine_stats[engine_id]:  # queue is not moving
                # run client for time
                pass

        previous = engine_stats
        time.sleep(600)
