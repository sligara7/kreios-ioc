/**
 * KREIOS-150 Momentum Microscope areaDetector Driver
 *
 * Implementation file for the KREIOS-150 driver.
 * Interfaces with SPECS KREIOS-150 via SpecsLab Prodigy Remote In protocol.
 *
 * Based on specsAnalyser driver structure, extended for 1D/2D/3D data.
 *
 * Author: NSLS-II / SPECS Integration
 * Date: January 2026
 */

#include "kreios.h"

// Driver version
#define DRIVER_VERSION     1
#define DRIVER_REVISION    0
#define DRIVER_MODIFICATION 0

static const char *driverName = "Kreios";

/**
 * C glue to make config function available in iocsh
 */
extern "C"
{
    int kreiosConfig(const char *portName, const char *driverPort, int maxBuffers,
                     size_t maxMemory, int priority, int stackSize)
    {
        new Kreios(portName, driverPort, maxBuffers, maxMemory, priority, stackSize);
        return asynSuccess;
    }

    int kreiosSetDebugLevel(const char *driver, const char *method, int debug)
    {
        Kreios *pKreios;
        static const char *functionName = "kreiosSetDebugLevel";

        pKreios = (Kreios *)findAsynPortDriver(driver);
        if (!pKreios) {
            printf("%s: Error: port %s not found.\n", functionName, driver);
            return -1;
        }
        return pKreios->debugLevel(method, debug);
    }
}

/**
 * Function to run the acquisition task within a separate thread
 */
static void kreiosTaskC(void *drvPvt)
{
    Kreios *pPvt = (Kreios *)drvPvt;
    pPvt->kreiosTask();
}

/**
 * Kreios destructor
 */
Kreios::~Kreios()
{
}

/**
 * Kreios constructor
 */
Kreios::Kreios(const char *portName, const char *driverPort, int maxBuffers,
               size_t maxMemory, int priority, int stackSize)
    : ADDriver(portName,
               1,
               NUM_KREIOS_PARAMS,
               maxBuffers,
               maxMemory,
               asynEnumMask | asynFloat64ArrayMask,
               asynEnumMask | asynFloat64ArrayMask,
               ASYN_CANBLOCK,
               1,
               priority,
               stackSize)
{
    static const char *functionName = "Kreios::Kreios";
    int status = 0;
    char versionString[20];

    // Setup flag for first connection
    firstConnect_ = true;

    // Initialize debugger
    initDebugger(1);
    debugLevel("Kreios::asynWriteRead", 0);

    // Initialize non-static data members
    portUser_ = NULL;
    strcpy(driverPort_, driverPort);

    // Create epicsEvents for signaling acquisition start/stop
    this->startEventId_ = epicsEventCreate(epicsEventEmpty);
    if (!this->startEventId_) {
        debug(functionName, "epicsEventCreate failure for start event");
        status = asynError;
    }

    this->stopEventId_ = epicsEventCreate(epicsEventEmpty);
    if (!this->stopEventId_) {
        debug(functionName, "epicsEventCreate failure for stop event");
        status = asynError;
    }

    // Create all KREIOS parameters
    createParam(KREIOSConnectString,                   asynParamInt32,         &KREIOSConnect_);
    createParam(KREIOSConnectedString,                 asynParamInt32,         &KREIOSConnected_);
    createParam(KREIOSPauseAcqString,                  asynParamInt32,         &KREIOSPauseAcq_);
    createParam(KREIOSMsgCounterString,                asynParamInt32,         &KREIOSMsgCounter_);
    createParam(KREIOSServerNameString,                asynParamOctet,         &KREIOSServerName_);
    createParam(KREIOSProtocolVersionString,           asynParamInt32,         &KREIOSProtocolVersion_);
    createParam(KREIOSProtocolVersionMinorString,      asynParamInt32,         &KREIOSProtocolVersionMinor_);
    createParam(KREIOSProtocolVersionMajorString,      asynParamInt32,         &KREIOSProtocolVersionMajor_);

    // Energy parameters
    createParam(KREIOSStartEnergyString,               asynParamFloat64,       &KREIOSStartEnergy_);
    createParam(KREIOSEndEnergyString,                 asynParamFloat64,       &KREIOSEndEnergy_);
    createParam(KREIOSRetardingRatioString,            asynParamFloat64,       &KREIOSRetardingRatio_);
    createParam(KREIOSKineticEnergyString,             asynParamFloat64,       &KREIOSKineticEnergy_);
    createParam(KREIOSStepWidthString,                 asynParamFloat64,       &KREIOSStepWidth_);
    createParam(KREIOSPassEnergyString,                asynParamFloat64,       &KREIOSPassEnergy_);

    // Samples and iteration parameters
    createParam(KREIOSSamplesString,                   asynParamInt32,         &KREIOSSamples_);
    createParam(KREIOSSamplesIterationString,          asynParamInt32,         &KREIOSSamplesIteration_);
    createParam(KREIOSSnapshotValuesString,            asynParamInt32,         &KREIOSSnapshotValues_);
    createParam(KREIOSCurrentSampleString,             asynParamInt32,         &KREIOSCurrentSample_);
    createParam(KREIOSPercentCompleteString,           asynParamInt32,         &KREIOSPercentComplete_);
    createParam(KREIOSRemainingTimeString,             asynParamFloat64,       &KREIOSRemainingTime_);
    createParam(KREIOSCurrentSampleIterationString,    asynParamInt32,         &KREIOSCurrentSampleIteration_);
    createParam(KREIOSPercentCompleteIterationString,  asynParamInt32,         &KREIOSPercentCompleteIteration_);
    createParam(KREIOSRemainingTimeIterationString,    asynParamFloat64,       &KREIOSRemainingTimeIteration_);

    // Data arrays (spectrum, image, volume for 1D/2D/3D)
    createParam(KREIOSAcqSpectrumString,               asynParamFloat64Array,  &KREIOSAcqSpectrum_);
    createParam(KREIOSAcqImageString,                  asynParamFloat64Array,  &KREIOSAcqImage_);
    createParam(KREIOSAcqVolumeString,                 asynParamFloat64Array,  &KREIOSAcqVolume_);
    createParam(KREIOSEnergyAxisString,                asynParamFloat64Array,  &KREIOSEnergyAxis_);

    // Operating mode parameters
    createParam(KREIOSRunModeString,                   asynParamInt32,         &KREIOSRunMode_);
    createParam(KREIOSOperatingModeString,             asynParamInt32,         &KREIOSOperatingMode_);
    createParam(KREIOSDefineString,                    asynParamInt32,         &KREIOSDefine_);
    createParam(KREIOSValidateString,                  asynParamInt32,         &KREIOSValidate_);
    createParam(KREIOSLensModeString,                  asynParamInt32,         &KREIOSLensMode_);
    createParam(KREIOSScanRangeString,                 asynParamInt32,         &KREIOSScanRange_);

    // Detector dimension parameters (key for 1D/2D/3D)
    createParam(KREIOSValuesPerSampleString,           asynParamInt32,         &KREIOSValuesPerSample_);
    createParam(KREIOSNumSlicesString,                 asynParamInt32,         &KREIOSNumSlices_);
    createParam(KREIOSNonEnergyChannelsString,         asynParamInt32,         &KREIOSNonEnergyChannels_);
    createParam(KREIOSNonEnergyUnitsString,            asynParamOctet,         &KREIOSNonEnergyUnits_);
    createParam(KREIOSNonEnergyMinString,              asynParamFloat64,       &KREIOSNonEnergyMin_);
    createParam(KREIOSNonEnergyMaxString,              asynParamFloat64,       &KREIOSNonEnergyMax_);

    // KREIOS-150 specific hardware parameters
    createParam(KREIOSDetectorVoltageString,           asynParamFloat64,       &KREIOSDetectorVoltage_);
    createParam(KREIOSBiasVoltageString,               asynParamFloat64,       &KREIOSBiasVoltage_);
    createParam(KREIOSCoilCurrentString,               asynParamFloat64,       &KREIOSCoilCurrent_);
    createParam(KREIOSFocusDisplacement1String,        asynParamFloat64,       &KREIOSFocusDisplacement1_);
    createParam(KREIOSFocusDisplacement2String,        asynParamFloat64,       &KREIOSFocusDisplacement2_);
    createParam(KREIOSAuxVoltageString,                asynParamFloat64,       &KREIOSAuxVoltage_);
    createParam(KREIOSDLDVoltageString,                asynParamFloat64,       &KREIOSDLDVoltage_);

    // Momentum microscopy parameters
    createParam(KREIOSKxMinString,                     asynParamFloat64,       &KREIOSKxMin_);
    createParam(KREIOSKxMaxString,                     asynParamFloat64,       &KREIOSKxMax_);
    createParam(KREIOSKyMinString,                     asynParamFloat64,       &KREIOSKyMin_);
    createParam(KREIOSKyMaxString,                     asynParamFloat64,       &KREIOSKyMax_);
    createParam(KREIOSKxCenterString,                  asynParamFloat64,       &KREIOSKxCenter_);
    createParam(KREIOSKyCenterString,                  asynParamFloat64,       &KREIOSKyCenter_);

    // PEEM parameters
    createParam(KREIOSFieldOfViewString,               asynParamFloat64,       &KREIOSFieldOfView_);
    createParam(KREIOSMagnificationString,             asynParamFloat64,       &KREIOSMagnification_);

    // Safe state and data delay
    createParam(KREIOSSafeStateString,                 asynParamInt32,         &KREIOSSafeState_);
    createParam(KREIOSDataDelayMaxString,              asynParamFloat64,       &KREIOSDataDelayMax_);

    // Set default values
    setIntegerParam(KREIOSConnected_,                 0);
    setIntegerParam(KREIOSPauseAcq_,                  0);
    setIntegerParam(KREIOSMsgCounter_,                0);
    setIntegerParam(KREIOSPercentComplete_,           0);
    setIntegerParam(KREIOSCurrentSample_,             0);
    setIntegerParam(KREIOSSnapshotValues_,            1);
    setIntegerParam(KREIOSSamplesIteration_,          0);
    setIntegerParam(KREIOSPercentCompleteIteration_,  0);
    setIntegerParam(KREIOSCurrentSampleIteration_,    0);
    setDoubleParam(KREIOSRemainingTime_,              0.0);
    setIntegerParam(KREIOSSafeState_,                 1);
    setDoubleParam(KREIOSDataDelayMax_,               5.0);

    // Default dimension parameters for 1D spectrum
    setIntegerParam(KREIOSValuesPerSample_,           1);
    setIntegerParam(KREIOSNumSlices_,                 1);
    setIntegerParam(KREIOSNonEnergyChannels_,         1);

    // Set standard ADDriver parameters
    setStringParam(ADManufacturer, "SPECS GmbH");
    setStringParam(ADModel, "KREIOS-150");
    epicsSnprintf(versionString, sizeof(versionString), "%d.%d.%d",
                  DRIVER_VERSION, DRIVER_REVISION, DRIVER_MODIFICATION);
    setStringParam(NDDriverVersion, versionString);
    setStringParam(ADSDKVersion, "Prodigy Remote In v1.22");
    setStringParam(ADSerialNumber, "N/A");
    setStringParam(ADFirmwareVersion, "N/A");

    // Set max detector dimensions
    setIntegerParam(ADMaxSizeX, KREIOS_DETECTOR_SIZE_X);
    setIntegerParam(ADMaxSizeY, KREIOS_DETECTOR_SIZE_Y);
    setIntegerParam(ADSizeX, KREIOS_DETECTOR_SIZE_X);
    setIntegerParam(ADSizeY, KREIOS_DETECTOR_SIZE_Y);

    // Initialize run modes
    runModes_.push_back("FAT");
    runModes_.push_back("SFAT");
    runModes_.push_back("FRR");
    runModes_.push_back("FE");
    runModes_.push_back("LVS");

    // Initialize operating modes
    operatingModes_.push_back("Spectroscopy");
    operatingModes_.push_back("Momentum");
    operatingModes_.push_back("PEEM");

    if (status == asynSuccess) {
        debug(functionName, "Starting up acquisition task...");
        // Create the thread that runs the acquisition
        status = (epicsThreadCreate("KreiosTask",
                                    epicsThreadPriorityMedium,
                                    epicsThreadGetStackSize(epicsThreadStackMedium),
                                    (EPICSTHREADFUNC)kreiosTaskC,
                                    this) == NULL);
        if (status) {
            debug(functionName, "epicsThreadCreate failure for acquisition task");
        }
    }

    if (status == asynSuccess) {
        // Attempt connection
        status |= makeConnection();

        // Read in the lens modes
        status |= readSpectrumParameter(KREIOSLensMode_);
        // Read in the scan ranges
        status |= readSpectrumParameter(KREIOSScanRange_);
        // Setup run modes
        status |= readRunModes();
        // Setup operating modes
        status |= readOperatingModes();
    }

    // Check if status is bad
    if (status != asynSuccess) {
        setIntegerParam(ADStatus, ADStatusError);
        setStringParam(ADStatusMessage, "Failed to initialise - check connection");
        callParamCallbacks();
    }
}

