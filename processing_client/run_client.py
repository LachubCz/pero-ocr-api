import os
import re
import cv2
import time
import zipfile
import requests
import argparse
import traceback
import numpy as np
import configparser
from urllib.request import Request, urlopen
from pathlib import Path

from pero_ocr.document_ocr.page_parser import PageParser
from pero_ocr.document_ocr.layout import PageLayout, create_ocr_processing_element
from pero_ocr.confidence_estimation import get_line_confidence

from helper import join_url


def get_args():
    """
    method for parsing of arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", help="Config path.")
    parser.add_argument("-a", "--api-key", help="API key.")
    parser.add_argument("-e", "--preferred-engine", dest="engine", help="Preferred engine ID.")
    parser.add_argument("--exit-on-done", action="store_true", help="Exit when no more data from server.")
    parser.add_argument("--time-limit", default=-1, type=float, help="Exit when runing longer than time-limit hours.")

    args = parser.parse_args()

    return args


def get_engine(config, headers, engine_id):
    r = requests.get(join_url(config['SERVER']['base_url'],
                              config['SERVER']['get_download_engine'],
                              str(engine_id)),
                     headers=headers)

    d = r.headers['content-disposition']
    filename = re.findall("filename=(.+)", d)[0]
    engine_name = filename[:-4].split('#')[0]
    engine_version = filename[:-4].split('#')[1]
    if not os.path.exists(os.path.join(config["SETTINGS"]['engines_path'], filename[:-4])):
        os.mkdir(os.path.join(config["SETTINGS"]['engines_path'], filename[:-4]))
        with open(os.path.join(config["SETTINGS"]['engines_path'], filename[:-4], filename), 'wb') as f:
            f.write(r.content)
        with zipfile.ZipFile(os.path.join(config["SETTINGS"]['engines_path'], filename[:-4], filename), 'r') as f:
            f.extractall(os.path.join(config["SETTINGS"]['engines_path'], filename[:-4]))

    engine_config = configparser.ConfigParser()
    engine_config.read(os.path.join(config["SETTINGS"]['engines_path'], filename[:-4], 'config.ini'))
    page_parser = PageParser(engine_config,
                             config_path=os.path.dirname(os.path.join(config["SETTINGS"]['engines_path'],
                                                                      filename[:-4],
                                                                      'config.ini')))
    return page_parser, engine_name, engine_version


def get_page_layout_text(page_layout):
    text = ""
    for line in page_layout.lines_iterator():
        text += "{}\n".format(line.transcription)
    return text


def get_score(page_layout):
    line_quantiles = []
    for line in page_layout.lines_iterator():
        if line.transcription is not None and line.transcription != "":
            char_map = dict([(c, i) for i, c in enumerate(line.characters)])
            c_idx = np.asarray([char_map[c] for c in line.transcription])

            confidences = get_line_confidence(line, c_idx)
            if confidences.size != 0:
                line_quantiles.append(np.quantile(confidences, .50))
    if not line_quantiles:
        return 1.0
    else:
        return np.quantile(line_quantiles, .50)


def main():
    args = get_args()

    start_time = time.time()

    config = configparser.ConfigParser()
    if args.config is not None:
        config.read(args.config)
    else:
        config.read('config.ini')

    Path(config['SETTINGS']['engines_path']).mkdir(parents=True, exist_ok=True)

    if args.api_key is not None:
        config["SETTINGS"]['api_key'] = args.api_key

    if args.engine is not None:
        config["SETTINGS"]['preferred_engine'] = args.preferred_engine

    with requests.Session() as session:
        headers = {'api-key': config['SETTINGS']['api_key']}
        page_parser, engine_name, engine_version = get_engine(config, headers, config["SETTINGS"]['preferred_engine'])

        while True:
            if args.time_limit > 0 and args.time_limit * 3600 < time.time() - start_time:
                break

            try:
                r = session.get(join_url(config['SERVER']['base_url'],
                                         config['SERVER']['get_processing_request'],
                                         config['SETTINGS']['preferred_engine']),
                                headers=headers)
            except requests.exceptions.ConnectionError:
                status = 'failed'
            else:
                request = r.json()
                status = request['status']

            if status == 'success':
                page_id = request['page_id']
                page_url = request['page_url']
                engine_id = request['engine_id']
                if engine_id != int(config['SETTINGS']['preferred_engine']):
                    page_parser, engine_name, engine_version = get_engine(config, headers, engine_id)
                    config['SETTINGS']['preferred_engine'] = str(engine_id)

                # Download image from url.
                try:
                    req = Request(page_url)
                    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11')
                    req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
                    if config['SERVER']['base_url'] in page_url:
                        req.add_header('api-key', config['SETTINGS']['api_key'])
                    page = urlopen(req).read()
                except:
                    exception = traceback.format_exc()
                    headers = {'api-key': config['SETTINGS']['api_key'],
                               'type': 'NOT_FOUND',
                               'engine-version': engine_version}
                    session.post(
                        join_url(config['SERVER']['base_url'], config['SERVER']['post_failed_processing'], page_id),
                        data=exception,
                        headers=headers)
                    continue


                # Decode image
                try:
                    encoded_img = np.frombuffer(page, dtype=np.uint8)
                    image = cv2.imdecode(encoded_img, flags=cv2.IMREAD_ANYCOLOR)
                    if len(image.shape) == 2:
                        image = np.stack([image, image, image], axis=2)
                except:
                    exception = traceback.format_exc()
                    headers = {'api-key': config['SETTINGS']['api_key'],
                               'type': 'INVALID_FILE',
                               'engine-version': engine_version}
                    session.post(
                        join_url(config['SERVER']['base_url'], config['SERVER']['post_failed_processing'], page_id),
                        data=exception,
                        headers=headers)
                    continue

                # Process image
                try:
                    page_layout = PageLayout(id=page_id, page_size=(image.shape[1], image.shape[0]))
                    page_layout = page_parser.process_page(image, page_layout)

                    headers = {'api-key': config['SETTINGS']['api_key'],
                               'engine-version': engine_version,
                               'score': str(get_score(page_layout))}

                    ocr_processing = create_ocr_processing_element(id="IdOcr",
                                                                   software_creator_str="Project PERO",
                                                                   software_name_str="{}" .format(engine_name),
                                                                   software_version_str="{}" .format(engine_version),
                                                                   processing_datetime=None)
                except:
                    exception = traceback.format_exc()
                    headers = {'api-key': config['SETTINGS']['api_key'],
                               'type': 'PROCESSING_FAILED',
                               'engine-version': engine_version}
                    session.post(
                        join_url(config['SERVER']['base_url'], config['SERVER']['post_failed_processing'], page_id),
                        data=exception,
                        headers=headers)
                    continue
                else:
                    session.post(join_url(config['SERVER']['base_url'], config['SERVER']['post_upload_results'], page_id),
                                 files={'alto': ('{}_alto.xml' .format(page_id), page_layout.to_altoxml_string(ocr_processing=ocr_processing), 'text/plain'),
                                        'page': ('{}_page.xml' .format(page_id), page_layout.to_pagexml_string(), 'text/plain'),
                                        'txt': ('{}.txt' .format(page_id), get_page_layout_text(page_layout), 'text/plain')},
                                 headers=headers)
            else:
                if args.exit_on_done:
                    break
                time.sleep(10)


if __name__ == '__main__':
    main()
