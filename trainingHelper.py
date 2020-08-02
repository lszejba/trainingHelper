##############################################################
# Driving Assist App
#############################################################

# 1. Zakres projektu
# Aplikacja ma pobierać dane dotyczące samochodu (prędkość, bieg, rpm, stan opon itp) z określoną, dość wysoką częstotliwością.
# Te dane nie będą wykorzystywane na bieżąco. Jeśli dane okrążenie dla danego typu samochodu jest najszybsze, wówczas będziemy te dane
# nadpisywać. (moduł 1)
# Jeśli mamy określoną ilość danych (N okrążeń przejechanych danym samochodem po danym torze) wówczas podczas jazdy będziemy wyświetlać
# podpowiedzi z odliczaniem (3... 2... 1... NOW) dotyczące nadchodzących zakrętów (docelowy bieg - może być więcej niż jeden, np. 2->1 jeśli
# trzeba dodatkowo zwolnić po chwili) oraz przyspieszania przy wychodzeniu z zakrętów (HALF THROTTLE/FULL THROTTLE). Naraz aktywne może
# być kilka podpowiedzi (np dla serii zakrętów, hamowanie->przyspieszenie itp) (moduł 2)
# Ostatni moduł przygotowuje dane do wyświetlenia dla modułu 2. Analizując zapisane dane (do przemyślenia: czy w połączeniu z aktualnymi?
# Np. aktualną prędkością?) przygotowuje listę podpowiedzi wraz z pewnego rodzaju timestamp'ami (zależnymi najprawdopodobniej od położenia
# na torze) kiedy mają być wyświetlone. Moduł powinien także analizować aktualne okrążenie i sprawdzać, czy mamy szansę poprawić najlepszy
# czas. Jeśli tak, wówczas w oddzielnym wątku powinien zacząć przygotowywać podpowiedzi na kolejne okrążenie (moduł 3)

# Dodatki: wyliczanie estimatedTimeLap (???)

import ac
import acsys
#import json
import math
import copy

appWindow=0
carCount=0
cars = []
playerModule1=0

class Car:
    def __init__(self, name, driver, number):
        self.name = name
        self.driver = driver
        self.number = number
        self.laps = []
        self.laps.append([])
        self.laps.append([])
        self.lapIndex = 0
        self.currentLapProgress = 0

    def getCurrentData(self):
        res = dict()
        # single values
        res['speedKph'] = ac.getCarState(self.number, acsys.CS.SpeedKMH)
        res['pedalGas'] = ac.getCarState(self.number, acsys.CS.Gas)
        res['pedalBrake'] = ac.getCarState(self.number, acsys.CS.Brake)
        res['pedalClutch'] = ac.getCarState(self.number, acsys.CS.Clutch)
        res['gear'] = ac.getCarState(self.number, acsys.CS.Gear)
        res['rpm'] = ac.getCarState(self.number, acsys.CS.RPM)
        res['lapCount'] = ac.getCarState(self.number, acsys.CS.LapCount)
        res['lapTimeCurrent'] = ac.getCarState(self.number, acsys.CS.LapTime)
        res['lapTimeLast'] = ac.getCarState(self.number, acsys.CS.LastLap)
        res['lapInvalidated'] = ac.getCarState(self.number, acsys.CS.LapInvalidated)
        res['driveTrainSpeed'] = ac.getCarState(self.number, acsys.CS.DriveTrainSpeed)
        res['lapPositionNormalized'] = ac.getCarState(self.number, acsys.CS.NormalizedSplinePosition)
        res['steer'] = ac.getCarState(self.number, acsys.CS.Steer)
        # [x,y,z] vector
#        res['worldPosition'] = ac.getCarState(carNumber, acsys.CS.WorldPosition)

        time = round(res['lapTimeCurrent'], 3)
        if self.currentLapProgress > res['lapPositionNormalized']:
            self.lapIndex = (self.lapIndex + 1) % 2
            # ADD PROCESSING HERE
            self.laps[(self.lapIndex + 1) % 2].clear()
        self.laps[self.lapIndex].append(res)
        self.currentLapProgress = res['lapPositionNormalized']
        return res

