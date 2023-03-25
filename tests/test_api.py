import json
import requests

GHOME_API = 'http://127.0.0.1:5000'


def api_post(sample_json):
    print(f'POST {sample_json}')
    with open(sample_json, encoding='utf-8') as f:
        jos = json.load(f)
    r = requests.post(GHOME_API, json=jos, headers=headers)
    print('RESP:', r.json())
    return r


def test_query():
    r = api_post('query_sample.json')


def test_exec():
    r = api_post('exec_sample.json')


if __name__ == '__main__':        # Test rom command line
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', '-t', default='test TOKEN from el-tako_ghome.py console')
    args = parser.parse_args()
    headers = {'Authorization': f'Bearer {args.token}'}
    test_query()
    test_exec()
