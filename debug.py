import os
import codecs


class Debug(object):
    DEBUG        = False
    READFROMFILE = False  # Read from file for debugging
    SAVELASTFILE = False  # Write to file upon each request

    @staticmethod
    def readFromFile(file_name):
        """
        readFromFile(): Read the debug information from file if READFROMFILE is enabled
        """
        if Debug.READFROMFILE and os.path.exists(file_name):
            with open(file_name, 'rb') as debug_file:
                return debug_file.read()
        else:
            return ''
    # END: def readFromFile():

    @staticmethod
    def writeToFile(file_name, debug, encoding):
        """
        writeToFile(): Write the debug information to file if SAVELASTFILE is enabled
        """
        if Debug.SAVELASTFILE:
            try:
                with codecs.open(file_name, 'w', encoding) as debug_file:
                    debug_file.write(str(debug))
            except TypeError:
                with open(file_name, 'ab') as debug_file:
                    debug_file.write(str(debug))
    # END: def writeToFile():
# END: class Debug
