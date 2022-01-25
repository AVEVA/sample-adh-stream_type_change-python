# AVEVA Data Hub Stream Type Change Python Sample

| :loudspeaker: **Notice**: Samples have been updated to reflect that they work on AVEVA Data Hub. The samples also work on OSIsoft Cloud Services unless otherwise noted. |
| -----------------------------------------------------------------------------------------------|  

**Version:** 1.1.0

[![Build Status](https://dev.azure.com/osieng/engineering/_apis/build/status/product-readiness/ADH/aveva.sample-adh-stream_type_change-python?branchName=main)](https://dev.azure.com/osieng/engineering/_build/latest?definitionId=4426&branchName=main)

Developed against Python 3.9.5.

## Requirements

- Python 3.7+
- Install required modules: `pip install -r requirements.txt`
- Register a [Client-Credentials Client](https://datahub.connect.aveva.com/clients) in your AVEVA Data Hub tenant and create a client secret to use in the configuration of this sample. ([Video Walkthrough](https://www.youtube.com/watch?v=JPWy0ZX9niU))
  - Note: the client must have a role with permissions to edit the specified streams and to create streamviews. 
  - If the client being used has the tenant admin role, we recommend creating a short lived secret to run this sample; if the secret were to be compromised, there would only be a short period of time for it to be useable. 

## About this sample

This sample uses the ADH sample python library, which makes REST API calls to ADH, to change the underlying SDS Types of Streams matching a search pattern. The main purpose of this sample is to demonstrate the steps necessary to change the underlying SDS Type of a Stream in ADH.

The processing steps of the sample are as follows:

1. The [appsettings.json](appsettings.placeholder.json) file is parsed into an appsettings object and an ADH client is created
1. A `type_to_stream_view_mappings` dictionary object is created to map an existing Type to a Stream View Id
    1. The Stream View will define how the existing Type's properties will map to the new Type's properties
    1. See the next two sections for more details on the creation of this dictionary
1. All Streams matching the `StreamSearchPattern` from [appsettings.json](appsettings.placeholder.json) are found from ADH
1. The user is prompted for confirmation to continue with processing since this is a change to the Streams
1. Each Stream's Type is changed from the existing Type to the new Type by calling the [Update Stream Type](https://docs.osisoft.com/bundle/ocs/page/api-reference/sequential-data-store/sds-streams.html#update-stream-type) action. 

## Using this sample when upgrading an adapter from version 1.1 to 1.2

The sample's specific logic as written will change the Types of PI Adapter streams from the 1.1 versioned Types of `TimeIndexed.<data_type>` (eg: `TimeIndexed.Double`) to the 1.2 versioned Types of `TimeIndexed.<data_type>.<adapter_type>Quality` (eg: `TimeIndexed.Double.OpcUaQuality`) to ingress the quality value where applicable. 

The steps to run this sample as an adapter stream type upgrade utility are as follows:

1. Upgrade the adapter instance from 1.1 to 1.2. New types will be created in the already configured ADH endpoint
1. Change this sample's [appsettings.json](appsettings.placeholder.json) settings to include:
    1. The adapter name (eg: `OpcUa`)
    1. The stream search pattern (eg: the `StreamIdPrefix` for this adapter instance's Data Source)
1. Run the sample
1. Observe the output and respond whether to continue with the stream view creations and type changes

### Enumeration Type Handling

[Enumeration data types](https://docs.osisoft.com/bundle/pi-adapter-opc-ua/page/overview/principles-of-operation.html#enumeration-types) have been introduced in the 1.2 version of some PI Adapters. For these enum streams, the Adapter will send create the enum type in the ADH Namespace, but **the script will not be able to migrate the stream to these types**. 
- The existing streams will currently be configured in ADH as an integer type, and it is not possible for the sample to detect whether these streams should migrate to the same integer type with the quality flag, or migrate to an enum type. 
- The script will therefore attempt to migrate them to the same integer type with the quality flag (which should immediately begin the data ingress of the quality data)
    - eg. `TimeIndexed.UInt32` -> `TimeIndexed.UInt32.OpcUaQuality`
- Since the sample will not create any new types, if the Adapter instance does not have any streams writing to the integer type with the quality flag, but they are all attempting to write to enum types, then this partial migration will not be possible. 

### Migrating Enum types manually

To migrate the enum type streams in ADH, follow the steps below for `Adapting this sample to other use cases.` While going through that section, use these steps for this specific use case
1. Manually create the stream view in the ADH portal for the existing integer Type to a specific enum Type.
1. Add an entry to the `type_to_stream_view_mappings` dictionary for the existing integer Type to the Stream View ID created in the previous step.
1. Set the `StreamSearchPattern` to match **only** these integer Typed Streams being matched to this Specific enum Type.
1. Run the sample to convert these streams
1. Repeat the previous steps with each of the enum Types necessary, repeatedly changing the `StreamSearchPattern` each time to match only the desired streams on each pass.

### Tested and Untested Adapter Types

This sample performs the specific action of migrating Streams from the version 1.1 PI Adapters to the version 1.2 PI Adapters. In each specific Adapter's case, there might be exceptions that do not work with this sample. Sometimes these can be worked around (eg: the enum types with the PI Adapter for OPC UA), and other times these exceptions are too impactful to use the sample at all. 

Within the `generate_adapter_upgrade_mappings` function, the specified `adapter_type` is checked against a list of tested and incompatible adapter types.
- If an incompatible adapter type is encountered, the sample will exit with an error message. 
- If the adapter type is neither tested nor known to be incompatible, a warning is logged and the script continues.
    - This is could a case where a new adapter type is being used, we welcome feedback to be sent to `samples@osisoft.com`
    - This also could be a case of the adapter type having a typo and not matching an actual adapter type (such as `OpcUa`, `DNP3`). In this case, nothing will migrate because no new version 1.2 Adapter SDS Types will be detected, and no action will be performed.

Over time, these sets will be expanded to reflect more adapter types. At the current moment, these are the known tests:
```python
tested_adapter_types = {'opcua'}
incompatible_adapter_types = {'dnp3'}
```

DNP3 is listed as incompatible because of the multiple different quality types that are possible. It is therefore not automatically detectable how to migrate any specific stream, but the above mentioned section on manual migration can be followed in this case as well.

## Adapting this sample to other use cases

Although this sample is built to be able to change SDS Types in a specific use case, it can be adapted to fit a more generic use case. The type conversion only require a dictionary mapping a Stream's existing Type to the ID of the Stream View that maps this Type to a new Type. 

This section of [program.py](program.py) covers the creation and/or definition of the necessary mapping table. Ultimately, the `type_to_stream_view_mappings` object needs to be set to a dictionary of `existing_type` to `stream_view_id` pairings for the sample to process later. 

```python
### Generic use case ###
""" type_to_stream_view_mappings = {
        'existing_type1': 'stream_view_id1',
        'existing_type2': 'stream_view_id2'
    } """
# Note: the stream views will need to be created first, whether programmatically or through the ADH portal

### Adapter 1.1 to 1.2 upgrade use case ###
type_to_stream_view_mappings = generate_adapter_upgrade_mappings(appsettings.get('AdapterType'), adh_client)
```

Alternatively, another function could be created to programmatically generate the necessary Stream Views, and then mappings table. For assistance with the programmatic creation of Stream Views and explicitly mapping properties from one Type to another Type, see the [ADH Waveform Python sample](https://github.com/osisoft/sample-ocs-waveform-python).

The steps to run this sample as an adapter stream type upgrade utility are as follows:

1. Create the new Types in ADH, either programmatically or in the [ADH Portal](datahub.connect.aveva.com)
1. Create the Stream View in ADH that maps the existing Type to the new Type.
    1. For assistance with this step, see how to [Get Started With Stream Views](https://docs.osisoft.com/bundle/ocs/page/overview/get-started/gs-stream-views.html)
1. Change this sample's [appsettings.json](appsettings.placeholder.json) settings to include the stream search pattern
1. Define `type_to_stream_view_mappings` to map the existing Types to the corresponding Stream View Id
    1. This could be done by manually defining the dictionary, defining it in a separate file and reading it in, or calling a generation function like the adapter use case
1. Run the sample
1. Observe the output and respond whether to continue with the stream view creations and type changes

## Configuring the sample

The sample is configured by modifying the file [appsettings.placeholder.json](appsettings.placeholder.json). Details on how to configure it can be found in the sections below. Before editing appsettings.placeholder.json, rename this file to `appsettings.json`. This repository's `.gitignore` rules should prevent the file from ever being checked in to any fork or branch, to ensure credentials are not compromised.

### Configuring appsettings.json

AVEVA Data Hub is secured by obtaining tokens from its identity endpoint. Client-credentials clients provide a client application identifier and an associated secret (or key) that are authenticated against the token endpoint. You must replace the placeholders in your `appsettings.json` file with the authentication-related values from your tenant and a client-credentials client created in your ADH tenant.

```json
{
  "Resource": "https://uswe.datahub.connect.aveva.com",                          # This is the base ADH URL being used
  "ApiVersion": "v1",                                               # The API version should most likely be kept at v1
  "TenantId": "REPLACE_WITH_TENANT_ID",                             # The Tenant that is being written to by the Adapter
  "NamespaceId": "REPLACE_WITH_NAMESPACE_ID",                       # The Namespace ID that is being written to by the Adapter
  "ClientId": "REPLACE_WITH_CLIENT_ID",                             # The ID of a client with the necessary permissions
  "ClientSecret": "REPLACE_WITH_CLIENT_SECRET",                     # The secret of this client
  "AdapterType": "REPLACE_WITH_ADAPTER_TYPE",                       # eg. OpcUa, DNP3. The SDS Types will contain this string
  "StreamSearchPattern": "REPLACE_WITH_STREAM_SEARCH_PATTERN"       # A search string to find only the streams to be migrated
}
```

## Logging

This sample uses the [Python logging](https://docs.python.org/3/library/logging.html) library to create a log file of `Debug`, `Info`, `Warning`, and `Error` messages. Since CRUD operations are being performed against ADH, it can be important to have a record of these oeprations. 

The default log file name is `logfile.txt` and the default log level is `INFO`. These are configurable at the bottom of [program.py](program.py) where the logging is setup
```python
level = logging.INFO     
log_file_name = 'logfile.txt'
```

Throughout the sample, each action taken or user notification is placed into one of the four severity buckets by calling the appropriate logging function([Debug](https://docs.python.org/3/library/logging.html#logging.Logger.debug), [Info](https://docs.python.org/3/library/logging.html#logging.Logger.info), [Warning](https://docs.python.org/3/library/logging.html#logging.Logger.warning), or [Error](https://docs.python.org/3/library/logging.html#logging.Logger.error)). To change the severity of a message, change the logging function for that message to the desired severity. The following are examples of each level used in the sample:
```python
logging.debug(f'Prompting user whether they would like to see the list of stream IDs.')
logging.info(f'Operation completed. Successfully converted {converted_streams} streams.')
logging.warning(f'Skipped {stream.Id} because it has a type of {stream.TypeId}, which is not in the mappings table.')
logging.error(f'Encountered error while converting stream: {error}')
```

## Running the sample

To run this example from the command line once the `appsettings.json` is configured, run

```shell
python program.py
```

## Testing the sample

The end to end test for this sample simulates an existing adapter being upgraded from 1.1 to 1.2, which is the most common expected use case of this sample. 

The testing procedure is as follows:

1. Find a list of existing Time.Indexed.[DataType] SDS Types
    - The test asserts that there are at least two in order to test the looping capabilities of the script
1. For each type, create two streams with a specific naming pattern that should be safe from unintentional collisions
    - The test first checks this assumption, and asserts that there are no existing streams matching the testing syntax
1. The old types and the stream names are recorded together in a dictionary for later look ups
1. Existing Stream Views that match the sample's Stream View Id syntax are searched for so that they are not deleted at the end of the test
    - Since the sample is creating the stream views, the test framework will be unaware of which ones were created by the sample. Recording them at this step is necessary to not over-delete.
1. To simulate the installation of a version 1.2 PI Adapter, the corresponding TimeIndexed.[DataType].[AdapterType]Quality SDS Types are created. 
    - The sample assumes these are already created, so the test must create them ahead of time.
    - The test keeps track of anything created as to not over-delete at the end
1. The sample is run, which changes the types of the streams that were previously created
1. Each stream is checked to ensure that its new type is its old type with `[AdapterType]Quality` appended to the end.
1. The created streams are deleted
1. The streams views created by the sample are deleted
1. The types created by the sample are deleted
1. Any exception encountered along the way will trigger a failed test

### Test Requirements

In order to execute the test against a particular ADH namespace, the following assertions must be true:
- The namespace already has two or more TimeIndexed.[DataType] SDS Types. 
- The namespace does not already have any streams that match the testing syntax of `e2etest_for_{sds_type}_{i}_conversion`
- The stream search pattern in appsettings matches the pattern for testing syntax. 
    - This is necessary as the sample will pull the search string from the `appsettings.json` file but the end to end test is creating strings with a hardcoded syntax. They must match before the test will execute

### Running the test

To run the end to end test from the command line once the `appsettings.json` is configured, run

```shell
python test.py
```

---

Tested against Python 3.9.1

For the main ADH samples page [ReadMe](https://github.com/osisoft/OSI-Samples-OCS)  
For the main AVEVA samples page [ReadMe](https://github.com/osisoft/OSI-Samples)