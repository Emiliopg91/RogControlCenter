#!/usr/bin/env python3
import urllib.request
import urllib.error


def main():
    url = "http://127.0.0.1:{{port}}/nextProfile"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Request to nextProfile successful")
            else:
                print(f"Unexpected status code: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"HTTP error calling nextProfile: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"URL error calling nextProfile: {e.reason}")
    except Exception as e:
        print(f"General error calling nextProfile: {e}")


if __name__ == "__main__":
    main()
