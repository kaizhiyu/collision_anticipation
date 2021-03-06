import vrep
import sys
import time
import numpy as np
from scipy.misc import imsave
import random
import scipy.io as sio
import scipy
from scipy import ndimage
import configparser

config = configparser.ConfigParser()
config.read('../config.ini')

base_dir = config['DEFAULT']['BASE_DIR']


'''
This is my main script to generate data from my vrep scene. This collects the video data and the collision ground truth
'''

x_list_of_positions = np.random.normal(0, 1.2, 30000)
y_list_of_positions = np.random.normal(-8 , 1.2, 30000)
z_permanent = .2555

with open(base_dir + '/vrep_scripts/saved_vel_pos_data/current_position.txt', "w") as new_pos_file:
    print(x_list_of_positions[0], file=new_pos_file)
    print(y_list_of_positions[0], file=new_pos_file)
    print(z_permanent, file=new_pos_file)



def start():
    vrep.simxFinish(-1) # just in case, close all opened connections
    clientID=vrep.simxStart('127.0.0.1',19997,True,True,5000,5) #start my Connection
    #x =vrep.simxStopSimulation(clientID,vrep.simx_opmode_oneshot)
    error_code =vrep.simxStartSimulation(clientID,vrep.simx_opmode_oneshot_wait)
    return clientID, error_code


def collectImageData(clientID):
    #get my vision sensor working and print the data in the while loop below for 5 seconds after simulation begins
    list_of_images = []
    collector = []
    if clientID!=-1:
        res,v0=vrep.simxGetObjectHandle(clientID,'Vision_sensor',vrep.simx_opmode_oneshot_wait)
        res,v1=vrep.simxGetObjectHandle(clientID,'PassiveVision_sensor',vrep.simx_opmode_oneshot_wait)
        ret_code, left_handle = vrep.simxGetObjectHandle(clientID,'DynamicLeftJoint', vrep.simx_opmode_oneshot_wait)
        ret_code, right_handle = vrep.simxGetObjectHandle(clientID,'DynamicRightJoint', vrep.simx_opmode_oneshot_wait)
        ret_code, base_handle = vrep.simxGetObjectHandle(clientID, 'LineTracerBase', vrep.simx_opmode_oneshot_wait)

        res,resolution,image=vrep.simxGetVisionSensorImage(clientID,v0,0,vrep.simx_opmode_streaming)
        t_end = time.time() + 2.8
        collision_bool = False
        count = 0
        while (vrep.simxGetConnectionId(clientID)!=-1 and time.time() < t_end):
            res,resolution,image=vrep.simxGetVisionSensorImage(clientID,v0,0,vrep.simx_opmode_buffer)

            #convert the image add to numpy array we collect about 35 images per simulation
            if res==vrep.simx_return_ok:
                #if we get the image now we need to get the state data this needs to be
                # print(count, len(list_of_images))
                action = 0 # I need to produce the action in a deep reinforcement learning algorithm but for now I will make the action 0
                ret_code, pos = vrep.simxGetObjectPosition(clientID, base_handle, -1, vrep.simx_opmode_oneshot)
                ret_code, velo, angle_velo = vrep.simxGetObjectVelocity(clientID, base_handle, vrep.simx_opmode_oneshot)
                collector.append([pos[0], pos[1], pos[2], velo[0], velo[1], velo[2], action])

                #got state data
                img = np.array(image,dtype=np.uint8)
                img.resize([resolution[1],resolution[0],3])
                rotate_img = img.copy()
                rotate_img = np.flipud(img)
                list_of_images.append(rotate_img)

                # scipy.misc.imsave(str(count) + 'outfile.png', rotate_img)
                count+=1

                #The following plays a video of the new image
                # cv2.imshow('image',rotate_img)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break
        return list_of_images, collector
    else:
        sys.exit()

def end(clientID):
    #end and cleanup
    error_code =vrep.simxStopSimulation(clientID,vrep.simx_opmode_oneshot_wait)
    vrep.simxFinish(clientID)
    return error_code

#check if there was a collision by calling globale variable set inside VREP
def detectCollisionSignal(clientID):
    detector = 0
    collision_str = "collision_signal"
    detector = vrep.simxGetIntegerSignal(clientID, collision_str, vrep.simx_opmode_oneshot_wait)
    start = time.time()
    while(time.time() < start +1):
        pass

    if detector[1] == 1:
        # print ("\nHit")
        return 1
    else:
        # print ("\nMiss")
        return 0

