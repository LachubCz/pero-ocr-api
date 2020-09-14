import os
import cv2
import glob
import json
import shutil
import requests
import argparse
import subprocess
import configparser
import numpy as np

from client_helper import join_url, log_in, check_request
#from pero_ocr.document_ocr.layout import PageLayout
#from pero_ocr.document_ocr.page_parser import PageParser


def get_args():
    """
    method for parsing of arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", action="store", dest="config", help="config path")
    parser.add_argument("-d", "--document-id", action="store", dest="document_id", help="document id")
    parser.add_argument("-l", "--login", action="store", dest="login", help="username")
    parser.add_argument("-p", "--password", action="store", dest="password", help="password")

    args = parser.parse_args()

    return args


def send_data(session, file, base_url, url_path, headers):
    with open(file, "rb") as f:
        data = f.read()

    r = session.post(join_url(base_url, url_path),
                     files={'data': ('data.json', data, 'text/plain')},
                     headers=headers)
    print(r.content)

    if not check_request(r):
        print("FAILED")
        return False
    else:
        print("SUCCESFUL")
        return True


def post_processing_request(config):
    with requests.Session() as session:
        print()
        print("SENDING DATA TO SERVER")
        print("##############################################################")
        headers = {'api-key': config['SETTINGS']['api_key']}
        if not send_data(session, file=config['SETTINGS']['file'], base_url=config['SERVER']['base_url'], url_path=config['SERVER']['post_processing_request'], headers=headers):
            return False
        print("##############################################################")

        return True


def post_cancel_request(config):
    with requests.Session() as session:
        print()
        print("SENDING DATA TO SERVER")
        print("##############################################################")
        headers = {'api-key': config['SETTINGS']['api_key']}
        r = session.post(join_url(config['SERVER']['base_url'], config['SERVER']['post_cancel_request']), headers=headers)
        print(r.content)
        print("##############################################################")

        return True


def get_request_status(config):
    with requests.Session() as session:
        print()
        print("SENDING DATA TO SERVER")
        print("##############################################################")
        headers = {'api-key': config['SETTINGS']['api_key']}
        r = session.get(join_url(config['SERVER']['base_url'], config['SERVER']['get_request_status']), headers=headers)
        print(r.content)
        #if not send_data(session, file=config['SETTINGS']['file'], base_url=config['SERVER']['base_url'], url_path=config['SERVER']['post_processing_request'], headers=headers):
        #    return False
        print("##############################################################")

        return True


def get_ocr_systems(config):
    with requests.Session() as session:
        print()
        print("SENDING DATA TO SERVER")
        print("##############################################################")
        headers = {'api-key': config['SETTINGS']['api_key']}
        r = session.get(join_url(config['SERVER']['base_url'], config['SERVER']['get_ocr_systems']), headers=headers)
        print(r.content)
        #if not send_data(session, file=config['SETTINGS']['file'], base_url=config['SERVER']['base_url'], url_path=config['SERVER']['post_processing_request'], headers=headers):
        #    return False
        print("##############################################################")

        return True


def main():
    args = get_args()

    config = configparser.ConfigParser()
    if args.config is not None:
        config.read(args.config)
    else:
        config.read('config.ini')

    if args.document_id is not None:
        config["SETTINGS"]['document_id'] = args.document_id
    if args.login is not None:
        config["SETTINGS"]['api_key'] = args.login

    if config["SETTINGS"]['command'] == 'post_processing_request':
        if post_processing_request(config):
            print("REQUEST COMPLETED")
        else:
            print("REQUEST FAILED")
    elif config["SETTINGS"]['command'] == 'post_cancel_request':
        if post_cancel_request(config):
            print("REQUEST COMPLETED")
        else:
            print("REQUEST FAILED")
    elif config["SETTINGS"]['command'] == 'get_request_status':
        if get_request_status(config):
            print("REQUEST COMPLETED")
        else:
            print("REQUEST FAILED")
    elif config["SETTINGS"]['command'] == 'ocr_systems':
        if get_ocr_systems(config):
            print("REQUEST COMPLETED")
        else:
            print("REQUEST FAILED")


if __name__ == '__main__':
    main()
