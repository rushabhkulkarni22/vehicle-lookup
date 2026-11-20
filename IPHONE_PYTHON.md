# Run Find Vehicle on an iPhone

Use **find_vehicle_iphone.py**. It is a standalone Python 3 script with console
input; it has no Tkinter, extra packages, web backend, or Apple signing requirement.
The desktop script is unchanged. The older Swift project is not needed for this option.

1. Install an iPhone Python app such as **Pyto** or **Pythonista 3** from the App Store.
2. Download `find_vehicle_iphone.py` from this repository to Files, then open/import it
   in the Python app. Alternatively, create a new script and paste the file's raw code.
3. Run the script and enter the vehicle registration in its console when prompted.
4. Enter another registration for another lookup, or enter `q` to stop.

Example:

```text
Vehicle number: MH12XQ4561
```

You only need that one Python file. No Mac, developer account, running laptop,
or hosted website is needed. Internet is needed to contact CarInfo. App availability
and pricing depend on your App Store region; check the listing before installing.

Results show vehicle fields and only already-masked owner names. No name guessing,
phone lookup, or history saving is included. There is a ten-second gap between
requests. CarInfo may block automated access or require verification; the script
reports this and provides the source URL instead of bypassing restrictions.

Verified locally with mocked console input and page responses. Not device-tested
inside Pyto or Pythonista; live requests also depend on CarInfo and your network.

App documentation:
- https://pyto.readthedocs.io/en/latest/
- https://omz-software.com/pythonista/docs-3.4/py3/ios/pythonista.html
- https://omz-software.com/pythonista/docs-3.4/py3/library/urllib.request.html
