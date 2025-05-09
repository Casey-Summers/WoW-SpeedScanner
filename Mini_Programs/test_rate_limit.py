import os
import time
import requests
from dotenv import load_dotenv

# === Setup ===
REGION = 'us'
TEST_ENDPOINT = f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/index"

load_dotenv()
CLIENT_ID = os.getenv('BLIZZARD_CLIENT_ID')
CLIENT_SECRET = os.getenv('BLIZZARD_CLIENT_SECRET')


def get_token():
    """Requests a new token from Blizzard API using client credentials."""
    url = 'https://oauth.battle.net/token'
    data = {'grant_type': 'client_credentials'}
    resp = requests.post(url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    resp.raise_for_status()
    j = resp.json()
    return j['access_token']


def benchmark_rate_limit(token, max_test_rps=100):
    """
    Benchmarks the max safe request-per-second rate before hitting 429 errors.

    Args:
        token (str): Blizzard OAuth token.
        max_test_rps (int): Max RPS to try before bailing out.

    Returns:
        float: Safe delay (in seconds) between requests.
    """
    headers = {'Authorization': f'Bearer {token}'}
    params = {'namespace': f'dynamic-{REGION}', 'locale': 'en_US'}
    session = requests.Session()
    session.headers.update(headers)

    print("🔬 Benchmarking safe Blizzard API request rate...")
    rps_safe = 0

    for test_rps in range(1, max_test_rps + 1):
        successes = 0
        failures = 0
        start = time.time()

        for _ in range(test_rps):
            try:
                resp = session.get(TEST_ENDPOINT, params=params)
                if resp.status_code == 429:
                    failures += 1
                    break  # Immediate break on rate-limit
                elif resp.status_code != 200:
                    failures += 1
                else:
                    successes += 1
            except Exception:
                failures += 1

        elapsed = time.time() - start
        actual_rps = successes / elapsed if elapsed > 0 else 0
        print(f"  ▶️ {test_rps} attempted => {successes} success / {failures} fail ({elapsed:.2f}s) | Actual RPS: {actual_rps:.2f}")

        if failures > 0:
            break
        else:
            rps_safe = test_rps

    if rps_safe == 0:
        print("❌ No safe request rate found. Try lowering test range.")
        return 1.0

    buffer_ratio = 0.85
    safe_delay = 1.0 / (rps_safe * buffer_ratio)
    print(f"\n✅ Max Attempted: {rps_safe} | Buffered delay: {safe_delay:.3f} seconds/request")
    return round(safe_delay, 3)


if __name__ == "__main__":
    token = get_token()
    delay = benchmark_rate_limit(token)
