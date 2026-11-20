# Find Vehicle for iPhone

Native SwiftUI app for iOS 16 or later. Open **FindVehicle.xcodeproj** in Xcode.
The original desktop file at the repository root is unchanged. `vehicle_lookup.py`
in this folder is a reference copy, not the iPhone executable.

## What it does

- Accepts an Indian registration number and fetches the public CarInfo page directly from the phone.
- Displays allowlisted vehicle details and already-masked owner names.
- Provides loading, cancellation, errors, accessibility labels, selectable result text, and a source link.
- Keeps no lookup history, cookies, API keys, or remote backend. Internet is required.
- Stops on blocked requests, redirects, login/verification pages, missing results, or oversized responses.

The laptop need not remain on when using the installed app. CarInfo availability
is not guaranteed: this is an HTML integration, not an authorized production API.
It does not guess owner identities or retrieve private contact information.

## Install on your iPhone

You need access to a Mac with Xcode and your Apple Account for this step.
An Apple Developer Program subscription is not required for personal testing.

1. Clone/download this repository on the Mac and open `iphone/FindVehicle.xcodeproj`.
2. Let Xcode resolve the SwiftSoup package dependency.
3. In Xcode Settings > Accounts, add your Apple Account.
4. Select the **FindVehicle** target > Signing & Capabilities. Enable automatic signing and choose your Personal Team. Change the bundle identifier if Xcode says it is unavailable. Set the test target's team too if running device tests.
5. Connect your iPhone to the Mac, trust it, and enable Developer Mode if Xcode requests it.
6. Select your iPhone as the destination and press Run. The app appears as **Find Vehicle** on the Home Screen.

With a free Personal Team, provisioning expires after seven days; rebuild and
reinstall using Xcode after expiry. This is not a permanent unsigned install.
Never send your Apple password or signing keys to this repository.

Apple's instructions and limits:
https://developer.apple.com/help/account/basics/about-your-developer-account

## Build and test

The GitHub Actions workflow builds for iOS Simulator, runs the XCTest parser tests,
and compiles for physical iPhone without signing. An unsigned build cannot be installed
on an ordinary iPhone. CI has no signing account and does not publish to TestFlight.

Locally on a Mac, select an iPhone simulator and choose Product > Test in Xcode.
Tests use synthetic HTML, not live vehicle data. A successful build does not prove
that CarInfo will accept requests from every phone/network. Device UI and live
network verification remain necessary before distribution.

The generated Xcode project is checked in. To regenerate it after changing project
settings, run `python3 iphone/make_project.py` from the repository root.
SwiftSoup is pinned to version 2.6.0 and remains covered by its own MIT license:
https://github.com/scinfu/SwiftSoup/tree/2.6.0
