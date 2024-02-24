import traceback
import os
import sys

############## GLOBALS ##############

############## CONSTANTS

DISC_PATH = "disc"

NAME_CLUSTER = "xxx SIMPLE FAT FILE SYSTEM SIMULATION xxx size 3000 xx clusters 30 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"

NAME_CLUSTER_START = 100
TABLE_CLUSTER_START = 101
ROOT_CLUSTER_START = 102
MAX_DISC_SIZE = 3000
CLUSTER_SIZE = 99

############## VARIABLES

############## ERRORS

DISC_FULL_ERROR = -1
FILE_TABLE_FULL_ERROR = -2

############## CLASSES ##############

class colors:
    INFO_PURPLE = '\033[95m'
    INFO_CYAN = '\033[96m'
    INFO_DARK_CYAN = '\033[36m'
    INFO_BLUE = '\033[94m'
    OK_GREEN = '\033[92m'
    INFO_YELLOW = '\033[93m'
    INFO_ORANGE = '\033[38;2;255;165;0m'
    ERROR_RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class FileHandle():
    def __init__(self, name = None, size = None, position = None, origin = None, active_cluster = None):
        self.name = name
        self.size = size
        self.position = position
        self.origin = origin
        self.active_cluster = active_cluster

############## FUNCTIONS ##############
        
def print_color_wrapper(text: str, format: str):
    print(format + text + colors.END)

def write_disc(disc:bytes):
    with open(DISC_PATH, 'wb') as f:
        f.write(disc)

def read_disc():
    with open(DISC_PATH, "rb") as f:
        return f.read()

def create_disc_with_size(size_in_bytes: int):
    with open(DISC_PATH, 'wb') as f:
        f.write(b'\0' * size_in_bytes)

def format_disc():
    disc = read_disc()
    byte_array = bytearray(disc)
    for i, char in enumerate(NAME_CLUSTER):
        byte_array[i] = ord(char)
    
    # set cluster 0 as not free
    byte_array[NAME_CLUSTER_START] = 255
    # set cluster 1 as not free
    byte_array[TABLE_CLUSTER_START] = 255
    # set cluster 2 as not free
    byte_array[ROOT_CLUSTER_START] = 255
    write_disc(bytes(byte_array))
    return byte_array

def mount_disc():
    try:
        disc = read_disc()
        return disc
    except Exception:
        traceback.print_exc()
        print_color_wrapper("Disc mount error", colors.ERROR_RED + colors.BOLD + colors.UNDERLINE)
        print_color_wrapper("Creating new disc", colors.BOLD + colors.INFO_PURPLE)
        create_disc_with_size(3072)
        print_color_wrapper("Formating disc", colors.BOLD + colors.INFO_PURPLE)
        byte_array = format_disc()
        return bytes(byte_array)

def unmount_disc():
    try:
        disc = read_disc()
        write_disc(disc)
        # Print disc memory address
        # print(id(disc))
        # Print disc reference count
        # print(sys.getrefcount(disc))
        del disc
        # This will now give UnboundLocalError since disc reference is deleted
        # When reference count drops to 0, Python's garbage collector will delete the object from memory
        # id(disc)
        # sys.getrefcount(disc)
        print_color_wrapper("Disc unmounted", colors.OK_GREEN)
        return True
    except Exception:
        traceback.print_exc()
        return False

def open_file(filename: str):
    fh = None
    try:
        if len(filename) == 1:
            if isinstance(filename, str):
                disc = read_disc()
                byte_array = bytearray(disc)
                fh = set_file_handle(byte_array, filename)
            else:
                raise ValueError(colors.ERROR_RED + "Wrong filename. Filename type must be str" + colors.END)
        else:
            raise ValueError(colors.ERROR_RED + "Wrong filename. Filename length must be 1" + colors.END)
        return fh
    except Exception:
        traceback.print_exc()
        return fh

def file_table_write_new_file(byte_array, filename):
    retval = None
    if byte_array[199] != 0:
        retval = FILE_TABLE_FULL_ERROR
    index = 101
    # If there is space in file table
    if retval == None:
        while True:
            if index == 130:
                retval = DISC_FULL_ERROR
                break
            if byte_array[index] == 0:
                byte_array[index] = 255
                retval = index
                break
            index += 1
        print_color_wrapper("Writing new file %s to the file table index: " % filename + str(index), colors.OK_GREEN)
        write_disc(bytes(byte_array))
    return retval

