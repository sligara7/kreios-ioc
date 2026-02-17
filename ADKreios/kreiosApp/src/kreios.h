/**
 * KREIOS-150 Momentum Microscope areaDetector Driver
 *
 * This driver interfaces with the SPECS KREIOS-150 momentum microscope
 * via the SpecsLab Prodigy Remote In protocol (v1.22).
 *
 * KREIOS-150 Specifications:
 * - 2D CMOS detector: 1285 x 730 channels (with binning)
 * - Kinetic energy range: 0-1500 eV
 * - Pass energies: 1-200 eV (continuously adjustable)
 * - Acceptance angle: +/-90 degrees full cone
 * - Energy resolution: <25 meV (momentum mode), <10 meV (spectroscopy)
 * - Angular resolution: <0.1 degrees
 * - Momentum resolution: 0.005-0.008 A^-1
 * - Lateral resolution: 35-50 nm
 * - Operating modes: PEEM, Momentum Microscopy, Spectroscopy
 *
 * Data dimensionality:
 * - 1D: Integrated spectrum (energy axis only)
 * - 2D: Image (energy x detector pixels / momentum)
 * - 3D: Volume (slices x energy x pixels / depth profiling)
 *
 * Author: NSLS-II / SPECS Integration
 * Date: January 2026
 */

#ifndef KREIOS_H
#define KREIOS_H

// Standard includes
#include <vector>
#include <sys/stat.h>
#include <iostream>
#include <sstream>
#include <string>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <errno.h>
#include <locale>
#include <map>
#include <algorithm>

// EPICS includes
#include <epicsThread.h>
#include <epicsEvent.h>
#include <epicsString.h>
#include <iocsh.h>
#include <drvSup.h>
#include <epicsExport.h>

// areaDetector includes
#include <ADDriver.h>

// Asyn driver includes
#include "asynOctetSyncIO.h"

// String length
#define KREIOS_MAX_STRING 4096
// Asyn timeout
#define KREIOS_TIMEOUT 10
// KREIOS Update rate (100ms polling)
#define KREIOS_UPDATE_RATE 0.1
// KREIOS Response strings
#define KREIOS_OK_STRING    "OK"
#define KREIOS_ERROR_STRING "ERROR"

// KREIOS Run Modes (spectrum acquisition types)
#define KREIOS_RUN_FAT   0   // Fixed Analyzer Transmission
#define KREIOS_RUN_SFAT  1   // Snapshot FAT
#define KREIOS_RUN_FRR   2   // Fixed Retard Ratio
#define KREIOS_RUN_FE    3   // Fixed Energies
#define KREIOS_RUN_LVS   4   // Logical Voltage Scan

// KREIOS Operating Modes
#define KREIOS_MODE_SPECTROSCOPY  0
#define KREIOS_MODE_MOMENTUM      1
#define KREIOS_MODE_PEEM          2

// KREIOS Parameter Types
#define KREIOS_TYPE_DOUBLE  "double"
#define KREIOS_TYPE_INTEGER "integer"
#define KREIOS_TYPE_STRING  "string"
#define KREIOS_TYPE_BOOL    "bool"

// KREIOS Detector dimensions
#define KREIOS_DETECTOR_SIZE_X  1285
#define KREIOS_DETECTOR_SIZE_Y  730
#define KREIOS_MAX_ENERGY_CHANNELS 100000
#define KREIOS_MAX_IMAGE_SIZE   2000000
#define KREIOS_MAX_VOLUME_SIZE  50000000

