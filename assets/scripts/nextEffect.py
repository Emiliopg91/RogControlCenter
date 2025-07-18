#!/usr/bin/env python3
import urllib.request
import urllib.error


def main():
    url = "http://127.0.0.1:{{port}}/nextEffect"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("Request to nextEffect successful")
            else:
                print(f"Unexpected status code: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"HTTP error calling nextEffect: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"URL error calling nextEffect: {e.reason}")
    except Exception as e:
        print(f"General error calling nextEffect: {e}")


if __name__ == "__main__":
    main()
