""" el-tako_ghome.py

    Simple Home automation using Eltako Func Series 14
    https://www.eltako.com/fileadmin/downloads/en/_main_catalogue/Gesamt-Katalog_ChT_gb_highRes.pdf
    FAM14 (pos 4)  FTS14EM, FUD14, FSR14  FSB14

    Version Date  Author	Comment
    V1.00 2023-01-04 LH     initial thanks to https://github.com/ClusterM/google-assistant-smart-home
    V1.01 2023-01-13 LH     add switch turn_on, turn_off or toggle
"""
import time
import json
import jwt
import urllib
import argparse
import datetime
import uvicorn
import requests
from hashlib import sha256
from starlette.staticfiles import StaticFiles
from starlette.responses import Response, JSONResponse
from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends, Security, Body
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer

DEMO = 1
if DEMO:
    import speak_driver as drv
else:
    import eltako_home_driver as drv

VERSION = "0.0.1"
AUTHOR = "(c) 2023 LuHe"
APPNAME = "El-tako Google Home Assistent"
DEBUG = False
dev_stat = {}

ini = {
    "HTTP_PORT": 8088,
    "STATIC_DIR": "../www",
    "API_BASE": "",
    "TAKO_HOME_API": "http://127.0.0.1:8088/tako-home/api/switch",
    "MYHOME": "my home name",
    "DEVICES": "devices.json",
    "USERS": {"your username": "your_paswwoord_hash SHA256"},
    "GOOGLE": {
        "client_id": "google home client id",
        "client_secret": "google home client secret",
        "api_key": "google home API key"
    },
    "JWT": {
        "secret": "my-32-character-ultra-secure-and-ultra-long-secret",
        "algo": "HS256",
        "exp": 60 * 60 * 24
    },
    "DYNDNS_URL": "dyn dns update GET url https://www.duckdns.org/update?domains=yourdomain&token=yourtoken"
}


def log(*pars):
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], repr(pars))


def jwt_decode(token):
        try:
            tok = jwt.decode(token, ini['JWT']['secret'], algorithms=ini['JWT']['algo'], options={"verify_signature": True})
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=403, detail="Token expired")
        except:
            raise HTTPException(status_code=403, detail="Token invalid")
        if tok.get('myhone') != ini['MYHOME']:
            raise HTTPException(status_code=403, detail="Not my home")
        if tok.get('usr') not in ini['USERS']:
            raise HTTPException(status_code=403, detail="Wrong user")
        return tok


# --------------- WEB service --------------
route_ghome = APIRouter()


bearer_scheme = HTTPBearer(scheme_name="BearerAuth")
async def sec_access(token: str = Security(bearer_scheme)):
    return jwt_decode(token.credentials)


@route_ghome.post("/auth/", tags=["googhe smart home"], summary="Auth")
async def ghome_auth(req: Request):
    """ Authorization request from Google
    GET https://my.ghome.com/auth? client_id=GOOGLE_CLIENT_ID&redirect_uri=REDIRECT_URI&
        state=STATE_STRING&scope=REQUESTED_SCOPES&response_type=code&user_locale=LOCALE
    verify and redirect
    https://oauth-redirect.googleusercontent.com/r/YOUR_PROJECT_ID?code=AUTHORIZATION_CODE&state=STATE_STRING
    """
    headers = dict(req.headers)
    qpars = dict(req.query_params)
    fpars = await req.form()
    hash = sha256(fpars.get('psw','').encode('utf-8')).hexdigest()
    if ini['USERS'].get(fpars.get('usr')) != hash:
        raise HTTPException(status_code=403, detail="wrong username or password")
    if qpars.get("client_id") != ini['GOOGLE']['client_id'] \
            or 'state' not in qpars \
            or 'redirect_uri' not in qpars \
            or qpars.get('response_type') != "code":
        log("Invalid auth", {'remote': req.client.host, 'url': req.url, 'headers': headers})
        raise HTTPException(status_code=400, detail="Invalid request")

    tok = {'usr': fpars['usr'], 'myhone': ini['MYHOME'], 'exp': int(time.time()) + 30}  # expires in 30 sec
    token = jwt.encode(tok, ini['JWT']['secret'], algorithm=ini['JWT']['algo'])
    params = {'state': qpars['state'], 'code': token, 'client_id': qpars['client_id']}
    params['client_secret'] = ini['GOOGLE']['client_secret']    # TODO remove
    print(token)
    log('Access granted', {'remote': req.client.host, 'url': req.url, 'headers': headers})
    redir_url = qpars['redirect_uri'] + '?' + urllib.parse.urlencode(params)
    return RedirectResponse(redir_url, status_code=303)


@route_ghome.get("/token", tags=["googhe smart home"], summary="Token")
@route_ghome.post("/token", tags=["googhe smart home"], summary="Token")
async def ghome_token(req: Request):
    headers = dict(req.headers)
    fpars = await req.form()
    if not fpars:
        fpars = dict(req.query_params)
    if fpars.get("client_id") != ini['GOOGLE']['client_id'] \
            or fpars.get("client_secret") != ini['GOOGLE']['client_secret']:
        log("Auth client invalid", {'remote': req.client.host, 'url': req.url, 'headers': headers})
        raise HTTPException(status_code=400, detail="Auth client invalid")
    tok = jwt_decode(fpars.get('code', fpars.get('refresh_token','')))
    if tok.get('usr') not in ini['USERS']:
        raise HTTPException(status_code=403, detail="Auth token invalid user")
    tok['exp'] = int(time.time()) + 60 * 60 * 24  # 1 day
    token = jwt.encode(tok, ini['JWT']['secret'], algorithm=ini['JWT']['algo'])
    log('Token granted', {'remote': req.client.host, 'tok': tok})
    resp = {"token_type": "Bearer", "access_token": token, "refresh_token": token, "expires_in": 60*60*24}
    return JSONResponse(resp)

