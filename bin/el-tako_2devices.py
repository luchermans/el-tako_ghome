""" el-tako_2devices.py

    Read el-tako_home.json and convert to

    https://www.eltako.com/fileadmin/downloads/en/_main_catalogue/Gesamt-Katalog_ChT_gb_highRes.pdf
    FAM14 (pos 4)  FTS14EM, FUD14, FSR14  FSB14

    Version Date  Author	Comment
    V1.00 2023-03-24 LH     initial
"""

import json

def tako_2dev(id, tako):
    """  build googleh home device
    https://developers.home.google.com/cloud-to-cloud/intents/sync
    """
    name = tako['name']
    tako_id = f"{tako['group']}.{name}"
    dev = {"id": tako_id, "roomHint": tako['group'] ,"type": "action.devices.types.SWITCH"}
    dev["willReportState"] = True
    dev["name"] = {"name": name, "defaultNames": [name], "nicknames": [name]}
    dev["deviceInfo"] = {"manufacturer": "eltako", "model": tako['typ'],
                         "hwVersion": "1.0","swVersion": "1.0"}
    dev['traits'] = ["action.devices.traits.OnOff"]
    if tako['typ'] == 'FUD14':
        dev['traits'].append("action.devices.traits.Brightness")
    return dev


def convert_2ghome(tako_json, dev_json):
    # read  el-tako_home.json and convert to google home devices
    devices = []
    with open(tako_json, encoding='utf-8') as f:
        takos = json.load(f)
    for id, tako in takos.items():
        devices.append(tako_2dev(id, tako))
    with open(dev_json, 'w', encoding='utf-8') as f:
        json.dump(devices, f, ensure_ascii=False, indent=4)

"""-----------------------------------------------------------------------    
    M A I N
------------------------------------------------------------------------"""
if __name__ == '__main__':        # Run from command line
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--tako_json', '-t', default='el-tako_home.ini', help='el-tako home json file')
    parser.add_argument('--dev_json', '-d', default='devices.ini', help='google home devices json file')
    args = parser.parse_args()
    convert_2ghome(args.tako_json, args.dev_json)
