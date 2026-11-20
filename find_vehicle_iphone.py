"""Console vehicle lookup for iPhone Python apps. Python 3 standard library only."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

BASE = 'https://www.carinfo.app/rc-details/'
LIMIT = 3_000_000
FIELDS = {
    'Make & Model': 'make_model', 'Owner Name': 'owner_name_masked',
    'Fuel Type': 'fuel_type', 'Vehicle Class': 'vehicle_class',
    'Registration Date': 'registration_date', 'RC Status': 'rc_status',
    'Insurance Validity': 'insurance_validity', 'PUC Validity': 'puc_validity',
}


class LookupError(Exception):
    pass


def normalize_plate(value):
    plate = re.sub(r'[\s-]', '', value).upper()
    if not re.fullmatch(r'(?:[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}|[0-9]{2}BH[0-9]{4}[A-Z]{1,2})', plate):
        raise LookupError('Enter an Indian registration number, for example MH12XQ4561.')
    return plate


class VisibleText(HTMLParser):
    """Read displayed HTML only; ignore scripts, hydration data and hidden tags."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        hidden = (tag in {'script', 'style', 'noscript', 'template'} or
                  'hidden' in attrs or attrs.get('aria-hidden') == 'true' or
                  bool(re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', attrs.get('style', ''), re.I)))
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append((tag, hidden or any(h for _, h in self.stack)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not any(h for _, h in self.stack):
            value = ' '.join(data.split())
            if value:
                self.tokens.append(value)


def masked_name(value):
    # Never return an unmasked name or an unmasked word alongside masked words.
    if not value or len(value) > 100 or not re.fullmatch(r'[A-Za-z*•.\- ]+', value):
        return None
    words = value.split()
    if not words or not all('*' in w or '•' in w for w in words):
        return None
    return value


def parse_page(html, plate):
    plate = normalize_plate(plate)
    parser = VisibleText()
    parser.feed(html)
    tokens = parser.tokens
    text = ' '.join(tokens)
    if re.search(r'verify (?:that )?you are human|access denied|complete the captcha|just a moment', text, re.I):
        raise LookupError('CarInfo requires verification. Open it in your browser; no bypass was attempted.')
    if not any(re.sub(r'[\s-]', '', t).upper() == plate for t in tokens):
        raise LookupError('No matching vehicle result was present in the public page. It may require login or browser rendering.')
    result = {'registration_number': plate, 'source_url': BASE + plate,
              'retrieved_at': datetime.now(timezone.utc).isoformat(),
              **{key: None for key in FIELDS.values()}}
    labels = {label.casefold(): key for label, key in FIELDS.items()}
    for i, token in enumerate(tokens[:-1]):
        key = labels.get(token.rstrip(':').casefold())
        if not key:
            continue
        value = tokens[i+1]
        if value.rstrip(':').casefold() in labels or len(value) > 160:
            continue
        if key == 'owner_name_masked':
            result[key] = masked_name(value)
        elif key == 'make_model':
            result[key] = value
        else:
            result[key] = value
    date_match = re.search(r'Insurance\s+(?:Expiring|Expired|Expires)\s+on\s+(\d{1,2}[-/][A-Za-z0-9]{2,9}[-/]\d{4})', text, re.I)
    if date_match:
        result['insurance_validity'] = date_match.group(1)
    if not result['make_model']:
        raise LookupError('The page did not contain a recognizable vehicle result. No details were guessed.')
    return result


class SameSiteRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != 'https' or target.hostname != 'www.carinfo.app' or target.path != urlsplit(req.full_url).path:
            raise LookupError('CarInfo redirected to a different page. Open the lookup in your browser.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def lookup(plate):
    plate = normalize_plate(plate)
    request = urllib.request.Request(BASE + plate, headers={
        'User-Agent': 'VehicleLookup/1.0', 'Accept': 'text/html',
    })
    try:
        with urllib.request.build_opener(SameSiteRedirect()).open(request, timeout=20) as response:
            if response.headers.get_content_type() != 'text/html':
                raise LookupError('Unexpected response format from CarInfo.')
            body = response.read(LIMIT+1)
            if len(body) > LIMIT:
                raise LookupError('The response exceeded the size limit.')
            html = body.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
    except urllib.error.HTTPError as exc:
        messages = {401: 'Login is required.', 403: 'CarInfo blocked automated access.',
                    404: 'That lookup page was not found.', 429: 'CarInfo is rate-limiting requests; try later.'}
        raise LookupError(messages.get(exc.code, f'CarInfo returned HTTP {exc.code}.') + ' No retry or bypass was attempted.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise LookupError('Unable to connect to CarInfo. Check your connection or open the source URL in Safari.') from None
    return parse_page(html, plate)


def main():
    """Run in the console of an iPhone Python 3 app such as Pyto."""
    print('FIND VEHICLE')
    print('Enter a registration number, or q to quit.')
    print('Internet required. Owner names stay masked. No history is saved.')
    last_start = None
    while True:
        try:
            entered = input('\nVehicle number: ').strip()
            if entered.lower() in {'q', 'quit', 'exit'}:
                break
            if not entered:
                continue
            try:
                plate = normalize_plate(entered)
            except LookupError as exc:
                print(str(exc))
                continue
            print('Source: ' + BASE + plate)
            if last_start is not None:
                remaining = 10 - (time.monotonic() - last_start)
                if remaining > 0:
                    print('Waiting {:.0f} seconds between requests...'.format(remaining))
                    time.sleep(remaining)
            print('Looking up {}...'.format(plate), flush=True)
            last_start = time.monotonic()
            try:
                result = lookup(plate)
            except LookupError as exc:
                print('Lookup unavailable: ' + str(exc))
                print('You can open the source URL above in Safari.')
                continue
            print('\nRegistration: ' + result['registration_number'])
            for label, key in FIELDS.items():
                if key == 'owner_name_masked':
                    label = 'Owner (masked)'
                print('{}: {}'.format(label, result.get(key) or 'Unavailable'))
            print('Retrieved: ' + result['retrieved_at'])
        except (EOFError, KeyboardInterrupt):
            break
    print('\nFinished.')


if __name__ == '__main__':
    main()

