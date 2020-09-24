import os
import time
import json
import urllib.request
import io
import PIL.Image as Image
import requests
import argparse
import configparser
import numpy as np

from pero_ocr.document_ocr.page_parser import PageParser
from pero_ocr.document_ocr.layout import PageLayout


def get_args():
    """
    method for parsing of arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", action="store", dest="config", help="Config path.")
    parser.add_argument("-a", "--api-key", action="store", dest="api", help="API key.")
    parser.add_argument("-e", "--preferred-engine", action="store", dest="engine", help="Preferred engine ID.")

    args = parser.parse_args()

    return args


def join_url(*paths):
    final_paths = []
    first_path = paths[0].strip()
    if first_path[-1] == '/':
        first_path = first_path[:-1]
    final_paths.append(first_path)
    for path in paths[1:]:
        final_paths.append(path.strip().strip('/'))
    return '/'.join(final_paths)


def get_engine_by_id(engines_declaration, engine_id):
    for engine in engines_declaration['engines']:
        if int(engine["engine_id"]) == int(engine_id):
            return engine


def main():
    args = get_args()

    config = configparser.ConfigParser()
    if args.config is not None:
        config.read(args.config)
    else:
        config.read('config.ini')

    if args.api is not None:
        config["SETTINGS"]['api_key'] = args.api

    if args.engine is not None:
        config["SETTINGS"]['preferred_engine'] = args.preferred_engine

    with open(config["SETTINGS"]['engines_declaration']) as json_file:
        engines = json.load(json_file)
    engine = get_engine_by_id(engines, config["SETTINGS"]['preferred_engine'])

    engine_config = configparser.ConfigParser()
    engine_config.read(engine["versions"][-1]["path_to_config"])
    page_parser = PageParser(engine_config, config_path=os.path.dirname(engine["versions"][-1]["path_to_config"]))

    with requests.Session() as session:
        while True:
            headers = {'api-key': config['SETTINGS']['api_key']}
            r = session.get(join_url(config['SERVER']['base_url'],
                                     config['SERVER']['get_processing_request'],
                                     config["SETTINGS"]['preferred_engine']),
                            headers=headers)
            request = r.json()
            status = request['status']
            page_id = request['page_id']
            page_url = request['page_url']
            engine_id = request['engine_id']

            if status == 'success':
                if engine_id != int(engine["engine_id"]):
                    engine = get_engine_by_id(engines, engine_id)
                    engine_config.read(engine["versions"][-1]["path_to_config"])
                    page_parser = PageParser(engine_config,
                                             config_path=os.path.dirname(engine["versions"][-1]["path_to_config"]))

                page = urllib.request.urlopen(page_url).read()
                stream = io.BytesIO(page)
                pil_image = Image.open(stream)

                open_cv_image = np.array(pil_image)
                open_cv_image = open_cv_image[:, :, ::-1].copy()

                page_layout = PageLayout(id=page_id, page_size=(pil_image.size[1], pil_image.size[0]))
                page_layout = page_parser.process_page(open_cv_image, page_layout)

                headers = {'api-key': config['SETTINGS']['api_key'],
                           'engine-version': engine["versions"][-1]['version_id'],
                           'score': '100'}

                session.post(join_url(config['SERVER']['base_url'], config['SERVER']['post_upload_results'], page_id),
                             files={'data': ('{}.xml' .format(page_id), page_layout.to_pagexml_string(), 'text/plain')},
                             headers=headers)
            else:
                time.sleep(10)


if __name__ == '__main__':
    main()
