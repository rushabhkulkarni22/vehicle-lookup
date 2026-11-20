"""CarInfo public vehicle lookup. Python standard library only."""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import webbrowser

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
        raise LookupError('Unable to connect to CarInfo. Check your connection or use the browser button.') from None
    return parse_page(html, plate)


def launch_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    root = tk.Tk()
    root.title('Vehicle Lookup')
    root.geometry('720x620')
    root.minsize(620, 550)
    root.configure(bg='#f1f5f9')
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TLabel', font=('Segoe UI', 11))
    style.configure('TButton', font=('Segoe UI', 10), padding=9)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True, padx=18, pady=18)
    ttk.Label(frame, text='Vehicle Lookup', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Vehicle information from CarInfo · Owner names stay masked', wraplength=620).pack(anchor='w', pady=(6, 20))
    plate_var = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=plate_var, font=('Segoe UI', 17))
    entry.pack(fill='x')
    entry.focus_set()
    ttk.Label(frame, text='Example: MH12XQ4561', foreground='#64748b').pack(anchor='w', pady=5)
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=10)
    status = tk.StringVar(value='Enter a number plate to begin.')
    results = tk.Text(frame, height=15, wrap='word', font=('Segoe UI', 11), relief='flat', padx=12, pady=12, state='disabled')
    results.pack(fill='both', expand=True, pady=10)
    ttk.Label(frame, textvariable=status, wraplength=620).pack(anchor='w', pady=6)
    mailbox = queue.Queue()
    state = {'result': None, 'next_request': 0, 'busy': False}

    def show(text):
        results.configure(state='normal')
        results.delete('1.0', 'end')
        results.insert('1.0', text)
        results.configure(state='disabled')

    def search():
        if state['busy']:
            return
        state['result'] = None
        export_btn.configure(state='disabled')
        show('')
        try:
            plate = normalize_plate(plate_var.get())
        except LookupError as exc:
            status.set(str(exc)); return
        if time.monotonic() < state['next_request']:
            status.set('Please wait a few seconds before another lookup.'); return
        plate_var.set(plate)
        state['busy'] = True
        state['next_request'] = time.monotonic() + 10
        search_btn.configure(state='disabled')
        status.set('Fetching public vehicle details…')
        def worker():
            try:
                mailbox.put((lookup(plate), None))
            except LookupError as exc:
                mailbox.put((None, str(exc)))
            except Exception:
                mailbox.put((None, 'Unexpected response. No result was saved; use the browser button.'))
        threading.Thread(target=worker, daemon=True).start()

    def poll():
        try:
            result, error = mailbox.get_nowait()
        except queue.Empty:
            pass
        else:
            state['busy'] = False
            search_btn.configure(state='normal')
            if error:
                status.set(error)
            else:
                state['result'] = result
                lines = [f"Registration: {result['registration_number']}", '']
                lines += [f"{label}: {result[key] or 'Not available'}" for label, key in FIELDS.items()]
                show('\n\n'.join(lines))
                status.set('Retrieved from CarInfo. Missing fields are not inferred. Verify important details with the source.')
                export_btn.configure(state='normal')
        root.after(100, poll)

    def open_browser():
        try:
            webbrowser.open(BASE + normalize_plate(plate_var.get()))
        except LookupError as exc:
            messagebox.showerror('Registration number', str(exc))

    def export():
        if not state['result']:
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')], initialfile='vehicle-details.json')
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as output:
                    json.dump(state['result'], output, indent=2, ensure_ascii=False)
            except OSError:
                messagebox.showerror('Save failed', 'Could not save the file to that location.')

    search_btn = ttk.Button(buttons, text='Look up vehicle', command=search)
    search_btn.pack(side='left')
    ttk.Button(buttons, text='Open CarInfo', command=open_browser).pack(side='left', padx=8)
    export_btn = ttk.Button(buttons, text='Save JSON', command=export, state='disabled')
    export_btn.pack(side='right')
    entry.bind('<Return>', lambda _: search())
    poll()
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plate', help='Fetch one registration number and print sanitized JSON instead of opening the app')
    args = parser.parse_args()
    if args.plate:
        try:
            print(json.dumps(lookup(args.plate), indent=2, ensure_ascii=False))
        except LookupError as exc:
            print(json.dumps({'error': str(exc)}))
            raise SystemExit(1)
    else:
        launch_gui()
