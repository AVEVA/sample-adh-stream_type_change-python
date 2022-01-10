import datetime
import json
import logging
import traceback
from ocs_sample_library_preview import (OCSClient, Types, Streams, StreamViews, SdsStreamView)

def get_appsettings():
    """Open and parse the appsettings.json file"""

    # Try to open the configuration file
    try:
        with open('appsettings.json', 'r') as f:
            appsettings = json.load(f)

    except Exception as error:
        logging.error(f'Error: {str(error)}')
        logging.error(f'Could not open/read appsettings.json')
        exit()

    return appsettings

def affirmative_response(response):
    logging.debug(f'checking user response of {response}')
    affirmative_responses = ['y', 'yes']
    return response.lower() in affirmative_responses

def output(level, message):
    logging.log(level, message)
    print(message)

def generate_adapter_upgrade_mappings(adapter_type, ocs_client, namespace_id, test):
    """This function takes in an adapter type (such as 'OpcUa'), generates the necessary stream views,
    and returns a mapping table for the existing type to the stream view that maps it to the new type.
    This function is specific to the adapter version 1.1 to 1.2 upgrade use case"""

    # Some adapters have known types that will not be migratable, for example DNP3. These should be skipped
    tested_adapter_types = {'opcua'}
    incompatible_adapter_types = {'dnp3'}

    # If a known imcompatible adapter is attempted, stop the script and log an error
    if adapter_type.lower() in incompatible_adapter_types:
        output(logging.ERROR, f'The adapter type of {adapter_type} is known to be incompatible with this script. Please perform the type changes manually or contact support for assistance.')
        raise Exception(f'Incompatible adapter type of {adapter_type} detected')

    # If the specified adapter type is not known to work or known to fail, warn and continue. This could be a typo in the settings file, or a new untested adapter type
    if adapter_type.lower() not in tested_adapter_types:
        output(logging.WARNING, f'Encountered untested adapter type of {adapter_type}. The konwn tested adapter types are {", ".join(tested_adapter_types)}. If this was unintended, please rerun the script with the correct adapter type.')


    mapping = {}
    
    # Find types created by the adapter upgrade (TimeIndexed.<datatype>.<AdapterType>Quality):
    type_search_query = f'TimeIndexed.* AND *.{adapter_type}Quality'
    new_types = ocs_client.Types.getTypes(namespace_id, query=type_search_query)

    if len(new_types) == 0:
        output(logging.ERROR, 'No PI Adapter v1.2 types were detected on the namespace for this adapter type. Be sure to upgrade the adapter before running this script. Quitting...')
        raise Exception(f'No PI Adapter v1.2 types were detected on this namespace.')


    if test:
        # If this script is being E2E tested, presume the user input to be y
        response = 'y'
        output(logging.DEBUG, f'Automated test will begin stream view creation without prompting the user, assuming a response of {response}.')
        

    else: 
        # Before creating the stream views, user confirmation is requested
        output(logging.INFO, f'Found {len(new_types)} types that are potentially going to be have stream views created to map existing types to them.')
        logging.debug(f'Prompting user whether they would like to see the list of new type IDs.')
        response = input('Would you like to see their IDs? (y/n): ')
        logging.debug(f'Response: {response}')
        print()

        if affirmative_response(response):
            for new_type in new_types:
                output(logging.INFO, new_type.Id)

        print()
        logging.debug(f'Prompting user whether they would like to continue with the stream view creations.')
        response = input('Would you like to create the stream views? (y/n): ')
        logging.debug(f'Response: {response}')
        print()
    
    if affirmative_response(response):

        for new_type in new_types:

            # Extract out the data type from the type name, and infer the existing type name
            type_name_parts = new_type.Id.split('.')
            
            # The 'simple' types (eg. TimeIndexed.Int32.OpcUaQuality) are three pieces: 0 = 'TimeIndexed'; 1 = <data type>; 2 = '<adapter_type>Quality
            # Others, such as 'enum' types are more pieces and cannot be migrated with this script
            if len(type_name_parts) > 3:
                output(logging.WARNING, f'Non-simple type detected. No streams will be automatically migrated to {new_type}...')
                output(logging.WARNING, f'...If possible, the existing steams will be converted to their corresponding integer quality type.')
                continue

            # The version 1.1 SDS Type ID is the first two parts joined back together (eg. TimeIndexed.Int32.OpcUaQuality -> TimeIndexed.Int32)
            existing_type_id = '.'.join(type_name_parts[:2])

            # The data type is the second piece of 0 = 'TimeIndexed'; 1 = <data type>; 2 = '<adapter_type>Quality
            data_type = type_name_parts[1]

            # Create the stream views from existing type to new type
            # Note: Explicit property mappings are not required for this conversion because OCS can infer them from the property names
            this_stream_view_id = f'{adapter_type}_{data_type}_quality'
            this_stream_view = SdsStreamView(id=this_stream_view_id, source_type_id=existing_type_id, target_type_id=new_type.Id)

            output(logging.INFO, f'Creating stream view with id {this_stream_view_id} mapping {existing_type_id} to {new_type.Id}...')
            try:
                this_stream_view = ocs_client.StreamViews.getOrCreateStreamView(namespace_id, this_stream_view)
            except Exception as error:
                # Log the error, but don't raise the exception. This failure is only a problem if it causes a stream to fail to convert, which will be caught later as a separate exception
                output(logging.ERROR, f'Encountered error while creating stream view with id {this_stream_view_id}: {error}')
                output(logging.ERROR, f'This script will continue but may fail later when attempting to convert streams from {existing_type_id} to {new_type.Id}.')
                
                
            # add the streamview id to the mappings list under the key of the existing type id
            mapping[existing_type_id] = this_stream_view.Id
        
        output(logging.INFO, 'Done creating stream views.')

    else:
        output(logging.INFO, 'Returning blank mapping table')
        
    return mapping

