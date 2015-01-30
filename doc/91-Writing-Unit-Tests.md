# Writing Unit Tests
The MoMo build system supports unit testing of firmware code in order to ensure robust functionality.
There are two different systems in place for testing 8-bit and 16-bit code since the architectures are
very different.  The structure of the unit tests is the same but the available functionality is different
as will be discussed below.  8-bit unit tests are run on the [GNU PIC Simulator](http://gpsim.sourceforge.net).  16-bit
unit test are run on Microchip's free but proprietary simulator sim30.  We use a customized version of gpsim until 
upstream supports all of the features we need.  Read the Contributing section for instructions on how to install and
patch an appropriate version of gpsim.

## Unit Test Introduction
Unit tests should consist of a single file each (with possible support files that vary based on the unit test type)
and should be stored in the test subdirectory of the module to which they pertain.  In the examples in this document
we will consider the 8-bit module pic12_executive.  You can see the unit tests defined for this module:

```shell
$ cd momo_modules/pic12_executive
$ ls test   
support_bus_master.cmd          test_boot_address.as        test_find_handler.as
support_find_handler_mib.as     test_bus_checkparam.as      test_flash_write.as
support_i2c_slave_16lf1847.cmd  test_bus_master.as          test_i2c_slave.as
support_i2c_slave.cmd           test_bus_returnstatus.as    test_i2c_utils.as
support_i2c_slave_receive.cmd   test_bus_slave_16lf1847.as  test_no_appmodule.as
support_no_appmodule.as         test_bus_slave.as
test_basic.as                   test_call_handler.as
```

Each file with a name that begins with 'test_' defines a unit test and all other files are supporting files that
are included in their corresponding unit tests.

## Defining a Unit Test
All unit tests need to contain a header the describes the unit test.

```shell
$ head -n 4 test/test_call_handler.as
;Name: test_call_handler
;Targets: all
;Type: executive
;Description: Test to ensure that the find_handler function works 
```

The header must start with either a ';' for assembly test files on 8-bit processors or a '//' in C test files and it
must be at the top of the file.  Only whitespace is allowed before the header starts.  The header consists of a list
of Name: Value pairs, called test attributes, some of which are required and others are optional.

### Required Test Attributes
All tests must define the attributes Name, Targets, Type and Description as described below:

- *Name* The name of the test.  This must not contain any whitespace and should be unique among all of the tests for a given module

- *Targets* If this test should only be compiled for a subset of the target architectures that this module targets, you need to list that 
subset here as a comma separated list.  For example

- *Type* The type of unit test that this is.  There are various options that are valid only for 8-bit and others only for 16-bit.

```
Targets:16lf1823,16lf1847
```

This would only compile the test for the 16lf1823 and 16lf1847 targets of the module.  If a test should be compiled for each target, specify

```
Targets: all
``` 
- *Description* A description of what the test does.  Description is allowed to extend onto multiple lines if it is the last attribute defined
for the test.  It is recommended that Description be the last attribute in the attribute list.

### Optional Test Attributes (8-bit)
Some attributes are used to add additional functionality to tests.  The attributes supported on 8-bit unit tests are:

- *Additional* takes a comma separated list of additional filenames that are added to the test. Depending on the file extension the files are 
processed differently.  If a .as file is listed it is compiled along with the main test file and may contain additional code or anything else
that can be compiled in a .as file.  If a .cmd file is specified then it is used to create a custom command script to drive gpsim.  This lets
unit tests define stimuli for the test to respond to, for example.  See support_i2c_slave.cmd for an example.  Since the cmd file is appended to 
the normal (autogenerated) test script, it must end with the run command so that the test is actually executed.

- *Checkpoints* takes a comma separated list of tokens in the form symbol=value, where value is an 8-bit integer in decimal, hex or binary.  
Checkpoints define a sequence of actions that must complete in order for the test to be considered successful.  For an example see test_basic.as
in pic12_executive/test.  Checkpoints are discussed in more detail in the Using Checkpoints section.

- *Patch* takes a comma separated list of taken in the form old_symbol=new_symbol and patches the hex file under test so that the first 3 words of
the function specified by old_symbol are replaced with an unconditional goto to new_symbol, which is the replacement function.  This lets tests
hook other functions that they want to either mock or checkpoint.

### Optional Test Attributes (16-bit)
Fill this in as we write more 16-bit unit tests and build-out more features in the framework

## How 8-bit Unit Tests Work
All 8-bit modules are divided into two components: the executive and the application.  The executive takes the first ~1K of ROM of the processor
and the application takes the rest of the ROM.  Since these are small chips and the application code might be tightly coupled, it makes the most
sense to test it as a unit.  So, unit tests for applications work by replacing the executive portion of the firmware with the unit testing code
and keeping the entire application code as it would be in the real module.  Executive tests work in a similar way by replacing the application code
with the unit testing script.  This is done automatically by the build system.  

There are three types of 8-bit unit tests that must be specified in the Type attribute: executive, executive_integration and application.  Executive unit tests can only be 
defined for the pic12_executive.  All other application modules must define all of their tests as application tests.  By default, no module code is run before jumping directly to the unit test code except when executive_integration testing is specified.  ```executive_integration``` tests run through the complete executive startup code and run the unit test code as an application module.  This lets you test things that require a fully initialized mib12_executive.

### An Example Unit Test
FILL In this section

### Including Different Support Files on Each Architecture
Sometimes the same unit test code will run on multiple architectures, so you would like it to run on multiple architectures, but those architectures require different support files.  For example, if you want to test whether a certain pin triggers an interrupt, the test code is the same: did the interrupt get triggers, but what if the pin is in a different location on the different architectures.  The unit testing build code handles this in the following way.  When you specify an additional file like a .cmd file to pass commands to gpsim or a .as file to include in your unit test code, the build system internally looks for that file name appended with the architecture currently being targeted and if that file is found, will use it instead of a generic version.  

For example, say that you're targeting the architectures ```12lf1822/v1``` and ```12lf1822/v2```.  In your unit test you have an additional file include statement like the following. 

```
Additional: support_pinlocation.cmd
```

When building for the v2 architeccture, the build system parses your architecture string into a prefix list:

```
["12lf1822", "v2"]
["12lf1822"]
[""]
```

It then splits the support file prefix off and adds in the architecture prefixes, in order until it finds a file that exists.  So it looks for:

```
support_pinlocation_12lf1822_v2.cmd
support_pinlocation_12lf1822.cmd
support_pinlocation.cmd
```

Once it finds a match it stops.  If no match is found, it throws a BuildError.  On the v1 architecture, the build system looks for 
```support_pinlocation_12lf1822_v1.cmd``` first, so you can just specify two different support files and the build system will pull them in automatically for the right architecture without needing to create a separate unit test code file.

### Using Checkpoints Effectively
FILL In this section

## How 16-bit Unit Tests Work

## Miscellaneous Information

### How Unit Tests are Discovered by the Build System
Inside the SConstruct file that builds each module are commands to search for a test subdirectory and create unit tests from each file in that directory
whose name begins with test_.  Adding a unit test is as simple as defining a new test_*.{c,as} file in the test directory for the module you would like
to test.

## How To Run Unit Tests
Each module has a default target alias called test that builds all of the unit tests for that module

```shell
$ momo build test
```

## Seeing Unit Test Output
Unit tests are run on the simulator and produce a log of their activities.  This log is stored in build/test/output/logs for each module.  This log is
then parsed by the build system to determine if the test passed succesfully and the result is written to a '.status' file containing either the world
PASSED or FAILED.  Then the build system examines the status files for all of the tests for each target architecture and creates a summary file in
build/test/output called results.txt that summarizes the results.  For the pic12_executive module we have

```shell
$ cat build/test/output/results.txt
Test Summary

## Target 16lf1823_exec ##
9/9 tests passed (100% pass rate)

## Target 16lf1847_exec ##
10/10 tests passed (100% pass rate)

## Target 12lf1822_exec ##
12/12 tests passed (100% pass rate)
```

Test results are broken down per target and the logs for any tests that fail can be inspected in build/test/output/logs.  The status and log files are
named according to the test name and architecture: test_foobar@random_architecture.{log,status}.

The test results are also shown at the end of momo build test:

```shell
$ momo build test
<lots of text>
Test Summary

## Target 16lf1823_exec ##
9/9 tests passed (100% pass rate)

## Target 16lf1847_exec ##
10/10 tests passed (100% pass rate)

## Target 12lf1822_exec ##
12/12 tests passed (100% pass rate)
scons: done building targets.
```