// KREIOS Command Strings (Prodigy Remote In protocol)
#define KREIOS_CMD_CONNECT      "Connect"
#define KREIOS_CMD_DISCONNECT   "Disconnect"
#define KREIOS_CMD_DEFINE_FAT   "DefineSpectrumFAT"
#define KREIOS_CMD_DEFINE_SFAT  "DefineSpectrumSFAT"
#define KREIOS_CMD_DEFINE_FRR   "DefineSpectrumFRR"
#define KREIOS_CMD_DEFINE_FE    "DefineSpectrumFE"
#define KREIOS_CMD_DEFINE_LVS   "DefineSpectrumLVS"
#define KREIOS_CMD_VALIDATE     "ValidateSpectrum"
#define KREIOS_CMD_START        "Start"
#define KREIOS_CMD_PAUSE        "Pause"
#define KREIOS_CMD_RESUME       "Resume"
#define KREIOS_CMD_ABORT        "Abort"
#define KREIOS_CMD_GET_STATUS   "GetAcquisitionStatus"
#define KREIOS_CMD_GET_DATA     "GetAcquisitionData"
#define KREIOS_CMD_CLEAR        "ClearSpectrum"
#define KREIOS_CMD_GET_NAMES    "GetAllAnalyzerParameterNames"
#define KREIOS_CMD_GET_INFO     "GetAnalyzerParameterInfo"
#define KREIOS_CMD_GET_VISNAME  "GetAnalyzerVisibleName"
#define KREIOS_CMD_GET_VALUE    "GetAnalyzerParameterValue"
#define KREIOS_CMD_SET_VALUE    "SetAnalyzerParameterValue"
#define KREIOS_CMD_GET_SPECTRUM "GetSpectrumParameterInfo"
#define KREIOS_CMD_GET_DATA_INFO "GetSpectrumDataInfo"
#define KREIOS_CMD_SET_SAFE_STATE "SetSafeState"
#define KREIOS_CMD_DISCONNECT_ANALYZER "DisconnectAnalyzer"

// CheckSpectrum variant commands
#define KREIOS_CMD_CHECK_FAT   "CheckSpectrumFAT"
#define KREIOS_CMD_CHECK_SFAT  "CheckSpectrumSFAT"
#define KREIOS_CMD_CHECK_FRR   "CheckSpectrumFRR"
#define KREIOS_CMD_CHECK_FE    "CheckSpectrumFE"
#define KREIOS_CMD_CHECK_LVS   "CheckSpectrumLVS"

// Analyzer direct voltage commands
#define KREIOS_CMD_SET_VALUE_DIRECTLY      "SetAnalyzerParameterValueDirectly"
#define KREIOS_CMD_VALIDATE_DIRECTLY       "ValidateAnalyzerParameterValueDirectly"

// Device command functions
#define KREIOS_CMD_GET_ALL_DEVICE_CMDS         "GetAllDeviceCommands"
#define KREIOS_CMD_GET_ALL_DEVICE_PARAM_NAMES  "GetAllDeviceParameterNames"
#define KREIOS_CMD_GET_DEVICE_PARAM_INFO       "GetDeviceParameterInfo"
#define KREIOS_CMD_GET_DEVICE_PARAM_VALUE      "GetDeviceParameterValue"
#define KREIOS_CMD_SET_DEVICE_PARAM_VALUE      "SetDeviceParameterValue"

// Direct device command functions
#define KREIOS_CMD_CREATE_DIRECT_DEVICE_CMD        "CreateDirectDeviceCommand"
#define KREIOS_CMD_GET_DIRECT_DEVICE_CMD_INFO      "GetDirectDeviceCommandInfo"
#define KREIOS_CMD_GET_DIRECT_DEVICE_PARAM_INFO    "GetDirectDeviceParameterInfo"
#define KREIOS_CMD_GET_DIRECT_DEVICE_PARAM_VALUE   "GetDirectDeviceParameterValue"
#define KREIOS_CMD_SET_DIRECT_DEVICE_PARAM_VALUE   "SetDirectDeviceParameterValue"
#define KREIOS_CMD_EXEC_DIRECT_DEVICE_CMD          "ExecuteDirectDeviceCommand"

// Device information commands (v1.22)
#define KREIOS_CMD_GET_ALL_DEVICES       "GetAllDevices"
#define KREIOS_CMD_GET_DEVICE_INFO       "GetDeviceInfo"
#define KREIOS_CMD_GET_LIVE_PARAM_INFO   "GetLiveParameterInfo"
#define KREIOS_CMD_GET_LIVE_PARAM_VALUE  "GetLiveParameterValue"

// Pre-defined EPICS Parameter Names
#define KREIOSConnectString                   "KREIOS_CONNECT"
#define KREIOSConnectedString                 "KREIOS_CONNECTED"
#define KREIOSPauseAcqString                  "KREIOS_PAUSE_ACQ"
#define KREIOSMsgCounterString                "KREIOS_MSG_COUNTER"
#define KREIOSServerNameString                "KREIOS_SERVER_NAME"
#define KREIOSProtocolVersionString           "KREIOS_PROTOCOL_VERSION"
#define KREIOSProtocolVersionMinorString      "KREIOS_PROTOCOL_VER_MINOR"
#define KREIOSProtocolVersionMajorString      "KREIOS_PROTOCOL_VER_MAJOR"