class Module1:
    def __init__(self,app,track, count):
        self.app = app
        self.track = track
        self.labelCarName = []
        self.labelSpeed = []
        self.labelGas = []
        self.labelBrake = []
        self.labelGear = []
        self.labelRpm = []
        self.labelTime = []
        self.labelLapInvalid = []
        self.labelPos = []
        self.labelSteer = []
        self.labelDataPoints0 = []
        self.labelDataPoints1 = []

        ac.setPosition(ac.addLabel(app, "Track: " + track), 20, 20)
        ac.setPosition(ac.addLabel(app, "Speed"), 20, 60)
        ac.setPosition(ac.addLabel(app, "Gas"), 20, 80)
        ac.setPosition(ac.addLabel(app, "Brake"), 20, 100)
        ac.setPosition(ac.addLabel(app, "Gear"), 20, 120)
        ac.setPosition(ac.addLabel(app, "RPM"), 20, 140)
        ac.setPosition(ac.addLabel(app, "Time"), 20, 160)
        ac.setPosition(ac.addLabel(app, "Lap invalid"), 20, 180)
        ac.setPosition(ac.addLabel(app, "Progress"), 20, 200)
        ac.setPosition(ac.addLabel(app, "Steer"), 20, 220)
        ac.setPosition(ac.addLabel(app, "Data points[0]"), 20, 280)
        ac.setPosition(ac.addLabel(app, "Data points[1]"), 20, 300)
        
        for i in range(count):
            offset = 150 + 60 * i
            self.labelCarName.append(ac.addLabel(app, "{0}".format(i)))
            ac.setPosition(self.labelCarName[i], offset, 40)
            self.labelSpeed.append(ac.addLabel(app, "<SPEED>"))
            ac.setPosition(self.labelSpeed[i], offset, 60)
            self.labelGas.append(ac.addLabel(app, "<GAS>"))
            ac.setPosition(self.labelGas[i], offset, 80)
            self.labelBrake.append(ac.addLabel(app, "<BRAKE>"))
            ac.setPosition(self.labelBrake[i], offset, 100)
            self.labelGear.append(ac.addLabel(app, "<GEAR>"))
            ac.setPosition(self.labelGear[i], offset, 120)
            self.labelRpm.append(ac.addLabel(app, "<RPM>"))
            ac.setPosition(self.labelRpm[i], offset, 140)
            self.labelTime.append(ac.addLabel(app, "<TIME>"))
            ac.setPosition(self.labelTime[i], offset, 160)
            self.labelLapInvalid.append(ac.addLabel(app, "<INVALID>"))
            ac.setPosition(self.labelLapInvalid[i], offset, 180)
            self.labelPos.append(ac.addLabel(app, "<POS>"))
            ac.setPosition(self.labelPos[i], offset, 200)
            self.labelSteer.append(ac.addLabel(app, "<STEER>"))
            ac.setPosition(self.labelSteer[i], offset, 220)
            self.labelDataPoints0.append(ac.addLabel(app, "0"))
            ac.setPosition(self.labelDataPoints0[i], offset, 280)
            self.labelDataPoints1.append(ac.addLabel(app, "0"))
            ac.setPosition(self.labelDataPoints1[i], offset, 300)
        
#    def getGeneralDataForCar(self,carNumber):
#        res = dict()
#        res['driverName'] = ac.getDriverName(carNumber)
#        res['carName'] = ac.getCarName(carNumber)
#        return res
        
    def updateLabels(self, carNumber, values):
        global cars
#        ac.log("Inside updateLabels");
        ac.setText(self.labelSpeed[carNumber], "{0}".format(round(values['speedKph'],1)))
        ac.setText(self.labelGas[carNumber], "{0}".format(round(values['pedalGas'],2)))
        ac.setText(self.labelBrake[carNumber], "{0}".format(round(values['pedalBrake'],2)))
        ac.setText(self.labelGear[carNumber], "{0}".format(round(values['gear']-1.0,0)))
        ac.setText(self.labelRpm[carNumber], "{0}".format(round(values['rpm'],0)))
        ac.setText(self.labelTime[carNumber], "{0}".format(round(values['lapTimeCurrent'],1)))
        ac.setText(self.labelLapInvalid[carNumber], "{0}".format(round(values['lapInvalidated'],0)))
        ac.setText(self.labelPos[carNumber], "{0} %".format(round(values['lapPositionNormalized'] * 100.0,2)))
        ac.setText(self.labelSteer[carNumber], "{0}".format(round(values['steer'],2)))
        ac.setText(self.labelDataPoints0[carNumber], "{0}".format(len(cars[carNumber].laps[0])))
        ac.setText(self.labelDataPoints1[carNumber], "{0}".format(len(cars[carNumber].laps[1])))
    

#class Module2:
#    def __init__(self, filename):
#        with open(filename) as f:
            

#class Module3:
#    def __init__(self):
        

def getGeneralData():
    res = dict()
    res['trackName'] = ac.getTrackName(0)
    res['trackConfiguration'] = ac.getTrackConfiguration(0)
    res['carCount'] = ac.getCarsCount()
    return res

def getGeneralDataForCar(carNumber):
    res = dict()
    res['driverName'] = ac.getDriverName(carNumber)
    res['carName'] = ac.getCarName(carNumber)
    return res

def acMain(ac_version):
    global appWindow, carCount, playerModule1, cars
    ac.log("trainingHelper - start")
    ac.console("trainingHelper - start")
    appWindow=ac.newApp("Training Helper")
    ac.setSize(appWindow,400,400)
    ac.drawBorder(appWindow,0)
    ac.setBackgroundOpacity(appWindow,0)
    ac.setFontSize(appWindow, 15)
    generalData = getGeneralData()
    carCount = generalData['carCount']
    playerModule1 = Module1(appWindow, generalData['trackName'] + generalData['trackConfiguration'], carCount)
    for i in range(carCount):
        playerData = getGeneralDataForCar(i)
        car = Car(playerData['carName'], playerData['driverName'], i)
        cars.append(car)
    #ac.log(playerData['carName'])
    #ac.setText(playerModule1.labelCarName, "{0}".format(playerData['carName']))    
    ac.addRenderCallback(appWindow, onFormRender)
    return "Training Helper"

def onFormRender(deltaT):
    global playerModule1, cars, carCount
#    ac.log("Inside onFormRender()")
#    speed = ac.getCarState(0, acsys.CS.SpeedKMH)
#    ac.setText(playerModule1.labelSpeed, "{0} KPH".format(round(speed,1)))
    for i in range(carCount):
        data = cars[i].getCurrentData()
        playerModule1.updateLabels(i, data)
		 