/**
 * Make connection to the Prodigy server
 */
asynStatus Kreios::makeConnection()
{
    int status = asynSuccess;

    status = connect();

    if (status == asynSuccess) {
        if (firstConnect_ == true) {
            // First connection - read device name
            if (status == asynSuccess) {
                status = readDeviceVisibleName();
            }

            // Setup EPICS parameters from hardware
            if (status == asynSuccess) {
                status = setupEPICSParameters();
            }

            // Read number of non-energy channels
            if (status == asynSuccess) {
                int nonEnergyChannels = 0;
                getAnalyserParameter("NumNonEnergyChannels", nonEnergyChannels);
                setIntegerParam(KREIOSNonEnergyChannels_, nonEnergyChannels);
            }

            callParamCallbacks();

            if (status == asynSuccess) {
                firstConnect_ = false;
            }
        }
    }

    return (asynStatus)status;
}

/**
 * Connect to the low-level asyn port
 */
asynStatus Kreios::connect()
{
    asynStatus status = asynSuccess;
    const char *functionName = "Kreios::connect";

    status = asynPortConnect(driverPort_, 0, &portUser_, "\n", "\n");
    if (status != asynSuccess) {
        debug(functionName, "Failed to connect to low level asynOctetSyncIO port", driverPort_);
        setIntegerParam(KREIOSConnected_, 0);
        setIntegerParam(ADStatus, ADStatusError);
        callParamCallbacks();
    } else {
        setIntegerParam(KREIOSConnected_, 1);
        setStringParam(ADStatusMessage, "Connected to KREIOS");
        setIntegerParam(ADStatus, ADStatusIdle);
        callParamCallbacks();
    }
    return status;
}

/**
 * Disconnect from the low-level asyn port
 */
asynStatus Kreios::disconnect()
{
    asynStatus status = asynSuccess;
    const char *functionName = "Kreios::disconnect";
    int connected = 0;

    getIntegerParam(KREIOSConnected_, &connected);
    if (connected == 1) {
        status = asynPortDisconnect(portUser_);
        if (status != asynSuccess) {
            debug(functionName, "Failed to disconnect from low level asynOctetSyncIO port", driverPort_);
        }
    }
    return status;
}

