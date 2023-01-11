#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pip install requests, configparser
import requests
import requests.utils
import sys
import traceback
import pickle
import os
import configparser
import re

import os.path


def init_config():
    config = configparser.ConfigParser()

    config['HTWK-login'] = {
        'Username': '<hrz-login>',
        'Password': ''}

    config['autotool'] = {
        'Base-URL': 'https://autotool.imn.htwk-leipzig.de/new/',
        'Courses': '123 123'
    }
    config['shib'] = {
        'Base-URL': 'https://shib1.rz.htwk-leipzig.de'
    }
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


shiboleth_base_url = ""
name = ""
word = ""
autotool = ""
courses = []
dir = ""


def print_log(msg, state):
    if state == 0:
        print("[..] " + msg)
    if state == 1:
        print("[OK] " + msg)
    if state == 2:
        print("[ER] " + msg)


def save_cookies(requests_cookiejar):
    with open(dir + ".cookies", 'wb') as f:
        pickle.dump(requests_cookiejar, f)
        print_log("cookies saved sucessfully", 1)


def load_cookies():
    with open(dir + ".cookies", 'rb') as f:
        return pickle.load(f)


# define your api call here
def send_Message(msg):
    # print(msg)
    # payload = {
    #  'chat_id':chatid,
    #  'text':msg
    # }
    print_log("send: " + msg, 0)
    # with requests.Session() as session:
    #  response = session.post('https://api.telegram.org/bot' + token + '/sendMessage', data=payload)
    #
    #  if response.status_code != 200:
    #    print_log("Nachricht versenden fehlgeschlagen!\n" + response.content,2)

# parses "aktuelle Aufgaben" to check for newly activated tasks


def parsePage(course, html):
    message = "Aufgabenstatus für Vorlesung " + course + "\n"
    prozent = html.partition('Das sind ')[2].partition(' Prozent.')[0]
    von = html.partition('gewichtete Punkte von ')[2].split(' ', 1)[0]
    aktuell = html.partition('Aus den bisherigen Pflicht-Aufgaben haben Sie ')[
        2].partition(' gewichtete Punkte von ')[0]
    if (von == "") or (aktuell == ""):
        raise Exception("Anzahlen der Aufgaben konnten nicht gelesen werden!")
    else:
        # generate status message
        if prozent == 100:
            message += "Alles Erledigt!"
        else:
            message += 'Es sind noch ' + \
                str(float(von) - float(aktuell)) + ' zu erledigen!'
            table = html.partition('<tbody>')[2].partition('</tbody>')[0]
            hoch = str_count(table, 'Hoch')
            niedrig = str_count(table, 'Niedrig')
            keinen = str_count(table, 'Keine Highscore')
            demo = str_count(table, 'Demonstration')

            if hoch != 0:
                message += "\n- " + str(hoch) + \
                    " Aufgaben mit Highscore (Hoch)"
            if niedrig != 0:
                message += "\n- " + str(niedrig) + \
                    " Aufgaben mit Highscore (Niedrig)"
            if keinen != demo:
                message += "\n- " + \
                    str(keinen) + " Aufgaben ohne Highscore (Demo " + str(demo) + ")"

            # read old status message
            if os.path.isfile(dir + '.status_' + course + '.txt'):
                with open(dir + '.status_' + course + '.txt', "r") as f:
                    status = ""
                    for line in f:
                        status = status + line
            else:
                status = ""

            # save new message in status file
            if message != status:
                print_log("Änderung erkannt.", 0)
                send_Message(message)
                with open(dir + ".status.txt", "w") as f:
                    f.write(message)
            else:
                print_log("keine Änderung erkannt, ende.", 0)

# will be called for every course in courses list


