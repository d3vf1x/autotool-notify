 #!/usr/bin/env python
# -*- coding: utf-8 -*-
#pip install requests
import requests, requests.utils,  sys, traceback, pickle, os

name = ''
word = ''
autotool = 'https://autotool.imn.htwk-leipzig.de/new/'
vorlesung = "251" #in der URL
token = ''
chatid = ''
dir = "/home/pi/python-autotool/"

def printLog(msg, state):
        if state == 0:
            print "[..] " + msg
        if state == 1:
            print "[OK] " + msg
        if state == 2:
            print "[ER] " + msg

def saveCookies(requests_cookiejar):
    with open(dir + "cookies.txt", 'wb') as f:
        pickle.dump(requests_cookiejar, f)
        printLog("cookies saved sucessfully",1)

def loadCookies():
    with open(dir + "cookies.txt", 'rb') as f:
        return pickle.load(f)

def sendMessage(msg):
    payload = {
            'chat_id':chatid,
            'text':msg
        }
    with requests.Session() as session:
       response = session.post('https://api.telegram.org/bot' + token + '/sendMessage',data=payload)
       if response.status_code != 200:
            printLog("Nachricht versenden fehlgeschlagen!",2)

def parsePage(html):

    prozent = html.partition('Das sind ')[2].partition(' Prozent.')[0]
    von = html.partition('<p>Von ')[2].partition(' Pflichtaufgaben')[0]
    aktuell = html.partition('Pflichtaufgaben haben Sie bis jetzt ')[2].partition(' erledigt')[0]

    if (von == "") or (aktuell == ""):
        raise Exception( "Anzahlen der Aufgaben konnten nicht gelesen werden!")
    else:

        if prozent == "100":
            message = "alles Erledigt!"
        else:
	    message = "Es sind noch " + str(int(von) - int(aktuell)) + " zu erledigen!"

        #message += "\n" + "Aufgaben:"

        table = html.partition('<tbody>')[2].partition('</tbody>')[0]

        Hoch = table.count('Hoch')
        Niedrig = table.count('Niedrig')
        keinen = table.count('Keine Highscore')
        demo = table.count('Demonstration')

        if Hoch != 0:
            message += "\n- " + str(Hoch) + " Aufgaben mit Highscore (Hoch)"
        if Niedrig != 0:
            message += "\n- " + str(Niedrig) + " Aufgaben mit Highscore (Niedrig)"
        if keinen != demo:
            message += "\n- " + str(keinen) + " Aufgaben ohne Highscore (Demo " + str(demo) + ")"

        #lese alte Statusnachricht
        with open(dir + "status.txt","r") as f:
            status = ""
            for line in f:
                status = status + line

        #schreibe ggf neue Nachricht in Datei
        if message != status:
            printLog("Änderung erkannt.", 0)
            sendMessage(message)
            with open(dir + "status.txt","w") as f:
                f.write(message)
        else:
            printLog( "keine Änderung erkannt, ende.",0)

def main():
    #Stoppt die ausführung
    if os.path.isfile(dir + "stopp.txt"):
	printLog("stopp.txt wurde gefunden, beende",0)
	sys.exit(0)

    try:
        # Session context wird geschlossen
        with requests.Session() as r:
            if os.stat(dir + "cookies.txt").st_size != 0:
                # lade cookies
                sessioncookies = loadCookies()

                aktuelleAufgaben = r.get(autotool + 'vorlesung/' + vorlesung + '/aufgaben/aktuell', cookies = sessioncookies)
                if aktuelleAufgaben.status_code == 200:
                    html = aktuelleAufgaben.text.encode('utf-8')
                    if(html.count('Pflichtaufgaben haben Sie bis jetzt') > 0):
                        printLog("Session weiterhin gültig", 1)
                        parsePage(html)
                        sys.exit(0)
                    else:
                        printLog("Session abgelaufen, erneuter Login erforderlich",0)


                else:
                    raise Exception(str(aktuelleAufgaben.status_code) + "Beim 1. versuch aufgaben aktuell zu laden")
            else:
                printLog("keine gespeicherte Session gefunden", 0)


        # erneuter Login
        with requests.Session() as s:

            printLog("starte loginprozedur",0)

            #Lade Autotool seite um auf loginseite weitergeleitet zu werden um Cookies
            #und jsessionid zu bekommen
            loginpage = s.get(autotool)
            # wenn Statuscode nicht OK gib fehlermeldung aus
            if loginpage.status_code != 200:
                raise Exception(str(loginpage.status_code) + " Versuch Loginseite zu öffnen!\n" + loginpage.content)


            formAdress = loginpage.text.partition('<form action="')[2].partition('"')[0]
            sessionId = formAdress.partition('jsessionid=')[2].partition('?')[0]
            cookies = {
                'JSESSIONID': sessionId
            }
            payload = {
                'j_username': name,
                'j_password': word,
                '_eventId_proceed':''
            }
            postresponse = s.post('https://shib1.rz.htwk-leipzig.de' + formAdress,
                data=payload, cookies=cookies)
            if postresponse.status_code != 200:
                raise Exception( str(postresponse.status_code) + " Beim POST Login mit Shibboleth:\n"+postresponse.content)


            RelayState = postresponse.text.partition('<input type="hidden" name="RelayState" value="cookie&#x3a;')[2].partition('"')[0]
            SAMLResponse = postresponse.text.partition('<input type="hidden" name="SAMLResponse" value="')[2].partition('"')[0]
            payload = {
                'RelayState': "cookie:"+RelayState,
                'SAMLResponse': SAMLResponse,
                'Continue':''
            }
            postresponse = s.post('https://autotool.imn.htwk-leipzig.de/Shibboleth.sso/SAML2/POST',
                data=payload, cookies={})
            if postresponse.status_code != 200:
                raise Exception(str(postresponse.status_code) + " Bei POST zu Shibboleth:\n" + postresponse.content)

            # Login Button auf autotoolseite drücken
            loginresponse = s.get(autotool + 'auth/login')
            if loginresponse.status_code != 200:
                raise Exception( str(loginresponse.status_code) + " Beim Login Autotool:\n" + loginresponse.content)

            # aktuelle Aufgaben seite laden
            aktuelleAufgaben = s.get(autotool + 'vorlesung/' + vorlesung + '/aufgaben/aktuell')
            if aktuelleAufgaben.status_code != 200:
                raise Exception( str(aktuelleAufgaben.status_code) + " Beim Aufruf der aktuellen Aufgaben:\n" + aktuelleAufgaben.content)

            # überprüfen ob die aurgabenübersich geladen wurde
            html = aktuelleAufgaben.text.encode('utf-8')
            if(html.count('Pflichtaufgaben haben Sie bis jetzt') > 0):
                printLog("login auf autotoolseite erfolgreich",1)
                saveCookies(s.cookies)
                parsePage(html)


    except KeyboardInterrupt:
        print "Abgebrochen durch Tastatureingabe"
    except Exception as error:
	f= open(dir + "stopp.txt","w+")
	f.close();
        sendMessage('Es ist ein Fehler aufgetreten!\n Crontab on halt!\n ' + repr(error))
        printLog('Es ist ein Fehler aufgetreten!\n ' + repr(error),2)
    sys.exit(0)


if __name__ == "__main__":
    main()
