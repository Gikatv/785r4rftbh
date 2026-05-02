import argparse
import base64
import json
import os
import re
import sys
from urllib.parse import urlparse

import requests
from pywidevine.pssh import PSSH
from pywidevine.device import Device
from pywidevine.cdm import Cdm


class ComplexJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_json'):
            return o.to_json()
        return super().default(o)


class LicenseChallenge:
    def __init__(self, otp: str, playback_info: str, href: str, tech: str, license_request: str):
        self.otp = otp
        self.playback_info = playback_info
        self.href = href
        self.tech = tech
        self.license_request = license_request

    def to_json(self):
        resp = {}
        if self.otp:
            resp['otp'] = self.otp
        if self.playback_info:
            resp['playbackInfo'] = self.playback_info
        if self.href:
            resp['href'] = self.href
        if self.tech:
            resp['tech'] = self.tech
        if self.license_request:
            resp['licenseRequest'] = self.license_request
        return resp


def get_video_id(token: str) -> str:
    try:
        decoded = json.loads(base64.b64decode(token))
        playback_info = decoded['playbackInfo']
        return json.loads(base64.b64decode(playback_info))['videoId']
    except Exception as e:
        print(f"Error extracting video ID: {e}")
        sys.exit(1)


def get_video_reference(token: str) -> str:
    try:
        return json.loads(base64.b64decode(token))['href']
    except Exception as e:
        print(f"Error extracting video reference: {e}")
        sys.exit(1)


def get_mpd(video_id: str) -> str:
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'origin': 'https://dev.vdocipher.com/',
        'referer': 'https://dev.vdocipher.com/'
    }

    url = f'https://dev.vdocipher.com/api/meta/{video_id}'

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data['dash']['manifest']
    except requests.exceptions.RequestException as e:
        print(f"Failed to get MPD: {e}")
        if 'resp' in locals():
            print("Response:", resp.text)
        sys.exit(1)
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Invalid response from meta API: {e}")
        sys.exit(1)


def get_pssh(mpd_url: str) -> str:
    try:
        resp = requests.get(mpd_url, timeout=15)
        resp.raise_for_status()
        match = re.search(r'<cenc:pssh>(.*?)</cenc:pssh>', resp.text)
        if match:
            return match.group(1)
        else:
            print("PSSH not found in MPD")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to get PSSH: {e}")
        sys.exit(1)


def get_license_response(license_challenge: str, mpd: str, video_reference: str) -> str:
    origin_url = urlparse(mpd)
    base_url = f"{origin_url.scheme}://{origin_url.hostname}"

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'origin': base_url,
        'referer': base_url + '/',
        'vdo-ref': video_reference
    }

    try:
        resp = requests.post(
            'https://license.vdocipher.com/auth',
            json={'token': license_challenge},
            headers=headers,
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()['license']
    except requests.exceptions.RequestException as e:
        print(f"Failed to get license: {e}")
        if 'resp' in locals():
            print("Response:", resp.text)
        sys.exit(1)


def setup_license_challenge(token: str, challenge: bytes) -> str:
    try:
        decoded_token = json.loads(base64.b64decode(token))

        license_challenge_obj = LicenseChallenge(
            otp=decoded_token.get('otp', ''),
            playback_info=decoded_token.get('playbackInfo', ''),
            href=decoded_token.get('href', ''),
            tech=decoded_token.get('tech', ''),
            license_request=base64.b64encode(challenge).decode('utf-8')
        )

        raw_json = json.dumps(license_challenge_obj.to_json(), cls=ComplexJsonEncoder)
        return base64.b64encode(raw_json.encode('utf-8')).decode('utf-8')

    except Exception as e:
        print(f"Error creating license challenge: {e}")
        sys.exit(1)


def create_argument_parser():
    parser = argparse.ArgumentParser(description='Vdocipher Widevine Downloader')
    parser.add_argument('--wvd', required=True, help='Path to .wvd file (pywidevine device)')
    parser.add_argument('--token', required=True, help='Vdocipher auth token')
    return parser.parse_args()


def main():
    args = create_argument_parser()

    print("Starting Vdocipher decryption...")

    video_ref = get_video_reference(args.token)
    video_id = get_video_id(args.token)

    print(f"Video ID     : {video_id}")
    print(f"Video Ref    : {video_ref[:60]}...")

    mpd = get_mpd(video_id)
    print(f"MPD URL      : {mpd}")

    pssh_b64 = get_pssh(mpd)
    print("PSSH found.")

    # Widevine CDM Setup
    device = Device.load(args.wvd)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()

    try:
        cdm.set_service_certificate(session_id, cdm.common_privacy_cert)

        challenge = cdm.get_license_challenge(
            session_id, 
            PSSH(pssh_b64), 
            privacy_mode=True
        )

        license_challenge_b64 = setup_license_challenge(args.token, challenge)
        license_response = get_license_response(license_challenge_b64, mpd, video_ref)

        cdm.parse_license(session_id, license_response)

        # Print Keys
        terminal_width = os.get_terminal_size().columns
        print('\n' + '*' * terminal_width)
        print("DECRYPTION KEYS FOUND:")
        
        content_keys = [key for key in cdm.get_keys(session_id) if key.type == 'CONTENT']
        
        for key in content_keys:
            print(f"[{key.type}] {key.kid.hex}:{key.key.hex()}")

        if not content_keys:
            print("No CONTENT keys found!")

        print(f"\n[ MPD ] {mpd}")
        print('*' * terminal_width)

    finally:
        cdm.close(session_id)


if __name__ == '__main__':
    main()