"""
Developed with 32-bit python on Windows 7. Might work in other environments,
but some of these APIs might not exist before Vista.

Much credit to Eric Blade for this:
https://mail.python.org/pipermail/python-win32/2009-July/009381.html
and David Heffernan:
http://stackoverflow.com/a/15898768/9585
"""


import win32con

import sys
import ctypes
import ctypes.wintypes

import time
import threading
from win32 import win32gui
import pywintypes
from win32api import GetSystemMetrics, ChangeDisplaySettings
import platform
import os
user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32
kernel32 = ctypes.windll.kernel32
dir_path = os.path.dirname(os.path.realpath(__file__))
print (dir_path)
print (os.getcwd())
loc_mm_res = os.path.join(os.path.dirname(__file__),"sofplus/data/mm_res")
loc_mm_res_desktop =  os.path.join(os.path.dirname(__file__),"sofplus/data/mm_res_desktop")

# force aware so can get accurate measurements of taskbar height
if platform.release() == '10':
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
elif platform.release() == '7':
    ctypes.windll.user32.SetProcessDPIAware()
else:
    sys.exit(1)


WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LONG,
    ctypes.wintypes.LONG,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD
)


# The types of events we want to listen for, and the names we'll use for
# them in the log output. Pick from
# http://msdn.microsoft.com/en-us/library/windows/desktop/dd318066(v=vs.85).aspx
processFlag = getattr(win32con, 'PROCESS_QUERY_LIMITED_INFORMATION',
                      win32con.PROCESS_QUERY_INFORMATION)

threadFlag = getattr(win32con, 'THREAD_QUERY_LIMITED_INFORMATION',
                     win32con.THREAD_QUERY_INFORMATION)
sofId = ""
resizeDone = 1
#timestamp of whne forground window was last sof
def callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread,
             dwmsEventTime):
    try:
        global lastTime
        global sofId
        #minimise a minimised window = bad?
        global sofMini
        global sofFull
        global resizeDone
        global origResDesktop
        global origResSof
        global cbuf_addText
        #if event == win32con.EVENT_OBJECT_FOCUS:
        fgWindow = win32gui.GetForegroundWindow()

        if fgWindow != sofId:
            t = threading.Timer(0.1,fgNotSoF)
            t.start()
        elif fgWindow == sofId:
            print(time.time())
            #reduce file reads
            if resizeDone == 0:
                origres = getSoFRes()
                #we have focus of sof
                if origres != getLiveDesktop():
                    #LALT bug theory:
                    #window must be minimised, desktop resized. then maximised
                    #else bug happens
                    win32gui.MoveWindow(sofId, 0, 0, origres[0], origres[1], False)
                    time.sleep(0.1)
                    win32gui.ShowWindow(sofId, win32con.SW_MINIMIZE)
                    time.sleep(0.1)
                    resizeDesktop(origres,1)
                    time.sleep(0.1)
                    win32gui.ShowWindow(sofId, win32con.SW_MAXIMIZE)
                    #win32gui.SetForegroundWindow(sofId) 
                    cbuf_addText(b';s_nosound 0;')
                    resizeDone = 1
            
    except KeyboardInterrupt:
        sys.exit(1)
def fgNotSoF():
    global sofId
    global cbuf_addText
    global origResDesktop
    global resizeDone
    while True:
        try:
            tup = win32gui.GetWindowPlacement(sofId)
            break
        except Exception as e:
            if e == KeyboardInterrupt:
                raise
            searchForSoFWindow()
    fgWindow = win32gui.GetForegroundWindow()
    if fgWindow != sofId:
        normal = 0
        minimized = 0
        if tup[1] == win32con.SW_SHOWMAXIMIZED:
            # print("mini false")
            minimized = 0
        elif tup[1] == win32con.SW_SHOWMINIMIZED:
            # print("mini true")
            minimized = 1
        elif tup[1] == win32con.SW_SHOWNORMAL:
            # print("normal true")
            normal = 1
        if not minimized or normal:
            win32gui.ShowWindow(sofId, win32con.SW_MINIMIZE)
        if origResDesktop != getLiveDesktop():
            #we know desktop res
            if not resizeDesktop(origResDesktop,0):
                print("Change res to original failed")
            else:
                cbuf_addText(b';s_nosound 1;')
                resizeDone = 0

def resizeDesktop(res,maxi):
    if getLiveDesktop() != res:
        print("resize desktop"+str(res))
        if not setRes(res[0],res[1]):
            print("failed setting sof resolution")
        else:
            return True
        if maxi == 1:
            #somehow fixes the LALT lag bug
            #win32gui.ShowWindow(sofId, win32con.SW_MINIMIZE)

            #win32gui.ShowWindow(sofId, win32con.SW_MAXIMIZE)
            pass

def setRes(x,y):
    
    devmode = pywintypes.DEVMODEType()

    devmode.PelsWidth = x
    devmode.PelsHeight = y
    devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
    if ChangeDisplaySettings(devmode, 0) != win32con.DISP_CHANGE_SUCCESSFUL:
        return False
    return True

