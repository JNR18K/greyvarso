"""Client LLM : FreeLLMAPI d'abord, fallback Pollinations. Sortie JSON robuste."""
import json
import re
import time
import requests

from .config import Config


class LLM:
    def __init__(self, cfg: Config, verbose=True):
        self.cfg = cfg
        self.verbose = verbose
        self.session = requests.Session()
        if cfg.ca_bundle:
            self.session.verify = cfg.ca_bundle

    def _endpoints(self):
        eps = []
        if self.cfg.llm_base_url:
            eps.append(("FreeLLMAPI", self.cfg.llm_base_url.rstrip("/") + "/chat/completions",
                        self.cfg.llm_api_key, self.cfg.llm_model))
        if self.cfg.fallback_llm_url:
            eps.append(("Pollinations", self.cfg.fallback_llm_url, "", self.cfg.fallback_llm_model))
        return eps

    def chat(self, system, user, temperature=0.9):
        last_err = None
        for name, url, key, model in self._endpoints():
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            body = {"model": model, "messages": [{"role": "system", "content": system},
                                                 {"role": "user", "content": user}]}
            if name != "Pollinations":
                body["temperature"] = temperature
            tries = 1 if "localhost" in url or "127.0.0.1" in url else 4
            for attempt in range(tries):
                try:
                    r = self.session.post(url, json=body, headers=headers, timeout=150)
                    r.raise_for_status()
                    content = r.json()["choices"][0]["message"]["content"]
                    if content and content.strip():
                        return content
                    last_err = f"{name}: réponse vide"
                except requests.HTTPError as e:
                    last_err = f"{name}: {e.response.status_code} {e.response.text[:150]}"
                except Exception as e:
                    last_err = f"{name}: {e}"
                    if isinstance(e, requests.ConnectionError) and tries == 1:
                        break
                if attempt + 1 < tries:
                    time.sleep(10 * (attempt + 1))
            if self.verbose:
                print(f"   ↪ {last_err[:110]} → fournisseur suivant…")
        raise RuntimeError(f"Aucun LLM disponible. Dernière erreur : {last_err}")

    def json(self, system, user, temperature=0.9, retries=3):
        system = system + "\n\nRéponds UNIQUEMENT avec du JSON valide, sans texte autour, sans ```."
        err = None
        for _ in range(retries):
            raw = self.chat(system, user, temperature)
            try:
                return parse_json(raw)
            except ValueError as e:
                err = e
                user = user + "\n\n(Ta réponse précédente n'était pas du JSON valide. Renvoie seulement le JSON.)"
        raise RuntimeError(f"JSON invalide après {retries} essais : {err}")


def parse_json(raw: str):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s, e = raw.find(open_c), raw.rfind(close_c)
        if s != -1 and e > s:
            try:
                return json.loads(raw[s:e + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("pas de JSON exploitable")