def file_table_extend_file(byte_array, fh):
    retval = None
    try:
        if byte_array[199] != 0:
            retval = FILE_TABLE_FULL_ERROR
            raise MemoryError(colors.ERROR_RED + "File table full" + colors.END) 
        index = 101
        # If there is space in file table
        if retval == None:
            while True:
                if index == 131:
                    retval = DISC_FULL_ERROR
                    write_disc(bytes(byte_array))
                    raise MemoryError(colors.ERROR_RED + "Disc full unable to write to cluster 31 for file %s" % fh.name + colors.END) 
                if byte_array[index] == 0:
                    byte_array[index] = 255
                    byte_array[fh.active_cluster] = index
                    fh.active_cluster = index
                    retval = index
                    break
                index += 1
            print_color_wrapper("Extending file %s to the file table index: " % fh.name + str(index), colors.INFO_CYAN)
            write_disc(bytes(byte_array))
        return retval
    except Exception:
        traceback.print_exc()
        return retval

def root_cluster_write_new_file(filename, byte_array, root_index, file_cluster):
    try:
        print_color_wrapper("Writing new file %s to the root cluster index: " % filename + str(root_index), colors.OK_GREEN)
        fh = FileHandle()

        # set origin
        fh.origin = root_index

        # set filename
        byte_array[root_index] = ord(filename)
        fh.name = filename

        # set position
        root_index += 1
        byte_array[root_index] = file_cluster
        fh.position = byte_array[root_index]

        # set size
        root_index += 1
        byte_array[root_index] = 1
        fh.size = 1

        write_disc(bytes(byte_array))
        return fh
    except Exception:
        traceback.print_exc()
        return None
    
def set_file_handle(byte_array, filename):
    # start of root cluster
    retval = None
    try:
        root_index = find_root_cluster(byte_array, ROOT_CLUSTER_START)
        root_index = (root_index % 100) * 100
        print_color_wrapper("Searching for free root cluster space from index: " + str(root_index), colors.INFO_YELLOW + colors.UNDERLINE)
        root_cluster_end = root_index + 99
        if check_root_cluster_write_space(byte_array, root_cluster_end):
            while(True):
                # if root cluster index is empty start writing
                if byte_array[root_index] == 0:
                    retval = file_table_write_new_file(byte_array, filename)
                    if retval == FILE_TABLE_FULL_ERROR: 
                        raise MemoryError(colors.ERROR_RED + "File table full, unable to open file %s" % filename + colors.END) 
                    elif retval == DISC_FULL_ERROR: 
                        raise MemoryError(colors.ERROR_RED + "Disc full, unable to open file %s" % filename + colors.END)
                    elif retval != None:
                        file_table_cluster = retval
                    retval = root_cluster_write_new_file(filename, byte_array, root_index, file_table_cluster)
                    break
                else:
                    root_index += 1
        else:
            retval = DISC_FULL_ERROR
        return retval
    except Exception:
        traceback.print_exc()
        return retval

def find_root_cluster(byte_array, index):
    if byte_array[index] == 255:
        return index
    else:
        index = find_root_cluster(byte_array, index)
        return index

def check_root_cluster_write_space(byte_array, index):
    if byte_array[index] == 0 and byte_array[index-1] and byte_array[index-2]:
        return True
    else:
        return DISC_FULL_ERROR

def print_clusters(num = 27):

    disc = read_disc()
    int_array = [int(byte) for byte in disc] 
    start_index = 100
    print_color_wrapper("\n#####################################", colors.INFO_YELLOW)
    print_color_wrapper("########## FIRST CLUSTER ############", colors.INFO_YELLOW)
    print(disc[:start_index])
    print_color_wrapper("########## FILE TABLE CLUSTER #######", colors.INFO_YELLOW)
    print(int_array[start_index:start_index+30])
    start_index += 100
    print_color_wrapper("########## ROOT CLUSTER #############", colors.INFO_YELLOW)
    print(int_array[start_index:start_index+100])
    start_index += 100

    for i in range(num):
        print_color_wrapper("########## FILE CLUSTER %s ###########"%(i+4), colors.INFO_DARK_CYAN)
        print(disc[start_index:start_index + 100])
        start_index += 100
    print_color_wrapper("\n#####################################", colors.INFO_DARK_CYAN)
    print()
    