// Energy parameters
#define KREIOSStartEnergyString               "KREIOS_START_ENERGY"
#define KREIOSEndEnergyString                 "KREIOS_END_ENERGY"
#define KREIOSRetardingRatioString            "KREIOS_RETARDING_RATIO"
#define KREIOSKineticEnergyString             "KREIOS_KINETIC_ENERGY"
#define KREIOSStepWidthString                 "KREIOS_STEP_WIDTH"
#define KREIOSPassEnergyString                "KREIOS_PASS_ENERGY"

// Samples and iteration parameters
#define KREIOSSamplesString                   "KREIOS_SAMPLES"
#define KREIOSSamplesIterationString          "KREIOS_SAMPLES_ITERATION"
#define KREIOSSnapshotValuesString            "KREIOS_SNAPSHOT_VALUES"
#define KREIOSCurrentSampleString             "KREIOS_CURRENT_SAMPLE"
#define KREIOSPercentCompleteString           "KREIOS_PERCENT_COMPLETE"
#define KREIOSRemainingTimeString             "KREIOS_REMAINING_TIME"
#define KREIOSCurrentSampleIterationString    "KREIOS_CRT_SAMPLE_ITER"
#define KREIOSPercentCompleteIterationString  "KREIOS_PCT_COMPLETE_ITER"
#define KREIOSRemainingTimeIterationString    "KREIOS_RMG_TIME_ITER"

// Data arrays
#define KREIOSAcqSpectrumString               "KREIOS_ACQ_SPECTRUM"
#define KREIOSAcqImageString                  "KREIOS_ACQ_IMAGE"
#define KREIOSAcqVolumeString                 "KREIOS_ACQ_VOLUME"
#define KREIOSEnergyAxisString                "KREIOS_ENERGY_AXIS"

// Operating mode parameters
#define KREIOSRunModeString                   "KREIOS_RUN_MODE"
#define KREIOSOperatingModeString             "KREIOS_OPERATING_MODE"
#define KREIOSDefineString                    "KREIOS_DEFINE"
#define KREIOSValidateString                  "KREIOS_VALIDATE"
#define KREIOSLensModeString                  "KREIOS_LENS_MODE"
#define KREIOSScanRangeString                 "KREIOS_SCAN_RANGE"

// Detector dimension parameters
#define KREIOSValuesPerSampleString           "KREIOS_VALUES_PER_SAMPLE"
#define KREIOSNumSlicesString                 "KREIOS_NUM_SLICES"
#define KREIOSNonEnergyChannelsString         "KREIOS_NON_ENERGY_CHANNELS"
#define KREIOSNonEnergyUnitsString            "KREIOS_NON_ENERGY_UNITS"
#define KREIOSNonEnergyMinString              "KREIOS_NON_ENERGY_MIN"
#define KREIOSNonEnergyMaxString              "KREIOS_NON_ENERGY_MAX"

// KREIOS-150 specific parameters
#define KREIOSDetectorVoltageString           "KREIOS_DETECTOR_VOLTAGE"
#define KREIOSBiasVoltageString               "KREIOS_BIAS_VOLTAGE"
#define KREIOSCoilCurrentString               "KREIOS_COIL_CURRENT"
#define KREIOSFocusDisplacement1String        "KREIOS_FOCUS_DISP_1"
#define KREIOSFocusDisplacement2String        "KREIOS_FOCUS_DISP_2"
#define KREIOSAuxVoltageString                "KREIOS_AUX_VOLTAGE"
#define KREIOSDLDVoltageString                "KREIOS_DLD_VOLTAGE"

// Momentum microscopy specific parameters
#define KREIOSKxMinString                     "KREIOS_KX_MIN"
#define KREIOSKxMaxString                     "KREIOS_KX_MAX"
#define KREIOSKyMinString                     "KREIOS_KY_MIN"
#define KREIOSKyMaxString                     "KREIOS_KY_MAX"
#define KREIOSKxCenterString                  "KREIOS_KX_CENTER"
#define KREIOSKyCenterString                  "KREIOS_KY_CENTER"

// PEEM specific parameters
#define KREIOSFieldOfViewString               "KREIOS_FIELD_OF_VIEW"
#define KREIOSMagnificationString             "KREIOS_MAGNIFICATION"