def detectCollisionSignalPerterbDistance(clientID):
    #get the current position of the robot
    lineTracerBase=vrep.simxGetObjectHandle(clientID, "LineTracerBase", vrep.simx_opmode_oneshot_wait)
    ret_code, pos=vrep.simxGetObjectPosition(clientID, lineTracerBase[1], -1, vrep.simx_opmode_oneshot_wait)

    if (abs(pos[0] - .057) > .07):
        return 1 #there is a hit
    else:
        return 0

def detectCollisionSignalPerterbAngle(clientID):

    lineTracerBase=vrep.simxGetObjectHandle(clientID, "LineTracerBase", vrep.simx_opmode_oneshot_wait)
    ret_code, pos=vrep.simxGetObjectOrientation(clientID, lineTracerBase[1], -1, vrep.simx_opmode_oneshot_wait)
    if abs(pos[2]) > .01:
        return 1 # there is a hit
    else:
        if abs(pos[0]) > .01:
            return 1
        else:
            if abs(pos[1]) > .1:
                return 1
            else:
                return 0
    return 0


def writeImagesStatesToFiles(image_array, state_array, n_iter, collision_signal):
    #save as the 5d tensor in theano style
    #I need a better way to select images from my video -- but for now just getting every tenth image be careful about images late in the game. -- prediction doesnt even help then
    reduced_image = []
    reduced_state = []
    #do it here

    time_dilation = round(np.random.normal(12, 3)) # make sure this system can work independent of the time dilation or hz of images coming in
    if time_dilation < 5:
        time_dilation == 5
    elif time_dilation > 20:
        time_dilation == 20 #set limits on how dilated the video it sees can be
    time_dilation = 15 #Leave this if you dont want to grab the right images

    reduced_image.append(image_array[0])
    reduced_state.append(state_array[0])

    for enumerator in range(len(image_array)):
        if enumerator % time_dilation == 0 and enumerator != 0:
            #create random number and decide on the enumerator value
            noise = random.uniform(0, 1) #dont grab every video at that exact offset
            if noise < .1:
                reduced_state.append(state_array[enumerator - 2])
                reduced_image.append(image_array[enumerator - 2])
            elif noise < .2:
                reduced_image.append(image_array[enumerator - 1])
                reduced_state.append(state_array[enumerator - 1])
            elif noise < .3:
                if enumerator + 1 < len(image_array):
                    reduced_state.append(state_array[enumerator + 1])
                    reduced_image.append(image_array[enumerator + 1])
            elif noise < .4:
                if enumerator + 2 < len(image_array):
                    reduced_state.append(state_array[enumerator + 2])
                    reduced_image.append(image_array[enumerator + 2])
            else:
                reduced_image.append(image_array[enumerator])
                reduced_state.append(state_array[enumerator])



    print("Cluster ", time_dilation, "  size of reduced array img and state ", len(reduced_image), len(reduced_state))
    selected_images = reduced_image[:70]
    selected_states = reduced_state[:70]
    # print("After slicing  ", len(selected_images))
            # scipy.misc.imsave(str(enumerator) + 'outfile.png', image_array[enumerator])

    video_arr = np.concatenate([arr[np.newaxis] for arr in selected_images])
    video = np.moveaxis(video_arr, -1, 1)
    state = np.asarray(selected_states) #this is ready to be saved!
    # print("hey bitch ", state_arr.shape)

    print (collision_signal)
    print (video.shape)
    print (state.shape)

    test_or_train = random.uniform(0, 1)
    if test_or_train < .45:
        if collision_signal:
            str_name_image = base_dir + '/data_generated/current_version/val/hit_image/' + str(n_iter) + 'collision3'
            str_name_state = base_dir + '/data_generated/current_version/val/hit_state/' + str(n_iter) + 'collision3'
            np.save(str_name_state, state)
            np.save(str_name_image, video)
        else:
            str_name_image = base_dir + '/data_generated/current_version/val/miss_image/' + str(n_iter) + 'collision3'
            str_name_state = base_dir + '/data_generated/current_version/val/miss_state/' + str(n_iter) + 'collision3'
            # np.save(str_name_state, state)
            # np.save(str_name_image, video)
        print(str_name_image, str_name_state)
    elif test_or_train < .9:
        if collision_signal:
            str_name_image = base_dir + '/data_generated/current_version/test/hit_image/' + str(n_iter) + 'collision3'
            str_name_state = base_dir + '/data_generated/current_version/test/hit_state/' + str(n_iter) + 'collision3'
            np.save(str_name_state, state)
            np.save(str_name_image, video)
        else:
            str_name_image = base_dir + '/data_generated/current_version/test/miss_image/' + str(n_iter) + 'collision3'
            str_name_state = base_dir + '/data_generated/current_version/test/miss_state/' + str(n_iter) + 'collision3'
            # np.save(str_name_state, state)
            # np.save(str_name_image, video)
        print(str_name_image, str_name_state)
    else:
        if collision_signal:
            str_name_image = base_dir + '/current_version/train/hit_image/' + str(n_iter) + 'collision3'
            str_name_state = base_dir + '/data_generated/current_version/train/hit_state/' + str(n_iter) + 'collision3'
            np.save(str_name_state, state)
            np.save(str_name_image, video)
        else:
            str_name_image = base_dir + '/data_generated/current_version/train/miss_image/' + str(n_iter) + 'collision3'
            str_name_state = base_dir + '/data_generated/current_version/train/miss_state/' + str(n_iter) + 'collision3'
            # np.save(str_name_state, state)
            # np.save(str_name_image, video)
        print(str_name_image, str_name_state)


