import pandas as pd
import time
import psutil
import sys
from win10toast import ToastNotifier
# cross platform notifier... not using now
# from notifypy import Notify
sys.path.append('../')
import speedify
from speedify import State, SpeedifyError, Priority

# This program uses the speedify_cli to watch speedify for state and live streaming
# and then uses the psutil package to watch for excessive load that might interfere
# with steaming and shows hte users appropriate notifications.

# Issues:
#  * Notification is making a noise every time now.  I want silent notificaitons, the person is streaming!  fix https://stackoverflow.com/questions/56695061/is-there-any-way-to-disable-the-notification-sound-on-win10toast-python-library
#  * Not using the crossplatform notification library, would work on linux and mac if i did that
#  * There's a GPUUItl... but it only works on NVIDIA so i removed.
#  * Notifications show the app name as 'Python'.  It's true, and this is a prototype, so whatever.
#  * Wonder if there's a way to tell if there's  congestion that's causing stream to not hit full speed?

# If you don't see the notifications, it probably means you have Windows Focus Assist on.  Turn it off.

delay = 5 # sampling interval information

toaster = ToastNotifier()

low_memory = False
busy_cpus = 0
is_streaming = False


def notify(title, msg):
    global toaster
    try:
        # using win10toast... annoytingly does not have a silent option, though
        # the stackoverflow question above explains how to patch it, i don't care enough
        # for a throw away prototype
        toaster.show_toast(str(title),str(msg),icon_path="SpeedifyApp.ico")
        print("Toast: " +str(title) + " / " + str(msg))
    except Exception as e:
        print("Error showing notification " + str(e))

def get_cpu_info():
    ''' :return:
         memtotal: Total Memory
         memfree: free memory
         memused: Linux: total - free, used memory
         mempercent: the proportion of memory used
         cpu: CPU usage of each accounting
    '''
    global low_memory
    global busy_cpus
    mem = psutil.virtual_memory()
    memtotal = mem.total
    memfree = mem.free
    mempercent = mem.percent
    memused = mem.used
    cpu = psutil.cpu_percent(percpu=True)

    if mempercent > 90:
        if not low_memory:
            notify("Low Memory","Memory used: " + str(mempercent) + "%.  Can you close some apps or tabs?")
        low_memory = True
    else:
        low_memory = False

    busy_cpus_now = 0
    total_cores = 0
    for cpu_perc in cpu :
        total_cores = total_cores + 1
        if cpu_perc > 90:
            busy_cpus_now = busy_cpus_now + 1
    if (busy_cpus_now > 0 and busy_cpus != busy_cpus_now):
        notify("CPUs Busy", str(busy_cpus_now) + " / " + str(total_cores) + " CPU Cores busy. Can you close some apps or tabs?")
    if (busy_cpus_now == 0 and busy_cpus != busy_cpus_now):
        notify("CPUs Recovered", "No CPU Cores fully loaded")
    busy_cpus = busy_cpus_now

    # meh, load is in a future release of psutil that pip doesn't have yet
    #load = psutil.getloadavg()
    #print("load: " + str(loads))
    return memtotal, memfree, memused, mempercent, cpu


 # Main function
def main():
    times = 0
    global is_streaming
    stream_name = None
    last_state = "DISCONNECTED"
    while True:

                     # Prints the current time
        time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
                     # Obtain information CPU

        try:
            stats = speedify.stats(1)

            active_streams = False
            for json_array in stats:
                #print("object type: " + str(json_array[0]))
                if(str(json_array[0]) == "streaming_stats"):
                    streaming_right_now = False
                    #print("  IS streaming_stats")
                    #print("Item: " + str(json_array))
                    json_dict = json_array[1]
                    #print("json_dict" + str(json_dict))
                    streams_array = json_dict["streams"]
                    for stream in streams_array :
                        if stream["active"] == True:
                            active_streams = True;
                            if "name" in stream:
                                # lazy cheat.  if there's more than one stream, i'm
                                # going to end out just using the name of hte last
                                # one which is not really correct, but i'm just
                                # experimenting
                                app_name = stream["name"]
                            print("active stream")
                            streaming_right_now = True
                    if( streaming_right_now and not is_streaming):
                        notify("Live Stream","Speedify is enhancing " + app_name )
                    if( not streaming_right_now and is_streaming ):
                        notify("Stream Complete",app_name + " stream complete")
                    is_streaming = streaming_right_now
                if(str(json_array[0]) == "state"):
                    state_obj = json_array[1]
                    new_state = state_obj["state"]
                    if (new_state == "DISCONNECTED" or new_state == "DISCONNECTING") and is_streaming == True:
                        # stats returns things in whatever order it wants so there's no guarantee this will happen in this order to get caught
                        notify("Stream broke?!" , "Speedify disconnected during live stream")
                        is_streaming = False
                    elif ((new_state!= "CONNECTED") and last_state == "CONNECTED" ):
                        notify("Speedify Disconnected" , "Connect before streaming")
                    elif new_state != last_state and new_state == "CONNECTED":
                        notify("Speedify Connected" , "Ready to start streaming")
                        last_state = new_state
                    last_state = new_state
            if(active_streams):
                # only notify about busy cpu / memory if we think you're live streaming.  otherwise it wouldn't be speedify's business
                cpu_info = get_cpu_info()
                print(cpu_info)

        except speedify.SpeedifyError as sapie:
            print("SpeedifyError " + str(sapie))
        time.sleep(delay)
        times += 1



if __name__ == '__main__':
    main()