// Safe state and data delay
#define KREIOSSafeStateString                 "KREIOS_SAFE_STATE"
#define KREIOSDataDelayMaxString              "KREIOS_DATA_DELAY_MAX"

// Group A: Simple trigger commands
#define KREIOSResumeString                    "KREIOS_RESUME"
#define KREIOSDisconnectAnalyzerString        "KREIOS_DISCONNECT_ANALYZER"
#define KREIOSSetSafeStateTriggerString       "KREIOS_SET_SAFE_STATE_TRIGGER"

// Group B: CheckSpectrum
#define KREIOSCheckSpectrumString             "KREIOS_CHECK_SPECTRUM"
#define KREIOSCheckStartEnergyString          "KREIOS_CHECK_START_ENERGY"
#define KREIOSCheckEndEnergyString            "KREIOS_CHECK_END_ENERGY"
#define KREIOSCheckStepWidthString            "KREIOS_CHECK_STEP_WIDTH"
#define KREIOSCheckSamplesString              "KREIOS_CHECK_SAMPLES"
#define KREIOSCheckDwellTimeString            "KREIOS_CHECK_DWELL_TIME"
#define KREIOSCheckPassEnergyString           "KREIOS_CHECK_PASS_ENERGY"

// Group C: GetAllAnalyzerParameterNames
#define KREIOSGetAllAnalyzerParamNamesString  "KREIOS_GET_ALL_ANALYZER_PARAMS"
#define KREIOSAnalyzerParamNamesString        "KREIOS_ANALYZER_PARAM_NAMES"

// Group D: Analyzer direct voltage
#define KREIOSSetAnalyzerDirectlyString       "KREIOS_SET_ANALYZER_DIRECTLY"
#define KREIOSValidateAnalyzerDirectlyString  "KREIOS_VALIDATE_ANALYZER_DIRECTLY"
#define KREIOSDirectPolarityString            "KREIOS_DIRECT_POLARITY"
#define KREIOSDirectParamNameString           "KREIOS_DIRECT_PARAM_NAME"
#define KREIOSDirectParamValueString          "KREIOS_DIRECT_PARAM_VALUE"

// Groups E/F/G: Shared query input PVs
#define KREIOSQueryDeviceString               "KREIOS_QUERY_DEVICE"
#define KREIOSQueryDeviceCmdString            "KREIOS_QUERY_DEVICE_CMD"
#define KREIOSQueryParamNameQString           "KREIOS_QUERY_PARAM_NAME"
#define KREIOSQueryValueString                "KREIOS_QUERY_VALUE"
#define KREIOSQueryTemplateString             "KREIOS_QUERY_TEMPLATE"

// Groups E/F/G: Trigger PVs (one per command)
#define KREIOSGetAllDeviceCmdsString          "KREIOS_GET_ALL_DEVICE_CMDS"
#define KREIOSGetAllDeviceParamNamesString    "KREIOS_GET_ALL_DEVICE_PARAM_NAMES"
#define KREIOSGetDeviceParamInfoString        "KREIOS_GET_DEVICE_PARAM_INFO"
#define KREIOSGetDeviceParamValueString       "KREIOS_GET_DEVICE_PARAM_VALUE"
#define KREIOSSetDeviceParamValueString       "KREIOS_SET_DEVICE_PARAM_VALUE"
#define KREIOSCreateDirectDeviceCmdString     "KREIOS_CREATE_DIRECT_DEVICE_CMD"
#define KREIOSGetDirectDeviceCmdInfoString    "KREIOS_GET_DIRECT_DEVICE_CMD_INFO"
#define KREIOSGetDirectDeviceParamInfoString  "KREIOS_GET_DIRECT_DEVICE_PARAM_INFO"
#define KREIOSGetDirectDeviceParamValString   "KREIOS_GET_DIRECT_DEVICE_PARAM_VAL"
#define KREIOSSetDirectDeviceParamValString   "KREIOS_SET_DIRECT_DEVICE_PARAM_VAL"
#define KREIOSExecDirectDeviceCmdString       "KREIOS_EXEC_DIRECT_DEVICE_CMD"
#define KREIOSGetAllDevicesString             "KREIOS_GET_ALL_DEVICES"
#define KREIOSGetDeviceInfoString             "KREIOS_GET_DEVICE_INFO"
#define KREIOSGetLiveParamInfoString          "KREIOS_GET_LIVE_PARAM_INFO"
#define KREIOSGetLiveParamValueString         "KREIOS_GET_LIVE_PARAM_VALUE"

