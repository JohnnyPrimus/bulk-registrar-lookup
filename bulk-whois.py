import argparse
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

from age import NoIdentityMatchError, ScryptIdentity, decrypt_bytes

RATE_LIMIT      = 20   # req/min — Pro:40, Ultra:60, Scale/Mega:100, Atlas:900
DEFAULT_KEY_FILE = Path(__file__).with_name('api_key.age')


def load_api_key(password: str, api_key_file: Path) -> str:
    ciphertext = api_key_file.read_bytes()
    identity = ScryptIdentity(password)

    try:
        return decrypt_bytes(ciphertext, [identity]).decode().strip()
    except (NoIdentityMatchError, ValueError):
        raise SystemExit('Failed to decrypt API key: wrong password or corrupt key file')


def whois_lookup(session: requests.Session, domain: str, retries: int = 3) -> dict:
    query = urlencode({'domain': domain})
    url = f'https://whoisjson.com/api/v1/whois?{query}'

    for attempt in range(1, retries + 1):
        response = session.get(url, timeout=15)

        if response.status_code == 429:  # WHOIS rate limit: back off and retry
            time.sleep(2 ** attempt)
            continue

        response.raise_for_status()
        return response.json()

    raise RuntimeError(f'{domain}: exceeded retry limit')


def bulk_whois(session: requests.Session, domains: list[str]) -> list[dict]:
    results  = []
    interval = 60.0 / RATE_LIMIT  # seconds between requests

    for domain in domains:
        started_at = time.monotonic()

        try:
            data = whois_lookup(session, domain)
            results.append({
                'domain': domain,
                'registered': data.get('registered'),
                'registrar': data.get('registrar'),
                'created': data.get('created'),
                'expires': data.get('expires'),
                'source': data.get('source'),  # WHOIS or RDAP
            })
            print(f'[ok]  {domain}  source={data.get("source")}')
        except requests.RequestException as exc:
            results.append({'domain': domain, 'error': str(exc)})
            print(f'[err] {domain}: {exc}')

        elapsed = time.monotonic() - started_at
        if elapsed < interval:
            time.sleep(interval - elapsed)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Bulk WHOIS lookup via whoisjson.com')
    parser.add_argument('password', help='passphrase used to decrypt the age-encrypted API key')
    parser.add_argument('--api-key-file', type=Path, default=DEFAULT_KEY_FILE,
                         help=f'path to the age-encrypted API key (default: {DEFAULT_KEY_FILE.name})')
    parser.add_argument('domains', nargs='*', default=['example.com', 'github.com', 'google.com'])
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = load_api_key(args.password, args.api_key_file)
    session = requests.Session()
    session.headers['Authorization'] = f'TOKEN={api_key}'

    results = bulk_whois(session, args.domains)
    print(f'Done: {len(results)} lookups')


if __name__ == '__main__':
    main()
