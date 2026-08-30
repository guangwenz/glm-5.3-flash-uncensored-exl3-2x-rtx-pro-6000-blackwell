#!/usr/bin/env python3
"""Construct an exact native-token prompt and verify near-limit needle retrieval."""
from __future__ import annotations
import argparse,json,time,urllib.request

def post(base,path,payload,timeout):
    r=urllib.request.Request(base.rstrip('/')+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(r,timeout=timeout) as x: return json.load(x)
def count(base,model,content,timeout): return int(post(base,'/tokenize',{'model':model,'messages':[{'role':'user','content':content}]},timeout)['count'])
def build(base,model,target,needle,timeout):
    prefix='A passcode appears exactly once below. Ignore filler and reply with only the passcode.\nBEGIN'
    marker=f'\nPASSCODE: {needle}\n'; suffix='\nEND\nWhat is the passcode?'
    filler=max(0,target-count(base,model,prefix+marker+suffix,timeout)); got=-1
    for _ in range(12):
        left=filler//2; content=prefix+(' x'*left)+marker+(' x'*(filler-left))+suffix; got=count(base,model,content,timeout); filler+=target-got
        if got==target: return content,got
    raise RuntimeError(f'could not construct exactly {target} tokens; last={got}')
def main():
    p=argparse.ArgumentParser(); p.add_argument('--base-url',default='http://127.0.0.1:8000'); p.add_argument('--model',default='glm-5.3-flash-uncensored-exl3'); p.add_argument('--target',type=int,default=261875); p.add_argument('--needle',default='864219'); p.add_argument('--timeout',type=int,default=900); a=p.parse_args()
    if a.target+64>262144: raise SystemExit('target plus requested output exceeds 262144')
    content,n=build(a.base_url,a.model,a.target,a.needle,a.timeout); payload={'model':a.model,'messages':[{'role':'user','content':content}],'max_tokens':64,'temperature':0}
    t=time.time(); d=post(a.base_url,'/v1/chat/completions',payload,a.timeout); elapsed=round(time.time()-t,3); ans=(d['choices'][0]['message'].get('content') or '').strip(); usage=d.get('usage') or {}
    result={'target_prompt_tokens':a.target,'tokenize_count':n,'server_prompt_tokens':usage.get('prompt_tokens'),'answer':ans,'seconds':elapsed,'pass':ans==a.needle and usage.get('prompt_tokens')==a.target}
    print(json.dumps(result,indent=2)); raise SystemExit(0 if result['pass'] else 1)
if __name__=='__main__': main()
