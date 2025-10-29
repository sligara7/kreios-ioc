# SpecsLab Prodigy Remote In

VERSION 1.22
SEPTEMBER 12, 2024


1 Introduction

1.1 SpecsLab Prodigy Behavior

In remote control mode:
• Prodigy shows that it is being remotely controlled.
• Prodigy shows the data as it is acquired.
• Experiment Editor and Remote Control cannot acquire data at the same time.
• A remote acquisition can be paused or aborted within the Remote Control plugin.
• Remote Control does not interfere with running local acquisitions.
• The spectrum is recorded with a one or two-dimensional detector and is written in an
    m×n-array.
• During data acquisition, only one scan will be recorded. Multiple scans are taken by
    repeating the acquisition. Data accumulation and / or averaging as well as storage is
    performed by the remote client.
• Local device parameters can only be set remotely for enabled device commands of the
    remote experiment.

1.2 General Protocol Description

• Communication is on a request / reply basis.
• In this context, SpecsLab Prodigy acts as the server.
• Requests are sent from the client application and are answered by SpecsLab Prodigy.
• SpecsLab Prodigy only accepts a single connection.
• The protocol format is plain ASCII text via TCP/IP.
• The TCP port of the remote control server is 7010.
• Each command is acknowledged by OK, OK: […] or Error: <code> “message”.
  An error condition is given by an error code and a textual description. Error codes are
  16-bit positive integer values. They are not unique but indicate an error “class”. Emphasis
  is put on the textual information.
• Each command and response are terminated by a newline character "\n".
• Token separation by <space> (ASCII 32dec).
• Message (character) strings are enclosed in double quotes: "<message>"; double quotes
  inside strings have to be escaped with a backslash ("\").
• Requests start with “?” followed by a request ID.
• Responses start with “!” followed by the corresponding request ID.
• Request IDs have a fixed length of 4 hexadecimal digits (e.g. 0001, AB03) where requests
  and responses have matching IDs.
• All command and parameter names are case sensitive.
• In the first version, no binary transfer is supported.

• Some commands which take a longer time to complete (for example, an acquisition) are
  performed asynchronously; a reply will be issued as a confirmation that the command
  will be / has been started and the actual state can be queried through other requests.
• Replies should normally be sent within one second; if a timeout occurs, the sender has
  to manage this depending on the command and state (resend, abort, …).
• When disconnecting voluntarily (or when the connection is lost) the devices used during
  remote control are set into their respective safe states.
• Aside from the point above, no automatic error mechanism is specified with this
  protocol.

1.3 Request Syntax

    ?<id> Command [InParams]

where:
   id                   Unique request identifier (hexadecimal value, always 4 digits)
   Command              Command name (character token, camel case, commands with spaces
                        must be enclosed in double quotes)
     InParams           Optional list of input parameters (“key:value”-list, space separated),
                        specific for each command; the order of parameters is arbitrary.

EXAMPLES:
?0107 Connect
?0231 GetAnalyzerParameterInfo ParameterName:”Detector Voltage”
?010B DefineSpectrum StartEnergy:1.0 EndEnergy:20.0 StepWidth:1.0
[...]
?010C Disconnect

1.4 Response Syntax

    !<id>              OK
or
    !<id>              OK: [OutParams]
or
    !<id>              Error: <Code> [Reason]

where:
   id                   Is the id of the corresponding request (4 digits, hexadecimal)
   OutParams                 List of output parameters (“key:value” list, space separated)
                        or error code and textual error message
     Code               Decimal representation of the error (see section 5).
     Reason                  Textual description of the error

EXAMPLES:
!0028 OK
!0028 OK: Detector Voltage:1950.0
!0198 Error: 201 Start energy should be above …
!0029 OK: ControllerStatus:running EnergyPosition:230.3

2 List of Commands (Requests from Client to SpecsLab Prodigy)

Every request can potentially be answered with an error reply.

2.1 Connect

Open connection to SpecsLab Prodigy.

Parameters:        (None)
Response:          OK: ServerName:<Text> ProtocolVersion:<Major.Minor>

Text               Arbitrary string reported from SpecsLab Prodigy
Major              Major number of the supported protocol version
Minor              Minor number of the supported protocol version

EXAMPLE:
?0100 Connect
!0100 OK: ServerName:“SpecsLab Prodigy 4.0” ProtocolVersion:1.2

2.2 Disconnect

Close connection to SpecsLab Prodigy.
When disconnecting voluntarily (or when the connection is lost) the devices used during
remote control are set into their respective safe states.

Parameters: (None)
Response: OK

EXAMPLE:
?00A0 Disconnect
!00A0 OK

[...truncated in markdown file for brevity...]

See the extracted text file for the full content.