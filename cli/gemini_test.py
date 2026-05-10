"""
Teste rapido da configuracao Gemini usada pelo dashboard RAG.
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

PREFERRED_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
)


def normalize_model_name(model: str) -> str:
    model = model.strip()
    return model if model.startswith("models/") else f"models/{model}"


def list_generate_content_models(api_key: str) -> list[str]:
    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=30,
    )
    response.raise_for_status()
    models = response.json().get("models", [])
    return [
        model["name"]
        for model in models
        if "generateContent" in model.get("supportedGenerationMethods", [])
    ]


def choose_models(api_key: str) -> list[str]:
    configured = os.getenv("GEMINI_MODEL", "").strip()
    available = list_generate_content_models(api_key)
    candidates: list[str] = []

    if configured:
        configured_name = normalize_model_name(configured)
        if configured_name in available:
            candidates.append(configured_name)
        else:
            print(
                f"GEMINI_MODEL={configured} nao esta disponivel para generateContent. Buscando alternativa..."
            )

    available_suffixes = {name.removeprefix("models/"): name for name in available}
    for preferred in PREFERRED_MODELS:
        if preferred in available_suffixes:
            candidate = available_suffixes[preferred]
            if candidate not in candidates:
                candidates.append(candidate)

    if not candidates and not available:
        raise RuntimeError(
            "Nenhum modelo Gemini com generateContent disponivel para esta chave."
        )
    if not candidates:
        candidates.append(available[0])
    return candidates


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY nao configurada no ambiente ou .env.")

    try:
        models = choose_models(api_key)
        model = models[0]
        payload = None
        last_error: requests.HTTPError | None = None
        for candidate_model in models:
            model = candidate_model
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/{candidate_model}:generateContent",
                params={"key": api_key},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": "Responda em uma frase: Gemini configurado?"}
                            ]
                        }
                    ]
                },
                timeout=30,
            )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                last_error = exc
                status_code = (
                    exc.response.status_code if exc.response is not None else None
                )
                if status_code in {500, 502, 503, 504}:
                    continue
                raise
            payload = response.json()
            break
        if payload is None and last_error:
            raise last_error
    except requests.HTTPError as exc:
        status_code = (
            exc.response.status_code if exc.response is not None else "sem status"
        )
        body = exc.response.text[:800] if exc.response is not None else str(exc)
        print(f"Erro HTTP ao testar Gemini: {status_code}", file=sys.stderr)
        print(body.replace(api_key, "[GEMINI_API_KEY]"), file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(
            "Erro de rede ao testar Gemini. Verifique conexao/DNS/proxy e tente novamente.",
            file=sys.stderr,
        )
        print(str(exc).replace(api_key, "[GEMINI_API_KEY]"), file=sys.stderr)
        return 1

    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "") for part in parts).strip()

    print(f"OK: Gemini configurado com {model.removeprefix('models/')}")
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
