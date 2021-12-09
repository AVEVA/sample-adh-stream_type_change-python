# OSIsoft Cloud Services Stream Type Change Python Sample

**Version:** 1.0.0

[![Build Status](https://dev.azure.com/osieng/engineering/_apis/build/status/product-readiness/OCS/osisoft.sample-ocs-security_management-python?repoName=osisoft%2Fsample-ocs-security_management-python&branchName=main)](https://dev.azure.com/osieng/engineering/_build/latest?definitionId=4027&repoName=osisoft%2Fsample-ocs-security_management-python&branchName=main)

Developed against Python 3.9.5.

## Requirements

- Python 3.9+
- Install required modules: `pip install -r requirements.txt`
- Register a [Client-Credentials Client](https://cloud.osisoft.com/clients) in your OSIsoft Cloud Services tenant and create a client secret to use in the configuration of this sample. ([Video Walkthrough](https://www.youtube.com/watch?v=JPWy0ZX9niU))
  - Note: the client must have a role with permissions to edit the specified streams and to create streamviews. 
  - If the client being used has the tenant admin role, we recommend creating a short lived secret to run this sample; if the secret were to be compromised, there would only be a short period of time for it to be useable. 

## About this sample

This sample uses the OCS sample python library, which makes REST API calls to OCS, to change the underlying SDS Types of Streams matching a search pattern. The main purpose of this sample is to demonstrate the steps necessary to change the underlying SDS Type of a Stream in OCS.

The processing steps of the sample are as follows:

1. The [appsettings.json](appsettings.placeholder.json) file is parsed into an appsettings object and an OCS client is created
1. A `type_to_stream_view_mappings` dictionary object is created to map an existing Type to a Stream View Id
    1. The Stream View will define how the existing Type's properties will map to the new Type's properties
    1. See the next two sections for more details on the creation of this dictionary
1. All Streams matching the `StreamSearchPattern` from [appsettings.json](appsettings.placeholder.json) are found from OCS
1. The user is prompted for confirmation to continue with processing since this is a change to the Streams
1. Each Stream's Type is changed from the existing Type to the new Type by calling the [Update Stream Type](https://docs.osisoft.com/bundle/ocs/page/api-reference/sequential-data-store/sds-streams.html#update-stream-type) action. 

## Using this sample when upgrading an adapter from version 1.1 to 1.2

The sample's specific logic as written will change the Types of PI Adapter streams from the 1.1 versioned Types of `TimeIndexed.<data_type>` (eg: `TimeIndexed.Double`) to the 1.2 versioned Types of `TimeIndexed.<data_type>.<adapter_name>Quality` (eg: `TimeIndexed.Double.OpcUaQuality`) to ingress the quality value where applicable. 

The steps to run this sample as an adapter stream type upgrade utility are as follows:

1. Upgrade the adapter instance from 1.1 to 1.2. New types will be created in the already configured OCS endpoint
1. Change this sample's [appsettings.json](appsettings.placeholder.json) settings to include:
    1. The adapter name (eg: `OpcUa`)
    1. The stream search pattern (eg: the `StreamIdPrefix` for this adapter instance's Data Source)
1. Run the sample
1. Observe the output and respond whether to continue with the stream view creations and type changes

## Adapting this sample to other use cases

Although this sample is built to be able to change SDS Types in a specific use case, it can be adapted to fit a more generic use case. The type conversion only require a dictionary mapping a Stream's existing Type to the ID of the Stream View that maps this Type to a new Type. 

This section of [program.py](program.py) covers the creation and/or definition of the necessary mapping table. Ultimately, the `type_to_stream_view_mappings` object needs to be set to a dictionary of `existing_type` to `stream_view_id` pairings for the sample to process later. 

```python
### Generic use case ###
""" type_to_stream_view_mappings = {
        'existing_type1': 'stream_view_id1',
        'existing_type2': 'stream_view_id2'
    } """
# Note: the stream views will need to be created first, whether programmatically or through the OCS portal

### Adapter 1.1 to 1.2 upgrade use case ###
type_to_stream_view_mappings = generate_adapter_upgrade_mappings(appsettings.get('AdapterName'), ocs_client)
```

Alternatively, another function could be created to programmatically generate the necessary Stream Views, and then mappings table. For assistance with the programmatic creation of Stream Views and explicitly mapping properties from one Type to another Type, see the [OCS Waveform Python sample](https://github.com/osisoft/sample-ocs-waveform-python).

The steps to run this sample as an adapter stream type upgrade utility are as follows:

1. Create the new Types in OCS, either programmatically or in the [OCS Portal](cloud.osisoft.com)
1. Create the Stream View in OCS that maps the existing Type to the new Type.
    1. For assistance with this step, see how to [Get Started With Stream Views](https://docs.osisoft.com/bundle/ocs/page/overview/get-started/gs-stream-views.html)
1. Change this sample's [appsettings.json](appsettings.placeholder.json) settings to include the stream search pattern
1. Define `type_to_stream_view_mappings` to map the existing Types to the corresponding Stream View Id
    1. This could be done by manually defining the dictionary, defining it in a separate file and reading it in, or calling a generation function like the adapter use case
1. Run the sample
1. Observe the output and respond whether to continue with the stream view creations and type changes

## Configuring the sample

The sample is configured by modifying the file [appsettings.placeholder.json](appsettings.placeholder.json). Details on how to configure it can be found in the sections below. Before editing appsettings.placeholder.json, rename this file to `appsettings.json`. This repository's `.gitignore` rules should prevent the file from ever being checked in to any fork or branch, to ensure credentials are not compromised.

### Configuring appsettings.json

OSIsoft Cloud Services is secured by obtaining tokens from its identity endpoint. Client credentials clients provide a client application identifier and an associated secret (or key) that are authenticated against the token endpoint. You must replace the placeholders in your `appsettings.json` file with the authentication-related values from your tenant and a client-credentials client created in your OCS tenant.

```json
{
  "Resource": "https://dat-b.osisoft.com",
  "ApiVersion": "v1",
  "TenantId": "REPLACE_WITH_TENANT_ID",
  "NamespaceId": "REPLACE_WITH_NAMESPACE_ID",
  "ClientId": "REPLACE_WITH_CLIENT_ID",
  "ClientSecret": "REPLACE_WITH_CLIENT_SECRET",
  "AdapterName": "REPLACE_WITH_ADAPTER_NAME",
  "StreamSearchPattern": "REPLACE_WITH_STREAM_SEARCH_PATTERN"
}
```

## Running the sample

To run this example from the command line once the `appsettings.json` is configured, run

```shell
python program.py
```

## Testing the sample

The end to end test for this sample simulates an existing adapter being upgraded from 1.2 to 1.3, which is the most common expected use case of this sample. 

The testing procedure is as follows:

1. Find a list of existing Time.Indexed.[DataType] SDS Types
    - The test asserts that there are at least two in order to test the looping capabilities of the script
1. For each type, create two streams with a specific naming pattern that should be safe from unintentional collisions
    - The test first checks this assumption, and asserts that there are no existing streams matching the testing syntax
1. The old types and the stream names are recorded together in a dictionary for later look ups
1. Existing Stream Views that match the sample's Stream View Id syntax are searched for so that they are not deleted at the end of the test
    - Since the sample is creating the stream views, the test framework will be unaware of which ones were created by the sample. Recording them at this step is necessary to not over-delete.
1. To simulate the installation of a version 1.3 PI Adapter, the corresponding TimeIndexed.[DataType].[AdapterName]Quality SDS Types are created. 
    - The sample assumes these are already created, so the test must create them ahead of time.
    - The test keeps track of anything created as to not over-delete at the end
1. The sample is run, which changes the types of the streams that were previously created
1. Each stream is checked to ensure that its new type is its old type with `[AdapterName]Quality` appended to the end.
1. The created streams are deleted
1. The streams views created by the sample are deleted
1. The types created by the sample are deleted
1. Any exception encountered along the way will trigger a failed test

### Test Requirements

In order to execute the test against a particular OCS namespace, the following assertions must be true:
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

For the main OCS samples page [ReadMe](https://github.com/osisoft/OSI-Samples-OCS)  
For the main OSIsoft samples page [ReadMe](https://github.com/osisoft/OSI-Samples)