/**
 * Main acquisition task
 *
 * This function runs in a separate thread and handles all acquisition logic.
 * It supports 1D (spectrum), 2D (image), and 3D (volume) data acquisition.
 */
void Kreios::kreiosTask()
{
    int status = asynSuccess;
    int acquire;
    int nbytes;
    int numImages = 0;
    int numImagesCounter = 0;
    int imageCounter = 0;
    int imageMode = 0;
    int arrayCallbacks = 0;
    int iterations = 1;
    double acquireTime, acquirePeriod;
    epicsTimeStamp startTime, endTime;
    double elapsedTime;
    std::map<std::string, std::string> data;
    NDArray *pImage;
    size_t dims[3];  // Support up to 3D
    int ndims;
    NDDataType_t dataType;
    epicsFloat64 *pNDData = 0;
    epicsFloat64 *image = 0;
    epicsFloat64 *spectrum = 0;
    epicsFloat64 *volume = 0;
    int nonEnergyChannels = 0;  // ValuesPerSample (pixels)
    int energyChannels = 0;     // Number of samples (energy points)
    int numSlices = 0;          // NumberOfSlices (for 3D)
    int currentDataPoint = 0;
    int numDataPoints = 0;
    int runMode = 0;
    int safeState = 1;
    const char *functionName = "Kreios::kreiosTask";

    debug(functionName, "Acquisition task started");

    this->lock();
    while (1) {
        getIntegerParam(ADAcquire, &acquire);

        // If not acquiring, wait for start event
        if (!acquire) {
            // Reset paused state
            setIntegerParam(KREIOSPauseAcq_, 0);

            if (!status) {
                debug(functionName, "Waiting for acquire command");
                setStringParam(ADStatusMessage, "Waiting for acquire command");
                int adstatus;
                getIntegerParam(ADStatus, &adstatus);
                if (adstatus != ADStatusAborted && adstatus != ADStatusError)
                    setIntegerParam(ADStatus, ADStatusIdle);
            }

            // Reset counters
            setIntegerParam(ADNumExposuresCounter, 0);
            setIntegerParam(ADNumImagesCounter, 0);
            callParamCallbacks();

            // Wait for start event
            this->unlock();
            debug(functionName, "Waiting for acquire to start");
            status = epicsEventWait(this->startEventId_);
            this->lock();
            getIntegerParam(ADAcquire, &acquire);
            setIntegerParam(KREIOSPauseAcq_, 0);

            // Read number of exposures (iterations)
            getIntegerParam(ADNumExposures, &iterations);

            // Read dimension parameters for 1D/2D/3D determination
            status = getAnalyserParameter("NumNonEnergyChannels", nonEnergyChannels);
            if (status == asynSuccess) {
                setIntegerParam(KREIOSNonEnergyChannels_, nonEnergyChannels);
            }

            // Get values per sample (detector pixels in non-energy direction)
            getIntegerParam(KREIOSValuesPerSample_, &nonEnergyChannels);
            if (nonEnergyChannels < 1) nonEnergyChannels = 1;

            // Get number of slices for 3D data
            getIntegerParam(KREIOSNumSlices_, &numSlices);
            if (numSlices < 1) numSlices = 1;

            // Clear stale data
            if (status == asynSuccess) {
                sendSimpleCommand(KREIOS_CMD_CLEAR);

                // Define spectrum according to run mode
                getIntegerParam(KREIOSRunMode_, &runMode);
                switch (runMode) {
                    case KREIOS_RUN_FAT:
                        status = defineSpectrumFAT();
                        break;
                    case KREIOS_RUN_SFAT:
                        status = defineSpectrumSFAT();
                        break;
                    case KREIOS_RUN_FRR:
                        status = defineSpectrumFRR();
                        break;
                    case KREIOS_RUN_FE:
                        status = defineSpectrumFE();
                        break;
                    case KREIOS_RUN_LVS:
                        status = defineSpectrumLVS();
                        break;
                    default:
                        debug(functionName, "Invalid run mode specified", runMode);
                        break;
                }
            }

            // Validate spectrum
            if (status == asynSuccess) {
                status = validateSpectrum();
            }

            if (status == asynSuccess) {
                // Read energy channels from validation
                getIntegerParam(KREIOSSamplesIteration_, &energyChannels);
                setIntegerParam(KREIOSSamples_, (energyChannels * iterations));

                // Handle snapshot mode energy channel calculation
                if (runMode == KREIOS_RUN_SFAT) {
                    double start, end, width;
                    getDoubleParam(KREIOSStartEnergy_, &start);
                    getDoubleParam(KREIOSEndEnergy_, &end);
                    getDoubleParam(KREIOSStepWidth_, &width);
                    energyChannels = (int)floor(((end - start) / width) + 0.5) + 1;
                    setIntegerParam(KREIOSSamplesIteration_, energyChannels);
                    setIntegerParam(KREIOSSamples_, (energyChannels * iterations));
                }

                // Free previous buffers
                if (image) {
                    free(image);
                    image = 0;
                }
                if (spectrum) {
                    free(spectrum);
                    spectrum = 0;
                }
                if (volume) {
                    free(volume);
                    volume = 0;
                }

                // Determine data dimensionality and allocate buffers
                // 1D: nonEnergyChannels=1, numSlices=1
                // 2D: nonEnergyChannels>1, numSlices=1
                // 3D: nonEnergyChannels>1, numSlices>1

                debug(functionName, "Allocating buffers: energyChannels=", energyChannels);
                debug(functionName, "Allocating buffers: nonEnergyChannels=", nonEnergyChannels);
                debug(functionName, "Allocating buffers: numSlices=", numSlices);

                // Always allocate spectrum (1D integrated data)
                spectrum = (double *)malloc(energyChannels * sizeof(epicsFloat64));

                if (nonEnergyChannels > 1 && numSlices == 1) {
                    // 2D image: energy x pixels
                    ndims = 2;
                    dims[0] = energyChannels;
                    dims[1] = nonEnergyChannels;
                    image = (double *)malloc(nonEnergyChannels * energyChannels * sizeof(epicsFloat64));
                    debug(functionName, "2D mode: image buffer allocated");
                } else if (nonEnergyChannels > 1 && numSlices > 1) {
                    // 3D volume: slices x energy x pixels
                    ndims = 3;
                    dims[0] = energyChannels;
                    dims[1] = nonEnergyChannels;
                    dims[2] = numSlices;
                    volume = (double *)malloc(numSlices * energyChannels * nonEnergyChannels * sizeof(epicsFloat64));
                    debug(functionName, "3D mode: volume buffer allocated");
                } else {
                    // 1D spectrum
                    ndims = 1;
                    dims[0] = energyChannels;
                    debug(functionName, "1D mode: spectrum only");
                }

                if (spectrum == 0 || (ndims >= 2 && image == 0 && volume == 0)) {
                    status = asynError;
                    debug(functionName, "Buffer allocation failed");
                }

                // Set size parameters
                setIntegerParam(NDArraySizeX, energyChannels);
                if (ndims >= 2) {
                    setIntegerParam(NDArraySizeY, nonEnergyChannels);
                }
                nbytes = dims[0];
                for (int d = 1; d < ndims; d++) {
                    nbytes *= dims[d];
                }
                nbytes *= sizeof(double);
                setIntegerParam(NDArraySize, nbytes);
                callParamCallbacks();

                getIntegerParam(NDDataType, (int *)&dataType);
            }
        }

        // Check for errors
        if (status != asynSuccess) {
            acquire = 0;
            setIntegerParam(ADAcquire, acquire);
            setIntegerParam(ADStatus, ADStatusError);
            callParamCallbacks();
        } else {
            // Initialize buffers
            for (int x = 0; x < energyChannels; x++) {
                spectrum[x] = 0.0;
            }
            if (image) {
                for (int x = 0; x < energyChannels * nonEnergyChannels; x++) {
                    image[x] = 0.0;
                }
            }
            if (volume) {
                for (int x = 0; x < energyChannels * nonEnergyChannels * numSlices; x++) {
                    volume[x] = 0.0;
                }
            }

            // Allocate NDArray
            pImage = this->pNDArrayPool->alloc(ndims, dims, dataType, 0, NULL);

            // Reset progress
            setIntegerParam(KREIOSPercentCompleteIteration_, 0);
            setIntegerParam(KREIOSCurrentSampleIteration_, 0);
            setIntegerParam(KREIOSPercentComplete_, 0);
            setIntegerParam(KREIOSCurrentSample_, 0);

            debug(functionName, "Starting acquisition");
            epicsTimeGetCurrent(&startTime);

            getDoubleParam(ADAcquireTime, &acquireTime);
            getDoubleParam(ADAcquirePeriod, &acquirePeriod);
            getIntegerParam(ADNumImages, &numImages);
            getIntegerParam(ADImageMode, &imageMode);
            getIntegerParam(KREIOSSafeState_, &safeState);

            setIntegerParam(ADStatus, ADStatusInitializing);
            setStringParam(ADStatusMessage, "Executing pre-scan...");

            // Loop over iterations
            int iteration = 0;
            while ((iteration < iterations) && (acquire == 1)) {
                sendSimpleCommand(KREIOS_CMD_CLEAR);
                sendStartCommand(safeState);

                std::vector<double> values;
                currentDataPoint = 0;
                numDataPoints = 0;
                sendSimpleCommand(KREIOS_CMD_GET_STATUS, &data);
                pNDData = (double *)(pImage->pData);

                // Acquisition polling loop
                while (acquire && status == asynSuccess &&
                       (((data["ControllerState"] != "finished") || (currentDataPoint < energyChannels)) &&
                        (data["ControllerState"] != "aborted") &&
                        (data["ControllerState"] != "error"))) {

                    int readEndDataPoint;
                    this->unlock();
                    epicsThreadSleep(KREIOS_UPDATE_RATE);
                    this->lock();

                    status = sendSimpleCommand(KREIOS_CMD_GET_STATUS, &data);
                    if (data.count("Code") > 0) {
                        data["ControllerState"] = "error";
                    }
                    debug(functionName, "Status", data);

                    // Check for available data
                    readIntegerData(data, "NumberOfAcquiredPoints", numDataPoints);

                    if (numDataPoints > currentDataPoint) {
                        if (currentDataPoint == 0) {
                            setIntegerParam(ADStatus, ADStatusAcquire);
                            setStringParam(ADStatusMessage, "Acquiring data...");

                            // Wait for first data to be ready
                            double period;
                            getDoubleParam(KREIOSDataDelayMax_, &period);
                            period = fmin(acquireTime, period);
                            debug(functionName, "Initial delay", period);
                            epicsThreadSleep(period);
                            readSpectrumDataInfo(KREIOSOrdinateRange);
                        }

                        // Limit read request size
                        const int maxValues = 1000000;
                        readEndDataPoint = numDataPoints;
                        if ((readEndDataPoint - currentDataPoint) * nonEnergyChannels > maxValues)
                            readEndDataPoint = currentDataPoint + (maxValues / nonEnergyChannels);

                        readAcquisitionData(currentDataPoint, (readEndDataPoint - 1), values);

                        // Process received data
                        int index = 0;
                        int numRxDataPoints = (int)values.size();
                        debug(functionName, "Samples read", (readEndDataPoint - currentDataPoint));
                        debug(functionName, "Data points received", numRxDataPoints);

                        if (numRxDataPoints < (readEndDataPoint - currentDataPoint) * nonEnergyChannels) {
                            debug(functionName, "*** Received too few data points ***");
                            sendSimpleCommand(KREIOS_CMD_ABORT);
                            status = asynError;
                            setIntegerParam(ADAcquire, 0);
                            setIntegerParam(ADStatus, ADStatusError);
                            setStringParam(ADStatusMessage, "KREIOS Receive Error");
                            continue;
                        }

                        // Store data based on dimensionality
                        if (ndims == 1) {
                            // 1D: just store spectrum
                            for (int x = currentDataPoint; x < readEndDataPoint; x++) {
                                if (iteration == 0) {
                                    spectrum[x] = values[index];
                                    pNDData[x] = values[index];
                                } else {
                                    spectrum[x] += values[index];
                                    pNDData[x] += values[index];
                                }
                                index++;
                            }
                        } else if (ndims == 2) {
                            // 2D: store image[y][x] = energy x pixels
                            for (int y = 0; y < nonEnergyChannels; y++) {
                                for (int x = currentDataPoint; x < readEndDataPoint; x++) {
                                    if (iteration == 0) {
                                        pNDData[(y * energyChannels) + x] = values[index];
                                        image[(y * energyChannels) + x] = values[index];
                                    } else {
                                        pNDData[(y * energyChannels) + x] += values[index];
                                        image[(y * energyChannels) + x] += values[index];
                                    }
                                    // Integrate for 1D spectrum
                                    spectrum[x] += values[index];
                                    index++;
                                }
                            }
                        } else if (ndims == 3) {
                            // 3D: store volume[z][y][x] = slices x pixels x energy
                            // Flat index = slice * (S * V) + sample * V + pixel
                            // where S = energyChannels, V = nonEnergyChannels
                            for (int z = 0; z < numSlices; z++) {
                                for (int y = 0; y < nonEnergyChannels; y++) {
                                    for (int x = currentDataPoint; x < readEndDataPoint; x++) {
                                        int flatIdx = z * (energyChannels * nonEnergyChannels) +
                                                      y * energyChannels + x;
                                        if (index < numRxDataPoints) {
                                            if (iteration == 0) {
                                                pNDData[flatIdx] = values[index];
                                                volume[flatIdx] = values[index];
                                            } else {
                                                pNDData[flatIdx] += values[index];
                                                volume[flatIdx] += values[index];
                                            }
                                            // Integrate for 1D spectrum
                                            spectrum[x] += values[index];
                                            index++;
                                        }
                                    }
                                }
                            }
                        }

                        currentDataPoint = readEndDataPoint;

                        // Callback for spectrum data
                        if (iteration == 0) {
                            doCallbacksFloat64Array(spectrum, currentDataPoint, KREIOSAcqSpectrum_, 0);
                        } else {
                            doCallbacksFloat64Array(spectrum, energyChannels, KREIOSAcqSpectrum_, 0);
                        }

                        // Callback for 2D image data
                        if (image) {
                            if (iteration == 0) {
                                doCallbacksFloat64Array(image, currentDataPoint * nonEnergyChannels,
                                                        KREIOSAcqImage_, 0);
                            } else {
                                doCallbacksFloat64Array(image, energyChannels * nonEnergyChannels,
                                                        KREIOSAcqImage_, 0);
                            }
                        }

                        // Callback for 3D volume data
                        if (volume) {
                            doCallbacksFloat64Array(volume,
                                                    energyChannels * nonEnergyChannels * numSlices,
                                                    KREIOSAcqVolume_, 0);
                        }
                    }

                    // Update progress
                    int percent = (int)(((double)currentDataPoint / (double)energyChannels) * 100.0);
                    setIntegerParam(KREIOSPercentCompleteIteration_, percent);
                    setIntegerParam(KREIOSCurrentSampleIteration_, currentDataPoint);

                    // Update overall progress
                    int totalSamples = energyChannels * iterations;
                    int currentTotal = (iteration * energyChannels) + currentDataPoint;
                    percent = (int)(((double)currentTotal / (double)totalSamples) * 100.0);
                    setIntegerParam(KREIOSPercentComplete_, percent);
                    setIntegerParam(KREIOSCurrentSample_, currentTotal);

                    // Check for abort request
                    getIntegerParam(ADAcquire, &acquire);
                    if (!acquire) {
                        sendSimpleCommand(KREIOS_CMD_ABORT);
                        setIntegerParam(ADStatus, ADStatusAborted);
                        setStringParam(ADStatusMessage, "Acquisition aborted");
                    }

                    callParamCallbacks();
                }

                iteration++;
            }

            // Acquisition complete
            if (acquire && status == asynSuccess) {
                setIntegerParam(ADStatus, ADStatusIdle);
                setStringParam(ADStatusMessage, "Acquisition complete");
                setIntegerParam(KREIOSPercentComplete_, 100);
                setIntegerParam(KREIOSPercentCompleteIteration_, 100);

                // Do NDArray callback
                getIntegerParam(NDArrayCallbacks, &arrayCallbacks);
                getIntegerParam(NDArrayCounter, &imageCounter);
                imageCounter++;
                setIntegerParam(NDArrayCounter, imageCounter);
                pImage->uniqueId = imageCounter;
                updateTimeStamps(pImage);
                getAttributes(pImage->pAttributeList);

                if (arrayCallbacks) {
                    debug(functionName, "Calling NDArray callback");
                    doCallbacksGenericPointer(pImage, NDArrayData, 0);
                }
            }

            // Release NDArray
            if (pImage) {
                pImage->release();
            }

            setIntegerParam(ADAcquire, 0);
            callParamCallbacks();
        }
    }
}

