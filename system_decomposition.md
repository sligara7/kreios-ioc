Review /workspaces/ioc/ioc_deploy ansible role.  This is how we deploy Input Output Controllers (IOCs).  

We received a new detector (https://www.specs-group.com/specs/products/detail/kreios-150-mm/) that we'd like to control with an IOC.  The issue was that it was really designed to be used with a stand-alone Windows machine.  We'd like to take the Windows out of the equation and strictly use an IOC (a VM provisioned with RedHat Enterprise Linux) instead of the Windows machine.  However, there is some documentation for remote_in (/workspaces/ioc/Documentation/SpecsLabProdigy_RemoteIn.md) and to remote_out (/workspaces/ioc/Documentation/SpecsLabProdigy_RemoteOut.pdf) that may allow us to do this.

Please use the reflow process (it is usually designed to be used from its own github repo, but I've downloaded it into this repo).  The kickoff step can be found in: /workspaces/ioc/reflow2/workflows/00-setup.json.  

Please do some system decomposition of the documentation for the software to use the Kreios-150mm detector and determine if there is something we can do to control it via an IOC (first deploy the IOC using the /workspaces/ioc/ioc_deploy).

