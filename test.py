"""This script tests the OCS Stream Type Change Python sample script"""

import json
from os import name
import unittest

from ocs_sample_library_preview.SDS.SdsTypeCode import SdsTypeCode
from .program import main
from ocs_sample_library_preview import OCSClient, SdsStream, SdsType, SdsTypeProperty

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

class OCSStreamTypeChangePythonSampleTests(unittest.TestCase):
    """Tests for the OCS Stream Type Change Python sample"""

    @classmethod
    def test_main(cls):
        """Tests the OCS Stream Type Change Python main sample script"""

        # track if an exception was thrown along the way
        exception = None

        # Read configuration from appsettings.json and create the OCS client object
        appsettings = get_appsettings()

        ocs_client = OCSClient(appsettings.get('ApiVersion'),
                                appsettings.get('TenantId'),
                                appsettings.get('Resource'),
                                appsettings.get('ClientId'),
                                appsettings.get('ClientSecret'))

        namespace_id = appsettings.get('NamespaceId')
        adapter_name = appsettings.get('AdapterName')
        stream_search_query = appsettings.get('StreamSearchPattern')

        # Fail the test now if the sample is about to use a stream search pattern that doesn't match the stream_id_template that the unit test will use below.
        # This approach is safer than running the test against any arbitrary search pattern, and letting the test framework determine which streams were new and which were exsiting
        # NOTE: changing this query string requires a change of the successful type change assertion further down the script
        expected_stream_search_query = 'unittest_for_* AND *_conversion'
        assert expected_stream_search_query.lower() == stream_search_query.lower(), f'stream search pattern did not matched expected value of {expected_stream_search_query}. Abandonning test to prevent unintentional CRUD operations'
        
        # confirm no streams with this search pattern already exist. Fail the test if there are
        existing_streams_matching_pattern = ocs_client.Streams.getStreams(namespace_id=namespace_id, query=stream_search_query)
        assert len(existing_streams_matching_pattern) == 0, f'streams matching the search pattern {stream_search_query} already exist on the Namespace. Abandonning test to prevent unintentional CRUD operations'

        num_streams_per_type = 2
        stream_id_template = 'unittest_for_{sds_type}_{i}_conversion'

        streams_created = []
        types_created = []
        existing_stream_views = []
        stream_to_old_type_mappings = {}

        # Confirm a few of the TimeIndexed.<datatype> types exist on the target namespace
        existing_type_query = f'TimeIndexed.* AND NOT *.{adapter_name}Quality'
        existing_types = ocs_client.Types.getTypes(namespace_id=namespace_id, query=existing_type_query)

        assert len(existing_types) < 2, 'Target namespace needs at least 2 existing TimeIndexed.<data_type> SDS Types to perform this test.'
        
        try:
            # Create two streams per existing 1.1 types
            for i in range(num_streams_per_type): 
                for e_type in existing_types: 
                    
                    # create the stream with the legacy type id, and follow the expected stream name/id format so the sample will find it
                    this_stream = SdsStream(id=stream_id_template.format(sds_type=e_type, i=i), 
                                            type_id=e_type.Id, 
                                            name=stream_id_template.format(sds_type=e_type, i=i))

                    ocs_client.Streams.getOrCreateStream(namespace_id=namespace_id, stream=this_stream)

                    # track that this stream was created by the test so that it's deleted at the end
                    streams_created.append(this_stream.Id)

                    # keep track of what the old type was for this stream, so that it can be checked later
                    stream_to_old_type_mappings[this_stream.Id] = e_type.Id

            # Check if the stream views that the sample will create already exist, if they do don't delete them at the end
            existing_stream_view_query = f'{adapter_name}_* AND *_quality'
            existing_stream_views = ocs_client.StreamViews.getStreamViews(namespace_id=namespace_id, query=existing_stream_view_query)
            
            # convert the list of stream view objects to a set of stream view ids for easier subtraction later
            existing_stream_view_ids = set()
            for stream_view in existing_stream_views:
                existing_stream_view_ids.add(stream_view.Id)

            # Check if the new types of TimeIndexed.<datatype>.{adapter_name}Quality exists, if they don't, create it and delete it at the end
            for e_type in existing_types:
                try:
                    # we don't need to do anything with this type object, we just need to check if it exists already
                    _ = ocs_client.Types.getType(namespace_id=namespace_id, type_id=f'{e_type.Id}.{adapter_name}Quality')

                except:
                    # create the type
                    new_13_type = SdsType(id=f'{e_type}.{adapter_name}Quality',
                                         name=f'{e_type}.{adapter_name}Quality')
                    
                    # copy over the two existing properties
                    for prop in e_type.Properties:
                        new_13_type.Properties.append(prop)
                    
                    # add the new quality property
                    uint32_type = SdsType('uint32', SdsTypeCode.UInt32)
                    quality_prop = SdsTypeProperty(id='Quality', is_key=False, sds_type=uint32_type, name='Quality')
                    new_13_type.Properties.append(quality_prop)

                    # commit it to OCS
                    # Note: This call could raise an exception, but it will be good to end the test and not continue on with wrong types, incase they linger on the namespace for some reason
                    ocs_client.Types.getOrCreateType(namespace_id=namespace_id, type=new_13_type)

                    # track that the type was created by the test so that it's deleted at the end
                    types_created.append(new_13_type.Id)

            # run the sample
            try:
                main(True)

            except Exception as e:
                print(f'Exception reported by the sample code: {e}')
                exception = e

            # check that the streams now have the correctly updated types
            for stream_created in streams_created:
                
                # look up what the old was, and add .{adapter_name}Quality, such as ".OpcUaQuality", to predict what the new type should be
                old_sds_type_id = stream_to_old_type_mappings[stream_created]
                expected_new_type_id = f'{old_sds_type_id}.{adapter_name}Quality'
                new_sds_type = ocs_client.Streams.getStreamType(namespace_id=namespace_id, stream_id=stream_created)
                assert new_sds_type.Id == expected_new_type_id, f'type conversion failed for {stream_created}. old type: {old_sds_type_id}, expected type: {expected_new_type_id}, new type: {new_sds_type}'


        except Exception as e:
            print(f'Exception in the testing framework: {e}')
            exception = e

        finally:
            # delete the streams
            for stream_created in streams_created:
                try:
                    ocs_client.Streams.deleteStream(namespace_id=namespace_id, stream_id=stream_created.Id)
                except Exception as e:
                    print(f'failed to delete stream {stream_created.Id}. {e}')
                    exception = e

            # figure out which stream views were created by the sample
            stream_views_after_script = ocs_client.StreamViews.getStreamViews(namespace_id=namespace_id, query=existing_stream_view_query)
            
            stream_view_ids_after_script = set()
            for stream_view in stream_views_after_script:
                stream_view_ids_after_script.add(stream_view.Id)

            newly_created_stream_view_ids = stream_view_ids_after_script - existing_stream_view_ids

            # delete the stream views that the sample created
            for stream_view_id in newly_created_stream_view_ids:
                try:
                    ocs_client.StreamViews.deleteStreamView(namespace_id=namespace_id, stream_view_id=stream_view_id)
                except Exception as e:
                    print(f'failed to delete stream view {stream_view_id}. {e}')
                    exception = e

            # delete the types
            for type_created in types_created:
                try:
                    ocs_client.Types.deleteType(namespace_id=namespace_id, type_id=type_created)
                except Exception as e:
                    print(f'failed to delete type {type_created}. {e}')
                    exception = e
            
        # Be sure to fail the test after the clean up phase
        assert exception is None, 'exception enountered during the test'


if __name__ == "__main__":
    unittest.main()