/**
 * Called when asyn clients call pasynInt32->write()
 */
asynStatus Kreios::writeInt32(asynUser *pasynUser, epicsInt32 value)
{
    int function = pasynUser->reason;
    int adstatus;
    int acquiring;
    asynStatus status = asynSuccess;
    const char *functionName = "Kreios::writeInt32";

    getIntegerParam(ADStatus, &adstatus);
    getIntegerParam(ADAcquire, &acquiring);

    if (function == ADAcquire) {
        if (value && !acquiring) {
            setStringParam(ADStatusMessage, "Acquiring data");
        }
        if (!value && acquiring) {
            setStringParam(ADStatusMessage, "Acquisition stopped");
            setIntegerParam(ADStatus, ADStatusAborted);
        }
    }
    callParamCallbacks();

    // Set the parameter
    status = setIntegerParam(function, value);

    if (function == ADAcquire) {
        if (value && !acquiring) {
            // Signal start event
            epicsEventSignal(startEventId_);
        }
        if (!value && acquiring) {
            // Signal stop event
            epicsEventSignal(stopEventId_);
        }
    } else if (function == KREIOSConnect_) {
        if (value == 1) {
            status = makeConnection();
        } else {
            status = disconnect();
        }
    } else if (function < FIRST_KREIOS_PARAM) {
        status = ADDriver::writeInt32(pasynUser, value);
    }

    callParamCallbacks();

    if (status) {
        asynPrint(pasynUser, ASYN_TRACE_ERROR,
                  "%s: error, status=%d function=%d, value=%d\n",
                  functionName, status, function, value);
    } else {
        asynPrint(pasynUser, ASYN_TRACEIO_DRIVER,
                  "%s: function=%d, value=%d\n",
                  functionName, function, value);
    }
    return status;
}