// Groups E/F/G: Shared query output PVs
#define KREIOSQueryResponseString             "KREIOS_QUERY_RESPONSE"
#define KREIOSQueryParamNamesRBVString        "KREIOS_QUERY_PARAM_NAMES_RBV"
#define KREIOSQueryValueTypeString            "KREIOS_QUERY_VALUE_TYPE"
#define KREIOSQueryUnitString                 "KREIOS_QUERY_UNIT"
#define KREIOSQueryParamValueRBVString        "KREIOS_QUERY_PARAM_VALUE"
#define KREIOSQueryConnectivityString         "KREIOS_QUERY_CONNECTIVITY"
#define KREIOSQueryDeviceTypeString           "KREIOS_QUERY_DEVICE_TYPE"
#define KREIOSQueryVisibleNameRBVString       "KREIOS_QUERY_VISIBLE_NAME"
#define KREIOSQueryStatusString               "KREIOS_QUERY_STATUS"

// Parameter value types
typedef enum {
    KREIOSTypeDouble,
    KREIOSTypeInteger,
    KREIOSTypeString,
    KREIOSTypeBool
} KREIOSValueType_t;

// Data info parameter types
typedef enum {
    KREIOSOrdinateRange
} KREIOSDataInfoParam_t;


/**
 * KREIOS-150 areaDetector driver class
 *
 * Extends ADDriver to provide EPICS interface to KREIOS-150 momentum microscope.
 */
class Kreios : public ADDriver
{
public:
    Kreios(const char *portName, const char *driverPort, int maxBuffers,
           size_t maxMemory, int priority, int stackSize);
    virtual ~Kreios();

    // Main acquisition task
    void kreiosTask();

    // Connection management
    asynStatus makeConnection();
    asynStatus connect();
    asynStatus disconnect();

    // Asyn interface overrides
    asynStatus readEnum(asynUser *pasynUser, char *strings[], int values[],
                        int severities[], size_t nElements, size_t *nIn);
    asynStatus writeInt32(asynUser *pasynUser, epicsInt32 value);
    asynStatus writeFloat64(asynUser *pasynUser, epicsFloat64 value);

    // Spectrum definition and validation
    asynStatus validateSpectrum();
    asynStatus defineSpectrumFAT();
    asynStatus defineSpectrumSFAT();
    asynStatus defineSpectrumFRR();
    asynStatus defineSpectrumFE();
    asynStatus defineSpectrumLVS();

    // Data acquisition
    asynStatus readAcquisitionData(int startIndex, int endIndex, std::vector<double> &values);
    asynStatus sendStartCommand(bool safeAfter);
    asynStatus sendSimpleCommand(const std::string& command,
                                 std::map<std::string, std::string> *data = NULL);

    // CheckSpectrum variants
    asynStatus checkSpectrum();
    asynStatus checkSpectrumFAT();
    asynStatus checkSpectrumSFAT();
    asynStatus checkSpectrumFRR();
    asynStatus checkSpectrumFE();
    asynStatus checkSpectrumLVS();

    // GetAllAnalyzerParameterNames
    asynStatus getAllAnalyzerParameterNames();

    // Analyzer direct voltage
    asynStatus setAnalyzerParameterDirectly();
    asynStatus validateAnalyzerParameterDirectly();

    // Query interface helpers
    asynStatus readQueryInputs(std::string &device, std::string &deviceCmd,
                               std::string &paramName, std::string &value,
                               std::string &tmpl);
    asynStatus setQueryOutputs(const std::map<std::string, std::string> &data, bool ok);

    // Device command handlers (Group E)
    asynStatus queryGetAllDeviceCmds();
    asynStatus queryGetAllDeviceParamNames();
    asynStatus queryGetDeviceParamInfo();
    asynStatus queryGetDeviceParamValue();
    asynStatus querySetDeviceParamValue();

    // Direct device command handlers (Group F)
    asynStatus queryCreateDirectDeviceCmd();
    asynStatus queryGetDirectDeviceCmdInfo();
    asynStatus queryGetDirectDeviceParamInfo();
    asynStatus queryGetDirectDeviceParamVal();
    asynStatus querySetDirectDeviceParamVal();
    asynStatus queryExecDirectDeviceCmd();

