import json
from ocs_sample_library_preview import (OCSClient, Types, Streams, StreamViews, SdsStreamView)

def get_appsettings():
    """Open and parse the appsettings.json file"""

    # Try to open the configuration file
    try:
        with open('appsettings.json', 'r') as f:
            appsettings = json.load(f)

    except Exception as error:
        print(f'Error: {str(error)}')
        print(f'Could not open/read appsettings.json')
        exit()

    return appsettings

def generate_adapter_upgrade_mappings(adapter_name, ocs_client):
    """This function takes in an adapter name (such as 'OpcUa'), generates the necessary stream views,
    and returns a mapping table for the existing type to the stream view that maps it to the new type.
    This function is specific to the adapter version 1.1 to 1.2 upgrade use case"""

    mapping = {}
    
    # Find types created by the adapter upgrade (TimeIndexed.<datatype>.<adaptername>Quality):
    type_search_query = f'TimeIndexed.* AND *.{adapter_name}Quality'
    new_types = ocs_client.Types.getTypes(namespace_id, query=type_search_query)

    # Before creating the stream views, user confirmation is requested
    print(f'Found {len(new_types)} types that are potentially going to be have stream views created to map old types to them.')
    response = input('Would you like to see their IDs? (y/n): ')
    print()

    if response.lower() == 'y' or response.lower() == 'yes':
        for new_type in new_types:
            print(new_type.Id)

    print()
    response = input('Would you like to create the stream views? (y/n): ')
    print()

    if response.lower() == 'y' or response.lower() == 'yes':

        for new_type in new_types:

            # Extract out the data type from the type name, and infer the old type name
            data_type = new_type.Id.split('.')[1] # 0 = 'TimeIndexed'; 1 = <data type>; 2 = '<adapter_name>Quality
            old_type_id = f'TimeIndexed.{data_type}'

            # Create the stream views from existing type to new type
            # Note: Explicit property mappings are not required for this conversion because OCS can infer them from the property names
            this_stream_view_id = f'{adapter_name}_{data_type}_quality'
            this_stream_view = SdsStreamView(id=this_stream_view_id, source_type_id=old_type_id, target_type_id=new_type.Id)

            print(f'Creating streamview with id {this_stream_view_id} mapping {old_type_id} to {new_type.Id}...')
            this_stream_view = ocs_client.StreamViews.getOrCreateStreamView(namespace_id, this_stream_view)

            # add the streamview id to the mappings list under the key of the old type id
            mapping[old_type_id] = this_stream_view.Id

    else:
        print('Returning blank mapping table')
        
    return mapping

appsettings = get_appsettings()

# Read configuration from appsettings.json and create the OCS client object
print()
print('Step 1: Authenticate against OCS')
ocs_client = OCSClient(appsettings.get('ApiVersion'),
                        appsettings.get('TenantId'),
                        appsettings.get('Resource'),
                        appsettings.get('ClientId'),
                        appsettings.get('ClientSecret'))

namespace_id = appsettings.get('NamespaceId')
stream_search_query = appsettings.get('StreamSearchPattern')

# Create a dictionary that maps the old type name to the stream view id that maps that type to the corresponding new type
# Only a dictionary is needed to proceed, but the sample can generate its own for the adapter upgrade from 1.1 to 1.2. 
# Uncommented certain lines of code such that one type_to_stream_view_mappings object is created

### Generic use case ###
# type_to_stream_view_mappings = {
#     'old_type1': 'stream_view_id1',
#     'old_type2': 'stream_view_id2'
# }
# Note: the stream views will need to be created first, whether programmatically or through the OCS portal

### Adapter 1.1 to 1.2 upgrade use case ###
type_to_stream_view_mappings = generate_adapter_upgrade_mappings(appsettings.get('AdapterName'), ocs_client)

# Get streams in the namespace
streams = ocs_client.Streams.getStreams(namespace_id, query=stream_search_query)

# Before changing the streams, user confirmation is requested
print()
print(f'Found {len(streams)} streams that are potentially going to be converted using stream view.')
print()
response = input('Would you like to see their IDs? (y/n): ')
print()

if response.lower() == 'y' or response.lower() == 'yes':
    for stream in streams:
        print(f'ID: {stream.Id} Name: {stream.Name}')

print()
response = input('Would you like to continue with the type conversions? (y/n): ')
print()

if response.lower() == 'y' or response.lower() == 'yes':

    print('Processing streams...')
    
    # Keep track of the streams processed and skipped
    converted_streams = 0
    skipped_streams = 0

    for stream in streams:

        # Look for the stream's existing type in the mappings table. If it's there, apply the stream view
        if stream.TypeId in type_to_stream_view_mappings:
            print(f'Changing type of {stream.Id} away from {stream.TypeId} using steamview id {type_to_stream_view_mappings[stream.TypeId]}...')
            ocs_client.Streams.updateStreamType(namespace_id, stream_id=stream.Id, stream_view_id=type_to_stream_view_mappings[stream.TypeId])
            converted_streams += 1

        # If it's not, skip it and notify the user why it wasn't processed
        else:
            print(f'Skipped {stream.Id} because it has a type of {stream.TypeId}, which is not in the mappings table.')
            skipped_streams += 1
                    
    print()
    print(f'Operation completed. Successfully converted {converted_streams} streams and skipped {skipped_streams} streams.')

else:
    print('Exiting. No transformation is going to happen.')