/**
 * Called when asyn clients call pasynFloat64->write()
 */
asynStatus Kreios::writeFloat64(asynUser *pasynUser, epicsFloat64 value)
{
    int function = pasynUser->reason;
    asynStatus status = asynSuccess;
    const char *functionName = "Kreios::writeFloat64";

    status = setDoubleParam(function, value);

    if (function < FIRST_KREIOS_PARAM) {
        status = ADDriver::writeFloat64(pasynUser, value);
    }

    callParamCallbacks();

    if (status) {
        asynPrint(pasynUser, ASYN_TRACE_ERROR,
                  "%s: error, status=%d function=%d, value=%f\n",
                  functionName, status, function, value);
    } else {
        asynPrint(pasynUser, ASYN_TRACEIO_DRIVER,
                  "%s: function=%d, value=%f\n",
                  functionName, function, value);
    }
    return status;
}

/**
 * Read enum strings for mbbo/mbbi records
 */
asynStatus Kreios::readEnum(asynUser *pasynUser, char *strings[], int values[],
                            int severities[], size_t nElements, size_t *nIn)
{
    int function = pasynUser->reason;
    size_t i;

    if (function == KREIOSLensMode_) {
        for (i = 0; ((i < lensModes_.size()) && (i < nElements)); i++) {
            if (strings[i]) free(strings[i]);
            strings[i] = epicsStrDup(lensModes_[i].c_str());
            values[i] = (int)i;
            severities[i] = 0;
        }
    } else if (function == KREIOSScanRange_) {
        for (i = 0; ((i < scanRanges_.size()) && (i < nElements)); i++) {
            if (strings[i]) free(strings[i]);
            strings[i] = epicsStrDup(scanRanges_[i].c_str());
            values[i] = (int)i;
            severities[i] = 0;
        }
    } else if (function == KREIOSRunMode_) {
        for (i = 0; ((i < runModes_.size()) && (i < nElements)); i++) {
            if (strings[i]) free(strings[i]);
            strings[i] = epicsStrDup(runModes_[i].c_str());
            values[i] = (int)i;
            severities[i] = 0;
        }
    } else if (function == KREIOSOperatingMode_) {
        for (i = 0; ((i < operatingModes_.size()) && (i < nElements)); i++) {
            if (strings[i]) free(strings[i]);
            strings[i] = epicsStrDup(operatingModes_[i].c_str());
            values[i] = (int)i;
            severities[i] = 0;
        }
    } else {
        *nIn = 0;
        return asynError;
    }
    *nIn = i;
    return asynSuccess;
}

// ============================================================================
// Spectrum Definition Methods
// ============================================================================