def main(test=False):
    """This function is the main body of the SDS sample script"""
    exception = None

    try:
        appsettings = get_appsettings()

        # Read configuration from appsettings.json and create the OCS client object
        output(logging.DEBUG, 'Authenticating to OCS...')
        ocs_client = OCSClient(appsettings.get('ApiVersion'),
                                appsettings.get('TenantId'),
                                appsettings.get('Resource'),
                                appsettings.get('ClientId'),
                                appsettings.get('ClientSecret'))

        namespace_id = appsettings.get('NamespaceId')
        stream_search_query = appsettings.get('StreamSearchPattern')

        # Create a dictionary that maps the existing type name to the stream view id that maps that type to the corresponding new type
        # Only a dictionary is needed to proceed, but the sample can generate its own for the adapter upgrade from 1.1 to 1.2. 
        # Uncommented certain lines of code such that one type_to_stream_view_mappings object is created

        ### Generic use case ###
        """ type_to_stream_view_mappings = {
                'existing_type1': 'stream_view_id1',
                'existing_type2': 'stream_view_id2'
            } """
        # Note: the stream views will need to be created first, whether programmatically or through the OCS portal

        ### Adapter 1.1 to 1.2 upgrade use case ###
        type_to_stream_view_mappings = generate_adapter_upgrade_mappings(appsettings.get('AdapterType'), ocs_client, namespace_id, test)

        # Get streams in the namespace
        streams = ocs_client.Streams.getStreams(namespace_id, query=stream_search_query)

        if len(streams) == 0:
            message = f'No stream found on namespace {namespace_id} that match the stream search pattern of {stream_search_query}'
            output(logging.ERROR, message)
            output(logging.ERROR, 'Quitting script...')
            raise Exception(message)

        if test:
            # If this script is being E2E tested, presume the user input to be y
            response = 'y'
            output(logging.DEBUG, f'Automated test will begin type conversion without prompting the user, assuming a response of {response}.')

        else: 
            # Before changing the streams, user confirmation is requested
            print()
            output(logging.INFO, f'Found {len(streams)} streams that are potentially going to be converted using stream view.')
            print()
            logging.debug(f'Prompting user whether they would like to see the list of stream IDs.')
            response = input('Would you like to see their IDs? (y/n): ')
            logging.debug(f'Response: {response}')
            print()

            if affirmative_response(response):
                for stream in streams:
                    output(logging.INFO, f'ID: {stream.Id} Name: {stream.Name}')

            print()
            logging.debug(f'Prompting user whether they would like to continue with the stream type edits.')
            response = input('Would you like to continue with the type conversions? (y/n): ')
            logging.debug(f'Response: {response}')
            print()

        if affirmative_response(response):

            output(logging.INFO, 'Processing streams...')
            
            # Keep track of the streams processed and skipped
            converted_streams = 0
            skipped_streams = 0
            failed_streams = 0

            for stream in streams:

                # Look for the stream's existing type in the mappings table. If it's there, apply the stream view
                if stream.TypeId in type_to_stream_view_mappings:
                    output(logging.INFO, f'Changing type of {stream.Id} away from {stream.TypeId} using steamview id {type_to_stream_view_mappings[stream.TypeId]}...')
                    try:
                        ocs_client.Streams.updateStreamType(namespace_id, stream_id=stream.Id, stream_view_id=type_to_stream_view_mappings[stream.TypeId])
                        converted_streams += 1
                    except Exception as error:
                        output(logging.ERROR, f'Encountered error while converting stream: {error}')
                        exception = error
                        failed_streams += 1

                # If it's not, skip it and notify the user why it wasn't processed
                else:
                    output(logging.WARNING, f'Skipped {stream.Id} because it has a type of {stream.TypeId}, which is not in the mappings table. It will need to be migrated separately.')
                    skipped_streams += 1

            # Log the final tallies of each counter  
            output(logging.INFO, f'Operation completed. Successfully converted {converted_streams} streams.')
            
            # If a stream failed or was skipped, log it was a warning. Otherwise, log it as info
            if failed_streams > 0 or skipped_streams > 0:
                output(logging.WARNING, f'Operation incomplete. Failed to convert {failed_streams} streams and skipped {skipped_streams} streams.')
            else:
                output(logging.INFO, f'No streams failed to convert or were skipped.')

        else:
            output(logging.INFO, 'Exiting. No transformation will be attempted.')

    except Exception as error:
        output(logging.ERROR, f'Encountered Error: {error}')
        traceback.print_exc()
        exception = error

    finally:
        if test and exception is not None:
            raise exception


if __name__ == '__main__':
    
    ## Logging Config ##

    # This sample is configured to log a record of the CRUD operations as 'Info' level, and all other operations as 'Debug'
    #level = logging.DEBUG   # use to troubleshoot the sample
    level = logging.INFO     # use for record keeping

    # specify the log file if necessary (append if already created)
    log_file_name = 'logfile.txt'

    # Set up the logger
    logging.basicConfig(filename=log_file_name, encoding='utf-8', level=level, datefmt='%Y-%m-%d %H:%M:%S', format= '%(asctime)s %(module)16s,line: %(lineno)4d %(levelname)8s | %(message)s')
    output(logging.INFO, 'Starting Stream Type change sample')

    try:
        # Run the sample
        main()
    
        # No except block is necessary as exceptions will be logged by the sample itself
    finally:
        # Write a message that the logger is done.
        output(logging.INFO, 'Stream Type change sample completed')