def write_to_hit_miss_txt(n_iter, collision_signal, txt_file_counter):
    filename_newpos = base_dir + '/vrep_scripts/saved_vel_pos_data/current_position.txt'
    filename_miss = base_dir + '/vrep_scripts/saved_vel_pos_data/train/miss/miss' + str(txt_file_counter)
    filename_hit = base_dir + '/vrep_scripts/saved_vel_pos_data/train/hit/hit' + str(txt_file_counter)
    filename_get_velocity = base_dir + '/vrep_scripts/saved_vel_pos_data/velocity.txt'
    print("\n")
    #load the current velocity used
    with open(filename_get_velocity, "r") as new_vel_file:
        content = new_vel_file.readlines()
    content = [float(x.strip()) for x in content]

    #get the current position
    x_pos = x_list_of_positions[txt_file_counter]
    y_pos = y_list_of_positions[txt_file_counter]

    #save the current position velo data for future use
    save_data = np.asarray((x_pos, y_pos, z_permanent, content[0], content[1], content[2]))
    if collision_signal:
        print("SAVING HIT POS VELO ", filename_hit)
        np.save(filename_hit, save_data)
    else:
        print("SAVING MISS POS VELO ", filename_miss)
        np.save(filename_miss, save_data)

    with open(filename_newpos, "w") as new_pos_file:
        print(x_list_of_positions[txt_file_counter + 1], file=new_pos_file)
        print(y_list_of_positions[txt_file_counter + 1], file=new_pos_file)
        print(z_permanent, file=new_pos_file)

def single_simulation(n_iter, txt_file_counter):
    print("####################################################################################################################")
    clientID, start_error = start()
    image_array, state_array = collectImageData(clientID) #store these images
    collision_signal = detectCollisionSignal(clientID) #This records whether hit or miss
    if collision_signal == 0:
        collision_signal = detectCollisionSignalPerterbDistance(clientID) #backup check
        if collision_signal == 0:
            collision_signal = detectCollisionSignalPerterbAngle(clientID)
    end_error = end(clientID)
    if collision_signal:
        print("HIT")
    else:
        print("MISS")
    #need to append hit or miss pos and velo and need to rewrite over last 3 position values make sure I write this info to the file
    write_to_hit_miss_txt(n_iter, collision_signal, txt_file_counter)
    writeImagesStatesToFiles(image_array, state_array, n_iter, collision_signal)
    # write_play_data(image_array, n_iter, collision_signal) #This is for generating tiny amount of play data
    print("\n")

def main(iter_start, iter_end):
    txt_file_counter = 20000
    for current_iteration in range(iter_start, iter_end):
        single_simulation(current_iteration, txt_file_counter)
        txt_file_counter+=1


if __name__ == '__main__':
    main(0,10000)