def write_file(fh, buffer):
    try:
        first_cluster_index = 0
        first_cluster_flag = False
        disc = read_disc()
        byte_array = bytearray(disc)
        fh.active_cluster = fh.position
        cluster_index = (fh.position % 100) * 100
        while True:
            if byte_array[cluster_index] == 0:
                # set first cluster index to enable data append
                if first_cluster_flag == False:
                    first_cluster_flag = True
                    first_cluster_index = cluster_index
                    first_cluster_index = round(first_cluster_index / 100) * 100
                cnt = 0
                for i in buffer:
                    index = cluster_index + cnt
                    if index > first_cluster_index + CLUSTER_SIZE:
                        retval = file_table_extend_file(byte_array, fh)
                        if retval != DISC_FULL_ERROR and retval != FILE_TABLE_FULL_ERROR:
                            # calculate starting index
                            cluster_index = (retval % 100) * 100
                            # set starting index for the new cluster
                            first_cluster_index = cluster_index
                            # counter reset
                            cnt = 0
                            index = cluster_index + cnt

                            # increment file size
                            fh.size = fh.size + 1
                            byte_array[fh.origin + 2] = fh.size
                        else:
                            # reset to starting position
                            return retval
                    if index > MAX_DISC_SIZE:
                        write_disc(bytes(byte_array))
                        raise MemoryError(colors.ERROR_RED + "Disc full, unable to write beyond index 3000 for file %s" % fh.name + colors.END)
                    byte_array[index] = ord(i)
                    cnt += 1
                print_color_wrapper("Buffer data: %s successfully written to file %s" % (buffer[:10], fh.name), colors.INFO_ORANGE)
                write_disc(bytes(byte_array))
                break
            cluster_index += 1
    except Exception:
        traceback.print_exc()

def close_file(fh):
    try:
        print_color_wrapper("File %s closed"%fh.name, colors.INFO_CYAN)
        del fh
        return True
    except Exception:
        traceback.print_exc()
        return False

def delete_file(fh):
    disc = read_disc()
    byte_array = bytearray(disc)
    file_position = fh.position

    # deleting data from the root cluster
    byte_array[fh.origin] = 0
    byte_array[fh.origin+1] = 0
    byte_array[fh.origin+2] = 0

    # deleting data from file clusters
    for i in range (fh.size):
        # deleting data from the file table cluster
        byte_array[file_position] = 0
        cluster_index = (file_position % 100) * 100
        for i in range(100):
            byte_array[cluster_index + i] = 0
        file_position += 1
    write_disc(bytes(byte_array))    

def open_write_file(data, len):
    fh = open_file(data)
    if fh != DISC_FULL_ERROR and FILE_TABLE_FULL_ERROR:
        write_file(fh, fh.name * len)
    return fh

def delete_disc():
    os.remove("disc")
    print_color_wrapper("Disc simulation file deleted !", colors.BOLD + colors.OK_GREEN)

def append_file_data(fh, data, len):
    if fh != DISC_FULL_ERROR and FILE_TABLE_FULL_ERROR:
        write_file(fh, data * len)

############## APPLICATION START ##############

if __name__ == "__main__":

    # Read or create new disc
    disc = mount_disc()

    # Write data
    fh_1 = open_write_file("a", 110) 
    fh_2 = open_write_file("b", 510)
    open_write_file("c", 310)
    fh_4 = open_write_file("d", 310)
    open_write_file("e", 310)
    open_write_file("f", 410)

    # Append data
    append_file_data(fh_1, "z", 50)

    # Delete data
    delete_file(fh_2)
    delete_file(fh_4)

    # Deplete empty disc space
    open_write_file("g", 10000)

    print_clusters()

    # Saves current disc data and remove reference for disc object
    unmount_disc()
    # Delete disc file
    delete_disc()