asynStatus Kreios::defineSpectrumFAT()
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    double startEnergy, endEnergy, stepWidth, passEnergy, dwellTime;
    int lensMode, scanRange;
    const char *functionName = "Kreios::defineSpectrumFAT";

    getDoubleParam(KREIOSStartEnergy_, &startEnergy);
    getDoubleParam(KREIOSEndEnergy_, &endEnergy);
    getDoubleParam(KREIOSStepWidth_, &stepWidth);
    getDoubleParam(KREIOSPassEnergy_, &passEnergy);
    getDoubleParam(ADAcquireTime, &dwellTime);
    getIntegerParam(KREIOSLensMode_, &lensMode);
    getIntegerParam(KREIOSScanRange_, &scanRange);

    cmd << KREIOS_CMD_DEFINE_FAT;
    cmd << ":StartEnergy=" << startEnergy;
    cmd << ":EndEnergy=" << endEnergy;
    cmd << ":StepWidth=" << stepWidth;
    cmd << ":PassEnergy=" << passEnergy;
    cmd << ":DwellTime=" << dwellTime;

    if (lensMode < (int)lensModes_.size()) {
        cmd << ":LensMode=" << lensModes_[lensMode];
    }
    if (scanRange < (int)scanRanges_.size()) {
        cmd << ":ScanRange=" << scanRanges_[scanRange];
    }

    debug(functionName, "Command", cmd.str());
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::defineSpectrumSFAT()
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    double startEnergy, endEnergy, stepWidth, passEnergy, dwellTime;
    int lensMode, scanRange;
    const char *functionName = "Kreios::defineSpectrumSFAT";

    getDoubleParam(KREIOSStartEnergy_, &startEnergy);
    getDoubleParam(KREIOSEndEnergy_, &endEnergy);
    getDoubleParam(KREIOSStepWidth_, &stepWidth);
    getDoubleParam(KREIOSPassEnergy_, &passEnergy);
    getDoubleParam(ADAcquireTime, &dwellTime);
    getIntegerParam(KREIOSLensMode_, &lensMode);
    getIntegerParam(KREIOSScanRange_, &scanRange);

    cmd << KREIOS_CMD_DEFINE_SFAT;
    cmd << ":StartEnergy=" << startEnergy;
    cmd << ":EndEnergy=" << endEnergy;
    cmd << ":StepWidth=" << stepWidth;
    cmd << ":PassEnergy=" << passEnergy;
    cmd << ":DwellTime=" << dwellTime;

    if (lensMode < (int)lensModes_.size()) {
        cmd << ":LensMode=" << lensModes_[lensMode];
    }
    if (scanRange < (int)scanRanges_.size()) {
        cmd << ":ScanRange=" << scanRanges_[scanRange];
    }

    debug(functionName, "Command", cmd.str());
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::defineSpectrumFRR()
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    double startEnergy, endEnergy, stepWidth, retardRatio, dwellTime;
    int lensMode, scanRange;
    const char *functionName = "Kreios::defineSpectrumFRR";

    getDoubleParam(KREIOSStartEnergy_, &startEnergy);
    getDoubleParam(KREIOSEndEnergy_, &endEnergy);
    getDoubleParam(KREIOSStepWidth_, &stepWidth);
    getDoubleParam(KREIOSRetardingRatio_, &retardRatio);
    getDoubleParam(ADAcquireTime, &dwellTime);
    getIntegerParam(KREIOSLensMode_, &lensMode);
    getIntegerParam(KREIOSScanRange_, &scanRange);

    cmd << KREIOS_CMD_DEFINE_FRR;
    cmd << ":StartEnergy=" << startEnergy;
    cmd << ":EndEnergy=" << endEnergy;
    cmd << ":StepWidth=" << stepWidth;
    cmd << ":RetardingRatio=" << retardRatio;
    cmd << ":DwellTime=" << dwellTime;

    if (lensMode < (int)lensModes_.size()) {
        cmd << ":LensMode=" << lensModes_[lensMode];
    }
    if (scanRange < (int)scanRanges_.size()) {
        cmd << ":ScanRange=" << scanRanges_[scanRange];
    }

    debug(functionName, "Command", cmd.str());
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::defineSpectrumFE()
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    double kineticEnergy, passEnergy, dwellTime;
    int lensMode, scanRange, samples;
    const char *functionName = "Kreios::defineSpectrumFE";

    getDoubleParam(KREIOSKineticEnergy_, &kineticEnergy);
    getDoubleParam(KREIOSPassEnergy_, &passEnergy);
    getDoubleParam(ADAcquireTime, &dwellTime);
    getIntegerParam(KREIOSLensMode_, &lensMode);
    getIntegerParam(KREIOSScanRange_, &scanRange);
    getIntegerParam(KREIOSSamples_, &samples);

    cmd << KREIOS_CMD_DEFINE_FE;
    cmd << ":KineticEnergy=" << kineticEnergy;
    cmd << ":PassEnergy=" << passEnergy;
    cmd << ":DwellTime=" << dwellTime;
    cmd << ":Samples=" << samples;

    if (lensMode < (int)lensModes_.size()) {
        cmd << ":LensMode=" << lensModes_[lensMode];
    }
    if (scanRange < (int)scanRanges_.size()) {
        cmd << ":ScanRange=" << scanRanges_[scanRange];
    }

    debug(functionName, "Command", cmd.str());
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::defineSpectrumLVS()
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    double dwellTime;
    int lensMode, scanRange;
    const char *functionName = "Kreios::defineSpectrumLVS";

    getDoubleParam(ADAcquireTime, &dwellTime);
    getIntegerParam(KREIOSLensMode_, &lensMode);
    getIntegerParam(KREIOSScanRange_, &scanRange);

    cmd << KREIOS_CMD_DEFINE_LVS;
    cmd << ":DwellTime=" << dwellTime;

    if (lensMode < (int)lensModes_.size()) {
        cmd << ":LensMode=" << lensModes_[lensMode];
    }
    if (scanRange < (int)scanRanges_.size()) {
        cmd << ":ScanRange=" << scanRanges_[scanRange];
    }

    debug(functionName, "Command", cmd.str());
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::validateSpectrum()
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    const char *functionName = "Kreios::validateSpectrum";

    debug(functionName, "Validating spectrum");
    status = commandResponse(KREIOS_CMD_VALIDATE, response, data);

    if (status == asynSuccess) {
        int samples = 0;
        readIntegerData(data, "Samples", samples);
        setIntegerParam(KREIOSSamplesIteration_, samples);

        // Read ValuesPerSample for 2D/3D determination
        int valuesPerSample = 1;
        readIntegerData(data, "ValuesPerSample", valuesPerSample);
        setIntegerParam(KREIOSValuesPerSample_, valuesPerSample);

        // Read NumberOfSlices for 3D
        int numSlices = 1;
        readIntegerData(data, "NumberOfSlices", numSlices);
        setIntegerParam(KREIOSNumSlices_, numSlices);

        setIntegerParam(KREIOSValidate_, 1);
        callParamCallbacks();
        debug(functionName, "Validation complete, samples=", samples);
    } else {
        setIntegerParam(KREIOSValidate_, 0);
        debug(functionName, "Validation failed");
    }

    return status;
}

// ============================================================================
// Data Acquisition Methods
// ============================================================================

asynStatus Kreios::readAcquisitionData(int startIndex, int endIndex, std::vector<double> &values)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    const char *functionName = "Kreios::readAcquisitionData";

    cmd << KREIOS_CMD_GET_DATA;
    cmd << ":FromIndex=" << startIndex;
    cmd << ":ToIndex=" << endIndex;

    debug(functionName, "Reading data", cmd.str());
    status = commandResponse(cmd.str(), response, data);

    if (status == asynSuccess) {
        // Parse the data values from the response
        // Data format: "Data:value1,value2,value3,..."
        if (data.count("Data") > 0) {
            std::string dataStr = data["Data"];
            std::stringstream ss(dataStr);
            std::string token;
            values.clear();
            while (std::getline(ss, token, ',')) {
                try {
                    double val = std::stod(token);
                    values.push_back(val);
                } catch (...) {
                    // Skip invalid values
                }
            }
        }
    }

    return status;
}

asynStatus Kreios::sendStartCommand(bool safeAfter)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    const char *functionName = "Kreios::sendStartCommand";

    cmd << KREIOS_CMD_START;
    if (!safeAfter) {
        cmd << ":SafeAfter=false";
    }

    debug(functionName, "Starting acquisition", cmd.str());
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::sendSimpleCommand(const std::string &command,
                                      std::map<std::string, std::string> *data)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> localData;
    const char *functionName = "Kreios::sendSimpleCommand";

    debug(functionName, "Command", command);

    if (data == NULL) {
        status = commandResponse(command, response, localData);
    } else {
        status = commandResponse(command, response, *data);
    }

    return status;
}

