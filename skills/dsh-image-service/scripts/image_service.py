"""Configurable images API adapter. Standard library only; no secret logging."""
import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

LIMIT = 64 * 1024 * 1024


def endpoint(value, allow_local=False):
    u = urllib.parse.urlsplit(value)
    if not u.hostname or u.username or u.password or u.fragment:
        raise ValueError('Endpoint must be an absolute URL without embedded credentials or fragment')
    if u.scheme != 'https' and not (allow_local and u.scheme == 'http' and u.hostname in ('localhost', '127.0.0.1', '::1')):
        raise ValueError('HTTPS is required (loopback HTTP requires --allow-local)')
    return value


def load_config(path, allow_local=False):
    config = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict):
        raise ValueError('Configuration must be an object')
    for key in ('generationUrl', 'model', 'apiKeyEnv'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError('Configure ' + key)
    endpoint(config['generationUrl'], allow_local)
    if config.get('editUrl'):
        endpoint(config['editUrl'], allow_local)
    options = config.get('requestOptions', {})
    if not isinstance(options, dict) or set(options) & {'prompt', 'model', 'n', 'size', 'image', 'mask'}:
        raise ValueError('requestOptions must be an object without reserved request fields')
    timeout = config.get('timeoutSeconds', 180)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 600:
        raise ValueError('timeoutSeconds must be between 1 and 600')
    return config


def image_type(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png', 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg', 'image/jpeg'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'webp', 'image/webp'
    raise ValueError('Expected PNG, JPEG or WebP image bytes')


def multipart(fields, attachments):
    boundary = 'dsh-' + uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        # Field names are config-controlled, but may not inject MIME headers.
        if any(ch in key for ch in '\r\n"'):
            raise ValueError('Invalid multipart field name')
        text = json.dumps(value) if isinstance(value, (dict, list, bool)) else str(value)
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{text}\r\n'.encode())
    for key, filename in attachments.items():
        p = Path(filename)
        if p.stat().st_size > LIMIT:
            raise ValueError('Input image exceeds 64 MiB')
        data = p.read_bytes()
        ext, mime = image_type(data)
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{key}.{ext}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + data + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('API redirects are refused to avoid forwarding credentials')


def run(args):
    config = load_config(args.config, args.allow_local)
    key = os.environ.get(config['apiKeyEnv'])
    if args.command == 'status':
        return {'configured': True, 'credentialAvailable': bool(key), 'model': config['model'],
                'generationHost': urllib.parse.urlsplit(config['generationUrl']).hostname,
                'editingConfigured': bool(config.get('editUrl')), 'networkChecked': False}
    if not key:
        raise ValueError('Credential environment variable is not set: ' + config['apiKeyEnv'])
    if not args.prompt.strip() or len(args.prompt) > 100000:
        raise ValueError('Prompt must contain 1 to 100000 characters')
    if not 1 <= args.count <= 4:
        raise ValueError('Image count must be between 1 and 4')
    fields = dict(config.get('requestOptions', {}), prompt=args.prompt, model=config['model'], n=args.count)
    if args.size:
        fields['size'] = args.size
    url = config['generationUrl']
    if args.command == 'edit':
        url = config.get('editUrl')
        if not url:
            raise ValueError('Configure editUrl to edit images')
        attachments = {'image': args.image}
        if args.mask:
            attachments['mask'] = args.mask
        body, content_type = multipart(fields, attachments)
    else:
        body, content_type = json.dumps(fields).encode(), 'application/json'
    req = urllib.request.Request(url, body, {'Authorization': 'Bearer ' + key, 'Content-Type': content_type}, method='POST')
    with urllib.request.build_opener(NoRedirect).open(req, timeout=config.get('timeoutSeconds', 180)) as response:
        raw = response.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('API response exceeds 64 MiB')
    result = json.loads(raw)
    rows = result.get('data') if isinstance(result, dict) else None
    if not isinstance(rows, list) or not 1 <= len(rows) <= 4:
        raise ValueError('API response must contain data with 1 to 4 images')
    images = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('b64_json'), str):
            raise ValueError('API must return data[].b64_json; configure a base64 response format')
        data = base64.b64decode(row['b64_json'], validate=True)
        ext, _ = image_type(data)
        images.append((data, ext))
    dest = Path(args.output_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for data, ext in images:
        path = dest / ('image-' + uuid.uuid4().hex + '.' + ext)
        with path.open('xb') as f:
            f.write(data)
        paths.append(str(path))
    return {'files': paths, 'count': len(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('status', 'generate', 'edit'):
        p = sub.add_parser(command)
        p.add_argument('--config', default='.dsh/image-service.json')
        p.add_argument('--allow-local', action='store_true', help='Allow loopback HTTP for a local service')
        if command != 'status':
            p.add_argument('--prompt', required=True)
            p.add_argument('--output-dir', required=True)
            p.add_argument('--count', type=int, default=1)
            p.add_argument('--size')
        if command == 'edit':
            p.add_argument('--image', required=True)
            p.add_argument('--mask')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False))
    except urllib.error.HTTPError as e:
        # Do not echo provider response bodies, URLs, prompts or credentials.
        print(json.dumps({'error': 'Image API returned HTTP ' + str(e.code)}), file=sys.stderr)
        return 1
    except (ValueError, OSError, binascii.Error) as e:
        message = str(e) if isinstance(e, ValueError) else type(e).__name__
        print(json.dumps({'error': message}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