def check_course(course):
    # stops next execution if error occurs
    if os.path.isfile(dir + ".stop_" + course + ".txt"):
        print_log(".stop_" + course + ".txt wurde gefunden, beende", 0)
        return
    try:

        # start with new session and check old cookies
        with requests.Session() as r:
            if os.path.isfile('.cookies'):
                # lade cookies
                sessioncookies = load_cookies()
                aktuelleAufgaben = r.get(
                    autotool + 'courses/' + str(courses) + '/aufgaben/aktuell', cookies=sessioncookies)
                if aktuelleAufgaben.status_code == 200:  # cookies are still valid!
                    html = aktuelleAufgaben.text.encode('utf-8')
                    if (str_count(html, 'Pflichtaufgaben haben Sie bis jetzt') > 0):
                        print_log("Session weiterhin gültig", 1)
                        parsePage(course, html)
                        sys.exit(0)
                else:
                    print_log(
                        "Session abgelaufen, erneuter Login erforderlich.", 0)
            else:
                print_log(
                    "keine gespeicherte Session gefunden, login erforderlich.", 0)

            # erneuter Login
            with requests.Session() as s:
                s.cookies.clear()
                print_log("starte loginprozedur: " + autotool, 0)
                # Lade Autotool seite um auf loginseite weitergeleitet zu werden um Cookies
                # und jsessionid zu bekommen
                loginpage = s.get(autotool)
                with open('login.html', 'w') as loginfile:
                    loginfile.write(loginpage.text)
                # wenn Statuscode nicht OK gib fehlermeldung aus
                if loginpage.status_code != 200:
                    with open('loginpage.html', 'w') as aktuelleAufgabenFile:
                        aktuelleAufgabenFile.write(loginpage.text)
                    raise Exception(
                        "HTTP-Error: " + str(loginpage.status_code) + " Versuch Loginseite zu öffnen!\n")

                # formAdress = loginpage.text.partition('action="')[0].partition('"')[0]
                formAdress = "/idp/profile/SAML2/Redirect/SSO"
                csrf_token = loginpage.text.partition(
                    '<input type="hidden" name="csrf_token" value="')[2].partition('"')[0]
                # print("url: " + formAdress)
                # print("csrf_token: " + csrf_token)

                payload = {
                    'csrf_token': csrf_token,
                    'shib_idp_ls_exception.shib_idp_session_ss': '',
                    'shib_idp_ls_success.shib_idp_session_ss': 'true',
                    'shib_idp_ls_value.shib_idp_session_ss': '',
                    'shib_idp_ls_exception.shib_idp_persistent_ss': '',
                    'shib_idp_ls_success.shib_idp_persistent_ss': 'true',
                    'shib_idp_ls_value.shib_idp_persistent_ss': '',
                    'shib_idp_ls_supported': 'true',
                    '_eventId_proceed': ''
                }

                postresponse = s.post(
                    shiboleth_base_url + formAdress + "?execution=e1s1", data=payload, cookies=s.cookies)
                if postresponse.status_code != 200:
                    raise Exception(str(postresponse.status_code) +
                                    " Beim POST 1 Login mit Shibboleth:\n")
                csrf_token = postresponse.text.partition(
                    '<input type="hidden" name="csrf_token" value="')[2].partition('"')[0]

                payload = {
                    'csrf_token': csrf_token,
                    'j_username': name,
                    'j_password': word,
                    '_eventId_proceed': ''
                }

                # this gets the final token and cookie for login at autootool
                postresponse = s.post(
                    shiboleth_base_url + formAdress + "?execution=e1s2", data=payload, cookies=s.cookies)
                if postresponse.status_code != 200:
                    raise Exception(str(postresponse.status_code) +
                                    " Beim POST 2 Login mit Shibboleth:\n")

                RelayState = postresponse.text.partition(
                    '<input type="hidden" name="RelayState" value="cookie&#x3a;')[2].partition('"')[0]
                SAMLResponse = postresponse.text.partition(
                    '<input type="hidden" name="SAMLResponse" value="')[2].partition('"')[0]
                payload = {
                    'RelayState': "cookie:"+RelayState,
                    'SAMLResponse': SAMLResponse
                }

                # Login at autotool
                postresponse = s.post(
                    'https://autotool.imn.htwk-leipzig.de/Shibboleth.sso/SAML2/POST', data=payload, cookies=s.cookies)
                if postresponse.status_code != 200:
                    raise Exception(
                        str(postresponse.status_code) + " Bei POST zu Shibboleth:\n")

                # Login Button auf autotoolseite drücken
                loginresponse = s.get(autotool + 'auth/login')
                if loginresponse.status_code != 200:
                    raise Exception(
                        "HTTP-Error: " + str(loginresponse.status_code) + " Beim Login Autotool:\n")

                # aktuelle Aufgaben seite laden
                url = autotool + 'vorlesung/' + course + '/aufgaben/aktuell'
                aktuelleAufgaben = s.get(url)
                if aktuelleAufgaben.status_code != 200:
                    raise Exception("HTTP-Error: " + str(aktuelleAufgaben.status_code) +
                                    " Beim Aufruf der aktuellen Aufgaben: '"+url+"'\n")

                # überprüfen ob die aufgabenübersich geladen wurde
                html = str(aktuelleAufgaben.text.encode('utf-8'))
                if (str_count(html, "Aus den bisherigen Pflicht-Aufgaben haben Sie") > 0):
                    print_log("login auf autotoolseite erfolgreich", 1)
                    save_cookies(s.cookies)
                    parsePage(course, html)
                else:
                    raise Exception("Pflichtaufgaben nicht gefunden!")

    except KeyboardInterrupt:
        print("Abgebrochen durch Tastatureingabe")
    except Exception as error:
        # automatische ausführung stoppen durch anlegen von dummy datei
        traceback.print_exc()
        f = open(dir + ".stop_" + course + ".txt", "w+")
        f.close()
        send_Message(
            'Es ist ein Fehler aufgetreten!\n Crontab on halt!\n' + repr(error))
        print_log("Es ist ein Fehler aufgetreten!\n " + repr(error), 2)


def str_count(string, substring):
    return len(re.findall(substring, string))


def main():
    if not os.path.isfile('config.ini'):
        init_config()
        print("Please edit the config file: 'config.ini'")
        exit(0)

    # Read config
    try:
        config = configparser.ConfigParser()
        config.sections()
        config.read('config.ini')

        global name
        name = config['HTWK-login']['Username']
        if not name:
            raise Exception("Invalid username")

        global word
        word = config['HTWK-login']['Password']
        if not word:
            raise Exception("Please add username")

        global autotool
        autotool = config['autotool']['Base-URL']
        if not autotool:
            raise Exception("Check shiboleth base url")

        global shiboleth_base_url
        shiboleth_base_url = config['shib']['Base-URL']
        if not shiboleth_base_url:
            raise Exception("Check shiboleth base url")

        global courses
        courses = config['autotool']['Courses'].split()
        if len(courses) <= 0:
            raise Exception("Please add course id!")

    except Exception as error:
        print("Invalid config file: " + repr(error))
        exit(-1)

    for c in courses:
        check_course(c)


if __name__ == "__main__":
    main()
