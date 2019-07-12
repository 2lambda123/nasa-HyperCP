
import collections
import numpy as np
import scipy as sp

import HDFRoot
from Utilities import Utilities
from ConfigFile import ConfigFile


class ProcessL3:

     # recalculate TimeTag2 to follow GPS UTC time
    @staticmethod
    def processGPSTime(node):
        sec = 0

        for gp in node.groups:
            #if gp.id.startswith("GPS"):
            if gp.hasDataset("UTCPOS"):
                ds = gp.getDataset("UTCPOS")
                sec = Utilities.utcToSec(ds.data["NONE"][0])
                #print("GPS UTCPOS:", ds.data["NONE"][0], "-> sec:", sec)
                #print(secToUtc(sec))

        for gp in node.groups:
            #if not gp.id.startswith("GPS"):
            if not gp.hasDataset("UTCPOS"):
                dsTimer = gp.getDataset("TIMER")
                if dsTimer is not None:
                    dsTimeTag2 = gp.getDataset("TIMETAG2")
                    for x in range(dsTimeTag2.data.shape[0]):
                        v = dsTimer.data["NONE"][x] + sec
                        dsTimeTag2.data["NONE"][x] = Utilities.secToTimeTag2(v)       

    @staticmethod
    def interpolateL3(xData, xTimer, yTimer, newXData, instr, kind='linear'):        
        for k in xData.data.dtype.names:
            if k == "Datetag" or k == "Timetag2":
                continue
            # print(k)
            x = list(xTimer)
            new_x = list(yTimer)
            y = np.copy(xData.data[k]).tolist()
            if kind == 'cubic':  
                # test = Utilities.interpSpline(x, y, new_x)   
                # print('len(test) = ' + str(len(test)))           
                newXData.columns[k] = Utilities.interpSpline(x, y, new_x)       
                # print('len(newXData.columns[k]) = ' + str(len(newXData.columns[k])))  
                # print('')      
            else:
                newXData.columns[k] = Utilities.interp(x, y, new_x, kind)

        Utilities.plotTimeInterp(xData, xTimer, newXData, yTimer, instr)

    # Converts a sensor group into the format used by Level 2s
    # The sensor dataset is renamed (e.g. ES -> ES_hyperspectral)
    # The separate DATETAG, TIMETAG2 datasets are combined into the sensor dataset
    @staticmethod
    def convertGroup(group, datasetName, newGroup, newDatasetName):
        sensorData = group.getDataset(datasetName)
        dateData = group.getDataset("DATETAG")
        timeData = group.getDataset("TIMETAG2")

        newSensorData = newGroup.addDataset(newDatasetName)

        # Datetag and Timetag2 columns added to sensor dataset
        newSensorData.columns["Datetag"] = dateData.data["NONE"].tolist()
        newSensorData.columns["Timetag2"] = timeData.data["NONE"].tolist()

        # Copies over the dataset
        for k in sensorData.data.dtype.names:
            #print("type",type(esData.data[k]))
            newSensorData.columns[k] = sensorData.data[k].tolist()
        newSensorData.columnsToDataset()


    # Preforms time interpolation to match xData to yData
    @staticmethod
    def interpolateData(xData, yData, instr):
        msg = ("Interpolate Data " + instr)
        print(msg)
        Utilities.writeLogFile(msg)

        # Interpolating to itself
        if xData is yData:
            return True

        #xDatetag= xData.data["Datetag"].tolist()
        xTimetag2 = xData.data["Timetag2"].tolist()

        #yDatetag= yData.data["Datetag"].tolist()
        yTimetag2 = yData.data["Timetag2"].tolist()

        # Convert TimeTag2 values to seconds to be used for interpolation
        xTimer = []
        for i in range(len(xTimetag2)):
            xTimer.append(Utilities.timeTag2ToSec(xTimetag2[i]))
        yTimer = []
        for i in range(len(yTimetag2)):
            yTimer.append(Utilities.timeTag2ToSec(yTimetag2[i]))

        if not Utilities.isIncreasing(xTimer):
            msg = ("xTimer does not contain strictly increasing values")
            print(msg)
            Utilities.writeLogFile(msg)
            return False
        if not Utilities.isIncreasing(yTimer):
            msg = ("yTimer does not contain strictly increasing values")
            print(msg)
            Utilities.writeLogFile(msg)
            return False

        xData.columns["Datetag"] = yData.data["Datetag"].tolist()
        xData.columns["Timetag2"] = yData.data["Timetag2"].tolist()

        #if Utilities.hasNan(xData):
        #    print("Found NAN 1")

        # Perform interpolation on full hyperspectral time series
        ProcessL3.interpolateL3(xData, xTimer, yTimer, xData, instr, 'cubic')
        xData.columnsToDataset()
        
        #if Utilities.hasNan(xData):
        #    print("Found NAN 2")
        #    exit
        return True

    # interpolate GPS to match ES using linear interpolation
    @staticmethod
    def interpolateGPSData(node, gpsGroup):
        # This is handled seperately in order to correct the Lat Long and UTC fields
        msg = "Interpolate GPS Data"
        print(msg)
        Utilities.writeLogFile(msg)

        if gpsGroup is None:            
            msg = "WARNING, gpsGroup is None"
            print(msg)
            Utilities.writeLogFile(msg)
            return

        refGroup = node.getGroup("Reference")
        esData = refGroup.getDataset("ES_hyperspectral")

        # GPS
        # Creates new gps group with Datetag/Timetag2 columns appended to all datasets
        gpsTimeData = gpsGroup.getDataset("UTCPOS")
        gpsCourseData = gpsGroup.getDataset("COURSE")
        gpsLatPosData = gpsGroup.getDataset("LATPOS")
        gpsLonPosData = gpsGroup.getDataset("LONPOS")
        gpsMagVarData = gpsGroup.getDataset("MAGVAR")
        gpsSpeedData = gpsGroup.getDataset("SPEED")
        gpsLatHemiData = gpsGroup.getDataset("LATHEMI")
        gpsLonHemiData = gpsGroup.getDataset("LONHEMI")

        newGPSGroup = node.getGroup("GPS")
        newGPSCourseData = newGPSGroup.addDataset("COURSE")
        newGPSLatPosData = newGPSGroup.addDataset("LATPOS")
        newGPSLonPosData = newGPSGroup.addDataset("LONPOS")
        newGPSMagVarData = newGPSGroup.addDataset("MAGVAR")
        newGPSSpeedData = newGPSGroup.addDataset("SPEED")

        # Add Datetag, Timetag2 data to gps groups
        # This matches ES data after interpolation
        newGPSCourseData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newGPSCourseData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newGPSLatPosData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newGPSLatPosData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newGPSLonPosData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newGPSLonPosData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newGPSMagVarData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newGPSMagVarData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newGPSSpeedData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newGPSSpeedData.columns["Timetag2"] = esData.data["Timetag2"].tolist()

        x = []
        y = []
        # Convert degrees minutes to decimal degrees format
        for i in range(gpsTimeData.data.shape[0]):
            latDM = gpsLatPosData.data["NONE"][i]
            latDirection = gpsLatHemiData.data["NONE"][i]
            latDD = Utilities.dmToDd(latDM, latDirection)
            gpsLatPosData.data["NONE"][i] = latDD

            lonDM = gpsLonPosData.data["NONE"][i]
            lonDirection = gpsLonHemiData.data["NONE"][i]
            lonDD = Utilities.dmToDd(lonDM, lonDirection)
            gpsLonPosData.data["NONE"][i] = lonDD
            x.append(lonDD)
            y.append(latDD)

        ''' This is a good idea to persue. No implementation yet.
        #print("PlotGPS")
        #Utilities.plotGPS(x, y, 'test1')
        #print("PlotGPS - DONE")'''

        # Convert GPS UTC time values to seconds to be used for interpolation
        xTimer = []
        for i in range(gpsTimeData.data.shape[0]):
            xTimer.append(Utilities.utcToSec(gpsTimeData.data["NONE"][i]))

        # Convert ES TimeTag2 values to seconds to be used for interpolation
        yTimer = []
        for i in range(esData.data.shape[0]):
            yTimer.append(Utilities.timeTag2ToSec(esData.data["Timetag2"][i]))

        # Interpolate by time values
        ProcessL3.interpolateL3(gpsCourseData, xTimer, yTimer, newGPSCourseData, 'linear')
        ProcessL3.interpolateL3(gpsLatPosData, xTimer, yTimer, newGPSLatPosData, 'linear')
        ProcessL3.interpolateL3(gpsLonPosData, xTimer, yTimer, newGPSLonPosData, 'linear')
        ProcessL3.interpolateL3(gpsMagVarData, xTimer, yTimer, newGPSMagVarData, 'linear')
        ProcessL3.interpolateL3(gpsSpeedData, xTimer, yTimer, newGPSSpeedData, 'linear')

        newGPSCourseData.columnsToDataset()
        newGPSLatPosData.columnsToDataset()
        newGPSLonPosData.columnsToDataset()
        newGPSMagVarData.columnsToDataset()
        newGPSSpeedData.columnsToDataset()

    # interpolate SATNAV to match ES
    @staticmethod
    def interpolateSATNAVData(node, satnavGroup):
        msg = "Interpolate SATNAV Data"
        print(msg)
        Utilities.writeLogFile(msg)

        if satnavGroup is None:
            msg = "WARNING, satnavGroup is None"
            print(msg)
            Utilities.writeLogFile(msg)
            return

        refGroup = node.getGroup("Reference")
        esData = refGroup.getDataset("ES_hyperspectral")

        satnavTimeData = satnavGroup.getDataset("TIMETAG2")
        satnavAzimuthData = satnavGroup.getDataset("AZIMUTH")
        satnavHeadingData = satnavGroup.getDataset("HEADING")
        satnavPitchData = satnavGroup.getDataset("PITCH")
        satnavPointingData = satnavGroup.getDataset("POINTING")
        satnavRollData = satnavGroup.getDataset("ROLL")

        newSATNAVGroup = node.getGroup("SATNAV")
        newSATNAVAzimuthData = newSATNAVGroup.addDataset("AZIMUTH")
        newSATNAVHeadingData = newSATNAVGroup.addDataset("HEADING")
        newSATNAVPitchData = newSATNAVGroup.addDataset("PITCH")
        newSATNAVPointingData = newSATNAVGroup.addDataset("POINTING")
        newSATNAVRollData = newSATNAVGroup.addDataset("ROLL")

        # Add Datetag, Timetag2 data to satnav groups
        # This matches ES data after interpolation
        newSATNAVAzimuthData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newSATNAVAzimuthData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newSATNAVHeadingData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newSATNAVHeadingData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newSATNAVPitchData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newSATNAVPitchData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newSATNAVPointingData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newSATNAVPointingData.columns["Timetag2"] = esData.data["Timetag2"].tolist()
        newSATNAVRollData.columns["Datetag"] = esData.data["Datetag"].tolist()
        newSATNAVRollData.columns["Timetag2"] = esData.data["Timetag2"].tolist()

        # Convert GPS UTC time values to seconds to be used for interpolation
        xTimer = []
        for i in range(satnavTimeData.data.shape[0]):
            xTimer.append(Utilities.timeTag2ToSec(satnavTimeData.data["NONE"][i]))

        # Convert ES TimeTag2 values to seconds to be used for interpolation
        yTimer = []
        for i in range(esData.data.shape[0]):
            yTimer.append(Utilities.timeTag2ToSec(esData.data["Timetag2"][i]))

        # Interpolate by time values
        ProcessL3.interpolateL3(satnavAzimuthData, xTimer, yTimer, newSATNAVAzimuthData, 'SunAz', 'linear')
        ProcessL3.interpolateL3(satnavHeadingData, xTimer, yTimer, newSATNAVHeadingData, 'Heading', 'linear')
        ProcessL3.interpolateL3(satnavPitchData, xTimer, yTimer, newSATNAVPitchData, 'Pitch', 'linear')
        ProcessL3.interpolateL3(satnavPointingData, xTimer, yTimer, newSATNAVPointingData, 'Pointing', 'linear')
        ProcessL3.interpolateL3(satnavRollData, xTimer, yTimer, newSATNAVRollData, 'Roll', 'linear')

        newSATNAVAzimuthData.columnsToDataset()
        newSATNAVHeadingData.columnsToDataset()
        newSATNAVPitchData.columnsToDataset()
        newSATNAVPointingData.columnsToDataset()
        newSATNAVRollData.columnsToDataset()

    # Interpolates by wavelength
    @staticmethod
    def interpolateWavelength(ds, newDS, new_x):

        # Copy dataset to dictionary
        ds.datasetToColumns()
        columns = ds.columns
        saveDatetag = columns.pop("Datetag")
        saveTimetag2 = columns.pop("Timetag2")
        
        # Get wavelength values
        wavelength = []
        for k in columns:
            #print(k)
            wavelength.append(float(k))
        x = np.asarray(wavelength)

        ''' PySciDON interpolated each instrument to a different set of bands.
            Here we use a common set.'''
        # # Determine interpolated wavelength values
        # start = np.ceil(wavelength[0])
        # end = np.floor(wavelength[len(wavelength)-1])
        # new_x = np.arange(start, end, interval)
        # #print(new_x)

        newColumns = collections.OrderedDict()
        newColumns["Datetag"] = saveDatetag
        newColumns["Timetag2"] = saveTimetag2

        # Append latpos/lonpos
        # ToDo: Do this better
        newColumns["LATPOS"] = saveDatetag
        newColumns["LONPOS"] = saveDatetag
        newColumns["AZIMUTH"] = saveDatetag
        newColumns["SHIP_TRUE"] = saveDatetag
        newColumns["PITCH"] = saveDatetag
        newColumns["ROTATOR"] = saveDatetag
        newColumns["ROLL"] = saveDatetag


        for i in range(new_x.shape[0]):
            #print(i, new_x[i])
            newColumns[str(new_x[i])] = []

        # Perform interpolation for each row
        for i in range(len(saveDatetag)):
            #print(i)

            values = []
            for k in columns:
                values.append(columns[k][i])
            y = np.asarray(values)
            #new_y = sp.interpolate.interp1d(x, y)(new_x)
            new_y = sp.interpolate.InterpolatedUnivariateSpline(x, y, k=3)(new_x)

            for i in range(new_x.shape[0]):
                newColumns[str(new_x[i])].append(new_y[i])


        #newDS = HDFDataset()
        newDS.columns = newColumns
        newDS.columnsToDataset()
        #print(ds.columns)
        #return newDS

    # Determines points to average data
    # Note: Prosoft always includes 1 point left/right of n
    #       even if it is outside of specified width
    @staticmethod
    def getDataAverage(n, data, time, width):
        lst = [data[n]]
        i = n-1
        while i >= 0:
            lst.append(data[i])
            if (time[n] - time[i]) > width:
                break
            i -= 1
        i = n+1
        while i < len(time):
            lst.append(data[i])
            if (time[i] - time[n]) > width:
                break
            i += 1
        avg = 0
        for v in lst:
            avg += v
        avg /= len(lst)
        return avg

    # # Performs averaging on the data
    # @staticmethod
    # def dataAveraging(ds):
        
    #     msg = "Process Data Average"
    #     print(msg)
    #     Utilities.writeLogFile(msg)
        
    #     interval = 2
    #     width = 1

    #     # Copy dataset to dictionary
    #     ds.datasetToColumns()
    #     columns = ds.columns
    #     saveDatetag = columns.pop("Datetag")
    #     saveTimetag2 = columns.pop("Timetag2")

    #     # convert timetag2 to seconds
    #     timer = []
    #     for i in range(len(saveTimetag2)):
    #         timer.append(Utilities.timeTag2ToSec(saveTimetag2[i]))

    #     # new data to return
    #     newColumns = collections.OrderedDict()
    #     newColumns["Datetag"] = []
    #     newColumns["Timetag2"] = []

    #     i = 0
    #     v = timer[0]
    #     while i < len(timer)-1:
    #         if (timer[i] - v) > interval:
    #             #print(saveTimetag2[i], timer[i])
    #             newColumns["Datetag"].append(saveDatetag[i])
    #             newColumns["Timetag2"].append(saveTimetag2[i])
    #             v = timer[i]
    #             i += 2
    #         else:
    #             i += 1

    #     for k in columns:
    #         data = columns[k]
    #         newColumns[k] = []

    #         # Do a natural log transform
    #         data = np.log(data)

    #         # generate points to average based on interval
    #         i = 0            
    #         v = timer[0]
    #         while i < len(timer)-1:
    #             if (timer[i] - v) > interval:
    #                 avg = ProcessL3.getDataAverage(i, data, timer, width)
    #                 newColumns[k].append(avg)
    #                 v = timer[i]
    #                 i += 2
    #             else:
    #                 i += 1

    #         newColumns = np.exp(newColumns)

    #     ds.columns = newColumns
    #     ds.columnsToDataset()

    # Makes each dataset have matching wavelength values
    # (this is not required, only for testing)
    @staticmethod
    def matchColumns(esData, liData, ltData):

        msg = "Match Columns"
        print(msg)
        Utilities.writeLogFile(msg)

        esData.datasetToColumns()
        liData.datasetToColumns()
        ltData.datasetToColumns()

        matchMin = -1
        matchMax = -1

        # Determine the minimum and maximum values for k
        for ds in [esData, liData, ltData]:
            nMin = -1
            nMax = -1
            for k in ds.columns.keys():
                #if k != "Datetag" and k != "Timetag2" and k != "LATPOS" and k != "LONPOS":
                if Utilities.isFloat(k):
                    num = float(k)
                    if nMin == -1:
                        nMin = num
                        nMax = num
                    elif num < nMin:
                        nMin = num
                    elif num > nMax:
                        nMax = num
            if matchMin == -1:
                matchMin = nMin
                matchMax = nMax
            if matchMin < nMin:
                matchMin = nMin
            if matchMax > nMax:
                matchMax = nMax
        #print(matchMin, matchMax)

        # Remove values to match minimum and maximum
        for ds in [esData, liData, ltData]:
            l = []
            for k in ds.columns.keys():
                #if k != "Datetag" and k != "Timetag2" and k != "LATPOS" and k != "LONPOS":
                if Utilities.isFloat(k):
                    num = float(k)
                    if num < matchMin:
                        l.append(k)
                    elif num > matchMax:
                        l.append(k)
            for k in l:
                del ds.columns[k]

        esData.columnsToDataset()
        liData.columnsToDataset()
        ltData.columnsToDataset()


    # Does time and wavelength interpolation and data averaging (not implemented here)
    @staticmethod
    def processL3(node):
        
        root = HDFRoot.HDFRoot() # creates a new instance of HDFRoot Class  (not sure about the .HDFRoot...its not a module in HDFRoot.py)
        root.copyAttributes(node) # Now copy the attributes in from the L2 object
        root.attributes["PROCESSING_LEVEL"] = "3"
        root.attributes["DEPTH_RESOLUTION"] = "N/A"

        # Time Interpolation        
        esGroup = None 
        gpsGroup = None
        liGroup = None
        ltGroup = None
        satnavGroup = None
        for gp in node.groups:
            #if gp.id.startswith("GPS"):
            if gp.getDataset("UTCPOS"):
                # print("GPS")
                gpsGroup = gp
            elif gp.getDataset("ES") and gp.attributes["FrameType"] == "ShutterLight":
                # print("ES")
                esGroup = gp
            elif gp.getDataset("LI") and gp.attributes["FrameType"] == "ShutterLight":
                # print("LI")
                liGroup = gp
            elif gp.getDataset("LT") and gp.attributes["FrameType"] == "ShutterLight":
                # print("LT")
                ltGroup = gp
            elif gp.getDataset("AZIMUTH"):
                # print("SATNAV")
                satnavGroup = gp

        refGroup = root.addGroup("Reference")
        sasGroup = root.addGroup("SAS")
        if gpsGroup is not None:
            gpsGroup2 = root.addGroup("GPS")
        if satnavGroup is not None:
            satnavGroup2 = root.addGroup("SATNAV")

        ProcessL3.convertGroup(esGroup, "ES", refGroup, "ES_hyperspectral")        
        ProcessL3.convertGroup(liGroup, "LI", sasGroup, "LI_hyperspectral")
        ProcessL3.convertGroup(ltGroup, "LT", sasGroup, "LT_hyperspectral")

        esData = refGroup.getDataset("ES_hyperspectral") # array with columns date, time, esdata*wavebands...
        liData = sasGroup.getDataset("LI_hyperspectral")
        ltData = sasGroup.getDataset("LT_hyperspectral")

        ''' PysciDON interpolates to the SLOWEST sampling rate, but ProSoft
        interpolates to the FASTEST. Not much in the literature on this, although
        Brewin et al. RSE 2016 used the slowest instrument on the AMT cruises.'''
        # Interpolate all datasets to the SLOWEST radiometric sampling rate
        esLength = len(esData.data["Timetag2"].tolist())
        liLength = len(liData.data["Timetag2"].tolist())
        ltLength = len(ltData.data["Timetag2"].tolist())
        
        interpData = None
        if esLength < liLength and esLength < ltLength:
            msg = "ES has fewest records - interpolating to ES; This should raise a red flag."
            print(msg)
            Utilities.writeLogFile(msg)                                       
            interpData = esData
        elif liLength < ltLength:
            msg = "LI has fewest records - interpolating to LI; This should raise a red flag."
            print(msg)
            Utilities.writeLogFile(msg)                                       
            interpData = liData
        else:
            msg = "LT has fewest records - interpolating to LT"
            print(msg)
            Utilities.writeLogFile(msg)                                       
            interpData = ltData
        #interpData = liData # Testing against Prosoft ##??

        # Perform time interpolation
        if not ProcessL3.interpolateData(esData, interpData, "ES"):
            return None
        if not ProcessL3.interpolateData(liData, interpData, "LI"):
            return None
        if not ProcessL3.interpolateData(ltData, interpData, "LT"):
            return None

        ProcessL3.interpolateGPSData(root, gpsGroup)
        ProcessL3.interpolateSATNAVData(root, satnavGroup)


        # Wavelength Interpolation
        interval = float(ConfigFile.settings["fL3InterpInterval"])
        ''' This was all very odd in PySciDon'''
        # root.attributes["BIN_INTERVAL"] = "1 m"
        # root.attributes["BIN_WIDTH"] = "0.5 m"
        # root.attributes["TIME_INTERVAL"] = "2 sec"
        # root.attributes["TIME_WIDTH"] = "1 sec"
        root.attributes["WAVEL_INTERP"] = (str(interval) + " nm") 

        newReferenceGroup = root.addGroup("Reference")
        newSASGroup = root.addGroup("SAS")
        if node.getGroup("GPS"):
            root.groups.append(node.getGroup("GPS"))
        if node.getGroup("SATNAV"):
            root.groups.append(node.getGroup("SATNAV"))

        referenceGroup = node.getGroup("Reference")
        sasGroup = node.getGroup("SAS")

        esData = referenceGroup.getDataset("ES_hyperspectral")
        liData = sasGroup.getDataset("LI_hyperspectral")
        ltData = sasGroup.getDataset("LT_hyperspectral")

        newESData = newReferenceGroup.addDataset("ES_hyperspectral")
        newLIData = newSASGroup.addDataset("LI_hyperspectral")
        newLTData = newSASGroup.addDataset("LT_hyperspectral")

        ''' PySciDON interpolated each instrument to a different set of bands.
        Here we use a common set.'''
        # Es dataset to dictionary
        esData.datasetToColumns()
        columns = esData.columns
        saveDatetag = columns.pop("Datetag")
        saveTimetag2 = columns.pop("Timetag2")
        # Get wavelength values
        esWavelength = []
        for k in columns:
            esWavelength.append(float(k))
        # Determine interpolated wavelength values
        esStart = np.ceil(esWavelength[0])
        esEnd = np.floor(esWavelength[len(esWavelength)-1])
        
        # Li dataset to dictionary
        liData.datasetToColumns()
        columns = liData.columns
        saveDatetag = columns.pop("Datetag")
        saveTimetag2 = columns.pop("Timetag2")
        # Get wavelength values
        liWavelength = []
        for k in columns:
            liWavelength.append(float(k))
        # Determine interpolated wavelength values
        liStart = np.ceil(liWavelength[0])
        liEnd = np.floor(liWavelength[len(liWavelength)-1])
        
        # Lt dataset to dictionary
        ltData.datasetToColumns()
        columns = ltData.columns
        saveDatetag = columns.pop("Datetag")
        saveTimetag2 = columns.pop("Timetag2")
        # Get wavelength values
        ltWavelength = []
        for k in columns:
            ltWavelength.append(float(k))
        # esWave = np.asarray(wavelength)
        # Determine interpolated wavelength values
        ltStart = np.ceil(ltWavelength[0])
        ltEnd = np.floor(ltWavelength[len(liWavelength)-1])

        # No extrapolation
        start = max(esStart,liStart,ltStart)
        end = min(esEnd,liEnd,ltEnd)
        new_x = np.arange(start, end, interval)
        # print(new_x)

        ProcessL3.interpolateWavelength(esData, newESData, new_x)
        ProcessL3.interpolateWavelength(liData, newLIData, new_x)
        ProcessL3.interpolateWavelength(ltData, newLTData, new_x)

        # Append latpos/lonpos to datasets
        if root.getGroup("GPS"):
            gpsGroup = node.getGroup("GPS")
            latposData = gpsGroup.getDataset("LATPOS")
            lonposData = gpsGroup.getDataset("LONPOS")

            latposData.datasetToColumns()
            lonposData.datasetToColumns()

            latpos = latposData.columns["NONE"]
            lonpos = lonposData.columns["NONE"]

            newESData.datasetToColumns()
            newLIData.datasetToColumns()
            newLTData.datasetToColumns()

            #print(newESData.columns)

            newESData.columns["LATPOS"] = latpos
            newLIData.columns["LATPOS"] = latpos
            newLTData.columns["LATPOS"] = latpos

            newESData.columns["LONPOS"] = lonpos
            newLIData.columns["LONPOS"] = lonpos
            newLTData.columns["LONPOS"] = lonpos

            newESData.columnsToDataset()
            newLIData.columnsToDataset()
            newLTData.columnsToDataset()
        
        if root.getGroup("SATNAV"):
            satnavGroup = node.getGroup("SATNAV")

            azimuthData = satnavGroup.getDataset("AZIMUTH")
            headingData = satnavGroup.getDataset("HEADING")
            pitchData = satnavGroup.getDataset("PITCH")
            pointingData = satnavGroup.getDataset("POINTING")
            rollData = satnavGroup.getDataset("ROLL")

            azimuthData.datasetToColumns()
            headingData.datasetToColumns()
            pitchData.datasetToColumns()
            pointingData.datasetToColumns()
            rollData.datasetToColumns()            

            azimuth = azimuthData.columns["SUN"]
            shipTrue = headingData.columns["SHIP_TRUE"]
            pitch = pitchData.columns["SAS"]
            rotator = pointingData.columns["ROTATOR"]
            roll = rollData.columns["SAS"]

            newESData.datasetToColumns()
            newLIData.datasetToColumns()
            newLTData.datasetToColumns()
            
            newESData.columns["AZIMUTH"] = azimuth
            newLIData.columns["AZIMUTH"] = azimuth
            newLTData.columns["AZIMUTH"] = azimuth

            newESData.columns["SHIP_TRUE"] = shipTrue
            newLIData.columns["SHIP_TRUE"] = shipTrue
            newLTData.columns["SHIP_TRUE"] = shipTrue

            newESData.columns["PITCH"] = pitch
            newLIData.columns["PITCH"] = pitch
            newLTData.columns["PITCH"] = pitch
            
            newESData.columns["ROTATOR"] = rotator
            newLIData.columns["ROTATOR"] = rotator
            newLTData.columns["ROTATOR"] = rotator
            
            newESData.columns["ROLL"] = roll
            newLIData.columns["ROLL"] = roll
            newLTData.columns["ROLL"] = roll

            newESData.columnsToDataset()
            newLIData.columnsToDataset()
            newLTData.columnsToDataset()

        # Make each dataset have matching wavelength values (for testing)
        ProcessL3.matchColumns(newESData, newLIData, newLTData)

        #ProcessL3.dataAveraging(newESData)
        #ProcessL3.dataAveraging(newLIData)
        #ProcessL3.dataAveraging(newLTData)

        return root