// ============================================================================
// Device Parameter Methods
// ============================================================================

asynStatus Kreios::readDeviceVisibleName()
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    const char *functionName = "Kreios::readDeviceVisibleName";

    status = commandResponse(KREIOS_CMD_GET_VISNAME, response, data);

    if (status == asynSuccess) {
        if (data.count("VisibleName") > 0) {
            setStringParam(ADModel, data["VisibleName"].c_str());
            debug(functionName, "Device name", data["VisibleName"]);
        }
    }

    return status;
}

asynStatus Kreios::setupEPICSParameters()
{
    asynStatus status = asynSuccess;
    const char *functionName = "Kreios::setupEPICSParameters";

    debug(functionName, "Setting up EPICS parameters");

    // This would read available parameters from the device
    // and create corresponding EPICS PVs dynamically
    // For now, the main parameters are already defined in the constructor

    return status;
}

asynStatus Kreios::getAnalyserParameterType(const std::string &name, KREIOSValueType_t &value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_GET_INFO << ":Name=" << name;
    status = commandResponse(cmd.str(), response, data);

    if (status == asynSuccess) {
        if (data.count("Type") > 0) {
            std::string type = data["Type"];
            if (type == KREIOS_TYPE_DOUBLE) {
                value = KREIOSTypeDouble;
            } else if (type == KREIOS_TYPE_INTEGER) {
                value = KREIOSTypeInteger;
            } else if (type == KREIOS_TYPE_STRING) {
                value = KREIOSTypeString;
            } else if (type == KREIOS_TYPE_BOOL) {
                value = KREIOSTypeBool;
            }
        }
    }

    return status;
}

asynStatus Kreios::getAnalyserParameter(const std::string &name, int &value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_GET_VALUE << ":Name=" << name;
    status = commandResponse(cmd.str(), response, data);

    if (status == asynSuccess) {
        if (data.count("Value") > 0) {
            try {
                value = std::stoi(data["Value"]);
            } catch (...) {
                status = asynError;
            }
        }
    }

    return status;
}

asynStatus Kreios::getAnalyserParameter(const std::string &name, double &value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_GET_VALUE << ":Name=" << name;
    status = commandResponse(cmd.str(), response, data);

    if (status == asynSuccess) {
        if (data.count("Value") > 0) {
            try {
                value = std::stod(data["Value"]);
            } catch (...) {
                status = asynError;
            }
        }
    }

    return status;
}

asynStatus Kreios::getAnalyserParameter(const std::string &name, std::string &value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_GET_VALUE << ":Name=" << name;
    status = commandResponse(cmd.str(), response, data);

    if (status == asynSuccess) {
        if (data.count("Value") > 0) {
            value = data["Value"];
        }
    }

    return status;
}

asynStatus Kreios::getAnalyserParameter(const std::string &name, bool &value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_GET_VALUE << ":Name=" << name;
    status = commandResponse(cmd.str(), response, data);

    if (status == asynSuccess) {
        if (data.count("Value") > 0) {
            std::string val = data["Value"];
            std::transform(val.begin(), val.end(), val.begin(), ::tolower);
            value = (val == "true" || val == "1");
        }
    }

    return status;
}

asynStatus Kreios::setAnalyserParameter(const std::string &name, int value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_SET_VALUE << ":Name=" << name << ":Value=" << value;
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::setAnalyserParameter(const std::string &name, double value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_SET_VALUE << ":Name=" << name << ":Value=" << value;
    status = commandResponse(cmd.str(), response, data);

    return status;
}

asynStatus Kreios::setAnalyserParameter(const std::string &name, std::string value)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;

    cmd << KREIOS_CMD_SET_VALUE << ":Name=" << name << ":Value=" << value;
    status = commandResponse(cmd.str(), response, data);

    return status;
}

// ============================================================================
// Data Parsing Methods
// ============================================================================

asynStatus Kreios::readIntegerData(std::map<std::string, std::string> data,
                                    const std::string &name, int &value)
{
    asynStatus status = asynSuccess;

    if (data.count(name) > 0) {
        try {
            value = std::stoi(data[name]);
        } catch (...) {
            status = asynError;
        }
    } else {
        status = asynError;
    }

    return status;
}

asynStatus Kreios::readDoubleData(std::map<std::string, std::string> data,
                                   const std::string &name, double &value)
{
    asynStatus status = asynSuccess;

    if (data.count(name) > 0) {
        try {
            value = std::stod(data[name]);
        } catch (...) {
            status = asynError;
        }
    } else {
        status = asynError;
    }

    return status;
}

asynStatus Kreios::readSpectrumParameter(int param)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    std::stringstream cmd;
    const char *functionName = "Kreios::readSpectrumParameter";

    if (param == KREIOSLensMode_) {
        cmd << KREIOS_CMD_GET_SPECTRUM << ":Name=LensMode";
        status = commandResponse(cmd.str(), response, data);
        if (status == asynSuccess && data.count("Values") > 0) {
            lensModes_.clear();
            std::stringstream ss(data["Values"]);
            std::string token;
            while (std::getline(ss, token, ',')) {
                cleanString(token);
                if (!token.empty()) {
                    lensModes_.push_back(token);
                }
            }
            debug(functionName, "Lens modes loaded", (int)lensModes_.size());
        }
    } else if (param == KREIOSScanRange_) {
        cmd << KREIOS_CMD_GET_SPECTRUM << ":Name=ScanRange";
        status = commandResponse(cmd.str(), response, data);
        if (status == asynSuccess && data.count("Values") > 0) {
            scanRanges_.clear();
            std::stringstream ss(data["Values"]);
            std::string token;
            while (std::getline(ss, token, ',')) {
                cleanString(token);
                if (!token.empty()) {
                    scanRanges_.push_back(token);
                }
            }
            debug(functionName, "Scan ranges loaded", (int)scanRanges_.size());
        }
    }

    return status;
}

asynStatus Kreios::readRunModes()
{
    // Run modes are predefined, already set in constructor
    return asynSuccess;
}

asynStatus Kreios::readOperatingModes()
{
    // Operating modes are predefined, already set in constructor
    return asynSuccess;
}

asynStatus Kreios::readSpectrumDataInfo(KREIOSDataInfoParam_t param)
{
    asynStatus status = asynSuccess;
    std::string response;
    std::map<std::string, std::string> data;
    const char *functionName = "Kreios::readSpectrumDataInfo";

    if (param == KREIOSOrdinateRange) {
        status = commandResponse(KREIOS_CMD_GET_DATA_INFO ":Name=OrdinateRange", response, data);
        if (status == asynSuccess) {
            double min = 0.0, max = 0.0;
            std::string units;
            readDoubleData(data, "Min", min);
            readDoubleData(data, "Max", max);
            if (data.count("Units") > 0) {
                units = data["Units"];
            }
            setDoubleParam(KREIOSNonEnergyMin_, min);
            setDoubleParam(KREIOSNonEnergyMax_, max);
            setStringParam(KREIOSNonEnergyUnits_, units.c_str());
            debug(functionName, "Ordinate range: min", min);
            debug(functionName, "Ordinate range: max", max);
        }
    }

    return status;
}

// ============================================================================
// Communication Methods
// ============================================================================