# example post data see https://developers.home.google.com/cloud-to-cloud/integration/query-execute
# https://developers.home.google.com/reference/home-graph/rest
EXAMPLE_POST_DATA = {
    "requestId": "som_id",
    "inputs":[{
        "intent": "action.devices.EXECUTE",
        "payload": {
           "commands":[{
              "devices": [{"id": "Living.TV"}, {"id": "Keuken.LED"}],
              "execution": [{
                  "command": "action.devices.commands.OnOff",
                  "params": {"on": True}
              }]
           }]
        }
    }]
}

@route_ghome.post("/", tags=["googhe smart home"], summary="Google Assistant")
async def ghome_fullfit(req: Request, post_data: dict = Body(..., example=EXAMPLE_POST_DATA), tok: str=Depends(sec_access)):
    log('fullfit', {'remote': req.client.host, 'post_data': post_data})
    res = {'requestId': post_data.get('requestId')}
    inputs = post_data.get('inputs', [])
    for inp in inputs:
        payload = inp.get('payload', {})
        intent = inp.get('intent')

        if intent == "action.devices.SYNC":     # return devices list
            res['payload'] = {"agentUserId": tok['usr'], "devices": devices}

        if intent == "action.devices.QUERY":    # return device status
            res['payload'] = {"devices": {}}
            for dev in payload.get('devices', []):
                id = dev['id']
                res['payload']['devices'][id] = dev_stat.get(id, {"online": False, "on": False})

        if intent == "action.devices.EXECUTE":      # Execute a command
            res['payload'] = {'commands': []}
            for cmd in payload.get('commands', {}):
                for dev in cmd.get('devices', {}):
                    id = dev['id']
                    if id not in dev_stat:
                        res['payload']['commands'].append({"ids": [id], "status": "ERROR", "errorCode": "deviceMotFound"})
                        continue
                    for exe in cmd['execution']:
                        exe_cmd = exe.get('command')
                        pars = exe.get('params', {})
                        if exe_cmd == 'action.devices.commands.OnOff':
                            dev_stat[id]['on'] = pars.get('on', False)
                            drv.switch(id, dev_stat[id]['on'])
                        if exe_cmd == 'action.devices.commands.BrightnessAbsolute' or \
                           exe_cmd == 'action.devices.commands.BrightnessRelative':
                            br = dev_stat[id].get('brightness', 0)
                            dev_stat[id]['brightness'] = pars.get('brightness', pars.get('brightnessRelativePercent', br))
                            drv.brightness(id, dev_stat[id]['brightness'])
                        res['payload']['commands'].append({"ids": [id], "status": "SUCCESS", "states": dev_stat[id]})

        if intent == "action.devices.DISCONNECT":   # Disconnect user
            log('Disconnect', {'remote': req.client.host, 'tok': tok})
            return {}

    return JSONResponse(res)


@route_ghome.get("/resync", tags=["googhe smart home"], summary="Google Assistant")
async def ghome_fullfit(req: Request, username: str, tok: str=Depends(sec_access)):
    r = await re_sync(username)
    return Response(content=r.content, status_code=r.status_code, headers=r.headers)


def fastapi_run(ini):
    # init fastAPI
    app = FastAPI(title=APPNAME, version=VERSION)
    # app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    #                    allow_methods=["*"], allow_headers=["*"])
    # IMPORTANT include routes in order (first included is first checked)
    app.include_router(route_ghome, prefix=f"{ini['API_BASE']}")
    if 'STATIC_DIR' in ini:   # LAST route to include
        app.mount("/", StaticFiles(directory=ini['STATIC_DIR'], html=True), name="static")
    # run main service
    log(f"Docs http://127.0.0.1:{ini['HTTP_PORT']}/auth")
    log(f"Docs http://127.0.0.1:{ini['HTTP_PORT']}/docs")
    uvicorn.run(app, host='0.0.0.0', port=ini['HTTP_PORT'])
    log(f"ERROR: fastapi stopped: http port:{ini['HTTP_PORT']}")


def re_sync(usr):
    url = "https://homegraph.googleapis.com/v1/devices:requestSync?key=" + ini['GOOGLE']['api_key']
    r = requests.post(url, data=json.dumps({"agentUserId": usr}))
    return r


"""-----------------------------------------------------------------------    
    M A I N
------------------------------------------------------------------------"""
if __name__ == '__main__':        # Run from command line
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', default='el-tako_ghome.ini', help='config file')
    parser.add_argument('--debug', '-d', default=False, action='store_true')
    parser.add_argument('--sync', '-s', default=None, help='re sync devices for user, example: -s username')
    args = parser.parse_args()
    if args.debug:
        DEBUG = True
    with open(args.config, encoding='utf-8') as f:
        ini_rd = json.load(f)
    ini.update(ini_rd)
    drv.init(ini['TAKO_HOME_API'])

    # read device config
    with open(ini['DEVICES'], encoding='utf-8') as f:
        devices = json.load(f)
    for dev in devices:
        dev_stat[dev['id']] =  {"online": True, "on": False}
        if "action.devices.traits.Brightness" in dev['traits']:
            dev_stat[dev['id']]["brightness"] = 0
            # build and print a test token
    usr = list(ini['USERS'].keys())[0]
    tok = {'usr': usr, 'myhone': ini['MYHOME'], 'exp': int(time.time()) + 60*60*12}  # expires in 10 sec
    print('test TOKEN:', jwt.encode(tok, ini['JWT']['secret'], algorithm=ini['JWT']['algo']))

    fastapi_run(ini)
