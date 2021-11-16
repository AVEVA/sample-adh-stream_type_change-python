import json
from ocs_sample_library_preview import (OCSClient, Types, Streams, StreamViews, SdsStreamView)

def get_appsettings():
    """Open and parse the appsettings.json file"""

    # Try to open the configuration file
    try:
        with open(
            'appsettings.json',
            'r',
        ) as f:
            appsettings = json.load(f)
    except Exception as error:
        print(f'Error: {str(error)}')
        print(f'Could not open/read appsettings.json')
        exit()

    return appsettings


appsettings = get_appsettings()

# Read endpoint and mapping configurations from config.json
print()
print('Step 1: Authenticate against OCS')
ocs_client = OCSClient(appsettings.get('ApiVersion'),
                        appsettings.get('TenantId'),
                        appsettings.get('Resource'),
                        appsettings.get('ClientId'),
                        appsettings.get('ClientSecret'))

namespace_id = appsettings.get('NamespaceId')

adapter_name = appsettings.get('AdapterName')
stream_search_query = appsettings.get('StreamSearchPattern')
type_search_query = f'TimeIndexed.* AND *.{adapter_name}Quality'

type_to_stream_view_mappings = {}

# Find types created by the adapter upgrade (TimeIndexed.<datatype>.<adaptername>Quality):
new_types = ocs_client.Types.getTypes(namespace_id, query=type_search_query)

for new_type in new_types:

    data_type = new_type.Id.split('.')[1] # 0 = 'TimeIndexed'; 1 = <data type>; 2 = '<adapter_name>Quality
    old_type_id = f'TimeIndexed.{data_type}'

    # Create the stream views from existing type to new type
    this_stream_view = SdsStreamView(id=f'{adapter_name}_{data_type}_quality', source_type_id=old_type_id, target_type_id=new_type.Id)
    this_stream_view = ocs_client.StreamViews.getOrCreateStreamView(namespace_id, this_stream_view)

    # add the streamview id to the mappings list under the key of the old type id
    type_to_stream_view_mappings[old_type_id] = this_stream_view.Id


# Get streams in the namespace
streams = ocs_client.Streams.getStreams(namespace_id, query=stream_search_query)

print(f'Found {len(streams)} streams that are potentially going to be converted using stream view.')
response = input('Would you like to continue? (y/n): ')

# Ask user to ACK the conversion

if response.lower() == 'y' or response.lower() == 'yes':
    print('Pyrocessing streams...')
    converted_streams = 0
    skipped_streams = 0
    for stream in streams:
        if stream.TypeId in type_to_stream_view_mappings:
            ocs_client.Streams.updateStreamType(namespace_id, stream_id=stream.Id, stream_view_id=type_to_stream_view_mappings[stream.TypeId])
            converted_streams += 1
        else:
            print(f'Skipping {stream.Id} because it has a type of {stream.TypeId}.')
            skipped_streams += 1
                    
    print(f'Operation completed. Successfully converted {converted_streams} streams and skipped {skipped_streams} streams.')

else:
    print('Exiting. No transformation is going to happen.')
