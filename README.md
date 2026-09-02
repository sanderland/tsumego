<table border=0>
<tr>
<td>

# Ten Thousand Tsumego
This repo contains the source code for the mobile app *Ten Thousand Tsumego* with over 10,000 go problems.

## Installation
* APK binaries for android are avaiable [here](https://github.com/sanderland/tsumego/releases).
* You can also run the app on desktop. On macOS, double-click `run-desktop.command`, or run `./run-desktop.command` from a terminal after creating the local environment:

  ```bash
  uv venv --python 3.13 .venv
  uv pip install --python .venv/bin/python -r requirements-desktop.txt
  ```

* To build the ARM64 APK for Android 12 devices such as Surface Duo, run:

  ```bash
  ./build-android.command
  ```

  The Android build uses the existing Android Studio SDK, API 36, NDK 28c, and OpenJDK 17 as required by python-for-Android.

## Manual
Simply choose a category, collection and browse the problems with the arrow keys.
Your position within a collection is saved.

## FAQ

* Q: I can't place any stones.
    * A: This is intentional, you are supposed to read out the problem completely. If you can't, leave the problem for another time.
* Q: I have found improvements to current problems, or have a problem set I want to contribute!
    * A: Great! Please file an issue on github.
</td>
<td>
   
![Screenshot](https://i.imgur.com/qC1gZ78.png)

</td>
</tr>
</table>