def setHook(WinEventProc, eventType):
    return user32.SetWinEventHook(
        eventType,
        eventType,
        0,
        WinEventProc,
        0,
        0,
        win32con.WINEVENT_OUTOFCONTEXT
    )

def sofWinEnumHandler( hwnd, ctx ):
    global sofId
    #if win32gui.IsWindowVisible( hwnd ):
    #print (hex(hwnd), win32gui.GetWindowText( hwnd ))
    if win32gui.GetWindowText( hwnd ) == "SoF":
        sofId = hwnd
        return False
    return True

def searchForSoFWindow():
    global sofId

    sofId = ""
    while sofId == "":
        # print("cant find SoF,,, ill keep looking")
        try:
            win32gui.EnumWindows( sofWinEnumHandler, None )
        except Exception as e:
            if e == KeyboardInterrupt:
                raise
            pass
        if sofId == "":
            time.sleep(2)
    print("Found the SoF window")
    return sofId

def getSoFRes():
    #get res from SoFplus generated .cfg file
    #rect can not be trusted
    global loc_mm_res
    while True:
        try:
            with open(loc_mm_res, "r") as f:
                x = f.readlines()
            break
            pass
        except Exception as e:
            print(loc_mm_res)
            print("Error, please make sure you're running the SoFplus script and there is file called mm_res in sofplus/data")
            time.sleep(1)
    data = x[1].split()
    data = data[2][1:-1]
    print("sof RES from file "+ str(data))
    res = data.split("x")
    retRes={}
    retRes[0]=int(res[0])
    retRes[1]=int(res[1])
    '''
    while True:
        try:
            rect = win32gui.GetWindowRect(hwnd)
            break
        except Exception as e:
            if e == KeyboardInterrupt:
                raise
            hwnd = searchForSoFWindow()
    x = rect[0]
    y = rect[1]
    w = rect[2] - x
    h = rect[3] - y
    retRes[0] = w
    retRes[1] = h
    '''
    return retRes
def getOrigDesktop():
    global resDesktop
    global loc_mm_res_desktop
    while True:
        try:
            with open(loc_mm_res_desktop, "r") as f:
                x = f.readlines()
            break
            pass
        except Exception as e:
            print (loc_mm_res_desktop)
            print("Error, please make sure you're running the SoFplus script and there is file called mm_res in sofplus/data")
            time.sleep(1)
    data = x[1].split()
    data = data[2][1:-1]
    print("RES from file"+ str(data))
    res = data.split("x")
    resDesktop={}
    resDesktop[0]=int(res[0])
    resDesktop[1]=int(res[1])
    #print("Width =", GetSystemMetrics(0))
    #print("Height =", GetSystemMetrics(1))
    #resDesktop={}
    #resDesktop[0]=GetSystemMetrics(0)
    #resDesktop[1]=GetSystemMetrics(1)
    return resDesktop
def getLiveDesktop():
    resDesktop={}
    resDesktop[0]=GetSystemMetrics(0)
    resDesktop[1]=GetSystemMetrics(1)
    return resDesktop
def getLiveSof():
    while True:
        try:
            rect = win32gui.GetWindowRect(hwnd)
            break
        except Exception as e:
            if e == KeyboardInterrupt:
                raise
            hwnd = searchForSoFWindow()
    x = rect[0]
    y = rect[1]
    w = rect[2] - x
    h = rect[3] - y
    retRes[0] = w
    retRes[1] = h
    return retRes 

def main():
    global sofId
    global origResDesktop
    #wait for SoF id to be gotten first
    #then continue 
    
    searchForSoFWindow()
    origResDesktop={}
    origResDesktop = getOrigDesktop()
    print("SoF found. Adding hooks.")

    ole32.CoInitialize(0)

    WinEventProc = WinEventProcType(callback)
    user32.SetWinEventHook.restype = ctypes.wintypes.HANDLE

    focusHook = setHook(WinEventProc,win32con.EVENT_OBJECT_FOCUS)
    if not focusHook:
        print('SetWinEventHook failed')
        sys.exit(1)

    #sizeMoveHook = setHook(WinEventProc,win32con.EVENT_OBJECT_SHOW)
    #if not sizeMoveHook:
    #    print('SetWinEventHook failed')
    #    sys.exit(1)

    msg = ctypes.wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        user32.TranslateMessageW(msg)
        user32.DispatchMessageW(msg)
        # time.sleep(0.1)

    user32.UnhookWinEvent(focusHook)
    #user32.UnhookWinEvent(sizeMoveHook)
    ole32.CoUninitialize()

