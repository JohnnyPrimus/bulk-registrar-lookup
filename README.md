# bulk-registrar-lookup

A small CLI tool that looks up the registrar (and other WHOIS/RDAP data) for a
list of domains via the [whoisjson.com](https://whoisjson.com) API, respecting
that API's rate limit, and writes the results to a CSV file.

Over time I found that while I still had DNS records for domains I owned, there was no
clear list of where they were registered. Moreover, I had let at least a few of the domains 
lapse, so I wanted to get a list of domain, where (or whether) it was still registered, and if
not, whether it could be reacquired.

The whoisjson.com API key is kept encrypted at rest using
[age](https://age-encryption.org) (scrypt/passphrase mode), so it's safe to
commit `api_key.age` to a private repo without exposing the key in plaintext.

## How it works

1. You provide a plain-text file with one domain per line.
2. The script decrypts `api_key.age` with a passphrase you supply to recover
   the whoisjson.com API key.
3. It queries the WHOIS/RDAP data for each domain, pausing between requests to
   stay under the configured rate limit (default 20 requests/minute).
4. Results (`domain`, `registrar`) are written to a CSV file.

## Requirements

- Python 3.11+
- Dependencies from `requirements.txt`:
  ```
  pip install -r requirements.txt
  ```
- A whoisjson.com API key ([sign up here](https://whoisjson.com))

## Setup

### 1. Encrypt your API key

Create the encrypted key file using the `age` module (installed via
`python_age`). This will prompt you for a passphrase to protect the key:

```
python -m age -p -o api_key.age
```

Paste your whoisjson.com API key, then press Enter followed by Ctrl+D (or
Ctrl+Z on Windows) to finish, and enter a passphrase when prompted.

By default, the script looks for `api_key.age` next to `bulk-whois.py`. Keep
this passphrase — you'll need it every time you run the tool.

`api_key.age` is excluded from git via `.gitignore`, so it won't be
accidentally committed, but if you so choose, it is safe to check in since it's encrypted.

### 2. Create your domains file

Create a plain text file with one domain per line, e.g. `domains.txt` that you intend to lookup (ICANN/RDAP):

```
example.com
another-example.org
```

## Usage

```
python bulk-whois.py <passphrase> <domains_file> [--api-key-file PATH] [--output PATH]
```

### Arguments

| Argument | Description |
|---|---|
| `password` | Passphrase used to decrypt `api_key.age` |
| `domains_file` | Path to a file with one domain per line |
| `--api-key-file` | Path to the encrypted API key file (default: `api_key.age`) |
| `--output` | Path to write the results CSV (default: `results.csv`) |

### Example

```
python bulk-whois.py mypassphrase domains.txt --output results.csv
```

Output (`results.csv`):

```
domain,registrar
example.com,RESERVED-Internet Assigned Numbers Authority
another-example.org,Some Registrar Inc.
```

Progress is also printed to the console as each domain is looked up:

```
[ok]  example.com  source=RDAP
[err] bad-domain.tld: 404 Client Error: Not Found
```

## Notes

- The rate limit (`RATE_LIMIT` in `bulk-whois.py`) defaults to 20
  requests/minute (whoisjson.com's free tier). Adjust it in the source if
  your plan allows a higher rate (Pro: 40, Ultra: 60, Scale/Mega: 100,
  Atlas: 900). They may or may not have a daily rate imposed as well, I only tested
  to a few hundred and it worked fine.
- On a `429` (rate limited) response, the script backs off exponentially and
  retries, up to 3 attempts per domain. (This is the basic cool-down implemented to comply with whoisjson's rate limit)
- Domains that fail to look up are still recorded in the results (with an
  empty `registrar` field); the error is printed to the console.
