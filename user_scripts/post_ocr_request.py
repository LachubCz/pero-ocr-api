# Based on: https://app.swaggerhub.com/apis-docs/LachubCz/PERO-API/1.0.1#/ by Michal Hradiš.
# For running the script you need to get the api key.
# First enter the link with data.
# Second enter the resulting format (alto, txt, page)

import requests
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--api-url', type=str, help='API URL', required=True)
    parser.add_argument('-a', '--api-key', type=str, help='API key', required=True)
    parser.add_argument('-e', '--engine-id', type=int, help='OCR engine ID', required=True)
    parser.add_argument('-l', '--url-list', type=str, help='File with name, url ', required=True)
    args = parser.parse_args()
    return args


def create_request_dict(engine_id, url_file):
    request_dict = {"engine": engine_id, "images": {}}
    with open(url_file, 'r') as f:
        for i, line in enumerate(f):
            words = line.split()
            img_url = words[0]
            if len(words) == 1:
                img_name = f'{i:03d}'
            elif len(words) >= 2:
                img_name = ' '.join(words[1:])
            request_dict['images'][img_name] = img_url

    return request_dict


def get_available_engines(server_url, api_key):
    r = requests.get(f"{server_url}/get_engines", headers={"api-key": api_key})
    if r.status_code != 200:
        print(f'ERROR: Failed to get available OCR engine list. Code: {r.status_code}')
        exit(-1)

    result = r.json()
    if result['status'] not in ["success", "succes"]:
        print(f'ERROR: Failed to get available OCR engine list. Status: {result["status"]}')
        exit(-1)

    return result['engines']


def post_request(server_url, api_key, request_dict):
    r = requests.post(f"{server_url}/post_processing_request",
                      json=request_dict,
                      headers= {"api-key": api_key, "Content-Type": "application/json"})

    if r.status_code == 404:
        print(f'ERROR: Requested engine was not found on server.')
        exit(-1)
    if r.status_code == 422:
        print(f'ERROR: Request JSON has wrong format.')
        exit(-1)
    if r.status_code != 200:
        print(f'ERROR: Request returned with unexpected status code: {r.status_code}')
        exit(-1)

    response = r.json()

    if response['status'] != "success":
        print(f'ERROR: Request status is wrong: {response["status"]}')
        print(response)
        exit(-1)

    return response['request_id']


def main():
    args = parse_arguments()

    engines = get_available_engines(args.api_url, args.api_key)

    engine_available = False
    print('Available OCR engines:')
    for engine in engines:
        print(engines[engine]['id'], engine, engines[engine]['description'])
        if args.engine_id == engines[engine]['id']:
            args.engine_id = engine
        if args.engine_id == engine:
            engine_available = True

    if not engine_available:
        print(f'ERROR: Requested engine "{args.engine_id}" is not available.')
        exit(-1)

    print('Using OCR engine:', engines[args.engine_id]['id'], args.engine_id, engines[args.engine_id]['description'])

    #request_dict = create_request_dict(engines[args.engine_id]['id'], args.url_list)
    #request_id = post_request(args.api_url, args.api_key, request_dict)
    print('OCR request successfully submitted with id:', request_id)


if __name__ == "__main__":
    main()
