#!/usr/bin/env python3
"""No-dependency health, text, native tool-call, and semantic image verification."""
from __future__ import annotations
import argparse,base64,binascii,json,struct,time,urllib.request,zlib

def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',binascii.crc32(kind+data)&0xffffffff)
def make_png():
    w=h=256; pix=bytearray([255]*(w*h*3)); cx=cy=128; r=72
    for y in range(h):
        for x in range(w):
            if (x-cx)**2+(y-cy)**2 <= r*r: pix[(y*w+x)*3:(y*w+x)*3+3]=bytes((20,80,230))
    raw=b''.join(b'\0'+bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
def req(base,path,payload=None,timeout=300):
    data=None if payload is None else json.dumps(payload).encode(); r=urllib.request.Request(base.rstrip('/')+path,data=data,headers={'Content-Type':'application/json'}); t=time.time()
    with urllib.request.urlopen(r,timeout=timeout) as x: body=json.load(x) if x.headers.get_content_type()=='application/json' else x.read().decode()
    return body,round(time.time()-t,3)
def answer(d): return (d['choices'][0]['message'].get('content') or '').strip()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base-url',default='http://127.0.0.1:8000'); ap.add_argument('--model',default='glm-5.3-flash-uncensored-exl3'); a=ap.parse_args(); out={}
    d,dt=req(a.base_url,'/v1/models'); advertised=next((m for m in d.get('data',[]) if m.get('id')==a.model),{}); out['model']={'pass':advertised.get('max_model_len')==262144,'advertised':advertised,'seconds':dt}
    p={'model':a.model,'messages':[{'role':'user','content':'Reply with exactly TEXT_OK'}],'max_tokens':64,'temperature':0}
    d,dt=req(a.base_url,'/v1/chat/completions',p); ans=answer(d); out['text']={'pass':ans=='TEXT_OK','answer':ans,'seconds':dt}
    p={'model':a.model,'messages':[{'role':'user','content':'Call record_value immediately with value TOOL_OK.'}],'tools':[{'type':'function','function':{'name':'record_value','description':'Record a value','parameters':{'type':'object','properties':{'value':{'type':'string'}},'required':['value']}}}],'max_tokens':256,'temperature':0}
    d,dt=req(a.base_url,'/v1/chat/completions',p); calls=d['choices'][0]['message'].get('tool_calls') or []
    try: ok=bool(calls) and json.loads(calls[0]['function']['arguments']).get('value')=='TOOL_OK'
    except Exception: ok=False
    out['tool']={'pass':ok,'tool_calls':calls,'seconds':dt}
    image=base64.b64encode(make_png()).decode(); p={'model':a.model,'messages':[{'role':'user','content':[{'type':'text','text':'Identify the colored shape. Answer with exactly two lowercase words: the color, then the shape.'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+image}}]}],'max_tokens':128,'temperature':0}
    d,dt=req(a.base_url,'/v1/chat/completions',p); ans=answer(d).lower().strip(' .'); out['vision']={'pass':ans=='blue circle','answer':ans,'seconds':dt}
    print(json.dumps(out,indent=2)); raise SystemExit(0 if all(v['pass'] for v in out.values()) else 1)
if __name__=='__main__': main()