    // Device information handlers (Group G)
    asynStatus queryGetAllDevices();
    asynStatus queryGetDeviceInfo();
    asynStatus queryGetLiveParamInfo();
    asynStatus queryGetLiveParamValue();

    // Device parameter management
    asynStatus readDeviceVisibleName();
    asynStatus setupEPICSParameters();
    asynStatus getAnalyserParameterType(const std::string& name, KREIOSValueType_t &value);
    asynStatus getAnalyserParameter(const std::string& name, int &value);
    asynStatus getAnalyserParameter(const std::string& name, double &value);
    asynStatus getAnalyserParameter(const std::string& name, std::string &value);
    asynStatus getAnalyserParameter(const std::string& name, bool &value);
    asynStatus setAnalyserParameter(const std::string& name, int value);
    asynStatus setAnalyserParameter(const std::string& name, double value);
    asynStatus setAnalyserParameter(const std::string& name, std::string value);

    // Data parsing helpers
    asynStatus readIntegerData(std::map<std::string, std::string> data,
                               const std::string& name, int &value);
    asynStatus readDoubleData(std::map<std::string, std::string> data,
                              const std::string& name, double &value);
    asynStatus readSpectrumParameter(int param);
    asynStatus readRunModes();
    asynStatus readOperatingModes();
    asynStatus readSpectrumDataInfo(KREIOSDataInfoParam_t param);

    // Communication
    asynStatus asynPortConnect(const char *port, int addr, asynUser **ppasynUser,
                               const char *inputEos, const char *outputEos);
    asynStatus asynPortDisconnect(asynUser *pasynUser);
    asynStatus commandResponse(const std::string &command, std::string &response,
                               std::map<std::string, std::string> &data);
    asynStatus asynWriteRead(const char *command, char *response);

    // String utilities
    asynStatus cleanString(std::string &str, const std::string &search = ": \n", int where = 0);

    // Debugging
    asynStatus initDebugger(int initDebug);
    asynStatus debugLevel(const std::string& method, int onOff);
    asynStatus debug(const std::string& method, const std::string& msg);
    asynStatus debug(const std::string& method, const std::string& msg, int value);
    asynStatus debug(const std::string& method, const std::string& msg, double value);
    asynStatus debug(const std::string& method, const std::string& msg, const std::string& value);
    asynStatus debug(const std::string& method, const std::string& msg,
                     std::map<std::string, std::string> value);
    asynStatus debug(const std::string& method, const std::string& msg,
                     std::map<int, std::string> value);

protected:
    // Connection parameters
    int KREIOSConnect_;
    #define FIRST_KREIOS_PARAM KREIOSConnect_
    int KREIOSConnected_;
    int KREIOSPauseAcq_;
    int KREIOSMsgCounter_;
    int KREIOSServerName_;
    int KREIOSProtocolVersion_;
    int KREIOSProtocolVersionMinor_;
    int KREIOSProtocolVersionMajor_;

    // Energy parameters
    int KREIOSStartEnergy_;
    int KREIOSEndEnergy_;
    int KREIOSRetardingRatio_;
    int KREIOSKineticEnergy_;
    int KREIOSStepWidth_;
    int KREIOSPassEnergy_;

    // Sample/iteration parameters
    int KREIOSSamples_;
    int KREIOSSamplesIteration_;
    int KREIOSSnapshotValues_;
    int KREIOSCurrentSample_;
    int KREIOSPercentComplete_;
    int KREIOSRemainingTime_;
    int KREIOSCurrentSampleIteration_;
    int KREIOSPercentCompleteIteration_;
    int KREIOSRemainingTimeIteration_;

    // Data arrays
    int KREIOSAcqSpectrum_;
    int KREIOSAcqImage_;
    int KREIOSAcqVolume_;
    int KREIOSEnergyAxis_;

    // Mode parameters
    int KREIOSRunMode_;
    int KREIOSOperatingMode_;
    int KREIOSDefine_;
    int KREIOSValidate_;
    int KREIOSLensMode_;
    int KREIOSScanRange_;

    // Dimension parameters
    int KREIOSValuesPerSample_;
    int KREIOSNumSlices_;
    int KREIOSNonEnergyChannels_;
    int KREIOSNonEnergyUnits_;
    int KREIOSNonEnergyMin_;
    int KREIOSNonEnergyMax_;