asynStatus Kreios::asynPortConnect(const char *port, int addr, asynUser **ppasynUser,
                                    const char *inputEos, const char *outputEos)
{
    asynStatus status = asynSuccess;
    const char *functionName = "Kreios::asynPortConnect";

    status = pasynOctetSyncIO->connect(port, addr, ppasynUser, NULL);
    if (status != asynSuccess) {
        debug(functionName, "Failed to connect", port);
        return status;
    }

    status = pasynOctetSyncIO->setInputEos(*ppasynUser, inputEos, strlen(inputEos));
    if (status != asynSuccess) {
        debug(functionName, "Failed to set input EOS");
        return status;
    }

    status = pasynOctetSyncIO->setOutputEos(*ppasynUser, outputEos, strlen(outputEos));
    if (status != asynSuccess) {
        debug(functionName, "Failed to set output EOS");
        return status;
    }

    return status;
}

asynStatus Kreios::asynPortDisconnect(asynUser *pasynUser)
{
    asynStatus status = asynSuccess;

    status = pasynOctetSyncIO->disconnect(pasynUser);

    return status;
}

asynStatus Kreios::commandResponse(const std::string &command, std::string &response,
                                    std::map<std::string, std::string> &data)
{
    asynStatus status = asynSuccess;
    char responseBuffer[KREIOS_MAX_STRING];
    const char *functionName = "Kreios::commandResponse";

    // Increment message counter
    int msgCounter;
    getIntegerParam(KREIOSMsgCounter_, &msgCounter);
    setIntegerParam(KREIOSMsgCounter_, ++msgCounter);

    status = asynWriteRead(command.c_str(), responseBuffer);

    if (status == asynSuccess) {
        response = responseBuffer;

        // Parse response into key-value pairs
        // Format: "OK:Key1=Value1:Key2=Value2" or "ERROR:Code=X:Message=Y"
        data.clear();
        std::stringstream ss(response);
        std::string token;

        while (std::getline(ss, token, ':')) {
            size_t pos = token.find('=');
            if (pos != std::string::npos) {
                std::string key = token.substr(0, pos);
                std::string value = token.substr(pos + 1);
                cleanString(key);
                cleanString(value);
                data[key] = value;
            } else {
                // First token might be OK or ERROR
                cleanString(token);
                if (token == KREIOS_ERROR_STRING) {
                    status = asynError;
                }
            }
        }
    }

    debug(functionName, "Response", response);

    return status;
}

asynStatus Kreios::asynWriteRead(const char *command, char *response)
{
    asynStatus status = asynSuccess;
    size_t nwrite, nread;
    int eomReason;
    const char *functionName = "Kreios::asynWriteRead";

    debug(functionName, "Command", command);

    status = pasynOctetSyncIO->writeRead(portUser_,
                                          command, strlen(command),
                                          response, KREIOS_MAX_STRING,
                                          KREIOS_TIMEOUT,
                                          &nwrite, &nread, &eomReason);

    if (status != asynSuccess) {
        debug(functionName, "Write/read failed");
    }

    return status;
}

// ============================================================================
// Utility Methods
// ============================================================================

asynStatus Kreios::cleanString(std::string &str, const std::string &search, int where)
{
    // Remove leading/trailing whitespace and specified characters
    size_t start = str.find_first_not_of(search);
    if (start == std::string::npos) {
        str = "";
        return asynSuccess;
    }
    size_t end = str.find_last_not_of(search);
    str = str.substr(start, end - start + 1);

    return asynSuccess;
}

// ============================================================================
// Debug Methods
// ============================================================================

asynStatus Kreios::initDebugger(int initDebug)
{
    // Initialize debug map with default values
    return asynSuccess;
}

asynStatus Kreios::debugLevel(const std::string &method, int onOff)
{
    debugMap_[method] = onOff;
    return asynSuccess;
}

asynStatus Kreios::debug(const std::string &method, const std::string &msg)
{
    if (debugMap_.count(method) == 0 || debugMap_[method] == 1) {
        printf("%s: %s\n", method.c_str(), msg.c_str());
    }
    return asynSuccess;
}

asynStatus Kreios::debug(const std::string &method, const std::string &msg, int value)
{
    if (debugMap_.count(method) == 0 || debugMap_[method] == 1) {
        printf("%s: %s %d\n", method.c_str(), msg.c_str(), value);
    }
    return asynSuccess;
}

asynStatus Kreios::debug(const std::string &method, const std::string &msg, double value)
{
    if (debugMap_.count(method) == 0 || debugMap_[method] == 1) {
        printf("%s: %s %f\n", method.c_str(), msg.c_str(), value);
    }
    return asynSuccess;
}

asynStatus Kreios::debug(const std::string &method, const std::string &msg, const std::string &value)
{
    if (debugMap_.count(method) == 0 || debugMap_[method] == 1) {
        printf("%s: %s %s\n", method.c_str(), msg.c_str(), value.c_str());
    }
    return asynSuccess;
}

asynStatus Kreios::debug(const std::string &method, const std::string &msg,
                          std::map<std::string, std::string> value)
{
    if (debugMap_.count(method) == 0 || debugMap_[method] == 1) {
        printf("%s: %s { ", method.c_str(), msg.c_str());
        for (auto it = value.begin(); it != value.end(); ++it) {
            printf("%s=%s ", it->first.c_str(), it->second.c_str());
        }
        printf("}\n");
    }
    return asynSuccess;
}

asynStatus Kreios::debug(const std::string &method, const std::string &msg,
                          std::map<int, std::string> value)
{
    if (debugMap_.count(method) == 0 || debugMap_[method] == 1) {
        printf("%s: %s { ", method.c_str(), msg.c_str());
        for (auto it = value.begin(); it != value.end(); ++it) {
            printf("%d=%s ", it->first, it->second.c_str());
        }
        printf("}\n");
    }
    return asynSuccess;
}

// ============================================================================
// IOC Shell Registration
// ============================================================================

static const iocshArg kreiosConfigArg0 = {"Port name", iocshArgString};
static const iocshArg kreiosConfigArg1 = {"Driver port", iocshArgString};
static const iocshArg kreiosConfigArg2 = {"Max buffers", iocshArgInt};
static const iocshArg kreiosConfigArg3 = {"Max memory", iocshArgInt};
static const iocshArg kreiosConfigArg4 = {"Priority", iocshArgInt};
static const iocshArg kreiosConfigArg5 = {"Stack size", iocshArgInt};
static const iocshArg *const kreiosConfigArgs[] = {&kreiosConfigArg0,
                                                    &kreiosConfigArg1,
                                                    &kreiosConfigArg2,
                                                    &kreiosConfigArg3,
                                                    &kreiosConfigArg4,
                                                    &kreiosConfigArg5};
static const iocshFuncDef configKreios = {"kreiosConfig", 6, kreiosConfigArgs};

static void configKreiosCallFunc(const iocshArgBuf *args)
{
    kreiosConfig(args[0].sval, args[1].sval, args[2].ival,
                 args[3].ival, args[4].ival, args[5].ival);
}

static const iocshArg kreiosDebugArg0 = {"Driver", iocshArgString};
static const iocshArg kreiosDebugArg1 = {"Method", iocshArgString};
static const iocshArg kreiosDebugArg2 = {"Debug level", iocshArgInt};
static const iocshArg *const kreiosDebugArgs[] = {&kreiosDebugArg0,
                                                   &kreiosDebugArg1,
                                                   &kreiosDebugArg2};
static const iocshFuncDef debugKreios = {"kreiosSetDebugLevel", 3, kreiosDebugArgs};

static void debugKreiosCallFunc(const iocshArgBuf *args)
{
    kreiosSetDebugLevel(args[0].sval, args[1].sval, args[2].ival);
}

static void kreiosRegister(void)
{
    iocshRegister(&configKreios, configKreiosCallFunc);
    iocshRegister(&debugKreios, debugKreiosCallFunc);
}

extern "C" {
    epicsExportRegistrar(kreiosRegister);
}
