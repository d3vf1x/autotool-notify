# Autotool notifier for HTWK-Leipzig autotool
This is just a Proof of Concept, so please use this program with caution!
You have to save your password and username in plaintext on your computer! 
Take a minute to understand the risks involved!
Use at your own risk.<br>
YOU HAVE BEEN WARNED!

But no let's explain what this program can/can't do:

It's a simple proof of concept for a notifier that checks the online learning platform https://gitlab.imn.htwk-leipzig.de/autotool/all0/ for new tasks in your courses.
You need an HTWK-Leipzig login to use it and you can only check courses that you take part in.

## General functionality

This tool will create a shibboleth session with your credentials. With this login, it will check the autotool page for new tasks in all specified courses. 
It will check the following url for every course given:

`https://autotool.imn.htwk-leipzig.de/new/vorlesung/{courseID}/aufgaben/aktuell`

After each run the program will save your cookies (`.cookies`) and will try them on the next run:

```
[OK] Gespeicherte Cookies gefunden.
[..] Überprüfe Aufgaben für Vorlesung 309...
...
```

The program will generate a message for every course based on the number of tasks that are still open.
It will call the [send_Message](https://github.com/d3vf1x/autotool-notify/blob/99e20cbb1d741cb03dc90d9a082014e46b85c1e2/autotool.py#L63) with this generated message string. For example:
`
Aufgabenstatus für Vorlesung 309
Alles Erledigt!
`

It will then save this message in a file `.status_{courseID}.txt` and will only call `send_Message()` if the message has changed.
To receive the message/notification you can link all sorts of services by adding the API-Call inside the `send_Message()` function.
An example is given for the telegram API.


## Usage
You need to install some dependencies first:

```
pip install requests configparser
```

To run the program, execute the following command:

```
python3 autotool.py
```

At the first startup, it will create a config file `config.ini` in the folder, where the python script is located.
Open it in a text editor and add your credentials and the courses that you are interested in. To find out the course ID of your course just check out the autotool website.
It will be in the URL.
Don't touch the URLs for now. 

```
[HTWK-login]
username = <login>
password = 12345

[autotool]
base-url = https://autotool.imn.htwk-leipzig.de
courses = 309 307

[shib]
Base-URL = https://shib1.rz.htwk-leipzig.de
```

Then just save the file and run the script again.
```
[..] keine gespeicherten Cookies gefunden, login erforderlich...
[..] starte loginprozedur: https://autotool.imn.htwk-leipzig.de/new/
[OK] login auf autotoolseite erfolgreich
[OK] Änderung erkannt.
[..] send: Aufgabenstatus für Vorlesung 309
Alles Erledigt!
[OK] login auf autotoolseite erfolgreich
[OK] Änderung erkannt.
[..] send: Aufgabenstatus für Vorlesung 307
Alles Erledigt!
[OK] cookies saved sucessfully
[OK] Alle Vorlesungen überprüft,ende
```




### Limitations
- This program will only account for mandatory tasks and will ignore any optional ones, if every mandatory task is already done