#WM_GETMINMAXINFO message
#~~~~~~~~~~~~~~~~~~~~~~~~~parse func
def func_parse(func_loc,func_name):
	with open(func_loc, 'r') as f:
		lines = f.readlines()

	funclist = {}
	cvar = ""
	counter = 0
	funcOpen = 0
	for x in lines:
		x = x.replace("\n", "%0a")
		x = x.replace("\"", "%22")
		x = x.replace("\t", " ")
		if x[0:8] == "function":
			if funcOpen == 0:
				funcOpen = 1
				cvar = x	
			else:
				funclist[counter] = ("\"" + str(cvar) + "\"")
				counter += 1
				cvar = x
		else:
			cvar += x
	funclist[counter] = ("\"" + str(cvar) + "\"")
	'''
	with open("injectme.txt", "w+") as f:
		for i in funclist:
			f.write(funclist[i] + "\n")
	'''
	func_load(funclist,func_name)

def func_load(funclist,func_name):
	global cbuf_addText
	init_func = func_name.replace(".func","_init")
	#This example just prints
	#The real version would enter these lines into the clients console using the python injector
	for x in funclist:
		cbuf_addText(b";set func_cvar %s;" % funclist[x].encode())
		cbuf_addText(b";~;")
		cbuf_addText(b";sp_sc_cvar_unescape func_cvar func_cvar;")
		cbuf_addText(b";~;")
		cbuf_addText(b";sp_sc_func_load_cvar func_cvar;")
		cbuf_addText(b";~;")
	cbuf_addText(b";sp_sc_func_exec %s;" % init_func.encode())
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def mayhem():
	global COM_Printf #echo
	global cbuf_addText
	# As has been mentioned before, all Python types except integers, strings, and bytes objects have
	# to be wrapped in their corresponding ctypes type, so that they can be converted to the required C data type:
	# Set up prototype and parameters for the desired function call
	COM_Printf_type = ctypes.CFUNCTYPE (
		None,
		ctypes.c_char_p
		)
	cbuf_addText_type = ctypes.CFUNCTYPE (
		None,
		ctypes.c_char_p
		)
	# hllApiParams = (1, "p1", 0), (1, "p2", 0), (1, "p3",0), (1, "p4",0)

	# Actually map the DLL function to a Python name `hllApi`.
	COM_Printf = COM_Printf_type (0x2001C6E0)
	cbuf_addText = cbuf_addText_type(0x20018180)
	cbuf_addText(b';s_nosound 0;')
	COM_Printf(b"Successfully Injected Your code\n")
	#func_name = "test_inject.func"
	#func_loc = os.path.join(annoying,func_name)
	#func_parse(func_loc,func_name)
	main()


if __name__ == '__main__':
	print('this script must be injected')
elif __name__ == '__mayhem__':
	mayhem()

'''
def injectFunc():

	//sound func template
	sp_sc_cvar_sset ~func   "function " #~fname "(*)" "%0a"
	sp_sc_cvar_append ~func "{" "%0a"
	sp_sc_cvar_append ~func     "set ~slot #~1" "%0a"
	sp_sc_cvar_append ~func     "sp_sc_flow_if number cvar spam_played_sound_$~slot == val 0" "%0a"
	sp_sc_cvar_append ~func     "{" "%0a" 
	sp_sc_cvar_append ~func         "set spam_played_sound_$~slot 1" "%0a"
	sp_sc_cvar_append ~func         "sp_sv_sound_register %22" #~sname "%22" "%0a"
	                              //play sound 'to' the player entity
	sp_sc_cvar_append ~func         "sp_sv_player_ent ~player_ent #~slot" "%0a"
	sp_sc_cvar_append ~func         "sp_sv_sound_play_ent %22" #~sname "%22 #~player_ent 0.9 0 0" "%0a"
	                              //Display 'fake' chat message
	sp_sc_cvar_append ~func         "sp_sv_info_client #~1" "%0a"
	sp_sc_cvar_append ~func         "sp_sc_func_exec client_say #~1 %22" #~str_chat "%22" "%0a"
	sp_sc_cvar_append ~func         "sp_sv_info_frames" "%0a"
	                              //Dont remove a sound if one was played less than 5 seconds ago
	sp_sc_cvar_append ~func         "set sound_spam_toggle #_sp_sv_info_frames" "%0a"
	sp_sc_cvar_append ~func         "sp_sc_func_exec sound_remove " #~sname "%0a"
	sp_sc_cvar_append ~func         "sset ~cmd set spam_played_sound_$~slot 0" "%0a"
	                              //One sound per 2 seconds
	sp_sc_cvar_append ~func         "sp_sc_timer 2000 #~cmd" "%0a"
	sp_sc_cvar_append ~func     "}" "%0a"
	sp_sc_cvar_append ~func     "else" "%0a"
	sp_sc_cvar_append ~func     "{" "%0a"
	                              //Stop spamming the sounds i told you to spam!" "%0a"
	sp_sc_cvar_append ~func         "sset ~msg %22%02Error: Stop spamming the sounds i told you to spam!%22" "%0a"
	sp_sc_cvar_append ~func         "sp_sv_print_client #~slot #~msg" "%0a"
	sp_sc_cvar_append ~func     "}" "%0a"
	sp_sc_cvar_append ~func "}"
	sp_sc_cvar_unescape ~func ~func
	sp_sc_func_load_cvar ~func
'''