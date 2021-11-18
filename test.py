"""This script tests the OCS Stream Type Change Python sample script"""

import unittest
from .program import main


class OCSStreamTypeChangePythonSampleTests(unittest.TestCase):
    """Tests for the OCS Stream Type Change Python sample"""

    @classmethod
    def test_main(cls):
        """Tests the OCS Stream Type Change Python main sample script"""

        # Confirm a few of the TimeIndexed.<datatype> types exist on the target namespace

        
        # Create some tests streams across a couple of the existing 1.1 types
        

        # Check if the new types of TimeIndexed.<datatype>.OpcUaQuality exists, if they do don't delete them at the end

        
        # Check if the new stream views exist, if they do don't delete them at the end


        # run the sample
        exception = None

        try:
            main(True)

        except Exception as error:
            exception = error

        finally:
            
            # delete the streams


            # delete the stream views


            # delete the types

            pass

        # Be sure to fail the test after the clean up phase
        if exception is not None:
            raise exception


if __name__ == "__main__":
    unittest.main()