    // KREIOS-150 specific hardware parameters
    int KREIOSDetectorVoltage_;
    int KREIOSBiasVoltage_;
    int KREIOSCoilCurrent_;
    int KREIOSFocusDisplacement1_;
    int KREIOSFocusDisplacement2_;
    int KREIOSAuxVoltage_;
    int KREIOSDLDVoltage_;

    // Momentum microscopy parameters
    int KREIOSKxMin_;
    int KREIOSKxMax_;
    int KREIOSKyMin_;
    int KREIOSKyMax_;
    int KREIOSKxCenter_;
    int KREIOSKyCenter_;

    // PEEM parameters
    int KREIOSFieldOfView_;
    int KREIOSMagnification_;

    // Safe state and timing
    int KREIOSSafeState_;
    int KREIOSDataDelayMax_;

    // Group A: Simple trigger commands
    int KREIOSResume_;
    int KREIOSDisconnectAnalyzer_;
    int KREIOSSetSafeStateTrigger_;

    // Group B: CheckSpectrum
    int KREIOSCheckSpectrum_;
    int KREIOSCheckStartEnergy_;
    int KREIOSCheckEndEnergy_;
    int KREIOSCheckStepWidth_;
    int KREIOSCheckSamples_;
    int KREIOSCheckDwellTime_;
    int KREIOSCheckPassEnergy_;

    // Group C: GetAllAnalyzerParameterNames
    int KREIOSGetAllAnalyzerParamNames_;
    int KREIOSAnalyzerParamNames_;

    // Group D: Analyzer direct voltage
    int KREIOSSetAnalyzerDirectly_;
    int KREIOSValidateAnalyzerDirectly_;
    int KREIOSDirectPolarity_;
    int KREIOSDirectParamName_;
    int KREIOSDirectParamValue_;

    // Groups E/F/G: Shared query inputs
    int KREIOSQueryDevice_;
    int KREIOSQueryDeviceCmd_;
    int KREIOSQueryParamNameQ_;
    int KREIOSQueryValue_;
    int KREIOSQueryTemplate_;

    // Groups E/F/G: Trigger PVs
    int KREIOSGetAllDeviceCmds_;
    int KREIOSGetAllDeviceParamNames_;
    int KREIOSGetDeviceParamInfo_;
    int KREIOSGetDeviceParamValue_;
    int KREIOSSetDeviceParamValue_;
    int KREIOSCreateDirectDeviceCmd_;
    int KREIOSGetDirectDeviceCmdInfo_;
    int KREIOSGetDirectDeviceParamInfo_;
    int KREIOSGetDirectDeviceParamVal_;
    int KREIOSSetDirectDeviceParamVal_;
    int KREIOSExecDirectDeviceCmd_;
    int KREIOSGetAllDevices_;
    int KREIOSGetDeviceInfo_;
    int KREIOSGetLiveParamInfo_;
    int KREIOSGetLiveParamValue_;

    // Groups E/F/G: Shared query outputs
    int KREIOSQueryResponse_;
    int KREIOSQueryParamNamesRBV_;
    int KREIOSQueryValueType_;
    int KREIOSQueryUnit_;
    int KREIOSQueryParamValueRBV_;
    int KREIOSQueryConnectivity_;
    int KREIOSQueryDeviceType_;
    int KREIOSQueryVisibleNameRBV_;
    int KREIOSQueryStatus_;
    #define LAST_KREIOS_PARAM KREIOSQueryStatus_

private:
    asynUser                           *portUser_;
    char                               driverPort_[KREIOS_MAX_STRING];
    std::map<std::string, int>         debugMap_;
    epicsEventId                       startEventId_;
    epicsEventId                       stopEventId_;
    std::vector<std::string>           lensModes_;
    std::vector<std::string>           scanRanges_;
    std::vector<std::string>           runModes_;
    std::vector<std::string>           operatingModes_;
    std::map<std::string, std::string> paramMap_;
    std::map<int, std::string>         paramIndexes_;
    bool                               firstConnect_;
};

// Number of asyn parameters (asyn commands) this driver supports
// Includes base ADDriver params plus KREIOS-specific params plus dynamic device params
#define NUM_KREIOS_PARAMS ((int)(&LAST_KREIOS_PARAM - &FIRST_KREIOS_PARAM + 150))

#endif /* KREIOS_H */
