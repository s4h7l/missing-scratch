"""Send a single public prompt, optionally with its PNG, to an allowlisted provider."""

import base64
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from .common import Problem

PROVIDERS = {
    "openai": ("https://api.openai.com/v1/chat/completions","OPENAI_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions","GEMINI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions","OPENROUTER_JUDGE_API_KEY"),
}


def models(provider):
    return sorted({m.strip() for m in os.getenv(f"MS_{provider.upper()}_MODELS","").split(",") if m.strip()})


def ready(provider, model):
    if provider not in PROVIDERS or model not in models(provider):
        raise Problem(422,"Model is outside the configured provider allowlist")
    if not os.getenv(PROVIDERS[provider][1]):
        raise Problem(503,"Provider access is not configured on this server")


def prompt(question, options):
    return question+"\nReply with exactly one option: "+", ".join(options)+"."


def parse(raw, options):
    token = raw.strip().upper() if isinstance(raw,str) else ""
    return token if token in options else None


def request_body(provider, model, mode, question, options, png, limit):
    text = prompt(question, options)
    content = [{"type":"text","text":text}]
    if mode=="vision":
        content.append({"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(png).decode()}})
    field = "max_completion_tokens" if provider=="openai" else "max_tokens"
    return {"model":model,"messages":[{"role":"user","content":content}],field:limit}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args):
        return None


def infer(provider,model,mode,question,options,png,limit):
    ready(provider,model)
    url,key = PROVIDERS[provider]
    payload=request_body(provider,model,mode,question,options,png,limit)
    req=Request(url, data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+os.environ[key],
                                                              "Content-Type":"application/json"})
    ts=time.monotonic()
    meta={"model_requested":model,"mode":mode,"max_output_tokens":limit}
    try:
        with build_opener(NoRedirect()).open(req,timeout=35) as res:
            data=res.read(1_048_577)
            if len(data)>1_048_576:
                raise ValueError("oversize")
        body=json.loads(data)
        message=body["choices"][0]["message"]
        raw=message.get("content")
        if not isinstance(raw,str):
            raw=""
        meta.update(request_id=body.get("id"),model_returned=body.get("model"),usage=body.get("usage",{}),
                    finish_reason=body["choices"][0].get("finish_reason"))
        status="ok" if parse(raw,options) else "invalid"
    except HTTPError as exc:
        raw,status="", "error"
        meta["error"]="provider_http_"+str(exc.code)
    except (URLError,OSError,TypeError,ValueError,KeyError,IndexError) as exc:
        raw,status="", "error"
        meta["error"]=type(exc).__name__
    meta["latency_ms"]=round(1000*(time.monotonic()-ts))
    return status,raw,parse(raw,options),meta
